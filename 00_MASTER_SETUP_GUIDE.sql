-- ============================================================================
-- INSURANCE AI HUB (E.D.I.E.) — MASTER SETUP GUIDE
-- Enterprise Data & Intelligence Engine
-- Complete recreation script for deploying to a new Snowflake account
-- ============================================================================
--
-- DATABASE: INSURANCE_AI_HUB
-- SCHEMAS:  ANALYTICS (12 tables), DOCUMENTS (3 tables), DATA_QUALITY (5 tables)
-- TOTAL:    20 tables | ~82,000+ rows | 200+ columns
--
-- ============================================================================
-- EXECUTION ORDER
-- ============================================================================
--
-- Run these scripts in order to recreate the full database from scratch:
--
--   STEP 1: 01_infrastructure.sql       — Warehouse, Database, Schemas
--   STEP 2: 02_tables.sql               — ORIGINAL DDL (fewer columns — matches 03-07)
--   STEP 3: 03_seed_dimensions.sql      — AGENTS (150) + CUSTOMERS (5,000)
--   STEP 4: 04_generate_facts.sql       — POLICIES (8K→10K), CLAIMS (3.5K→15K),
--                                          BILLING (20K→25K), AT_RISK_POLICIES (1.2K)
--   STEP 5: 05_generate_documents.sql   — POLICY_DOCUMENTS (2K) + DOCUMENT_CHUNKS (12K)
--   STEP 6: 06_generate_dq.sql          — DQ_RULES (50), DQ_RESULTS (5K),
--                                          DQ_SCORES (1K), DQ_COLUMN_HEALTH (3K)
--   STEP 7: 07_inject_issues.sql        — Deliberate DQ issues for realism
--   STEP 8: 09b_schema_evolution.sql    — ALTERs + backfills ~40 new columns on existing tables
--   STEP 9: 10_close_kpi_gaps.sql       — 7 new tables + 2 column backfills for KPI gaps
--
-- NOTE: Step 2 uses the ORIGINAL 02_tables.sql DDL so that scripts 03-07
-- work unmodified. Step 8 (09b_schema_evolution.sql) then renames columns,
-- adds ~40 new columns, and backfills realistic data to reach the current
-- production schema. Section A below documents the FINAL DDL state.
--
-- ============================================================================
-- COLUMN EVOLUTION SUMMARY (handled by 09b_schema_evolution.sql)
-- ============================================================================
--
-- 09b_schema_evolution.sql performs all of the following transformations:
--
-- POLICIES (3 renames + 7 additions):
--   PLAN_TIER     → COVERAGE_TIER
--   START_DATE    → EFFECTIVE_DATE
--   END_DATE      → EXPIRATION_DATE
--   (Added) POLICY_NUMBER, LINE_OF_BUSINESS, BOUND_DATE, POLICY_TERM_MONTHS,
--           ISSUING_STATE, ENDORSEMENT_TYPE, EXPENSE_AMOUNT
--
-- AGENTS (7 additions):
--   (Added) AGENCY_NAME, PRODUCER_CODE, COMMISSION_RATE, TOTAL_PREMIUM_BOOK,
--           RETENTION_RATE, NPS_SCORE, APPOINTMENT_STATUS
--
-- CLAIMS (9 additions):
--   (Added) LOSS_DATE, FNOL_DATE, FNOL_CHANNEL, REPORTED_BY, RESERVE_AMOUNT,
--           PAID_AMOUNT, RECOVERY_AMOUNT, LITIGATION_FLAG, CATASTROPHE_CODE
--   NOTE: ESCALATION_FLAG is added by 10_close_kpi_gaps.sql (Step 9)
--
-- BILLING (5 additions):
--   (Added) BILLING_PLAN, INSTALLMENT_NUMBER, TOTAL_INSTALLMENTS,
--           GRACE_PERIOD_END, TRANSACTION_REF, CANCELLATION_DATE
--
-- AT_RISK_POLICIES (5 additions):
--   (Added) CUSTOMER_LIFETIME_VALUE, COMPETITOR_QUOTE_FLAG, MODEL_VERSION,
--           SCORE_DATE, CAMPAIGN_ID
--
-- CUSTOMERS (5 additions):
--   (Added) SALESFORCE_ACCOUNT_ID, PREFERRED_CONTACT_METHOD, HOUSEHOLD_ID,
--           LIFE_EVENT_FLAG, ANNUAL_INCOME_RANGE
--
-- DQ_RULES: (Added) SOURCE_SYSTEM, PIPELINE_NAME, OWNER
-- DQ_RESULTS: (Added) PIPELINE_RUN_ID, ANOMALY_SCORE
-- DQ_SCORES: (Added) SOURCE_SYSTEM
-- DQ_COLUMN_HEALTH: (Added) FRESHNESS_HOURS
-- POLICY_DOCUMENTS: (Added) SOURCE_SYSTEM, FILING_STATE, REGULATORY_APPROVAL_DATE, FORM_NUMBER
--


-- ############################################################################
-- SECTION A: CURRENT TABLE DDL (All 20 Tables)
-- ############################################################################

USE DATABASE INSURANCE_AI_HUB;
USE WAREHOUSE INSURANCE_AI_HUB_WH;

