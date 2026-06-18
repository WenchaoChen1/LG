# 测试用例：数据映射 UI 中显示父级科目上下文

- **需求来源**：https://github.com/WenchaoChen1/LG/blob/master/docs/智能解析/需求文档-数据映射UI显示父级科目上下文.md
- **Asana 任务**：Display Parent Account Context in Data Mapping UI（task/1215349591481275）
- **适用页面**：Data Mapping（数据映射）审查视图 — 源财务科目侧
- **生成时间**：2026-06-16

---

---

## 测试用例

### 一、父级科目列展示

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-001 | 新增父级列紧邻名称列并列展示 | 上传含层级科目结构的文件，进入 Data Mapping 视图 | 查看源财务科目区的列布局 | 源科目名称列旁新增一个独立父级科目上下文列，与名称列并列展示 |
| TC-002 | 父级列有清晰标签 | 同上，已进入映射视图 | 查看父级科目列的列标题 | 列标题清晰，如 `Extracted Parent`，用户可理解列含义 |
| TC-003 | 单级父级显示父级名 | 源文档中 "Depreciation" 科目位于 "Computer Equipment" 之下（单级父级） | 查看该行父级列 | 父级列显示 `Computer Equipment` |
| TC-004 | 多级父层显示完整链以 > 分隔 | 源文档中 "Service Revenue" 的层级为 Revenue → Operating Revenue → Service Revenue | 查看 "Service Revenue" 行的父级列 | 父级列显示完整链 `Revenue > Operating Revenue > Service Revenue`，从最顶级到直接父级 |
| TC-005 | 顶级科目父级列留空 | 源文档中某科目为顶级科目，无父级 | 查看该行父级列 | 父级列单元格留空 |
| TC-006 | 长父级链截断且悬停展示完整层级 | 某科目父级链长度超出列宽 | 查看该行父级列 | 父级列文本被截断显示 |
| | | | 将鼠标悬停在被截断的父级列单元格上 | 悬停展示完整父级层级 |


