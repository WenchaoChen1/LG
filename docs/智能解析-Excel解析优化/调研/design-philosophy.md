# Excel 解析优化 · 设计理念（WHY）

> 关联文档: [Python 端设计](./python-design.md) · [前端设计](./frontend-design.md) · [代码示例](./code-examples.md)
> 上游文档: [智能解析 Python 端设计](../../智能解析/调研/python-design.md) · [智能解析系统架构](../../智能解析/调研/system-architecture.md) · [Excel 科目父链交由代码计算设计稿](../../superpowers/specs/2026-08-03-excel-account-label-join-in-code-design.md) · [trace 分析与耗时优化方案](../../../CIOaas-python/docs/2026-07-27-智能解析trace分析与耗时优化方案.md)
>
> 日期: 2026-09-08 · 状态: 调研结论，待负责人就 §六 拍板 · 范围: CIOaas-python Excel/CSV 轨；Java 零改动；前端仅"跳过可见"

## 一、要回答的问题

用户问题：AI 解析 Excel 时遇到合并单元格或数据量很大，怎么把 Excel 交给 LLM，最终拿到想要的数据？

"想要的数据"是确定的：按 `(lg_category, YYYY-MM)` 聚合、只取最细粒度叶子行、写入 `fi_*` 两张表（Actuals → FinanceManualData，Proforma → FinancialForecastHistory），15 个 LG 科目 + UNMAPPED，中间态是 cell 级 `ai_financial_extraction_mapping_data`，前端 DataMappingPanel 按 `(task, source_row_id)` 渲染供人工审核。任何"换一种喂法"的方案都必须落回这份契约。

## 二、结论

Excel 轨今天的做法（渲染成带 rowspan/colspan 的 HTML 透传 LLM，超预算按行切片，LLM 逐 cell 转录）方向没错，业界证据也支持 HTML 是合并单元格场景最稳的喂法。真正的问题是三件：

1. **超限 sheet 静默丢弃**：>2000 行的 sheet 置空后跳过，文件仍 REVIEW_READY、0 行，DB/API/UI 无任何信号。
2. **LLM 转录数值让墙钟与成本随列数线性膨胀**：抽取墙钟 ≈ 输出 token ÷ 110 tok/s，每 cell 约 28 token；60 列 × 300 行的表推算 37 个 chunk、约 20 分钟、约 15 美元。
3. **合并块归并与父级链仍靠 LLM 推断**：代码只坍缩"源 A 列、稀疏互补"一种形态，其余合并块与父级链由 LLM 按缩进/rowspan/样式推断，错了静默。

推荐路线：**P0** 先把"跳过"做成用户可见并修几处死分支与真缺口（.xls、坍缩标签列、cs 头带回、cache 预热）；**P1** 重拾已经落地又被整树回退的"稳定行 id + 代码父链 + 精简出参 + 代码回填值"主线，这是唯一同时解"合并"与"大表"的路线；**P2** 视产品口径再看 GL 流水聚合轨。逐项落地步骤见 [Python 端设计](./python-design.md) §六。

## 三、三条原则

1. **确定性优先**：凡 openpyxl/pandas 能从 sheet 结构算出来的——行身份、父级链、合并块归并、期间列 → 月份、单元格数值——都在代码里做完；LLM 只剩语义活：哪些行是叶子条目、每行归哪个 lg_category（含 pf/cf）、哪些列是期间列。原因是 LLM 做"执行算法"的事出错静默且不可复现，提示词为防它偏离算法已累积大段规则（§4.6.3 父链规则即典型）。
2. **可见性先于扩边界**：任何新闸门（列宽上限、Plan D 可达、预算收紧）上线前，"被跳过 / 被截断 / 部分失败"必须能被用户看到；否则新闸门只是把静默换个位置。
3. **金样本闸门**：改抽取行为必须拿同一批真实报表跑两轮逐 cell diff（`shared.py` docstring 已如此要求）。当前仓库没有任何 xlsx fixture，设计稿的 912/912 交叉校验脚本在仓库外——把它们脚本化入仓是 P1 的前置。

## 四、业界证据如何影响选择

