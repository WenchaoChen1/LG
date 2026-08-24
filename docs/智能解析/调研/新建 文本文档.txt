# Opus 4.7 vs Sonnet 4.6 vs GPT-5.5 vs Gemini 3.5 Flash —— 短边压缩 7 档实测对比

> 配套文档：`image_tease.md`（长边压缩 Opus 详细分析）、`short_side_image_tease.md`（短边压缩 Opus 详细分析）。
> 本文做**四方模型对比**：同一组短边压缩 7 张图，分别用 `anthropic/claude-opus-4.7`、`anthropic/claude-sonnet-4.6`、`openai/gpt-5.5`（`gpt-5.5-20260423`）、`google/gemini-3.5-flash`（`gemini-3.5-flash-20260519`），对比 token / cost / wall / 准确率。

## 0. TL;DR（一句话）

**Sonnet 4.6 综合最优：最便宜（~$0.07）+ 准确率最稳（7/7 全对）+ 无 reasoning 浪费。Gemini 3.5 Flash 紧随其后（~$0.077、7/7 全对），但 reasoning token 极重导致 3/7 撞 max_tokens、必须调高上限。Opus 速度最快（33s）但短=600 翻车。GPT-5.5 最贵 + 最慢 + 短=500 出危险的多位数字错误，本用例无优势。**

| 维度 | Opus 4.7 | Sonnet 4.6 | GPT-5.5 | Gemini 3.5 Flash | 赢家 |
|---|---|---|---|---|---|
| 平均单图 cost | $0.153 | **$0.070** | $0.161 | $0.077 | **Sonnet** |
| cost 高分辨率端（3024） | $0.173 | **$0.072** | $0.255 | $0.071 | **Sonnet/Gemini** |
| Cell 准确率 | 6/7（短=600✗） | **7/7** | 6/7（短=500✗） | **7/7** | **Sonnet/Gemini** |
| Stage 1 分类 | 7/7 ✓ | 7/7 ✓ | 7/7 ✓ | 7/7 ✓ | 持平 |
| 平均总 wall | **33s** | 38s | 54s | 40s | **Opus** |
| input token @3024 | 17,982 | 11,909 | 31,129 | **9,679** | **Gemini** |
| reasoning tokens | 0 | 0 | 1,100-2,100 | **3,800-6,200** | Opus/Sonnet |
| 撞 max_tokens=8192？ | 否 | 否 | 否 | **是（3/7）** | 其它三家 |
| 输出 JSON 格式 | 干净 ✓ | 栅栏 ✗ | 干净 ✓ | 干净 ✓ | Opus/GPT/Gemini |

**结构性洞察（input token 随分辨率的扩展行为，三家厂商三种策略）：**
- **Anthropic（Opus/Sonnet）**：服务端下采样到 ~1.15 MP，input token 高分辨率端**封顶**（Sonnet @3024 = 11,909）
- **Google（Gemini）**：封顶更狠，input token **几乎完全不随分辨率变**（全 7 档都 ~9,680，最低）
- **OpenAI（GPT-5.5）**：**tile-based、不封顶**，input token 随像素线性暴涨（@3024 达 31K，是 Gemini 的 3.2×）

**对可能上传高清图的 OCR 场景，GPT 成本扩展性最差；Anthropic / Google 都封顶。**

## 1. 测试设置

