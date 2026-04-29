# Benchmark 通知 - 前端对接文档

> 后端分支：`feature/benchmark-notify-update`（CIOaas-api 子仓库）
> 本文档覆盖前端在两个 Benchmarking 页面（Admin portal / Company portal）接入横幅的全部细节。
> 横幅本身的显示组件 + dismiss 按钮 UI 是前端本次要新建的。

---

## 1. 横幅业务规则速览

| 场景 | 触发时机 | 显示页面 | 角色 | 文案（完整） |
|------|----------|---------|------|------------|
| **2.1 外部基准更新** | 管理员在 Benchmark Entry 新增 platform-edition 组合 | portfolio benchmarking tab / company benchmarking tab | Admin portal 用户 + Company Admin + Company User | `New benchmark data available. Benchmark comparisons now reflect the latest survey ({platform} — {edition}).` |
| **2.2 内部基准位置变化** | 每月 25 号定时批 或 应用启动时补发 或 手动重跑 | portfolio benchmarking tab / company benchmarking tab | Admin portal 用户 + Company Admin | `Benchmark positioning updated. Your company's placement may have shifted due to changes in benchmark data, not your financial performance.` |

**共同规则：**
- 首次登录该页面就显示
- 用户可关闭（调 dismiss 接口），不关闭则一直显示
- 多个平台-Edition 同时有更新 → 横幅合并到同一条，`{platform} — {edition}` 之间用逗号分隔（后端已处理 content 合并）
- 失权用户不显示（后端已过滤，前端正常调就行）

---

## 2. 数据结构与 notifyType 约定

### 2.1 notifyType 对照表

| Code | 枚举名 | 横幅类型 | 角色/入口 | 横幅固定文案模板 |
|------|-------|---------|----------|---------------|
| **1** | `ENTRY_UPDATE_COMPANY` | 2.1 外部更新 | Company Admin / Company User 看 company benchmarking tab | `New benchmark data available. Benchmark comparisons now reflect the latest survey ({content}).` |
| **2** | `ENTRY_UPDATE_PORTFOLIO_ADMIN` | 2.1 外部更新 | Admin portal 用户看 portfolio benchmarking tab | 同上 |
| **3** | `POSITION_UPDATE_COMPANY` | 2.2 位置变化 | Company Admin 看 company benchmarking tab | `Benchmark positioning updated. Your company's placement may have shifted due to changes in benchmark data, not your financial performance.` |
| **4** | `POSITION_UPDATE_PORTFOLIO_ADMIN` | 2.2 位置变化 | Admin portal 用户看 portfolio benchmarking tab | 同上 |
| **5** | `POSITION_UPDATE_PORTFOLIO_COMPANY` | 保留，当前后端未写入 | — | — |

**关键差异：**
- 类型 1/2（2.1）：后端 `content` 字段有意义（即 `{platform} — {edition}` 或合并后的多项）→ 前端需要把 content 内容插入到文案模板里
- 类型 3/4（2.2）：后端 `content` 为空字符串 → 前端直接显示固定文案，不使用 content

---

### 2.2 横幅实体字段（`BenchmarkNotifyAlertDto`）

```typescript
interface BenchmarkNotifyAlertDto {
  id: string;                // 横幅主键，dismiss 时用
  userId: string;            // 归属用户
  companyId: string;         // company 场景用，portfolio 场景为 ""
  companyGroupId: string;    // portfolio 场景用，company 场景为 ""
  notifyType: number;        // 1/2/3/4/5，见上表
  content: string;           // 2.1 有内容（platform — edition 可能多项逗号分隔），2.2 为空
  createdAt: string;         // ISO-8601 时间戳
}
```

---

## 3. API 清单

所有接口走 `/api/web` 前缀（umi-request 默认代理）。
所有接口需要登录 Bearer Token（`request.ts` 自动注入）。
所有响应包在项目通用 `Result<T>` 结构里：

```typescript
interface Result<T> {
  success: boolean;
  data: T;
  message?: string;
}
```

### 3.1 查询当前用户在某上下文下的横幅（GET）

用于页面加载时拉横幅。**每进入一个 benchmarking tab 页面只调一次**——一次拉到该上下文下所有命中的横幅类型，前端再按 `notifyType` 分流到对应 banner。

