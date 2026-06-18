# memory\_file\_spec\_v4

# AI Chatbot 记忆文件规格说明文档

文档用途：面向开发团队，说明 Layer 1a 与 Layer 1b 记忆文件的完整实现规格，包括用户权限、写入来源与触发节点、内容分类、提取 Prompt 示例及冲突解决策略。

## 一、整体架构概览

|层级|名称|归属范围|是否可见于公司端|
|---|---|---|---|
|Layer 1a|公司记忆文件|每家公司各一份|是（Company Admin 可查看）|
|Layer 1b|管理端记忆文件|每家公司各一份|否（仅管理端用户）|
|Layer 2|Golden Section 知识库（Playbook）|租户内共享|否（本文不涉及）|

Layer 1b 的公司归属关系：Layer 1b 是 per\-company 的，而非 per\-portfolio\-manager。同一家公司所有有权访问该公司的所有管理端用户（PM/PGM/Super Admin）共享同一份 Layer 1b 文件——任何有权限的管理端用户的聊天内容都写入同一文件，查询时也读取同一文件。

术语约定：

- 「管理端用户」指有权访问 Admin Portal 的用户，包括 PM（投资经理）、PGM、Super Admin。本文档在做需求讲解时统一使用「管理端用户」这一总称。

- 在面向 AI 的提取 / 回应 Prompt 中，应使用更通俗、贴近业务的称谓（如「投资经理」），而非「管理端用户」「PM/PGM/Super Admin」这类系统/角色术语，以免 Prompt 措辞生硬或泄露内部角色体系。

- 「公司端用户」指有权访问Company Portal的用户（Company User、Company Admin）。在面向 AI 的 Prompt 中，对应称谓为「创始人 / founder」。本文档在需求讲解中使用「公司端用户」，Prompt 中使用「创始人」，二者指向同一对象。

## 二、Layer 1a — 公司记忆文件

### 2\.1 用户权限矩阵

|角色|贡献写入|AI 调取使用|UI 查看|
|---|---|---|---|
|Company User|是（通过聊天、文档上传）<br>|是|否|
|Company Admin|是（通过聊天、文档上传）<br>|是|是（只读，可在线查看）|
|PM / PGM / Super Admin|否（其聊天写入 Layer 1b）<br>|是（同时读取 1a \+ 1b）|是（只读，可在线查看）|

注意：管理端用户对 Layer 1a 只读——他们的聊天内容不会写入 Layer 1a，但 AI 为他们生成回答时会同时调用 Layer 1a 和 Layer 1b。

### 2\.2 写入来源（Sources）与触发节点

写入来源和触发节点如下。
注意：提取任务失败时，静默写日志，不向用户展示错误，聊天正常继续。

#### **Source A：Company Profile（系统初始化）**

- 触发节点：该公司 AI Chatbot 首次启用时自动执行；此后以下任何字段被修改时，记忆中对应内容实时自动更新。

- 写入内容（以下为 LG 中的对应字段名）：

    - 公司名称（LG 字段名：Company）

    - 公司描述（LG 字段名：Company Overview。注意：该字段内含有关于公司所属行业的描述，提取时需将行业信息单独拆出，归入「行业」类别）

    - 公司类型（LG 字段名：Company Type）

    - 行业（内容来源：从 Company Overview 字段中提取行业相关描述）

    - 发展阶段（LG 字段名：Company Status）

    - 商业模式（内容来源：从 Company Overview 字段中提取商业模式相关描述）

    - 公司官网（LG 字段名：Company URL）

    - 公司官网信息总结：AI 在初始化时主动访问公司官网，从网站内容中提取对公司业务的理解，并将这些理解写入记忆文件。不做字段内容的简单存储，而是基于网站信息形成对公司的结构化认知。具体： 

        - 爬取范围：爬取网站的所有页面。

        - 提取维度：沿用 Layer 1a 聊天抽取的同一套内容分类维度。

        - 触发时机：

            - 初始化时执行；

            - 此后当 Company Settings 中的 Company URL 字段被新增／更新／删除时，重新触发爬取。

            - 系统主动监测网站内容变化、网站内容变化而自动更新。

- 特性：此来源的内容也须经过 AI 提取写入（例如从 Company Overview 中自动抽取行业描述，公司官网信息总结），不做字段间的简单直接映射。

#### **Source B：公司端聊天对话（Company Chat Session）**

- 触发节点：每次一问一答完成（携带一定上下文）给存储，异步执行不阻塞。

- 写入内容：AI 从对话中提取的有持久战略价值的公司相关信息（见 2\.3 内容分类）。

- 排除内容：完整对话原文（原文由 Chat History 功能单独存储）、通用性问答、事务性交流、Source A 字段中已准确存储的信息。

- 处理流程：

    - 每次用户消息与 AI 回答完成后立即触发提取，仅评估本次 exchange（最新一轮问答）

    - 加载该公司当前 Layer 1a 记忆文件作为上下文（避免重复写入）

    - 执行结构化 AI 提取任务（见 2\.3 中各分类 Prompt）

    - 对提取结果逐条判断：新信息 → 插入；更新/更正 ；无变化 → 跳过

#### **Source C：文档上传（Document Upload，Company 端）**

- 触发节点：Company User 或 Company Admin 在聊天中上传文件时立即触发，不等待 Session 结束。

- 写入内容：从文档中提取的高层次知识摘要，写入 Layer 1a。每条记忆条目须附带以下元数据：来源类（document summary）、文档名称、时间戳、上传人、对应的聊天session。

- 并行处理：文档同时进行 RAG 索引（供后续聊天动态检索使用），与记忆摘要生成并行执行，互不依赖。

- 归属绑定：公司端用户始终处于该公司的聊天上下文中，系统自动确定归属，不依赖 AI 推断。

- 文件处理模型（知识库、RAG、记忆摘要的关系）：

    - 所有通过聊天上传的文件都进入知识库，并进行 RAG 索引；记忆摘要是独立且有条件的步骤。

    - 若文件不含值得存储的公司相关内容，则不生成记忆摘要，但文件仍进入知识库、仍可在聊天中经 RAG 检索。

    - 公司端上传隐式归属本公司；

    - 可见性按权限而非内容决定，且RAG 检索权限与知识库可见性一致：

        - Company User只能看到自己上传的文件；

        - Company Admin能看到本公司用户上传的所有文件。

### 2\.3 Source B 内容分类及提取 Prompt

**通用实现说明：**

1. 开发团队可使用统一的结构化提取 Prompt，将下列分类作为约束框架，各分类自己的 Prompt 说明为准。

2. 字段逐步补全：每次提取不要求所有字段都完整输出。若某次对话只涉及某分类的部分信息，只输出有内容的字段，与已有记录合并补全，不强制覆盖空缺字段。此规则适用于所有分类。

3. 分类边界：各分类之间不应重叠。每条信息只归入最合适的一个分类，避免同一内容在多个分类中重复存储。

4. 人名匹配规则（适用于 C3、C4、C5 等涉及实体名称的分类）：

    - 字符串完全一致 → 直接判定为同一实体

    - 名称部分匹配（如”Sarah Li”与”Sarah”）→ 结合上下文语义判断是否为同一人，判断为同一人时合并记录，不确定时新建记录并标注”待确认关联”

    - 字符串 vs 语义：实体名称（人名、公司名）用字符串匹配；描述性内容（职能、行业特征）用语义匹配

5. 各分类均需携带元数据：source\_type（chat / profile / document）、created\_at、updated\_at。

#### **分类 C1：公司基础事实补充／更正**

定义：用户在聊天中对公司的事实性陈述，包含两类：

1. 对Source A的更正

2. Source A中尚未记录的公司事实信息例如：近期重大业务事件（"我们刚签下第一个企业级客户"）、市场定位（"我们是专注中端医疗市场的唯一服务商"）、团队规模或架构变化、融资进展等。这类信息用于丰富 AI对公司的理解，超出 Company Settings 所能覆盖的范围。

对应 Source A 字段：

- 公司名称（LG 字段名：Company）

- 公司描述（LG 字段名：Company Overview。注意：该字段内含有关于公司所属行业的描述，提取时需将行业信息单独拆出，归入「行业」类别）

- 公司类型（LG 字段名：Company Type）

- 行业（内容来源：从 Company Overview 字段中提取行业相关描述）

- 发展阶段（LG 字段名：Company Status）

- 商业模式（内容来源：从 Company Overview 字段中提取商业模式相关描述）

- 公司官网（LG 字段名：Company URL）

