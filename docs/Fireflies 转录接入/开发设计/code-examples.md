# Fireflies 会议转录接入 — 代码示例

> 关联文档: [开发设计](./dev-design-doc.md) · [设计](../设计/design-doc.md)
>
> 本文放 DDL 与参考代码片段；表的字段说明、索引用途见开发设计第 1 节。迁移文件名与 sprint 号以实际发版为准。

## 1. Java 迁移 `deploy/upgrade_doc/sprint122/V1__ff_init.sql`

```sql
-- sprint122 V1：Fireflies 域建表（ff_connection_configuration / ff_meeting_meta_info / ff_meeting_sentence / ff_cheat_sheet / ff_expertise_tag）
-- 先于 Java 发版执行（ddl-auto 只建表不建索引）；可重跑
-- psql -v ON_ERROR_STOP=1 --single-transaction -f V1__ff_init.sql

CREATE TABLE IF NOT EXISTS ff_connection_configuration (
    id                    varchar(36)   NOT NULL,
    organization_id       varchar(36)   NOT NULL,
    api_key_cipher        text,
    account_email         varchar(255),
    connection_status     varchar(16)   NOT NULL DEFAULT 'UNCONNECTED',
    last_success_sync_at  timestamptz,
    consecutive_failures  int           NOT NULL DEFAULT 0,
    sync_started_at       timestamptz,
    email_domains         jsonb         NOT NULL DEFAULT '[]'::jsonb,
    created_by            varchar(36),
    created_at            timestamptz,
    updated_by            varchar(36),
    updated_at            timestamptz,
    CONSTRAINT pk_ff_connection_configuration PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_ff_connection_configuration_org ON ff_connection_configuration (organization_id);
COMMENT ON TABLE  ff_connection_configuration IS 'Fireflies settings per tenant: connection, encrypted API key and firm email domains';
COMMENT ON COLUMN ff_connection_configuration.organization_id      IS 'Tenant; one row per tenant';
COMMENT ON COLUMN ff_connection_configuration.api_key_cipher       IS 'AES-GCM ciphertext of the API key; null when never linked or removed; APIs return only a mask';
COMMENT ON COLUMN ff_connection_configuration.account_email        IS 'Fireflies account that owns the key; compared on re-link to detect an account change';
COMMENT ON COLUMN ff_connection_configuration.connection_status    IS 'UNCONNECTED / CONNECTED / FAILED / DISCONNECTED';
COMMENT ON COLUMN ff_connection_configuration.last_success_sync_at IS 'Last successfully completed pull; cleared when the account changes';
COMMENT ON COLUMN ff_connection_configuration.consecutive_failures IS 'Consecutive non-auth failures; reaching N turns the status to DISCONNECTED';
COMMENT ON COLUMN ff_connection_configuration.sync_started_at      IS 'Non-null while a pull is running; taken by conditional UPDATE, cleared on finish';
COMMENT ON COLUMN ff_connection_configuration.email_domains        IS 'Email domains of the tenant firm (identification step 1: GS side); lower case, without @, no public mail domains';

CREATE TABLE IF NOT EXISTS ff_meeting_meta_info (
    id                varchar(36)   NOT NULL,
    organization_id   varchar(36)   NOT NULL,
    fireflies_id      varchar(64)   NOT NULL,
    title             varchar(512),
    started_at        timestamptz   NOT NULL,
    duration_minutes  numeric(8,2),
    participants      jsonb         NOT NULL DEFAULT '[]'::jsonb,
    attendance        jsonb         NOT NULL DEFAULT '[]'::jsonb,
    speakers          jsonb         NOT NULL DEFAULT '[]'::jsonb,
    overview          text,
    content_hash      varchar(64),
    dispatched_at     timestamptz,
    created_by        varchar(36),
    created_at        timestamptz,
    updated_by        varchar(36),
    updated_at        timestamptz,
    CONSTRAINT pk_ff_meeting_meta_info PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_ff_meeting_meta_info_org_ffid ON ff_meeting_meta_info (organization_id, fireflies_id);
CREATE INDEX IF NOT EXISTS idx_ff_meeting_meta_info_org_started ON ff_meeting_meta_info (organization_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_ff_meeting_meta_info_participants_gin ON ff_meeting_meta_info USING gin (participants jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_ff_meeting_meta_info_undispatched ON ff_meeting_meta_info (organization_id, created_at)
    WHERE dispatched_at IS NULL;
COMMENT ON TABLE  ff_meeting_meta_info IS 'Fireflies meeting metadata (raw side); processing state lives in ai_ff_meeting_state';
COMMENT ON COLUMN ff_meeting_meta_info.fireflies_id     IS 'Native Fireflies transcript id; unique per tenant';
COMMENT ON COLUMN ff_meeting_meta_info.title            IS 'Display and search only; never used for type identification';
COMMENT ON COLUMN ff_meeting_meta_info.started_at       IS 'Meeting start (Fireflies dateString), UTC';
COMMENT ON COLUMN ff_meeting_meta_info.duration_minutes IS 'Fireflies duration, in minutes';
COMMENT ON COLUMN ff_meeting_meta_info.participants     IS 'Invited emails (lower case), JSON array';
COMMENT ON COLUMN ff_meeting_meta_info.attendance       IS 'meeting_attendance as returned: [{name, join_time, leave_time}]';
COMMENT ON COLUMN ff_meeting_meta_info.speakers         IS 'speakers as returned: [{id, name}]';
COMMENT ON COLUMN ff_meeting_meta_info.overview         IS 'Fireflies summary.overview; source of the GS-to-founder summary';
COMMENT ON COLUMN ff_meeting_meta_info.content_hash     IS 'Hash of sentences and metadata; a change after dispatch is only logged as a warning on re-pull';
COMMENT ON COLUMN ff_meeting_meta_info.created_at       IS 'First ingest time (the row is only updated afterwards)';
COMMENT ON COLUMN ff_meeting_meta_info.dispatched_at    IS 'Time it was handed to Python over SQS; raw data is frozen once set';

CREATE TABLE IF NOT EXISTS ff_meeting_sentence (
    id              varchar(36)    NOT NULL,
    meeting_id      varchar(36)    NOT NULL,
    sentence_order  int            NOT NULL,
    speaker_id      int,
    speaker_name    varchar(255),
    text            text           NOT NULL,
    start_time      numeric(10,3),
    end_time        numeric(10,3),
    CONSTRAINT pk_ff_meeting_sentence PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_ff_meeting_sentence_meeting_order ON ff_meeting_sentence (meeting_id, sentence_order);
COMMENT ON TABLE  ff_meeting_sentence IS 'Transcript sentences of a Fireflies meeting';
COMMENT ON COLUMN ff_meeting_sentence.meeting_id     IS 'ff_meeting_meta_info.id (no foreign key)';
COMMENT ON COLUMN ff_meeting_sentence.sentence_order IS 'Position of the sentence in the transcript (Fireflies index)';
COMMENT ON COLUMN ff_meeting_sentence.speaker_id     IS 'Fireflies speaker id; same value as speakers[].id and speaker_ref';
COMMENT ON COLUMN ff_meeting_sentence.speaker_name   IS 'Speaker display name as returned';
COMMENT ON COLUMN ff_meeting_sentence.text           IS 'Fireflies text: default transcription, or the version edited in Fireflies';
COMMENT ON COLUMN ff_meeting_sentence.start_time     IS 'Start, seconds';
COMMENT ON COLUMN ff_meeting_sentence.end_time       IS 'End, seconds';

CREATE TABLE IF NOT EXISTS ff_cheat_sheet (
    id                 varchar(36)   NOT NULL,
    organization_id    varchar(36)   NOT NULL,
    name               varchar(255)  NOT NULL,
    emails             jsonb         NOT NULL DEFAULT '[]'::jsonb,
    organization       varchar(255)  NOT NULL,
    role               varchar(32)   NOT NULL,
    expertise_tags     jsonb         NOT NULL DEFAULT '[]'::jsonb,
    area_of_expertise  varchar(2048),
    valid_from         date          NOT NULL,
    valid_to           date,
    source             varchar(32)   NOT NULL DEFAULT 'MANUAL',
    source_meeting_id  varchar(36),
    reviewed_by        varchar(36),
    reviewed_at        timestamptz,
    created_by         varchar(36),
    created_at         timestamptz,
    updated_by         varchar(36),
    updated_at         timestamptz,
    CONSTRAINT pk_ff_cheat_sheet PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_ff_cheat_sheet_org_name ON ff_cheat_sheet (organization_id, name);
CREATE INDEX IF NOT EXISTS idx_ff_cheat_sheet_emails_gin ON ff_cheat_sheet USING gin (emails jsonb_path_ops);
COMMENT ON TABLE  ff_cheat_sheet IS 'Cheat Sheet (external parties); one row per version, append-only';
COMMENT ON COLUMN ff_cheat_sheet.name              IS 'Unique identifier of a person within the tenant; shared by all versions';
COMMENT ON COLUMN ff_cheat_sheet.emails            IS 'Emails (lower case), JSON array';
COMMENT ON COLUMN ff_cheat_sheet.organization      IS 'External organization, free text';
COMMENT ON COLUMN ff_cheat_sheet.role              IS 'LP / STRATEGIC_PARTNER / EXIT_PARTNER / FOUNDER / GS_STAFF / OTHER';
COMMENT ON COLUMN ff_cheat_sheet.expertise_tags    IS 'Expertise tag texts, JSON array; non-empty means expert';
COMMENT ON COLUMN ff_cheat_sheet.area_of_expertise IS 'Description only; not used for routing';
COMMENT ON COLUMN ff_cheat_sheet.valid_from        IS 'Validity start (required)';
COMMENT ON COLUMN ff_cheat_sheet.valid_to          IS 'Validity end; null means present';
COMMENT ON COLUMN ff_cheat_sheet.source            IS 'MANUAL / FF_SUMMARY_RECORDS';
COMMENT ON COLUMN ff_cheat_sheet.source_meeting_id IS 'Source meeting (ff_meeting_meta_info.id) when registered from Summary Records';
COMMENT ON COLUMN ff_cheat_sheet.reviewed_by       IS 'Last reviewer who confirmed without changes';
COMMENT ON COLUMN ff_cheat_sheet.reviewed_at       IS 'Last review time; updated alone, never touches updated_at';
COMMENT ON COLUMN ff_cheat_sheet.updated_at        IS 'Write time of the version; decides overlaps (latest wins)';

CREATE TABLE IF NOT EXISTS ff_expertise_tag (
    id               varchar(36)  NOT NULL,
    organization_id  varchar(36)  NOT NULL,
    name             varchar(64)  NOT NULL,
    preset           boolean      NOT NULL DEFAULT false,
    sort_no          int          NOT NULL,
    created_by       varchar(36),
    created_at       timestamptz,
    updated_by       varchar(36),
    updated_at       timestamptz,
    CONSTRAINT pk_ff_expertise_tag PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_ff_expertise_tag_org_name ON ff_expertise_tag (organization_id, lower(name));
CREATE INDEX IF NOT EXISTS idx_ff_expertise_tag_org_sort ON ff_expertise_tag (organization_id, sort_no);
COMMENT ON TABLE  ff_expertise_tag IS 'Expertise tag dictionary per tenant; unused tags are deleted physically';
COMMENT ON COLUMN ff_expertise_tag.name    IS 'Tag text; unique per tenant, case-insensitive';
COMMENT ON COLUMN ff_expertise_tag.preset  IS 'One of the 5 preset tags (cannot be deleted)';
COMMENT ON COLUMN ff_expertise_tag.sort_no IS 'Display order; presets 1-5, new tags appended';

-- 存量组织补齐 5 项预置专长标签（新建组织由 OrganizationServiceImpl.save 写入）
INSERT INTO ff_expertise_tag (id, organization_id, name, preset, sort_no, created_by, created_at, updated_by, updated_at)
SELECT gen_random_uuid()::varchar(36), o.id, t.name, true, t.sort_no, '1', now(), '1', now()
FROM organization o
CROSS JOIN (VALUES ('Multiples', 1), ('Buyer behavior', 2), ('Exit trends', 3),
                   ('Software usage', 4), ('Commercial buying behavior', 5)) AS t (name, sort_no)
ON CONFLICT (organization_id, lower(name)) DO NOTHING;
```

