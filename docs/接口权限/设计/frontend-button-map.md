# 附录 B：管理端按钮 → 模块 × 动作清单

> 关联文档: [设计方案](./design-doc.md) · [附录 A：后端接口映射](./endpoint-permission-map.md)

- 代码根：`web/CIOaas-web/src/`。下文路径无前缀的都相对 `src/pages/`；`~` 表示行号指向处理函数或调用处，而不是按钮本身。
- 调研日期 2026-10-13（sprint121）。行号会随开发漂移，实施时以符号名为准。
- **"共用"列**：Y 表示公司端用户也会进这个组件，隐藏判断必须写成"仅管理端（`roleType === 1`）按权限隐藏，公司端维持原逻辑"；"Y（管理端分支）"表示按钮本来就只在管理端渲染。
- 动作取值：CREATE / UPDATE / DELETE；CREATE_OR_UPDATE 表示有新增或修改任一权限即显示（新增和修改合一的保存、流程动作）。

## 不纳入隐藏的入口

- 个人资料和改密码页；只改视图偏好的操作，比如切换列表样式、保存列设置（`portfolioCompanies/general/companyTable.tsx:733`）、切换币种；关闭横幅；导出 PDF 或 PNG；Ask Goldie 个人会话的重命名和删除。
- 只读页面：QBO Log、Metrics Tracing、Normalization Tracing、Dev Settings、知识库、Memory Settings、LLM 和 Tracing 页、Financial Extract Tasks。
- 旧的 `pages/company/**`：路由已注释掉，也没有被引用。
- **RAG 相关页面（`devSupport/rag/**`，约 16 处入口）**：调用的是 Python 接口 `/api/ai/*`，不在第一期的后端校验范围内。前端只隐藏、后端不拦不构成防护，所以第一期整块不纳入，见设计方案 §3。

- **调用已不存在的后端接口的入口**：KPA 管理页（`settings/kpaAdmin/**`）上的文档上传 / 删除、KPA 工具选择和评论，调的是 `/document/multipleFilesUploadForKpaCategory`、`/document/deleteForKpaCategory`、`/tools/saveSingleKpaCategoryTool`、`/tools/saveKpaCategoryToolComment`。这四个后端接口已经不存在，代码里有 `TODO(dead-upload-cleanup)`，所以不纳入隐藏，见附录 A §4.7。
- **重置密码按钮**：调的 `/users/sendEmailToReset` 是匿名接口，后端拦不住，前端也不隐藏，以免两边口径不一致。

模块划分和附录 A 一致：**按钮归哪个模块，就看它调的接口在附录 A 里归哪个模块**。

## company（公司、公司设置）

| 页面 / 组件 file:line | 按钮 / 入口 | 动作 | 后端接口 | 共用 |
|---|---|---|---|---|
| `portfolioCompanies/home/PortfolioCompaniesPage.tsx:358`、`:733-735`（×2） | "Add Company"（现由功能名 'Add Company' 控制，`:139`） | CREATE | 跳转 `/addCompany` | N |
| `portfolioCompanies/addCompany/AddCompanyPage.tsx:308-325` | 确认 "Yes, Create Company" | CREATE | POST `/invite/addCompanyAndSetStage` | N |
| `addCompany/components/addProgrct.tsx:268`、`addTechSteck.tsx:357`、`addStage.tsx:149`（×3） | 向导各步 Save | CREATE | 同一流程 | N |
| `companySettings/components/general/GeneralTab.tsx:636`（`:600` 的 "+" 行） | 保存公司基本信息 | UPDATE | POST `/invite/addWithoutEmail` | Y |
| `GeneralTab.tsx:656-658` | "Deactivate Company" | DELETE | PUT `/invite/delete/{id}` | Y（管理端分支） |
| `companySettings/components/modules/ModulesTab.tsx:181` | 保存模块开关（FI/DI） | UPDATE | POST `/invite/updateModulesSettings` | N（管理端 Tab） |
| `companySettings/stage/CompanyStagePage.tsx:268`、`:285`、`:299`（×3） | "Save Stage" | CREATE_OR_UPDATE | POST `/stage/saveCompanyStage` | Y |

## investment（仅管理端）

