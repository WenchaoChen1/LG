# 测试用例：Benchmark Entry

- **需求来源**：benchmark-entry-requirements.md（本地 PRD）
- **所属项目**：LG - Benchmark Entry
- **生成时间**：2026-03-26

---

## 需求清单

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R1 | UI 需求 | 顶部导航栏左侧显示公司 Logo（图片），纯展示，无点击行为 |
| R2 | 功能需求 | 顶部导航栏中右区域显示 "Convert all currencies to USD" 文字和 Switch 开关，默认开启（checked），开启时琥珀色 |
| R3 | UI 需求 | 顶部导航栏右侧显示用户头像（圆形首字母缩写）+ 用户名 + 下拉箭头，纯展示，无下拉菜单功能 |
| R4 | UI 需求 | 页面标题区显示主标题 "Benchmark Entry"（28px，semibold，#0D2B56）和副标题（14px，灰色，Futura PT） |
| R5 | 业务规则 | 4 个固定预定义分类（Revenue & Growth / Profitability & Efficiency / Burn & Runway / Capital Efficiency），不可增加、删除、重命名 |
| R6 | UI 需求 | 同一 Category 下的 Metric 物理相邻，Category 单元格使用 rowSpan 纵向合并，垂直居中、左对齐 |
| R7 | 业务规则 | 6 个固定预定义指标，不可增加、删除，Metric 名称不可编辑 |
| R8 | 功能需求 | 点击 Metric 名称区域可展开/折叠详情数据，箭头图标同步切换（▶ ↔ ▼） |
| R9 | 功能需求 | Metric 折叠状态下，若存在详情数据，行尾显示 "{n} item(s)" 文字提示 |
| R10 | 功能需求 | 多个 Metric 可同时展开，互不影响 |
| R11 | 功能需求 | LG Formula 字段支持内联实时编辑，聚焦时边框可见，失焦时边框透明，内容实时保存 |
| R12 | 功能需求 | 展开 Metric 后，详情行下方显示 "Add detail" 按钮，点击后在末尾插入一行空白新增行（accent/30 高亮），"Add detail" 按钮暂时隐藏 |
| R13 | 业务规则 | 新增详情行时所有字段均为非必填，允许提交空行 |
| R14 | 功能需求 | 新增行点击 ✓ 或按 Enter 保存数据，新增行消失，数据以普通详情行样式显示，"Add detail" 按钮重新显示 |
| R15 | 功能需求 | 新增行点击 ✕ 取消，新增行消失，已输入数据丢弃，"Add detail" 按钮重新显示 |
| R16 | 功能需求 | 鼠标悬停详情行时，行背景变色，行尾渐变显示编辑按钮（✏️）和删除按钮（🗑️） |
| R17 | 功能需求 | 点击编辑按钮后，该行字段从只读变为可编辑控件（文本→输入框，Platform→Select，FY Period→YearPicker，Data→Select），操作按钮变为 ✓ 和 ✕ |
| R18 | 功能需求 | 编辑行点击 ✓ 或按 Enter 保存更新，行恢复只读状态 |
| R19 | 功能需求 | 编辑行点击 ✕ 取消，所有修改丢弃，恢复编辑前的值，行恢复只读状态 |
| R20 | 功能需求 | 点击删除按钮（🗑️）后，该行立即从列表中移除，无二次确认弹窗，不可撤销 |
| R21 | 业务规则 | Category 单元格 rowSpan 根据展开/折叠状态动态计算调整 |
| R22 | 功能需求 | 货币转换开关切换：开启→琥珀色，关闭→灰色，仅 UI 状态持久化，无实际转换逻辑 |
| R23 | UI 需求 | 表格包含 14 个数据列 + 1 个操作列，固定布局，最小宽度 1100px，溢出时横向滚动 |
| R24 | UI 需求 | 不同行类型有不同的背景色、悬停效果、边框和操作按钮显示规则 |
| R25 | UI 需求 | 空状态：无 Metric 数据时显示数据库图标 + "No benchmark entries yet" + "Add entries to get started" |
| R26 | 数据需求 | Platform 字段为下拉选择，可选值：Benchmarkit.ai / KeyBanc / High Alpha |
| R27 | 数据需求 | Data 字段为下拉选择，可选值：Actual / Forecast |
| R28 | 功能需求 | FY Period 字段通过年份选择器组件选择：弹出浮层，3×4 网格显示 12 个年份，支持十年段翻页，点击年份后浮层自动关闭 |
| R29 | UI 需求 | 数值字段（25th / Median / 75th）右对齐，等宽字体 |
| R30 | 功能需求 | 文本输入框中按 Enter 等同于点击 ✓ 确认（新增和编辑场景均支持） |
| R31 | 业务规则 | 数据仅存储在前端状态中，刷新页面后重置为初始样本数据 |
| R32 | 边界条件 | 每个 Metric 下可添加不限数量的详情行 |
| R33 | 功能需求 | LG Formula 输入框状态：默认边框透明，悬停时边框可见，聚焦时边框可见（主色调） |

