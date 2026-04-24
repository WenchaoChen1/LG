# 测试用例：基准参考数据更新用户通知

- **需求来源**：`docs/Finance email+条幅+提醒/Notify Users When Benchmark Reference Data Is Updated_需求文档.md`
- **生成时间**：2026-04-23

---

## 需求清单

| #   | 需求类型 | 需求描述 |
|-----|----------|----------|
| R1  | 功能需求 | 外部基准流：在 Benchmark Entry 中同一平台添加新 Edition（如 KeyBanc 已有 2023/2024/2025，添加 2026）实时触发一次通知 |
| R2  | 功能需求 | 外部基准流：在 Benchmark Entry 中添加全新平台（非 KeyBanc/High Alpha/Benchmarkit）实时触发一次通知 |
| R3  | 业务规则 | 外部基准流：同时添加多个平台新 Edition 时，触发次数 = 满足条件的次数（如三平台都新增则触发 3 次） |
| R4  | 业务规则 | 外部基准流：触发机制为实时触发，无延时 |
| R5  | 功能需求 | 外部基准流：Admin portal 用户首次登录时在 portfolio benchmarking tab 显示横幅 |
| R6  | 功能需求 | 外部基准流：Company portal 所有用户首次登录时在 company benchmarking tab 显示横幅 |
| R7  | UI 需求  | 外部基准流横幅文案：`New benchmark data available. Benchmark comparisons now reflect the latest survey (platform — Edition).`，多平台版本以逗号间隔在同一横幅显示 |
| R8  | 功能需求 | 外部基准流横幅：用户可关闭横幅；不关闭则一直显示，再次登录仍显示 |
| R9  | 功能需求 | 外部基准流邮件：Portfolio manager 与 Company Admin 均收到通知邮件 |
| R10 | UI 需求  | 外部基准流邮件标题：`New Benchmark Survey Update` |
| R11 | UI 需求  | 外部基准流邮件正文：包含实际接收人姓名、公司/组合名、platform-Edition 占位符正确替换 |
| R12 | 功能需求 | 外部基准流邮件含 `View Benchmark` 超链接：未登录则跳登录页，已登录按角色跳 portfolio/company benchmarking tab |
| R13 | 业务规则 | 外部基准流：若 portfolio portal 人员不再有对应公司访问权限，横幅不显示 |
| R14 | 业务规则 | 外部基准流邮件发送：Portfolio manager 在一个组织下收一封，若管理多个 portfolio 则在邮件正文罗列 portfolio 名字 |
| R15 | 业务规则 | 外部基准流邮件发送：Company Admin 有几个公司收几封，每封正文带各公司的名字 |
| R16 | 业务规则 | 内部基准流触发条件：首次发送——有同行变化即发，不考虑阈值，记录当前百分位为新基准 |
| R17 | 业务规则 | 内部基准流触发条件：closed month 任意指标百分位计算方式由"平台基准↔同行基准"切换则触发，记录当前百分位为新基准 |
| R18 | 业务规则 | 内部基准流触发条件：closed month 指标值未变，但对比上封邮件 actual 对 internal peer 百分位变化≥10（由内部基准变化导致）则触发 |
| R19 | 业务规则 | 内部基准流触发条件：closed month 指标值变化且同行变化共同导致 actual 对 internal peer 百分位变化≥10 则触发 |
| R20 | 业务规则 | 内部基准流特殊情况：新 closed month 入库 → 静默更新基准至当前百分位，不发通知 |
| R21 | 业务规则 | 内部基准流特殊情况：已有 closed month 财务数据被修订但未触发邮件时 → 静默更新基准至重算后百分位，不发通知 |
| R22 | 数据需求 | 内部基准流监测指标：ARR Growth Rate、Gross Margin、Monthly Net Burn Rate、Monthly Runway、Rule of 40、Sales Efficiency Ratio |
| R23 | 数据需求 | closed month 定义：Manual 公司取 Financial Entry 最后一条有 Actuals 的月份；Automatic 公司按服务器时间 15 号界定，并回溯至有 Actuals 的月份 |
| R24 | 功能需求 | 内部基准流横幅：Admin portal 用户首次登录在 portfolio benchmarking tab 和 company benchmarking tab 分别显示横幅 |
| R25 | 业务规则 | 内部基准流横幅：Admin portal 两个 tab 的横幅独立显示与关闭，互不影响 |
| R26 | 功能需求 | 内部基准流横幅：Company Admin 首次登录在 company benchmarking tab 显示横幅 |
| R27 | UI 需求  | 内部基准流横幅文案：`Benchmark positioning updated. Your company's placement may have shifted due to changes in benchmark data, not your financial performance.` |
| R28 | 功能需求 | 内部基准流横幅：用户可关闭；不关闭则一直显示，再次登录仍显示 |
| R29 | 功能需求 | 内部基准流邮件：Portfolio manager、其他有该公司权限人员、Company Admin 均收到通知 |
| R30 | UI 需求  | 内部基准流邮件标题：`Update to Benchmark Positioning` |
| R31 | UI 需求  | 内部基准流邮件正文：人名正确替换为实际接收人 |
| R32 | 功能需求 | 内部基准流邮件含 `View Benchmark` 超链接：未登录则跳登录页，已登录按角色跳对应 benchmarking tab |
| R33 | 业务规则 | 内部基准流：若 portfolio portal 人员不再有对应公司访问权限，横幅不显示 |
| R34 | 业务规则 | 内部基准流监测频率：每月 25 号监测 |
| R35 | 数据需求 | 内部基准流监测数据类型：仅 Actuals 数据 |
| R36 | 业务规则 | 特殊公司：状态为 Exited、Shut down 的公司以及未绑定 portfolio 的公司不进行监测 |

