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
2026-10-10 按第⑥阶段开发设计审核修订，改动处标「（审核 X-n）」。

---

## 1. 代码基线核对

设计文档的前提逐条对过真实代码，结论如下（出入集中在 §11）：

| 设计前提 | 代码现状 | 结论 |
|---|---|---|
| commitUpload 请求体是 `{companyId, fileIds}` | `controller/AiFinancialExtractionController.java:51-55` 收 `AiFinancialStagedFilesRequest`；该类同时被 `/files/batchDeleteByIds`（`:62-67`）使用 | ✅ 所以**新建**请求类，不改共享类 |
| commitUpload 建任务 + 建登记行 + 发 SQS | `service/AiFinancialExtractionServiceImpl.java:388-451`：去重 fileIds（`:392-402`）→ 建 task（`:406`）→ 逐个 HEAD + `new AiFileRegistry` + `save`（`:411-436`）→ 任务置 `UPLOAD_COMPLETE` + 发 SQS（`:442-444`） | ✅ |
| 带 taskId 的 getUploadUrl 建 PENDING 登记行 | `ServiceImpl:109-110` 以 `taskId` 是否为空区分；`:155-166` 建 PENDING 行，`:171-173` `saveAll` | ✅ |
| uploadComplete 请求不变 | `ServiceImpl:311-380`；本批 = `kept` 中 `PENDING → UPLOADED` 的行（`:357-364`） | ✅ |
| replaceFile 请求不变 | `ServiceImpl:251-293`；旧行在 `:277` 软删，新行在 `:281-287` 置 `UPLOADED` | ✅ 需在软删前取旧行的类型；顺序改为先校验后删除（§4.4，审核 S-5） |
| SQS 在提交之后发 | `infrastructure/messaging/AiFinancialExtractionSqsProcessor.java:62-73` + `:125-137`：在事务内调用时挂到 `afterCommit` | ✅ Python 读到的一定是已提交的 `business_type` |
| 财务抽取行的 `business_type` 全部为空、Java 从未写过 | `grep setBusinessType / getBusinessType` 在 `web/ai/` 下 0 处 | ✅ |
| `business_type` 无 CHECK 约束、长度够 | 实体 `domain/AiFileRegistry.java:102` `length = 40`；Python 迁移只有 COMMENT 没有 CHECK | ✅ `EXTRACT_FI_PROFORMA` 19 个字符 |
| Actuals 当月护栏 | `service/AiFinancialExtractionConflictServiceImpl.java:665-668` + `:1678`（`isClosedActualsMonth`） | ✅ 不动 |
| 校验失败返回 400 | 本工程没有返回 HTTP 400 的路径（§5.2） | ✅ 原设计写 400，已按 §11 同步修订（审核 C-9） |

**模块结构现状**：本模块是平铺包（`controller/ service/ domain/ repository/ util/ vo/`），没有
`interfaces/application/domain` 四层；6 个 Service 方法签名**全部直接收 Request**，枚举放在 `util/`
且不带 `Enum` 后缀（`util/AiFinancialExtractionTaskStatus.java`）。本需求**沿用模块现状**，新类按现有位置
与命名放，不在本需求里重构分层。这一点偏离 `standards/architecture.md` §1 与 `coding.md` §2
（「Service 不接触 Request」），**经第⑥阶段审核同意，登记为模块例外**（2026-10-10，§10 J-R1）。

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
| 9 | `extract/domain/AiFinancialExtractionMappingData.java`、`extract/vo/response/AiFinancialPullExtractRowResponse.java` | 改（只改注释） | `parentTableId` 的 javadoc（`:39-44`）与 `@Schema` 描述（`:30-33`）补一句「历史字段：sprint121 起新任务恒为 NULL，仅供历史回放」——Python 停止写 `parent_table_id`（dev-python §7）（审核 A-7） |
| 10 | `extract/vo/request/AiFinancialStagedFilesRequest.java` | 字段不动 | 类注释 `:11-15` 的「Shared by commitUpload and batchDeleteByIds」改完后失效，建议只删掉 commitUpload 这半句 |
| 11 | `extract/service/AiFinancialExtractionConflictServiceImpl.java` | 改（删 1 行） | `applyUserEditsToMappingData` 不再写 `editSourceDataType`（删 `:562`），§4.5（审核 S-4，已拍板） |
| 12 | `extract/vo/request/AiFinancialEditedCellItem.java` | 改（只改注释） | `editSourceDataType`（`:43-45`）字段保留，`@Schema` 描述改为「sprint121 起忽略、不再落库」 |
| 13 | 单测两个新文件 | **新增** | §9 |

