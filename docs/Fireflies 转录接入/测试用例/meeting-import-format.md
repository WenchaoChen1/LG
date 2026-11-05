# Fireflies 会议导入文件格式要求

> 关联文档: [开发设计](../开发设计/meeting-import-dev-design.md) · [设计](../设计/design-doc.md)

devSupport「Fireflies → Meeting Import」页导入的文件，按本文件的要求编写。

- 只在本地和 test 环境使用，生产上线前会封掉。
- 导入的会议和真实拉取的一样，会进入识别和提取流程。
- 导入**不能撤销**，所以请用专门的测试租户。

## 1. 用法

1. **准备系统数据。** 按附录 B 配好以下内容：
   - Configuration 页的邮箱域名；
   - LG 用户与公司；
   - Cheat Sheet。

   导入功能只导会议，不会建这些数据。
2. **用 AI 产出导入文件。** 把本文件和测试用例（一个或多个）一起交给 AI，告诉它：「按这份格式要求，把测试用例转换成导入文件」。
   - 有需要时补一句默认时区和 ID 前缀，例如：「默认时区 -07:00，ID 前缀 B」。
   - 拿到结果后，人工看一遍文件开头的「转换说明」，补上 AI 标出的占位。
3. **导入。** 打开 devSupport → Fireflies → Meeting Import：
   1. 选租户；
   2. 拖入一个或多个 `.md` 文件；
   3. 预览里没有报错就点导入。
4. **看结果。** 去该租户的 Fireflies Management → Summary Records 查看识别和提取结果。各种导入结果的含义见附录 A。

## 2. 格式要求

文件用 UTF-8 编码的 `.md`。一个文件可以放多场会，每场会以一行 `# 标题` 开头，结构如下（完整示例见第 4 节）：

````markdown
（第一个 # 之前的内容导入时忽略，用来写转换说明）

# <会议标题>
- Fireflies ID: <ID>
- Date: <YYYY-MM-DD HH:mm ±HH:MM>
- Duration: <分钟数>

## Participants

| Name | Email | Attended |
|---|---|---|
| <显示名> | <邮箱> | yes |

## Summary

<Fireflies 摘要正文>

## Transcript

```
[00:00] <说话人>: <内容>
```

## 测试要点

（导入时忽略，写期望结果）
````

### 2.1 会议信息

会议信息紧跟在 `# 标题` 下面，写成 `- 键: 值`。其他的 `- 键: 值` 行导入时忽略。

| 项 | 必填 | 写法 | 说明 |
|---|---|---|---|
| 标题 | 是 | `# ` 后面的整行 | 超过 512 个字符的部分会截掉 |
| `Fireflies ID` | 是 | 只用字母、数字、`-`、`_`，最长 64 位 | 同一租户内唯一；Summary Records 里显示的就是它 |
| `Date` | 是 | `YYYY-MM-DD HH:mm ±HH:MM` | 必须写时区偏移，UTC 写 `+00:00`。Cheat Sheet 按会议的 **UTC 日期**取版本，偏移写错可能换到另一天 |
| `Duration` | 是 | 分钟数，可以带小数，如 `60`、`48.2` | |

### 2.2 Participants

这一节必须有。表头固定为 `| Name | Email | Attended |`，每行写一个人；表里可以没有数据行（会有提醒）。

| 这一行是 | Name | Email | Attended |
|---|---|---|---|
| 受邀并到场 | 显示名 | 邮箱 | `yes` |
| 受邀但没到场 | 显示名 | 邮箱 | `no` |
| 没受邀、但到场了 | 显示名 | 留空 | `yes` |
| 记录机器人（如 Fireflies.ai Notetaker） | 显示名 | **留空** | `yes` |

各列导入后的去向：

- **Email** 填了的，进受邀名单（Fireflies 的 `participants`）。导入时转成小写；同一场会里同一个邮箱只能出现一次。
- **Attended** 为 `yes` 的，进出席名单（Fireflies 的 `meeting_attendance`）。出席名单只记显示名，只作为 P8 的线索。
- **记录机器人不要写邮箱。** 真实数据里，机器人只出现在出席名单，不在受邀名单里。系统不会把机器人邮箱排除掉，写了邮箱就会被当成未识别的参会人，会议会进 Pending。
- **接入方式、在场时间、组织者都不导入。** 系统用不到这些信息；中途离场之类的情况，在转录里体现即可。

### 2.3 Summary

这一节可以省略。有内容时，整节正文就是 Fireflies 摘要（overview）。

- 只写 overview 正文，不要 `**Overview**` 之类的小标题，也不要 `>` 引用符。
- 省略这一节，表示 Fireflies 没有生成摘要。

### 2.4 Transcript

这一节必须有。

