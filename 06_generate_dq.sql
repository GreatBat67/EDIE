-- ============================================================
-- INSURANCE AI HUB (E.D.I.E.) - Data Quality Observability Layer
-- Phase 3d: DQ_RULES (50), DQ_RESULTS (5,000), DQ_SCORES (1,000), DQ_COLUMN_HEALTH (3,000)
-- ============================================================

USE DATABASE INSURANCE_AI_HUB;
USE WAREHOUSE INSURANCE_AI_HUB_WH;
USE SCHEMA DATA_QUALITY;

-- ============================================================
-- DQ_RULES - 50 rows
-- Realistic data quality rules across all ANALYTICS tables
-- ============================================================

INSERT INTO DQ_RULES VALUES
-- CUSTOMERS table rules (10 rules)
('DQR-001','customers_email_not_null','Email address should not be null for active customers','ANALYTICS','CUSTOMERS','EMAIL','Completeness','SELECT COUNT(*) FROM ANALYTICS.CUSTOMERS WHERE EMAIL IS NULL','95.00','High',TRUE),
('DQR-002','customers_phone_not_null','Phone number should not be null','ANALYTICS','CUSTOMERS','PHONE','Completeness','SELECT COUNT(*) FROM ANALYTICS.CUSTOMERS WHERE PHONE IS NULL','90.00','Medium',TRUE),
('DQR-003','customers_email_format','Email must contain @ and valid domain','ANALYTICS','CUSTOMERS','EMAIL','Validity','SELECT COUNT(*) FROM ANALYTICS.CUSTOMERS WHERE EMAIL NOT LIKE ''%@%.%''','98.00','High',TRUE),
('DQR-004','customers_credit_score_range','Credit score must be between 300 and 850','ANALYTICS','CUSTOMERS','CREDIT_SCORE','Validity','SELECT COUNT(*) FROM ANALYTICS.CUSTOMERS WHERE CREDIT_SCORE NOT BETWEEN 300 AND 850','99.00','Critical',TRUE),
('DQR-005','customers_unique_id','Customer ID must be unique','ANALYTICS','CUSTOMERS','CUSTOMER_ID','Uniqueness','SELECT COUNT(*) - COUNT(DISTINCT CUSTOMER_ID) FROM ANALYTICS.CUSTOMERS','100.00','Critical',TRUE),
('DQR-006','customers_state_valid','State must be a valid 2-letter US state code','ANALYTICS','CUSTOMERS','STATE','Validity','SELECT COUNT(*) FROM ANALYTICS.CUSTOMERS WHERE LENGTH(STATE) != 2','99.00','Medium',TRUE),
('DQR-007','customers_dob_reasonable','Date of birth must be between 1940 and 2007','ANALYTICS','CUSTOMERS','DATE_OF_BIRTH','Validity','SELECT COUNT(*) FROM ANALYTICS.CUSTOMERS WHERE DATE_OF_BIRTH < ''1940-01-01'' OR DATE_OF_BIRTH > ''2007-01-01''','99.50','High',TRUE),
('DQR-008','customers_risk_tier_valid','Risk tier must be Low, Medium, High, or Critical','ANALYTICS','CUSTOMERS','RISK_TIER','Validity','SELECT COUNT(*) FROM ANALYTICS.CUSTOMERS WHERE RISK_TIER NOT IN (''Low'',''Medium'',''High'',''Critical'')','100.00','Critical',TRUE),
('DQR-009','customers_segment_valid','Segment must be Premium, Standard, or Budget','ANALYTICS','CUSTOMERS','SEGMENT','Validity','SELECT COUNT(*) FROM ANALYTICS.CUSTOMERS WHERE SEGMENT NOT IN (''Premium'',''Standard'',''Budget'')','100.00','Critical',TRUE),
('DQR-010','customers_since_not_future','Customer since date should not be in the future','ANALYTICS','CUSTOMERS','CUSTOMER_SINCE','Timeliness','SELECT COUNT(*) FROM ANALYTICS.CUSTOMERS WHERE CUSTOMER_SINCE > CURRENT_DATE()','100.00','High',TRUE),