---

## 测试用例

### 一、外部基准更新 - 触发条件

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-001 | 同平台新增一个 Edition 触发一次通知 | KeyBanc 平台已存在 2023/2024/2025 Editions | 管理员在 Benchmark Entry 为 KeyBanc 添加 2026 Edition 并保存 | 系统实时触发一次外部基准更新流程（邮件+横幅） |
| | | | 查看邮件发送日志 | 仅生成 1 批邮件任务，platform-Edition 字段为 `KeyBanc SaaS Survey — 2026` |
| TC-002 | 新增全新平台触发一次通知 | 当前平台为 KeyBanc、High Alpha、Benchmarkit 三个 | 管理员在 Benchmark Entry 添加新平台 `NewSurvey` 的 2026 Edition 并保存 | 实时触发一次外部基准更新流程 |
| | | | 查看横幅文案 | 括号内显示 `NewSurvey — 2026` |
| | | | 查看横幅文案 | 括号内以逗号分隔显示 `KeyBanc SaaS Survey — 2026, High Alpha — 2026, Benchmarkit — 2026` |
| TC-004 | 触发机制实时性 | 管理员已登录 Admin 端 Benchmark Entry 页面 | 管理员保存新 Edition 的同一分钟内，登录一个 Company Admin 账号查看 company benchmarking tab | 横幅立即可见，无明显延迟（<1 分钟） |
| TC-005 | 无触发条件不发送通知 | 平台仅修正已有 Edition 字段值，未新增 Edition 亦未新增平台 | 管理员保存修改 | 不发送邮件，不显示横幅 |