-- ============================================================================
-- SCHEMA: ANALYTICS (12 tables)
-- ============================================================================
USE SCHEMA ANALYTICS;

-- ---------------------------------------------------------------------------
-- 1. CUSTOMERS (20 columns) — Customer demographics, risk, credit
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE CUSTOMERS (
    CUSTOMER_ID                 VARCHAR(20)     NOT NULL,
    SALESFORCE_ACCOUNT_ID       VARCHAR(20)     NOT NULL,
    FIRST_NAME                  VARCHAR(50)     NOT NULL,
    LAST_NAME                   VARCHAR(50)     NOT NULL,
    DATE_OF_BIRTH               DATE            NOT NULL,
    GENDER                      VARCHAR(12),
    EMAIL                       VARCHAR(100),
    PHONE                       VARCHAR(20),
    ADDRESS                     VARCHAR(200),
    CITY                        VARCHAR(50),
    STATE                       VARCHAR(2),
    ZIP_CODE                    VARCHAR(10),
    RISK_TIER                   VARCHAR(10)     NOT NULL,
    CREDIT_SCORE                NUMBER(38,0),
    SEGMENT                     VARCHAR(20)     NOT NULL,
    PREFERRED_CONTACT_METHOD    VARCHAR(10),
    HOUSEHOLD_ID                VARCHAR(20),
    LIFE_EVENT_FLAG             VARCHAR(20),
    ANNUAL_INCOME_RANGE         VARCHAR(15),
    CUSTOMER_SINCE              DATE            NOT NULL
)
COMMENT = 'Customer profiles with demographics, contact info, risk tier, credit score, and segmentation';

-- ---------------------------------------------------------------------------
-- 2. AGENTS (18 columns) — Agent profile, performance, production
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE AGENTS (
    AGENT_ID                VARCHAR(20)     NOT NULL,
    AGENT_NAME              VARCHAR(100)    NOT NULL,
    AGENCY_NAME             VARCHAR(100)    NOT NULL,
    PRODUCER_CODE           VARCHAR(20)     NOT NULL,
    REGION                  VARCHAR(30)     NOT NULL,
    STATE                   VARCHAR(2)      NOT NULL,
    SPECIALIZATION          VARCHAR(30)     NOT NULL,
    LICENSE_NUMBER          VARCHAR(20)     NOT NULL,
    HIRE_DATE               DATE            NOT NULL,
    PERFORMANCE_RATING      NUMBER(3,2)     NOT NULL,
    COMMISSION_RATE         NUMBER(4,3)     NOT NULL,
    TOTAL_PREMIUM_BOOK      NUMBER(14,2)    NOT NULL,
    RETENTION_RATE          NUMBER(4,3)     NOT NULL,
    NPS_SCORE               NUMBER(3,0),
    ACTIVE_POLICIES_COUNT   NUMBER(38,0)    NOT NULL,
    APPOINTMENT_STATUS      VARCHAR(15)     NOT NULL,
    STATUS                  VARCHAR(10)     NOT NULL,
    APPLICATION_DATE        DATE
)
COMMENT = 'Insurance agents with region, specialization, license, performance rating, commission, and production metrics';

-- ---------------------------------------------------------------------------
-- 3. POLICIES (21 columns) — Policy coverage, premium, status
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE POLICIES (
    POLICY_ID               VARCHAR(20)     NOT NULL,
    POLICY_NUMBER           VARCHAR(30)     NOT NULL,
    CUSTOMER_ID             VARCHAR(20)     NOT NULL,
    AGENT_ID                VARCHAR(20)     NOT NULL,
    POLICY_TYPE             VARCHAR(30)     NOT NULL,
    LINE_OF_BUSINESS        VARCHAR(40)     NOT NULL,
    COVERAGE_TIER           VARCHAR(15)     NOT NULL,
    EFFECTIVE_DATE          DATE            NOT NULL,
    EXPIRATION_DATE         DATE            NOT NULL,
    BOUND_DATE              DATE            NOT NULL,
    POLICY_TERM_MONTHS      NUMBER(3,0)     NOT NULL,
    ISSUING_STATE           VARCHAR(2)      NOT NULL,
    PREMIUM_AMOUNT          NUMBER(12,2)    NOT NULL,
    COVERAGE_AMOUNT         NUMBER(14,2)    NOT NULL,
    DEDUCTIBLE              NUMBER(10,2)    NOT NULL,
    STATUS                  VARCHAR(15)     NOT NULL,
    RENEWAL_STATUS          VARCHAR(15)     NOT NULL,
    ENDORSEMENT_TYPE        VARCHAR(30),
    UNDERWRITING_SCORE      NUMBER(5,2),
    CREATED_AT              TIMESTAMP_NTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    EXPENSE_AMOUNT          NUMBER(12,2)
)
COMMENT = 'Insurance policies with type, tier, premium, coverage, deductible, status, renewal, and expense tracking';

