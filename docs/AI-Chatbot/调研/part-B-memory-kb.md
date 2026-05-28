# 第 2 部分：Memory 与知识库类需求（Memory & Knowledge Base）

> 本部分包含 **12 个** Memory File 与 Knowledge Base 相关需求：
> - **Layer 1a Backend 共 8 个**（由旧 LG-1329 拆分）：1 个 Initialization + 1 个 Document Upload Processing + 6 个 Chat Extraction 子类别
> - **Layer 1b Backend 共 2 个**（由旧 LG-1330 拆分）
> - **Layer 2 共 2 个**：Ingestion / Management + Access for All Users
>
> 与 [Research LG-1385 _Layer 1b Chat Content - Company Association and Memory Binding Logic_](./part-A-foundation.md) 配套使用。
>
> **关键变更（vs 2026-05-12）**：抽取触发器由 _end-of-session_ → **real-time incremental at each message exchange, processing asynchronously**（采纳 wenchao 2026-05-15 建议，Karen 5/15 确认）。

---

## A. Layer 1a Backend — 公司 Memory File 后端（8 个 User Story，由旧 LG-1329 拆分）

> **拆分背景**：Liang Chunru 2026-05-18 评论指出 LG-1329 包含约 9 类抽取内容 + 初始化 + 文档上传共 11 类逻辑，过大无法在单 sprint 交付。建议按 source（初始化 / 文档上传 / 聊天抽取）+ 按 chat extraction 内容类别拆分。Karen 5/18 同意。
>
> 拆分结果如下：1 个 Initialization、1 个 Document Upload Processing、6 个 Chat Extraction 子类别（Founder Profile / Company Facts & Data Corrections / ICP / Competitive Landscape / Porter's Five Forces / Strategic Context & Challenges）。

### A.1 Layer 1a Backend - Initialization & Company Settings Seeding（LG-1390）

- **Asana ID**: 1214913562391185
- **状态**: Needs Sizing（Working Status = Not Started）
- **最近修改**: 2026-05-21
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214913562391185

#### 业务需求

本 Story 覆盖 **Layer 1a Memory File 的创建与初始播种**。Chatbot 首次为某家公司初始化时，系统必须自动创建该公司的 Layer 1a 存储，并以来自 Company Settings 的所有结构化数据填充：company name、description、business model、sector、industry、stage、URL 以及其他 LG profile 字段。这为 AI 从第一次对话起就提供有意义的基线认知，无需用户输入。

当 Company Settings 字段后续被更新时，Memory File 必须自动同步反映。

> 备注：当 consultative onboarding epic 引入时，若公司实体在 onboarding 阶段才创建（因为可能含 LG structured 字段之外的额外公司信息），Layer 1a 的初始化时机需要在 onboarding 工作流中处理。

#### 验收标准

- Chatbot 首次为某公司初始化时，系统自动为该公司创建 Layer 1a Memory File。
- 初始化时自动以全部 Company Settings 元数据填充：name / description / business model / sector / industry（写在 description 内）/ stage / URL / 其他结构化 profile 字段。
- **AI 在创建 Memory File 时是基于 profile 字段的"理解"（understanding）而非仅做字段存储**——例如，AI 应基于 URL "scrape" 或学习公司网站内容。
- 当任一 Company Settings 字段被用户更新时，对应 Layer 1a memory entry 自动更新。
- 用户**不需要任何配置**即可启用 Memory File——它自动运作。
- 架构需支持依赖 UI Story 所需的访问控制模型：Company Admin 对自家 Layer 1a 只读；Portfolio Manager 对访问范围内所有公司的 Layer 1a 只读。
- 注：consultative onboarding epic 引入后，需要在 onboarding 工作流中加入 Memory File 初始化逻辑。

#### UX 设计要点

- 本 Story 为后端与数据架构故事——范围内无面向用户的 UI。

#### 依赖与备注

- 是 Layer 1a 系列其他 7 个 Story（LG-1388 / LG-1391~1396）的**基础前置**——必须先有 Memory File 存储才能写入。
- 是 UI Story（LG-1333 Company User Memory File Access UI / LG-1336 Portfolio Manager Memory File Access UI）的依赖。
- consultative onboarding epic 引入后需要联动调整。

---

### A.2 Layer 1a Backend - Document Upload Processing（LG-1388）

