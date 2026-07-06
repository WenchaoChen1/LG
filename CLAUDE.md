# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 必读子项目 CLAUDE.md（强制）

- 每次问答都必须先根据问题与扫描到的目录，读取并遵循以下子项目 `CLAUDE.md`：
  - `CIOaas-api/CLAUDE.md`
  - `CIOaas-web/CLAUDE.md`
  - `CIOaas-python/CLAUDE.md`
- 若问题涉及 `cio-bigdata/`，还须读取 `cio-bigdata/CLAUDE.md`。
- 若问题涉及在 `docs/` 下创建或修改功能文档，必须先读 `docs/CLAUDE.md`（定义 9 阶段文档流水线的目录结构、命名规则与禁止事项）。
- 各子项目另有 `standards/`（`architecture.md`、`coding.md`、`git.md`）；开发前按对应子项目 `CLAUDE.md` 中的「规范加载」执行，**不要**在根目录重复抄写这些规范。
- 若问题涉及多个子项目，按相关性依次读取；若无法确定，默认先读上述三个主工程 `CLAUDE.md` 再执行后续操作。

## 编码原则（强制）

> ⚠️ **项目规范（各子项目 `standards/`）始终最高优先级**：下述 YAGNI 是在规范框架内取最简实现，**不得**据此违反 `architecture.md` / `coding.md` 的分层、传输实体（Request/Response/DTO）、命名等强制约定。

在不违反规范的前提下，代码**简单直接表达功能**、不过度设计（YAGNI）：

- 优先最直接满足**当前需求**的实现，避免多余的抽象层 / 预留扩展点
- 不引入当前用不到的字段 / 参数 / 配置 / 模式（"以后可能要"不是理由）
- 复杂度按真实出现的需求再加，不为假想场景提前设计
- 每个流程用一个主方法按步骤顺序**平铺**调用子方法（读主方法即懂全流程），不要 a→b→c 多层嵌套调用链、长函数内嵌套闭包互相调用
- 重构/梳理代码默认在**原文件内**做（重组结构 + 删冗余），拆分出新文件须用户明确要求

## Git 规则（强制）

- **提交消息必须使用英文**：`git commit -m "English description"`
- **禁止自动推送远程**：`git push` 只有在用户明确说"推送"时才执行，提交（commit）不等于推送
- **提交前确认**：执行 `git add` 和 `git commit` 前需用户确认，不要自动批量提交

## 测试运行策略（强制）

- **改完代码不自动跑测试**：开发过程中每次对话修改代码后，**不要**自动执行测试，改为在回复末尾**提醒**"有改动待测试"（可附建议的测试范围/命令）。
- **收到命令再统一跑**：仅当开发人员明确下达"跑测试 / run test"等指令时，才统一运行测试（一次性覆盖本轮全部改动）。
- **例外**：与"跑测试"无关的轻量校验（如语法/导入冒烟、ruff/stylelint、`tsc`）可按需自行执行，不受此限。

## 执行策略（强制）

**Agent Teams 优先（= 能拆分并行就并行）**：只要任务能拆成 ≥ 2 个相互独立的子目标，就**必须**拆开用多个子代理（角色可分：PM / Architect / Dev / QA / Reviewer 等）并行执行，**不要**单 agent 顺序跑。

- **典型应用场景**：
  - 多步流水线任务（需求 → 设计 → 编码 → 审查 → 测试）
  - 跨子项目（Java + Python + Web 联动）的功能开发或排查
  - 代码审查（用多个 reviewer agent + 各语言审查 skill 并行）
  - 大范围调研（多个 explore agent 并行扫不同模块）
  - 头脑风暴 / 评估方案（多视角并行：安全 / 性能 / 可维护性 / UX 等）
- **执行方式**：用 `Agent` 工具派发并行子代理（`Explore` 调研 / `general-purpose` 多步任务 / `Plan` 设计方案 等），配合可用的 skills；相互独立的子任务在**同一条消息里一次性发起**以并发执行。
- **判断标准**：任务能拆成 ≥ 2 个独立子目标并行执行 → 拆开并行；否则单 agent。
- **可以单跑的简单任务**：读单文件、改一行配置、查端口状态、grep 一个符号等明确单步操作，不必上 multi-agent。

