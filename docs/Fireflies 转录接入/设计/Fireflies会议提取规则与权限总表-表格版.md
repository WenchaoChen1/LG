# Fireflies 会议提取规则与权限总表

> 整理日期：2026-09-29
>
> **角色**：创始人 = Company Admin + Company User；PM = Portfolio Manager；PGM = Portfolio Group Manager；SA = Super Admin。
>
> **查看位置**：**会议管理页** = Fireflies Management → Summary Records → Review 详情的 Content Routing Matrix；**原始转录页** = Fireflies Management → Raw Data。
>
> **产出格式**：所有产出均为 markdown，统一经大模型生成或整理；ff自带的摘要也过一遍大模型产出 markdown。


# rag 各角色权限现状
| 角色 | 知识库 | summary | playbook |
|---|---|---|---|
| 公司端普通用户 | **Goldie**：本公司 APP 空间里自己上传的文件<br>**知识库页**：本公司由公司端上传的文件中自己的那些，只能下载自己的 | **Goldie**：自己上传文件的摘要<br>**Memory 页**：没有入口，直输地址提示无权限 | **Goldie**：打开 Playbook 开关后可用，全平台同一份 |
| 公司端 Company Admin | **Goldie**：本公司 APP 空间的全部文件，不含管理端为本公司上传的<br>**知识库页**：本公司由公司端上传的全部文件，可按上传者筛选、可下载 | **Goldie**：本公司由公司端上传的文件的摘要<br>**Memory 页**：本公司的 Company Memory | 同上 |
| 管理端 | **Goldie**：本组织的 ADMIN 空间，加上可见公司各自的 APP 空间；只召回属于可见公司的文件和本会话的文件<br>**知识库页**：选定组织下可见公司的文件（公司端、管理端上传的都有），可按公司、来源、上传者筛选；超管可下载任意公司的文件 | **Goldie**：可见公司的文件摘要（公司端、管理端上传的都算），加本会话文件<br>**Memory 页**：Company Memory 和 Portfolio Memory 两层，可按层、公司筛选 | **Goldie**：同上<br>**devSupport**：可维护（抓取、审核、发布） |
| devSupport 使用者（在自己角色之外额外能看） | 全部空间的条目和正文，可跨空间做召回测试 | 条目详情、分段弹窗、召回结果里都有 summary | Playbook 空间的内容；维护操作仍只限管理端账号 |

# 会议提取规则与权限

