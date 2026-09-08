-- ============================================================
-- INSURANCE AI HUB (E.D.I.E.) - Document Intelligence Layer
-- Phase 3c: POLICY_DOCUMENTS (2,000) + DOCUMENT_CHUNKS (12,000)
-- Realistic insurance contract language for RAG/Cortex Search
-- ============================================================

USE DATABASE INSURANCE_AI_HUB;
USE WAREHOUSE INSURANCE_AI_HUB_WH;
USE SCHEMA DOCUMENTS;

-- ============================================================
-- POLICY_DOCUMENTS - 2,000 rows
-- Realistic insurance contract text with coverage terms,
-- exclusions, deductibles, and conditions
-- ============================================================

INSERT INTO POLICY_DOCUMENTS
WITH
doc_types AS (
    SELECT ARRAY_CONSTRUCT('Contract','Contract','Contract','Endorsement','Endorsement','Exclusion','Declaration','Rider') AS arr
),
-- Auto insurance content templates
auto_content AS (
    SELECT ARRAY_CONSTRUCT(
        'AUTOMOBILE INSURANCE POLICY - COMPREHENSIVE COVERAGE\n\nSection 1: Liability Coverage\nThis policy provides bodily injury and property damage liability coverage up to the limits specified in the declarations page. Coverage applies when the insured is legally liable for damages arising from the ownership, maintenance, or use of the covered automobile.\n\nSection 2: Collision Coverage\nWe will pay for direct and accidental loss to your covered auto caused by collision less the applicable deductible. Collision means the upset of your covered auto or its impact with another vehicle or object.\n\nSection 3: Comprehensive Coverage\nWe will pay for loss to your covered auto caused by anything other than collision, including but not limited to: fire, theft, vandalism, flood, hail, windstorm, earthquake, explosion, or contact with animals.\n\nSection 4: Uninsured/Underinsured Motorist\nWe will pay compensatory damages which an insured is legally entitled to recover from the owner or operator of an uninsured or underinsured motor vehicle.',
        'AUTOMOBILE POLICY ENDORSEMENT - RENTAL REIMBURSEMENT\n\nThis endorsement modifies the automobile insurance policy to which it is attached.\n\nRental Reimbursement Coverage: We will reimburse the insured for transportation expenses incurred due to the loss of use of the covered vehicle, subject to the following conditions:\n\n1. Maximum daily benefit: $50 per day\n2. Maximum coverage period: 30 days per occurrence\n3. Coverage begins 24 hours after the loss and continues until the vehicle is repaired or replaced\n4. Receipts must be submitted within 60 days of the rental period\n\nExclusions: This coverage does not apply to mechanical breakdown, routine maintenance, or vehicles used for commercial purposes.',
        'AUTOMOBILE POLICY EXCLUSION SCHEDULE\n\nThe following exclusions apply to all coverages under this policy:\n\n1. Intentional Acts: Any loss arising from intentional damage caused by the insured or any person acting at the direction of the insured.\n2. Racing: Any loss occurring while the vehicle is being used in any racing, speed contest, or demolition activity.\n3. Commercial Use: Any loss while the vehicle is being used to carry persons or property for compensation (rideshare activities excluded if endorsement purchased).\n4. War and Terrorism: Any loss caused by war, invasion, civil unrest, or acts of terrorism.\n5. Nuclear Hazard: Any loss caused by nuclear reaction, radiation, or radioactive contamination.\n6. Wear and Tear: Normal mechanical breakdown, deterioration, or gradual wear.\n7. DUI/DWI: Losses occurring while the operator is under the influence of alcohol or controlled substances above legal limits.\n8. Unauthorized Drivers: Losses while the vehicle is operated by a person not listed on the policy without reasonable belief of permission.'
    ) AS arr
),
-- Home insurance content templates
home_content AS (
    SELECT ARRAY_CONSTRUCT(
        'HOMEOWNERS INSURANCE POLICY - HO-3 SPECIAL FORM\n\nCOVERAGE A: DWELLING\nWe cover the dwelling on the residence premises shown in the Declarations, including structures attached to the dwelling. We cover materials and supplies located on or next to the residence premises used to construct, alter, or repair the dwelling.\n\nCOVERAGE B: OTHER STRUCTURES\nWe cover other structures on the residence premises set apart from the dwelling by clear space, including structures connected to the dwelling by only a fence, utility line, or similar connection. Coverage limit: 10% of Coverage A.\n\nCOVERAGE C: PERSONAL PROPERTY\nWe cover personal property owned or used by an insured while it is anywhere in the world. Coverage limit: 50% of Coverage A. Special limits apply to: jewelry ($1,500), firearms ($2,500), silverware ($2,500), watercraft ($1,500), securities ($1,500).\n\nCOVERAGE D: LOSS OF USE\nIf a covered loss makes the residence premises uninhabitable, we cover additional living expenses and fair rental value. Coverage limit: 20% of Coverage A.',
        'HOMEOWNERS POLICY - WATER DAMAGE AND SEWER BACKUP ENDORSEMENT\n\nThis endorsement extends coverage to include:\n\n1. Sewer and Drain Backup: We will pay for direct physical loss to covered property caused by water or waterborne material that backs up through sewers or drains, or that overflows or is discharged from a sump, sump pump, or related equipment. Maximum coverage: $25,000 per occurrence.\n\n2. Surface Water Overflow: Coverage for damage caused by surface water that enters the dwelling through doors, windows, or other openings above ground level due to severe rainfall events.\n\nIMPORTANT LIMITATIONS:\n- This endorsement does NOT cover flood as defined by the National Flood Insurance Program\n- Groundwater seepage is NOT covered\n- Continuous or repeated seepage over a period of 14 days or more is excluded\n- The insured must maintain sewer lines and sump equipment in proper working condition\n- Deductible: $2,500 per occurrence (separate from base policy deductible)',
        'HOMEOWNERS POLICY EXCLUSION ADDENDUM\n\nThe following perils are EXCLUDED from coverage under this policy:\n\n1. FLOOD: Surface water, waves, tidal water, overflow of any body of water, spray from any of these. Flood insurance must be purchased separately through the NFIP or private flood market.\n2. EARTH MOVEMENT: Earthquake, landslide, mudflow, subsidence, sinkhole. Earthquake coverage available by endorsement.\n3. MOLD AND FUNGUS: Any loss caused by mold, fungus, wet rot, or dry rot, unless directly resulting from a covered peril and discovered within 14 days.\n4. ORDINANCE OR LAW: Increased costs due to enforcement of building codes or ordinances unless Coverage E endorsement is added.\n5. NEGLECT: Loss resulting from the insureds failure to use all reasonable means to save and preserve property during and after a covered loss.\n6. POWER FAILURE: Loss caused by power failure originating away from the residence premises.\n7. WAR: Any act of war, undeclared war, civil war, insurrection, or rebellion.\n8. GOVERNMENT ACTION: Destruction or confiscation by government or public authority.'
    ) AS arr
),
-- Life insurance content templates
life_content AS (
    SELECT ARRAY_CONSTRUCT(
        'TERM LIFE INSURANCE POLICY\n\nDEATH BENEFIT PROVISION\nUpon receipt of due proof of the death of the insured during the policy term, we will pay the death benefit to the designated beneficiary. The face amount is specified in the policy schedule.\n\nPREMIUM PAYMENT\nPremiums are due on the dates specified in the premium schedule. A grace period of 31 days is allowed for each premium payment after the first. The policy remains in force during the grace period.\n\nCONVERSION PRIVILEGE\nDuring the first 15 years of this policy, or before age 65, whichever is earlier, you may convert this term policy to a whole life or universal life policy without evidence of insurability. The premium for the new policy will be based on the insureds attained age at conversion.\n\nRENEWABILITY\nThis policy is renewable at the end of each term period up to age 80, subject to increased premiums based on attained age. No evidence of insurability is required for renewal.',
        'LIFE INSURANCE - ACCELERATED DEATH BENEFIT RIDER\n\nThis rider allows the insured to receive a portion of the death benefit while living if diagnosed with a qualifying terminal illness.\n\nELIGIBILITY CONDITIONS:\n1. The insured must be diagnosed with a terminal illness with a life expectancy of 12 months or less\n2. Certification required from two licensed physicians\n3. Minimum policy must have been in force for 2 years (contestability period)\n\nBENEFIT AMOUNT:\n- Maximum accelerated amount: 75% of the death benefit or $500,000, whichever is less\n- Remaining death benefit continues in force with proportionally reduced premiums\n- An administrative fee of $150 applies to the acceleration\n\nTAX IMPLICATIONS: Accelerated benefits may be tax-free under IRC Section 101(g). Consult a tax advisor.',
        'LIFE INSURANCE POLICY - EXCLUSIONS AND CONTESTABILITY\n\nSUICIDE EXCLUSION: If the insured dies by suicide within two years from the policy date (or reinstatement date), our liability is limited to a refund of premiums paid.\n\nCONTESTABILITY: We may contest this policy within two years of the issue date based on material misrepresentation in the application. After two years, the policy is incontestable except for non-payment of premiums or fraudulent misstatements.\n\nEXCLUSIONS FROM COVERAGE:\n1. Death while engaged in illegal activities as a principal\n2. Death resulting from active participation in war or armed conflict (military service exclusion)\n3. Death from aviation activities other than as a fare-paying passenger on a scheduled airline\n4. Death occurring while incarcerated in a correctional facility\n\nMISSTATEMENT OF AGE: If the age of the insured has been misstated, benefits will be adjusted to the amount the premium paid would have purchased at the correct age.'
    ) AS arr
),
-- Health insurance content templates
health_content AS (
    SELECT ARRAY_CONSTRUCT(
        'GROUP HEALTH INSURANCE POLICY - PREFERRED PROVIDER ORGANIZATION (PPO)\n\nSCHEDULE OF BENEFITS:\n- Annual Deductible: Individual $1,500 / Family $3,000\n- Out-of-Pocket Maximum: Individual $6,000 / Family $12,000\n- Coinsurance: 80/20 in-network, 60/40 out-of-network\n- Primary Care Visit: $30 copay\n- Specialist Visit: $50 copay\n- Emergency Room: $250 copay (waived if admitted)\n- Prescription Drugs: Tier 1 $10, Tier 2 $35, Tier 3 $60, Tier 4 30%\n\nPREVENTIVE CARE: Covered at 100% in-network with no deductible or copay, as required by the Affordable Care Act. Includes annual physicals, immunizations, cancer screenings, and well-child visits.\n\nMENTAL HEALTH PARITY: Mental health and substance use disorder services are covered at the same level as medical/surgical benefits, in compliance with the Mental Health Parity and Addiction Equity Act.',
        'HEALTH INSURANCE - PRIOR AUTHORIZATION REQUIREMENTS\n\nThe following services require prior authorization before coverage applies:\n\n1. All inpatient hospital admissions (except emergency)\n2. Outpatient surgical procedures exceeding $5,000\n3. Advanced diagnostic imaging (MRI, CT, PET scans)\n4. Specialty medications (Tier 3 and Tier 4)\n5. Physical therapy beyond 20 visits per calendar year\n6. Durable medical equipment exceeding $1,000\n7. Home health care services\n8. Skilled nursing facility stays\n\nFAILURE TO OBTAIN AUTHORIZATION: Services performed without required prior authorization will be subject to a 50% reduction in benefits or denial of coverage. Emergency services are exempt from prior authorization requirements.\n\nAPPEAL PROCESS: If authorization is denied, the member may file an appeal within 180 days. Two levels of internal appeal are available, followed by external review by an independent organization.',
        'HEALTH INSURANCE EXCLUSIONS AND LIMITATIONS\n\nNOT COVERED SERVICES:\n1. Cosmetic surgery unless medically necessary for reconstruction after injury\n2. Experimental or investigational treatments not approved by FDA\n3. Services for which no charge is normally made\n4. Injuries sustained during commission of a felony\n5. Services rendered by immediate family members\n6. Weight loss surgery unless BMI exceeds 40 or 35 with comorbidities\n7. Infertility treatments beyond 3 IVF cycles\n8. Dental services (covered under separate dental plan)\n9. Vision correction surgery (LASIK, PRK)\n10. Long-term custodial care\n\nPRE-EXISTING CONDITIONS: Under the ACA, no pre-existing condition exclusions apply to this policy. However, waiting periods of up to 90 days may apply for new enrollees.'
    ) AS arr
),
-- Commercial insurance content templates
commercial_content AS (
    SELECT ARRAY_CONSTRUCT(
        'COMMERCIAL GENERAL LIABILITY POLICY (CGL)\n\nCOVERAGE A: BODILY INJURY AND PROPERTY DAMAGE LIABILITY\nWe will pay those sums that the insured becomes legally obligated to pay as damages because of bodily injury or property damage to which this insurance applies. We have the right and duty to defend the insured against any suit seeking those damages.\n\nLIMITS OF INSURANCE:\n- Each Occurrence: $1,000,000\n- General Aggregate: $2,000,000\n- Products/Completed Operations Aggregate: $2,000,000\n- Personal and Advertising Injury: $1,000,000\n- Damage to Premises Rented: $100,000\n- Medical Expense: $5,000\n\nCOVERAGE B: PERSONAL AND ADVERTISING INJURY\nWe will pay those sums for personal and advertising injury caused by an offense arising out of your business, including libel, slander, false arrest, wrongful eviction, and infringement of copyright in your advertisement.',
        'COMMERCIAL PROPERTY INSURANCE - BUSINESS INTERRUPTION ENDORSEMENT\n\nThis endorsement provides coverage for loss of business income and extra expense when business operations are suspended due to direct physical loss at the described premises.\n\nBUSINESS INCOME COVERAGE:\n- Period of Restoration: Maximum 12 months from date of loss\n- Monthly Limit of Indemnity: 1/4 of the annual limit\n- Ordinary Payroll: Covered for 90 days only\n- Extended Business Income: 60 days beyond restoration\n\nEXTRA EXPENSE COVERAGE:\n- Covers reasonable expenses to minimize suspension of operations\n- Includes temporary relocation costs, expediting charges, and overtime labor\n- Maximum: $250,000 per occurrence\n\nWAITING PERIOD: 72-hour waiting period applies from the time of direct physical loss before business income coverage begins. No waiting period for extra expense.',
        'COMMERCIAL POLICY - CYBER LIABILITY ENDORSEMENT\n\nThis endorsement provides coverage for cyber-related losses and liabilities.\n\nCOVERAGE SECTIONS:\n1. DATA BREACH RESPONSE: Costs for notification, credit monitoring, forensic investigation, and public relations following a data breach. Limit: $500,000.\n2. NETWORK SECURITY LIABILITY: Third-party claims arising from failure of network security, including transmission of malware, denial-of-service attacks, and unauthorized access.\n3. PRIVACY LIABILITY: Claims arising from failure to protect personally identifiable information (PII) or protected health information (PHI).\n4. REGULATORY PROCEEDINGS: Defense costs and penalties from regulatory actions (GDPR, CCPA, HIPAA).\n5. BUSINESS INTERRUPTION: Loss of income due to security breach causing system downtime. 8-hour waiting period.\n\nEXCLUSIONS: Infrastructure failure, unencrypted portable devices, known vulnerabilities unpatched for 60+ days, insider trading, patent infringement.'
    ) AS arr
),
policy_data AS (
    SELECT POLICY_ID, POLICY_TYPE, START_DATE, END_DATE,
           ROW_NUMBER() OVER (ORDER BY POLICY_ID) AS pol_rn
    FROM INSURANCE_AI_HUB.ANALYTICS.POLICIES
),
raw_data AS (
    SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS rn
    FROM TABLE(GENERATOR(ROWCOUNT => 2000))
)
SELECT
    'DOC-' || LPAD(r.rn::VARCHAR, 5, '0') AS DOCUMENT_ID,
    p.POLICY_ID,
    doc_types.arr[UNIFORM(0, 7, RANDOM(r.rn * 7))]::VARCHAR AS DOCUMENT_TYPE,
    CASE p.POLICY_TYPE
        WHEN 'Auto' THEN 'Auto Insurance - ' || doc_types.arr[UNIFORM(0, 7, RANDOM(r.rn * 7))]::VARCHAR || ' - Policy ' || p.POLICY_ID
        WHEN 'Home' THEN 'Homeowners - ' || doc_types.arr[UNIFORM(0, 7, RANDOM(r.rn * 7))]::VARCHAR || ' - Policy ' || p.POLICY_ID
        WHEN 'Life' THEN 'Life Insurance - ' || doc_types.arr[UNIFORM(0, 7, RANDOM(r.rn * 7))]::VARCHAR || ' - Policy ' || p.POLICY_ID
        WHEN 'Health' THEN 'Health Plan - ' || doc_types.arr[UNIFORM(0, 7, RANDOM(r.rn * 7))]::VARCHAR || ' - Policy ' || p.POLICY_ID
        ELSE 'Commercial - ' || doc_types.arr[UNIFORM(0, 7, RANDOM(r.rn * 7))]::VARCHAR || ' - Policy ' || p.POLICY_ID
    END AS TITLE,
    CASE p.POLICY_TYPE
        WHEN 'Auto' THEN auto_content.arr[UNIFORM(0, 2, RANDOM(r.rn * 11))]::VARCHAR
        WHEN 'Home' THEN home_content.arr[UNIFORM(0, 2, RANDOM(r.rn * 13))]::VARCHAR
        WHEN 'Life' THEN life_content.arr[UNIFORM(0, 2, RANDOM(r.rn * 17))]::VARCHAR
        WHEN 'Health' THEN health_content.arr[UNIFORM(0, 2, RANDOM(r.rn * 19))]::VARCHAR
        ELSE commercial_content.arr[UNIFORM(0, 2, RANDOM(r.rn * 23))]::VARCHAR
    END AS CONTENT,
    CASE p.POLICY_TYPE
        WHEN 'Auto' THEN 'Automobile insurance policy covering liability, collision, comprehensive, and uninsured motorist protection with specified limits and deductibles.'
        WHEN 'Home' THEN 'Homeowners insurance policy providing dwelling, personal property, liability, and loss of use coverage with special form perils.'
        WHEN 'Life' THEN 'Term or whole life insurance policy with death benefit, conversion privileges, and optional accelerated benefit riders.'
        WHEN 'Health' THEN 'Group health insurance plan with PPO network, deductibles, coinsurance, copays, and prescription drug coverage tiers.'
        ELSE 'Commercial general liability and property insurance with business interruption, cyber liability, and professional indemnity coverage.'
    END AS SUMMARY,
    p.START_DATE AS EFFECTIVE_DATE,
    p.END_DATE AS EXPIRATION_DATE,
    UNIFORM(1, 3, RANDOM(r.rn * 29)) AS VERSION,
    'EN' AS LANGUAGE,
    CASE UNIFORM(1, 10, RANDOM(r.rn * 31))
        WHEN 1 THEN 'DOCX'
        WHEN 2 THEN 'TXT'
        ELSE 'PDF'
    END AS FILE_FORMAT,
    DATEADD('day', -UNIFORM(0, 30, RANDOM(r.rn * 37)), p.START_DATE)::TIMESTAMP_NTZ AS CREATED_AT