- 公司官网信息总结：这是对公司官网URL 字段特殊处理。AI 在初始化时主动访问公司官网，从网站内容中提取对公司业务的理解，并将这些理解写入记忆文件。不做字段内容的简单存储，而是基于网站信息形成对公司的结构化认知。URL更新时，应该再次触发这个过程。

提取 Prompt：

分析用户对话，识别用户提及的关于公司的客观事实。

1. Target Fields

    1. 公司名称（LG 字段名：Company）

    2. 公司描述（LG 字段名：Company Overview。注意：该字段内含有关于公司所属行业的描述，提取时需将行业信息单独拆出，归入「行业」类别）

    3. 公司类型（LG 字段名：Company Type）

    4. 行业（内容来源：从 Company Overview 字段中提取行业相关描述）

    5. 发展阶段（LG 字段名：Company Status）

    6. 商业模式（内容来源：从 Company Overview 字段中提取商业模式相关描述）

    7. 公司官网（LG 字段名：Company URL）

    8. 动态生成字段：

        1. **业务里程碑与近期事件：** 公司近期经历的重大事件或成就，例如赢得首个或具有代表性的客户、进入新市场、达到某一收入或增长门槛、启动关键举措，或进行重大的业务运营变革。这些是反映业务当前发展状态且具时效性的事实。

        2. **融资与资本活动：** 关于公司融资历史和当前资本状况的信息，包括已完成的融资轮次及金额、当前的资金跑道（Runway）、投资者关系，以及公司目前是否正在积极进行融资。此项不包括通过上传的财务报表所体现的连续性收入或财务业绩数据。

        3. **行业与监管背景：** 公司运营所处的外部环境，包括特定行业的合规要求、监管批准或限制、公司持有或正在申请的认证，以及对业务运营或进入市场（Go\-to\-market）方式产生实质性影响的相关政策或市场转变。

2. Extraction Rules

    1. 范围限制：仅提取涉及公司维度的客观事实。忽略日常问候或常规项目管理讨论。

    2. 唯一性去重（重要）：如果该事实信息已经属于或应当归入记忆文件的其他分类（例如属于已经存在的财务数据备注 Notes 模块），则本分类拒绝提取，避免数据交叉重复。

    3. 拆分逻辑：如果一句话同时包含多项事实，必须智能拆分成多个字段（例如将行业和商业模式从 Overview 中剥离）。

    4. 变更类型判断（change\_type）：

    - supplement：若信息在系统现有事实中属于空白，或属于新发现的未知维度事实。

    - correction：若新陈述与系统现有的记录明确冲突，或用户显式表达了更正。

3. 冲突处理：新信息覆盖旧信息，保留时间戳。

4. 输出：

\{

"category": "company\_facts",

"field": "\<事实所属维度。固定字段取 Source A 字段名（如 Industry / Business Model / Company Type 等）；动态事实取动态类别名（business\_milestone / funding\_capital / industry\_regulatory）\>",

"value": "\<该事实的具体内容\>",

"change\_type": "supplement \| correction",

"timestamp": "\<记录时间\>"

\}

5. 示例

    - 模拟对话:「补充一下，我们其实已经不只做医疗了，现在主营是金融科技；另外上个月刚签下第一个企业级客户，也刚完成了 A 轮融资。

    - 提取结果:

    ```Plain Text
    [
      {
        "category": "company_facts",
        "field": "Industry",
        "value": "主营已从医疗转向金融科技",
        "change_type": "correction"
      },
      {
        "category": "company_facts",
        "field": "business_milestone",
        "value": "签下首个企业级客户",
        "change_type": "supplement"
      },
      {
        "category": "company_facts",
        "field": "funding_capital",
        "value": "已完成 A 轮融资",
        "change_type": "supplement"
      }
    ]
    ```

#### **分类 C2：数据****更正****／澄清**

所有标准化字段全部整理出来 名字 时间 值 数据类型

标准化字段如下，适用于三种数据类型（Actuals, Committed Forecast, System generated Forecsat）

- Revenue

- COGS

- OPEX

- Other Expenses

- Capitalized R\&D \(Monthly\)

- Cash

- Accounts Receivable

- Other Assets

- Accounts Payable

- Long\-Term Debt

- Other Liabilities

- Gross Profit

- Gross Margin

- EBITDA

- Net Income

- Monthly Runway

- Rule of 40

- MRR YoY Growth Rate

- Net Profit Margin

- Sales Efficiency Ratio

- ARR

- Monthly Net Burn Rate

- Debt/Assets Ratio

- Cash on Hand

- MRR

- New MRR LTM

- Capitalized R\&D \(Total\)

- Assets

- Liabilities

- Runway Left

- End of Runway

定义：用户对 LG 中现有标准化财务数据（Actuals、Committed Forecast、System Generated Forecast）的更正或澄清。MVP 阶段仅作为聊天上下文记录，不传播至下游财务计算，不修改 LG 原始数据。本分类所有更正条目均仅用于当前及未来聊天上下文，不写回 LG。

提取 Prompt：

分析以下对话内容，识别用户对 LG 现有标准化财务数据（Actuals、Committed Forecast、System Generated Forecast）的更正或澄清声明。

记录：数据类型（Actuals / Committed Forecast / System Generated Forecast）、被更正的标准化字段名、该数据点对应的期间（月份）、原始值（如已知）、更正值、备注（更正原因）、更正时间。

输出：

Plain

```Plain Text
{
  "category": "data_correction",
  "data_type": "Actuals | Committed Forecast | System Generated Forecast",
  "field": "<标准化字段名，如 ARR>",
  "period": "<该数据点对应的期间，如 2025-07>",
  "original_value": "<原始值，如已知>",
  "corrected_value": "<更正值>",
  "remarks": "<更正原因／备注>",
  "timestamp": "<更正时间>"
}
```

示例：

- 对话模拟：「其实我们 2025 年 7 月的 Actuals ARR 是 120 万，不是系统里的 95 万，一笔大客户续约被归错月份了。」

- 提取结果：

Plain

```Plain Text
{
  "category": "data_correction",
  "data_type": "Actuals",
  "field": "ARR",
  "period": "2025-07",
  "original_value": "$950K",
  "corrected_value": "$1.2M",
  "remarks": "大客户续约被错误归入下月",
  "timestamp": "2026-06-12T10:00:00Z"
}
```

冲突处理：同一数据点（同一 data\_type \+ field \+ period）再次给出不同更正值 → 追加新更正记录，带新的 timestamp；AI 使用最新一条更正值。

#### **分类 C3：人员与组织架构**

记录这个人的姓名、职位、负责领域

定义：公司关键人物、职能角色及其在组织中的核心战略权责，用于 AI 在策略对话中引用具体负责人并提供可执行的行动建议。系统随对话逐步增量补全，不要求一次性完整。

满足以下任一条件 → 创建或更新条目：

- 职位关键词命中以下列表（须同时提及姓名）：创始人、联创、Founder、Co\-founder、CEO、CTO、CFO、COO、CMO、CPO、CRO及其中文等价称谓；副总裁、VP（需跟有职能方向）；总监、Director（需跟有职能方向）；Head of \[职能\]；负责人（需跟有职能方向，如"产品负责人"）；合伙人、Partner；董事

- 职位不在上述列表，但对话中明确说明此人是某项战略决策或关键执行的主要负责人（例如："虽然他头衔是经理，但我们整个技术架构都是他在主导"）

不提取的情况：

- 只有泛指称呼，无姓名（"我们的 CS 同事会跟进"）

- 有姓名但只是顺带一提，无职能上下文，且职位不在关键词列表中（"昨天 Mike 发了条消息"）

- 个人贡献者角色，无战略决策职能（工程师、设计师、销售专员、CS 专员等，除非对话明确说明其战略角色）

提取 Prompt：

分析以下对话内容，识别用户提及的关键人员及组织架构上下文。

特征提取：请在单次分析中，完整提取以下 5 个平级核心维度：姓名（Name）、职位（Role）、所属职能部门（Department）、核心战略权责（Strategic Ownership）、以及备注说明（Notes）。

战略权责提取重点（关键）：不仅记录其头衔，必须重点提炼此人在组织中所拥有或主导的战略所有权（如：“全权负责并推进所有企业级大单的落地”、“正在独立构建公司底层的财务模型”）。这作为 AI 后续生成针对性行动建议的关键依据。

多部门与信息补全规则：若某人跨部门或未明确提及职位，如实记录明确提及的部分，未提及的字段留空（""）或在 `notes` 中注明待后续补全，切勿盲目推断。

