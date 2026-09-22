-- ============================================================
-- INSURANCE AI HUB (E.D.I.E.) - External Data Integration
-- Phase 11: External/Marketplace proxy tables + internal
-- enrichment tables to close remaining business question gaps
-- ============================================================
--
-- Creates:
--   EXTERNAL_DATA schema (4 tables - Marketplace proxies)
--     - NOAA_STORM_EVENTS        (~2,000 rows)
--     - FRED_ECONOMIC_INDICATORS  (~1,500 rows)
--     - FEMA_RISK_INDEX           (~5,000 rows)
--     - NAIC_STATUTORY_GUIDELINES (~100 rows)
--   ANALYTICS tables (3 new)
--     - VEHICLE_DETAILS             (~8,000 rows)
--     - CUSTOMER_ATTRIBUTE_HISTORY  (~10,000 rows)
--     - CLAIM_ACTIVITY_LOG          (~15,000 rows)
--   Column addition
--     - CLAIMS.FRICTION_REASON      (backfill all rows)
--
-- Closes: 3 NO → 0 NO, ~9 PARTIAL → YES
-- ============================================================

USE DATABASE INSURANCE_AI_HUB;
USE WAREHOUSE INSURANCE_AI_HUB_WH;

-- ############################################################################
-- NEW SCHEMA: EXTERNAL_DATA
-- ############################################################################

CREATE SCHEMA IF NOT EXISTS EXTERNAL_DATA
    COMMENT = 'External data proxies simulating Marketplace listings (NOAA weather, FRED economics, FEMA risk, NAIC guidelines). Replace with real Marketplace installs for production.';


-- ============================================================
-- 1. NOAA_STORM_EVENTS (~2,000 rows)
-- Marketplace: Severe Weather Data Inventory (GZSTZJUPD05, FREE)
-- Enables: Marcus #6 (hail claims + NOAA alerts)
-- ============================================================
USE SCHEMA EXTERNAL_DATA;

CREATE OR REPLACE TABLE NOAA_STORM_EVENTS (
    EVENT_ID            VARCHAR(20)     NOT NULL,
    EVENT_DATE          DATE            NOT NULL,
    EVENT_TYPE          VARCHAR(30)     NOT NULL,
    STATE               VARCHAR(2)      NOT NULL,
    COUNTY              VARCHAR(50),
    FIPS_CODE           VARCHAR(5),
    MAGNITUDE           DECIMAL(5,2),
    INJURIES            INT             DEFAULT 0,
    DEATHS              INT             DEFAULT 0,
    PROPERTY_DAMAGE     DECIMAL(14,2)   DEFAULT 0,
    CROP_DAMAGE         DECIMAL(14,2)   DEFAULT 0,
    SOURCE              VARCHAR(30)     NOT NULL DEFAULT 'NOAA-SWDI',
    BEGIN_LAT           DECIMAL(8,5),
    BEGIN_LON           DECIMAL(9,5),
    CONSTRAINT PK_NOAA PRIMARY KEY (EVENT_ID)
)
COMMENT = 'NOAA Severe Weather Data Inventory proxy — storm events by state, date, and type for claims correlation';

