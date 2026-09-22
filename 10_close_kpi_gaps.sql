-- ============================================================
-- INSURANCE AI HUB (E.D.I.E.) - Close KPI Gaps
-- Phase 10: Add missing columns + 7 new tables to enable
-- all 71 stakeholder KPIs
-- Run AFTER 09b_schema_evolution.sql
-- ============================================================
--
-- NOTE: All INSERT statements use pre-computed random values in
-- CTEs (UNIFORM/RANDOM inside GENERATOR) to avoid Snowflake's
-- "argument to RANDOM needs to be constant" error.
--

USE DATABASE INSURANCE_AI_HUB;
USE WAREHOUSE INSURANCE_AI_HUB_WH;

-- ============================================================
-- PART A: COLUMN ADDITIONS TO EXISTING TABLES
-- ============================================================

-- A1. AGENTS: Add APPLICATION_DATE for Agency Onboarding Velocity
ALTER TABLE ANALYTICS.AGENTS ADD COLUMN IF NOT EXISTS APPLICATION_DATE DATE;

UPDATE ANALYTICS.AGENTS
SET APPLICATION_DATE = DATEADD('day', -(14 + MOD(ABS(HASH(AGENT_ID)), 77)), HIRE_DATE)
WHERE APPLICATION_DATE IS NULL;

-- A2. CLAIMS: Add ESCALATION_FLAG for Escalation Rate
ALTER TABLE ANALYTICS.CLAIMS ADD COLUMN IF NOT EXISTS ESCALATION_FLAG BOOLEAN DEFAULT FALSE;

UPDATE ANALYTICS.CLAIMS
SET ESCALATION_FLAG = CASE
    WHEN LITIGATION_FLAG = TRUE THEN TRUE
    WHEN FRAUD_SCORE > 75 THEN TRUE
    WHEN CLAIM_AMOUNT > 100000 THEN TRUE
    WHEN MOD(ABS(HASH(CLAIM_ID)), 100) < 8 THEN TRUE
    ELSE FALSE
END;


-- ============================================================
-- PART B1: APPLICATIONS TABLE (~2,500 rows)
-- Covers: Underwriting Decline Rate, Quote-to-Bind Ratio
-- ============================================================
USE SCHEMA ANALYTICS;

CREATE TABLE IF NOT EXISTS APPLICATIONS (
    APPLICATION_ID          VARCHAR(20)     NOT NULL,
    CUSTOMER_ID             VARCHAR(20),
    AGENT_ID                VARCHAR(20),
    APPLICATION_DATE        DATE            NOT NULL,
    POLICY_TYPE             VARCHAR(20)     NOT NULL,
    REQUESTED_COVERAGE      DECIMAL(14,2)   NOT NULL,
    REQUESTED_PREMIUM       DECIMAL(12,2)   NOT NULL,
    RISK_SCORE              DECIMAL(5,2),
    UNDERWRITING_DECISION   VARCHAR(20)     NOT NULL,
    DECLINE_REASON          VARCHAR(100),
    QUOTE_AMOUNT            DECIMAL(12,2),
    QUOTE_DATE              DATE,
    BOUND_DATE              DATE,
    POLICY_ID               VARCHAR(20),
    STATUS                  VARCHAR(20)     NOT NULL,
    CREATED_AT              TIMESTAMP_NTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_APPLICATIONS PRIMARY KEY (APPLICATION_ID)
)
COMMENT = 'Policy applications with underwriting decisions, quotes, and bind outcomes for conversion tracking';

TRUNCATE TABLE IF EXISTS APPLICATIONS;