## 2. Python 迁移 `sql/migrations/business/V034__sprint122_fireflies_init.sql`

```sql
-- V034：Fireflies 识别、提取与路由的表（ai_ff_*），以及 ai_file_registry.business_type 注释加 FIREFLIES / FIREFLIES_SUMMARY、ai_rag_business_association.business_type 注释加 EXPERT_TESTIMONY / CROSS_COMPANY
-- 先于本批 Python 发版执行；可重跑
-- 部署后把这些表的读写权限授给 Python 的数据库账号

BEGIN;

CREATE OR REPLACE FUNCTION set_ai_ff_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- P1 会议处理状态
CREATE TABLE IF NOT EXISTS ai_ff_meeting_state (
    id                     VARCHAR(36)   NOT NULL DEFAULT gen_random_uuid()::varchar(36),
    meeting_id             VARCHAR(36)   NOT NULL,
    organization_id        VARCHAR(36)   NOT NULL,
    fireflies_id           VARCHAR(64)   NOT NULL,
    title                  VARCHAR(512),
    started_at             TIMESTAMPTZ   NOT NULL,
    duration_minutes       NUMERIC(8,2),
    meeting_type           VARCHAR(16)   NOT NULL DEFAULT 'UNKNOWN',
    meeting_status         VARCHAR(16),
    pending_reasons        JSONB         NOT NULL DEFAULT '[]'::jsonb,
    portfolio_ids          JSONB         NOT NULL DEFAULT '[]'::jsonb,
    processing_stage       VARCHAR(16)   NOT NULL DEFAULT 'IDENTIFYING',
    processing_started_at  TIMESTAMPTZ   NOT NULL,
    extraction_status      VARCHAR(16),
    extraction_trigger     VARCHAR(24),
    extraction_started_at  TIMESTAMPTZ,
    identification_result  VARCHAR(32),
    current_extraction_input  JSONB,
    created_by             VARCHAR(36),
    created_at             TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_by             VARCHAR(36),
    updated_at             TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT pk_ai_ff_meeting_state PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_ai_ff_meeting_state_meeting ON ai_ff_meeting_state (meeting_id);
CREATE INDEX IF NOT EXISTS idx_ai_ff_meeting_state_list ON ai_ff_meeting_state (organization_id, started_at DESC)
    WHERE meeting_status IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ai_ff_meeting_state_status ON ai_ff_meeting_state (organization_id, meeting_status, meeting_type);
COMMENT ON TABLE  ai_ff_meeting_state IS 'Processing state of a Fireflies meeting (1:1 with ff_meeting_meta_info); no foreign key';
COMMENT ON COLUMN ai_ff_meeting_state.meeting_id            IS 'ff_meeting_meta_info.id';
COMMENT ON COLUMN ai_ff_meeting_state.fireflies_id          IS 'Copied from ff_meeting_meta_info for list display and search';
COMMENT ON COLUMN ai_ff_meeting_state.title                 IS 'Copied from ff_meeting_meta_info';
COMMENT ON COLUMN ai_ff_meeting_state.started_at            IS 'Copied from ff_meeting_meta_info; list order, date filter, business date';
COMMENT ON COLUMN ai_ff_meeting_state.duration_minutes      IS 'Copied from ff_meeting_meta_info';
COMMENT ON COLUMN ai_ff_meeting_state.meeting_type          IS 'GS_FOUNDER / GS_LP / GS_INTERNAL / GS_PARTNER / UNKNOWN';
COMMENT ON COLUMN ai_ff_meeting_state.meeting_status        IS 'PASSED / PENDING; null before the first run finishes or when invalid';
COMMENT ON COLUMN ai_ff_meeting_state.pending_reasons       IS 'JSON array of TO_IDENTIFY / TO_CONFIRM_EXPERT / TO_REVIEW';
COMMENT ON COLUMN ai_ff_meeting_state.portfolio_ids         IS 'Portfolio mark: company_group ids';
COMMENT ON COLUMN ai_ff_meeting_state.processing_stage      IS 'IDENTIFYING / EXTRACTING / DONE (first automatic run)';
COMMENT ON COLUMN ai_ff_meeting_state.processing_started_at IS 'Start of the current first-run attempt; also the token of who is processing, rewritten when an SQS redelivery takes over';
COMMENT ON COLUMN ai_ff_meeting_state.extraction_status     IS 'Latest extraction task: RUNNING / SUCCEEDED / VOIDED';
COMMENT ON COLUMN ai_ff_meeting_state.extraction_trigger    IS 'AUTO / AUTO_ROUTE / START_EXTRACTION (includes the P1 rerun before a type change)';
COMMENT ON COLUMN ai_ff_meeting_state.extraction_started_at IS 'Start of the latest extraction task; for non-first-run tasks, RUNNING past the stuck limit is voided by the scheduled sweep';
COMMENT ON COLUMN ai_ff_meeting_state.identification_result IS 'Result of the identification stage: NORMAL / NO_SUBSTANCE (invalid: no sentences, or P1 found no substance) / QUALITY_CHECK_FAILED (P1) / ATTENDEE_INFERENCE_FAILED (P8); one value by that precedence';
COMMENT ON COLUMN ai_ff_meeting_state.updated_at            IS 'Refreshed by trigger on every update; also the optimistic-lock token of the review page';
COMMENT ON COLUMN ai_ff_meeting_state.current_extraction_input      IS 'Input the online content was extracted with (type, companies, participants, speaker bindings); not the extracted content';
DROP TRIGGER IF EXISTS trg_ai_ff_meeting_state_updated_at ON ai_ff_meeting_state;
CREATE TRIGGER trg_ai_ff_meeting_state_updated_at BEFORE UPDATE ON ai_ff_meeting_state
    FOR EACH ROW EXECUTE FUNCTION set_ai_ff_updated_at();

-- P2 参会人
CREATE TABLE IF NOT EXISTS ai_ff_meeting_participant (
    id                         VARCHAR(36)   NOT NULL DEFAULT gen_random_uuid()::varchar(36),
    organization_id            VARCHAR(36)   NOT NULL,
    meeting_id                 VARCHAR(36)   NOT NULL,
    email                      VARCHAR(255)  NOT NULL,
    matched_name               VARCHAR(255),
    invited                    BOOLEAN       NOT NULL,
    role                       VARCHAR(32)   NOT NULL DEFAULT 'UNIDENTIFIED',
    match_step                 VARCHAR(24),
    lg_user_id                 VARCHAR(36),
    company_id                 VARCHAR(36),
    cheat_sheet_name           VARCHAR(255),
    cheat_sheet_id             VARCHAR(36),
    display_name               VARCHAR(255),
    organization               VARCHAR(255),
    expertise_tags             JSONB         NOT NULL DEFAULT '[]'::jsonb,
    ai_inferred_identity       JSONB,
    testimony_backfill_status  VARCHAR(16),
    created_by                 VARCHAR(36),
    created_at                 TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_by                 VARCHAR(36),
    updated_at                 TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT pk_ai_ff_meeting_participant PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_ai_ff_meeting_participant_meeting_email ON ai_ff_meeting_participant (meeting_id, email);
CREATE INDEX IF NOT EXISTS idx_ai_ff_meeting_participant_founder ON ai_ff_meeting_participant (organization_id, email)
    WHERE role = 'FOUNDER' AND company_id IS NULL;
COMMENT ON TABLE  ai_ff_meeting_participant IS 'Identification result: participants of a meeting (current state)';
COMMENT ON COLUMN ai_ff_meeting_participant.email                     IS 'Invited email, or the Cheat Sheet / LG account email for merged speakers; lower case';
COMMENT ON COLUMN ai_ff_meeting_participant.matched_name              IS 'Matched speaker display name (most sentences); null if none';
COMMENT ON COLUMN ai_ff_meeting_participant.invited                   IS 'Whether the email is on the invite list';
COMMENT ON COLUMN ai_ff_meeting_participant.role                      IS 'GS_STAFF / FOUNDER / LP / STRATEGIC_PARTNER / EXIT_PARTNER / OTHER / UNIDENTIFIED';
COMMENT ON COLUMN ai_ff_meeting_participant.match_step                IS 'GS_DOMAIN / LG_USER_EMAIL / LG_USER_DOMAIN / CHEAT_SHEET_EMAIL / P8 / MANUAL';
COMMENT ON COLUMN ai_ff_meeting_participant.lg_user_id                IS 'LG user matched by full email';
COMMENT ON COLUMN ai_ff_meeting_participant.company_id                IS 'Company of a company-side participant; null for Cheat Sheet / P8 founders';
COMMENT ON COLUMN ai_ff_meeting_participant.cheat_sheet_name             IS 'Cheat Sheet reference key (name)';
COMMENT ON COLUMN ai_ff_meeting_participant.cheat_sheet_id            IS 'ff_cheat_sheet.id (one row per version) picked by meeting date at identification time';
COMMENT ON COLUMN ai_ff_meeting_participant.display_name              IS 'Name shown on the participant chip';
COMMENT ON COLUMN ai_ff_meeting_participant.organization              IS 'Organization shown on the participant chip';
COMMENT ON COLUMN ai_ff_meeting_participant.expertise_tags            IS 'Expertise tags effective on the meeting date';
COMMENT ON COLUMN ai_ff_meeting_participant.ai_inferred_identity      IS 'Identity inferred by AI (P8): name, role, organization or Cheat Sheet version, confidence, evidence; kept even if not adopted';
COMMENT ON COLUMN ai_ff_meeting_participant.testimony_backfill_status IS 'RUNNING / FAILED; null means none or succeeded';
DROP TRIGGER IF EXISTS trg_ai_ff_meeting_participant_updated_at ON ai_ff_meeting_participant;
CREATE TRIGGER trg_ai_ff_meeting_participant_updated_at BEFORE UPDATE ON ai_ff_meeting_participant
    FOR EACH ROW EXECUTE FUNCTION set_ai_ff_updated_at();

-- P3 说话人绑定
CREATE TABLE IF NOT EXISTS ai_ff_meeting_speaker (
    id               VARCHAR(36)   NOT NULL DEFAULT gen_random_uuid()::varchar(36),
    organization_id  VARCHAR(36)   NOT NULL,
    meeting_id       VARCHAR(36)   NOT NULL,
    speaker_id       INT           NOT NULL,
    speaker_name     VARCHAR(255),
    participant_id   VARCHAR(36),
    bind_source      VARCHAR(24),
    ai_speaker_match JSONB,
    bound_by         VARCHAR(36),
    bound_at         TIMESTAMPTZ,
    created_by       VARCHAR(36),
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_by       VARCHAR(36),
    updated_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT pk_ai_ff_meeting_speaker PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_ai_ff_meeting_speaker_meeting_spk ON ai_ff_meeting_speaker (meeting_id, speaker_id);
COMMENT ON TABLE  ai_ff_meeting_speaker IS 'Identification result: Fireflies speaker to participant binding';
COMMENT ON COLUMN ai_ff_meeting_speaker.speaker_id     IS 'Fireflies speaker id';
COMMENT ON COLUMN ai_ff_meeting_speaker.speaker_name   IS 'Speaker display name';
COMMENT ON COLUMN ai_ff_meeting_speaker.participant_id IS 'Bound participant; null means unmatched speaker';
COMMENT ON COLUMN ai_ff_meeting_speaker.bind_source    IS 'NAME_PREFIX / P8 / MANUAL_ASSIGN / MANUAL_CHEAT_SHEET';
COMMENT ON COLUMN ai_ff_meeting_speaker.ai_speaker_match IS 'AI (P8 speaker_map) match of this speaker to a participant or Cheat Sheet person, confidence, evidence; low confidence included';
COMMENT ON COLUMN ai_ff_meeting_speaker.bound_by       IS 'Who bound it manually';
COMMENT ON COLUMN ai_ff_meeting_speaker.bound_at       IS 'When it was bound manually';
DROP TRIGGER IF EXISTS trg_ai_ff_meeting_speaker_updated_at ON ai_ff_meeting_speaker;
CREATE TRIGGER trg_ai_ff_meeting_speaker_updated_at BEFORE UPDATE ON ai_ff_meeting_speaker
    FOR EACH ROW EXECUTE FUNCTION set_ai_ff_updated_at();

-- P4 公司关联
CREATE TABLE IF NOT EXISTS ai_ff_meeting_company (
    id                    VARCHAR(36)   NOT NULL DEFAULT gen_random_uuid()::varchar(36),
    organization_id       VARCHAR(36)   NOT NULL,
    meeting_id            VARCHAR(36)   NOT NULL,
    company_id            VARCHAR(36)   NOT NULL,
    adopted               BOOLEAN       NOT NULL,
    basis                 VARCHAR(16),
    basis_participant_id  VARCHAR(36),
    basis_value           VARCHAR(255),
    ai_transcript_mention JSONB,
    auto_routed           BOOLEAN       NOT NULL DEFAULT FALSE,
    assigned_by           VARCHAR(36),
    assigned_at           TIMESTAMPTZ,
    created_by            VARCHAR(36),
    created_at            TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_by            VARCHAR(36),
    updated_at            TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT pk_ai_ff_meeting_company PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_ai_ff_meeting_company_meeting_company ON ai_ff_meeting_company (meeting_id, company_id);
CREATE INDEX IF NOT EXISTS idx_ai_ff_meeting_company_org_company ON ai_ff_meeting_company (organization_id, company_id) WHERE adopted = TRUE;
COMMENT ON TABLE  ai_ff_meeting_company IS 'Identification result: companies associated with a meeting, including candidates';
COMMENT ON COLUMN ai_ff_meeting_company.adopted              IS 'Adopted after apply; false for candidates and removed companies';
COMMENT ON COLUMN ai_ff_meeting_company.basis                IS 'EMAIL / EMAIL_DOMAIN / TRANSCRIPT / MANUAL';
COMMENT ON COLUMN ai_ff_meeting_company.basis_participant_id IS 'Participant matched by email or domain';
COMMENT ON COLUMN ai_ff_meeting_company.basis_value          IS 'Matched email or domain';
COMMENT ON COLUMN ai_ff_meeting_company.ai_transcript_mention IS 'AI (P1) mention of this company in the transcript: confidence, attendee_company, evidence';
COMMENT ON COLUMN ai_ff_meeting_company.auto_routed          IS 'Associated by auto-route after a company change';
COMMENT ON COLUMN ai_ff_meeting_company.assigned_by          IS 'Who assigned it manually';
COMMENT ON COLUMN ai_ff_meeting_company.assigned_at          IS 'When it was assigned manually';
DROP TRIGGER IF EXISTS trg_ai_ff_meeting_company_updated_at ON ai_ff_meeting_company;
CREATE TRIGGER trg_ai_ff_meeting_company_updated_at BEFORE UPDATE ON ai_ff_meeting_company
    FOR EACH ROW EXECUTE FUNCTION set_ai_ff_updated_at();

-- P5 专家候选
CREATE TABLE IF NOT EXISTS ai_ff_expert_candidate (
    id               VARCHAR(36)   NOT NULL DEFAULT gen_random_uuid()::varchar(36),
    organization_id  VARCHAR(36)   NOT NULL,
    meeting_id       VARCHAR(36)   NOT NULL,
    participant_id   VARCHAR(36)   NOT NULL,
    tag              VARCHAR(64)   NOT NULL,
    claims           JSONB         NOT NULL DEFAULT '[]'::jsonb,
    status           VARCHAR(16)   NOT NULL DEFAULT 'PENDING',
    auto_resolved    BOOLEAN       NOT NULL DEFAULT FALSE,
    decided_by       VARCHAR(36),
    decided_at       TIMESTAMPTZ,
    deleted          BOOLEAN       NOT NULL DEFAULT FALSE,
    created_by       VARCHAR(36),
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_by       VARCHAR(36),
    updated_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT pk_ai_ff_expert_candidate PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_ai_ff_expert_candidate_live ON ai_ff_expert_candidate (meeting_id, participant_id, tag)
    WHERE deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_ai_ff_expert_candidate_pending_tag ON ai_ff_expert_candidate (organization_id, tag)
    WHERE status = 'PENDING' AND deleted = FALSE;
COMMENT ON TABLE  ai_ff_expert_candidate IS 'Possible-expert suggestions: one suggested tag of one person in one meeting';
COMMENT ON COLUMN ai_ff_expert_candidate.participant_id IS 'ai_ff_meeting_participant.id of the suggested expert';
COMMENT ON COLUMN ai_ff_expert_candidate.tag            IS 'Suggested expertise tag text';
COMMENT ON COLUMN ai_ff_expert_candidate.claims         IS 'Substantive claims: [{claim, basis, basis_type, timestamp}]';
COMMENT ON COLUMN ai_ff_expert_candidate.status         IS 'PENDING / ACCEPTED / DECLINED / WITHDRAWN';
COMMENT ON COLUMN ai_ff_expert_candidate.auto_resolved  IS 'Resolved automatically when the confirm dialog opened';
COMMENT ON COLUMN ai_ff_expert_candidate.decided_by     IS 'Who decided (dialog save, or the opener for auto-resolve)';
COMMENT ON COLUMN ai_ff_expert_candidate.decided_at     IS 'When it was decided';
DROP TRIGGER IF EXISTS trg_ai_ff_expert_candidate_updated_at ON ai_ff_expert_candidate;
CREATE TRIGGER trg_ai_ff_expert_candidate_updated_at BEFORE UPDATE ON ai_ff_expert_candidate
    FOR EACH ROW EXECUTE FUNCTION set_ai_ff_updated_at();

-- P6 拒绝名单
CREATE TABLE IF NOT EXISTS ai_ff_expert_rejection (
    id               VARCHAR(36)   NOT NULL DEFAULT gen_random_uuid()::varchar(36),
    organization_id  VARCHAR(36)   NOT NULL,
    email            VARCHAR(255)  NOT NULL,
    tag              VARCHAR(64)   NOT NULL,
    meeting_id       VARCHAR(36)   NOT NULL,
    created_by       VARCHAR(36),
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_by       VARCHAR(36),
    updated_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT pk_ai_ff_expert_rejection PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_ai_ff_expert_rejection_org_email_tag ON ai_ff_expert_rejection (organization_id, email, tag);
COMMENT ON TABLE  ai_ff_expert_rejection IS 'Rejected (email, expertise tag) pairs; filtered before expert inference';
COMMENT ON COLUMN ai_ff_expert_rejection.email      IS 'Email on the participant row of the source meeting, lower case';
COMMENT ON COLUMN ai_ff_expert_rejection.tag        IS 'Rejected expertise tag';
COMMENT ON COLUMN ai_ff_expert_rejection.meeting_id IS 'Source meeting';
DROP TRIGGER IF EXISTS trg_ai_ff_expert_rejection_updated_at ON ai_ff_expert_rejection;
CREATE TRIGGER trg_ai_ff_expert_rejection_updated_at BEFORE UPDATE ON ai_ff_expert_rejection
    FOR EACH ROW EXECUTE FUNCTION set_ai_ff_updated_at();

-- P7 路由中间表
CREATE TABLE IF NOT EXISTS ai_ff_routing_row (
    id                      VARCHAR(36)   NOT NULL DEFAULT gen_random_uuid()::varchar(36),
    organization_id         VARCHAR(36)   NOT NULL,
    meeting_id              VARCHAR(36)   NOT NULL,
    destination             VARCHAR(24)   NOT NULL,
    output_type             VARCHAR(16)   NOT NULL,
    company_id              VARCHAR(36),
    content                 TEXT          NOT NULL DEFAULT '',
    category                VARCHAR(64),
    source_timestamp        VARCHAR(8),
    speaker_participant_id  VARCHAR(36),
    authorized              BOOLEAN       NOT NULL DEFAULT FALSE,
    in_playbook             BOOLEAN       NOT NULL DEFAULT FALSE,
    fund_tag_ids            JSONB,
    file_id                 VARCHAR(36),
    projection_status       VARCHAR(16)   NOT NULL DEFAULT 'NONE',
    projection_attempts     INT           NOT NULL DEFAULT 0,
    edited_by               VARCHAR(36),
    edited_at               TIMESTAMPTZ,
    deleted                 BOOLEAN       NOT NULL DEFAULT FALSE,
    created_by              VARCHAR(36),
    created_at              TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_by              VARCHAR(36),
    updated_at              TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT pk_ai_ff_routing_row PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_ai_ff_routing_row_meeting ON ai_ff_routing_row (meeting_id);
CREATE INDEX IF NOT EXISTS idx_ai_ff_routing_row_tab ON ai_ff_routing_row (organization_id, destination, created_at DESC)
    WHERE deleted = FALSE AND authorized = TRUE AND file_id IS NOT NULL
      AND destination IN ('CROSS_COMPANY', 'TESTIMONY_SIGNED');
CREATE INDEX IF NOT EXISTS idx_ai_ff_routing_row_file ON ai_ff_routing_row (file_id);
CREATE INDEX IF NOT EXISTS idx_ai_ff_routing_row_projection ON ai_ff_routing_row (projection_status)
    WHERE projection_status IN ('PENDING', 'FAILED');
COMMENT ON TABLE  ai_ff_routing_row IS 'Routing rows: one Authorize cell = one projected knowledge entry';
COMMENT ON COLUMN ai_ff_routing_row.destination            IS 'KB_APP / KB_ADMIN / FUND_LEVEL / CROSS_COMPANY / TESTIMONY_ANON / TESTIMONY_SIGNED';
COMMENT ON COLUMN ai_ff_routing_row.output_type            IS 'SUMMARY / KB / CROSS_COMPANY / TESTIMONY; summary and KB body are separate rows, each authorized and projected on its own';
COMMENT ON COLUMN ai_ff_routing_row.company_id             IS 'Required for KB_APP / KB_ADMIN';
COMMENT ON COLUMN ai_ff_routing_row.content                IS 'Summary for SUMMARY rows, markdown body for KB rows, statement for cross-company, body without the source line for testimony';
COMMENT ON COLUMN ai_ff_routing_row.category               IS 'Cross-company or testimony category; only used to build the entry title on projection';
COMMENT ON COLUMN ai_ff_routing_row.source_timestamp       IS 'Cross-company and testimony only: time point hh:mm:ss in the meeting; used only to order rows in the matrix and Goldie Base cards; not shown, not projected';
COMMENT ON COLUMN ai_ff_routing_row.speaker_participant_id IS 'Testimony only: participant (ai_ff_meeting_participant.id) of the speaker, resolved from the prompt speaker_ref on write; name, organization, role and tags are read from that row';
COMMENT ON COLUMN ai_ff_routing_row.authorized             IS 'Authorize checkbox';
COMMENT ON COLUMN ai_ff_routing_row.in_playbook            IS 'Play candidate flag; for testimony only set on the signed row';
COMMENT ON COLUMN ai_ff_routing_row.fund_tag_ids           IS 'Fund tags (company_group ids) picked manually on the admin knowledge base; KB rows only; null means never picked';
COMMENT ON COLUMN ai_ff_routing_row.file_id                IS 'files.id (= ai_file_registry.file_id) currently online; the RAG entry is reached via ai_file_registry.ai_rag_entry_id';
COMMENT ON COLUMN ai_ff_routing_row.projection_status      IS 'NONE / PENDING / ONLINE / FAILED';
COMMENT ON COLUMN ai_ff_routing_row.projection_attempts    IS 'Retries so far';
COMMENT ON COLUMN ai_ff_routing_row.edited_by              IS 'Last inline save by';
COMMENT ON COLUMN ai_ff_routing_row.edited_at              IS 'Last inline save at';
DROP TRIGGER IF EXISTS trg_ai_ff_routing_row_updated_at ON ai_ff_routing_row;
CREATE TRIGGER trg_ai_ff_routing_row_updated_at BEFORE UPDATE ON ai_ff_routing_row
    FOR EACH ROW EXECUTE FUNCTION set_ai_ff_updated_at();

-- P8 审计
CREATE TABLE IF NOT EXISTS ai_ff_audit_log (
    id               BIGSERIAL     NOT NULL,
    organization_id  VARCHAR(36)   NOT NULL,
    event_type       VARCHAR(32)   NOT NULL,
    meeting_id       VARCHAR(36),
    target_type      VARCHAR(16),
    target_id        VARCHAR(36),
    before_value     JSONB,
    after_value      JSONB,
    operator         VARCHAR(36)   NOT NULL,
    triggered_by     VARCHAR(36),
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT pk_ai_ff_audit_log PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_ai_ff_audit_log_org_created ON ai_ff_audit_log (organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_ff_audit_log_meeting ON ai_ff_audit_log (meeting_id);
COMMENT ON TABLE  ai_ff_audit_log IS 'Fireflies audit events written by Python (identification, extraction, routing decisions and overrides)';
COMMENT ON COLUMN ai_ff_audit_log.event_type   IS 'IDENTIFY / EXTRACT / TYPE_CHANGE / COMPANY_CHANGE / CONTENT_EDIT / AUTHORIZE_CHANGE / PROJECTION_FAILED';
COMMENT ON COLUMN ai_ff_audit_log.target_type  IS 'COMPANY / ROUTING_ROW / PARTICIPANT; null for meeting-level events';
COMMENT ON COLUMN ai_ff_audit_log.target_id    IS 'Id of the affected object; null together with target_type';
COMMENT ON COLUMN ai_ff_audit_log.before_value IS 'Value before the change';
COMMENT ON COLUMN ai_ff_audit_log.after_value  IS 'Value after the change';
COMMENT ON COLUMN ai_ff_audit_log.operator     IS 'User id; "1" (system user) for automatic decisions';
COMMENT ON COLUMN ai_ff_audit_log.triggered_by IS 'User who caused a System action, if any';

-- X1 ai_file_registry：business_type 新取值 FIREFLIES / FIREFLIES_SUMMARY（只改注释）
COMMENT ON COLUMN ai_file_registry.business_type IS 'Business-type enum. purpose = rag rows: APP_USER / ADMIN_USER / APP_COMPANY / ADMIN_COMPANY / ADMIN_ORGANIZATION / KNOWLEDGE_BASE / PLAYBOOK / PARSING_MEMORY / SESSION_UPLOAD / FIREFLIES (meeting-derived KB body, cross-company and testimony entries) / FIREFLIES_SUMMARY (meeting summary entries, shown on the Memory panel). purpose = financial_extract rows: EXTRACT_FI_ACTUALS / EXTRACT_FI_PROFORMA = the statement type (Actuals / Proforma) the user declared for the file at upload, written by Java; NULL for files uploaded before sprint121. The knowledge-base and Memory panels filter on this column, so EXTRACT_FI_* rows never show there (the chatbot retrieval scope is decided by ai_rag_business_association, not by this table).';

-- 新空间业务类型 EXPERT_TESTIMONY / CROSS_COMPANY（代码种子 rag/domain/enums.py，只改注释）
COMMENT ON COLUMN ai_rag_business_association.business_type IS 'Business type code: APP_USER / ADMIN_USER / APP_COMPANY / ADMIN_COMPANY / ADMIN_ORGANIZATION / KNOWLEDGE_BASE / PLAYBOOK / PARSING_MEMORY / EXPERT_TESTIMONY / CROSS_COMPANY';

COMMIT;
```