### 二、外部基准更新 - 横幅显示与关闭

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-006 | Admin portal 用户首次登录看到横幅 | 已触发外部基准更新通知；Admin portal 用户未查看过 | Admin portal 用户登录并进入 portfolio benchmarking tab | 页面顶部显示横幅 `New benchmark data available. Benchmark comparisons now reflect the latest survey (KeyBanc SaaS Survey — 2026). Your relative positioning may change as a result.` |
| TC-007 | Company portal 用户首次登录看到横幅 | 已触发外部基准更新通知；Company portal 普通用户未查看过 | Company portal 用户登录并进入 company benchmarking tab | 页面顶部显示相同文案的横幅 |
| TC-008 | 横幅多平台版本逗号分隔 | 一次触发携带 KeyBanc 2026、High Alpha 2026 两条更新 | 用户登录进入 benchmarking tab | 横幅括号内显示 `KeyBanc SaaS Survey — 2026, High Alpha — 2026` |
| TC-009 | 用户关闭横幅 | 横幅正在显示 | 用户点击横幅关闭按钮 | 横幅立即消失，当前页面不再显示 |
| TC-010 | 关闭后再次登录不再显示 | TC-009 操作已完成 | 用户退出并重新登录，进入相同 benchmarking tab | 该条通知的横幅不再出现 |
| TC-011 | 未关闭横幅多次登录仍显示 | 已触发外部基准通知；用户登录看到横幅但未关闭，直接退出 | 用户重新登录并进入 benchmarking tab | 横幅仍然显示 |
| TC-012 | 非 benchmarking tab 不显示横幅 | 已触发外部基准通知 | 用户登录后先访问非 benchmarking tab 的其他 tab | 页面不显示该横幅 |
| TC-013 | portfolio portal 人员失去访问权限后横幅不显示 | portfolio portal 用户 A 原先管理 Company X；触发外部基准通知后 A 被移除对 Company X 的访问权限 | A 登录系统进入 benchmarking tab | 针对 Company X 的横幅不显示 |

### 三、外部基准更新 - 邮件接收与内容

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-014 | Portfolio manager 收到邮件 | Portfolio manager Jacobo Vargas 管理组织 Org1 下的 Portfolio P1，P1 含 Company A | 管理员触发外部基准更新 | Jacobo Vargas 收到 1 封标题为 `New Benchmark Survey Update` 的邮件 |
| TC-015 | Company Admin 收到邮件 | Company Admin 管理 Company A | 同 TC-014 触发 | Company Admin 收到 1 封标题为 `New Benchmark Survey Update` 的邮件 |
| TC-016 | 邮件正文占位符替换 | 接收人 Jacobo Vargas，公司名 Acme Inc. | 查收邮件正文 | 正文首行为 `Hello Jacobo Vargas,`；正文中 `[CompanyName]/[PortfolioName]` 替换为 `Acme Inc.` 或对应 Portfolio 名 |
| TC-017 | 邮件正文 platform-Edition 替换 | 触发内容为 KeyBanc 2026 | 查收邮件正文 | 括号内显示 `KeyBanc SaaS Survey — 2026` |
| TC-018 | Portfolio manager 管理多 Portfolio 合并为一封 | Portfolio manager 在 Org1 下管理 P1、P2、P3 | 触发一次外部基准通知 | 该 Portfolio manager 仅在 Org1 下收 1 封邮件，正文罗列 `P1, P2, P3` |
| TC-019 | Portfolio manager 跨组织分别收邮件 | Portfolio manager 在 Org1、Org2 两个组织各有 Portfolio | 触发一次外部基准通知 | 该 Portfolio manager 共收到 2 封邮件，分别对应 Org1、Org2 |
| TC-020 | Company Admin 多公司分别收邮件 | Company Admin 同时管理 Company A、Company B | 触发一次外部基准通知 | 该 Company Admin 共收到 2 封邮件，每封正文中分别含 Company A、Company B 名称 |
| TC-021 | 多 platform-Edition 在邮件中逗号分隔 | 一次触发携带 KeyBanc 2026、High Alpha 2026 | 查收邮件正文 | 括号内显示 `KeyBanc SaaS Survey — 2026, High Alpha — 2026` |