INSERT INTO NOAA_STORM_EVENTS
WITH
event_types AS (
    SELECT ARRAY_CONSTRUCT('Hail','Hail','Tornado','Thunderstorm Wind','Winter Storm','Flash Flood',
                           'Hurricane','Tropical Storm','Ice Storm','Heavy Rain','Wildfire','Blizzard') AS arr
),
states AS (
    SELECT ARRAY_CONSTRUCT('CA','TX','FL','NY','IL','PA','OH','GA','NC','MI',
                           'NJ','VA','WA','AZ','MA','CO','IN','MO','TN','LA',
                           'IA','KS','OK','NE','AL','SC','MN','WI','MS','AR') AS arr
),
counties AS (
    SELECT ARRAY_CONSTRUCT('Adams','Baker','Clark','Douglas','Edwards','Franklin',
                           'Greene','Hamilton','Jackson','Jefferson','Knox','Lincoln',
                           'Madison','Nelson','Orange','Pike','Ross','Summit','Wayne','York') AS arr
),
raw AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn,
        UNIFORM(0, 1460, RANDOM()) AS r_days,
        UNIFORM(0, 11, RANDOM()) AS r_type,
        UNIFORM(0, 29, RANDOM()) AS r_state,
        UNIFORM(0, 19, RANDOM()) AS r_county,
        UNIFORM(0, 300, RANDOM()) AS r_mag,
        UNIFORM(0, 10, RANDOM()) AS r_inj,
        UNIFORM(0, 2, RANDOM()) AS r_deaths,
        UNIFORM(1000, 5000000, RANDOM()) AS r_prop,
        UNIFORM(0, 500000, RANDOM()) AS r_crop,
        UNIFORM(25000, 48000, RANDOM()) AS r_lat,
        UNIFORM(-124000, -70000, RANDOM()) AS r_lon
    FROM TABLE(GENERATOR(ROWCOUNT => 2000))
)
SELECT
    'NOAA-' || LPAD(r.rn::VARCHAR, 5, '0'),
    DATEADD('day', r.r_days, '2022-01-01'::DATE),
    event_types.arr[r.r_type]::VARCHAR,
    states.arr[r.r_state]::VARCHAR,
    counties.arr[r.r_county]::VARCHAR,
    LPAD((MOD(r.rn, 50) + 1)::VARCHAR, 5, '0'),
    ROUND(r.r_mag / 100.0, 2),
    r.r_inj,
    r.r_deaths,
    ROUND(r.r_prop::DECIMAL(14,2), 2),
    ROUND(r.r_crop::DECIMAL(14,2), 2),
    'NOAA-SWDI',
    ROUND(r.r_lat / 1000.0, 5),
    ROUND(r.r_lon / 1000.0, 5)
FROM raw r
CROSS JOIN event_types
CROSS JOIN states
CROSS JOIN counties;


-- ============================================================
-- 2. FRED_ECONOMIC_INDICATORS (~1,500 rows)
-- Marketplace: FRED Series (GZTYZ40XYNE)
-- Enables: Trish #3 (claims vs FRED inflation)
-- ============================================================

CREATE OR REPLACE TABLE FRED_ECONOMIC_INDICATORS (
    INDICATOR_ID        VARCHAR(20)     NOT NULL,
    SERIES_ID           VARCHAR(30)     NOT NULL,
    SERIES_NAME         VARCHAR(100)    NOT NULL,
    OBSERVATION_DATE    DATE            NOT NULL,
    VALUE               DECIMAL(10,4)   NOT NULL,
    UNIT                VARCHAR(20)     NOT NULL,
    FREQUENCY           VARCHAR(10)     NOT NULL,
    CONSTRAINT PK_FRED PRIMARY KEY (INDICATOR_ID)
)
COMMENT = 'FRED Federal Reserve Economic Data proxy — CPI, inflation, unemployment series for financial benchmarking';

INSERT INTO FRED_ECONOMIC_INDICATORS
WITH
series AS (
    SELECT * FROM VALUES
        ('CPIAUCSL','CPI All Urban Consumers','Index','Monthly'),
        ('CUSR0000SETD','CPI Vehicle Repair','Index','Monthly'),
        ('CUSR0000SAM','CPI Medical Care','Index','Monthly'),
        ('CUSR0000SAH1','CPI Shelter','Index','Monthly'),
        ('CUSR0000SETB01','CPI Auto Insurance','Index','Monthly'),
        ('UNRATE','Unemployment Rate','Percent','Monthly'),
        ('FEDFUNDS','Federal Funds Rate','Percent','Monthly'),
        ('DGS10','10-Year Treasury Yield','Percent','Daily'),
        ('MORTGAGE30US','30-Year Mortgage Rate','Percent','Weekly'),
        ('PPIACO','Producer Price Index','Index','Monthly')
    AS t(SID, SNAME, SUNIT, SFREQ)
),
months AS (
    SELECT DATEADD('month', SEQ4(), '2022-01-01'::DATE) AS obs_date,
           ROW_NUMBER() OVER (ORDER BY SEQ4()) AS mrn
    FROM TABLE(GENERATOR(ROWCOUNT => 42))
    WHERE DATEADD('month', SEQ4(), '2022-01-01'::DATE) <= '2025-06-30'::DATE
),
raw AS (
    SELECT
        s.SID, s.SNAME, s.SUNIT, s.SFREQ, m.obs_date,
        ROW_NUMBER() OVER (ORDER BY s.SID, m.obs_date) AS rn
    FROM series s
    CROSS JOIN months m
)
SELECT
    'FRED-' || LPAD(rn::VARCHAR, 5, '0'),
    SID,
    SNAME,
    obs_date,
    CASE
        WHEN SUNIT = 'Index' THEN ROUND(250 + rn * 0.3 + MOD(ABS(HASH(SID || obs_date::VARCHAR)), 50) / 10.0, 4)
        WHEN SID = 'UNRATE' THEN ROUND(3.5 + MOD(ABS(HASH(SID || obs_date::VARCHAR)), 30) / 10.0, 4)
        WHEN SID = 'FEDFUNDS' THEN ROUND(0.5 + MOD(ABS(HASH(SID || obs_date::VARCHAR)), 50) / 10.0, 4)
        WHEN SID = 'DGS10' THEN ROUND(2.0 + MOD(ABS(HASH(SID || obs_date::VARCHAR)), 30) / 10.0, 4)
        WHEN SID = 'MORTGAGE30US' THEN ROUND(4.5 + MOD(ABS(HASH(SID || obs_date::VARCHAR)), 35) / 10.0, 4)
        ELSE ROUND(200 + rn * 0.2 + MOD(ABS(HASH(SID || obs_date::VARCHAR)), 40) / 10.0, 4)
    END,
    SUNIT,
    SFREQ