-- ---------------------------------------------------------------------------
-- 4. CLAIMS (25 columns) — Claim events, amounts, fraud, resolution
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE CLAIMS (
    CLAIM_ID                VARCHAR(20)     NOT NULL,
    POLICY_ID               VARCHAR(20)     NOT NULL,
    CUSTOMER_ID             VARCHAR(20)     NOT NULL,
    CLAIM_DATE              DATE            NOT NULL,
    LOSS_DATE               DATE            NOT NULL,
    FNOL_DATE               DATE            NOT NULL,
    FNOL_CHANNEL            VARCHAR(15)     NOT NULL,
    REPORTED_BY             VARCHAR(15)     NOT NULL,
    CLAIM_TYPE              VARCHAR(30)     NOT NULL,
    CAUSE_OF_LOSS           VARCHAR(30),
    CLAIM_AMOUNT            NUMBER(12,2)    NOT NULL,
    APPROVED_AMOUNT         NUMBER(12,2),
    RESERVE_AMOUNT          NUMBER(12,2),
    PAID_AMOUNT             NUMBER(12,2)    DEFAULT 0,
    RECOVERY_AMOUNT         NUMBER(12,2)    DEFAULT 0,
    STATUS                  VARCHAR(20)     NOT NULL,
    FRAUD_SCORE             NUMBER(5,2),
    FRICTION_SCORE          NUMBER(5,2),
    ADJUSTER_ID             VARCHAR(20),
    RESOLUTION_DAYS         NUMBER(38,0),
    INCIDENT_LOCATION       VARCHAR(100),
    LITIGATION_FLAG         BOOLEAN         NOT NULL DEFAULT FALSE,
    CATASTROPHE_CODE        VARCHAR(20),
    CLOSED_DATE             DATE,
    ESCALATION_FLAG         BOOLEAN         DEFAULT FALSE
)
COMMENT = 'Insurance claims with amounts, fraud scoring, adjuster assignment, resolution time, litigation, and escalation flags';

-- ---------------------------------------------------------------------------
-- 5. BILLING (18 columns) — Invoices, payments, balances
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE BILLING (
    INVOICE_ID              VARCHAR(20)     NOT NULL,
    POLICY_ID               VARCHAR(20)     NOT NULL,
    CUSTOMER_ID             VARCHAR(20)     NOT NULL,
    BILLING_PLAN            VARCHAR(15)     NOT NULL,
    INSTALLMENT_NUMBER      NUMBER(3,0)     NOT NULL,
    TOTAL_INSTALLMENTS      NUMBER(3,0)     NOT NULL,
    INVOICE_DATE            DATE            NOT NULL,
    DUE_DATE                DATE            NOT NULL,
    GRACE_PERIOD_END        DATE            NOT NULL,
    AMOUNT_DUE              NUMBER(12,2)    NOT NULL,
    AMOUNT_PAID             NUMBER(12,2)    NOT NULL DEFAULT 0,
    OUTSTANDING_BALANCE     NUMBER(12,2)    NOT NULL DEFAULT 0,
    LATE_FEE                NUMBER(8,2)     NOT NULL DEFAULT 0,
    PAYMENT_STATUS          VARCHAR(20)     NOT NULL,
    PAYMENT_METHOD          VARCHAR(15),
    PAYMENT_DATE            DATE,
    TRANSACTION_REF         VARCHAR(30),
    CANCELLATION_DATE       DATE
)
COMMENT = 'Billing invoices with installment tracking, payment status, outstanding balances, and late fees';

-- ---------------------------------------------------------------------------
-- 6. AT_RISK_POLICIES (18 columns) — Churn and retention risk snapshot
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE AT_RISK_POLICIES (
    RISK_ID                     VARCHAR(20)     NOT NULL,
    POLICY_ID                   VARCHAR(20)     NOT NULL,
    CUSTOMER_ID                 VARCHAR(20)     NOT NULL,
    RISK_CATEGORY               VARCHAR(25)     NOT NULL,
    CHURN_PROBABILITY           NUMBER(5,4)     NOT NULL,
    REVENUE_AT_RISK             NUMBER(12,2)    NOT NULL,
    CUSTOMER_LIFETIME_VALUE     NUMBER(12,2)    NOT NULL,
    DAYS_UNTIL_RENEWAL          NUMBER(38,0)    NOT NULL,
    MISSED_PAYMENTS_COUNT       NUMBER(38,0)    NOT NULL DEFAULT 0,
    CLAIM_FREQUENCY             NUMBER(38,0)    NOT NULL DEFAULT 0,
    NPS_SCORE                   NUMBER(38,0),
    LAST_CONTACT_DATE           DATE,
    RETENTION_ACTION            VARCHAR(30)     NOT NULL,
    COMPETITOR_QUOTE_FLAG       BOOLEAN         NOT NULL DEFAULT FALSE,
    MODEL_VERSION               VARCHAR(15)     NOT NULL,
    SCORE_DATE                  DATE            NOT NULL,
    CAMPAIGN_ID                 VARCHAR(20),
    SNAPSHOT_DATE               DATE            NOT NULL
)
COMMENT = 'At-risk policy snapshot with churn probability, revenue exposure, NPS, LTV, and retention actions';

