# EPIC: Manual Uploads with OCR — 技术设计文档

> **Asana EPIC**: [Manual Uploads with OCR](https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1210456521366357)
> **状态**: 技术方案设计
> **创建日期**: 2026-04-16
> **技术栈**: React (CIOaas-web) + Python FastAPI (CIOaas-python) + Spring Cloud Gateway (CIOaas-api)

---

## 1. 需求概述

### 1.1 一句话描述

用户无需集成 QuickBooks 等系统，直接上传 PDF/Excel/图片等财务文件，系统通过 OCR + AI 自动提取、分类、映射财务数据，用户在线审核确认后写入 Looking Glass 数据库。

### 1.2 业务目标

| 目标 | 说明 |
|------|------|
| 扩大可服务市场 | 覆盖没有 QuickBooks 等集成的公司 |
| 降低入驻门槛 | 早期创业公司无需技术集成即可使用 |
| 非技术用户参与 | 上传原始文件即可获取财务洞察 |

### 1.3 6 步工作流

```
① 上传文件 → ② 数据提取(OCR/Excel) → ③ AI 账户映射 → ④ 并排审核编辑 → ⑤ 写入 LG → ⑥ 系统持续学习
```

### 1.4 子任务清单

| # | 子任务 | 负责人 | 核心内容 |
|---|--------|--------|----------|
| 1 | Allow Users to upload a financial document | Jesús H Peralta | 支持 PDF/Excel/CSV/图片，拖拽+选择上传，单文件 ≤20MB，批量 ≤100MB |
| 2 | Extraction of Financial Data - AI + OCR | Jesús H Peralta | 对扫描 PDF/图片执行 OCR（eSapiens），检测财务表格，识别文档类型 |
| 3 | Extraction of Financial Data - Excel | Jesús H Peralta | 直接解析 Excel/CSV 表格数据，处理合并单元格、公式求值 |
| 4 | Add AI-Assisted Account Mapping Suggestions | Liang Chunru | AI 自动映射到 LG 标准财务分类（16+ 类别） |
| 5 | Side-by-Side Review & Inline Editing | Jesús H Peralta | 左侧原始文档 + 右侧提取数据，支持 Raw/Standardized 切换和内联编辑 |
| 6 | Write data to LG Schema | Jesús H Peralta | 冲突检测 + Overwrite/Skip/Cancel + 审计日志 + 版本控制 |
| 7 | Add Note Field to Importing During Data Validation | Jesús H Peralta | 冲突解决时可添加备注（≤2000 字），写入后只读 |
| 8 | System Learning and Continuous Improvement | Liang Chunru | 保存并复用公司级映射历史，增量提高准确率 |

---

## 2. 系统架构