| 页面 / 组件 file:line | 按钮 / 入口 | 动作 | 后端接口 |
|---|---|---|---|
| `companyOverview/investments/InvestmentsPage.tsx:441` → `addInvestment/AddInvestmentPage.tsx:652` | "Add Investment" | CREATE | POST `/invite/investmentSave`（新增或修改合一，按钮按 CREATE 隐藏） |
| `InvestmentsPage.tsx:238`、`investmentDetails/InvestmentDetailsPage.tsx:192`（×2） | "Edit Investment" | UPDATE | 同上 |
| `companyOverview/investments/components/AddDocumentation.tsx:686` | 上传投资附件 | CREATE | POST `/invite/investmentUpload` |
| `AddDocumentation.tsx:619` | 删除投资附件 | DELETE（归 companyDocument） | 按实际调用的文档删除接口归模块 |

## user（管理端用户、公司成员）

| 页面 / 组件 file:line | 按钮 / 入口 | 动作 | 后端接口 | 共用 |
|---|---|---|---|---|
| `settings/userManage/UserManagePage.tsx:164` | "Add Portfolio User"（现由 'Add Admin' 控制，`:103`） | CREATE | POST `/users/adminUser` | N |
| `UserManagePage.tsx:120` → `detail/UserDetailPage.tsx:675` | 点卡片编辑后 Save | UPDATE | 同上 | N |
| `UserDetailPage.tsx:633` | "Add User to Portfolio" | UPDATE | 同上 | N |
| `UserDetailPage.tsx:648-655` | "Delete User" | DELETE | PUT `/users/delete/{id}` | N |
| `UserManagePage.tsx:129` | 重新邀请 | CREATE_OR_UPDATE | GET `/users/inviteAgain` | N |
| `companySettings/components/team/TeamTab.tsx:382` → `addUser.tsx:355-359` | "Add User" | CREATE | POST `/users/invite` | Y |
| `TeamTab.tsx:393` → `addUser.tsx:355` | 编辑成员 | UPDATE | PUT `/users/{id}` | Y |
| `addUser.tsx:336-343` | "Delete User" | DELETE | PUT `/users/delete/{id}` | Y |
| `TeamTab.tsx:189` | 重新邀请 | CREATE_OR_UPDATE | GET `/users/inviteAgain` | Y |
| `TeamTab.tsx:368` → `addGroup.tsx:118` | "Create Group" | CREATE_OR_UPDATE | POST/PUT `/organize` | Y |
| `addGroup.tsx:95-102` | "Delete Group" | DELETE | DELETE `/organize` | Y |

## companyFinancial（财务录入、版本、AI 提取、财务设置，全部共用）

`FinancialEntryV2` 复用 `FinancialEntry/components/*`，改一处 V1 和 V2 都生效。