INSERT INTO APPLICATIONS
WITH
decline_reasons AS (
    SELECT ARRAY_CONSTRUCT('High Risk Score','Adverse Claims History','Insufficient Credit',
                           'Coverage Limit Exceeded','Regulatory Non-Compliance','Incomplete Documentation') AS arr
),
policy_types AS (
    SELECT ARRAY_CONSTRUCT('Auto','Auto','Auto','Home','Home','Life','Health','Health','Commercial','Commercial') AS arr
),
customer_ids AS (
    SELECT CUSTOMER_ID, ROW_NUMBER() OVER (ORDER BY CUSTOMER_ID) AS rn,
           COUNT(*) OVER () AS total FROM CUSTOMERS
),
agent_ids AS (
    SELECT AGENT_ID, ROW_NUMBER() OVER (ORDER BY AGENT_ID) AS rn,
           COUNT(*) OVER () AS total FROM AGENTS WHERE STATUS = 'Active'
),
policy_ids AS (
    SELECT POLICY_ID, ROW_NUMBER() OVER (ORDER BY POLICY_ID) AS rn,
           COUNT(*) OVER () AS total FROM POLICIES
),
raw AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn,
        UNIFORM(0, 1275, RANDOM()) AS r_days,
        UNIFORM(0, 9, RANDOM()) AS r_ptype,
        UNIFORM(25000, 2000000, RANDOM()) AS r_cov,
        UNIFORM(200, 5000, RANDOM()) AS r_prem,
        UNIFORM(15, 98, RANDOM()) AS r_risk,
        UNIFORM(1, 100, RANDOM()) AS r_decision,
        UNIFORM(0, 5, RANDOM()) AS r_decline,
        UNIFORM(1, 100, RANDOM()) AS r_bind,
        UNIFORM(1, 7, RANDOM()) AS r_quote_lag,
        UNIFORM(2, 21, RANDOM()) AS r_bind_lag,
        UNIFORM(90, 115, RANDOM()) AS r_quote_mult
    FROM TABLE(GENERATOR(ROWCOUNT => 2500))
)
SELECT
    'APP-' || LPAD(r.rn::VARCHAR, 5, '0'),
    c.CUSTOMER_ID,
    a.AGENT_ID,
    DATEADD('day', r.r_days, '2022-01-01'::DATE),
    policy_types.arr[r.r_ptype]::VARCHAR,
    ROUND(r.r_cov::DECIMAL(14,2), 2),
    ROUND(r.r_prem::DECIMAL(12,2), 2),
    ROUND(r.r_risk::DECIMAL(5,2), 2),
    CASE WHEN r.r_decision <= 65 THEN 'Approved'
         WHEN r.r_decision <= 85 THEN 'Declined'
         ELSE 'Referred' END,
    CASE WHEN r.r_decision > 65 AND r.r_decision <= 85
         THEN decline_reasons.arr[r.r_decline]::VARCHAR ELSE NULL END,
    CASE WHEN r.r_decision <= 65 OR r.r_decision > 85
         THEN ROUND(r.r_prem * r.r_quote_mult / 100.0, 2) ELSE NULL END,
    CASE WHEN r.r_decision <= 65 OR r.r_decision > 85
         THEN DATEADD('day', r.r_quote_lag, DATEADD('day', r.r_days, '2022-01-01'::DATE)) ELSE NULL END,
    CASE WHEN r.r_decision <= 65 AND r.r_bind <= 80
         THEN DATEADD('day', r.r_bind_lag, DATEADD('day', r.r_days, '2022-01-01'::DATE)) ELSE NULL END,
    CASE WHEN r.r_decision <= 65 AND r.r_bind <= 80
         THEN pol.POLICY_ID ELSE NULL END,
    CASE WHEN r.r_decision > 65 AND r.r_decision <= 85 THEN 'Declined'
         WHEN r.r_decision > 85 THEN 'UnderReview'
         WHEN r.r_bind <= 80 THEN 'Bound'
         WHEN r.r_bind <= 92 THEN 'QuoteExpired'
         ELSE 'Withdrawn' END,
    CURRENT_TIMESTAMP()
FROM raw r
CROSS JOIN policy_types
CROSS JOIN decline_reasons
JOIN customer_ids c ON c.rn = MOD(r.rn - 1, c.total) + 1
JOIN agent_ids a ON a.rn = MOD(r.rn - 1, a.total) + 1
LEFT JOIN policy_ids pol ON pol.rn = MOD(r.rn - 1, pol.total) + 1;


-- ============================================================
-- PART B2: POLICY_CHANGE_LOG (~1,500 rows)
-- Covers: Policy Endorsement Churn (tier downgrades)
-- ============================================================

CREATE TABLE IF NOT EXISTS POLICY_CHANGE_LOG (
    CHANGE_ID           VARCHAR(20)     NOT NULL,
    POLICY_ID           VARCHAR(20)     NOT NULL,
    CHANGE_DATE         DATE            NOT NULL,
    CHANGE_TYPE         VARCHAR(30)     NOT NULL,
    FIELD_CHANGED       VARCHAR(50)     NOT NULL,
    OLD_VALUE           VARCHAR(100),
    NEW_VALUE           VARCHAR(100),
    REASON              VARCHAR(100),
    REQUESTED_BY        VARCHAR(20),
    CREATED_AT          TIMESTAMP_NTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_POLICY_CHANGE_LOG PRIMARY KEY (CHANGE_ID)
)
COMMENT = 'Policy mid-term change log tracking tier changes, coverage adjustments, and endorsement modifications';

TRUNCATE TABLE IF EXISTS POLICY_CHANGE_LOG;

