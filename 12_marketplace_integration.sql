-- ============================================================
-- INSURANCE AI HUB (E.D.I.E.) - Real Marketplace Data Integration
-- Phase 12: Integration views over SNOWFLAKE_PUBLIC_DATA_FREE
-- + PROPERTY_CHARACTERISTICS table for underwriting
-- ============================================================
--
-- DATA SOURCE: SNOWFLAKE_PUBLIC_DATA_FREE (already installed)
-- Contains REAL, auto-refreshing data from:
--   - US Census Bureau (American Community Survey)
--   - Bureau of Labor Statistics (CPI, inflation)
--   - FEMA (disasters, NFIP flood claims/policies)
--   - Data Commons (demographics, economics)
--   - And 90+ other public sources
--
-- This script creates:
--   1. EXTERNAL_DATA.STATE_FIPS_LOOKUP — State FIPS ↔ abbreviation mapping
--   2. EXTERNAL_DATA.V_CPI_INSURANCE_INDICES — Real BLS CPI data for insurance LOBs
--   3. EXTERNAL_DATA.V_FEMA_DISASTER_HISTORY — Real FEMA disaster declarations
--   4. EXTERNAL_DATA.V_FEMA_FLOOD_CLAIMS — Real NFIP flood claims with property data
--   5. EXTERNAL_DATA.V_FEMA_FLOOD_POLICIES — Real NFIP policies with construction/risk data
--   6. EXTERNAL_DATA.V_ZIP_DEMOGRAPHICS — Real Census ACS demographics by ZIP
--   7. ANALYTICS.PROPERTY_CHARACTERISTICS — Property/construction data for Home/Commercial
--
-- All views join directly to insurance tables via STATE, ZIP_CODE, DATE
-- ============================================================

USE DATABASE INSURANCE_AI_HUB;
USE WAREHOUSE INSURANCE_AI_HUB_WH;

-- Keep EXTERNAL_DATA schema, but replace synthetic tables with real views
CREATE SCHEMA IF NOT EXISTS EXTERNAL_DATA
    COMMENT = 'Integration layer over real Marketplace data (Snowflake Public Data) with views joinable to insurance tables via STATE, ZIP_CODE, DATE';


-- ############################################################################
-- 1. STATE FIPS LOOKUP — Bridge between our 2-letter STATE and Marketplace GEO_IDs
-- ############################################################################
USE SCHEMA EXTERNAL_DATA;

CREATE OR REPLACE TABLE STATE_FIPS_LOOKUP (
    STATE_ABBREV    VARCHAR(2)  NOT NULL,
    STATE_NAME      VARCHAR(50) NOT NULL,
    STATE_GEO_ID    VARCHAR(20) NOT NULL,
    STATE_FIPS      VARCHAR(2)  NOT NULL,
    CONSTRAINT PK_STATE_FIPS PRIMARY KEY (STATE_ABBREV)
)
COMMENT = 'State FIPS code lookup bridging 2-letter abbreviations to Snowflake Public Data GEO_IDs';

INSERT INTO STATE_FIPS_LOOKUP
SELECT 
    gc.VALUE AS STATE_ABBREV,
    gi.GEO_NAME AS STATE_NAME,
    gi.GEO_ID AS STATE_GEO_ID,
    REPLACE(gi.GEO_ID, 'geoId/', '') AS STATE_FIPS
FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_INDEX gi
JOIN SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_CHARACTERISTICS gc
    ON gi.GEO_ID = gc.GEO_ID AND gc.RELATIONSHIP_TYPE = 'state_abbreviation'
WHERE gi.LEVEL = 'State' AND gi.GEO_ID LIKE 'geoId/%';


-- ############################################################################
-- 2. V_CPI_INSURANCE_INDICES — Real BLS CPI data relevant to insurance
-- Auto insurance, medical care, shelter, all items — full history
-- ############################################################################