输出：

\{

"category": "people",

"name": "\<姓名，必须明确提及时填写\>",

"role": "\<职位/头衔，仅明确提及时填写，无则留空\>",

"department": "\<所属职能部门，如 Sales / Engineering / Finance / Product，无则留空\>",

"strategic\_ownership": "\<在组织中的核心战略权责/所有权描述，无则留空\>",

"notes": "\<补充说明，如头衔与职能不符、信息待补全等备注\>"

\}

示例A ：关键词命中，信息完整

- 模拟对话：「销售方向主要由 Sarah 负责，她是 VP of Sales，专门盯着中端市场。产品和工程都是 Marcus 在管，他头衔只是高级工程师，但实际上整个技术方向都是他定的。」

- 提取结果：

\[

\{

"category": "people",

"name": "Sarah",

"role": "VP of Sales",

"department": "Sales",

"strategic\_ownership": "全权负责销售方向，重点盯防并推进中端市场业务的落地",

"notes": ""

\},

\{

"category": "people",

"name": "Marcus",

"role": "高级工程师",

"department": "Engineering",

"strategic\_ownership": "全权统筹并主导产品和工程方向，决定公司整体的技术架构走向",

"notes": "实际技术决策负责人，头衔与战略职能不符"

\}

\]

示例 B — 关键词命中，信息不完整：

- 模拟对话：「我们有个副总叫 John，但我现在没时间细说他负责什么。」

- 提取结果：

\{

"category": "people",

"name": "John",

"role": "副总",

"department": "",

"strategic\_ownership": "",

"notes": "暂无更多上下文，待后续补全"

\}

"暂无更多上下文，待后续补全" 

示例 C — 职位未命中关键词，但有明确战略角色说明：

- 模拟对话：「产品和工程都是 Marcus 在管，他头衔只是高级工程师，但实际上整个技术方向都是他定的。」

- 提取结果：

\{

"category": "people",

"name": "Marcus",

"role": "高级工程师",

"department": "Engineering",

"strategic\_ownership": "主导产品与工程方向，决定公司整体技术架构走向",

"notes": "实际技术决策负责人，头衔与职能不符"

\}

示例 D — 不提取：

- 模拟对话：「我们的 CS 专员小花会负责后续跟进这个客户。」

- 提取结果：不输出（个人贡献者，无战略职能，不在关键词列表）

示例 E — 多人同时提及：

- 模拟对话：「销售方向主要由 Sarah 负责，她是 VP of Sales，专门盯着中端市场。产品和工程都是 Marcus 在管。」

- 提取结果：

\[

\{

"category": "people",

"name": "Sarah",

"role": "VP of Sales",

"department": "Sales",

"strategic\_ownership": "负责销售方向，重点盯防中端市场",

"notes": ""

\},

\{

"category": "people",

"name": "Marcus",

"role": "",

"department": "Engineering / Product",

"strategic\_ownership": "负责产品与工程",

"notes": "职位未明确提及，待补全"

\}

\]

注意：Marcus 的职位在对话中未明确提及，因此 role 字段不填，等待后续对话补全。

#### **分类 C4：目标客户画像（ICP）**

客户名称、客户类型、规模、行业、核心痛点、购买动机

定义：公司理想目标客户群体（Ideal Customer Profile）的具体特征描述。支持多个 ICP，随对话逐步增量补全，不要求一次性完整，涵盖该客群的画像特征及宏观行为规律。chatbot 应主动驱动 founder 定义并持续收窄其理想客户画像\(ICP\),通过反复追问"能否更聚焦/更窄"推动 founder 从宽泛 ICP 逐步收敛到高度具体的画像\(如:行业垂直 \+ 地域 \+ 基金规模/ARR 区间等多重限定\)。

提取 Prompt：

- 分析以下对话内容，识别用户对目标客户（ICP）群体的描述。

- 特征提取：必须提取以下维度：客户类型/买家角色（Customer Type/Role）、公司规模（Size）、所属行业（Industry）、核心痛点（Pain Point）、流失规律（Churn Patterns，哪类客户用着用着不续费、跑掉了。如：“独立站小卖家每到 Q3 容易流失”。*注意：具体某一家客户（如 Pepsi）退款的个别事件不算。*）和增购规律（Expansion Patterns，哪类客户用了一段时间后，追加预算、买更多账号或升级套餐了。如：“大卖家满 6 个月后通常会增购席位”。*注意：具体某一次加购了 5 个账号的单次交易流水不算*。）

- 多 ICP 处理：当创始人描述了多个截然不同的目标客群时，分别记录，用 ICP\-1、ICP\-2 等标签区分，并保留足够的上下文。

- 增量与演进更新：若对话仅更新某 ICP 的部分信息，与已有记录合并，不覆盖其他已有字段。如果创始人明确陈述 ICP 正在发生“变化或演变”，需用最新表述直接更新（Update）该条目，而非盲目追加。

输出：\{

"category": "icp",

"label": "ICP\-X",

"customer\_type": "\<客户类型/买家角色\>",

"size": "\<公司规模\>",

"industry": "\<所属行业\>",

"pain\_points": \["\<核心痛点\>"\],

"strategic\_patterns": \{

"churn\_patterns": \["\<该客群的流失规律/趋势，若无则填空\>"\],

"expansion\_patterns": \["\<该客群的成功/增购规律，若无则填空\>"\]

\},

"notes": "\<关于ICP演进或变化的备注说明\>"

\}

示例：

- 模拟对话：“我们主攻 20\-100人的跨境电商团队。他们最大的痛点是多平台库存对账总出错。

另外我最近发现两个很明显的规律：第一，这帮跨境大卖家进来之后，只要能熬过前 6 个月，后面基本都会自动扩容和增购席位；第二，那些做独立站的小卖家太不稳定了，每到第三季度财务做预算时，他们就会面临一波季节性流失。所以我们最近战略性放弃了 Shopify 独立站，100% 聚焦在平台型大卖家上。”

- 输出：\[

\{

"category": "icp",

"label": "ICP\-1",

"customer\_type": "平台型跨境电商大卖家",

"size": "20\-100人",

"industry": "跨境电商",

"pain\_points": \[

"多平台库存对账极易出错"

\],

"churn\_patterns": \[

"独立站小卖家客群在第三季度财务预算周期极易发生季节性流失"

\],

"expansion\_patterns": \[

"平台型大卖家客群在入驻满 6 个月后，通常会表现出高频的自动扩容与席位增购行为"

\],

"notes": "战略性放弃 Shopify 独立站客群，100% 聚焦平台型大卖家"

\}

\]

#### ******分类 ****C5：竞争对手**** \& 替换品威胁**

1. 直接竞争对手

    1. 定义：直接竞争者是指创始人在对话中明确提及的、与公司争夺同一批客户的其他公司或产品。这类竞争对手通常会出现在客户的采购候选名 单上，与该公司产品进行直接比较。竞争发生在供应商选择层面——客户已决定购买此类解决方案，正在不同供应商之间做取舍。竞品可以是整个公司，也可以是某家公司的特定产品，两者记录格式一致。

    2. 提取 Prompt：分析以下对话内容，识别用户提及的直接竞争对手信息，提取以下字段：名称、所属公司（若竞品为某家公司的特定产品，同时记录母公司名称和产品名称）、竞争定位（以创始人视角描述的双方相对优劣势）、竞争动态背景（竞争格局变化的上下文，如新进入者 、融资事件、市场整合动向）。所有提取内容均标注为创始人视角。若已有该竞品记录，合并更新，不重复新建。

    3. 对应的英文字段名称：Competitor Name，Parent Company，Competitive Positioning，Competitive Dynamics Context， Source Perspective: Founder

    4. 示例：

        1. 对话模拟："上个月在一个中型医疗集团的项目里，我们输给了 Salesforce Health Cloud。他们和 Epic的系统集成做得比我们深，这块我们确实差一些。但我们实施周期只要他们的一半，价格也低了 40%。另外最近听说 Oracle也在往这个赛道进，收购了一家做医疗 CRM 的小公司。"

        2. 提取结果：
        Competitor Name: Salesforce Health Cloud
        Parent Company: Salesforce
        Product Name: Health Cloud
        Competitive Positioning: 竞争对手在系统集成方面（尤其是与 Epic 的对接深度）优于本公司；本公司在实施周期（快约一倍）和定价（低约40%）方面具有优势
        Competitive Dynamics Context: Oracle 近期通过收购医疗 CRM 公司进入该赛道，为潜在新进入
        Source Perspective: Founder