### 四、外部基准更新 - 邮件 View Benchmark 链接跳转

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-022 | 未登录点击链接跳登录页 | 接收人当前未登录 Looking Glass | 接收人在邮件中点击 `View Benchmark` 超链接 | 浏览器打开 Looking Glass 登录页 |
| TC-023 | 登录后自动跳转原目标 | 接续 TC-022，接收人为 Portfolio manager | 在登录页输入凭据登录成功 | 登录后自动跳转 portfolio benchmarking tab 页面 |
| TC-024 | 已登录 Portfolio manager 跳 portfolio tab | Portfolio manager 已登录 Looking Glass | 点击邮件中 `View Benchmark` 链接 | 直接打开 portfolio benchmarking tab |
| TC-025 | 已登录 Company Admin 跳 company tab | Company Admin 已登录 Looking Glass | 点击邮件中 `View Benchmark` 链接 | 直接打开 company benchmarking tab |
| TC-026 | 失去访问权限时横幅异常处理 | Portfolio portal 人员 A 收到针对 Company X 的邮件后，被移除对 Company X 的访问权限 | A 点击邮件中 `View Benchmark` 链接并完成登录 | 落地页面对 Company X 的横幅不显示；系统不报错 |

### 五、内部基准变化 - 触发条件

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-027 | 首次发送：任何同行变化即触发 | 公司从未发送过内部基准邮件；closed month 的 ARR Growth Rate actual 对 internal peer 首次计算出百分位 P30 | 每月 25 号监测任务运行 | 触发邮件+横幅；系统记录 P30 为该指标新基准 |
| TC-028 | 百分位计算由平台基准切换为同行基准触发 | 上月该指标百分位由平台基准算出为 P40；本月该公司同行数量达成阈值，计算方式切换为同行基准 | 每月 25 号监测任务运行 | 触发邮件+横幅；记录当前同行百分位为新基准 |
| TC-029 | 百分位计算由同行基准切换为平台基准触发 | 上月该指标由同行基准算出 P60；本月同行减少，切回平台基准 | 每月 25 号监测任务运行 | 触发邮件+横幅；记录当前平台百分位为新基准 |
| TC-030 | 指标值不变、百分位变化恰好=10 触发 | 上次邮件记录基准为 ARR Growth Rate P20；本月该指标 actual 值与上月完全相同；但同行财务数据变化使 actual 对 internal peer 变为 P30；变化差 = 10 | 每月 25 号监测任务运行 | 触发邮件+横幅（临界值 =10 触发）；新基准记录为 P30 |
| TC-031 | 指标值不变、百分位变化 =9 不触发 | 上次邮件记录基准 P20；本月指标 actual 值不变；同行变化导致百分位变为 P29；差值 = 9 | 每月 25 号监测任务运行 | 不触发邮件/横幅；基准不更新 |
| TC-032 | 指标值与同行同时变化导致百分位变化≥10 触发 | 上次记录基准 Gross Margin P40；本月公司 Gross Margin actual 值变化且同行数据也变化，导致 actual 对 internal peer 变为 P55；差值 = 15 | 每月 25 号监测任务运行 | 触发邮件+横幅；新基准记录为 P55 |
| TC-033 | 指标值变化但同行未变不因此触发（由公司自身财务变化导致） | 上次记录基准 P40；本月公司 actual 变化但同行未变，新百分位 P52 | 每月 25 号监测任务运行 | 不触发该条邮件（该条规则仅针对同行也变化的情况） |
| TC-034 | 多指标同时满足触发条件合并为一封邮件 | 同一公司的 ARR Growth Rate、Gross Margin 两指标本月均满足触发条件 | 每月 25 号监测任务运行 | 该公司的 Portfolio manager 与 Company Admin 每人就该公司仅收到 1 封合并邮件 |