CREATE OR REPLACE VIEW V_CPI_INSURANCE_INDICES AS
SELECT 
    bls.DATE AS OBSERVATION_DATE,
    bls.VARIABLE AS SERIES_ID,
    bls.VARIABLE_NAME AS SERIES_NAME,
    bls.VALUE AS INDEX_VALUE,
    bls.GEO_ID,
    CASE 
        WHEN bls.VARIABLE LIKE '%Motor_vehicle_insurance%' THEN 'Auto Insurance'
        WHEN bls.VARIABLE LIKE '%Motor_vehicle_maintenance%' OR bls.VARIABLE LIKE '%Motor_vehicle_parts%' THEN 'Vehicle Repair'
        WHEN bls.VARIABLE LIKE '%Medical_care%' THEN 'Medical Care'
        WHEN bls.VARIABLE LIKE '%Shelter%' OR bls.VARIABLE LIKE '%shelter%' THEN 'Shelter'
        WHEN bls.VARIABLE LIKE '%All_items%' AND bls.VARIABLE NOT LIKE '%less%' THEN 'All Items'
        WHEN bls.VARIABLE LIKE '%Tenants%' OR bls.VARIABLE LIKE '%renters%' THEN 'Renters Insurance'
        ELSE 'Other'
    END AS INSURANCE_CATEGORY
FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.BUREAU_OF_LABOR_STATISTICS_PRICE_TIMESERIES bls
WHERE bls.VARIABLE LIKE ANY (
    'CPI:_Motor_vehicle_insurance%Monthly%',
    'CPI:_Motor_vehicle_maintenance%Monthly%',
    'CPI:_Motor_vehicle_parts%Monthly%',
    'CPI:_Medical_care,%Monthly%',
    'CPI:_Medical_care_services%Monthly%',
    'CPI:_Shelter%Monthly%',
    'CPI:_All_items,%Monthly%',
    'CPI:_Tenants%Monthly%'
)
AND bls.VARIABLE LIKE '%Not_seasonally_adjusted%'
AND bls.GEO_ID = 'country/USA'
COMMENT = 'Real BLS CPI indices for insurance-relevant categories (auto insurance, medical, shelter, all items) — full history, monthly';


-- ############################################################################
-- 3. V_FEMA_DISASTER_HISTORY — Real FEMA disaster declarations with geography
-- Joins to insurance tables via STATE
-- ############################################################################

CREATE OR REPLACE VIEW V_FEMA_DISASTER_HISTORY AS
SELECT 
    dd.DISASTER_ID,
    dd.FEMA_DESIGNATED_AREA,
    sl.STATE_ABBREV AS STATE,
    dd.COUNTY_GEO_ID,
    dd.FEMA_REGION_ID,
    dd.TRIBAL_REQUEST,
    dd.DECLARED_PROGRAMS_DETAILED,
    dd.DESIGNATED_DATE,
    dd.ENTRY_DATE,
    dd.UPDATE_DATE,
    dd.CLOSEOUT_DATE,
    di.DISASTER_DECLARATION_NAME,
    di.DISASTER_DECLARATION_TYPE,
    di.DISASTER_TYPE,
    di.DISASTER_DECLARATION_DATE,
    di.DISASTER_BEGIN_DATE,
    di.DISASTER_END_DATE,
    di.DECLARED_PROGRAMS,
    di.APPROVED_INDIVIDUAL_ASSISTANCE_APPLICATIONS,
    di.APPROVED_INDIVIDUAL_AND_HOUSEHOLDS_PROGRAM_AMOUNT AS IHP_AMOUNT,
    di.APPROVED_HOUSING_ASSISTANCE_AMOUNT AS HA_AMOUNT,
    di.APPROVED_OTHER_NEEDS_ASSISTANCE_AMOUNT AS ONA_AMOUNT,
    di.STATE_OBLIGATED_PUBLIC_ASSISTANCE_AMOUNT AS PA_AMOUNT,
    di.STATE_OBLIGATED_HAZARD_MITIGATION_GRANT_PROGRAM_AMOUNT AS HM_AMOUNT
FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.FEMA_DISASTER_DECLARATION_AREAS_INDEX dd
JOIN SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.FEMA_DISASTER_DECLARATION_INDEX di
    ON dd.DISASTER_ID = di.DISASTER_ID
LEFT JOIN STATE_FIPS_LOOKUP sl
    ON dd.STATE_GEO_ID = sl.STATE_GEO_ID
