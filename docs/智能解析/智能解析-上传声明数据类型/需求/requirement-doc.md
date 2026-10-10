# 需求文档：手动上传时声明 Actuals / Proforma

> 关联文档：
> - 下游（第四阶段 · 功能设计）：[design-doc](../设计/design-doc.md)
> - 被本需求取代的旧规则：[需求文档-Actuals导入中处理当前日历月数据](../../需求文档-Actuals导入中处理当前日历月数据.md)（"当月数据转为 Proforma" 不再适用，见 §二）
> - 智能解析总体需求：[Manual_Uploads_with_OCR_需求文档](../../Manual_Uploads_with_OCR_需求文档.md)

**来源任务**：Manual Upload - Actuals / Pro Forma Declaration at Upload
**适用模块**：手动上传 OCR 导入（Financial Entry 的 Import Statements 上传弹窗、数据映射页）
**Figma 设计稿**：https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=17631-18431
**适用公司**：手动录入（Manual）公司
**计划迭代**：sprint121
**修订**：2026-10-10 按开发设计审核结论修订 R4：当前日历月按"每批上传"取一次；系统推断出的月份同样受当前月保护。补充 R5 历史月份 Proforma 的影响说明、R8 选错类型的处理方式、R9 与实际数相加的后果；AC7 改为"规则不变、差异只来自输入变化"

---

## 一、背景与问题

目前系统通过分析数据本身来判断上传的表格是 Actuals（实际）还是 Proforma（预测），判断以**表**为单位：只要表里有一个未来月份，整张表就被判为 Proforma，即使表里同时还有历史月份。对于在一张表里合理地同时包含历史数据和预测数据的文件，这种做法会分错类。

评估了两种方案后，确定的方向是：**由用户在上传时明确声明文件类型，系统不再推断**。用户上传财务报表时，为每个文件选择 Actuals 或 Proforma。一个文件不能同时包含两种数据：同一期间既要传实际数又要传预测数的，分两次上传。

这样就不再需要按列、按月份推断日期，也免去了随之而来的边界问题：动态列、每次修改映射都要重新校验，以及更灵活的 AI 辅助归类方案所要求的映射页大改。

## 二、与现有规则的关系

| 现有规则 | 本需求后 |
|---|---|
| 系统按表推断 Actuals / Proforma（关键字、未来月份） | **取消**，以用户声明为准 |
| Actuals 表中的当前日历月数据转为 Proforma（旧需求《Actuals 导入中处理当前日历月数据》） | **取消**。声明为 Actuals 的文件，当前日历月及以后的数据**不提取**（不再转成 Proforma） |
| 映射页可以逐行把数据改派为 Actual 或 Forecast | **取消**，类型跟随文件声明 |
| 映射页横幅 "{月份} data treated as Proforma — current month data may be incomplete for Actuals" | 新上传的任务不再出现（不再有当月转 Proforma） |
| 重复月份检测 / 去重 | **不变** |

## 三、用户角色

能在 Financial Entry 页面使用 Import Statements 上传财务报表的用户（手动录入公司）。角色权限与现状一致，本需求不调整。

## 四、业务规则

### R1 上传时必须声明类型
- 每个文件都必须选择类型：**Actuals** 或 **Proforma**。
- **没有默认值**，用户必须自己选。
- 有任一文件未选类型时，不能进入下一步。
- 单文件上传和批量上传规则一致。

### R2 批量设置
- 文件列表下方提供 "Set table type for all files to"，可以一次把所有文件设成同一种类型。
- 批量设置之后，仍然可以逐个修改。
- 一个批次里可以同时有 Actuals 文件和 Proforma 文件，各自按声明的类型处理。

### R3 声明类型是权威的
系统不根据文件里的日期内容推断或改写用户声明的类型。

### R4 Actuals 文件的当前月保护
- 声明为 Actuals 的文件，**当前日历月及以后月份**的数据**不提取**。
- 其他（过去）月份正常提取，并归为 Actuals。
- 这条规则不受用户声明影响，用户也不能关闭。
- 当前日历月：以系统开始处理该批上传文件时的日期（UTC）所在月份为准，同一批文件按同一个月份判断。上传弹窗点一次 Next 是一批；映射页每次上传新文件、替换文件，各算新的一批。
- 完全识别不出月份的数据照常提取，由用户在映射页指定月份；系统按相邻列推断出的月份，如果是当前月及以后，同样不提取。提交时，系统同样不会写入当前月及以后的 Actuals。

### R5 Proforma 文件不受日期限制
声明为 Proforma 的文件，所有月份都提取并归为 Proforma，包括全部是历史月份的情况。例如创始人上传上一年的预测，用来和实际结果对比。

影响说明：提交后，文件涉及的每个年份各生成一个新的承诺预测（Committed Forecast）版本，名称为 "Imported" 加导入日期，覆盖该年份已有的预测值，包括页面上手动编辑时已锁定的过去月份；现金数据随之重新计算。文件跨两个年份就生成两个版本。

### R6 一个文件只能是一种类型
同一个文件不能同时作为 Actuals 和 Proforma 提交。混合数据需要用户先拆成两个文件，分别上传。