| 页面 / 组件 file:line | 按钮 / 入口 | 动作 | 后端接口 |
|---|---|---|---|
| `financial/FinancialEntry/components/HeaderBar.tsx:784`、`:796`（×2） | "Edit Financial Actuals" / "Edit Committed Forecast"（进入编辑态） | UPDATE | — |
| `HeaderBar.tsx:431`、`:562`、`:834`（×3） | "Accept as Committed Forecast" | CREATE_OR_UPDATE | POST `/financialForecastHistory/acceptCommitted`（V1）或 `/financialEditing/submit`（V2） |
| `HeaderBar.tsx:517`、`:535`（×2） | 版本重命名 | UPDATE | PUT `/financialForecastHistory/version` |
| `HeaderBar.tsx:730` / `:665`、`:705` / `:714`、`:910`（×5） | 版本备注的新增、保存、编辑、删除 | CREATE / UPDATE / DELETE | 同上 |
| `FinancialEntry/components/EditFooter.tsx:39` | Submit | CREATE_OR_UPDATE | `financialEntrySubmit` / `financialForecastSubmit` / V2 `editingSubmit` |
| `FinancialEntry/components/FinanceTable.tsx:759` | "Save Changes" | UPDATE | POST `/financeManualData` 或 `/financialEditing/save` |
| `FinancialEntry/components/TableToolbar.tsx:466`、`:582`（×2）；`ImportStatementsModal.tsx:459` | "Import Statements" / 移除 | CREATE | 上传流程 |
| `FinancialEntry/components/DocumentModal.tsx:145` / `:132` / `:167`、`:175` | 上传 / 替换 / 删除附件 | CREATE / UPDATE / DELETE | `/financeManualData/uploadFile`、`/deleteFile`（V2 为 `/financialEditing/document/*`） |
| `financial/systemHistory/Index.tsx:286` → `:527` | 归档版本 | DELETE | DELETE `/financialForecastHistory/version` |
| `financial/aiFinancialExtraction/components/FileSelector.tsx:252` / `:257` | 替换 / 删除文档 | UPDATE / DELETE | `/ai/financialExtraction/tasks/*` |
| `aiFinancialExtraction/components/FileProcessingErrorsModal.tsx:51` | 重新上传 / 上传 | CREATE | `getUploadUrl` / `commitUpload` |
| `aiFinancialExtraction/components/VerifySubmitPanel.tsx`（`AiFinancialExtractionPage.tsx:~410`） | Verify / Resolve / Submit | CREATE_OR_UPDATE | `/financial-data-conflict/tasks/*` |
| `companySettings/components/finance/FinanceTab.tsx:543` → `:1114` | 编辑收入列报方式 | UPDATE | PUT `/invite/revenueRecognitionSet` |
| `FinanceTab.tsx:581` → `ModalCurrency.tsx:88` | 编辑币种 | UPDATE | PUT `/invite/currencySave` |
| `FinanceTab.tsx:597` | 编辑录入方式 | UPDATE | conversion mode |
| `FinanceTab.tsx:617` → `:1158` | 编辑会计方法 | UPDATE | PUT `/invite/accountMethodGetSet` |
| `FinanceTab.tsx:635` / `:636` | 断开 / 连接 QuickBooks | DELETE / CREATE | `/companyQuickbooks/disconnect`、OAuth 跳转 |
| `FinanceTab.tsx:645`、`:969`、`:794`、`:800`（×4） | QBO 设置编辑 / 保存 | UPDATE | POST `/companyQuickbooks` |
| `companySettings/financeSetting/FinanceSettingPage.tsx:378` | "Save and Go to Next Step" | CREATE_OR_UPDATE | 财务初始化 |

## companyDocument（全部共用）

| 页面 / 组件 file:line | 按钮 / 入口 | 动作 | 后端接口 |
|---|---|---|---|
| `document/companyDocuments/CompanyDocumentsPage.tsx:476`、`:592`、`:660`、`:681`（×4） | Add Documentation / Save and Add | CREATE | POST `/document/addDocuments` |
| `CompanyDocumentsPage.tsx:543`、`:649`、`:708`、`:731`（×4） | 删除 | DELETE | DELETE `/document/deleteDocumentByDocumentId` |
| `companyOverview/documentation/components/DocumentList.tsx:454`、`:582`、`:661`、`:682`（×4） | Add Documentation / Save and Add | CREATE | POST `/companyDocumentation/addDocumentation` |
| `DocumentList.tsx:532`、`:648`、`:709`、`:735`（×4） | 删除 | DELETE | DELETE `/companyDocumentation/deleteDocumentByDocumentId` |
| `companyOverview/home/CompanyOverviewPage.tsx:894-901` | 下拉菜单里的删除 | DELETE | `deleteDocumentData` |
| `development/overview/index.tsx:160-167` | 删除文档 | DELETE | 同上 |
| `document/home/DocumentPage.tsx:203` | 删除 | DELETE | dva `document/deleteFile` |
| `DocumentPage.tsx:221`、`:323`、`:475`；`document/components/ModalShare.tsx:111`（×4） | Share / Share All | CREATE_OR_UPDATE | POST `/document/shareDocumentEmail` |

## project（DI 产品、连接器、公司级技术栈，全部共用）