**不改**：SQS 消息（`contract/AiFinancialExtractionSqsMessage.java`）、verify / complete 的写入逻辑
（`AiFinancialExtractionConflictServiceImpl` 只删 §4.5 那一行）、`AiFinancialStagedFilesRequest` 的字段、Repository（§4.1 的已提交校验用
`JpaRepository` 自带的 `findAllById`）、`/files/batchDeleteByIds`。

---

## 3. 取值映射：`AiFinancialFileDataType`

| 枚举常量（= 接口值 `dataType`） | `businessType()`（= 登记行 `business_type`） |
|---|---|
| `ACTUALS` | `EXTRACT_FI_ACTUALS` |
| `PROFORMA` | `EXTRACT_FI_PROFORMA` |

只提供两个静态方法：

- `Optional<AiFinancialFileDataType> fromCode(String raw)`：接口值转枚举，空或不认识返回 empty，区分大小写。
  形状同 `AiFinancialExtractionTaskStatus.fromCode`，但不 trim（与 `@Pattern` 一致）（审核 C-6）。
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

**请求**：`{companyId, files: [{fileId, dataType}]}`，字段与校验注解见 §5.1。`companyId` 比旧类多一个
`@Size(max = 36)`：它会拼进 staging 前缀并写入 `company_id`（实体 `length = 36`，`AiFileRegistry.java:75`），超长值在入口就拦掉（审核 S-10）。
响应不变。

**Service 改动**（`:388-451`，主流程顺序不变，换掉两处、加一处）：

1. **去重段**（`:391-402`）：`Set<String> fileIds` 换成 `LinkedHashMap<String, String> businessTypeByFileId`
   （fileId → business_type，保持请求顺序）。逐项 `toBusinessType(item.getDataType())` 后 `putIfAbsent`：
   - 空项（`item == null` 或 `fileId` 为空）`continue` 跳过，与旧实现跳过空 fileId 的行为一致；入口
     `@NotNull` / `@NotBlank` 已拦，这里只防直接调用 Service 时 NPE（审核 C-7）。
   - 同一 fileId 重复出现、类型相同：去重（与原先 `LinkedHashSet` 去重的行为一致）。
   - 同一 fileId 重复出现、**类型不同**：抛 `BadRequestException("Conflicting dataType for file: " + fileId)`
     （需求 R6：一个文件只能是一种类型。原实现是静默去重，换成映射后不挡的话就成了「后一个覆盖前一个」）。
   - 原 `"fileIds is required"` 的兜底保留在循环之后（map 为空即抛），文案改成 `"files is required"`。
2. **已提交校验**（新增，审核 S-6）：`AiFileRegistry` 的 `@Id` 是业务赋值的 `file_id`（`AiFileRegistry.java:52-54`），
   `save()` 一个 new 出来的对象时 Spring Data 判为非新实体、走 `merge`，库里已有同 `file_id` 的行（含软删行，
   实体没有 `@SQLRestriction`）会被整行覆盖。现在重复提交只是碰巧失败：merge 不触发 `@PrePersist`，`created_at`
   被写成 NULL 撞 NOT NULL（`AiFileRegistry.java:135-136`），落 `Throwable` 兜底返回 500。改为在去重之后、建任务之前用 `JpaRepository`
   自带的 `findAllById(businessTypeByFileId.keySet())`（不带 `deleted` 条件，软删行也查得到）查一次，查到任意一行就抛
   `BadRequestException("File already committed: " + fileId)`。