| 项 | 值 |
|---|---|
| Method | `GET` |
| Path | `/api/web/benchmark/notify-alerts` |
| 必填 | `userId` 当前用户 |
| 必填（二选一） | `companyId` **或** `companyGroupId` |
| 可选 | `notifyType` —— 只想拉单一类型时传，否则**别传**就能一次拿全部 |

#### Query 参数规则

| 调用场景 | userId | companyId | companyGroupId | notifyType |
|---------|--------|-----------|--------------|-----------|
| Admin portal 打开 portfolio benchmarking tab | 当前用户 | **省略** | 当前 portfolio id | **省略** → 一次返回 type=2 + type=4 全部命中横幅 |
| Company portal 打开 company benchmarking tab | 当前用户 | 当前 company id | **省略** | **省略** → 一次返回 type=1 + type=3 全部命中横幅 |
| 排查/调试，只想拉某一类 | 当前用户 | (按场景) | (按场景) | 1/2/3/4 |

#### 响应

```typescript
// 200 成功 —— 始终返回数组（不再返回单条对象）
{ success: true, data: BenchmarkNotifyAlertDto[] }

// 该上下文下没有任何横幅（没触发过 / 已被 dismiss / 权限失效全过滤掉）
{ success: true, data: [] }

// 400 BadRequest —— companyId 和 companyGroupId 都没传
{ success: false, message: "Either companyId or companyGroupId is required" }
```

返回数组里**最多 2 条**：
- Company 视角：`notifyType=1`（外部更新）+ `notifyType=3`（位置变化）
- Portfolio 视角：`notifyType=2`（外部更新）+ `notifyType=4`（位置变化）

如果只命中一种或都没命中，返回 1 条或空数组。

#### 调用示例

```typescript
// src/services/api/benchmark/notifyAlertService.ts
import request from '@/utils/request';

export type BenchmarkNotifyAlertDto = {
  id: string;
  userId: string;
  companyId: string;
  companyGroupId: string;
  notifyType: number;
  content: string;
  createdAt: string;
};

export async function listNotifyAlerts(params: {
  userId: string;
  companyId?: string;
  companyGroupId?: string;
  notifyType?: number;
}): Promise<BenchmarkNotifyAlertDto[]> {
  const res = await request('/api/web/benchmark/notify-alerts', {
    method: 'GET',
    params,
  });
  return res.success && Array.isArray(res.data) ? res.data : [];
}
```

---

### 3.2 关闭（dismiss）横幅（DELETE）

用户点击横幅上的关闭按钮时调用。

| 项 | 值 |
|---|---|
| Method | `DELETE` |
| Path | `/api/web/benchmark/notify-alerts/dismiss/{id}` |
| 参数 | Path `id` = `BenchmarkNotifyAlertDto.id` |

#### 响应

```typescript
{ success: true, data: "dismiss success" }
```

dismiss 后该行被**物理删除**（不是软删）。下次后端再触发相同 (user, company/group, notifyType) 的横幅会重新创建一条新记录。

#### 调用示例

```typescript
export async function dismissNotifyAlert(id: string): Promise<void> {
  await request(`/api/web/benchmark/notify-alerts/dismiss/${id}`, {
    method: 'DELETE',
  });
}
```

---

### 3.3 SME 手动重跑接口（可选，管理员后台）

仅当产品有"SME 手动运维页面"需求才接入。普通用户不需要。

#### 重跑某次月度批的 DIFF 阶段（重发邮件）

| 项 | 值 |
|---|---|
| Method | `POST` |
| Path | `/api/web/benchmark/position-monitor/rerun-diff/{runId}` |
| 参数 | Path `runId` = 某次 run 记录的 UUID |
| 响应 | `{ success: true, data: "rerun dispatched" }` |

#### 重新触发首次补发

| 项 | 值 |
|---|---|
| Method | `POST` |
| Path | `/api/web/benchmark/position-monitor/rerun-first-time` |
| 参数 | 无 |
| 响应 | `{ success: true, data: "catchup dispatched" }` |

---

## 4. 前端接入步骤（推荐实现顺序）

### Step 1 — 扩展 API service