- 转录放在 ```` ``` ```` 代码块里，每句写一行：`[时间] 说话人: 内容`。
- **测试无效会议**时，可以一句都没有：保留空的代码块或只留节标题。

各部分的写法：

- **时间**：可以写 `[mm:ss]`，也可以写 `[h:mm:ss]`，如 `[00:12]`、`[29:40]`、`[00:01:30]`。两段式的分钟数可以超过 59，比如 `[75:10]`。后一句的时间不能早于前一句。
- **说话人**：取 `]` 后面到第一个 `: ` 之间的文字。
  - 可以带 Fireflies 的 `(Unverified)` 后缀，也可以是 `Speaker 2` 这类无名标签。
  - 不能以括号开头。`(第二位参会人)` 这类没换掉的占位会被拦下。
- **内容**：不能为空。原文跨多行的一句话，要合并成一行。

转录导入后，系统这样存：

- 句子按行序编号；
- 说话人按首次出现的顺序编号；
- 每句的开始时间取行首的时间；结束时间取下一句的开始时间，最后一句没有结束时间。

### 2.5 忽略的内容

导入时会忽略以下内容，可以放用例编号、前置数据、期望结果、转换说明：

- 第一个 `# ` 之前的全部内容；
- 每场会里除 Participants、Summary、Transcript 以外的 `## ` 节，比如 `## 测试要点`。

### 2.6 预览时的检查

**报错**：有报错的会议不能导入，改好后重新拖入。

- 必填项缺失，或格式不对；
- 缺少 `## Participants` 或 `## Transcript` 节；
- Participants 表头不对；某一行既没有邮箱、Attended 也不是 `yes`；邮箱格式不对；同一场里邮箱重复；
- 转录某一行格式不对、时间倒退、说话人以括号开头；
- 这次拖入的文件里，有两场会的 Fireflies ID 相同。

**提醒**：有提醒的会议可以导入。已经有报错的会议不再显示提醒。

- 转录一句都没有：这场会会被判为 Invalid；
- 没有任何受邀邮箱：这场会多半是 Unknown，会进 Pending。

## 3. 从测试用例转换时的规则

这一节写给做转换的 AI。测试用例写法各异，按以下规则转换成第 2 节的格式；具体写法参照第 4 节的示例。

1. **一场会写一个 `# 标题` 块。**
   - 标题用会议标题，不要用文档标题或用例名。
   - 原文里有多组变体（如 F08-a / b / c）的，每个变体拆成独立的一场：参会人、日期、ID 按该变体填，转录按原文的说明替换。
2. **Fireflies ID**：用原文的 ID。原文没有时，用「ID 前缀 + 文件名开头的编号」，变体再加 `-a`、`-b`，如 `A07`、`A07-b`。用户没有指定 ID 前缀时，用 `TEST`。
3. **Date**：写成 `YYYY-MM-DD HH:mm ±HH:MM`。
   - 原文写了时区名的，换算成偏移。美国时区要看当天是否在夏令时（2026 年的夏令时到 11 月 1 日结束）：PT 为 `-07:00` / `-08:00`，CT 为 `-05:00` / `-06:00`，ET 为 `-04:00` / `-05:00`。
   - 原文没写时区的，用用户指定的默认时区；用户没指定时，用 `+00:00`。
   - 原文只有日期、没有时刻的，写 `12:00 +00:00`。
4. **Duration**：换算成分钟数，最多保留两位小数。例如：`60 min` → `60`；`48:12`（分:秒）→ `48.2`；`00:52`（52 秒）→ `0.87`。
5. **Participants**：
   - 原文参会人名单里的每个人写一行。邮箱照抄，不要补，也不要改。
   - Attended：到场写 `yes`，原文明确说没到场的写 `no`；原文没说的默认 `yes`。
   - 记录机器人只写名字，Email 留空，Attended 写 `yes`。
   - 转录里发过言、有名有姓、但不在参会人名单里的人，加一行：Email 留空，Attended 写 `yes`。`Speaker 2` 这类无名标签不要加。
   - 接入方式、在场时间、组织者等列不要写。
6. **Summary**：只抄 Fireflies 摘要的 Overview 正文，去掉 `**Overview**` 之类的小标题和 `>` 引用符。原文说没有摘要的，整节不写。
7. **Transcript**：
   - 时间照抄原文，`[mm:ss]` 或 `[hh:mm:ss]` 都可以。
   - 原文里跨多行的一句话，合并成一行。
   - 占位说话人（如 `(第二位参会人)`）：原文给了对应关系的，换成真名；原文没说清对应谁的，不要猜，保留占位，并在转换说明里列出。导入页会拦下这些行，人工补完才能导入。
   - 没有说话人的旁注行（如 `(connection lost)`），删掉。
   - 原文没有转录内容的（用来测无效会议），保留 `## Transcript` 节和一个空代码块。
8. **测试要点**：原文的覆盖用例、前置数据、测试要点等，放在每场会最后的 `## 测试要点` 节。拆成变体的，只写该变体的期望。
9. **转换说明**：在文件开头、第一个 `# ` 之前，写一节 `## 转换说明`，列出每一处推断和改动：
   - 时区换算、时长换算；
   - 新增的未受邀到场人；
   - 删掉的行；
   - 保留的占位。

   没有就写「无」。
10. **输出**：只输出导入文件的内容。多个测试用例可以合成一个文件，也可以一个用例一个文件。

## 4. 示例

