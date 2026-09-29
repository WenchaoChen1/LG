描述：** 本页面保存所有已录制会议的逐字原始转录及元数据，保证底层数据完整、可追溯。

**Meeting list（表格视图）**

每一行为一场会议，字段如下：Meeting ID、Title、Date、Time、Duration、Participants、Ingested at。

**Status 标识**

- 当会议非常短且没有实质内容时，判定为无效会议，显示灰色 "Invalid" 标签

**原始转录入口**

- 每一行末尾提供 "Raw transcript" 链接；点击后进入详情页，展示带时间戳与发言人的完整逐字转录
  - 顶部显示会议名称
  - 会议元数据：Date、Time、Duration、Participants
  - 完整逐字转录（Full Transcript）

**数据接入**

- 按天定时拉取

**权限**

- 创始人本人可查看自已参加的会议，未参加的本公司人员不可见
- 管理端PGM、Super Admin可见
