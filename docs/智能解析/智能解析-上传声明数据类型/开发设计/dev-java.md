# 手动上传时声明 Actuals / Proforma · Java 开发设计

> 关联文档：
> - 上游（第四阶段 · 功能设计）：[design-doc](../设计/design-doc.md) —— D1 ~ D10 全部结论在那里，本文不重复论证
> - 需求：[requirement-doc](../需求/requirement-doc.md)（R1 / R6 / R8 / R11 与本文直接相关）
> - 参考代码：[code-examples](./code-examples.md) 的「Java」一节（DTO、枚举、Service 片段、单测骨架）
> - 同目录的 Python / 前端开发设计各自成文，本文只写 Java

本文只写 **Java 怎么改**：类清单、插入点、校验与报错、事务时序、兼容与单测。按 `docs/CLAUDE.md`，
完整类与函数放 [code-examples](./code-examples.md)，本文只引用签名与插入点。
**Java 侧没有 DDL**：列注释更新在 Python 迁移树 V030（设计 §3.1；归属依据见
`CIOaas-api/deploy/upgrade_doc/sprint114/README.md:6-11`：`ai_` 前缀表的 schema 变更统一归 Python 迁移树）。

下文路径简写：`extract/` = `CIOaas-api/gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/ai/financial/extract/`。
行号基于 `CIOaas-api` 分支 `sprint121`、提交 `ccf3430f6`（2026-10-09）。

---

## 1. 代码基线核对

设计文档的前提逐条对过真实代码，结论如下（出入集中在 §11）：

| 设计前提 | 代码现状 | 结论 |
|---|---|---|
| commitUpload 请求体是 `{companyId, fileIds}` | `controller/AiFinancialExtractionController.java:51-55` 收 `AiFinancialStagedFilesRequest`；该类同时被 `/files/batchDeleteByIds`（`:62-67`）使用 | ✅ 所以**新建**请求类，不改共享类 |
| commitUpload 建任务 + 建登记行 + 发 SQS | `service/AiFinancialExtractionServiceImpl.java:388-451`：去重 fileIds（`:392-402`）→ 建 task（`:406`）→ 逐个 HEAD + `new AiFileRegistry` + `save`（`:411-436`）→ 任务置 `UPLOAD_COMPLETE` + 发 SQS（`:442-444`） | ✅ |
| 带 taskId 的 getUploadUrl 建 PENDING 登记行 | `ServiceImpl:109-110` 以 `taskId` 是否为空区分；`:155-166` 建 PENDING 行，`:171-173` `saveAll` | ✅ |
| uploadComplete 请求不变 | `ServiceImpl:311-380`；本批 = `kept` 中 `PENDING → UPLOADED` 的行（`:357-364`） | ✅ |
| replaceFile 请求不变 | `ServiceImpl:251-293`；旧行在 `:277` 软删，新行在 `:281-287` 置 `UPLOADED` | ✅ 需在软删前取旧行的类型 |
| SQS 在提交之后发 | `infrastructure/messaging/AiFinancialExtractionSqsProcessor.java:62-73` + `:125-137`：在事务内调用时挂到 `afterCommit` | ✅ Python 读到的一定是已提交的 `business_type` |
| 财务抽取行的 `business_type` 全部为空、Java 从未写过 | `grep setBusinessType / getBusinessType` 在 `web/ai/` 下 0 处 | ✅ |
| `business_type` 无 CHECK 约束、长度够 | 实体 `domain/AiFileRegistry.java:102` `length = 40`；Python 迁移只有 COMMENT 没有 CHECK | ✅ `EXTRACT_FI_PROFORMA` 19 个字符 |
| Actuals 当月护栏 | `service/AiFinancialExtractionConflictServiceImpl.java:665-668` + `:1678`（`isClosedActualsMonth`） | ✅ 不动 |
| 校验失败返回 400 | **不成立**，见 §5 | ⚠️ |

