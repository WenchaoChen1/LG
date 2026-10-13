# 附录 A：后端写接口 → 模块 × 动作映射

> 关联文档: [设计方案](./design-doc.md) · [附录 B：前端按钮清单](./frontend-button-map.md)

- 范围：`java/CIOaas-api/gstdev-cioaas-web` 全部 POST / PUT / DELETE 接口（177 个），加上 8 个会改数据的 GET，共 185 行。调研日期 2026-10-13（sprint121）。
- 结论：**143 个需要加权限声明，42 个豁免**。
- 路径都省略了上下文路径 `/web`，网关对外是 `/api/web/...`。
- 动作取值：
  - CREATE / UPDATE / DELETE；
  - CREATE_OR_UPDATE：新增和修改合一的保存接口、流程动作（提交、接受、发布、同步、分享等），有新增或修改任一权限即放行；
  - EXEMPT：不做权限检查，备注写明原因。
- 名称有歧义的接口都核对过 service 代码，结论写在备注里。

## 1. 模块清单（22 个）

| code | 页面上的名称 | 说明 | 覆盖的 Controller |
|---|---|---|---|
| company | Companies | 公司的新增、编辑、归档、停用，模块开关，公司阶段 | CompanyController（公司部分）、StageController |
| investment | Investments | 公司投资记录的录入和导入 | CompanyController（`/invite/investment*`） |
| companyFinancial | Company Financials | 财务录入、编辑、预测、审阅；QuickBooks 设置与科目映射；AI 财务解析与冲突处理；公司财务设置（收入确认、记账方法、币种） | FinancialStatements、FinancialEditing、FinanceManualData、FinancialForecastData、FinancialForecastHistory、FinancialSetting（`/companyQuickbooks`）、FinancialDataConflict、FinancialNormalized、Quickbooks、AiFinancialExtraction、CompanyController（财务设置三个接口） |
| companyDocument | Documents | 公司文档、资料、文件删除 | DocumentController、CompanyDocumentationController、FileController |
| project | Projects | 产品/项目的增删改、归档、成员；项目技术栈；项目连接器配置与同步；产品权重 | ProjectController、TechStackController、ThirdPartyController（`/connection`）、ScoreController（`saveProjectWeight`） |
| techStack | Tech Stack Management | 平台技术栈配置（层、分类、元素、权重） | TechStackManagementController |
| kpa | Company KPA | 公司 KPA 评审 | KpaBusinessController |
| kpaConfig | KPA Configuration | KPA 配置 | KpaManagementController |
| scoreConfig | SDP Score Calculation Setup | SDP 评分配置及子项 | ScoreController（`saveScoreConfiguration`）、EtlScoreTypeController |
| financeScore | Financial Health Score Calculation | 财务健康分配置 | FinanceScoreLevelController |
| alert | Alert Configuration | 告警阈值 | EtlConfigController |
| portfolioGroup | Portfolio Group Management | Portfolio 分组（organization 表）及其菜单 | OrganizationController |
| portfolio | Portfolio Management | Portfolio（companyGroup 表）及公司归属 | CompanyGroupController |
| user | User Management | 管理端用户、公司成员、邀请、团队分组 | UserController、OrganizeController、ROrganizeUserController |
| role | Roles & Permissions | 角色、组织角色、公司角色、菜单与功能、本次新增的权限分配 | RoleController、ROrganizationRoleController、MenuController、新增的权限管理接口 |
| indicator | Indicator | 指标 | EtlScoreTargetController |
| businessIssue | Business Issues | 业务问题的提交和审核 | BusinessIssuesController |
| peerGroup | Peer Group Management | 同行组 | ColleagueCompanyController |
| benchmarkEntry | Benchmark Entry | Benchmark 数据录入 | BenchmarkController |
| erl | Exit Readiness | ERL 问卷填报、基准记录、差距分析 | ErlAssessmentController、ErlBenchmarkController、ErlGapAnalysisController |
| erlConfig | ERL Configuration | ERL 题库与维度配置、发布 | ErlQuestionConfigController、ErlDimensionConfigController |
| connector | Connectors Management | 连接器工具目录（dTool） | ThirdPartyController（`/dTool`） |

另有几点说明：