-- AGENTS table rules (5 rules)
('DQR-011','agents_unique_license','License number must be unique per agent','ANALYTICS','AGENTS','LICENSE_NUMBER','Uniqueness','SELECT COUNT(*) - COUNT(DISTINCT LICENSE_NUMBER) FROM ANALYTICS.AGENTS','100.00','Critical',TRUE),
('DQR-012','agents_performance_range','Performance rating must be between 1.00 and 5.00','ANALYTICS','AGENTS','PERFORMANCE_RATING','Validity','SELECT COUNT(*) FROM ANALYTICS.AGENTS WHERE PERFORMANCE_RATING NOT BETWEEN 1.00 AND 5.00','100.00','High',TRUE),
('DQR-013','agents_region_valid','Region must be a valid US region','ANALYTICS','AGENTS','REGION','Validity','SELECT COUNT(*) FROM ANALYTICS.AGENTS WHERE REGION NOT IN (''Northeast'',''Southeast'',''Midwest'',''West'',''Southwest'')','100.00','Medium',TRUE),
('DQR-014','agents_status_valid','Status must be Active or Inactive','ANALYTICS','AGENTS','STATUS','Validity','SELECT COUNT(*) FROM ANALYTICS.AGENTS WHERE STATUS NOT IN (''Active'',''Inactive'')','100.00','Critical',TRUE),
('DQR-015','agents_active_policies_positive','Active policies count must be non-negative','ANALYTICS','AGENTS','ACTIVE_POLICIES_COUNT','Validity','SELECT COUNT(*) FROM ANALYTICS.AGENTS WHERE ACTIVE_POLICIES_COUNT < 0','100.00','Medium',TRUE),

-- POLICIES table rules (10 rules)
('DQR-016','policies_unique_id','Policy ID must be unique','ANALYTICS','POLICIES','POLICY_ID','Uniqueness','SELECT COUNT(*) - COUNT(DISTINCT POLICY_ID) FROM ANALYTICS.POLICIES','100.00','Critical',TRUE),
('DQR-017','policies_valid_customer','Customer ID must exist in CUSTOMERS table','ANALYTICS','POLICIES','CUSTOMER_ID','Consistency','SELECT COUNT(*) FROM ANALYTICS.POLICIES p WHERE NOT EXISTS (SELECT 1 FROM ANALYTICS.CUSTOMERS c WHERE c.CUSTOMER_ID = p.CUSTOMER_ID)','100.00','Critical',TRUE),
('DQR-018','policies_valid_agent','Agent ID must exist in AGENTS table','ANALYTICS','POLICIES','AGENT_ID','Consistency','SELECT COUNT(*) FROM ANALYTICS.POLICIES p WHERE NOT EXISTS (SELECT 1 FROM ANALYTICS.AGENTS a WHERE a.AGENT_ID = p.AGENT_ID)','100.00','Critical',TRUE),
('DQR-019','policies_end_after_start','End date must be after start date','ANALYTICS','POLICIES','END_DATE','Validity','SELECT COUNT(*) FROM ANALYTICS.POLICIES WHERE END_DATE <= START_DATE','100.00','Critical',TRUE),
('DQR-020','policies_premium_positive','Premium amount must be positive','ANALYTICS','POLICIES','PREMIUM_AMOUNT','Validity','SELECT COUNT(*) FROM ANALYTICS.POLICIES WHERE PREMIUM_AMOUNT <= 0','100.00','Critical',TRUE),
('DQR-021','policies_coverage_exceeds_premium','Coverage must exceed annual premium','ANALYTICS','POLICIES','COVERAGE_AMOUNT','Validity','SELECT COUNT(*) FROM ANALYTICS.POLICIES WHERE COVERAGE_AMOUNT < PREMIUM_AMOUNT * 12','99.00','High',TRUE),
('DQR-022','policies_type_valid','Policy type must be Auto, Home, Life, Health, or Commercial','ANALYTICS','POLICIES','POLICY_TYPE','Validity','SELECT COUNT(*) FROM ANALYTICS.POLICIES WHERE POLICY_TYPE NOT IN (''Auto'',''Home'',''Life'',''Health'',''Commercial'')','100.00','Critical',TRUE),
('DQR-023','policies_tier_valid','Plan tier must be Basic, Standard, Premium, or Platinum','ANALYTICS','POLICIES','PLAN_TIER','Validity','SELECT COUNT(*) FROM ANALYTICS.POLICIES WHERE PLAN_TIER NOT IN (''Basic'',''Standard'',''Premium'',''Platinum'')','100.00','High',TRUE),
('DQR-024','policies_underwriting_range','Underwriting score must be between 0 and 100','ANALYTICS','POLICIES','UNDERWRITING_SCORE','Validity','SELECT COUNT(*) FROM ANALYTICS.POLICIES WHERE UNDERWRITING_SCORE NOT BETWEEN 0 AND 100','99.00','Medium',TRUE),
('DQR-025','policies_freshness','Policies table should have records within last 7 days','ANALYTICS','POLICIES',NULL,'Timeliness','SELECT CASE WHEN MAX(CREATED_AT) < DATEADD(day, -7, CURRENT_TIMESTAMP()) THEN 1 ELSE 0 END FROM ANALYTICS.POLICIES','100.00','High',TRUE),

