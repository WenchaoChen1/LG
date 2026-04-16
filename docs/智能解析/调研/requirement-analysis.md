# EPIC: Manual Uploads with OCR — 需求理解与分析

> **Asana EPIC**: [Manual Uploads with OCR](https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1210456521366357)
> **Asana GID**: 1210456521366357
> **所属项目**: LG Roadmap → Now (1-3 Months)
> **截止日期**: 2026-05-29
> **LG Tag**: AI Integration
> **创建日期**: 2026-04-16（本文档）

---

## 1. EPIC 概述

### 1.1 一句话描述

让用户无需集成 QuickBooks 等系统，直接上传 PDF/Excel/图片等财务文件，系统通过 OCR + AI 自动提取、分类、映射财务数据，用户在线审核确认后写入 Looking Glass 数据库。

### 1.2 EPIC 原始描述

**Feature Summary**

Users can upload PDFs or spreadsheets; system parses them using OCR and extracts financials.

**Business/User Needs**

- The business need to expand the addressable market to non-integrated companies.
- The business needs to reduce friction for onboarding early-stage startups.
- Users want to obtain insights easily from their raw files without integrations.
- Users want that non-technical users can participate fully.

**Technical Considerations**

- Use OCR engine (using eSapiens) + rule-based validators.
- Build human-in-the-loop correction workflow.
- Manage file security, validation status, and traceability.

**Product Impact**

- Critical for onboarding flexibility.
- Adds complexity to QA and error handling.

---

## 2. 业务目标

| 目标 | 说明 | 优先级 |
|------|------|--------|
| 扩大可服务市场 | 覆盖没有 QuickBooks 等集成的公司，扩大 addressable market | 核心 |
| 降低入驻门槛 | 早期创业公司无需技术集成即可使用 LG | 核心 |
| 非技术用户参与 | 上传原始文件即可获取财务洞察，无需理解数据格式 | 重要 |
| 快速获取洞察 | 用户从上传到看到 Benchmark 对比，全流程自动化 | 重要 |

---

## 3. 核心工作流（6 步 Pipeline）

```
① 上传文件 → ② 数据提取(OCR/Excel) → ③ AI 账户映射 → ④ 并排审核编辑 → ⑤ 写入 LG → ⑥ 系统持续学习
```

### 3.1 流程详解

| 步骤 | 用户操作 | 系统行为 | 对应 Story |
|------|----------|----------|------------|
| 1. 上传 | 拖拽或选择文件 | 校验格式/大小，入队 | Story #1 |
| 2. 提取 | 无（等待） | OCR/Excel 解析，提取表格结构 | Story #2, #3 |
| 3. 映射 | 无（自动） | AI 将行项映射到 LG 标准分类 | Story #4 |
| 4. 审核 | 查看、编辑、确认 | 并排展示原始文档和提取数据 | Story #5 |
| 5. 写入 | 确认提交 | 冲突检测 → 写入数据库 | Story #6, #7 |
| 6. 学习 | 无（自动） | 保存用户修正作为 AI 训练信号 | Story #8 |

---

## 4. 子任务详情

### 4.1 Story #1: Allow Users to upload a financial document (PDF/XLSX)

- **Asana GID**: 1210477091808535
- **负责人**: Jesús H Peralta
- **状态**: Ready for Design

**核心需求:**

- 支持格式: PDF（扫描或数字）、Excel (.xlsx/.xls)、CSV、图片（JPG/JPEG/PNG/TIFF）
- 上传方式: 拖拽（桌面）+ 文件选择器（桌面+移动端）
- 文件限制: 单文件 ≤ 20MB，批量 ≤ 100MB
- 状态追踪: Pending → Uploading（进度%） → Completed → Error
- 权限: Company Admin/User 上传本公司；Portfolio Admin 上传所有有权限公司
- 队列管理: 可移除、可重试、可追加

**上传后自动进入提取 Pipeline（Step 2）。**

### 4.2 Story #2: Extraction of Financial Data - AI + OCR

- **Asana GID**: 1210477091808537
- **负责人**: Jesús H Peralta
- **状态**: Ready for Design

**核心需求:**

