> 关联文档: [导入格式](./meeting-import-template.md) · [开发设计](../开发设计/meeting-import-dev-design.md)
>
> 本文件可以直接导入：第一个 `# ` 之前的内容导入时忽略。下面是按导入格式第 5 节的提示词，把 B 套 F18、F08（a、b 两个变体）、F22 转换后的结果，「转换说明」也是 AI 输出的一部分。

## 转换说明

- 默认时区 -07:00；原文都有 Fireflies ID，没用到 ID 前缀
- F18、F22：原文 `(PT)`，10 月底仍是夏令时，换算为 `-07:00`
- F08-a、F08-b：原文没写时区，按默认时区 `-07:00`；示例只转了 a、b 两个变体
- F08：`(第二位参会人)`、`(第三位参会人)` 按原文说明换成各变体第 2、3 位参会人
- F18：Mark Chen「00:00–30:00 中途离开」的在场时间不导入，离场体现在转录里
- F22：删掉无说话人的旁注行 `[00:14] (connection lost)`
- 各场的接入方式、组织者不导入

# Acme Strategy + GS Debrief
- Fireflies ID: 01JCG5X4Y2
- Date: 2026-10-28 09:00 -07:00
- Duration: 60

## Participants

| Name | Email | Attended |
|---|---|---|
| Tom Lee | tom@lgcapital.com | yes |
| Amy Zhou | amy@lgcapital.com | yes |
| Mark Chen | mark@acme.com | yes |

## Summary

Mark walked through Acme's go-to-market plan for Q1. After Mark left, Tom and Amy debriefed: they consider Acme's sales leadership a risk and will raise it at the next board meeting.

## Transcript

```
[00:00] Tom Lee: Mark, walk us through the Q1 GTM plan.
[02:10] Mark Chen: We focus on mid-market dental labs, two new AEs, and the usage-based pilot.
[29:40] Mark Chen: I have to drop, thanks both.
[30:05] Amy Zhou: Now that Mark's gone, honestly I think Acme's sales leadership is a risk.
[30:30] Tom Lee: Agreed. Let's raise it at the next board meeting.
[59:30] Amy Zhou: Okay, wrap.
```

## 测试要点

- 用例：F18 · GS → Founder · Founder 中途离场（不切分子会议）；覆盖 MT TC-058、TC-059
- 整场作为**一条记录**分类，不拆成两场子会议
- AI Meeting Type：GS → Founder；Company：Acme Inc
- 风险提示：[30:05] 之后是 GS 内部讨论，MVP 不拆分，这部分可能进入 Founder Memory 1a。需人工确认 1a 和 Founder KB 中**不应**出现 "sales leadership is a risk"；出现了就按下一步改判
- 管理员手动改判兜底（MT TC-059）：AI Meeting Type 改为 GS Internal → Start Extraction → Confirm & Apply Routing → 1a 和 Founder KB 行消失，路由按 GS Internal 规则重新计算

# Market Roundtable
- Fireflies ID: 01JCE1A7B1
- Date: 2026-10-25 10:00 -07:00
- Duration: 30

## Participants

| Name | Email | Attended |
|---|---|---|
| Tom Lee | tom@lgcapital.com | yes |
| Mark Chen | mark@acme.com | yes |
| Lisa Wong | lisa@northcap.com | yes |

## Summary

Roundtable on market conditions. Participants agreed that buyers are more disciplined and that pricing models are shifting toward usage-based structures.

## Transcript

```
[00:00] Tom Lee: Thanks everyone, open discussion on the market today.
[02:00] Mark Chen: Buyers are a lot more disciplined than two years ago.
[04:30] Lisa Wong: Agreed, and pricing is shifting toward usage-based models.
[29:00] Tom Lee: Thanks all.
```

## 测试要点

- 用例：F08-a · 类型优先级；覆盖 MT TC-053、TC-055
- GS → Founder 和 GS → LP 同时满足
- 期望 AI Meeting Type：**GS → Founder**；Company：Acme Inc

# Market Roundtable
- Fireflies ID: 01JCE1A7B2
- Date: 2026-10-25 11:00 -07:00
- Duration: 30

## Participants

| Name | Email | Attended |
|---|---|---|
| Tom Lee | tom@lgcapital.com | yes |
| Lisa Wong | lisa@northcap.com | yes |
| Sara Lin | sara@stratx.com | yes |

## Summary

Roundtable on market conditions. Participants agreed that buyers are more disciplined and that pricing models are shifting toward usage-based structures.

## Transcript

```
[00:00] Tom Lee: Thanks everyone, open discussion on the market today.
[02:00] Lisa Wong: Buyers are a lot more disciplined than two years ago.
[04:30] Sara Lin: Agreed, and pricing is shifting toward usage-based models.
[29:00] Tom Lee: Thanks all.
```

## 测试要点

- 用例：F08-b · 类型优先级；覆盖 MT TC-053、TC-055
- GS → LP 和 GS → Partner 同时满足
- 期望 AI Meeting Type：**GS → LP**；Company：空

# Acme quick check
- Fireflies ID: 01JCH6F8G4
- Date: 2026-10-29 15:00 -07:00
- Duration: 3

## Participants

| Name | Email | Attended |
|---|---|---|
| Tom Lee | tom@lgcapital.com | yes |
| Mark Chen | mark@acme.com | yes |

## Summary

Mark confirmed the pilot kickoff date; the call was cut short due to a connection issue.

## Transcript

```
[00:00] Tom Lee: Quick one, pilot still on for January?
[00:06] Mark Chen: Yes, January 12th. Sorry, connection's bad, I'll—
```

## 测试要点

- 用例：F22 · 边界 · 极短会议
- AI Meeting Type：GS → Founder；Company：Acme Inc；Status：Passed
- 各路由行都能生成很短的摘要（如 "Pilot kickoff confirmed for January"），不留空、不报错，**不编造**转录中没有的内容
- Cross Company 可以为空，或说明"无可迁移趋势"，不应强行生成内容
