# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 必读子项目 CLAUDE.md（强制）

- 每次问答都必须先根据问题与扫描到的目录，读取并遵循以下子项目 `CLAUDE.md`：
  - `CIOaas-api/CLAUDE.md`
  - `CIOaas-web/CLAUDE.md`
  - `CIOaas-python/CLAUDE.md`
- 若问题涉及 `cio-bigdata/`，还须读取 `cio-bigdata/CLAUDE.md`。
- 各子项目另有 `standards/`（`architecture.md`、`coding.md`、`git.md`）；开发前按对应子项目 `CLAUDE.md` 中的「规范加载」执行，**不要**在根目录重复抄写这些规范。
- 若问题涉及多个子项目，按相关性依次读取；若无法确定，默认先读上述三个主工程 `CLAUDE.md` 再执行后续操作。

## Git 规则（强制）

- **提交消息必须使用中文**：`git commit -m "中文描述"`
- **禁止自动推送远程**：`git push` 只有在用户明确说"推送"时才执行，提交（commit）不等于推送
- **提交前确认**：执行 `git add` 和 `git commit` 前需用户确认，不要自动批量提交

## Windows 开发环境

- PowerShell 脚本（`.ps1`）必须在 PowerShell 中执行，**不能**在 bash/Git Bash 中运行
- `conda` 命令在 bash 终端中不可用，需使用 Anaconda Prompt 或 PowerShell
- Java/Maven 输出可能出现 GBK 编码乱码，可在 PowerShell 中运行：`chcp 65001` 切换为 UTF-8
- 路径使用正斜杠（`/`）或双反斜杠（`\\`），避免在 bash 环境中混用

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

## 跨项目协作模式

Java (CIOaas-api) 和 Python (CIOaas-python) 通过 AWS SQS 异步通信，**不直接互相调用 HTTP**：

```
Java → SQS 队列 → Python（AI 处理）
Python → SQS 队列 → Java（结果回调）
```

- Java 负责：文件上传/S3 存储、任务生命周期、用户认证、最终数据写入 `fi_*` 表
- Python 负责：AI 提取/映射、映射记忆管理、LLM 调用
- 共享 PostgreSQL 数据库，但通过 DB 角色隔离各自的写权限

详细设计见 `docs/智能解析/调研/system-architecture.md`。

---

## 本地目录（不纳入 Git）

以下目录在 `.gitignore` 中，不提交到远程：

- `.claude/` — Claude Code 本地配置
- `esapiens/`、`esapiens-python/` — OCR 引擎本地实验代码
- `other/` — 归档的历史文档
- `不要使用-Functional documentation/` — 已废弃的旧文档目录
