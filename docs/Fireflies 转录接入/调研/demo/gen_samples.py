# -*- coding: utf-8 -*-
"""由 2026-09-18/20 落盘的原始返回，生成接口返回样例文档。不调用任何接口。"""
import io, json, re

SRC = ""   # 原始返回与本脚本同目录（四个 json 不入库，见 .gitignore）
MID = "01KZYS4QBCSC54X8BTSB6G9Y35"
STR_MAX, ARR_MAX = 240, 3

def L(f): return json.load(io.open(SRC + f, encoding="utf-8"))

def trim(x, path=""):
    """截断长字符串与长数组，保留结构。"""
    if isinstance(x, str):
        if len(x) > STR_MAX:
            return x[:STR_MAX] + "…〖截断，全长 %d 字符〗" % len(x)
        return x
    if isinstance(x, list):
        out = [trim(v, path) for v in x[:ARR_MAX]]
        if len(x) > ARR_MAX:
            out.append("…〖截断，共 %d 项〗" % len(x))
        return out
    if isinstance(x, dict):
        return {k: trim(v, path + "." + k) for k, v in x.items()}
    return x

def block(obj):
    return "```json\n" + json.dumps(trim(obj), ensure_ascii=False, indent=2) + "\n```"

def trim_mcp_text(raw, keep_sentences=6):
    """MCP 纯文本：保留全部标签行，Sentences 段只留前 N 行。"""
    lines, out = raw.split("\n"), []
    in_sent = False
    kept = 0
    label = re.compile(r"^[A-Z][A-Za-z ]{0,30}:")
    for ln in lines:
        if ln.startswith("Sentences:"):
            in_sent = True; kept = 1; out.append(ln); continue
        if in_sent:
            if label.match(ln) and not ln.startswith("["):
                in_sent = False
                out.append("…〖Sentences 截断，全段共 %d 行〗" % sum(1 for l in lines if l.startswith("[")))
                out.append(ln); continue
            if kept < keep_sentences:
                out.append(ln); kept += 1
            continue
        out.append(ln)
    if in_sent:
        out.append("…〖Sentences 截断，全段共 %d 行〗" % sum(1 for l in lines if l.startswith("[")))
    return "\n".join(out)

# ---- 四份数据 ----
gql_list_all = L("ff_full.json")["data"]["transcripts"]
gql_list = next(t for t in gql_list_all if t["id"] == MID)
gql_detail = L("gql_detail_full.json")
mcp_list = L("ff_mcp_list2.json")[0]
mcp_detail = L("ff_mcp_tr.json")["_raw"]

W = []
w = W.append

w("""# Fireflies 会议接口返回样例（四份）

> 关联文档: [API 能力与数据质量调研](./fireflies-api-capability-survey.md)（结构对比见其附录 B）、[实测脚本](./demo/README.md)

> **用途**：并排看清同一场会议在四个接口下**返回什么结构、装什么值**。字段层面的逐项差异表在调研文档附录 B，本文件不重复，只放实际返回。
>
> **数据来源**：2026-09-18 / 09-20 实测落盘的原始返回，**未重新调用接口**（两条通道共用 50 次/天配额）。
>
> **样本会议**：`%s` — LG Weekly Business Requirements Discussion，2026-08-21，48 分钟，2 位说话人，504 句。
> 该会归属 API key 账号，经 `shareMeeting` 分享给 OAuth 账号后，两条通道取的是**同一场会**，故可直接对照。
>
> **截断规则**（原文太长，按统一规则压缩，均已就地标注）：
> - 字符串超过 %d 字符 → 截断并标 `…〖截断，全长 N 字符〗`
> - 数组超过 %d 项 → 保留前 %d 项并标 `…〖截断，共 N 项〗`
> - MCP 纯文本的 `Sentences:` 段只留前几行，其余标注行数
>
> 未截断处即为**原样返回**，包括 `null`、空数组和 MCP 的占位文案。

## 0. 四份样例速查

| # | 通道 | 接口 | 序列化 | 本文件 |
|---|---|---|---|---|
| 1 | GraphQL | `transcripts`（列表） | JSON，字段由查询指定 | [§1](#1-graphql-列表transcripts) |
| 2 | GraphQL | `transcript`（详情） | JSON，字段由查询指定 | [§2](#2-graphql-详情transcript) |
| 3 | MCP | `fireflies_get_transcripts`（列表） | JSON（`format:"json"`），**固定 10 字段、驼峰命名** | [§3](#3-mcp-列表fireflies_get_transcripts) |
| 4 | MCP | `fireflies_get_transcript`（详情） | **纯文本**，无 `format` 参数 | [§4](#4-mcp-详情fireflies_get_transcript) |

对照时最值得注意的三处：**① 命名风格**（GraphQL 下划线 vs MCP 驼峰）、**② 空值表达**（`null` vs `No audio url` 这类占位文案）、**③ 逐句粒度**（GraphQL 每句一个 8 字段对象 vs MCP 压平成一行文本）。

---
""" % (MID, STR_MAX, ARR_MAX, ARR_MAX))

