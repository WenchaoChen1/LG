# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Windows 开发环境

- PowerShell 脚本（`.ps1`）必须在 PowerShell 中执行，**不能**在 bash/Git Bash 中运行
- `conda` 命令在 bash 终端中不可用，需使用 Anaconda Prompt 或 PowerShell
- Java/Maven 输出可能出现 GBK 编码乱码，可在 PowerShell 中运行：`chcp 65001` 切换为 UTF-8
- 路径使用正斜杠（`/`）或双反斜杠（`\\`），避免在 bash 环境中混用

---

## 项目概览

本仓库是一个 monorepo，包含 CIOaaS（CIO as a Service）平台的五个子项目：

| 目录 | 技术栈 | 用途 |
|------|--------|------|
| `CIOaas-api/` | Java 17、Spring Boot 3.3、Spring Cloud | 后端 REST API + API 网关 |
| `CIOaas-web/` | React 16、Ant Design Pro、UmiJS 3、TypeScript | 前端单页应用 |
| `CIOaas-python/` | Python 3.12、FastAPI、FastMCP | 预测/财务 ML API + MCP 服务 |
| `cio-bigdata/` | Python 3.6、ETL 管道 | 数据集成（Redshift、QuickBooks 等） |
| `db-optimization/` | SQL | PostgreSQL 数据库优化脚本 |

## Git 分支规范

| 仓库 | 分支命名规律 | 示例 |
|------|-------------|------|
| `CIOaas-api` | `sprint/sprintXXX` | `sprint/sprint106` |
| `CIOaas-web` | `sprint_2026/sprintXXX/sprintXXX-release` | `sprint_2026/sprint106/sprint106-release` |
| `CIOaas-python` | 环境名称 | `test`、`staging` |

---

## CIOaas-api（Java Spring Boot）

### 构建与运行

```bash
# 在 CIOaas-api/ 根目录执行
mvn install

# 启动网关服务
.\run-gateway.ps1

# 启动 Web 服务（普通模式）
.\run-web.ps1

# 启动 Web 服务（调试模式，远程调试端口 5005）
.\run-web.ps1 -debug
```

手动启动：
```bash
cd gstdev-cioaas-web && mvn spring-boot:run
```

### 模块结构

- `gstdev-cioaas-common/` — 公共工具类、基础类、异常处理、持久化、AOP、配置
- `gstdev-cioaas-logging/` — 统一日志配置（支持 JSON/Logstash 格式）
- `gstdev-cioaas-web/` — 主应用：Controller、Service、Repository、业务逻辑
- `gstdev-cioaas-gateway/` — Spring Cloud Gateway：路由、过滤器、JWT 鉴权

### 核心架构

- **服务发现与配置中心**：Nacos（地址通过 `NACOS_SERVER_ADDR`，命名空间通过 `NACOS_NAMESPACE`），服务启动前通过 `bootstrap.yml` 从 Nacos 加载配置。
- **认证**：JWT（jjwt 0.12.6），在网关过滤器链中统一校验。
- **数据库**：PostgreSQL（主库，HikariCP 连接池）+ Amazon Redshift（分析/ETL）。
- **AWS 集成**：S3、SQS（java-dynamic-sqs-listener）、EventBridge Scheduler。
- **业务域**（位于 `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/`）：
  - `fi/` — 财务智能（Financial Intelligence）
  - `di/` — 数据智能（Data Intelligence）
  - `etl/` — ETL 管道
  - `index/` — 指标/KPI 校验
  - `airflow/` — Airflow DAG 集成
  - `oauth/` — OAuth2 认证流程
  - `scheduler/` — AWS EventBridge 调度
  - `sqs/` — SQS 消息处理
  - `storage/` — S3 文件存储
  - `system/` — 系统管理/配置
- 每个业务域遵循 `controller → service → repository → domain` 分层，并包含 `mapper/`（MapStruct）和 `contract/`（DTO）。

### 必要环境变量

在 `CIOaas-api/` 根目录创建 `.env` 文件：
- `NACOS_SERVER_ADDR`、`NACOS_NAMESPACE`、`NACOS_USERNAME`、`NACOS_PASSWORD`
- `CIOAAS_LOGGING_JSON_ENABLED`

### 受保护的本地配置文件

以下文件已设置 `skip-worktree`（本地修改不会被提交），并由 pre-push hook 保护——若这两个文件的变更出现在待推送的 commit 中，推送会被阻止并提醒：
- `gstdev-cioaas-gateway/src/main/resources/bootstrap.yml`
- `gstdev-cioaas-web/src/main/resources/bootstrap.yml`

若需临时恢复追踪：`git update-index --no-skip-worktree <文件路径>`

### 网关调试

