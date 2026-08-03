# devSupport / Playbook Manage 页面设计

> 日期：2026-08-03 ｜ 状态：待评审（评审通过后进开发）
> 关联文档：[playbook 知识库设计](./2026-06-23-playbook-knowledge-design.md)、[playbook 实现计划](../plans/2026-06-23-playbook-knowledge.md)、[devSupport 财务提取模块](./2026-07-27-devsupport-financial-extract-module-design.md)、[待优化项台账](../../../python/CIOaas-python/docs/待优化项.md)

## 1. 需求

在 devSupport → RAG Management 下新增 **Playbook Manage** 页面，把 playbook 的运维从"手动 curl"搬上页面。三块功能：

1. **拉取在线 playbook** —— 抓源站整页 HTML 存 S3 并登记
2. **ingest 解析** —— 解析 + LLM 推断关系 + 向量化，产出一个 DRAFT 版本
3. **审核版本生效** —— 版本对比、人工修改关系、人工删除节点，审核通过后发布

第一阶段（2026-07-31）已用 curl 把 crawl → ingest → activate → 检索整条链路真实跑通，三版数据（v1 sonnet5 / v2 opus5 / v3 改版内容）都在库里。本次是把它页面化，并补上审核所需的能力。

## 2. 现状核实（逐条读码确认）

### 2.1 需求 1、2 的后端已就绪，需求 3 的后端全缺

`source/rag/interfaces/routes.py` 现有四个 playbook 端点：`POST /playbook/crawl`、`POST /playbook/ingest`、`POST /playbook/versions/{v}/activate`、`GET /playbook/versions`，全部走 `_require_admin`。前两个直接满足需求 1、2；`activate` 有，但**审核所需的一切（看节点、比版本、改关系、删节点）都没有**。

### 2.2 硬阻塞：网关 120 秒 < ingest 143 秒

```yaml
# java/CIOaas-api/deploy/cioaas-gateway.yml
connect-timeout: 5000
response-timeout: 120000        # 120 秒
```

ingest 实测耗时 **134–143 秒**（关系推断 76s + 63 条逐条向量化 64s + 其余）。**页面经网关调同步端点必定超时**——服务端会跑完、版本照样产出，但前端拿不到响应，也无从知道成功与否。第一阶段测试用 `curl --max-time 900` 直接打 8090 绕过了网关，所以这个问题没暴露。

顺带一个对照：rag 既有的文件入库长任务走的是 `BackgroundTasks`（`routes.py` 头注释明写"异步副作用（入库向量化 / 检索命中统计）走 BackgroundTasks"）。playbook 的 ingest 是同步的，属第一阶段"无页面、手动调用"下的合理简化，上页面后需与既有约定对齐。

### 2.3 没有任何节点级查询端点

`GET /playbook/versions` 返回的 `PlaybookVersionInfo` 只有版本元信息（version / status / node_count / relation_count / relation_model / file_id / note / created_by / created_at / activated_by / activated_at）。**没有端点能列出某版本的节点与关系**——而"人工修改关系"的前提是先能看到它们。

### 2.4 diff 只能拿到一次，且没有字段级差异

`_compute_diff` 逻辑已存在，但只在 ingest 响应体里返回，**看完就没了**，无法事后查询；基线是自动选的（优先 ACTIVE、回退上一个版本号），不能指定任意两版比对。

另外它的 `changed_pids` **只有 pid 列表**，没有"改了什么"——前端要展示"stage 从 Pre-Revenue 变 Early Traction"就得自己去查两版数据。

已知盲区（台账已记）：`attrs` 只比 `(category, stage, questions)`，**description 与正文不参与比较**。第一阶段改版测试实测：把 `insurance` 的 description 整句换掉，`changed_pids` 完全不出现它。

### 2.5 孤儿引用检测对"软删节点"失效（既有缺陷，直接影响删节点功能）

```sql
-- source/rag/domain/repository/playbook_repository.py: _ORPHAN_REFS_SQL
AND NOT EXISTS (
  SELECT 1 FROM ai_rag_playbook q
   WHERE q.pid = d.value AND q.version = p.version     -- 缺 AND NOT q.deleted
)
```