- **数据**：`2020 P&L Summary.xlsx` 第一个 sheet（21 行 × 2 列）
- **图源**：openpyxl + PIL 渲染的 master 4032×3024 PNG，LANCZOS 降到其它档
- **短边档**：3024 / 2048 / 1536 / 1024 / 768 / 600 / 500（共 7 张，跟 `short_side_image_tease.md` 完全一致）
- **流程**：复用项目同款 prompts（`IDENTIFY_FINANCIAL_STATEMENT_*` + `IDENTIFY_DATA_VALUES_*`），调用走 `llm.raw_router.complete(model=..., provider=Provider.OPENROUTER)` —— 显式传 model，不依赖 `vision_complete` 的硬编码默认
- **并发**：ThreadPoolExecutor 7 个 worker 同时跑 7 张图（Sonnet 41.6s / GPT-5.5 66s 完成全部）
- **Cache bust**：每次注入唯一 `<test_run_id>UUID</test_run_id>` 到 system prompt 头部
- **max_tokens（stage 2）**：从 production 默认 98,304 限到 8,192（避开 OpenRouter daily 限额；实测 output 用量 ~2.4-3.4K，缓冲足够）
- **价位估算**（OpenRouter list price，因 `raw_router` 返回的 `cost_usd=None`，按 token × 单价估算）：
  - Opus 4.7：$15/M input + $75/M output（这批 Opus JSON 里有 OpenRouter 实返 cost，直接用）
  - Sonnet 4.6：$3/M input + $15/M output（估算）
  - GPT-5.5：$5/M input + $30/M output（估算，从 1-token 探活返回的 cost_details 反推：prompt $0.00004/8tok、completion $0.00015/5tok）
- **vision_complete 默认 model**：本 session 依次改过 `llm/core.py` 里的硬编码（Opus → Sonnet → **当前 GPT-5.5**）。本测试本身不依赖它（显式传 model）。
- **Opus / Sonnet baseline**：复用本 session 早先跑的历史 JSON（`results/` + `results_sonnet/`）。

> **⚠️ 公平性 caveat：prompt 在三次跑之间有漂移**。GPT-5.5 跑时 `IDENTIFY_DATA_VALUES_USER_PROMPT` 已新增「多页 batch context」段（`batch_index` / `batch_total` / `page_numbers_in_batch` 占位符，单图场景填 0/1/[1]），比 Opus/Sonnet 跑时多 ~200 prompt tokens。对 input token 的影响 < 2%（相对 ~10K image tokens），不改变结论量级，但严格对比时需知晓。Stage 1 prompt 也新增了 `is_continuation_of_previous` 输出字段。

## 2. 主对比表（3 模型 × 7 档）

`输入 / 输出 / reason`= input / output / reasoning tokens。reasoning 已含在 output 内（GPT-5.5 才非零）。