**模块结构现状**：本模块是平铺包（`controller/ service/ domain/ repository/ util/ vo/`），没有
`interfaces/application/domain` 四层；6 个 Service 方法签名**全部直接收 Request**，枚举放在 `util/`
且不带 `Enum` 后缀（`util/AiFinancialExtractionTaskStatus.java`）。本需求**沿用模块现状**，新类按现有位置
与命名放，不在本需求里重构分层。这一点偏离 `standards/architecture.md` §1 与 `coding.md` §2
（「Service 不接触 Request」），留到开发设计审核时确认（§10 J-R1）。

---

## 2. 改动清单

| # | 类 | 动作 | 要点 |
|---|---|---|---|
| 1 | `extract/util/AiFinancialFileDataType.java` | **新增** | 枚举 `ACTUALS` / `PROFORMA`，携带对应的 `business_type`；**取值映射只在这里定义**（设计 D3、§6）。§3 |
| 2 | `extract/vo/request/AiFinancialCommitUploadRequest.java` | **新增** | `companyId` + `files`。命名对齐同模块的 `AiFinancialCommitUploadResponse` |
| 3 | `extract/vo/request/AiFinancialCommitUploadFileItem.java` | **新增** | `fileId` + `dataType`（必填）。命名对齐同模块的 `AiFinancialPresignUploadFileItem` |
| 4 | `extract/vo/request/AiFinancialPresignUploadFileItem.java` | 改 | 加可选 `dataType` |
| 5 | `extract/controller/AiFinancialExtractionController.java` | 改 | `commitUpload` 入参换成新请求类（`:53`）；`commitUpload` / `uploadComplete` / `replace` 三处 javadoc 补一句类型规则 |
| 6 | `extract/service/AiFinancialExtractionService.java` | 改 | `commitUpload` 签名（`:37`）与 javadoc（`:30-36`） |
| 7 | `extract/service/AiFinancialExtractionServiceImpl.java` | 改 | 四个入口 + 一个私有转换方法，§4 |
| 8 | `extract/domain/AiFileRegistry.java` | 改（只改注释） | §7 |
| 9 | `extract/vo/request/AiFinancialStagedFilesRequest.java` | 字段不动 | 类注释 `:11-15` 的「Shared by commitUpload and batchDeleteByIds」改完后失效，建议只删掉 commitUpload 这半句 |
| 10 | 单测两个新文件 | **新增** | §9 |

**不改**：SQS 消息（`contract/AiFinancialExtractionSqsMessage.java`）、verify / complete
（`AiFinancialExtractionConflictServiceImpl`）、`AiFinancialStagedFilesRequest` 的字段、Repository、
`/files/batchDeleteByIds`。

---

## 3. 取值映射：`AiFinancialFileDataType`

| 枚举常量（= 接口值 `dataType`） | `businessType()`（= 登记行 `business_type`） |
|---|---|
| `ACTUALS` | `EXTRACT_FI_ACTUALS` |
| `PROFORMA` | `EXTRACT_FI_PROFORMA` |

只提供两个静态方法，形状照抄同目录 `AiFinancialExtractionTaskStatus.fromCode`：

- `Optional<AiFinancialFileDataType> fromCode(String raw)`：接口值转枚举，空或不认识返回 empty（区分大小写，
  与请求上的 `@Pattern` 一致）。
- `boolean isDeclaredBusinessType(String businessType)`：登记行上的值是不是两个声明类型之一；历史行的 NULL 返回 false。

**为什么放 `util/` 而不是 `gstdev-cioaas-common`**：只有本模块用，不跨业务域（`architecture.md` §1.1 只要求
**跨域**共享的枚举下沉 common）。Python 侧读取时按同一张表反向转换（设计 §3.3），两个字面值是跨语言契约，
用单测钉住（§9 T1）。

Service 里加一个私有静态方法 `toBusinessType(String dataType)`：调 `fromCode`，empty 时抛
`BadRequestException`，否则返回 `businessType()`。commitUpload 与 getUploadUrl 共用它，异常留在 Service
层、枚举里不抛异常。

---

## 4. 接口改动（`AiFinancialExtractionServiceImpl`）

### 4.1 `POST /tasks/commitUpload`

**请求**：`{companyId, files: [{fileId, dataType}]}`，字段与校验注解见 §5.1。响应不变。

