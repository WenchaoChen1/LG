# 测试用例：月度基准更新邮件

- **需求来源**：`docs/Finance email+条幅+提醒/Implement Monthly Benchmark Email Reports_需求文档.md`
- **生成时间**：2026-04-23

---

## 需求清单

| #   | 需求类型 | 需求描述 |
|-----|----------|----------|
| R1  | 功能需求 | 新 closed month 提交触发：每日定时检测，有新 closed month 时发送邮件，始终与上封邮件的百分位比较 |
| R2  | 功能需求 | 每月 25 号定期触发邮件，始终与上封邮件的百分位比较 |
| R3  | 数据需求 | closed month 定义：Manual 公司取 Financial Entry 最后一条有 Actuals 月份；Automatic 公司按服务器时间 15 号为界限，并回溯至有 Actuals 的月份 |
| R4  | 业务规则 | Company Admin：每次触发都收邮件，与上封邮件百分位比较，**无静默更新场景** |
| R5  | 业务规则 | Portfolio Manager：仅接收投资组合内有重大变化的公司汇总，未达阈值时触发静默更新（不发邮件） |
| R6  | 业务规则 | 重大变化定义①：任何指标 Actual 百分位移动 ≥ 5 点（含 5；覆盖 Internal Peers 与任一外部基准） |
| R7  | 业务规则 | 重大变化定义②：任何指标 Actual 百分位跨越分位数边界。边界规则：Q1: P0≤n<P25；Q2: P25≤n<P50；Q3: P50≤n<P75；Q4: P75≤n≤P100 |
| R8  | UI 需求  | Company Admin 邮件标题：`Benchmarking Report for [CompanyName] — [ClosedMonth Year]` |
| R9  | UI 需求  | Company Admin 邮件问候语：`Hello [CompanyAdminName]` |
| R10 | UI 需求  | Company Admin 邮件情况简介文案：`Your latest financials for [CompanyName] have been updated through [ClosedMonth Year]. Benchmark movement reflects updated company financials. Below is a summary of how your company's performance compares to both industry benchmarks and your peers in Looking Glass:` |
| R11 | 业务规则 | 首封邮件无法计算变化幅度 → 直接发送并记录当前百分位为基准 |
| R12 | 业务规则 | 下次计算变化幅度时，与"最近一次存储的基准"对比（邮件触发或静默更新都作数） |
| R13 | 业务规则 | 邮件发出时记录当前百分位为收件人新基准 |
| R14 | 功能需求 | Company Admin 邮件始终包含全部 6 个基准指标的详细数据 |
| R15 | UI 需求  | Portfolio Manager 邮件标题：`Your Benchmarking Summarized Report is Ready` |
| R16 | UI 需求  | Portfolio Manager 邮件问候语：`Hello [PortfolioManagerName]` |
| R17 | UI 需求  | Portfolio Manager 邮件情况简介文案：`Your latest financials for [PortfolioName] have been updated. Benchmark movement reflects updated company financials. Below is a summary of companies with meaningful changes in benchmark positioning based on the latest financial updates.` |
| R18 | UI 需求  | Portfolio Manager 邮件公司清单排序：英文 A-Z 在前，中文首字母 A-Z 在后 |
| R19 | 业务规则 | Portfolio Manager 邮件：每家入选公司仅展示有重大变化的指标 |
| R20 | 业务规则 | Portfolio Manager 首封邮件展示所有公司快照，不做重要变化阈值过滤 |
| R21 | 业务规则 | PM 端：新 closed month 入库但未达重要变化阈值 → 静默更新基准 |
| R22 | 业务规则 | PM 端：Closed month 数据被修订但未达重要变化阈值 → 静默更新基准 |
| R23 | UI 需求  | 指标展示顺序：ARR Growth Rate → Gross Margin → Monthly Net Burn Rate → Monthly Runway → Rule of 40 → Sales Efficiency Ratio |
| R24 | 功能需求 | 每个指标板块必含 Actuals 行 |
| R25 | UI 需求  | Actuals 行内容：Actual 值、Internal Peers 百分位、KeyBanc 2026、High Alpha 2026、Benchmarkit.ai 2026；每项带变化标记 |
| R26 | UI 需求  | 百分位变化标记：↑ 上升 / ↓ 下降 / 无标记；格式 `P63 ↑ (moved up from P58)` / `P55 ↓ (moved down from P70)` / `P55` |
| R27 | 业务规则 | 预测行优先展示 Committed Forecast；无 CF 时展示 System Generated Forecast；两者都无则不显示预测行 |
| R28 | UI 需求  | Committed Forecast 行包含：Actual 值、Internal Peers、KeyBanc 2026、High Alpha 2026、Benchmarkit.ai 2026 |
| R29 | 数据需求 | 内部同行百分位用 Nearest Rank 法计算 |
| R30 | 数据需求 | 外部基准百分位用线性插值法计算 |
| R31 | 数据需求 | 百分位移动与上一个 closed month 存储的基准对比 |