| 短边 cap | 实际尺寸 | 模型 | 输入 | 输出 | reason | 合计 | Cost | Wall(s) | Cell | Stage1 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 3024 | 4032×3024 | Opus | 17,982 | 3,319 | 0 | 21,301 | $0.173 | 36.0 | 17/17 | Actuals ✓ |
| | | **Sonnet** | 11,909 | 2,425 | 0 | 14,334 | **$0.072** | 38.1 | **17/17** | Actuals ✓ |
| | | GPT-5.5 | 31,129 | 3,312 | 1,998 | 34,441 | $0.255 | 59.1 | 17/17 | Actuals ✓ |
| | | Gemini | **9,679** | 6,291 | 3,836 | 15,970 | $0.071 | 37.8 | **17/17** | Actuals ✓ |
| 2048 | 2731×2048 | Opus | 18,433 | 3,319 | 0 | 21,752 | $0.175 | 38.5 | 17/17 | Actuals ✓ |
| | | **Sonnet** | 11,911 | 2,425 | 0 | 14,336 | **$0.072** | 39.5 | **17/17** | Actuals ✓ |
| | | GPT-5.5 | 20,617 | 2,430 | 1,116 | 23,047 | $0.176 | 61.5 | 17/17 | Actuals ✓ |
| | | Gemini | **9,689** | 6,356 | 3,925 | 16,045 | $0.072 | 34.3 | **17/17** | Actuals ✓ |
| 1536 | 2048×1536 | Opus | 16,652 | 2,684 | 0 | 19,336 | $0.150 | 32.5 | 17/17 | Actuals ✓ |
| | | **Sonnet** | 11,909 | 2,425 | 0 | 14,334 | **$0.072** | 37.0 | **17/17** | Actuals ✓ |
| | | GPT-5.5 | 14,759 | 2,755 | 1,441 | 17,514 | $0.156 | 51.8 | 17/17 | Actuals ✓ |
| | | Gemini | **9,689** | 5,873 | 3,445 | 15,562 | **$0.067** | 38.2 | **17/17** | Actuals ✓ |
| 1024 | 1365×1024 | Opus | 12,591 | 3,372 | 0 | 15,963 | $0.147 | 33.9 | 17/17 | Actuals ✓ |
| | | **Sonnet** | 11,909 | 2,425 | 0 | 14,334 | **$0.072** | 36.8 | **17/17** | Actuals ✓ |
| | | GPT-5.5 | 10,701 | 3,292 | 1,978 | 13,993 | $0.152 | 54.0 | 17/17 | Actuals ✓ |
| | | Gemini | **9,681** | 8,665 | 6,237 | 18,346 | $0.093 | 41.7 | **17/17** | Actuals ✓ |
| 768 | 1024×768 | Opus | 10,576 | 2,678 | 0 | 13,254 | $0.120 | 28.4 | 17/17 | Actuals ✓ |
| | | **Sonnet** | 10,857 | 2,425 | 0 | 13,282 | $0.069 | 37.3 | **17/17** | Actuals ✓ |
| | | GPT-5.5 | 9,241 | 3,416 | 2,102 | 12,657 | $0.149 | 66.0 | 17/17 | Actuals ✓ |
| | | Gemini | 9,685 | 8,186 | 5,734 | 17,871 | $0.088 | 46.0 | **17/17** | Actuals ✓ |
| **600** | **800×600** | Opus | 11,559 | 2,748 | 0 | 14,307 | $0.127 | 29.4 | **16/17 ✗** | Actuals ✓ |
| | | **Sonnet** | 10,047 | 2,413 | 0 | 12,460 | **$0.066** | 41.6 | **17/17 ✓** | Actuals ✓ |
| | | GPT-5.5 | 8,539 | 2,713 | 1,399 | 11,252 | $0.124 | 45.9 | 17/17 ✓ | Actuals ✓ |
| | | Gemini | 9,681 | 6,886 | 4,455 | 16,567 | $0.077 | 42.5 | **17/17 ✓** | Actuals ✓ |
| **500** | **667×500** | Opus | 11,139 | 3,376 | 0 | 14,515 | $0.140 | 32.7 | 17/17 | Actuals ✓ |
| | | **Sonnet** | 9,647 | 2,425 | 0 | 12,072 | **$0.065** | 37.6 | **17/17** | Actuals ✓ |
| | | GPT-5.5 | 8,207 | 2,420 | 1,106 | 10,627 | $0.114 | 40.7 | **15/17 ✗** | Actuals ✓ |
| | | Gemini | 9,691 | 6,513 | 4,085 | 16,204 | $0.073 | 40.6 | **17/17 ✓** | Actuals ✓ |

> Gemini 3 张（3024/2048/1024）首轮 stage2 用 max_tokens=8192 被 reasoning 撑爆（`LengthFinishReasonError`），表中数据是 max_tokens=16384 补跑的结果。

**平均 cost / wall：**

| 模型 | 平均 cost | cost 范围 | 平均总 wall | Cell 全对档数 | reasoning |
|---|---:|---|---:|---:|---:|
| Opus 4.7 | $0.153 | $0.120 - $0.175 | **33s** | 6/7 | 0 |
| **Sonnet 4.6** | **$0.070** | $0.065 - $0.072 | 38s | **7/7** | 0 |
| GPT-5.5 | $0.161 | $0.114 - $0.255 | 54s | 6/7 | 1.1-2.1K |
| Gemini 3.5 Flash | $0.077 | $0.067 - $0.093 | 40s | **7/7** | 3.8-6.2K |