- 适用文件: 扫描 PDF、图片格式
- OCR 引擎: eSapiens
- 支持: 多页文档、无边框表格、倾斜/旋转布局
- 数值识别: 负数、小数、百分比、货币符号
- 文档类型识别: P&L / Balance Sheet / Cash Flow / Proforma / Misc
- 识别规则:
  - Sheet name 关键词（P&L/Income/Profit → P&L，Balance/Assets → BS，Cash Flow → CF）
  - Row label 模式（Revenue/COGS/EBITDA → P&L 指标；Assets/Liabilities/Equity → BS 指标）
  - 结构线索（Assets = Liabilities + Equity → BS；有期初/期末现金 → CF）
  - **兜底**: 无法分类 → "Financial Summary / Misc"，标记用户确认
- 报告周期推断: 列头 → Sheet 名 → 表格标题 → 文件名（依次降级）

### 4.3 Story #3: Extraction of Financial Data - Excel

- **Asana GID**: 1212280100704847
- **负责人**: Jesús H Peralta
- **状态**: Ready for Design

**核心需求:**

- 适用文件: Excel (.xlsx)、CSV
- 直接解析（不走 OCR）
- 支持: 合并单元格、多 section、空行分隔、公式单元格（取计算值）
- 输出格式与 OCR 提取完全一致（统一下游处理）
- 文档类型和报告周期的识别逻辑同 Story #2

### 4.4 Story #4: Add AI-Assisted Account Mapping Suggestions

- **Asana GID**: 1211824829276744
- **负责人**: Liang Chunru
- **状态**: Storytelling

**核心需求:**

自动将提取的行项映射到 LG 标准财务分类（16 类）:

| P&L 分类 | Balance Sheet 分类 |
|----------|-------------------|
| Revenue | Cash |
| COGS | Accounts Receivable |
| S&M Expenses | R&D Capitalized |
| R&D Expenses | Other Assets |
| G&A Expenses | Accounts Payable |
| S&M Payroll | Long Term Debt |
| R&D Payroll | Other Liabilities |
| G&A Payroll | |
| Other Operating Expenses | |

**映射规则（已由财务 SME Nico Carlson 确认）:**

- **Revenue**: `sales`, `revenue`, `income`, `fees`, `subscriptions`, `gross receipts`
  - 特殊: `refund`/`returns`/`contra` → Revenue Contra（负值）
- **COGS**: `cogs`, `cost of goods`, `materials`, `inventory`, `direct labor`, `hosting`*, `cloud`*, `server`*
  - *注: `hosting`/`cloud`/`server` 在 SaaS 公司为 COGS，非 SaaS 为 R&D
- **S&M Expenses**: `marketing`, `advertising`, `commission`, `customer acquisition`, `trade show` 等
- **R&D Expenses**: `research`, `development`, `engineering`, `product development`, `devops` 等
- **G&A Expenses**: `g&a`, `overhead`, `rent`, `legal`, `accounting`, `insurance`, `hr` 等
- **Payroll 三分类**:
  - S&M Payroll: Payroll 关键词 + `sales`/`marketing` 上下文
  - R&D Payroll: Payroll 关键词 + `r&d`/`engineering` 上下文
  - G&A Payroll: **兜底** — 无法判断部门时默认此项，标记 LOW confidence
- **OOE**: Other Income + Other Expense，同周期互抵（expense - income）
- **R&D Capitalized**: 需双重信号 — (资本化 + R&D 上下文) 或 (摊销信号)
  - 摊销关键词: `amortization`, `amortization of intangibles`, `amortization of software`
- **Other Assets / Other Liabilities**: 被识别为资产/负债但不属于上述具体分类的兜底

**数据持久化:**

每条映射记录: 建议分类 + 时间戳 + 来源（AI suggested / User Override）

### 4.5 Story #5: Side-by-Side Review & Inline Editing (OCR + Excel)

- **Asana GID**: 1210477091808539
- **负责人**: Jesús H Peralta
- **状态**: Ready for Design

**核心需求:**