---

## 测试用例

### 一、邮件触发机制

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-001 | 新 closed month 提交触发 | 公司 A 上一 closed month 为 2026-02，CA/PM 已收过对应邮件；Financial Entry 新增 2026-03 Actuals 数据 | 每日定时任务执行检测 | 系统识别 2026-03 为新 closed month，生成基准邮件并发送给 CA 与 PM |
| TC-002 | 同一新 closed month 不重复触发 | 新 closed month 触发一次后，当日定时任务再次执行 | 观察邮件发送 | 不重复发送邮件 |
| TC-003 | 25 号月度定期触发 | 系统服务器时间 2026-04-25 00:00 | 25 号定时任务执行 | 针对所有在监测范围内的公司生成并发送基准邮件 |
| TC-004 | 非 25 号且无新 closed month 不触发 | 服务器时间 2026-04-20；无公司产生新 closed month | 每日定时任务执行 | 不发送月度基准邮件 |
| TC-005 | 25 号恰逢新 closed month 仅发一封邮件 | 2026-04-25 当天 CA 端同时满足"25 号月度"与"新 closed month 提交" | 定时任务执行 | 接收人不收到重复邮件，合并为一封邮件发送 |

### 二、closed month 判定规则

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-006 | Manual 公司取最后一条 Actuals 月份 | 公司 Financial Statements Settings = Manual；Financial Entry 最后一条 Actuals 为 2026-02 | 系统读取 closed month | closed month = 2026-02 |
| TC-007 | Manual 公司无 Actuals 不参与发送 | Manual 公司 Financial Entry 无任何 Actuals 记录 | 触发任务执行 | 该公司被跳过，不发送邮件 |
| TC-008 | Automatic 公司未过 15 号取上上月 | Settings = Automatic；服务器时间 2026-04-10；2026-02 有 Actuals | 读取 closed month | closed month = 2026-02 |
| TC-009 | Automatic 公司已过 15 号取上月 | Settings = Automatic；服务器时间 2026-04-20；2026-03 有 Actuals | 读取 closed month | closed month = 2026-03 |
| TC-010 | Automatic 公司服务器时间恰好 15 号 00:00 边界 | Settings = Automatic；服务器时间 2026-04-15 00:00 | 读取 closed month | 按"未过 15 号"判定 → 取上上月 |
| TC-011 | Automatic 公司服务器时间 15 号 23:59 边界 | Settings = Automatic；服务器时间 2026-04-15 23:59 | 读取 closed month | 按"未过 15 号"判定 → 取上上月 |
| TC-012 | Automatic 公司服务器时间 16 号 00:00 边界 | Settings = Automatic；服务器时间 2026-04-16 00:00 | 读取 closed month | 按"已过 15 号"判定 → 取上月 |
| TC-013 | Automatic 目标月无 Actuals 向历史回溯 | 服务器时间 2026-04-20；2026-03 无 Actuals；2026-02 有 Actuals | 读取 closed month | closed month = 2026-02 |
| TC-014 | Automatic 多月无 Actuals 连续回溯 | 服务器时间 2026-04-20；2026-03 与 2026-02 均无 Actuals；2026-01 有 Actuals | 读取 closed month | closed month = 2026-01 |