## 3. 成本分析（按生产场景外推）

按本测试平均单图成本估算 monthly cost（假设平均分辨率混合）：

| 月调用量（张图） | Sonnet | Gemini | Opus | GPT-5.5 |
|---:|---:|---:|---:|---:|
| 1,000 | **$70** | $77 | $153 | $161 |
| 10,000 | **$702** | $772 | $1,532 | $1,609 |
| 100,000 | **$7,020** | $7,720 | $15,320 | $16,090 |

**Sonnet 和 Gemini 是第一梯队（~$0.07-0.08），Opus 和 GPT-5.5 贵一倍多（~$0.15-0.16）。**

**高分辨率场景（手机原图 12 MP / 高 DPI 扫描）单图成本对比，差异更明显：**
- Gemini：~$0.071（input 封顶最狠 ~9.7K，但 output 因 reasoning 偏高）
- Sonnet：~$0.072（input 封顶 ~12K，output 无 reasoning）
- Opus：~$0.173（input 封顶 ~18K）
- GPT-5.5：**$0.255 且无上限**（tile-based，4032×3024 input 飙到 31K）

> **cost 结构差异（重要）**：
> - Sonnet 便宜靠「中等 input + 低 output（无 reasoning）」
> - Gemini 便宜靠「极低 input」但被「极高 reasoning output」抵消大半
> - Opus / GPT-5.5 贵在 input 单价高（$15/$5 per M）
>
> 注：production 实际单图 cost 可能更高（stage 2 max_tokens 本测试限到 8192-16384，production 默认 98,304；多页 PDF 线性扩展）。Gemini / GPT-5.5 的 reasoning tokens 已计入估算。

## 4. 准确率深度对比

### 4.1 Cell-level（数值识别）—— 三个模型在不同分辨率翻车

| 模型 | 全对档数 | 翻车档 | 错误形态 |
|---|---:|---|---|
| **Sonnet 4.6** | **7/7** | 无 | —— |
| **Gemini 3.5 Flash** | **7/7** | 无 | —— |
| Opus 4.7 | 6/7 | **短=600 (0.48 MP)** | `$548,522` → `548.522`（千位逗号误识为小数点，2/2 复现） |
| GPT-5.5 | 6/7 | **短=500 (0.33 MP)** | `Other G&A Expenses` 26426 → **264626**（多插一位数字）；`Office Lease` 39662 → 39682（6→8 误读） |

**三个观察：**

1. **Sonnet 和 Gemini 是仅有的两个全对模型** —— 包括 Opus 翻车的短=600 和 GPT 翻车的短=500，两者都对。共同点：**两者都做了推理**（Sonnet 写 chain-of-thought 文字前缀、Gemini 烧 3.8-6.2K reasoning tokens），让模型有机会做 context-aware sanity check（"Software License Revenue = $548 不合理，应是 $548,522"）。**推理在低分辨率 OCR 边界上确实换来了准确率** —— 但 Sonnet 用的是"轻量 CoT"（几百 token），Gemini 用的是"重量 reasoning"（数千 token），后者代价大得多却没换来更高准确率。

2. **每个失败模型的分辨率 / 形态都不同**：
   - Opus 在 0.48 MP 栽在「逗号 vs 小数点」（字符形近混淆）
   - GPT-5.5 在 0.33 MP 栽在「数字位数」（`264626` 多插一位 + `39682` 误读单字）
   - 印证 `short_side_image_tease.md` 的结论：**低分辨率 OCR 失败是「不同特征在不同分辨率失效」的离散事件，不是单调过程，且跟模型强相关**。

3. **GPT-5.5 的 `264626` 错误最危险**：多插一位数字让金额翻 10 倍（26K → 264K），且不像 `548.522` 那样能靠「数值不合理」直觉发现 —— 264626 本身是个看似合理的数。**这种错误最难在下游 sanity check 拦住。**

### 4.2 Stage 1（报表类型分类）

