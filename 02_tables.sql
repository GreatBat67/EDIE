-- ============================================================
-- INSURANCE AI HUB (E.D.I.E.) - Table Definitions
-- Phase 2: All 12 tables across 3 schemas (149 columns total)
-- ============================================================

USE DATABASE INSURANCE_AI_HUB;
USE WAREHOUSE INSURANCE_AI_HUB_WH;

-- ============================================================
-- SCHEMA: ANALYTICS (6 tables)
-- ============================================================
USE SCHEMA ANALYTICS;

-- -----------------------------------------------------------
-- CUSTOMERS (15 columns) - Dimension
-- Customer demographic, contact, risk and credit information
-- -----------------------------------------------------------
CREATE OR REPLACE TABLE CUSTOMERS (
    CUSTOMER_ID         VARCHAR(20)     NOT NULL,
    FIRST_NAME          VARCHAR(50)     NOT NULL,
    LAST_NAME           VARCHAR(50)     NOT NULL,
    DATE_OF_BIRTH       DATE            NOT NULL,
    GENDER              VARCHAR(12),
    EMAIL               VARCHAR(100),
    PHONE               VARCHAR(20),
    ADDRESS             VARCHAR(200),
    CITY                VARCHAR(50),
    STATE               VARCHAR(2),
    ZIP_CODE            VARCHAR(10),
    RISK_TIER           VARCHAR(10)     NOT NULL,
    CREDIT_SCORE        INT,
    CUSTOMER_SINCE      DATE            NOT NULL,
    SEGMENT             VARCHAR(20)     NOT NULL,
    CONSTRAINT PK_CUSTOMERS PRIMARY KEY (CUSTOMER_ID)
)
COMMENT = 'Customer profiles with demographics, contact info, risk tier, credit score, and segmentation';

-- -----------------------------------------------------------
-- AGENTS (10 columns) - Dimension
-- Agent profile, region, specialization and performance
-- -----------------------------------------------------------
CREATE OR REPLACE TABLE AGENTS (
    AGENT_ID                VARCHAR(20)     NOT NULL,
    AGENT_NAME              VARCHAR(100)    NOT NULL,
    REGION                  VARCHAR(30)     NOT NULL,
    STATE                   VARCHAR(2)      NOT NULL,
    SPECIALIZATION          VARCHAR(30)     NOT NULL,
    LICENSE_NUMBER          VARCHAR(20)     NOT NULL,
    HIRE_DATE               DATE            NOT NULL,
    PERFORMANCE_RATING      DECIMAL(3,2)    NOT NULL,
    ACTIVE_POLICIES_COUNT   INT             NOT NULL,
    STATUS                  VARCHAR(10)     NOT NULL,
    CONSTRAINT PK_AGENTS PRIMARY KEY (AGENT_ID)
)
COMMENT = 'Insurance agents with region, specialization, license, performance rating, and active policy counts';

-- -----------------------------------------------------------
-- POLICIES (14 columns) - Fact / Transactional
-- Policy coverage, premium, deductible, status and financials
-- -----------------------------------------------------------
CREATE OR REPLACE TABLE POLICIES (
    POLICY_ID           VARCHAR(20)     NOT NULL,
    CUSTOMER_ID         VARCHAR(20)     NOT NULL,
    AGENT_ID            VARCHAR(20)     NOT NULL,
    POLICY_TYPE         VARCHAR(20)     NOT NULL,
    PLAN_TIER           VARCHAR(10)     NOT NULL,
    START_DATE          DATE            NOT NULL,
    END_DATE            DATE            NOT NULL,
    PREMIUM_AMOUNT      DECIMAL(12,2)   NOT NULL,
    COVERAGE_AMOUNT     DECIMAL(14,2)   NOT NULL,
    DEDUCTIBLE          DECIMAL(10,2)   NOT NULL,
    STATUS              VARCHAR(15)     NOT NULL,
    RENEWAL_STATUS      VARCHAR(15)     NOT NULL,
    UNDERWRITING_SCORE  DECIMAL(5,2),
    CREATED_AT          TIMESTAMP_NTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_POLICIES PRIMARY KEY (POLICY_ID),
    CONSTRAINT FK_POLICIES_CUSTOMER FOREIGN KEY (CUSTOMER_ID) REFERENCES CUSTOMERS(CUSTOMER_ID),
    CONSTRAINT FK_POLICIES_AGENT FOREIGN KEY (AGENT_ID) REFERENCES AGENTS(AGENT_ID)
)
COMMENT = 'Insurance policies with type, tier, premium, coverage, deductible, status, and renewal info';