- **左侧面板**: 原始文档（PDF 带翻页 / Excel sheet 预览）
- **右侧面板**: 提取数据，两种视图可切换:
  - **Raw View**: 原始提取行项
  - **Standardized View**: 映射到 LG 分类后的视图（可展开查看原始行项）
- 内联编辑: 数值、行标签、分类（Standardized View 中）
- 选中右侧行 → 左侧高亮对应源位置
- 切换视图模式不丢失用户编辑
- 系统追踪: 原始提取值 + 用户编辑值
- 用户可确认（进入写入）或拒绝（重新上传）
- Mobile Responsive（可折叠面板）

### 4.6 Story #6: Write data to LG Schema

- **Asana GID**: 1212365913414040
- **负责人**: Jesús H Peralta
- **状态**: Ready for Design

**核心需求:**

- **写入前提**: 所有行项已审核、已映射、元数据完整
- **冲突检测**: 写入前检查是否已有同 company + document_type + data_classification + reporting_period 的数据
- **冲突处理选项**:
  - **Overwrite**: 新数据替换旧版本，旧版本保留为历史记录
  - **Skip**: 跳过冲突项，处理其他非冲突数据
  - **Cancel**: 不写入任何数据，返回审核
- **写入后行为**:
  - 数据立即反映到: Financial Statement 页面 + Committed Forecast 页面 + 下游 normalization/benchmarking
  - 原始文件归档到 Company Documents 页面
  - 显示成功确认，展示 Benchmark Info Page
- **审计日志**: 每次写入记录时间戳、用户、源文档、周期、类型、操作（written/overwritten/skipped/cancelled）
- **版本控制**: 被覆盖的数据保留历史版本

### 4.7 Story #7: Add Note Field to Importing During Data Validation

- **Asana GID**: 1213752333534662
- **负责人**: Jesús H Peralta
- **状态**: Ready for Design

**核心需求:**

- 在冲突解决步骤中为每个冲突值提供**可选 Note 字段**
- 用途: 记录历史数据变更原因（如修订的财务报表、外部更正）
- 限制: 最多 2000 字符，非必填
- 存储: 关联到上传事件和冲突解决记录
- 可见性: Financial Statements 模块可查看（需设计 UI 展示位置）
- 提交后只读

**来源**: Dougal 在审核 Lovable 原型时提出的新需求

### 4.8 Story #8: System Learning and Continuous Improvement

- **Asana GID**: 1211900347046564
- **负责人**: Liang Chunru
- **状态**: Storytelling

**核心需求:**

- 捕获用户在审核中的所有操作（approve/override/manual mapping）作为 AI 训练信号
- 增量学习: 定期用用户反馈更新 AI 模型
- 新文档识别: 识别之前未见过的文档布局和账户模式
- 向后兼容: 模型更新不影响已处理文档
- 审计: 所有模型更新记录版本、时间戳、数据集

**实际讨论结论（评论中确认）:**

Liang Chunru 和 Karen Arnoldi 讨论后的务实方案:
- 保存用户修正过的映射作为"公司记忆"
- 未来上传时优先使用公司历史映射
- 双轨版本: Core Engine Version（通用规则） + Company Mapping History ID（公司记忆）

---

## 5. 关键评论与讨论摘要

### 5.1 Lovable 原型审核

**Liang Chunru (2026-03-17)** 提交了完整的 Lovable 原型，覆盖:

1. **文件上传**: "Import Statements" 按钮，支持 PDF/Excel/CSV/Image
2. **提取+编辑**: Split-view（原文件 vs 提取表格），按 Extracted Table 分组
   - 行 = Financial Accounts，列 = Time Periods (Months)
   - 可编辑: Table Name/Type/Currency/Accounts/Time Periods/Values
   - 空值默认 0，自动货币格式化
   - 支持 Remove Row / Remove Column 清除噪音
   - 双向滚动同步（源文档 ↔ 提取表格）
3. **硬验证**: 点击 "Next: Accounts Mapping" 时触发
   - 三要素必须完整: Account Name + Value + Month
   - 精确阻止提示（指明文件名和表 ID）
4. **账户映射**: Source-driven view，隐藏无匹配的 LG 指标
   - 未映射账户列在 "Unmapped" 区域，必须手动映射才能提交