FROM raw;


-- ============================================================
-- 3. FEMA_RISK_INDEX (~5,000 rows)
-- Marketplace: FEMA National Risk Index (GZSTZKU9FH9, FREE)
-- Enables: Elena #4 (flood zones), Elena #10 (coastal),
--          Sarah #2 (territories), Sarah #9 (Sunbelt)
-- ============================================================

CREATE OR REPLACE TABLE FEMA_RISK_INDEX (
    RECORD_ID           VARCHAR(20)     NOT NULL,
    STATE               VARCHAR(2)      NOT NULL,
    COUNTY              VARCHAR(50)     NOT NULL,
    ZIP_CODE            VARCHAR(10)     NOT NULL,
    OVERALL_RISK_SCORE  DECIMAL(5,2)    NOT NULL,
    FLOOD_RISK          VARCHAR(15)     NOT NULL,
    HURRICANE_RISK      VARCHAR(15)     NOT NULL,
    EARTHQUAKE_RISK     VARCHAR(15)     NOT NULL,
    WILDFIRE_RISK       VARCHAR(15)     NOT NULL,
    TORNADO_RISK        VARCHAR(15)     NOT NULL,
    HAIL_RISK           VARCHAR(15)     NOT NULL,
    COASTAL_ZONE        BOOLEAN         NOT NULL DEFAULT FALSE,
    WIND_ZONE           INT             NOT NULL,
    TERRITORY_TYPE      VARCHAR(20)     NOT NULL,
    POPULATION          INT,
    EXPECTED_ANNUAL_LOSS DECIMAL(14,2),
    CONSTRAINT PK_FEMA PRIMARY KEY (RECORD_ID)
)
COMMENT = 'FEMA National Risk Index proxy — natural hazard risk scores by ZIP for geographic risk assessment and underwriting';