- **Asana ID**: 1214913562391187
- **状态**: Needs Sizing（Working Status = Not Started）
- **最近修改**: 2026-05-21
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214913562391187

#### 业务需求

本 Story 覆盖**公司侧用户在聊天界面上传文档**之后的处理与 Layer 1a Memory File 的存储。文档上传后并行触发两个流程：

1. **RAG 索引**——使文档全文可被当前及未来会话动态检索。
2. **自动摘要写入 Layer 1a**——系统自动生成关于公司相关关键 learnings 的高层摘要，作为一条 Layer 1a memory entry 保存。

上传文档及其衍生内容**严格作用于该公司的 Layer 1a Memory File**，在任何情况下都不会流入 Layer 1b 或 GS Knowledge Base（Layer 2）。

#### 验收标准

- 当公司侧用户在 chat 中上传文档时，并行触发：
  - RAG 索引整份文档以便动态检索
  - 自动生成与公司相关的高层摘要并保存为 Layer 1a memory entry
- RAG 索引和 memory 摘要均严格限定于该公司的 Layer 1a。
- 文档内容在任何情况下都不流入 Layer 1b 或 Layer 2。
- RAG 索引在合理时间内完成——目标在典型文档大小下 **30 秒内**。
- 来自文档处理的 memory entry 存储时附带元数据：source type（document summary）、document name、timestamp。
- 失败的文档处理记录日志供排查，**不向用户暴露错误**——chatbot 在 memory 更新失败时仍正常工作。
- 文档上传通道由 **LG-1400 _Document Upload for Chat Analysis (Company Portal)_** 覆盖（用户层 UI 与 Java 上传通道）。

#### UX 设计要点

- 后端与数据架构故事——本范围内无 UI。

#### 依赖与备注

- 依赖 LG-1390（Initialization）已创建 Layer 1a 存储。
- 配套 LG-1400（Company Portal 上传 UI）。

---

### A.3 Layer 1a Backend - Chat Extraction: Company Facts & Data Corrections（LG-1391）

- **Asana ID**: 1214953638826103
- **状态**: Needs Sizing（Working Status = Not Started）
- **最近修改**: 2026-05-21
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214953638826103

#### 业务需求

本 Story 覆盖公司侧 chat 会话中**第一组**内容的实时增量抽取：

1. **Company Facts**——创始人在对话中讲到、但在 LG structured data（Company Settings、financial data、既有 memory entry）中没有对应字段的事实。例如：
   - "we just signed our first enterprise customer"（最近商业事件）
   - "we are the only provider focused on mid-market healthcare"（市场定位）
   - 团队规模 / 结构变更、最近融资 / 战略转向等
2. **Data Corrections**——用户指出 LG 中存储值不正确或过时的更正。例如 "that revenue figure for March is wrong, it should be $1.1M"。**Corrections 不触发对财务数据、Normalization Table、forecasts 或任何 LG 数据结构的更新**——它们仅作为 context 存储在 memory file 里，供 AI 在回答该数据点时引用。

#### 验收标准

**抽取触发器**：
- **实时增量**——每条 user message 与 AI response 的往返发生时立即评估。
- 抽取处理**异步执行，不阻塞 AI 回复**。
- 每次只评估**最近一次往返**，不重新处理全部历史。

**Company Facts 抽取**：
- 正确识别并抽取用户讲到的、但 LG structured data 中没有的公司事实。
- 抽取的 fact 作为 Layer 1a memory entry 存储，附 source type（chat extraction）+ timestamp。
- 通用资讯类问题、事务性交流、纯观点（不构成事实）正确排除。
- LG 已准确记录的内容**不重复抽取**。

**Data Corrections 抽取**：
- 正确识别用户在指出某个 LG 中已存的值不正确或过时。
- Corrections 存储为 Layer 1a memory entry，附 source type、timestamp、足以定位是哪个数据点 + 更正后的值。
- **存储 correction 不触发对 financial data / Normalization Table / forecasts / 其他 LG 数据结构的任何更新**。
- AI 在未来回答关于该数据点的问题时，能够引用该 correction（例如询问 March revenue 时，AI 可同时给出 LG 存值 + correction）。

**冲突处理**：
- 新抽取与既有 entry 冲突 / 实质性更新 → 既有 entry 更新到最新。
- 防止重复抽取已存信息。

