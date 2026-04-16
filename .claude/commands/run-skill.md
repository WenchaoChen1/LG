# 主动执行 Requirement Skill

列出所有可用的 requirement skill，选择并主动执行其中定义的步骤。

## 使用方式

```
/run-skill              # 列出所有 skill，交互式选择执行
/run-skill <skill名>    # 直接执行指定 skill
```

---

## 执行步骤

### 情况一：未提供参数

1. 读取 `D:/github-code/LG/.claude/commands/` 下所有 `.md` 文件
2. 排除以下 4 个系统 skill：`parse-req.md`、`req-to-skill.md`、`edit-skill.md`、`run-skill.md`
3. 以编号列表展示所有可用 requirement skill：
   ```
   可执行的 Requirement Skills：
   [1] user-management     — 用户管理功能
   [2] portfolio-assign    — Portfolio 分配逻辑
   ...
   输入编号或 skill 名称来执行：
   ```
4. 用户输入编号或名称后，进入情况二

### 情况二：执行指定 skill

1. 读取 `D:/github-code/LG/.claude/commands/<skill名>.md` 的完整内容
2. 读取文件头部的 `> 需求来源` 字段，自动加载对应需求文件以获取完整上下文（路径可能为 `features/<name>/requirement/requirement-doc.md` 或 `features/<name>/req-spec.md`，按实际路径加载）
3. 展示该 skill 的**业务背景**和**执行步骤**，让用户确认
4. 询问执行所需的参数（如 skill 中定义了输入参数）
5. **按照 skill 文件中"执行步骤"一节逐步执行**：
   - 读取相关代码文件
   - 执行代码修改、生成、验证等操作
   - 每完成一步输出进度
6. 执行完毕后，逐条检查 skill 中"验收标准"章节的每个 checkbox，输出：
   ```
   ✓ 已完成 x/x 项，待确认：<未勾选项列表>
   ```

---

## 规则

- 执行前必须展示步骤并等待用户确认，不得静默执行
- 若 skill 文件中有"注意事项"，执行前必须先提示用户
- 执行过程中遇到不确定的情况，暂停并询问用户，不自行假设
- 系统 skill（parse-req、req-to-skill、edit-skill、run-skill）不在执行列表中
