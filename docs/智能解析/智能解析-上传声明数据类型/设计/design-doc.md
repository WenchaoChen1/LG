# 手动上传时声明 Actuals / Proforma · 设计文档

> 关联文档：
> - 上游（第二阶段 · 需求）：[requirement-doc](../需求/requirement-doc.md)，业务规则 R1~R12 与验收标准 AC1~AC11 在那里，本文不重复
> - 下游（第五阶段 · 开发设计）：[dev-design-doc](../开发设计/dev-design-doc.md)（总览）· [dev-python](../开发设计/dev-python.md) · [dev-java](../开发设计/dev-java.md) · [dev-frontend](../开发设计/dev-frontend.md) · [code-examples](../开发设计/code-examples.md)
> - 智能解析总体设计：[system-architecture](../../调研/system-architecture.md) · [java-design](../../调研/java-design.md) · [python-design](../../调研/python-design.md) · [frontend-design](../../调研/frontend-design.md)
> - 被取代的旧规则：[需求文档-Actuals导入中处理当前日历月数据](../../需求文档-Actuals导入中处理当前日历月数据.md)

本文只写**功能设计**：流程、接口契约、数据模型、各端处理规则和交互，不写代码级实现（那是第五阶段 `开发设计/`）。

**决策状态**：§9 中 D1~D10 已全部和产品确认；§10 剩四项设计稿细节待定，不影响后端。

**修订**：2026-10-10 按三端开发设计对照真实代码的核对结果修订 §4、§5、§6、§7、§10（返回码、uploadComplete 的校验范围、初始化判失败的新状态迁移、下游输入变化、前端现状细节）。

---

## 1. 现状（改造前）

| 环节 | 现在的做法 |
|---|---|
| 上传弹窗 | 只选文件，不选类型；点 Next 调 `commitUpload` 提交本批文件 |
| 类型判定 | **Python 按表判定**：先由大模型打标签，再按月份校正（全是过去月判 Actuals，最早月份在未来判 Proforma，混合则保留大模型的判断，大模型对混合表倾向判 Proforma） |
| 当月处理 | Python 把 Actuals 表的当月列**拆成一张 Proforma 表**，单元格带 `parentTableId`，映射页据此显示 "current month data may be incomplete" 横幅 |
| 映射页 | 每行可以手动改派 Actual / Forecast |
| Java 写入 | 完全按前端传来的每行类型写入；Actuals 写入前已经剔除当月和未来月（`isClosedActualsMonth`）；Proforma 不限月份 |
| QBO | 前端只对 Manual 公司显示 Import Statements 入口；后端没有 QBO 判断 |

## 2. 改造后的总体流程

```
上传弹窗：选文件 → 预签名 + 直传 S3（不变）→ 每个文件选类型（新增）→ Next
   │  commitUpload（新增：每个文件的类型）
   ▼
Java：建任务；写登记行，ai_file_registry.business_type = EXTRACT_FI_ACTUALS / EXTRACT_FI_PROFORMA（新增）
   │  SQS 发起抽取（消息不变）
   ▼
Python：init_task 读登记行的 business_type → 每个文件的声明类型（新增）
   │  抽取（不变）→ refine：
   │    ① 表的类型 = 文件声明类型（替代按月份校正）
   │    ② 声明为 Actuals：剔除当前月及以后的单元格（替代当月拆成 Proforma 表）
   ▼
写 mapping_data（单元格 source_data_type = 声明类型；新任务不再有 parentTableId）
   ▼
映射页：标签页按单元格类型分 Actuals / Proforma（不变）；不能再逐行改类型（新增限制）
   ▼
verify / complete（不变；Java 的 Actuals 当月护栏保留，作为第二道防线）
```

## 3. 数据模型

### 3.1 文件声明类型：复用 `ai_file_registry.business_type`（D2）
| 取值 | 含义 | 写入方 |
|---|---|---|
| `EXTRACT_FI_ACTUALS` | 财务抽取文件，用户声明为 Actuals | Java |
| `EXTRACT_FI_PROFORMA` | 财务抽取文件，用户声明为 Proforma | Java |
| `NULL` | 历史财务抽取文件（本需求之前上传） | — |

