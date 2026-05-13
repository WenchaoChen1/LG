# 测试用例：Manual Uploads with OCR 需求文档

- **需求来源**：[Manual_Uploads_with_OCR_需求文档.md](https://github.com/WenchaoChen1/LG/blob/master/docs/智能解析/Manual_Uploads_with_OCR_需求文档.md)
- **生成时间**：2026-05-13

---

## 需求清单

按业务流程拆分为 7 个功能模块（对应需求文档第 2 节业务流程总览 ①~⑥ + 3.7 系统学习）。

### 模块一：① 文件上传（3.1）

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R1.1 | 功能需求 | 仅手动录入类型公司可见 Import Statement 上传按钮；自动对接公司aaa不显示 |
| R1.2 | 业务规则 | Company Admin / Company User 可上传本公司文档；Portfolio portal 角色可上传其有权限的全部公司文档 |
| R1.3 | UI 需求 | 上传按钮位置：Financial Entry / Committed Forecast 页面的 Import Statement 按钮，点击进入上传流程 |
| R1.4 | 功能需求 | 支持上传 PDF（扫描/数字）、Excel（.xlsx/.xls）、CSV、图片（JPG/JPEG/PNG/TIFF） |
| R1.5 | 功能需求 | 桌面端支持拖拽上传或点击选择；移动端使用文件选择器（不支持拖拽） |
| R1.6 | 功能需求 | 支持单文件与多文件批量上传 |
| R1.7 | 边界条件 | 单文件 ≤ 20MB；批量总大小 ≤ 100MB |
| R1.8 | 业务规则 | 文档类型和名字相同的文件判定为重复，仅保留一个，第二个不予上传 |
| R1.9 | UI 需求 | 上传错误提示包含 5 种文案：超 20MB、类型不支持、总大小超 100MB、重名、纯上传失败 |
| R1.10 | 业务规则 | 同类型错误不重复展示，仅罗列 File name；错误消息 5 秒自动消失或可点 X 关闭 |
| R1.11 | 业务规则 | 旧错误未消失时新文件触发同类型错误，将文件名追加并重置 5 秒倒计时 |
| R1.12 | 业务规则 | 不同类型错误独立弹出新错误框，各自独立计时 |
| R1.13 | 业务规则 | 二次上传时第二批与第一批合计超 100MB，第二批整批不予上传 |
| R1.14 | UI 需求 | 每个文件显示上传进度条；Next 按钮在全部上传完成前不可用 |
| R1.15 | 功能需求 | 上传过程中显示 Clear All 按钮，点击清空全部正在上传的文件 |
| R1.16 | 功能需求 | 上传完成后点击 Remove 按钮可移除文件 |
| R1.17 | 功能需求 | 点击上传按钮可继续添加文件 |
| R1.18 | 功能需求 | 点击 Next 进入数据提取；点击 Cancel 或右上 ✖ 关闭弹框回到 Financial Entry |

### 模块二：② 数据提取（3.2 / 3.2a / 3.2b）

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R2.1 | 业务规则 | 仅提取 table 中的数据 |
| R2.2 | 业务规则 | 每张表沿数据类型（Actuals/Proforma）与报表类型（P&L/Balance Sheet）两个维度独立分类 |
| R2.3 | 业务规则 | 预测数据识别信号：关键词 Forecast/Proforma/Projection/Budget/Plan、未来期列、历史+未来混合（任一即视为 Proforma），均不命中归为 Actuals |
| R2.4 | 业务规则 | 报表类型识别：P&L 关键词（P&L/Income/Profit）、Balance Sheet 关键词（Balance/Assets/Liabilities）、行标签模式、结构线索（A=L+E） |
| R2.5 | 业务规则 | 无法明确归类的表格 → 不抽取财务科目，在 3.4 提示；整文件未提取则归档至 Documentation |
| R2.6 | 业务规则 | 多页财务可能同时含多种数据类型与报表类型 |
| R2.7 | 业务规则 | 报告期识别优先级：列头/行标签 → 工作表名 → 表格标题/邻近文字 → 文件名（兜底） |
| R2.8 | 功能需求 | OCR 适用图片型 PDF、扫描 PDF、独立图片；支持多页，无可提取财务内容的页面跳过并记日志 |
| R2.9 | 业务规则 | OCR 容错：无边框、版面倾斜/旋转、格式不一致仍能提取表格 |
| R2.10 | 业务规则 | OCR 精确捕获无公式数值；正确解释负数、小数、百分数、货币符号；表头-数据行关联正确 |
| R2.11 | 业务规则 | Excel/CSV：扫描所有 Sheet；合并单元格/多表区/空行分隔仍能抽取；公式取计算值；保留币种/百分比/负数 |
| R2.12 | 业务规则 | Excel/CSV 启发式分类允许误判并标记待审核 |

### 模块三：③ AI 辅助账户映射（3.3）

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R3.1 | 业务规则 | AI 映射在数据提取完成后自动执行，无独立用户步骤 |
| R3.2 | 业务规则 | 每个被抽取的行项均生成一个建议 LG 科目 |
| R3.3 | 数据需求 | 支持 15 个 LG 标准科目（Revenue、COGS、S&M、R&D、G&A、三类 Payroll、Cash、AR、R&D Capitalized、Other Assets、AP、LT Debt、Other Liabilities） |
| R3.4 | 业务规则 | AI 以自然语义匹配为主，关键词为指南；考虑父子层级（如父 R&D 下 Wages → R&D Payroll） |
| R3.5 | 业务规则 | 推理失败标记 Unmapped，在 Side-by-Side 的 Unmapped Accounts 区域呈现 |
| R3.6 | 业务规则 | Revenue 特殊：标签含 refund/returns/contra 记为 Revenue Contra（负值），map 到 Gross Revenue |
| R3.7 | 业务规则 | COGS 关键词包含 cost of goods、materials、hosting、cloud、infrastructure 等 |
| R3.8 | 业务规则 | S&M Expenses 关键词覆盖 Marketing/Sales/Customer Cost/Events 等子类 |
| R3.9 | 业务规则 | R&D Expenses 关键词覆盖 research、development、engineering 等 |
| R3.10 | 业务规则 | G&A Expenses 关键词覆盖 Overhead/Facilities/Professional Services/Admin |
| R3.11 | 业务规则 | Payroll 类不确定时默认 G&A Payroll，并在源/LG 显示 alert 图标 |
| R3.12 | 业务规则 | Cash 关键词包含 cash、bank、checking、savings 等 |
| R3.13 | 业务规则 | Accounts Receivable 关键词包含 a/r、receivables、trade receivables 等 |
| R3.14 | 业务规则 | Capitalized R&D 需同时出现 资本化信号 + R&D/开发信号 或 摊销信号 |
| R3.15 | 业务规则 | Other Assets：被识别为资产但未映射到 Cash/AR/Capitalized R&D |
| R3.16 | 业务规则 | Accounts Payable 关键词包含 a/p、payables、trade payables |
| R3.17 | 业务规则 | Long Term Debt 关键词包含 loan、note payable、debt、convertible note 等 |
| R3.18 | 业务规则 | Other Liabilities：被识别为负债但未映射到 AP / LT Debt |
| R3.19 | 业务规则 | COGS/R&D 关键词重叠（cloud/hosting/AWS）默认归 COGS，源条目与 LG 指标旁显示警示图标 |
| R3.20 | 业务规则 | 同月内多个源账目映射到同一 LG 指标 + AI 判定语义重复 → 每条源行项与对应 LG 行显示告警图标；unmapped 移入 mapped 同样显示 |
| R3.21 | 业务规则 | 用户为 unmapped 缺名字段补名后，AI 不再解析该字段（即使后续 map 也不识别语义重复） |
| R3.22 | 业务规则 | Source Account 合并规则：跨 Table 同指标+同报表类型+同数据类型+无时间重叠+名称完全一致 → 合并 |
| R3.23 | 业务规则 | 映射持久化：建议 LG 科目、时间戳、来源（AI suggested/User Override）；用户覆盖后原 AI 建议保留为审计历史 |

### 模块四：④ Side-by-Side 审核与内联编辑（3.4）

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R4.1 | UI 需求 | 解析中显示 loading circle，左右屏均为灰色；替换/重新上传同样显示 |
| R4.2 | 功能需求 | 解析后若有失败文件，弹 File Processing Errors 弹窗列出文件名 |
| R4.3 | 功能需求 | File Processing Errors 按钮：Re-upload / Discard Problem Files / ✖ |
| R4.4 | 业务规则 | Re-upload 时第二批与第一批合计超 100MB 整批不上传 |
| R4.5 | 业务规则 | 部分文件失败时 Discard 或 ✖ 回到解析页；全部文件失败时回到 Financial Entry |
| R4.6 | UI 需求 | 左面板：文件选择下拉（默认 All Files）、Excel Sheet Tab、PDF 翻页、底部缩放控件 |
| R4.7 | 功能需求 | 左面板右上角支持新增/替换/删除已上传文件；选 All Files 时仅显示新增 |
| R4.8 | UI 需求 | 右面板显示 Actuals 与 Proforma 两个 Tab；默认显示规则按数据类型组合判断 |
| R4.9 | UI 需求 | 切换到无数据 Tab 显示空状态 No financial accounts found for this data type |
| R4.10 | 功能需求 | Unmapped accounts 区域位于 Actuals/Proforma Tab 上方，受 Tab 控制 |
| R4.11 | UI 需求 | 平台级 USD 显示开关不适用于该上传流程 |
| R4.12 | UI 需求 | 缺账目名 → UNIDENTIFIED 标签（可编辑名称，编辑后标签消失） |
| R4.13 | UI 需求 | 缺值 → NA；缺日期 → No Date |
| R4.14 | 功能需求 | 缺日期可从日历下拉选择开始月份；多数据按月份依次累加排列 |
| R4.15 | 业务规则 | 非连续月日期 + 缺日期字段：先排已知月份，缺日期数据从最后已知月份后动态增加列 |
| R4.16 | 业务规则 | 链式日期推算：紧邻左列 = 已知月份 − 1，紧邻右列 = +1，可链式传递 |
| R4.17 | 业务规则 | 无日期列前后均有已知日期 → 以左侧月份 +1 为准，忽略右侧推算结果 |
| R4.18 | 业务规则 | 缺名 + 缺日期 → 先显 UNIDENTIFIED；填名后切换显示 No Date |
| R4.19 | UI 需求 | 选日期后多出的月份列在其他项无数据时显 "-"，不算数据缺失 |
| R4.20 | 业务规则 | 用户为 UNIDENTIFIED 命名后不触发自动映射，仍须手动指派 LG 指标 |
| R4.21 | UI 需求 | 指派下拉每个指标都包含 Actuals 与 Forecast 两种选择，Forecast 显紫色，上方支持名称筛选 |
| R4.22 | UI 需求 | 第一个可指派 LG 指标账目名旁显示 Click to assign this item to an LG Metric 提示，做第一个 map 后消失 |
| R4.23 | 功能需求 | 内联编辑：数值删除后回填 0；编辑过的数值灰色背景显示 |
| R4.24 | 业务规则 | 数据不完整账户行（含 NA）无指派下拉；指标名、月份、数值全部完整才显示下拉 |
| R4.25 | 业务规则 | 指派后整行所有月份数据被指派到相应月份，非单元格颗粒度 |
| R4.26 | 业务规则 | 源账目名非空即锁定；为空可补充，保存后不可更改 |
| R4.27 | 功能需求 | 已 mapped 项可编辑数值、重新指派指标（Actuals/Forecast）、改回 unmapped |
| R4.28 | UI 需求 | 该批无任何可用数据时右面板提示 No mapped data 文案 |
| R4.29 | 功能需求 | No mapped 后点 Next 弹 Files Uploaded Successfully 弹框；文件提交至 Documentation/Imported Statements 文件夹 |
| R4.30 | UI 需求 | 只包含一种数据类型时另一 Tab 显示 No financial accounts found for this data type |
| R4.31 | 业务规则 | LG 指标下只有一个源账目时直接显示数值（可编辑） |
| R4.32 | 业务规则 | 多源账目可展开，指标名旁显数量；源账目数值可编辑，LG 指标值为合计且不可编辑 |
| R4.33 | 业务规则 | 合计因币种不一致或类型冲突无法计算 → 默认显 "-"，不写入 LG |
| R4.34 | UI 需求 | total 总计行项不进入匹配流程，仅提取最细颗粒度子项 |
| R4.35 | 业务规则 | 同月内同 LG 指标多源账目语义重复显告警图标 |
| R4.36 | 业务规则 | 用户可将源行项改映射到 LG 两种类型的任意指标 |
| R4.37 | UI 需求 | 非连续月数据有消息提示；右面板可左右滑动，首列固定 |
| R4.38 | 功能需求 | 左选文件 → 右面板同步；多文件时 All Files 展示合并数据 |
| R4.39 | 业务规则 | 左右 Actuals/Proforma Tab 切换不影响左面板 |
| R4.40 | UI 需求 | 左右面板比例可调（默认 50%），提供图标隐藏左面板 |
| R4.41 | 功能需求 | 用户可确认数据进入下一步；也可拒绝并重新/上传新文件 |
| R4.42 | 业务规则 | 确认后无 Unmapped → 直接进 Mapping Summary；有 Unmapped 弹确认窗显示两项统计 + 提示 |
| R4.43 | 功能需求 | Unmapped 确认窗按钮：Continue to Next Step / Go Back |
| R4.44 | 业务规则 | 不存在未匹配项时 unmapped 那行提示不显示 |
| R4.45 | 功能需求 | 右上角 Cancel 弹 Cancel Data Mapping? 确认窗（Cancel data mapping / Continue data mapping） |

### 模块五：⑤ 写入 LG Schema（3.5）

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R5.1 | 业务规则 | 仅 mapped section 中非 "-" 项进入写入流程 |
| R5.2 | UI 需求 | Verify Data 摘要页展示 Mapping Summary 文案、源文件总数、映射类型数、映射科目数 |
| R5.3 | UI 需求 | Verify Data 显示源文件列表（文件名/大小/已匹配源账目数） |
| R5.4 | 功能需求 | Verify Data 按钮：Previous Step / Start Verification；加载时 loading circle |
| R5.5 | 业务规则 | 冲突检测按公司+LG 指标+报告期（月+年）维度，按目标月份的存储币种比对 |
| R5.6 | 业务规则 | 仅目标月份有值且不同于映射合计才视为冲突 |
| R5.7 | 业务规则 | 冲突页只显 Actuals；Proforma 直接生成新 committed forecast 版本（Source=Import Statements，User=上传人） |
| R5.8 | 业务规则 | 上传人后期被删除时系统保留留痕，不影响字段显示 |
| R5.9 | UI 需求 | 冲突页与 Financial Entry 同格式；冲突单元格字体红色 |
| R5.10 | 业务规则 | 上传与 LG 货币不同 → 统一转换为 LG 货币对比；选择上传值时保存原始货币和值 |
| R5.11 | UI 需求 | 冲突弹框内容：指标-Month Year、Radio（默认 MAPPED VALUE / LG VALUE）、必填 Notes、✖ 仅可关闭、Next/Save |
| R5.12 | 业务规则 | Notes 未填点 Next 报错 A note is required before continuing. |
| R5.13 | 业务规则 | 冲突弹框全部填完 Next 才激活；解决后变绿色自动打开下一个，跳转顺序：同指标左→右，指标内完成跳下一指标 |
| R5.14 | UI 需求 | 最后一个冲突弹框按钮为 Save |
| R5.15 | 功能需求 | 冲突页可点 Previous Step 或右上 Previous 回到 Verify Data 摘要页 |
| R5.16 | 业务规则 | 仅 Proforma 批次：直接提交不走冲突，Mapping Summary 按钮为 Confirm and write to LG |
| R5.17 | 业务规则 | Mapped Value 选择：新数据替换当前版本，原值保留为历史 |
| R5.18 | 业务规则 | LG Value 选择：LG 数据不变，跳过该指标，继续后续 |
| R5.19 | 业务规则 | LG 为空 → 自动写入；LG 已有数据与当前一致 → 不触发新写入 |
| R5.20 | 业务规则 | 无任何冲突 → 跳过该步骤，直接到提交成功页 |
| R5.21 | 功能需求 | 写入按钮：Confirm & Submit to LG，提交后跳 Benchmarking 页并弹成功窗 |
| R5.22 | UI 需求 | 提交成功弹窗文案与 Close 按钮 |
| R5.23 | 业务规则 | 上下步切换数据保留；冲突页返回 mapping 修改后回 Summary 显提示，再次 verification 重检受影响数据 |
| R5.24 | 业务规则 | Schema 校验失败：终止写入、显错误、回相关步骤高亮 |
| R5.25 | 业务规则 | 不允许部分写入：整体成功或整体失败 |
| R5.26 | 业务规则 | 写入审计：时间戳、用户、源文档、报告期、文档类型、动作（written/overwritten/skipped）；被覆盖数据保留历史 |
| R5.27 | 业务规则 | 已写入数据立即反映至 Financial Entry / Committed Forecast / normalization / benchmarking |
| R5.28 | 业务规则 | 上传源文档不论是否抽取出科目都出现在 Company Documents 的 Imported Statements 文件夹 |
| R5.29 | 业务规则 | 新 closed month 触发的邮件通知须正常运行 |

### 模块六：⑥ 数据校验期备注字段（3.6）

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R6.1 | 功能需求 | 冲突解决步骤每个冲突值旁有必填备注（free-form，上限 2000 字符，超出不能继续输入） |
| R6.2 | 业务规则 | 不论选何方案，备注字段均可用 |
| R6.3 | UI 需求 | Note 页面无数据显 No Data |
| R6.4 | 功能需求 | Financial Entry 与 Committed Forecast 页面有 Note 按钮，进入 Data Mapping Notes 列表页 |
| R6.5 | UI 需求 | Note 列表字段：Data Mapping Time Stamp（UTC）、Metric、Financial Month、LG Value、Mapped Value、Data Source、Note Content |
| R6.6 | 功能需求 | Note 列表有 Select Metric 下拉 + 月历筛选，两者均含 search bar |
| R6.7 | UI 需求 | 超长备注截断显示（最多两行），See More 弹窗查看，仅 X/Close 关闭，长内容竖向滚动 |
| R6.8 | UI 需求 | 分页：总数与范围、页码直选、上下箭头、省略号跳转、每页行数（10/20，默认 10） |
| R6.9 | UI 需求 | 面包屑 Financial Entry > Data Mapping Notes 可返回 |
| R6.10 | 业务规则 | 上传最终确认后备注为只读；备注与上传事件关联用于审计 |

### 模块七：⑦ 系统学习与持续改进（3.7）

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R7.1 | 业务规则 | Side-by-Side Review 所有决策（approve/override/manual mapping）记录为 AI 训练信号 |
| R7.2 | 业务规则 | 公司级学习：实时更新 Company Mapping History；立即影响后续映射建议 |
| R7.3 | 业务规则 | 核心引擎级学习：全局更新通用规则与关键词集合 |
| R7.4 | 业务规则 | 新文档识别：基于历史学习给出映射建议 |
| R7.5 | 业务规则 | 向后兼容：AI 模型更新不得使既有映射失效或对已处理文档引入错误 |
| R7.6 | 业务规则 | 审计版本：Core Engine Version + Company Mapping History ID 写入每条映射结果 |
| R7.7 | 业务规则 | 本次记住内容不作用于当次；流程中退出（如冲突解决时）不保存学习内容 |

---

## 测试用例

### 一、文件上传：入口与权限

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-001 | 手动录入公司可见 Import Statement | Company Admin 登录 manual entry 公司 | 我导航到 Financial Entry 页面 | 页面显示 Import Statement 按钮 |
| | | | 我导航到 Committed Forecast 页面 | 页面显示 Import Statement 按钮 |
| TC-002 | 自动对接公司不显示入口 | 当前公司为 automatic 类型 | 我导航到 Financial Entry | 不显示 Import Statement 按钮 |
| | | | 我导航到 Committed Forecast | 不显示 Import Statement 按钮 |
| TC-003 | Company Admin 上传权限 | Company Admin 登录 | 我点击 Import Statement | 上传弹框打开，可上传本公司文档 |
| TC-004 | Company User 上传权限 | Company User 登录 | 我点击 Import Statement | 上传弹框打开，可上传本公司文档 |
| TC-005 | Portfolio portal 多公司上传 | Portfolio portal 角色登录，有 3 家公司权限 | 我进入公司 A 的 Financial Entry | 可上传 A 的文档 |
| | | | 我切换到公司 B 的 Financial Entry | 可上传 B 的文档 |
| TC-006 | 点击 Import Statement 进入上传流程 | 在 Financial Entry 页 | 我点击 Import Statement | 进入上传弹框 |

### 二、文件上传：上传方式与队列

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-007 | 桌面端拖拽上传 | 桌面端上传弹框 | 我拖拽一个 5MB PDF 到上传区域 | 文件开始上传，显示进度条 |
| TC-008 | 桌面端点击选择文件 | 同上 | 我点击上传按钮 | 打开本地文件选择器 |
| | | | 我选择一个 2MB Excel 文件 | 文件开始上传 |
| TC-009 | 移动端文件选择器 | 移动端上传弹框 | 我尝试拖拽文件 | 不响应拖拽 |
| | | | 我点击上传按钮 | 打开移动端文件选择器 |
| TC-010 | 多文件批量上传 | 上传弹框 | 我一次选择 3 个文件（合计 30MB） | 3 个文件进入队列，各自显示进度条 |
| TC-011 | 继续添加文件 | 已上传 2 个文件完成 | 我点击上传按钮 | 打开文件选择器 |
| | | | 我选择第 3 个文件 | 第 3 个加入队列开始上传 |
| TC-012 | 进度条与 Next 禁用 | 3 个文件上传中 | 我观察 Next 按钮 | Next 禁用 |
| | | | 全部上传完成 | Next 变为可用 |
| TC-013 | Clear All 清空队列 | 3 个文件上传中（进度 60%） | 我点击 Clear All | 全部上传中文件被移除，队列清空 |
| TC-014 | Remove 移除单个文件 | 文件 A、B 上传完成 | 我点击 A 旁的 Remove | A 被移除，B 保留 |
| TC-015 | 上传中无 Remove | 文件 A 上传进度 50% | 我查看 A | 仅显示进度条，无 Remove 按钮 |
| TC-016 | Cancel 退出上传弹框 | 上传弹框已上传 1 个文件 | 我点击 Cancel | 关闭弹框，回到 Financial Entry |
| TC-017 | ✖ 退出上传弹框 | 同上 | 我点击右上角 ✖ | 关闭弹框，回到 Financial Entry |
| TC-018 | Next 进入数据提取 | 全部文件上传完成 | 我点击 Next | 进入 Side-by-Side 审核页 |

### 三、文件上传：格式与大小校验

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-019 | 支持的 PDF（数字版） | 上传弹框 | 我上传 invoice.pdf（数字版） | 上传成功 |
| TC-020 | 支持的 PDF（扫描版） | 同上 | 我上传 scanned.pdf | 上传成功 |
| TC-021 | 支持的 Excel | 同上 | 我先后上传 .xlsx 和 .xls | 均上传成功 |
| TC-022 | 支持的 CSV | 同上 | 我上传 data.csv | 上传成功 |
| TC-023 | 支持的图片 | 同上 | 我先后上传 .jpg/.jpeg/.png/.tiff | 全部上传成功 |
| TC-024 | 不支持的类型 | 同上 | 我上传 doc.docx | 显示 Failed to Upload doc.docx. File type is not supported |
| TC-025 | 单文件超 20MB | 同上 | 我上传 25MB PDF | 显示 Failed to Upload {File name}. File exceeds the 20MB limit |
| TC-026 | 单文件 = 20MB 边界 | 同上 | 我上传恰好 20MB PDF | 上传成功（含等于） |
| TC-027 | 批量超 100MB | 同上 | 一次选 5 个文件合计 110MB | 显示 The combined size of your files exceeds the 100MB limit |
| TC-028 | 二次上传累计超 100MB | 已上传 80MB | 再上传一批 30MB | 第二批整批不上传 |
| TC-029 | 同类型同名重复 | 已上传 invoice.pdf | 再上传 invoice.pdf | 显示 A file with this name already exists.；仅保留第一个 |
| TC-030 | 同名不同类型不算重复 | 已上传 data.csv | 上传 data.pdf | data.pdf 上传成功 |
| TC-031 | 纯上传失败提示 | 网络异常 | 上传中断 | 显示 Failed to Upload {File name}.（无解释） |

### 四、文件上传：错误提示动态行为

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-032 | 同类错误追加文件名 + 倒计时重置 | a.pdf 触发超 20MB 错误（显示中） | 5 秒内再上传超 20MB 的 b.pdf | 错误框追加 b.pdf，倒计时重置 5 秒 |
| TC-033 | 5 秒自动消失 | 错误提示展示 | 我等待 5 秒不操作 | 错误自动消失 |
| TC-034 | 点击 X 关闭 | 错误提示展示 | 我点击 X | 错误立即关闭 |
| TC-035 | 不同类型错误并列独立 | 超限错误展示中 | 我上传不支持类型的文件 | 弹独立"类型不支持"错误框，并列存在，独立计时 |
| TC-036 | 同次多个同类不重复 | 一次上传 3 个文件均超 20MB | 我提交 | 错误框列 3 个文件名，不重复文案 |

### 五、数据提取：表格分类与报告期

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-037 | 仅提取 table 数据 | 上传含文本段落+表格的 PDF | 系统提取完成 | 仅表格数据进入提取结果，文本段落忽略 |
| TC-038 | Proforma：关键词命中 | 表格含 "Forecast 2027" 标题 | 系统分类 | 识别为 Proforma |
| TC-039 | Proforma：未来期列 | 列头全为 2027-01 ~ 2027-12（上传日 2026-05-13） | 系统分类 | 识别为 Proforma |
| TC-040 | Proforma：混合期 | 列头含 2025-01 ~ 2027-06 | 系统分类 | 识别为 Proforma（滚动预测） |
| TC-041 | Actuals 默认归类 | 表格无 Forecast 关键词，全历史期 | 系统分类 | 识别为 Actuals |
| TC-042 | P&L 识别 | 表格含 Income Statement + Revenue/COGS | 系统分类 | 识别为 P&L |
| TC-043 | Balance Sheet 识别 | 表格含 Balance Sheet + Assets/Liabilities/Equity 且 A=L+E | 系统分类 | 识别为 Balance Sheet |
| TC-044 | 双维度独立分类 | 一份 PDF 含 P&L Actual + Balance Sheet Proforma | 系统分类 | 两表分别标记，互不干扰 |
| TC-045 | 多页多类型 | 一份多页 PDF 含 4 张表（Actual P&L、Proforma P&L、Actual BS、Proforma BS） | 系统分类 | 4 张表各自分类，均能提取 |
| TC-046 | 无法归类表不抽取 | 表格未命中规则 | 系统处理 | 不抽取该表科目；进入映射页提示 |
| TC-047 | 整文件无可抽取 | 全部表无法归类 | 进入 Side-by-Side | 右面板显 No mapped data |
| TC-048 | 报告期优先级 1：列头 | 列头 "Jan 2025" | 系统识别 | 报告期取列头 |
| TC-049 | 报告期优先级 2：Sheet 名 | 列头无日期；Sheet 名 "FY2025" | 系统识别 | 报告期取 Sheet 名 |
| TC-050 | 报告期优先级 3：标题/邻近 | 列头与 Sheet 均无日期；表格上方 "2024 Annual" | 系统识别 | 报告期取标题 |
| TC-051 | 报告期优先级 4：文件名兜底 | 表格内外均无日期；文件名 "report_2024Q4.pdf" | 系统识别 | 报告期取文件名 |

### 六、数据提取：OCR

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-052 | 多页扫描 PDF | 上传 10 页扫描 PDF（5 页含表） | 系统提取 | 5 页表格提取，5 页非财务页跳过并记日志 |
| TC-053 | 无边框表格 | 扫描 PDF 表格无可见边框 | 系统提取 | 仍能识别行列 |
| TC-054 | 倾斜表格 | 扫描 PDF 表格倾斜 5° | 系统提取 | 仍能识别，数据完整 |
| TC-055 | 负数/百分数/货币 | 表格含 -100、(200)、25%、$1,500 | 系统提取 | 各格式正确解释 |
| TC-056 | 表头-数据行关联 | 含双层表头与子表头的扫描 PDF | 系统提取 | 子表头与对应数据行正确关联 |

### 七、数据提取：Excel / CSV

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-057 | 多 Sheet 扫描 | xlsx 含 5 Sheet | 系统提取 | 5 个 Sheet 都被扫描 |
| TC-058 | 合并单元格表头 | xlsx 表头使用合并单元格 | 系统提取 | 表格抽取，合并单元格归位正确 |
| TC-059 | 多表区与空行 | 一 Sheet 含 2 表区，空行分隔 | 系统提取 | 两表区独立抽取 |
| TC-060 | 公式取计算值 | 单元格 =SUM(A1:A5) 结果 1500 | 系统提取 | 抽取值为 1500（非公式串） |
| TC-061 | 保留币种百分比负数 | 单元格 €1,200、-5%、-300 | 系统提取 | 各格式原样保留 |
| TC-062 | 启发式分类标记待审核 | 模糊 Sheet 名+部分行标签 | 系统分类 | 可允许误判，前端可见待审核标记 |

### 八、AI 映射：基础规则

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-063 | 映射自动执行 | 数据提取完成 | 我观察 | 无需手动操作即生成建议 LG 科目 |
| TC-064 | Gross Revenue 关键词 | 源账目 "Sales Revenue" | 系统映射 | 建议 Gross Revenue |
| TC-065 | Revenue Contra 特殊 | 源账目 "Sales Refunds" 含 refund，值 -500 | 系统映射 | 映射为 Gross Revenue（Revenue Contra），值显示为负 |
| TC-066 | COGS 关键词 | 源账目 "Cost of Goods Sold" | 系统映射 | 建议 COGS |
| TC-067 | S&M Marketing | 源账目 "Digital Marketing" | 系统映射 | 建议 Sales & Marketing Expenses |
| TC-068 | S&M Sales 子类 | 源账目 "Sales Commission" | 系统映射 | 建议 Sales & Marketing Expenses |
| TC-069 | R&D Expenses | 源账目 "Software Development" | 系统映射 | 建议 R&D Expenses |
| TC-070 | R&D Payroll 父子层级 | 父 R&D 下子项 Wages | 系统映射 | 建议 R&D Payroll（不是 G&A Payroll） |
| TC-071 | G&A Facilities | 源账目 "Office Rent" | 系统映射 | 建议 G&A Expenses |
| TC-072 | G&A Professional Services | 源账目 "Legal Fees" | 系统映射 | 建议 G&A Expenses |
| TC-073 | Payroll 不确定默认 G&A + alert | 源账目 "Compensation" 无父子线索 | 系统映射 | 默认 G&A Payroll，源/LG 均显 alert 图标 |
| TC-074 | Cash 关键词 | 源账目 "Bank Checking" | 系统映射 | 建议 Cash |
| TC-075 | Accounts Receivable | 源账目 "Trade Receivables" | 系统映射 | 建议 Accounts Receivable |
| TC-076 | Capitalized R&D 双信号命中 | "Capitalized Software Development" 含 capitalized + software development | 系统映射 | 建议 R&D Capitalized |
| TC-077 | Capitalized R&D 单信号不命中 | "Software Development"（无资本化信号） | 系统映射 | 不映射为 R&D Capitalized，按 R&D Expenses 处理 |
| TC-078 | Other Assets 兜底 | 资产类不在 Cash/AR/Capitalized R&D 关键词 | 系统映射 | 建议 Other Assets |
| TC-079 | Accounts Payable | 源账目 "Trade Payables" | 系统映射 | 建议 Accounts Payable |
| TC-080 | Long Term Debt | 源账目 "Convertible Note" | 系统映射 | 建议 Long Term Debt |
| TC-081 | Other Liabilities 兜底 | 负债类不在 AP/LT Debt 关键词 | 系统映射 | 建议 Other Liabilities |
| TC-082 | 推理失败 Unmapped | 源账目语义不明（如 "Misc XYZ"） | 系统映射 | 标记 Unmapped，进入 Unmapped Accounts 区域 |

### 九、AI 映射：特殊场景

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-083 | COGS/R&D 重叠默认 COGS | 源账目 "AWS Hosting" | 系统映射 | 默认 COGS，源与 LG 旁警示图标 |
| TC-084 | 语义重复警示 | 同月 "desk and chair expenses" 与 "office furniture expenses" 均映射到 G&A Expenses | 系统检测 | 两条源行项与 G&A Expenses 行均显警示图标 |
| TC-085 | unmapped 改 mapped 后语义重复警示 | 一条 unmapped 手动 map 到 G&A Expenses，与已有 office supplies 同义 | 系统检测 | 源行项与 LG 行显警示图标 |
| TC-086 | 补名后不再触发语义检测 | unmapped 缺名项被用户补名后 map | 系统检测 | 不识别与他项语义重复，不显警示 |

### 十、AI 映射：Source Account 合并规则

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-087 | 合并成功 | Table A：Gross Revenue/P&L/Actual/2024-01~06；Table B：Gross Revenue/P&L/Actual/2024-07~12，名称一致 | 系统处理 | 两表 source 合并为一条 |
| TC-088 | 时间重叠不合并 | Table A：2024-01~06；Table B：2024-04~09 | 系统处理 | 不合并 |
| TC-089 | 数据类型不同不合并 | Actual vs Proforma 同指标无重叠 | 系统处理 | 不合并 |
| TC-090 | 同 Table 内不合并 | 同 Table 内 Col1 Actual 2024-01；Col2 Actual 2024-02 | 系统处理 | 不合并 |
| TC-091 | 名称不一致不合并 | Total Gross Revenue vs Gross Revenue | 系统处理 | 不合并 |

### 十一、Side-by-Side：解析状态与错误弹窗

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-092 | 解析中 loading + 灰屏 | 文件已提交解析中 | 我查看 Side-by-Side | 左面板 loading circle，左右屏灰色 |
| TC-093 | 替换文件后再次 loading | 解析完成后替换一文件 | 我观察 | 重新解析，loading 再次出现 |
| TC-094 | 部分文件失败弹 File Processing Errors | 5 个文件 2 个失败 | 解析完成 | 弹窗列出 2 个失败文件名 |
| TC-095 | 全部失败弹窗 | 3 个文件全部失败 | 解析完成 | 弹窗列出 3 个文件 |
| TC-096 | Re-upload 操作 | 弹窗显示 | 我点 Re-upload | 关闭弹窗，打开文件选择器，可选新文件上传 |
| TC-097 | Re-upload 累计超 100MB | 已 80MB，Re-upload 再选 30MB | 我提交 | 第二批整批不上传，显 100MB 错误 |
| TC-098 | Discard Problem Files：部分失败 | 5 文件 2 个失败的弹窗 | 我点 Discard Problem Files | 关闭弹窗，回到解析页面（保留 3 个成功文件） |
| TC-099 | Discard Problem Files：全部失败 | 3 文件全部失败的弹窗 | 我点 Discard Problem Files | 关闭弹窗，回到 Financial Entry |
| TC-100 | ✖ 关闭：部分失败 | 5 文件 2 个失败的弹窗 | 我点 ✖ | 关闭弹窗，回到解析页面 |
| TC-101 | ✖ 关闭：全部失败 | 3 文件全部失败的弹窗 | 我点 ✖ | 关闭弹窗，回到 Financial Entry |

### 十二、Side-by-Side：左面板

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-102 | 默认 All Files | 多文件已解析 | 进入 Side-by-Side | 下拉默认 All Files，左面板显文件列表 |
| TC-103 | 切换单文件 | 多文件状态 | 我从下拉选文件 A | 左面板切换至 A 内容 |
| TC-104 | Excel Sheet Tab | 选中 xlsx 含 3 Sheet | 我查看下拉下方 | 显示 3 个 Sheet Tab |
| | | | 我切换 Sheet 2 | 切换至 Sheet 2 内容 |
| TC-105 | PDF 翻页 | 选中多页 PDF | 我查看翻页控件 | 控件可见 |
| | | | 我点击下一页 | 翻到下一页 |
| TC-106 | 缩放控制 | 选中 PDF | 我查看底部 | 显示缩放控制条 |
| | | | 我拖动缩放 | PDF 按比例缩放 |
| TC-107 | 文件管理操作 | 已上传文件列表 | 我查看右上角 | 显示新增/替换/删除选项 |
| TC-108 | All Files 时仅显新增 | 下拉为 All Files | 我查看右上角 | 仅显新增选项 |

### 十三、Side-by-Side：右面板 Tab 与 Unmapped

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-109 | 仅 Actuals 数据默认 Actuals | 文件仅含 Actuals | 我查看右面板 | 默认 Actuals Tab |
| TC-110 | 仅 Proforma 默认 Proforma | 文件仅含 Proforma | 我查看右面板 | 默认 Proforma Tab |
| TC-111 | 同时包含默认 Actuals | 文件含 Actuals+Proforma | 我查看右面板 | 默认 Actuals Tab |
| TC-112 | 切到无数据 Tab 空状态 | 仅 Actuals 数据 | 我切到 Proforma Tab | 显 No financial accounts found for this data type |
| TC-113 | 水平/垂直滚动 + 首列固定 | 列数超出可视宽度 | 我滚动右面板 | 支持双向滚动，首列固定 |
| TC-114 | 非连续月消息提示 | 提取列为 2025-01/03/05 | 我查看右面板 | 显示非连续月消息提示 |
| TC-115 | USD 开关不适用 | 我在 Side-by-Side 页 | 我观察平台级 USD 显示开关 | 不显示或不可操作（不适用该流程） |
| TC-116 | Unmapped 位置 + Tab 控制 | Unmapped 含 Actuals 和 Proforma 项 | 我切换 Actuals Tab | Unmapped 区位于 Tab 上方，只显 Actuals 类型项 |
| | | | 我切换 Proforma Tab | Unmapped 只显 Proforma 类型项 |

### 十四、Side-by-Side：缺数据显示与日期推算

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-117 | 缺账目名显 UNIDENTIFIED | 某行账目名空 | 我查看 Unmapped 区 | 显 UNIDENTIFIED 标签 |
| TC-118 | 补名后 UNIDENTIFIED 消失 | 显 UNIDENTIFIED | 我编辑输入 "Misc Revenue" 保存 | 标签消失，显输入名 |
| TC-119 | 缺值显 NA | 某单元格无值 | 我查看 | 显 NA |
| TC-120 | 缺日期显 No Date | 某行日期缺 | 我查看 | 列头显 No Date |
| TC-121 | 缺名+缺日期初始 | 某行无名无日期 | 我查看 | 显 UNIDENTIFIED |
| | | | 我填账目名 | 切换为 No Date |
| TC-122 | 源账目名空可补充并锁定 | 源账目名为空 | 我编辑保存 "AR Misc" | 保存成功 |
| | | | 我再次尝试编辑 | 锁定不可改 |
| TC-123 | 源账目名非空锁定 | 已有名 "Revenue" | 我尝试编辑 | 不可编辑 |
| TC-124 | 选日期后多数据按月累加 | 某 account 8 个数据缺日期 | 我选起始月 2025-01 | 8 个数据依次落到 2025-01 ~ 2025-08 |
| TC-125 | 非连续月+缺日期排列 | 已知列 2025-02/05/08，缺日期 account 8 个数据 | 系统排列 | 第 1 个落 2 月，第 2/3 落 5/8 月；剩余从 2025-09 起动态增加列 |
| TC-126 | 链式推算：左邻 -1 | 已知 2025-06，左侧紧邻无日期 | 系统推算 | 左邻为 2025-05 |
| TC-127 | 链式推算：右邻 +1 | 已知 2025-06，右侧紧邻无日期 | 系统推算 | 右邻为 2025-07 |
| TC-128 | 链式传递多列 | 已知 2025-06，其左侧连续 3 列无日期 | 系统推算 | 依次 2025-05、2025-04、2025-03 |
| TC-129 | 左右冲突以左为主 | 列 X 无日期，左邻 2025-06、右邻 2025-09 | 系统推算 | X = 2025-07（左+1），忽略右-1 的 2025-08 |
| TC-130 | 选日期后多出月份其他项显 "-" | 某 account 选 2025-09，导致新增此列 | 我查看其他 account 在 2025-09 | 显 "-"，不算数据缺失 |

### 十五、Side-by-Side：内联编辑与指派

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-131 | 数值编辑灰底 | 单元格值 1000 | 我编辑为 1200 保存 | 显 1200 且灰色背景 |
| TC-132 | 删除值回填 0 | 单元格值 500 | 我清空保存 | 显 0，作为有效数据，灰色背景 |
| TC-133 | 数据完整才显指派下拉 | 某 unmapped 缺日期 | 我查看 | 无下拉，不能 map |
| | | | 我补全日期 | 出现指派下拉 |
| TC-134 | NA 阻止指派 | 某账目含 NA 月份 | 我查看 | 无下拉 |
| TC-135 | "-" 不阻止指派 | 某账目月份为 "-" | 我查看 | 有下拉 |
| TC-136 | 指派后整行落到指标 | 1-6 月完整数据 | 我从下拉选 Gross Revenue (Actuals) | 1-6 月所有数据整行 map |
| TC-137 | 下拉含 Actuals/Forecast 双选 | 打开指派下拉 | 我查看 | 每指标显两条：Actuals 与 Forecast |
| TC-138 | Forecast 紫色 | 同上 | 我查看 Forecast 项 | 紫色显示 |
| TC-139 | 下拉支持名称筛选 | 打开下拉 | 我输入 "rev" | 仅显含 rev 的指标 |
| TC-140 | 第一指派提示气泡 | 进入页面，无任何 map | 我查看 | 第一个可指派账目旁显 Click to assign this item to an LG Metric |
| | | | 我完成第一个 map | 提示消失 |
| TC-141 | mapped 项改 unmapped | 已 mapped | 我从下拉选 unmapped | 该行回到 Unmapped 区 |
| TC-142 | mapped 项重新指派 | 已 map 到 G&A Expenses | 我改选 R&D Expenses (Actuals) | 重新映射到 R&D Expenses |
| TC-143 | mapped 切换 Actuals/Forecast | 已 map Gross Revenue (Actuals) | 我改选 Gross Revenue (Forecast) | 切换到 Forecast 下显示 |

### 十六、Side-by-Side：多源账目与合计

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-144 | 单源直接显数值 | Cash 下仅 1 个源账目 | 我查看 | 直接显数值，可编辑 |
| TC-145 | 多源展开 + 数量显示 | G&A Expenses 下 3 个源账目 | 我查看 | 指标名旁显 "3" |
| | | | 我点击展开 | 展开 3 条源账目 |
| TC-146 | 合计金额计算 | 3 源 2025-01 数值 100/200/300 | 我查看 LG 合计 | 显 600，不可编辑 |
| TC-147 | 合计因币种不一致显 "-" | 同 LG 指标 2 源 USD 100 + EUR 200 | 我查看合计 | 默认 "-"，不写入 |
| TC-148 | 合计因类型冲突显 "-" | 货币指标下含百分比类源项 | 我查看 | 显 "-"，不写入 |
| TC-149 | 多币种原样显示 | 源分别 $100、€200、£150 | 我查看源账目 | 各币种符号原样显示 |
| TC-150 | total 不进匹配 | Excel 含 "Total Expenses" 总计行+子项 | 我查看 | 总计不进入匹配；仅子项进入 |

### 十七、Side-by-Side：联动与布局

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-151 | 左选文件 → 右同步 | All Files 状态 | 我从下拉选文件 A | 右面板同步显 A 的数据 |
| TC-152 | All Files 合并数据 | 多文件状态 | 我选 All Files | 右面板显合并数据 |
| TC-153 | Tab 切换不影响左面板 | 左选文件 A，右 Actuals Tab | 我切到 Proforma Tab | 左面板仍 A |
| TC-154 | 左右面板比例可调 | 默认 50/50 | 我拖动分隔条 | 比例可调 |
| TC-155 | 隐藏左面板 | 50/50 | 我点击隐藏图标 | 左面板隐藏，右全宽 |

### 十八、Side-by-Side：No mapped data 特殊路径

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-156 | No mapped data 提示 | 该批无可映射数据 | 我查看右面板 | 显 No mapped data 文案 |
| TC-157 | Next 弹 Files Uploaded Successfully | No mapped 状态 | 我点 Next | 弹窗显 No financial accounts extracted. [amount] file(s) have been uploaded to the Imported Statements folder |
| TC-158 | Go to Documentation | 弹窗显示 | 我点 Go to Documentation | 跳 All Documentation 页 |
| TC-159 | Close 关闭弹窗 | 弹窗显示 | 我点 Close | 关闭弹窗 |
| TC-160 | 首次创建 Imported Statements 文件夹 | 首次提交 | 我提交 | Documentation 下创建 Imported Statements 文件夹 |

### 十九、Side-by-Side：返回与继续

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-161 | 无 Unmapped 直进 Summary | 全部 mapped | 我点 Next | 直进 Mapping Summary |
| TC-162 | 有 Unmapped 弹确认窗 | 50 条改动 + 15 条 unmapped 未解决 | 我点 Next | 弹窗显 [50] fields with mismatched LG metric mappings 和 [15] unmapped accounts that will not be written |
| TC-163 | 无未匹配第二行不显 | 仅 50 条改动，0 unmapped | 我点 Next | 弹窗仅显第一行 |
| TC-164 | Continue to Next Step | 确认窗 | 我点 Continue to Next Step | 进 Mapping Summary |
| TC-165 | Go Back | 确认窗 | 我点 Go Back | 关闭，回 Mapping |
| TC-166 | Cancel Data Mapping 弹确认 | Side-by-Side 页 | 我点右上 Cancel | 弹 Cancel Data Mapping? 确认窗 |
| | | | 我点 Cancel data mapping | 回 Financial Entry |
| TC-167 | Continue data mapping 保持页 | 同上 | 我点 Continue data mapping | 关闭弹窗，保持页 |

### 二十、写入：Verify Data 摘要页

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-168 | Mapping Summary 文案与统计 | 进入 Verify Data | 我查看 | 显文案、源文件总数、映射类型数、映射科目数 |
| TC-169 | 源文件列表 | 同上 | 我查看下方列表 | 显文件名/大小/匹配源账目数 |
| TC-170 | Previous Step 返回 Mapping | Verify Data | 我点 Previous Step | 回 Data Mapping 页 |
| TC-171 | Start Verification + loading | Verify Data | 我点 Start Verification | 显 loading circle，开始校验 |
| TC-172 | 仅 Proforma 按钮 Confirm and write | 本批仅 Proforma 数据 | 我查看按钮 | 显 Confirm and write to LG（跳过冲突） |
| TC-173 | 仅 mapped 非 "-" 项写入 | 含合计 "-" 的指标 | 我提交 | 该指标不写入，其他正常写入 |

### 二十一、写入：冲突检测与冲突弹框

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-174 | 冲突按公司+指标+月年比对 | 公司 A、Revenue、2025-01 LG 已有 1000，本次合计 1200 | 我 Start Verification | 该单元格识别为冲突 |
| TC-175 | 目标月份为空不冲突 | LG 该月无值，本次合计 800 | 我 Start Verification | 不视为冲突，自动写入 |
| TC-176 | 一致不写入 | LG 500，本次 500 | 我 Start Verification | 不触发新写入 |
| TC-177 | 仅显 Actuals 冲突 | 同时有 Actuals 与 Proforma 数据均与 LG 不同 | 我 Start Verification | 冲突页仅显 Actuals 单元格 |
| TC-178 | Proforma 直生 history Source/User | 仅 Proforma 提交 | 提交完成 | Committed Forecast history Source=Import Statements，User=上传人 |
| TC-179 | 上传人删除留痕 | 上传人账户被删除 | 我查看 history | User 字段仍显原上传人 |
| TC-180 | 冲突单元格字体红 | 冲突页 | 我查看冲突单元格 | 字体红色 |
| TC-181 | 货币不同统一转换 | 上传 EUR 100，LG USD 110 | 我 Start Verification | 转换为 LG 货币（USD）对比 |
| TC-182 | 选 Mapped 保留原币种 | 冲突中选 Mapped Value，源 EUR 100 | 我保存 | 存原始 EUR 100 |
| TC-183 | 默认 Radio MAPPED VALUE | 我点冲突单元格 | 弹框显示 | Radio 默认选中 MAPPED VALUE |
| TC-184 | Notes 必填报错 | 弹框打开 | 我未填 Notes 点 Next | 报错 A note is required before continuing. |
| TC-185 | Notes 长度 2000 上限 | 弹框 | 我粘 2500 字符 | 仅接受 2000，超出不能继续输入 |
| TC-186 | 弹框仅 ✖ 关闭 | 弹框打开 | 我点弹框外 | 弹框不关 |
| TC-187 | 全部填完 Next 激活 | Radio 已选、Notes 已填 | 我查看 Next | 激活 |
| TC-188 | 解决后变绿自动下一个 | 冲突 #1 已解决 | 我点 Next | #1 变绿，自动打开 #2 弹框 |
| TC-189 | 跳转顺序：同指标左→右 | Revenue 有 2025-01/03/05 三冲突 | 我依次解决 | 顺序 01→03→05 |
| TC-190 | 指标内完成跳下指标 | Revenue 全完后还有 COGS 冲突 | 我继续 | 跳到 COGS 第一个冲突，依旧左→右 |
| TC-191 | 最后冲突按钮 Save | 仅剩最后 1 冲突 | 我查看 | 按钮显 Save |
| TC-192 | 点击 Save 完成 | 最后冲突填完 | 我点 Save | 关闭，全部冲突解决 |
| TC-193 | 冲突页 Previous Step 返回 | 冲突页 | 我点 Previous Step | 回 Verify Data |
| TC-194 | 冲突页右上 Previous 返回 | 冲突页 | 我点右上 Previous | 回 Verify Data |

### 二十二、写入：覆盖、跳过与提交

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-195 | MAPPED VALUE 覆盖 | LG=1000、上传=1200，选 Mapped | 我保存提交 | LG 变 1200，原 1000 保留为历史 |
| TC-196 | LG VALUE 跳过 | 选 LG Value | 我保存提交 | LG 不变，该指标不写入，其他继续 |
| TC-197 | 无任何冲突跳过该步 | 全部一致或 LG 空 | 我 Start Verification | 跳过冲突页直接到成功 |
| TC-198 | Confirm & Submit 提交 | 所有冲突已解决 | 我点 Confirm & Submit to LG | 跳 Benchmarking 页弹成功窗 |
| TC-199 | 成功弹窗文案 | 成功弹窗显示 | 我查看 | 显 Data Submitted Successfully + [amount] Source Files / Data Types Updated / Mapped Accounts |
| TC-200 | Close 关闭成功弹窗 | 弹窗 | 我点 Close | 关闭 |

### 二十三、写入：步骤切换与 Schema 校验

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-201 | 切换不改动数据保留 | 已解决 2 个冲突 | 我 Previous Step→Verify→Start Verification | 已解决冲突保留 |
| TC-202 | 改动后回 Summary 显提示 | 冲突页→Previous→Mapping 改源账目数值 | 我 Next 回 Verify Data | 显 Your mapping changes have been applied. Please review the updated verification results. |
| TC-203 | 重检受影响数据 | 已显提示后 | 我点 Start Verification | 有变化冲突重检；无变化保留 |
| TC-204 | 提示再次回 Summary 消失 | 完成重检后再回 Verify Data | 我查看 | 提示已消失 |
| TC-205 | Schema 校验失败终止 | 提交校验未通过 | 系统处理 | 终止写入，显错误，回相关步骤高亮 |
| TC-206 | 不允许部分写入 | 校验中部分失败 | 系统处理 | 整体不写入 |

### 二十四、写入：审计与下游反映

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-207 | 立即反映 Financial Entry | 刚提交 Actuals | 我导航到 Financial Entry | 数据已显示 |
| TC-208 | 立即反映 Committed Forecast | 刚提交 Proforma | 我导航到 Committed Forecast | 新版本已显 |
| TC-209 | 触发 normalization | 提交完成 | 我查看 normalization 流程 | 已触发 |
| TC-210 | 触发 benchmarking | 提交完成 | 我查看 benchmarking | 已触发 |
| TC-211 | Imported Statements 文件夹 | 提交完成（含 No mapped 场景） | 我导航 Company Documents | 上传文件均在 Imported Statements 文件夹 |
| TC-212 | 新 closed month 邮件通知 | 提交触发新 closed month | 我查看邮件 | 收到通知邮件 |
| TC-213 | 审计字段齐全 | 提交完成 | 我查看后端审计 | 含时间戳、用户、源文档、报告期、文档类型、动作（written/overwritten/skipped） |
| TC-214 | 被覆盖数据保留历史 | LG 原 1000 被覆盖 1200 | 我查看历史 | 原 1000 作为历史版本保留 |

### 二十五、备注字段与列表页

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-215 | 备注 free-form 输入 | 冲突弹框 Notes | 我输入字母+数字+中文+符号 | 全部可输入 |
| TC-216 | 任何方案下 Notes 可用 | Radio 选 LG Value | 我查看 Notes | 仍可输入且必填 |
| TC-217 | 上传确认后备注只读 | 提交成功后 | 我打开某条 Note 记录 | 备注只读 |
| TC-218 | Financial Entry 入口 | 在 Financial Entry 页 | 我点 Note 按钮 | 进 Data Mapping Notes 列表 |
| TC-219 | Committed Forecast 入口 | 在 Committed Forecast 页 | 我点 Note 按钮 | 进 Data Mapping Notes 列表 |
| TC-220 | Note 列表字段齐全 | 列表页 | 我查看表头 | 显 Data Mapping Time Stamp(UTC) / Metric / Financial Month / LG Value / Mapped Value / Data Source / Note Content |
| TC-221 | 时间顺序排列 | 多条备注 | 我查看顺序 | 按时间排列 |
| TC-222 | 无数据显 No Data | 公司无备注 | 我打开列表 | 显 No Data |
| TC-223 | Select Metric 下拉筛选 | 列表显示 | 我点 Select Metric 下拉 | 含 Metric 列表 + search bar |
| | | | 我搜 "Revenue" 选 Gross Revenue | 列表筛该指标 |
| TC-224 | 月历筛选 | 同上 | 我点月历选择器 | 含 search bar |
| | | | 我选 2025-03 | 列表筛该月 |
| TC-225 | 超长备注截断 | 备注超两行字符 | 我查看 Note Content | 截断两行，显 See More |
| TC-226 | See More 弹窗 | 超长备注 | 我点 See More | 弹窗显完整 |
| TC-227 | 弹窗仅 X/Close 关闭 | 备注弹窗 | 我点弹窗外 | 不关 |
| | | | 我点 X 或 Close | 关闭 |
| TC-228 | 长内容弹窗竖向滚动 | 弹窗内容超出高度 | 我查看 | 显竖向滚动条 |
| TC-229 | 分页总数范围 | 列表有 192 条 | 我查看底部 | 显 1 - 10 of 192 items |
| TC-230 | 上下页箭头 | 同上 | 我点下一页 | 显 11-20 |
| TC-231 | 页码直选 | 同上 | 我点页码 5 | 跳到第 5 页 |
| TC-232 | 省略号跳转 | 多页 | 我点省略号 | 显跳转输入 |
| TC-233 | 每页行数 | 同上 | 我查看每页行数 | 默认 10 |
| | | | 我切 20/页 | 显 20 条 |
| TC-234 | 面包屑返回 | 列表页 | 我点 Financial Entry | 返回 Financial Entry |

### 二十六、AI 学习与持续改进

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-235 | 决策记录为 AI 信号 | 我 override 一条映射 | 提交完成 | override 决策记录 |
| TC-236 | 公司级学习实时 | 我将"Subscription Revenue"override 为 Gross Revenue 并提交 | 我再上传含该账目的新文档 | 该公司 AI 直接建议 Gross Revenue |
| TC-237 | 核心引擎级学习 | 通用规则与关键词集合更新 | 任意公司新上传 | 应用全局更新 |
| TC-238 | 新文档识别 | 上传前未见版式 | 系统提取与映射 | 给出基于历史学习的建议 |
| TC-239 | 向后兼容 | AI 模型更新发布 | 我打开过去已处理文档 | 既有映射不失效，无新增错误 |
| TC-240 | 双版本审计写入 | 提交完成 | 我查看映射记录 | 含 Core Engine Version + Company Mapping History ID |
| TC-241 | 流程中退出不保存学习 | 我在冲突解决步骤关闭/Cancel | 我再上传同一文档 | 流程中已 override 未被记住 |
| TC-242 | 本次记住不作用于当次 | 我在同一次流程改了 A→Gross Revenue | 同一流程内再次出现 A | 不自动建议（须完整提交后才生效） |

### 二十七、端到端流程完整性

> 串联上传 → 提取（OCR/Excel）→ AI 映射 → Side-by-Side → 写入 → 学习的全流程闭环测试，覆盖主成功路径与典型异常路径。

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-243 | 主成功路径：Excel 无冲突 Actuals | 公司 LG 该期数据为空 | 我点 Import Statement 上传一份 5MB xlsx（仅 Actuals） | 进度条 100%，Next 可用 |
| | | | 我点 Next | 进入解析，loading 后右面板显数据，AI 全部自动 mapped |
| | | | 我点 Next | 直接进 Mapping Summary（无 Unmapped） |
| | | | 我点 Start Verification | 无冲突直接到提交成功 |
| | | | 我导航 Financial Entry | 数据已写入；Imported Statements 文件夹含原文件 |
| TC-244 | 主成功路径：扫描 PDF + 手动映射 Actuals | 公司 LG 该期数据为空 | 我拖拽 8MB 扫描 PDF 到上传区 | 上传完成 |
| | | | 我点 Next | OCR 完成；右面板部分 unmapped |
| | | | 我把 unmapped 中的 5 条手动指派到对应 LG 指标 | 各行变为 mapped |
| | | | 我点 Next | 因仍有少量 unmapped，弹确认窗显两项统计 |
| | | | 我点 Continue to Next Step → Start Verification | 无冲突直接到提交成功 |
| | | | 我查看 Financial Entry | 数据已写入；unmapped 未写入 |
| TC-245 | 主成功路径：混合 + 冲突解决 + 备注 | LG 已有 2025-01 Revenue=1000 | 我一次上传 3 文件（含 Actuals 与 Proforma） | 上传完成 |
| | | | 我点 Next → 全部 mapped → Next → Start Verification | 冲突单元格红色，弹首个冲突弹框 |
| | | | 我对 Revenue 2025-01 选 Mapped Value 输入 Notes "Q1 closed restated, ticket #123" 点 Next | 单元格变绿，自动打开下一个冲突 |
| | | | 我依序解决所有冲突，最后弹框点 Save | 全部冲突解决 |
| | | | 我点 Confirm & Submit to LG | 跳 Benchmarking 并弹成功窗 |
| | | | 我点 Note 按钮查看备注 | 列表显刚才填的备注 |
| | | | 我查看 Committed Forecast history | Proforma 新版本 Source=Import Statements |
| TC-246 | 全部文件失败回退路径 | 上传 3 个全坏文件 | 我上传 → Next → 解析完成 | 弹 File Processing Errors 列 3 文件 |
| | | | 我点 Discard Problem Files | 回 Financial Entry |
| | | | 我导航 Company Documents | 失败文件未出现（不抽取也走归档需重新上传） |
| TC-247 | 部分文件失败回退路径 | 上传 5 文件，2 个坏 | 我上传 → Next | 弹 File Processing Errors 列 2 文件 |
| | | | 我点 Re-upload 选两个替代文件 | 替代文件进队列 |
| | | | 我完成上传与映射并提交 | 提交成功 |
| TC-248 | 无可用数据归档路径 | 上传 1 张无表的图片 | 我上传 → Next | 右面板显 No mapped data |
| | | | 我点 Next | 弹 Files Uploaded Successfully |
| | | | 我点 Go to Documentation | 跳 All Documentation |
| | | | 我查看 Imported Statements 文件夹 | 原文件出现在此 |
| TC-249 | 仅 Proforma 走简化路径 | LG 该期 Proforma history 1 个版本 | 我上传仅 Proforma 数据文件 → Next → 全部 mapped → Next | 进 Mapping Summary，按钮显 Confirm and write to LG（无冲突步骤） |
| | | | 我点 Confirm and write to LG | 提交成功 |
| | | | 我查看 Committed Forecast history | 新增版本，Source=Import Statements |
| TC-250 | 流程中退出学习不保存 | 我开始上传 Actuals 文件 | 我 override 一条 AI 建议 | mapped 变更暂存 |
| | | | 在冲突解决步骤我点 Cancel data mapping | 回 Financial Entry |
| | | | 我重新上传相同文件走到 Side-by-Side | 之前的 override 未被 AI 记住，建议保持原状 |
| TC-251 | 完整路径学习生效 | 公司从未处理过 "X Revenue" 账目 | 我上传含此账目的文件，override 为 Gross Revenue，全流程提交成功 | 提交完成；学习写入 Company Mapping History |
| | | | 我再上传含 "X Revenue" 的另一份文件 | 进入 Side-by-Side 时 AI 直接建议 Gross Revenue |
| TC-252 | 步骤切换数据保留 + 受影响重检 | 已完成部分冲突解决 | 我点 Previous Step 回 Verify Data 再点 Previous Step 到 Mapping | 已解决冲突保留 |
| | | | 我在 Mapping 修改某源数值 → Next → Verify Data | 显 Your mapping changes have been applied. Please review the updated verification results. |
| | | | 我点 Start Verification | 受影响冲突重检，其他保留 |
| TC-253 | Cancel 流程逐级返回 | 已上传文件并在 Side-by-Side | 我点右上 Cancel | 弹 Cancel Data Mapping? |
| | | | 我点 Continue data mapping | 保持页 |
| | | | 我再次点 Cancel → Cancel data mapping | 回 Financial Entry，本次流程数据不写入 |

---

## 需求追溯矩阵

### 模块一：① 文件上传

| 需求 | 描述 | 覆盖 | 用例 | 备注 |
|---|---|---|---|---|
| R1.1 | Manual 类型可见入口 | ✅ | TC-001, TC-002 | |
| R1.2 | 三种角色上传权限 | ✅ | TC-003, TC-004, TC-005 | |
| R1.3 | 上传按钮位置 | ✅ | TC-001, TC-006 | |
| R1.4 | 支持的文件格式 | ✅ | TC-019 ~ TC-023 | |
| R1.5 | 桌面/移动端上传方式 | ✅ | TC-007, TC-008, TC-009 | |
| R1.6 | 批量上传 | ✅ | TC-010, TC-011 | |
| R1.7 | 20MB / 100MB 限制 | ✅ | TC-025, TC-026, TC-027 | |
| R1.8 | 重复文件判定 | ✅ | TC-029, TC-030 | |
| R1.9 | 5 种错误文案 | ✅ | TC-024, TC-025, TC-027, TC-029, TC-031 | |
| R1.10 | 同类错误合并不重复 | ✅ | TC-033, TC-034, TC-036 | |
| R1.11 | 错误追加 + 倒计时重置 | ✅ | TC-032 | |
| R1.12 | 不同类型错误独立 | ✅ | TC-035 | |
| R1.13 | 二次上传累计超 100MB | ✅ | TC-028, TC-097 | |
| R1.14 | 进度条 + Next 禁用 | ✅ | TC-012 | |
| R1.15 | Clear All | ✅ | TC-013 | |
| R1.16 | Remove | ✅ | TC-014, TC-015 | |
| R1.17 | 继续添加 | ✅ | TC-011 | |
| R1.18 | Cancel / Next 跳转 | ✅ | TC-016, TC-017, TC-018 | |

### 模块二：② 数据提取

| 需求 | 描述 | 覆盖 | 用例 | 备注 |
|---|---|---|---|---|
| R2.1 | 仅提取 table | ✅ | TC-037 | |
| R2.2 | 双维度独立分类 | ✅ | TC-044 | |
| R2.3 | Proforma 识别信号 | ✅ | TC-038 ~ TC-041 | |
| R2.4 | 报表类型识别 | ✅ | TC-042, TC-043 | |
| R2.5 | 无法归类的归档 | ✅ | TC-046, TC-047, TC-248 | |
| R2.6 | 多页多类型 | ✅ | TC-045 | |
| R2.7 | 报告期识别优先级 | ✅ | TC-048 ~ TC-051 | |
| R2.8 | OCR 多页跳过 | ✅ | TC-052 | |
| R2.9 | OCR 容错 | ✅ | TC-053, TC-054 | |
| R2.10 | OCR 精确捕获 | ✅ | TC-055, TC-056 | |
| R2.11 | Excel/CSV 解析 | ✅ | TC-057 ~ TC-061 | |
| R2.12 | 启发式分类标记待审核 | ✅ | TC-062 | |

### 模块三：③ AI 辅助账户映射

| 需求 | 描述 | 覆盖 | 用例 | 备注 |
|---|---|---|---|---|
| R3.1 | 映射自动执行 | ✅ | TC-063 | |
| R3.2 | 每行项生成建议 | ✅ | TC-064 ~ TC-081 | |
| R3.3 | 15 个 LG 科目 | ✅ | TC-064 ~ TC-081 | |
| R3.4 | 语义 + 父子层级 | ✅ | TC-070 | |
| R3.5 | Unmapped 标记 | ✅ | TC-082, TC-116 | |
| R3.6 | Revenue Contra | ✅ | TC-065 | |
| R3.7 | COGS 关键词 | ✅ | TC-066 | |
| R3.8 | S&M 子类 | ✅ | TC-067, TC-068 | |
| R3.9 | R&D 关键词 | ✅ | TC-069 | |
| R3.10 | G&A 子类 | ✅ | TC-071, TC-072 | |
| R3.11 | Payroll 默认 G&A + alert | ✅ | TC-073 | |
| R3.12 | Cash 关键词 | ✅ | TC-074 | |
| R3.13 | AR 关键词 | ✅ | TC-075 | |
| R3.14 | Capitalized R&D 双信号 | ✅ | TC-076, TC-077 | |
| R3.15 | Other Assets 兜底 | ✅ | TC-078 | |
| R3.16 | AP 关键词 | ✅ | TC-079 | |
| R3.17 | LT Debt 关键词 | ✅ | TC-080 | |
| R3.18 | Other Liabilities 兜底 | ✅ | TC-081 | |
| R3.19 | COGS/R&D 重叠默认 COGS | ✅ | TC-083 | |
| R3.20 | 语义重复警示 | ✅ | TC-084, TC-085 | |
| R3.21 | 补名后不再触发语义检测 | ✅ | TC-086 | |
| R3.22 | Source 合并规则 | ✅ | TC-087 ~ TC-091 | |
| R3.23 | 映射持久化与审计 | ✅ | TC-213, TC-240 | |

### 模块四：④ Side-by-Side 审核与内联编辑

| 需求 | 描述 | 覆盖 | 用例 | 备注 |
|---|---|---|---|---|
| R4.1 | Loading 状态 | ✅ | TC-092, TC-093 | |
| R4.2 | File Processing Errors 弹窗 | ✅ | TC-094, TC-095 | |
| R4.3 | 弹窗按钮 | ✅ | TC-096, TC-098, TC-100 | |
| R4.4 | Re-upload 累计超 100MB | ✅ | TC-097 | |
| R4.5 | Discard/✖ 返回逻辑 | ✅ | TC-098 ~ TC-101 | |
| R4.6 | 左面板下拉/Sheet/翻页/缩放 | ✅ | TC-102 ~ TC-106 | |
| R4.7 | 左面板文件管理 | ✅ | TC-107, TC-108 | |
| R4.8 | 右面板 Tab 默认 | ✅ | TC-109, TC-110, TC-111 | |
| R4.9 | 无数据 Tab 空状态 | ✅ | TC-112 | |
| R4.10 | Unmapped 位置 + Tab 控制 | ✅ | TC-116 | |
| R4.11 | USD 开关不适用 | ✅ | TC-115 | |
| R4.12 | UNIDENTIFIED 标签 | ✅ | TC-117, TC-118 | |
| R4.13 | NA / No Date | ✅ | TC-119, TC-120 | |
| R4.14 | 选月份累加 | ✅ | TC-124 | |
| R4.15 | 非连续月+缺日期排列 | ✅ | TC-125 | |
| R4.16 | 链式日期推算 | ✅ | TC-126 ~ TC-128 | |
| R4.17 | 左右冲突以左为主 | ✅ | TC-129 | |
| R4.18 | 缺名+缺日期切换 | ✅ | TC-121 | |
| R4.19 | "-" 不算缺失 | ✅ | TC-130 | |
| R4.20 | UNIDENTIFIED 命名不自动 map | ✅ | TC-118 | |
| R4.21 | 指派下拉双选/紫/筛选 | ✅ | TC-137, TC-138, TC-139 | |
| R4.22 | 第一指派提示气泡 | ✅ | TC-140 | |
| R4.23 | 数值编辑回填 0 + 灰底 | ✅ | TC-131, TC-132 | |
| R4.24 | 数据完整才显下拉 | ✅ | TC-133, TC-134, TC-135 | |
| R4.25 | 指派后整行落到指标 | ✅ | TC-136 | |
| R4.26 | 源账目名锁定 | ✅ | TC-122, TC-123 | |
| R4.27 | mapped 可编辑/重指派/回 unmapped | ✅ | TC-141, TC-142, TC-143 | |
| R4.28 | No mapped data 提示 | ✅ | TC-156 | |
| R4.29 | No mapped 后归档 Documentation | ✅ | TC-157 ~ TC-160 | |
| R4.30 | 单一数据类型空 Tab 提示 | ✅ | TC-112 | |
| R4.31 | 单源直接显数值 | ✅ | TC-144 | |
| R4.32 | 多源展开 + 合计 | ✅ | TC-145, TC-146 | |
| R4.33 | 合计无法计算 "-" | ✅ | TC-147, TC-148 | |
| R4.34 | total 不进匹配 | ✅ | TC-150 | |
| R4.35 | 多源语义重复警示 | ✅ | TC-084 | |
| R4.36 | 改映射任意指标 | ✅ | TC-142, TC-143 | |
| R4.37 | 非连续月提示 + 首列固定 | ✅ | TC-113, TC-114 | |
| R4.38 | 左选 → 右同步 / All Files | ✅ | TC-151, TC-152 | |
| R4.39 | Tab 切换不影响左 | ✅ | TC-153 | |
| R4.40 | 比例调节 + 隐藏 | ✅ | TC-154, TC-155 | |
| R4.41 | 确认或重新上传 | ✅ | TC-096, TC-161 | |
| R4.42 | 有/无 Unmapped 处理 | ✅ | TC-161, TC-162 | |
| R4.43 | 确认窗按钮 | ✅ | TC-164, TC-165 | |
| R4.44 | 无未匹配第二行不显 | ✅ | TC-163 | |
| R4.45 | Cancel Data Mapping 确认 | ✅ | TC-166, TC-167 | |

### 模块五：⑤ 写入 LG Schema

| 需求 | 描述 | 覆盖 | 用例 | 备注 |
|---|---|---|---|---|
| R5.1 | 仅 mapped 非 "-" 写入 | ✅ | TC-173, TC-147 | |
| R5.2 | Verify Data 文案统计 | ✅ | TC-168 | |
| R5.3 | 源文件列表 | ✅ | TC-169 | |
| R5.4 | Verify Data 按钮 + loading | ✅ | TC-170, TC-171 | |
| R5.5 | 冲突按维度比对 | ✅ | TC-174 | |
| R5.6 | 仅有值且不同才冲突 | ✅ | TC-175, TC-176 | |
| R5.7 | 仅显 Actuals + Proforma 直生 | ✅ | TC-177, TC-178 | |
| R5.8 | 上传人删除留痕 | ✅ | TC-179 | |
| R5.9 | 冲突格式 + 红色 | ✅ | TC-180 | |
| R5.10 | 货币转换 + 原币种保存 | ✅ | TC-181, TC-182 | |
| R5.11 | 冲突弹框内容 | ✅ | TC-183, TC-186, TC-187 | |
| R5.12 | Notes 必填报错 | ✅ | TC-184 | |
| R5.13 | 跳转顺序 | ✅ | TC-188, TC-189, TC-190 | |
| R5.14 | 最后冲突 Save | ✅ | TC-191, TC-192 | |
| R5.15 | 冲突页 Previous | ✅ | TC-193, TC-194 | |
| R5.16 | 仅 Proforma 直接提交 | ✅ | TC-172, TC-249 | |
| R5.17 | Mapped Value 覆盖 | ✅ | TC-195 | |
| R5.18 | LG Value 跳过 | ✅ | TC-196 | |
| R5.19 | LG 空自动写入 / 一致不写 | ✅ | TC-175, TC-176 | |
| R5.20 | 无冲突跳过该步 | ✅ | TC-197 | |
| R5.21 | Confirm & Submit | ✅ | TC-198 | |
| R5.22 | 成功弹窗 + Close | ✅ | TC-199, TC-200 | |
| R5.23 | 切换数据保留 + 提示 | ✅ | TC-201 ~ TC-204, TC-252 | |
| R5.24 | Schema 校验失败 | ✅ | TC-205 | |
| R5.25 | 不允许部分写入 | ✅ | TC-206 | |
| R5.26 | 写入审计 + 历史 | ✅ | TC-213, TC-214 | |
| R5.27 | 立即反映下游 | ✅ | TC-207 ~ TC-210 | |
| R5.28 | Imported Statements 文件夹 | ✅ | TC-160, TC-211, TC-248 | |
| R5.29 | closed month 邮件 | ✅ | TC-212 | |

### 模块六：⑥ 备注字段

| 需求 | 描述 | 覆盖 | 用例 | 备注 |
|---|---|---|---|---|
| R6.1 | 必填 + 2000 上限 | ✅ | TC-184, TC-185 | |
| R6.2 | 任何方案可用 | ✅ | TC-216 | |
| R6.3 | 无数据显 No Data | ✅ | TC-222 | |
| R6.4 | Note 入口 | ✅ | TC-218, TC-219 | |
| R6.5 | 列表字段 | ✅ | TC-220 | |
| R6.6 | Metric/月历筛选 | ✅ | TC-223, TC-224 | |
| R6.7 | 超长截断 + See More | ✅ | TC-225 ~ TC-228 | |
| R6.8 | 分页 | ✅ | TC-229 ~ TC-233 | |
| R6.9 | 面包屑返回 | ✅ | TC-234 | |
| R6.10 | 最终只读 + 审计关联 | ✅ | TC-217 | |

### 模块七：⑦ 系统学习与持续改进

| 需求 | 描述 | 覆盖 | 用例 | 备注 |
|---|---|---|---|---|
| R7.1 | 决策记录为信号 | ✅ | TC-235 | |
| R7.2 | 公司级实时学习 | ✅ | TC-236, TC-251 | |
| R7.3 | 核心引擎级学习 | ✅ | TC-237 | |
| R7.4 | 新文档识别 | ✅ | TC-238 | |
| R7.5 | 向后兼容 | ✅ | TC-239 | |
| R7.6 | 双版本审计 | ✅ | TC-240 | |
| R7.7 | 流程退出不保存 + 本次不作用 | ✅ | TC-241, TC-242, TC-250 | |

### 端到端流程覆盖

| 流程路径 | 覆盖用例 |
|---|---|
| 主成功：Excel 全 mapped 无冲突 → 提交 | TC-243 |
| 主成功：OCR 部分 unmapped 手动 map → 提交 | TC-244 |
| 主成功：混合数据 + 冲突解决 + 备注 → 提交 | TC-245 |
| 异常：全部文件失败 → Discard → 退回 | TC-246 |
| 异常：部分失败 → Re-upload → 提交 | TC-247 |
| 异常：无可用数据 → 归档 Documentation | TC-248 |
| 简化：仅 Proforma → 跳过冲突 → 提交 | TC-249 |
| 学习：流程中退出不保存 | TC-250 |
| 学习：完整提交后学习生效 | TC-251 |
| 步骤切换 + 数据保留 + 受影响重检 | TC-252 |
| Cancel 退出 | TC-253 |

**覆盖率：100%**（127/127 条需求全部为"已覆盖"状态）

> 本测试用例集按业务流程的 7 大模块组织需求清单，并新增"端到端流程完整性"一章（TC-243 ~ TC-253）串联上传 → 提取 → AI 映射 → Side-by-Side 审核 → 写入 → 学习的全流程闭环，覆盖主成功路径与典型异常路径。