| 证据 | 对本项目的含义 |
|---|---|
| HTML 带 span 对合并单元格检测 76.67%，为各格式最优（Table Meets LLM，GPT-3.5 时代）；但 token 约 CSV 的 3 倍 | 保留 HTML 作为结构载体；不要把"省 token"的期望放在换输入格式上 |
| 新一代模型上 HTML 与 Markdown 差距缩到 1 到 2 个百分点 | 输入格式之争已不重要，收益在**输出侧**：让 LLM 少输出 |
| SpreadsheetLLM/SheetCompressor 压缩 25 倍，但格式聚合丢确切数值 | 只能用于分类/定位阶段，抽取阶段禁用 |
| LLM + 代码执行对同构大表（GL 流水）远优于全表直读（TableRAG 49.2% vs 4.6%），但对层级/转置表脆弱（PyAgent 转置 −77.73%） | GL 与财报应分轨：GL 走代码聚合，财报走结构展开 + 文本直读 |
| Anthropic Files API 不接受 xlsx 作 document 块；1M 上下文有 context rot | "把 xlsx 直接扔给模型"不成立，Stage 0 渲染省不掉；窗口够大不等于可以整表塞入 |
| Docling/Unstructured/MarkItDown 等开源转换器要么丢 span，要么把合并区变 NaN | 不能替代 Stage 0；只借鉴其"空白间隙切子表 + 锚点记 span"思路 |

来源 URL 见 [Python 端设计](./python-design.md) §九。

## 五、否决的方案与理由

三视角对抗验证（可落地 / 准确率 / 成本，各 1 到 5 分）后不推荐：

| 方案 | 均分 | 否决理由 |
|---|---|---|
| duckdb 工具智能体（ReAct 只读 SQL 探索大表并 emit） | 2.3 | ReAct 仅 async 而抽取图全同步；`DBRouterChatModel` 不透传 max_tokens/cache；run_sql 限 50 行与 emit 300 行自相矛盾；LLM 亲手转录聚合值 100 科目 × 12 月约 34k token、5 分钟，240 s 预算算不过账；GL 按月 SUM 对 7 个 BS 科目得到发生额而非余额，静默错值 |
| 合并块 LLM 微裁决（对未坍缩块发无数值微调用问语义） | 2.7 | "双列分类法 vs label-merge"轴代码已确定性判定（`_is_col0_label_merge`），LLM 再判是冗余并新增出错面；"稠密块求和 vs 子项"轴又刻意不给数值失去判据；自设闸门把整列稠密块（主要目标）全部判 unknown |
| map-reduce 的"上一片尾部叶子行"语境 + LLM reduce 归一遍 | 3.0 | 尾部叶子行不携带父级名，解不了 17/24 无缩进 sheet 的父链断裂；reduce 让看不见结构信号的模型凭语义改父链，与提示词 §4.6.3"禁止凭语义猜父级"正面冲突。仅保留其中"chunk≥1 带回年份/季度 cs 头"这一便宜正向的半边 |
| 分类锚点采样替代前 200 行截断 | 3.7 | 技术可行、成本中性，但要解决的"财务表落在 200 行之后"在语料与生产日志里无一例实证；先用 classify 日志量化频率，为真再做 |

## 六、未决问题（需负责人拍板）

1. **回退原因**：`ac5fdb28` / `d9118cca` 把 optimize 线整树回退，提交信息只写"暂不上 main"；P1 重拾这条线前需确认不是"代码算父链 / 代码取值"路线本身被否决。
2. **GL 流水口径**：是否允许把 GL 派生的科目月度聚合行入库？若允许，BS 科目按发生额还是必须有期末余额？≤2000 行 GL 当前被分类判"非财务报表"拒收，>2000 行若走聚合轨则同类文件两种结果，分类政策需统一。
3. **金样本**：提交 `860439cb` 的 18 文件/35 sheet 语料与设计稿的 12 个真实 Excel 是否仍在开发机？能否脱敏入仓作回归基线？
4. **用户可见文案归属**：跳过/告警文案由 Python 直出（现状口径）还是按 `user-input-requirements.md` R-2.2 交 Java 生成？
5. **钱与时间的取舍**：cache 预热省约 73% 分类输入成本但墙钟 +4 s；抽取并发 4→8 只降时延不降成本；预算三档 A/B（500/1600/3000）用哪批样本、以什么指标放行。
6. **生产模型配置**：测试环境曾跑 fable-5（抽取单价翻倍、耗时不变）；确认各环境 `OCR_CLASSIFY_MODEL` / `OCR_EXTRACT_MODEL` 实际配置。

## 七、本文来源与置信度

- 材料：5 路并行现状阅读（合并单元格、大数据量、LLM 契约、Java/前端/需求、外部调研）→ 4 位设计者共 23 个方案 → 11 个方案完成三视角对抗验证（其余 12 个因额度中断，结论按同机制族推断，正文标"未验证"）→ 人工核对全部关键断言的代码位置。
- 所有"文件:行号"引用基于 CIOaas-python `sprint117` 分支 HEAD `2d0cab55`（2026-09-07）。
- 标注"推算"的数字（37 chunk / 20 分钟 / 15 美元等）由实测单价（约 110 tok/s、约 28 token/cell、单 chunk 均值 95 s / 0.39 美元）线性外推，未在生产复现。