w("""## 1. GraphQL 列表（`transcripts`）

**请求**

```graphql
query { transcripts(limit: 50) {
  id title dateString date duration privacy transcript_url
  participants speakers { name }
  meeting_attendees { displayName email }
  summary { ... } sentences { ... }
} }
```

一次返回 43 场；下面是其中样本会议那一条。**列表与详情同为 `Transcript` 类型**，所以 `sentences`、`summary` 可以直接写进列表查询——这正是 GraphQL 只需 1 次调用的原因。

**返回**（顶层 %d 个字段：%s）

%s

---
""" % (len(gql_list), "、".join("`%s`" % k for k in gql_list), block(gql_list)))

w("""## 2. GraphQL 详情（`transcript`）

**请求**

```graphql
query { transcript(id: "%s") { <把 Transcript 的 30 个字段都写上> } }
```

**返回**（顶层 %d 个字段：%s）

实测 `audio_url`、`video_url` 在 Free 账号下返回 `paid_required`（HTTP 403 错误），故不在此列；`transcript_chapters` 等字段账号内本就为空。

%s

---
""" % (MID, len(gql_detail), "、".join("`%s`" % k for k in gql_detail), block(gql_detail)))

w("""## 3. MCP 列表（`fireflies_get_transcripts`）

**请求**

```json
{"method":"tools/call","params":{"name":"fireflies_get_transcripts",
 "arguments":{"limit":1,"format":"json"}}}
```

`format` 只有 `fireflies_search`、`fireflies_get_transcripts`、`fireflies_get_soundbites`、`fireflies_get_user_contacts` 四个工具支持，取 `json` 时字段固定 10 个、**驼峰命名**（`organizerEmail` 而非 GraphQL 的 `organizer_email`），不能像 GraphQL 那样自选字段。

**注意**：列表**不含 `sentences`**（官方描述 "excludes detailed transcript content"），正文必须逐场再调 `fireflies_get_transcript`——这是 MCP 要 1+N 次调用的根因。内嵌 `summary` 也只有 3 项。

**返回**（固定 %d 个字段：%s）

%s

---
""" % (len(mcp_list), "、".join("`%s`" % k for k in mcp_list), block(mcp_list)))

w("""## 4. MCP 详情（`fireflies_get_transcript`）

**请求**

```json
{"method":"tools/call","params":{"name":"fireflies_get_transcript",
 "arguments":{"transcriptId":"%s"}}}
```

该工具**只接受 id，没有 `format` 参数**，返回给 LLM 阅读的格式化纯文本（实测 53 KB / 526 行 / 21 个标签）。用于数据管道需自行解析，比 GraphQL 脆弱——且措辞调整会造成**静默脏数据而非报错**。

**返回**（`content[0].text` 的原文）

```text
%s
```

对照 §2 可见 MCP 详情缺的 7 个字段：`analytics`、`workspace_users`、`shared_with`、`meeting_attendance`、`meeting_info`、`apps_preview`／`channels`。其中 `meeting_attendance` 承载进出场时间，是判断"谁中途离场"的唯一数据源，MCP 通道完全不具备。

**接入时必须处理的两处文本特性**（都只在这份原文里看得见，字段对照表体现不出来）：

1. **空值是自然语言占位符，且每个字段措辞不同**——上面的 `Audio Url: No audio url`、`Video Url: No video url`，GraphQL 对应位置是 `paid_required` 报错或 `null`。解析时必须维护占位文案映射表，**漏一个就会把 "No audio url" 当真值入库**。
2. **末行的 `⚠️ Partial results: some fields may be missing due to 2 error(s)`**——MCP 对部分字段失败的处理是**降级返回 + 文本告警**，HTTP 仍是 200、JSON-RPC 也不报 error。这意味着**靠状态码判断成败会漏掉数据缺失**，必须额外匹配这行告警；而它属于展示文案，Fireflies 未承诺稳定，措辞一改这个检测就静默失效。
""" % (MID, trim_mcp_text(mcp_detail)))

out = "".join(W)
io.open("../api-response-samples.md", "w", encoding="utf-8", newline="\n").write(out)
print("生成 %d 字符" % len(out))
