# Fireflies 会议接口返回样例（四份）

> 关联文档: [API 能力与数据质量调研](./fireflies-api-capability-survey.md)（结构对比见其附录 B）、[实测脚本](./demo/README.md)

> **用途**：并排看清同一场会议在四个接口下**返回什么结构、装什么值**。字段层面的逐项差异表在调研文档附录 B，本文件不重复，只放实际返回。
>
> **数据来源**：2026-09-18 / 09-20 实测落盘的原始返回，**未重新调用接口**（两条通道共用 50 次/天配额）。
>
> **样本会议**：`01KZYS4QBCSC54X8BTSB6G9Y35` — LG Weekly Business Requirements Discussion，2026-08-21，48 分钟，2 位说话人，504 句。
> 该会归属 API key 账号，经 `shareMeeting` 分享给 OAuth 账号后，两条通道取的是**同一场会**，故可直接对照。
>
> **截断规则**（原文太长，按统一规则压缩，均已就地标注）：
> - 字符串超过 240 字符 → 截断并标 `…〖截断，全长 N 字符〗`
> - 数组超过 3 项 → 保留前 3 项并标 `…〖截断，共 N 项〗`
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
## 1. GraphQL 列表（`transcripts`）

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

**返回**（顶层 12 个字段：`id`、`title`、`dateString`、`date`、`duration`、`privacy`、`transcript_url`、`participants`、`speakers`、`meeting_attendees`、`summary`、`sentences`）

```json
{
  "id": "01KZYS4QBCSC54X8BTSB6G9Y35",
  "title": "LG Weekly Business Requirements Discussion",
  "dateString": "2026-08-21T16:00:00.000Z",
  "date": 1787328000000,
  "duration": 48.970001220703125,
  "privacy": "link",
  "transcript_url": "https://app.fireflies.ai/view/01KZYS4QBCSC54X8BTSB6G9Y35",
  "participants": [
    "karen@whalesongproduct.com",
    "wenchao@whalesongproduct.com",
    "tingting@whalesongproduct.com",
    "…〖截断，共 8 项〗"
  ],
  "speakers": [
    {
      "name": "Karen Arnoldi"
    },
    {
      "name": "Dougal Cameron"
    }
  ],
  "meeting_attendees": [
    {
      "displayName": null,
      "email": "karen@whalesongproduct.com"
    },
    {
      "displayName": null,
      "email": "wenchao@whalesongproduct.com"
    },
    {
      "displayName": null,
      "email": "tingting@whalesongproduct.com"
    },
    "…〖截断，共 8 项〗"
  ],
  "summary": {
    "overview": "- **AI Memory System:** Goldie will store meeting data in categorized, editable markdown files; portfolio managers add insights; supports evolving company profiles.  \n- **Chat-Based Memory Extraction:** Postponed until 2027 to avoid MVP del…〖截断，全长 979 字符〗",
    "short_summary": "The team discussed the vision for an AI memory management system, with Goldie set to categorize and store meeting data in editable markdown files. Portfolio managers will contribute insights, and the system will evolve alongside ongoing int…〖截断，全长 787 字符〗",
    "gist": "The meeting focused on the development of an AI memory management system and updates on the AI chatbot release.",
    "keywords": [
      "AI memory management",
      "Fireflies integration",
      "meeting classification",
      "…〖截断，共 6 项〗"
    ],
    "action_items": "\n**Karen Arnoldi**\nShare Goldie memory management demo with the development team and confirm alignment with long-term AI vision (05:33)\nConfirm with dev team the non-hard deletion of chat history for interim period and ensure capability to …〖截断，全长 1323 字符〗",
    "outline": null,
    "topics_discussed": null,
    "meeting_type": null,
    "shorthand_bullet": "🧠 **AI Memory Management Vision** (00:55 - 05:33)\nFocus on structured storage of company info into editable files by functional buckets\nMaintain clean, accessible knowledge base for Goldie assistant\nAvoid expanding Goldie into executive tas…〖截断，全长 2404 字符〗",
    "bullet_gist": "🧠 AI Memory System: Goldie will store meeting data in categorized, editable markdown files; portfolio managers add insights; supports evolving company profiles.\n⏳ Chat-Based Memory Extraction: Postponed until 2027 to avoid MVP delay; interi…〖截断，全长 945 字符〗",
    "notes": "## **AI Memory Management Vision**\n\nThe team aims to build a structured, proactive AI memory system to capture and organize company insights during founder interactions.\n\n- **Goldie as an AI archivist for founder-company memory** is envisio…〖截断，全长 8965 字符〗",
    "transcript_chapters": []
  },
  "sentences": [
    {
      "index": 0,
      "speaker_name": "Karen Arnoldi",
      "text": "Sure.",
      "start_time": 0.24,
      "end_time": 0.48
    },
    {
      "index": 1,
      "speaker_name": "Karen Arnoldi",
      "text": "We are recording here.",
      "start_time": 2.32,
      "end_time": 4.4
    },
    {
      "index": 2,
      "speaker_name": "Karen Arnoldi",
      "text": "Yep.",
      "start_time": 4.88,
      "end_time": 5.4
    },
    "…〖截断，共 504 项〗"
  ]
}
```