## 测试用例

### 一、顶部导航栏

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-001 | 公司 Logo 展示 | 已打开 Benchmark Entry 页面 | 我查看顶部导航栏左侧区域 | 公司 Logo 图片正常显示 |
| | | | 我点击公司 Logo | 无任何跳转或响应，Logo 为纯展示 |
| TC-002 | 货币转换开关-默认状态 | 已打开 Benchmark Entry 页面 | 我查看顶部导航栏中右区域 | 显示 "Convert all currencies to USD" 文字和 Switch 开关 |
| | | | 我查看 Switch 开关状态 | 开关默认为开启（checked）状态，颜色为琥珀色 |
| TC-003 | 货币转换开关-关闭 | 已打开 Benchmark Entry 页面，开关为开启状态 | 我点击 Switch 开关 | 开关切换为关闭状态，颜色变为灰色 |
| TC-004 | 货币转换开关-重新开启 | 已打开 Benchmark Entry 页面，开关为关闭状态 | 我点击 Switch 开关 | 开关切换为开启状态，颜色变为琥珀色 |
| TC-005 | 用户信息展示 | 已打开 Benchmark Entry 页面 | 我查看顶部导航栏右侧区域 | 显示用户头像（圆形，首字母缩写）、用户名和下拉箭头 |
| | | | 我点击用户头像区域 | 无下拉菜单弹出，为纯展示 |

### 二、页面标题区

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-006 | 页面标题展示 | 已打开 Benchmark Entry 页面 | 我查看页面标题区域 | 主标题显示 "Benchmark Entry"（28px，semibold，色值 #0D2B56） |
| | | | 我查看副标题 | 副标题显示 "Manage and compare performance metrics across platforms"（14px，灰色，Futura PT 字体） |

### 三、Category 分类管理

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-007 | 固定分类展示 | 已打开 Benchmark Entry 页面 | 我查看表格第一列 "Looking Glass Category" | 显示 4 个固定分类：Revenue & Growth、Profitability & Efficiency、Burn & Runway、Capital Efficiency |
| TC-008 | Category 不可编辑 | 已打开 Benchmark Entry 页面 | 我尝试双击 Category 单元格文字 | Category 名称不可编辑，无输入框出现 |
| TC-009 | Category rowSpan 合并 | 已打开 Benchmark Entry 页面 | 我查看 "Burn & Runway" 分类 | "Burn & Runway" 单元格使用 rowSpan 纵向合并，覆盖其下的 "Monthly Net Burn Rate" 和 "Monthly Runway" 两行 |
| | | | 我查看 Category 单元格对齐方式 | 单元格垂直居中、左对齐，带有右侧和底部边框，浅色背景 |
| TC-010 | Category-Metric 映射关系 | 已打开 Benchmark Entry 页面 | 我查看每个 Category 下的 Metric | Revenue & Growth 包含 ARR Growth Rate；Profitability & Efficiency 包含 Gross Margin；Burn & Runway 包含 Monthly Net Burn Rate 和 Monthly Runway；Capital Efficiency 包含 Rule of 40 和 Sales Efficiency Ratio |