-- ---------------------------------------------------------------------------
-- 7. APPLICATIONS (16 columns) — Underwriting pipeline
-- Enables: Underwriting Decline Rate, Quote-to-Bind Ratio
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE APPLICATIONS (
    APPLICATION_ID          VARCHAR(20)     NOT NULL,
    CUSTOMER_ID             VARCHAR(20),
    AGENT_ID                VARCHAR(20),
    APPLICATION_DATE        DATE            NOT NULL,
    POLICY_TYPE             VARCHAR(20)     NOT NULL,
    REQUESTED_COVERAGE      NUMBER(14,2)    NOT NULL,
    REQUESTED_PREMIUM       NUMBER(12,2)    NOT NULL,
    RISK_SCORE              NUMBER(5,2),
    UNDERWRITING_DECISION   VARCHAR(20)     NOT NULL,
    DECLINE_REASON          VARCHAR(100),
    QUOTE_AMOUNT            NUMBER(12,2),
    QUOTE_DATE              DATE,
    BOUND_DATE              DATE,
    POLICY_ID               VARCHAR(20),
    STATUS                  VARCHAR(20)     NOT NULL,
    CREATED_AT              TIMESTAMP_NTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_APPLICATIONS PRIMARY KEY (APPLICATION_ID)
)
COMMENT = 'Policy applications with underwriting decisions, quotes, and bind outcomes for conversion tracking';

-- ---------------------------------------------------------------------------
-- 8. POLICY_CHANGE_LOG (10 columns) — Mid-term policy modifications
-- Enables: Policy Endorsement Churn (tier downgrades)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE POLICY_CHANGE_LOG (
    CHANGE_ID               VARCHAR(20)     NOT NULL,
    POLICY_ID               VARCHAR(20)     NOT NULL,
    CHANGE_DATE             DATE            NOT NULL,
    CHANGE_TYPE             VARCHAR(30)     NOT NULL,
    FIELD_CHANGED           VARCHAR(50)     NOT NULL,
    OLD_VALUE               VARCHAR(100),
    NEW_VALUE               VARCHAR(100),
    REASON                  VARCHAR(100),
    REQUESTED_BY            VARCHAR(20),
    CREATED_AT              TIMESTAMP_NTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_POLICY_CHANGE_LOG PRIMARY KEY (CHANGE_ID)
)
COMMENT = 'Policy mid-term change log tracking tier changes, coverage adjustments, and endorsement modifications';

-- ---------------------------------------------------------------------------
-- 9. CUSTOMER_SURVEYS (10 columns) — NPS and satisfaction
-- Enables: Net Promoter Score (full customer base)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE CUSTOMER_SURVEYS (
    SURVEY_ID               VARCHAR(20)     NOT NULL,
    CUSTOMER_ID             VARCHAR(20)     NOT NULL,
    POLICY_ID               VARCHAR(20),
    SURVEY_DATE             DATE            NOT NULL,
    SURVEY_TYPE             VARCHAR(10)     NOT NULL,
    NPS_RATING              NUMBER(38,0)    NOT NULL,
    PROMOTER_CATEGORY       VARCHAR(15)     NOT NULL,
    SATISFACTION_SCORE      NUMBER(3,1),
    COMMENTS                TEXT,
    CHANNEL                 VARCHAR(20)     NOT NULL,
    CONSTRAINT PK_SURVEYS PRIMARY KEY (SURVEY_ID)
)
COMMENT = 'Customer survey responses including NPS ratings, satisfaction scores, and feedback for retention analytics';

-- ---------------------------------------------------------------------------
-- 10. FINANCIAL_LEDGER (9 columns) — Reserves, investments, adjustments
-- Enables: Loss Reserve Adequacy, Investment Yield, Audit Premium Recovery
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE FINANCIAL_LEDGER (
    LEDGER_ID               VARCHAR(20)     NOT NULL,
    ENTRY_DATE              DATE            NOT NULL,
    FISCAL_QUARTER          VARCHAR(10)     NOT NULL,
    ACCOUNT_TYPE            VARCHAR(30)     NOT NULL,
    ACCOUNT_SUBTYPE         VARCHAR(50),
    LINE_OF_BUSINESS        VARCHAR(20),
    AMOUNT                  NUMBER(14,2)    NOT NULL,
    DESCRIPTION             VARCHAR(200),
    CREATED_AT              TIMESTAMP_NTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_FINANCIAL_LEDGER PRIMARY KEY (LEDGER_ID)
)
COMMENT = 'Financial ledger entries for loss reserves, investment income, audit adjustments, and operating expenses';

-- ---------------------------------------------------------------------------
-- 11. REINSURANCE_TREATIES (11 columns) — Treaty definitions
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE REINSURANCE_TREATIES (
    TREATY_ID               VARCHAR(20)     NOT NULL,
    TREATY_NAME             VARCHAR(100)    NOT NULL,
    TREATY_TYPE             VARCHAR(30)     NOT NULL,
    REINSURER_NAME          VARCHAR(100)    NOT NULL,
    RETENTION_LIMIT         NUMBER(14,2)    NOT NULL,
    CESSION_RATE            NUMBER(5,4),
    MAX_CESSION             NUMBER(14,2),
    EFFECTIVE_DATE          DATE            NOT NULL,
    EXPIRATION_DATE         DATE            NOT NULL,
    LINE_OF_BUSINESS        VARCHAR(20),
    STATUS                  VARCHAR(15)     NOT NULL,
    CONSTRAINT PK_REINSURANCE_TREATIES PRIMARY KEY (TREATY_ID)
)
COMMENT = 'Reinsurance treaty definitions with retention limits, cession rates, and reinsurer details';

