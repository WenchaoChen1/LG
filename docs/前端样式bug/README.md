# 前端样式 Bug 清单

> 对比基准：**LG-UI**（`Remix of LG-UI_UX/`，Lovable 导出的 shadcn-ui + Tailwind 项目）= 目标 UI 样式
> 当前系统：**CIOaas-web**（UmiJS + Ant Design + Less）
> 对比方式：**代码级**（直接读样式源码，精确到 px / hex / 字重 / hover）
> 整理结构：**按页面分文件**，本 README 放全局主题色对照与跨页面共性问题。

---

## 页面索引

| 页面 | 路由（LG-UI） | 报告文件 | 状态 |
|------|--------------|----------|------|
| 财务页 Financial → Import Statements 弹窗 | `/dashboard/block/financial` | [财务页-Financial.md](./财务页-Financial.md) | ✅ 已整理 |

---

## 全局主题色对照表

两边**共用同一套品牌语言**（金色 + 深蓝 navy + Futura PT 字体），但当前系统在落地时出现了若干**色值不统一**问题，整理字体/颜色 bug 时需结合当前系统既定主题色判断「真偏差」还是「合法品牌色」。

| 语义 | LG-UI 目标 | 当前系统实际取值 | 状态 |
|------|-----------|-----------------|------|
| **品牌金（primary / 强调）** | `#E1990F` | 自定义 Less：`#E1990F` ✅ ／ Ant 主色 `primaryColor`：`#FAAD14` ⚠️ ／ 导入弹窗：`#F59F0A` ⚠️ | ⚠️ **三处金色不一致** |
| 深蓝 navy（标题 / 品牌文字色） | blue-900 ≈ `#0E2C58`；弹窗标题 `#0D2B56` | `#0D2B56`（`--blue-900`，全站文字品牌色） | ✅ 一致 |
| 正文近黑 foreground | `#15191C`（grey-900） | `#111827` | 近似，差异可忽略 |
| 次级灰文字 muted-foreground | `#848688`（grey-600） | `#6B7280` / `#9CA3AF`（不统一） | 近似 |
| 边框灰 border | `#ECEEF1`（grey-300，极浅） | `#E5E7EB` / `#D6D8DC` / `#D1D5DB`（三种，偏深） | ⚠️ 偏深且不统一 |
| 字体 | `Futura PT`（CDN） | `Futura-PT-Demi` / `Futura-PT-Medium`（本地 .otf） | ✅ 同字族 |

### 🔑 关键发现（跨页面共性，优先级最高）

1. **三种金色并存**
   - 品牌金 `#E1990F`（LG-UI 与当前 `global.less` / `index.less` 用的就是它）
   - Ant Design 主色 `#FAAD14`（`config/defaultSettings.ts: primaryColor`）→ 所有走 Ant token 的主色元素（主按钮、开关、选中态、Tabs 高亮…）会渲染成 `#FAAD14`
   - 导入弹窗 `#F59F0A`（`ImportStatementsModal.less`，进度条 / Next 按钮 / 拖拽 hover / Remove / Clear All 全用它）
   - **建议**：统一收敛到品牌金 `#E1990F`；Ant `primaryColor` 也应改为 `#E1990F` 以保证 Ant 组件与自定义样式一致。

2. **边框灰不统一**：当前系统在不同位置用了 `#E5E7EB` / `#D6D8DC` / `#D1D5DB`，且整体比 LG 的 `#ECEEF1` 偏深。建议统一为一个浅灰 token。

3. **字体颜色判断原则**（回应「字体颜色要参照当前系统主题色」）：
   - 标题 / 主要文字用的 `#0D2B56`（navy）是**当前系统既定品牌文字色** → **保留**，不按 LG 的近黑 `#15191C` 一刀切。
   - 真正需要修的是**金色强调色** `#F59F0A` → 应统一为品牌金 `#E1990F`。
   - 近黑（`#111827` vs `#15191C`）、灰（`#6B7280` vs `#848688`）差异极小，可统一但非必须。

---

## 严重度图例

| 标记 | 含义 |
|------|------|
| 🔴 高 | 明显偏离品牌 / 视觉差异大（如金色不对、图标风格不同、文案大小写） |
| 🟡 中 | 尺寸 / 边框 / 圆角 / 字号差异，肉眼可辨 |
| 🔵 低 | 1–2px 或近似色差异，或属当前系统合法主题色（可保留） |