INSERT INTO POLICY_CHANGE_LOG
WITH
change_types AS (
    SELECT ARRAY_CONSTRUCT('TierDowngrade','TierDowngrade','TierUpgrade','CoverageReduction',
                           'CoverageIncrease','DeductibleChange','EndorsementAdd','EndorsementRemove') AS arr
),
tiers AS (
    SELECT ARRAY_CONSTRUCT('Basic','Standard','Preferred','Elite') AS arr
),
reasons AS (
    SELECT ARRAY_CONSTRUCT('Customer Request','Cost Reduction','Life Event','Annual Review',
                           'Risk Reassessment','Agent Recommendation') AS arr
),
policy_data AS (
    SELECT POLICY_ID, COVERAGE_TIER, COVERAGE_AMOUNT, DEDUCTIBLE, EFFECTIVE_DATE,
           ROW_NUMBER() OVER (ORDER BY POLICY_ID) AS rn,
           COUNT(*) OVER () AS total
    FROM POLICIES WHERE STATUS IN ('InForce','Renewed')
),
raw AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn,
        UNIFORM(0, 7, RANDOM()) AS r_chtype,
        UNIFORM(30, 300, RANDOM()) AS r_days,
        UNIFORM(0, 5, RANDOM()) AS r_reason,
        UNIFORM(1, 100, RANDOM()) AS r_req,
        UNIFORM(80, 150, RANDOM()) AS r_ded_mult
    FROM TABLE(GENERATOR(ROWCOUNT => 1500))
)
SELECT
    'CHG-' || LPAD(r.rn::VARCHAR, 5, '0'),
    p.POLICY_ID,
    DATEADD('day', r.r_days, p.EFFECTIVE_DATE),
    change_types.arr[r.r_chtype]::VARCHAR,
    CASE change_types.arr[r.r_chtype]::VARCHAR
        WHEN 'TierDowngrade' THEN 'COVERAGE_TIER'
        WHEN 'TierUpgrade' THEN 'COVERAGE_TIER'
        WHEN 'CoverageReduction' THEN 'COVERAGE_AMOUNT'
        WHEN 'CoverageIncrease' THEN 'COVERAGE_AMOUNT'
        WHEN 'DeductibleChange' THEN 'DEDUCTIBLE'
        ELSE 'ENDORSEMENT_TYPE'
    END,
    CASE change_types.arr[r.r_chtype]::VARCHAR
        WHEN 'TierDowngrade' THEN p.COVERAGE_TIER
        WHEN 'TierUpgrade' THEN p.COVERAGE_TIER
        WHEN 'CoverageReduction' THEN p.COVERAGE_AMOUNT::VARCHAR
        WHEN 'CoverageIncrease' THEN p.COVERAGE_AMOUNT::VARCHAR
        WHEN 'DeductibleChange' THEN p.DEDUCTIBLE::VARCHAR
        ELSE NULL
    END,
    CASE change_types.arr[r.r_chtype]::VARCHAR
        WHEN 'TierDowngrade' THEN tiers.arr[GREATEST(0, ARRAY_POSITION(p.COVERAGE_TIER::VARIANT, tiers.arr) - 1)]::VARCHAR
        WHEN 'TierUpgrade' THEN tiers.arr[LEAST(3, COALESCE(ARRAY_POSITION(p.COVERAGE_TIER::VARIANT, tiers.arr), 0) + 1)]::VARCHAR
        WHEN 'CoverageReduction' THEN ROUND(p.COVERAGE_AMOUNT * 0.75, 2)::VARCHAR
        WHEN 'CoverageIncrease' THEN ROUND(p.COVERAGE_AMOUNT * 1.25, 2)::VARCHAR
        WHEN 'DeductibleChange' THEN ROUND(p.DEDUCTIBLE * r.r_ded_mult / 100.0, 2)::VARCHAR
        WHEN 'EndorsementAdd' THEN 'Rider'
        ELSE 'Waiver'
    END,
    reasons.arr[r.r_reason]::VARCHAR,
    CASE WHEN r.r_req <= 60 THEN 'Customer' ELSE 'Agent' END,
    CURRENT_TIMESTAMP()
FROM raw r
CROSS JOIN change_types
CROSS JOIN tiers
CROSS JOIN reasons
JOIN policy_data p ON p.rn = MOD(r.rn - 1, p.total) + 1;


-- ============================================================
-- PART B3: CUSTOMER_SURVEYS (~3,000 rows)
-- Covers: NPS (full customer base)
-- ============================================================

CREATE TABLE IF NOT EXISTS CUSTOMER_SURVEYS (
    SURVEY_ID           VARCHAR(20)     NOT NULL,
    CUSTOMER_ID         VARCHAR(20)     NOT NULL,
    POLICY_ID           VARCHAR(20),
    SURVEY_DATE         DATE            NOT NULL,
    SURVEY_TYPE         VARCHAR(10)     NOT NULL,
    NPS_RATING          INT             NOT NULL,
    PROMOTER_CATEGORY   VARCHAR(15)     NOT NULL,
    SATISFACTION_SCORE  DECIMAL(3,1),
    COMMENTS            TEXT,
    CHANNEL             VARCHAR(20)     NOT NULL,
    CONSTRAINT PK_SURVEYS PRIMARY KEY (SURVEY_ID)
)
COMMENT = 'Customer survey responses including NPS ratings, satisfaction scores, and feedback for retention analytics';

TRUNCATE TABLE IF EXISTS CUSTOMER_SURVEYS;