- 健康检查：`http://localhost:9000/actuator/health`
- 查看所有路由：`http://localhost:9000/actuator/gateway/routes`
- Nacos 端口：HTTP 8848，gRPC 客户端 9848，gRPC 服务端 9849
- **路由顺序关键规则**：OAuth 路由必须配置在 `/api/**` 通配路由之前，否则 OAuth 请求会被错误拦截

### 部署到 AWS

```bash
cd /var/cioaas/api && ./deploy.sh
# 若 Docker 登录失败：./aws-ecr-login.sh
```

---

## CIOaas-web（React 前端）

### 开发与构建

```bash
cd CIOaas-web
cp .env.example .env   # 配置环境变量
npm install

npm run dev            # 启动开发服务器（端口 8004，dev 环境）
npm run start:test     # test 环境
npm run start:staging  # staging 环境
npm run start:uat      # UAT 环境

npm run build:prod     # 生产环境构建
npm run build:test     # test 环境构建
```

### 代码检查与测试

```bash
npm run lint           # ESLint + Stylelint + Prettier 检查
npm run lint:fix       # 自动修复 ESLint 问题
npm run test           # 运行测试（UmiJS test runner / Puppeteer）
npm run test:component # 仅运行组件测试
npm run tsc            # TypeScript 类型检查
```

### 部署环境

| 环境 | Git 分支 | CI/CD | 说明 |
|------|---------|-------|------|
| dev | dev | 手动部署 | 本地开发 |
| test | test | CircleCI 自动 | 测试环境 |
| uat | uat | CircleCI 自动 | UAT 验收 |
| staging | staging | CircleCI 自动 | 预发布 |
| prod | master | CircleCI 自动 | 生产环境 |

### 架构说明

基于 **Ant Design Pro v4**，使用 **UmiJS 3** 框架和 **dva** 状态管理：
- `src/pages/` — 路由级页面组件（每个功能一个目录）
- `src/components/` — 公共 UI 组件
- `src/services/` — API 请求函数（umi-request）
- `src/models/` — dva 全局状态模型
- `src/layouts/` — 布局组件
- `src/utils/` — 工具函数
- `config/routes.ts` — 所有路由定义
- `config/proxy.ts` — 开发代理目标（默认：`https://admin-test.lgpi.io`）

---

## CIOaas-python（FastAPI + MCP）

### 安装与运行

```bash
cd CIOaas-python
conda create -n cioaas-env python=3.12
conda activate cioaas-env
pip install -r requirements.txt      # 生产依赖
pip install -r requirements-dev.txt  # 开发依赖

# 启动服务（端口 8090）
cd source && uvicorn main:app --host 0.0.0.0 --port 8090
# 或通过启动脚本：
./start.sh
```

环境变量通过项目根目录的 `.env` 文件配置。关键变量：
- `LGPI_BEARER_TOKEN` — MCP 工具访问 LGPI Admin API 所需的 token
- `ENABLE_NEWRELIC=true` — 启用 New Relic APM 监控（`start.sh` 会按此变量决定是否加载 Agent）

### 架构说明

FastAPI 应用，包含两个主要 API 路由：
- `source/forecast/` — 时间序列预测引擎（`forecast_engine.py`）
- `source/financial/` — 财务数据接口
- `source/lgpi/` — LGPI Admin API 客户端（供 MCP 工具查询组织树和财务报表；Token 通过 `LGPI_BEARER_TOKEN` 环境变量配置）

**MCP 服务**（基于 FastMCP）挂载在 `/mcp`：
- `source/cioaas_mcp/mcp_tools.py` — 工具定义
- `source/cioaas_mcp/tools_registry.py` — 工具注册表
- 访问地址：`http://host:8090/mcp`（Streamable HTTP）

---

## cio-bigdata（ETL / 数据管道）

### 安装

```bash
cd cio-bigdata
pip install -r requirements-dev.txt
# 需要 Python 3.6
```

环境变量通过 `.env` 文件配置。

### 架构说明

数据集成管道按数据源组织在 `source/` 目录下：
- `awscost/`、`cloudwatch/`、`newrelic/`、`sonarqube/`、`circleci/`、`github/` — 云指标采集
- `quickbooks/` — QuickBooks 财务数据同步
- `etlscore/` — ETL 质量评分
- `ai/` — AI 辅助数据处理
- `intruder/` — 安全扫描数据

数据流向：源 API → 转换处理 → Amazon Redshift（通过 `pipelinewise-target-redshift`）。

---

## db-optimization（SQL 优化脚本）

`db-optimization/` 目录下按优先级组织的 PostgreSQL 数据库优化脚本：
- `P0_*` — 关键：敏感数据安全、主键、外键
- `P1_*` — 重要：枚举文档、数值字段单位、字段注释
- `P2_*` — 优化：索引、数据类型修正、约束与默认值
- `P3_*` — 增强：审计字段、大字段优化、命名规范
