# 测试用例：Redirect Users to Benchmark Company Dashboard Upon New Financial Data

- **需求来源**：`docs/Finance email+条幅+提醒/Redirect_to_Benchmark_Dashboard需求.md`
- **生成时间**：2026-04-24

---

## 需求清单

| #   | 需求类型 | 需求描述 |
|-----|----------|----------|
| R1  | 功能需求 | 场景 1：用户手动填写或通过 OCR 上传提交新 closed month 财务数据 |
| R2  | 功能需求 | 场景 1：提交新 closed month 成功后，提交人自动跳转到 Company Benchmarking 页面 |
| R3  | 功能需求 | 场景 1：其他有该公司权限的用户再次进入该公司 Financial Entry 页面时显示条幅提示（文案同场景 2 的通知文案） |
| R4  | 业务规则 | 场景 1：跳转到 Benchmarking 页面时自动应用预设过滤器——报告期 = 新提交的 closed month 月份 |
| R5  | 业务规则 | 场景 1：自动应用基准视图过滤器 = `Actuals – Internal Peers` |
| R6  | 业务规则 | 场景 1：用户无需手动配置过滤条件即可看到最相关的基准对比数据 |
| R7  | 功能需求 | 场景 2：第三方（如 QuickBooks）自动同步新的财务数据到 LG，系统识别新 closed month 并可用 |
| R8  | 业务规则 | 场景 2：系统不立即重定向，仅在有该公司权限的用户下次登录时显示条幅通知 |
| R9  | UI 需求  | 条幅通知文案：`Benchmark Data Updated. Benchmark results for have been updated based on the latest financial data.` |
| R10 | UI 需求  | 通知形式为条幅消息 |
| R11 | 功能需求 | 用户点击通知中的链接 → 跳转到 Company Benchmarking 页面 |
| R12 | 业务规则 | 跳转完成后条幅关闭，后续不再显示该通知 |
| R13 | 功能需求 | 用户可点击"关闭"按钮主动解除通知 |
| R14 | 业务规则 | 场景 2：进入 Benchmarking 页面同样应用预设过滤器（新月份 + `Actuals – Internal Peers`） |
| R15 | 业务规则 | 保持现有基准对标页面功能和数据完整性（不破坏既有筛选/展示） |

---

## 测试用例

### 一、场景 1 - 手动输入新 closed month 后自动跳转

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-001 | 手动填写新 closed month 后自动跳转 Benchmarking | 已登录有编辑权限的用户；进入 Company A 的 Financial Entry 页面；当前 closed month 为 2026-02 | 在 Financial Entry 页面手动填写 2026-03 月 Actuals 数据 | 数据保存成功 |
| | | | 点击提交/保存按钮 | 页面自动跳转至 Company A 的 Company Benchmarking 页面 |
| TC-002 | OCR 上传新 closed month 后自动跳转 | 已登录编辑权限用户；Company A closed month = 2026-02 | 在 Financial Entry 页面选择 OCR 上传 2026-03 财务数据文件 | OCR 解析完成，数据入库成功 |
| | | | 确认提交 | 自动跳转至 Company A 的 Company Benchmarking 页面 |
| TC-003 | 非新 closed month 的更新不跳转 | Company A 已有 2026-03 closed month；用户修改 2026-03 的某字段，但不产生新 closed month | 保存修改 | 页面不跳转 Benchmarking，仍停留在 Financial Entry 页面 |
| TC-004 | 提交失败不跳转 | Financial Entry 某必填字段缺失或触发校验失败 | 点击提交 | 出现错误提示；不跳转；用户留在 Financial Entry 页面 |
| TC-005 | 非提交人无自动跳转 | 用户 B 对 Company A 有访问权限但不是本次数据提交人；用户 A 完成提交 | 用户 B 在用户 A 提交期间保持自己的页面 | 用户 B 本人页面不被跳转 |

### 二、场景 1 - 预设过滤器自动应用

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-006 | 报告期自动设为新提交的 closed month | 用户提交 Company A 新 closed month = 2026-03 并跳转至 Benchmarking | 观察报告期过滤器值 | 过滤器显示 `2026-03`（新提交月份） |
| TC-007 | 基准视图自动设为 Actuals – Internal Peers | 同上跳转场景 | 观察基准视图过滤器 | 值为 `Actuals – Internal Peers` |
| TC-008 | 无需手动配置即可看到对比数据 | 同上跳转场景 | 观察页面内容 | 页面直接展示针对该月的 Actuals vs Internal Peers 对比数据 |
| TC-009 | 跳转后切换过滤器仍可正常工作 | 跳转落地 Benchmarking | 手动将报告期切换为 2026-02；基准视图切换为 `Actuals – KeyBanc 2026` | 页面刷新并展示新筛选条件下的数据（保持既有功能完整） |
| TC-010 | 跳转后再次提交下个月份过滤器重置 | 跳转后用户未改动过滤器；回到 Financial Entry 提交 2026-04 | 再次提交 | 再次跳转 Benchmarking，过滤器自动切换为 2026-04 + `Actuals – Internal Peers` |
| TC-011 | 跳转后首屏加载性能 | 用户完成提交触发跳转 | 观察 Benchmarking 页面加载 | 过滤器在首屏渲染时已应用，不出现先展示其他月/视图再切换的闪烁 |