### 六、内部基准变化 - 特殊情况（静默更新）

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-035 | 新 closed month 入库静默更新 | 公司 closed month 从 2026-02 变为 2026-03；2026-03 是全新数据点 | 系统检测到新 closed month 入库 | 不发送邮件、不显示横幅；系统静默将基准更新为 2026-03 当前百分位 |
| TC-036 | 新 closed month 后下次监测不误判 | 接续 TC-035；下个 25 号到来时，2026-03 数据无新同行变化 | 每月 25 号监测任务运行 | 不触发通知（证明 TC-035 的静默更新生效，避免将新数据点误判为偏移） |
| TC-037 | 已有 closed month 数据被修订且未触发条件静默更新 | closed month 2026-03 的 Actuals 数据被修订，重算后百分位由 P40 变 P45；不满足任何触发条件 | 监测任务运行 | 不发送邮件、不显示横幅；系统静默将基准更新为 P45 |
| TC-038 | 已有 closed month 数据修订触发条件正常发送 | closed month 2026-03 数据被修订，重算后 actual 对 internal peer 百分位变化≥10 且满足触发规则 | 监测任务运行 | 正常发送邮件+横幅；不执行静默更新（基准随邮件记录更新） |

### 七、内部基准变化 - 横幅显示与关闭

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-039 | Admin portal 用户 portfolio tab 显示横幅 | 已触发内部基准变化通知；Admin portal 用户未查看过 | Admin portal 用户登录并进入 portfolio benchmarking tab | 顶部显示横幅 `Benchmark positioning updated. Your company's placement may have shifted due to changes in benchmark data, not your financial performance.` |
| TC-040 | Admin portal 用户 company tab 也显示横幅 | 同 TC-039 | 用户切换至 company benchmarking tab | 该 tab 顶部同样显示相同文案横幅 |
| TC-041 | Admin portal 两个 tab 横幅独立关闭 | Admin portal 用户在 portfolio 和 company 两个 tab 均能看到横幅 | 用户在 portfolio benchmarking tab 点击关闭横幅 | portfolio tab 横幅消失；切换至 company tab，该 tab 横幅仍显示 |
| TC-042 | 单独关闭 company tab 横幅 | 接续 TC-041；portfolio tab 横幅已关闭、company tab 横幅仍在 | 用户在 company tab 关闭横幅 | company tab 横幅消失；再切回 portfolio tab 保持已关闭状态 |
| TC-043 | Company Admin 仅在 company tab 看到横幅 | 已触发内部基准变化通知；Company Admin 未查看过 | Company Admin 登录进入 company benchmarking tab | 显示横幅 |
| TC-044 | Company Admin 不在 portfolio tab 看到横幅 | Company Admin 无 portfolio benchmarking tab 访问或该 tab 不应显示该横幅 | Company Admin 尝试访问 portfolio benchmarking tab | 不显示该内部基准横幅（符合角色权限） |
| TC-045 | 内部基准横幅未关闭多次登录仍显示 | 用户看到横幅后未关闭、直接退出 | 用户重新登录并进入对应 tab | 横幅仍显示 |
| TC-046 | 内部基准横幅关闭后不再显示 | 用户已关闭横幅 | 用户退出并重新登录进入该 tab | 横幅不再显示 |

### 八、内部基准变化 - 邮件接收与内容

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-047 | Portfolio manager 收到邮件 | Portfolio manager 管理 Portfolio P1，P1 含 Company A；A 触发内部基准变化 | 监测任务运行 | Portfolio manager 收到 1 封标题为 `Update to Benchmark Positioning` 的邮件 |
| TC-048 | 其他有该公司权限的人员收到邮件 | 用户 B 具有 Company A 的访问权限但不是 Portfolio manager | 监测任务运行 | B 收到同一标题的邮件 |
| TC-049 | Company Admin 收到邮件 | Company Admin 管理 Company A | 监测任务运行 | Company Admin 收到 1 封标题为 `Update to Benchmark Positioning` 的邮件 |
| TC-050 | 邮件正文人名占位符替换 | 接收人 Jacobo Vargas | 查收邮件正文 | 首行为 `Hello Jacobo Vargas,` |
| TC-051 | 邮件正文文案一致 | 任一接收人收到邮件 | 查收邮件正文 | 正文与需求定义一致：`You may notice a change in your company's benchmark positioning. This shift is due to updates in the benchmark reference data, which can affect how companies are ranked relative to one another. It reflects movement within the cohort, not changes in your company's financial performance.` |