COMMENT = 'Real FEMA disaster declarations with incident types, dates, and approved assistance amounts — joinable to insurance tables via STATE';


-- ############################################################################
-- 4. V_FEMA_FLOOD_CLAIMS — Real NFIP flood claims with property details
-- Rich property data: building type, construction date, flood zone, damage amounts
-- ############################################################################

CREATE OR REPLACE VIEW V_FEMA_FLOOD_CLAIMS AS
SELECT 
    fc.NATIONAL_FLOOD_INSURANCE_PROGRAM_CLAIM_ID AS CLAIM_ID,
    sl.STATE_ABBREV AS STATE,
    REPLACE(fc.ZIP_GEO_ID, 'zip/', '') AS ZIP_CODE,
    fc.BUILDING_TYPE,
    fc.OCCUPANCY_TYPE,
    fc.UNITS,
    fc.FLOOD_EVENT,
    fc.FLOOD_TYPE,
    fc.FLOOD_WATER_DURATION_HOURS,
    fc.FLOOD_WATER_DEPTH,
    fc.CAUSE_OF_DAMAGE,
    fc.DATE_OF_LOSS,
    fc.BUILDING_PROPERTY_VALUE,
    fc.BUILDING_DAMAGE_AMOUNT,
    fc.AMOUNT_PAID_ON_BUILDING_CLAIM,
    fc.NET_BUILDING_PAYMENT_AMOUNT,
    fc.CONTENTS_PROPERTY_VALUE,
    fc.CONTENTS_DAMAGE_AMOUNT,
    fc.AMOUNT_PAID_ON_CONTENTS_CLAIM,
    fc.TOTAL_BUILDING_INSURANCE_COVERAGE,
    fc.BUILDING_DEDUCTIBLE,
    fc.ORIGINAL_CONSTRUCTION_DATE,
    fc.NUMBER_OF_FLOORS,
    fc.BASE_FLOOD_ELEVATION,
    fc.LOWEST_FLOOR_ELEVATION,
    fc.ELEVATION_DIFFERENCE,
    fc.CURRENT_FLOOD_ZONE,
    fc.POLICY_RATED_FLOOD_ZONE,
    fc.BASEMENT_ENCLOSURE_CRAWLSPACE,
    fc.LATITUDE,
    fc.LONGITUDE
FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.FEMA_NATIONAL_FLOOD_INSURANCE_PROGRAM_CLAIM_INDEX fc
LEFT JOIN STATE_FIPS_LOOKUP sl ON fc.STATE_GEO_ID = sl.STATE_GEO_ID
COMMENT = 'Real FEMA NFIP flood claims with property construction details, flood zones, elevation data, and damage amounts';


-- ############################################################################
-- 5. V_FEMA_FLOOD_POLICIES — Real NFIP policies with construction/risk data
-- Construction date, building type, flood zone, replacement cost, elevation
-- ############################################################################

CREATE OR REPLACE VIEW V_FEMA_FLOOD_POLICIES AS
SELECT 
    fp.NATIONAL_FLOOD_INSURANCE_PROGRAM_POLICY_ID AS POLICY_ID,
    sl.STATE_ABBREV AS STATE,
    REPLACE(fp.ZIP_GEO_ID, 'zip/', '') AS ZIP_CODE,
    fp.CITY,
    fp.BUILDING_TYPE,
    fp.OCCUPANCY_TYPE,
    fp.NUMBER_OF_FLOORS,
    fp.ORIGINAL_CONSTRUCTION_DATE,
    fp.BUILDING_REPLACEMENT_COST,
    fp.TOTAL_BUILDING_INSURANCE_COVERAGE,
    fp.BUILDING_DEDUCTIBLE,
    fp.TOTAL_CONTENTS_INSURANCE_COVERAGE,
    fp.CONTENTS_DEDUCTIBLE,
    fp.TOTAL_INSURANCE_PREMIUM_OF_THE_POLICY AS PREMIUM,
    fp.POLICY_COST,
    fp.INSURANCE_TO_VALUE_RATIO,
    fp.CURRENT_FLOOD_ZONE,
    fp.POLICY_RATED_FLOOD_ZONE,
    fp.BASE_FLOOD_ELEVATION,
    fp.LOWEST_FLOOR_ELEVATION,
    fp.ELEVATION_DIFFERENCE,
    fp.BASEMENT_ENCLOSURE_CRAWLSPACE,
    fp.COMMUNITY_RATING_SYSTEM_CLASS,
    fp.POLICY_EFFECTIVE_DATE,
    fp.POLICY_TERMINATION_DATE,
    fp.POLICY_CANCELLATION_DATE,
    fp.POLICY_CANCELLATION_REASON,
    fp.POLICY_RATING_METHOD,
    fp.SUBSIDIZATION_TYPE,
    fp.LATITUDE,
    fp.LONGITUDE
FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.FEMA_NATIONAL_FLOOD_INSURANCE_PROGRAM_POLICY_INDEX fp
LEFT JOIN STATE_FIPS_LOOKUP sl ON fp.STATE_GEO_ID = sl.STATE_GEO_ID
COMMENT = 'Real FEMA NFIP policies with construction details, flood zones, replacement costs, and premium data';


-- ############################################################################
-- 6. V_ZIP_DEMOGRAPHICS — Real Census ACS demographics by ZIP
-- Median income, population, housing — the foundation for geographic risk rating
-- ############################################################################

CREATE OR REPLACE VIEW V_ZIP_DEMOGRAPHICS AS
SELECT 
    REPLACE(acs.GEO_ID, 'zip/', '') AS ZIP_CODE,
    acs.VARIABLE,
    acs.VARIABLE_NAME,
    acs.DATE AS SURVEY_DATE,
    acs.VALUE,
    acs.UNIT
FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.AMERICAN_COMMUNITY_SURVEY_TIMESERIES acs
WHERE acs.GEO_ID LIKE 'zip/%'
COMMENT = 'Real Census ACS demographic data by ZIP code — income, population, housing, education for geographic risk assessment';


-- ############################################################################
-- 7. PROPERTY_CHARACTERISTICS — Construction data for Home/Commercial policies
-- This IS internal underwriting data (collected at policy bind), not external
-- ############################################################################
USE SCHEMA ANALYTICS;

CREATE OR REPLACE TABLE PROPERTY_CHARACTERISTICS (
    PROPERTY_ID         VARCHAR(20)     NOT NULL,
    POLICY_ID           VARCHAR(20)     NOT NULL,
    CONSTRUCTION_TYPE   VARCHAR(30)     NOT NULL,
    YEAR_BUILT          INT             NOT NULL,
    SQUARE_FOOTAGE      INT             NOT NULL,
    NUMBER_OF_STORIES   INT             NOT NULL,
    ROOF_TYPE           VARCHAR(30)     NOT NULL,
    FOUNDATION_TYPE     VARCHAR(30)     NOT NULL,
    HEATING_TYPE        VARCHAR(20),
    ELECTRICAL_UPDATE_YEAR INT,
    PLUMBING_UPDATE_YEAR INT,
    ROOF_UPDATE_YEAR    INT,
    FIRE_PROTECTION     VARCHAR(20)     NOT NULL,
    DISTANCE_FIRE_STATION_MI DECIMAL(4,1),
    FLOOD_ZONE          VARCHAR(15),
    PROPERTY_USE        VARCHAR(30)     NOT NULL,
    REPLACEMENT_COST    DECIMAL(14,2)   NOT NULL,
    CONSTRAINT PK_PROPERTY PRIMARY KEY (PROPERTY_ID)
)
COMMENT = 'Property construction characteristics for Home/Commercial policies — masonry type, roof, year built, flood zone for underwriting risk assessment';