### 三、Company Admin 邮件接收逻辑

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-015 | CA 每次触发都收邮件 | Company A 连续两个月产生新 closed month；CA Jacobo | 前后两次触发任务执行 | Jacobo 收到 2 封邮件，分别对应两个月 |
| TC-016 | CA 首封邮件无阈值过滤 | Company B 首次产生 closed month；CA 未收过任何邮件 | 触发任务执行 | 直接发送首封邮件，包含所有 6 个指标；系统记录当前百分位为新基准 |
| TC-017 | CA 端无静默更新 | Company A 本月与上月百分位变化均 < 5 点且无分位数跨越 | 25 号触发 | CA 仍然收到邮件（因 CA 无静默更新场景） |
| TC-018 | CA 邮件百分位比较基于上次存储基准 | 公司上次邮件发出时记录 ARR Growth Rate Internal Peers 基准为 P58；本月实时为 P65 | 触发 CA 邮件 | 邮件中 ARR Growth Rate Internal Peers 显示 `P65 ↑ (moved up from P58)`；邮件发出后基准更新为 P65 |
| TC-019 | Company 仅绑定在某 Portfolio 下 | Company C 绑定 Portfolio P1；CA 为 Jacobo | 触发任务执行 | Jacobo 仅收到 Company C 的邮件 |

### 四、Company Admin 邮件标题、问候与情况简介

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-020 | CA 邮件标题格式 | CompanyName = Card Medic；closed month = 2026-03 | 查收邮件 | 标题为 `Benchmarking Report for Card Medic — March 2026` |
| TC-021 | CA 邮件问候语占位符替换 | CA 实际姓名 Jacobo Vargas | 查看邮件正文首行 | 显示 `Hello Jacobo Vargas` |
| TC-022 | CA 邮件情况简介占位符替换 | CompanyName = Card Medic；closed month = March 2026 | 查看情况简介段落 | 完整包含 `Your latest financials for Card Medic have been updated through March 2026. Benchmark movement reflects updated company financials. Below is a summary of how your company's performance compares to both industry benchmarks and your peers in Looking Glass:` |
| TC-023 | CA 邮件含 6 个指标板块 | 公司有全部 6 个指标的 Actuals | 查看邮件正文 | 依次展示 ARR Growth Rate、Gross Margin、Monthly Net Burn Rate、Monthly Runway、Rule of 40、Sales Efficiency Ratio 共 6 个板块 |
| TC-024 | CA 邮件指标顺序固定 | 同 TC-023 | 观察邮件正文 | 6 个指标严格按需求列出的顺序排列，不因数据变化而重排 |

### 五、Portfolio Manager 邮件接收逻辑

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-025 | PM 首封邮件展示所有公司 | PM Jacobo 管理 Portfolio P1，P1 含 3 家公司；PM 未收过任何邮件 | 触发任务执行 | Jacobo 收到 1 封 PM 汇总邮件，公司清单包含全部 3 家公司（不做阈值过滤）；系统记录所有公司当前百分位为基准 |
| TC-026 | PM 常规触发仅包含有重大变化公司 | PM 曾收过邮件；P1 下 3 家公司中仅 Company A 本次有指标达到阈值 | 触发 | 邮件公司清单仅含 Company A；其他 2 家未列出，基准静默更新 |
| TC-027 | PM 所有公司都未达阈值不发邮件 | PM 曾收过邮件；P1 下所有公司本次都未达阈值 | 触发 | 不发送 PM 邮件；所有公司基准静默更新为当前百分位 |
| TC-028 | PM 跨 Portfolio 分别收邮件 | PM 同时管理 P1、P2 | 触发任务执行 | 每个有重大变化公司所属的 Portfolio 单独发一封邮件；P1、P2 各一封 |
| TC-029 | PM 静默更新：新 closed month 未达阈值 | 公司 A 新 closed month 入库，所有指标变化均 < 5 且无分位跨越 | 触发 | PM 不发送该公司邮件；系统将公司 A 基准静默更新为当前百分位 |
| TC-030 | PM 静默更新：closed month 数据修订未达阈值 | closed month 数据被修订，重算后变化未达阈值 | 触发 | PM 不发送该公司邮件；静默更新基准 |
| TC-031 | PM 基准对比最近一次存储值（邮件或静默） | 公司 A 上次是静默更新为 P60；本次实时为 P66（+6，达阈值） | 触发 | PM 邮件内该指标显示 `P66 ↑ (moved up from P60)`，说明静默更新的基准被用作对比基线 |