| 页面 / 组件 file:line | 按钮 / 入口 | 动作 | 后端接口 |
|---|---|---|---|
| `development/product/index.tsx:138-139`；`development/overview/index.tsx:662`、`:828-830`（×3） | Add Product | CREATE | 跳转产品设置 |
| `companyDevelopmentProduct/productSetting/general/GeneralPage.tsx:323`；`components/addEditProject.tsx:187`（×2） | 保存产品 | CREATE_OR_UPDATE | POST `/project/saveAndAssign` |
| `GeneralPage.tsx:326`；`addEditProject.tsx:159-167`（×2） | 删除产品 | DELETE | PUT `/project/delete/{id}` |
| `development/product/index.tsx:~63` | 归档产品 | UPDATE | POST `/project/archiveProject` |
| `companyDevelopmentProduct/home/ProjectNaviPage.tsx:127` | 编辑图标 | UPDATE | 跳转 |
| `companyDevelopmentProduct/productSetting/dataConnections.tsx:~45` | 大数据开关 | UPDATE | POST `/project/saveBigDataModule` |
| `companyDevelopmentProduct/toolConfig/ToolConfigPage.tsx:586` | 保存连接器配置 | CREATE_OR_UPDATE | POST/PUT `/thirdParty/connection` |
| `ToolConfigPage.tsx:597-604` | "Remove Connector" | DELETE | DELETE `/thirdParty/connection` |
| `development/product/weight.tsx:123` | 保存产品权重 | CREATE_OR_UPDATE | POST `/score/saveProjectWeight` |
| `companyDevelopmentProduct/techStack/index.tsx:199`、`:215`、`:302` → `editTechStack.tsx:148` | "Edit Tech Stack" | UPDATE | POST `/techStack/updateTechStackElement` |
| `settings/kpaAdmin/components/InviteMember.tsx` | 邀请项目成员 | CREATE_OR_UPDATE | POST `/project/inviteuser` |

## techStack（平台技术栈配置 `/profile/techStackNavi`，仅管理端）

| 页面 / 组件 file:line | 按钮 / 入口 | 动作 | 后端接口 |
|---|---|---|---|
| `settings/techStackManagement/TechStackManagementPage.tsx:54` | "Add Element" | CREATE | — |
| `TechStackManagementPage.tsx:~123` | 保存分类权重 | UPDATE | POST `/techStackManagement/saveTechCategoryWeight` |
| `settings/techStackManagement/components/CategoriesAndElements.tsx:501` | 保存元素 | CREATE_OR_UPDATE | POST `/techStackManagement/saveTechStackElement` |
| `CategoriesAndElements.tsx:587` | 删除元素 | DELETE | PUT `/techStackManagement/deleteElement` |
| `CategoriesAndElements.tsx:647`、`:736`、`:817`（×3） | 编辑元素权重 / 保存 | UPDATE | POST `/techStackManagement/saveTechStackElements` |
| `CategoriesAndElements.tsx:661` | 分类 Done | UPDATE | POST `/techStackManagement/updateTechCategory` |
| `settings/techStackManagement/components/Layers.tsx:255` | 保存层级 | CREATE_OR_UPDATE | POST `/techStackManagement/layer` |

## kpa（公司 KPA 评审）

| 页面 / 组件 file:line | 按钮 / 入口 | 动作 | 后端接口 | 共用 |
|---|---|---|---|---|
| `development/kPAReviews/add.tsx:404`；`development/components/KPADocumentation.tsx:229`（×2） | 提交 KPA Review | CREATE | POST `/kpaBusiness/addKpaReview` | Y |
| `development/kPAReviews/edit.tsx` | 编辑 Review | UPDATE | PUT `/kpaBusiness/editKpaReview` | Y |
| `KPADocumentation.tsx:211` / `:200` | 添加 / 删除文档 | CREATE / DELETE | 随 Review 一起提交 | Y |

## kpaConfig（KPA 配置，仅管理端）

| 页面 / 组件 file:line | 按钮 / 入口 | 动作 | 后端接口 |
|---|---|---|---|
| `settings/kPAConfiguration/KpaConfigurationPage.tsx:97` | 编辑 | UPDATE | 跳转 |
| `settings/kPAConfiguration/edit/KpaConfigEditPage.tsx:319-320` / `:312` | 添加 / 移除软件 | UPDATE | 随保存提交 |
| `KpaConfigEditPage.tsx:366` | Save Changes | UPDATE | POST `/kpaManagement/updateKpaLevel` |

## scoreConfig（SDP 评分配置，仅管理端）