3. **建登记行**（`:425-434`）：在 `row.setDeleted(Boolean.FALSE)` 之后加
   `row.setBusinessType(businessTypeByFileId.get(fileId))`。循环改为遍历 `businessTypeByFileId` 的 entry。
4. **HEAD 看返回值**（`:417-422`，审核 J-R6，2026-10-10 拍板顺手修）：`storage.headObject(...)` 的结果
   `exists()` 为 false 时同样 `missing.add(fileId); continue;`。原实现只 `catch` 异常，而 `headObject` 遇 404 返回
   `S3ObjectHead.missing()`、不抛（`storage/storage/AwsSThreeStorage.java:186-195`），S3 上没有的文件照样被登记、送去
   解析。不增加调用（HEAD 本来就发），无性能影响。全部 missing 时沿用 `:438-439` 的 `"No uploaded files found to commit"`。
   前端配套：读 `missingFileIds` 逐个提示（dev-frontend §3.3）。

类型校验与已提交校验都在 `resolveOrCreateTask`（`:406`）**之前**完成，失败时不会建任务。HEAD 校验、`missing` /
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

- **只校验 `PENDING` 行**：`fileIds` 里允许出现已解析的历史文件（`:299` 的 javadoc、`:365` 的分支注释）（审核 C-5），上线前建的任务里
  这些行的 `business_type` 是 NULL（需求 R11 不补写），全量校验会把老任务的"上传新文件"整个拦死。
- **放在改状态的循环（`:356-371`）之前**：先校验后改写，失败时没有任何行被改。即便在中途抛出，整个事务也会回滚，
  挂在 afterCommit 的 SQS 不会发出。

### 4.4 `POST /tasks/{taskId}/file/replace`

**请求**不变。**Service 改动**（替换 `:276-287`，先校验、后删除）：

1. **旧登记行必须存在**（审核 S-5）：`:277` 的 `findByFileIdAndDeletedFalse(oldId).ifPresent(...)` 改成
   `.orElseThrow(() -> new BadRequestException("Old file not found for task: " + oldId))`。`assertFileBelongsToTask`
   （`:743-756`）在登记行不存在时只回退查 `files`，`files` 行也没有就直接放行，所以现状下旧文件不存在也能"替换"成功；
   加了继承后，这种请求会让新文件拿到 NULL 类型。
2. **新行校验挪到删除之前**（审核 S-5）：新行查询 + `PENDING` 校验（原 `:281-285`）挪到旧文件下线（`:277-278`）之前。
   `fileService.delete` 的 S3 删除即时生效、不随事务回滚（`FileServiceImpl:106-111`），现状是先删旧文件再校验新行，
   新行不合法时事务回滚了，旧文件的 S3 对象却已经没了。
3. **取类型再软删**：`inherited = oldRow.getBusinessType()` 在软删之前取（软删后 `findByFileIdAndDeletedFalse` 查不到）。
4. `:286` `newRow.setStatus("UPLOADED")` 旁边加 `newRow.setBusinessType(inherited)`：**无条件覆盖**，即使前端调
   getUploadUrl 时误带了 `dataType` 也以旧文件为准（需求 R8：替换文件继承类型）。
5. `inherited == null`（旧文件是上线前上传的）：照设计原样复制 NULL，打一条 `log.warn`（审核 S-10）。按 `coding.md` §11
   （每条业务日志含 traceId / userId / organizationId）：traceId 由 `LoggingContextFilter` 放进 MDC、日志格式自带；
   userId 照 `:721` 显式取 `SecurityUtils.getUserId()`；organizationId 取 `task.getOrganizationId()`（任务创建时的快照，
   老任务可能为空）；再加 taskId / oldFileId / newFileId，前缀沿用模块的 `[AI-Extract]`。这个文件随后会被 Python 判为
   `FILE_FAILED`（设计 §5.1、D9）。不改为直接拒绝替换"类型为 NULL 的旧文件"——已拍板照现稿，见 §10 J-R2。