### 六、Portfolio Manager 邮件标题、问候、情况简介与公司清单排序

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-032 | PM 邮件标题固定 | PM 触发邮件 | 查收邮件 | 标题为 `Your Benchmarking Summarized Report is Ready` |
| TC-033 | PM 邮件问候语占位符替换 | PM 姓名 Jacobo Vargas | 查看首行 | 显示 `Hello Jacobo Vargas` |
| TC-034 | PM 邮件情况简介占位符替换 | PortfolioName = GSV Fund III | 查看简介段落 | 完整包含 `Your latest financials for GSV Fund III have been updated. Benchmark movement reflects updated company financials. Below is a summary of companies with meaningful changes in benchmark positioning based on the latest financial updates.` |
| TC-035 | PM 公司清单英文 A-Z 排序 | 重大变化公司：Zeta, Accelerist, FreightTrain | 查看清单 | 显示顺序为 Accelerist, FreightTrain, Zeta |
| TC-036 | PM 公司清单中文首字母 A-Z 排序 | 重大变化公司：张三公司、阿尔法公司、贝塔公司 | 查看清单 | 排序为 阿尔法公司（A）、贝塔公司（B）、张三公司（Z） |
| TC-037 | PM 公司清单英文优先于中文 | 重大变化公司：贝塔公司、Zeta、阿尔法公司、Accelerist | 查看清单 | 顺序为 Accelerist → Zeta → 阿尔法公司 → 贝塔公司（英文全部在前） |
| TC-038 | PM 单家公司达阈值 | 仅 Accelerist 达阈值 | 查看清单 | 清单只含 Accelerist |

### 七、重大变化判定 - 百分位移动阈值

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-039 | 百分位恰好移动 5 点触发 | 上次基准 P58；本次 P63；差 = 5 | PM 流程判定 | 视为重大变化，公司列入清单 |
| TC-040 | 百分位移动 4 点不触发 | 上次 P58；本次 P62；差 = 4 | PM 流程判定 | 不视为重大变化；基准静默更新为 P62 |
| TC-041 | 百分位下降 5 点触发 | 上次 P70；本次 P65；差 = -5（绝对值 = 5） | PM 流程判定 | 视为重大变化 |
| TC-042 | 百分位下降 4 点不触发 | 上次 P70；本次 P66 | PM 流程判定 | 不视为重大变化；静默更新 |
| TC-043 | Internal Peers 百分位移动达阈值 | Internal Peers 百分位由 P58 → P63 | PM 流程判定 | 视为重大变化（覆盖 Internal Peers 来源） |
| TC-044 | KeyBanc 外部基准百分位移动达阈值 | KeyBanc 2026 百分位由 P55 → P70 | PM 流程判定 | 视为重大变化（覆盖外部基准来源） |
| TC-045 | High Alpha 基准百分位移动达阈值 | High Alpha 百分位由 P70 → P55 | PM 流程判定 | 视为重大变化 |
| TC-046 | Benchmarkit 基准百分位移动达阈值 | Benchmarkit.ai 百分位由 P40 → P50 | PM 流程判定 | 视为重大变化 |
| TC-047 | 百分位移动 0 点不触发 | 所有指标百分位完全未变 | PM 流程判定 | 不视为重大变化；静默更新（也视作基准一致） |