### R7 映射页不能改类型
映射页上不再提供逐行切换 Actual / Forecast 的选项。所有数据的类型都跟随所在文件的声明。

### R8 映射页内上传与替换
- **Upload New Document（上传新文件）**：必须为新文件选择类型，规则同 R1。
- **Replace Document（替换文件）**：不需要选择，新文件**继承**被替换文件的类型。
- **选错类型的处理方式**：映射页不提供改类型的入口，替换也沿用原类型。
  - 任务里有多个文件：删掉选错的文件，再用 Upload New Document 重新上传并选对类型，其他文件的映射保留。
  - 只有一个文件：取消本次映射，回到 Financial Entry 重新上传（或把文件改名后用 Upload New Document 上传，再删掉原文件）。

### R9 文件中混有预算 / 预测数据
声明为 Actuals 的文件里如果混有 Budget / Forecast 等列（或工作簿里另有预算 / 预测 sheet），它们统一按 Actuals 处理：当前月及以后被 R4 排除，历史月份作为 Actuals 导入，**与同一科目同月的实际数相加**（报表里的 Variance 等差异列同理）。这是预期行为，用户须在上传前把预算 / 预测拆成单独的 Proforma 文件。

### R10 重复月份检测不变
现有的重复月份检测与去重逻辑独立运行，不受本需求影响。

### R11 上线时的在途任务
上线时还在处理中的任务，不会自动重跑，按失败处理，用户需要重新上传。历史任务不补写类型。

### R12 文案统一
界面上统一用 **Proforma**，不用 "Pro Forma" 或 "Forecast"。

## 五、交互要求（以 Figma 为准）

### 5.1 Upload Financial Documents 弹窗
1. 顶部固定显示说明横幅：**"For Actuals files, data for the current month and later is not extracted."**
2. 拖拽或点击选择文件的区域，支持的格式与大小限制不变。
3. 文件列表的列：FILE NAME / FILE SIZE / TABLE TYPE / Remove。
   - TABLE TYPE 是下拉框，选项为 **Actuals**、**Proforma**，初始为空（占位文案待设计确认，见 §八）。
4. 列表底部：
   - **Set table type for all files to ▾**：批量设置，选项同上。
   - **Clear All**：功能保持现状不变。
5. 底部按钮：Cancel / Next。所有文件都上传完成、并且都选了类型时，Next 才可用。

### 5.2 数据映射页
1. 指派 LG 指标的下拉里，去掉 Actual / Forecast 的选择。
2. Upload New Document：选文件之前（或选文件时）为本次上传的文件选择类型，具体样式待设计（见 §八）。
3. Replace Document：交互保持现状，不额外询问类型。
4. Actuals / Proforma 两个标签页保持不变，数据按文件声明的类型落在对应标签页。

## 六、验收标准

| # | 验收项 |
|---|---|
| AC1 | 手动录入公司的单文件上传和批量上传，每个文件都必须选择 Actuals 或 Proforma；有文件未选时 Next 不可用 |
| AC2 | 批量设置能一次设好所有文件，设完后仍可逐个修改；同一批里可以同时有 Actuals 和 Proforma 文件 |
| AC3 | 系统不按文件的日期内容推断或改写声明的类型 |
| AC4 | 声明为 Actuals 的文件，当前日历月及以后的数据不提取；过去月份正常提取并归为 Actuals |
| AC5 | 声明为 Proforma 的文件，所有月份（含全部为历史月份）都提取并归为 Proforma |
| AC6 | 一个文件不能同时作为 Actuals 和 Proforma 提交；文件的数据全部按其声明类型提取 |
| AC7 | 重复月份检测与去重的规则不变；同一文件的去重结果如与改动前不同，差异只来自本需求带来的输入变化（同一文件内类型统一、Actuals 文件的当前月及以后已剔除） |
| AC8 | 映射页不能再逐行切换 Actual / Forecast |
| AC9 | 映射页 Upload New Document 必须选类型；Replace Document 继承被替换文件的类型 |
| AC10 | 弹窗顶部显示说明横幅 "For Actuals files, data for the current month and later is not extracted." |
| AC11 | 界面文案统一为 Proforma |

## 七、不在本期范围
- QBO 公司的上传入口与类型规则（下个 sprint）。目前 QBO 公司看不到 Import Statements 入口，本期不变。
- 提取完成后提示"某文件的哪些月份没有作为 Actuals 导入"。本期只用弹窗里的固定说明横幅告知用户。
- 历史任务、历史文件补写类型。

## 八、待确认
| # | 问题 | 负责 |
|---|---|---|
| Q1 | TABLE TYPE 下拉未选择时的占位文案（如 "Select"） | 设计 |
| Q2 | 映射页 Upload New Document 选择类型的交互样式（小弹窗还是在文件选择后选择） | 设计 |
| Q3 | 上传弹窗增加 TABLE TYPE 列后的宽度与手机布局 | 设计 |
| Q4 | Clear All 是否常驻（现状只在有文件上传中时出现） | 设计 |