2. 替换品威胁提取（Substitution Threats）

    1. 定义：替换品威胁是指客户用来解决同一问题的替代方式，但这些方式并非同类产品范畴内的直接竞争者。与直接竞争者不同，替代者威胁意味着客户尚未进入该产品类别的采购流程——竞争发生在"是否需要购买专门解决方案"这个层面，而非"选择哪家供应商"。

    2. 提取 Prompt：：分析以下对话内容，识别用户提及的替换品威胁信息，提取以下字段：替代方式描述（客户当前用于解决同一问题 的非竞品方式）、使用背景（客户选择此替代方式的原因或当前使用情况）。所有提取内容均标注为创始人视角。若已有该替代方式记 录，合并更新，不重复新建。

    3. 对应的英文字段名称：Alternative Approach，Usage Context，Source Perspective: Founder

    4. 示例：

        1. 对话模拟："我们大多数潜在客户还在用 Excel加一个兼职财务顾问来管现金流预测。他们觉得现在规模还不到要买专门工具的时候，而且这个顾问跟了他们好几年，换起来麻烦。"

        2. 提取结果：
        Alternative Approach: Excel \+ 兼职财务顾问
        Usage Context: 客户认为当前规模尚不需要专门工具；与顾问存在长期合作关系，替换成本较高
        Source Perspective: Founder

3. C5存储的竞品信息反映的是客户端用户（Founder）的主观视角，代表其对竞争格局的判断，并非客观的市场评估。AI在调用这些信息时须以此框架呈现（例如："根据您的描述，Salesforce 的劣势在于……"，而非作为客观事实陈述）。

4. C5 与 C6 允许同一信息在两处分别存储，因两者服务于不同检索目的（战术竞品 vs\. 行业结构分析），不视为重复。

#### **分类 C6：波特五力分析（Porter’s Five Forces）**

定义：公司行业竞争格局的结构化分析框架，随对话逐步填充，允许部分完整，五个子维度独立存储。

五个子维度：

\- C6\-1：竞争对手强度（Competitive Rivalry）— 市场中竞争者的数量和激烈程度

\- C6\-2：新进入者威胁（Threat of New Entrants）— 新竞争者进入市场的难易程度

\- C6\-3：买方议价能力（Bargaining Power of Buyers）— 客户对价格和条款的议价能力

\- C6\-4：供应商议价能力（Bargaining Power of Suppliers）— 关键供应商/技术依赖方的议价能力

\- C6\-5：替代品威胁（Threat of Substitutes）— 客户转向完全不同解决方案的可能性

提取 Prompt：

分析以下对话内容，识别与波特五力框架对应的信息，归属到五个维度的一个或多个。
各维度独立存储，未提及的维度可以为空（null）。
若对话新增信息，与已有该维度记录合并补充；若用户明确更正，则覆盖。
输出：

\{

"category": "porters\_five\_forces",

"force": "\<维度标识\>",

"summary": "\<综述\>",

"key\_points": \["\<要点\>"\]

\}

维度标识取值：competitive\_rivalry \| new\_entrants \| buyer\_power \| supplier\_power \| substitutes

各维度示例：

C6\-1 竞争对手强度： 

- 模拟对话：「我们这个赛道有十几家竞争者，大家都在抢同一批客户，价格战很厉害，但我们靠数据深度做出了差异化。」 

- 提取结果：

\{

"force": "competitive\_rivalry",

"summary": "竞争激烈，参与者众多，价格压力大，公司以数据深度差异化",

"key\_points": \["约十几家竞争者", "价格战普遍", "公司差异化方向：数据分析深度"\]

\}

C6\-2 新进入者威胁：

- 模拟对话：「进我们这个赛道门槛挺高的，客户数据迁移成本大，换系统大约要 6 个月，新竞争者不太容易进来。」

- 提取结果：

\{

"force": "new\_entrants",

"summary": "市场进入门槛高，客户迁移成本大，新进入者威胁低",

"key\_points": \["数据迁移成本高", "系统切换约需 6 个月", "对新进入者有天然壁垒"\]

\}

C6\-3 买方议价能力：

- 模拟对话：「我们的客户体量都不大，单个客户占收入比不超过 5%，所以客户议价空间有限，但他们对续约价格越来越敏感了。」 

- 提取结果：

\{

"force": "buyer\_power",

"summary": "单客户收入集中度低，整体议价能力有限，但价格敏感度在上升",

"key\_points": \["单客户收入占比 ≤5%", "续约价格敏感度上升"\]

\}

C6\-4 供应商议价能力： 

- 模拟对话：「我们主要依赖 AWS 的基础设施，如果 AWS 涨价我们很难快速迁移，这是个风险。」 

- 提取结果：

\{

"force": "supplier\_power",

"summary": "关键技术依赖 AWS，迁移成本高，供应商议价能力较强",

"key\_points": \["核心基础设施依赖 AWS", "快速迁移难度大"\]

\}

C6\-5 替代品威胁： 

- 模拟对话：「有些客户会考虑用 Excel 加顾问的组合来替代我们，但规模到一定程度就不够用了。」 

- 提取结果：

\{

"force": "substitutes",

"summary": "替代品威胁主要来自 Excel \+ 顾问组合，但规模限制是天然壁垒",

"key\_points": \["替代方案：Excel \+ 顾问", "规模增长后替代品失效"\]

\}

冲突处理：各维度独立处理。当新信息与现有某维度条目存在矛盾或实质性更新时，更新该维度条目以反映最新理解。部分补充信息（用户补充了新的支撑细节但未推翻原有判断）→ 与已有内容合并追加，不覆盖。

C5 与 C6 允许同一信息在两处分别存储，因两者服务于不同检索目的（战术竞品 vs\. 行业结构分析），不视为重复

#### **分类 C7：战略性挑战**

定义：公司面临的具有持续影响（staying power）的战略问题。存模式，不存一次性事件。战略挑战是最具行动价值的记忆类别之一——知道一家公司长期在为什么挣扎，AI 才能主动给出相关指引、在挑战恶化或好转时及时提示，并把战略建议放在真实的持续障碍上、而非假设场景里。

合格的挑战类型（包含但不限于）：

- 持续的销售效率或 CAC 问题（获客成本与新增 ARR 严重不匹配）

- 对特定目标 ICP 的 GTM 打法迟迟不见起色

- 进入新细分市场时的产品\-市场匹配（PMF）挑战

- 绑定到特定用例或客群的留存 / churn 问题

- 关键职能的团队搭建难题

- 销售过程中反复出现的竞争替换问题

每种情况都存储挑战的性质与背景，不存储触发它的具体事件。

提取 Prompt：

分析以下对话内容，识别公司面临的具有战略持久性的挑战（留存问题、定价挑战、GTM 效率、PMF、CAC/销售效率、关键职能团队搭建、竞争替换等）。

重要区分：

- 应存储：挑战主题（Theme）、受影响的目标客户（ICP Affected）、以及背景描述（Detail）

- 不应存储：具体单次事件的细节

实用判断测试：提取前问一个问题——「这个信息在 3\-6 个月后还会与这家公司的战略对话相关吗？」如果是，存储模式；如果否（属于一次性事件或短期细节），不提取。

持续性阈值：单条消息里一次性提到某个困难，不足以建立战略挑战条目，除非上下文明确表明这是个持续问题（如「我们为这事挣扎了好几个月」）。需要足够的上下文信号，才能把某事归类为有持续性的战略挑战，而非随口一提。

输出：

```Plain Text
{
  "category": "strategic_challenge",
  "theme": "<大模型自主高度概括的战略挑战主题，如：企业级GTM路径失效 / 组织核心管理层断层>",
  "icp_affected": "<受影响的 ICP 标签或名称，若影响全盘/属于内部管理则填 Global>",
  "detail": "<该持续性困境的系统性根源、背景及创始人判断的详细描述>",
  "status": "active | resolved",
  "source_type": "chat_extraction",
  "timestamp": "<抽取时间>",
  "resolved_timestamp": "<标记为已解决的时间，未解决时为 null>"
}
```

挑战解决（Resolution）：当创始人表示某个先前的战略挑战已解决或不再是问题时，更新对应条目的状态。已解决的挑战不删除，而是把 status 置为 resolved 并带上 resolved\_timestamp，让 AI 保留「该挑战曾存在并被处理」的历史背景；同时 AI 不再在未来回复中把已解决的挑战当作当前问题来引用。

冲突与更新处理：当新信息更新或取代某条先前的战略背景时，更新原条目以反映最新理解；任何战略背景始终以最新版本为准。