### 八、重大变化判定 - 分位数边界跨越

分位数边界规则：Q1: P0 ≤ n < P25；Q2: P25 ≤ n < P50；Q3: P50 ≤ n < P75；Q4: P75 ≤ n ≤ P100

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-048 | Q2→Q3 跨越（P49→P51）触发 | 上次 P49（Q2）；本次 P51（Q3） | PM 流程判定 | 视为重大变化（即使差值 = 2 也触发） |
| TC-049 | Q1→Q2 跨越边界（P24→P25）触发 | 上次 P24（Q1）；本次 P25（Q2） | PM 流程判定 | 视为重大变化（P25 属于 Q2） |
| TC-050 | Q3→Q4 跨越边界（P74→P75）触发 | 上次 P74（Q3）；本次 P75（Q4） | PM 流程判定 | 视为重大变化（P75 属于 Q4） |
| TC-051 | Q3→Q2 向下跨越触发 | 上次 P52（Q3）；本次 P48（Q2） | PM 流程判定 | 视为重大变化 |
| TC-052 | Q4 内移动不跨越（P74→P70）不触发 | 上次 P74（Q3）→ P70（Q3）；同 Q3，差 = 4 | PM 流程判定 | 不触发（不跨越且差 < 5）；静默更新 |
| TC-053 | Q4 内大幅度移动 P75→P100 不跨越但达阈值 | 上次 P75（Q4）；本次 P100（Q4）；差 = 25 | PM 流程判定 | 触发（虽未跨越边界，但 ≥ 5 点移动已达阈值） |
| TC-054 | Q4 边界 P75 临界值归属 | 上次 P74（Q3）；本次 P75 | PM 流程判定 | 视为 Q3→Q4 跨越并触发 |
| TC-055 | Q1 边界 P0 临界值归属 | 上次 P0（Q1）；本次 P4（Q1）；差 = 4 | PM 流程判定 | 不触发（同 Q1，差 < 5） |

### 九、指标板块 - Actuals 行展示

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-056 | Actuals 行默认含所有字段 | 公司某指标存在 Actual 值与全部基准百分位 | 查看邮件指标板块 | Actuals 行依次展示 `Actual: xx%`、`Internal Peers: ...`、`KeyBanc 2026: ...`、`High Alpha 2026: ...`、`Benchmarkit.ai 2026: ...` |
| TC-057 | Actuals 行真实值显示 | 指标 actual = 64% | 查看 | 显示 `Actual: 64%` |
| TC-058 | Internal Peers 百分位上升标记 | 本次 P63；上次 P58 | 查看 | 显示 `Internal Peers: P63 ↑ (moved up from P58)` |
| TC-059 | Internal Peers 百分位下降标记 | 本次 P55；上次 P70 | 查看 | 显示 `Internal Peers: P55 ↓ (moved down from P70)` |
| TC-060 | Internal Peers 百分位不变无标记 | 本次 P55；上次 P55 | 查看 | 显示 `Internal Peers: P55`，无 ↑↓ 符号，无移动描述 |
| TC-061 | KeyBanc 外部基准下降标记 | KeyBanc 本次 P55；上次 P70 | 查看 | 显示 `KeyBanc 2026: P55 ↓ (moved down from P70)` |
| TC-062 | High Alpha 基准不变无标记 | High Alpha 本次 P55；上次 P55 | 查看 | 显示 `High Alpha 2026: P55` |
| TC-063 | Benchmarkit 基准上升标记 | Benchmarkit.ai 本次 P50；上次 P45 | 查看 | 显示 `Benchmarkit.ai 2026: P50 ↑ (moved up from P45)` |
| TC-064 | CA 首封邮件 Actuals 无移动描述 | CA 首封邮件，无上次基准 | 查看所有指标 Actuals 行 | 各基准显示百分位值但不带 ↑↓ 与 "moved up/down from ..." 描述 |

