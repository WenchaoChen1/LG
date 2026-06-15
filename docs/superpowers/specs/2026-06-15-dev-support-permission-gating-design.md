> 关联文档: [AI Chatbot 设计](../../AI-Chatbot/设计/design-doc.md)、[断流恢复计划](../plans/2026-06-15-ai-chatbot-resume-streaming.md)

# Dev Support 入口接入权限架构 — 设计文档

**日期**: 2026-06-15
**范围**: 纯前端（CIOaas-web），零后端代码改动
**决策**: 仅前端两层（菜单隐藏 + 路由守卫）；一个 `devSupport` 权限管整个入口

## 1. 背景与目标

顶部右侧头像下拉里的 "AI Development Support" 入口（路由 `/devSupport`，下含 AI Chatbot `/chat`、`/chatSimulate`、`/chatManage` 及 `/llm/*`、`/rag/*`、`/tracing`）目前是**写死的**，对所有登录用户无条件显示，且 `/devSupport/*` 路由**无任何守卫**——任何登录用户手输 URL 都能进。

目标：
1. 只有拥有该权限的用户才能看到入口按钮；
2. 只有拥有该权限的用户才能访问 `/devSupport` 下的全部路由，**手输 URL 也不行**（重定向）；
3. 复用现有"角色-菜单"机制，不引入新框架（YAGNI）。

后端 API 强制鉴权（`@PreAuthorize`）**不在本次范围**——与系统现状一致（全项目目前无 API 级按权限拒绝，仅校验登录）。

## 2. 现有机制（事实，基于代码核实）

旁边的 "Menu & Function Management"、"Roles Management" 等管理菜单本就是按权限显示的，链路：

```
menu 表(category=2 Top Right, path) → Roles Management 分配 → r_role_menu
  → 登录 getMenuTreeByRoleId → saveRoles() → localStorage['roles'] (rolesData)
  → BasicLayout.gst_menu 用 getVerifyRoles 按 path 比对 → 命中才渲染
```

关键代码：
- `src/layouts/BasicLayout.tsx`
  - `menuRight_SuperAdmin` 数组（~641）：管理端下拉项 `{key,name,type,path}`。
  - `getVerifyRoles`（560-576）：用 `ele.path === role.path` 过滤 `rolesData`（仅比对顶层）。
  - `getMenuList`（605-617）：`roleType===1` 走 `getVerifyRoles(superAdmin)`。
  - **写死项**（837-839）：`<Menu.Item key="aiDevSupport">AI Development Support</Menu.Item>`，在数组与过滤循环之外，无条件渲染。
  - `handleGSTMenuClick`（500-541）：已支持 `key==='aiDevSupport' → history.push('/devSupport')`。
- `src/models/login.ts`：所有用户都 `saveRoles(getNewMenuList)`（145）；仅 `roleType>1` 额外取 `getCompanyUserMenu` 存 `clientRoutePermissions`（153-173）。管理端登录强制 `roleType==1`（175-182）。
- `src/utils/utils.ts`：`getRoles()`(349) 读 `localStorage['roles']`，结构为 `[{path, name, menuDtoList:[{path,...}]}]`；`checkClientRoutePermission`(1467) 按 `menuList[].route===path` 匹配（仅 `roleType>1` 有数据）。
- `src/layouts/SecurityLayout.tsx`：逐条手写路由守卫，目前只挡 `/investmentDetails`（59-64，且 `roleType!=1` 才生效）。`/devSupport/*` 零守卫。

**结论**：Dev Support 唯一问题是前端写死了，没走上面这套机制。截图显示 menuManagement 里 "Dev Support"（Top Right / `/devSupport` / sort 20）已是受管菜单，菜单行很可能已存在 DB。

## 3. 改动方案

### ① 菜单按钮按权限显示 — `src/layouts/BasicLayout.tsx`

- 删除写死项（837-839）。
- 在 `menuRight_SuperAdmin` 数组追加：
  ```ts
  { key: 'aiDevSupport', name: 'AI Development Support', type: 1, path: '/devSupport' }
  ```
- 效果：改由 `getVerifyRoles` 过滤——`rolesData` 顶层含 `/devSupport`（角色被分配该菜单）才显示。跳转逻辑已存在，无需改。

### ② 路由守卫拦直连 URL — `src/utils/utils.ts` + `src/layouts/SecurityLayout.tsx`

- `utils.ts` 新增纯函数（复用 `getRoles()`，匹配顶层 + `menuDtoList` 子层，与全站既有结构一致）：
  ```ts
  export const hasMenuPermissionByPath = (path: string): boolean => {
    const roles = getRoles() || [];
    return roles.some((e: any) =>
      e.path === path || (e.menuDtoList || []).some((c: any) => c.path === path));
  };
  ```
- `SecurityLayout.tsx` 在通用重定向之前插入（覆盖整个子树 + 直连 URL）：
  ```tsx
  if (isLogin && (location.pathname === '/devSupport' || location.pathname.startsWith('/devSupport/'))) {
    if (!hasMenuPermissionByPath('/devSupport')) {
      return <Redirect to={isAdminEnd() ? '/company' : `/companyOverview?id=${companyData.id || ''}`} />;
    }
  }
  ```
- 与 `/investmentDetails` 模式的差异：**不排除 `roleType==1`**——要连超管也按"角色是否分配该菜单"来卡，故用对管理端也有数据的 `getRoles()`，而非只对客户端有效的 `checkClientRoutePermission`。

### ③ 配置（无代码，部署后管理员在页面操作）

1. 确认/补建 DB 菜单行：name "AI Development Support"、path `/devSupport`、category=2(Top Right)、enable。（截图显示已存在。）
2. 在 **Roles Management** 把 Dev Support 菜单分配给应有权限的角色。**先分配给自己的超管角色**，否则上线后自己也会看不到/进不去。

## 4. 行为变更与注意

- **客户端用户（roleType>1）将不再看到此入口**：此前写死项对所有人可见；改后仅管理端按角色显示。本入口为管理/内部 AI 控制台（管理端登录强制 roleType==1），故定为管理端专属。若未来客户端需聊天，应另开独立入口（不在本次范围）。
- **"权限生效 = 需要分配"**：分配前无人可见/可进，直到在 Roles Management 分配——符合预期，勿忘第③步。
- `startsWith('/devSupport/')` 不会误伤 `/devSettings`（前缀不同）。

## 5. 验证

- 单元测试：`hasMenuPermissionByPath` 命中顶层 / 命中 `menuDtoList` / 未命中 / 空 `roles` 四种情况。
- `npm run tsc` 通过（注意存量 2 个坏文件基线）。
- 手动：有权限角色登录可见入口、可进 `/devSupport/*`；无权限角色看不到入口、手输 URL 被重定向。

## 6. 影响文件清单

| 文件 | 改动 |
|------|------|
| `CIOaas-web/src/layouts/BasicLayout.tsx` | 删写死项；`menuRight_SuperAdmin` 加 `aiDevSupport` |
| `CIOaas-web/src/utils/utils.ts` | 新增 `hasMenuPermissionByPath` |
| `CIOaas-web/src/layouts/SecurityLayout.tsx` | 新增 `/devSupport` 子树路由守卫 |
| `CIOaas-web/src/utils/__tests__/...` | `hasMenuPermissionByPath` 单测 |