5. **冲突解决+提交**: 跨表 + 对比已有 LG 数据，用户选择 Accept 来源

**Karen Arnoldi (2026-03-20)** 与 Dougal 审核后反馈:
> "Overall he seemed good with the look and the flow. He commented on the need for including an optional notes field in the data validation piece when data conflicts occur."
→ 由此创建了 Story #7

### 5.2 OCR 提取规则讨论

**Liang Chunru (2025-12-15)** 提出 5 个关键问题:

1. 系统无法识别的字段如何展示给用户审核？
2. 需要具体的文档类型识别规则
3. 需要提取置信度规则
4. 审核+内联编辑占工作量 70%，建议拆分为独立 story
5. "Hover 显示 OCR 原始文本和边界框" 是否必要？

**Karen Arnoldi 回复:**
1. "Cannot confidently translate" 指系统能读取数据但不确定含义 → 提取并展示，但标记审核原因
2. 同意基于启发式规则
3. 同意基于规则的阈值
4. **同意拆分** — 审核编辑移到独立 story（即 Story #5）
5. 同意降级 — 只做定位到源页面，不做精确边界框

### 5.3 文档类型识别规则讨论

**Liang Chunru (2026-01-12)** 提问:
- 规则是按优先级还是组合要求？
- 单个关键词能否触发确认？
- Cash Flow 期初/期末余额是否为强制条件？

**Karen Arnoldi 回复:**
- **基于置信度评分，不是严格优先级或全通过要求**
- 单个关键词 = 低信号；多个相关关键词 = 强信号；关键词+结构 = 最高置信度
- 期初/期末余额是强信号但非强制

**Liang Chunru (2026-03-04)** 提议简化:
> "Since the confidence-scoring rule is not yet implemented, I assume we will simplify the fallback: If a document type cannot be clearly categorized based on the defined rules, classify as 'Financial Summary / Misc'."

**Karen Arnoldi 同意** (2026-03-04)，并更新了需求描述。

### 5.4 AI 映射规则 — 财务 SME 确认

**Liang Chunru (2026-03-02)** 提出 4 个待确认问题:

1. Payroll 拆分: 单一 "Payroll Expenses" vs 三分类 (S&M/R&D/G&A)?
2. Other Operating Expenses 是否等同 Miscellaneous Operating Expenses?
3. Other Income / Expense 如何映射？
4. R&D Capitalized 的双重信号逻辑?

**Nico Carlson (2026-03-06)** 正式回复:

> 1. **Payroll 拆为 S&M/R&D/G&A 三类**。无法判断时默认 G&A，标记审核。
> 2. **OOE 就是 Miscellaneous Operating Expenses（计算指标）**。R&D Capitalized = Capitalized R&D (Monthly)。
> 3. **Other Income/Expense 均映射到 OOE**。同周期互抵 (expense - income)，负值表示 income 大于 expense。
> 4. **双重信号正确**，但要加 amortization 作为信号。关键词: "amortization", "amortization of intangibles", "amortization of software", "amortized development costs", "intangible assets"。

### 5.5 OOE 映射矛盾（未完全解决）

**Liang Chunru (2026-03-19)** 指出:
> "The issue regarding 'Miscellaneous Operating Expenses, now is a computed live metric' is still unresolved. Since this metric also appears in the Supported LG Categories, including it would mean it's no longer computed, creating a conflict with our existing logic."

**Karen Arnoldi (2026-03-19)** 回复:
> "I'm wondering why we have Misc OPEX as a supported LG category for the mapping. I thought it was OOE."

**Liang Chunru (2026-03-23)**:
> "I will remove the Misc OPEX from the supported LG category for now."

**状态: 暂时移除，但 Nico 尚未给出最终确认。这是一个 P0 风险点。**

### 5.6 AI 模型版本管理讨论

**Liang Chunru (2025-12-17)** 提出版本策略:

> "AI Model Version" is handled by two independent version streams:
> - **Core Engine Version** (Universal Rules): Tracks changes to general rules and keywords.
> - **Company Mapping History ID** (Learned Memory): Tracks changes by users to client-specific custom mappings.
> We log both IDs for every mapping result to ensure full auditability.