---
## 2. GraphQL 详情（`transcript`）

**请求**

```graphql
query { transcript(id: "01KZYS4QBCSC54X8BTSB6G9Y35") { <把 Transcript 的 30 个字段都写上> } }
```

**返回**（顶层 25 个字段：`id`、`title`、`host_email`、`organizer_email`、`privacy`、`date`、`dateString`、`duration`、`participants`、`is_live`、`transcript_url`、`calendar_id`、`cal_id`、`calendar_type`、`meeting_link`、`fireflies_users`、`workspace_users`、`user`、`meeting_info`、`meeting_attendees`、`meeting_attendance`、`speakers`、`shared_with`、`sentences`、`summary`）

实测 `audio_url`、`video_url` 在 Free 账号下返回 `paid_required`（HTTP 403 错误），故不在此列；`transcript_chapters` 等字段账号内本就为空。

```json
{
  "id": "01KZYS4QBCSC54X8BTSB6G9Y35",
  "title": "LG Weekly Business Requirements Discussion",
  "host_email": "karen@whalesongproduct.com",
  "organizer_email": "tingting@whalesongproduct.com",
  "privacy": "link",
  "date": 1787328000000,
  "dateString": "2026-08-21T16:00:00.000Z",
  "duration": 48.970001220703125,
  "participants": [
    "karen@whalesongproduct.com",
    "wenchao@whalesongproduct.com",
    "tingting@whalesongproduct.com",
    "…〖截断，共 8 项〗"
  ],
  "is_live": false,
  "transcript_url": "https://app.fireflies.ai/view/01KZYS4QBCSC54X8BTSB6G9Y35",
  "calendar_id": "040000008200E00074C5B7101A82E00807EA081550627D8A6034DC0100000000000000001000000081A7927EECB852478C55B72C2203EA0B",
  "cal_id": "AAMkADMyYmVjY2M2LWIwNDctNDY4OS1hNTg5LWUzNTg5Mjg5N2FhOAFRAAgI3v8XJM4AAEYAAAAAIkx5UQDbdEiqwJhtGiyDAAcAdeAoCOVEy06RfwOa05Kc3wAAAAABDQAAdeAoCOVEy06RfwOa05Kc3wAD7-otPQAAEA==",
  "calendar_type": "outlook",
  "meeting_link": "https://teams.microsoft.com/l/meetup-join/19:meeting_NzE2N2EyYTctNjNjNi00YmQxLWFkZWQtODgxNjQ2ZjAxN2Qw@thread.v2/0?context={\"Tid\":\"1c428c68-8aa5-4378-a081-333e84e8c2e6\",\"Oid\":\"7ba04e5f-b545-4998-9807-915a039245ec\"}",
  "fireflies_users": [
    "kelly@whalesongproduct.com",
    "dougal@goldensection.com",
    "jacobo@whalesongproduct.com",
    "…〖截断，共 4 项〗"
  ],
  "workspace_users": [],
  "user": {
    "user_id": "01K73SAVP0XTFEJQNCMAZQCJFC",
    "name": "Tingting Song",
    "email": "tingting@whalesongproduct.com"
  },
  "meeting_info": {
    "silent_meeting": false,
    "summary_status": "processed",
    "fred_joined": true
  },
  "meeting_attendees": [
    {
      "displayName": null,
      "email": "karen@whalesongproduct.com",
      "name": null
    },
    {
      "displayName": null,
      "email": "wenchao@whalesongproduct.com",
      "name": null
    },
    {
      "displayName": null,
      "email": "tingting@whalesongproduct.com",
      "name": null
    },
    "…〖截断，共 8 项〗"
  ],
  "meeting_attendance": [
    {
      "name": "Karen Arnoldi",
      "join_time": "2026-08-21T16:01:18.420Z",
      "leave_time": "2026-08-21T16:48:35.882Z"
    },
    {
      "name": "Dougal Cameron",
      "join_time": "2026-08-21T16:01:18.421Z",
      "leave_time": "2026-08-21T16:48:24.154Z"
    }
  ],
  "speakers": [
    {
      "id": 0,
      "name": "Karen Arnoldi"
    },
    {
      "id": 1,
      "name": "Dougal Cameron"
    }
  ],
  "shared_with": [
    {
      "email": "shupeng@whalesongproduct.com",
      "name": "Shupeng Yao"
    }
  ],
  "sentences": [
    {
      "index": 0,
      "speaker_name": "Karen Arnoldi",
      "speaker_id": 0,
      "text": "Sure.",
      "raw_text": "Sure.",
      "start_time": 0.24,
      "end_time": 0.48,
      "ai_filters": {
        "text_cleanup": "Sure.",
        "task": null,
        "pricing": null,
        "metric": null,
        "question": null,
        "date_and_time": null,
        "sentiment": "neutral"
      }
    },
    {
      "index": 1,
      "speaker_name": "Karen Arnoldi",
      "speaker_id": 0,
      "text": "We are recording here.",
      "raw_text": "We are recording here.",
      "start_time": 2.32,
      "end_time": 4.4,
      "ai_filters": {
        "text_cleanup": "We are recording here.",
        "task": null,
        "pricing": null,
        "metric": null,
        "question": null,
        "date_and_time": null,
        "sentiment": "neutral"
      }
    },
    {
      "index": 2,
      "speaker_name": "Karen Arnoldi",
      "speaker_id": 0,
      "text": "Yep.",
      "raw_text": "Yep.",
      "start_time": 4.88,
      "end_time": 5.4,
      "ai_filters": {
        "text_cleanup": "Yep.",
        "task": null,
        "pricing": null,
        "metric": null,
        "question": null,
        "date_and_time": null,
        "sentiment": "neutral"
      }
    },
    "…〖截断，共 504 项〗"
  ],
  "summary": {
    "overview": "- **AI Memory System:** Goldie will store meeting data in categorized, editable markdown files; portfolio managers add insights; supports evolving company profiles.  \n- **Chat-Based Memory Extraction:** Postponed until 2027 to avoid MVP del…〖截断，全长 979 字符〗",
    "short_summary": "The team discussed the vision for an AI memory management system, with Goldie set to categorize and store meeting data in editable markdown files. Portfolio managers will contribute insights, and the system will evolve alongside ongoing int…〖截断，全长 787 字符〗",
    "gist": "The meeting focused on the development of an AI memory management system and updates on the AI chatbot release.",
    "keywords": [
      "AI memory management",
      "Fireflies integration",
      "meeting classification",
      "…〖截断，共 6 项〗"
    ],
    "action_items": "\n**Karen Arnoldi**\nShare Goldie memory management demo with the development team and confirm alignment with long-term AI vision (05:33)\nConfirm with dev team the non-hard deletion of chat history for interim period and ensure capability to …〖截断，全长 1323 字符〗",
    "bullet_gist": "🧠 AI Memory System: Goldie will store meeting data in categorized, editable markdown files; portfolio managers add insights; supports evolving company profiles.\n⏳ Chat-Based Memory Extraction: Postponed until 2027 to avoid MVP delay; interi…〖截断，全长 945 字符〗",
    "shorthand_bullet": "🧠 **AI Memory Management Vision** (00:55 - 05:33)\nFocus on structured storage of company info into editable files by functional buckets\nMaintain clean, accessible knowledge base for Goldie assistant\nAvoid expanding Goldie into executive tas…〖截断，全长 2404 字符〗",
    "notes": "## **AI Memory Management Vision**\n\nThe team aims to build a structured, proactive AI memory system to capture and organize company insights during founder interactions.\n\n- **Goldie as an AI archivist for founder-company memory** is envisio…〖截断，全长 8965 字符〗",
    "outline": null,
    "topics_discussed": null,
    "meeting_type": null,
    "transcript_chapters": []
  }
}
```