### 三、场景 1 - 非提交人条幅提示

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-012 | 其他有权限用户进入 Financial Entry 看到条幅 | 用户 A 已提交 Company A 新 closed month；用户 B 对 Company A 有访问权限，提交发生时未在该页面 | 用户 B 登录系统并导航到 Company A 的 Financial Entry 页面 | 页面顶部显示条幅 `Benchmark Data Updated. Benchmark results for have been updated based on the latest financial data.` |
| TC-013 | 无权限用户不看到条幅 | 用户 C 对 Company A 无访问权限 | 用户 C 尝试访问 Company A Financial Entry | 无访问权限（被拒）；不显示条幅 |
| TC-014 | 条幅点击链接跳 Benchmarking 并应用过滤 | 用户 B 在 Financial Entry 看到条幅 | 点击条幅中的链接 | 跳转 Company A Benchmarking 页面；过滤器：报告期 = 新月份，基准视图 = `Actuals – Internal Peers` |
| TC-015 | 条幅关闭按钮解除通知 | 条幅正在显示 | 点击条幅"关闭"按钮 | 条幅立即消失 |
| TC-016 | 跳转后条幅关闭不再显示 | 用户 B 通过条幅链接跳转到 Benchmarking 后返回 Financial Entry | 返回并刷新 Financial Entry 页面 | 条幅不再显示 |
| TC-017 | 未关闭条幅下次登录仍显示 | 用户 B 看到条幅但未点击关闭、未点击链接；直接退出登录 | 用户 B 重新登录并进入 Financial Entry | 条幅仍显示 |
| TC-018 | 提交人不在 Financial Entry 看到自己的条幅 | 用户 A 为本次提交人 | 用户 A 返回 Financial Entry 页面 | 不显示条幅（提交人通过自动跳转已感知，不再二次条幅） |

### 四、场景 2 - 第三方同步触发通知

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-019 | QuickBooks 同步识别新 closed month | Company A 接入 QuickBooks；新 closed month = 2026-03 通过同步到达 LG | 同步完成后系统处理 | 系统识别 2026-03 为新可用 closed month |
| TC-020 | 同步不立即重定向用户 | 用户 B 当前正使用系统（非 Financial Entry 页面） | 同步在后台发生 | 用户 B 当前页面不被重定向；不中断其操作 |
| TC-021 | 下次登录触发条幅 | Company A 已因同步产生新 closed month；用户 B 有访问权限；尚未登录 | 用户 B 登录系统 | 登录后看到 Benchmark Data Updated 条幅 |
| TC-022 | 会话内未登录不触发通知 | 用户 B 在同步发生前已登录，并持续保持活跃会话 | 用户 B 继续操作 | 根据需求仅"下次登录时"显示——在当前会话内不主动弹出条幅（需在下次登录时显示） |
| TC-023 | 无访问权限用户不收到通知 | 用户 D 对 Company A 无访问权限 | 用户 D 登录系统 | 不显示 Company A 相关条幅 |

### 五、场景 2 - 条幅通知文案、形式与交互

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-024 | 通知文案完整性 | 用户登录后看到条幅 | 查看条幅文案 | 显示 `Benchmark Data Updated. Benchmark results for have been updated based on the latest financial data.` |
| TC-025 | 通知以条幅形式展现 | 用户登录后 | 观察通知 UI | 以页面条幅形式展示（非 Toast、非 Modal），位于页面顶部 |
| TC-026 | 条幅含可点击链接 | 条幅显示 | 查看条幅 | 文案中包含指向 Company Benchmarking 页面的可点击链接 |
| TC-027 | 点击链接跳转 Benchmarking | 用户点击条幅链接 | 观察跳转 | 浏览器打开 Company Benchmarking 页面 |
| TC-028 | 跳转落地页自动应用预设过滤器 | 接续 TC-027 | 观察过滤器 | 报告期 = 同步产生的新月份；基准视图 = `Actuals – Internal Peers` |
| TC-029 | 关闭按钮解除通知 | 条幅显示 | 点击"关闭"按钮 | 条幅消失，当前页面不再显示 |
| TC-030 | 关闭后再次登录不再显示同一条幅 | TC-029 后用户退出并重新登录 | 登录系统 | 该条同步触发的条幅不再显示 |
| TC-031 | 跳转后条幅关闭后续解除通知 | 用户点击条幅链接跳转 | 跳转完成后退出并再次登录 | 该条通知不再出现 |
| TC-032 | 未关闭未点击多次登录仍显示 | 用户登录看到条幅后未交互直接退出 | 再次登录 | 条幅仍显示 |