- **只用于 `purpose='financial_extract'` 的行**。`purpose='rag'` 的行继续使用 KNOWLEDGE_BASE / SESSION_UPLOAD / PLAYBOOK / ERL_ATTACHMENT 等原有取值。
- **复用的可行性**（2026-10-10 核实）：
  - 现有财务抽取行这一列全部为空，Java 从未写过它。
  - Python 读这一列的地方（知识库检索范围、记忆面板、会话文件、防改写保护）只匹配 rag 那几个取值，不会误纳入财务抽取行。
  - 防改写保护只在同一个 `file_id` 被重新登记时生效，财务文件的 `file_id` 是独立的，不会撞上。
- **不改表结构**：只更新列注释里的取值清单（Python 迁移 V030，只含 COMMENT），Java 实体和 Python ORM 的注释同步更新。
- **无需迁移数据**：历史行保持 NULL（需求 R11）。

### 3.2 单元格类型不变
`ai_financial_extraction_mapping_data.source_data_type` 仍然取 `ACTUALS` / `PROFORMA`，值等于所在文件的声明类型。`parent_table_id` 列保留，新任务恒为空，历史任务的值不动。

### 3.3 两种取值的对应关系（D3）
| 接口 / 单元格（对外） | 登记行 `business_type`（对内） |
|---|---|
| `ACTUALS` | `EXTRACT_FI_ACTUALS` |
| `PROFORMA` | `EXTRACT_FI_PROFORMA` |

前端和接口只用 `ACTUALS` / `PROFORMA`，与单元格类型同一套值。业务类型的命名不暴露给前端，只在 Java 写入、Python 读取时各转换一次。

## 4. 接口契约（前端 → Java）

路径前缀 `/api/web/ai/financialExtraction`。

| 接口 | 用在哪条路径 | 变化 |
|---|---|---|
| `POST /tasks/commitUpload` | 首次上传弹窗点 Next | 请求体改为 `{companyId, files: [{fileId, dataType}]}`（原为 `{companyId, fileIds}`）。`dataType` 必填，取值 `ACTUALS` / `PROFORMA`。响应不变（`taskId / committedFileIds / missingFileIds`） |
| `POST /tasks/getUploadUrl` | 映射页"上传新文件"、替换文件 | `fileList[]` 每项新增可选 `dataType`。带 taskId（映射页路径）时，Java 建 PENDING 登记行的同时写入类型。首次上传路径不带 taskId，不需要传（类型在 commitUpload 传） |
| `POST /tasks/{taskId}/uploadComplete` | 映射页"上传新文件"完成 | 请求不变。Java 校验本次**新上传（登记行状态为 PENDING）**的文件都已声明类型，缺失则拒绝。不校验任务里已解析过的文件：上线前建的任务，这些文件的类型为空（需求 R11 不补写） |
| `POST /tasks/{taskId}/file/replace` | 映射页"替换文件" | 请求不变。Java 把旧文件登记行的 `business_type` 复制给新文件（需求 R8：继承） |
| 其余接口（verify / complete / 删除 / 预览） | — | 不变 |

**校验与报错**（沿用本工程现有口径，工程里没有返回 HTTP 400 的路径）：
- 请求字段校验失败（commitUpload 缺 `files`、`dataType` 缺失或取值不合法）：**HTTP 422**，带字段级错误。
- 业务校验失败（同一文件给了两种类型、uploadComplete 有新文件未声明类型等）：**HTTP 200 + `success: false`** + 可读提示。
- 前端在提交前已经拦截（未选齐类型时 Next 不可用），这里是兜底；两种返回前端都按失败处理。

**Java → Python 的 SQS 消息**：不变。Python 从数据库读声明类型（D4），这样消息重投、任务重跑都读到同一个值。

**Python → 前端的拉取接口**（`/api/ai/financial-extract/tasks/{taskId}/extract-data` 及 increment）：不变。单元格的 `sourceDataType` 就是声明类型；新任务的 `parentTableId` 恒为空。

## 5. Python 处理规则