| 页面 / 组件 file:line | 按钮 / 入口 | 动作 | 后端接口 |
|---|---|---|---|
| `settings/sDPScore/SdpScorePage.tsx:704`、`:712`（×2） | Save / Save Changes | UPDATE | POST `/score/saveScoreConfiguration` |
| `settings/sDPScore/components/codeQuality.tsx:418` → `addSubItem.tsx:52` | "Add Item" | CREATE | POST `/etlScoreType` |
| `codeQuality.tsx:321`、`:308` | 编辑 / 保存 | UPDATE | PUT `/etlScoreType` |
| `codeQuality.tsx:331-337` | 删除 | DELETE | DELETE `/etlScoreType` |

## financeScore、alert、portfolioGroup、portfolio（仅管理端）

| 模块 | 页面 / 组件 file:line | 按钮 / 入口 | 动作 | 后端接口 |
|---|---|---|---|---|
| financeScore | `settings/financeConfig/FinanceConfigPage.tsx:260` | Save Changes | UPDATE | POST `/financeScoreLevel/saveFinanceScoreSetup` |
| alert | `settings/alertConfiguration/AlertConfigurationPage.tsx:269-276` | Submit | UPDATE | PUT `/EtlConfig` |
| portfolioGroup | `devSupport/portfolioGroupManagement/PortfolioGroupManagementPage.tsx:237`、`:312` → `components/PortfolioGroupAddModal.tsx:110` | 新增 / Save | CREATE | POST `/organization` |
| portfolioGroup | `PortfolioGroupManagementPage.tsx:247` | 编辑 | UPDATE | PUT `/organization` |
| portfolioGroup | `PortfolioGroupManagementPage.tsx:257-266` | 删除 | DELETE | DELETE `/organization` |
| portfolioGroup | `PortfolioGroupManagementPage.tsx:404` | 保存菜单树 | UPDATE | PUT `/organization/modifyOrganizationMenu` |
| portfolio | `settings/portfolioManagement/PortfolioManagementPage.tsx:203` → `add/PortfolioAddPage.tsx:144` | Create Portfolio | CREATE | POST `/companyGroup` |
| portfolio | `PortfolioManagementPage.tsx:217`、`:347`、`:427`（×3） → `components/ModifyCompanyGroup.tsx:327` | 编辑 / 保存 | UPDATE | PUT `/companyGroup`、POST `/companyGroup/relevance` |
| portfolio | `ModifyCompanyGroup.tsx:304` | 删除 Portfolio | DELETE | DELETE `/companyGroup` |
| portfolio | `ModifyCompanyGroup.tsx:308` | 从 Portfolio 移除公司 | DELETE | DELETE `/companyGroup/delete` |

## role（角色、菜单、公司角色、权限管理，仅管理端）

| 页面 / 组件 file:line | 按钮 / 入口 | 动作 | 后端接口 |
|---|---|---|---|
| `devSupport/rolesManagement/RolesManagementPage.tsx:319-328` → `components/SettingRoleModal.tsx:90-97` | "Add Role"（现在按 `roleType === 1` 判断） | CREATE | POST `/rOrganizationRole/addOrganizationRole` |
| `RolesManagementPage.tsx:293` | 编辑角色 | UPDATE | 同上 |
| `RolesManagementPage.tsx:304-313` | 删除角色 | DELETE | DELETE `/rOrganizationRole/deleteOrganizationRole` |
| `RolesManagementPage.tsx:412-418` | 保存菜单 / 功能树 | UPDATE | PUT `/rOrganizationRole/modifyOrganizationRoleMenu` |
| `devSupport/menuManagement/MenuManagementPage.tsx:179`、`:278-288`、`:301-312` → `components/AddMenuModal.tsx:171` | Add Menu / Add Function | CREATE | POST `/menus/addMenu` |
| `MenuManagementPage.tsx:82`、`:190`、`:246`（×3） | 编辑菜单或功能 | UPDATE | 同上 |
| `MenuManagementPage.tsx:94`、`:202`、`:257`（×3） | 删除菜单或功能 | DELETE | DELETE `/menus/deleteMenu` |
| `devSupport/companyRoles/CompanyRolesPage.tsx:211-220` | Add Role | CREATE | POST `/rOrganizationRole/addCompanyRole` |
| `CompanyRolesPage.tsx:185` / `:196-205` | 编辑 / 删除角色 | UPDATE / DELETE | DELETE `/rOrganizationRole/deleteOrganizationRole` |
| `CompanyRolesPage.tsx:287` | 保存 | UPDATE | PUT `/rOrganizationRole/modifyOrganizationRoleMenu` |
| 新增的权限管理页 | 保存角色权限 | UPDATE | 见设计方案 §7 |

