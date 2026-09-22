## Fireflies Summary Records

**说明**：该功能是会议摘要查看及手动分配功能，当AI无法自行路由会议内容时（未识别会议类型或参会人员)，租户管理员可以手动修改。raw data每日定时拉取，拉取后分析完成后展示在此页

### Records列表

- 字段：Meeting（会议名 + ID · 时长 ）、Time、AI Meeting Type、Companies、Status
- 会议名和 Review 链接均可点击，跳转到对应会议详情页 
- Search bar支持模糊查询Meeting、Companies
- Filter可过滤查询：AI Meeting Type、 Status、Period
- Status: Passed(AI可以100%判断会议类型和参会人员并路由全部内容的)，Flagged(AI判定为LG-Founder的会议类型)，Pending(AI无法判定会议类型和参会人员，需要人工手动处理的)

### Review按钮

点击该按钮进入会议摘要详情页面，可以查看详情或修改

**会议信息卡**

- Date：会议日期（拉取）
- Duration：会议时长（拉取）
- Fireflies ID：拉取

- Scrub Status 徽章：✓ Passed（绿）/ ◷ Pending（红）/ ⚠ Flagged（琥珀色）
  - 映射规则: 人员 Unidentified/会议类型未判断成功→ Pending、GS-Founder会议类型 → Flagged
- AI Meeting Type：标签 + 下拉（GS → Founder、GS → Board Call with Founder、GS → LP、GS Internal、GS → Strategic Partner、GS → Exit Partner、Unknown），切换时标签实时更新；Unknown 灰色，其他蓝色
- Company：展示已识别公司，可点 × 移除；可多选，可搜索下拉添加公司
- Participants：姓名标签，各角色不同颜色；未识别身份者（Unidentified）带红点，点击弹出 "Assign New External Party" 弹框（Name、Email、Organization、Role、Expertise Tags、Validity period）；其他参会者点击也打开弹框，已识别者 Name 只读

**Content Routing Matrix**

**Content** 

- 已处理后的内容
- 单元格可编辑（每行一条 bullet）；改动后该格出现琥珀高亮边框 
-  底部 Cancel / Save 按钮，Save 只保存该行，Cancel 还原该行

**Visible to** 

- 谁能看到这一行内容

- 不同角色看到的可能是同样的内容，合并展示

**Authorize** 

- 勾选则授权，visible to中的角色即可看到该行内容

**注：具体的操作步骤的实现形式参考文档“会议内容提取规则”** (https://github.com/WenchaoChen1/LG/blob/master/docs/Fireflies%20%E8%BD%AC%E5%BD%95%E6%8E%A5%E5%85%A5/%E8%B0%83%E7%A0%94/%E4%BC%9A%E8%AE%AE%E5%86%85%E5%AE%B9%E6%8F%90%E5%8F%96%E8%A7%84%E5%88%99-%E9%9C%80%E6%B1%82%E6%96%87%E6%A1%A3.md)
