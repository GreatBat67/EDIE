-- ############################################################################
-- 12_MARKETPLACE_INTEGRATION_AND_DAILY_TASKS.sql
-- Links live Marketplace data (SNOWFLAKE_PUBLIC_DATA_FREE) into the
-- INSURANCE_AI_HUB schema via views, and creates daily tasks to refresh
-- internal enrichment tables.
-- ############################################################################

USE DATABASE INSURANCE_AI_HUB;
USE WAREHOUSE COMPUTE_WH;


-- ############################################################################
-- PART 1: MARKETPLACE DATA VIEWS
-- These views expose live, auto-refreshing Marketplace data through
-- the EXTERNAL_DATA schema — no manual refresh needed.
-- ############################################################################

USE SCHEMA EXTERNAL_DATA;

-- ============================================================
-- 1a. LIVE_NWS_WEATHER_ALERTS  (replaces NOAA_STORM_EVENTS)
-- Source: SNOWFLAKE_PUBLIC_DATA_FREE — NWS alerts, updated continuously
-- ============================================================

CREATE OR REPLACE VIEW LIVE_NWS_WEATHER_ALERTS AS
SELECT
    NWS_ALERT_ID                            AS ALERT_ID,
    REPLACE(COUNTY_GEO_ID, 'geoId/', '')    AS COUNTY_FIPS,
    s.STATE_ABBREV                          AS STATE,
    EVENT_TYPE,
    EVENT_SEVERITY,
    EVENT_URGENCY,
    EVENT_CERTAINTY,
    ALERT_STATUS,
    ALERT_TYPE,
    ALERT_TITLE,
    ALERT_DESCRIPTION,
    ONSET_TIMESTAMP                         AS EVENT_BEGIN,
    END_TIMESTAMP                           AS EVENT_END,
    SENT_TIMESTAMP                          AS REPORTED_DATE,
    NWS_REPORTER                            AS SOURCE
FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.NWS_WEATHER_ALERT_EVENTS nws
LEFT JOIN STATE_FIPS_LOOKUP s
    ON s.STATE_GEO_ID = LEFT(nws.COUNTY_GEO_ID, 9)
WHERE ONSET_TIMESTAMP >= '2022-01-01';

COMMENT ON VIEW LIVE_NWS_WEATHER_ALERTS IS
    'Live NWS weather alerts from Snowflake Public Data — auto-refreshing, replaces synthetic NOAA_STORM_EVENTS';


-- ============================================================
-- 1b. LIVE_FEMA_DISASTER_DECLARATIONS  (replaces FEMA_RISK_INDEX)
-- Source: SNOWFLAKE_PUBLIC_DATA_FREE — FEMA disaster declarations
-- ============================================================

CREATE OR REPLACE VIEW LIVE_FEMA_DISASTER_DECLARATIONS AS
SELECT
    DISASTER_DECLARATION_RECORD_ID          AS RECORD_ID,
    DISASTER_ID,
    FEMA_DESIGNATED_AREA                    AS DESIGNATED_AREA,
    s.STATE_ABBREV                          AS STATE,
    REPLACE(fda.COUNTY_GEO_ID, 'geoId/', '') AS COUNTY_FIPS,
    FEMA_REGION_ID                          AS FEMA_REGION,
    TRIBAL_REQUEST,
    DECLARED_PROGRAMS_DETAILED              AS PROGRAMS,
    DESIGNATED_DATE,
    ENTRY_DATE,
    UPDATE_DATE,
    CLOSEOUT_DATE
FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.FEMA_DISASTER_DECLARATION_AREAS_INDEX fda
LEFT JOIN STATE_FIPS_LOOKUP s
    ON s.STATE_GEO_ID = fda.STATE_GEO_ID
WHERE DESIGNATED_DATE IS NOT NULL;

COMMENT ON VIEW LIVE_FEMA_DISASTER_DECLARATIONS IS
    'Live FEMA disaster declaration areas from Snowflake Public Data — auto-refreshing';


-- ============================================================
-- 1c. LIVE_FEMA_FLOOD_CLAIMS  (new — enriches flood risk analysis)
-- Source: SNOWFLAKE_PUBLIC_DATA_FREE — NFIP flood insurance claims
-- ============================================================