INSERT INTO CUSTOMER_SURVEYS
WITH
channels AS (
    SELECT ARRAY_CONSTRUCT('Email','SMS','Phone','WebPortal','MobileApp','InPerson') AS arr
),
comments_pos AS (
    SELECT ARRAY_CONSTRUCT(
        'Great service, very responsive agent.',
        'Claims process was smooth and fast.',
        'Happy with my coverage and premium rate.',
        'Agent went above and beyond to help.',
        'Easy online portal for policy management.',
        'Quick turnaround on my claim.') AS arr
),
comments_neg AS (
    SELECT ARRAY_CONSTRUCT(
        'Claim took too long to resolve.',
        'Premium increase was unexpected.',
        'Hard to reach customer service.',
        'Denied claim without clear explanation.',
        'Website is difficult to navigate.',
        'Agent never follows up.') AS arr
),
customer_ids AS (
    SELECT CUSTOMER_ID, ROW_NUMBER() OVER (ORDER BY CUSTOMER_ID) AS rn,
           COUNT(*) OVER () AS total FROM CUSTOMERS
),
policy_ids AS (
    SELECT POLICY_ID, ROW_NUMBER() OVER (ORDER BY POLICY_ID) AS rn,
           COUNT(*) OVER () AS total FROM POLICIES
),
raw AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn,
        UNIFORM(0, 1275, RANDOM()) AS r_days,
        UNIFORM(1, 100, RANDOM()) AS r_type,
        UNIFORM(1, 100, RANDOM()) AS r_nps_band,
        UNIFORM(0, 1, RANDOM()) AS r_nps_promo,
        UNIFORM(7, 8, RANDOM()) AS r_nps_passive,
        UNIFORM(0, 6, RANDOM()) AS r_nps_detract,
        UNIFORM(10, 50, RANDOM()) AS r_sat,
        UNIFORM(0, 5, RANDOM()) AS r_channel,
        UNIFORM(0, 5, RANDOM()) AS r_comment
    FROM TABLE(GENERATOR(ROWCOUNT => 3000))
)
SELECT
    'SRV-' || LPAD(r.rn::VARCHAR, 5, '0'),
    c.CUSTOMER_ID,
    pol.POLICY_ID,
    DATEADD('day', r.r_days, '2022-01-01'::DATE),
    CASE WHEN r.r_type <= 70 THEN 'NPS' WHEN r.r_type <= 90 THEN 'CSAT' ELSE 'CES' END,
    CASE WHEN r.r_nps_band <= 30 THEN 9 + r.r_nps_promo
         WHEN r.r_nps_band <= 70 THEN r.r_nps_passive
         ELSE r.r_nps_detract END,
    CASE WHEN r.r_nps_band <= 30 THEN 'Promoter'
         WHEN r.r_nps_band <= 70 THEN 'Passive'
         ELSE 'Detractor' END,
    ROUND(r.r_sat / 10.0, 1),
    CASE WHEN r.r_nps_band <= 30 THEN comments_pos.arr[r.r_comment]::VARCHAR
         WHEN r.r_nps_band <= 70 THEN NULL
         ELSE comments_neg.arr[r.r_comment]::VARCHAR END,
    channels.arr[r.r_channel]::VARCHAR
FROM raw r
CROSS JOIN channels
CROSS JOIN comments_pos
CROSS JOIN comments_neg
JOIN customer_ids c ON c.rn = MOD(r.rn - 1, c.total) + 1
LEFT JOIN policy_ids pol ON pol.rn = MOD(r.rn - 1, pol.total) + 1;


-- ============================================================
-- PART B4: FINANCIAL_LEDGER (~500 rows)
-- Covers: Loss Reserve Adequacy, Investment Yield, Audit Premium Recovery
-- ============================================================

CREATE TABLE IF NOT EXISTS FINANCIAL_LEDGER (
    LEDGER_ID           VARCHAR(20)     NOT NULL,
    ENTRY_DATE          DATE            NOT NULL,
    FISCAL_QUARTER      VARCHAR(10)     NOT NULL,
    ACCOUNT_TYPE        VARCHAR(30)     NOT NULL,
    ACCOUNT_SUBTYPE     VARCHAR(50),
    LINE_OF_BUSINESS    VARCHAR(20),
    AMOUNT              DECIMAL(14,2)   NOT NULL,
    DESCRIPTION         VARCHAR(200),
    CREATED_AT          TIMESTAMP_NTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_FINANCIAL_LEDGER PRIMARY KEY (LEDGER_ID)
)
COMMENT = 'Financial ledger entries for loss reserves, investment income, audit adjustments, and operating expenses';

TRUNCATE TABLE IF EXISTS FINANCIAL_LEDGER;