| 会议类型 | 去向 | 提取规则 | 去逐字化 | 敏感信息处理 | 谁能看、在哪看 |
|---|---|---|---|---|---|
| **所有类型** | 原始转录（永久留存，不进向量库） | 带时间戳、说话人的完整逐字稿 | ❌ 原文 | ❌ | 管理端 PGM/Super Admin：原始转录页（Raw data）<br>公司端：原始转录只有参会人本人可看 |
| **GS→Founder** | 1a + 1b（同一份） | **来源**：Fireflies返回的summary.overview（为空时从原文生成）<br>**处理**：经大模型整理为 markdown，≤1000 字符，超长的在这一步一并压缩<br>**粒度**：1a 与 1b 用同一份文本 | ✅ 摘要定稿后过 n-gram 剔除 | 创始人已经参与会议，不做敏感信息过滤 | 公司端：Goldie<br>PM:Goldie<br>PGM/Super Admin: Goldie、会议管理页 |
|  | Founder KB、Portfolio KB（同一份） | **来源**：Fireflies summary.overview（Fireflies 生成的会议摘要）<br>**处理**：经大模型整理为 markdown<br>**粒度**：管理端公司端关联同一份 | ✅ | 创始人已经参与会议，不做敏感信息过滤 | 公司端：Goldie、Founder KB<br>PM：Goldie、Portfolio KB<br>PGM/Super Admin：Goldie、会议管理页、Portfolio KB |
|  | Cross-Company（0~N 条） | **抽取**：可移植洞察点，每场 0~N 条，产出 0 条属正常<br>**判据**：脱离这家公司仍然成立，且对相似阶段的其他公司有参考价值<br>**标签**：行业/垂直、公司阶段（ARR 区间、轮次）、问题类型<br>**需管理员审核**：Cross company 内容需要审核后发出 | ✅ | [去身份] | PGM/Super Admin：Goldie、会议管理页；<br>PM、公司端：Goldie |
| **GS→LP** | 1b（按正文提到的公司拆分，只采高置信） | **基金层**：组合（基金）级别摘要，归到 GS 基金实体（Fund II / Fund III / Credit Fund）：募资进度、基金整体回报、LP 结构与关切<br>**公司层**：按正文提到的**被投公司**拆分，每家一条，只采高置信识别：交易事实（被兜售、估值、买方、价格、时间表）、LP 对该公司的评价、GS 的退出计划与估值判断 | ✅ | 是 [交易敏感] 的唯一去处；提到其他被投公司时剥掉对方标识 | PM：Goldie<br>PGM/Super Admin：Goldie、会议管理页 |
|  | Portfolio KB（管理端知识库） | **来源**：同 1b（基金层 + 公司层）<br>**形式**：markdown，管理员可打开、编辑；附原始转录链接，不复制原文 | ✅ | 同 1b | PM：Goldie、管理端知识库<br>PGM/Super admin：Goldie、管理端知识库、会议管理页 |
|  | 专家证词（匿名版 + 署名版） | **抽取**：融资（融资轮次、估值预期、资金用途）、市场（市场环境、行业规模、竞争格局）、估值倍数（P/E、P/S、EV/EBITDA 等）<br>**附带**：发言人角色标签、时间戳、按会议日期回溯的专长标签<br>**版本**：匿名版 + 署名版，正文相同，只差首行来源<br>**关键词**：Fundraising、Market、Multiples | ✅ | [去身份] + [LP 保密] + [保密过滤]；<br>交易事实不进证词 | PM/公司端：Goldie（匿名版）<br>PGM/Super admin：Goldie（署名版）、会议管理页（两版各一行） |
|  | Cross-Company（一份匿名版） | **抽取**：仅市场趋势：行业新技术、需求偏好变化、竞争对手动向、政策法规变化<br>**判据**：只留可复用、可跨场景迁移的趋势；排除单一客户、单一项目、一次性交易<br>**标签**：行业/垂直、公司阶段（ARR 区间、轮次）、问题类型<br>**关键词**：Market Trends、Portable Trends Only、Live-deal Quarantined | ✅ | [去身份] + [LP 保密] + [保密过滤] + [在途隔离] | PGM/Super admin：Goldie、会议管理页；<br>PM、公司端：Goldie |
| **GS Internal** | 1b（按正文提到的公司拆分） | **粒度**：按正文提到的公司拆分，每家一条，只采高置信识别<br>**抽取**（只抽结论）：GS 对该公司的判断与评估、决定采取的动作、风险评估结论、资源投入决定、具体交易事实<br>**不抽**：讨论过程、谁说了什么、分歧、未形成结论的讨论 | ✅ | [交易敏感] 只落这里 | PM、Company Admin：Goldie<br>PGM/Super admin：Goldie、会议管理页 |
|  | Portfolio KB（管理端知识库） | **来源**：同 1b<br>**形式**：markdown，管理员可打开、编辑；附原始转录链接，不复制原文 | ✅ | 同 1b | PM：Goldie、管理端知识库<br>PGM/Super admin：Goldie、管理端知识库、会议管理页 |
|  | Cross-Company | **战略-决议闭环**：战略方向 → 待解决问题 → 最终决策 → 行动项与负责人，写明推进了什么、达成什么共识、谁跟进<br>**全公司视角**：GS 内部跨部门、跨业务线的全局看法与共识，不写单个团队的细节<br>**标签**：行业/垂直、公司阶段（ARR 区间、轮次）、问题类型<br>**关键词**：Strategy-Resolution Loop、Firm-wide Views | ✅ | [去身份] + [在途隔离]（设计有意加严） | PGM/Super admin：Goldie、会议管理页；<br>PM、公司端：Goldie |
| **GS→External Partner**（战略+退出合并） | 1b（按正文提到的公司拆分） | **粒度**：按正文提到的公司拆分，每家一条，只采高置信识别<br>**抽取**（以退出为主轴）：交易事实、退出计划与时间表、买方意向与估值判断<br>**不入**：与退出无关的商业合作、采购内容（按可移植趋势进 Cross-Company） | ✅ | [交易敏感] 只落这里；整条默认扣留，经 Pending Assignment 放行 | PM：Goldie<br>PGM/Super admin：Goldie、会议管理页 |
|  | Portfolio KB（管理端知识库） | **来源**：同 1b<br>**形式**：markdown，管理员可打开、编辑；附原始转录链接，不复制原文 | ✅ | 同 1b：默认扣留，经 Pending Assignment 放行 | PM：Goldie、管理端知识库<br>PGM/Super admin：Goldie、管理端知识库、会议管理页 |
|  | 专家证词（两版，与 LP 共用一个库） | **抽取**：商业采购行为（采购流程、预算负责人、销售周期、ACV、价格敏感度）、软件使用（采用、替代、AI 采纳）、估值倍数（按行业、增长、规模）、买方行为（谁在买、收购意愿、尽调重点、交易结构）、退出趋势（时机、流程、earnout、PE/IPO 窗口）<br>**附带**：发言人角色标签、时间戳、按会议日期回溯的专长标签<br>**版本**：匿名版 + 署名版，正文相同，只差首行来源<br>**关键词**：Commercial Buying Behavior、Software Usage、Multiples、Buyer Behavior、Exit Trends | ✅ | [去身份] + [LP 保密]；<br>交易事实不进证词 | 公司端：Goldie（匿名版）<br>PM、PGM、Super admin：Goldie（署名版）、会议管理页（两版各一行） |
|  | Cross-Company | **抽取**：市场趋势（技术、需求、竞争、政策）、商业趋势（盈利模式、定价、渠道转化、客户采购行为）<br>**判据**：只留可迁移的趋势；每场都按在途交易处理，能指向特定公司的内容一律不进<br>**标签**：行业/垂直、公司阶段（ARR 区间、轮次）、问题类型<br>**关键词**：Market Trends、Commercial Trends、Portable Trends Only、Live-deal Quarantined | ✅ | [去身份] + [在途隔离·每场都适用] + [LP 保密] + [保密过滤]<br>能指向特定公司的内容一律不进，匿名了也不行 | PGM/Super admin：Goldie、会议管理页；<br>PM、公司端：Goldie |
| **未分配**（Pending） | — | 参会人与公司归属照常识别；不提取内容，等人工指定会议类型后再提取 | — | — | PGM：会议管理页，指定类型 → 首次提取（Authorize 默认不勾）→ Confirm & Apply Routing |
