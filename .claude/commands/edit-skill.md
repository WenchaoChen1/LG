# 编辑 Requirement Skill

查看并编辑 `.claude/commands/` 目录下由需求文件生成的 skill 规则。

## 使用方式

```
/edit-skill              # 列出所有可编辑的 skill
/edit-skill <skill名>    # 直接编辑指定 skill
```

例如：`/edit-skill user-management`

---

## 执行步骤

### 情况一：未提供参数（`$ARGUMENTS` 为空）

1. 读取 `D:/github-code/LG/.claude/commands/` 目录下所有 `.md` 文件
2. 排除以下 4 个系统 skill：`parse-req.md`、`req-to-skill.md`、`edit-skill.md`、`run-skill.md`
3. 以表格形式列出所有可用 skill：
   - Skill 名称（调用命令）
   - 文件路径
   - 需求来源（从文件头部 `需求来源：` 字段读取）
   - 最后更新时间

4. 提示用户输入 `/edit-skill <skill名>` 进行编辑

### 情况二：提供了 skill 名称

1. 定位文件：`D:/github-code/LG/.claude/commands/<skill名>.md`
2. 读取并**完整展示**当前内容
3. 询问用户要修改哪部分：
   - **[1] 业务规则** — 修改约束条件、规则列表
   - **[2] 执行步骤** — 修改 Claude 的操作流程
   - **[3] 注意事项** — 修改边界条件/异常处理
   - **[4] 使用方式** — 修改参数说明
   - **[5] 整体重写** — 保留需求来源信息，重写其余内容
   - **[6] 自由编辑** — 用户直接描述要改什么

4. 根据用户选择，执行对应修改并写回文件
5. 以 diff 格式展示本次变更（`+ 新增行` / `- 删除行`），然后确认是否满意
6. 若修改涉及"执行步骤"或"业务规则"章节，额外提示：`⚠ 此修改与需求文件可能不同步，建议同步更新 requirements/<需求文件名>.md`

---

## 规则

- 修改时保留文件头部的 `> 最后更新` 和 `> 需求来源` 元信息，并将 `最后更新` 更新为今天的日期（格式：`YYYY-MM-DD`）
- 禁止删除 4 个系统 skill：`parse-req.md`、`req-to-skill.md`、`edit-skill.md`、`run-skill.md`
- 如果指定的 skill 不存在，提示用户检查名称或使用 `/req-to-skill` 先生成
