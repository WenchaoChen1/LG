# 需求文件转开发 Skill

将完整闭环需求文档转换为可执行的开发 skill。支持新工作流（`features/<name>/requirement/requirement-doc.md`）和旧工作流（`features/<name>/req-spec.md`）两种路径。
生成的 skill 会强绑定需求文件，执行时自动加载需求上下文并在完成后对照验收标准检查。

## 使用方式

```
/req-to-skill <需求文件路径>
```

例如：
- `/req-to-skill features/user-management/requirement/requirement-doc.md`（新工作流）
- `/req-to-skill features/user-management/req-spec.md`（旧工作流）

> 建议先用 `/gen-requirement-doc` 生成需求文档（新工作流），或 `/parse-req` 补全为完整闭环需求（旧工作流），再执行本命令

---

## 执行步骤

1. **读取需求文件**：读取 `$ARGUMENTS` 指定的需求文件（路径相对于 `D:/github-code/LG/`）。支持以下路径格式：
   - `features/<name>/requirement/requirement-doc.md`（新工作流）
   - `features/<name>/req-spec.md`（旧工作流）

2. **提取关键信息**：
   - 功能模块名称 → skill 文件名（小写英文 + 连字符）
   - 涉及的前端路径（第 6 章）
   - 涉及的后端业务域（第 4、5 章）
   - 权限规则（第 7 章）
   - 验收标准（第 10 章）—— 将嵌入 skill，作为完成判断依据

3. **检查命名冲突**：若 `.claude/commands/<skill名>.md` 已存在，先将旧文件备份为 `<skill名>.bak.md`，再继续生成

4. **生成开发 skill 文件**：路径 `D:/github-code/LG/.claude/commands/<skill名>.md`，格式见下方模板

5. **展示并确认**：展示生成内容，提示用户可用 `/edit-skill <skill名>` 修改，用 `/run-skill <skill名>` 执行

---

## 开发 Skill 文件模板

```markdown
# <功能名称>

> 最后更新：<生成日期>
> 需求来源：<需求文件实际路径，如 features/<name>/requirement/requirement-doc.md>
> 需求版本：<需求文件中的版本号>

## 需求摘要

<从需求文件第 1、2 章提取的背景与目标，2-3 句话>

## 开发范围

**前端**
- 页面/路由：<从需求第 6 章提取>
- 涉及文件：`CIOaas-web/src/pages/xxx/`

**后端**
- 涉及业务域：<根据 API 路径前缀推断：`/fi/` → `fi/`、`/di/` → `di/`、`/etl/` → `etl/` 等，对照 `CIOaas-api/gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/` 下目录>
- 涉及文件：`CIOaas-api/.../xxx/`

**数据库**
- <从需求第 5 章提取的表变更>

## 业务规则

<从需求第 3、7 章提取，逐条编号列出>

## 执行步骤

> 执行前请先读取需求文件：`<需求文件实际路径>` 获取完整上下文

### 前置检查
1. 读取 `<需求文件实际路径>` 确认需求理解无误
2. 检查相关现有代码文件，了解当前实现

### 后端开发
<根据需求第 3、4、5 章生成具体步骤，遵循以下固定分层结构>
1. **Domain**：在 `domain/` 下新增/修改实体类及字段
2. **Repository**：在 `repository/` 下新增查询方法
3. **Service**：在 `service/` 下实现业务逻辑
4. **Mapper**：在 `mapper/` 下新增 MapStruct 映射方法
5. **DTO**：在 `contract/` 下新增请求/响应 DTO
6. **Controller**：在 `controller/` 下新增/修改接口，注解权限

### 前端开发
<根据需求第 6、7 章生成具体步骤，遵循以下固定结构>
1. **Service**：在 `src/services/` 下新增 API 请求函数
2. **Model**：在 `src/models/` 下新增/修改 dva state 及 effects
3. **页面组件**：在 `src/pages/xxx/` 下实现页面和组件
4. **路由注册**：在 `config/routes.ts` 中添加路由配置

### 收尾
1. 检查权限控制是否按需求第 7 章实现
2. 对照验收标准逐项确认（见下方）

## 验收标准

> 完成开发后逐项检查，全部通过方可提交

<从需求第 10 章原样复制，保持 checkbox 格式>
- [ ] 标准一
- [ ] 标准二

## 注意事项

<从需求第 3.3、11 章提取的异常处理和风险>
```

---

## 规则

- 如果 `$ARGUMENTS` 为空，扫描 `features/` 目录，列出含 `requirement/` 或 `req-spec.md` 的功能目录供选择
- 生成的 skill 中**必须包含验收标准**，来自需求文件第 10 章
- 生成的 skill 中**执行步骤必须引用需求文件路径**，确保执行时能追溯上下文
- Skill 名称与需求文件主题一致