**性能与错误处理**：
- 抽取失败仅记日志，不向用户暴露错误。
- 单次抽取失败不影响 chatbot 正常运作。

#### UX 设计要点

- 后端与数据架构故事——本范围内无 UI。

---

### A.4 Layer 1a Backend - Chat Extraction: ICP and Customer Profile（LG-1392）

- **Asana ID**: 1214953638826104
- **状态**: Needs Sizing（Working Status = Not Started）
- **最近修改**: 2026-05-21
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214953638826104

#### 业务需求

本 Story 覆盖**Ideal Customer Profile (ICP) 与客户相关上下文**的实时增量抽取。系统应**渐进式构建**ICP 画像，而不是要求创始人一次性提供完整定义。

随着创始人在对话中谈到客户、deals、churn、续约、go-to-market 方法，AI 抽取并积累相关信号，包括：
- 主 ICP 描述（行业 / 公司规模 / 角色 / 痛点）
- 多个 ICP 的区分
- 与特定客户分段相关的 churn 模式（作为 **strategic pattern** 存储，例如 "seasonal churn from SMB ICP"，而非个体客户名 / 事件）
- ICP 随时间演变 / 变化的上下文

#### 验收标准

**抽取触发器**：实时增量（同 LG-1391 规则）。

**ICP 抽取**：
- 正确识别主 ICP 描述（行业、公司规模、买家角色、产品解决的核心痛点）。
- 当创始人描述多个 ICP 时，每个独立存为 memory entry，附区分上下文。
- "ICP 在演变 / 变化" 类语句 → 更新既有 ICP entry 反映当前理解。
- 当对话中浮现时，抽取产品对每个 ICP 的价值（ROI 故事、关键 benefit、差异化点）。

**客户模式抽取**：
- 与特定客户分段或 ICP 相关的 churn 模式作为**strategic pattern** 抽取（如 "seasonal churn from SMB customers"、"enterprise ICP showing lower churn than expected"）。
- **明确排除**：个体客户名、具体 deal outcome、一次性客户事件。
- 客户成功模式（如 "enterprise customers consistently expand after 6 months"）在被提及时抽取。

**冲突处理**：
- 创始人指明 ICP 已变 → 更新现有 ICP entry 而非创建冲突副本。
- 最新 ICP 描述始终视为权威版本。

**性能与错误处理**：同 LG-1391。

#### UX 设计要点

- 后端与数据架构故事——本范围内无 UI。

---

### A.5 Layer 1a Backend - Chat Extraction: Competitive Landscape（LG-1393）

- **Asana ID**: 1214953638826105
- **状态**: Needs Sizing（Working Status = Not Started）
- **最近修改**: 2026-05-21
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214953638826105

#### 业务需求

本 Story 覆盖**竞争 landscape**信息的实时增量抽取。竞争信息随创始人在对话中自然提及竞争对手时（讨论赢单/丢单、自家 positioning、pricing 挑战、竞争位移建议）渐进式累积。系统抽取：
- 关键竞争对手名称
- 创始人对竞争对手相对于自家产品的强弱势刻画
- 竞争动态随时间的变化
- **Substitution threats**（非直接对手但客户会考虑的替代方案，作为独立类别）

> 存储时需明确"这是创始人视角"——不是客观市场评估。AI 在未来引用时应保留此归属。

#### 验收标准

**抽取触发器**：实时增量。

**竞争对手抽取**：
- 正确识别创始人提及的竞争对手名称。
- 每个对手抽取其相对强弱势上下文。
- 抽取竞争 positioning 语句（如 "we win on ease of use but lose on enterprise feature depth"）。
- 抽取竞争动态变化（如 "a new well-funded competitor entered the market last quarter"）。

**Substitution Threat 抽取**：
- 正确识别 substitution threats（非直接对手的替代方案，例如 "most of our prospects are currently using spreadsheets and internal tools"）。
- Substitution threats 与直接对手作为**独立类别**存储。

**完整性与更新**：
- 新信息与既有 entry 冲突或实质更新（如 "we actually now win deals against Competitor X more often than we lose"）→ 更新到最新。
- 存储与检索时附带"创始人视角"归属。

**性能与错误处理**：同 LG-1391。

#### UX 设计要点

- 后端与数据架构故事——本范围内无 UI。

---

### A.6 Layer 1a Backend - Chat Extraction: Porter's Five Forces Profile（LG-1394）