### 十、指标板块 - 预测数据行展示

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-065 | 同时有 CF 与 SGF 优先展示 CF | ARR Growth Rate 同时有 Committed Forecast 与 System Generated Forecast | 查看指标板块 | 板块内 Actuals 行之后展示 `Committed Forecast` 行；不展示 SGF 行 |
| TC-066 | 仅有 SGF 展示 SGF 行 | 指标无 CF，但有 SGF | 查看指标板块 | 展示 `System Generated Forecast` 行 |
| TC-067 | 两种预测均无不显示预测行 | 指标仅有 Actuals，无任何 Forecast | 查看指标板块 | 板块只含 Actuals 行，不显示任何预测行 |
| TC-068 | CF 行字段齐全 | 指标 CF 值 64%，且有全部基准 | 查看 CF 行 | 依次展示 `Committed Forecast: 64%`、`Internal Peers: P58`、`KeyBanc 2026: P55`、`High Alpha 2026: P52`、`Benchmarkit.ai 2026: P55` |
| TC-069 | SGF 行字段齐全 | 指标 SGF 值 64%，无 CF，有全部基准 | 查看 SGF 行 | 依次展示 `System Generated Forecast: 64%` 与各基准百分位 |
| TC-070 | 6 个指标中仅部分有预测 | ARR/Gross Margin 有 CF；其余 4 指标无 CF/SGF | 查看邮件 | ARR/Gross Margin 板块含 CF 行；其余板块仅 Actuals 行 |

### 十一、PM 邮件 - 仅展示有重大变化的指标

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-071 | PM 邮件过滤未变化指标 | 公司 A 的 ARR Growth Rate 达阈值；其余 5 指标均未达阈值 | 查看 PM 邮件中公司 A 的板块 | 仅展示 ARR Growth Rate 指标板块；其余 5 指标不展示 |
| TC-072 | PM 邮件多指标达阈值全部展示 | Gross Margin、Rule of 40 达阈值；其余未达 | 查看公司 A 板块 | 按需求顺序展示 Gross Margin、Rule of 40 两个板块 |
| TC-073 | PM 首封邮件不过滤指标 | PM 首封邮件，某公司在清单中 | 查看该公司板块 | 展示全部 6 个指标板块（首封快照不过滤） |
| TC-074 | PM 邮件多公司指标不同 | 公司 A 仅 ARR 达阈值；公司 B 仅 Rule of 40 达阈值 | 查看 PM 邮件 | 公司 A 板块仅含 ARR；公司 B 板块仅含 Rule of 40 |

### 十二、百分位计算与基准更新

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-075 | Internal Peers 使用 Nearest Rank 法 | 公司某指标 actual = 64%；同行 10 家排序后第 7 位值恰好包含该公司 | 查看 Internal Peers 百分位 | 百分位按 Nearest Rank 法得出（例：位置 7/10 → P70） |
| TC-076 | 外部基准使用线性插值法 | KeyBanc 2026：P50=30%、P75=40%；公司值=35% | 查看 KeyBanc 百分位 | 显示 ~P62.5（计算：50+(75-50)×(35-30)/(40-30) = 62.5） |
| TC-077 | 百分位移动对比上一 closed month 基准 | 上一 closed month 2026-02 存储基准 P58；本 closed month 2026-03 实时百分位 P63 | 查看 Internal Peers | 显示 `P63 ↑ (moved up from P58)` |
| TC-078 | 邮件发出后基准更新 | 发送邮件时当前 Internal Peers 百分位为 P63 | 查看系统基准记录 | 该收件人对该公司该指标的基准记录更新为 P63 |
| TC-079 | 静默更新同样修改基准 | PM 端未发邮件但满足静默更新条件；当前 P60 | 检查系统记录 | PM 视图下基准更新为 P60（虽未发邮件） |
| TC-080 | CA 端基准独立记录 | 同一公司 CA 与 PM 的基准记录分别维护 | 检查记录 | CA 与 PM 的基准快照独立，不互相覆盖 |

---

## 需求追溯矩阵