它只要求"那一行存在"，不管是否软删。而图扩展回查扩展节点的 `get_by_pids` **是**过滤 `deleted` 的。两者不一致的后果：**软删一个节点后，指向它的关系不被判为孤儿、activate 照样通过，但图扩展时那个前置/输入源静默消失**——正是 `find_orphan_refs` 注释里担心的"图扩展会静默少节点、完全不报错"，只是软删这条路径漏在防线之外。

### 2.6 activate 校验已预期软删，但不容许"多出行"

```python
# _integrity_checks
elif rows > expected:
    problems.append(f"属性行数 {rows} 多于 node_count {expected}（数据异常）")
```

`node_count` 是 ingest 最后一步回填的 **commit marker**。注释明确写了 `node_count` 当**上限**而非等值比，理由正是"运维手工软删掉一条坏 playbook 之后行数会少 1，若要求相等那个版本从此永远无法 activate"——**所以删节点是设计早已预期的操作，不需要改校验**。反过来，任何"增加节点"的功能都会撞上 `rows > expected` 这条，必须同步维护 `node_count`（本期不做加节点，见决策 3）。

### 2.7 现有校验不查依赖环（但遍历层面已防住，危害是纯语义的）

`_integrity_checks` 查四项（跑完了 / 行数合理 / entry 还在 / 每条有 profile）+ 孤儿引用，**不检测 `depends_on` 成环**。

⚠️ **先澄清一点：技术层面不会出事**。递归 CTE 自带路径防环：

```sql
SELECT p.pid::text, d.value, p.pid::text, 1, ARRAY[p.pid, d.value]::text[]   -- path 起手装了 seed
...
 WHERE w.depth < :hops
   AND NOT d.value = ANY(w.path)        -- 防环：走过的不再走
```

所以 `A → B → A` 的第二跳会被挡掉，**不会无限递归，也不会把 A 列成 A 自己的前置**。

真正的危害是**语义自相矛盾**：`A depends_on B` 且 `B depends_on A` 时，问 A 答"先做 B"、问 B 答"先做 A"，用户无法执行。环包括任意长度（`A→B→A`、`A→B→C→A`…），自环已被 `validate_edges` 拒。

所以环检测的定位是**审核期的数据质量闸门**（与"每条要有 profile""不能有孤儿引用"同性质），不是防崩溃。三版 LLM 推断实测**全部无环**（`depends_on` 各 40 / 30 / 22 条），说明自动流程里这不是问题；**人工编辑才是主要风险源**——表格逐行改看不到全局，给 B 加 `→A` 时很难注意到 A 已经 `→B`。

### 2.8 轮询设施基本就位，缺一个查询端点

`safe_begin` 在 ingest 流程**最开头**就返回 `op_id`；`safe_finish` 已把 `entry_count` / `chunk_count` / `total_tokens` / `duration_ms` 以及 extra 里的 `space_id` / `version` / `file_id` / `relation_model` / `relation_count` 全写进 `ai_rag_operation_log`。缺两样：**没有查询端点**（`routes.py` 里搜不到 operation_log 相关路由），以及 `empty_body_pids` 没写进 extra。

⚠️ **不能靠轮询版本列表代替状态查询**：ingest 的失败大头在关系推断（76 秒那步，第一阶段三次失败全在这），**那时版本行还没创建**，前端会一直看到"没变化"，无法区分在跑还是已挂。

### 2.9 前端挂载点

`src/pages/devSupport/_shell/DevSupportShell.tsx` 的 `rag` 分组（`title: 'RAG Management'`）items 数组现有 6 项（Overview / Spaces / Recall / Stats / Connections / BusinessAssociation）；路由在 `config/routes.ts`；页面目录 `src/pages/devSupport/rag/<子功能>/`。新增一项与现有子页同构。

## 3. 已定决策

