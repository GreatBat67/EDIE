-- ============================================================
-- INSURANCE AI HUB (E.D.I.E.) - Generate Fact Tables
-- Phase 3b: POLICIES (8K), CLAIMS (3.5K), BILLING (20K), AT_RISK_POLICIES (1.2K)
-- ============================================================

USE DATABASE INSURANCE_AI_HUB;
USE WAREHOUSE INSURANCE_AI_HUB_WH;
USE SCHEMA ANALYTICS;

-- ============================================================
-- POLICIES - 8,000 rows
-- FK to CUSTOMERS and AGENTS, date range 2022-01-01 to 2025-06-30
-- Distribution: Auto(35%), Home(25%), Life(15%), Health(15%), Commercial(10%)
-- ============================================================

INSERT INTO POLICIES
WITH
policy_types AS (
    SELECT ARRAY_CONSTRUCT('Auto','Auto','Auto','Auto','Auto','Auto','Auto',
                           'Home','Home','Home','Home','Home',
                           'Life','Life','Life',
                           'Health','Health','Health',
                           'Commercial','Commercial') AS arr
),
plan_tiers AS (
    SELECT ARRAY_CONSTRUCT('Basic','Basic','Standard','Standard','Standard','Premium','Premium','Platinum') AS arr
),
statuses AS (
    SELECT ARRAY_CONSTRUCT('Active','Active','Active','Active','Active','Active','Expired','Expired','Cancelled','Pending') AS arr
),
renewal_statuses AS (
    SELECT ARRAY_CONSTRUCT('Auto-Renew','Auto-Renew','Auto-Renew','Manual','Manual','Pending','Declined') AS arr
),
customer_ids AS (
    SELECT CUSTOMER_ID, ROW_NUMBER() OVER (ORDER BY CUSTOMER_ID) AS cust_rn
    FROM CUSTOMERS
),
agent_ids AS (
    SELECT AGENT_ID, ROW_NUMBER() OVER (ORDER BY AGENT_ID) AS agt_rn
    FROM AGENTS
    WHERE STATUS = 'Active'
),
raw_data AS (
    SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn
    FROM TABLE(GENERATOR(ROWCOUNT => 8000))
)
SELECT
    'POL-' || LPAD((10000 + r.rn)::VARCHAR, 5, '0') AS POLICY_ID,
    c.CUSTOMER_ID,
    a.AGENT_ID,
    policy_types.arr[UNIFORM(0, 19, RANDOM(r.rn * 7))]::VARCHAR AS POLICY_TYPE,
    plan_tiers.arr[UNIFORM(0, 7, RANDOM(r.rn * 11))]::VARCHAR AS PLAN_TIER,
    DATEADD('day', UNIFORM(0, 1275, RANDOM(r.rn * 13)), '2022-01-01'::DATE) AS START_DATE,
    DATEADD('day', UNIFORM(0, 1275, RANDOM(r.rn * 13)) + 365, '2022-01-01'::DATE) AS END_DATE,
    CASE policy_types.arr[UNIFORM(0, 19, RANDOM(r.rn * 7))]::VARCHAR
        WHEN 'Auto' THEN ROUND(UNIFORM(80, 450, RANDOM(r.rn * 17))::DECIMAL(12,2), 2)
        WHEN 'Home' THEN ROUND(UNIFORM(100, 600, RANDOM(r.rn * 19))::DECIMAL(12,2), 2)
        WHEN 'Life' THEN ROUND(UNIFORM(50, 300, RANDOM(r.rn * 23))::DECIMAL(12,2), 2)
        WHEN 'Health' THEN ROUND(UNIFORM(200, 800, RANDOM(r.rn * 29))::DECIMAL(12,2), 2)
        ELSE ROUND(UNIFORM(500, 5000, RANDOM(r.rn * 31))::DECIMAL(12,2), 2)
    END AS PREMIUM_AMOUNT,
    CASE policy_types.arr[UNIFORM(0, 19, RANDOM(r.rn * 7))]::VARCHAR
        WHEN 'Auto' THEN ROUND(UNIFORM(15000, 100000, RANDOM(r.rn * 37))::DECIMAL(14,2), 2)
        WHEN 'Home' THEN ROUND(UNIFORM(150000, 750000, RANDOM(r.rn * 41))::DECIMAL(14,2), 2)
        WHEN 'Life' THEN ROUND(UNIFORM(100000, 2000000, RANDOM(r.rn * 43))::DECIMAL(14,2), 2)
        WHEN 'Health' THEN ROUND(UNIFORM(50000, 500000, RANDOM(r.rn * 47))::DECIMAL(14,2), 2)
        ELSE ROUND(UNIFORM(500000, 10000000, RANDOM(r.rn * 53))::DECIMAL(14,2), 2)
    END AS COVERAGE_AMOUNT,
    CASE plan_tiers.arr[UNIFORM(0, 7, RANDOM(r.rn * 11))]::VARCHAR
        WHEN 'Basic' THEN ROUND(UNIFORM(1000, 5000, RANDOM(r.rn * 59))::DECIMAL(10,2), 2)
        WHEN 'Standard' THEN ROUND(UNIFORM(500, 2500, RANDOM(r.rn * 61))::DECIMAL(10,2), 2)
        WHEN 'Premium' THEN ROUND(UNIFORM(250, 1000, RANDOM(r.rn * 67))::DECIMAL(10,2), 2)
        ELSE ROUND(UNIFORM(100, 500, RANDOM(r.rn * 71))::DECIMAL(10,2), 2)
    END AS DEDUCTIBLE,
    statuses.arr[UNIFORM(0, 9, RANDOM(r.rn * 73))]::VARCHAR AS STATUS,
    renewal_statuses.arr[UNIFORM(0, 6, RANDOM(r.rn * 79))]::VARCHAR AS RENEWAL_STATUS,
    ROUND(UNIFORM(20.00, 98.00, RANDOM(r.rn * 83))::DECIMAL(5,2), 2) AS UNDERWRITING_SCORE,
    DATEADD('second', UNIFORM(0, 86400, RANDOM(r.rn * 89)),
        DATEADD('day', UNIFORM(0, 1275, RANDOM(r.rn * 13)), '2022-01-01'::DATE)
    )::TIMESTAMP_NTZ AS CREATED_AT