- **Asana ID**: 1214953638826106
- **状态**: Needs Sizing（Working Status = Not Started）
- **最近修改**: 2026-05-21
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214953638826106

#### 业务需求

本 Story 覆盖 **Porter's Five Forces** 信号的实时增量抽取，**渐进构建**每家公司的结构化竞争环境画像。

Porter's Five Forces 评估塑造行业竞争强度与吸引力的 5 个力：
1. **Competitive Rivalry**（竞争强度、对手数量与攻势、市场增速、产品差异化）
2. **Threat of New Entrants**（公司享有的进入壁垒：监管批准 / 网络效应 / 专利 / 资本要求；新威胁的出现）
3. **Bargaining Power of Buyers**（客户价格敏感度、切换难度、收入集中度、谈判 leverage）
4. **Bargaining Power of Suppliers**（关键技术 / 供应商依赖、风险、可替代性）
5. **Threat of Substitutes**（客户考虑的非直接替代品、类别颠覆风险）

> 画像**不通过结构化表单收集**，而是从创始人在多次对话中自然分享的上下文中渐进积累。一个谈论合同期与切换成本 → buyer power；谈论云基础设施依赖 → supplier power；谈论监管批准让创业公司难以进入 → barrier to entry。

> 部分覆盖（仅 2-3 个力）已经有用——系统应将 Porter 画像视为**长期演进的结构**，不强制全维填充才上线。

#### 验收标准

**抽取触发器**：实时增量。

**Five Forces 抽取**：
- 对话中浮现的信号正确归类到对应力：
  - Competitive Rivalry / Threat of New Entrants / Bargaining Power of Buyers / Bargaining Power of Suppliers / Threat of Substitutes
- 每条信号映射到正确的力 + 存储为 Layer 1a memory entry，附 source type / timestamp / 所属力。
- 单条 turn 含多个力的信号时，分别抽取并归入对应类别。

**画像精修**：
- 新信息更新或冲突既有 entry → 更新到最新。
- 画像视为长期累积结构——首次抽取就有效（部分覆盖也算）。

**性能与错误处理**：同 LG-1391。

#### UX 设计要点

- 后端与数据架构故事——本范围内无 UI。

---

### A.7 Layer 1a Backend - Chat Extraction: Strategic Context and Challenges（LG-1395）

- **Asana ID**: 1214953638826107
- **状态**: Needs Sizing（Working Status = Not Started）
- **最近修改**: 2026-05-21
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214953638826107

#### 业务需求

本 Story 覆盖**战略上下文**的实时增量抽取，包括：
- 商业模式 / pricing model 细节
- 产品对 ICP 的 value proposition 与 ROI 故事
- **Strategic challenges with staying power**（持续战略挑战）
- 组织结构与关键人员

**关键区分（staying power vs transient）**：
- staying power：6 个月以上的销售效率问题、SaaS 商业模式转型、CTO 主导的架构重构 → 抽取
- transient：上周二某 deal 关闭 → 不抽取（属于 chat history 的范畴，不进 memory）

**人员与组织上下文**：当创始人提到团队成员时（"get with our Head of Sales"、"our CTO built our entire data pipeline"），抽取人名 + 角色 + 组织相关性。这使 AI 未来生成战略建议时能引用对的人，让建议具体且可执行。

#### 验收标准

**抽取触发器**：实时增量。

**商业 / Pricing 模型抽取**：
- 商业模式上下文（SaaS、marketplace、services、hybrid 等）。
- Pricing 细节（seat-based、usage-based、value-based、services 捆绑等）。
- 模型转型 / 变化 → 更新既有 entry。

**Value Proposition / ROI 抽取**：
- 描述对 ICP 的价值时抽取（解决什么问题、客户为什么付费、交付什么 outcome）。
- ROI 故事 / 量化客户 outcome（如 "our customers typically save 40% on processing costs"）。

**Strategic Challenges 抽取**：
- 有 staying power 的战略挑战（跨多次会话相关、反映持续模式而非一次性事件）。
- 合格例：持续销售效率问题、对某 ICP 不通的 GTM 动作、在新 segment 的 PMF 挑战。
- **明确排除**：3-6 个月后将不再相关的瞬时具体事件——"存模式，不存实例"。
- 创始人指明挑战已解决 → 更新对应 entry 反映当前状态。