| # | 决策 | 依据 / 后果 |
|---|---|---|
| 1 | **只允许修改 DRAFT 版本** | 审核的语义就是"发布前改"。改 ACTIVE 等于直接改线上数据且无回滚点，版本化设计的价值就没了 |
| 2 | **一期不做人工修改的跨版本继承** | 不动 `ai_rag_playbook` 表结构、无需新迁移。代价：源站更新后重新 ingest，之前所有人工修改归零、需重做。**这是已知取舍，不是 bug** |
| 3 | **不做"人工增加节点"** | 该需求的初衷是承载 LG 指标定义，而那条路已判定不成立（见 §7.1）。连带消除 §2.6 的 `node_count` 联动问题 |
| 4 | **关系编辑用表格；关系图完全不做**（连只读预览也不做） | 63 节点 / 50+ 边。表格实现简单、能批量改。图可视化对"审核每一条边"这个目标帮助有限，一期不投入 |
| 5 | **ingest 改异步**：返回 `operationId`，前端轮询状态 | §2.2 硬阻塞。不是优化，是"上页面就必须做" |
| 6 | **删节点一期就做**（软删） | §2.6 显示设计早已预期；审核发现坏手册想删是自然动作 |
| 7 | **人工改动往 `version.note` 追加一行** | 决策 2 不动表结构，故用 note 留痕。`_merge_note` 已是追加语义（不覆盖 ingest 时写的构建说明） |
| 8 | **版本列表不分页** | 版本增长很慢（一次 ingest 一版），现有 `list_versions(limit=50)` 足够。真到 50 版时再说 |
| 9 | **页面不做模型选择器，固定用后端默认 opus5** | 后端 `relationModel` 参数与白名单（opus5 / sonnet5）保留，需要跑 sonnet5 做对比时仍可 curl 传，页面不暴露这个选择。后续要加只是前端一个控件 |

## 4. 架构

```
Playbook Manage 页面
   │
   ├─ 拉取 ──── POST /playbook/crawl ─────────────── 同步（实测 6.4s，网关内）
   │
   ├─ 解析 ──── POST /playbook/ingest ────────────── 立刻返回 operationId（后台跑 143s）
   │              └─ 轮询 GET /playbook/ingest/{id} ── 读 ai_rag_operation_log
   │
   └─ 审核 ──── GET  /playbook/versions ──────────── 版本列表
                GET  /playbook/versions/{v}/nodes ── 节点 + 关系（表格数据源）
                GET  /playbook/versions/{v}/diff ─── 字段级差异，可指定 against
                PATCH .../nodes/{pid}/relations ──── 改关系（立即校验，含环检测）
                DELETE .../nodes/{pid} ───────────── 软删 + 清理反向关系
                POST /playbook/versions/{v}/activate  发布（跑完整性校验）
```

ingest 的异步时序（前端可据此给进度提示，各阶段耗时来自第一阶段实测）：

| 时刻 | 后台在做 | 前端可见 |
|---|---|---|
| 0s | `safe_begin` 写审计行 | 拿到 operationId，状态 `STARTED` |
| ~1s | 取素材（S3 下载） | 仍 `STARTED` |
| ~2s | 解析 62–63 节点 | 仍 `STARTED` |
| 2s–78s | **LLM 推断关系（唯一 LLM 调用，期间零输出）** | 仍 `STARTED`（提示"正在推断关系，约 1–2 分钟"） |
| ~78s | 建 DRAFT 版本行 | 仍 `STARTED` |
| 78s–142s | 逐条写 entry + 向量化（63 次 embedding） | 仍 `STARTED` |
| ~143s | 回填 node_count + 写审计终态 | `SUCCESS` + version / node_count / chunk_count |

失败可能落在任一阶段；`STARTED` → `FAILED` 时 `err_message` 给原因（第一阶段的三次失败都是关系推断被 `max_tokens` 截断，现已修）。

## 5. 后端设计

### 5.1 端点契约

| 端点 | 方法 | 说明 |
|---|---|---|
| `/playbook/crawl` | POST | **不改**。透传 Authorization 给 Java 预签名 |
| `/playbook/ingest` | POST | **改异步**：经 `BackgroundTasks` 投递，立刻返回 `{operationId}`；`empty_body_pids` 补写进 operation_log 的 extra |
| `/playbook/ingest/{operation_id}` | GET | **新增**。返回 `status`（STARTED/SUCCESS/FAILED）+ 成功时的 version/nodeCount/chunkCount/totalTokens/relationCount/emptyBodyPids + 失败时的 errClass/errMessage + durationMs |
| `/playbook/versions` | GET | **不改** |
| `/playbook/versions/{v}/nodes` | GET | **新增**。每节点：pid / title / category / stage / questions / dependsOn / feeds / refersTo / hasBody / entryId。表格数据源 |
| `/playbook/versions/{v}/diff` | GET | **新增**。query `against`（缺省沿用 `_compute_diff` 的基线选择）。除现有五项外，`changedPids` 升级为**字段级**：每项给 pid + 变了哪个字段 + 前后值 |
| `/playbook/versions/{v}/nodes/{pid}/relations` | PATCH | **新增**。body 三个数组（全量覆盖语义）。**仅 DRAFT**，立即校验 |
| `/playbook/versions/{v}/nodes/{pid}` | DELETE | **新增**。软删 + 清理反向关系。**仅 DRAFT** |
| `/playbook/versions/{v}/activate` | POST | **不改** |