新文件：`src/services/api/benchmark/notifyAlertService.ts`，包含 `listNotifyAlerts` + `dismissNotifyAlert`。

### Step 2 — 横幅区组件

每个 benchmarking tab 顶部挂一个 **`<NotifyBannerArea>`**（不是每种类型一个组件）——它内部一次性拉所有横幅、再按 type 渲染。

```typescript
type Scope =
  | { kind: 'company'; companyId: string }
  | { kind: 'portfolio'; companyGroupId: string };

interface NotifyBannerAreaProps {
  userId: string;
  scope: Scope;
}
```

组件逻辑：

```tsx
function NotifyBannerArea({ userId, scope }: NotifyBannerAreaProps) {
  const [alerts, setAlerts] = useState<BenchmarkNotifyAlertDto[]>([]);

  useEffect(() => {
    listNotifyAlerts({
      userId,
      companyId: scope.kind === 'company' ? scope.companyId : undefined,
      companyGroupId: scope.kind === 'portfolio' ? scope.companyGroupId : undefined,
    }).then(setAlerts);
  }, [userId, scope]);

  const onDismiss = async (id: string) => {
    await dismissNotifyAlert(id);
    setAlerts(prev => prev.filter(a => a.id !== id));
  };

  return (
    <>
      {alerts.map(a => (
        <Alert
          key={a.id}
          type="info"
          banner showIcon closable
          message={renderAlertText(a)}
          onClose={() => onDismiss(a.id)}
        />
      ))}
    </>
  );
}

function renderAlertText(a: BenchmarkNotifyAlertDto): string {
  // 类型 1/2 (2.1 外部更新)：动态文案，内容来自 a.content
  if (a.notifyType === 1 || a.notifyType === 2) {
    return `New benchmark data available. Benchmark comparisons now reflect the latest survey (${a.content}).`;
  }
  // 类型 3/4 (2.2 位置变化)：固定文案
  return "Benchmark positioning updated. Your company's placement may have shifted due to changes in benchmark data, not your financial performance.";
}
```

**关键点**：
- 一个组件实例 = 一次 GET 请求，比之前每 type 一个 banner 节省一次请求
- 每个返回的 alert 用各自的 `id` 单独 dismiss，互不影响
- 如果将来后端加新 notifyType，前端只在 `renderAlertText` 里加分支即可

### Step 3 — 在两个 benchmarking 页面集成

#### Admin portal — portfolio benchmarking tab
页面（大约 `src/pages/portfolioCompanies/Benchmarking/`）：
```tsx
<NotifyBannerArea userId={currentUserId} scope={{ kind: 'portfolio', companyGroupId: portfolioId }} />
```

#### Company portal — company benchmarking tab
页面（大约 `src/pages/companyFinance/benchmark/`）：
```tsx
<NotifyBannerArea userId={currentUserId} scope={{ kind: 'company', companyId }} />
```

每个页面**只挂一个** `NotifyBannerArea`，组件内部把 2.1 和 2.2 横幅同时渲染出来。

---

## 5. 邮件中的"View Benchmark"深链参数解码

用户点击邮件里的 `View Benchmark` 按钮会进入：
- Company 场景 → `/Finance?params=<base64>` （company benchmarking tab）
- Portfolio 场景 → `/company?params=<base64>` （portfolio benchmarking tab）

`params` 是 Base64 编码的查询串。现有 layout 或路由守卫应已经在处理 `params` 参数（2.1 Entry 的邮件用的就是同一格式，上线前试一试老邮件的跳转是否正常）。

**Company 场景 base64 解码后示例：**
```
companyId=c-123&active=5&userId=u-456
```

**Portfolio 场景：**
```
portfolioId=p-789&active=5&userId=u-456&organizationId=o-321
```

`active=5` 指的是 Benchmarking tab 的索引（项目里现有约定）。若前端路由层已经有处理，这块无需额外写代码。

### 未登录跳转
用户未登录状态下点击深链：现有 `request.ts` / `SecurityLayout` 的 401 逻辑会把 `redirect` 参数带到登录页，登录后回跳。这套走通就行。

### 失权场景
Portfolio manager 点邮件进来后若已失去对应 company 的权限，横幅**不会显示**（后端 `GET /benchmark/notify-alerts` 行级过滤掉该 alert）。前端正常调接口 + 按返回的数组渲染即可（失权场景该 alert 不在返回列表里）。