CREATE OR REPLACE VIEW LIVE_FEMA_FLOOD_CLAIMS AS
SELECT
    NATIONAL_FLOOD_INSURANCE_PROGRAM_CLAIM_ID   AS CLAIM_ID,
    s.STATE_ABBREV                              AS STATE,
    CITY,
    REPLACE(nfip.ZIP_GEO_ID, 'zip/', '')        AS ZIP_CODE,
    OCCUPANCY_TYPE,
    BUILDING_TYPE,
    FLOOD_EVENT,
    CAUSE_OF_DAMAGE,
    DATE_OF_LOSS,
    BUILDING_PROPERTY_VALUE,
    BUILDING_DAMAGE_AMOUNT,
    AMOUNT_PAID_ON_BUILDING_CLAIM,
    CONTENTS_DAMAGE_AMOUNT,
    AMOUNT_PAID_ON_CONTENTS_CLAIM,
    CURRENT_FLOOD_ZONE,
    NUMBER_OF_FLOORS,
    ORIGINAL_CONSTRUCTION_DATE,
    LATITUDE,
    LONGITUDE
FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.FEMA_NATIONAL_FLOOD_INSURANCE_PROGRAM_CLAIM_INDEX nfip
LEFT JOIN STATE_FIPS_LOOKUP s
    ON s.STATE_GEO_ID = nfip.STATE_GEO_ID;

COMMENT ON VIEW LIVE_FEMA_FLOOD_CLAIMS IS
    'Live FEMA NFIP flood insurance claims from Snowflake Public Data — auto-refreshing, enriches property risk analysis';


-- ============================================================
-- 1d. LIVE_BLS_CPI_DATA  (replaces FRED_ECONOMIC_INDICATORS)
-- Source: SNOWFLAKE_PUBLIC_DATA_FREE — BLS Consumer Price Index
-- ============================================================

CREATE OR REPLACE VIEW LIVE_BLS_CPI_DATA AS
SELECT
    GEO_ID,
    VARIABLE                                AS SERIES_ID,
    VARIABLE_NAME                           AS SERIES_NAME,
    DATE                                    AS OBSERVATION_DATE,
    VALUE,
    CASE
        WHEN VARIABLE_NAME ILIKE '%index%' THEN 'Index'
        WHEN VARIABLE_NAME ILIKE '%percent%' THEN 'Percent'
        WHEN VARIABLE_NAME ILIKE '%average price%' THEN 'USD'
        ELSE 'Index'
    END                                     AS UNIT,
    CASE
        WHEN VARIABLE_NAME ILIKE '%monthly%' THEN 'Monthly'
        WHEN VARIABLE_NAME ILIKE '%quarterly%' THEN 'Quarterly'
        WHEN VARIABLE_NAME ILIKE '%annual%' THEN 'Annual'
        ELSE 'Monthly'
    END                                     AS FREQUENCY
FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.BUREAU_OF_LABOR_STATISTICS_PRICE_TIMESERIES
WHERE GEO_ID = 'country/USA'
  AND DATE >= '2020-01-01';

COMMENT ON VIEW LIVE_BLS_CPI_DATA IS
    'Live BLS CPI & price data from Snowflake Public Data — auto-refreshing, replaces synthetic FRED_ECONOMIC_INDICATORS';


-- ============================================================
-- 1e. LIVE_FEMA_FLOOD_POLICIES  (new — flood insurance coverage)
-- ============================================================

CREATE OR REPLACE VIEW LIVE_FEMA_FLOOD_POLICIES AS
SELECT
    nfip.*,
    s.STATE_ABBREV AS STATE
FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.FEMA_NATIONAL_FLOOD_INSURANCE_PROGRAM_POLICY_INDEX nfip
LEFT JOIN STATE_FIPS_LOOKUP s
    ON s.STATE_GEO_ID = nfip.STATE_GEO_ID;

COMMENT ON VIEW LIVE_FEMA_FLOOD_POLICIES IS
    'Live FEMA NFIP flood insurance policies from Snowflake Public Data — coverage amounts, premiums, geographic distribution';


-- ############################################################################
-- PART 2: DAILY REFRESH TASKS
-- Scheduled tasks that regenerate internal enrichment tables daily at 2 AM UTC.
-- Uses a task graph: root task triggers child tasks in parallel.
-- ############################################################################