INSERT INTO FEMA_RISK_INDEX
WITH
risk_levels AS (
    SELECT ARRAY_CONSTRUCT('VeryLow','Low','Moderate','High','VeryHigh') AS arr
),
territory_types AS (
    SELECT ARRAY_CONSTRUCT('Coastal','Inland','Mountain','Plains','Urban','Suburban','Rural') AS arr
),
counties AS (
    SELECT ARRAY_CONSTRUCT('Adams','Baker','Clark','Cook','Dallas','Douglas','Edwards',
                           'Franklin','Greene','Hamilton','Harris','Jackson','Jefferson',
                           'Knox','Lincoln','Madison','Marion','Nelson','Orange','Pike') AS arr
),
zip_data AS (
    SELECT DISTINCT ZIP_CODE, STATE FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMERS
    WHERE ZIP_CODE IS NOT NULL
),
numbered_zips AS (
    SELECT ZIP_CODE, STATE, ROW_NUMBER() OVER (ORDER BY STATE, ZIP_CODE) AS rn,
           COUNT(*) OVER () AS total
    FROM zip_data
),
raw AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn,
        UNIFORM(10, 99, RANDOM()) AS r_risk,
        UNIFORM(0, 4, RANDOM()) AS r_flood,
        UNIFORM(0, 4, RANDOM()) AS r_hurr,
        UNIFORM(0, 4, RANDOM()) AS r_eq,
        UNIFORM(0, 4, RANDOM()) AS r_fire,
        UNIFORM(0, 4, RANDOM()) AS r_torn,
        UNIFORM(0, 4, RANDOM()) AS r_hail,
        UNIFORM(1, 100, RANDOM()) AS r_coastal,
        UNIFORM(1, 4, RANDOM()) AS r_wind,
        UNIFORM(0, 6, RANDOM()) AS r_terr,
        UNIFORM(0, 19, RANDOM()) AS r_county,
        UNIFORM(5000, 200000, RANDOM()) AS r_pop,
        UNIFORM(50000, 5000000, RANDOM()) AS r_eal
    FROM TABLE(GENERATOR(ROWCOUNT => 5000))
)
SELECT
    'FEMA-' || LPAD(r.rn::VARCHAR, 5, '0'),
    z.STATE,
    counties.arr[r.r_county]::VARCHAR,
    z.ZIP_CODE,
    ROUND(r.r_risk::DECIMAL(5,2), 2),
    risk_levels.arr[CASE
        WHEN z.STATE IN ('FL','LA','TX','SC','NC') THEN LEAST(4, r.r_flood + 1)
        ELSE r.r_flood END]::VARCHAR,
    risk_levels.arr[CASE
        WHEN z.STATE IN ('FL','TX','LA','NC','SC','GA') THEN LEAST(4, r.r_hurr + 2)
        ELSE r.r_hurr END]::VARCHAR,
    risk_levels.arr[CASE
        WHEN z.STATE IN ('CA','WA','OR') THEN LEAST(4, r.r_eq + 2)
        ELSE r.r_eq END]::VARCHAR,
    risk_levels.arr[CASE
        WHEN z.STATE IN ('CA','CO','AZ','OR') THEN LEAST(4, r.r_fire + 1)
        ELSE r.r_fire END]::VARCHAR,
    risk_levels.arr[r.r_torn]::VARCHAR,
    risk_levels.arr[r.r_hail]::VARCHAR,
    CASE WHEN z.STATE IN ('FL','CA','TX','NC','SC','NJ','MA','NY','VA','GA') AND r.r_coastal <= 35
         THEN TRUE ELSE FALSE END,
    r.r_wind,
    CASE
        WHEN z.STATE IN ('FL','CA','TX','NC','SC','NJ','MA','NY') AND r.r_coastal <= 35 THEN 'Coastal'
        WHEN z.STATE IN ('CO','WY','MT','UT','ID') THEN 'Mountain'
        WHEN z.STATE IN ('KS','NE','IA','OK','SD','ND') THEN 'Plains'
        ELSE territory_types.arr[r.r_terr]::VARCHAR
    END,
    r.r_pop,
    ROUND(r.r_eal::DECIMAL(14,2), 2)
FROM raw r
CROSS JOIN risk_levels
CROSS JOIN territory_types
CROSS JOIN counties
JOIN numbered_zips z ON z.rn = MOD(r.rn - 1, z.total) + 1;


-- ============================================================
-- 4. NAIC_STATUTORY_GUIDELINES (~100 rows)
-- Marketplace: SNL Insurance Regulatory Data (GZT0Z8P3D5A)
-- Enables: Trish #8 (reserve ratios vs NAIC guidelines)
-- ============================================================

CREATE OR REPLACE TABLE NAIC_STATUTORY_GUIDELINES (
    GUIDELINE_ID        VARCHAR(20)     NOT NULL,
    STATE               VARCHAR(2)      NOT NULL,
    LINE_OF_BUSINESS    VARCHAR(40)     NOT NULL,
    MIN_RESERVE_RATIO   DECIMAL(5,2)    NOT NULL,
    MAX_COMBINED_RATIO  DECIMAL(5,2)    NOT NULL,
    MIN_CAPITAL_ADEQUACY DECIMAL(5,2)   NOT NULL,
    MIN_SURPLUS_RATIO   DECIMAL(5,2)    NOT NULL,
    EFFECTIVE_YEAR      INT             NOT NULL,
    SOURCE              VARCHAR(30)     NOT NULL DEFAULT 'NAIC Model Act',
    CONSTRAINT PK_NAIC PRIMARY KEY (GUIDELINE_ID)
)
COMMENT = 'NAIC statutory guideline reference — minimum reserve ratios and combined ratio thresholds by state and LOB';