> 这是项目级强制规则，对所有 Claude Code 端（CLI / 桌面 / 网页 / IDE 插件）一致生效。

## Windows 开发环境

- PowerShell 脚本（`.ps1`）必须在 PowerShell 中执行，**不能**在 bash/Git Bash 中运行
- `conda` 命令在 bash 终端中不可用，需使用 Anaconda Prompt 或 PowerShell
- Java/Maven 输出可能出现 GBK 编码乱码，可在 PowerShell 中运行：`chcp 65001` 切换为 UTF-8
- 路径使用正斜杠（`/`）或双反斜杠（`\\`），避免在 bash 环境中混用

## 本地依赖环境（Docker）

`docker-compose.yml` 一键拉起 LG 全部依赖镜像（与全局 `D:\docker\compose.yml` 独立，端口可共存）：

```bash
cp .env.docker.example .env.docker           # 首次：复制并改密码（.env.docker 不提交，含 PG/MySQL/Redis 密码）
docker compose --env-file .env.docker up -d  # 默认起 postgres + mysql + nacos + redis
docker compose down                          # 停容器保留数据
docker compose down -v                       # 停容器并删卷（数据丢失！）
```

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| postgres | `pgvector/pgvector:pg15` | 5432 | 单实例双库隔离：业务库 `lg_test`（保持干净）+ RAG 库 `lg_rag`（**仅此库**装 pgvector + pg_trgm，由 `docker/postgres/init/` 初始化） |
| mysql | `nacos/nacos-mysql:5.7` | 3306 | Nacos 配置中心后端存储 |
| nacos | `nacos/nacos-server:v2.3.1` | 8848 / 9848 / 9849 | 配置中心 + 服务注册；控制台 `http://localhost:8848/nacos`（nacos/nacos） |
| redis | `redis:7-alpine` | 6379 | 缓存 / 会话 |

- 可选服务（默认注释）：`minio`（S3 本地替代）、`elasticsearch`（RAG 可选向量后端，默认 RAG 走 PG）。需要时取消对应 service + volume 注释。
- 衔接关系：Java 各模块 `bootstrap.yml` 从 `${NACOS_SERVER_ADDR}`（默认 `localhost:8848`）读配置；Python 各业务表**不在启动期自动建表**——DDL 走版本化迁移 `CIOaas-python/sql/migrations/{business,vector}/`（V001 为全量 baseline，向量库需 pgvector 扩展），由 `CIOaas-python/scripts/migrate.py` 部署期自动执行或人工执行（详见 CIOaas-python/CLAUDE.md「数据库版本迁移」）。

## 项目概览

本仓库是一个 monorepo。构建命令、模块结构、网关调试、分支命名等**均以各子目录 `CLAUDE.md` 与 `standards/` 为准**，此处仅作索引：

| 目录 | 技术栈 | 用途 |
|------|--------|------|
| `CIOaas-api/` | Java 17、Spring Boot 3、Spring Cloud | 后端 REST API + API 网关 |
| `CIOaas-web/` | React 16、Ant Design Pro、UmiJS 3、TypeScript | 前端单页应用 |
| `CIOaas-python/` | Python 3.12、FastAPI、FastMCP | 预测/财务 ML API + MCP 服务 |
| `cio-bigdata/` | Python 3.6、ETL / Singer、Airflow | 数据集成（Redshift、QuickBooks 等） |
| `docs/` | Markdown | 功能需求文档、设计文档、审核报告 |
| `docs/智能解析/调研/` | Markdown | OCR Agent 技术方案（系统架构/Java/Python/前端/设计理念） |
| `docs/AI-Chatbot/` | Markdown | AI Chatbot V1 设计文档（范围/ACL/对话图/API 契约/双端 UX） |

> 四个子项目（`CIOaas-api/`、`CIOaas-web/`、`CIOaas-python/`、`cio-bigdata/`）是**独立的嵌套 Git 仓库**，已在父仓库 `.gitignore` 中忽略，各有独立提交历史。某些 checkout 可能不包含全部子项目（例如 `cio-bigdata/` 当前未拉取时，涉及它的问题暂不适用）。

## 跨项目协作模式

Java 与 Python 之间有两种协作模式，按业务域区分：

### AI 财务提取（智能解析）— SQS 异步

