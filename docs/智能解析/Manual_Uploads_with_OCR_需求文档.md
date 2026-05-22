# EPIC: Manual Uploads with OCR — 需求文档

## 1. 目标与范围

允许手动录入类型（manual entry）公司的用户，将财务文档（PDF、Excel、CSV、图片）上传至 Looking Glass（以下简称 LG），由系统通过 OCR 或直接解析提取财务数据，经 AI 辅助映射到 LG 标准财务科目后，由用户在左右分屏界面核对、编辑，并最终写入 LG 数据库。自动类型（automatic）的公司不会看到此功能入口。

## 2. 业务流程总览

```
① 上传文档
② 提取数据
    ├─ 2a. OCR（扫描/图片 PDF、图片）
    └─ 2b. 直接解析（Excel / CSV）
③ AI 辅助科目映射（自动，后台）
④ Side-by-Side 审核与内联编辑（用户核对）
    └─ 冲突解决（含必填备注）——写入环节中触发
⑤ 写入 LG Schema
⑥ 系统从用户修正中学习，持续优化后续映射
```

---

## 3. 功能需求

### 3.1 文件上传-Stepper中属于Data Mapping步骤

**入口与权限**
- 仅手动录入类型公司可见上传按钮；自动对接公司不显示。
- Company Admin、Company User 可上传本公司文档；Portfolio portal的角色可上传其有权限的全部公司文档。
- 按钮位置： Financial Entry/Committed Forecast 页面 Import Statement按钮，点击按钮即可进入上传流程

**支持的文件格式**
- PDF（扫描版或数字版）
- Excel（.xlsx、.xls）
- CSV
- 图片：JPG、JPEG、PNG、TIFF（TIFF：浏览器原生不支持 TIFF 显示，预览时把 TIFF 转 PNG/JPG，实际存储还是TIFF。）

**上传方式**
- 桌面端：拖拽至上传区域；或点击上传按钮选择文件。点击Cancel按钮或右上角✖按钮可以退出该上传流程
- 移动端：使用移动端文件选择器（不支持拖拽）。
- 支持单文件与多文件（批量）上传。