INSERT INTO NAIC_STATUTORY_GUIDELINES
WITH
states AS (
    SELECT ARRAY_CONSTRUCT('CA','TX','FL','NY','IL','PA','OH','GA','NC','MI',
                           'NJ','VA','WA','AZ','MA','CO','IN','MO','TN','LA') AS arr
),
lobs AS (
    SELECT ARRAY_CONSTRUCT('Personal Auto','Homeowners','Individual Life','Group Health','Commercial Lines') AS arr
),
raw AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn,
        UNIFORM(0, 19, RANDOM()) AS r_state,
        UNIFORM(0, 4, RANDOM()) AS r_lob,
        UNIFORM(50, 75, RANDOM()) AS r_reserve,
        UNIFORM(95, 108, RANDOM()) AS r_combined,
        UNIFORM(150, 300, RANDOM()) AS r_capital,
        UNIFORM(20, 50, RANDOM()) AS r_surplus
    FROM TABLE(GENERATOR(ROWCOUNT => 100))
)
SELECT
    'NAIC-' || LPAD(r.rn::VARCHAR, 4, '0'),
    states.arr[r.r_state]::VARCHAR,
    lobs.arr[r.r_lob]::VARCHAR,
    ROUND(r.r_reserve::DECIMAL(5,2), 2),
    ROUND(r.r_combined::DECIMAL(5,2), 2),
    ROUND(r.r_capital::DECIMAL(5,2), 2),
    ROUND(r.r_surplus::DECIMAL(5,2), 2),
    2025,
    'NAIC Model Act'
FROM raw r
CROSS JOIN states
CROSS JOIN lobs;


-- ############################################################################
-- NEW ANALYTICS TABLES
-- ############################################################################
USE SCHEMA ANALYTICS;

-- ============================================================
-- 5. VEHICLE_DETAILS (~8,000 rows — one per auto policy)
-- Enables: Marcus #4 (auto make/model in claims)
-- ============================================================

CREATE OR REPLACE TABLE VEHICLE_DETAILS (
    VEHICLE_ID          VARCHAR(20)     NOT NULL,
    POLICY_ID           VARCHAR(20)     NOT NULL,
    VIN                 VARCHAR(17)     NOT NULL,
    MAKE                VARCHAR(30)     NOT NULL,
    MODEL               VARCHAR(50)     NOT NULL,
    YEAR                INT             NOT NULL,
    BODY_TYPE           VARCHAR(20)     NOT NULL,
    ENGINE_TYPE         VARCHAR(15)     NOT NULL,
    SAFETY_RATING       INT,
    ANNUAL_MILEAGE      INT,
    GARAGE_ZIP          VARCHAR(10),
    CONSTRAINT PK_VEHICLE PRIMARY KEY (VEHICLE_ID)
)
COMMENT = 'Vehicle details for auto policies — make, model, year, safety rating for claims analysis and risk scoring';