**Service 改动**（`:388-451`，主流程顺序不变，只换掉两处）：

1. **去重段**（`:391-402`）：`Set<String> fileIds` 换成 `LinkedHashMap<String, String> businessTypeByFileId`
   （fileId → business_type，保持请求顺序）。逐项 `toBusinessType(item.getDataType())` 后 `putIfAbsent`：
   - 同一 fileId 重复出现、类型相同：去重（与原先 `LinkedHashSet` 去重的行为一致）。
   - 同一 fileId 重复出现、**类型不同**：抛 `BadRequestException("Conflicting dataType for file: " + fileId)`
     （需求 R6：一个文件只能是一种类型。原实现是静默去重，换成映射后不挡的话就成了「后一个覆盖前一个」）。
   - 原 `"fileIds is required"` 的空列表兜底保留，文案改成 `"files is required"`（`@NotEmpty` 已在入口拦截，
     这里只防直接调用 Service）。
2. **建登记行**（`:425-434`）：在 `row.setDeleted(Boolean.FALSE)` 之后加
   `row.setBusinessType(businessTypeByFileId.get(fileId))`。循环改为遍历 `businessTypeByFileId` 的 entry。

所有类型校验都在 `resolveOrCreateTask`（`:406`）**之前**完成，失败时不会留下空任务。HEAD 校验、`missing` /
`committed` 两个清单、任务状态推进、SQS 都不动。

### 4.2 `POST /tasks/getUploadUrl`

**请求**：`fileList[]` 每项加可选 `dataType`（§5.1）。

**Service 改动**：只改增量分支 `if (!deferred)`（`:155-166`），在建行时加
`row.setBusinessType(StringUtils.isBlank(entry.getDataType()) ? null : toBusinessType(entry.getDataType()))`。

- **带 taskId（映射页）**：传了就写入；**没传也放行**——替换文件也走这条路径（先 getUploadUrl 拿新 fileId，
  再调 `file/replace`），而 Java 在签发链接时分不清是"上传新文件"还是"替换"，所以必填校验只能放到 uploadComplete（§4.3）。
- **不带 taskId（首次上传弹窗）**：这条分支不建登记行，`dataType` 自然被忽略。

### 4.3 `POST /tasks/{taskId}/uploadComplete`

**请求**不变。**Service 改动**：在「校验保留列表」循环（`:338-345`）里，归属校验之后加一条：

> 行状态为 `PENDING` 且 `!AiFinancialFileDataType.isDeclaredBusinessType(row.getBusinessType())` →
> 抛 `BadRequestException("Table type (Actuals / Proforma) is required for file: " + 文件名)`
> （文件名取 `row.getFileName()`，为空时退回 fileId）。

两个关键点：

- **只校验 `PENDING` 行**：`fileIds` 里允许出现已解析的历史文件（`:301-302`、`:365` 的注释与分支），上线前建的任务里
  这些行的 `business_type` 是 NULL（需求 R11 不补写），全量校验会把老任务的"上传新文件"整个拦死。
- **放在改状态的循环（`:356-371`）之前**：先校验后改写，失败时没有任何行被改。即便在中途抛出，整个事务也会回滚，
  挂在 afterCommit 的 SQS 不会发出。

### 4.4 `POST /tasks/{taskId}/file/replace`

**请求**不变。**Service 改动**：

1. `:277` 的软删要先拿到旧行：把 `findByFileIdAndDeletedFalse(oldId).ifPresent(this::softDeleteExtractionFile)`
   拆成"先查出 `Optional` → 再 `ifPresent` 软删"，并记下 `oldRow.map(AiFileRegistry::getBusinessType).orElse(null)`。
   **必须在软删之前或同一次查询里取**，软删之后 `findByFileIdAndDeletedFalse` 就查不到了。
2. `:286` `newRow.setStatus("UPLOADED")` 旁边加 `newRow.setBusinessType(inherited)`：**无条件覆盖**，即使前端调
   getUploadUrl 时误带了 `dataType` 也以旧文件为准（需求 R8：替换文件继承类型）。
