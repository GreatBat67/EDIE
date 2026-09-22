-- ============================================================
-- INSURANCE AI HUB (E.D.I.E.) - Inject Realistic Data Issues
-- Phase 4: Deliberate data quality problems for realism
-- These issues support the "Data Trust" pillar demos
-- ============================================================

USE DATABASE INSURANCE_AI_HUB;
USE WAREHOUSE INSURANCE_AI_HUB_WH;
USE SCHEMA ANALYTICS;

-- ============================================================
-- ISSUE 1: NULL emails and phones (3-5% of customers)
-- Supports DQ rule DQR-001, DQR-002 failure scenarios
-- ============================================================

-- Null out ~4% of emails (200 customers)
UPDATE CUSTOMERS
SET EMAIL = NULL
WHERE CUSTOMER_ID IN (
    SELECT CUSTOMER_ID FROM CUSTOMERS
    SAMPLE (4)
    LIMIT 200
);

-- Null out ~3% of phones (150 customers)
UPDATE CUSTOMERS
SET PHONE = NULL
WHERE CUSTOMER_ID IN (
    SELECT CUSTOMER_ID FROM CUSTOMERS
    WHERE PHONE IS NOT NULL
    SAMPLE (3)
    LIMIT 150
);

-- ============================================================
-- ISSUE 2: Near-duplicate customers (15 records)
-- Same name/DOB but different IDs — simulates bad dedup
-- ============================================================

INSERT INTO CUSTOMERS
SELECT
    'CUST-D' || LPAD(ROW_NUMBER() OVER (ORDER BY CUSTOMER_ID)::VARCHAR, 4, '0') AS CUSTOMER_ID,
    FIRST_NAME,
    LAST_NAME,
    DATE_OF_BIRTH,
    GENDER,
    -- Slight variation in email (added suffix)
    REPLACE(EMAIL, '@', '.dup@') AS EMAIL,
    -- Different phone
    '(' || LPAD(UNIFORM(200, 999, RANDOM())::VARCHAR, 3, '0') || ') ' ||
        LPAD(UNIFORM(200, 999, RANDOM())::VARCHAR, 3, '0') || '-' ||
        LPAD(UNIFORM(1000, 9999, RANDOM())::VARCHAR, 4, '0') AS PHONE,
    ADDRESS,
    CITY,
    STATE,
    ZIP_CODE,
    RISK_TIER,
    -- Slightly different credit score
    CREDIT_SCORE + UNIFORM(-15, 15, RANDOM()) AS CREDIT_SCORE,
    -- Different customer_since date
    DATEADD('day', UNIFORM(1, 60, RANDOM()), CUSTOMER_SINCE) AS CUSTOMER_SINCE,
    SEGMENT
FROM CUSTOMERS
WHERE CUSTOMER_ID IN (
    SELECT CUSTOMER_ID FROM CUSTOMERS ORDER BY RANDOM() LIMIT 15
);

-- ============================================================
-- ISSUE 3: Claims with extreme resolution days (long tail)
-- 5% of claims take 200+ days — creates operational friction
-- ============================================================

UPDATE CLAIMS
SET RESOLUTION_DAYS = UNIFORM(200, 450, RANDOM())
WHERE CLAIM_ID IN (
    SELECT CLAIM_ID FROM CLAIMS
    WHERE RESOLUTION_DAYS IS NOT NULL
    SAMPLE (5)
    LIMIT 175
);

-- ============================================================
-- ISSUE 4: Clustered fraud signals in North Region
-- Creates the "North Region spike" demo scenario
-- High fraud scores clustered in a specific time window
-- ============================================================

UPDATE CLAIMS
SET FRAUD_SCORE = ROUND(UNIFORM(82.00, 98.50, RANDOM())::DECIMAL(5,2), 2)
WHERE CLAIM_ID IN (
    SELECT cl.CLAIM_ID
    FROM CLAIMS cl
    JOIN POLICIES p ON cl.POLICY_ID = p.POLICY_ID
    JOIN AGENTS a ON p.AGENT_ID = a.AGENT_ID
    WHERE a.REGION = 'Northeast'
      AND cl.CLAIM_DATE BETWEEN '2025-03-01' AND '2025-05-31'
    LIMIT 45
);

-- ============================================================
-- ISSUE 5: Billing inconsistencies
-- Some "Paid" invoices with NULL payment_date
-- Some outstanding_balance != amount_due - amount_paid
-- ============================================================

