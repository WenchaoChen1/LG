# Fireflies 会议导入（devSupport 测试页）开发步骤

> 关联文档: [开发设计](./meeting-import-dev-design.md) · [导入文件格式要求](../测试用例/meeting-import-format.md)

第 1、2 步互不依赖，可以作为一轮并行开发。

| # | 层 | 步骤 | 范围（端 / 表 / 接口 / 页面 / 主要文件） | 设计依据 | 依赖 | 完成标准 | 状态 |
|---|---|---|---|---|---|---|---|
| 1 | 点 | Java 导入接口 | Java：API-D1；新增 Request、Response、DTO、`FfMeetingImportStatusEnum`；`FfMeetingController`、`FfMeetingConverter`、`FfSyncService(Impl)`（`importMeetings`、`toTranscript`，抽出 `dispatchMeeting`） | 开发设计 1、3 | — | 编译通过；`FfSyncServiceImplTest` 新增用例与原有用例都通过 | 已完成 Java f152ae486 |
| 2 | 点 | 前端解析函数 | Web：`pages/devSupport/firefliesImport/utils/parseMeetingImport.ts` 与单测 | 开发设计 6；格式要求 2 | — | jest 通过；格式要求第 4 节的示例解析出 4 场且无报错 | 已完成 Web 8fe47edec |
| 3 | 线 | 导入页 | Web：PG-D1 页面、路由、`NAV_GROUPS`，以及 `firefliesWebApi` 与 request / response 类型 | 开发设计 2、4、5、6 | 1、2 | tsc（只看新增文件）与 lint 通过；本地页面能预览示例并调通接口 | 已完成 Web 8fe47edec |
| 4 | 面 | 本地联调 | 本地测试租户按格式要求附录 B 配好前置数据，导入格式要求第 4 节的示例，Python 正常消费 | 开发设计 8「联调」 | 3 | 4 场在 Summary Records 可见并处理到终态；再导一次全部为「已存在」 | 待开发 |