- **"Portfolio" 两个模块的命名是交叉的**：`OrganizationController` 对应页面 "Portfolio Group Management"，`CompanyGroupController` 对应页面 "Portfolio Management"。模块名跟页面名走。
- **没有建的模块**：
  - Pricing Tier：菜单行在，但前端入口已注释，后端只有 GET；
  - Sprint Retrospective：菜单行在，但没有路由，也没有后端接口。
- **只有读接口、不需要声明的 Controller**：ErlCard、ErlDimension、ErlPortfolio、Dictionary、Folder、Log、CompanySubscription、PortfolioBenchmark、IndexValidation、AuthCheck（Python 调来校验 token）、Health（匿名）。

## 2. 接口映射（185 行）

| 模块 | Controller.方法 | HTTP + 路径 | 动作 | 备注 |
|---|---|---|---|---|
| company | CompanyController.getAiDetail | `POST /invite/aiDetail` | EXEMPT | 查询 |
| company | CompanyController.delete | `PUT /invite/delete/{companyId}` | DELETE | 用 PUT 做的软删除 |
| company | CompanyController.archiveCompany | `POST /invite/archiveCompany` | UPDATE | 归档 / 取消归档 |
| company | CompanyController.addWithoutEmail | `POST /invite/addWithoutEmail` | CREATE_OR_UPDATE | 按 id 区分新增或编辑 |
| company | CompanyController.updateModulesSettings | `POST /invite/updateModulesSettings` | UPDATE | FI/DI 开关与权重 |
| company | CompanyController.addCompanyAndSetStage | `POST /invite/addCompanyAndSetStage` | CREATE | |
| company | CompanyController.portfolioCapacitySave | `POST /invite/portfolioCapacitySave` | EXEMPT | 个人的列偏好设置 |
| company | StageController.saveCompanyStage | `POST /stage/saveCompanyStage` | CREATE_OR_UPDATE | Company Settings 的 Stage 页 |
| investment | CompanyController.investmentListView | `POST /invite/investment` | EXEMPT | 查询 |
| investment | CompanyController.investmentSave | `POST /invite/investmentSave` | CREATE_OR_UPDATE | 按 id 区分新增或编辑 |
| investment | CompanyController.upload | `POST /invite/investmentUpload` | CREATE | 导入 |
| investment | CompanyController.investmentExport | `POST /invite/investmentExport` | EXEMPT | 查询 / 导出 |
| companyFinancial | AiFinancialExtractionController.presignedUploads | `POST /ai/financialExtraction/tasks/getUploadUrl` | CREATE | AI 上传的第一步 |
| companyFinancial | AiFinancialExtractionController.commitUpload | `POST /ai/financialExtraction/tasks/commitUpload` | CREATE | 建任务并提交解析 |
| companyFinancial | AiFinancialExtractionController.batchDeleteByIds | `POST /ai/financialExtraction/files/batchDeleteByIds` | DELETE | 用 POST 做的删除 |
| companyFinancial | AiFinancialExtractionController.batchDelete | `POST /ai/financialExtraction/tasks/{taskId}/batchDelete` | DELETE | 用 POST 做的删除 |
| companyFinancial | AiFinancialExtractionController.replace | `POST /ai/financialExtraction/tasks/{taskId}/file/replace` | UPDATE | |
| companyFinancial | AiFinancialExtractionController.uploadComplete | `POST /ai/financialExtraction/tasks/{taskId}/uploadComplete` | CREATE_OR_UPDATE | 流程：提交 |
| companyFinancial | FinancialDataConflictController.verify | `POST /financial-data-conflict/tasks/{taskId}/verify` | CREATE_OR_UPDATE | 叫 verify，实际会改冲突记录并推进任务状态 |
| companyFinancial | FinancialDataConflictController.completeTask | `POST /financial-data-conflict/tasks/{taskId}/complete` | CREATE_OR_UPDATE | 解决冲突并写入财务数据 |
| companyFinancial | FinanceManualDataController.save | `POST /financeManualData` | CREATE_OR_UPDATE | 两端都调 |
| companyFinancial | FinanceManualDataController.deleteFile | `DELETE /financeManualData/deleteFile` | DELETE | |
| companyFinancial | FinanceManualDataController.uploadFile | `POST /financeManualData/uploadFile` | CREATE | |
| companyFinancial | FinanceManualDataController.review | `POST /financeManualData/reviewFromPage` | CREATE_OR_UPDATE | **只有创始人调**：审阅通过 / 驳回 |
| companyFinancial | FinanceManualDataController.review | `GET /financeManualData/review` | CREATE_OR_UPDATE | **会改数据的 GET**，只有创始人调（邮件链接） |
| companyFinancial | FinancialEditingController.init | `POST /financialEditing/init` | CREATE_OR_UPDATE | 进入编辑态并写快照 |
| companyFinancial | FinancialEditingController.save | `POST /financialEditing/save` | CREATE_OR_UPDATE | 保存单月 |
| companyFinancial | FinancialEditingController.oneClickCalculation | `POST /financialEditing/oneClickCalculation` | CREATE_OR_UPDATE | Quick-Fill / Set-to-Zero / Distribute OE |
| companyFinancial | FinancialEditingController.tables | `POST /financialEditing/submit` | CREATE_OR_UPDATE | 流程：提交；两端都调 |
| companyFinancial | FinancialEditingController.cancel | `POST /financialEditing/cancel` | CREATE_OR_UPDATE | 流程：放弃编辑 |
| companyFinancial | FinancialEditingController.uploadDocument | `POST /financialEditing/document/upload` | CREATE | |
| companyFinancial | FinancialEditingController.deleteDocument | `DELETE /financialEditing/document` | DELETE | |
| companyFinancial | FinancialEditingController.dismissBenchmarkBanner | `POST /financialEditing/banner/benchmark/dismiss` | EXEMPT | 个人关闭提示 |
| companyFinancial | FinancialEditingController.closeNewForecast | `GET /financialEditing/alert/closeNewForecast` | EXEMPT | 会改数据的 GET，但只是个人关闭提示 |
| companyFinancial | FinancialForecastDataController.saveCache | `POST /financialForecastData/cache` | CREATE_OR_UPDATE | 草稿缓存 |
| companyFinancial | FinancialForecastDataController.submit | `POST /financialForecastData/submit` | CREATE_OR_UPDATE | 流程：提交 |
| companyFinancial | FinancialForecastDataController.oneClickCalculation | `POST /financialForecastData/oneClickCalculation` | CREATE_OR_UPDATE | 生成 OE / Cash |
| companyFinancial | FinancialForecastHistoryController.updateVersion | `PUT /financialForecastHistory/version` | UPDATE | 版本名、备注 |
| companyFinancial | FinancialForecastHistoryController.deleteVersion | `DELETE /financialForecastHistory/version` | DELETE | |
| companyFinancial | FinancialForecastHistoryController.saveAcceptForecastCache | `POST /financialForecastHistory/acceptCommitted/cache` | CREATE_OR_UPDATE | |
| companyFinancial | FinancialForecastHistoryController.acceptCommitted | `POST /financialForecastHistory/acceptCommitted` | CREATE_OR_UPDATE | 流程：接受 |
| companyFinancial | FinancialForecastHistoryController.closeNewForecast | `GET /financialForecastHistory/closeNewForecast` | EXEMPT | 会改数据的 GET，但只是个人关闭提示 |
| companyFinancial | FinancialNormalizedController.getChatSummary | `POST /financialNormalized/chatSummary` | EXEMPT | 查询 |
| companyFinancial | FinancialNormalizedController.getMetricTrace | `POST /financialNormalized/metricTrace` | EXEMPT | 查询 |
| companyFinancial | FinancialSettingController.save | `POST /companyQuickbooks` | CREATE_OR_UPDATE | QuickBooks 设置 |
| companyFinancial | FinancialSettingController.updatePayroll | `POST /companyQuickbooks/updatePayroll` | UPDATE | |
| companyFinancial | FinancialSettingController.disconnect | `POST /companyQuickbooks/disconnect` | UPDATE | 只改状态，不删行 |
| companyFinancial | FinancialSettingController.companyIssues | `POST /companyQuickbooks/companyIssues` | EXEMPT | 查询 |
| companyFinancial | FinancialSettingController.conversionMode | `POST /companyQuickbooks/conversionMode` | UPDATE | |
| companyFinancial | FinancialSettingController.financialDataView | `POST /companyQuickbooks/financialDataView` | EXEMPT | 查询 |
| companyFinancial | FinancialSettingController.refresh | `GET /companyQuickbooks/refresh` | CREATE_OR_UPDATE | **会改数据的 GET**：发 QBO 映射和同步消息 |
| companyFinancial | FinancialSettingController.connect | `GET /companyQuickbooks/connect` | EXEMPT | 只记一条点击日志 |
| companyFinancial | FinancialSettingController.findById | `GET /companyQuickbooks` | EXEMPT | 匿名：QBO OAuth 回调 |
| companyFinancial | FinancialSettingController.authorization | `GET /companyQuickbooks/authorization` | EXEMPT | 匿名：发起 QBO OAuth |
| companyFinancial | FinancialStatementsController.financialEntrySubmit | `POST /financialStatements/financialEntrySubmit` | CREATE_OR_UPDATE | 流程：提交；两端都调 |
| companyFinancial | FinancialStatementsController.comment | `POST /financialStatements/comment` | CREATE | 给 QBO 数据变更写评论 |
| companyFinancial | FinancialStatementsController.acceptChanges | `POST /financialStatements/acceptChanges` | CREATE_OR_UPDATE | 流程：接受 |
| companyFinancial | FinancialStatementsController.allAccept | `POST /financialStatements/allAccept` | CREATE_OR_UPDATE | 流程：全部接受 |
| companyFinancial | QuickbooksController.setAccount | `POST /quickbooks/setAccount` | CREATE_OR_UPDATE | 科目映射批量保存 |
| companyFinancial | CompanyController.revenueRecognitionSet | `PUT /invite/revenueRecognitionSet` | UPDATE | |
| companyFinancial | CompanyController.accountMethodGetSet | `PUT /invite/accountMethodGetSet` | UPDATE | 名字带 Get，实际是设置 |
| companyFinancial | CompanyController.currencySet | `PUT /invite/currencySave` | UPDATE | |
| companyDocument | CompanyDocumentationController.getDocumentationList | `POST /companyDocumentation/getDocumentationList` | EXEMPT | 查询 |
| companyDocument | CompanyDocumentationController.addDocumentation | `POST /companyDocumentation/addDocumentation` | CREATE | 投资页也会调 |
| companyDocument | CompanyDocumentationController.deleteDocumentByDocumentId | `DELETE /companyDocumentation/deleteDocumentByDocumentId` | DELETE | |
| companyDocument | DocumentController.getAllDocumentsByCompanyId | `POST /document/getAllDocumentsByCompanyId` | EXEMPT | 查询 |
| companyDocument | DocumentController.deleteDocumentByDocumentId | `DELETE /document/deleteDocumentByDocumentId` | DELETE | |
| companyDocument | DocumentController.addDocuments | `POST /document/addDocuments` | CREATE | |
| companyDocument | DocumentController.shareDocumentEmail | `POST /document/shareDocumentEmail` | CREATE_OR_UPDATE | 流程：邮件外发分享 |
| companyDocument | FileController.delete | `DELETE /storage/files/{id}` | DELETE | 通用文件删除，文档、ERL、AI 页面都会调；第一期统一归 companyDocument |
| companyDocument | FileController.presign | `POST /storage/uploads/presign` | EXEMPT | 基础设施：通用预签名；真正的新增在使用 fileId 的业务接口上检查 |
| companyDocument | FileController.verify | `POST /storage/uploads/{id}/verify` | EXEMPT | 基础设施：确认上传完成 |
| companyDocument | FileController.verifyS3 | `POST /storage/files/verifyS3` | EXEMPT | 查询 |
| project | ProjectController.saveAndAssign | `POST /project/saveAndAssign` | CREATE_OR_UPDATE | 新增或编辑项目 |
| project | ProjectController.archiveProjectSetUp | `POST /project/archiveProject` | UPDATE | 归档 / 恢复 |
| project | ProjectController.delete | `PUT /project/delete/{projectId}` | DELETE | 用 PUT 做的软删除 |
| project | ProjectController.inviteUserToProject | `POST /project/inviteuser` | CREATE_OR_UPDATE | 邀请项目成员或改成员信息 |
| project | ProjectController.saveBigDataModule | `POST /project/saveBigDataModule` | UPDATE | |
| project | ProjectController.editProject | `POST /project/editProject` | CREATE_OR_UPDATE | |
| project | ScoreController.saveProjectWeight | `POST /score/saveProjectWeight` | CREATE_OR_UPDATE | 产品权重 |
| project | TechStackController.updateTechStackElement | `POST /techStack/updateTechStackElement` | UPDATE | service 内按 roleType 分支，两端都调 |
| project | ThirdPartyController.createConnection | `POST /thirdParty/connection` | CREATE | 项目连接器配置 |
| project | ThirdPartyController.updateConnection | `PUT /thirdParty/connection` | UPDATE | |
| project | ThirdPartyController.deleteConnection | `DELETE /thirdParty/connection` | DELETE | |
| project | ThirdPartyController.syncConnection | `POST /thirdParty/connection/{id}/sync` | CREATE_OR_UPDATE | 流程：手动同步 |
| techStack | TechStackManagementController.saveLayer | `POST /techStackManagement/layer` | CREATE_OR_UPDATE | 已核实：id 为空则新增 |
| techStack | TechStackManagementController.saveTechCategoryWeight | `POST /techStackManagement/saveTechCategoryWeight` | CREATE_OR_UPDATE | |
| techStack | TechStackManagementController.saveTechStackElements | `POST /techStackManagement/saveTechStackElements` | CREATE_OR_UPDATE | |
| techStack | TechStackManagementController.saveTechStackElement | `POST /techStackManagement/saveTechStackElement` | CREATE_OR_UPDATE | 已核实是新增或修改合一 |
| techStack | TechStackManagementController.updateTechCategory | `POST /techStackManagement/updateTechCategory` | UPDATE | |
| techStack | TechStackManagementController.deleteElement | `PUT /techStackManagement/deleteElement` | DELETE | 用 PUT 做的软删除 |
| kpa | KpaBusinessController.addKpaReview | `POST /kpaBusiness/addKpaReview` | CREATE | |
| kpa | KpaBusinessController.editKpaReview | `PUT /kpaBusiness/editKpaReview` | UPDATE | |
| kpa | KpaBusinessController.delKpaReview | `DELETE /kpaBusiness/delKpaReview` | DELETE | |
| kpaConfig | KpaManagementController.updateKpaLevel | `POST /kpaManagement/updateKpaLevel` | UPDATE | |
| kpaConfig | KpaCategoryController.kpaCategoryGotIt | `POST /tools/KpaCategoryGotIt` | EXEMPT | "Got it" 确认，只记提醒时间 |
| scoreConfig | ScoreController.saveScoreConfiguration | `POST /score/saveScoreConfiguration` | CREATE_OR_UPDATE | |
| scoreConfig | EtlScoreTypeController.save | `POST /etlScoreType` | CREATE | 和 PUT 成对，这里的 save 就是新增 |
| scoreConfig | EtlScoreTypeController.modify | `PUT /etlScoreType` | UPDATE | |
| scoreConfig | EtlScoreTypeController.deleteById | `DELETE /etlScoreType` | DELETE | |
| financeScore | FinanceScoreLevelController.saveFinanceScoreSetup | `POST /financeScoreLevel/saveFinanceScoreSetup` | CREATE_OR_UPDATE | |
| alert | EtlConfigController.modify | `PUT /EtlConfig` | UPDATE | |
| portfolioGroup | OrganizationController.save | `POST /organization` | CREATE | |
| portfolioGroup | OrganizationController.modify | `PUT /organization` | UPDATE | |
| portfolioGroup | OrganizationController.deleteById | `DELETE /organization` | DELETE | |
| portfolioGroup | OrganizationController.modifyOrganizationMenu | `PUT /organization/modifyOrganizationMenu` | UPDATE | 同时会删角色-菜单关联 |
| portfolio | CompanyGroupController.save | `POST /companyGroup` | CREATE | 和 PUT 成对，这里的 save 就是新增 |
| portfolio | CompanyGroupController.modify | `PUT /companyGroup` | UPDATE | |
| portfolio | CompanyGroupController.deleteById | `DELETE /companyGroup` | DELETE | |
| portfolio | CompanyGroupController.delete | `DELETE /companyGroup/delete` | UPDATE | 解除某公司的全部 Portfolio 归属，也可以按 DELETE 处理 |
| portfolio | CompanyGroupController.relevance | `POST /companyGroup/relevance` | UPDATE | 重新关联公司和 Portfolio |
| portfolio | CompanyGroupController.remove | `DELETE /companyGroup/remove` | UPDATE | 从某个 Portfolio 移出一家公司 |
| portfolio | CompanyGroupController.status | `POST /companyGroup/status` | UPDATE | 归属状态 |
| user | UserController.create | `POST /users` | CREATE | 见设计方案 §13：P0 问题的关系 |
| user | UserController.adminUser | `POST /users/adminUser` | CREATE_OR_UPDATE | 已核实是新增或修改合一 |
| user | UserController.clientUser | `POST /users/clientUser` | CREATE_OR_UPDATE | |
| user | UserController.inviteUser | `POST /users/invite` | CREATE | |
| user | UserController.inviteAgain | `GET /users/inviteAgain` | CREATE_OR_UPDATE | **会改数据的 GET**：重发邀请邮件 |
| user | UserController.update | `PUT /users/{userId}` | UPDATE | 注册、选公司流程里用户也会改自己，**改自己时放行** |
| user | UserController.resetPassword | `PUT /users/passwordReset/{userId}` | UPDATE | 管理员重置密码 |
| user | UserController.delete | `PUT /users/delete/{userId}` | DELETE | 用 PUT 做的软删除 |
| user | UserController.updateProjects | `POST /users/updateProjects` | UPDATE | |
| user | OrganizeController.save | `POST /organize` | CREATE | 公司设置里的团队分组 |
| user | OrganizeController.modify | `PUT /organize` | UPDATE | |
| user | OrganizeController.deleteById | `DELETE /organize` | DELETE | |
| user | ROrganizeUserController.saveOrganizeAndUserIds | `POST /rOrganizeUser/saveOrganizeAndUserIds` | CREATE_OR_UPDATE | 团队分组成员 |
| user | UserController.profile | `PUT /users/profile` | EXEMPT | 个人资料；**id 取自请求体、没和调用者绑定（越权）** |
| user | UserController.acceptInvite | `POST /users/activate` | EXEMPT | 被邀请人激活 |
| user | UserController.logout | `DELETE /users/logout` | EXEMPT | 匿名 |
| user | UserController.sendEmailToReset | `POST /users/sendEmailToReset` | EXEMPT | 匿名 |
| user | UserController.changePassword | `POST /users/changePassword` | EXEMPT | 匿名（重置链接） |
| user | UserController.changePasswordWhenLogin | `POST /users/changePasswordWhenLogin` | EXEMPT | 匿名 |
| user | UserController.select | `POST /users/select` | EXEMPT | 登录时选公司 |
| user | UserController.switchView | `POST /users/switchView` | EXEMPT | 个人设置 |
| user | UserController.switchCurrency | `POST /users/switchCurrency` | EXEMPT | 个人设置 |
| user | UserController.checkPasswordByUserId | `POST /users/checkPasswordByUserId` | EXEMPT | 个人；id 取自请求体（越权） |
| user | UserController.changePasswordByUserId | `PUT /users/changePasswordByUserId` | EXEMPT | 个人；id 取自请求体（越权） |
| user | OAuthTokenController.token | `POST /oauth/token` | EXEMPT | 匿名登录 |
| user | OAuthTokenController.switchAccount | `POST /oauth/switch` | EXEMPT | 切换账号 |
| role | RoleController.saveRoleList | `POST /roles/saveRoleList` | CREATE_OR_UPDATE | |
| role | RoleController.saveRoleAndMenuList | `POST /roles/saveRoleAndMenuList` | CREATE_OR_UPDATE | |
| role | RoleController.addRole | `POST /roles/addRole` | CREATE_OR_UPDATE | 按 id 区分新增或编辑 |
| role | RoleController.delete | `DELETE /roles/deleteRole` | DELETE | |
| role | ROrganizationRoleController.addOrganizationRole | `POST /rOrganizationRole/addOrganizationRole` | CREATE_OR_UPDATE | 按 id 区分新增或编辑 |
| role | ROrganizationRoleController.addCompanyRole | `POST /rOrganizationRole/addCompanyRole` | CREATE_OR_UPDATE | |
| role | ROrganizationRoleController.deleteOrganizationRole | `DELETE /rOrganizationRole/deleteOrganizationRole` | DELETE | |
| role | ROrganizationRoleController.modifyOrganizationRoleMenu | `PUT /rOrganizationRole/modifyOrganizationRoleMenu` | UPDATE | |
| role | MenuController.getMenuTreeByRoleId | `POST /menus/getMenuTreeByRoleId` | EXEMPT | 查询 |
| role | MenuController.create | `POST /menus/addMenu` | CREATE_OR_UPDATE | 新增或修改菜单 / 功能 |
| role | MenuController.delete | `DELETE /menus/deleteMenu` | DELETE | |
| indicator | EtlScoreTargetController.save | `POST /etlScoreTarget` | CREATE | |
| indicator | EtlScoreTargetController.modify | `PUT /etlScoreTarget` | UPDATE | |
| indicator | EtlScoreTargetController.deleteById | `DELETE /etlScoreTarget` | DELETE | |
| indicator | IndexValidationController.getValidationData | `POST /indicator/validation/list` | EXEMPT | 查询 |
| businessIssue | BusinessIssuesController.save | `POST /businessIssues` | CREATE | 两端都能提交 |
| businessIssue | BusinessIssuesController.admin | `POST /businessIssues/admin` | EXEMPT | 查询 |
| businessIssue | BusinessIssuesController.client | `POST /businessIssues/client` | EXEMPT | 查询 |
| businessIssue | BusinessIssuesController.check | `POST /businessIssues/check` | UPDATE | 管理端审核通过 / 驳回，名字叫 check 有误导 |
| peerGroup | PortfolioBenchmarkController.getSnapshot | `POST /portfolio-benchmark/snapshot` | EXEMPT | 查询 |
| peerGroup | PortfolioBenchmarkController.getTrend | `POST /portfolio-benchmark/trend` | EXEMPT | 查询 |
| peerGroup | ColleagueCompanyController.saveGroup | `POST /colleague/groups` | CREATE_OR_UPDATE | 已核实是新增或修改合一 |
| peerGroup | ColleagueCompanyController.deleteGroup | `DELETE /colleague/groups/{groupId}` | DELETE | |
| peerGroup | BenchmarkNotificationController.dismiss | `POST /benchmark-notification/dismiss` | EXEMPT | 个人关闭提示 |
| peerGroup | BenchmarkNotifyAlertController.delete | `DELETE /benchmark/notify-alerts/dismiss/{id}` | EXEMPT | 个人关闭提示 |
| benchmarkEntry | BenchmarkController.addDetail | `POST /benchmark/details` | CREATE | |
| benchmarkEntry | BenchmarkController.updateDetail | `PUT /benchmark/details/{detailId}` | UPDATE | |
| benchmarkEntry | BenchmarkController.deleteDetail | `DELETE /benchmark/details/{detailId}` | DELETE | |
| benchmarkEntry | BenchmarkController.updateFormula | `PUT /benchmark/metrics/{metricId}/formula` | UPDATE | |
| erl | ErlAssessmentController.saveDraft | `POST /erl/assessment/draft` | CREATE_OR_UPDATE | 两端都调（GSV 端 / 创始人端） |
| erl | ErlAssessmentController.previewProgress | `POST /erl/assessment/progress` | EXEMPT | 查询（只预览、不落库） |
| erl | ErlAssessmentController.submit | `POST /erl/assessment/submit` | CREATE_OR_UPDATE | 流程：提交；两端都调 |
| erl | ErlAssessmentController.discardDraft | `DELETE /erl/assessment/draft` | DELETE | 两端都调 |
| erl | ErlAssessmentController.deleteAttachment | `DELETE /erl/assessment/attachment/{id}` | DELETE | 两端都调 |
| erl | ErlBenchmarkController.createBenchmark | `POST /erl/benchmark` | CREATE | 只有管理端（service 已有 `assertAdminEnd`） |
| erl | ErlGapAnalysisController.generateGapAnalysis | `POST /erl/gapAnalysis/generate` | CREATE_OR_UPDATE | 只有管理端，会触发 LLM |
| erl | ErlGapAnalysisController.shareGapAnalysis | `POST /erl/gapAnalysis/share` | CREATE_OR_UPDATE | 只有管理端，分享给创始人 |
| erlConfig | ErlDimensionConfigController.saveConfig | `PUT /erl/dimension/config` | CREATE_OR_UPDATE | 整套替换 |
| erlConfig | ErlQuestionConfigController.createQuestion | `POST /erl/question` | CREATE | |
| erlConfig | ErlQuestionConfigController.updateQuestion | `PUT /erl/question/{questionKey}` | UPDATE | |
| erlConfig | ErlQuestionConfigController.deleteQuestion | `DELETE /erl/question/{questionKey}` | DELETE | |
| erlConfig | ErlQuestionConfigController.reorderQuestions | `PUT /erl/question/reorder` | UPDATE | |
| erlConfig | ErlQuestionConfigController.publishQuestions | `POST /erl/question/publish` | CREATE_OR_UPDATE | 流程：发布 |
| connector | ThirdPartyController.createDTool | `POST /thirdParty/dTool` | CREATE | |
| connector | ThirdPartyController.updateDTool | `PUT /thirdParty/dTool` | UPDATE | |
| connector | ThirdPartyController.deleteDTool | `DELETE /thirdParty/dTool` | DELETE | |