FROM raw_data r
CROSS JOIN policy_types
CROSS JOIN plan_tiers
CROSS JOIN statuses
CROSS JOIN renewal_statuses
JOIN customer_ids c ON c.cust_rn = MOD(r.rn - 1, 5000) + 1
JOIN agent_ids a ON a.agt_rn = MOD(r.rn - 1, (SELECT COUNT(*) FROM AGENTS WHERE STATUS = 'Active')) + 1;

-- ============================================================
-- CLAIMS - 3,500 rows
-- FK to POLICIES and CUSTOMERS
-- Seasonal patterns: spikes in Aug-Oct (hurricane) and Dec-Feb (winter)
-- Fraud: 2-3% high fraud scores (>80)
-- ============================================================

INSERT INTO CLAIMS
WITH
claim_types_by_policy AS (
    SELECT OBJECT_CONSTRUCT(
        'Auto', ARRAY_CONSTRUCT('Collision','Collision','Theft','Vandalism','Glass Damage','Liability'),
        'Home', ARRAY_CONSTRUCT('Water Damage','Fire','Storm Damage','Theft','Mold','Structural'),
        'Life', ARRAY_CONSTRUCT('Death Benefit','Terminal Illness','Accidental Death','Disability','Critical Illness','Dismemberment'),
        'Health', ARRAY_CONSTRUCT('Emergency Room','Surgery','Prescription','Specialist Visit','Lab Work','Mental Health'),
        'Commercial', ARRAY_CONSTRUCT('Property Damage','Liability','Workers Comp','Business Interruption','Equipment Failure','Cyber Breach')
    ) AS obj
),
claim_statuses AS (
    SELECT ARRAY_CONSTRUCT('Open','Open','Under Review','Under Review','Approved','Approved','Approved','Denied','Closed','Closed') AS arr
),
causes AS (
    SELECT ARRAY_CONSTRUCT(
        'Weather Event','Human Error','Equipment Failure','Natural Disaster','Negligence',
        'Arson','Vandalism','Wear and Tear','Manufacturing Defect','Unknown'
    ) AS arr
),
locations AS (
    SELECT ARRAY_CONSTRUCT(
        'Residence','Highway','Parking Lot','Intersection','Commercial Property',
        'Workplace','Public Area','Rural Road','Shopping Center','Industrial Zone'
    ) AS arr
),
policy_data AS (
    SELECT POLICY_ID, CUSTOMER_ID, POLICY_TYPE, PREMIUM_AMOUNT, START_DATE, END_DATE,
           ROW_NUMBER() OVER (ORDER BY POLICY_ID) AS pol_rn
    FROM POLICIES
    WHERE STATUS IN ('Active','Expired')
),
raw_data AS (
    SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn
    FROM TABLE(GENERATOR(ROWCOUNT => 3500))
)
SELECT
    'CLM-' || LPAD((50000 + r.rn)::VARCHAR, 5, '0') AS CLAIM_ID,
    p.POLICY_ID,
    p.CUSTOMER_ID,
    -- Seasonal bias: more claims in Aug-Oct and Dec-Feb
    CASE
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 7)) <= 35 THEN
            DATEADD('day', UNIFORM(0, 91, RANDOM(r.rn * 11)),
                DATE_FROM_PARTS(UNIFORM(2022, 2025, RANDOM(r.rn * 13)), 8, 1))
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 7)) <= 60 THEN
            DATEADD('day', UNIFORM(0, 89, RANDOM(r.rn * 17)),
                DATE_FROM_PARTS(UNIFORM(2022, 2024, RANDOM(r.rn * 19)), 12, 1))
        ELSE
            DATEADD('day', UNIFORM(0, 1275, RANDOM(r.rn * 23)), '2022-01-01'::DATE)
    END AS CLAIM_DATE,
    claim_types_by_policy.obj[p.POLICY_TYPE][UNIFORM(0, 5, RANDOM(r.rn * 29))]::VARCHAR AS CLAIM_TYPE,
    CASE p.POLICY_TYPE
        WHEN 'Auto' THEN ROUND(UNIFORM(500, 45000, RANDOM(r.rn * 31))::DECIMAL(12,2), 2)
        WHEN 'Home' THEN ROUND(UNIFORM(1000, 150000, RANDOM(r.rn * 37))::DECIMAL(12,2), 2)
        WHEN 'Life' THEN ROUND(UNIFORM(10000, 500000, RANDOM(r.rn * 41))::DECIMAL(12,2), 2)
        WHEN 'Health' THEN ROUND(UNIFORM(200, 75000, RANDOM(r.rn * 43))::DECIMAL(12,2), 2)
        ELSE ROUND(UNIFORM(5000, 500000, RANDOM(r.rn * 47))::DECIMAL(12,2), 2)
    END AS CLAIM_AMOUNT,
    CASE claim_statuses.arr[UNIFORM(0, 9, RANDOM(r.rn * 53))]::VARCHAR
        WHEN 'Approved' THEN ROUND(UNIFORM(500, 45000, RANDOM(r.rn * 59))::DECIMAL(12,2) * UNIFORM(0.40, 0.95, RANDOM(r.rn * 61))::DECIMAL(5,2), 2)
        WHEN 'Closed' THEN ROUND(UNIFORM(500, 45000, RANDOM(r.rn * 59))::DECIMAL(12,2) * UNIFORM(0.50, 1.00, RANDOM(r.rn * 67))::DECIMAL(5,2), 2)
        ELSE NULL
    END AS APPROVED_AMOUNT,
    claim_statuses.arr[UNIFORM(0, 9, RANDOM(r.rn * 53))]::VARCHAR AS STATUS,
    -- Fraud score: 2-3% above 80, bulk between 5-40
    CASE
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 71)) <= 3 THEN ROUND(UNIFORM(80.00, 99.00, RANDOM(r.rn * 73))::DECIMAL(5,2), 2)
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 71)) <= 15 THEN ROUND(UNIFORM(40.00, 79.99, RANDOM(r.rn * 79))::DECIMAL(5,2), 2)
        ELSE ROUND(UNIFORM(2.00, 39.99, RANDOM(r.rn * 83))::DECIMAL(5,2), 2)
    END AS FRAUD_SCORE,
    'ADJ-' || LPAD(UNIFORM(1, 50, RANDOM(r.rn * 89))::VARCHAR, 3, '0') AS ADJUSTER_ID,
    -- Resolution days: skewed with long tail
    CASE
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 97)) <= 50 THEN UNIFORM(3, 30, RANDOM(r.rn * 101))
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 97)) <= 80 THEN UNIFORM(31, 90, RANDOM(r.rn * 103))
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 97)) <= 95 THEN UNIFORM(91, 180, RANDOM(r.rn * 107))
        ELSE UNIFORM(181, 365, RANDOM(r.rn * 109))
    END AS RESOLUTION_DAYS,
    ROUND(UNIFORM(1.0, 10.0, RANDOM(r.rn * 113))::DECIMAL(5,2), 2) AS FRICTION_SCORE,
    causes.arr[UNIFORM(0, 9, RANDOM(r.rn * 127))]::VARCHAR AS CAUSE_OF_LOSS,
    locations.arr[UNIFORM(0, 9, RANDOM(r.rn * 131))]::VARCHAR AS INCIDENT_LOCATION,
    CASE
        WHEN claim_statuses.arr[UNIFORM(0, 9, RANDOM(r.rn * 53))]::VARCHAR IN ('Approved','Closed','Denied')
        THEN DATEADD('day', UNIFORM(3, 180, RANDOM(r.rn * 137)),
            DATEADD('day', UNIFORM(0, 1275, RANDOM(r.rn * 23)), '2022-01-01'::DATE))
        ELSE NULL
    END AS CLOSED_DATE