示例：

- 模拟对话：「我们针对 Enterprise（企业级大客户）这一层客户的 GTM 获客策略完全没有转起来。销售团队进去拉锯三个月，最后发现我们的获客路径太重了，投入产出比根本不对。这应该是个长期的 PMF 问题，导致销售效率异常低下。」

- 输出：

```Plain Text
[
  {
    "category": "strategic_challenge",
    "theme": "企业级客户GTM路径失效及PMF困境",
    "icp_affected": "Enterprise_ICP",
    "detail": "针对企业级大客户的获客路径过重，导致投入产出比失衡、销售效率低下。创始人判断该问题本质上是产品与该新市场缺乏长期 PMF 所致。",
    "status": "active",
    "source_type": "chat_extraction",
    "timestamp": "2026-06-08T10:00:00Z",
    "resolved_timestamp": null
  }
]
```

---

#### **分类 C8：价值主张与 ROI**

定义：产品针对目标客户（ICP）所交付的核心价值主张、竞争差异化特征、购买动机，以及可量化或具规律性的投资回报（ROI）/ 客户成果。当价值主张针对特定 ICP / segment 时，连同其 segment 上下文一并存储；ICP 为关联上下文，非强制分组主键。

**提取 Prompt**：分析以下对话内容，识别产品的价值主张及 ROI 故事。

- **价值主张（Value Proposition）**：明确识别产品解决了什么具体问题（What problem it solves）、产品与市场替代方案或竞品相比有什么独特差异（How it is differentiated）、客户愿意为此付钱的底层原因（Why customers pay for it）、以及产品交付的具体业务结果（What outcomes it delivers）。在此基础上凝练一句话核心主张（`value_statement`）。

- **投资回报（ROI \& Outcomes）**： 

    - 优先提取量化成果：提取对话中提及的任何量化客户成果或 ROI 故事（例如："我们的客户通常可以节省 40% 的处理成本"）

    - 允许提取规律性方向：如果提及非量化但描述了某种持续模式/规律的成果（如："客户在首月内能显著减少手工工作量"），也应予以提取。

- **ICP / Segment 上下文关联**：当价值主张或 ROI 是针对特定 ICP / 客户 segment 描述的，需将其关联的 segment 上下文一并提取存储（记入 `icp_label`，如 `ICP-1`）。若对话未指向特定 ICP，则不强制绑定，`icp_label` 留空。（按英文 AC：each segment\-specific value proposition is stored with its associated customer segment context；ICP 为关联上下文，非强制分组主键。）

- **冲突与版本处理**：当新信息更新或取代某条先前的价值主张 / ROI 条目时，更新原条目以反映最新理解，并防止重复抽取；任何价值主张 / ROI 条目始终以最新版本为准。

**输出 JSON 格式**：

json

```JSON
{
  "category": "value_prop",
  "icp_label": "<关联的 ICP-X 标签；未指向特定 ICP 时留空>",
  "value_statement": "<一句话核心价值主张，格式『为[ICP]提供[独特价值]』；只作整合定位、不展开要素，要素细节归入下方各数组>",
  "problems_solved": ["<产品具体解决的问题>"],
  "differentiation": ["<与替代方案或竞品相比的独特差异点/核心优势>"],
  "buying_reasons": ["<客户选择并为此付费的核心原因>"],
  "outcomes_delivered": ["<交付的具体业务结果（含量化及具规律性的定性成果）>"],
  "roi_stories": ["<具体可量化的 ROI、指标或客户成功案例（过滤掉非重复性个案）>"],
  "source_type": "chat | profile | document",
  "contributor": "<贡献该条目的用户标识>",
  "source_session": "<对应聊天 session id>",
  "created_at": "<创建时间>",
  "updated_at": "<最近更新时间>"
}
```

示例：

- 模拟对话："我们今天刚签了一家 120 人的 SaaS 公司。市面上普通报表工具都得自己配 SQL，我们直接内置了模型，这是他们选我们而不是竞品的原因。用过系统后，他们反馈说最爽的一点是不用再让人工去天天跑离职预测的报表了，直接帮他们减少了 40% 的报表人工成本。对他们这种公司的 CFO 来说，我们卖的就是'数据准确和省心'。我算了一下，这帮 CFO 通常在 6 个月内就能把买软件的钱通过省下的人工完全赚回来。另外上周有个客户说由于他们停电导致系统少算了一天我们还帮他补了，这个就算了不用写进去了。"

- 提取结果：

json

```JSON
{
  "category": "value_prop",
  "icp_label": "ICP-1",
  "value_statement": "为中端 SaaS 的 CFO 提供免配置、省人力的内置模型报表",
  "problems_solved": ["需要人工每日手动跑客户离职预测报表，流程繁琐耗时"],
  "differentiation": ["内置模型，无需客户自行配置 SQL"],
  "buying_reasons": ["追求数据准确性，释放人力以获得省心的管理体验"],
  "outcomes_delivered": ["大幅降低财务/运营团队在报表制作上的人工成本"],
  "roi_stories": [
    "平均减少 40% 的人工报表时间成本",
    "CFO 核心决策层通常可在 6 个月内完全收回软件采购成本（实现 ROI）"
  ],
  "source_type": "chat",
  "contributor": "<示例：company_admin_user_id>",
  "source_session": "<示例：sess_20260612_a1b2>",
  "created_at": "2026-06-12T10:00:00Z",
  "updated_at": "2026-06-12T10:00:00Z"
}
```

#### **分类 C9：****商业与****定价模式**

定义：公司整体的商业模式（如纯 SaaS、平台型、服务\+软件混合等）以及产品定价结构（按座位、按用量、价值定价等）。支持随对话增量补全及历史版本追踪。

提取 Prompt：分析以下对话内容，识别用户描述的商业模式与产品定价机制。杜绝提取针对某一家具体客户（如“给某某客户特批了5折”）的单次销售报价或个别谈判记录。必须提炼为面向市场的通用定价规则。商业或定价模式正在发生“转型、过渡或变化”（Transition/Change）时，更新内容。

- 维度提取：商业模式（Business Model）、定价模式（Pricing Model）、定价细节描述（Pricing Details）

输出：

\{

"category": "pricing\_model",

"business\_model": "\<商业模式，如 SaaS / Hybrid / Marketplace\>",

"pricing\_type": "\<定价类型，如 seat\-based / usage\-based / mixed\>",

"description": "\<具体定价与合同细节描述\>",

"is\_transitioned": false,

"notes": "\<关于模式转型、演进或历史版本交替的备注说明\>"

\}

示例：

- 模拟对话： Jacobo，我们之前一直是一家纯软件 SaaS 公司，按照席位收费，每个席位每月 99 美元。但是我们最近发现这种模式太限制大客户的活跃度了，所以团队决定做定价模式转型：从下个月开始，我们要全面转为‘软件 \+ 按 OCR 识别张数’的混合用量计费模式（Usage\-based），基础包包含 1000 张，超出部分按张扣费，之前的纯座位费就逐步淘汰掉。”

- 提取结果：

\[

\{

"category": "pricing\_model",

"business\_model": "SaaS",

"pricing\_type": "Usage\-based（正在从 Seat\-based 转型）",

"description": "全面转为『软件 \+ 按 OCR 识别张数』的用量计费模式。基础包内含 1000 张，超出后按张扣费。逐步淘汰旧版 $99/席位/月 的纯席位计费。",

"is\_transitioned": true,

"notes": "创始人明确宣布发生定价模式转型，从 $99/月纯席位制全面过渡到按 OCR 识别张数计费的用量模式（Usage\-based）。"

\}

\]

#### **分类 C10：****客户端用户****性格与沟通风格**

定义：从对话中逐步积累的客户端用户领导风格、性格特征和沟通偏好，采用 **DISC 标签体系**进行类型判定，仅供 AI 调整与该用户对话时的回应风格，不对用户展示。

设计思路：

- Evidence 实时提取，每条标注 DISC 类型（D / I / S / C），存入 evidence 列表

\- 标签判定基于**最近 20 条 evidence 的分布**实时计算，每条新 evidence 存入后立即重新评估

- 分主类型（disc\_primary）与次类型（disc\_secondary）两级；副类型仅允许与主类型相邻的 DISC 类型

**DISC 相邻类型说明：**

DISC 四种类型在轮盘上的顺序为 D → I → S → C → D，相邻即紧挨着的类型：

对角组合（D/S、I/C）不设副类型——两者行为规则方向相反，无法有效混合执行。

**DISC 类型与识别信号：**