**Karen Arnoldi 回复**: 认同方向，具体细节在开发中迭代。

### 5.7 硬验证规则讨论

**Liang Chunru (2026-03-17)** 提出:
> "Should we mandate that every record must have three specific elements — Financial Account, Value, and Month — before moving forward?"

**Karen Arnoldi 回复**:
> "I agree with you. And actually, providing the ability to remove rows or columns is giving flexibility to the user... way more friendly to allow the user to proceed instead of complete prevention."

**结论**: 三要素 (Account Name / Value / Month) 为硬验证，但用户可通过删除噪音行/列来清理数据后通过验证。

---

## 6. 需求合理性分析

### 6.1 合理的部分

| 方面 | 评价 |
|------|------|
| 业务定位 | 扩大非集成公司的可服务市场 — 真实的增长瓶颈 |
| 6 步 Pipeline | 逻辑闭环完整 |
| OCR 与 Excel 拆分 | 正确，解析逻辑完全不同，降低风险 |
| Human-in-the-loop | 财务数据不能全自动，并排审核是必须的 |
| 冲突检测 + Overwrite/Skip/Cancel | 防止误覆盖历史数据，审计合规必备 |

### 6.2 有问题的地方

#### P0 阻塞

**1. OOE 映射矛盾未解**
- OOE 在 LG 中是计算指标（computed live metric），不能直接写入
- 但 Other Income/Expense 的映射规则要求映射到 OOE
- Liang 暂时移除了 Misc OPEX，但 Nico 未给最终确认
- **风险**: 开发时不知道 Other Income/Expense 写入哪个字段

**2. AI 关键词优先级缺失**
- `hosting`, `cloud`, `server` 同时出现在 COGS 和 R&D 的关键词列表中
- 没有定义多分类冲突时的优先级规则
- **风险**: 同一行项可能被同时匹配到多个分类

#### P1 高风险

**3. 多类型混合文档切分规则缺失**
- 需求说 "Multi-page financial packets may contain multiple document types"
- 但没有定义如何自动切分（哪一页开始是新报表？）
- 也没有处理跨页表格的规则

**4. 错误恢复机制缺失**
- OCR 提取失败后用户能做什么？（只能重传？）
- 写入 LG 失败后之前的审核编辑是否保留？
- 用户审核到一半关浏览器，进度是否保存？

**5. 数据校验规则太弱**
- 硬验证只要求三要素，但缺少:
  - Balance Sheet 不平衡告警
  - P&L 加总错误告警
  - 重复报告周期检测
  - 币种冲突检测

#### P2 应改进

**6. System Learning story 过于空泛**
- "Incremental Learning: AI model is updated periodically" — 什么周期？谁触发？
- "Backward Compatibility" — 怎么保证？无技术方案
- 实际上评论中已讨论出务实方案（公司记忆），但 story 描述远超此范围

**7. 安全/合规考虑不足**
- 没有文件安全扫描（恶意 PDF/Excel 宏）
- 没有 PII/敏感数据处理策略
- eSapiens OCR 的数据安全/驻留未确认
- 文件留存策略未定义

**8. 权限模型有漏洞**
- 谁能删除已上传文件？
- 谁能覆盖他人审核过的数据？
- Portfolio Admin 上传后 Company User 能否看到/编辑？
- 审计日志是否记录"代谁上传"？

#### P3 建议调整

**9. Mobile Responsive 范围过广**
- 并排审核在手机上不可用（320px 屏幕放不下）
- 财务表格 12+ 列在手机上横滑体验极差
- 建议: 上传功能做 Mobile，审核编辑做 Desktop Only

**10. 工作量与交付日期不匹配**
- 7 个子任务中 6 个的 due date 是 2026-04-16，但状态全是 Ready for Design / Storytelling
- EPIC 截止日 2026-05-29，但需求细化都没完成
- 多个任务在 On Hold ↔ Ready for Design 之间反复

---

## 7. 待确认问题清单