### 六、多公司/多通知场景

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-033 | 多家公司同时产生更新多条通知 | 用户对 Company A、Company B 都有权限；两家分别产生新 closed month 同步更新 | 用户登录系统 | 两条条幅通知均显示（或按公司聚合显示，每家公司一条） |
| TC-034 | 关闭其中一条不影响另一条 | 接续 TC-033 | 关闭 Company A 的条幅 | Company A 条幅消失；Company B 条幅仍显示 |
| TC-035 | 手动提交场景与同步场景条幅不重复 | Company A 已因同步产生条幅通知；随后用户 A 又手动提交了新一个月 closed month | 用户 B 登录 | 页面仅显示一条聚合/最新的条幅，不重复堆叠 |
| TC-036 | 同公司同月只通知一次 | Company A 同一新 closed month 触发一次通知；用户 B 已关闭后 | 系统未再次触发，用户 B 重新登录 | 不再显示该公司该月的条幅 |

### 七、Benchmarking 页面数据完整性

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-037 | 跳转不破坏既有过滤器/导航 | 用户跳转至 Benchmarking | 尝试切换其他 Tab、应用其他过滤条件、返回 Dashboard | 所有既有功能可正常使用，无报错、无数据缺失 |
| TC-038 | 跳转页面展示完整指标对比 | 跳转落地 Benchmarking | 滚动查看 6 个基准指标板块 | ARR Growth Rate、Gross Margin、Monthly Net Burn Rate、Monthly Runway、Rule of 40、Sales Efficiency Ratio 均正常显示 |
| TC-039 | 页面刷新后过滤器保持或回退符合预期 | 用户处于跳转后的 Benchmarking 页面 | 浏览器手动刷新（F5） | 刷新后过滤器仍为"报告期 = 新月份 + Actuals – Internal Peers"（或按系统默认规则处理，且不报错） |
| TC-040 | 直接从导航进入 Benchmarking 不受影响 | 用户未经条幅/提交流程，从侧边栏直接进入 Benchmarking | 查看过滤器 | 过滤器使用该页面原有默认值，不被预设过滤逻辑覆盖 |

---

## 需求追溯矩阵

| 需求编号 | 需求描述 | 覆盖状态 | 对应测试用例 | 备注 |
|---------|---------|---------|------------|------|
| R1  | 手动填写/OCR 上传提交新 closed month | ✅ 已覆盖 | TC-001, TC-002 | |
| R2  | 提交人自动跳转 Benchmarking | ✅ 已覆盖 | TC-001, TC-002, TC-003, TC-004 | 含不应跳转的反向场景 |
| R3  | 其他有权限用户在 Financial Entry 看到条幅 | ✅ 已覆盖 | TC-012, TC-013, TC-017, TC-018 | |
| R4  | 报告期过滤器 = 新 closed month 月份 | ✅ 已覆盖 | TC-006, TC-010, TC-014, TC-028 | |
| R5  | 基准视图 = Actuals – Internal Peers | ✅ 已覆盖 | TC-007, TC-014, TC-028 | |
| R6  | 无需手动配置即可看到对比数据 | ✅ 已覆盖 | TC-008, TC-011 | |
| R7  | 第三方同步识别新 closed month | ✅ 已覆盖 | TC-019 | |
| R8  | 同步不立即重定向，仅下次登录显示条幅 | ✅ 已覆盖 | TC-020, TC-021, TC-022 | |
| R9  | 条幅通知文案 | ✅ 已覆盖 | TC-012, TC-024 | |
| R10 | 通知形式为条幅消息 | ✅ 已覆盖 | TC-025 | |
| R11 | 点击通知链接跳 Benchmarking | ✅ 已覆盖 | TC-014, TC-026, TC-027 | |
| R12 | 跳转完成后条幅关闭并解除 | ✅ 已覆盖 | TC-016, TC-031 | |
| R13 | 点击关闭按钮解除通知 | ✅ 已覆盖 | TC-015, TC-029, TC-030, TC-034 | |
| R14 | 场景 2 同样应用预设过滤器 | ✅ 已覆盖 | TC-028 | |
| R15 | 保持既有 Benchmarking 功能与数据完整性 | ✅ 已覆盖 | TC-009, TC-037, TC-038, TC-039, TC-040 | |

**覆盖率：100%**（15/15 需求全部已覆盖）