## indicator、businessIssue、peerGroup

| 模块 | 页面 / 组件 file:line | 按钮 / 入口 | 动作 | 后端接口 | 共用 |
|---|---|---|---|---|---|
| indicator | `devSupport/indicator/IndicatorPage.tsx:38`、`:52-54`（现由功能名 'add Indicator' 控制） | Add Indicator | CREATE | POST `/etlScoreTarget` | N |
| indicator | `devSupport/indicator/components/IndicatorAddModal.tsx:248` | 保存 | CREATE_OR_UPDATE | POST/PUT `/etlScoreTarget` | N |
| indicator | `IndicatorAddModal.tsx:231` | 删除 | DELETE | DELETE `/etlScoreTarget` | N |
| businessIssue | `settings/businessIssues/details/IssueDetailsPage.tsx:154` / `:162` | Approve / Reject | CREATE_OR_UPDATE | POST `/businessIssues/check` | N |
| businessIssue | `settings/businessIssues/add/IssueAddPage.tsx:269`、`:218` | 新建 Issue | CREATE | POST `/businessIssues` | Y |
| peerGroup | `settings/peerGroupManagement/PeerGroupManagementPage.tsx:352`、`:390`；`detail/PeerGroupDetailPage.tsx:431`（×3） | Add Peer Group | CREATE | POST `/colleague/groups` | N |
| peerGroup | `PeerGroupManagementPage.tsx:296`；`PeerGroupDetailPage.tsx:399`（×2） | 编辑 | UPDATE | — | N |
| peerGroup | `settings/peerGroupManagement/components/PeerGroupModal.tsx:397` | 保存 | CREATE_OR_UPDATE | POST `/colleague/groups` | N |
| peerGroup | `PeerGroupModal.tsx:411`、`:459`（×2） | Delete Peer Group | DELETE | DELETE `/colleague/groups/{id}` | N |

## erlConfig（ERL 题库与维度配置，仅管理端）

| 页面 / 组件 file:line | 按钮 / 入口 | 动作 | 后端接口 |
|---|---|---|---|
| `exitReadiness/configuration/ConfigurationPage.tsx:317` → `components/QuestionForm.tsx:125` | 新增题目 / 保存 | CREATE | `createErlQuestion` |
| `exitReadiness/configuration/components/QuestionBandGroup.tsx:175` → `QuestionForm.tsx:125` | 编辑题目 | UPDATE | `updateErlQuestion` |
| `ConfigurationPage.tsx:165-183` | 删除题目 | DELETE | `deleteErlQuestion` |
| `ConfigurationPage.tsx:331`（确认框 `:130`、`:227`） | 发布 / 排序 | CREATE_OR_UPDATE / UPDATE | `publishErlQuestions`、`reorderErlQuestions` |
| `exitReadiness/configuration/components/DimensionConfigForm.tsx:249-253` / `:339` / `:143` | 新增 / 编辑 / 移除维度 | CREATE_OR_UPDATE | 随保存整套提交 |
| `DimensionConfigForm.tsx:217`、`:319`（×2） | 保存维度配置 | CREATE_OR_UPDATE | `saveErlDimensionConfig` |

## erl（ERL 填报、基准、差距分析）

接口 URL 大多在 `src/services/api/exitReadiness/erlApi.ts` 里拼出来。