FROM raw_data r
CROSS JOIN doc_types
CROSS JOIN auto_content
CROSS JOIN home_content
CROSS JOIN life_content
CROSS JOIN health_content
CROSS JOIN commercial_content
JOIN policy_data p ON p.pol_rn = MOD(r.rn - 1, (SELECT COUNT(*) FROM INSURANCE_AI_HUB.ANALYTICS.POLICIES)) + 1;

-- ============================================================
-- DOCUMENT_CHUNKS - 12,000 rows (~6 chunks per document)
-- Splits document content into RAG-ready chunks
-- ============================================================

INSERT INTO DOCUMENT_CHUNKS
WITH
doc_data AS (
    SELECT DOCUMENT_ID, CONTENT,
           ROW_NUMBER() OVER (ORDER BY DOCUMENT_ID) AS doc_rn
    FROM POLICY_DOCUMENTS
),
chunk_offsets AS (
    SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS chunk_seq
    FROM TABLE(GENERATOR(ROWCOUNT => 6))
),
-- Generate 6 chunks per document
expanded AS (
    SELECT
        d.DOCUMENT_ID,
        d.CONTENT,
        d.doc_rn,
        c.chunk_seq,
        ROW_NUMBER() OVER (ORDER BY d.doc_rn, c.chunk_seq) AS global_rn
    FROM doc_data d
    CROSS JOIN chunk_offsets c
    WHERE d.doc_rn <= 2000
)
SELECT
    'CHK-' || LPAD(global_rn::VARCHAR, 6, '0') AS CHUNK_ID,
    DOCUMENT_ID,
    chunk_seq AS CHUNK_INDEX,
    -- Extract approximate sections from content based on chunk index
    CASE chunk_seq
        WHEN 1 THEN SUBSTR(CONTENT, 1, LEAST(LENGTH(CONTENT), 600))
        WHEN 2 THEN SUBSTR(CONTENT, GREATEST(1, FLOOR(LENGTH(CONTENT) * 0.15)), LEAST(600, LENGTH(CONTENT) - FLOOR(LENGTH(CONTENT) * 0.15) + 1))
        WHEN 3 THEN SUBSTR(CONTENT, GREATEST(1, FLOOR(LENGTH(CONTENT) * 0.30)), LEAST(600, LENGTH(CONTENT) - FLOOR(LENGTH(CONTENT) * 0.30) + 1))
        WHEN 4 THEN SUBSTR(CONTENT, GREATEST(1, FLOOR(LENGTH(CONTENT) * 0.50)), LEAST(600, LENGTH(CONTENT) - FLOOR(LENGTH(CONTENT) * 0.50) + 1))
        WHEN 5 THEN SUBSTR(CONTENT, GREATEST(1, FLOOR(LENGTH(CONTENT) * 0.70)), LEAST(600, LENGTH(CONTENT) - FLOOR(LENGTH(CONTENT) * 0.70) + 1))
        WHEN 6 THEN SUBSTR(CONTENT, GREATEST(1, FLOOR(LENGTH(CONTENT) * 0.85)), LEAST(600, LENGTH(CONTENT) - FLOOR(LENGTH(CONTENT) * 0.85) + 1))
    END AS CHUNK_TEXT,
    -- Approximate token count (chars / 4)
    CEIL(CASE chunk_seq
        WHEN 1 THEN LEAST(LENGTH(CONTENT), 600)
        WHEN 2 THEN LEAST(600, LENGTH(CONTENT) - FLOOR(LENGTH(CONTENT) * 0.15) + 1)
        WHEN 3 THEN LEAST(600, LENGTH(CONTENT) - FLOOR(LENGTH(CONTENT) * 0.30) + 1)
        WHEN 4 THEN LEAST(600, LENGTH(CONTENT) - FLOOR(LENGTH(CONTENT) * 0.50) + 1)
        WHEN 5 THEN LEAST(600, LENGTH(CONTENT) - FLOOR(LENGTH(CONTENT) * 0.70) + 1)
        ELSE LEAST(600, LENGTH(CONTENT) - FLOOR(LENGTH(CONTENT) * 0.85) + 1)
    END / 4.0) AS TOKEN_COUNT,
    CASE UNIFORM(1, 3, RANDOM(global_rn * 7))
        WHEN 1 THEN 'arctic-embed-m'
        WHEN 2 THEN 'e5-base-v2'
        ELSE 'arctic-embed-l'
    END AS EMBEDDING_MODEL
FROM expanded;

-- Verify counts
SELECT 'POLICY_DOCUMENTS' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM POLICY_DOCUMENTS
UNION ALL
SELECT 'DOCUMENT_CHUNKS', COUNT(*) FROM DOCUMENT_CHUNKS;