INSERT INTO VEHICLE_DETAILS
WITH
makes_models AS (
    SELECT * FROM VALUES
        ('Toyota','Camry','Sedan'),('Toyota','RAV4','SUV'),('Toyota','Corolla','Sedan'),('Toyota','Highlander','SUV'),
        ('Honda','Civic','Sedan'),('Honda','CR-V','SUV'),('Honda','Accord','Sedan'),('Honda','Pilot','SUV'),
        ('Ford','F-150','Truck'),('Ford','Explorer','SUV'),('Ford','Escape','SUV'),('Ford','Mustang','Coupe'),
        ('Chevrolet','Silverado','Truck'),('Chevrolet','Equinox','SUV'),('Chevrolet','Malibu','Sedan'),('Chevrolet','Tahoe','SUV'),
        ('Tesla','Model 3','Sedan'),('Tesla','Model Y','SUV'),('Tesla','Model S','Sedan'),
        ('BMW','3 Series','Sedan'),('BMW','X3','SUV'),('BMW','X5','SUV'),
        ('Mercedes-Benz','C-Class','Sedan'),('Mercedes-Benz','GLE','SUV'),
        ('Hyundai','Tucson','SUV'),('Hyundai','Elantra','Sedan'),('Hyundai','Santa Fe','SUV'),
        ('Kia','Sportage','SUV'),('Kia','Forte','Sedan'),('Kia','Telluride','SUV'),
        ('Nissan','Rogue','SUV'),('Nissan','Altima','Sedan'),('Nissan','Sentra','Sedan'),
        ('Subaru','Outback','Wagon'),('Subaru','Forester','SUV'),
        ('Jeep','Grand Cherokee','SUV'),('Jeep','Wrangler','SUV'),
        ('Ram','1500','Truck'),('Ram','2500','Truck'),
        ('GMC','Sierra','Truck')
    AS t(VMAKE, VMODEL, VBODY)
),
engine_types AS (
    SELECT ARRAY_CONSTRUCT('Gasoline','Gasoline','Gasoline','Gasoline','Gasoline',
                           'Hybrid','Hybrid','Electric','Diesel','Diesel') AS arr
),
auto_policies AS (
    SELECT POLICY_ID, CUSTOMER_ID,
           ROW_NUMBER() OVER (ORDER BY POLICY_ID) AS rn,
           COUNT(*) OVER () AS total
    FROM POLICIES WHERE POLICY_TYPE IN ('PersonalAuto','CommercialAuto')
),
makes_numbered AS (
    SELECT VMAKE, VMODEL, VBODY,
           ROW_NUMBER() OVER (ORDER BY VMAKE, VMODEL) AS mrn,
           COUNT(*) OVER () AS mtotal
    FROM makes_models
),
raw AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn,
        UNIFORM(2015, 2025, RANDOM()) AS r_year,
        UNIFORM(0, 9, RANDOM()) AS r_engine,
        UNIFORM(1, 5, RANDOM()) AS r_safety,
        UNIFORM(5000, 25000, RANDOM()) AS r_miles
    FROM TABLE(GENERATOR(ROWCOUNT => 8000))
)
SELECT
    'VEH-' || LPAD(r.rn::VARCHAR, 5, '0'),
    ap.POLICY_ID,
    UPPER(SUBSTR(MD5(ap.POLICY_ID || r.rn::VARCHAR), 1, 17)),
    m.VMAKE,
    m.VMODEL,
    r.r_year,
    m.VBODY,
    engine_types.arr[r.r_engine]::VARCHAR,
    r.r_safety,
    r.r_miles,
    (SELECT c.ZIP_CODE FROM CUSTOMERS c WHERE c.CUSTOMER_ID = ap.CUSTOMER_ID LIMIT 1)
FROM raw r
CROSS JOIN engine_types
JOIN auto_policies ap ON ap.rn = MOD(r.rn - 1, ap.total) + 1
JOIN makes_numbered m ON m.mrn = MOD(r.rn - 1, m.mtotal) + 1;


-- ============================================================
-- 6. CUSTOMER_ATTRIBUTE_HISTORY (~10,000 rows)
-- Enables: Sid #8 (risk tier drift after claim)
-- ============================================================

CREATE OR REPLACE TABLE CUSTOMER_ATTRIBUTE_HISTORY (
    HISTORY_ID          VARCHAR(20)     NOT NULL,
    CUSTOMER_ID         VARCHAR(20)     NOT NULL,
    ATTRIBUTE_NAME      VARCHAR(30)     NOT NULL,
    OLD_VALUE           VARCHAR(50),
    NEW_VALUE           VARCHAR(50)     NOT NULL,
    CHANGE_DATE         DATE            NOT NULL,
    CHANGE_REASON       VARCHAR(50)     NOT NULL,
    TRIGGERED_BY        VARCHAR(20)     NOT NULL,
    CONSTRAINT PK_CUST_HIST PRIMARY KEY (HISTORY_ID)
)
COMMENT = 'Customer attribute change history tracking risk tier, segment, and credit score changes over time';