3. `inherited == null`（旧文件是上线前上传的）：照设计原样复制 NULL，打一条 `log.warn`（含 taskId / oldFileId /
   newFileId）。这个文件随后会被 Python 判为 `FILE_FAILED`（设计 §5.1、D9），见 §10 J-R2。

---

## 5. 校验与报错

### 5.1 请求类上的注解（第一道，入口校验）

| 字段 | 注解 | 说明 |
|---|---|---|
| `AiFinancialCommitUploadRequest.companyId` | `@NotBlank` | 同旧类 |
| `AiFinancialCommitUploadRequest.files` | `@NotEmpty(message = "files is required")` `@Size(max = 100)`，元素 `@NotNull @Valid` | 上限沿用旧 `fileIds` 的 100 |
| `AiFinancialCommitUploadFileItem.fileId` | `@NotBlank @Size(max = 36)` | 同旧 `fileIds` 元素 |
| `AiFinancialCommitUploadFileItem.dataType` | `@NotBlank(message = "dataType is required")` + `@Pattern(regexp = "ACTUALS\|PROFORMA", message = "dataType must be ACTUALS or PROFORMA")` | 同模块先例：`vo/request/AiFinancialConflictResolveItem.java:23-27` 的 `action` 字段 |
| `AiFinancialPresignUploadFileItem.dataType` | 只加 `@Pattern`（同上），不加 `@NotBlank` | `@Pattern` 对 null 不生效 → 可选；传了就必须合法 |

**`dataType` 用 `String` + `@Pattern`，不直接声明成枚举类型**：声明成枚举后，非法值会在 Jackson 反序列化阶段失败
（`HttpMessageNotReadableException`），被 `GlobalExceptionHandler` 的 `Throwable` 兜底分支
（`gstdev-cioaas-common/.../exception/GlobalExceptionHandler.java:131-141`）当成 500 返回"An unexpected error
occurred"，不满足"可读提示"。

### 5.2 返回码（以 `GlobalExceptionHandler` 现状为准）

| 场景 | 抛出 | 实际返回 |
|---|---|---|
| commitUpload 缺 `files`、缺 `dataType`、`dataType` 非法；getUploadUrl 的 `dataType` 非法 | `@Valid` → `MethodArgumentNotValidException` | **HTTP 422**，body `{message: "Verification fails", errors: [{field: "files[0].dataType", message: "dataType must be ACTUALS or PROFORMA"}]}`（`GlobalExceptionHandler.java:45-68`） |
| **旧前端**的 `{companyId, fileIds}` | `fileIds` 是未知字段，被忽略（`web/config/JacksonConfiguration.java:24`），`files` 为 null → `@NotEmpty` | **HTTP 422**，`field: "files"` |
| commitUpload 同一 fileId 声明两种类型 | `BadRequestException` | **HTTP 200** + `{success: false, message}`（`GlobalExceptionHandler.java:158-162`） |
| uploadComplete 本批有文件未声明类型 | `BadRequestException` | HTTP 200 + `success: false` |
| Service 被直接调用、`dataType` 非法（单测路径） | `BadRequestException`（`toBusinessType`） | — |

⚠️ 设计文档 §4 写的"返回 400"在这个工程里不存在：`BadRequestException` 自带 `status = 400`
（`BadRequestException.java:16`），但全局处理器不读这个字段，统一返回 HTTP 200 + `success: false`。
本文**不新增**异常处理分支，沿用现状（§11 #1）。

### 5.3 报错文案（英文，与模块现有文案一致）

| 位置 | 文案 |
|---|---|
| `@NotEmpty` files | `files is required` |
| `@NotBlank` dataType | `dataType is required` |
| `@Pattern` dataType | `dataType must be ACTUALS or PROFORMA` |
| `toBusinessType` | `dataType must be ACTUALS or PROFORMA: {raw}` |
| commitUpload 类型冲突 | `Conflicting dataType for file: {fileId}` |
| uploadComplete 未声明 | `Table type (Actuals / Proforma) is required for file: {fileName}` |