### 四、Metric 展开/折叠

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-011 | Metric 默认折叠状态 | 已打开 Benchmark Entry 页面 | 我查看所有 Metric 行 | 所有 Metric 默认为折叠状态，箭头图标为 ▶ |
| TC-012 | 展开 Metric | 已打开 Benchmark Entry 页面，Metric 为折叠状态 | 我点击 "ARR Growth Rate" Metric 名称区域 | 箭头从 ▶ 变为 ▼ |
| | | | 我查看该 Metric 下方区域 | 显示所有详情行（如有） |
| | | | 我查看详情行下方 | 显示 "Add detail" 按钮 |
| | | | 我查看 Category 单元格 | "Revenue & Growth" 单元格 rowSpan 动态增加 |
| TC-013 | 折叠 Metric | 已打开 Benchmark Entry 页面，"ARR Growth Rate" 已展开 | 我点击 "ARR Growth Rate" Metric 名称区域 | 箭头从 ▼ 变为 ▶ |
| | | | 我查看该 Metric 下方区域 | 详情区域隐藏 |
| | | | 我查看 Category 单元格 | "Revenue & Growth" 单元格 rowSpan 动态减少 |
| TC-014 | 折叠时显示计数提示 | 已打开 Benchmark Entry 页面，"ARR Growth Rate" 已展开且存在 2 条详情数据 | 我点击 "ARR Growth Rate" 折叠该 Metric | Metric 行尾显示 "2 item(s)" 文字提示 |
| TC-015 | 折叠时无数据不显示计数 | 已打开 Benchmark Entry 页面，某 Metric 无详情数据 | 我查看该折叠状态的 Metric 行 | 行尾不显示 item(s) 计数文字 |
| TC-016 | 多个 Metric 同时展开 | 已打开 Benchmark Entry 页面 | 我点击 "ARR Growth Rate" 展开 | "ARR Growth Rate" 成功展开 |
| | | | 我点击 "Gross Margin" 展开 | "Gross Margin" 成功展开，"ARR Growth Rate" 仍保持展开状态 |
| | | | 我点击 "Rule of 40" 展开 | "Rule of 40" 成功展开，前两个 Metric 仍保持展开状态 |

### 五、LG Formula 编辑

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-017 | LG Formula 默认状态 | 已打开 Benchmark Entry 页面 | 我查看任一 Metric 的 LG Formula 列 | 输入框边框透明，背景透明，显示占位文字 "Enter formula" |
| TC-018 | LG Formula 悬停状态 | 已打开 Benchmark Entry 页面 | 我将鼠标悬停在 "ARR Growth Rate" 的 LG Formula 输入框上 | 输入框边框变为可见，背景保持透明 |
| TC-019 | LG Formula 聚焦编辑 | 已打开 Benchmark Entry 页面 | 我点击 "ARR Growth Rate" 的 LG Formula 输入框 | 输入框获得焦点，边框变为可见（主色调） |
| | | | 我输入 "(Current ARR - Previous ARR) / Previous ARR" | 内容显示在输入框中，实时保存，无需额外确认 |
| TC-020 | LG Formula 失焦 | 已在 LG Formula 输入框中输入内容 | 我点击页面其他区域 | 输入框失去焦点，边框恢复透明，已输入内容保留 |
| TC-021 | LG Formula 支持中英文 | 已打开 Benchmark Entry 页面 | 我点击 LG Formula 输入框并输入中文 "年增长率计算公式" | 中文内容正常显示和保存 |

