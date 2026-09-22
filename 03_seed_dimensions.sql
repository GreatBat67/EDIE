-- ============================================================
-- INSURANCE AI HUB (E.D.I.E.) - Seed Dimension Tables
-- Phase 3a: AGENTS (150 rows) + CUSTOMERS (5,000 rows)
-- Pure Snowflake SQL using GENERATOR + arrays
-- ============================================================

USE DATABASE INSURANCE_AI_HUB;
USE WAREHOUSE INSURANCE_AI_HUB_WH;
USE SCHEMA ANALYTICS;

-- ============================================================
-- AGENTS - 150 rows
-- Distribution: 5 regions, 5 specializations, bimodal performance
-- ============================================================

INSERT INTO AGENTS
WITH
first_names AS (
    SELECT ARRAY_CONSTRUCT(
        'James','Robert','Michael','David','William','Richard','Joseph','Thomas','Christopher','Daniel',
        'Matthew','Anthony','Mark','Steven','Paul','Andrew','Joshua','Kenneth','Kevin','Brian',
        'Sarah','Jennifer','Jessica','Emily','Amanda','Ashley','Megan','Stephanie','Nicole','Elizabeth',
        'Patricia','Linda','Barbara','Susan','Margaret','Dorothy','Lisa','Karen','Nancy','Betty',
        'Charles','Donald','George','Edward','Ronald','Timothy','Jason','Jeffrey','Ryan','Jacob',
        'Michelle','Kimberly','Donna','Carol','Ruth','Sharon','Laura','Cynthia','Kathleen','Amy',
        'Angela','Melissa','Deborah','Brenda','Rebecca','Diane','Shirley','Pamela','Sandra','Teresa'
    ) AS arr
),
last_names AS (
    SELECT ARRAY_CONSTRUCT(
        'Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Davis','Rodriguez','Martinez',
        'Hernandez','Lopez','Gonzalez','Wilson','Anderson','Thomas','Taylor','Moore','Jackson','Martin',
        'Lee','Perez','Thompson','White','Harris','Sanchez','Clark','Ramirez','Lewis','Robinson',
        'Walker','Young','Allen','King','Wright','Scott','Torres','Nguyen','Hill','Flores',
        'Green','Adams','Nelson','Baker','Hall','Rivera','Campbell','Mitchell','Carter','Roberts',
        'Turner','Phillips','Evans','Collins','Stewart','Morris','Murphy','Cook','Rogers','Morgan',
        'Peterson','Cooper','Reed','Bailey','Bell','Gomez','Kelly','Howard','Ward','Cox'
    ) AS arr
),
regions AS (
    SELECT ARRAY_CONSTRUCT('Northeast','Southeast','Midwest','West','Southwest') AS arr
),
region_states AS (
    SELECT ARRAY_CONSTRUCT(
        ARRAY_CONSTRUCT('NY','NJ','CT','MA','PA'),
        ARRAY_CONSTRUCT('FL','GA','NC','SC','VA'),
        ARRAY_CONSTRUCT('IL','OH','MI','IN','WI'),
        ARRAY_CONSTRUCT('CA','WA','OR','CO','NV'),
        ARRAY_CONSTRUCT('TX','AZ','NM','OK','LA')
    ) AS arr
),
specializations AS (
    SELECT ARRAY_CONSTRUCT('Auto','Home','Life','Health','Commercial') AS arr
),
raw_data AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn
    FROM TABLE(GENERATOR(ROWCOUNT => 150))
)
SELECT
    'AGT-' || LPAD(rn::VARCHAR, 3, '0') AS AGENT_ID,
    first_names.arr[UNIFORM(0, 69, RANDOM(rn))]::VARCHAR || ' ' ||
        last_names.arr[UNIFORM(0, 69, RANDOM(rn + 1000))]::VARCHAR AS AGENT_NAME,
    regions.arr[MOD(rn - 1, 5)]::VARCHAR AS REGION,
    region_states.arr[MOD(rn - 1, 5)][UNIFORM(0, 4, RANDOM(rn + 2000))]::VARCHAR AS STATE,
    specializations.arr[MOD(FLOOR((rn - 1) / 5), 5)]::VARCHAR AS SPECIALIZATION,
    'LIC-' || LPAD((100000 + rn * 7)::VARCHAR, 6, '0') AS LICENSE_NUMBER,
    DATEADD('day', -UNIFORM(365, 3650, RANDOM(rn + 3000)), '2025-06-30'::DATE) AS HIRE_DATE,
    CASE
        WHEN UNIFORM(1, 100, RANDOM(rn + 4000)) <= 15 THEN ROUND(UNIFORM(1.00, 2.50, RANDOM(rn + 4001))::DECIMAL(3,2), 2)
        WHEN UNIFORM(1, 100, RANDOM(rn + 4000)) <= 40 THEN ROUND(UNIFORM(2.51, 3.50, RANDOM(rn + 4002))::DECIMAL(3,2), 2)
        ELSE ROUND(UNIFORM(3.51, 5.00, RANDOM(rn + 4003))::DECIMAL(3,2), 2)
    END AS PERFORMANCE_RATING,
    UNIFORM(10, 120, RANDOM(rn + 5000)) AS ACTIVE_POLICIES_COUNT,
    CASE WHEN UNIFORM(1, 100, RANDOM(rn + 6000)) <= 90 THEN 'Active' ELSE 'Inactive' END AS STATUS