-- CLAIMS table rules (10 rules)
('DQR-026','claims_unique_id','Claim ID must be unique','ANALYTICS','CLAIMS','CLAIM_ID','Uniqueness','SELECT COUNT(*) - COUNT(DISTINCT CLAIM_ID) FROM ANALYTICS.CLAIMS','100.00','Critical',TRUE),
('DQR-027','claims_valid_policy','Policy ID must exist in POLICIES table','ANALYTICS','CLAIMS','POLICY_ID','Consistency','SELECT COUNT(*) FROM ANALYTICS.CLAIMS cl WHERE NOT EXISTS (SELECT 1 FROM ANALYTICS.POLICIES p WHERE p.POLICY_ID = cl.POLICY_ID)','100.00','Critical',TRUE),
('DQR-028','claims_amount_positive','Claim amount must be positive','ANALYTICS','CLAIMS','CLAIM_AMOUNT','Validity','SELECT COUNT(*) FROM ANALYTICS.CLAIMS WHERE CLAIM_AMOUNT <= 0','100.00','Critical',TRUE),
('DQR-029','claims_approved_le_claimed','Approved amount should not exceed claim amount','ANALYTICS','CLAIMS','APPROVED_AMOUNT','Validity','SELECT COUNT(*) FROM ANALYTICS.CLAIMS WHERE APPROVED_AMOUNT > CLAIM_AMOUNT','99.00','High',TRUE),
('DQR-030','claims_fraud_score_range','Fraud score must be between 0 and 100','ANALYTICS','CLAIMS','FRAUD_SCORE','Validity','SELECT COUNT(*) FROM ANALYTICS.CLAIMS WHERE FRAUD_SCORE NOT BETWEEN 0 AND 100','100.00','High',TRUE),
('DQR-031','claims_resolution_days_positive','Resolution days must be non-negative','ANALYTICS','CLAIMS','RESOLUTION_DAYS','Validity','SELECT COUNT(*) FROM ANALYTICS.CLAIMS WHERE RESOLUTION_DAYS < 0','100.00','Medium',TRUE),
('DQR-032','claims_friction_range','Friction score must be between 0 and 10','ANALYTICS','CLAIMS','FRICTION_SCORE','Validity','SELECT COUNT(*) FROM ANALYTICS.CLAIMS WHERE FRICTION_SCORE NOT BETWEEN 0 AND 10','99.50','Medium',TRUE),
('DQR-033','claims_status_valid','Claim status must be a valid value','ANALYTICS','CLAIMS','STATUS','Validity','SELECT COUNT(*) FROM ANALYTICS.CLAIMS WHERE STATUS NOT IN (''Open'',''Under Review'',''Approved'',''Denied'',''Closed'')','100.00','Critical',TRUE),
('DQR-034','claims_closed_date_logic','Closed date should only exist for closed/approved/denied claims','ANALYTICS','CLAIMS','CLOSED_DATE','Consistency','SELECT COUNT(*) FROM ANALYTICS.CLAIMS WHERE CLOSED_DATE IS NOT NULL AND STATUS IN (''Open'',''Under Review'')','98.00','Medium',TRUE),
('DQR-035','claims_not_null_amount','Claim amount should never be null','ANALYTICS','CLAIMS','CLAIM_AMOUNT','Completeness','SELECT COUNT(*) FROM ANALYTICS.CLAIMS WHERE CLAIM_AMOUNT IS NULL','100.00','Critical',TRUE),

-- BILLING table rules (8 rules)
('DQR-036','billing_unique_invoice','Invoice ID must be unique','ANALYTICS','BILLING','INVOICE_ID','Uniqueness','SELECT COUNT(*) - COUNT(DISTINCT INVOICE_ID) FROM ANALYTICS.BILLING','100.00','Critical',TRUE),
('DQR-037','billing_due_after_invoice','Due date must be after invoice date','ANALYTICS','BILLING','DUE_DATE','Validity','SELECT COUNT(*) FROM ANALYTICS.BILLING WHERE DUE_DATE < INVOICE_DATE','100.00','High',TRUE),
('DQR-038','billing_amount_positive','Amount due must be positive','ANALYTICS','BILLING','AMOUNT_DUE','Validity','SELECT COUNT(*) FROM ANALYTICS.BILLING WHERE AMOUNT_DUE <= 0','100.00','Critical',TRUE),
('DQR-039','billing_paid_not_exceed_due','Amount paid should not exceed amount due','ANALYTICS','BILLING','AMOUNT_PAID','Validity','SELECT COUNT(*) FROM ANALYTICS.BILLING WHERE AMOUNT_PAID > AMOUNT_DUE * 1.1','99.00','Medium',TRUE),
('DQR-040','billing_balance_consistency','Outstanding balance should equal due minus paid','ANALYTICS','BILLING','OUTSTANDING_BALANCE','Consistency','SELECT COUNT(*) FROM ANALYTICS.BILLING WHERE ABS(OUTSTANDING_BALANCE - (AMOUNT_DUE - AMOUNT_PAID)) > 0.01','98.00','High',TRUE),
('DQR-041','billing_status_valid','Payment status must be Paid, Partial, Overdue, or Pending','ANALYTICS','BILLING','PAYMENT_STATUS','Validity','SELECT COUNT(*) FROM ANALYTICS.BILLING WHERE PAYMENT_STATUS NOT IN (''Paid'',''Partial'',''Overdue'',''Pending'')','100.00','Critical',TRUE),
('DQR-042','billing_payment_date_logic','Payment date should exist for Paid invoices','ANALYTICS','BILLING','PAYMENT_DATE','Consistency','SELECT COUNT(*) FROM ANALYTICS.BILLING WHERE PAYMENT_STATUS = ''Paid'' AND PAYMENT_DATE IS NULL','95.00','Medium',TRUE),
('DQR-043','billing_late_fee_logic','Late fee should only apply to overdue/partial payments','ANALYTICS','BILLING','LATE_FEE','Consistency','SELECT COUNT(*) FROM ANALYTICS.BILLING WHERE LATE_FEE > 0 AND PAYMENT_STATUS = ''Paid''','98.00','Low',TRUE),