INSERT INTO CUSTOMER_ATTRIBUTE_HISTORY
WITH
attributes AS (
    SELECT ARRAY_CONSTRUCT('RISK_TIER','RISK_TIER','RISK_TIER','SEGMENT','SEGMENT','CREDIT_SCORE','CREDIT_SCORE') AS arr
),
risk_tiers AS (
    SELECT ARRAY_CONSTRUCT('Low','Medium','High','Critical') AS arr
),
segments AS (
    SELECT ARRAY_CONSTRUCT('Budget','Standard','Premium') AS arr
),
reasons AS (
    SELECT ARRAY_CONSTRUCT('Claim Filed','Annual Review','Payment Default','Credit Update',
                           'Policy Renewal','Risk Reassessment','Life Event') AS arr
),
triggers AS (
    SELECT ARRAY_CONSTRUCT('Claim','Renewal','AnnualReview','SystemUpdate','AgentRequest') AS arr
),
cust_data AS (
    SELECT CUSTOMER_ID, RISK_TIER, SEGMENT, CREDIT_SCORE, CUSTOMER_SINCE,
           ROW_NUMBER() OVER (ORDER BY CUSTOMER_ID) AS rn,
           COUNT(*) OVER () AS total
    FROM INSURANCE_AI_HUB.ANALYTICS.CUSTOMERS
),
raw AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn,
        UNIFORM(0, 6, RANDOM()) AS r_attr,
        UNIFORM(0, 3, RANDOM()) AS r_old_rt,
        UNIFORM(0, 3, RANDOM()) AS r_new_rt,
        UNIFORM(0, 2, RANDOM()) AS r_old_seg,
        UNIFORM(0, 2, RANDOM()) AS r_new_seg,
        UNIFORM(300, 850, RANDOM()) AS r_old_cs,
        UNIFORM(300, 850, RANDOM()) AS r_new_cs,
        UNIFORM(30, 1200, RANDOM()) AS r_days,
        UNIFORM(0, 6, RANDOM()) AS r_reason,
        UNIFORM(0, 4, RANDOM()) AS r_trigger
    FROM TABLE(GENERATOR(ROWCOUNT => 10000))
)
SELECT
    'CHIST-' || LPAD(r.rn::VARCHAR, 6, '0'),
    c.CUSTOMER_ID,
    attributes.arr[r.r_attr]::VARCHAR,
    CASE attributes.arr[r.r_attr]::VARCHAR
        WHEN 'RISK_TIER' THEN risk_tiers.arr[r.r_old_rt]::VARCHAR
        WHEN 'SEGMENT' THEN segments.arr[r.r_old_seg]::VARCHAR
        ELSE r.r_old_cs::VARCHAR
    END,
    CASE attributes.arr[r.r_attr]::VARCHAR
        WHEN 'RISK_TIER' THEN risk_tiers.arr[r.r_new_rt]::VARCHAR
        WHEN 'SEGMENT' THEN segments.arr[r.r_new_seg]::VARCHAR
        ELSE r.r_new_cs::VARCHAR
    END,
    DATEADD('day', r.r_days, c.CUSTOMER_SINCE),
    reasons.arr[r.r_reason]::VARCHAR,
    triggers.arr[r.r_trigger]::VARCHAR
FROM raw r
CROSS JOIN attributes
CROSS JOIN risk_tiers
CROSS JOIN segments
CROSS JOIN reasons
CROSS JOIN triggers
JOIN cust_data c ON c.rn = MOD(r.rn - 1, c.total) + 1;


-- ============================================================
-- 7. CLAIM_ACTIVITY_LOG (~15,000 rows)
-- Enables: Marcus #5 (adjuster inactivity detection)
-- ============================================================

CREATE OR REPLACE TABLE CLAIM_ACTIVITY_LOG (
    ACTIVITY_ID         VARCHAR(20)     NOT NULL,
    CLAIM_ID            VARCHAR(20)     NOT NULL,
    ADJUSTER_ID         VARCHAR(20)     NOT NULL,
    ACTIVITY_DATE       TIMESTAMP_NTZ   NOT NULL,
    ACTIVITY_TYPE       VARCHAR(30)     NOT NULL,
    NOTES               VARCHAR(200),
    DURATION_MINUTES    INT,
    CONSTRAINT PK_CLAIM_ACT PRIMARY KEY (ACTIVITY_ID)
)
COMMENT = 'Claim adjuster activity log with timestamped events for workload monitoring and SLA tracking';