### 六、新增详情数据

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-022 | 点击 Add detail 新增行 | "ARR Growth Rate" Metric 已展开 | 我点击 "Add detail" 按钮 | 在详情列表末尾插入一行空白新增行 |
| | | | 我查看新增行背景 | 新增行背景为 accent/30 高亮色 |
| | | | 我查看各字段 | 各字段显示对应输入控件（下拉选择、文本输入等） |
| | | | 我查看 "Add detail" 按钮 | "Add detail" 按钮暂时隐藏 |
| TC-023 | 新增行-填写完整数据后保存 | 已点击 "Add detail"，新增行已显示 | 我在 Platform 下拉选择 "Benchmarkit.ai" | 下拉选择成功，显示 "Benchmarkit.ai" |
| | | | 我在 Edition 输入 "Q3 2024 SaaS Benchmarks" | 文本正常输入显示 |
| | | | 我在 FY Period 点击年份选择器选择 "2024" | 年份选择器弹出浮层，选择 2024 后浮层关闭 |
| | | | 我在 25th 输入 "15%" | 数值正常输入显示 |
| | | | 我在 Median 输入 "25%" | 数值正常输入显示 |
| | | | 我在 75th 输入 "40%" | 数值正常输入显示 |
| | | | 我在 Data 下拉选择 "Actual" | 下拉选择成功 |
| | | | 我点击 ✓ 确认按钮 | 数据保存成功，新增行消失，数据以普通详情行样式显示，"Add detail" 按钮重新显示 |
| TC-024 | 新增行-提交空行 | 已点击 "Add detail"，新增行已显示 | 我不填写任何字段，直接点击 ✓ 确认按钮 | 空行成功保存，数据以普通详情行样式显示（所有字段为空值显示），"Add detail" 按钮重新显示 |
| TC-025 | 新增行-按 Enter 保存 | 已点击 "Add detail" 并在 Edition 输入框中输入内容 | 我在文本输入框中按 Enter 键 | 数据保存成功，效果等同于点击 ✓ 确认按钮 |
| TC-026 | 新增行-取消操作 | 已点击 "Add detail" 并填写了部分数据 | 我点击 ✕ 取消按钮 | 新增行消失，所有已输入数据丢弃，"Add detail" 按钮重新显示 |

### 七、编辑详情数据

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-027 | 悬停显示操作按钮 | "ARR Growth Rate" 已展开，存在至少一条详情数据 | 我将鼠标悬停在某条详情行上 | 行背景变为悬停色 |
| | | | 我查看行尾区域 | 行尾渐变显示 ✏️ 编辑按钮和 🗑️ 删除按钮 |
| TC-028 | 鼠标移出隐藏操作按钮 | 已悬停在详情行上，操作按钮已显示 | 我将鼠标移出该详情行 | 行背景恢复默认，编辑和删除按钮渐变隐藏（opacity 恢复为 0） |
| TC-029 | 进入编辑模式 | 已悬停在详情行上，操作按钮已显示 | 我点击 ✏️ 编辑按钮 | 该行所有字段从只读文本变为可编辑控件 |
| | | | 我查看文本类字段 | 文本字段变为输入框（Input） |
| | | | 我查看 Platform 字段 | Platform 变为下拉选择（Select） |
| | | | 我查看 FY Period 字段 | FY Period 变为年份选择器（YearPicker） |
| | | | 我查看 Data 字段 | Data 变为下拉选择（Select） |
| | | | 我查看操作按钮 | 操作按钮变为 ✓（确认）和 ✕（取消） |
| TC-030 | 编辑后保存 | 详情行已进入编辑模式，Platform 原值为 "Benchmarkit.ai" | 我将 Platform 从 "Benchmarkit.ai" 更改为 "KeyBanc" | 下拉选择成功切换 |
| | | | 我点击 ✓ 确认按钮 | 数据更新保存，行恢复为只读状态，Platform 显示为 "KeyBanc" |
| TC-031 | 编辑后按 Enter 保存 | 详情行已进入编辑模式 | 我修改 Edition 字段内容 | 内容更新显示 |
| | | | 我在文本输入框中按 Enter 键 | 数据更新保存，行恢复为只读状态 |
| TC-032 | 编辑后取消 | 详情行已进入编辑模式，Platform 原值为 "Benchmarkit.ai" | 我将 Platform 从 "Benchmarkit.ai" 更改为 "High Alpha" | 下拉选择成功切换 |
| | | | 我点击 ✕ 取消按钮 | 所有修改丢弃，Platform 恢复为 "Benchmarkit.ai"，行恢复为只读状态 |