## 3. 汇总

| 模块 | CREATE | UPDATE | DELETE | CREATE_OR_UPDATE | EXEMPT | 行数 | 需声明 |
|---|---|---|---|---|---|---|---|
| company | 1 | 2 | 1 | 2 | 2 | 8 | 6 |
| investment | 1 | 0 | 0 | 1 | 2 | 4 | 2 |
| companyFinancial | 5 | 8 | 5 | 22 | 10 | 50 | 40 |
| companyDocument | 2 | 0 | 3 | 1 | 5 | 11 | 6 |
| project | 1 | 4 | 2 | 5 | 0 | 12 | 12 |
| techStack | 0 | 1 | 1 | 4 | 0 | 6 | 6 |
| kpa | 1 | 1 | 1 | 0 | 0 | 3 | 3 |
| kpaConfig | 0 | 1 | 0 | 0 | 1 | 2 | 1 |
| scoreConfig | 1 | 1 | 1 | 1 | 0 | 4 | 4 |
| financeScore | 0 | 0 | 0 | 1 | 0 | 1 | 1 |
| alert | 0 | 1 | 0 | 0 | 0 | 1 | 1 |
| portfolioGroup | 1 | 2 | 1 | 0 | 0 | 4 | 4 |
| portfolio | 1 | 5 | 1 | 0 | 0 | 7 | 7 |
| user | 3 | 4 | 2 | 4 | 13 | 26 | 13 |
| role | 0 | 1 | 3 | 6 | 1 | 11 | 10 |
| indicator | 1 | 1 | 1 | 0 | 1 | 4 | 3 |
| businessIssue | 1 | 1 | 0 | 0 | 2 | 4 | 2 |
| peerGroup | 0 | 0 | 1 | 1 | 4 | 6 | 2 |
| benchmarkEntry | 1 | 2 | 1 | 0 | 0 | 4 | 4 |
| erl | 1 | 0 | 2 | 4 | 1 | 8 | 7 |
| erlConfig | 1 | 2 | 1 | 2 | 0 | 6 | 6 |
| connector | 1 | 1 | 1 | 0 | 0 | 3 | 3 |
| **合计** | **23** | **38** | **28** | **54** | **42** | **185** | **143** |