INSERT INTO CLAIM_ACTIVITY_LOG
WITH
activity_types AS (
    SELECT ARRAY_CONSTRUCT('InitialReview','ContactClaimant','RequestDocuments','FieldInspection',
                           'DamageAssessment','CoverageVerification','ApprovalSubmission','DenialDraft',
                           'EscalationRefer','SupervisorReview','PaymentAuthorization','CloseFile',
                           'FollowUpCall','ThirdPartyContact','LegalReferral') AS arr
),
notes_arr AS (
    SELECT ARRAY_CONSTRUCT(
        'Initial review completed, coverage confirmed.',
        'Left voicemail with claimant, awaiting callback.',
        'Requested repair estimates and police report.',
        'Scheduled field inspection for property damage.',
        'Damage assessment report received from vendor.',
        'Verified policy coverage and endorsements.',
        'Submitted approval request to supervisor.',
        'Drafted denial letter — exclusion applies.',
        'Escalated to senior adjuster for review.',
        'Supervisor approved settlement amount.',
        'Payment authorization processed.',
        'File closed — all documentation complete.',
        'Follow-up call — claimant confirmed receipt.',
        'Contacted body shop for supplemental estimate.',
        'Referred to legal for litigation review.'
    ) AS arr
),
claim_data AS (
    SELECT CLAIM_ID, ADJUSTER_ID, CLAIM_DATE,
           ROW_NUMBER() OVER (ORDER BY CLAIM_ID) AS rn,
           COUNT(*) OVER () AS total
    FROM CLAIMS WHERE ADJUSTER_ID IS NOT NULL
),
raw AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn,
        UNIFORM(0, 14, RANDOM()) AS r_type,
        UNIFORM(0, 14, RANDOM()) AS r_note,
        UNIFORM(0, 90, RANDOM()) AS r_dayoff,
        UNIFORM(0, 86400, RANDOM()) AS r_secoff,
        UNIFORM(5, 180, RANDOM()) AS r_dur
    FROM TABLE(GENERATOR(ROWCOUNT => 15000))
)
SELECT
    'ACT-' || LPAD(r.rn::VARCHAR, 6, '0'),
    cd.CLAIM_ID,
    cd.ADJUSTER_ID,
    DATEADD('second', r.r_secoff, DATEADD('day', r.r_dayoff, cd.CLAIM_DATE))::TIMESTAMP_NTZ,
    activity_types.arr[r.r_type]::VARCHAR,
    notes_arr.arr[r.r_note]::VARCHAR,
    r.r_dur
FROM raw r
CROSS JOIN activity_types
CROSS JOIN notes_arr
JOIN claim_data cd ON cd.rn = MOD(r.rn - 1, cd.total) + 1;


-- ############################################################################
-- COLUMN ADDITION: CLAIMS.FRICTION_REASON
-- Enables: Marcus #2 (top friction reasons by region)
-- ############################################################################

ALTER TABLE ANALYTICS.CLAIMS ADD COLUMN IF NOT EXISTS FRICTION_REASON VARCHAR(30);

UPDATE ANALYTICS.CLAIMS
SET FRICTION_REASON = CASE MOD(ABS(HASH(CLAIM_ID || 'fr')), 6)
    WHEN 0 THEN 'Documentation Delay'
    WHEN 1 THEN 'Adjuster Reassignment'
    WHEN 2 THEN 'Dispute Resolution'
    WHEN 3 THEN 'Third Party Response'
    WHEN 4 THEN 'System Error'
    ELSE 'Policy Verification'
END
WHERE FRICTION_SCORE > 5.0;

UPDATE ANALYTICS.CLAIMS
SET FRICTION_REASON = CASE MOD(ABS(HASH(CLAIM_ID || 'fr2')), 3)
    WHEN 0 THEN 'Documentation Delay'
    WHEN 1 THEN 'Third Party Response'
    ELSE 'Policy Verification'
END
WHERE FRICTION_SCORE BETWEEN 3.0 AND 5.0 AND FRICTION_REASON IS NULL;


-- ############################################################################
-- VERIFICATION
-- ############################################################################

SELECT 'NOAA_STORM_EVENTS' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM EXTERNAL_DATA.NOAA_STORM_EVENTS
UNION ALL SELECT 'FRED_ECONOMIC_INDICATORS', COUNT(*) FROM EXTERNAL_DATA.FRED_ECONOMIC_INDICATORS
UNION ALL SELECT 'FEMA_RISK_INDEX', COUNT(*) FROM EXTERNAL_DATA.FEMA_RISK_INDEX
UNION ALL SELECT 'NAIC_STATUTORY_GUIDELINES', COUNT(*) FROM EXTERNAL_DATA.NAIC_STATUTORY_GUIDELINES
UNION ALL SELECT 'VEHICLE_DETAILS', COUNT(*) FROM ANALYTICS.VEHICLE_DETAILS
UNION ALL SELECT 'CUSTOMER_ATTRIBUTE_HISTORY', COUNT(*) FROM ANALYTICS.CUSTOMER_ATTRIBUTE_HISTORY
UNION ALL SELECT 'CLAIM_ACTIVITY_LOG', COUNT(*) FROM ANALYTICS.CLAIM_ACTIVITY_LOG
UNION ALL SELECT 'CLAIMS (FRICTION_REASON filled)', SUM(CASE WHEN FRICTION_REASON IS NOT NULL THEN 1 ELSE 0 END) FROM ANALYTICS.CLAIMS;