**人员与组织上下文抽取**：
- 关键人物：name + role + 组织相关性。
- 帮助 AI 给出具体可执行建议的组织上下文（"our VP of Sales owns all enterprise deals"、"our Head of Finance is building out our financial model"）。
- 没有战略上下文的普通员工名（如 customer success rep 顺带提及）**不抽取**，除非有明确组织意义。

**冲突处理 + 性能 + 错误处理**：同 LG-1391。

#### UX 设计要点

- 后端与数据架构故事——本范围内无 UI。

---

### A.8 Layer 1a Backend - Chat Extraction: Founder Profile（LG-1396）

- **Asana ID**: 1214953638826108
- **状态**: Needs Sizing（Working Status = Not Started）
- **最近修改**: 2026-05-21
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214953638826108

#### 业务需求

本 Story 覆盖**创始人 psychographic 与 leadership 画像信号**的实时增量抽取。理解创始人如何思考、沟通、决策，让 AI 能以最适合那个人的方式 frame 回复——不仅准确，而且**真正有用**。
- 冲突回避、倾向回避困难对话的创始人 → 与直接、数据驱动想要不加修饰分析的创始人需要不同的 framing。
- 视觉化思考的创始人 vs 通过详细书面框架处理信息的创始人 → 不同沟通方式。

**画像渐进且 subtle 地构建**——从创始人的写作风格、提问内容、面对挑战的反应、使用的语言中拾取自然存在的信号。多次对话之后逐渐浮现有意义的画像。

**存储格式很重要**：画像存为**观察性 tendency**而非绝对标签（hedging language）。例如：
- ✅ "tends to think through decisions by talking them out"
- ❌ "extroverted decision-maker"

画像存在 Layer 1a，**对 Company Admin 用户在 Memory Settings 面板可见且可纠正**——这帮助用户改善聊天体验并修正 mischaracterization。

> 注：Portfolio Manager 的 Layer 1b memory 可能含 GS 自己对创始人的内部看法（可能不同）——由 Layer 1b 系列 Story 处理。

#### 验收标准

**抽取触发器**：实时增量。

**Founder Profile 信号抽取**：
- 当模式从对话中浮现时，正确抽取关于创始人 leadership 风格、沟通偏好、决策倾向的信号。
- 合格信号类型（开放清单）：冲突回避或直接、数据驱动 vs 直觉驱动、沟通风格（简洁 vs 探索）、面对挑战 / 困难反馈时的反应、strong conviction 区域 vs uncertainty 区域。
- 画像观察存储时使用合适的 hedging 语言（"appears to prefer data-driven framing when discussing financial performance"），不用绝对标签（"data-driven"）。
- **单条消息不足以创建 profile entry**——需跨多次往返出现模式才抽取一条 founder profile observation。

**画像可访问性**：
- Founder profile entry 存在 Layer 1a 中，Company Admin 用户在 Memory Settings 只读面板可访问。
- 显示时以观察性 tendency 措辞 frame——让创始人理解这是观察而非绝对评估。
- AI 用 founder profile 上下文调整 framing（更直接 vs 更探索）。
- Portfolio Manager 的 Layer 1b GS 内部视角与 Layer 1a 的 founder profile **不同**，分别管理。

**冲突与更新处理**：
- 后续信号显示既有观察不准确或已变 → 更新到最新。
- 最近的 profile observation 始终视为权威。

**性能与错误处理**：同 LG-1391。

#### UX 设计要点

- 后端与数据架构故事——本范围内无 UI（UI 在 LG-1333 中体现）。

---

## B. Layer 1b Backend — Portfolio Admin Memory File 后端（2 个 + 1 个 Research）

> **拆分背景**：Liang Chunru 2026-05-18 评论指出 LG-1330 与 LG-1329 同样过大，且公司归属逻辑尚未明确，建议按 source 拆 + 单独开 Research ticket（LG-1385）。Karen 5/18 同意并创建 LG-1385（详见 [part-A-foundation.md](./part-A-foundation.md)）。

### B.1 Layer 1b Backend - Initialization & Architecture (Portfolio Admin)（LG-1397）

- **Asana ID**: 1214953638826115
- **状态**: Needs Sizing（Working Status = Not Started）
- **最近修改**: 2026-05-21
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214953638826115