-- Paid invoices missing payment date (~3%)
UPDATE BILLING
SET PAYMENT_DATE = NULL
WHERE INVOICE_ID IN (
    SELECT INVOICE_ID FROM BILLING
    WHERE PAYMENT_STATUS = 'Paid'
    SAMPLE (3)
    LIMIT 500
);

-- Balance calculation errors (~1.5%)
UPDATE BILLING
SET OUTSTANDING_BALANCE = OUTSTANDING_BALANCE + UNIFORM(5, 50, RANDOM())::DECIMAL(12,2)
WHERE INVOICE_ID IN (
    SELECT INVOICE_ID FROM BILLING
    WHERE PAYMENT_STATUS = 'Partial'
    SAMPLE (15)
    LIMIT 300
);

-- ============================================================
-- ISSUE 6: Seasonal claims spike injection
-- Extra claims in hurricane season (Aug-Oct 2024) for Southeast
-- Supports the "why did claims jump" demo
-- ============================================================

INSERT INTO CLAIMS
WITH
policy_pool AS (
    SELECT p.POLICY_ID, p.CUSTOMER_ID, p.POLICY_TYPE,
           ROW_NUMBER() OVER (ORDER BY RANDOM()) AS rn
    FROM POLICIES p
    JOIN AGENTS a ON p.AGENT_ID = a.AGENT_ID
    WHERE a.REGION = 'Southeast'
      AND p.STATUS = 'Active'
      AND p.POLICY_TYPE IN ('Home','Auto')
    LIMIT 50
)
SELECT
    'CLM-H' || LPAD(rn::VARCHAR, 4, '0') AS CLAIM_ID,
    POLICY_ID,
    CUSTOMER_ID,
    DATEADD('day', UNIFORM(0, 60, RANDOM(rn)), '2024-08-15'::DATE) AS CLAIM_DATE,
    CASE POLICY_TYPE
        WHEN 'Home' THEN CASE UNIFORM(1,3,RANDOM(rn))
            WHEN 1 THEN 'Storm Damage'
            WHEN 2 THEN 'Water Damage'
            ELSE 'Structural'
        END
        ELSE CASE UNIFORM(1,2,RANDOM(rn))
            WHEN 1 THEN 'Collision'
            ELSE 'Glass Damage'
        END
    END AS CLAIM_TYPE,
    ROUND(UNIFORM(5000, 85000, RANDOM(rn * 7))::DECIMAL(12,2), 2) AS CLAIM_AMOUNT,
    ROUND(UNIFORM(3000, 60000, RANDOM(rn * 11))::DECIMAL(12,2), 2) AS APPROVED_AMOUNT,
    'Approved' AS STATUS,
    ROUND(UNIFORM(5.00, 35.00, RANDOM(rn * 13))::DECIMAL(5,2), 2) AS FRAUD_SCORE,
    'ADJ-' || LPAD(UNIFORM(1, 50, RANDOM(rn * 17))::VARCHAR, 3, '0') AS ADJUSTER_ID,
    UNIFORM(14, 60, RANDOM(rn * 19)) AS RESOLUTION_DAYS,
    ROUND(UNIFORM(3.0, 8.5, RANDOM(rn * 23))::DECIMAL(5,2), 2) AS FRICTION_SCORE,
    'Hurricane/Tropical Storm' AS CAUSE_OF_LOSS,
    'Residence' AS INCIDENT_LOCATION,
    DATEADD('day', UNIFORM(14, 60, RANDOM(rn * 19)),
        DATEADD('day', UNIFORM(0, 60, RANDOM(rn)), '2024-08-15'::DATE)) AS CLOSED_DATE
FROM policy_pool;

-- ============================================================
-- ISSUE 7: Agent performance gaps (bimodal)
-- A few agents with very low ratings but high policy counts
-- Creates suspicious pattern for investigation
-- ============================================================

UPDATE AGENTS
SET PERFORMANCE_RATING = ROUND(UNIFORM(1.10, 1.80, RANDOM())::DECIMAL(3,2), 2),
    ACTIVE_POLICIES_COUNT = UNIFORM(80, 120, RANDOM())
WHERE AGENT_ID IN (
    SELECT AGENT_ID FROM AGENTS
    WHERE STATUS = 'Active'
    ORDER BY RANDOM()
    LIMIT 8
);