INSERT INTO FINANCIAL_LEDGER
WITH
lobs AS (
    SELECT ARRAY_CONSTRUCT('Auto','Home','Life','Health','Commercial') AS arr
),
account_types AS (
    SELECT ARRAY_CONSTRUCT('LossReserve','InvestmentIncome','AuditAdjustment','OperatingExpense','CapitalReserve') AS arr
),
subtypes AS (
    SELECT ARRAY_CONSTRUCT('Incurred But Not Reported','Fixed Income Portfolio','Premium Audit Recovery',
                           'Underwriting Operations','Statutory Surplus') AS arr
),
descriptions AS (
    SELECT ARRAY_CONSTRUCT(
        'IBNR reserve allocation','Quarterly investment income from bond portfolio',
        'Audit premium adjustment - payroll audit','Underwriting department operating costs',
        'Statutory capital surplus reserve') AS arr
),
quarters AS (
    SELECT VALUE::VARCHAR AS q,
           ROW_NUMBER() OVER (ORDER BY INDEX) AS qrn
    FROM TABLE(FLATTEN(ARRAY_CONSTRUCT(
        '2022-Q1','2022-Q2','2022-Q3','2022-Q4',
        '2023-Q1','2023-Q2','2023-Q3','2023-Q4',
        '2024-Q1','2024-Q2','2024-Q3','2024-Q4',
        '2025-Q1','2025-Q2')))
),
raw AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn,
        UNIFORM(0, 89, RANDOM()) AS r_dayoff,
        UNIFORM(0, 4, RANDOM()) AS r_lob,
        UNIFORM(0, 4, RANDOM()) AS r_acct,
        UNIFORM(500000, 15000000, RANDOM()) AS r_amt_big,
        UNIFORM(10000, 500000, RANDOM()) AS r_amt_med,
        UNIFORM(50000, 1000000, RANDOM()) AS r_amt_sm
    FROM TABLE(GENERATOR(ROWCOUNT => 500))
)
SELECT
    'FIN-' || LPAD(r.rn::VARCHAR, 5, '0'),
    DATEADD('day', r.r_dayoff,
        DATE_FROM_PARTS(LEFT(q.q, 4)::INT,
            CASE RIGHT(q.q, 1) WHEN '1' THEN 1 WHEN '2' THEN 4 WHEN '3' THEN 7 ELSE 10 END, 1)),
    q.q,
    account_types.arr[r.r_acct]::VARCHAR,
    subtypes.arr[r.r_acct]::VARCHAR,
    lobs.arr[r.r_lob]::VARCHAR,
    CASE r.r_acct
        WHEN 0 THEN ROUND(r.r_amt_big::DECIMAL(14,2), 2)
        WHEN 1 THEN ROUND(r.r_amt_med::DECIMAL(14,2), 2)
        WHEN 2 THEN ROUND(r.r_amt_med::DECIMAL(14,2) * 0.4, 2)
        WHEN 3 THEN ROUND(r.r_amt_sm::DECIMAL(14,2), 2)
        ELSE ROUND(r.r_amt_big::DECIMAL(14,2), 2)
    END,
    descriptions.arr[r.r_acct]::VARCHAR,
    CURRENT_TIMESTAMP()
FROM raw r
CROSS JOIN account_types
CROSS JOIN subtypes
CROSS JOIN descriptions
CROSS JOIN lobs
JOIN quarters q ON q.qrn = MOD(r.rn - 1, 14) + 1;


-- ============================================================
-- PART B5: REINSURANCE_TREATIES + REINSURANCE_RECOVERIES
-- Covers: Reinsurance Recovery Rate (full)
-- ============================================================

CREATE TABLE IF NOT EXISTS REINSURANCE_TREATIES (
    TREATY_ID           VARCHAR(20)     NOT NULL,
    TREATY_NAME         VARCHAR(100)    NOT NULL,
    TREATY_TYPE         VARCHAR(30)     NOT NULL,
    REINSURER_NAME      VARCHAR(100)    NOT NULL,
    RETENTION_LIMIT     DECIMAL(14,2)   NOT NULL,
    CESSION_RATE        DECIMAL(5,4),
    MAX_CESSION         DECIMAL(14,2),
    EFFECTIVE_DATE      DATE            NOT NULL,
    EXPIRATION_DATE     DATE            NOT NULL,
    LINE_OF_BUSINESS    VARCHAR(20),
    STATUS              VARCHAR(15)     NOT NULL,
    CONSTRAINT PK_REINSURANCE_TREATIES PRIMARY KEY (TREATY_ID)
)
COMMENT = 'Reinsurance treaty definitions with retention limits, cession rates, and reinsurer details';

TRUNCATE TABLE IF EXISTS REINSURANCE_TREATIES;

INSERT INTO REINSURANCE_TREATIES VALUES
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


CREATE TABLE IF NOT EXISTS REINSURANCE_RECOVERIES (
    RECOVERY_ID         VARCHAR(20)     NOT NULL,
    TREATY_ID           VARCHAR(20)     NOT NULL,
    CLAIM_ID            VARCHAR(20)     NOT NULL,
    GROSS_LOSS          DECIMAL(14,2)   NOT NULL,
    CEDED_AMOUNT        DECIMAL(14,2)   NOT NULL,
    RECOVERED_AMOUNT    DECIMAL(14,2)   NOT NULL,
    RECOVERY_DATE       DATE,
    STATUS              VARCHAR(15)     NOT NULL,
    CONSTRAINT PK_REINSURANCE_RECOVERIES PRIMARY KEY (RECOVERY_ID),
    CONSTRAINT FK_RR_TREATY FOREIGN KEY (TREATY_ID) REFERENCES REINSURANCE_TREATIES(TREATY_ID)
)
COMMENT = 'Reinsurance recovery records linking claims to treaty cessions with recovery amounts and status';