全部沿用 `_require_admin`（playbook 是平台运营方维护的全局内容，公司端账号无权维护）。

### 5.2 关系修改的校验（PATCH 时立即执行，不等到 activate）

| 校验 | 失败处置 | 来源 |
|---|---|---|
| 目标 pid 在本版本内存在且未软删 | 拒绝 | 复用 `validate_edges` 的幻觉 pid 检查口径 |
| 不自引用 | 拒绝 | 同上 |
| 关系类型只能是三列之一 | 拒绝 | 列名即类型 |
| 本版本关系总数 ≤ 节点数 × 1.5 | 拒绝 | `RELATION_COUNT_MULTIPLIER`，主防线是防 2 跳图扩展 context 爆炸 |
| **`depends_on` 不成环**（任意长度） | 拒绝 | **新增**（§2.7）。递归 CTE 自带路径防环、不会崩，拦的是**语义自相矛盾**（问 A 说先做 B、问 B 说先做 A）。改完立即在内存图上跑一次 DFS |

立即校验而非留到 activate 的理由：编辑态给即时反馈；且 activate 的完整性校验是"发布前最后一道防线"，不该承担交互反馈职责。

### 5.3 删节点的三步

1. **软删属性行**（`deleted = true`）——`list_entry_ids` / `count_active_rows` / `relation_element_count` 都过滤 `deleted`，所以该节点立刻退出检索范围与统计
2. **清理反向关系**——把该 pid 从其余节点的三个数组里移除。不做这步会留下"指向已软删节点"的边，而它**不会被孤儿检测发现**（§2.5），图扩展时静默少节点
3. **修 `_ORPHAN_REFS_SQL`，补 `AND NOT q.deleted`**——防线。这样万一别处软删了节点未清理关系，activate 会 loud fail 而非静默降级。属修既有缺陷，一行 SQL

**不动 entry 与 chunk**：那条 entry 及其 profile/body chunk 留在库里但不再被任何版本引用（检索圈定靠 `list_entry_ids`）。与台账里"版本清理端点"那条同源——库里本来就有一批未被引用的 entry/chunk 等着统一清理，此处不额外处理，避免被误认为新增泄漏。

### 5.4 note 留痕

改关系 / 删节点成功后，往 `version.note` 追加一行（含操作类型、pid、操作人、时间）。目的是让版本列表里能直接看出"这版被人工改过"，事后追溯不必翻日志。`_merge_note` 已是追加语义，不会覆盖 ingest 时写的构建说明。

## 6. 前端设计

### 6.1 挂载

`DevSupportShell.tsx` 的 `rag` 分组 items 追加一项（`key: 'rag-playbook'`、`label: 'Playbook'`、`path: '/devSupport/rag/playbook'`）；`config/routes.ts` 加路由；新建 `src/pages/devSupport/rag/playbookManage/`。locales 若有菜单文案需同步。

### 6.2 页面结构（单页三区）

**操作区**（顶部）
- 「拉取源站」按钮 → crawl。成功展示 fileId / cardCount / 字节数；被拒时展示原因（源站卡片数低于下限 = 可能是登录页/反爬页/改版）
- 「解析」按钮 → ingest。点击后进入**进度态**：轮询状态端点，按 §4 的时序给文案（关系推断那 76 秒是纯等待，必须有明确提示，否则会被当成卡死）。**进行中禁用按钮**——两人同时点会撞版本号（`next_version` 无锁，后提交方报"版本号已被占用"）
- **不给模型选择器**（决策 9）：不传 `relationModel`，走后端默认 opus5