### 5.1 读取声明类型
- `init_task` 组装文件清单时，读每个文件登记行的 `business_type`，按 §3.3 转成 `ACTUALS` / `PROFORMA`，随文件信息一起往下传。
- 取值为空或不合法：**该文件判为失败**（文件状态 FILE_FAILED，给出"未声明类型"的错误信息），不再回退到旧的推断逻辑（需求 R11）。其余文件照常处理；全部文件都失败时任务失败，这与现有规则一致。
- 这是一个**新的状态迁移 UPLOADED → FILE_FAILED**（不经过 PROCESSING）：现在 FILE_FAILED 只会在落库阶段或处理中的文件被清理时出现。联调时要确认 Java 和前端按终态展示，没有"失败前一定经过 PROCESSING"的假设。

### 5.2 类型 = 声明类型（替代按月份校正）
- 文件内所有财务表的类型统一设为该文件的声明类型。
- 大模型在识别阶段给出的类型标签不再参与最终判定。是否同步清理提示词里的判定段落，在开发设计阶段决定，不影响功能。

### 5.3 Actuals 当前月保护（替代当月拆成 Proforma 表）
- **范围**：只对声明为 Actuals 的文件生效。
- **剔除对象**：月份**大于等于当前月**的单元格，按单元格剔除，不进入后续步骤，也不入库。
- **当前月**：处理时刻的 UTC 日期取年月（D6），由 refine 步骤自己计算——与传给大模型的参考日期算法相同，但不是同一次取值。Java 不参与这个判定。
- **时机**：放在补齐缺失月份之后，这样推算出来的月份（包括被推成"最后一月 + 1"的合计列）也会被检查。同时放在补行、补零、重复月份去重之前，这几步只处理最终会入库的单元格。
- **没有月份的单元格**（映射页 NO DATE）保留。用户在映射页给它指定月份后，如果是当前月或未来月，提交时会被 Java 现有的 Actuals 护栏挡住（需求 R4）。
- **整个文件的单元格都被剔除时**：文件按"解析完成但没有数据"处理，与现有的"没有识别到表"情形一致。弹窗顶部的说明横幅已经提前告知用户，不另加提示（需求 §七）。
- **Proforma 文件**：不做任何月份剔除（需求 R5）。

### 5.4 不受影响的部分
- **重复月份去重**：算法不变（需求 R10）。需要注意输入有两点变化：同一文件内的表类型统一了；Actuals 文件的当月及以后单元格在去重前就已剔除。回归测试时要对比去重结果。
- **补行与映射判定**：算法也不变，但输入同样会变——补行步骤原来会跳过"同名科目、模型判出的类型不一致"的组，类型统一后不再跳过；某一行唯一一个推算月份的单元格被剔除后，映射判定也不再因它降级。回归时一并对比。
- **训练信号、RAG 覆盖、任务级归一化**：都不看类型，不受影响。

## 6. Java 处理规则
- **写入类型**：commitUpload、getUploadUrl（带 taskId）、replaceFile 三个入口按 §4 写入或复制 `business_type`。取值转换（§3.3）集中在一处定义。
- **必填校验**：文件必须有声明类型（§4）。Java 不区分手动录入公司和 QBO 公司——QBO 公司本期看不到入口（需求 §七）。
- **上线前建的任务替换文件**：旧文件类型为空，新文件继承空值后会被 Python 判为失败（§5.1）。按 D9 不补写历史，本期按此处理，提示文案写明"未声明类型，请重新上传"。
- **complete 写入**：逻辑不变，仍按每行 `sourceDataType` 分成 Actuals 和 Proforma 两部分写入；Actuals 当月护栏保留。
- **SQS**：消息结构不变。

## 7. 前端交互设计

### 7.1 Upload Financial Documents 弹窗（Import Statements）
| 元素 | 规则 |
|---|---|
| 说明横幅 | 固定显示在顶部："For Actuals files, data for the current month and later is not extracted." |
| 选择文件区 | 不变（格式、大小限制、拖拽或点击） |
| 文件列表 | 列：FILE NAME / FILE SIZE / **TABLE TYPE** / Remove。TABLE TYPE 为下拉，选项 Actuals / Proforma，初始为空（占位文案见 §10） |
| 批量设置 | 列表底部 "Set table type for all files to ▾"，选中后所有文件都设为该类型；之后仍可逐个修改 |
| Clear All | 功能不变：和现在一样，只在有文件正在上传时显示，只取消正在上传的文件（是否改为常驻见 §10 Q4） |
| Next | 同时满足以下条件才可用：有文件、没有正在上传的文件、**每个文件都选了类型**、不在提交中。点击后调 commitUpload，带上每个文件的类型 |
| Cancel | 不变 |
| 宽度 | 现宽 560px 放不下新增的 TABLE TYPE 列，开发设计暂按加宽到 640px、手机上类型下拉折到第二行处理（见 §10 Q3） |