### 4.5 complete：不再保存前端回传的 `editSourceDataType`（审核 S-4，2026-10-10 拍板）

`ConflictServiceImpl.applyUserEditsToMappingData` 把映射页的编辑写回 `mapping_data`，`:562` 仍会保存前端回传的
`editSourceDataType`。R7 已经去掉逐行改派，这个字段在新任务上不该再有值，**删掉 `:562` 这一行**：

- **只删、不清空**：上线前已在映射页的任务，用户之前的改派值留在库里（前端 `rowClassify.ts:28`、`useOCRData.ts:56`
  仍按 `editSourceDataType` 优先显示），删掉这行后不会被覆盖；改成写空串反而会把历史改派抹掉。
- **请求字段保留**：`AiFinancialEditedCellItem.editSourceDataType` 不删，只改描述。旧前端还会传它（Jackson 已关
  `FAIL_ON_UNKNOWN_PROPERTIES`，删了也不报错，但已发布接口不删字段，见 `coding.md` §9），Java 忽略即可。
- **范围**：只管"编辑不落库"。complete 写财务数据时仍按前端回传的每行 `sourceDataType` 分 Actuals / Proforma
  （`:982`），不和文件声明交叉核对（§10 J-R5）。
- 不加单测：这是私有方法，要经 `completeTask` 整条链才能走到，桩链长；改动只是删一行。新前端也不再发这个字段，
  联调观察不到差异。

---

## 5. 校验与报错

### 5.1 请求类上的注解（第一道，入口校验）

| 字段 | 注解 | 说明 |
|---|---|---|
| `AiFinancialCommitUploadRequest.companyId` | `@NotBlank @Size(max = 36)` | 旧类只有 `@NotBlank`；长度上限同 `company_id` 列（§4.1，审核 S-10） |
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
| commitUpload 的 fileId 已有登记行（含软删，审核 S-6） | `BadRequestException` | HTTP 200 + `success: false`（现状是 500） |
| uploadComplete 本批有文件未声明类型 | `BadRequestException` | HTTP 200 + `success: false` |
| replaceFile 旧登记行不存在（审核 S-5） | `BadRequestException` | HTTP 200 + `success: false`（现状是放行） |
| Service 被直接调用、`dataType` 非法（单测路径） | `BadRequestException`（`toBusinessType`） | — |

原设计 §4 写的是"返回 400"，已按 §11 #1 同步修订（审核 C-9）：`BadRequestException` 自带 `status = 400`
（`BadRequestException.java:16`），但全局处理器不读这个字段，统一返回 HTTP 200 + `success: false`。
本文**不新增**异常处理分支，沿用现状。

### 5.3 报错文案（英文，与模块现有文案一致）

| 位置 | 文案 |
|---|---|
| `@NotEmpty` files | `files is required` |
| `@NotBlank` dataType | `dataType is required` |
| `@Pattern` dataType | `dataType must be ACTUALS or PROFORMA` |
| `toBusinessType` | `dataType must be ACTUALS or PROFORMA: {raw}` |
| commitUpload 类型冲突 | `Conflicting dataType for file: {fileId}` |
| commitUpload 重复提交 | `File already committed: {fileId}` |
| uploadComplete 未声明 | `Table type (Actuals / Proforma) is required for file: {fileName}` |
| replaceFile 旧文件不存在 | `Old file not found for task: {oldFileId}` |

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
| 新 Java + 旧前端（映射页） | Upload New Document 不带类型 → uploadComplete 拒绝（HTTP 200 + `success: false`）（审核 C-8） |
| 旧 Java + 新前端 | 旧 `AiFinancialStagedFilesRequest.fileIds` 为 `@NotEmpty`，新前端不再传它 → 同样 422 |
| 新 Java + 新前端 + 旧 Python | 旧 Python 忽略声明、按旧逻辑推断；新前端已去掉逐行改派（R7），判错了用户改不回来——例如一个全是历史月份的 Proforma 文件被判成 ACTUALS，提交后写进 `finance_manual_data`。**不能作为过渡状态** |
| 旧 Java + 新 Python | 旧 commitUpload 不写 `business_type` → 每个新文件都被判 `FILE_FAILED` |

