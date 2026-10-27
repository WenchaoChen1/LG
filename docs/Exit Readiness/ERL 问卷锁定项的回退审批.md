# ERL 问卷锁定项的回退审批

## 原始需求：

上个季度的回答已提交，但想做更改，需要向 GS 申请修改权限，GS 同意后才能修改



## 需求解读：

**背景：**

ERL 各维度问卷默认采用单向推进机制：已达成（Yes）项在下一季度自动结转并锁定，不再复评。

**特殊场景：**

创始人在填写新一季度问卷时，发现某道从上季度结转、锁定为 Yes 的题目，其实际情况在本季度已不再成立，需要将答案改为 No。

**处理规则：**

此类锁定项的回退操作需走 GS 审批流程，审批通过后该题答案由 Yes 修改为 No。

**核心概念：**

锁定题回退：对已锁定的历史达成项，在新一季度中申请解锁并反向作答，须经 GS 审批。



## 功能说明：

### **一、创始人端（申请方）**

1. **锁定题目展示**

- 默认收起，支持用户逐个stage展开查看题目内容
- 每道锁定题目右侧提供「Change to No」入口（申请修改按钮）

2. **修改确认弹框**

点击 Change to No 后弹出确认框，包含：
- 题目原题（只读展示）
- 修改原因文本框（必填）
- Cancel 按钮：关闭弹框，答案保持不变
- Apply 按钮(必填字段填后激活）：
  - 发送申请至管理端
  - 关闭弹框
  - 后续题目置灰不可继续作答
  - Save as Draft / Submit 按钮置灰
  - 该季度该维度问卷顶部显示审核中状态条

3. **审核中状态条（页面顶部提示）**

▎ Under Review — Your request to change a locked answer is pending approval.
▎ Submitted by: {用户名} · On: {提交时间}
▎ Question: {题目} · Change: Yes → No · Reason: {修改原因}

4. **申请提交后的作答规则**

- 当前季度该维度：不可再次提交正式答卷，仅可保存草稿
- 草稿中的锁定题范围 = 以当前最后一次正式提交的季度为准
- 未来季度：可继续保存草稿、可继续提交正式数据，锁定题目范围仍以当前最后一次正式提交的季度为准

5. **申请自动作废规则**

- 触发条件：在该申请待审核期间，用户又提交了同维度未来季度的问卷正式答卷
- 原因说明：待审核状态下锁定题尚未回退；若此时未来季度已正式提交，问卷进度已超越申请回退的题目进度，回退申请失去意义
- 系统行为：申请自动作废，审核人进入页面后展示提示语

审核人页面提示语（申请作废）：

▎ This request has been automatically voided.
▎ The applicant has since submitted a later quarter's questionnaire for this dimension, which has advanced beyond the question in this request. The rollback is no longer applicable, and no action is required.

---

### 二、申请发送方式

**邮件通知**

- 收件人：该公司所有 Portfolio Group Manager 邮箱
- 邮件内容：
  - 问题修改申请描述（题目、原答案 Yes → 新答案 No、修改原因、提交人、提交时间）
  - 问卷路由链接按钮（跳转至待审核问卷页面）

邮件正文提示语：

▎ A locked answer rollback request requires your review.
▎ Applicant: {用户名} · Company: {公司名} · Dimension: {维度} · Quarter: {季度}
▎ Question: {题目}
▎ Requested change: Yes → No
▎ Reason provided: {修改原因}
▎
▎ Click the button below to review the full questionnaire and approve or refuse this request.
▎ [Review Request]

---

### **三、管理端（审核方）**

1. **审核页面**

点击邮件链接进入待审核问卷页面（Founder问题详情页）：

- 展示待审核状态条
  - ▎ Submitted by: {用户名} · On: {提交时间}
    ▎ Question: {题目} · Reason: {修改原因}

- 展示问卷内容和所有答案（只读）
- 高亮待审核的锁定题及修改请求
- 底部提供 Approve / Refuse 按钮

2. **Approve 流程**

- 点击 Approve → 弹出确认框

Approve 确认弹框提示语：

▎ Approve this rollback request?
▎ The locked answer for "{题目}" will be changed from Yes to No, and this quarter's questionnaire will be formally submitted on the applicant's behalf. Drafts for this and future quarters will be preserved.
▎
▎ [Cancel] [Confirm Approval]

- 点击 Confirm Approval 后：
  - 该题答案由 Yes 改为 No 生效
  - 该季度该维度问卷正式提交
  - 发送通知邮件给提交人
  - 该季度及未来季度草稿保留（回退后锁定题减少，不影响后续草稿修改）

通知提交人邮件（Approve）：

▎ Your rollback request has been approved.
▎ Question: {题目} · Change applied: Yes → No
▎ Reviewed by: {审核人} · On: {审核时间}
▎ The questionnaire for {季度} · {维度} has been formally submitted. Your drafts for this and future quarters remain available for editing.

3. **Refuse 流程**

- 点击 Refuse → 弹出弹框，包含必填的拒绝原因文本框
- 输入字符后 Send 按钮激活
- 点击 Send 后：
  - 修改无效，锁定题答案保持 Yes
  - 待审核状态消失
  - 发送通知邮件给提交人
  - 所有已提交问卷和草稿保持不变

Refuse 弹框提示语：

▎ Refuse this rollback request?
▎ Please provide a reason. This will be sent to the applicant.
▎
▎ Reason (required): [________________]
▎
▎ [Cancel] [Send]

通知提交人邮件（Refuse）：

▎ Your rollback request has been declined.
▎ Question: {题目} · Requested change: Yes → No (not applied)
▎ Reviewed by: {审核人} · On: {审核时间}
▎ Reason: {拒绝原因}
▎ The locked answer remains unchanged. All submitted questionnaires and drafts are preserved. You may continue editing drafts or submit a new request if circumstances change.

---

四、状态流转一览
<img width="833" height="243" alt="image" src="https://github.com/user-attachments/assets/34d96dad-531d-4aae-bdf3-8b12d79dce37" />