INSERT INTO PROPERTY_CHARACTERISTICS
WITH
construction_types AS (
    -- Real US housing stock distribution: ~30% masonry/brick, ~55% wood frame, ~10% steel/concrete, ~5% mixed
    SELECT ARRAY_CONSTRUCT('Wood Frame','Wood Frame','Wood Frame','Wood Frame','Wood Frame','Wood Frame',
                           'Masonry','Masonry','Masonry','Masonry',
                           'Steel Frame','Reinforced Concrete','Mixed','Log','Manufactured') AS arr
),
roof_types AS (
    SELECT ARRAY_CONSTRUCT('Asphalt Shingle','Asphalt Shingle','Asphalt Shingle','Asphalt Shingle',
                           'Metal','Metal','Tile','Tile','Slate','Flat/Built-Up','TPO Membrane','Wood Shake') AS arr
),
foundation_types AS (
    SELECT ARRAY_CONSTRUCT('Slab','Slab','Slab','Crawl Space','Crawl Space','Basement','Basement',
                           'Pier and Beam','Pier and Beam','Raised Foundation') AS arr
),
heating_types AS (
    SELECT ARRAY_CONSTRUCT('Forced Air','Forced Air','Forced Air','Heat Pump','Heat Pump',
                           'Radiant','Boiler','Electric Baseboard','Geothermal','None') AS arr
),
fire_protection AS (
    SELECT ARRAY_CONSTRUCT('Sprinkler','Sprinkler','Smoke Detector','Smoke Detector','Smoke Detector',
                           'Alarm System','Alarm System','Fire Extinguisher','None') AS arr
),
flood_zones AS (
    SELECT ARRAY_CONSTRUCT('X','X','X','X','X','X','A','AE','AH','VE','X500','B','C') AS arr
),
property_uses AS (
    SELECT ARRAY_CONSTRUCT('Primary Residence','Primary Residence','Primary Residence','Primary Residence',
                           'Rental','Rental','Vacation','Office','Retail','Warehouse','Mixed Use') AS arr
),
home_comm_policies AS (
    SELECT p.POLICY_ID, p.COVERAGE_AMOUNT, p.ISSUING_STATE, p.POLICY_TYPE,
           ROW_NUMBER() OVER (ORDER BY p.POLICY_ID) AS rn,
           COUNT(*) OVER () AS total
    FROM POLICIES p
    WHERE p.POLICY_TYPE IN ('Homeowners','CommercialMultiPeril')
),
raw AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn,
        UNIFORM(0, 14, RANDOM()) AS r_const,
        UNIFORM(1940, 2024, RANDOM()) AS r_year,
        UNIFORM(800, 6000, RANDOM()) AS r_sqft,
        UNIFORM(1, 3, RANDOM()) AS r_stories,
        UNIFORM(0, 11, RANDOM()) AS r_roof,
        UNIFORM(0, 9, RANDOM()) AS r_found,
        UNIFORM(0, 9, RANDOM()) AS r_heat,
        UNIFORM(0, 8, RANDOM()) AS r_fire,
        UNIFORM(0, 12, RANDOM()) AS r_flood,
        UNIFORM(0, 10, RANDOM()) AS r_use,
        UNIFORM(1, 80, RANDOM()) AS r_dist,
        UNIFORM(1970, 2025, RANDOM()) AS r_elec,
        UNIFORM(1970, 2025, RANDOM()) AS r_plumb,
        UNIFORM(1990, 2025, RANDOM()) AS r_roofyr
    FROM TABLE(GENERATOR(ROWCOUNT => 4000))
)
SELECT
    'PROP-' || LPAD(r.rn::VARCHAR, 5, '0'),
    hcp.POLICY_ID,
    construction_types.arr[r.r_const]::VARCHAR,
    r.r_year,
    CASE WHEN hcp.POLICY_TYPE = 'CommercialMultiPeril' THEN r.r_sqft * 3 ELSE r.r_sqft END,
    CASE WHEN hcp.POLICY_TYPE = 'CommercialMultiPeril' THEN LEAST(r.r_stories + 1, 5) ELSE r.r_stories END,
    roof_types.arr[r.r_roof]::VARCHAR,
    foundation_types.arr[r.r_found]::VARCHAR,
    heating_types.arr[r.r_heat]::VARCHAR,
    CASE WHEN r.r_elec >= r.r_year THEN r.r_elec ELSE r.r_year + 10 END,
    CASE WHEN r.r_plumb >= r.r_year THEN r.r_plumb ELSE r.r_year + 15 END,
    CASE WHEN r.r_roofyr >= r.r_year THEN r.r_roofyr ELSE r.r_year + 20 END,
    fire_protection.arr[r.r_fire]::VARCHAR,
    ROUND(r.r_dist / 10.0, 1),
    flood_zones.arr[r.r_flood]::VARCHAR,
    CASE WHEN hcp.POLICY_TYPE = 'CommercialMultiPeril'
         THEN property_uses.arr[GREATEST(7, r.r_use)]::VARCHAR
         ELSE property_uses.arr[LEAST(6, r.r_use)]::VARCHAR END,
    hcp.COVERAGE_AMOUNT
