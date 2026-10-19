## Fireflies Summary Records

**说明**：该功能是会议摘要查看及手动分配功能，当AI无法自行路由会议内容时（未识别会议类型或参会人员)，租户管理员可以手动修改。raw data每日定时拉取，拉取后分析完成后展示在此页

### Records列表

- 字段：Meeting（会议名 + ID · 时长 ）、Time、AI Meeting Type、Companies、Status
- 会议名和 Review 链接均可点击，跳转到对应会议详情页 
- Search bar支持模糊查询Meeting、Companies
- Filter可过滤查询：AI Meeting Type、 Status、Period
- Status: Passed(AI可以100%判断会议类型和参会人员并路由全部内容的)，Pending(AI无法判定会议类型和参会人员，需要人工手动处理的)

### Review按钮

点击该按钮进入会议摘要详情页面，可以查看详情或修改

**会议信息卡**

- Start Extraction按钮：无未识别信息时，默认置灰，修改后且必填信息都填完激活，点击重新进行提取分类；有未识别信息时，默认置灰，所有必填信息填好后激活，点击重新进行提取分类。
- Date：会议日期（拉取）
- Duration：会议时长（拉取）
- Fireflies ID：拉取
- AI Meeting Type为必填，GS-Founder类型时 Company为必填，所有未识别人均应被处理

- Scrub Status 徽章：✓ Passed（绿）/ ◷ Pending（红）
  - 映射规则: 人员 Unidentified/会议类型未判断成功→ Pending
- AI Meeting Type：标签 + 下拉（GS → Founder、GS → LP、GS Internal、GS → Partner、Unknown），切换时标签实时更新；Unknown 灰色，其他蓝色
- Company：展示已识别公司，可点 × 移除；可多选，可搜索下拉添加公司(仅可搜索该用户有权限的公司）
- Portfolio（该账户下有权限的）：可多选，默认不选，非必选,管理员选择后激活下方Confirm按钮，仅为标记，不作为任何权限划分依据；
    - 针对GS-Founder的会议，默认实时获取这个公司关联的portfolio，但是这个字段仅是显示，不可手动更改，没有任何其他业务逻辑，也不会根据这个字段去决定任何访问权限
- Participants：姓名标签，各角色不同颜色；未识别身份者（Unidentified）带红点，点击弹出 "Assign New External Party" 弹框（Name、Email、Organization、Role、Expertise Tags、Validity period）；其他LG外部人员点击也打开弹框，已识别者 Name 只读,可编辑，保存后回流到cheat sheet。LG平台内部人员点击无弹框
- 外部参与者（非已标记为专家）在证词类别中提出实质性主张。姓名标签显示可能为专家，管理员点击姓名，弹出详细信息弹框，可同意或拒绝，同意则储存到cheat sheet。如果是专家的话,应该还携带Al推测的专家标签Expertise tags (Cheat Sheet库里面的标签。
同意和拒绝是针对这个人的邮箱+标签Expertise tags

**Content Routing Matrix**

**Content** 

- 已处理后的内容
- 单元格可编辑（每行一条 bullet）；改动后该格出现琥珀高亮边框
- 底部 Cancel / Save 按钮，Save 只保存该行，Cancel 还原该行
- 点击保存，应再次走驱逐字化和脱敏流程，完成后再保存

**Visible to** 

- 谁能看到这一行内容
- 不同角色看到的如果是同样的内容，则合并展示
- Expert testimony 分别展示管理端和Founder端的措辞

**Authorize** 

- 勾选则授权，visible to中的角色即可看到该行内容

**注：具体的操作步骤的实现形式参考文档“会议内容提取规则”** (https://github.com/WenchaoChen1/LG/blob/master/docs/Fireflies%20%E8%BD%AC%E5%BD%95%E6%8E%A5%E5%85%A5/%E8%B0%83%E7%A0%94/%E4%BC%9A%E8%AE%AE%E5%86%85%E5%AE%B9%E6%8F%90%E5%8F%96%E8%A7%84%E5%88%99-%E9%9C%80%E6%B1%82%E6%96%87%E6%A1%A3.md)