**版本列表**（中部表格，**不分页**——决策 8）
- 列：version / status / nodeCount / relationCount / relationModel / note / createdBy / createdAt / activatedBy / activatedAt
- 行操作：`审核`（进审核视图）、`发布`（仅 DRAFT，且校验通过）

**审核视图**（点某版本进入）
- **diff 面板**：与基线版本的对比（新增/删除 pid、字段级属性变更、关系增删）。⚠️ 需在界面上注明 **description 与正文不参与比较**（§2.4 盲区），提示审核者另行抽查正文
- **节点表格**：每行一节点，列 = pid / title / category / stage / questions / 三个关系列。关系列用多选控件（候选 = 本版本其余节点），**仅 DRAFT 可编辑**
- 行操作：`删除节点`（仅 DRAFT，二次确认）
- 校验失败时就地展示原因（幻觉 pid / 自引用 / 超上限 / **成环**）
- **不做关系图**（决策 4），连只读预览也不做

## 7. 非目标（本期明确不做）

### 7.1 用 playbook 承载 LG 指标定义

需求侧提出把 30+ 个 LG 指标定义放进 playbook（起因：AI 回答的 Sales Efficiency Ratio 定义与 LG 系统互为倒数）。**已查证该路不成立**：

- LG 的定义**已经在系统提示词里**（`retrieval_agent_prompt._RULES` 的「LG 特殊指标口径」段就有 Sales Efficiency Ratio 与 Monthly Net Burn Rate）
- 错误答案来自 **playbook 正文**：`sales-efficiency-ratio` 手册原文写的是 "the ratio of annualized recurring revenue from a period to the S&M expenses"，即 `ARR / S&M`，正是 LG 定义（`S&M / New MRR LTM`）的倒数
- 更深一层：同段正文的 "a ratio less than 0.7 indicates it might be time to spend more money on S&M" —— **连"好/坏"的方向都是反的**（LG 口径下比值越小越好）
- 所以把 LG 定义再加进 playbook = 同一个库里两个矛盾定义，检索可能召回任一个甚至同时召回，**比现状更糟**

正确方向在提示词层（后续单独处理）：把 `_RULES` 那段的措辞从"与**通用知识**冲突"扩到"与**检索到的任何文档（含 playbook）**冲突"；只补真正与通用定义冲突的 6–8 个指标（不是全部 30 个）；在 `search_playbooks` 工具描述里注明"其中指标定义/公式/阈值可能与 LG 口径不同，涉及定义时以 LG 为准"。

### 7.2 其余不做项

- **人工修改的跨版本继承**（决策 2）：需要在属性行上加来源标记 + 迁移逻辑，动表结构
- **人工增加节点**（决策 3）
- **从已有版本克隆出 DRAFT**：ACTIVE 版本的关系若需修正，当前只能重跑 ingest（花约 $0.2，且关系会全部重新推断、与原版仅约一半重叠）。将来嫌重可加一个纯 DB 复制的克隆端点（复用同一批 entry/chunk，不花 LLM 钱）
- **正文/description 纳入 diff**：台账已记，两条改法（纳入 attrs / 给正文算内容指纹存进属性行）都待排期
- **版本数据清理**：台账已记

## 8. 风险与注意事项

| 风险 | 说明 |
|---|---|
| 每次 ingest 花真金白银 | opus5 约 $0.21/次（实测）。页面上"解析"按钮易被反复点，需进行中禁用 + 二次确认 |
| 人工修改随下次 ingest 归零 | 决策 2 的直接后果。页面上应明示，避免运维投入大量人工编辑后困惑 |
| 关系是 LLM 推断产物、每次重新掷骰子 | 实测：同模型同内容仅改一个标题词，关系重叠只有 27/54；换模型重叠 20/63。**diff 每次都得真审**，不能因"这次改动小"跳过 |
| 审核成本 | 63 节点 / 50+ 关系，一轮人工审需要懂业务的人。这是 playbook 质量的唯一闸门（关系无金标，无法自动评价） |
| 并发 ingest | `next_version` 无锁，两次并发会有一方失败并返回友好提示。页面侧禁用即可，不需要加锁 |

## 9. 待确认

无。原三项（版本列表分页 / 关系图只读预览 / 解析是否可选模型）已于 2026-08-03 确认，分别落为决策 8、决策 4、决策 9。