TRUNCATE TABLE IF EXISTS REINSURANCE_RECOVERIES;

INSERT INTO REINSURANCE_RECOVERIES
WITH
large_claims AS (
    SELECT CLAIM_ID, CLAIM_AMOUNT, APPROVED_AMOUNT, CLAIM_DATE,
           ROW_NUMBER() OVER (ORDER BY CLAIM_AMOUNT DESC) AS rn
    FROM CLAIMS
    WHERE CLAIM_AMOUNT > 8000 AND STATUS IN ('Approved','Closed','PartiallyPaid','Subrogation')
    LIMIT 400
),
treaty_data AS (
    SELECT TREATY_ID, RETENTION_LIMIT, CESSION_RATE,
           ROW_NUMBER() OVER (ORDER BY TREATY_ID) AS rn,
           COUNT(*) OVER () AS total
    FROM REINSURANCE_TREATIES
),
raw_rand AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn,
        UNIFORM(1, 100, RANDOM()) AS r_status,
        UNIFORM(40, 80, RANDOM()) AS r_partial,
        UNIFORM(30, 120, RANDOM()) AS r_recdays
    FROM TABLE(GENERATOR(ROWCOUNT => 400))
)
SELECT
    'RRC-' || LPAD(lc.rn::VARCHAR, 5, '0'),
    t.TREATY_ID,
    lc.CLAIM_ID,
    lc.CLAIM_AMOUNT,
    ROUND(lc.CLAIM_AMOUNT * COALESCE(t.CESSION_RATE, 0.50), 2),
    ROUND(lc.CLAIM_AMOUNT * COALESCE(t.CESSION_RATE, 0.50) *
          CASE WHEN rr.r_status <= 60 THEN 1.00
               WHEN rr.r_status <= 75 THEN rr.r_partial / 100.0
               ELSE 0.00 END, 2),
    CASE WHEN rr.r_status <= 75
         THEN DATEADD('day', rr.r_recdays, lc.CLAIM_DATE)
         ELSE NULL END,
    CASE WHEN rr.r_status <= 60 THEN 'Recovered'
         WHEN rr.r_status <= 75 THEN 'Partial'
         WHEN rr.r_status <= 90 THEN 'Pending'
         ELSE 'Disputed' END
FROM large_claims lc
JOIN treaty_data t ON t.rn = MOD(lc.rn - 1, t.total) + 1
JOIN raw_rand rr ON rr.rn = lc.rn;


-- ============================================================
-- PART B6: SCHEMA_AUDIT_LOG (~300 rows) in DATA_QUALITY
-- Covers: Schema Drift Alerts
-- ============================================================
USE SCHEMA DATA_QUALITY;

CREATE TABLE IF NOT EXISTS SCHEMA_AUDIT_LOG (
    AUDIT_ID            VARCHAR(20)     NOT NULL,
    SCHEMA_NAME         VARCHAR(30)     NOT NULL,
    TABLE_NAME          VARCHAR(30)     NOT NULL,
    COLUMN_NAME         VARCHAR(50),
    EVENT_TYPE          VARCHAR(30)     NOT NULL,
    OLD_VALUE           VARCHAR(200),
    NEW_VALUE           VARCHAR(200),
    DETECTED_AT         TIMESTAMP_NTZ   NOT NULL,
    SEVERITY            VARCHAR(10)     NOT NULL,
    ACKNOWLEDGED        BOOLEAN         NOT NULL DEFAULT FALSE,
    ACKNOWLEDGED_BY     VARCHAR(50),
    CONSTRAINT PK_SCHEMA_AUDIT PRIMARY KEY (AUDIT_ID)
)
COMMENT = 'Schema drift detection log tracking column additions, removals, type changes, and renames across all schemas';

TRUNCATE TABLE IF EXISTS SCHEMA_AUDIT_LOG;