---
## 3. MCP 列表（`fireflies_get_transcripts`）

**请求**

```json
{"method":"tools/call","params":{"name":"fireflies_get_transcripts",
 "arguments":{"limit":1,"format":"json"}}}
```

`format` 只有 `fireflies_search`、`fireflies_get_transcripts`、`fireflies_get_soundbites`、`fireflies_get_user_contacts` 四个工具支持，取 `json` 时字段固定 10 个、**驼峰命名**（`organizerEmail` 而非 GraphQL 的 `organizer_email`），不能像 GraphQL 那样自选字段。

**注意**：列表**不含 `sentences`**（官方描述 "excludes detailed transcript content"），正文必须逐场再调 `fireflies_get_transcript`——这是 MCP 要 1+N 次调用的根因。内嵌 `summary` 也只有 3 项。

**返回**（固定 10 个字段：`id`、`title`、`dateString`、`duration`、`organizerEmail`、`meetingLink`、`summary`、`meetingAttendees`、`meetingInfo`、`participants`）

```json
{
  "id": "01KZYS4QBCSC54X8BTSB6G9Y35",
  "title": "LG Weekly Business Requirements Discussion",
  "dateString": "2026-08-21T16:00:00.000Z",
  "duration": 48.970001220703125,
  "organizerEmail": "tingting@whalesongproduct.com",
  "meetingLink": "https://teams.microsoft.com/l/meetup-join/19:meeting_NzE2N2EyYTctNjNjNi00YmQxLWFkZWQtODgxNjQ2ZjAxN2Qw@thread.v2/0?context={\"Tid\":\"1c428c68-8aa5-4378-a081-333e84e8c2e6\",\"Oid\":\"7ba04e5f-b545-4998-9807-915a039245ec\"}",
  "summary": {
    "short_summary": "The team discussed the vision for an AI memory management system, with Goldie set to categorize and store meeting data in editable markdown files. Portfolio managers will contribute insights, and the system will evolve alongside ongoing int…〖截断，全长 787 字符〗",
    "keywords": [
      "AI memory management",
      "Fireflies integration",
      "meeting classification",
      "…〖截断，共 6 项〗"
    ],
    "action_items": "\n**Karen Arnoldi**\nShare Goldie memory management demo with the development team and confirm alignment with long-term AI vision (05:33)\nConfirm with dev team the non-hard deletion of chat history for interim period and ensure capability to …〖截断，全长 1323 字符〗"
  },
  "meetingAttendees": [
    {
      "displayName": null,
      "email": "karen@whalesongproduct.com"
    },
    {
      "displayName": null,
      "email": "wenchao@whalesongproduct.com"
    },
    {
      "displayName": null,
      "email": "tingting@whalesongproduct.com"
    },
    "…〖截断，共 8 项〗"
  ],
  "meetingInfo": {
    "fred_joined": true,
    "silent_meeting": false,
    "summary_status": "processed"
  },
  "participants": [
    "karen@whalesongproduct.com",
    "wenchao@whalesongproduct.com",
    "tingting@whalesongproduct.com",
    "…〖截断，共 8 项〗"
  ]
}
```