FROM raw_data, first_names, last_names, regions, region_states, specializations;

-- ============================================================
-- CUSTOMERS - 5,000 rows
-- Distribution: realistic demographics, risk tiers, credit scores
-- ============================================================

INSERT INTO CUSTOMERS
WITH
first_names AS (
    SELECT ARRAY_CONSTRUCT(
        'James','Robert','Michael','David','William','Richard','Joseph','Thomas','Christopher','Daniel',
        'Matthew','Anthony','Mark','Steven','Paul','Andrew','Joshua','Kenneth','Kevin','Brian',
        'Sarah','Jennifer','Jessica','Emily','Amanda','Ashley','Megan','Stephanie','Nicole','Elizabeth',
        'Patricia','Linda','Barbara','Susan','Margaret','Dorothy','Lisa','Karen','Nancy','Betty',
        'Charles','Donald','George','Edward','Ronald','Timothy','Jason','Jeffrey','Ryan','Jacob',
        'Michelle','Kimberly','Donna','Carol','Ruth','Sharon','Laura','Cynthia','Kathleen','Amy',
        'Angela','Melissa','Deborah','Brenda','Rebecca','Diane','Shirley','Pamela','Sandra','Teresa',
        'Alexander','Benjamin','Samuel','Nathan','Henry','Jack','Logan','Owen','Ethan','Lucas',
        'Madison','Olivia','Abigail','Sophia','Isabella','Charlotte','Amelia','Harper','Evelyn','Aria'
    ) AS arr
),
last_names AS (
    SELECT ARRAY_CONSTRUCT(
        'Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Davis','Rodriguez','Martinez',
        'Hernandez','Lopez','Gonzalez','Wilson','Anderson','Thomas','Taylor','Moore','Jackson','Martin',
        'Lee','Perez','Thompson','White','Harris','Sanchez','Clark','Ramirez','Lewis','Robinson',
        'Walker','Young','Allen','King','Wright','Scott','Torres','Nguyen','Hill','Flores',
        'Green','Adams','Nelson','Baker','Hall','Rivera','Campbell','Mitchell','Carter','Roberts',
        'Turner','Phillips','Evans','Collins','Stewart','Morris','Murphy','Cook','Rogers','Morgan',
        'Peterson','Cooper','Reed','Bailey','Bell','Gomez','Kelly','Howard','Ward','Cox',
        'Diaz','Richardson','Wood','Watson','Brooks','Bennett','Gray','James','Reyes','Cruz',
        'Hughes','Price','Myers','Long','Foster','Sanders','Ross','Morales','Powell','Sullivan'
    ) AS arr
),
cities_by_state AS (
    SELECT ARRAY_CONSTRUCT(
        OBJECT_CONSTRUCT('state','CA','cities',ARRAY_CONSTRUCT('Los Angeles','San Francisco','San Diego','Sacramento','San Jose')),
        OBJECT_CONSTRUCT('state','TX','cities',ARRAY_CONSTRUCT('Houston','Dallas','Austin','San Antonio','Fort Worth')),
        OBJECT_CONSTRUCT('state','FL','cities',ARRAY_CONSTRUCT('Miami','Orlando','Tampa','Jacksonville','Fort Lauderdale')),
        OBJECT_CONSTRUCT('state','NY','cities',ARRAY_CONSTRUCT('New York','Buffalo','Rochester','Albany','Syracuse')),
        OBJECT_CONSTRUCT('state','IL','cities',ARRAY_CONSTRUCT('Chicago','Aurora','Naperville','Springfield','Peoria')),
        OBJECT_CONSTRUCT('state','PA','cities',ARRAY_CONSTRUCT('Philadelphia','Pittsburgh','Allentown','Erie','Reading')),
        OBJECT_CONSTRUCT('state','OH','cities',ARRAY_CONSTRUCT('Columbus','Cleveland','Cincinnati','Toledo','Akron')),
        OBJECT_CONSTRUCT('state','GA','cities',ARRAY_CONSTRUCT('Atlanta','Augusta','Savannah','Athens','Macon')),
        OBJECT_CONSTRUCT('state','NC','cities',ARRAY_CONSTRUCT('Charlotte','Raleigh','Durham','Greensboro','Winston-Salem')),
        OBJECT_CONSTRUCT('state','MI','cities',ARRAY_CONSTRUCT('Detroit','Grand Rapids','Ann Arbor','Lansing','Flint')),
        OBJECT_CONSTRUCT('state','NJ','cities',ARRAY_CONSTRUCT('Newark','Jersey City','Trenton','Princeton','Camden')),
        OBJECT_CONSTRUCT('state','VA','cities',ARRAY_CONSTRUCT('Virginia Beach','Richmond','Norfolk','Arlington','Alexandria')),
        OBJECT_CONSTRUCT('state','WA','cities',ARRAY_CONSTRUCT('Seattle','Tacoma','Spokane','Bellevue','Olympia')),
        OBJECT_CONSTRUCT('state','AZ','cities',ARRAY_CONSTRUCT('Phoenix','Tucson','Mesa','Scottsdale','Tempe')),
        OBJECT_CONSTRUCT('state','MA','cities',ARRAY_CONSTRUCT('Boston','Worcester','Springfield','Cambridge','Lowell')),
        OBJECT_CONSTRUCT('state','CO','cities',ARRAY_CONSTRUCT('Denver','Colorado Springs','Aurora','Boulder','Fort Collins')),
        OBJECT_CONSTRUCT('state','IN','cities',ARRAY_CONSTRUCT('Indianapolis','Fort Wayne','Bloomington','Evansville','South Bend')),
        OBJECT_CONSTRUCT('state','MO','cities',ARRAY_CONSTRUCT('Kansas City','St. Louis','Springfield','Columbia','Independence')),
        OBJECT_CONSTRUCT('state','TN','cities',ARRAY_CONSTRUCT('Nashville','Memphis','Knoxville','Chattanooga','Clarksville')),
        OBJECT_CONSTRUCT('state','LA','cities',ARRAY_CONSTRUCT('New Orleans','Baton Rouge','Shreveport','Lafayette','Lake Charles'))
    ) AS arr
),
streets AS (
    SELECT ARRAY_CONSTRUCT(
        'Main St','Oak Ave','Maple Dr','Cedar Ln','Pine Rd','Elm St','Washington Blvd',
        'Park Ave','Lake Dr','Hill Rd','River Rd','Forest Ave','Sunset Blvd','Highland Dr',
        'Valley Rd','Spring St','Church St','Market St','Academy Ave','Union St'
    ) AS arr
),
genders AS (
    SELECT ARRAY_CONSTRUCT('Male','Female','Non-Binary') AS arr
),
raw_data AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn
    FROM TABLE(GENERATOR(ROWCOUNT => 5000))
)
SELECT
    'CUST-' || LPAD(rn::VARCHAR, 5, '0') AS CUSTOMER_ID,
    first_names.arr[UNIFORM(0, 79, RANDOM(rn * 13))]::VARCHAR AS FIRST_NAME,
    last_names.arr[UNIFORM(0, 79, RANDOM(rn * 17))]::VARCHAR AS LAST_NAME,
    DATEADD('day', -UNIFORM(6570, 25550, RANDOM(rn * 19)), CURRENT_DATE()) AS DATE_OF_BIRTH,
    CASE
        WHEN UNIFORM(1, 100, RANDOM(rn * 23)) <= 48 THEN 'Male'
        WHEN UNIFORM(1, 100, RANDOM(rn * 23)) <= 96 THEN 'Female'
        ELSE 'Non-Binary'
    END AS GENDER,
    LOWER(first_names.arr[UNIFORM(0, 79, RANDOM(rn * 13))]::VARCHAR) || '.' ||
        LOWER(last_names.arr[UNIFORM(0, 79, RANDOM(rn * 17))]::VARCHAR) || rn::VARCHAR ||
        CASE UNIFORM(1, 4, RANDOM(rn * 29))
            WHEN 1 THEN '@gmail.com'
            WHEN 2 THEN '@yahoo.com'
            WHEN 3 THEN '@outlook.com'
            ELSE '@hotmail.com'
        END AS EMAIL,
    '(' || LPAD(UNIFORM(200, 999, RANDOM(rn * 31))::VARCHAR, 3, '0') || ') ' ||
        LPAD(UNIFORM(200, 999, RANDOM(rn * 37))::VARCHAR, 3, '0') || '-' ||
        LPAD(UNIFORM(1000, 9999, RANDOM(rn * 41))::VARCHAR, 4, '0') AS PHONE,
    UNIFORM(100, 9999, RANDOM(rn * 43))::VARCHAR || ' ' ||
        streets.arr[UNIFORM(0, 19, RANDOM(rn * 47))]::VARCHAR AS ADDRESS,
    cities_by_state.arr[MOD(rn, 20)]['cities'][UNIFORM(0, 4, RANDOM(rn * 53))]::VARCHAR AS CITY,
    cities_by_state.arr[MOD(rn, 20)]['state']::VARCHAR AS STATE,
    LPAD(UNIFORM(10001, 99999, RANDOM(rn * 59))::VARCHAR, 5, '0') AS ZIP_CODE,
    CASE
        WHEN UNIFORM(1, 100, RANDOM(rn * 61)) <= 40 THEN 'Low'
        WHEN UNIFORM(1, 100, RANDOM(rn * 61)) <= 75 THEN 'Medium'
        WHEN UNIFORM(1, 100, RANDOM(rn * 61)) <= 92 THEN 'High'
        ELSE 'Critical'
    END AS RISK_TIER,
    CASE
        WHEN UNIFORM(1, 100, RANDOM(rn * 67)) <= 10 THEN UNIFORM(300, 549, RANDOM(rn * 71))
        WHEN UNIFORM(1, 100, RANDOM(rn * 67)) <= 35 THEN UNIFORM(550, 649, RANDOM(rn * 73))
        WHEN UNIFORM(1, 100, RANDOM(rn * 67)) <= 70 THEN UNIFORM(650, 749, RANDOM(rn * 79))
        ELSE UNIFORM(750, 850, RANDOM(rn * 83))
    END AS CREDIT_SCORE,
    DATEADD('day', -UNIFORM(30, 1260, RANDOM(rn * 89)), '2025-06-30'::DATE) AS CUSTOMER_SINCE,
    CASE
        WHEN UNIFORM(1, 100, RANDOM(rn * 97)) <= 20 THEN 'Premium'
        WHEN UNIFORM(1, 100, RANDOM(rn * 97)) <= 65 THEN 'Standard'
        ELSE 'Budget'
    END AS SEGMENT
FROM raw_data, first_names, last_names, cities_by_state, streets, genders;

-- Verify counts
SELECT 'AGENTS' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM AGENTS
UNION ALL
SELECT 'CUSTOMERS', COUNT(*) FROM CUSTOMERS;