INSERT INTO SCHEMA_AUDIT_LOG
WITH
schemas_arr AS (SELECT ARRAY_CONSTRUCT('ANALYTICS','ANALYTICS','ANALYTICS','DOCUMENTS','DATA_QUALITY') AS arr),
analytics_tables AS (SELECT ARRAY_CONSTRUCT('CUSTOMERS','AGENTS','POLICIES','CLAIMS','BILLING','AT_RISK_POLICIES') AS arr),
docs_tables AS (SELECT ARRAY_CONSTRUCT('POLICY_DOCUMENTS','DOCUMENT_CHUNKS') AS arr),
dq_tables AS (SELECT ARRAY_CONSTRUCT('DQ_RULES','DQ_RESULTS','DQ_SCORES','DQ_COLUMN_HEALTH') AS arr),
event_types AS (SELECT ARRAY_CONSTRUCT('ColumnAdded','ColumnAdded','ColumnDropped','TypeChanged','ColumnRenamed','NullabilityChanged','DefaultChanged') AS arr),
severities AS (SELECT ARRAY_CONSTRUCT('Critical','Critical','High','High','Medium','Medium','Medium','Low','Low','Low') AS arr),
col_names AS (SELECT ARRAY_CONSTRUCT('TEMP_FLAG','LEGACY_CODE','OLD_STATUS','MIGRATION_ID','BACKUP_DATE','ETL_BATCH_ID','SOURCE_SYSTEM_V2','ARCHIVED_FLAG','REVIEW_SCORE','CONTACT_PREF') AS arr),
raw AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn,
        UNIFORM(0, 4, RANDOM()) AS r_schema,
        UNIFORM(0, 5, RANDOM()) AS r_tbl_a,
        UNIFORM(0, 1, RANDOM()) AS r_tbl_d,
        UNIFORM(0, 3, RANDOM()) AS r_tbl_q,
        UNIFORM(0, 9, RANDOM()) AS r_col,
        UNIFORM(0, 6, RANDOM()) AS r_evt,
        UNIFORM(0, 9, RANDOM()) AS r_sev,
        UNIFORM(0, 1275, RANDOM()) AS r_days,
        UNIFORM(0, 86400, RANDOM()) AS r_secs,
        UNIFORM(1, 100, RANDOM()) AS r_ack
    FROM TABLE(GENERATOR(ROWCOUNT => 300))
)
SELECT
    'SAD-' || LPAD(r.rn::VARCHAR, 5, '0'),
    schemas_arr.arr[r.r_schema]::VARCHAR,
    CASE schemas_arr.arr[r.r_schema]::VARCHAR
        WHEN 'ANALYTICS' THEN analytics_tables.arr[r.r_tbl_a]::VARCHAR
        WHEN 'DOCUMENTS' THEN docs_tables.arr[r.r_tbl_d]::VARCHAR
        ELSE dq_tables.arr[r.r_tbl_q]::VARCHAR
    END,
    col_names.arr[r.r_col]::VARCHAR,
    event_types.arr[r.r_evt]::VARCHAR,
    CASE event_types.arr[r.r_evt]::VARCHAR
        WHEN 'TypeChanged' THEN 'VARCHAR(50)'
        WHEN 'ColumnRenamed' THEN col_names.arr[r.r_col]::VARCHAR
        WHEN 'ColumnDropped' THEN col_names.arr[r.r_col]::VARCHAR
        WHEN 'NullabilityChanged' THEN 'NOT NULL'
        WHEN 'DefaultChanged' THEN 'NULL'
        ELSE NULL
    END,
    CASE event_types.arr[r.r_evt]::VARCHAR
        WHEN 'TypeChanged' THEN 'VARCHAR(200)'
        WHEN 'ColumnRenamed' THEN col_names.arr[r.r_col]::VARCHAR || '_V2'
        WHEN 'ColumnAdded' THEN 'VARCHAR(100)'
        WHEN 'NullabilityChanged' THEN 'NULLABLE'
        WHEN 'DefaultChanged' THEN '0'
        ELSE NULL
    END,
    DATEADD('second', r.r_secs, DATEADD('day', r.r_days, '2022-01-01'::DATE))::TIMESTAMP_NTZ,
    severities.arr[r.r_sev]::VARCHAR,
    CASE WHEN r.r_ack <= 65 THEN TRUE ELSE FALSE END,
    CASE WHEN r.r_ack <= 65 THEN 'data_ops_team' ELSE NULL END
FROM raw r
CROSS JOIN schemas_arr CROSS JOIN analytics_tables CROSS JOIN docs_tables
CROSS JOIN dq_tables CROSS JOIN event_types CROSS JOIN severities CROSS JOIN col_names;


-- ============================================================
-- PART B7: RAG_QUERY_LOG (~5,000 rows) in DOCUMENTS
-- Covers: Coverage Search Query Rate
-- ============================================================
USE SCHEMA DOCUMENTS;

CREATE TABLE IF NOT EXISTS RAG_QUERY_LOG (
    QUERY_ID            VARCHAR(20)     NOT NULL,
    USER_ROLE           VARCHAR(30)     NOT NULL,
    QUERY_TEXT          TEXT            NOT NULL,
    QUERY_DATE          TIMESTAMP_NTZ   NOT NULL,
    DOCUMENTS_RETURNED  INT             NOT NULL,
    CHUNKS_RETRIEVED    INT             NOT NULL,
    RESPONSE_TIME_MS    INT             NOT NULL,
    QUERY_SOURCE        VARCHAR(30)     NOT NULL,
    RELEVANCE_SCORE     DECIMAL(5,4),
    POLICY_ID           VARCHAR(20),
    CONSTRAINT PK_RAG_QUERY PRIMARY KEY (QUERY_ID)
)
COMMENT = 'RAG query log tracking contract search queries, retrieval counts, response times, and relevance scores';

TRUNCATE TABLE IF EXISTS RAG_QUERY_LOG;