> **NOTE**：notes 头部标记 "TBD if the PA user is scoped to the Portfolio level or Global level"——此问题与 LG-1330 5/15 Karen 评论 + Liang 5/18 portfolio-级建议关联，待 LG-1385 Research 输出后 finalize。

#### 业务需求

本 Story 覆盖**每公司一份 Layer 1b Memory File 的创建**，以及强制其与 Layer 1a 隔离、仅 Portfolio Manager 访问的基础架构。

每家公司在 Chatbot 首次被 Portfolio Admin 用户初始化时创建独立 Layer 1b 存储，与 Layer 1a 在数据层完全分离——两者从不合并、组合或混杂。Layer 1b **绝不可被 company-side 用户访问**——无 UI、无 chat 回复路径、无 prompt injection 路径，无论 prompt 如何措辞。

#### 验收标准

- 每公司在 Portfolio Admin 用户首次初始化 Chatbot 时自动创建 Layer 1b Memory File。
- Layer 1a 与 Layer 1b 在数据层**完全分离的存储**——从不合并 / 混杂。
- Layer 1b 仅 Portfolio Manager 与 Admin 角色可查询——任何情况下 Company User / Company Admin 都不可查询。
- AI 模型在**架构层**被约束，防止将 Layer 1b 内容暴露给 company-side 用户，无论 chat prompt 如何措辞。
- Company-side 用户尝试提取 Layer 1b 内容时，收到**中立、不揭示的回复**——既不确认也不否认 Layer 1b 的存在。
- Layer 1b 内容在任何情况下都不流入 Layer 2。
- 一家公司的 Layer 1b 内容**绝不可被其他公司访问**。
- Memory entry 存储时附带 source type + timestamp。
- 架构支持 Portfolio Manager 与 Admin 角色通过 Memory Settings UI 只读访问（详见 LG-1336）。

#### UX 设计要点

- 后端与数据架构故事——本范围内无 UI。

#### 依赖与备注

- 是 LG-1398（Chat Extraction & Document Upload）的前置。
- 是 LG-1336（Portfolio Manager Memory File Access UI）的依赖。

---

### B.2 Layer 1b Backend - Chat Extraction & Document Upload Processing (Portfolio Admin)（LG-1398）

- **Asana ID**: 1214953638826116
- **状态**: Needs Sizing（Working Status = Not Started）
- **最近修改**: 2026-05-21
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214953638826116

> **NOTE 1**：notes 头部标记 "TBD if the PA user is scoped to the Portfolio level or Global level"。
> **NOTE 2**：本 Story 的 AC 在 **LG-1385 Research（Layer 1b Chat Content - Company Association）** 完成后可能需更新——它依赖 Research 输出的具体公司归属策略。

#### 业务需求

本 Story 覆盖**从 Portfolio Manager 聊天会话与文档上传向 Layer 1b 写入内容**的逻辑。

**Chat Extraction**：从 PM 聊天会话抽取的关于具体公司的内容，路由到该公司 Layer 1b 文件（**遵循 Layer 1a 同样的实时增量抽取规则 + 相同的内容类别分组**）。质量门槛一致：只保存有意义、与公司相关的 learnings。Layer 1a 排除的内容（generic、transactional、verbatim transcript）同样排除。

**Document Upload**：沿用 LG-1399（Document Upload Portfolio Admin）中定义的工作流：AI 基于会话上下文推断可能公司 → 弹 confirmation prompt → PM 确认后 RAG 索引 + 写入对应公司 Layer 1b；PM 选不同公司 → 写入所选公司；未选 → 不写入任何 Layer 1b，仅作为 session-only 文件。

#### 验收标准

- 本 Story 依赖 **Research ticket LG-1385**（1214913562391163）完成后才能 finalize AC。
- PM 聊天抽取内容按 LG-1385 输出的方案路由到正确公司的 Layer 1b 文件。
- **实时增量抽取触发器 + 质量规则** mirror Layer 1a（统一规则）。
- Layer 1a 的内容类别分组（Founder Profile / Company Facts / ICP / Competitive Landscape / Porter's Five Forces / Strategic Context）同样适用于 Layer 1b 抽取。
- PM 文档上传：AI 推断公司 + confirmation prompt：
  - 确认 → RAG 索引 + 摘要写入该公司 Layer 1b
  - 选不同公司 → 处理给所选公司
  - 未选 / 忽略 → 不写入任何 Layer 1b，仅作为 session-only 文件