**四个模型 7/7 全部判出 `Actuals` ✓**。本次短边测试范围（0.33-12.19 MP）内没有任何模型触发 Stage 1 误分类。（注：Opus 在 `short_side_image_tease.md` 里 long=768 / 0.44 MP 那档曾 2/2 误判 Proforma，但那是不同图源的渲染路径，不在本次对比范围内。）

## 5. Wall time 分段对比（识别耗时）

按 stage 拆分的总 wall（identify_statement = stage 1，identify_data_values = stage 2）：

| 短边 cap | Opus | Sonnet | GPT-5.5 | Gemini |
|---|---:|---:|---:|---:|
| 3024 | 36.0 | 38.1 | 59.1 | 37.8 |
| 2048 | 38.5 | 39.5 | 61.5 | 34.3 |
| 1536 | 32.5 | 37.0 | 51.8 | 38.2 |
| 1024 | 33.9 | 36.8 | 54.0 | 41.7 |
| 768 | 28.4 | 37.3 | 66.0 | 46.0 |
| 600 | 29.4 | 41.6 | 45.9 | 42.5 |
| 500 | 32.7 | 37.6 | 40.7 | 40.6 |
| **平均** | **33.1** | 38.3 | 54.2 | 40.2 |

Stage 1（分类）耗时对比（最能区分模型「思考开销」）：

| | Opus | Sonnet | GPT-5.5 | Gemini |
|---|---:|---:|---:|---:|
| 平均 Stage 1 wall | **4.4s** | 12.3s | ~13s | ~12s |

**关键观察：**

1. **Opus Stage 1 最快（~4.4s）** —— 严格 `json_mode`，直接吐 `{is_financial,...}` 不加推理。其它三家分类前都「思考」：Sonnet 写 CoT 文字、GPT-5.5 + Gemini 烧 reasoning tokens。对一个只需输出 ~30 token 的二元分类，全是过度思考。
2. **GPT-5.5 总 wall 最慢（54s，比 Opus 慢 64%）** —— reasoning + 高分辨率 input token 双重拖累。
3. **Sonnet（38s）/ Gemini（40s）居中**。Gemini 虽然 reasoning token 最多（3.8-6.2K），但 input token 最低，且 Google 推理速度快，所以总 wall 没被拖到 GPT 那么慢。
4. 四者 Stage 2 都在 22-55s 区间，输出量大稀释了模型差异。

**延迟敏感场景（交互式上传 + 即时识别）选 Opus；批处理不敏感。**

## 6. 输出格式差异：只有 Sonnet 需要剥 markdown 栅栏