FROM raw r
CROSS JOIN construction_types CROSS JOIN roof_types CROSS JOIN foundation_types
CROSS JOIN heating_types CROSS JOIN fire_protection CROSS JOIN flood_zones CROSS JOIN property_uses
JOIN home_comm_policies hcp ON hcp.rn = MOD(r.rn - 1, hcp.total) + 1;


-- ############################################################################
-- DROP SYNTHETIC TABLES (replaced by real Marketplace views)
-- Keep NOAA_STORM_EVENTS and NAIC_STATUTORY_GUIDELINES (no real equivalent installed)
-- Keep FEMA_RISK_INDEX (supplement until FEMA NRI Marketplace listing installed)
-- ############################################################################

DROP TABLE IF EXISTS EXTERNAL_DATA.FRED_ECONOMIC_INDICATORS;
-- FRED replaced by V_CPI_INSURANCE_INDICES (real BLS data)

-- Note: NOAA_STORM_EVENTS, FEMA_RISK_INDEX, NAIC_STATUTORY_GUIDELINES retained
-- as synthetic supplements until their Marketplace equivalents are installed.
-- When you install:
--   GZSTZJUPD05 (NOAA) → drop NOAA_STORM_EVENTS
--   GZSTZKU9FH9 (FEMA NRI) → drop FEMA_RISK_INDEX
--   GZT0Z8P3D5A (SNL Insurance) → drop NAIC_STATUTORY_GUIDELINES


-- ############################################################################
-- VERIFICATION
-- ############################################################################

-- Real data counts
SELECT 'V_CPI_INSURANCE_INDICES (real)' AS SOURCE, COUNT(*) AS ROW_COUNT
FROM EXTERNAL_DATA.V_CPI_INSURANCE_INDICES
UNION ALL
SELECT 'V_FEMA_DISASTER_HISTORY (real)', COUNT(*)
FROM EXTERNAL_DATA.V_FEMA_DISASTER_HISTORY
UNION ALL
SELECT 'V_FEMA_FLOOD_CLAIMS (real)', COUNT(*)
FROM EXTERNAL_DATA.V_FEMA_FLOOD_CLAIMS
UNION ALL
SELECT 'V_FEMA_FLOOD_POLICIES (real)', COUNT(*)
FROM EXTERNAL_DATA.V_FEMA_FLOOD_POLICIES
UNION ALL
SELECT 'STATE_FIPS_LOOKUP', COUNT(*)
FROM EXTERNAL_DATA.STATE_FIPS_LOOKUP
UNION ALL
SELECT 'PROPERTY_CHARACTERISTICS', COUNT(*)
FROM ANALYTICS.PROPERTY_CHARACTERISTICS;

-- Sample join: Insurance claims vs real FEMA disasters in same state/month
-- SELECT c.CLAIM_ID, c.CLAIM_DATE, c.CAUSE_OF_LOSS, c.CLAIM_AMOUNT,
--        d.DISASTER_TITLE, d.INCIDENT_TYPE, d.DECLARATION_DATE
-- FROM ANALYTICS.CLAIMS c
-- JOIN ANALYTICS.POLICIES p ON c.POLICY_ID = p.POLICY_ID
-- JOIN EXTERNAL_DATA.V_FEMA_DISASTER_HISTORY d 
--     ON p.ISSUING_STATE = d.STATE
--     AND c.CLAIM_DATE BETWEEN d.INCIDENT_BEGIN_DATE AND COALESCE(d.INCIDENT_END_DATE, d.DECLARATION_DATE + 30)
-- WHERE c.CATASTROPHE_CODE IS NOT NULL
-- LIMIT 20;