USE SCHEMA ANALYTICS;


-- ============================================================
-- 2a. Root task — runs daily at 2:00 AM UTC
-- ============================================================

CREATE OR REPLACE TASK DAILY_ENRICHMENT_ROOT
    WAREHOUSE = 'COMPUTE_WH'
    SCHEDULE  = 'USING CRON 0 2 * * * UTC'
    COMMENT   = 'Root task: triggers daily refresh of enrichment tables at 2 AM UTC'
AS
    SELECT 1;


-- ============================================================
-- 2b. VEHICLE_DETAILS refresh
-- Re-syncs vehicle records for any new auto policies
-- ============================================================

CREATE OR REPLACE TASK DAILY_REFRESH_VEHICLE_DETAILS
    WAREHOUSE = 'COMPUTE_WH'
    AFTER INSURANCE_AI_HUB.ANALYTICS.DAILY_ENRICHMENT_ROOT
AS
    INSERT INTO INSURANCE_AI_HUB.ANALYTICS.VEHICLE_DETAILS (VEHICLE_ID, POLICY_ID, VIN, MAKE, MODEL, YEAR, BODY_TYPE, ENGINE_TYPE, SAFETY_RATING, ANNUAL_MILEAGE, GARAGE_ZIP)
    WITH new_policies AS (
        SELECT p.POLICY_ID, p.CUSTOMER_ID, c.ZIP_CODE,
               ROW_NUMBER() OVER (ORDER BY p.POLICY_ID) AS rn
        FROM INSURANCE_AI_HUB.ANALYTICS.POLICIES p
        JOIN INSURANCE_AI_HUB.ANALYTICS.CUSTOMERS c ON c.CUSTOMER_ID = p.CUSTOMER_ID
        WHERE p.POLICY_TYPE IN ('PersonalAuto','CommercialAuto')
          AND p.POLICY_ID NOT IN (SELECT POLICY_ID FROM INSURANCE_AI_HUB.ANALYTICS.VEHICLE_DETAILS)
    ),
    makes AS (
        SELECT column1 AS VMAKE, column2 AS VMODEL, column3 AS VBODY,
               ROW_NUMBER() OVER (ORDER BY column1, column2) AS mrn,
               COUNT(*) OVER () AS mtotal
        FROM VALUES
            ('Toyota','Camry','Sedan'),('Toyota','RAV4','SUV'),('Honda','Civic','Sedan'),
            ('Honda','CR-V','SUV'),('Ford','F-150','Truck'),('Ford','Explorer','SUV'),
            ('Chevrolet','Silverado','Truck'),('Chevrolet','Equinox','SUV'),
            ('Tesla','Model 3','Sedan'),('Tesla','Model Y','SUV'),
            ('BMW','3 Series','Sedan'),('BMW','X5','SUV'),
            ('Hyundai','Tucson','SUV'),('Kia','Sportage','SUV'),
            ('Nissan','Rogue','SUV'),('Subaru','Outback','Wagon')
    )
    SELECT
        'VEH-' || LPAD(
            ((SELECT COALESCE(MAX(REPLACE(VEHICLE_ID, 'VEH-', '')::INT), 0) FROM INSURANCE_AI_HUB.ANALYTICS.VEHICLE_DETAILS)
            + np.rn)::VARCHAR, 5, '0'),
        np.POLICY_ID,
        UPPER(SUBSTR(MD5(np.POLICY_ID), 1, 17)),
        m.VMAKE, m.VMODEL,
        UNIFORM(2015, 2025, RANDOM()),
        m.VBODY,
        CASE MOD(ABS(HASH(np.POLICY_ID)), 5)
            WHEN 0 THEN 'Hybrid' WHEN 1 THEN 'Electric' WHEN 2 THEN 'Diesel' ELSE 'Gasoline'
        END,
        UNIFORM(1, 5, RANDOM()),
        UNIFORM(5000, 25000, RANDOM()),
        np.ZIP_CODE
    FROM new_policies np
    JOIN makes m ON m.mrn = MOD(np.rn - 1, m.mtotal) + 1;


-- ============================================================
-- 2c. CUSTOMER_ATTRIBUTE_HISTORY refresh
-- Appends attribute changes from the previous day
-- ============================================================