数据结构：

\{

"category": "founder\_psychographic",

"disc\_primary": "D \| I \| S \| C \| unknown",

"disc\_secondary": "D \| I \| S \| C \| null",

"evidence": \[

\{ "observation": "\<具体行为描述\>", "suggests\_type": "D \| I \| S \| C", "source\_session": "\<session\_id\>", "timestamp": "\<时间\>" \}

\],

"last\_evaluated": "\<上次标签评估时间\>"

,"display\_summary": "\<面向 Company Admin 的展示文字,为一段纯自然语言描述,说明该用户的沟通风格与行为倾向;不包含 DISC 标签\(D/I/S/C\)\>"\}

提取 Prompt（实时提取，每条对话内容产生时触发）：

分析以下对话内容，识别用户表现出的领导风格、沟通偏好、决策方式的具体行为信号。

要求：仅记录有明显行为证据支持的观察，不做主观推断。每条 evidence 描述一个具体行为或表达，不超过一句话。

每条 evidence 必须标注其对应 DISC 类型（D / I / S / C）：

- D：结果导向、决断、直接、不耐铺垫的行为

- I：热情、关系、认可需求、情绪化表达的行为

- S：稳健、抗变化、团队导向、需要安全感的行为

- C：分析、细节、数据追问、追求准确的行为

输出：\[\{ "observation": "\<具体行为描述\>", "suggests\_type": "D \| I \| S \| C" \}, \.\.\.\]

**标签判定规则：**

每条 evidence 存入后，取 evidence 列表中**最近 20 条**（不足 20 条时取全量），统计各类型数量，立即更新标签：

\- disc\_primary：窗口内数量最多的类型，且该类型数量 **≥5**

\- disc\_secondary：窗口内数量第二多的类型，且数量 **≥3**，且为 disc\_primary 的相邻类型

- 主类型未满足条件：disc\_primary = unknown，AI 使用默认中性策略，直接参考原始 evidence 做轻微风格适配

- 次类型未满足条件：disc\_secondary = null，仅执行主类型规则

- 平局：

    - 主类型：两种类型数量相同且均 ≥5，disc\_primary 保持原值，等待下一条 evidence 打破平局;若此时主类型尚未确立过\(原值为 unknown\),则继续保持 unknown,不会一次出现两个主类型。

    - 次类型：两种类型数量相同且均 ≥3，disc\_secondary 保持原值，等待下一条 evidence 打破平局;若此时主类型尚未确立过\(原值为 null\),则继续保持 null,不会一次出现两个次类型。

**展示文字生成:**

当 disc\_primary 首次确定或发生变更时，系统同步生成 display\_summary——将主次类型及相关 evidence综合转化为自然语言的行为倾向描述，供 Company Admin 在 Memory Settings 中查看。展示内容为纯自然语言的行为倾向描述,不展示 DISC 类型标签;主次类型仅用于内部驱动描述文字的生成与 AI 回应风格。

**AI 行为规则（按 DISC 类型）：**

D 型：第一句给结论，不铺垫；回答简短；用主动语态肯定句（“建议做 X”，不是”可以考虑 X”）；不加情感安抚语句；风险和问题直接说，不过度包装。

I 型：先表达共鸣或认可再进入实质内容；用案例和故事替代数字罗列；保持轻松语气，适当使用积极词汇；建议用”很多成功的公司也在做……“而非直接引用数据；负面信息用”值得关注的机会点”表达。

S 型：变化或建议要充分铺垫原因和影响；给出具体下一步减少模糊感；语气稳定，避免紧迫或冲击性措辞；强调延续性（“这和你们目前在做的方向一致……”）；负面信息配合”过渡路径”一起给出。

C 型：回答逻辑严密附明确来源或依据；避免笼统表达（不说”通常”“一般来说”，要说”在 X 条件下”）；主动说明假设前提和局限性；给出结构化分析（分点、分步骤）；不省略细节，宁可多说也不留模糊空间。

**复合类型处理（disc\_primary / disc\_secondary）：**

副类型只允许出现相邻组合（D/I、D/C、I/S、S/C 及其反向），对角组合（D/S、I/C）不设副类型。

### 2\.4 上传文档摘要

本节说明 Source C（文档上传）在写入 Layer 1a 时的文档处理细节。通用的触发节点、归属绑定、元数据与 RAG 并行处理见 2\.2 Source C；本节按文件类型分两类说明各自的处理逻辑。两类文件的共同骨架如下。

共同骨架（两类文件均适用）：

- 双流程并行： 

    - 一是 RAG 索引——将文档全文处理后存入 Layer 1a 向量库，使其在当前及未来所有会话中可被动态检索（用户无需重新上传或引用），目标 30 秒内完成；

    - 二是记忆摘要——AI 通读全文，自动生成一份「公司相关关键认知」的高层摘要，作为一条 Layer 1a 记忆条目存储，附带元数据（来源类 document summary、文档名称、文件类型、时间戳、上传人、对应聊天 session）。

- RAG 作为主检索机制：query 时直接对 RAG 全文索引检索，不走摘要；摘要仅作辅助上下文，帮助 AI 定位相关文件、辅助生成回应，但不对 RAG 检索做门槛或过滤。因摘要无法涵盖文件全部内容，若要求「先命中摘要才检索文件」会导致未被摘要捕捉的内容静默不可达，故所有检索一律直接走 RAG，摘要在旁提供补充上下文。

- 无公司相关内容的处理：仅当文件完全不含任何 company\-relevant 内容时才不生成摘要；此时文件仍可在 chat 会话中经 RAG 检索，但不出现在 Memory Settings 面板。无摘要不是错误状态，无需通知用户。

- 数据隔离：通过 chatbot 上传的文档不导入 LG、不进入财务数据管线，仅用于丰富 AI 记忆，需与 Manual Upload OCR（进财务数据）严格区分。

- 失败处理：文档过大、加密、损坏等无法处理时，静默记日志，并在聊天界面给用户一条优雅的内联提示，聊天正常继续。

- 范围说明：本节为后端处理逻辑；上传界面、文件类型校验、上传回执属于前端 UI 范畴，不在本节。

#### 类型一：叙述型文本文档（LG\-1388，PDF / Word / 纯文本）

适用文件：\.pdf、\.docx、\.txt。即叙述性、散文型文本。

典型场景：导出为 PDF 的 pitch deck、Word 格式的董事会纪要或 memo、战略规划文档、投资人更新、Fireflies 导出的纯文本会议转录、公司介绍或定位文档。

处理要点：

- 完整索引：多页 PDF、多段落 Word 须完整索引，不能因文档长而截断；Fireflies 的 \.txt 转录须全文保留。

- 摘要质量标准：以聊天抽取（Source B）的分类（C1–C10）作为优先提取目标，引导摘要优先识别公司事实、战略背景、ICP 信号、竞争提及等信息；但不以分类为边界，凡有意义的 company\-relevant 内容均应纳入摘要并存储，而非丢弃。排除通用模板话术、标准法律措辞、格式噪声。

#### 类型二：结构化表格数据（LG\-1428，Excel / CSV）

适用文件：\.xlsx、\.xls、\.csv。即行列、表头、数值构成的结构化表格数据，处理逻辑须专门为表格设计，与叙述型文本根本不同。

典型场景：尚未录入 LG 的财务表（历史 actuals、forecast、operating model）、KPI 跟踪表、pipeline 与营收导出；以及非财务表格，如客户名单、产品目录、市场细分表等。

处理要点：

- 文件范围（重要）：Excel/CSV 不限于财务数据文件。非财务表格（如客户名单、产品目录、市场细分表等）同样进行 RAG 索引与摘要，用户选择分享的任何上下文都应用于丰富 AI 对公司的理解。财务解析逻辑、账户映射、指标归一化绝不施加于非财务文件。

- 索引保留结构：RAG 索引须正确保留行列表头与数值的对应关系，使 AI 能准确回答如「三月营收是多少」这类问题；Excel 多 sheet 须全部索引，不只第一个 sheet；须优雅处理合并单元格、用作分隔的空行、小计与合计行、非标准表头位置。

- 摘要范围（只记录内容、不做分析）：结构化文件的摘要只记录「文件包含什么」，不做分析性解读。具体捕捉：覆盖的时间段（如适用）、文件中存在的数据类别或指标、以及有助于 AI 理解「这是什么文件、何时该检索它」的高层结构上下文。趋势分析、成本结构分析等任何分析性推导，明确不在摘要阶段进行——这些分析在 query 时由 AI 检索相关数据（RAG）后完成。摘要不解读、不推导洞见，只描述数据的结构与内容。