**42 个豁免的构成：**
- 19 个用 POST 做的查询；
- 9 个匿名接口；
- 9 个个人自助操作；
- 5 个个人关闭提示；
- 2 个存储基础设施。

## 4. 实施时要注意的点

1. **只有创始人调的接口**（`reviewFromPage`、`GET /financeManualData/review`）：第一期公司端跳过检查，所以它们实际不受影响，但仍然要加声明，守护测试才能通过。
2. **两端都调、service 里按 roleType 分支的接口**（`financialEntrySubmit`、`financialEditing/submit`、`updateTechStackElement`、ERL 填报等）：第一期只在 roleType=1 时检查，公司端行为不变。
3. **ERL 管理端专用的接口**：service 里已经有 `assertAdminEnd()`，新的权限检查是在它之外再加一层，不替换它。
4. **`PUT /users/{userId}`**：调用者改自己时直接放行；改别人才检查 `user:UPDATE`。
5. **`PUT /users/profile`、`/users/checkPasswordByUserId`、`/users/changePasswordByUserId`**：目标用户 id 取自请求体、没和调用者绑定，属于越权问题，不在本方案范围内，另行处理。
6. **`GET /erl/gapAnalysis`**：按读接口处理，没有列入上表。它在管理端遇到冷却窗口时会异步排队一次对账和 LLM 调用，属于系统行为，不是用户发起的写操作。
7. **前端在调、但后端已经不存在的接口**：`/document/multipleFilesUploadForKpaCategory`、`/document/deleteForKpaCategory`、`/tools/saveSingleKpaCategoryTool`、`/tools/saveKpaCategoryToolComment`。这些调用会 404，不在本表里；对应的前端按钮也不纳入隐藏，见附录 B。