---
## 4. MCP 详情（`fireflies_get_transcript`）

**请求**

```json
{"method":"tools/call","params":{"name":"fireflies_get_transcript",
 "arguments":{"transcriptId":"01KZYS4QBCSC54X8BTSB6G9Y35"}}}
```

该工具**只接受 id，没有 `format` 参数**，返回给 LLM 阅读的格式化纯文本（实测 53 KB / 526 行 / 21 个标签）。用于数据管道需自行解析，比 GraphQL 脆弱——且措辞调整会造成**静默脏数据而非报错**。

**返回**（`content[0].text` 的原文）

```text
Id: 01KZYS4QBCSC54X8BTSB6G9Y35
DateString: 2026-08-21T16:00:00.000Z
Privacy: link
Speakers: Karen Arnoldi, Dougal Cameron
Sentences: [00:00 - 00:00] Karen Arnoldi: Sure.
[00:02 - 00:04] Karen Arnoldi: We are recording here.
[00:04 - 00:05] Karen Arnoldi: Yep.
[00:05 - 00:05] Dougal Cameron: Yeah.
[00:06 - 00:06] Karen Arnoldi: Okay.
[00:06 - 00:15] Dougal Cameron: It's funny that I don't understand why certain Fireflies join and why certain don't like why tingting joined and mine didn't.
…〖Sentences 截断，全段共 503 行〗
Title: LG Weekly Business Requirements Discussion
Host Email: karen@whalesongproduct.com
Organizer Email: tingting@whalesongproduct.com
Calendar Id: 040000008200E00074C5B7101A82E00807EA081550627D8A6034DC0100000000000000001000000081A7927EECB852478C55B72C2203EA0B
Fireflies Users: kelly@whalesongproduct.com, dougal@goldensection.com, jacobo@whalesongproduct.com, wenchao@whalesongproduct.com
Participants: karen@whalesongproduct.com, wenchao@whalesongproduct.com, tingting@whalesongproduct.com, dougal@goldensection.com, kelly@whalesongproduct.com, jacobo@whalesongproduct.com, jesus@whalesongproduct.com, chunru@whalesongproduct.com
Date: 1787328000000
Transcript Url: https://app.fireflies.ai/view/01KZYS4QBCSC54X8BTSB6G9Y35
Audio Url: No audio url
Video Url: No video url
Duration: 48.970001220703125
Meeting Attendees: karen@whalesongproduct.com, wenchao@whalesongproduct.com, tingting@whalesongproduct.com, dougal@goldensection.com, kelly@whalesongproduct.com, jacobo@whalesongproduct.com, jesus@whalesongproduct.com, chunru@whalesongproduct.com
Cal Id: AAMkADMyYmVjY2M2LWIwNDctNDY4OS1hNTg5LWUzNTg5Mjg5N2FhOAFRAAgI3v8XJM4AAEYAAAAAIkx5UQDbdEiqwJhtGiyDAAcAdeAoCOVEy06RfwOa05Kc3wAAAAABDQAAdeAoCOVEy06RfwOa05Kc3wAD7-otPQAAEA==
Calendar Type: outlook
Meeting Link: https://teams.microsoft.com/l/meetup-join/19:meeting_NzE2N2EyYTctNjNjNi00YmQxLWFkZWQtODgxNjQ2ZjAxN2Qw@thread.v2/0?context={"Tid":"1c428c68-8aa5-4378-a081-333e84e8c2e6","Oid":"7ba04e5f-b545-4998-9807-915a039245ec"}
Is Live: false

⚠️ Partial results: some fields may be missing due to 2 error(s)
```

对照 §2 可见 MCP 详情缺的 7 个字段：`analytics`、`workspace_users`、`shared_with`、`meeting_attendance`、`meeting_info`、`apps_preview`／`channels`。其中 `meeting_attendance` 承载进出场时间，是判断"谁中途离场"的唯一数据源，MCP 通道完全不具备。

**接入时必须处理的两处文本特性**（都只在这份原文里看得见，字段对照表体现不出来）：

1. **空值是自然语言占位符，且每个字段措辞不同**——上面的 `Audio Url: No audio url`、`Video Url: No video url`，GraphQL 对应位置是 `paid_required` 报错或 `null`。解析时必须维护占位文案映射表，**漏一个就会把 "No audio url" 当真值入库**。
2. **末行的 `⚠️ Partial results: some fields may be missing due to 2 error(s)`**——MCP 对部分字段失败的处理是**降级返回 + 文本告警**，HTTP 仍是 200、JSON-RPC 也不报 error。这意味着**靠状态码判断成败会漏掉数据缺失**，必须额外匹配这行告警；而它属于展示文案，Fireflies 未承诺稳定，措辞一改这个检测就静默失效。