### 九、内部基准变化 - 邮件 View Benchmark 链接跳转

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-052 | 未登录点击链接跳登录页 | 接收人当前未登录 | 点击邮件中 `View Benchmark` 超链接 | 浏览器打开登录页 |
| TC-053 | 登录后自动跳转原目标 | 接续 TC-052，接收人为 Portfolio manager | 登录成功 | 自动跳转 portfolio benchmarking tab |
| TC-054 | 已登录 Portfolio 角色跳 portfolio tab | Portfolio manager 已登录 | 点击链接 | 直接打开 portfolio benchmarking tab |
| TC-055 | 已登录 Company Admin 跳 company tab | Company Admin 已登录 | 点击链接 | 直接打开 company benchmarking tab |
| TC-056 | 失去访问权限时横幅不显示 | Portfolio portal 人员 A 失去对 Company X 的访问权限后点击链接 | A 登录后到达落地页 | 针对 Company X 的内部基准横幅不显示；页面不报错 |

### 十、监测频率、数据类型与指标覆盖

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-057 | 每月 25 号触发监测 | 系统服务器时间为 2026-04-25 00:00 | 观察监测任务调度 | 监测任务在当天按计划启动一次 |
| TC-058 | 非 25 号不触发常规监测 | 系统服务器时间为 2026-04-26 | 观察监测任务 | 不启动内部基准监测任务（不影响外部基准实时触发） |
| TC-059 | 仅 Actuals 数据参与监测 | closed month 同时存在 Actuals 与 Forecast 数据 | 监测任务运行 | 计算仅基于 Actuals，Forecast 数据不被引用 |
| TC-060 | 所有 6 个指标均参与监测 | 某公司 6 个指标均有 Actuals 数据 | 监测任务运行，分别构造 6 个指标满足触发条件的情况 | ARR Growth Rate、Gross Margin、Monthly Net Burn Rate、Monthly Runway、Rule of 40、Sales Efficiency Ratio 每个指标均能独立触发邮件 |
| TC-061 | 非监测指标不触发 | 除 6 指标外的其他指标百分位变化≥10 | 监测任务运行 | 不触发邮件或横幅 |

### 十一、特殊公司状态与绑定

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-062 | Exited 公司不参与监测 | Company A 状态 = Exited；满足内部基准变化触发条件 | 监测任务运行 | 不向 A 的任何相关人发送邮件；不显示横幅 |
| TC-063 | Shut down 公司不参与监测 | Company B 状态 = Shut down；满足触发条件 | 监测任务运行 | 不发送邮件，不显示横幅 |
| TC-064 | 未绑定 portfolio 的公司不参与监测 | Company C 未绑定任何 portfolio；满足触发条件 | 监测任务运行 | 不发送邮件，不显示横幅 |
| TC-065 | Active 公司且已绑定 portfolio 正常参与 | Company D 状态 = Active 且绑定 Portfolio P1；满足触发条件 | 监测任务运行 | 正常发送邮件与显示横幅 |
| TC-066 | 外部基准通知对 Exited 公司 | Company A 状态 = Exited | 管理员触发外部基准更新 | 针对 Company A 的横幅不显示；相关接收人邮件中不包含 Company A（与"特殊情况说明"逻辑一致） |

---

## 需求追溯矩阵