发布与回滚（审核 S-1 / A-1 / A-2，与设计 §8、[dev-design-doc](./dev-design-doc.md) §3.2 一致）：

- **V030** 任意时间执行（只改注释）。
- **Java + 前端 + Python 同一个发布窗口**：Java 与前端同批，Python 紧接着发（分钟级）。原稿"Python 可择日、平滑过渡"
  不成立，原因见上表第 4 行。
- **回滚三端一起**：回滚 Java + 前端时必须同时回滚 Python（否则就是上表最后一行）；只回滚 Python 只能作短时止血，
  期间声明不生效。
- 发布后用核查 SQL 找出窗口期内类型与声明不一致的任务，SQL 在 [dev-design-doc](./dev-design-doc.md) §3.2。

已写入的 `EXTRACT_FI_*` 对回滚后的旧 Java（从不读这一列）和旧 Python（rag 查询只匹配原来那几个取值）都无副作用，
回滚不需要清数据。getUploadUrl 新增的 `dataType` 是可选字段，旧 Java 收到会忽略，对发布顺序没有额外要求。

**提交要求**（§10 J-R8）：commitUpload 改请求体的那次提交，body 末尾加 `BREAKING CHANGE:` 脚注，写明
`POST /tasks/commitUpload` 的请求体由 `fileIds` 改为 `files[{fileId, dataType}]`、须与前端同批发布（`standards/git.md:24`；
写法参照 ERL `96d59ec53`）。前端对应提交同样加。

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
| T13 | commitUpload 的 fileId 已有登记行（stub `findAllById` 返回一条 `deleted = true` 的行）（审核 S-6） | 抛 `BadRequestException("File already committed: f-1")`；`taskRepository.save`、`extractionFileRepository.save`、`sqsProcessor` 都 `never()` |
| T14 | replaceFile 旧登记行不存在（`files` 行也没有，`assertFileBelongsToTask` 放行）（审核 S-5） | 抛 `BadRequestException`；`fileService.delete` `never()`；新行仍为 PENDING |
| T15 | replaceFile 新行不是 PENDING（审核 S-5） | 抛 `BadRequestException`；旧行 `deleted` 仍为 false、`fileService.delete` `never()`（先校验后删除） |
| T16 | commitUpload 两个文件，第二个 HEAD 返回 `S3ObjectHead.missing()`（审核 J-R6） | `committedFileIds == [f-1]`、`missingFileIds == [f-2]`；`extractionFileRepository.save` 只调一次 |

Mockito 严格模式下，拒绝类用例（T3 / T4 / T9 / T13 / T14 / T15）只 stub 会被走到的调用，否则会报 `UnnecessaryStubbingException`。

**同构省略只适用于 T5 / T10 / T12**（审核 C-3）。T6–T8 走 `presignUploads`，比 commitUpload 多几处 stub，不 stub 会 NPE：

- `fileRepository.saveAndFlush(any())`：返回入参并 `setId(...)`，否则 `persisted` 为 null，`:149` `persisted.getId()` NPE（`:148-152`）；
- `storage.presignPutObject(...)`：返回 `new PresignedPutObjectResult(url, requiredHeaders, expiresInSeconds)`（record，
  `storage/model/PresignedPutObjectResult.java:12`），否则 `:186` `presigned.url()` NPE（调用在 `:180`）；