FROM raw_data r
CROSS JOIN claim_types_by_policy
CROSS JOIN claim_statuses
CROSS JOIN causes
CROSS JOIN locations
JOIN policy_data p ON p.pol_rn = MOD(r.rn - 1, (SELECT COUNT(*) FROM POLICIES WHERE STATUS IN ('Active','Expired'))) + 1;

-- ============================================================
-- BILLING - 20,000 rows
-- Monthly invoices from policies, 8% delinquency rate
-- ============================================================

INSERT INTO BILLING
WITH
payment_methods AS (
    SELECT ARRAY_CONSTRUCT('Credit Card','Credit Card','Credit Card','ACH','ACH','ACH','Check','Wire') AS arr
),
policy_data AS (
    SELECT POLICY_ID, CUSTOMER_ID, PREMIUM_AMOUNT, START_DATE,
           ROW_NUMBER() OVER (ORDER BY POLICY_ID) AS pol_rn
    FROM POLICIES
),
raw_data AS (
    SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn
    FROM TABLE(GENERATOR(ROWCOUNT => 20000))
)
SELECT
    'INV-' || LPAD((80000 + r.rn)::VARCHAR, 6, '0') AS INVOICE_ID,
    p.POLICY_ID,
    p.CUSTOMER_ID,
    DATEADD('month', MOD(r.rn - 1, 30), p.START_DATE) AS INVOICE_DATE,
    DATEADD('day', 30, DATEADD('month', MOD(r.rn - 1, 30), p.START_DATE)) AS DUE_DATE,
    ROUND(p.PREMIUM_AMOUNT / 12, 2) AS AMOUNT_DUE,
    -- Payment patterns: 85% full, 7% partial, 8% zero (overdue)
    CASE
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 7)) <= 85 THEN ROUND(p.PREMIUM_AMOUNT / 12, 2)
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 7)) <= 92 THEN ROUND(p.PREMIUM_AMOUNT / 12 * UNIFORM(0.3, 0.8, RANDOM(r.rn * 11))::DECIMAL(5,2), 2)
        ELSE 0.00
    END AS AMOUNT_PAID,
    -- Outstanding = due - paid
    CASE
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 7)) <= 85 THEN 0.00
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 7)) <= 92 THEN
            ROUND(p.PREMIUM_AMOUNT / 12 - (p.PREMIUM_AMOUNT / 12 * UNIFORM(0.3, 0.8, RANDOM(r.rn * 11))::DECIMAL(5,2)), 2)
        ELSE ROUND(p.PREMIUM_AMOUNT / 12, 2)
    END AS OUTSTANDING_BALANCE,
    CASE
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 7)) > 92 THEN ROUND(UNIFORM(15, 75, RANDOM(r.rn * 13))::DECIMAL(8,2), 2)
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 7)) > 85 THEN ROUND(UNIFORM(5, 25, RANDOM(r.rn * 17))::DECIMAL(8,2), 2)
        ELSE 0.00
    END AS LATE_FEE,
    CASE
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 7)) <= 85 THEN 'Paid'
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 7)) <= 92 THEN 'Partial'
        ELSE 'Overdue'
    END AS PAYMENT_STATUS,
    CASE
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 7)) <= 92 THEN payment_methods.arr[UNIFORM(0, 7, RANDOM(r.rn * 19))]::VARCHAR
        ELSE NULL
    END AS PAYMENT_METHOD,
    CASE
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 7)) <= 85 THEN
            DATEADD('day', UNIFORM(-5, 25, RANDOM(r.rn * 23)),
                DATEADD('month', MOD(r.rn - 1, 30), p.START_DATE))
        WHEN UNIFORM(1, 100, RANDOM(r.rn * 7)) <= 92 THEN
            DATEADD('day', UNIFORM(30, 60, RANDOM(r.rn * 29)),
                DATEADD('month', MOD(r.rn - 1, 30), p.START_DATE))
        ELSE NULL
    END AS PAYMENT_DATE