Java (CIOaas-api) 和 Python (CIOaas-python) 通过 AWS SQS 异步通信，**不直接互相调用 HTTP**：

```
Java → SQS 队列 → Python（AI 处理）
Python → SQS 队列 → Java（结果回调）
```

- Java 负责：文件上传/S3 存储、任务生命周期、用户认证、最终数据写入 `fi_*` 表
- Python 负责：AI 提取/映射、映射记忆管理、LLM 调用
- 共享 PostgreSQL 数据库，但通过 DB 角色隔离各自的写权限

详细设计见 `docs/智能解析/调研/system-architecture.md`。

### AI Chatbot — HTTP 经网关 + SSE 流式

Web 聊天页（`/devSupport/chat`）→ Java 网关 → Python `source/chatbot/`（业务模块，interfaces/service/domain 分层，`/api/ai/chat/*` 接口）；对话图与数据查询工具在 `source/ai/agent/chatbot_graph/`（standard 主图）、`source/ai/agent/chatbot_kb_graph/`（kb 纯知识库智能体独立子包）、`source/ai/agent/chatbot_combo_graph/`（combo 组合智能体独立子包）、`source/ai/tools/`（提示词中文、给用户的回答默认英文）：

- SSE 流式经统一网关 `POST /api/ai/sse/stream`，channel 命名规范 `{模块}.{流类型}`（`chatbot.chat` / `demo.echo`）
- **三智能体 + 知识库问答（2026-07）**：`chatbot.chat` payload 可选 `agent_mode`（`standard` 缺省 / `kb` 纯知识库 / `combo` 组合分诊），standard 轨新增知识库工具 `search_knowledge_base`（进程内直调 rag 检索，非经 Java 网关）；模式选择走**斜杠命令文本标记**（与 `/sql` 同款）——后端 `stream_turn` 按问题文本判定，优先级 `/sql`＞`/knowledge`＞`/combined`＞payload `agent_mode`（命令字面→模式：`/knowledge`→kb、`/combined`→combo，收口 `_MODE_MARKERS` 词边界正则常量防 URL 误触发），前端无选择器（`+` 工具菜单加静态命令提示，前端不发 `agent_mode`）。设计见 `docs/superpowers/specs/2026-07-05-chatbot-knowledge-base-qa-design.md`
- Python 查询 LG 业务数据（LGPI 公司/财务接口）时同样**经 Java 网关回调**（路由带 `/web` 前缀），不直连 Java 服务
- 会话/消息持久化在共享 PG 表 `ai_chatbot_thread` / `ai_chatbot_message`（Python 启动时幂等建表）；消息带 `parent_message_id` 分支树，支持从任意消息 fork 新会话（前端问题编辑/回答重新生成都走 fork 分支）
- 鉴权：Redis 会话 + 公司归属 ACL（Python 侧校验）；`/api/ai/chat/manage/*` 管理查询仅管理端（前端管理页 `/devSupport/chatManage`）
- **断流恢复（切换会话 / 刷新页面续流，2026-06-15）**：后端生成与连接解耦，SSE 帧缓冲在 Redis（`sse:buf:{stream_id}`，TTL 1h，`Last-Event-ID` 重放，`GET /api/ai/sse/subscribe/{id}` 凭 stream_id 续看**不做 header 鉴权**）。前端把在跑流的 `stream_id` 按 threadId 存 `sessionStorage`，进入会话时有记录则经 `/subscribe` 从 seq 0 续流、否则读 DB；**末条已是落库的 assistant 则不续传**（防与重放重复渲染）。**纯前端，后端 0 改动**。详见 `docs/superpowers/plans/2026-06-15-ai-chatbot-resume-streaming.md`

详细设计见 `docs/AI-Chatbot/设计/design-doc.md`，前后端实现计划见 `docs/superpowers/plans/2026-06-05-ai-chatbot-v1-*.md`、`docs/superpowers/plans/2026-06-15-ai-chatbot-resume-streaming.md`。

---

## 本地目录（不纳入 Git）

以下目录在 `.gitignore` 中，不提交到远程：

- `.claude/` — Claude Code 本地配置
- `esapiens/`、`esapiens-python/` — OCR 引擎本地实验代码
- `other/` — 归档的历史文档
- `不要使用-Functional documentation/` — 已废弃的旧文档目录