- T6 / T7 带 taskId：`taskRepository.findByIdAndCompanyIdAndDeletedFalse(TASK_ID, COMPANY_ID)`（`:709`）返回状态不是
  `UPLOAD_COMPLETE` / `PROCESSING` 的任务，否则被 `:113` 的 `blocksNewUpload` 拒绝；
- 请求项的 `length` 是 `Long`，必须赋值（`:129` 拆箱）。

T8 不带 taskId，不需要任务 stub，只断言 `saveAll` `never()`。

**新文件 2**：`.../extract/vo/request/AiFinancialCommitUploadRequestValidationTest.java`

照 `src/test/.../thirdParty/application/dto/ThirdPartyConnectionHostUrlValidationTest.java` 的写法，用
`Validation.buildDefaultValidatorFactory().getValidator()` 直接校验请求对象（Service 单测绕过了 `@Valid`，入口这一层要单独测）：

| # | 用例 | 断言 |
|---|---|---|
| V1 | 合法 body | 0 条违规 |
| V2 | 某项缺 `dataType` / 值为 `"Actuals"` / `"FORECAST"` | 违规路径为 `files[0].dataType` |
| V3 | 旧 body 形状（只有 `companyId`，`files` 为 null） | 违规路径为 `files`——这条锁住"旧前端会被拒"（§8） |
| V4 | `AiFinancialPresignUploadFileItem.dataType` 为 null 通过、`"X"` 不通过 | 用 `validator.validateProperty(item, "dataType")` 只校验这一个字段（先例同上 `:57`、`:63`），不校验整个 item——否则没赋值的 `fileName` / `length` 也会报违规（审核 C-4） |

建议命令（按根 `CLAUDE.md`「测试运行策略」，等用户下指令再跑；Surefire 多个类用逗号分隔，审核 C-1）：
`mvn -pl gstdev-cioaas-web test "-Dtest=AiFinancialExtractionDeclaredTypeTest,AiFinancialCommitUploadRequestValidationTest"`；
回归加跑同包现有的 `AiFinancialExtractionPngPreviewTest`、`AiFinancialExtractionClosedMonthTest`。

---

## 10. 风险与待确认