前端提交前已经拦截（Next 不可用），这几条都是兜底，前端不需要按文案做判断。

---

## 6. 事务与 SQS 时序（不改）

三个写入口都已经是 `@Transactional(REQUIRED)`（`ServiceImpl:103`、`:250`、`:389`），`business_type` 和登记行的
其它字段在**同一次 save** 里写入。SQS 通过 `runAfterCommitOrNow` 挂在 afterCommit（`SqsProcessor:125-137`），
所以 Python `init_task` 收到消息时，登记行的类型一定已经提交——这正是设计 D4（"从数据库读类型、消息不变"）
能成立的前提。**不要**把 `setBusinessType` 挪到发 SQS 之后的单独事务里，也不要为此改 SQS 契约。

uploadComplete 的校验失败发生在事务内，回滚后 afterCommit 不触发，不会出现"已发消息但登记行没类型"的状态。

---

## 7. 实体注释（`domain/AiFileRegistry.java`）

只改注释，不改字段与映射：

| 位置 | 改法 |
|---|---|
| `business_type` 字段 javadoc（`:95-101`） | 按用途分两组列出：`purpose='rag'` 行沿用 APP_USER / ADMIN_USER / APP_COMPANY / ADMIN_COMPANY / ADMIN_ORGANIZATION / KNOWLEDGE_BASE / PLAYBOOK / PARSING_MEMORY / SESSION_UPLOAD / ERL_ATTACHMENT；`purpose='financial_extract'` 行（sprint121 新增，Java 写）为 `EXTRACT_FI_ACTUALS` / `EXTRACT_FI_PROFORMA`，表示用户上传时声明的类型，历史行为 NULL，取值映射见 `AiFinancialFileDataType`。注意补上 **`ADMIN_ORGANIZATION`**：DB 注释（Python V023）早已有这个值，实体注释漏了 |
| 类 javadoc「财务抽取文件」一条（`:19-20`） | 补"`business_type` 写入用户声明的 `EXTRACT_FI_*`" |
| 类 javadoc `:29` "本财务模块仅写 OCR 相关列，6 个通用化关联列由各自业务写入" 与字段组注释 `:88-90` "本财务模块不写这些列" | 改成"除 `business_type` 外不写"，否则注释与代码矛盾 |

DB 列注释由 Python 迁移 V030 更新，Java 不建 SQL。

---

## 8. 兼容与发布

| 组合 | 结果 |
|---|---|
| 新 Java + 旧前端 | commitUpload 全部 422（§5.2），**首次上传整条链路不可用** |
| 旧 Java + 新前端 | 旧 `AiFinancialStagedFilesRequest.fileIds` 为 `@NotEmpty`，新前端不再传它 → 同样 422 |
| 新 Java + 旧 Python | 旧 Python 忽略 `business_type`，继续按旧逻辑推断，可以平滑过渡（设计 §8） |

所以 **Java 与前端必须同批发布，回滚也必须同批回滚**；Python 在两者之后发布。已写入的 `EXTRACT_FI_*` 对回滚后的旧
Java（从不读这一列）和旧 Python（rag 查询只匹配原来那几个取值）都无副作用，回滚不需要清数据。
getUploadUrl 新增的 `dataType` 是可选字段，旧 Java 收到会忽略，对发布顺序没有额外要求。

---

## 9. 单元测试

风格照 `src/test/.../ai/financial/extract/service/AiFinancialExtractionPngPreviewTest.java`：
`@ExtendWith(MockitoExtension.class)` + `@InjectMocks AiFinancialExtractionServiceImpl`，全 Mock、不起 Spring。
需要 Mock 的依赖比预览测试多三个：`AbstractStorage storage`、`S3Properties s3Properties`、
`AiFinancialExtractionSqsProcessor sqsProcessor`。`SecurityUtils` 不需要静态 Mock：没有登录上下文时
`getUserId()` / `getPrincipal()` 都返回 null（`SecurityUtils.java:46-81`），`resolveOrCreateTask` 只会打一条 WARN。
用 `ArgumentCaptor<AiFileRegistry>`（`save`）或 `ArgumentCaptor<List<AiFileRegistry>>`（`saveAll`）断言写入的类型。