---

## 6. 测试要点（前端自测）

### 6.1 场景：管理员新增 platform-edition

1. 用 admin 账号登录
2. Benchmark Entry 页面新增一个全新 platform-edition 组合
3. 重新进入 portfolio benchmarking tab（或刷新）
4. 应看到 2.1 文案横幅，内容包含新 edition

关闭后：再次刷新 → 不再显示（dismiss 成功）。

### 6.2 场景：位置变化横幅

启动服务时 `BenchmarkPositionInitializer` 会异步跑首次补发，生成 2.2 横幅。直接登录进 benchmarking tab 应看到 2.2 固定文案。

关闭测试：dismiss 一个，刷新页面另一个 notifyType 的横幅仍在（独立关闭）。

### 6.3 场景：多个 platform-edition 合并

1. 依次新增 2 个不同 platform 的新 edition（如 KeyBanc-2026、HighAlpha-2027）
2. 刷新 benchmarking tab
3. 应看到**同一个** 2.1 横幅，`(KeyBanc — 2026, HighAlpha — 2027)` 逗号分隔

### 6.4 场景：权限失效

1. portfolio manager U 管 portfolio P，进入 P 页面看到 2.2 横幅
2. admin 把 U 从 P 的成员列表移除
3. U 刷新或重进 P 页面 → **横幅不显示**（`listNotifyAlerts` 返回的数组里没有 P 对应的 alert）

---

## 7. 常见问题

| 问题 | 答案 |
|------|-----|
| 横幅什么时候创建？ | 2.1：管理员新增 platform-edition 瞬间后端异步写入；2.2：每月 25 号 06:00 UTC 定时批 + 应用启动时异步补发 |
| 一个用户会收到多少条横幅？ | 每个 (user, company 或 group, notifyType) 组合最多 1 条 |
| 多个 Edition 触发时 content 怎么合并？ | 后端按 `,` 拼接到同一行 content，前端只拿一次就看到所有 |
| 前端需要轮询吗？ | 不需要。进入 benchmarking tab 时 GET 一次即可。如果产品要求"在页面停留时看到新横幅"，可以加 30 秒轮询；默认不需要 |
| dismiss 后怎么测"触发又出来"？ | 从后端 alert 表手动 DELETE 一条，或在 2.1 场景下新增一个新 platform-edition 来重新触发 |
| 失权用户调 GET 返回什么？ | `{ success: true, data: [] }`（不是 403）——后端做行级过滤，把无权限的 alert 从数组里剔除 |
| API 返回 500 怎么办？ | 走项目 `request.ts` 既有的错误 banner 逻辑即可；对横幅来说失败就当无横幅处理，不要 block 页面 |
| 邮件里的 `active=5` 是什么？ | benchmarking tab 的索引；现有 BasicLayout 路由已识别，前端不用处理 |

---

## 8. 字段 / 端点速查卡

```
GET    /api/web/benchmark/notify-alerts
         ?userId=...&companyId=...               # 公司视角
         ?userId=...&companyGroupId=...          # Portfolio 视角
         (可加 &notifyType=1|2|3|4 仅过滤单一类型，默认全部)
         → { success, data: BenchmarkNotifyAlertDto[] }     # 数组，最多 2 条

DELETE /api/web/benchmark/notify-alerts/dismiss/{id}
         → { success, data: "dismiss success" }

POST   /api/web/benchmark/position-monitor/rerun-diff/{runId}      # 运维用
POST   /api/web/benchmark/position-monitor/rerun-first-time        # 运维用
```

```
notifyType 1 = ENTRY_UPDATE_COMPANY        (company 页面, 2.1 外部更新)
notifyType 2 = ENTRY_UPDATE_PORTFOLIO_ADMIN (portfolio 页面, 2.1 外部更新)
notifyType 3 = POSITION_UPDATE_COMPANY     (company 页面, 2.2 位置变化)
notifyType 4 = POSITION_UPDATE_PORTFOLIO_ADMIN (portfolio 页面, 2.2 位置变化)
```

有任何字段对不上或接口行为与本文档不符，告诉我后端具体在哪一步出了差异，不要前端侧 hack。