- 多公司会话正确处理——单次会话的 learning 可分布到多家公司 Layer 1b（依据 Research 输出的归属逻辑）。

#### UX 设计要点

- 后端与数据架构故事——本范围内无 UI（UI 由 LG-1399 + LG-1336 覆盖）。

#### 依赖与备注

- **强依赖** LG-1385 Research 完成（详见 [part-A-foundation.md](./part-A-foundation.md)）。
- 依赖 LG-1397（Init & Architecture）。
- 配套 LG-1399（Document Upload Portfolio Admin）的 UI 与上传通道。

---

## C. Layer 2 — GS Knowledge Base

### C.1 GS Knowledge Base - Layer 2 Ingestion & Management（LG-1331）

- **Asana ID**: 1214057483533665
- **状态**: Prioritization In Progress（Working Status = Not Started，T-Shirt = M）
- **最近修改**: 2026-05-20
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533665

#### 业务需求

AI Chatbot 的双层知识架构依赖一个已填充、可查询的 Golden Section Knowledge Base 作为 Layer 2 共享资源。与 Layer 1（公司专属 Memory File）由用户活动自动构建不同，Layer 2 必须由 Golden Section 内部显式填充。MVP 阶段，该层由 Golden Section 既有 playbooks 与 best practice frameworks 构成。

**结论 from LG-1326 调研**：外部站点托管不会带来 GEO 收益。AI 模型不会因接收某站点内容而提升该站点的权威性。基于此采用 **Option B**：把外部站点（https://www.goldensection.com/vertical-saas-playbooks）现有 GS playbook 全部复制进 Looking Glass 内由我们管理的**单一 markdown 文件**。该文件即为 GS Knowledge Base 后续内容来源。

本 Story 覆盖：
1. 将该 markdown 文件及配套文档摄取为 Chatbot 可查询的格式（vector store）
2. 为授权 GS 用户（Super Admin、PGM）提供持续管理 / 更新内容的内部工具

**架构提示**：当 LG 商业化销售给外部 equity firms 时，每家公司（每个 tenant）需要其专属知识库，与其他 tenants 完全隔离。Layer 2 必须从 day 1 即 **tenant-scoped 设计**，不要以"将永远只有一个全局知识库"为假设。

#### 验收标准

**内容摄取**：
- 把外部 GS 网站现有 playbook 内容全部复制进一份内部管理的 markdown 文件，作为 Layer 2 内容来源。
- 实现后端摄取流水线，接收常见格式（至少 PDF、Word .docx、markdown .md），处理为可被检索的查询存储（vector store）。
- 所有内容作为共享 GS Knowledge Base 的一部分被存储与索引，对所有 chatbot 用户开放，不论公司或角色。
- GS Knowledge Base 与任何公司的 Layer 1 在数据与架构层**完全隔离**。
- 任何可识别公司、财务数据、创始人相关上下文**永不**存入 Layer 2。
- 一组完整的初始 GS playbook 被摄取并作为验收测试的一部分被验证。

**内容管理**：
- 提供面向内部的管理界面 / 流程，使授权用户能上传新内容、更新 markdown、或移除文档。
- 编辑权限限 **Portfolio Group Manager** 及以上。
- 内容更新后自动重新索引。
- 移除后不再在 chatbot 回复中检索到。
- 管理界面有简洁状态指示：最近更新时间 + 当前已索引文档数。

**Chatbot 查询行为**：
- chatbot 在用户询问战略 / 最佳实践 / GS 指引相关问题时准确检索并引用 Playbook 内容相关章节。
- 借助 Layer 2 生成的回复**不会逐字暴露原始文档文本**——AI 以对话式语言综合表达。

**未来多租户兼容**：
- Layer 2 架构支持未来 per-tenant 知识库隔离——每家外部 equity firm 可有其独立知识库。

**额外 RAG 细节**：
- 后端摄取流水线兼容 LG-1328 中建立的 RAG 架构。
- 初始 GS playbooks 在上线时已被验证摄取——知识库上线时不能为空。

#### UX 设计要点