-- ============================================================
-- ISSUE 8: Stale AT_RISK_POLICIES snapshot
-- Some records with old snapshot dates (appears as stale data)
-- ============================================================

UPDATE AT_RISK_POLICIES
SET SNAPSHOT_DATE = DATEADD('day', -UNIFORM(45, 120, RANDOM()), CURRENT_DATE()),
    LAST_CONTACT_DATE = DATEADD('day', -UNIFORM(90, 180, RANDOM()), CURRENT_DATE())
WHERE RISK_ID IN (
    SELECT RISK_ID FROM AT_RISK_POLICIES
    SAMPLE (20)
    LIMIT 240
);

-- ============================================================
-- ISSUE 9: Premium outliers (Commercial policies 10x normal)
-- A few extreme values that look like data entry errors
-- ============================================================

UPDATE POLICIES
SET PREMIUM_AMOUNT = PREMIUM_AMOUNT * UNIFORM(8, 15, RANDOM())::DECIMAL(5,2)
WHERE POLICY_ID IN (
    SELECT POLICY_ID FROM POLICIES
    WHERE POLICY_TYPE = 'Commercial'
    ORDER BY RANDOM()
    LIMIT 12
);

-- ============================================================
-- ISSUE 10: Duplicate claim IDs in North Region window
-- Supports the "data quality explains the spike" narrative
-- ============================================================

INSERT INTO CLAIMS
SELECT
    'CLM-DUP' || LPAD(ROW_NUMBER() OVER (ORDER BY CLAIM_ID)::VARCHAR, 3, '0') AS CLAIM_ID,
    POLICY_ID,
    CUSTOMER_ID,
    CLAIM_DATE,
    CLAIM_TYPE,
    CLAIM_AMOUNT,
    APPROVED_AMOUNT,
    STATUS,
    FRAUD_SCORE,
    ADJUSTER_ID,
    RESOLUTION_DAYS,
    FRICTION_SCORE,
    CAUSE_OF_LOSS,
    INCIDENT_LOCATION,
    CLOSED_DATE
FROM CLAIMS
WHERE CLAIM_DATE BETWEEN '2025-03-01' AND '2025-04-30'
  AND CLAIM_ID IN (
    SELECT cl.CLAIM_ID FROM CLAIMS cl
    JOIN POLICIES p ON cl.POLICY_ID = p.POLICY_ID
    JOIN AGENTS a ON p.AGENT_ID = a.AGENT_ID
    WHERE a.REGION = 'Northeast'
    LIMIT 12
);

-- ============================================================
-- VERIFICATION: Summary of injected issues
-- ============================================================

SELECT 'Null Emails' AS ISSUE, COUNT(*) AS COUNT FROM CUSTOMERS WHERE EMAIL IS NULL
UNION ALL SELECT 'Null Phones', COUNT(*) FROM CUSTOMERS WHERE PHONE IS NULL
UNION ALL SELECT 'Duplicate Customers', COUNT(*) FROM CUSTOMERS WHERE CUSTOMER_ID LIKE 'CUST-D%'
UNION ALL SELECT 'Extreme Resolution (200+ days)', COUNT(*) FROM CLAIMS WHERE RESOLUTION_DAYS > 200
UNION ALL SELECT 'High Fraud Score (>80)', COUNT(*) FROM CLAIMS WHERE FRAUD_SCORE > 80
UNION ALL SELECT 'Hurricane Claims', COUNT(*) FROM CLAIMS WHERE CAUSE_OF_LOSS = 'Hurricane/Tropical Storm'
UNION ALL SELECT 'Duplicate Claims', COUNT(*) FROM CLAIMS WHERE CLAIM_ID LIKE 'CLM-DUP%'
UNION ALL SELECT 'Low Perf High Volume Agents', COUNT(*) FROM AGENTS WHERE PERFORMANCE_RATING < 2.0 AND ACTIVE_POLICIES_COUNT > 75
UNION ALL SELECT 'Stale Risk Snapshots (45+ days)', COUNT(*) FROM AT_RISK_POLICIES WHERE SNAPSHOT_DATE < DATEADD('day', -44, CURRENT_DATE())
UNION ALL SELECT 'Premium Outliers (>10000)', COUNT(*) FROM POLICIES WHERE PREMIUM_AMOUNT > 10000;