**新文件 1**：`.../extract/service/AiFinancialExtractionDeclaredTypeTest.java`

| # | 用例 | 断言 |
|---|---|---|
| T1 | 映射字面值 | `ACTUALS.businessType() == "EXTRACT_FI_ACTUALS"`、`PROFORMA` 同理；`fromCode("actuals")` 为空（区分大小写）；`isDeclaredBusinessType(null)` / `("KNOWLEDGE_BASE")` 为 false。这两个字面值是给 Python 的契约，用例钉住 |
| T2 | commitUpload 按文件写类型 | 两个文件分别 ACTUALS / PROFORMA → 两次 `save` 捕获到的 `businessType` 依次为 `EXTRACT_FI_ACTUALS` / `EXTRACT_FI_PROFORMA`；`sendExtractionStartMessage` 收到两个 fileId |
| T3 | commitUpload `dataType` 非法或为 null | 抛 `BadRequestException`；`taskRepository.save`、`extractionFileRepository.save`、`sqsProcessor` 都 `never()`（类型校验在建任务之前） |
| T4 | commitUpload 同一 fileId 两种类型 | 抛 `BadRequestException`，消息含 fileId；同样不建任务 |
| T5 | commitUpload 同一 fileId 同一类型重复 | 只登记一次 |
| T6 | getUploadUrl 带 taskId + `dataType=PROFORMA` | `saveAll` 捕获的行 `businessType == EXTRACT_FI_PROFORMA` |
| T7 | getUploadUrl 带 taskId、不带 `dataType`（替换路径） | 正常返回，行的 `businessType` 为 null |
| T8 | getUploadUrl 不带 taskId | `extractionFileRepository.saveAll` `never()`（`dataType` 被忽略） |
| T9 | uploadComplete 本批 PENDING 行没有类型 | 抛 `BadRequestException`，消息含文件名；行状态仍为 PENDING、`sqsProcessor` `never()` |
| T10 | uploadComplete 的 `fileIds` 里混入历史 `REVIEW_READY` 行（NULL 类型）+ 本批已声明的 PENDING 行 | 不抛异常；只有 PENDING 行转 UPLOADED 并送解析 |
| T11 | replaceFile 继承类型 | 旧行 `EXTRACT_FI_ACTUALS`，新 PENDING 行带 `EXTRACT_FI_PROFORMA`（模拟前端误传）→ 新行保存时为 `EXTRACT_FI_ACTUALS`；旧行 `deleted == true` |
| T12 | replaceFile 旧行无类型 | 新行 `businessType` 为 null，不抛异常（设计原样复制） |

Mockito 严格模式下，拒绝类用例（T3 / T4 / T9）只 stub 会被走到的调用，否则会报 `UnnecessaryStubbingException`。

**新文件 2**：`.../extract/vo/request/AiFinancialCommitUploadRequestValidationTest.java`

照 `src/test/.../thirdParty/application/dto/ThirdPartyConnectionHostUrlValidationTest.java` 的写法，用
`Validation.buildDefaultValidatorFactory().getValidator()` 直接校验请求对象（Service 单测绕过了 `@Valid`，入口这一层要单独测）：

| # | 用例 | 断言 |
|---|---|---|
| V1 | 合法 body | 0 条违规 |
| V2 | 某项缺 `dataType` / 值为 `"Actuals"` / `"FORECAST"` | 违规路径为 `files[0].dataType` |
| V3 | 旧 body 形状（只有 `companyId`，`files` 为 null） | 违规路径为 `files`——这条锁住"旧前端会被拒"（§8） |
| V4 | `AiFinancialPresignUploadFileItem.dataType` 为 null 通过、`"X"` 不通过 | 可选但合法 |

建议命令（按根 `CLAUDE.md`「测试运行策略」，等用户下指令再跑）：
`mvn -pl gstdev-cioaas-web test -Dtest=AiFinancialExtractionDeclaredTypeTest+AiFinancialCommitUploadRequestValidationTest`；
回归加跑同包现有的 `AiFinancialExtractionPngPreviewTest`、`AiFinancialExtractionClosedMonthTest`。