- 公司侧用户与 Portfolio Manager 都不直接看到知识库文档——他们仅通过 chatbot 自然语言回复与之交互。MVP 无"浏览 playbooks"的 UI。
- 内部管理界面 MVP 不需消费级精致——简洁可用即可：文档列表 + 状态指示器 + 上传 + 删除。
- chatbot 用户侧，大量引用 GS playbook 内容的回复加上"Based on GS best practices"等不显眼归属标识。
- 推荐 markdown 作为主要内容管理格式（人类可读、轻量、便于版本管理）。

#### 依赖与备注

- 依赖前置故事 LG-1328（AI Architecture & Model Routing Foundation）的 RAG 架构。
- 内容编辑权限：Portfolio Group Manager 及以上。
- LLM 自动从对话识别知识库更新为 Post-MVP，本 Story 不构建。
- 架构必须为 per-tenant 知识库隔离做预留，避免后续大规模重构。

---

### C.2 AI Chatbot - GS Knowledge Base Access for All Users（Layer 2）（LG-1338）

- **Asana ID**: 1214081544026467
- **状态**: Prioritization In Progress（Working Status = Not Started，T-Shirt = L）
- **最近修改**: 2026-05-15
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026467

#### 业务需求

在 Knowledge Base 完成摄取与索引后，本 Story 将 Layer 2 知识源接入 chatbot 体验，覆盖**所有用户角色**——Company User、Company Admin、PM、PGM。让任何用户都能基于组织 playbooks 与 best practice frameworks 提问并获得对话式指引。

**MVP 单租户语境**：唯一组织 = Golden Section，Layer 2 = GS playbooks 单一 markdown 文件。

**未来多租户**：每家 equity firm 独立知识库，与其他 tenant 完全隔离。**没有任何已规划的产品功能**会让 tenant 自动继承或访问 GS 的 playbooks。早期商业伙伴可能通过非正式运营 workaround 分享 playbook，但不作为产品功能内建。

**架构上预留扩展点（不实现）**：跨 portfolio 匿名化 Fireflies 市场情报层，未来或许作为 opt-in 资源跨 tenant 提供。**Post-MVP**。

**实现要求**：Layer 2 接入与 chatbot 访问层**按 tenant-scoped 设计**——系统查询当前用户所属组织对应的知识库，而非硬编码全局知识库。

#### 验收标准

**Chatbot 查询接入**：
- chatbot 能从 Layer 2 知识库检索并综合相关内容，回应所有用户角色关于战略 / 最佳实践 / 组织指引的问题。
- Layer 2 存储是可被查询的来源，公司侧与 Portfolio Manager 双端 chatbot 界面均可调用。
- 引用 Layer 2 内容的回复包含不显眼的归属（如 "Based on GS best practices"）。
- chatbot 不逐字返回原始文档文本——始终自然对话式综合。
- Layer 2 与任何公司的 Layer 1 完全隔离。
- 对所有角色开放：Company User / Company Admin / Portfolio Manager / Portfolio Group Manager / Admin。

**Tenant-Scoped 架构**：
- Layer 2 范围限定为当前用户所属组织对应的知识库——系统不查询单一硬编码全局知识库。
- MVP 单一 tenant 解析到 GS 知识库；多租户引入时可按 tenant 替换不同知识库，不需重构 chatbot 访问层。
- 不引入会阻碍未来 per-tenant 隔离的任何"单一全局知识库"硬编码假设。
- 架构明确**不**包含让 tenant 自动继承或访问 GS 知识库的特性。

#### UX 设计要点

- 知识库体感应像可随时调用的资深顾问，而非搜索工具或文档库。"What would GS recommend for..." 比 "Search GS playbooks for..." 更具引导性。
- 知识库在两端 chat 界面都应清晰呈现——欢迎页通过 suggested prompt card 提示组织级指引可用。
- Suggested prompt 文案按受众定制——创始人 vs PM 不同。
- Layer 2 内容严格只读——任何用户不可通过聊天修改 / 新增 / 移除。
- 归属标识保持低调——回复末尾小字标签或斜体注脚。
- 多租户语境下归属文案动态引用所属 firm 身份（如 "Based on [Firm Name] best practices"），不要硬编码 "GS"。

#### 依赖与备注

- 依赖故事 LG-1331（Layer 2 Ingestion & Management）。
- MVP 阶段单租户：唯一 tenant = GS；尽管如此，必须按 tenant-scoped 实现。
- 跨 tenant 匿名化 Fireflies 市场情报层属于 post-MVP。
- 归属标识文案需可按 tenant 配置（避免硬编码 "GS"）。