> 注：Python 侧所有 `ai_ff_*` 表共用一个触发器函数 `set_ai_ff_updated_at()`，不按表各建一个（现有 V028 是按表建的，功能相同，只是少写 6 个同样的函数）。`ai_file_registry.business_type` 的注释沿用 V030 的原文，只在 rag 取值里追加 `FIREFLIES` / `FIREFLIES_SUMMARY`；`ai_rag_business_association.business_type` 同样沿用 V030 原文、追加 `EXPERT_TESTIMONY` / `CROSS_COMPANY`（空间业务类型的代码种子在 `rag/domain/enums.py`）。

## 3. 提取输入（`current_extraction_input`）示例

只存提取时用的页头输入，不存提取出的内容；字段名与结构开发时可调整。

```json
{
  "meetingType": "GS_FOUNDER",
  "companyIds": ["c-techvision"],
  "participants": [
    {"id": "p1", "role": "GS_STAFF", "organization": "Golden Section", "companyId": null, "expertiseTags": []},
    {"id": "p2", "role": "FOUNDER", "organization": "TechVision Inc.", "companyId": "c-techvision", "expertiseTags": []},
    {"id": "p3", "role": "UNIDENTIFIED", "organization": null, "companyId": null, "expertiseTags": []}
  ],
  "speakers": [
    {"speakerId": 0, "participantId": "p1"},
    {"speakerId": 1, "participantId": "p2"},
    {"speakerId": 2, "participantId": null}
  ]
}
```