-- AT_RISK_POLICIES table rules (7 rules)
('DQR-044','atrisk_unique_id','Risk ID must be unique','ANALYTICS','AT_RISK_POLICIES','RISK_ID','Uniqueness','SELECT COUNT(*) - COUNT(DISTINCT RISK_ID) FROM ANALYTICS.AT_RISK_POLICIES','100.00','Critical',TRUE),
('DQR-045','atrisk_churn_range','Churn probability must be between 0 and 1','ANALYTICS','AT_RISK_POLICIES','CHURN_PROBABILITY','Validity','SELECT COUNT(*) FROM ANALYTICS.AT_RISK_POLICIES WHERE CHURN_PROBABILITY NOT BETWEEN 0 AND 1','100.00','Critical',TRUE),
('DQR-046','atrisk_revenue_positive','Revenue at risk must be positive','ANALYTICS','AT_RISK_POLICIES','REVENUE_AT_RISK','Validity','SELECT COUNT(*) FROM ANALYTICS.AT_RISK_POLICIES WHERE REVENUE_AT_RISK <= 0','100.00','High',TRUE),
('DQR-047','atrisk_nps_range','NPS score must be between -100 and 100','ANALYTICS','AT_RISK_POLICIES','NPS_SCORE','Validity','SELECT COUNT(*) FROM ANALYTICS.AT_RISK_POLICIES WHERE NPS_SCORE NOT BETWEEN -100 AND 100','100.00','Medium',TRUE),
('DQR-048','atrisk_category_valid','Risk category must be valid','ANALYTICS','AT_RISK_POLICIES','RISK_CATEGORY','Validity','SELECT COUNT(*) FROM ANALYTICS.AT_RISK_POLICIES WHERE RISK_CATEGORY NOT IN (''Churn'',''Payment Default'',''Underinsured'')','100.00','High',TRUE),
('DQR-049','atrisk_valid_policy','Policy ID must exist in POLICIES table','ANALYTICS','AT_RISK_POLICIES','POLICY_ID','Consistency','SELECT COUNT(*) FROM ANALYTICS.AT_RISK_POLICIES ar WHERE NOT EXISTS (SELECT 1 FROM ANALYTICS.POLICIES p WHERE p.POLICY_ID = ar.POLICY_ID)','100.00','Critical',TRUE),
('DQR-050','atrisk_snapshot_not_future','Snapshot date should not be in the future','ANALYTICS','AT_RISK_POLICIES','SNAPSHOT_DATE','Timeliness','SELECT COUNT(*) FROM ANALYTICS.AT_RISK_POLICIES WHERE SNAPSHOT_DATE > CURRENT_DATE()','100.00','High',TRUE);

-- ============================================================
-- DQ_RESULTS - 5,000 rows
-- Daily rule execution results over ~90 days
-- Some rules deliberately failing to create interesting patterns
-- ============================================================

