# 手动上传时声明 Actuals / Proforma · 开发设计（总览）

> 关联文档：
> - 上游（第四阶段 · 功能设计）：[design-doc](../设计/design-doc.md)——D1~D10 已拍板，本阶段照做、不再论证
> - 需求：[requirement-doc](../需求/requirement-doc.md)
> - 分端开发设计：[dev-python](./dev-python.md) · [dev-java](./dev-java.md) · [dev-frontend](./dev-frontend.md)
> - 参考代码：[code-examples](./code-examples.md)（V030、Java 类与片段、Python 新函数、前端片段、三端单测骨架）

本文是第⑤阶段的总览，只写跨端的部分：改动一览、跨端契约、实施与发布顺序、联调测试、风险汇总。各端**怎么改**见分端文档。按 `docs/CLAUDE.md`，三端实现细节不混写在一个文件里，完整代码统一放 [code-examples](./code-examples.md)。

代码基线（三端开发设计均据此核对，行号以此为准）：

| 仓库 | 分支 | 提交 |
|---|---|---|
| CIOaas-python | sprint121 | `70ca1e6a` |
| CIOaas-api | sprint121 | `ccf3430f6` |
| CIOaas-web | sprint121 | `eea52f3c` |

---

## 1. 改动一览

| 端 | 主要改动 | 详见 |
|---|---|---|
| **Python** | init_task 读登记行 `business_type` 得到每个文件的声明类型，未声明的文件直接判 FILE_FAILED；refine 原 Stage 2.6（按月份校正类型）换成"表类型 = 声明类型"，原 Stage 2.8（当月拆成 Proforma 表）删除，新增 Stage 2.65"Actuals 文件剔除当前月及以后的单元格"；停止写 `parent_table_id`；迁移 V030（只改列注释）；删除两个旧测试文件、新增两个 | [dev-python](./dev-python.md) §2~§10 |
| **Java** | 新增枚举 `AiFinancialFileDataType`（取值映射唯一定义处）和 commitUpload 的新请求类；commitUpload / getUploadUrl（带 taskId）写 `business_type`，uploadComplete 校验新文件已声明，replaceFile 继承旧文件类型；实体只改注释；无 DDL | [dev-java](./dev-java.md) §2~§9 |
| **前端** | 上传弹窗加 TABLE TYPE 列、批量设置、说明横幅、Next 启用条件，commitUpload 按文件带类型；映射页去掉 Actual / Forecast 改派，Upload New Document 先选类型；新增 `services/api/ai/request.ts`、`dto.ts`；4 个新单测文件 | [dev-frontend](./dev-frontend.md) §2~§7 |

## 2. 跨端契约

### 2.1 类型取值（D3）
| 位置 | 取值 | 谁写 / 谁读 |
|---|---|---|
| 前端 → Java 请求（commitUpload `files[].dataType`、getUploadUrl `fileList[].dataType`） | `ACTUALS` / `PROFORMA` | 前端写，Java 读 |
| `ai_file_registry.business_type`（`purpose='financial_extract'` 的行） | `EXTRACT_FI_ACTUALS` / `EXTRACT_FI_PROFORMA`；历史行 `NULL` | Java 写，Python 读 |
| `ai_financial_extraction_mapping_data.source_data_type`（单元格） | `ACTUALS` / `PROFORMA`（等于文件声明类型） | Python 写，拉取接口与 Java complete 读 |

两个 `EXTRACT_FI_*` 字面值是 Java 与 Python 的跨语言契约：Java 在 `AiFinancialFileDataType`、Python 在 `init_task_node._DATA_TYPE_BY_BUSINESS_TYPE` 各定义一次，两边单测都把字面值钉住，改动必须两端同步。

### 2.2 接口与返回码
| 接口 | 变化 | 失败时 |
|---|---|---|
| `POST /tasks/commitUpload` | 请求体 `{companyId, files:[{fileId, dataType}]}`（替换 `fileIds`） | 字段不合法：HTTP 422；同一文件两种类型：HTTP 200 + `success:false` |
| `POST /tasks/getUploadUrl` | `fileList[]` 可选 `dataType`，只在带 taskId（映射页上传新文件）时写入登记行 | 取值不合法：HTTP 422 |
| `POST /tasks/{taskId}/uploadComplete` | 请求不变；校验本批 PENDING 文件都已声明 | HTTP 200 + `success:false` |
| `POST /tasks/{taskId}/file/replace` | 请求不变；新文件继承旧文件 `business_type` | — |
| SQS 抽取消息、Python 拉取接口、verify / complete | 不变 | — |

### 2.3 文件状态
新增一条状态迁移：**UPLOADED → FILE_FAILED**（未声明类型，在 init_task 判定，不经过 PROCESSING）。错误信息为 "Table type (Actuals / Proforma) was not declared for this file; please re-upload it"。其余状态流转不变。

## 3. 实施与发布顺序

### 3.1 开发
- 三端在各自仓库的 `sprint121` 上开发，按各子项目 `standards/git.md` 提交，提交消息用英文。
- 三端可以**并行开发**，没有先后依赖：契约（§2）已经定死，各端单测都不依赖其他端。
- 联调需要三端都完成，并在测试库执行 V030。