-- ---------------------------------------------------------------------------
-- 12. REINSURANCE_RECOVERIES (8 columns) — Recovery records
-- Enables: Reinsurance Recovery Rate (full)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE REINSURANCE_RECOVERIES (
    RECOVERY_ID             VARCHAR(20)     NOT NULL,
    TREATY_ID               VARCHAR(20)     NOT NULL,
    CLAIM_ID                VARCHAR(20)     NOT NULL,
    GROSS_LOSS              NUMBER(14,2)    NOT NULL,
    CEDED_AMOUNT            NUMBER(14,2)    NOT NULL,
    RECOVERED_AMOUNT        NUMBER(14,2)    NOT NULL,
    RECOVERY_DATE           DATE,
    STATUS                  VARCHAR(15)     NOT NULL,
    CONSTRAINT PK_REINSURANCE_RECOVERIES PRIMARY KEY (RECOVERY_ID),
    CONSTRAINT FK_RR_TREATY FOREIGN KEY (TREATY_ID) REFERENCES REINSURANCE_TREATIES(TREATY_ID)
)
COMMENT = 'Reinsurance recovery records linking claims to treaty cessions with recovery amounts and status';


-- ============================================================================
-- SCHEMA: DOCUMENTS (3 tables)
-- ============================================================================
USE SCHEMA DOCUMENTS;

-- ---------------------------------------------------------------------------
-- 13. POLICY_DOCUMENTS (16 columns) — Full contract text
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE POLICY_DOCUMENTS (
    DOCUMENT_ID             VARCHAR(20)     NOT NULL,
    POLICY_ID               VARCHAR(20)     NOT NULL,
    DOCUMENT_TYPE           VARCHAR(30)     NOT NULL,
    TITLE                   VARCHAR(200)    NOT NULL,
    CONTENT                 TEXT            NOT NULL,
    SUMMARY                 TEXT,
    EFFECTIVE_DATE          DATE            NOT NULL,
    EXPIRATION_DATE         DATE,
    VERSION                 NUMBER(38,0)    NOT NULL DEFAULT 1,
    LANGUAGE                VARCHAR(10)     NOT NULL DEFAULT 'EN',
    FILE_FORMAT             VARCHAR(10)     NOT NULL DEFAULT 'PDF',
    CREATED_AT              TIMESTAMP_NTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    SOURCE_SYSTEM           VARCHAR(20),
    FILING_STATE            VARCHAR(2),
    REGULATORY_APPROVAL_DATE DATE,
    FORM_NUMBER             VARCHAR(20),
    CONSTRAINT PK_POLICY_DOCS PRIMARY KEY (DOCUMENT_ID)
)
COMMENT = 'Full policy document text including contracts, endorsements, exclusions, declarations, and riders';

-- ---------------------------------------------------------------------------
-- 14. DOCUMENT_CHUNKS (6 columns) — RAG-ready text chunks
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE DOCUMENT_CHUNKS (
    CHUNK_ID                VARCHAR(20)     NOT NULL,
    DOCUMENT_ID             VARCHAR(20)     NOT NULL,
    CHUNK_INDEX             NUMBER(38,0)    NOT NULL,
    CHUNK_TEXT              TEXT            NOT NULL,
    TOKEN_COUNT             NUMBER(38,0)    NOT NULL,
    EMBEDDING_MODEL         VARCHAR(30)     NOT NULL DEFAULT 'arctic-embed-m',
    CONSTRAINT PK_CHUNKS PRIMARY KEY (CHUNK_ID),
    CONSTRAINT FK_CHUNKS_DOC FOREIGN KEY (DOCUMENT_ID) REFERENCES POLICY_DOCUMENTS(DOCUMENT_ID)
)
COMMENT = 'Chunked policy document text (500-1000 tokens) for vector embedding and RAG/Cortex Search retrieval';

-- ---------------------------------------------------------------------------
-- 15. RAG_QUERY_LOG (10 columns) — Contract search query log
-- Enables: Coverage Search Query Rate
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE RAG_QUERY_LOG (
    QUERY_ID                VARCHAR(20)     NOT NULL,
    USER_ROLE               VARCHAR(30)     NOT NULL,
    QUERY_TEXT              TEXT            NOT NULL,
    QUERY_DATE              TIMESTAMP_NTZ   NOT NULL,
    DOCUMENTS_RETURNED      NUMBER(38,0)    NOT NULL,
    CHUNKS_RETRIEVED        NUMBER(38,0)    NOT NULL,
    RESPONSE_TIME_MS        NUMBER(38,0)    NOT NULL,
    QUERY_SOURCE            VARCHAR(30)     NOT NULL,
    RELEVANCE_SCORE         NUMBER(5,4),
    POLICY_ID               VARCHAR(20),
    CONSTRAINT PK_RAG_QUERY PRIMARY KEY (QUERY_ID)
)
COMMENT = 'RAG query log tracking contract search queries, retrieval counts, response times, and relevance scores';


-- ============================================================================
-- SCHEMA: DATA_QUALITY (5 tables)
-- ============================================================================
USE SCHEMA DATA_QUALITY;