这个弹窗是新旧两版 Financial Entry（V2 默认、V1 回退）共用的，两版同时生效。

### 7.2 数据映射页
| 位置 | 变化 |
|---|---|
| 指派 LG 指标的下拉 | 去掉 Actual / Forecast 选项，只选指标；行的类型跟随单元格（即文件声明）。原来改回 "Unmapped Accounts" 时也能顺带改类型，同样去掉 |
| Upload New Document | 临时方案（待 §10 Q2）：先弹一个小窗选类型（无默认），确认后再打开文件选择框，本次选中的文件共用这个类型；调 getUploadUrl 时按文件带上 `dataType`。接口本身支持按文件传，以后改成逐个文件选只需改前端 |
| Replace Document | 不变，不询问类型（继承） |
| Actuals / Proforma 标签页 | 不变 |
| "current month data may be incomplete" 横幅 | 新任务不会再触发（`parentTableId` 恒为空）。代码保留：历史任务在映射页（含 devSupport 只读回放）仍会显示（D9） |
| 文案 | 统一为 "Proforma"（需求 R12） |

## 8. 发布与兼容

| 顺序 | 内容 | 原因 |
|---|---|---|
| 1 | Python 迁移 V030（只改 COMMENT） | 不影响运行，任何时间都可以执行 |
| 2 | **Java 与前端同批发布** | commitUpload 的请求体变了，两端必须同时切换，否则上传会被拒 |
| 3 | Python | Python 先发的话，新任务的登记行还没有类型，会全部失败。Java 先发时，旧版 Python 会忽略这一列，继续按旧逻辑推断，可以平滑过渡 |

**在途任务**：Python 发布时，还在排队的任务如果是 Java 发布之前提交的（登记行没有类型），会按 §5.1 判为失败（需求 R11）。

## 9. 决策台账
| # | 决策 | 结论 | 日期 |
|---|---|---|---|
| D1 | 声明粒度 | 按文件声明，一个文件一种类型；同一批次可以混合 | 2026-10-10 |
| D2 | 存储位置 | 复用 `ai_file_registry.business_type`，不新增列 | 2026-10-10 |
| D3 | 取值 | 登记行用 `EXTRACT_FI_ACTUALS` / `EXTRACT_FI_PROFORMA`；接口和单元格仍用 `ACTUALS` / `PROFORMA` | 2026-10-10 |
| D4 | Python 从哪里拿类型 | 从数据库登记行读取，SQS 消息不变 | 2026-10-10 |
| D5 | 当前月保护的提示方式 | 弹窗里的固定说明横幅，不做提取后的提示 | 2026-10-10 |
| D6 | "当前月"口径 | Python 用处理时刻的 UTC 年月（与传给大模型的参考日期同一算法）；Java 不参与 | 2026-10-10 |
| D7 | 默认类型 | 无默认值，必选 | 2026-10-10 |
| D8 | 映射页改派 | 不能再逐行改 Actual / Forecast；上传新文件要选类型，替换文件继承 | 2026-10-10 |
| D9 | 存量与在途任务 | 不迁移数据；类型为空的文件判失败，不回退到旧推断；当月横幅代码保留给历史回放 | 2026-10-10 |
| D10 | QBO | 本期不涉及（入口本来就只对 Manual 公司显示），下个 sprint 处理 | 2026-10-10 |

## 10. 待定（设计稿细节，不影响后端）
| # | 问题 |
|---|---|
| Q1 | TABLE TYPE 下拉未选择时的占位文案（暂用 "Select"） |
| Q2 | 映射页 Upload New Document 选择类型的交互样式（暂用"先选类型、再选文件"，见 §7.2） |
| Q3 | 上传弹窗加宽后的宽度与手机布局（暂按 640px，见 §7.1） |
| Q4 | Clear All 是否改为常驻（需求和设计稿画成常驻，现状只在上传中出现；本期按"功能不变"处理） |