下面是把 B 套的 F18、F08（a、b 两个变体）、F22 转换后的结果，默认时区为 -07:00。代码块里的内容存成 `.md` 文件，就可以直接导入。

````markdown
## 转换说明

- 默认时区 -07:00；原文都有 Fireflies ID，没用到 ID 前缀
- F18、F22：原文 `(PT)`，10 月底仍是夏令时，换算为 `-07:00`
- F08-a、F08-b：原文没写时区，按默认时区 `-07:00`；只转了 a、b 两个变体
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
````

## 附录 A：导入结果

| 结果 | 含义 | 怎么办 |
|---|---|---|
| 已导入 | 已入库，并已发给 AI 处理 | 等几分钟，到 Summary Records 查看 |
| 未投递 | 已入库，但发消息失败了 | 原样再导一次：同一个 ID 只要还没投递，就会整场重写后重新发送 |
| 已存在 | 本租户已有这个 ID，并且已经处理过，这次没有任何改动 | 想重测，就把 ID 改一下（如加后缀 `-r2`）再导 |
| 失败 | 写库出错 | 按提示改数据后再导 |

导入的会议在系统里和真实拉取的一样：Ingested at 记的是导入时间，触发方式记为 Sync now，操作人记为导入的人。

## 附录 B：系统里要先准备的数据

识别时对每个受邀邮箱依次尝试下面几步，命中一步就停：

1. 本机构邮箱域名；
2. LG 用户的完整邮箱；
3. LG 用户的邮箱域名；
4. Cheat Sheet 里的邮箱；
5. 前几步都没命中时，交给大模型推断（P8）。

| 想让此人被识别成 | 邮箱怎么写 | 系统里要先有 |
|---|---|---|
| GS staff | 本机构的域名 | 在 Configuration 页把这个域名加进本机构邮箱域名（最稳）；或者此人是本租户的管理端 LG 用户 |
| Founder @某公司 | 这家公司的域名 | 公司在营（Active / Thriving / Needs Intervention / Needs Guidance），并且有公司端 LG 用户用这个邮箱，或用同一个域名。系统没有单独的「公司域名」字段，域名就取公司端用户的邮箱域名 |
| LP / Strategic Partner / Exit Partner / Other | 不属于本机构、也不属于任何 LG 用户的域名 | Cheat Sheet 里登记这个邮箱，并且会议当天（UTC 日期）落在这一版的有效期内 |
| 未识别 | 上面都对不上的邮箱 | 不用准备。会交给 P8 推断，会议多半进 Pending |

其他注意事项：

- **公共邮箱不参与域名匹配。** gmail.com、outlook.com 等 23 个公共邮箱域名不会按域名判断成 GS 或某家公司。
- **说话人靠「姓名对邮箱前缀」挂到参会人。**
  - 规则：先去掉 `(Unverified)`，再拿名、姓、名姓、姓名、首字母等组合，去对比邮箱 `@` 前面只保留字母后的部分。比如 `Mark Chen` 能对上 `mark@`、`markchen@`、`mchen@`、`mc@`。
  - 对不上的交给 P8；P8 也拿不准时，会议进 Pending。
  - 所以 `Nora Kim` 配 `ceo@beta.io` 这种写法一定会走 P8。
- **系统目前不支持以下匹配：**
  - HubSpot（MVP 跳过）；
  - 日历数据（没有存）；
  - 按姓名直接匹配 Cheat Sheet：姓名只作为候选交给 P8，不会直接采纳。

## 附录 C：现有两套用例的已知问题

两套用例分别是 `fireflies_test_transcripts`（简称 A 套）和 `Fireflies会议记录样本-测试用例配套版`（简称 B 套）。

**A、B 两套要放进不同的租户。** 两套里都有同名但不同的人（Mark Chen、Lisa Wong），GS 用的域名也不一样。

**B 套的前置数据**（README 第一节），要补上以下几项：

- 本机构邮箱域名加上 `whalesongproduct.com`、`goldensection.com`、`gst.com`；
- Beta、Gamma、Delta、Omega 每家公司至少要有一个公司端 LG 用户，否则按域名识别不出 Founder。

**B 套的部分期望，和当前实现的结果不一致：**

| 用例 | 用例里的期望 | 当前实现 |
|---|---|---|
| F10-a/b | 靠 HubSpot 命中 | 系统没有 HubSpot，只能靠 P8 推断 |
| F11 | 靠日历把 `Speaker 2` 对成 Paul | 系统不存日历数据，只能靠 P8 推断 |
| F09-a/b、F20-b | 按姓名命中 Cheat Sheet | 姓名只作为候选，最终由 P8 判断 |
| F01、F06、F24-a | 有专家建议的会议也是 Passed | 有未处理的建议标签时，会议停在 Pending（待确认专家）（设计 1.10） |
| F14、F15、F19 | `ceo@beta.io` 这类邮箱的说话人能自动对上 | 身份能靠邮箱识别出来，但说话人名对不上 `ceo@` 这样的前缀，要靠 P8 才能对上 |
| F06 | 正文提到的公司不关联 | GS → Partner 的会议会采纳正文提到的公司，需要核对 F06 的内容 |