-- ---------------------------------------------------------------------------
-- 16. DQ_RULES (13 columns) — Rule definitions
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE DQ_RULES (
    RULE_ID                 VARCHAR(20)     NOT NULL,
    RULE_NAME               VARCHAR(100)    NOT NULL,
    RULE_DESCRIPTION        TEXT            NOT NULL,
    TARGET_SCHEMA           VARCHAR(30)     NOT NULL,
    TARGET_TABLE            VARCHAR(30)     NOT NULL,
    TARGET_COLUMN           VARCHAR(50),
    RULE_TYPE               VARCHAR(20)     NOT NULL,
    SEVERITY                VARCHAR(10)     NOT NULL,
    THRESHOLD               NUMBER(5,2)     NOT NULL,
    IS_ACTIVE               BOOLEAN         NOT NULL DEFAULT TRUE,
    SOURCE_SYSTEM           VARCHAR(30)     NOT NULL,
    PIPELINE_NAME           VARCHAR(50)     NOT NULL,
    OWNER                   VARCHAR(50)     NOT NULL
)
COMMENT = 'Data quality rule definitions with SQL expressions, thresholds, severity, and target table/column mappings';

-- ---------------------------------------------------------------------------
-- 17. DQ_RESULTS (14 columns) — Rule execution results
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE DQ_RESULTS (
    RESULT_ID               VARCHAR(20)     NOT NULL,
    RULE_ID                 VARCHAR(20)     NOT NULL,
    TARGET_TABLE            VARCHAR(30)     NOT NULL,
    RUN_DATE                TIMESTAMP_NTZ   NOT NULL,
    TOTAL_RECORDS           NUMBER(38,0)    NOT NULL,
    PASSED_RECORDS          NUMBER(38,0)    NOT NULL,
    FAILED_RECORDS          NUMBER(38,0)    NOT NULL,
    PASS_RATE               NUMBER(5,2)     NOT NULL,
    STATUS                  VARCHAR(10)     NOT NULL,
    EXECUTION_TIME_MS       NUMBER(38,0)    NOT NULL,
    RUN_BY                  VARCHAR(50)     NOT NULL,
    PIPELINE_RUN_ID         VARCHAR(30)     NOT NULL,
    ANOMALY_SCORE           NUMBER(4,3),
    ERROR_SAMPLE            TEXT
)
COMMENT = 'DQ rule execution results with pass/fail counts, pass rates, error samples, and execution metadata';

-- ---------------------------------------------------------------------------
-- 18. DQ_SCORES (14 columns) — Table-level quality scores
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE DQ_SCORES (
    SCORE_ID                VARCHAR(20)     NOT NULL,
    SCHEMA_NAME             VARCHAR(30)     NOT NULL,
    TABLE_NAME              VARCHAR(30)     NOT NULL,
    SOURCE_SYSTEM           VARCHAR(30)     NOT NULL,
    SCORE_DATE              DATE            NOT NULL,
    COMPLETENESS_SCORE      NUMBER(5,2)     NOT NULL,
    UNIQUENESS_SCORE        NUMBER(5,2)     NOT NULL,
    VALIDITY_SCORE          NUMBER(5,2)     NOT NULL,
    TIMELINESS_SCORE        NUMBER(5,2)     NOT NULL,
    CONSISTENCY_SCORE       NUMBER(5,2)     NOT NULL,
    OVERALL_SCORE           NUMBER(5,2)     NOT NULL,
    TREND                   VARCHAR(10)     NOT NULL,
    RECORDS_ASSESSED        NUMBER(38,0)    NOT NULL,
    RULES_EVALUATED         NUMBER(38,0)    NOT NULL
)
COMMENT = 'Daily table-level data quality scores across 5 dimensions with trend indicators';

-- ---------------------------------------------------------------------------
-- 19. DQ_COLUMN_HEALTH (13 columns) — Column-level health metrics
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE DQ_COLUMN_HEALTH (
    HEALTH_ID               VARCHAR(20)     NOT NULL,
    SCHEMA_NAME             VARCHAR(30)     NOT NULL,
    TABLE_NAME              VARCHAR(30)     NOT NULL,
    COLUMN_NAME             VARCHAR(50)     NOT NULL,
    CHECK_DATE              DATE            NOT NULL,
    NULL_RATE               NUMBER(5,2)     NOT NULL,
    DUPLICATE_RATE          NUMBER(5,2)     NOT NULL,
    OUTLIER_RATE            NUMBER(5,2)     NOT NULL,
    DISTINCT_COUNT          NUMBER(38,0)    NOT NULL,
    HEALTH_SCORE            NUMBER(5,2)     NOT NULL,
    DATA_TYPE_CONSISTENCY   NUMBER(5,2)     NOT NULL,
    FRESHNESS_HOURS         NUMBER(6,1)     NOT NULL,
    STATUS                  VARCHAR(10)     NOT NULL
)
COMMENT = 'Weekly column-level health metrics including null rates, duplicates, outliers, and overall health scores';

