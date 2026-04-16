# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 必读子项目 CLAUDE.md（强制）

- 每次问答都必须先根据问题与扫描到的目录，读取并遵循以下子项目 `CLAUDE.md`：
  - `d:/github-code/LG/CIOaas-api/CLAUDE.md`
  - `d:/github-code/LG/CIOaas-web/CLAUDE.md`
  - `d:/github-code/LG/CIOaas-python/CLAUDE.md`
- 若问题涉及 `cio-bigdata/`，还须读取 `d:/github-code/LG/cio-bigdata/CLAUDE.md`。
- 各子项目另有 `standards/`（`architecture.md`、`coding.md`、`git.md`）；开发前按对应子项目 `CLAUDE.md` 中的「规范加载」执行，**不要**在根目录重复抄写这些规范。
- 若问题涉及多个子项目，按相关性依次读取；若无法确定，默认先读上述三个主工程 `CLAUDE.md` 再执行后续操作。

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
| `db-optimization/` | SQL | PostgreSQL 数据库优化脚本 |

---

## db-optimization（本目录无独立 CLAUDE.md）

`db-optimization/` 下按优先级组织的 PostgreSQL 脚本：

- `P0_*` — 关键：敏感数据安全、主键、外键
- `P1_*` — 重要：枚举文档、数值字段单位、字段注释
- `P2_*` — 优化：索引、数据类型修正、约束与默认值
- `P3_*` — 增强：审计字段、大字段优化、命名规范