含义：这版内容按「GS → 创始人、公司 TechVision、p3 未识别、2 号说话人没对上」提取。之后管理员把 p3 登记为 LP，最新识别结果与它不一致，即「参会人有改动」。

## 4. 定时清扫要接手的会议（供清扫功能设计参考）

开发设计 P1「卡死兜底」：这四类 Fireflies 本身不处理，交给定时清扫（单独设计，与本功能一起上线）。清扫没跑时也可人工用这几条查询应急。

```sql
-- 首轮停在识别中 / 提取中超过 1 小时：消息已进死信或过期，没人再处理
SELECT meeting_id, organization_id, fireflies_id, processing_stage, processing_started_at
FROM ai_ff_meeting_state
WHERE processing_stage <> 'DONE'
  AND processing_started_at < now() - interval '1 hour'
ORDER BY processing_started_at;

-- 已投递超过 1 小时，Python 仍没有状态行（首次连接回溯 14 天、消息积压时可能误报，误报的重投 Python 按会议去重）
SELECT m.id, m.organization_id, m.fireflies_id, m.dispatched_at
FROM ff_meeting_meta_info m
LEFT JOIN ai_ff_meeting_state s ON s.meeting_id = m.id
WHERE m.dispatched_at < now() - interval '1 hour'
  AND s.id IS NULL
ORDER BY m.dispatched_at;

-- 非首轮的提取任务卡在 RUNNING 超过 1 小时（首轮提取在 processing_stage = 'EXTRACTING'，归第一条）
SELECT meeting_id, organization_id, extraction_trigger, extraction_started_at
FROM ai_ff_meeting_state
WHERE extraction_status = 'RUNNING'
  AND processing_stage = 'DONE'
  AND extraction_started_at < now() - interval '1 hour';

-- 证词补抽卡在 RUNNING 超过 1 小时
SELECT meeting_id, id AS participant_id, updated_at
FROM ai_ff_meeting_participant
WHERE testimony_backfill_status = 'RUNNING'
  AND updated_at < now() - interval '1 hour';
```

人工应急的恢复办法：前两类删掉第一类的状态行（产出在下次开跑时会先删），都把 `dispatched_at` 置空，下一次拉取 Java 自动补投，Python 当新会议从头处理（J2「投递与补投」、P1 `processing_started_at`）；第三类按设计 6.11 的作废改状态表（`extraction_status = 'VOIDED'`，会议转 Pending 待识别）；第四类把 `testimony_backfill_status` 置为 `FAILED`。