| 模型 | json_mode 行为 | 调用方处理 |
|---|---|---|
| Opus 4.7 | 严格只返回裸 JSON | 直接 `json.loads` ✓ |
| **Sonnet 4.6** | **JSON 外包 ```json 栅栏**，低分辨率还加 CoT 前缀 | **必须剥栅栏** ✗ |
| GPT-5.5 | 严格只返回裸 JSON（`{"cells":[...` 开头） | 直接 `json.loads` ✓ |
| Gemini 3.5 Flash | 严格只返回裸 JSON（`{\n  "cells":[...` 开头） | 直接 `json.loads` ✓ |

**四个模型里只有 Sonnet 即使设了 `json_mode=True` 仍然把 JSON 包 markdown 栅栏 + 短=600 还加 chain-of-thought 前缀**（详见下方实例）。Opus / GPT-5.5 / Gemini 都严格遵守 json_mode、直接吐裸 JSON。

实例（Sonnet 实际响应原文头部）：

```
```json
{
  "cells": [
    {
      "row_position": 1,
      "column_position": 1,
      ...
```

更糟的是 **short=600 这一档 Sonnet 还加了 chain-of-thought 推理前缀**：

```
I need to analyze this P&L statement and extract leaf data cells, skipping aggregate/summary rows.

**Identifying rows to skip (aggregate/blacklist):**
- "Total Base Business Revenue" — contains "total"...
...

```json
{
  "cells": [...]
}
```
```

**调用方处理对策（已加进 `run_sonnet_sweep.py` 的 `extract_json` helper）：**

```python
def extract_json(text: str):
    """3 级 fallback parse。"""
    s = text.strip()
    # 1) 整串就是单个 ```json ... ``` block
    m = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```$", s, re.DOTALL)
    if m:
        try: return json.loads(m.group(1).strip())
        except: pass
    # 2) 文本中嵌入了 ```json ... ``` block（CoT 前缀场景）
    m = re.search(r"```(?:json)?\s*\n(.*?)\n```", s, re.DOTALL)
    if m:
        try: return json.loads(m.group(1).strip())
        except: pass
    # 3) 兜底：第一个 { 到最后一个 }
    i, j = s.find("{"), s.rfind("}")
    if i >= 0 and j > i:
        try: return json.loads(s[i:j+1])
        except: pass
    return None
```

**如果切换生产到 Sonnet**：项目里现有的 `_parse_json_response` 解析逻辑（在 `nodes/financial_extract_helpers.py` 之类的位置）需要相应加固。

## 7. 其它有趣观察

1. **input token 随分辨率的扩展行为，三家厂商三种策略**（最重要的结构性发现）：
   - **Anthropic（Opus/Sonnet）：下采样到 ~1.15 MP，input token 高分辨率端封顶**。Sonnet 在 3024/2048/1536/1024 四档 input 完全一致（11,909-11,911，差 ≤ 2）。
   - **Google（Gemini）：封顶最狠，input token 几乎完全不随分辨率变**——全 7 档（0.33-12.19 MP）input 都在 9,679-9,691，差 ≤ 12 token。**Google 把任何图都压到同一个极低的内部 token 预算。**
   - **OpenAI（GPT-5.5）：tile-based 编码，不封顶，input token ~线性随像素涨**：8,207（0.33MP）→ 31,129（12.19MP），3.8 倍。
   - 含义：**上传高清图时，GPT 成本暴涨；Anthropic / Google 封顶不变**。要在 GPT 上控成本必须客户端先压图。

2. **reasoning token 是新的隐藏成本维度**（区分老模型 vs 新 reasoning 模型）：
   - Opus / Sonnet：reasoning = 0（传统模型）
   - GPT-5.5：1.1-2.1K reasoning/调用
   - **Gemini 3.5 Flash：3.8-6.2K reasoning/调用（最重）**——这些 token 按 output 价计费、却不进最终 JSON，是纯成本。对「答案确定」的结构化抽取基本是浪费。Gemini 的「flash」之名容易误导——它 reasoning 烧得最凶，并不轻量。

3. **Gemini reasoning 溢出 max_tokens 是真实运维坑**：8192 的 stage2 上限被 3/7 图撑爆（`LengthFinishReasonError`）。**用 Gemini 必须把 max_tokens 调到 ≥16384**，否则高 reasoning 场景直接报错丢数据。其它三家在 8192 下都没问题。

4. **Sonnet output_tokens 极稳定 = 2,425**（7 档里 4 个完全相同）。Opus ~24% 波动，GPT/Gemini 因 reasoning 波动更大。

5. **输出格式**：只有 Sonnet 包 markdown 栅栏；Opus/GPT/Gemini 都吐裸 JSON。Sonnet 低分辨率还偶发无效 UTF-8 字节（需 `errors='replace'`）。

6. **`cost_usd` 字段**：项目 `raw_router` 对四个模型都返回 `cost_usd=None`（OpenRouter cost 字段没被 provider 实现层解析）。本文 cost 全按 list price 估算。要真实 cost 看 OpenRouter dashboard。

## 8. 推荐 / 决策矩阵（四方）

| 业务诉求 | 推荐 | 原因 |
|---|---|---|
| **成本敏感**（月 > 10K calls） | **Sonnet 4.6** | 最便宜（$0.07）+ 准确率最高 + 无 reasoning 浪费 |
| **数值准确率优先**（金额密集 / 易混字符） | **Sonnet 4.6 / Gemini 3.5 Flash** | 唯二 7/7 全对；Opus 栽逗号、GPT 栽多位数字 |
| **上传高清图**（手机原图 / 高 DPI 扫描） | **Gemini / Sonnet / Opus**（避开 GPT） | 前三家 input token 封顶；GPT tile 编码成本暴涨（$0.26/图） |
| **延迟敏感**（交互式即时识别） | **Opus 4.7** | Stage 1 最快（4.4s）+ 总 wall 最快（33s）。GPT 最慢（54s） |
| **strict JSON output** | **Opus / GPT / Gemini** | 都吐裸 JSON；只有 Sonnet 必须剥栅栏 |
| **选 GPT-5.5？** | **不推荐** | 最贵 + 最慢 + 低分辨率出危险的多位数字错误，无一项领先 |
| **选 Gemini 3.5 Flash？** | **可选第二梯队** | 准确率 7/7 + cost 接近 Sonnet，但 reasoning 极重（需调高 max_tokens）、wall 略慢 |

**针对 CIOaaS-python 项目的核心建议（四方综合）：**

**首选 Sonnet 4.6** —— 最便宜 + 准确率最高 + 无 reasoning 浪费 + 无 max_tokens 溢出风险。唯一代价是切换前要做两件加固：

1. **加固 JSON 解析**：加 markdown fence-stripping + CoT 前缀剥离（第 6 节 `extract_json` 的 3 级 fallback）。Sonnet 下 `json_mode=True` 不保证裸 JSON。
2. **延迟预算**：`AI_REQUEST_TIMEOUT_SECONDS=120` 仍够；若有「Stage 1 < 5s」SLA 要去掉（Sonnet Stage 1 ~12s）。

**Gemini 3.5 Flash 作为备选第二梯队** —— 准确率同样 7/7、cost 接近，但如果采用**必须把 stage2 `max_tokens` 调到 ≥16384**（reasoning 太重会撑爆 8192），且延迟略高于 Sonnet。

**GPT-5.5 不建议**（最贵 + 最慢 + 危险的多位数字错误）；**Opus 4.7 保留给延迟敏感的交互式路径**（Stage 1 最快）。

## 9. 复现

```bash
# vision_complete 默认 model 本 session 改过 4 次：
#   source/llm/core.py  Opus → Sonnet → GPT-5.5 → 当前 "google/gemini-3.5-flash"
# 测试本身不依赖它（显式传 model）

cd D:/workspace/github/CIOaas-python

# Sonnet sweep（早先跑的，用专用脚本）
uv run python C:/Users/Administrator/Desktop/ocr_test_file/run_sonnet_sweep.py
#   → image_test/results_sonnet/short<cap>.json

# 通用 sweep（GPT-5.5 / Gemini 用这个；--model 可换任意 OpenRouter 模型）
uv run python C:/Users/Administrator/Desktop/ocr_test_file/run_model_sweep.py \
  --model openai/gpt-5.5 --out-subdir results_gpt55
uv run python C:/Users/Administrator/Desktop/ocr_test_file/run_model_sweep.py \
  --model google/gemini-3.5-flash --out-subdir results_gemini
#   ⚠️ Gemini 高 reasoning 会撑爆 stage2 max_tokens=8192；3/7 图用 16384 补跑
```

**实测原始数据**：
- Opus：`image_test/results/*.json`
- Sonnet：`image_test/results_sonnet/short*.json`
- GPT-5.5：`image_test/results_gpt55/short*.json`
- Gemini：`image_test/results_gemini/short*.json`

（每个 JSON 含完整 token 拆分 + reasoning tokens + cells + raw content；cost 为 list-price 估算）。