---

## 10. 风险与待确认

| # | 风险 / 问题 | 处置 |
|---|---|---|
| J-R1 | 本模块的 Service 直接收 Request，偏离「Request → DTO → Service」规范（§1） | 本需求沿用模块现状。若审核要求补 DTO，代价是只为 commitUpload 引入 `application/dto` + Converter，模块内会出现两种写法；更合理的是另立重构任务整体改 |
| J-R2 | 上线前建的任务，在映射页**替换**旧文件 → 新文件继承 NULL → Python 判 `FILE_FAILED` | 符合设计 D9 / 需求 R11（历史不补写），但用户只会看到文件失败、不知道原因。可选改进：Java 在替换时发现旧文件没有类型就直接拒绝，给出可读提示（例如"请改用 Upload New Document"）——属于产品决策，不在 D1~D10 内，**本期按设计原样复制** |
| J-R3 | 映射页 Upload New Document 的类型**只能在 getUploadUrl 时提交**，之后没有接口能改 | 设计 §10 Q2（类型选择的交互样式）尚未定稿。若设计稿选择"先上传、后选类型"，前端必须等用户选完再调 getUploadUrl；否则 Java 要在 uploadComplete 上加字段。请前端按此约束实现 |
| J-R4 | "当前月"的口径两端不同：Python 用处理时刻的 UTC（D6），Java 护栏用 `LocalDate.now()` 的 JVM 默认时区（`ConflictServiceImpl:665`） | JVM 跑在 UTC 时两边一致；不是 UTC 时，月初几小时内两道防线的判断可能差一个月。D6 已定 Java 不参与，**本期不改**，上线前确认生产 JVM 时区即可 |
| J-R5 | complete 仍然信任前端回传的每行 `sourceDataType`（`ConflictServiceImpl:982`），不和文件声明交叉核对 | 设计 §6 明确"complete 写入逻辑不变"；映射页已不能改派类型（R7），数据来自 Python 按声明类型写的单元格。不加校验 |
| J-R6 | **顺带发现，与本需求无关**：commitUpload 的 S3 落盘校验（`ServiceImpl:418-424`）只 `catch` 异常、不看返回值，而 `headObject` 遇到 404 返回 `S3ObjectHead.missing()`、不抛异常（`storage/storage/AwsSThreeStorage.java:186-195`）。S3 上不存在的文件因此仍会被登记并送去解析，`missingFileIds` 实际只收得到"不在本公司 staging 目录"的文件 | 本期不改，由用户决定是否另立任务。单测 T2 里把 `headObject` stub 成 `exists = true`，这样以后修了这处，用例依然成立 |

---

## 11. 与上游设计的出入（已于 2026-10-10 同步进设计文档 §4 / §6）

| # | 设计文档原文 | 实际 | 建议 |
|---|---|---|---|
| 1 | §4「返回 400 并给出可读的提示」 | 本工程没有返回 HTTP 400 的路径：入口字段校验 → **422**（带字段级 `errors[]`），业务校验 → **HTTP 200 + `success: false`**（§5.2） | 设计 §4 改成"字段校验失败 422；业务校验失败 `success: false` + 提示"，前端两种都要当失败处理 |
| 2 | §3.1「Java 实体注释同步更新」 | 实体注释除了新增两个值，还漏了 `ADMIN_ORGANIZATION`；类 javadoc 与字段组注释写着"本模块不写这些列"，改完后与代码矛盾 | 已列入 §7 |
| 3 | §6「必填校验：手动录入公司的文件必须有声明类型」 | Java 里没有"手动录入公司 / QBO 公司"的判断，校验对所有公司一视同仁 | 与 D10 一致（QBO 本来看不到入口），文档措辞可去掉"手动录入公司"这个限定 |
| 4 | §4 uploadComplete「校验本次每个文件都已声明类型」 | "本次"必须落实为 **`kept` 中状态为 PENDING 的行**；按 `fileIds` 全量校验会拦住老任务 | 已在 §4.3 落实 |