| 页面 / 组件 file:line | 按钮 / 入口 | 动作 | 后端接口 | 共用 |
|---|---|---|---|---|
| `exitReadiness/benchmark/BenchmarkPage.tsx:128`；`scoreDetails/components/BenchmarkPanel.tsx:93`；`benchmark/add/BenchmarkAddPage.tsx:360-362`（×3） | 新增基准 / Save Record | CREATE | `saveErlBenchmark` | N |
| `exitReadiness/dimension/DimensionPage.tsx:194-195`；`scoreDetails/components/DimensionQuestionsCard.tsx:116`（×2） | 新建评估 | CREATE_OR_UPDATE | 进入填报 | Y |
| `exitReadiness/assessment/AssessmentPage.tsx:554-561` / `:563-570` | Save Draft / Submit | CREATE_OR_UPDATE | `saveErlDraft`、`submitErlAssessment` | Y |
| `AssessmentPage.tsx:409-416` | Discard Draft | DELETE | `deleteErlDraft` | Y |
| `exitReadiness/components/AttachmentUploader.tsx:140` | 上传 / 删除附件 | CREATE_OR_UPDATE / DELETE | 随草稿保存、`deleteErlAttachment` | Y |
| `companyOverview/home/components/ErlCard/ErlGapBlock.tsx:295`（`useErlCard.ts:260`） | 分享给创始人 / 生成差距分析 | CREATE_OR_UPDATE | `shareErlGapAnalysis`、`generateErlGapAnalysis` | Y（管理端分支） |

## benchmarkEntry、connector（Dev Support 平台页，仅管理端）

| 模块 | 页面 / 组件 file:line | 按钮 / 入口 | 动作 | 后端接口 |
|---|---|---|---|---|
| benchmarkEntry | `devSupport/benchmarkEntry/components/AddDetailRow.tsx:79-80`（现由 `isAdmin` 控制，`BenchmarkEntryPage.tsx:22`） | Add detail | CREATE | POST `/benchmark/details` |
| benchmarkEntry | `benchmarkEntry/components/DetailRow.tsx:258` / `:267-275` | 编辑 / 删除 | UPDATE / DELETE | PUT / DELETE `/benchmark/details/{id}` |
| benchmarkEntry | `benchmarkEntry/components/MetricRow.tsx:49-53` | 保存公式 | UPDATE | PUT `/benchmark/metrics/{id}/...` |
| connector | `devSupport/connectorsManagement/ConnectorsManagementPage.tsx:100` | Add New connector | CREATE | PUT `/thirdParty/dTool` |
| connector | `ConnectorsManagementPage.tsx:47`；`components/ToolSetting.tsx:172`、`:150`（×3） | 编辑 / 保存 / 上传 Logo | UPDATE | 同上 |
| connector | `ConnectorsManagementPage.tsx:50-55` | 删除 | DELETE | DELETE `/thirdParty/dTool` |

## 汇总

KPA 管理页上调用已不存在接口的约 9 处，以及重置密码的 2 处，已经从下表剔除。

| 模块 | 入口数（含重复） | 是否与公司端共用 |
|---|---|---|
| company | ~12 | 部分 |
| investment | ~5 | 否 |
| user | ~14 | 部分（公司设置里的成员管理共用） |
| companyFinancial | ~30 | 全部 |
| companyDocument | ~20 | 全部 |
| project | ~16 | 全部 |
| techStack | ~9 | 否 |
| kpa | ~4 | 全部 |
| kpaConfig | ~4 | 否 |
| scoreConfig | ~6 | 否 |
| financeScore | 1 | 否 |
| alert | 1 | 否 |
| portfolioGroup | ~6 | 否 |
| portfolio | ~7 | 否 |
| role | ~20 | 否 |
| indicator | ~4 | 否 |
| businessIssue | 3 | 1 处共用 |
| peerGroup | ~9 | 否 |
| erlConfig | ~8 | 否 |
| erl | ~10 | 大部分 |
| benchmarkEntry | ~4 | 否 |
| connector | ~5 | 否 |
| **合计** | **约 200 处（去重约 150）**，分布在约 75 个页面文件 | 约 85 处在共用组件里 |

另外还有约 12~15 个基础文件要改：
- 新增权限 hook 和守卫组件；
- `src/models/login.ts`、`src/layouts/BasicLayout.tsx`；
- `src/utils/utils.ts` 的 `clearUserInfo`；
- `src/utils/request.ts`，处理 403；
- `config/routes.ts`、`src/pages/devSupport/_shell/DevSupportShell.tsx`；
- 新增 service 文件；
- 新页面目录，4~6 个文件；
- `src/pages/settings/profile/userChangePSD/UserChangePsdPage.tsx:77`，这里也会清登录态；
- 现在按功能名判断的 6 处，见设计方案 §10.4。

**前端合计约 90 个文件。**