INSERT INTO DQ_RESULTS
WITH
raw_data AS (
    SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn
    FROM TABLE(GENERATOR(ROWCOUNT => 5000))
),
rule_data AS (
    SELECT RULE_ID, TARGET_TABLE, THRESHOLD, SEVERITY,
           ROW_NUMBER() OVER (ORDER BY RULE_ID) AS rule_rn
    FROM DQ_RULES
)
SELECT
    'DQR-RES-' || LPAD(r.rn::VARCHAR, 5, '0') AS RESULT_ID,
    rd.RULE_ID,
    DATEADD('day', -MOD(r.rn - 1, 100), CURRENT_TIMESTAMP())::TIMESTAMP_NTZ AS RUN_DATE,
    rd.TARGET_TABLE,
    CASE rd.TARGET_TABLE
        WHEN 'CUSTOMERS' THEN 5000
        WHEN 'AGENTS' THEN 150
        WHEN 'POLICIES' THEN 8000
        WHEN 'CLAIMS' THEN 3500
        WHEN 'BILLING' THEN 20000
        ELSE 1200
    END AS TOTAL_RECORDS,
    -- Most rules pass well, some have degrading quality
    CASE
        WHEN rd.RULE_ID IN ('DQR-001','DQR-002') THEN
            CASE rd.TARGET_TABLE
                WHEN 'CUSTOMERS' THEN 5000 - UNIFORM(50, 300, RANDOM(r.rn * 7))
                ELSE 5000 - UNIFORM(10, 50, RANDOM(r.rn * 11))
            END
        WHEN rd.RULE_ID IN ('DQR-034','DQR-040','DQR-042') THEN
            CASE rd.TARGET_TABLE
                WHEN 'CLAIMS' THEN 3500 - UNIFORM(20, 150, RANDOM(r.rn * 13))
                WHEN 'BILLING' THEN 20000 - UNIFORM(100, 800, RANDOM(r.rn * 17))
                ELSE 1200 - UNIFORM(5, 30, RANDOM(r.rn * 19))
            END
        ELSE
            CASE rd.TARGET_TABLE
                WHEN 'CUSTOMERS' THEN 5000 - UNIFORM(0, 10, RANDOM(r.rn * 23))
                WHEN 'AGENTS' THEN 150
                WHEN 'POLICIES' THEN 8000 - UNIFORM(0, 15, RANDOM(r.rn * 29))
                WHEN 'CLAIMS' THEN 3500 - UNIFORM(0, 8, RANDOM(r.rn * 31))
                WHEN 'BILLING' THEN 20000 - UNIFORM(0, 20, RANDOM(r.rn * 37))
                ELSE 1200 - UNIFORM(0, 5, RANDOM(r.rn * 41))
            END
    END AS PASSED_RECORDS,
    -- FAILED = TOTAL - PASSED (calculated in outer)
    CASE rd.TARGET_TABLE
        WHEN 'CUSTOMERS' THEN 5000
        WHEN 'AGENTS' THEN 150
        WHEN 'POLICIES' THEN 8000
        WHEN 'CLAIMS' THEN 3500
        WHEN 'BILLING' THEN 20000
        ELSE 1200
    END -
    CASE
        WHEN rd.RULE_ID IN ('DQR-001','DQR-002') THEN
            CASE rd.TARGET_TABLE
                WHEN 'CUSTOMERS' THEN 5000 - UNIFORM(50, 300, RANDOM(r.rn * 7))
                ELSE 5000 - UNIFORM(10, 50, RANDOM(r.rn * 11))
            END
        WHEN rd.RULE_ID IN ('DQR-034','DQR-040','DQR-042') THEN
            CASE rd.TARGET_TABLE
                WHEN 'CLAIMS' THEN 3500 - UNIFORM(20, 150, RANDOM(r.rn * 13))
                WHEN 'BILLING' THEN 20000 - UNIFORM(100, 800, RANDOM(r.rn * 17))
                ELSE 1200 - UNIFORM(5, 30, RANDOM(r.rn * 19))
            END
        ELSE
            CASE rd.TARGET_TABLE
                WHEN 'CUSTOMERS' THEN 5000 - UNIFORM(0, 10, RANDOM(r.rn * 23))
                WHEN 'AGENTS' THEN 150
                WHEN 'POLICIES' THEN 8000 - UNIFORM(0, 15, RANDOM(r.rn * 29))
                WHEN 'CLAIMS' THEN 3500 - UNIFORM(0, 8, RANDOM(r.rn * 31))
                WHEN 'BILLING' THEN 20000 - UNIFORM(0, 20, RANDOM(r.rn * 37))
                ELSE 1200 - UNIFORM(0, 5, RANDOM(r.rn * 41))
            END
    END AS FAILED_RECORDS,
    -- Pass rate
    ROUND(
        CASE
            WHEN rd.RULE_ID IN ('DQR-001','DQR-002') THEN UNIFORM(92.00, 97.00, RANDOM(r.rn * 43))
            WHEN rd.RULE_ID IN ('DQR-034','DQR-040','DQR-042') THEN UNIFORM(88.00, 96.00, RANDOM(r.rn * 47))
            ELSE UNIFORM(97.00, 100.00, RANDOM(r.rn * 53))
        END::DECIMAL(5,2), 2
    ) AS PASS_RATE,
    CASE
        WHEN rd.RULE_ID IN ('DQR-001','DQR-002') AND UNIFORM(1, 100, RANDOM(r.rn * 59)) <= 40 THEN 'Fail'
        WHEN rd.RULE_ID IN ('DQR-034','DQR-040','DQR-042') AND UNIFORM(1, 100, RANDOM(r.rn * 61)) <= 30 THEN 'Fail'
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 67)) <= 5 THEN 'Warning'
        ELSE 'Pass'
    END AS STATUS,
    CASE
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 71)) <= 20 THEN '{"sample_ids":["CUST-00142","CUST-03891","CUST-02445"],"issue":"null_value"}'
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 73)) <= 10 THEN '{"sample_ids":["POL-12345","POL-14567"],"issue":"constraint_violation"}'
        ELSE NULL
    END AS ERROR_SAMPLE,
    UNIFORM(50, 5000, RANDOM(r.rn * 79)) AS EXECUTION_TIME_MS,
    CASE UNIFORM(1, 10, RANDOM(r.rn * 83))
        WHEN 1 THEN 'Manual'
        ELSE 'Scheduled'
    END AS RUN_BY