-- ---------------------------------------------------------------------------
-- 20. SCHEMA_AUDIT_LOG (11 columns) — Schema drift detection
-- Enables: Schema Drift Alerts
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE SCHEMA_AUDIT_LOG (
    AUDIT_ID                VARCHAR(20)     NOT NULL,
    SCHEMA_NAME             VARCHAR(30)     NOT NULL,
    TABLE_NAME              VARCHAR(30)     NOT NULL,
    COLUMN_NAME             VARCHAR(50),
    EVENT_TYPE              VARCHAR(30)     NOT NULL,
    OLD_VALUE               VARCHAR(200),
    NEW_VALUE               VARCHAR(200),
    DETECTED_AT             TIMESTAMP_NTZ   NOT NULL,
    SEVERITY                VARCHAR(10)     NOT NULL,
    ACKNOWLEDGED            BOOLEAN         NOT NULL DEFAULT FALSE,
    ACKNOWLEDGED_BY         VARCHAR(50),
    CONSTRAINT PK_SCHEMA_AUDIT PRIMARY KEY (AUDIT_ID)
)
COMMENT = 'Schema drift detection log tracking column additions, removals, type changes, and renames across all schemas';


-- ############################################################################
-- SECTION B: DATA GENERATION REFERENCE
-- ############################################################################
--
-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ TABLE                    │ ROWS    │ SOURCE FILE              │ SCHEMA  │
-- ├──────────────────────────┼─────────┼──────────────────────────┼─────────┤
-- │ CUSTOMERS                │ 5,017   │ 03_seed_dimensions.sql   │ ANLYTCS │
-- │ AGENTS                   │ 150     │ 03_seed_dimensions.sql   │ ANLYTCS │
-- │ POLICIES                 │ 10,000  │ 04_generate_facts.sql    │ ANLYTCS │
-- │ CLAIMS                   │ 15,000  │ 04_generate_facts.sql    │ ANLYTCS │
-- │ BILLING                  │ 25,000  │ 04_generate_facts.sql    │ ANLYTCS │
-- │ AT_RISK_POLICIES         │ 1,200   │ 04_generate_facts.sql    │ ANLYTCS │
-- │ APPLICATIONS             │ 2,500   │ 10_close_kpi_gaps.sql    │ ANLYTCS │
-- │ POLICY_CHANGE_LOG        │ 1,500   │ 10_close_kpi_gaps.sql    │ ANLYTCS │
-- │ CUSTOMER_SURVEYS         │ 3,000   │ 10_close_kpi_gaps.sql    │ ANLYTCS │
-- │ FINANCIAL_LEDGER         │ 500     │ 10_close_kpi_gaps.sql    │ ANLYTCS │
-- │ REINSURANCE_TREATIES     │ 20      │ 10_close_kpi_gaps.sql    │ ANLYTCS │
-- │ REINSURANCE_RECOVERIES   │ 400     │ 10_close_kpi_gaps.sql    │ ANLYTCS │
-- │ POLICY_DOCUMENTS         │ 2,000   │ 05_generate_documents.sql│ DOCS    │
-- │ DOCUMENT_CHUNKS          │ 12,000  │ 05_generate_documents.sql│ DOCS    │
-- │ RAG_QUERY_LOG            │ 5,000   │ 10_close_kpi_gaps.sql    │ DOCS    │
-- │ DQ_RULES                 │ 50      │ 06_generate_dq.sql       │ DQ      │
-- │ DQ_RESULTS               │ 5,000   │ 06_generate_dq.sql       │ DQ      │
-- │ DQ_SCORES                │ 1,000   │ 06_generate_dq.sql       │ DQ      │
-- │ DQ_COLUMN_HEALTH         │ 3,000   │ 06_generate_dq.sql       │ DQ      │
-- │ SCHEMA_AUDIT_LOG         │ 300     │ 10_close_kpi_gaps.sql    │ DQ      │
-- ├──────────────────────────┼─────────┼──────────────────────────┼─────────┤
-- │ TOTAL                    │ ~86,637 │                          │         │
-- └──────────────────────────────────────────────────────────────────────────┘
--
-- Data Issues (07_inject_issues.sql):
--   - ~200 null emails, ~150 null phones in CUSTOMERS
--   - 15 near-duplicate customers (CUST-D prefix)
--   - 175 claims with extreme resolution days (200+)
--   - 45 clustered high fraud scores in Northeast region (Mar-May 2025)
--   - ~500 "Paid" invoices with NULL payment_date
--   - ~300 billing balance calculation errors
--   - 50 hurricane season claims (Aug-Oct 2024, Southeast)
--   - 8 agents with very low ratings but high policy counts
--   - 240 stale AT_RISK_POLICIES snapshots
--   - 12 premium outliers in Commercial policies
--   - 12 duplicate claim IDs (CLM-DUP prefix)
--
-- Marketplace Enrichment (08_marketplace_enrichment.sql):
--   - Reference only — lists recommended free/paid Marketplace datasets
--   - No SQL to execute; install via Snowsight Marketplace UI
--


-- ############################################################################
-- SECTION C: REINSURANCE TREATY SEED DATA (Static Insert)
-- ############################################################################
-- This is the only static data insert. All other inserts use GENERATOR.
-- Included here for completeness since it's a small reference table.