| # | 风险 / 问题 | 处置 |
|---|---|---|
| J-R1 | 本模块的 Service 直接收 Request，偏离「Request → DTO → Service」规范（§1） | **已拍板（2026-10-10）：登记为模块例外**，新代码沿用模块现状、不补 DTO（只为 commitUpload 补会让同一接口里出现两种写法）。不记待优化项（审核 A-6） |
| J-R2 | 上线前建的任务，在映射页**替换**旧文件 → 新文件继承 NULL → Python 判 `FILE_FAILED` | 符合设计 D9 / 需求 R11（历史不补写），但用户只会看到文件失败、不知道原因。可选改进：Java 在替换时发现旧文件没有类型就直接拒绝，给出可读提示（例如"请改用 Upload New Document"）——属于产品决策，不在 D1~D10 内。**已拍板（2026-10-10）：照现稿**，按设计原样复制、不在替换时拒绝；只影响上线时尚未提交的老任务，属过渡期问题。§4.4 的"旧行必须存在、先校验后删除"（审核 S-5）与此无关，本期照做 |
| J-R3 | 映射页 Upload New Document 的类型**只能在 getUploadUrl 时提交**，之后没有接口能改 | 设计 §10 Q2（类型选择的交互样式）尚未定稿。若设计稿选择"先上传、后选类型"，前端必须等用户选完再调 getUploadUrl；否则 Java 要在 uploadComplete 上加字段。请前端按此约束实现 |
| J-R4 | "当前月"的口径两端不同：Python 用处理时刻的 UTC（D6），Java 护栏用 `LocalDate.now()` 的 JVM 默认时区（`ConflictServiceImpl:665`） | JVM 跑在 UTC 时两边一致；不是 UTC 时，月初几小时内两道防线的判断可能差一个月。D6 已定 Java 不参与，**本期不改**，上线前确认生产 JVM 时区即可 |
| J-R5 | complete 仍然信任前端回传的每行 `sourceDataType`（`ConflictServiceImpl:982`），不和文件声明交叉核对 | 设计 §6 明确"complete 写入逻辑不变"；映射页已不能改派类型（R7），数据来自 Python 按声明类型写的单元格。不加交叉校验。最小加固**已拍板采用**（2026-10-10）：不再保存 `editSourceDataType`，见 §4.5（审核 S-4 / A-13） |
| J-R6 | **顺带发现，与本需求无关**：commitUpload 的 S3 落盘校验（`ServiceImpl:418-424`）只 `catch` 异常、不看返回值，而 `headObject` 遇到 404 返回 `S3ObjectHead.missing()`、不抛异常（`storage/storage/AwsSThreeStorage.java:186-195`）。S3 上不存在的文件因此仍会被登记并送去解析，`missingFileIds` 实际只收得到"不在本公司 staging 目录"的文件 | **已拍板（2026-10-10）：本期顺手修**，见 §4.1 第 4 步、单测 T16；前端配套提示 missing 文件（dev-frontend §3.3） |
| J-R7 | 写路径没有"调用者 → 公司"授权：commitUpload 的 staging 前缀用请求体里的 `companyId`（`ServiceImpl:405`、`:414`）；带 taskId 的 getUploadUrl 按请求体 `companyId` 查任务（`:110`、`:706-711`）；uploadComplete 只按 taskId 查任务（`:316-345`）；complete 的 `loadTask` 同样只按 id（`ConflictServiceImpl:347-361`、`:1252-1263`）。`ServiceImpl:506` 的注释也承认预览接口不校验归属（审核 S-2） | 存量问题，本需求沿用。**2026-10-10 用户决定暂不处理** |
| J-R8 | commitUpload 在原路径上改请求体，旧 `{companyId, fileIds}` 直接 422（§5.2 / §8），与 `coding.md:112`「已发布接口禁止删除字段或改类型，破坏性变更须新路径 + `BREAKING CHANGE`」不符 | **已拍板（2026-10-10）：登记为例外**，原路径改请求体、Java 与前端同批发布，两端提交 body 加 `BREAKING CHANGE:`（§8 提交要求）。理由：唯一调用方是同批发布的上传弹窗；类型必填后旧格式本来就无法兼容，开新路径只会让旧请求"调得通"、文件却在 Python 判失败；先例 ERL `96d59ec53`（审核 A-3） |

---

## 11. 与上游设计的出入（已于 2026-10-10 同步进设计文档 §4 / §6）

| # | 设计文档原文 | 实际 | 建议 |
|---|---|---|---|
| 1 | §4「返回 400 并给出可读的提示」 | 本工程没有返回 HTTP 400 的路径：入口字段校验 → **422**（带字段级 `errors[]`），业务校验 → **HTTP 200 + `success: false`**（§5.2） | 设计 §4 改成"字段校验失败 422；业务校验失败 `success: false` + 提示"，前端两种都要当失败处理 |
| 2 | §3.1「Java 实体注释同步更新」 | 实体注释除了新增两个值，还漏了 `ADMIN_ORGANIZATION`；类 javadoc 与字段组注释写着"本模块不写这些列"，改完后与代码矛盾 | 已列入 §7 |
| 3 | §6「必填校验：手动录入公司的文件必须有声明类型」 | Java 里没有"手动录入公司 / QBO 公司"的判断，校验对所有公司一视同仁 | 与 D10 一致（QBO 本来看不到入口），文档措辞可去掉"手动录入公司"这个限定 |
| 4 | §4 uploadComplete「校验本次每个文件都已声明类型」 | "本次"必须落实为 **`kept` 中状态为 PENDING 的行**；按 `fileIds` 全量校验会拦住老任务 | 已在 §4.3 落实 |