FROM raw_data r
JOIN rule_data rd ON rd.rule_rn = MOD(r.rn - 1, 50) + 1;

-- ============================================================
-- DQ_SCORES - 1,000 rows
-- Daily table-level quality scores over ~90 days
-- Covers all 6 ANALYTICS tables + 2 DOCUMENTS tables
-- ============================================================

INSERT INTO DQ_SCORES
WITH
tables_to_score AS (
    SELECT * FROM (VALUES
        ('ANALYTICS','CUSTOMERS'),('ANALYTICS','AGENTS'),('ANALYTICS','POLICIES'),
        ('ANALYTICS','CLAIMS'),('ANALYTICS','BILLING'),('ANALYTICS','AT_RISK_POLICIES'),
        ('DOCUMENTS','POLICY_DOCUMENTS'),('DOCUMENTS','DOCUMENT_CHUNKS')
    ) AS t(SCHEMA_NM, TABLE_NM)
),
date_range AS (
    SELECT DATEADD('day', -SEQ4(), CURRENT_DATE()) AS score_dt
    FROM TABLE(GENERATOR(ROWCOUNT => 125))
),
raw_data AS (
    SELECT
        t.SCHEMA_NM, t.TABLE_NM, d.score_dt,
        ROW_NUMBER() OVER (ORDER BY t.SCHEMA_NM, t.TABLE_NM, d.score_dt DESC) AS rn
    FROM tables_to_score t
    CROSS JOIN date_range d
)
SELECT
    'DQS-' || LPAD(rn::VARCHAR, 5, '0') AS SCORE_ID,
    SCHEMA_NM AS SCHEMA_NAME,
    TABLE_NM AS TABLE_NAME,
    score_dt AS SCORE_DATE,
    -- Completeness: generally high, CUSTOMERS lower due to nulls
    ROUND(CASE TABLE_NM
        WHEN 'CUSTOMERS' THEN UNIFORM(91.00, 97.50, RANDOM(rn * 7))
        WHEN 'CLAIMS' THEN UNIFORM(93.00, 99.00, RANDOM(rn * 11))
        ELSE UNIFORM(96.00, 100.00, RANDOM(rn * 13))
    END::DECIMAL(5,2), 2) AS COMPLETENESS_SCORE,
    -- Uniqueness: very high for most
    ROUND(UNIFORM(97.00, 100.00, RANDOM(rn * 17))::DECIMAL(5,2), 2) AS UNIQUENESS_SCORE,
    -- Validity: high
    ROUND(CASE TABLE_NM
        WHEN 'BILLING' THEN UNIFORM(92.00, 99.00, RANDOM(rn * 19))
        ELSE UNIFORM(95.00, 100.00, RANDOM(rn * 23))
    END::DECIMAL(5,2), 2) AS VALIDITY_SCORE,
    -- Timeliness: degrades for some tables
    ROUND(CASE
        WHEN TABLE_NM = 'AT_RISK_POLICIES' AND score_dt < DATEADD('day', -60, CURRENT_DATE())
            THEN UNIFORM(70.00, 85.00, RANDOM(rn * 29))
        WHEN TABLE_NM IN ('CLAIMS','BILLING') THEN UNIFORM(85.00, 98.00, RANDOM(rn * 31))
        ELSE UNIFORM(90.00, 100.00, RANDOM(rn * 37))
    END::DECIMAL(5,2), 2) AS TIMELINESS_SCORE,
    -- Consistency
    ROUND(CASE TABLE_NM
        WHEN 'BILLING' THEN UNIFORM(88.00, 97.00, RANDOM(rn * 41))
        ELSE UNIFORM(93.00, 100.00, RANDOM(rn * 43))
    END::DECIMAL(5,2), 2) AS CONSISTENCY_SCORE,
    -- Overall = weighted average (simulated)
    ROUND(UNIFORM(89.00, 99.00, RANDOM(rn * 47))::DECIMAL(5,2), 2) AS OVERALL_SCORE,
    CASE
        WHEN UNIFORM(1, 100, RANDOM(rn * 53)) <= 50 THEN 'Stable'
        WHEN UNIFORM(1, 100, RANDOM(rn * 53)) <= 80 THEN 'Improving'
        ELSE 'Declining'
    END AS TREND,
    CASE TABLE_NM
        WHEN 'CUSTOMERS' THEN 5000
        WHEN 'AGENTS' THEN 150
        WHEN 'POLICIES' THEN 8000
        WHEN 'CLAIMS' THEN 3500
        WHEN 'BILLING' THEN 20000
        WHEN 'AT_RISK_POLICIES' THEN 1200
        WHEN 'POLICY_DOCUMENTS' THEN 2000
        ELSE 12000
    END AS RECORDS_ASSESSED,
    CASE TABLE_NM
        WHEN 'CUSTOMERS' THEN 10
        WHEN 'AGENTS' THEN 5
        WHEN 'POLICIES' THEN 10
        WHEN 'CLAIMS' THEN 10
        WHEN 'BILLING' THEN 8
        WHEN 'AT_RISK_POLICIES' THEN 7
        ELSE 3
    END AS RULES_EVALUATED