-- -----------------------------------------------------------
-- CLAIMS (15 columns) - Fact / Transactional
-- Insurance claim events, amounts, fraud and resolution
-- -----------------------------------------------------------
CREATE OR REPLACE TABLE CLAIMS (
    CLAIM_ID            VARCHAR(20)     NOT NULL,
    POLICY_ID           VARCHAR(20)     NOT NULL,
    CUSTOMER_ID         VARCHAR(20)     NOT NULL,
    CLAIM_DATE          DATE            NOT NULL,
    CLAIM_TYPE          VARCHAR(30)     NOT NULL,
    CLAIM_AMOUNT        DECIMAL(12,2)   NOT NULL,
    APPROVED_AMOUNT     DECIMAL(12,2),
    STATUS              VARCHAR(15)     NOT NULL,
    FRAUD_SCORE         DECIMAL(5,2),
    ADJUSTER_ID         VARCHAR(20),
    RESOLUTION_DAYS     INT,
    FRICTION_SCORE      DECIMAL(5,2),
    CAUSE_OF_LOSS       VARCHAR(50),
    INCIDENT_LOCATION   VARCHAR(100),
    CLOSED_DATE         DATE,
    CONSTRAINT PK_CLAIMS PRIMARY KEY (CLAIM_ID),
    CONSTRAINT FK_CLAIMS_POLICY FOREIGN KEY (POLICY_ID) REFERENCES POLICIES(POLICY_ID),
    CONSTRAINT FK_CLAIMS_CUSTOMER FOREIGN KEY (CUSTOMER_ID) REFERENCES CUSTOMERS(CUSTOMER_ID)
)
COMMENT = 'Insurance claims with amounts, fraud scoring, adjuster assignment, resolution time, and friction metrics';

-- -----------------------------------------------------------
-- BILLING (12 columns) - Fact / Transactional
-- Invoices, payments, balances and billing status
-- -----------------------------------------------------------
CREATE OR REPLACE TABLE BILLING (
    INVOICE_ID          VARCHAR(20)     NOT NULL,
    POLICY_ID           VARCHAR(20)     NOT NULL,
    CUSTOMER_ID         VARCHAR(20)     NOT NULL,
    INVOICE_DATE        DATE            NOT NULL,
    DUE_DATE            DATE            NOT NULL,
    AMOUNT_DUE          DECIMAL(12,2)   NOT NULL,
    AMOUNT_PAID         DECIMAL(12,2)   NOT NULL DEFAULT 0,
    OUTSTANDING_BALANCE DECIMAL(12,2)   NOT NULL DEFAULT 0,
    LATE_FEE            DECIMAL(8,2)    NOT NULL DEFAULT 0,
    PAYMENT_STATUS      VARCHAR(15)     NOT NULL,
    PAYMENT_METHOD      VARCHAR(20),
    PAYMENT_DATE        DATE,
    CONSTRAINT PK_BILLING PRIMARY KEY (INVOICE_ID),
    CONSTRAINT FK_BILLING_POLICY FOREIGN KEY (POLICY_ID) REFERENCES POLICIES(POLICY_ID),
    CONSTRAINT FK_BILLING_CUSTOMER FOREIGN KEY (CUSTOMER_ID) REFERENCES CUSTOMERS(CUSTOMER_ID)
)
COMMENT = 'Billing invoices with payment tracking, outstanding balances, late fees, and payment methods';

-- -----------------------------------------------------------
-- AT_RISK_POLICIES (13 columns) - Fact / Snapshot
-- Customer/policy churn and revenue-at-risk indicators
-- -----------------------------------------------------------
CREATE OR REPLACE TABLE AT_RISK_POLICIES (
    RISK_ID                 VARCHAR(20)     NOT NULL,
    POLICY_ID               VARCHAR(20)     NOT NULL,
    CUSTOMER_ID             VARCHAR(20)     NOT NULL,
    RISK_CATEGORY           VARCHAR(20)     NOT NULL,
    CHURN_PROBABILITY       DECIMAL(5,4)    NOT NULL,
    REVENUE_AT_RISK         DECIMAL(12,2)   NOT NULL,
    DAYS_UNTIL_RENEWAL      INT             NOT NULL,
    MISSED_PAYMENTS_COUNT   INT             NOT NULL DEFAULT 0,
    CLAIM_FREQUENCY         INT             NOT NULL DEFAULT 0,
    NPS_SCORE               INT,
    LAST_CONTACT_DATE       DATE,
    RETENTION_ACTION        VARCHAR(30)     NOT NULL,
    SNAPSHOT_DATE           DATE            NOT NULL,
    CONSTRAINT PK_AT_RISK PRIMARY KEY (RISK_ID),
    CONSTRAINT FK_ATRISK_POLICY FOREIGN KEY (POLICY_ID) REFERENCES POLICIES(POLICY_ID),
    CONSTRAINT FK_ATRISK_CUSTOMER FOREIGN KEY (CUSTOMER_ID) REFERENCES CUSTOMERS(CUSTOMER_ID)
)
COMMENT = 'At-risk policy snapshot with churn probability, revenue exposure, NPS, and recommended retention actions';