**文件大小限制与校验**
- 单文件 ≤ 20MB；批量总大小 ≤ 100MB。
- 文档类型和名字相同的文件判定为重复，仅保留一个，第二个不予上传
- 无效文件类型、超限、文件损坏，不可上传，并展示对应错误：
  - `Failed to Upload {File name}. File exceeds the 20MB limit`
  - `Failed to Upload {File name}. File type is not supported`
  - `Failed to Upload {File name}. The combined size of your files exceeds the 100MB limit.`
  - `Failed to Upload {File name}. File is corrupted`
  - `Failed to Upload {File name}. A file with this name already exists.`
  - `Failed to Upload {File name}. `(单纯上传失败，无需解释）
- 同种类型Error，内容不重复展示,仅罗列File name，error消息展示五秒自动消失，也可以点击X关闭
- 动态更新：若旧报错消息尚未消失时，新上传文件再次触发同类型错误，应将新文件名追加至现有列表中，并重置 5 秒倒计时。
- 不同类型隔离：若触发的是不同类型的错误，则正常弹出新的错误消息框，各自独立计时。
- 若同批文档总大小超过100MB，文件不予上传,若二次上传时，第二批与第一批加起来超过100MB，则第二批整批不予上传

**状态与队列管理**
- 每个文件显示上传进度条, Next按钮在全部上传完成前不可用
- 上传过程中，显示clear all按钮，若点击此按钮，则清空全部在上传的文件
- 上传完成后，点击Remove按钮可移除文件
- 点击上传按钮继续添加文件
  
**返回与继续**
- 点击Next按钮，系统自动将文件转入处理流水线，进入 3.2 的提取逻辑。
- 点击Cancel按钮，关闭弹框，回到Financial Entry页面

---

### 3.2 数据提取-Stepper中属于Data Mapping步骤


**表格类型识别**
- 仅提取table中的数据
- 每一个提取出的表格都会沿两个维度独立进行分类：报表类型（Statement Type）和数据类型（Data Type）。报表类型与数据类型是独立进行分类的。
- 数据类型：Actuals、Proforma
 - 关键词：
   - “预测数据”的识别信号（满足其中任一条件即视为预测数据）：
    - 表格标题、章节标题或邻近文本中包含以下关键词之一：Forecast（预测​​）、Proforma（预测报表）、Projection（推算）、Budget（预算）或 Plan（计划）。
    - 列标题所指代的报告期属于未来期间（即日期晚于文档上传日期）。
    - 表格中包含历史日期列与未来日期列的混合数据（即滚动预测）。
    - 若上述所有信号均未出现，该表格将被归类为“Actuals”

- 报表类型：P&L、Balance sheet
 - 关键词：
    - `P&L / Income / Profit` → P&L
    - `Balance / Assets / Liabilities`  → Balance sheet
    - **行标签模式**：
      - P&L：Revenue、COGS、Gross Margin、EBITDA、Net Income。
      - Balance Sheet：Assets、Liabilities、Equity、Cash、Debt。
    - **结构线索**：Balance Sheet 满足 Assets = Liabilities + Equity；P&L 为按期合计的流量报表。
  - **边缘案例**：如果某个表格类型无法依据既定规则进行明确归类，则意味着该表格中未提取出可映射至 LG 支持指标的财务科目。若整个文件中均未提取出任何财务科目，相关情况将在“数据映射”页面上予以提示，详见3.4特殊情况。
  - 多页财务可能同时包含多种数据类型和财务报表类型。

**报告期识别（按优先级）**
1. 列头、行标签
2. 工作表名
3. 表格标题或附近文字
4. 文件名（作为回退选项）

#### 3.2a OCR + AI 提取（扫描 PDF / 图片）

**适用文档**
- 图片型 PDF、扫描 PDF、独立图片文件（JPG、PNG 等）。
- 支持多页文档；自动识别含财务表格的页面；无可提取财务内容的页面跳过并记录日志。

**OCR 与表格提取**
- 即使存在以下情况仍能提取表格：无边框、版面倾斜/旋转、格式不一致。
- 精确捕获无公式数值；正确解释负数、小数、百分数、货币符号。
- 表头、子表头与对应数据行正确关联。
- 针对原文件里面提取出来的表示金额的字段，如果提取出来没有货币符号，那就默认按美元展示并保存

#### 3.2b Excel / CSV 直接解析

**适用文档**：Excel（.xlsx）、CSV。

**解析与提取**
- 扫描 Excel 中所有 Sheet。
- 即使存在合并单元格、多表区、空行分隔，仍能抽取表格。
- 公式单元格取其计算值。
- 提取内容：行标签、列头、数值；保留币种、百分比、负数；尽力识别列头中的日期。
- 针对原文件里面提取出来的表示金额的字段，如果提取出来没有货币符号，那就默认按美元展示并保存
**表类型与报告期识别（启发式）**
- 按 Sheet/表名、行标签模式、结构线索进行分类；允许误判并标记待审核。
- 报告期识别：行标签/列头 、Table名、Sheet 名 、文件名（兜底）。
- 若无法明确分类，同样不抽取可映射到 LG 指标的科目。

**边际用例**
如果某种文档类型无法依据既定规则进行明确归类，则意味着未能提取出任何财务科目，从而无法将其映射至 LG 所支持的指标。

---

### 3.3 AI 辅助账户映射（Step 3，自动后台)-Stepper中属于Data Mapping步骤

**执行时机**：数据提取（OCR 或 Excel）完成后自动执行，无独立用户步骤。

**映射产物**：每个被抽取的行项均生成一个建议 LG 科目。

**支持的 LG 标准科目(排序也按照下面的顺序）**
- P&L
  - Gross Revenue
  - COGS
  - S&M Expenses
  - S&M Payroll
  - R&D Expenses
  - R&D Payroll
  - G&A Expenses
  - G&A Payroll
  - Capitalized R&D (Monthly)

- Balance Sheet
  - Cash
  - Accounts Receivable
  - Other Assets
  - Accounts Payable
  - Long-Term Debt
  - Other Liabilities
 
- source account(mapped section LG指标下面的以及unmapped里面的)就按字母升序排列。没有source account名字的排序不做要求，但是用户补充上名字之后，要执行排序规则。

**映射规则（语义级 + AI）**
- 下列关键词是语义指南，AI以自然语言理解进行匹配，不做严格字面匹配；即使措辞不完全一致，只要语义相符即可匹配。
- AI 须考虑源文档中的父子层级：父账目的类别语境作用于子账目。示例：父账目 "R&D" 下的子项 "Wages" → 映射为 **R&D Payroll**，而非 G&A Payroll。
- 若规则层面匹配不到，AI 以独立语义推理从支持列表中选一个最合适的 LG 科目。结合它的table的数据类型，报表类型，父子级关系以及该字段本身去推理
- 若推理后仍无法确定，标记为 Unmapped，并在 Side-by-Side Review 的 Unmapped Accounts 区域呈现。

**各类别关键词（摘要）**
- **Gross Revenue**：`sales, revenue, income, fees, subscriptions, gross receipts`。特殊情况：若标签含 `refund / returns / contra` → Revenue Contra （收入抵减科目/反向收入账目）记录为负值，map到Gross Revenue指标。是指在会计中用于减少总销售收入的科目，它的本质是一个金额与正常收入账目相反（借方余额）的账目，主要用来记录退货、折让或折扣，从而计算出企业的净销售额。

- **COGS**：`cogs, cost of goods, materials, inventory, supplies used, direct labor, hosting, infrastructure, cloud, server, bandwidth, third-party, api, support`。

- **S&M Expenses**：
 - Marketing and Advertising: `marketing, advertising, ads, promotion, campaign, digital marketing, seo, sem, ppc, social media, brand, branding, public relations, pr, media`；
 - Sales:`sales, commission(s), sales commission, sales expense, business development, bd, customer acquisition, lead generation`；
 - Customer and Channel Costs:`customer success, customer support, merchant fees, payment processing fees, referral fees`；
 - Events and Outreach:`trade show, conference, event, sponsorship`。

- **R&D Expenses**：`research, development, r&d, r and d, product development, engineering, software development, technical development, developer, engineering salaries, technical consulting, product design, ux research, cloud hosting, aws, azure, gcp, development tools, software licenses, testing, qa, quality assurance, devops, infrastructure engineering`。

- **G&A Expenses**：
 - Overhead:`general and administrative, g&a, overhead, corporate expense, office expense`；
 - Facilities:`rent, lease, utilities, office supplies, internet, phone, equipment`；
 - Professional Services:`legal, legal fees, accounting, audit, consulting, professional services`；
 - Admin:`hr, human resources, recruiting, insurance, licenses, permits`。

- **Payroll** `wages, salary, payroll, compensation, benefits, payroll taxes` 如果 AI 无法确定如何将分配至特定的薪资类别，则默认归入“一般及行政费用”（G&A），并在source account和LG account以alert icon标记以供用户复核。

- **Cash**：`cash, bank, checking, savings, cash equivalents, money market, treasury, short-term investments, marketable securities`。

- **Accounts Receivable**：`accounts receivable, a/r, receivables, trade receivables, unbilled revenue, contract asset`。

- **Capitalized R&D（Monthly）**：需同时出现 资本化信号 + R&D/开发信号 或 摊销信号。这三类的关键词如下:["capitalized", "capitalised", "capitalized r&d", "capitalized research", "capitalized development", "software development", "internal-use software", "capitalized engineering"]["amortization", "amortization of intangibles", "amortization of software", "amortized development costs", "intangible assets"].

- **Other Assets**：被识别为资产且未映射到 Cash / AR / Capitalized R&D (Monthly)。

- **Accounts Payable**：`accounts payable, a/p, payables, trade payables`。

- **Long Term Debt**：`long term debt, loan, note payable, term loan, debt, convertible note, venture debt, credit facility, line of credit, revolving`。

- **Other Liabilities**：被识别为负债且未映射到 Accounts Payable / Long Term Debt。

- **关键词重叠冲突（COGS 与 R&D）**： 某些术语（例如“cloud”、“hosting”、“AWS”）同时出现在 COGS（销售成本）和 R&D（研发费用）的关键词集中，从而引发潜在的分类冲突。当 AI 检测到此类歧义时：
默认归类为 COGS，在源条目及对应的 LG 指标旁显示警示图标，以供用户审阅

- **语义重复**：如果在同一月内，多个映射至同一 LG 指标的源账目被 AI 判定为语义重复（即含义部分或完全重叠，例如“桌椅费用”与“办公家具费用”），则会在每一条重复的源明细项以及对应的 LG 指标行上显示一个警示图标。若同义的unmapped的项移入mapped项，同样也显示警示图标。
 - 在上传文件后，如果用户对unmapped里面确实source account name的字段补充了name，AI不会再次去解析这个字段，即使在用户把这个字段map到LG指标后，系统不会知道这个source account是否和其他的source account存在语义重复。

**Source Account 合并规则**
<img width="609" height="249" alt="image" src="https://github.com/user-attachments/assets/6e30ed19-cf09-420a-8de5-823c99aa9956" />
<img width="545" height="306" alt="image" src="https://github.com/user-attachments/assets/2fc5c1d2-ab02-43ae-b17f-28168a9fe743" />

- 示例 2 — 不合并（时间重叠）：
  - Table A：Gross Revenue | P&L | Actual | 2024-01 ~ 2024-06
  - Table B：Gross Revenue | P&L | Actual | 2024-04 ~ 2024-09 → 2024-04 ~ 2024-06 时间段重叠 ❌ → 不合并

- 示例 3 — 不合并（数据类型不同）：
  - Table A：Gross Revenue | P&L | Actual | 2024-01 ~ 2024-06
  - Table B：Gross Revenue | P&L | Proforma | 2024-07 ~ 2024-12 → Actual ≠ Proforma ❌ → 不合并

- 示例 4 — 不合并（来自同一 Table）：
  - 同一 Table 内 Col 1：Gross Revenue | P&L | Actual | 2024-01
  - 同一 Table 内 Col 2：Gross Revenue | P&L | Actual | 2024-02 → 来自同一 Table ❌ → 不合并（同 Table 内数据不触发合并逻辑）

- 示例 5 — 不合并（指标名称不一致）：
  - Table A：Total Gross Revenue | P&L | Actual | 2024-01 ~ 2024-06
  - Table B：Gross Revenue | P&L | Actual | 2024-07 ~ 2024-12 → “Total Gross Revenue” ≠ “Gross Revenue”，名称不完全匹配 ❌ → 不合并

**持久化与可审计**
- 每条映射存储：建议的 LG 科目、时间戳、来源（AI suggested / User Override）。
- 若用户在 Side-by-Side Review 中修改科目：用户选择覆盖 AI 建议，供 3.7 学习使用；原 AI 建议作为审计历史保留。

**文件直接上传到Documentation板块的情况**

- 上传的这批文件有财务数据，但是AI没能map到LG的任何给定的指标上，所以只存在unmapped内容。这个时候在map页面点击next，会出现 Data Mapping Issues Detected窗口，在窗口再点击next，文件就应该直接上传Documentation板块，出来文件上传成功的那个窗口。
- 冲突只对比Actuals数据，预测数据不进行冲突对比。若一批数据只有预测数据，则直接提交文件至Documentation模块，不走冲突检测流程，Mapping Summary页面的按钮名称为Confirm and write to LG
- 若有实际数据，但无冲突，则直接提交文件至Documentation模块，不走冲突检测流程，Mapping Summary页面的按钮名称为Confirm and write to LG
- 若该批文件没有任何可用数据，右面版提示 No mapped data
  No mapped amount data was extracted from this file, so nothing can be mapped. Try uploading a clearer file or a different file format.
  - 点击Next，弹出Files Uploaded Successfully弹框，显示No financial accounts extracted. [amount] file(s) have been uploaded to the Imported Statements folder in Documentation.该批文件直接提交到Documentation板块，可点击close按钮关闭弹框，或点击Go to Documentation按钮跳转到All Documentation页面，文件夹提前建好，命名为Imported Statements
- Documentation页面的categoty为Benchmark Report
- 有公司文件夹访问权限的用户，将对其中的文件拥有全部权限（包括下载、删除和共享）。用户不可手动将文件上传至该文件夹。

---

### 3.4 Side-by-Side 审核与内联编辑-Stepper中属于Data Mapping步骤

呈现左右分屏，供用户在写入前核对、修正抽取数据与映射结果。左屏显示loding circle，解析过程中左右屏均显示灰色。若替换文件或重新上传，同样显示loading circle且左右屏显示灰色。
- 若有提取失败的文件，则在解析完成后显示报错弹窗：File Processing Errors
The following files could not be processed. You can re-upload each file, or discard them to continue.
 [file name] 
 [file name] 
 [file name] (有几个文件罗列几个）
- 按钮：
- Re-upload(关闭弹窗，打开本地文件夹，可以重新选择文件上传，若二次上传时，第二批与第一批加起来超过100MB，则第二批整批不予上传）
- Discard Problem Files（关闭弹窗，回到解析页面,若本批文档全部无法解析，则回到financial statement页面）
- ✖（关闭弹窗，回到解析页面,若本批文档全部无法解析，则回到financial statement页面）

**左面板 — 源文档浏览器**
- 顶部：文件选择下拉，若有多个文件，可切换文件或选择 "All Files" ，默认显示"All Files"，左面板显示文件列表。
  - Excel 多 Sheet：下拉下方显示 Sheet Tab 导航。
  - PDF：显示翻页控件。- 点击右上角Cancel按钮，会出Cancel Data Mapping?确认弹框，可点击Cancel data mapping回到Financial Entry页面,若点击Continue data mapping,保持在本页不动。
  - All: 显示文件列表
- 特殊情况：TIFF：浏览器原生不支持 TIFF 显示，预览时把 TIFF 转 PNG/JPG，实际存储还是TIFF，文件下拉里显示PNG/JPG后缀

- 右上角处有选项可新增文件 / 替换与删除已上传文件，若文件下拉处选择的ALL选项，则仅显示新增选项。
- 有 Excel / CSV 时可切换 Tab。
- 底部：缩放控制条（PDF / 图片）。

**右面板 — 数据映射**
  
- 平台级 USD 显示开关不适用于该上传流程。
- 显示两个 Tab：**Actuals** 与 **Proforma**，默认显示规则：
  - 仅 Actuals 数据（P&L / Balance Sheet）→ 默认 Actuals。
  - 仅 Proforma 数据 → 默认 Proforma。
  - 同时包含 → 默认 Actuals。
  - 切换到所选文件无数据的 Tab → 显示空状态。
- Tab 下按当前所选文档类型 / 文件列出 LG 财务指标，与 Financial Entry 相同格式；右面板支持水平与垂直滚动。结构：
  - **Unmapped accounts**（位于 Actuals / Proforma Tab 上方,受actual/proforma tab控制）
    - AI 未能映射到任何 LG 指标的源账目。
    - 数据不完整的源账户：
      - 缺账目名 → 显示 "UNIDENTIFIED"，可编辑名称，编辑完后标签消失；
      - 缺值（未识别） → 显示 "NA"；
      - 缺日期 → 显示"No Date"，可从日历下拉选择器中选择开始月份，选择后该数据自动落到相应月份下，若一个account有多个数据，则选择开始月份后，从左到右第一个数据落到开始月份，后面月份依次累加，数据依次落到月份，直到最后一个数据
        - 特殊情况补充1：若解析后某字段数据为非连续月数据且另一字段数据缺日期，另一字段展示规则如下，先排列非连续月，其他缺日期数据从最后一个有日期的数据月后动态增加列，依次排列。例如，解析后，除一个字段外，其它字段都有日期，对应月份是25年2月，5月和8月。没日期的字段有8个月份的数据(可能有数值，也可能没数值为NA)，那这8个月份的数据，第一个数据放到2月那一列，然后往后排，5月和8月，8月之后没有现存的月份了，就动态增加列，9 月10月等，把这几个月的数据放下。
          - 页面提示：Non-consecutive months detected. The extracted data spans adiscontinuous range - please review column dates before submitting.
        - 特殊情况补充2：部分列有日期 — 以已知日期链式推算相邻月份。当 account 内至少有一列数据有明确年月时，以该已知日期为锚点，向左和向右逐列推算：
           - 紧邻左列 = 已知月份 − 1
           - 紧邻右列 = 已知月份 + 1
           - 可链式传递，不限于直接相邻列
           - 举例： <img width="614" height="165" alt="image" src="https://github.com/user-attachments/assets/73c4588f-90e2-482e-84b7-04533bd9cdbd" />
        -  特殊情况补充3：
           -  无日期列前后均有已知日期 — 以前方（左侧）月份为主
           - 某列无日期，且其左右紧邻列都有已知日期时，以左侧月份 + 1 为准，忽略右侧推算结果。此规则主要用于解决左右推算结果不一致的冲突。
           - 举例：<img width="633" height="591" alt="image" src="https://github.com/user-attachments/assets/b55caf78-7e3b-4896-992e-8e6040321b34" />
        - 特殊情况补充4：
           - 如果在这个页面，整批没有提取出财务数据或者没有mapped板块，右上角Next按钮就叫Confirm & Commit to LG。若没有mapped内容，那按钮叫这个名字，但是我给unmapped里面的一个字段map下来了，那这个按钮又会变成Next
      - 既缺名称又缺日期 → 首先显示“UNIDENTIFIED”。一旦用户填写了账目名称，即切换显示为“No Date”
      - 若No date项选择了日期后多出月份列，其他项无此月数值或因源数据中本来就无此月数据就显示"-"，不算数据缺失
    - 用户可为 UNIDENTIFIED 账目手动命名；命名不会触发自动映射，仍须手动指派 LG 指标。
    - 指派下拉中每个指标都包含Actuals和Forecast两种选择，Forecast显示紫色，下拉框上方可输入指标名称筛选
- 页面小提示：Click to assign this item to an LG Metric，该提示位于第一个可指派LG指标的账目名旁，提示用户可以点击匹配指标，用户做了第一个source account的map后就消失了。
- alert的tooltip：mapped section里面会有三种alert情况，鼠标悬停提示消息：
  - Unclear payroll type; defaulted to G&A Payroll. 
  - Keyword conflict between COGS and R&D Expenses; defaulted to COGS.
  - Duplicate or overlapping source accounts detected.
- 若一个指标涉及多种提示，tooltip里面就按那个字母升序展示就行，也就是
   - Duplicate or overlapping source accounts detected.
   - Keyword conflict between COGS and R&D Expenses; defaulted to COGS.
   - Unclear payroll type; defaulted to G&A Payroll.

  **内联编辑**
- 可编辑项：
  - **数值**：删除数值后默认回填 0，作为有效数据，编辑过的数值灰色背景显示
  - **科目指派**
   - 只有账目名的所有月份数据都非N/A时（“-”可以）指派下拉按钮才会出现
   - 数据不完整的账户行在补全前，无手动映射的下拉按钮，不能手动指派到LG指标，指派后该账目名下所有的月份（整行数据）数据都被指派到相应月份，非单元格颗粒度。 指标名称，月份，数值必须全部完整，才会显示指派下拉按钮。
- 编辑值实时替换提取值
- 源账目名称非空即锁定；若为空可补充，保存后不可更改
- 下方已匹配的项也可编辑数值，也可重新指派指标（包括Actuals和Forecast）,也可指派为unmapped，回到unmapped板块
- map页面源字段展示：最多两行展示，如果仍展示不全，用...示意
  
**特殊情况** 
- 若该批文件只包含一种数据类型，如只有Actuals数据或者只有Proforma数据，则右屏其对应的tab应为空白页，显示 No financial accounts found for this data type 。
  
  - **LG 科目**
  - **底层源行项**
    - 显示最细粒度行项名；支持多币种并原样显示。总计性的行项不进入匹配流程，如total expenses,只提取其最细颗粒度子项，total expenses本身不提取。
    - 若LG指标下只有一个源账目，则直接显示数值，数值可编辑
    - 同一 LG 指标多个源账目 → 行可展开，指标名旁显示账目数，源账目数值可编辑，LG指标数值为下面源账目的合计金额，合计金额不可编辑。
      - 若 LG 指标合计因币种不一致或数据类型冲突（如货币指标下出现百分比）而无法计算 → 默认显示 "-"，不写入 LG；冲突解决不在本需求范围内，由其他 ticket 处理。
    - 同一时间期内映射到同一 LG 指标的多个源账目，若 AI 判定语义部分或完全重复（如 "desk and chair expenses" 与 "office furniture expenses"），在每个重复源行项与对应 LG 行上显示告警图标。
    - 用户可将源行项改映射到LG两种类型的任意一个指标。
- 若提取数据为非连续月，会有消息提示，
- 该面板可左右滑动，首列固定

**左右面板联动**
- 左侧选文件 → 右侧同步展示该文件抽取数据。
- 多文件时左侧下拉出现 "All Files"，选中后右侧展示合并数据。
- 切换右侧 Actuals / Proforma Tab 不影响左侧；左侧始终反映当前选中文件，与 Tab 无关。
- 左右面板比例可调，默认50%；提供图标隐藏左面板。


**返回与继续**
- 用户可确认已审核数据。
- 用户可拒绝并重新上传 / 上传新文件。
- 确认后进入写入schema步骤，如果没有未匹配的源账目，则直接进入mapping summary页面。
  - 如果存在Mismatched 或 Unmapped accounts 时，点击右上角Next按钮，尝试进入下一步，会弹出确认弹窗，告知"Unmapped Accounts 组的数据不会被写入 LG"，须显式确认。
 - 内容：Data Mapping Issues Detected:
        [50] fields with mismatched LG metric mappings （解析后未匹配对的账目源的数量（也就是初始时匹配了但未匹配对，又进行了手动匹配）+ unmapped中人工匹配到mapped板块的账户源数量）
        [15] unmapped accounts that will not be written to Looking Glass（人工审核后仍未匹配的账目源数量）
        Any unmapped data will not be saved. Would you like to continue?
  - Continue to Next Step按钮：点击进入下一步
  - Go Back按钮：点击回到mapping页面
  - 若不存在未匹配的项，则“[15] unmapped accounts that will not be written to Looking Glass Any unmapped data will not be saved. Would you like to continue?”不显示
- 点击右上角Cancel按钮，会出Cancel Data Mapping?确认弹框，可点击Cancel data mapping回到Financial Entry页面,若点击Continue data mapping,保持在本页不动。

---

### 3.5 写入 LG Schema（Step 5）-Stepper中属于Verify and Submit

**前置条件**
- 只有mapped section中非“-”的项才会进入写入流程。
- 平台级 USD 显示开关不适用于该流程。

**Verify Data 摘要页**
- 冲突检测前显示摘要：
   - Mapping Summary
   Please review the mapped data. Before being submitted, the system will verify that there's no overlapping information
   本次提交的源文件总数、映射类型（Actuals / Proforma）数量、映射科目数量。
   - 展示源文件列表，包括文件名称，文件大小，文件中已匹配的源账目数量
- 用户点击 "Previous Step" 回到 Data Mapping页面
- 用户点击 "Start Verification" 触发校验。
- 加载时显示loading circle。

**既有数据冲突检测与用户抉择**
- 按公司、LG 指标、报告期（月+年）维度比对；冲突校验作为后台任务进行，按目标 LG 指标与月份的存储币种进行比较。
- 仅当目标月份有值、且该值不同于映射合计时，才视为冲突。
- 冲突页面只显示Actuals有冲突的数据；预测数据则直接生成新committed forecast版本，Committed Forecast history 页面的Source 显示Import Statements,User为本次上传文件的用户，若该用户后期被删除了，系统应保存留痕该上传人信息，以免字段显示错误
- 冲突页面与 Financial Entry 相同格式展示：列为报告期、行为 LG 指标；冲突单元格字体红色。
- 若上传数据与LG数据的货币不同，则统一转换为LG货币对比，若选择上传数据，存还是存原始货币和值
- 点击冲突有详情弹框：
   - 指标-Month Year
   - Radio 选项：MAPPED VALUE（默认选中），LG VALUE；
   - Notes 必填，详见3.6，若未填写note就点击Next,Note文本框报错：A note is required before continuing.
   - ✖按钮，该popup只能通过点击该关闭按钮关闭
   - Next 按钮/ Save 按钮
- 冲突弹框中所有内容均填完， Next按钮才激活，冲突解决后点击next 按钮，冲突数值变绿色，自动打开下一个冲突的popup，最后一个冲突popup 按钮为Save,跳转顺序为同一个指标从左到右，一个指标完成后跳下一个指标，依旧从左到右。
- 用户点击 "Previous Step" 或右上方“Previous”按钮 回到Verify Data 摘要页

**覆盖与跳过**
- 选择Mapped Value：新数据替换选定期次与指标的当前版本；原值保留为历史版本。
- 选择LG Value：LG 数据不变；被跳过的指标不写入；流程继续处理其余满足前置条件的指标 / 文档。
- 若目标指标/月份在 LG 为空：自动写入。
- 若 LG 已有数据且与当前值一致：不触发新写入。
- 若无任何冲突则跳过这一步，直接到提交成功页面

**返回与提交**
- 点击Previous Step回到Verify Data页面
- 点击Confirm & Submit to LG按钮提交数据，跳转到Benchmarking页面，弹出弹窗
- 提交成功弹窗:
  - 提示信息：Data Submitted Successfully
 The following data has been submitted to [company name]:
 [amount] Source Files, [amount]Data Types Updated, [amount]Mapped Accounts
  - Close按钮：点击关闭弹窗

**特殊情况**
- 回到上一步的操作：返回上一步过程中，若上下步都未做改变，则已修改/编辑的数据或已解决的冲突都保存，上下步来回切换时展示内容不变
- 在冲突页面返回到mapping页面时，在mapping页面的mapped板块做了改动，点击Next到mapping summary页面，提示Your mapping changes have been applied. Please review the updated verification results.继续点击start verification,判断对冲突页面数据是否有影响，有变化的展示数据，没变化的不变还是展示用户之前解决的冲突数据。如果此时再回到mapping summary页面，提示消息已经消失。
  - 例如：在解决冲突页面已经解决了部分冲突，回到上一步mapping页面，修改了一些数据，这部分数据有已解决的冲突，则回到冲突页面时要重新检测展示

**Schema 完整性与错误处理**
- 所有数据须通过 LG Schema 校验后方可写入。
- Schema 校验失败：终止写入、显示清晰错误、将用户带回相关审核步骤并高亮错误。
- 不允许部分写入：已映射数据的写入整体成功或整体失败。

**审计与版本**
- 每次写入尝试记录：时间戳、用户身份、源文档、报告期、文档类型、采取的动作（written / overwritten / skipped）。
- 被覆盖的数据保留历史版本，便于审计。

**写入后行为**
- 已写入数据立即反映至：Financial Entry 页、Committed Forecast 页、下游 normalization 与 benchmarking 流程。
- 不论是否从中抽取到财务科目，上传的源文档都会出现在 Company Documents 页 "Imported Statements" 文件夹下，有该公司权限的人都可查看。
- 新closed month触发的邮件通知须正常运行。
- 显示清晰的成功提示。
- 用户随后进入 Benchmarking Page

---

### 3.6 数据校验期的备注字段（冲突解决备注）-Stepper中属于Verify and Submit

**使用场景**：写入步骤的冲突解决阶段。当历史已关期财务值被修改，需捕获修改原因以便审计。

**备注字段规则**
- 在冲突解决步骤中，每个冲突数据值旁提供一个必填的手动输入备注字段（free-form，上限 2000 字符，超出2000不能继续输入）。
- 无论用户选择何种解决方案（保留已有 / 采用上传值或手动覆盖），备注字段均可用。

**备注可见性与查看**
- 若Note页面无数据，显示No Data
- 备注作为上传事件的一部分存储于 financial statement 模块内。
- Financial Entry 页与 Committed Forecast 页显示 Note 按钮，点击进入备注列表页，按数据映射过程的时间顺序展示：
  - 表头：Data Mapping Time Stamp（UTC）、Metric、Financial Month、LG Value、Mapped Value、Data Source（"Mapped" / "Manually Entered"）、Note Content。
  - Select Metric下拉（包含列表所含有LG的Metric)、月历选择器（可选择年月筛选数据），这两个filter都有search bar
  - 超长备注截断显示（最多两行），提供 "See More" 打开弹窗查看完整内容，仅 "X" 或 "Close" 可关闭,若内容过多，弹窗内显示竖向滚动条。
- 分页与导航：
  - 显示总数与当前范围（如 `1 - 10 of 192 items`）。
  - 页码直选、上/下一页箭头、省略号跳转。
  - 每页行数下拉（10/页、20/页等），默认 10。
- 面包屑：例如：`Financial Entry > Data Mapping Notes`，可返回上一模块。

**流程影响**：备注功能集成至冲突解决步骤，不影响其他上传流程。

**可审计性**
- 备注与上传事件、已解决差异保持关联以便后续查阅。
- 上传最终确认后备注为只读。

---

### 3.7 系统学习与持续改进

**反馈捕获**
- Side-by-Side Review 中用户的所有决策（approve / override / manual mapping）均被记录为 AI 训练信号。

**增量学习**
- **公司级**：实时。用户每次保存映射修正，该公司的 Company Mapping History 随之更新，并立即影响该公司后续的映射动作与建议。
- **核心引擎级**：全局。由通用映射规则与关键词集合的变化触发，应用于所有客户。

**新文档识别**：系统能识别此前未见过的版式与科目类型，并基于历史学习给出映射建议。

**向后兼容**：AI 模型更新不得使既有映射失效或对已处理文档引入错误。

**审计与版本追踪**（两条独立版本线，写入每条映射结果）
- **Core Engine Version**：追踪通用规则与关键词变更，全局共享。
- **Company Mapping History ID**：追踪该公司用户确认的映射修正；用户每次保存修正即更新。

**补充**
- 本次记住内容不作用于当次
- 只有全部完成该流程才会储存学习内容，若流程中退出，如在解决冲突时退出，则mapping中记住的规则不保存
---

