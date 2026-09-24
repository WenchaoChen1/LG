## Fireflies Raw Data

**说明**：该页面为所有录制的会议的原始逐字稿 + 元数据，保证底层数据完整可追溯。

**会议列表（表格展示）**

每行一场会议，字段：Meeting ID、Title、Date、Time、Duration、Participants、Ingested at（入库时间）

**状态标识**

- 当一些会议很短且无重点内容时，判定为无效会议，显示灰色 "Invalid" 标签

**原始逐字稿入口**

- 每行末尾有 "Raw transcript" 链接，点击跳转到详情页面，展示带时间戳、说话人的完整逐字稿
  - 顶部显示会议名字
  - 会议元数据：Date Time Duration Participants
  - Full Transcript

**数据拉取**

- 每日定时拉取