### 八、删除详情数据

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-033 | 删除详情行 | "ARR Growth Rate" 已展开，存在 3 条详情数据 | 我将鼠标悬停在第 2 条详情行上 | 行尾出现 🗑️ 删除按钮 |
| | | | 我点击 🗑️ 删除按钮 | 该行立即从列表中移除，无二次确认弹窗 |
| | | | 我查看剩余详情行 | 剩余 2 条详情数据正常显示 |
| TC-034 | 删除后 rowSpan 调整 | "Burn & Runway" 下 "Monthly Net Burn Rate" 已展开，存在详情行 | 我删除一条详情行 | Category 单元格 "Burn & Runway" 的 rowSpan 自动减少 |
| TC-035 | 删除最后一条详情行 | Metric 已展开，仅存在 1 条详情数据 | 我悬停该条详情行并点击 🗑️ 删除按钮 | 该行立即移除，详情区域仅剩 "Add detail" 按钮行 |
| TC-036 | 删除后折叠计数更新 | Metric 存在 3 条详情数据并处于展开状态 | 我删除 1 条详情行 | 详情行变为 2 条 |
| | | | 我折叠该 Metric | 行尾显示 "2 item(s)" |

### 九、年份选择器

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-037 | 年份选择器弹出 | 详情行处于编辑/新增模式 | 我点击 FY Period 的年份选择器按钮 | 弹出浮层（Popover），宽度 240px |
| | | | 我查看浮层内容 | 显示 3×4 网格，共 12 个年份 |
| | | | 我查看当前年份 | 当前年份（2026）使用 accent 背景色高亮 |
| TC-038 | 选择年份 | 年份选择器浮层已弹出 | 我点击 "2024" | 年份 "2024" 被选中，浮层自动关闭，按钮显示 "2024" |
| TC-039 | 年份选择器翻页 | 年份选择器浮层已弹出，当前显示 2020s 年段 | 我点击右箭头翻页按钮 | 切换到 2030s 年段，显示对应的 12 个年份 |
| | | | 我点击左箭头翻页按钮 | 切回 2020s 年段 |
| TC-040 | 十年外年份半透明 | 年份选择器浮层已弹出，当前十年段为 2020s | 我查看超出 2020-2029 范围的年份 | 十年段外的年份（如 2019、2030）半透明显示（opacity 50%） |

### 十、字段下拉选择

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-041 | Platform 下拉选项 | 详情行处于编辑/新增模式 | 我点击 Platform 下拉选择 | 显示 3 个选项：Benchmarkit.ai、KeyBanc、High Alpha |
| | | | 我选择 "KeyBanc" | Platform 字段显示 "KeyBanc" |
| TC-042 | Platform 留空 | 详情行处于新增模式 | 我不选择 Platform，保持为空 | Platform 不强制选择，允许留空 |
| TC-043 | Data 下拉选项 | 详情行处于编辑/新增模式 | 我点击 Data 下拉选择 | 显示 2 个选项：Actual、Forecast |
| | | | 我选择 "Forecast" | Data 字段显示 "Forecast" |

### 十一、空值显示与字段对齐

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-044 | 空值显示为破折号 | 存在一条详情行，Platform、Edition、Definition、FY Period、Segment、Data、Best Guess 字段为空 | 我查看该详情行的空值字段 | Platform、Edition、Definition、FY Period、Segment、Data、Best Guess 为空时显示 "—" |
| TC-045 | 数值字段右对齐和等宽字体 | 存在一条详情行，25th / Median / 75th 已填写数值 | 我查看 25th、Median、75th 列 | 数值右对齐显示，使用等宽字体 |

