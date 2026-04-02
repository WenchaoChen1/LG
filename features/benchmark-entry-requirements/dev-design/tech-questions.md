# Benchmark Entry Requirements — 技术疑点

> 设计版本：v1.0 草稿
> 日期：2026-03-23

以下问题需要用户确认后，arch-designer 将据此修正设计文档。

---

## Q1：`metricId` 字段在接口与数据库之间的类型不一致

**背景**：设计文档中 `GET /benchmark/list` 响应和 `POST /benchmark/save` 请求体的 `metricId` 字段均使用枚举字符串（如 `"ARR_GROWTH_RATE"`）。但数据库表 `benchmark_detail.metric_id` 定义为 `VARCHAR(36)` 外键，关联 `benchmark_metric.id`（UUID）。如果 `metric_key` 枚举字符串长度超过 36 字符或结构不匹配，外键约束会失败；且初始化脚本用 `gen_random_uuid()` 生成 UUID，前端/后端不知道具体值。

**问题**：`benchmark_detail.metric_id` 存储的应该是 UUID（`benchmark_metric.id`），还是枚举字符串（`benchmark_metric.metric_key`）？接口中传递的 `metricId` 与数据库外键如何对应？

**选项**：

- A. `metric_id` 存 UUID，后端接口中 `metricId` 字段传枚举 key，后端自行查库转换为 UUID。（推荐：前端不感知内部 UUID，接口语义清晰）
- B. `metric_id` 直接改为存枚举 key（VARCHAR 50），去掉外键约束，简化关联逻辑。（简单但牺牲了数据库引用完整性）

**用户答案**：我需要一张表 怎么会有不一致存在  这些指标固定的使用枚举

---

## Q2：前端路由挂载位置

**背景**：设计文档将路由直接定义为顶级路径 `/benchmarkEntry`，配置 `hideInMenu: true`。但查看现有 `config/routes.ts`，所有业务页面都挂在 `'/'` → `SecurityLayout` → `BasicLayout` 嵌套结构内（如 `/company/projects`、`/profile` 等），这样才能复用已登录校验和侧边栏。设计文档直接在根级配置 `hideInMenu: true` 会绕过 SecurityLayout，导致未登录用户可访问该页面。

**问题**：`/benchmarkEntry` 路由应该挂在哪里？

**选项**：

- A. 挂在现有 `BasicLayout` 嵌套内（推荐：与所有业务页面一致，自动继承登录校验和侧边栏布局）
- B. 按设计文档挂在根级，同时补充手动登录校验逻辑。

**用户答案**：放到根目录下 不需要权限校验

---

## Q3：Platform 下拉选项的来源

**背景**：设计文档第 8 条"开发注意事项"说明"前端 Platform 下拉选项从后端返回的数据中获取（通过 list 接口的 `platformDisplayName` 字段），而非前端硬编码"。但实际上 `GET /benchmark/list` 接口只在每条已有的详情行中携带 `platformDisplayName`，没有单独的枚举列表字段。如果数据库中该 Metric 下还没有任何详情行，则从响应数据中提取不到任何 Platform 选项，新增行的 Platform 下拉会为空。

**问题**：Platform 枚举选项（Benchmarkit.ai / KeyBanc / High Alpha）是前端硬编码，还是由后端接口提供？

**选项**：

- A. 前端硬编码三个固定选项。（推荐：Platform 枚举由后端 Java enum 管理，当前固定 3 个值，前端跟后端枚举保持同步即可；无需额外接口）
- B. 在 `GET /benchmark/list` 响应中新增顶层 `platformOptions` 字段，统一返回所有平台枚举。（灵活但需修改接口结构）

**用户答案**：b

---

## Q4：货币开关状态是否需要后端持久化

**背景**：需求文档和设计文档均说明"货币转换开关仅保存 UI 状态，本期不做实际货币转换"。设计文档中前端将开关状态存入 React state（`currencySwitch: boolean`），但未说明是否需要持久化到后端——当用户刷新页面或换设备后，开关状态是否需要恢复。

**问题**：货币开关状态是否需要持久化（保存到后端或 localStorage）？

**选项**：

- A. 仅 React state，刷新后恢复默认值（开启），不持久化。（推荐：本期功能范围内开关无实际业务意义，不值得额外存储）
- B. 持久化到 localStorage（客户端，无需后端改动）。
- C. 持久化到后端（需新增接口和数据库字段）。

**用户答案**：暂时不处理货币

---

## Q5：并发编辑冲突策略

**背景**：设计文档第 7 节异常处理中明确标注"本期暂不实现乐观锁，采用'最后写入胜出'策略"，并标注"需确认"。当两个用户同时编辑同一条详情行，后保存的用户会覆盖前者的修改，前者不会收到任何通知。

**问题**："最后写入胜出"策略是否可以接受？还是需要增加乐观锁（`version` 字段）来检测并发冲突？

**选项**：

- A. 接受"最后写入胜出"，本期不实现乐观锁。（推荐：用户规模小，并发冲突概率极低；乐观锁会增加后端逻辑和前端错误处理复杂度）
- B. 实现乐观锁：`benchmark_detail` 表增加 `version` 字段，更新时校验版本号，冲突时返回 409 并提示用户刷新。

**用户答案**：b

---

**共 5 个问题，请全部回答后输入「继续」。**