-- ============================================================
-- SCHEMA: DOCUMENTS (2 tables)
-- ============================================================
USE SCHEMA DOCUMENTS;

-- -----------------------------------------------------------
-- POLICY_DOCUMENTS (12 columns) - Document Master
-- Policy contracts, exclusions and coverage text
-- -----------------------------------------------------------
CREATE OR REPLACE TABLE POLICY_DOCUMENTS (
    DOCUMENT_ID         VARCHAR(20)     NOT NULL,
    POLICY_ID           VARCHAR(20)     NOT NULL,
    DOCUMENT_TYPE       VARCHAR(30)     NOT NULL,
    TITLE               VARCHAR(200)    NOT NULL,
    CONTENT             TEXT            NOT NULL,
    SUMMARY             TEXT,
    EFFECTIVE_DATE      DATE            NOT NULL,
    EXPIRATION_DATE     DATE,
    VERSION             INT             NOT NULL DEFAULT 1,
    LANGUAGE            VARCHAR(10)     NOT NULL DEFAULT 'EN',
    FILE_FORMAT         VARCHAR(10)     NOT NULL DEFAULT 'PDF',
    CREATED_AT          TIMESTAMP_NTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_POLICY_DOCS PRIMARY KEY (DOCUMENT_ID)
)
COMMENT = 'Full policy document text including contracts, endorsements, exclusions, declarations, and riders';

-- -----------------------------------------------------------
-- DOCUMENT_CHUNKS (6 columns) - Document Detail / RAG
-- Chunked policy text for vector/RAG retrieval
-- -----------------------------------------------------------
CREATE OR REPLACE TABLE DOCUMENT_CHUNKS (
    CHUNK_ID            VARCHAR(20)     NOT NULL,
    DOCUMENT_ID         VARCHAR(20)     NOT NULL,
    CHUNK_INDEX         INT             NOT NULL,
    CHUNK_TEXT          TEXT            NOT NULL,
    TOKEN_COUNT         INT             NOT NULL,
    EMBEDDING_MODEL     VARCHAR(30)     NOT NULL DEFAULT 'arctic-embed-m',
    CONSTRAINT PK_CHUNKS PRIMARY KEY (CHUNK_ID),
    CONSTRAINT FK_CHUNKS_DOC FOREIGN KEY (DOCUMENT_ID) REFERENCES POLICY_DOCUMENTS(DOCUMENT_ID)
)
COMMENT = 'Chunked policy document text (500-1000 tokens) for vector embedding and RAG/Cortex Search retrieval';

-- ============================================================
-- SCHEMA: DATA_QUALITY (4 tables)
-- ============================================================
USE SCHEMA DATA_QUALITY;

-- -----------------------------------------------------------
-- DQ_RULES (11 columns) - DQ Metadata / Configuration
-- Definitions and thresholds for DQ rules
-- -----------------------------------------------------------
CREATE OR REPLACE TABLE DQ_RULES (
    RULE_ID             VARCHAR(20)     NOT NULL,
    RULE_NAME           VARCHAR(100)    NOT NULL,
    RULE_DESCRIPTION    TEXT,
    TARGET_SCHEMA       VARCHAR(30)     NOT NULL,
    TARGET_TABLE        VARCHAR(30)     NOT NULL,
    TARGET_COLUMN       VARCHAR(50),
    RULE_TYPE           VARCHAR(20)     NOT NULL,
    RULE_EXPRESSION     TEXT            NOT NULL,
    THRESHOLD           DECIMAL(5,2)    NOT NULL,
    SEVERITY            VARCHAR(10)     NOT NULL,
    IS_ACTIVE           BOOLEAN         NOT NULL DEFAULT TRUE,
    CONSTRAINT PK_DQ_RULES PRIMARY KEY (RULE_ID)
)
COMMENT = 'Data quality rule definitions with SQL expressions, thresholds, severity, and target table/column mappings';