### 十二、表格样式与布局

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-046 | 表格列结构 | 已打开 Benchmark Entry 页面 | 我查看表格表头 | 共 15 列：Looking Glass Category、LG Metric Name、LG Formula、Platform、Edition、Metric Name、Definition、FY Period、Segment、25th、Median、75th、Data、Best Guess、操作列（无标题） |
| TC-047 | 表头样式 | 已打开 Benchmark Entry 页面 | 我查看表头行 | 浅灰背景，深蓝色文字，全大写，12px，medium 字重，加宽字距 |
| TC-048 | 表格横向滚动 | 在窄屏设备或缩小浏览器窗口宽度至小于 1100px | 我查看表格外层容器 | 出现横向滚动条，可左右滚动查看所有列 |
| TC-049 | 表格外框样式 | 已打开 Benchmark Entry 页面 | 我查看表格外框 | 圆角边框（6px），Futura PT 字体，14px |

### 十三、行样式

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-050 | Metric 父行折叠时悬停 | Metric 为折叠状态 | 我将鼠标悬停在 Metric 父行上 | 背景变为 --table-row-hover 色，底部有边框 |
| TC-051 | Metric 父行展开时无底部边框 | Metric 为展开状态 | 我查看 Metric 父行 | 父行无底部边框（与下方详情行连续） |
| TC-052 | 详情行只读悬停 | Metric 已展开，存在详情行 | 我将鼠标悬停在详情行上 | 行背景变为 --table-row-hover，行尾渐变显示 ✏️ 和 🗑️ |
| TC-053 | 新增行高亮样式 | 已点击 "Add detail" | 我查看新增行 | 背景为 accent/30 高亮色，底部有边框 |

### 十四、空状态

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-054 | 空状态展示 | 表格无任何 Metric 数据（初始空状态） | 我查看表格区域 | 显示数据库图标（40×40px，40% 透明度） |
| | | | 我查看空状态文案 | 主文案显示 "No benchmark entries yet"（14px，medium），副文案显示 "Add entries to get started"（12px） |
| | | | 我查看空状态布局 | 垂直居中，上下内边距 64px |

### 十五、数据持久化

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-055 | 刷新页面数据重置 | 已新增并保存多条详情数据 | 我刷新浏览器页面 | 页面数据重置为初始样本数据，新增的数据不保留 |

### 十六、边界条件

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-056 | 大量详情行添加 | "ARR Growth Rate" 已展开 | 我连续点击 "Add detail" 并保存，重复 20 次 | 每次新增均成功保存，共 20 条详情行正常显示，无性能问题 |
| | | | 我折叠 "ARR Growth Rate" | 行尾显示 "20 item(s)" |
| TC-057 | Metric 名称不可编辑 | 已打开 Benchmark Entry 页面 | 我尝试双击 Metric 名称 "ARR Growth Rate" | 无编辑行为，Metric 名称为只读 |
| TC-058 | 数值字段输入非数值 | 详情行处于新增/编辑模式 | 我在 25th 字段输入 "N/A" | 内容正常输入并保存（字段不做格式强制校验，存储为字符串） |
| TC-059 | 数值字段输入百分比 | 详情行处于新增/编辑模式 | 我在 Median 字段输入 "35.5%" | 内容正常输入并保存 |
| TC-060 | 年份选择器不支持手动键入 | 详情行处于新增/编辑模式 | 我尝试在 FY Period 字段手动键入年份 | 不支持手动键入，仅可通过年份选择器组件选择 |
| TC-061 | 同一 Metric 内 Add detail 时再次展开折叠 | "ARR Growth Rate" 已展开，新增行正在编辑中 | 我点击 "ARR Growth Rate" 折叠 | Metric 折叠，详情区域（包括新增行）隐藏 |
| | | | 我再次点击 "ARR Growth Rate" 展开 | Metric 展开，新增行状态应正确恢复或重置 |
| TC-062 | 已选年份高亮 | 年份选择器浮层已弹出，已选年份为 2024 | 我查看 2024 年份 | "2024" 使用 primary 背景色高亮，区别于当前年份的 accent 高亮 |

## 需求追溯矩阵