### 2.1 总体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    CIOaas-web (React)                        │
│  UploadPage → ExtractingPage → MappingPage → ReviewPage     │
│       ↕              ↕              ↕            ↕          │
│    FileAPI      StatusPolling   MappingAPI    CommitAPI      │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────┴──────────────────────────────────┐
│                  CIOaas-api (Java Gateway)                   │
│              路由转发 /api/v1/ocr/** → Python                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│                CIOaas-python (FastAPI)                        │
│                                                              │
│  ┌─────────┐  ┌───────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Upload  │→ │ Extractor │→ │ AI Mapper│→ │ LG Writer  │  │
│  │ Service │  │ (OCR/XLSX)│  │ (LLM)    │  │ (DB)       │  │
│  └─────────┘  └───────────┘  └──────────┘  └────────────┘  │
│       ↕            ↕              ↕              ↕          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              PostgreSQL + S3 (File Storage)           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Pipeline 状态机

```
UPLOAD → EXTRACT → MAP → REVIEW → VALIDATE → COMMIT
  │         │        │       │         │         │
  ↓         ↓        ↓       ↓         ↓         ↓
FAILED   FAILED   FAILED  (user)   CONFLICT  FAILED
                           edit    RESOLUTION
```

每一步均支持失败回退和中间状态持久化。用户关闭浏览器后重新打开可恢复到上次进度。

---

## 3. 数据模型

### 3.1 核心表结构

```sql
-- 上传会话
CREATE TABLE ocr_upload_session (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id        BIGINT NOT NULL REFERENCES company(id),
    uploaded_by       BIGINT NOT NULL REFERENCES sys_user(id),
    status            VARCHAR(20) NOT NULL DEFAULT 'UPLOADING',
        -- UPLOADING / EXTRACTING / MAPPING / REVIEWING / COMMITTED / FAILED
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 上传文件
CREATE TABLE ocr_uploaded_file (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id        UUID NOT NULL REFERENCES ocr_upload_session(id),
    filename          VARCHAR(500) NOT NULL,
    file_type         VARCHAR(10) NOT NULL,  -- PDF / XLSX / CSV / JPG / PNG / TIFF
    file_size         BIGINT NOT NULL,
    s3_key            VARCHAR(1000) NOT NULL,
    status            VARCHAR(20) NOT NULL DEFAULT 'PENDING',
        -- PENDING / UPLOADED / EXTRACTING / EXTRACTED / FAILED
    error_message     TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 提取的表格
CREATE TABLE ocr_extracted_table (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id           UUID NOT NULL REFERENCES ocr_uploaded_file(id),
    table_index       INT NOT NULL DEFAULT 0,
    document_type     VARCHAR(20) NOT NULL DEFAULT 'MISC',
        -- PNL / BALANCE_SHEET / CASH_FLOW / PROFORMA / MISC
    doc_type_confidence VARCHAR(10) NOT NULL DEFAULT 'LOW',
        -- HIGH / MEDIUM / LOW
    currency          VARCHAR(10) DEFAULT 'USD',
    source_page       INT,            -- PDF 页码
    source_sheet_name VARCHAR(200),   -- Excel sheet 名
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 提取的行数据
CREATE TABLE ocr_extracted_row (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_id          UUID NOT NULL REFERENCES ocr_extracted_table(id),
    row_index         INT NOT NULL,
    account_label     VARCHAR(500) NOT NULL,
    section_header    VARCHAR(500),     -- 所属 section（如 "Operating Expenses"）
    values            JSONB NOT NULL,   -- {"2024-01": 12345.67, "2024-02": 13000.00}
    is_header         BOOLEAN DEFAULT false,
    is_total          BOOLEAN DEFAULT false,
    user_edited       BOOLEAN DEFAULT false,
    deleted           BOOLEAN DEFAULT false  -- 用户删除的噪音行
);

-- AI 映射结果
CREATE TABLE ocr_mapping_result (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    row_id                UUID NOT NULL REFERENCES ocr_extracted_row(id),
    lg_category           VARCHAR(50) NOT NULL,
        -- REVENUE / COGS / SM_EXPENSE / RD_EXPENSE / GA_EXPENSE
        -- SM_PAYROLL / RD_PAYROLL / GA_PAYROLL / OOE
        -- CASH / AR / RD_CAPITALIZED / OTHER_ASSETS
        -- AP / LONG_TERM_DEBT / OTHER_LIABILITIES
    confidence            VARCHAR(10) NOT NULL,  -- HIGH / MEDIUM / LOW
    source                VARCHAR(20) NOT NULL,  -- RULE_ENGINE / COMPANY_MEMORY / LLM
    original_ai_suggestion VARCHAR(50),           -- AI 原始建议（用户覆盖后保留）
    reasoning             TEXT,                   -- LLM 推理说明
    user_note             VARCHAR(2000),          -- 用户备注
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 公司级映射记忆（AI 学习基础）
CREATE TABLE ocr_company_mapping_memory (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id            BIGINT NOT NULL REFERENCES company(id),
    account_label_pattern VARCHAR(500) NOT NULL,
    lg_category           VARCHAR(50) NOT NULL,
    frequency             INT NOT NULL DEFAULT 1,  -- 被确认次数
    last_used_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, account_label_pattern)
);

-- 数据冲突记录
CREATE TABLE ocr_conflict_record (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id        UUID NOT NULL REFERENCES ocr_upload_session(id),
    company_id        BIGINT NOT NULL,
    document_type     VARCHAR(20) NOT NULL,
    reporting_month   INT NOT NULL,
    reporting_year    INT NOT NULL,
    data_classification VARCHAR(20) NOT NULL,  -- HISTORICAL / FORECAST
    resolution        VARCHAR(20),  -- OVERWRITE / SKIP / CANCEL
    user_note         VARCHAR(2000),
    resolved_by       BIGINT REFERENCES sys_user(id),
    resolved_at       TIMESTAMPTZ
);
```

### 3.2 索引设计

```sql
-- 公司记忆模糊匹配（trigram）
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_mapping_memory_label_trgm
    ON ocr_company_mapping_memory
    USING gin (account_label_pattern gin_trgm_ops);

CREATE INDEX idx_mapping_memory_company
    ON ocr_company_mapping_memory (company_id);

-- 冲突检测
CREATE INDEX idx_financial_data_conflict
    ON financial_data (company_id, document_type, data_classification, reporting_month, reporting_year);

-- Session 查询
CREATE INDEX idx_upload_session_company
    ON ocr_upload_session (company_id, created_at DESC);

-- 行数据查询
CREATE INDEX idx_extracted_row_table
    ON ocr_extracted_row (table_id, row_index);
```

---

## 4. AI 映射引擎设计

### 4.1 三层架构

```
┌─────────────────────────────────────┐
│  Layer 3: LLM 兜底 (Claude API)     │  ← 只处理 Layer 1+2 无法映射的（~15%）
├─────────────────────────────────────┤
│  Layer 2: 公司记忆匹配              │  ← 基于历史映射的精确/模糊匹配（~25%）
├─────────────────────────────────────┤
│  Layer 1: 规则引擎 (Keywords)        │  ← 确定性规则，零成本，最快（~60%）
└─────────────────────────────────────┘
```

**为什么不全部用 LLM？**

| 方案 | 优点 | 缺点 |
|------|------|------|
| 全 LLM | 最灵活 | 成本高（每次上传可能 100+ 行项），延迟大，不可预测 |
| 全规则引擎 | 零成本，可预测 | 覆盖率不足，无法处理不规范标签 |
| **三层混合（推荐）** | 成本可控，渐进增强 | 实现复杂度稍高 |

### 4.2 LG 标准财务分类（16 类）

| 分类 | 枚举值 | 报表类型 |
|------|--------|----------|
| Revenue | `REVENUE` | P&L |
| COGS | `COGS` | P&L |
| S&M Expenses | `SM_EXPENSE` | P&L |
| R&D Expenses | `RD_EXPENSE` | P&L |
| G&A Expenses | `GA_EXPENSE` | P&L |
| S&M Payroll | `SM_PAYROLL` | P&L |
| R&D Payroll | `RD_PAYROLL` | P&L |
| G&A Payroll | `GA_PAYROLL` | P&L |
| Other Operating Expenses | `OOE` | P&L |
| Cash | `CASH` | Balance Sheet |
| Accounts Receivable | `AR` | Balance Sheet |
| R&D Capitalized | `RD_CAPITALIZED` | Balance Sheet |
| Other Assets | `OTHER_ASSETS` | Balance Sheet |
| Accounts Payable | `AP` | Balance Sheet |
| Long Term Debt | `LONG_TERM_DEBT` | Balance Sheet |
| Other Liabilities | `OTHER_LIABILITIES` | Balance Sheet |

### 4.3 Layer 1：规则引擎

#### 4.3.1 关键词优先级体系

规则引擎按 **优先级从高到低** 匹配，解决关键词冲突：

```
Priority 1（最精确）: R&D Capitalized, AP, AR, Long Term Debt
Priority 2（上下文相关）: S&M Payroll, R&D Payroll（需 section 上下文）
Priority 3（Payroll 兜底）: G&A Payroll; COGS（排除 R&D 关键词）
Priority 4（费用大类）: Revenue, S&M Expense, R&D Expense, G&A Expense
Priority 5（Balance Sheet）: Cash, Other Assets, Other Liabilities
```

#### 4.3.2 完整映射规则

**Revenue**
- 关键词: `sales`, `revenue`, `income`, `fees`, `subscriptions`, `gross receipts`
- 排除词: `cost of`, `expense`, `other income`
- 特殊: `refund`, `returns`, `contra` → 仍映射为 Revenue，但标记为负值

**COGS**
- 关键词: `cogs`, `cost of goods`, `cost of revenue`, `materials`, `inventory`, `supplies used`, `direct labor`
- 排除词: `research`, `development`
- 特殊: `hosting`, `cloud`, `server`, `bandwidth` — **需上下文判断**:
  - SaaS 公司 → COGS
  - 非 SaaS 公司 → R&D Expenses

**S&M Expenses**（不含 Payroll）
- Marketing: `marketing`, `advertising`, `ads`, `promotion`, `campaign`, `digital marketing`, `seo`, `sem`, `ppc`, `social media`, `brand`, `branding`, `public relations`, `pr`, `media`
- Sales: `sales commission`, `business development`, `customer acquisition`, `lead generation`
- Customer/Channel: `customer success`, `customer support`, `merchant fees`, `payment processing fees`, `referral fees`
- Events: `trade show`, `conference`, `event`, `sponsorship`
- 排除词: `payroll`, `salary`, `wages`

**R&D Expenses**（不含 Payroll）
- 关键词: `research`, `development`, `r&d`, `r and d`, `product development`, `engineering`, `software development`, `technical development`, `technical consulting`, `product design`, `ux research`, `development tools`, `software licenses`, `testing`, `qa`, `quality assurance`, `devops`, `infrastructure engineering`
- 排除词: `payroll`, `salary`, `capitalized`

**G&A Expenses**（不含 Payroll）
- Overhead: `general and administrative`, `g&a`, `overhead`, `corporate expense`, `office expense`
- Facilities: `rent`, `lease`, `utilities`, `office supplies`, `internet`, `phone`, `equipment`
- Professional Services: `legal`, `legal fees`, `accounting`, `audit`, `consulting`, `professional services`
- Admin: `hr`, `human resources`, `recruiting`, `insurance`, `licenses`, `permits`
- 排除词: `payroll`, `salary`

**Payroll 分类（三级）**
- 通用关键词: `wages`, `salary`, `payroll`, `compensation`, `benefits`, `payroll taxes`
- 判断部门上下文:
  - 行标签或 section header 含 `sales`, `marketing`, `s&m` → **S&M Payroll**
  - 行标签或 section header 含 `r&d`, `research`, `engineering`, `development` → **R&D Payroll**
  - 无法判断或含 `g&a`, `general`, `admin` → **G&A Payroll**（兜底）
- **Nico Carlson（财务 SME）确认**: 无法判断部门时一律默认 G&A Payroll，标记 LOW confidence 提醒用户审核

**Other Operating Expenses (OOE)**
- Other Income 和 Other Expense 均映射到此
- 同一周期两者共存时：`net = expense - income`，负值表示 income 大于 expense
- **注意**: OOE 在 LG 中是计算指标，写入时需特殊处理（见 Section 7.3）

**Cash**
- 关键词: `cash`, `bank`, `checking`, `savings`, `cash equivalents`, `money market`, `treasury`, `short-term investments`, `marketable securities`

**Accounts Receivable**
- 关键词: `accounts receivable`, `a/r`, `receivables`, `trade receivables`, `unbilled revenue`, `contract asset`

**R&D Capitalized**
- **需要双重信号**:
  - 信号 A (Capitalization): `capitalized`, `capitalised`, `capitalized r&d`, `capitalized research`, `capitalized development`, `internal-use software`
  - 信号 B (Amortization): `amortization`, `amortization of intangibles`, `amortization of software`, `amortized development costs`, `intangible assets`
  - 必须满足: (信号 A + R&D 上下文) 或 (信号 B)
- **Nico Carlson 确认**: amortization 本身就是强信号，因为它适用于无形资产（专利、软件）

**Other Assets**
- 条件: 被识别为 Asset 分类，但不属于 Cash / AR / R&D Capitalized

**Accounts Payable**
- 关键词: `accounts payable`, `a/p`, `payables`, `trade payables`

**Long Term Debt**
- 关键词: `long term debt`, `loan`, `note payable`, `term loan`, `debt`, `convertible note`, `venture debt`, `credit facility`, `line of credit`, `revolving`
- 排除词: `short term`

**Other Liabilities**
- 条件: 被识别为 Liability 分类，但不属于 AP / Long Term Debt

#### 4.3.3 规则引擎实现

```python
from dataclasses import dataclass
from enum import Enum

class LGCategory(str, Enum):
    REVENUE = "Revenue"
    COGS = "COGS"
    SM_EXPENSE = "S&M Expenses"
    RD_EXPENSE = "R&D Expenses"
    GA_EXPENSE = "G&A Expenses"
    SM_PAYROLL = "S&M Payroll"
    RD_PAYROLL = "R&D Payroll"
    GA_PAYROLL = "G&A Payroll"
    OOE = "Other Operating Expenses"
    CASH = "Cash"
    AR = "Accounts Receivable"
    RD_CAPITALIZED = "R&D Capitalized"
    OTHER_ASSETS = "Other Assets"
    AP = "Accounts Payable"
    LONG_TERM_DEBT = "Long Term Debt"
    OTHER_LIABILITIES = "Other Liabilities"

@dataclass
class MappingRule:
    category: LGCategory
    keywords: list[str]
    negative_keywords: list[str]    # 排除词
    priority: int                    # 数字越小优先级越高
    requires_context: list[str]      # 需要同时出现的上下文关键词

RULES = [
    # === Priority 1: 最精确的匹配 ===
    MappingRule(
        category=LGCategory.RD_CAPITALIZED,
        keywords=["capitalized r&d", "capitalized research",
                  "capitalized development", "amortization of software",
                  "amortization of intangibles", "internal-use software",
                  "amortized development costs"],
        negative_keywords=[],
        priority=1,
        requires_context=[]
    ),
    MappingRule(
        category=LGCategory.AP,
        keywords=["accounts payable", "a/p", "trade payables"],
        negative_keywords=[],
        priority=1,
        requires_context=[]
    ),
    MappingRule(
        category=LGCategory.AR,
        keywords=["accounts receivable", "a/r", "trade receivables",
                  "unbilled revenue", "contract asset"],
        negative_keywords=[],
        priority=1,
        requires_context=[]
    ),
    MappingRule(
        category=LGCategory.LONG_TERM_DEBT,
        keywords=["long term debt", "term loan", "convertible note",
                  "venture debt", "credit facility", "revolving",
                  "note payable"],
        negative_keywords=["short term"],
        priority=1,
        requires_context=[]
    ),

    # === Priority 2: Payroll（需部门上下文） ===
    MappingRule(
        category=LGCategory.SM_PAYROLL,
        keywords=["wages", "salary", "payroll", "compensation", "benefits"],
        negative_keywords=[],
        priority=2,
        requires_context=["sales", "marketing", "s&m"]
    ),
    MappingRule(
        category=LGCategory.RD_PAYROLL,
        keywords=["wages", "salary", "payroll", "compensation", "benefits"],
        negative_keywords=[],
        priority=2,
        requires_context=["r&d", "research", "engineering", "development"]
    ),

    # === Priority 3: Payroll 兜底 + COGS ===
    MappingRule(
        category=LGCategory.GA_PAYROLL,
        keywords=["wages", "salary", "payroll", "compensation",
                  "benefits", "payroll taxes"],
        negative_keywords=[],
        priority=3,
        requires_context=[]
    ),
    MappingRule(
        category=LGCategory.COGS,
        keywords=["cogs", "cost of goods", "cost of revenue",
                  "materials", "inventory", "direct labor", "supplies used"],
        negative_keywords=["research", "development"],
        priority=3,
        requires_context=[]
    ),

    # === Priority 4: 费用大类 ===
    MappingRule(
        category=LGCategory.REVENUE,
        keywords=["revenue", "sales", "income", "fees",
                  "subscriptions", "gross receipts"],
        negative_keywords=["cost of", "expense", "other income"],
        priority=4,
        requires_context=[]
    ),
    MappingRule(
        category=LGCategory.SM_EXPENSE,
        keywords=["marketing", "advertising", "promotion", "campaign",
                  "commission", "customer acquisition", "lead generation",
                  "trade show", "sponsorship"],
        negative_keywords=["payroll", "salary"],
        priority=4,
        requires_context=[]
    ),
    MappingRule(
        category=LGCategory.RD_EXPENSE,
        keywords=["research", "development", "r&d", "engineering",
                  "product development", "software development",
                  "technical consulting", "qa", "devops"],
        negative_keywords=["payroll", "salary", "capitalized"],
        priority=4,
        requires_context=[]
    ),
    MappingRule(
        category=LGCategory.GA_EXPENSE,
        keywords=["general and administrative", "g&a", "overhead",
                  "rent", "lease", "utilities", "legal", "audit",
                  "accounting", "insurance", "hr", "recruiting"],
        negative_keywords=["payroll", "salary"],
        priority=4,
        requires_context=[]
    ),

    # === Priority 5: Balance Sheet 项 ===
    MappingRule(
        category=LGCategory.CASH,
        keywords=["cash", "bank", "checking", "savings",
                  "cash equivalents", "money market", "treasury"],
        negative_keywords=[],
        priority=5,
        requires_context=[]
    ),
]

def rule_engine_match(
    label: str,
    section_context: str = ""
) -> tuple[LGCategory | None, str]:
    """
    规则引擎匹配。
    返回 (category, confidence)。
    confidence: HIGH = priority <=2, MEDIUM = priority <=4, LOW = priority 5
    """
    label_lower = label.lower().strip()
    context_lower = section_context.lower()

    sorted_rules = sorted(RULES, key=lambda r: r.priority)

    for rule in sorted_rules:
        if any(neg in label_lower for neg in rule.negative_keywords):
            continue
        keyword_hit = any(kw in label_lower for kw in rule.keywords)
        if not keyword_hit:
            continue
        if rule.requires_context:
            context_hit = any(
                ctx in label_lower or ctx in context_lower
                for ctx in rule.requires_context
            )
            if not context_hit:
                continue
        confidence = (
            "HIGH" if rule.priority <= 2
            else "MEDIUM" if rule.priority <= 4
            else "LOW"
        )
        return rule.category, confidence

    return None, "UNMAPPED"
```

### 4.4 Layer 2：公司记忆匹配

```python
async def company_memory_match(
    company_id: int,
    label: str,
    db: AsyncSession
) -> tuple[LGCategory | None, str]:
    """查找该公司历史上对类似标签的映射"""

    # 精确匹配
    exact = await db.execute(
        select(CompanyMappingMemory)
        .where(
            CompanyMappingMemory.company_id == company_id,
            func.lower(CompanyMappingMemory.account_label_pattern) == label.lower()
        )
        .order_by(CompanyMappingMemory.frequency.desc())
    )
    if result := exact.scalar_one_or_none():
        return result.lg_category, "HIGH"

    # 模糊匹配（trigram 相似度 > 0.6）
    fuzzy = await db.execute(
        select(CompanyMappingMemory)
        .where(
            CompanyMappingMemory.company_id == company_id,
            func.similarity(
                CompanyMappingMemory.account_label_pattern, label
            ) > 0.6
        )
        .order_by(
            func.similarity(CompanyMappingMemory.account_label_pattern, label).desc()
        )
        .limit(1)
    )
    if result := fuzzy.scalar_one_or_none():
        return result.lg_category, "MEDIUM"

    return None, "UNMAPPED"
```

### 4.5 Layer 3：LLM 提示词设计

#### 4.5.1 System Prompt

```
You are a financial data classification engine for Looking Glass (LG),
a SaaS platform that helps investors analyze portfolio company financials.

Your job: map a financial line item to exactly ONE LG category.

## LG Categories (ONLY use these, no others)

### Income Statement (P&L)
- Revenue — top-line sales, fees, subscriptions, service income
- COGS — direct costs: materials, hosting, infrastructure, direct labor
- S&M Expenses — marketing, advertising, commissions, events (NOT payroll)
- R&D Expenses — engineering, product dev, technical consulting (NOT payroll)
- G&A Expenses — rent, legal, accounting, insurance, admin overhead (NOT payroll)
- S&M Payroll — wages/salary/benefits for sales & marketing staff
- R&D Payroll — wages/salary/benefits for engineering/R&D staff
- G&A Payroll — wages/salary/benefits for admin/G&A staff (DEFAULT for unspecified payroll)
- Other Operating Expenses — other income/expense items; if both exist, net them

### Balance Sheet
- Cash — cash, bank accounts, money market, short-term investments
- Accounts Receivable — trade receivables, unbilled revenue
- R&D Capitalized — capitalized software/R&D costs AND their amortization
- Other Assets — any asset not in the above 3 categories
- Accounts Payable — trade payables
- Long Term Debt — loans, notes payable, credit facilities, convertible notes
- Other Liabilities — any liability not AP or Long Term Debt

## Rules
1. Return EXACTLY one category from the list above
2. If the line item is clearly a subtotal/header row, return "SKIP"
3. For payroll without department context, default to "G&A Payroll"
4. For "hosting/cloud/server": if the company is SaaS → COGS; otherwise → R&D Expenses
5. Revenue contra items (refunds, returns) → still "Revenue" but flag as negative
6. "R&D Capitalized" requires BOTH a capitalization/amortization signal AND R&D context
```

#### 4.5.2 User Prompt Template

```
Map these financial line items to LG categories.

Company context:
- Industry: {industry}
- Document type: {document_type}
- Section header (if any): {section_header}

Line items to classify:
{line_items_json}

Respond in JSON array format:
[
  {
    "row_index": 0,
    "label": "original label",
    "category": "LG Category Name",
    "confidence": "HIGH|MEDIUM|LOW",
    "reasoning": "brief explanation"
  }
]

IMPORTANT:
- Only use categories from the system prompt
- "confidence" = HIGH if keywords clearly match, MEDIUM if contextual inference, LOW if uncertain
- Batch all items in one response
```

#### 4.5.3 提示词设计关键决策

| 决策 | 原因 |
|------|------|
| System prompt 列出全部 16 个分类 + 规则 | LLM 需要完整分类空间，防止幻觉出不存在的分类 |
| 传入 `document_type` 上下文 | Balance Sheet 里的 "Revenue" 可能是 "Deferred Revenue"（负债） |
| 传入 `section_header` | "R&D Department" section 下的 "Salary" → R&D Payroll |
| 传入 `industry` | SaaS 公司的 "hosting" → COGS；制造业 → G&A |
| 批量处理而非逐行 | 减少 API 调用次数，LLM 利用同文档上下文做更好的判断 |
| 要求返回 `reasoning` | 审计可追溯，用户审核时可参考 AI 推理依据 |

### 4.6 三层协调逻辑

```python
async def map_extracted_rows(
    rows: list[ExtractedRow],
    company_id: int,
    document_type: str,
    industry: str,
    db: AsyncSession
) -> list[MappingResult]:
    results = []
    llm_batch = []

    for row in rows:
        if row.is_header or row.is_total:
            continue

        # === Layer 1: 规则引擎 ===
        category, confidence = rule_engine_match(
            row.account_label,
            section_context=row.section_header or ""
        )
        if category and confidence in ("HIGH", "MEDIUM"):
            results.append(MappingResult(
                row_id=row.id,
                lg_category=category,
                confidence=confidence,
                source="RULE_ENGINE"
            ))
            continue

        # === Layer 2: 公司记忆 ===
        category, confidence = await company_memory_match(
            company_id, row.account_label, db
        )
        if category:
            results.append(MappingResult(
                row_id=row.id,
                lg_category=category,
                confidence=confidence,
                source="COMPANY_MEMORY"
            ))
            continue

        # === 收集到 LLM 批次 ===
        llm_batch.append(row)

    # === Layer 3: LLM 批量处理 ===
    if llm_batch:
        llm_results = await call_llm_mapping(
            llm_batch, company_id, document_type, industry
        )
        results.extend(llm_results)

    return results
```

---

## 5. 文档类型识别算法

### 5.1 评分机制

```python
def classify_document_type(
    sheet_name: str,
    row_labels: list[str],
    structure: dict
) -> tuple[str, str]:
    """
    返回 (document_type, confidence)。
    基于 sheet 名称、行标签模式、结构线索三类信号加权评分。
    """
    scores = {"PNL": 0, "BALANCE_SHEET": 0, "CASH_FLOW": 0, "PROFORMA": 0}

    # Signal 1: Sheet name (weight: 3)
    sheet_lower = (sheet_name or "").lower()
    SHEET_SIGNALS = {
        "PNL": ["p&l", "income", "profit", "loss", "pnl"],
        "BALANCE_SHEET": ["balance", "assets", "liabilities", "bs"],
        "CASH_FLOW": ["cash flow", "cashflow", "cf"],
        "PROFORMA": ["forecast", "proforma", "projection", "budget"]
    }
    for doc_type, keywords in SHEET_SIGNALS.items():
        if any(kw in sheet_lower for kw in keywords):
            scores[doc_type] += 3

    # Signal 2: Row label patterns (weight: 2 per match)
    labels_text = " ".join(l.lower() for l in row_labels)
    PNL_INDICATORS = ["revenue", "cogs", "gross margin", "ebitda",
                      "net income", "operating income"]
    BS_INDICATORS = ["total assets", "total liabilities", "equity",
                     "current assets", "current liabilities"]
    CF_INDICATORS = ["operating activities", "investing activities",
                     "financing activities", "net cash"]
    scores["PNL"] += sum(2 for ind in PNL_INDICATORS if ind in labels_text)
    scores["BALANCE_SHEET"] += sum(2 for ind in BS_INDICATORS if ind in labels_text)
    scores["CASH_FLOW"] += sum(2 for ind in CF_INDICATORS if ind in labels_text)

    # Signal 3: Structural cues (weight: 4-5)
    if structure.get("has_beginning_end_cash"):
        scores["CASH_FLOW"] += 4
    if structure.get("assets_eq_liabilities_plus_equity"):
        scores["BALANCE_SHEET"] += 5

    # 选最高分
    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score >= 8:
        return best_type, "HIGH"
    elif best_score >= 4:
        return best_type, "MEDIUM"
    elif best_score >= 2:
        return best_type, "LOW"
    else:
        return "MISC", "LOW"
```

### 5.2 多类型混合文档处理

- 多页 PDF: 按页分组，每页独立识别 document_type
- 多 sheet Excel: 每个 sheet 独立识别
- 用户可在审核页面手动修改文档类型和合并/拆分表格

---

## 6. 前端设计（React）

### 6.1 页面路由

```
/financial-upload
  ├── Step 1: UploadPage          — 文件上传 + 队列管理
  ├── Step 2: ExtractingPage      — 提取进度（自动，无交互）
  ├── Step 3: ReviewPage          — 并排审核 + 内联编辑（核心页面）
  │     ├── SourcePanel (左)      — PDF 预览 / Excel 预览
  │     ├── DataPanel (右)        — Raw View / Standardized View 切换
  │     └── MappingPanel (右下)   — 分类映射 + 置信度标签
  ├── Step 4: ConflictPage        — 数据冲突解决 + Note 字段
  └── Step 5: ConfirmPage         — 最终确认 + 写入 LG
```

### 6.2 前端状态管理（dva model）

```typescript
// models/ocrUpload.ts
interface OCRUploadState {
  currentStep: 0 | 1 | 2 | 3 | 4;
  sessionId: string | null;

  // Step 1: Upload
  fileList: UploadFile[];
  uploadProgress: Record<string, number>;  // fileId → progress %

  // Step 2: Extraction
  extractionStatus: 'idle' | 'processing' | 'done' | 'error';
  extractedTables: ExtractedTable[];

  // Step 3: Review
  activeTableId: string | null;
  viewMode: 'raw' | 'standardized';
  editedRows: Record<string, Partial<ExtractedRow>>;  // rowId → edits
  mappingOverrides: Record<string, string>;            // rowId → new category

  // Step 4: Conflict Resolution
  conflicts: ConflictItem[];
  resolutions: Record<string, 'OVERWRITE' | 'SKIP' | 'CANCEL'>;
  notes: Record<string, string>;  // conflictId → user note

  // Step 5: Commit
  commitStatus: 'idle' | 'committing' | 'done' | 'error';
}
```

### 6.3 核心页面：并排审核

```
┌──────────────────────────┬──────────────────────────────────┐
│                          │  [Raw View] [Standardized View]  │
│   Original Document      │                                  │
│                          │  ┌─ Table 1: Income Statement ─┐ │
│   ┌──────────────────┐   │  │ Account    │ Jan  │ Feb │...│ │
│   │  PDF Page 1      │   │  │────────────┼──────┼─────┤   │ │
│   │                  │   │  │ Revenue ✓  │12,345│13,00│   │ │
│   │  ← Page Nav →    │   │  │ COGS    ✓  │ 4,500│ 4,80│   │ │
│   │                  │   │  │ Hosting ⚠  │ 1,200│ 1,30│   │ │
│   └──────────────────┘   │  │ Salary  ⚠  │ 8,000│ 8,20│   │ │
│                          │  └──────────────────────────────┘ │
│                          │                                  │
│                          │  ✓ HIGH  ⚠ MEDIUM  ✗ UNMAPPED   │
└──────────────────────────┴──────────────────────────────────┘
```

关键交互:
- 点击右侧行 → 左侧 PDF/Excel 定位到对应源位置
- 双击数值可内联编辑
- 在 Standardized View 中可通过下拉菜单修改分类
- 所有编辑实时 autosave（debounce 500ms）
- 大数据表使用 `react-window` 虚拟滚动

### 6.4 硬验证规则（Step 3 → Step 4 的前置条件）

三要素必须完整：
1. **Account Name** — 不为空
2. **Value** — 必须是数值
3. **Month** — 不为空且不是 "Unidentified"

不满足时阻止进入下一步，精确提示: 如 `"2024_PnL.pdf" → Table 1 → Row 5: Account Name is empty"`

---

## 7. API 设计

### 7.1 接口列表

```yaml
# === Upload ===
POST   /api/v1/ocr/sessions                       # 创建上传会话
POST   /api/v1/ocr/sessions/{id}/files             # 上传文件 (multipart)
DELETE /api/v1/ocr/sessions/{id}/files/{fileId}     # 删除队列中的文件
POST   /api/v1/ocr/sessions/{id}/extract           # 触发提取

# === Extraction Status ===
GET    /api/v1/ocr/sessions/{id}/status            # 获取会话状态（轮询）
GET    /api/v1/ocr/sessions/{id}/tables            # 获取提取的表格列表
GET    /api/v1/ocr/tables/{tableId}/rows           # 获取表格行数据

# === Review & Edit ===
PATCH  /api/v1/ocr/tables/{tableId}/rows/{rowId}            # 编辑行数据
PATCH  /api/v1/ocr/tables/{tableId}/rows/{rowId}/mapping    # 修改映射
DELETE /api/v1/ocr/tables/{tableId}/rows/{rowId}            # 删除噪音行
DELETE /api/v1/ocr/tables/{tableId}/columns/{colKey}        # 删除噪音列

# === Conflict & Commit ===
POST   /api/v1/ocr/sessions/{id}/validate          # 触发验证 + 冲突检测
POST   /api/v1/ocr/sessions/{id}/resolve           # 提交冲突解决方案
POST   /api/v1/ocr/sessions/{id}/commit            # 写入 LG
```

### 7.2 Gateway 路由配置

在 CIOaas-api 的 Gateway 配置中添加:

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: ocr-service
          uri: http://cioaas-python:8090
          predicates:
            - Path=/api/v1/ocr/**
          filters:
            - StripPrefix=0
```

### 7.3 OOE 写入特殊处理

OOE（Miscellaneous Operating Expenses）在 LG 中是计算字段，不能直接写入。写入逻辑:

```python
# 在 LG Writer 中
if mapping.lg_category == LGCategory.OOE:
    # 拆分为 other_income / other_expense 独立字段
    if row_value >= 0:
        write_to_field = "other_expense"
    else:
        write_to_field = "other_income"
        row_value = abs(row_value)
```

---

## 8. 边界情况处理

| 边界情况 | 处理方案 |
|----------|----------|
| **同一行匹配多个分类** | 优先级排序（priority 字段），最精确的匹配胜出 |
| **"Cloud Hosting" — COGS 还是 R&D？** | 传入 company industry: SaaS → COGS，其他 → R&D |
| **Payroll 无部门上下文** | 默认 G&A Payroll，置信度 LOW，提醒用户审核 |
| **多页 PDF 含多种报表** | 按页分组独立识别 document_type，用户可手动合并/拆分 |
| **Excel 有合并单元格** | openpyxl 读取时 unmerge，将合并值填充到每个子单元格 |
| **数值格式混乱** | 正则预处理: 括号 `(1,234)` → `-1234`，逗号去除，`%` 保留标记 |
| **用户审核到一半关浏览器** | Session 所有编辑实时 autosave，重新打开恢复 |
| **OCR 识别质量极差** | 提取行数 < 3 或数值识别率 < 50% → 标记 "Low Quality"，建议重传 |
| **同公司同月已有数据** | 写入前检测冲突，弹出 Overwrite/Skip/Cancel 选项 |
| **Balance Sheet 不平衡** | Soft warning（不阻止提交，但提醒用户） |
| **P&L 子项加总不等于汇总行** | Soft warning |
| **同文件出现重复报告周期** | 检测并标记，用户确认后才允许继续 |

---

## 9. 安全设计

### 9.1 文件安全

```python
import magic

ALLOWED_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "image/jpeg", "image/png", "image/tiff"
}

async def validate_file(file_content: bytes, filename: str) -> None:
    # 真实 MIME 类型检查（不信任扩展名）
    mime = magic.from_buffer(file_content[:2048], mime=True)
    if mime not in ALLOWED_MIMES:
        raise ValueError(f"File type {mime} not allowed")

    # Excel 防御 XXE 攻击
    if mime.startswith("application/vnd.openxmlformats"):
        from defusedxml import ElementTree
        # 使用 defusedxml 替代默认 XML parser
```

### 9.2 LLM Prompt Injection 防御

用户文件名/行标签可能含恶意 prompt 注入:

```python
def sanitize_for_llm(text: str) -> str:
    """清理传入 LLM 的用户数据"""
    # 去除可能的 prompt injection 关键词
    dangerous_patterns = [
        "ignore previous", "system:", "assistant:", "user:",
        "forget your instructions", "new instructions"
    ]
    result = text
    for pattern in dangerous_patterns:
        result = result.replace(pattern, "[FILTERED]")
    return result[:500]  # 限制长度
```

### 9.3 S3 文件存储安全

- Pre-signed URL（有效期 15 分钟）
- SSE-S3 服务端加密
- Bucket policy 禁止公开访问
- 文件留存策略: 提交后保留 90 天，之后归档到 Glacier

### 9.4 权限校验

- Gateway 层: JWT 校验
- Python 端: 二次校验 company_id 归属关系
- Company Admin/User: 只能上传本公司文件
- Portfolio Admin: 可上传所有有权限公司的文件

---

## 10. 性能优化

| 项目 | 方案 |
|------|------|
| OCR 处理时间（20 页 PDF ~30-60s） | 异步处理 + 进度轮询（WebSocket 或 SSE） |
| 大文件上传 | 分片上传（chunk upload）+ 断点续传 |
| 公司记忆模糊匹配 | PostgreSQL pg_trgm 索引 |
| 并排审核页面大表格 | react-window 虚拟滚动 |
| Autosave | debounce 500ms，只发送 diff 数据 |
| LLM 调用 | 三层架构控制只 ~15% 走 LLM；批量处理减少调用次数 |

---

## 11. 需求问题清单（待确认）

以下问题需要产品/财务 SME 确认后才能开始开发:

| # | 问题 | 影响范围 | 阻塞级别 |
|---|------|----------|----------|
| 1 | OOE 作为计算指标 vs 映射目标的矛盾 — Other Income/Expense 最终写入哪个字段？ | AI Mapper + LG Writer | **P0 阻塞** |
| 2 | `hosting/cloud/server` 默认归 COGS 还是 R&D？公司 industry 从哪获取？ | 规则引擎 | P1 |
| 3 | 多类型混合 PDF 是要求用户按报表分别上传，还是系统自动切分？ | OCR Extractor | P1 |
| 4 | eSapiens OCR 是 SaaS 还是 self-hosted？数据驻留合规要求？ | 安全/合规 | P1 |
| 5 | 已上传文件的删除权限 — 谁能删？Portfolio Admin 上传后 Company User 能看到吗？ | 权限模型 | P2 |
| 6 | Mobile 审核编辑页面是否为 Desktop Only？ | 前端 | P2 |

---

## 12. 开发分期建议

| 阶段 | 范围 | 估算 |
|------|------|------|
| **Phase 1 (MVP)** | Upload + Excel 提取 + 规则引擎映射 + 简单审核 + 写入 LG | 3 sprint |
| **Phase 2** | OCR 提取 + 并排审核 + 内联编辑 + 冲突检测 | 2 sprint |
| **Phase 3** | LLM 映射 + 公司记忆 + Note 字段 + Mobile 适配 | 2 sprint |
| **Phase 4** | 持续学习 + 性能优化 + 安全加固 | 1 sprint |

**为什么 Excel 先于 OCR？** Excel 提取是确定性的（直接读表格），OCR 有不确定性（识别率问题）。先做 Excel 可验证整个 Pipeline（映射→审核→写入），再接入 OCR 只是换一个 Extractor 实现。

---

## 13. AI 模型版本管理

双轨版本控制:

| 版本类型 | 说明 | 变更触发 |
|----------|------|----------|
| **Core Engine Version** | 通用规则（关键词表+优先级+LLM prompt） | 系统更新时全局生效 |
| **Company Mapping History ID** | 公司级映射记忆（用户修正的历史） | 每次用户确认映射时更新 |

每条 MappingResult 记录两个版本 ID，确保完整审计追溯。