-- -----------------------------------------------------------
-- DQ_RESULTS (12 columns) - DQ Fact / Execution
-- Individual DQ rule execution results
-- -----------------------------------------------------------
CREATE OR REPLACE TABLE DQ_RESULTS (
    RESULT_ID           VARCHAR(20)     NOT NULL,
    RULE_ID             VARCHAR(20)     NOT NULL,
    RUN_DATE            TIMESTAMP_NTZ   NOT NULL,
    TARGET_TABLE        VARCHAR(30)     NOT NULL,
    TOTAL_RECORDS       INT             NOT NULL,
    PASSED_RECORDS      INT             NOT NULL,
    FAILED_RECORDS      INT             NOT NULL,
    PASS_RATE           DECIMAL(5,2)    NOT NULL,
    STATUS              VARCHAR(10)     NOT NULL,
    ERROR_SAMPLE        TEXT,
    EXECUTION_TIME_MS   INT             NOT NULL,
    RUN_BY              VARCHAR(50)     NOT NULL DEFAULT 'Scheduled',
    CONSTRAINT PK_DQ_RESULTS PRIMARY KEY (RESULT_ID),
    CONSTRAINT FK_DQ_RESULTS_RULE FOREIGN KEY (RULE_ID) REFERENCES DQ_RULES(RULE_ID)
)
COMMENT = 'DQ rule execution results with pass/fail counts, pass rates, error samples, and execution metadata';

-- -----------------------------------------------------------
-- DQ_SCORES (13 columns) - DQ Fact / Snapshot
-- Historical table-level data-quality scores
-- -----------------------------------------------------------
CREATE OR REPLACE TABLE DQ_SCORES (
    SCORE_ID                VARCHAR(20)     NOT NULL,
    SCHEMA_NAME             VARCHAR(30)     NOT NULL,
    TABLE_NAME              VARCHAR(30)     NOT NULL,
    SCORE_DATE              DATE            NOT NULL,
    COMPLETENESS_SCORE      DECIMAL(5,2)    NOT NULL,
    UNIQUENESS_SCORE        DECIMAL(5,2)    NOT NULL,
    VALIDITY_SCORE          DECIMAL(5,2)    NOT NULL,
    TIMELINESS_SCORE        DECIMAL(5,2)    NOT NULL,
    CONSISTENCY_SCORE       DECIMAL(5,2)    NOT NULL,
    OVERALL_SCORE           DECIMAL(5,2)    NOT NULL,
    TREND                   VARCHAR(10)     NOT NULL,
    RECORDS_ASSESSED        INT             NOT NULL,
    RULES_EVALUATED         INT             NOT NULL,
    CONSTRAINT PK_DQ_SCORES PRIMARY KEY (SCORE_ID)
)
COMMENT = 'Daily table-level data quality scores across 5 dimensions with trend indicators';

-- -----------------------------------------------------------
-- DQ_COLUMN_HEALTH (12 columns) - DQ Fact / Snapshot
-- Column-level health, nulls, duplicates, outliers and scores
-- -----------------------------------------------------------
CREATE OR REPLACE TABLE DQ_COLUMN_HEALTH (
    HEALTH_ID               VARCHAR(20)     NOT NULL,
    SCHEMA_NAME             VARCHAR(30)     NOT NULL,
    TABLE_NAME              VARCHAR(30)     NOT NULL,
    COLUMN_NAME             VARCHAR(50)     NOT NULL,
    CHECK_DATE              DATE            NOT NULL,
    NULL_RATE               DECIMAL(5,2)    NOT NULL,
    DUPLICATE_RATE          DECIMAL(5,2)    NOT NULL,
    OUTLIER_RATE            DECIMAL(5,2)    NOT NULL,
    DISTINCT_COUNT          INT             NOT NULL,
    HEALTH_SCORE            DECIMAL(5,2)    NOT NULL,
    DATA_TYPE_CONSISTENCY   DECIMAL(5,2)    NOT NULL,
    STATUS                  VARCHAR(10)     NOT NULL,
    CONSTRAINT PK_DQ_COL_HEALTH PRIMARY KEY (HEALTH_ID)
)
COMMENT = 'Weekly column-level health metrics including null rates, duplicates, outliers, and overall health scores';