### 3.2 发布（与设计 §8 一致）
| 顺序 | 内容 | 原因 |
|---|---|---|
| 任意时间 | V030（人工 psql 执行，只改注释） | 不影响任何版本的代码 |
| 1 | **Java 与前端同批** | commitUpload 请求体两端必须同时切换，单独发任一端都会让上传失败（HTTP 422） |
| 2 | Python | 先发 Python 会让新任务全部判失败（登记行还没有类型）；Java 先发时，旧 Python 忽略这一列、继续按旧逻辑推断，可以平滑过渡 |

**回滚**：Java 与前端一起回滚；Python 可单独回滚（旧 Python 不读 `business_type`，已写入的值不影响它），不需要清数据。不加环境变量开关。

## 4. 测试计划

### 4.1 单元测试（各端开发时编写，"跑测试"指令下统一执行）
| 端 | 新增 | 改写 / 删除 | 回归 |
|---|---|---|---|
| Python | `test_declared_data_type.py`（12 例）、`test_init_task_declared_type.py`（4 例） | 删 `test_split_proforma_tail.py`、`test_finalize_data_type.py`；改 `test_renumber_column_positions.py` 的 state | 去重、补行、RAG override、训练信号、拉取 / 回放契约，见 [dev-python](./dev-python.md) §10 |
| Java | `AiFinancialExtractionDeclaredTypeTest`、`AiFinancialCommitUploadRequestValidationTest` | — | `AiFinancialExtractionClosedMonthTest`（Actuals 护栏），见 [dev-java](./dev-java.md) §9 |
| 前端 | `ImportStatementsModal.test.tsx`、`DataMappingPanel.test.tsx`、`FileSelector.test.tsx`、`useOCRData.test.tsx` | — | `src/pages/financial` 现有套件，见 [dev-frontend](./dev-frontend.md) §7 |

### 4.2 联调（三端完成、V030 执行后）
按惯例先审核再联调，联调只挑 2~3 个有代表性的文件，不跑全量语料：

| # | 场景 | 预期 |
|---|---|---|
| 1 | 一个同时含历史月和当前月 / 未来月的 Excel，声明为 **Actuals** | 只抽出过去月份，都在 Actuals 标签页；当前月及以后没有数据；不出现 "current month data may be incomplete" 横幅 |
| 2 | 同一个文件声明为 **Proforma** | 所有月份都抽出，都在 Proforma 标签页 |
| 3 | 一批里同时有 Actuals 和 Proforma 文件 | 各自按声明类型落标签页；提交后 Actuals 写入财务数据、Proforma 写入预测 |
| 4 | 映射页 Upload New Document，选类型后上传 | 新文件按所选类型抽取 |
| 5 | 映射页 Replace Document | 新文件沿用被替换文件的类型 |
| 6 | 指派 LG 指标 | 下拉里没有 Actual / Forecast；指派后行留在原标签页 |
| 7 | 去重回归：同一个含重复月份的文件新旧版本各跑一次 | 去重结果与改动前一致，或差异能用 [dev-python](./dev-python.md) §5 的输入变化解释 |

## 5. 风险汇总

| # | 风险 | 处置 | 出处 |
|---|---|---|---|
| X1 | "当前月"两端口径：Python 用处理时刻 UTC；Java 的 Actuals 护栏用 JVM 默认时区 | 需求已定以 UTC 为准；**上线前确认生产 JVM 时区为 UTC** | dev-java J-R4 / dev-python R5 |
| X2 | 新状态迁移 UPLOADED → FILE_FAILED | 联调确认 Java 和前端按终态展示 | dev-python R1 |
| X3 | Java 与前端必须同批发布 | 发布单上写明；回滚也一起回滚 | §3.2 |
| X4 | 去重、补行、映射判定的输入变化 | 联调场景 7 对比 | dev-python §5 |
| X5 | 上线前建的任务替换文件会判失败 | 按 D9 接受，错误文案提示重新上传 | dev-java J-R2 / dev-python R7 |
| X6 | 上线前已在映射页的任务，类型来自旧推断，上线后不能再改 | R7 的直接后果，需要改类型只能重新上传；请产品知悉 | dev-frontend 风险 3 |
| X7 | 设计稿未定的 Q1~Q4（占位文案、映射页选类型样式、弹窗宽度、Clear All 是否常驻） | 前端先按临时方案实现，集中在常量和样式里，定稿后小改 | design-doc §10 |
| X8 | 规范偏离（Java Service 直接收 Request、前端文案未走 i18n、`services/api/ai` 仍以内联类型为主） | 都是模块存量写法，本期沿用；留给第⑥阶段审核决定 | dev-java J-R1 / dev-frontend 风险 7 |

**顺带发现、与本需求无关**：commitUpload 的 S3 落盘校验不看返回值，S3 上不存在的文件也会被登记并送去解析（dev-java J-R6）。本期不改，是否另立任务由你决定。

## 6. 本期不做
- QBO 公司的入口和类型规则（下个 sprint）。
- 抽取完成后提示"哪些月份没有作为 Actuals 导入"。
- 修改提示词或提示词版本号（模型给的类型会被声明类型覆盖）。
- 历史任务、历史文件补写类型；新旧逻辑并存的开关。

## 7. 下一步
第⑥阶段**开发设计审核**：从架构合理性、安全、性能、需求覆盖度审查本目录四份文档，重点看 X1、X8 和 Q1~Q4。审核通过后按 §3 开发。
