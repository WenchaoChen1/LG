#!/bin/bash
# ============================================================
# Postgres 首次初始化（仅 PGDATA 为空时执行一次）
# ------------------------------------------------------------
# 目的：业务库与 RAG 向量库**完全隔离**，pgvector / pg_trgm 扩展只在
# RAG 库里安装，业务库保持干净不受影响。
#
#   ${POSTGRES_DB}    业务库（默认 lg_test）—— 由 entrypoint 自动建，不动它
#   ${PG_RAG_DB}      RAG 向量库（默认 lg_rag）—— 本脚本建 + 装扩展
# ============================================================
set -e

RAG_DB="${PG_RAG_DB:-lg_rag}"

echo "[init] creating RAG database '${RAG_DB}' (if not exists) ..."

# 1) 在 postgres 库内建 RAG 库（CREATE DATABASE 不能在事务里，且无 IF NOT EXISTS
#    语法 → 用 \gexec + WHERE NOT EXISTS 模式实现幂等）
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres <<-EOSQL
    SELECT 'CREATE DATABASE "${RAG_DB}"'
     WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${RAG_DB}')\gexec
EOSQL

# 2) 仅在 RAG 库里装扩展，业务库不动
echo "[init] installing pgvector + pg_trgm extensions in '${RAG_DB}' ..."
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "${RAG_DB}" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
EOSQL

echo "[init] done. business db='${POSTGRES_DB}' (no vector ext), rag db='${RAG_DB}' (vector + pg_trgm)"