FROM raw_data
WHERE rn <= 1000;

-- ============================================================
-- DQ_COLUMN_HEALTH - 3,000 rows
-- Weekly column-level health metrics
-- Key columns across ANALYTICS tables, ~12 weeks of history
-- ============================================================

INSERT INTO DQ_COLUMN_HEALTH
WITH
columns_to_monitor AS (
    SELECT * FROM (VALUES
        ('ANALYTICS','CUSTOMERS','CUSTOMER_ID'),('ANALYTICS','CUSTOMERS','EMAIL'),
        ('ANALYTICS','CUSTOMERS','PHONE'),('ANALYTICS','CUSTOMERS','CREDIT_SCORE'),
        ('ANALYTICS','CUSTOMERS','RISK_TIER'),('ANALYTICS','CUSTOMERS','STATE'),
        ('ANALYTICS','AGENTS','AGENT_ID'),('ANALYTICS','AGENTS','PERFORMANCE_RATING'),
        ('ANALYTICS','AGENTS','REGION'),('ANALYTICS','AGENTS','STATUS'),
        ('ANALYTICS','POLICIES','POLICY_ID'),('ANALYTICS','POLICIES','PREMIUM_AMOUNT'),
        ('ANALYTICS','POLICIES','COVERAGE_AMOUNT'),('ANALYTICS','POLICIES','STATUS'),
        ('ANALYTICS','POLICIES','UNDERWRITING_SCORE'),('ANALYTICS','POLICIES','POLICY_TYPE'),
        ('ANALYTICS','CLAIMS','CLAIM_ID'),('ANALYTICS','CLAIMS','CLAIM_AMOUNT'),
        ('ANALYTICS','CLAIMS','APPROVED_AMOUNT'),('ANALYTICS','CLAIMS','FRAUD_SCORE'),
        ('ANALYTICS','CLAIMS','RESOLUTION_DAYS'),('ANALYTICS','CLAIMS','STATUS'),
        ('ANALYTICS','BILLING','INVOICE_ID'),('ANALYTICS','BILLING','AMOUNT_DUE'),
        ('ANALYTICS','BILLING','OUTSTANDING_BALANCE'),('ANALYTICS','BILLING','PAYMENT_STATUS'),
        ('ANALYTICS','AT_RISK_POLICIES','CHURN_PROBABILITY'),('ANALYTICS','AT_RISK_POLICIES','REVENUE_AT_RISK'),
        ('ANALYTICS','AT_RISK_POLICIES','NPS_SCORE'),('ANALYTICS','AT_RISK_POLICIES','MISSED_PAYMENTS_COUNT')
    ) AS t(SCHEMA_NM, TABLE_NM, COL_NM)
),
weeks AS (
    SELECT DATEADD('week', -SEQ4(), CURRENT_DATE()) AS check_dt
    FROM TABLE(GENERATOR(ROWCOUNT => 100))
    WHERE SEQ4() < 100
),
raw_data AS (
    SELECT
        c.SCHEMA_NM, c.TABLE_NM, c.COL_NM, w.check_dt,
        ROW_NUMBER() OVER (ORDER BY c.SCHEMA_NM, c.TABLE_NM, c.COL_NM, w.check_dt DESC) AS rn
    FROM columns_to_monitor c
    CROSS JOIN weeks w
)
SELECT
    'DQH-' || LPAD(rn::VARCHAR, 5, '0') AS HEALTH_ID,
    SCHEMA_NM AS SCHEMA_NAME,
    TABLE_NM AS TABLE_NAME,
    COL_NM AS COLUMN_NAME,
    check_dt AS CHECK_DATE,
    -- Null rate: EMAIL and PHONE have higher nulls, most others near 0
    ROUND(CASE COL_NM
        WHEN 'EMAIL' THEN UNIFORM(3.00, 7.00, RANDOM(rn * 7))
        WHEN 'PHONE' THEN UNIFORM(2.00, 5.50, RANDOM(rn * 11))
        WHEN 'APPROVED_AMOUNT' THEN UNIFORM(15.00, 25.00, RANDOM(rn * 13))
        WHEN 'NPS_SCORE' THEN UNIFORM(1.00, 4.00, RANDOM(rn * 17))
        WHEN 'UNDERWRITING_SCORE' THEN UNIFORM(0.50, 2.00, RANDOM(rn * 19))
        ELSE UNIFORM(0.00, 1.00, RANDOM(rn * 23))
    END::DECIMAL(5,2), 2) AS NULL_RATE,
    -- Duplicate rate: IDs should be 0, others have some
    ROUND(CASE
        WHEN COL_NM LIKE '%_ID' THEN 0.00
        WHEN COL_NM IN ('STATUS','RISK_TIER','REGION','POLICY_TYPE','PAYMENT_STATUS') THEN UNIFORM(40.00, 80.00, RANDOM(rn * 29))
        ELSE UNIFORM(0.00, 5.00, RANDOM(rn * 31))
    END::DECIMAL(5,2), 2) AS DUPLICATE_RATE,
    -- Outlier rate
    ROUND(CASE COL_NM
        WHEN 'CLAIM_AMOUNT' THEN UNIFORM(2.00, 8.00, RANDOM(rn * 37))
        WHEN 'PREMIUM_AMOUNT' THEN UNIFORM(1.00, 5.00, RANDOM(rn * 41))
        WHEN 'RESOLUTION_DAYS' THEN UNIFORM(3.00, 12.00, RANDOM(rn * 43))
        WHEN 'CREDIT_SCORE' THEN UNIFORM(0.50, 3.00, RANDOM(rn * 47))
        WHEN 'OUTSTANDING_BALANCE' THEN UNIFORM(1.00, 6.00, RANDOM(rn * 53))
        ELSE UNIFORM(0.00, 2.50, RANDOM(rn * 59))
    END::DECIMAL(5,2), 2) AS OUTLIER_RATE,
    -- Distinct count
    CASE COL_NM
        WHEN 'CUSTOMER_ID' THEN 5000
        WHEN 'POLICY_ID' THEN 8000
        WHEN 'CLAIM_ID' THEN 3500
        WHEN 'AGENT_ID' THEN 150
        WHEN 'INVOICE_ID' THEN 20000
        WHEN 'STATUS' THEN UNIFORM(3, 6, RANDOM(rn * 61))
        WHEN 'RISK_TIER' THEN 4
        WHEN 'REGION' THEN 5
        WHEN 'POLICY_TYPE' THEN 5
        WHEN 'PAYMENT_STATUS' THEN 4
        ELSE UNIFORM(50, 5000, RANDOM(rn * 67))
    END AS DISTINCT_COUNT,
    -- Health score: composite
    ROUND(CASE
        WHEN COL_NM IN ('EMAIL','PHONE') THEN UNIFORM(72.00, 92.00, RANDOM(rn * 71))
        WHEN COL_NM = 'RESOLUTION_DAYS' THEN UNIFORM(75.00, 90.00, RANDOM(rn * 73))
        WHEN COL_NM LIKE '%_ID' THEN UNIFORM(95.00, 100.00, RANDOM(rn * 79))
        ELSE UNIFORM(82.00, 99.00, RANDOM(rn * 83))
    END::DECIMAL(5,2), 2) AS HEALTH_SCORE,
    -- Data type consistency
    ROUND(UNIFORM(97.00, 100.00, RANDOM(rn * 89))::DECIMAL(5,2), 2) AS DATA_TYPE_CONSISTENCY,
    CASE
        WHEN COL_NM IN ('EMAIL','PHONE') AND UNIFORM(1, 100, RANDOM(rn * 97)) <= 30 THEN 'Warning'
        WHEN COL_NM = 'RESOLUTION_DAYS' AND UNIFORM(1, 100, RANDOM(rn * 101)) <= 20 THEN 'Warning'
        WHEN UNIFORM(1, 100, RANDOM(rn * 103)) <= 3 THEN 'Critical'
        ELSE 'Healthy'
    END AS STATUS
FROM raw_data
WHERE rn <= 3000;

-- Verify counts
SELECT 'DQ_RULES' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM DQ_RULES
UNION ALL SELECT 'DQ_RESULTS', COUNT(*) FROM DQ_RESULTS
UNION ALL SELECT 'DQ_SCORES', COUNT(*) FROM DQ_SCORES
UNION ALL SELECT 'DQ_COLUMN_HEALTH', COUNT(*) FROM DQ_COLUMN_HEALTH;