- 财务管线隔离（强调）：须显式声明该文件内容可供聊天引用，但未导入 LG 财务数据；隔离须写死，不触发任何归一化、映射、写操作。

- 解析容错：CSV 非标准分隔符（分号、tab）须能自动探测并正确解析。

## 三、Layer 1b — 管理端记忆文件

### 3\.1 用户权限矩阵

|角色|贡献写入|AI 调取使用|UI 查看|
|---|---|---|---|
|Company User|否|否|否|
|Company Admin|否|否|否|
|PM / PGM / Super Admin|是（通过聊天、文档上传）|是（同时读取 1a \+ 1b）|是（只读）|

安全约束：Layer 1b 的存在不得通过任何系统响应、UI 元素或聊天回答暴露给公司端用户，包括通过精心构造的 prompt 进行注入攻击，必须在架构层面强制隔离。

### 3\.2 写入来源（Sources）与触发节点

Layer 1b 没有 Source A Company Profile 来源（仅 Layer 1a 有）。

#### **Source**** B****：管理端聊天对话（Chat Session）**

- 触发节点：与 Layer 1a 相同。

- 公司归属判断：管理端聊天为全局入口，不绑定特定公司。系统通过**上下文智能推断**判断归属：

    - AI 分析本次 Session 的对话内容，识别对话中明确提及或可以确定指向的具体公司（如公司名称、创始人姓名、已知数据等可识别特征）。

    - 若可确定唯一归属公司 → 提取内容写入该公司的 Layer 1b。

    - 若无法确定（跨公司对比讨论、通用问答、无公司上下文）→ 本次 Session 内容不进行 memory 提取，仅作为聊天历史保存；AI 仍可正常回答，但无任何 memory 写入。

    - 推断过程在后台执行，不向用户展示推断依据，不要求用户做任何确认操作。

- 排除内容：完整对话原文、通用问答、事务性交流。

#### **Source**** C****：文档上传（Document Upload，PM 端）**

- 触发节点：管理端用户上传文件时立即触发。

- 公司归属流程： 

    - 上传时，AI 根据当前 Session 的对话上下文推断该文件可能归属的相关公司，提交用户确认。

    - 若用户确认推断的公司 → 文件归属该公司。

    - 若 AI 无法推断出公司 → 由用户自行选择归属公司；用户选择后归属该公司。

    - 若用户不确认 AI 的推断、也不自行选择公司 → 视为无公司归属的文件，仅归属到上传人本人。

    - 归属推断基于 Session 内对话上下文，不单独对文件内容做公司识别推断。

- 文件处理模型（与 Layer 1a 一致，管理端语境）： 

    - 管理端通过聊天上传的文件，全部进入知识库并进行 RAG 索引；记忆摘要是独立且有条件的步骤。

    - 是否进入知识库、是否 RAG 索引：所有文件一律进入、一律索引，不设门槛。

    - 是否生成记忆摘要：仅当文件同时满足「已归属具体公司」且「含合格的公司相关内容」时，才生成摘要并写入该公司的 Layer 1b。以下两种情况均不生成摘要（但文件仍进入知识库、仍可 RAG 检索）：一是无公司归属的文件（仅归属到上传人）；二是已归属具体公司、但不含值得存储的公司相关内容的文件。

    - 可见性与 RAG 权限：归属到具体公司的文件，按该公司角色权限可见、可 RAG；仅归属到上传人的文件，仅上传人可见、可 RAG。RAG 检索权限与知识库可见性一致。

### 3\.3 内容分类及提取 Prompt

Layer 1b 沿用与 Layer 1a 相同的内容分类\(C1–C9\),但不包含 C10。各分类的定义、提取标准及冲突处理规则与 Layer 1a 相同，Prompt 措辞调整为管理端视角（即投资经理对该公司的观察」，而非「用户自述」）。

**通用说明：**

- 提取来源为管理端用户（PM/PGM/Super Admin）在聊天或上传文档中对该公司的描述、判断、评估。

- C1–C9的提取逻辑、字段结构、冲突处理均与 Layer 1a Section 2\.3 一致，此处不重复列出，开发可复用同一套提取引擎。

- 主要差异：Layer 1b 中的信息来自管理端外部观察视角，Layer 1a 中的信息来自公司端自述视角。两者独立存储，AI 在对 管理端用户回答时同时读取，差异本身具有价值，不合并消除（见 Section 4\.3）。

**以下为各分类在 Layer 1b 语境下的 Prompt 调整说明：**

C1–C2（公司基础事实 / 数据更正）：将 Prompt 中「用户」替换为「投资经理」，适用场景为管理端用户在聊天中补充或更正该公司在 LG 中的基础信息。

C3–C9（人员组织 / ICP / 竞争对手 / 波特五力 / 战略挑战 / 价值主张 / 定价模式）：将 Prompt 中「用户描述」替换为「投资经理对该公司的观察或判断」，其余字段结构不变。

## 四、冲突解决策略

这个策略内部开发的时候使用不给客户

### 4\.1 记忆文件内部冲突与冗余处理

本节处理记忆文件内部的冲突与冗余，分以下几类。涉及记忆与 LG 原始数据的冲突（C1 对 Company Settings 的更正、C2 对财务数据的更正）见 4\.2。

**第一类：同层、同源、同分类内部**

新抽取若与已有条目矛盾或实质更新它，则更新该条目以反映最新信息，并防止重复抽取。旧值不另外保留版本历史。若新内容同时适用于多个源对应的条目，则相关条目一并更新。

例外——战略挑战（C7）：当创始人表示某挑战已解决时，不删除该条目，而是将其标记为 resolved 并带时间戳，保留「该挑战曾存在并被处理」的历史背景；AI 不再在未来回复中把已解决的挑战当作当前问题引用。

**第二类：同层、跨分类的内容重叠（如竞争格局 C5 与波特五力 C6）**

各分类独立填充，不互相自动更新。提取逻辑按陈述意图路由——是战术性竞争观察（竞争格局）还是结构性行业评估（波特五力），分别归入对应分类。某条陈述确实同时符合多个分类时，在各分类分别建立条目。此类冗余是预期且可接受的，不作为数据完整性问题处理，因为各条目服务于不同的检索目的；AI 回答时多条均可被引用并呈现。

**第三类：同层、两个用户提供源之间的矛盾（聊天 Source B 与文档 Source C，且均非覆盖式更新）****~~（待PDM确认）~~**

~~当两个用户提供源对同一事实给出不同值、且无一方构成对另一方的覆盖更新时，系统无法判定谁更准确，两个值并存并标注来源；AI 回答时同时呈现两者、说明来源差异，引导用户澄清，而非替用户选定。~~

~~建议处理方式（待 PDM 确认）：抛给用户后，依据用户回应分别处理——~~

- ~~用户确认其中一个、否定另一个：被确认的值保留，被否定的值标记为失效／存疑。若被否定的是文档（Source C）的值，该判定仅记录在聊天抽取（Source B）侧，文档来源条目本身不动，即聊天抽取不反写文档条目。~~

- ~~用户表示两个都不对并给出新值：新值生效，原两个值标记失效。~~

- ~~用户表示两个都不对但未给新值：两个值均标记为失效／存疑，暂无有效值。~~

- ~~用户未表态：维持两个值并存现状。~~

当两个用户提供源对同一事实给出不同值，两个值并存并标注来源；AI 回答时同时呈现两者、说明来源差异。MVP 不对该类冲突做进一步处理。即两个值始终并存，AI 在回答时一并呈现并提示来源差异；系统不依据用户的后续回应去做"确认其一／否定其一／给出新值／标记失效"等自动判定与状态变更。

**第四类：跨层冲突（Layer 1a vs Layer 1b）**

不做跨层去重。Layer 1a 记录公司侧用户所述，Layer 1b 记录投资经理（PM）所述或评估，两者视为有意的「双视角」并存——相同、互补、分歧三种情况均有效，不合并、不消除。AI 在对投资经理回答时同时读取两层，当存在分歧时如实呈现差异，而非择一消除（如「该公司创始人表示…从投资经理的评估／财务数据来看…」）。

**展示的 AI 措辞约束（贯穿全节）**

凡需同时呈现多个来源或多条记忆时，AI 须以自然语言融合呈现，不暴露记忆层级或系统来源名称（不出现「Layer 1a／1b」「Source A／B／C」「记忆来源 A 是…」这类生硬措辞），而以业务语言区分（如「系统记录…您此前提到…」「该公司创始人表示…从投资经理的评估来看…」）。