| # | 问题 | 提问对象 | 阻塞级别 |
|---|------|----------|----------|
| 1 | OOE 作为计算指标 vs 映射目标的矛盾 — Other Income/Expense 最终写入哪个字段？ | Nico Carlson | **P0** |
| 2 | `hosting/cloud/server` 默认归 COGS 还是 R&D？公司 industry 从哪获取？ | Karen Arnoldi | P1 |
| 3 | 多类型混合 PDF 是要求用户按报表分别上传，还是系统自动切分？ | Karen Arnoldi | P1 |
| 4 | eSapiens OCR 是 SaaS 还是 self-hosted？数据驻留合规要求？ | 技术团队 | P1 |
| 5 | 已上传文件的删除权限 — 谁能删？Portfolio Admin 上传后 Company User 能看到吗？ | Karen Arnoldi | P2 |
| 6 | Mobile 审核编辑页面是否改为 Desktop Only？ | Karen Arnoldi / Dougal | P2 |
| 7 | System Learning story 是否缩小范围为"公司级映射记忆"？ | Karen Arnoldi | P2 |

---

## 8. 团队成员与角色

| 成员 | 角色 | 主要工作 |
|------|------|----------|
| **Karen Arnoldi** | Product Owner | 需求编写、原型审核、优先级决策 |
| **Jesús H Peralta** | UI/UX Designer | Lovable 原型设计、UI 交互定义 |
| **Liang Chunru** | Tech Lead | 技术可行性分析、功能需求细化、原型评审 |
| **Nico Carlson** | Financial SME | 财务分类规则确认、映射逻辑审核 |
| **Dougal** | Business Stakeholder | 业务需求验收、最终审批 |
| **Víctor Juárez** | 初始创建者 | EPIC 创建和初始 story 拆分 |
| **Jacobo Vargas** | Project Manager | 日期调整、backlog 管理 |
| **wenchao** | Dev Team | T-Shirt Sizing、技术估算 |

---

## 9. 时间线

| 日期 | 事件 |
|------|------|
| 2025-06-03 | Víctor Juárez 创建 EPIC |
| 2025-06-05 | 子任务创建并加入 LG Backlog |
| 2025-10-16 | Karen Arnoldi 将 EPIC 移至 "Now (1-3 Months)" |
| 2025-11-03 ~ 2025-12-10 | Karen 编写各 story 的详细需求 |
| 2025-12-10 | 所有 story 标记 Requirements Complete，进入 Sizing |
| 2025-12-15 | Liang Chunru 完成 T-Shirt Sizing，提出多个技术问题 |
| 2026-01-09 | Karen 将 story 状态退回 Ready for Reqs（需补充细节） |
| 2026-01-12 ~ 2026-01-13 | Karen 回复 Liang 的技术问题，重新标记 Requirements Complete |
| 2026-01-30 | Karen 将 story 从 Prioritized 退回 Backlog（需进一步细化） |
| 2026-02-04 | Karen 更新需求描述（多轮迭代） |
| 2026-03-02 | Liang 提出 AI 映射规则的 4 个财务 SME 问题 |
| 2026-03-06 | Nico Carlson 正式回复映射规则确认 |
| 2026-03-16 | 所有 story 进入 Ready for Design，Jesús 开始 UI 设计 |
| 2026-03-17 | Liang 提交完整 Lovable 原型 |
| 2026-03-20 | Karen + Dougal 审核原型，提出 Note 字段需求 |
| 2026-04-02 | Jesús 更新 Lovable 原型，所有 story 标记 UI Complete |
| 2026-04-07 | Liang 提交 Lovable 评审意见 |
| 2026-04-09 | 多个 story 状态改为 On Hold |
| 2026-04-13 | story 状态恢复为 Ready for Design |

---

## 10. 相关文档

| 文档 | 路径 |
|------|------|
| 技术设计方案 | [docs/智能解析/technical-design.md](./technical-design.md) |
| Lovable 原型 | [Lovable Preview](https://preview--visual-link.lovable.app/) (需 token) |
| Lovable 编辑器 | [Lovable Dev](https://lovable.dev/projects/6dfa3c14-7c77-4565-9c1f-73999c9dcbc7) |