-- (Run after creating REINSURANCE_TREATIES table)
/*
INSERT INTO ANALYTICS.REINSURANCE_TREATIES VALUES
('RTY-001','Property Quota Share 2022','QuotaShare','Swiss Re',0.00,0.30,5000000.00,'2022-01-01','2022-12-31','Home','Expired'),
('RTY-002','Auto Excess of Loss 2022','ExcessOfLoss','Munich Re',150000.00,NULL,2000000.00,'2022-01-01','2022-12-31','Auto','Expired'),
('RTY-003','Property Quota Share 2023','QuotaShare','Swiss Re',0.00,0.30,6000000.00,'2023-01-01','2023-12-31','Home','Expired'),
('RTY-004','Auto Excess of Loss 2023','ExcessOfLoss','Munich Re',150000.00,NULL,2500000.00,'2023-01-01','2023-12-31','Auto','Expired'),
('RTY-005','Commercial Surplus 2023','SurplusShare','Hannover Re',100000.00,0.25,3000000.00,'2023-01-01','2023-12-31','Commercial','Expired'),
('RTY-006','CAT Excess of Loss 2023','CatExcessOfLoss','Lloyds',500000.00,NULL,10000000.00,'2023-01-01','2023-12-31',NULL,'Expired'),
('RTY-007','Property Quota Share 2024','QuotaShare','Swiss Re',0.00,0.35,7000000.00,'2024-01-01','2024-12-31','Home','Expired'),
('RTY-008','Auto Excess of Loss 2024','ExcessOfLoss','Munich Re',175000.00,NULL,3000000.00,'2024-01-01','2024-12-31','Auto','Expired'),
('RTY-009','Commercial Surplus 2024','SurplusShare','Hannover Re',125000.00,0.25,3500000.00,'2024-01-01','2024-12-31','Commercial','Expired'),
('RTY-010','CAT Excess of Loss 2024','CatExcessOfLoss','Lloyds',750000.00,NULL,15000000.00,'2024-01-01','2024-12-31',NULL,'Expired'),
('RTY-011','Life Excess of Loss 2024','ExcessOfLoss','RGA',200000.00,NULL,5000000.00,'2024-01-01','2024-12-31','Life','Expired'),
('RTY-012','Property Quota Share 2025','QuotaShare','Swiss Re',0.00,0.35,8000000.00,'2025-01-01','2025-12-31','Home','Active'),
('RTY-013','Auto Excess of Loss 2025','ExcessOfLoss','Munich Re',200000.00,NULL,3500000.00,'2025-01-01','2025-12-31','Auto','Active'),
('RTY-014','Commercial Surplus 2025','SurplusShare','Hannover Re',150000.00,0.30,4000000.00,'2025-01-01','2025-12-31','Commercial','Active'),
('RTY-015','CAT Excess of Loss 2025','CatExcessOfLoss','Lloyds',1000000.00,NULL,20000000.00,'2025-01-01','2025-12-31',NULL,'Active'),
('RTY-016','Life Excess of Loss 2025','ExcessOfLoss','RGA',250000.00,NULL,6000000.00,'2025-01-01','2025-12-31','Life','Active'),
('RTY-017','Health Stop Loss 2025','StopLoss','Gen Re',100000.00,NULL,2000000.00,'2025-01-01','2025-12-31','Health','Active'),
('RTY-018','Aggregate XOL 2025','AggregateExcess','Berkshire Re',5000000.00,NULL,25000000.00,'2025-01-01','2025-12-31',NULL,'Active'),
('RTY-019','Property Fac 2025','Facultative','Everest Re',500000.00,0.50,1000000.00,'2025-01-01','2025-12-31','Home','Active'),
('RTY-020','Workers Comp Treaty 2025','QuotaShare','Odyssey Re',0.00,0.20,3000000.00,'2025-01-01','2025-12-31','Commercial','Active');
*/


-- ############################################################################
-- SECTION D: FULL FILE LISTING (Copy all to new account workspace)
-- ############################################################################
--
-- /workspace/
-- ├── 00_MASTER_SETUP_GUIDE.sql    ← This file (DDL reference + execution guide)
-- ├── 01_infrastructure.sql         ← STEP 1: Warehouse, Database, Schemas
-- ├── 02_tables.sql                 ← STEP 2: ORIGINAL DDL (matches 03-07 INSERT column lists)
-- ├── 03_seed_dimensions.sql        ← STEP 3: AGENTS + CUSTOMERS data generation
-- ├── 04_generate_facts.sql         ← STEP 4: POLICIES, CLAIMS, BILLING, AT_RISK data
-- ├── 05_generate_documents.sql     ← STEP 5: POLICY_DOCUMENTS + DOCUMENT_CHUNKS
-- ├── 06_generate_dq.sql            ← STEP 6: DQ_RULES, DQ_RESULTS, DQ_SCORES, DQ_COLUMN_HEALTH
-- ├── 07_inject_issues.sql          ← STEP 7: Deliberate data quality issues
-- ├── 08_marketplace_enrichment.sql ← REFERENCE: External dataset recommendations (no SQL to run)
-- ├── 09_explore_data.sql           ← OPTIONAL: Exploration queries
-- ├── 09b_schema_evolution.sql      ← STEP 8: ALTER + backfill ~40 columns to current schema
-- └── 10_close_kpi_gaps.sql         ← STEP 9: 7 new tables + 2 column backfills
--
-- ============================================================================
-- END OF MASTER SETUP GUIDE
-- ============================================================================