| 需求编号 | 需求描述 | 覆盖状态 | 对应测试用例 | 备注 |
|---------|---------|---------|------------|------|
| R1  | 新 closed month 提交触发 | ✅ 已覆盖 | TC-001, TC-002 | |
| R2  | 25 号月度定期触发 | ✅ 已覆盖 | TC-003, TC-004, TC-005 | |
| R3  | closed month 定义规则 | ✅ 已覆盖 | TC-006~TC-014 | 含 Manual/Automatic + 15 号边界 + 回溯 |
| R4  | CA 每次触发收邮件，无静默更新 | ✅ 已覆盖 | TC-015, TC-017 | |
| R5  | PM 仅含重要变化公司，未达阈值静默更新 | ✅ 已覆盖 | TC-026, TC-027, TC-029, TC-030 | |
| R6  | 重大变化阈值 ≥ 5 点 | ✅ 已覆盖 | TC-039~TC-047 | 含 =5 与 =4 边界、上升/下降、各基准来源 |
| R7  | 分位数边界跨越 | ✅ 已覆盖 | TC-048~TC-055 | 含 P24/P25、P74/P75 边界与未跨越场景 |
| R8  | CA 邮件标题格式 | ✅ 已覆盖 | TC-020 | |
| R9  | CA 邮件问候语 | ✅ 已覆盖 | TC-021 | |
| R10 | CA 邮件情况简介 | ✅ 已覆盖 | TC-022 | |
| R11 | 首封邮件直接发送并记基准 | ✅ 已覆盖 | TC-016, TC-064 | |
| R12 | 下次变化幅度对比最近一次基准 | ✅ 已覆盖 | TC-018, TC-031 | 含静默更新后作为基准 |
| R13 | 邮件发出时记录新基准 | ✅ 已覆盖 | TC-078, TC-080 | |
| R14 | CA 邮件含全部 6 指标 | ✅ 已覆盖 | TC-023, TC-024 | |
| R15 | PM 邮件标题 | ✅ 已覆盖 | TC-032 | |
| R16 | PM 邮件问候语 | ✅ 已覆盖 | TC-033 | |
| R17 | PM 邮件情况简介 | ✅ 已覆盖 | TC-034 | |
| R18 | PM 公司清单排序（英先中后 A-Z） | ✅ 已覆盖 | TC-035, TC-036, TC-037, TC-038 | |
| R19 | PM 仅展示有重大变化的指标 | ✅ 已覆盖 | TC-071, TC-072, TC-074 | |
| R20 | PM 首封邮件不过滤 | ✅ 已覆盖 | TC-025, TC-073 | |
| R21 | PM 新 closed month 未达阈值静默更新 | ✅ 已覆盖 | TC-029 | |
| R22 | PM 数据修订未达阈值静默更新 | ✅ 已覆盖 | TC-030 | |
| R23 | 指标展示顺序 | ✅ 已覆盖 | TC-023, TC-024, TC-072 | |
| R24 | 每个指标必含 Actuals 行 | ✅ 已覆盖 | TC-056 | |
| R25 | Actuals 行字段齐全 | ✅ 已覆盖 | TC-056~TC-063 | |
| R26 | 百分位变化 ↑/↓/无 标记格式 | ✅ 已覆盖 | TC-058~TC-063 | 含上升、下降、不变 |
| R27 | 预测数据优先 CF，无则 SGF，两者无不显示 | ✅ 已覆盖 | TC-065~TC-067, TC-070 | |
| R28 | CF/SGF 行字段齐全 | ✅ 已覆盖 | TC-068, TC-069 | |
| R29 | Internal Peers 使用 Nearest Rank 法 | ✅ 已覆盖 | TC-075 | |
| R30 | 外部基准使用线性插值法 | ✅ 已覆盖 | TC-076 | 含具体计算验证 |
| R31 | 百分位移动对比上一 closed month | ✅ 已覆盖 | TC-077 | |

**覆盖率：100%**（31/31 需求全部已覆盖）