CREATE OR REPLACE TASK DAILY_REFRESH_CUSTOMER_ATTR_HISTORY
    WAREHOUSE = 'COMPUTE_WH'
    AFTER INSURANCE_AI_HUB.ANALYTICS.DAILY_ENRICHMENT_ROOT
AS
    INSERT INTO INSURANCE_AI_HUB.ANALYTICS.CUSTOMER_ATTRIBUTE_HISTORY (HISTORY_ID, CUSTOMER_ID, ATTRIBUTE_NAME, OLD_VALUE, NEW_VALUE, CHANGE_DATE, CHANGE_REASON, TRIGGERED_BY)
    WITH next_id AS (
        SELECT COALESCE(MAX(REPLACE(HISTORY_ID, 'CHIST-', '')::INT), 0) AS max_id
        FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMER_ATTRIBUTE_HISTORY
    ),
    changed_customers AS (
        SELECT CUSTOMER_ID, RISK_TIER, SEGMENT, CREDIT_SCORE,
               ROW_NUMBER() OVER (ORDER BY RANDOM()) AS rn
        FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMERS
        WHERE MOD(ABS(HASH(CUSTOMER_ID || CURRENT_DATE()::VARCHAR)), 100) < 2
        LIMIT 50
    )
    SELECT
        'CHIST-' || LPAD((ni.max_id + cc.rn)::VARCHAR, 6, '0'),
        cc.CUSTOMER_ID,
        CASE MOD(cc.rn, 3)
            WHEN 0 THEN 'RISK_TIER' WHEN 1 THEN 'SEGMENT' ELSE 'CREDIT_SCORE'
        END,
        CASE MOD(cc.rn, 3)
            WHEN 0 THEN cc.RISK_TIER
            WHEN 1 THEN cc.SEGMENT
            ELSE cc.CREDIT_SCORE::VARCHAR
        END,
        CASE MOD(cc.rn, 3)
            WHEN 0 THEN CASE MOD(ABS(HASH(cc.CUSTOMER_ID || 'new')), 4)
                            WHEN 0 THEN 'Low' WHEN 1 THEN 'Medium' WHEN 2 THEN 'High' ELSE 'Critical' END
            WHEN 1 THEN CASE MOD(ABS(HASH(cc.CUSTOMER_ID || 'seg')), 3)
                            WHEN 0 THEN 'Budget' WHEN 1 THEN 'Standard' ELSE 'Premium' END
            ELSE UNIFORM(300, 850, RANDOM())::VARCHAR
        END,
        CURRENT_DATE(),
        CASE MOD(ABS(HASH(cc.CUSTOMER_ID || CURRENT_DATE()::VARCHAR)), 5)
            WHEN 0 THEN 'Annual Review' WHEN 1 THEN 'Claim Filed' WHEN 2 THEN 'Credit Update'
            WHEN 3 THEN 'Policy Renewal' ELSE 'Risk Reassessment'
        END,
        CASE MOD(ABS(HASH(cc.CUSTOMER_ID)), 4)
            WHEN 0 THEN 'Renewal' WHEN 1 THEN 'Claim' WHEN 2 THEN 'SystemUpdate' ELSE 'AnnualReview'
        END
    FROM changed_customers cc
    CROSS JOIN next_id ni;


-- ============================================================
-- 2d. CLAIM_ACTIVITY_LOG refresh
-- Appends adjuster activity from the previous day
-- ============================================================

CREATE OR REPLACE TASK DAILY_REFRESH_CLAIM_ACTIVITY_LOG
    WAREHOUSE = 'COMPUTE_WH'
    AFTER INSURANCE_AI_HUB.ANALYTICS.DAILY_ENRICHMENT_ROOT