FROM raw_data r
CROSS JOIN payment_methods
JOIN policy_data p ON p.pol_rn = MOD(r.rn - 1, (SELECT COUNT(*) FROM POLICIES)) + 1;

-- ============================================================
-- AT_RISK_POLICIES - 1,200 rows
-- Snapshot of policies with churn/risk indicators
-- Correlated with billing delinquency and claims frequency
-- ============================================================

INSERT INTO AT_RISK_POLICIES
WITH
risk_categories AS (
    SELECT ARRAY_CONSTRUCT('Churn','Churn','Churn','Payment Default','Payment Default','Underinsured') AS arr
),
retention_actions AS (
    SELECT ARRAY_CONSTRUCT('Discount Offer','Agent Call','Auto-Renew Lock','Premium Reduction','Coverage Review','None') AS arr
),
-- Select policies that have billing issues or high claim frequency
risky_policies AS (
    SELECT
        p.POLICY_ID,
        p.CUSTOMER_ID,
        p.PREMIUM_AMOUNT,
        p.END_DATE,
        COALESCE(b.missed, 0) AS missed_payments,
        COALESCE(c.claim_count, 0) AS claims_filed,
        ROW_NUMBER() OVER (ORDER BY COALESCE(b.missed, 0) DESC, COALESCE(c.claim_count, 0) DESC) AS risk_rn
    FROM POLICIES p
    LEFT JOIN (
        SELECT POLICY_ID, COUNT(*) AS missed
        FROM BILLING WHERE PAYMENT_STATUS IN ('Overdue','Partial')
        GROUP BY POLICY_ID
    ) b ON b.POLICY_ID = p.POLICY_ID
    LEFT JOIN (
        SELECT POLICY_ID, COUNT(*) AS claim_count
        FROM CLAIMS
        GROUP BY POLICY_ID
    ) c ON c.POLICY_ID = p.POLICY_ID
    WHERE p.STATUS = 'Active'
    ORDER BY COALESCE(b.missed, 0) + COALESCE(c.claim_count, 0) DESC
    LIMIT 1200
)
SELECT
    'RSK-' || LPAD(rp.risk_rn::VARCHAR, 5, '0') AS RISK_ID,
    rp.POLICY_ID,
    rp.CUSTOMER_ID,
    risk_categories.arr[UNIFORM(0, 5, RANDOM(rp.risk_rn * 7))]::VARCHAR AS RISK_CATEGORY,
    -- Higher churn probability for policies with more missed payments
    ROUND(LEAST(0.9999,
        0.20 + (rp.missed_payments * 0.08) + (rp.claims_filed * 0.04) + UNIFORM(0.00, 0.25, RANDOM(rp.risk_rn * 11))::DECIMAL(5,4)
    ), 4) AS CHURN_PROBABILITY,
    ROUND(rp.PREMIUM_AMOUNT * 12, 2) AS REVENUE_AT_RISK,
    GREATEST(0, DATEDIFF('day', CURRENT_DATE(), rp.END_DATE)) AS DAYS_UNTIL_RENEWAL,
    rp.missed_payments AS MISSED_PAYMENTS_COUNT,
    rp.claims_filed AS CLAIM_FREQUENCY,
    UNIFORM(-20, 80, RANDOM(rp.risk_rn * 13)) AS NPS_SCORE,
    DATEADD('day', -UNIFORM(1, 90, RANDOM(rp.risk_rn * 17)), CURRENT_DATE()) AS LAST_CONTACT_DATE,
    retention_actions.arr[UNIFORM(0, 5, RANDOM(rp.risk_rn * 19))]::VARCHAR AS RETENTION_ACTION,
    CURRENT_DATE() AS SNAPSHOT_DATE
FROM risky_policies rp
CROSS JOIN risk_categories
CROSS JOIN retention_actions;

-- Verify counts
SELECT 'POLICIES' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM POLICIES
UNION ALL SELECT 'CLAIMS', COUNT(*) FROM CLAIMS
UNION ALL SELECT 'BILLING', COUNT(*) FROM BILLING
UNION ALL SELECT 'AT_RISK_POLICIES', COUNT(*) FROM AT_RISK_POLICIES;