INSERT INTO RAG_QUERY_LOG
WITH
queries AS (
    SELECT ARRAY_CONSTRUCT(
        'What are the flood exclusion clauses?',
        'Does this policy cover mold damage?',
        'What is the deductible for windstorm events?',
        'Find cyber liability coverage terms',
        'What are the subrogation rights?',
        'Show me the business interruption waiting period',
        'What triggers the umbrella policy?',
        'Find the professional liability exclusions',
        'What is covered under inland marine?',
        'Are pandemic losses excluded?',
        'What is the coinsurance clause?',
        'Find the cancellation provisions',
        'What endorsements apply to earthquake coverage?',
        'Show workers compensation class codes',
        'What are the pollution exclusions?',
        'Find the terrorism risk insurance terms',
        'What is the aggregate limit for product liability?',
        'Show me the named insured schedule',
        'Find the loss payee requirements',
        'What are the reporting requirements for claims?'
    ) AS arr
),
sources AS (SELECT ARRAY_CONSTRUCT('Underwriting','Underwriting','Underwriting','Claims','Claims','CustomerService','CustomerService','Legal','Compliance','AgentPortal') AS arr),
roles AS (SELECT ARRAY_CONSTRUCT('Underwriter','ClaimsAdjuster','SeniorUnderwriter','PolicyAnalyst','ComplianceOfficer','AgentSupport') AS arr),
policy_data AS (
    SELECT POLICY_ID, ROW_NUMBER() OVER (ORDER BY POLICY_ID) AS rn,
           COUNT(*) OVER () AS total
    FROM POLICY_DOCUMENTS
),
raw AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn,
        UNIFORM(0, 5, RANDOM()) AS r_role,
        UNIFORM(0, 19, RANDOM()) AS r_query,
        UNIFORM(0, 1275, RANDOM()) AS r_days,
        UNIFORM(0, 86400, RANDOM()) AS r_secs,
        UNIFORM(1, 5, RANDOM()) AS r_docs,
        UNIFORM(3, 20, RANDOM()) AS r_chunks,
        UNIFORM(150, 3000, RANDOM()) AS r_resp,
        UNIFORM(0, 9, RANDOM()) AS r_src,
        UNIFORM(3500, 9800, RANDOM()) AS r_rel
    FROM TABLE(GENERATOR(ROWCOUNT => 5000))
)
SELECT
    'RQL-' || LPAD(r.rn::VARCHAR, 5, '0'),
    roles.arr[r.r_role]::VARCHAR,
    queries.arr[r.r_query]::VARCHAR,
    DATEADD('second', r.r_secs, DATEADD('day', r.r_days, '2022-01-01'::DATE))::TIMESTAMP_NTZ,
    r.r_docs,
    r.r_chunks,
    r.r_resp,
    sources.arr[r.r_src]::VARCHAR,
    ROUND(r.r_rel / 10000.0, 4),
    pd.POLICY_ID
FROM raw r
CROSS JOIN queries CROSS JOIN sources CROSS JOIN roles
JOIN policy_data pd ON pd.rn = MOD(r.rn - 1, pd.total) + 1;


-- ============================================================
-- VERIFICATION: Row counts for all new/modified tables
-- ============================================================
SELECT 'AGENTS (APPLICATION_DATE)' AS CHECK_ITEM,
       COUNT(*) AS ROW_COUNT,
       COUNT(APPLICATION_DATE) AS NON_NULL_COUNT
FROM INSURANCE_AI_HUB.ANALYTICS.AGENTS
UNION ALL
SELECT 'CLAIMS (ESCALATION_FLAG)',
       COUNT(*),
       SUM(CASE WHEN ESCALATION_FLAG = TRUE THEN 1 ELSE 0 END)
FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS
UNION ALL
SELECT 'APPLICATIONS', COUNT(*), NULL FROM INSURANCE_AI_HUB.ANALYTICS.APPLICATIONS
UNION ALL
SELECT 'POLICY_CHANGE_LOG', COUNT(*), NULL FROM INSURANCE_AI_HUB.ANALYTICS.POLICY_CHANGE_LOG
UNION ALL
SELECT 'CUSTOMER_SURVEYS', COUNT(*), NULL FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMER_SURVEYS
UNION ALL
SELECT 'FINANCIAL_LEDGER', COUNT(*), NULL FROM INSURANCE_AI_HUB.ANALYTICS.FINANCIAL_LEDGER
UNION ALL
SELECT 'REINSURANCE_TREATIES', COUNT(*), NULL FROM INSURANCE_AI_HUB.ANALYTICS.REINSURANCE_TREATIES
UNION ALL
SELECT 'REINSURANCE_RECOVERIES', COUNT(*), NULL FROM INSURANCE_AI_HUB.ANALYTICS.REINSURANCE_RECOVERIES
UNION ALL
SELECT 'SCHEMA_AUDIT_LOG', COUNT(*), NULL FROM INSURANCE_AI_HUB.DATA_QUALITY.SCHEMA_AUDIT_LOG
UNION ALL
SELECT 'RAG_QUERY_LOG', COUNT(*), NULL FROM INSURANCE_AI_HUB.DOCUMENTS.RAG_QUERY_LOG;