| 需求编号 | 需求描述 | 覆盖状态 | 对应测试用例 | 备注 |
|---------|---------|---------|------------|------|
| R1 | 公司 Logo 展示，无点击行为 | ✅ 已覆盖 | TC-001 | |
| R2 | 货币转换开关，默认开启，琥珀色 | ✅ 已覆盖 | TC-002, TC-003, TC-004 | |
| R3 | 用户头像+用户名+下拉箭头，纯展示 | ✅ 已覆盖 | TC-005 | |
| R4 | 页面标题和副标题样式 | ✅ 已覆盖 | TC-006 | |
| R5 | 4 个固定分类不可变 | ✅ 已覆盖 | TC-007, TC-008 | |
| R6 | Category rowSpan 合并，垂直居中左对齐 | ✅ 已覆盖 | TC-009 | |
| R7 | 6 个固定指标不可变 | ✅ 已覆盖 | TC-010, TC-057 | |
| R8 | Metric 展开/折叠，箭头切换 | ✅ 已覆盖 | TC-011, TC-012, TC-013 | |
| R9 | 折叠时显示 "{n} item(s)" 计数 | ✅ 已覆盖 | TC-014, TC-015 | |
| R10 | 多个 Metric 同时展开 | ✅ 已覆盖 | TC-016 | |
| R11 | LG Formula 内联编辑，实时保存 | ✅ 已覆盖 | TC-017, TC-018, TC-019, TC-020, TC-021 | |
| R12 | Add detail 按钮，新增行高亮，按钮隐藏 | ✅ 已覆盖 | TC-022 | |
| R13 | 新增详情行所有字段非必填 | ✅ 已覆盖 | TC-024 | |
| R14 | 新增行点击 ✓ 或 Enter 保存 | ✅ 已覆盖 | TC-023, TC-025 | |
| R15 | 新增行点击 ✕ 取消 | ✅ 已覆盖 | TC-026 | |
| R16 | 悬停显示编辑和删除按钮 | ✅ 已覆盖 | TC-027, TC-028 | |
| R17 | 编辑模式字段变为可编辑控件 | ✅ 已覆盖 | TC-029 | |
| R18 | 编辑行保存（✓ 或 Enter） | ✅ 已覆盖 | TC-030, TC-031 | |
| R19 | 编辑行取消，恢复原值 | ✅ 已覆盖 | TC-032 | |
| R20 | 删除即时生效，无确认，不可撤销 | ✅ 已覆盖 | TC-033, TC-035 | |
| R21 | Category rowSpan 动态调整 | ✅ 已覆盖 | TC-012, TC-013, TC-034 | |
| R22 | 货币开关切换颜色 | ✅ 已覆盖 | TC-003, TC-004 | |
| R23 | 表格 15 列，固定布局，横向滚动 | ✅ 已覆盖 | TC-046, TC-048, TC-049 | |
| R24 | 不同行类型样式差异 | ✅ 已覆盖 | TC-050, TC-051, TC-052, TC-053 | |
| R25 | 空状态展示 | ✅ 已覆盖 | TC-054 | |
| R26 | Platform 下拉 3 个选项 | ✅ 已覆盖 | TC-041, TC-042 | |
| R27 | Data 下拉 2 个选项 | ✅ 已覆盖 | TC-043 | |
| R28 | 年份选择器组件规格 | ✅ 已覆盖 | TC-037, TC-038, TC-039, TC-040, TC-062 | |
| R29 | 数值字段右对齐等宽字体 | ✅ 已覆盖 | TC-045 | |
| R30 | Enter 键等同 ✓ 确认 | ✅ 已覆盖 | TC-025, TC-031 | |
| R31 | 前端数据刷新重置 | ✅ 已覆盖 | TC-055 | |
| R32 | 详情行无数量限制 | ✅ 已覆盖 | TC-056 | |
| R33 | LG Formula 输入框三态样式 | ✅ 已覆盖 | TC-017, TC-018, TC-019, TC-020 | |

**覆盖率：100%**（33/33 需求全部覆盖）
