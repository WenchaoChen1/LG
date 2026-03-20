-- Benchmark Entry: single table for categories, metrics, and detail data
-- entry_type: 'METRIC' (parent rows) or 'DETAIL' (child rows)

CREATE TABLE IF NOT EXISTS fi_benchmark_entry (
    id              VARCHAR(36)     PRIMARY KEY,
    parent_id       VARCHAR(36)     REFERENCES fi_benchmark_entry(id),
    entry_type      VARCHAR(10)     NOT NULL,
    category        VARCHAR(30)     NOT NULL,
    category_display_name VARCHAR(100),
    metric          VARCHAR(30),
    metric_display_name VARCHAR(100),
    formula         TEXT,
    display_order   INTEGER         NOT NULL DEFAULT 0,
    platform        VARCHAR(20),
    edition         VARCHAR(200),
    source_metric_name VARCHAR(200),
    definition      TEXT,
    fy_period       INTEGER,
    segment         VARCHAR(200),
    percentile_25th VARCHAR(50),
    median          VARCHAR(50),
    percentile_75th VARCHAR(50),
    data_type       VARCHAR(20),
    best_guess      VARCHAR(500),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_by      VARCHAR(36),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_by      VARCHAR(36)
);

COMMENT ON TABLE fi_benchmark_entry IS 'Benchmark Entry: stores both metric definitions and detail data rows';
COMMENT ON COLUMN fi_benchmark_entry.entry_type IS 'METRIC = parent row, DETAIL = child row';
COMMENT ON COLUMN fi_benchmark_entry.parent_id IS 'Self-ref: NULL for METRIC rows, points to METRIC row id for DETAIL rows';
COMMENT ON COLUMN fi_benchmark_entry.category IS 'BenchmarkCategory enum value';
COMMENT ON COLUMN fi_benchmark_entry.metric IS 'BenchmarkMetric enum value, required for METRIC rows';
COMMENT ON COLUMN fi_benchmark_entry.platform IS 'BenchmarkPlatform enum value, DETAIL rows only';
COMMENT ON COLUMN fi_benchmark_entry.data_type IS 'BenchmarkDataType enum value (ACTUAL/FORECAST), DETAIL rows only';

-- Indexes
CREATE INDEX idx_entry_type_category ON fi_benchmark_entry (entry_type, category, display_order);
CREATE INDEX idx_entry_parent_id ON fi_benchmark_entry (parent_id, created_at);
CREATE UNIQUE INDEX uidx_entry_category_metric ON fi_benchmark_entry (category, metric) WHERE entry_type = 'METRIC';
