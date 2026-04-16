-- =============================================================================
-- SonarQube 表结构增量迁移
-- 适用于已部署 sprint108_ddl.sql 的数据库
-- 执行环境：PostgreSQL
-- =============================================================================

-- ── 1. sonarqube_component：删除旧指标列，新增 measures 等列 ─────────────────

ALTER TABLE sonarqube_component
    ADD COLUMN IF NOT EXISTS component_key      VARCHAR(255),
    ADD COLUMN IF NOT EXISTS component_id       VARCHAR(100),
    ADD COLUMN IF NOT EXISTS organization       VARCHAR(100),
    ADD COLUMN IF NOT EXISTS qualifier          VARCHAR(20),
    ADD COLUMN IF NOT EXISTS last_analysis_date VARCHAR(50),
    ADD COLUMN IF NOT EXISTS batch_date         TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS measures           TEXT;

ALTER TABLE sonarqube_component
    DROP COLUMN IF EXISTS bugs,
    DROP COLUMN IF EXISTS vulnerabilities,
    DROP COLUMN IF EXISTS security_hotspots,
    DROP COLUMN IF EXISTS code_smells,
    DROP COLUMN IF EXISTS new_code_smells,
    DROP COLUMN IF EXISTS sqale_index,
    DROP COLUMN IF EXISTS coverage,
    DROP COLUMN IF EXISTS duplicated_lines_density,
    DROP COLUMN IF EXISTS ncloc,
    DROP COLUMN IF EXISTS ncloc_language_distribution,
    DROP COLUMN IF EXISTS reliability_rating,
    DROP COLUMN IF EXISTS security_rating,
    DROP COLUMN IF EXISTS sqale_rating;

COMMENT ON COLUMN sonarqube_component.component_key      IS 'Component unique key (corresponds to Python tap key field)';
COMMENT ON COLUMN sonarqube_component.component_id       IS 'SonarQube internal component ID';
COMMENT ON COLUMN sonarqube_component.organization       IS 'SonarQube organization slug';
COMMENT ON COLUMN sonarqube_component.qualifier          IS 'Component qualifier (e.g. TRK = project)';
COMMENT ON COLUMN sonarqube_component.last_analysis_date IS 'Last analysis timestamp from SonarQube';
COMMENT ON COLUMN sonarqube_component.batch_date         IS 'Sync batch timestamp';
COMMENT ON COLUMN sonarqube_component.measures           IS 'Raw SonarQube measures JSON array from API, parsed at query time';


-- ── 2. sonarqube_project_status：新增条件/周期详情列 ─────────────────────────

ALTER TABLE sonarqube_project_status
    ADD COLUMN IF NOT EXISTS conditions         TEXT,
    ADD COLUMN IF NOT EXISTS periods            TEXT,
    ADD COLUMN IF NOT EXISTS ignored_conditions VARCHAR(10),
    ADD COLUMN IF NOT EXISTS batch_date         TIMESTAMP WITH TIME ZONE;

COMMENT ON COLUMN sonarqube_project_status.conditions         IS 'Quality gate conditions JSON array';
COMMENT ON COLUMN sonarqube_project_status.periods            IS 'Quality gate periods JSON array';
COMMENT ON COLUMN sonarqube_project_status.ignored_conditions IS 'Whether conditions are ignored';
COMMENT ON COLUMN sonarqube_project_status.batch_date         IS 'Sync batch timestamp';


-- ── 3. sonarqube_component_search：新增组织/ID/批次列 ────────────────────────

ALTER TABLE sonarqube_component_search
    ADD COLUMN IF NOT EXISTS organization        VARCHAR(100),
    ADD COLUMN IF NOT EXISTS component_search_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS batch_date          TIMESTAMP WITH TIME ZONE;

COMMENT ON COLUMN sonarqube_component_search.organization        IS 'SonarQube organization slug';
COMMENT ON COLUMN sonarqube_component_search.component_search_id IS 'SonarQube internal component ID';
COMMENT ON COLUMN sonarqube_component_search.batch_date          IS 'Sync batch timestamp';