| 需求编号 | 需求描述 | 覆盖状态 | 对应测试用例 | 备注 |
|---------|---------|---------|------------|------|
| R1  | 同平台新增 Edition 触发 | ✅ 已覆盖 | TC-001 | |
| R2  | 新增全新平台触发 | ✅ 已覆盖 | TC-002 | |
| R3  | 多平台同时新增触发多次 | ✅ 已覆盖 | TC-003 | |
| R4  | 实时触发机制 | ✅ 已覆盖 | TC-004 | |
| R5  | Admin portal 横幅（外部基准） | ✅ 已覆盖 | TC-006 | |
| R6  | Company portal 横幅（外部基准） | ✅ 已覆盖 | TC-007 | |
| R7  | 外部基准横幅文案与多平台逗号分隔 | ✅ 已覆盖 | TC-006, TC-008 | |
| R8  | 外部基准横幅关闭与持久化 | ✅ 已覆盖 | TC-009, TC-010, TC-011 | |
| R9  | 外部基准邮件双角色接收 | ✅ 已覆盖 | TC-014, TC-015 | |
| R10 | 外部基准邮件标题 | ✅ 已覆盖 | TC-014 | |
| R11 | 外部基准邮件正文占位符 | ✅ 已覆盖 | TC-016, TC-017, TC-021 | |
| R12 | 外部基准邮件链接跳转 | ✅ 已覆盖 | TC-022~TC-025 | |
| R13 | 外部基准失去权限横幅不显示 | ✅ 已覆盖 | TC-013, TC-026 | |
| R14 | Portfolio manager 一组织一封、多 portfolio 罗列 | ✅ 已覆盖 | TC-018, TC-019 | |
| R15 | Company Admin 多公司多封 | ✅ 已覆盖 | TC-020 | |
| R16 | 首次发送无阈值 | ✅ 已覆盖 | TC-027 | |
| R17 | 基准计算方式切换触发 | ✅ 已覆盖 | TC-028, TC-029 | |
| R18 | 指标不变、百分位变化≥10 触发 | ✅ 已覆盖 | TC-030, TC-031 | 含 =10 与 =9 边界 |
| R19 | 指标值与同行均变化触发 | ✅ 已覆盖 | TC-032, TC-033 | |
| R20 | 新 closed month 静默更新 | ✅ 已覆盖 | TC-035, TC-036 | |
| R21 | 修订数据未触发时静默更新 | ✅ 已覆盖 | TC-037, TC-038 | |
| R22 | 6 指标覆盖 | ✅ 已覆盖 | TC-060, TC-061 | |
| R24 | Admin 双 tab 均显示横幅 | ✅ 已覆盖 | TC-039, TC-040 | |
| R25 | Admin 双 tab 横幅独立 | ✅ 已覆盖 | TC-041, TC-042 | |
| R26 | Company Admin 仅 company tab 横幅 | ✅ 已覆盖 | TC-043, TC-044 | |
| R27 | 内部基准横幅文案 | ✅ 已覆盖 | TC-039, TC-051 | |
| R28 | 内部基准横幅关闭与持久化 | ✅ 已覆盖 | TC-045, TC-046 | |
| R29 | 内部基准邮件接收人 | ✅ 已覆盖 | TC-047, TC-048, TC-049 | |
| R30 | 内部基准邮件标题 | ✅ 已覆盖 | TC-047, TC-049 | |
| R31 | 内部基准邮件正文人名 | ✅ 已覆盖 | TC-050 | |
| R32 | 内部基准邮件链接跳转 | ✅ 已覆盖 | TC-052~TC-055 | |
| R33 | 内部基准失去权限横幅不显示 | ✅ 已覆盖 | TC-056 | |
| R34 | 每月 25 号监测 | ✅ 已覆盖 | TC-057, TC-058 | |
| R35 | 仅 Actuals 数据监测 | ✅ 已覆盖 | TC-059 | |
| R36 | Exited/Shut down/未绑定 portfolio 公司不监测 | ✅ 已覆盖 | TC-062~TC-066 | |

**覆盖率：100%**（36/36 需求全部已覆盖）