AS
    INSERT INTO INSURANCE_AI_HUB.ANALYTICS.CLAIM_ACTIVITY_LOG (ACTIVITY_ID, CLAIM_ID, ADJUSTER_ID, ACTIVITY_DATE, ACTIVITY_TYPE, NOTES, DURATION_MINUTES)
    WITH next_id AS (
        SELECT COALESCE(MAX(REPLACE(ACTIVITY_ID, 'ACT-', '')::INT), 0) AS max_id
        FROM INSURANCE_AI_HUB.ANALYTICS.CLAIM_ACTIVITY_LOG
    ),
    open_claims AS (
        SELECT CLAIM_ID, ADJUSTER_ID,
               ROW_NUMBER() OVER (ORDER BY RANDOM()) AS rn
        FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS
        WHERE CLAIM_STATUS IN ('Open', 'Under Review', 'Pending')
          AND ADJUSTER_ID IS NOT NULL
        LIMIT 200
    ),
    activity_types_arr AS (
        SELECT ARRAY_CONSTRUCT(
            'InitialReview','ContactClaimant','RequestDocuments','FieldInspection',
            'DamageAssessment','CoverageVerification','ApprovalSubmission',
            'FollowUpCall','ThirdPartyContact','SupervisorReview'
        ) AS arr
    )
    SELECT
        'ACT-' || LPAD((ni.max_id + oc.rn)::VARCHAR, 6, '0'),
        oc.CLAIM_ID,
        oc.ADJUSTER_ID,
        DATEADD('second', UNIFORM(0, 86400, RANDOM()), CURRENT_DATE()::TIMESTAMP_NTZ),
        at.arr[MOD(ABS(HASH(oc.CLAIM_ID || oc.rn::VARCHAR)), 10)]::VARCHAR,
        'Daily activity recorded by system.',
        UNIFORM(5, 120, RANDOM())
    FROM open_claims oc
    CROSS JOIN next_id ni
    CROSS JOIN activity_types_arr at;


-- ============================================================
-- 2e. CLAIMS FRICTION_REASON update
-- Fills FRICTION_REASON for any new claims missing it
-- ============================================================

CREATE OR REPLACE TASK DAILY_UPDATE_FRICTION_REASON
    WAREHOUSE = 'COMPUTE_WH'
    AFTER INSURANCE_AI_HUB.ANALYTICS.DAILY_ENRICHMENT_ROOT
AS
    UPDATE INSURANCE_AI_HUB.ANALYTICS.CLAIMS
    SET FRICTION_REASON = CASE MOD(ABS(HASH(CLAIM_ID || 'fr')), 6)
        WHEN 0 THEN 'Documentation Delay'
        WHEN 1 THEN 'Adjuster Reassignment'
        WHEN 2 THEN 'Dispute Resolution'
        WHEN 3 THEN 'Third Party Response'
        WHEN 4 THEN 'System Error'
        ELSE 'Policy Verification'
    END
    WHERE FRICTION_SCORE > 3.0 AND FRICTION_REASON IS NULL;


-- ############################################################################
-- PART 3: RESUME ALL TASKS
-- ############################################################################

-- Resume child tasks first, then root task
ALTER TASK DAILY_REFRESH_VEHICLE_DETAILS RESUME;
ALTER TASK DAILY_REFRESH_CUSTOMER_ATTR_HISTORY RESUME;
ALTER TASK DAILY_REFRESH_CLAIM_ACTIVITY_LOG RESUME;
ALTER TASK DAILY_UPDATE_FRICTION_REASON RESUME;
ALTER TASK DAILY_ENRICHMENT_ROOT RESUME;


-- ############################################################################
-- VERIFICATION
-- ############################################################################

-- Check all tasks are running
SHOW TASKS IN SCHEMA INSURANCE_AI_HUB.ANALYTICS;

-- Test live Marketplace views
SELECT 'LIVE_NWS_WEATHER_ALERTS' AS VIEW_NAME, COUNT(*) AS ROW_COUNT FROM EXTERNAL_DATA.LIVE_NWS_WEATHER_ALERTS
UNION ALL SELECT 'LIVE_FEMA_DISASTER_DECLARATIONS', COUNT(*) FROM EXTERNAL_DATA.LIVE_FEMA_DISASTER_DECLARATIONS
UNION ALL SELECT 'LIVE_FEMA_FLOOD_CLAIMS', COUNT(*) FROM EXTERNAL_DATA.LIVE_FEMA_FLOOD_CLAIMS
UNION ALL SELECT 'LIVE_BLS_CPI_DATA', COUNT(*) FROM EXTERNAL_DATA.LIVE_BLS_CPI_DATA
UNION ALL SELECT 'LIVE_FEMA_FLOOD_POLICIES', COUNT(*) FROM EXTERNAL_DATA.LIVE_FEMA_FLOOD_POLICIES;