### 4\.2 记忆文件与 LG 数据冲突（Memory vs\. LG Structured Data）

~~原则：记忆文件中的更正与 LG 原始数据独立并存，不发生直接覆盖、不写回原始源。此原则适用于 C2（对财务数据的更正）和 C1 中对 Company Settings 字段的更正／补充。~~

~~示例（财务，C2）： \- 用户曾告知 2025 年 7 月 ARR 为 120 万（LG 中存的是 95 万） \- 用户问：「我们 7 月的 ARR 达标了吗？」 \- AI 回答：「根据您上次提供的更新值，您 7 月的 ARR 为 120 万美元。LG 系统中记录的为 95 万美元。」~~

~~示例（Company Settings，C1）： \- 用户在聊天中说：「我们其实已经不只做医疗了，现在主营是金融科技。」（LG Company Settings 中行业仍为「医疗」） \- AI 后续涉及行业时：「根据您最近提供的信息，贵公司目前主营金融科技。LG 系统中记录的行业为『医疗』。」~~

**~~更正的时效性~~**~~：待PDM确认点~~

~~用户可直接在 LG 中编辑原始数据（更新 Company Settings 字段或财务数据）。~~

- ~~需明确：当用户后续在 LG 中更新了原始数据后，记忆中的更正条目是否失效、是否仍优先于新的原始值。~~

- ~~判断新旧的难点（财务数据）：若以时间戳判断更正与原始数据的新旧：~~

    - ~~这个可以适用于C1的补充更正优先级校验。~~

    - ~~但是，需注意财务数据存在版本粒度问题。例如 Committed Forecast 为年版本、共用一个版本时间戳：用户先更正了 2026\-02 的某数据点（写入记忆），其后手动更改了该年版本中 2026\-07 的数据（未改动 2026\-02），但年版本时间戳整体更新。此时若按年版本时间戳判断「原始数据比更正更新」从而作废更正，会误删仍然有效的 2026\-02 更正。正确处理需能~~**~~下钻到月度~~**~~数据点级别的时间戳进行比对，而非使用年版本整体时间戳——此能力是否可实现需开发评估。~~

原则：记忆文件中的更正与 LG 原始数据独立并存，不发生直接覆盖、不写回原始源。此原则适用于 C2（对财务数据的更正）和 C1 中对 Company Settings 字段的更正／补充。

只要记忆文件中存在对某数据点的更正或补充，AI 即优先采用记忆中的值，并在回答中标注其与 LG 原始记录的差异；LG 原始数据保持不变。

### 4\.3 记忆文件与知识库冲突（Memory vs\. Layer 2 Knowledge Base）

原则：不视为「冲突」，而是「通用 → 个性化」的适配关系。Layer 2 是通用模板，Layer 1a/1b 是该公司的个性化参数，AI 应以公司 Memory 过滤 Layer 2 的通用建议后再输出。

|场景|处理方式|
|---|---|
|Layer 2 提供通用建议，与公司实际情况不符|AI 先检索 Layer 2 通用知识，再用 Layer 1a/1b 中的公司上下文进行个性化适配，输出定制化建议|
|Layer 2 建议与记忆文件描述有明显差异|在回答中同时呈现通用建议和个性化调整，清晰说明差异来源|
|Layer 1b 评估与 Layer 1a 内容有分歧|视为有意的「双视角」，两层分别代表公司端自述与管理端外部观察，差异本身有价值，不合并，不消除|

示例 A — Layer 2 建议与公司实际情况不符： \- Layer 2 建议：「提高客户留存的通用方法是加强客户成功团队的主动触达频率。」 \- Layer 1a 记录：该公司目标客户（ICP\-1）是 50\-200 人的 B2B SaaS 公司，过去尝试过高频触达但反馈认为打扰过多。 \- AI 回答：「GS Playbook 建议通过加强客户成功团队的主动触达来提升留存率。结合您目标客户（ICP\-1）的反馈，频繁触达可能适得其反，建议调整为按关键节点触达（如合同续签前 60 天、季度业务回顾），而非高频主动联系。」

示例 B — Layer 1b 评估与 Layer 1a 内容有分歧： \- Layer 1a（公司端自述）：「我们的 GTM 效率非常高，销售周期平均只有 30 天。」 \- Layer 1b（管理端观察）：「从财务数据来看，该公司的销售周期实际接近 60 天，公司端描述的 30 天可能是最优情况下的数据。」 \- AI（对 PM）回答：「公司创始人表示其销售周期平均 30 天。但投资经理表示从财务数据分析来看，实际周期更接近 60 天，建议下次会面时就这一差距做深入了解。」



## 五、客户提供的示例问题

1. **Company / Founder User Questions** 

    1. **Pricing Strategy**

        1. "How should I think through a price increase? What type of pricing is appropriate for me with my customers?"

        2. *Expected chatbot behavior:* Walk the founder through an exercise to calculate 4\-6X ROI for their customer by ICP, arrive at an optimal price point, and connect it to benchmark data showing whether a price increase would bring them back into benchmark range

    2. **Sales Efficiency Improvement**

        1. "My sales efficiency is $1\.80\. Best practice is $1\.10 and the benchmark in Looking Glass shows $0\.85\. How do I get to $0\.85? How is that possible?"

        2. *Expected chatbot behavior:* Ask questions about current go\-to\-market tactics, team size, org structure, weekly KPIs and achievement against them\. If the go\-to\-market appears to be functioning well, guide the founder to conclude the root issue is pricing rather than execution

    3. **Forecast Discrepancy**

        1. "The system\-generated forecast shows I'm running out of cash at the end of the year, but my own forecast shows I'm not\. What am I missing?"

        2. *Expected chatbot behavior:* Ask about pipeline assumptions — how much is known with confirmed dates vs\. assumed\. Surface whether the founder's forecast relies on achieving top\-decile sales efficiency they have not historically demonstrated\. Guide them to reconcile the two

    4. **Operational / Team Incentives**

        1. "How do I incentivize my team to better achieve my plans?"

        2. *Expected chatbot behavior:* Provide guidance from the GS knowledge base on team performance, accountability structures, and incentive frameworks

    5. **Benchmark Context and Strategy**

        1. "I'm at P5 on sales efficiency and P5 on growth rate, but my strategy is to grow slower and be profitable\. What should I do about being P5? Are there ways to grow revenue without growing expenses?"

        2. *Expected chatbot behavior:* Explore options — most likely a price increase or a channel partner strategy to grow pipeline without increasing S\&M spend

2. **Portfolio Manager / Admin User Questions** 

    1. **Forecast Reliability Assessment**

        1. "How often does this management team achieve their committed forecast? How often do they achieve their system\-generated forecast?"

        2. "How does their forecast accuracy change at 1 month out, 2 months out, 6 months out, 12 months out? Does it tend to increase or decrease over time?

        3. *Expected chatbot behavior:* Surface historical forecast accuracy and predictability metrics to help the portfolio manager assess how reliable the team's planning and execution are

    2. **Top Portfolio Performers**

        1. "Who are my top performing companies and why?"

        2. *Expected chatbot behavior:* Return a ranked answer — e\.g\., "It's Company A, Company B, and Company C because they systematically increase their 12\-month forecast and hit the increase with 85% accuracy\. They are also top decile on sales efficiency, gross margin, growth rate, and profitability"

    3. **Best Practice Identification and Knowledge Base Export**

        1. "What activities can we suspect the top performers are doing that we can export to other portfolio companies?"

        2. "What questions should we go ask them to improve our knowledge base?"

        3. *Expected chatbot behavior:* Surface hypotheses about what makes top performers best\-in\-class, recommend setting up a meeting with them, and note that the recorded meeting would go into the knowledge base pending portfolio admin ratification

# 任务流程拆分


1. 客户端基于LG系统的数据指标的问答（需要确定问答哪些数据，原因范围不确定意味着回答数据不稳，第一版需要圈定一个大概范围）

2. 客户端公司setting数据实现记忆保存以及问答查询

3. 客户端公司聊天对话实现记忆保存以及问答查询

    1. 上面10个点每个都要有单独的任务

4. 客户端公式文件上传实现问答

5. 管理端基于LG系统的数据指标的问答

6. 管理端公司setting数据实现记忆保存以及问答查询

7. 管理端公司聊天对话实现记忆保存以及问答查询

    1. 上面9点每个都要有单独的任务

8. 管理端公式文件上传实现问答

9. 管理端个人文件知识库

10. 组织层级知识库





记忆数据类型




