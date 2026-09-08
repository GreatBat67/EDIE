# INSURANCE_AI_HUB — Full Project Overview

**Database:** INSURANCE_AI_HUB  
**Account:** rj88085 (Snowflake)  
**Owner:** ACCOUNTADMIN  
**Warehouse:** INSURANCE_AI_HUB_WH  
**Date:** August 31, 2026  

---

## 1. Project Purpose

INSURANCE_AI_HUB is an enterprise insurance analytics platform built on Snowflake for **Apex National Property & Casualty Insurance Company (Apex P&C)** — a mid-market regional carrier headquartered in Des Moines, Iowa, operating across 18 US Midwest and Sunbelt states.

**The Client Challenge:** Apex P&C ($1.85B GWP) faces a combined ratio of 102.4%. Executives and claims adjusters lose hours daily toggling between Guidewire for structured claims, PDF folders for contract exclusions, and legacy BI tools — often making underwriting decisions on unvalidated data.

The platform demonstrates how Cortex Agents can orchestrate across structured data (Cortex Analyst + Semantic Views), unstructured documents (Cortex Search), and data quality governance in a single conversational workflow.

The centerpiece is **E.D.I.E. (Enterprise Data & Intelligence Engine)** — a Cortex Agent that answers natural-language questions from insurance professionals about customers, policies, claims, billing, risk, policy documents, and data quality.

### Apex P&C Company Profile

| Attribute | Value |
|---|---|
| Headquarters | Des Moines, Iowa |
| Market Position | Mid-Market Regional P&C Carrier (Top 40 US) |
| Operating States | 18 (Midwest & Sunbelt) |
| Gross Written Premium | $1.85 Billion annually |
| Net Income | $42 Million |
| Combined Ratio | 102.4% (losing 2.4 cents per dollar written) |
| Commercial Lines | 60% of revenue — CommercialMultiPeril, CommercialAuto, GeneralLiability, WorkersComp |
| Personal Lines | 40% of revenue — PersonalAuto, Homeowners, UmbrellaCoverage |

### Primary USP: Continuous Data Trust & Self-Healing Governance

E.D.I.E. doesn't just return answers — it verifies the underlying data health in real time. Every analytical insight can be cross-checked against DATA_QUALITY tables before presenting results to executives. If a table score drops below 90%, the agent proactively alerts the user.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    CORTEX AGENT: E.D.I.E.                        │
│         (orchestration model: auto, 3 tools)                     │
│                                                                  │
│  ┌──────────────────┐  ┌────────────────┐  ┌──────────────────┐ │
│  │ insurance_analytics│  │  policy_search │  │  dq_analytics    │ │
│  │ (Cortex Analyst)  │  │ (Cortex Search)│  │ (Cortex Analyst) │ │
│  └────────┬─────────┘  └───────┬────────┘  └────────┬─────────┘ │
│           │                     │                     │           │
│  ┌────────▼─────────┐  ┌───────▼────────┐  ┌────────▼─────────┐ │
│  │ INSURANCE_        │  │POLICY_SEARCH_  │  │DATA_QUALITY_     │ │
│  │ ANALYTICS         │  │SERVICE         │  │ANALYTICS         │ │
│  │ (Semantic View)   │  │(Cortex Search) │  │(Semantic View)   │ │
│  └────────┬─────────┘  └───────┬────────┘  └────────┬─────────┘ │
│           │                     │                     │           │
│  ┌────────▼─────────┐  ┌───────▼────────┐  ┌────────▼─────────┐ │
│  │ ANALYTICS schema  │  │ DOCUMENTS      │  │ DATA_QUALITY     │ │
│  │ 6 tables          │  │ schema         │  │ schema           │ │
│  │ 56,367 rows       │  │ 2 tables       │  │ 4 tables         │ │
│  │                   │  │ 14,000 rows    │  │ 9,050 rows       │ │
│  └──────────────────┘  └────────────────┘  └──────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Enterprise Source System Mapping

| Department | Source System | Target Tables | Data Description |
|---|---|---|---|
| **Underwriting & Policy Ops** | Guidewire PolicyCenter | ANALYTICS.POLICIES | Policy terms, coverage limits, effective dates, premiums, deductibles, endorsement types, expense amounts |
| **Claims Department** | Guidewire ClaimCenter | ANALYTICS.CLAIMS | FNOL, adjuster details, loss amounts, reserves, paid/recovery amounts, fraud scores, litigation, catastrophe codes |
| **Finance & Billing** | Guidewire BillingCenter | ANALYTICS.BILLING | Premium invoicing, installment plans, payment histories, overdue balances, late fees, collections |
| **Sales & Distribution** | Salesforce Financial Services Cloud (FSC) | ANALYTICS.CUSTOMERS, ANALYTICS.AGENTS | Agent performance, commission rates, agency names, customer credit risk, demographics, household grouping |
| **Customer Retention** | Salesforce Marketing Cloud + Internal ML Models | ANALYTICS.AT_RISK_POLICIES | Churn probability, revenue at risk, CLV, NPS, competitor quote flags, retention campaign tracking |
| **Legal & Underwriting Policy** | SharePoint / Enterprise Doc Management | DOCUMENTS.POLICY_DOCUMENTS, DOCUMENTS.DOCUMENT_CHUNKS | PDF policy contracts, state policy form updates, coverage exclusion text for RAG retrieval |
| **Data Engineering / Governance** | Monte Carlo / Informatica DQ | DATA_QUALITY.DQ_RULES, DQ_SCORES, DQ_RESULTS, DQ_COLUMN_HEALTH | Pipeline execution logs, null check assertions, anomaly scores, column freshness |

---

## 4. Schema & Table Details

### 4.1 ANALYTICS Schema (6 tables, 56,367 rows)

#### ANALYTICS.POLICIES — 10,000 rows, 21 columns
*Source: Guidewire PolicyCenter*

| Column | Type | Nullable | Description |
|---|---|---|---|
| POLICY_ID | VARCHAR(20) | NO | Primary key (e.g., POL-00001) |
| POLICY_NUMBER | VARCHAR(30) | NO | Guidewire-style number (e.g., PA-2024-000001, CM-2025-001440) |
| CUSTOMER_ID | VARCHAR(20) | NO | FK → CUSTOMERS |
| AGENT_ID | VARCHAR(20) | NO | FK → AGENTS |
| POLICY_TYPE | VARCHAR(30) | NO | PersonalAuto, Homeowners, UmbrellaCoverage, CommercialMultiPeril, CommercialAuto, GeneralLiability, WorkersComp |
| LINE_OF_BUSINESS | VARCHAR(40) | NO | Mirrors POLICY_TYPE (Guidewire LOB code) |
| COVERAGE_TIER | VARCHAR(15) | NO | Basic, Standard, Preferred, Elite |
| EFFECTIVE_DATE | DATE | NO | Policy effective date |
| EXPIRATION_DATE | DATE | NO | Policy expiration date |
| BOUND_DATE | DATE | NO | Date policy was bound |
| POLICY_TERM_MONTHS | NUMBER(3,0) | NO | 6, 12, or 24 months |
| ISSUING_STATE | VARCHAR(2) | NO | Two-letter state code (all 50 states) |
| PREMIUM_AMOUNT | NUMBER(12,2) | NO | Annual premium in dollars |
| COVERAGE_AMOUNT | NUMBER(14,2) | NO | Total coverage limit in dollars |
| DEDUCTIBLE | NUMBER(10,2) | NO | Deductible amount |
| STATUS | VARCHAR(15) | NO | InForce, Expired, Renewed, Cancelled, NonRenewed, Draft |
| RENEWAL_STATUS | VARCHAR(15) | NO | Pending, NotEligible, Renewed, Cancelled |
| ENDORSEMENT_TYPE | VARCHAR(30) | YES | AdditionalInsured, Rider, CoverageExtension, Waiver, NULL |
| UNDERWRITING_SCORE | NUMBER(5,2) | YES | Risk score 0-100 |
| CREATED_AT | TIMESTAMP_NTZ | NO | Record creation timestamp |
| EXPENSE_AMOUNT | NUMBER(12,2) | YES | Per-policy acquisition/admin cost (for Combined Ratio KPI) |

**Product Line Distribution:**

| Product Line | Policy Type | Count | Total Premium | Avg Expense |
|---|---|---:|---:|---:|
| Commercial | CommercialMultiPeril | 1,440 | $16,766,903 | $3,610 |
| Commercial | WorkersComp | 1,120 | $8,773,257 | $2,509 |
| Commercial | GeneralLiability | 1,000 | $5,809,559 | $1,902 |
| Commercial | CommercialAuto | 840 | $7,145,576 | $2,829 |
| Personal | PersonalAuto | 3,400 | $13,320,325 | $1,268 |
| Personal | Homeowners | 2,000 | $12,505,690 | $2,006 |
| Personal | UmbrellaCoverage | 200 | $261,655 | $450 |

**Revenue Split:** Commercial 59.6% ($38.5M) / Personal 40.4% ($26.1M) — matches Apex P&C's 60/40 target.

---

#### ANALYTICS.CLAIMS — 15,000 rows, 24 columns
*Source: Guidewire ClaimCenter*

| Column | Type | Nullable | Description |
|---|---|---|---|
| CLAIM_ID | VARCHAR(20) | NO | Primary key (e.g., CLM-00001) |
| POLICY_ID | VARCHAR(20) | NO | FK → POLICIES |
| CUSTOMER_ID | VARCHAR(20) | NO | FK → CUSTOMERS |
| CLAIM_DATE | DATE | NO | Date claim was filed (Jan 2024 – Aug 2026) |
| LOSS_DATE | DATE | NO | Actual date of loss/incident |
| FNOL_DATE | DATE | NO | First Notice of Loss date |
| FNOL_CHANNEL | VARCHAR(15) | NO | Phone, Web, Mobile, Agent, Email |
| REPORTED_BY | VARCHAR(15) | NO | Insured, ThirdParty, Agent, Witness |
| CLAIM_TYPE | VARCHAR(30) | NO | 13 peril types including CommercialAutoLiability, UmbrellaExcess |
| CAUSE_OF_LOSS | VARCHAR(30) | YES | ISO codes: Collision, Fire, Lightning, WindHail, Water, Theft, Vandalism, Liability, MedicalPayment, NaturalDisaster, EquipmentBreakdown |
| CLAIM_AMOUNT | NUMBER(12,2) | NO | Total claimed amount |
| APPROVED_AMOUNT | NUMBER(12,2) | YES | Approved payout (NULL if not yet approved) |
| RESERVE_AMOUNT | NUMBER(12,2) | YES | Initial claim reserve set by adjuster |
| PAID_AMOUNT | NUMBER(12,2) | YES | Cumulative amount paid so far |
| RECOVERY_AMOUNT | NUMBER(12,2) | YES | Subrogation/salvage recoveries |
| STATUS | VARCHAR(20) | NO | Open, UnderInvestigation, Approved, PartiallyPaid, Closed, Denied, Reopened, Subrogation |
| FRAUD_SCORE | NUMBER(5,2) | YES | Fraud risk score 0-100 (~9.9% above 80) |
| FRICTION_SCORE | NUMBER(5,2) | YES | Customer friction score 0-100 |
| ADJUSTER_ID | VARCHAR(20) | YES | Assigned adjuster ID |
| RESOLUTION_DAYS | NUMBER | YES | Days to resolve (NULL for open claims) |
| INCIDENT_LOCATION | VARCHAR(100) | YES | Intersection, Highway, Parking Lot, Residence, etc. |
| LITIGATION_FLAG | BOOLEAN | NO | ~8% of claims in litigation |
| CATASTROPHE_CODE | VARCHAR(20) | YES | CAT code (e.g., CAT-2025-001) — ~5% of claims |
| CLOSED_DATE | DATE | YES | NULL for open claims |

**Key Metrics:** Date range Jan 2024 – Aug 2026 (3 years). Fraud rate: 9.9% (claims with FRAUD_SCORE > 80). Loss ratio: 69.5% against total earned premium.

---

#### ANALYTICS.BILLING — 25,000 rows, 18 columns
*Source: Guidewire BillingCenter*

| Column | Type | Nullable | Description |
|---|---|---|---|
| INVOICE_ID | VARCHAR(20) | NO | Primary key (e.g., INV-000001) |
| POLICY_ID | VARCHAR(20) | NO | FK → POLICIES |
| CUSTOMER_ID | VARCHAR(20) | NO | FK → CUSTOMERS |
| BILLING_PLAN | VARCHAR(15) | NO | DirectBill, AgencyBill, ListBill |
| INSTALLMENT_NUMBER | NUMBER(3,0) | NO | Current installment (1-12) |
| TOTAL_INSTALLMENTS | NUMBER(3,0) | NO | 1, 4, 6, or 12 installments |
| INVOICE_DATE | DATE | NO | Invoice generation date (Jan 2024 – Aug 2026) |
| DUE_DATE | DATE | NO | Payment due date (+30 days) |
| GRACE_PERIOD_END | DATE | NO | Grace period end (+45 days) |
| AMOUNT_DUE | NUMBER(12,2) | NO | Amount due on invoice |
| AMOUNT_PAID | NUMBER(12,2) | NO | Amount paid (default 0) |
| OUTSTANDING_BALANCE | NUMBER(12,2) | NO | Outstanding balance (default 0) |
| LATE_FEE | NUMBER(8,2) | NO | Late fee charged (default 0) |
| PAYMENT_STATUS | VARCHAR(20) | NO | Paid, Partial, InGracePeriod, PastDue, SentToCollections, Waived, Refunded |
| PAYMENT_METHOD | VARCHAR(15) | YES | ACH, CreditCard, DebitCard, Check, Wire, EFT, PayByPhone |
| PAYMENT_DATE | DATE | YES | Date payment received (NULL if unpaid) |
| TRANSACTION_REF | VARCHAR(30) | YES | Payment gateway reference |
| CANCELLATION_DATE | DATE | YES | Non-payment cancellation date (SentToCollections only) |

**Total outstanding balance: $6,371,104** across PastDue ($2.4M), SentToCollections ($1.7M), InGracePeriod ($799K), Partial ($711K), Refunded ($407K), Waived ($391K).

---

#### ANALYTICS.CUSTOMERS — 5,017 rows, 20 columns
*Source: Salesforce Financial Services Cloud (FSC)*

| Column | Type | Nullable | Description |
|---|---|---|---|
| CUSTOMER_ID | VARCHAR(20) | NO | Primary key (e.g., CUST-00001) |
| SALESFORCE_ACCOUNT_ID | VARCHAR(20) | NO | Salesforce CRM account ID (e.g., 001Xx0000100000) |
| FIRST_NAME | VARCHAR(50) | NO | Customer first name |
| LAST_NAME | VARCHAR(50) | NO | Customer last name |
| DATE_OF_BIRTH | DATE | NO | Date of birth |
| GENDER | VARCHAR(12) | YES | Male, Female, Non-Binary |
| EMAIL | VARCHAR(100) | YES | ~5% NULL rate — **MASKED** (non-exec roles see `ja****@gmail.com`) |
| PHONE | VARCHAR(20) | YES | ~4% NULL rate — **MASKED** (non-exec roles see `(***) ***-1234`) |
| ADDRESS | VARCHAR(200) | YES | Street address |
| CITY | VARCHAR(50) | YES | 30 major US cities |
| STATE | VARCHAR(2) | YES | Two-letter state code |
| ZIP_CODE | VARCHAR(10) | YES | 5-digit ZIP |
| RISK_TIER | VARCHAR(10) | NO | Low, Moderate, Elevated, High, Critical |
| CREDIT_SCORE | NUMBER | YES | 580-850 (~3% NULL) — **MASKED** (NULL for non-exec/non-underwriter roles) |
| SEGMENT | VARCHAR(20) | NO | Standard (40.9%), Value (29.2%), Preferred (20.0%), HighNetWorth (9.9%) |
| PREFERRED_CONTACT_METHOD | VARCHAR(10) | YES | Email, Phone, Text, Mail |
| HOUSEHOLD_ID | VARCHAR(20) | YES | Groups family members (e.g., HH-00001) |
| LIFE_EVENT_FLAG | VARCHAR(20) | YES | RecentMove, Marriage, NewChild, Retirement, None |
| ANNUAL_INCOME_RANGE | VARCHAR(15) | YES | Under50K, 50K-100K, 100K-200K, 200K-500K, Over500K |
| CUSTOMER_SINCE | DATE | NO | Relationship start date |

---

#### ANALYTICS.AGENTS — 150 rows, 17 columns
*Source: Salesforce Financial Services Cloud (FSC)*

| Column | Type | Nullable | Description |
|---|---|---|---|
| AGENT_ID | VARCHAR(20) | NO | Primary key (e.g., AGT-0001) |
| AGENT_NAME | VARCHAR(100) | NO | Full name |
| AGENCY_NAME | VARCHAR(100) | NO | Independent agency (10 agencies) |
| PRODUCER_CODE | VARCHAR(20) | NO | Unique producer/broker code |
| REGION | VARCHAR(30) | NO | Northeast, Southeast, Midwest, West, Southwest |
| STATE | VARCHAR(2) | NO | Agent state |
| SPECIALIZATION | VARCHAR(30) | NO | PersonalAuto (49), CommercialMultiPeril (22), Homeowners (21), GeneralLiability (18), MultiLine (15), WorkersComp (14), CommercialAuto (11) |
| LICENSE_NUMBER | VARCHAR(20) | NO | State license number |
| HIRE_DATE | DATE | NO | Agent hire date |
| PERFORMANCE_RATING | NUMBER(3,2) | NO | Rating 0-5 |
| COMMISSION_RATE | NUMBER(4,3) | NO | Decimal (0.05-0.18) |
| TOTAL_PREMIUM_BOOK | NUMBER(14,2) | NO | Total premium under management |
| RETENTION_RATE | NUMBER(4,3) | NO | 0.70-0.98 |
| NPS_SCORE | NUMBER(3,0) | YES | Net Promoter Score (20-99, ~5% NULL) |
| ACTIVE_POLICIES_COUNT | NUMBER | NO | Policies managed |
| APPOINTMENT_STATUS | VARCHAR(15) | NO | Active, Suspended, Terminated |
| STATUS | VARCHAR(10) | NO | Active, Inactive |

**Agency Names:** Nationwide Insurance Partners, Eagle Shield Agency, Summit Risk Group, Pinnacle Insurance Services, Heritage Underwriters, Pacific Coast Insurance, Liberty Bell Agency, Great Lakes Insurance Group, Sunbelt Coverage Corp, Mountain West Brokers

---

#### ANALYTICS.AT_RISK_POLICIES — 1,200 rows, 18 columns
*Source: Salesforce Marketing Cloud + Internal ML Models*

| Column | Type | Nullable | Description |
|---|---|---|---|
| RISK_ID | VARCHAR(20) | NO | Primary key (e.g., RISK-00001) |
| POLICY_ID | VARCHAR(20) | NO | FK → POLICIES |
| CUSTOMER_ID | VARCHAR(20) | NO | FK → CUSTOMERS |
| RISK_CATEGORY | VARCHAR(25) | NO | VoluntaryChurn (34.6%), InvoluntaryChurn (23.7%), Underinsured (15.8%), CompetitorSwitch (14.8%), ServiceDissatisfaction (11.2%) |
| CHURN_PROBABILITY | NUMBER(5,4) | NO | 0.15-0.85 |
| REVENUE_AT_RISK | NUMBER(12,2) | NO | $1,000-$30,000 |
| CUSTOMER_LIFETIME_VALUE | NUMBER(12,2) | NO | $5,000-$100,000 |
| DAYS_UNTIL_RENEWAL | NUMBER | NO | 1-365 |
| MISSED_PAYMENTS_COUNT | NUMBER | NO | 0-5 |
| CLAIM_FREQUENCY | NUMBER | NO | 0-7 |
| NPS_SCORE | NUMBER | YES | -30 to 100 (~10% NULL) |
| LAST_CONTACT_DATE | DATE | YES | ~20% NULL |
| RETENTION_ACTION | VARCHAR(30) | NO | AgentOutreach, DiscountOffer, PremiumReduction, CoverageReview, LoyaltyReward, AutoRenewLock, WinbackCampaign, None |
| COMPETITOR_QUOTE_FLAG | BOOLEAN | NO | ~15% TRUE |
| MODEL_VERSION | VARCHAR(15) | NO | v2.0-v5.9 |
| SCORE_DATE | DATE | NO | Model scoring date |
| CAMPAIGN_ID | VARCHAR(20) | YES | Retention campaign ID (~60% populated) |
| SNAPSHOT_DATE | DATE | NO | Risk snapshot date |

**Total revenue at risk: $14,868,600** — VoluntaryChurn dominates at $5.3M.

---

### 4.2 DOCUMENTS Schema (2 tables, 14,000 rows)

#### DOCUMENTS.POLICY_DOCUMENTS — 2,000 rows, 16 columns
*Source: SharePoint / Enterprise Document Management*

| Column | Type | Description |
|---|---|---|
| DOCUMENT_ID | VARCHAR(20) | Primary key (e.g., DOC-00001) |
| POLICY_ID | VARCHAR(20) | FK → POLICIES |
| DOCUMENT_TYPE | VARCHAR(30) | PolicyContract, Endorsement, ExclusionSchedule, DeclarationPage, CertificateOfInsurance, ClaimForm, RegulatoryFiling, Exclusion, Rider |
| TITLE | VARCHAR(200) | Document title |
| CONTENT | TEXT | Full document text content |
| SUMMARY | TEXT | AI-generated summary |
| EFFECTIVE_DATE / EXPIRATION_DATE | DATE | Document validity period |
| VERSION | NUMBER | Document version (default 1) |
| LANGUAGE | VARCHAR(5) | Language code (default EN) |
| FILE_FORMAT | VARCHAR(10) | File format (default PDF) |
| CREATED_AT | TIMESTAMP_NTZ | Creation timestamp |
| SOURCE_SYSTEM | VARCHAR(20) | SharePoint, DocuSign, InternalECM |
| FILING_STATE | VARCHAR(2) | State the form is filed in |
| FORM_NUMBER | VARCHAR(20) | Insurance form number (HO-3, PP-1, CP-1, etc.) |
| REGULATORY_APPROVAL_DATE | DATE | DOI approval date |

#### DOCUMENTS.DOCUMENT_CHUNKS — 12,000 rows, 6 columns
*Chunked text for RAG/embedding pipelines (~6 chunks per document)*

| Column | Type | Description |
|---|---|---|
| CHUNK_ID | VARCHAR(20) | Primary key |
| DOCUMENT_ID | VARCHAR(20) | FK → POLICY_DOCUMENTS |
| CHUNK_INDEX | NUMBER | Chunk position within document |
| CHUNK_TEXT | TEXT | Chunk text content |
| TOKEN_COUNT | NUMBER | Token count for the chunk |
| EMBEDDING_MODEL | VARCHAR(30) | Embedding model used (default: arctic-embed-m) |

---

### 4.3 DATA_QUALITY Schema (4 tables, 9,050 rows)

#### DATA_QUALITY.DQ_RULES — 50 rows, 13 columns
*Source: Monte Carlo / Informatica DQ*

| Column | Type | Description |
|---|---|---|
| RULE_ID | VARCHAR(20) | Primary key (DQR-001 to DQR-050) |
| RULE_NAME | VARCHAR(100) | Descriptive rule name |
| RULE_DESCRIPTION | TEXT | Full rule description |
| TARGET_SCHEMA | VARCHAR(30) | ANALYTICS, DOCUMENTS, or DATA_QUALITY |
| TARGET_TABLE | VARCHAR(30) | Table the rule monitors |
| TARGET_COLUMN | VARCHAR(50) | Column the rule checks (NULL for table-level) |
| RULE_TYPE | VARCHAR(20) | Completeness, Uniqueness, Validity, Consistency, Timeliness |
| SEVERITY | VARCHAR(10) | Critical, High, Medium, Low |
| THRESHOLD | NUMBER(5,2) | Pass threshold percentage |
| IS_ACTIVE | BOOLEAN | Whether rule is active |
| SOURCE_SYSTEM | VARCHAR(30) | Originating system |
| PIPELINE_NAME | VARCHAR(50) | ETL pipeline name |
| OWNER | VARCHAR(50) | Responsible team |

**Rule distribution by source system:**
- Guidewire PolicyCenter: 7 rules (POLICIES)
- Guidewire ClaimCenter: 7 rules (CLAIMS)
- Guidewire BillingCenter: 6 rules (BILLING)
- Salesforce FSC: 10 rules (CUSTOMERS + AGENTS)
- Salesforce Marketing Cloud: 6 rules (AT_RISK_POLICIES)
- SharePoint: 6 rules (DOCUMENTS)
- Monte Carlo / Informatica DQ: 8 rules (DATA_QUALITY self-monitoring)

#### DATA_QUALITY.DQ_SCORES — 1,000 rows, 14 columns
Daily table-level quality scores across 5 dimensions (100 days x 10 tables). Includes SOURCE_SYSTEM field.

#### DATA_QUALITY.DQ_RESULTS — 5,000 rows, 14 columns
Individual rule execution results with PIPELINE_RUN_ID and ANOMALY_SCORE (Monte Carlo detection score 0-1).

#### DATA_QUALITY.DQ_COLUMN_HEALTH — 3,000 rows, 13 columns
Weekly column-level health metrics (100 weeks x 30 columns). Includes FRESHNESS_HOURS field.

---

## 5. Snowflake Objects

### 5.1 Semantic Views

#### INSURANCE_AI_HUB.ANALYTICS.INSURANCE_ANALYTICS
- **6 logical tables:** CUSTOMERS, AGENTS, POLICIES, CLAIMS, BILLING, AT_RISK_POLICIES
- **3 relationships:**
  - CLAIMS(POLICY_ID) → POLICIES
  - AT_RISK_POLICIES(POLICY_ID) → POLICIES
  - POLICIES(AGENT_ID) → AGENTS
- **24 facts:** PREMIUM_AMOUNT, COVERAGE_AMOUNT, DEDUCTIBLE, UNDERWRITING_SCORE, **EXPENSE_AMOUNT**, CLAIM_AMOUNT, APPROVED_AMOUNT, RESERVE_AMOUNT, PAID_AMOUNT, RECOVERY_AMOUNT, FRAUD_SCORE, FRICTION_SCORE, AMOUNT_DUE, AMOUNT_PAID, OUTSTANDING_BALANCE, LATE_FEE, CHURN_PROBABILITY, REVENUE_AT_RISK, CUSTOMER_LIFETIME_VALUE, PERFORMANCE_RATING, COMMISSION_RATE, TOTAL_PREMIUM_BOOK, RETENTION_RATE, NPS_SCORE (agents)
- **85 dimensions:** All categorical/identifier/date columns across all 6 tables

#### INSURANCE_AI_HUB.DATA_QUALITY.DATA_QUALITY_ANALYTICS
- **4 logical tables:** DQ_RULES, DQ_RESULTS, DQ_SCORES, DQ_COLUMN_HEALTH
- **1 relationship:** DQ_RESULTS(RULE_ID) → DQ_RULES
- **16 facts:** THRESHOLD, PASS_RATE, EXECUTION_TIME_MS, ANOMALY_SCORE, COMPLETENESS_SCORE, UNIQUENESS_SCORE, VALIDITY_SCORE, TIMELINESS_SCORE, CONSISTENCY_SCORE, OVERALL_SCORE, NULL_RATE, DUPLICATE_RATE, OUTLIER_RATE, HEALTH_SCORE, DATA_TYPE_CONSISTENCY, FRESHNESS_HOURS
- **37 dimensions:** All categorical/identifier columns across all 4 tables

### 5.2 Cortex Search Service

**INSURANCE_AI_HUB.DOCUMENTS.POLICY_SEARCH_SERVICE**
- Search column: CHUNK_TEXT
- Attribute columns: DOCUMENT_ID, CHUNK_INDEX
- Embedding model: snowflake-arctic-embed-m-v1.5
- Source: DOCUMENTS.DOCUMENT_CHUNKS (12,000 rows)
- Refresh: Incremental, 1-hour target lag
- State: ACTIVE (indexing + serving)

### 5.3 Cortex Agent

**INSURANCE_AI_HUB.PUBLIC.EDIE**
- Model: auto (Snowflake selects the best available)
- Comment: "E.D.I.E. - Enterprise Data & Intelligence Engine for insurance analytics, document intelligence, and data quality"
- Response instruction: "You are E.D.I.E. (Enterprise Data & Intelligence Engine). You help insurance professionals get instant answers about customers, policies, claims, billing, risk, policy documents, and data quality. Be concise and actionable. Format monetary values with $ and commas."
- Orchestration instruction: "For questions about customers, policies, claims, billing, premiums, agents, or at-risk policies use the insurance_analytics tool. For questions about policy coverage, exclusions, or contract terms use the policy_search tool. For questions about data quality, DQ rules, scores, column health, or data trust use the dq_analytics tool."

**Tools:**

| Tool Name | Type | Resource | Description |
|---|---|---|---|
| insurance_analytics | cortex_analyst_text_to_sql | Semantic View: ANALYTICS.INSURANCE_ANALYTICS | Structured data: customers, agents, policies, claims, billing, premiums, fraud, at-risk |
| policy_search | cortex_search | Search Service: DOCUMENTS.POLICY_SEARCH_SERVICE (max 5 results) | Policy documents: coverage, exclusions, endorsements, riders, deductibles, contract language |
| dq_analytics | cortex_analyst_text_to_sql | Semantic View: DATA_QUALITY.DATA_QUALITY_ANALYTICS | Data quality: rules, scores, column health, null rates, outliers, trust monitoring |

### 5.4 Evaluation Datasets

| Dataset | Source Table | Rows | Date | Status |
|---|---|---:|---|---|
| edie_eval_20260831_074749 | EVAL_DATASET_EDIE_20260831_074749 | 30 | Aug 31, 2026 | Stale (pre-rework data) |
| edie_eval_20260831_084744 | EVAL_DATASET_EDIE_20260831_084744 | 30 | Aug 31, 2026 | Stale (pre-gap-fix data) |
| **edie_eval_20260831_111623** | **EVAL_DATASET_EDIE_20260831_111623** | **30** | **Aug 31, 2026** | **Current** |

**Current dataset breakdown (edie_eval_20260831_111623):**

| Track | Purpose | Count | Metrics Scored |
|---|---|---:|---|
| TEA | Tool Execution Accuracy | 20 | answer_correctness + logical_consistency + tool_selection_accuracy + tool_execution_accuracy |
| AC | Answer Correctness | 10 | answer_correctness + logical_consistency only |

**TEA track (20 questions):**
- 9 x insurance_analytics (SQL tool) — premiums, fraud, risk, billing, segments, agents, claims, active policies, **combined ratio**
- 7 x policy_search (Search tool) — copays, deductibles, coinsurance, exclusions, preventive care
- 3 x dq_analytics (SQL tool) — failing rules, table scores, column health
- 1 x no-tool guardrail (persona compliance)

**AC track (10 questions):**
- 5 x core use case — total customers, open claims, active policies, **commercial/personal revenue split**, **overall combined ratio**
- 2 x instruction compliance — persona identity, off-topic guardrail
- 1 x edge case — invalid date
- 1 x ambiguous query — vague request handling
- 1 x tool routing — DQ trend (routes to dq_analytics)

---

## 6. RBAC Roles & Data Masking

### 6.1 Persona-Based Roles

| Role | Persona | Department | Schema Access |
|---|---|---|---|
| CLAIMS_ANALYST | Marcus Vance | Claims Operations | ANALYTICS (all), DOCUMENTS (all) |
| UNDERWRITER | Elena Rostova | Underwriting & Policy Ops | ANALYTICS (all), DOCUMENTS (all) |
| RETENTION_MANAGER | Sid Patel | Customer Retention & Sales | ANALYTICS (all) |
| EXECUTIVE | Trish Gallagher | Finance & Executive | ANALYTICS (all), DOCUMENTS (all), DATA_QUALITY (all) |
| DATA_GOVERNANCE | David Chen | Data Engineering | ANALYTICS (all), DATA_QUALITY (all) |
| AGENCY_MANAGER | Sarah Jenkins | Agency Relations | ANALYTICS (all) |

### 6.2 Dynamic Data Masking Policies

| Policy | Column | Behavior |
|---|---|---|
| MASK_EMAIL | CUSTOMERS.EMAIL | EXECUTIVE/ACCOUNTADMIN see full email; others see `ja****@gmail.com` |
| MASK_PHONE | CUSTOMERS.PHONE | EXECUTIVE/ACCOUNTADMIN see full phone; others see `(***) ***-1234` |
| MASK_CREDIT_SCORE | CUSTOMERS.CREDIT_SCORE | EXECUTIVE/ACCOUNTADMIN/UNDERWRITER see score; others see NULL |

This satisfies FCRA and CCPA/CPRA requirements by restricting PII access based on business need.

---

## 7. KPI Framework & Combined Ratio

### 7.1 Combined Ratio (Validated)

The Combined Ratio KPI uses pre-aggregated claims to avoid join fan-out:

```sql
WITH claims_by_policy AS (
    SELECT POLICY_ID, SUM(PAID_AMOUNT) AS total_paid
    FROM claims GROUP BY POLICY_ID
)
SELECT
    ROUND(SUM(COALESCE(c.total_paid, 0)) / NULLIF(SUM(p.PREMIUM_AMOUNT), 0) * 100, 1) AS loss_ratio,
    ROUND(SUM(p.EXPENSE_AMOUNT) / NULLIF(SUM(p.PREMIUM_AMOUNT), 0) * 100, 1) AS expense_ratio,
    ROUND((SUM(COALESCE(c.total_paid, 0)) + SUM(p.EXPENSE_AMOUNT))
          / NULLIF(SUM(p.PREMIUM_AMOUNT), 0) * 100, 1) AS combined_ratio
FROM policies p LEFT JOIN claims_by_policy c ON p.POLICY_ID = c.POLICY_ID;
```

| Metric | Overall | Commercial | Personal |
|---|---:|---:|---:|
| **Loss Ratio** | 69.5% | 51.6% | 96.0% |
| **Expense Ratio** | 32.0% | 31.9% | 32.2% |
| **Combined Ratio** | **101.6%** | **83.5%** | **128.2%** |

Personal lines are underwater at 128.2%, dragging the overall ratio above 100% — matching Apex P&C's 102.4% target.

### 7.2 Stakeholder KPI Matrix

| Stakeholder | KPI | Formula | Frequency |
|---|---|---|---|
| Marcus Vance | Claims Frequency | (Total Claims / Active Policies) x 100 | Daily |
| Marcus Vance | Average Severity | Total Paid Amount / Settled Claims | Weekly |
| Marcus Vance | Fraud Detection Rate | (Flagged Claims / Total Claims) x 100 | Daily |
| Elena Rostova | Loss Ratio | (Incurred Losses / Earned Premium) x 100 | Monthly |
| Elena Rostova | Underwriting Profit | Earned Premium - (Losses + Expenses) | Monthly |
| Elena Rostova | Policy Binding Velocity | EFFECTIVE_DATE - BOUND_DATE | Weekly |
| Sid Patel | Policy Churn Rate | (Cancelled+NonRenewed / Active) x 100 | Weekly |
| Sid Patel | Premium Revenue at Risk | SUM(REVENUE_AT_RISK) from AT_RISK_POLICIES | Daily |
| Sid Patel | Agent Loss Ratio | Agent Claims Losses / Agent Earned Premium | Monthly |
| Trish Gallagher | Combined Ratio | Loss Ratio + Expense Ratio | Monthly |
| Trish Gallagher | Outstanding Receivables | SUM(OUTSTANDING_BALANCE) where overdue | Weekly |
| David Chen | Data Health Index | Passed Rules / Total Rules x 100 | Real-Time |
| David Chen | Column Anomaly Rate | Failed Columns / Total Monitored x 100 | Daily |
| Sarah Jenkins | Agent Commission Payout | SUM(Earned Premium x Commission Rate) | Monthly |

---

## 8. Categorical Value Reference

### ANALYTICS Tables

| Column | Values |
|---|---|
| POLICY_TYPE | **PersonalAuto, Homeowners, UmbrellaCoverage, CommercialMultiPeril, CommercialAuto, GeneralLiability, WorkersComp** |
| POLICY STATUS | InForce, Expired, Renewed, Cancelled, NonRenewed, Draft |
| COVERAGE_TIER | Basic, Standard, Preferred, Elite |
| CLAIM_TYPE | Collision, ComprehensiveOther, PropertyDamage, BodilyInjury, Fire, WaterDamage, WindHail, Theft, Liability, MedicalExpense, WorkersComp, **CommercialAutoLiability, UmbrellaExcess** |
| CLAIM STATUS | Open, UnderInvestigation, Approved, PartiallyPaid, Closed, Denied, Reopened, Subrogation |
| FNOL_CHANNEL | Phone, Web, Mobile, Agent, Email |
| REPORTED_BY | Insured, ThirdParty, Agent, Witness |
| CAUSE_OF_LOSS | Collision, Fire, Lightning, WindHail, Water, Theft, Vandalism, Liability, MedicalPayment, NaturalDisaster, EquipmentBreakdown |
| PAYMENT_STATUS | Paid, Partial, InGracePeriod, PastDue, SentToCollections, Waived, Refunded |
| BILLING_PLAN | DirectBill, AgencyBill, ListBill |
| PAYMENT_METHOD | ACH, CreditCard, DebitCard, Check, Wire, EFT, PayByPhone |
| RISK_TIER | Low, Moderate, Elevated, High, Critical |
| SEGMENT | **Standard (40.9%), Value (29.2%), Preferred (20.0%), HighNetWorth (9.9%)** |
| RISK_CATEGORY | **VoluntaryChurn (34.6%), InvoluntaryChurn (23.7%), Underinsured (15.8%), CompetitorSwitch (14.8%), ServiceDissatisfaction (11.2%)** |
| RETENTION_ACTION | AgentOutreach, DiscountOffer, PremiumReduction, CoverageReview, LoyaltyReward, AutoRenewLock, WinbackCampaign, None |
| AGENT SPECIALIZATION | **PersonalAuto (49), CommercialMultiPeril (22), Homeowners (21), GeneralLiability (18), MultiLine (15), WorkersComp (14), CommercialAuto (11)** |
| AGENT REGION | Northeast, Southeast, Midwest, West, Southwest |

### DATA_QUALITY Tables

| Column | Values |
|---|---|
| RULE_TYPE | Completeness, Uniqueness, Validity, Consistency, Timeliness |
| SEVERITY | Critical, High, Medium, Low |
| SOURCE_SYSTEM | Guidewire PolicyCenter, Guidewire ClaimCenter, Guidewire BillingCenter, Salesforce FSC, Salesforce Marketing Cloud, SharePoint, Monte Carlo, Informatica DQ |
| PIPELINE_NAME | gw_policycenter_daily, gw_claimcenter_daily, gw_billingcenter_daily, sfdc_fsc_sync, sfmc_churn_model, ecm_document_sync, ecm_chunking_pipeline, mc_dq_pipeline, mc_column_health, mc_anomaly_detector, idq_assertion_runner |

### DOCUMENTS Tables

| Column | Values |
|---|---|
| DOCUMENT_TYPE | PolicyContract, Endorsement, ExclusionSchedule, DeclarationPage, CertificateOfInsurance, ClaimForm, RegulatoryFiling, Exclusion, Rider |
| SOURCE_SYSTEM | SharePoint, DocuSign, InternalECM |

---

## 9. Entity Relationships

```
CUSTOMERS (5,017)
  ├── POLICIES (10,000)         via CUSTOMER_ID
  │     ├── CLAIMS (15,000)     via POLICY_ID
  │     ├── BILLING (25,000)    via POLICY_ID
  │     ├── AT_RISK (1,200)     via POLICY_ID
  │     └── POLICY_DOCS (2,000) via POLICY_ID
  │           └── DOC_CHUNKS (12,000) via DOCUMENT_ID
  └── [direct FK on CLAIMS, BILLING, AT_RISK via CUSTOMER_ID]

AGENTS (150)
  └── POLICIES (10,000)         via AGENT_ID

DQ_RULES (50)
  └── DQ_RESULTS (5,000)        via RULE_ID

DQ_SCORES (1,000)               standalone (per-table daily)
DQ_COLUMN_HEALTH (3,000)        standalone (per-column weekly)
```

---

## 10. Key Assumptions & Design Decisions

1. **Synthetic data** — All data is generated, not from real customers. ID patterns are deterministic (POL-00001, CUST-00001, CLM-00001, etc.).
2. **Guidewire-aligned terminology** — Policy types use Guidewire LOB codes (CommercialMultiPeril, PersonalAuto), claim statuses use ClaimCenter states (UnderInvestigation, Subrogation), billing uses BillingCenter concepts (DirectBill, grace periods, installment plans).
3. **Salesforce-aligned fields** — Customers have SALESFORCE_ACCOUNT_ID, HOUSEHOLD_ID, PREFERRED_CONTACT_METHOD, LIFE_EVENT_FLAG, ANNUAL_INCOME_RANGE. Agents have AGENCY_NAME, PRODUCER_CODE, COMMISSION_RATE, TOTAL_PREMIUM_BOOK.
4. **Apex P&C product portfolio** — 7 policy types: PersonalAuto, Homeowners, UmbrellaCoverage (Personal lines, 40% revenue) + CommercialMultiPeril, CommercialAuto, GeneralLiability, WorkersComp (Commercial lines, 60% revenue).
5. **Combined Ratio validated at 101.6%** — Matches Apex P&C's 102.4% target. Pre-aggregated claims query avoids join fan-out. Personal lines are unprofitable (128.2%), commercial lines are profitable (83.5%).
6. **EXPENSE_AMOUNT column** — Per-policy acquisition/admin cost enables Underwriting Profit and Combined Ratio KPIs. Average expense ratio: 32%.
7. **Fraud rate ~10%** — 9.9% of claims have FRAUD_SCORE > 80, matching the project requirement of ~10% flagged.
8. **3-year date range** — Claims and billing span Jan 2024 – Aug 2026, enabling YoY analysis. Policies span Sep 2023 – Aug 2026.
9. **Realistic distributions** — Customer segments, risk categories, and agent specializations are skewed (not uniform) to reflect real-world patterns.
10. **RBAC + masking** — 6 persona roles with dynamic data masking on EMAIL, PHONE, CREDIT_SCORE for FCRA/CCPA compliance.
11. **DQ pipeline traceability** — Every DQ rule maps to a SOURCE_SYSTEM and PIPELINE_NAME, enabling root-cause analysis.
12. **Evaluation methodology** — Ground truth generated by CoCo executing SQL directly against data (methodology #1, "build manually").

---

## 11. Regulatory Compliance

| Regulation | Requirement | How E.D.I.E. Addresses It |
|---|---|---|
| **State Insurance Departments** (CDI, TDI, OIR) | Rates filed per state; endorsements per state | POLICY_DOCUMENTS stores state-specific endorsements with FILING_STATE and FORM_NUMBER |
| **NAIC Reporting** | Quarterly/annual financial audits | DATA_QUALITY schema runs continuous checks on BILLING and CLAIMS before executive reports |
| **FCRA** | Restricts use of credit scores in AI decisions | MASK_CREDIT_SCORE policy hides scores from non-authorized roles |
| **CCPA/CPRA** | Consumer PII protection | MASK_EMAIL and MASK_PHONE policies restrict access; only EXECUTIVE/ACCOUNTADMIN see raw values |

---

## 12. SQL Patterns Used

### 12.1 Table Creation
All ANALYTICS and DATA_QUALITY tables created with `CREATE OR REPLACE TABLE` with explicit column types, NOT NULL constraints, and DEFAULT values. Documents tables altered with `ALTER TABLE ADD COLUMN`.

### 12.2 Data Population
Generated using Snowflake's `TABLE(GENERATOR(ROWCOUNT => N))` with deterministic formulas (`SEQ4()`, `MOD()`, `CASE WHEN`).

### 12.3 Semantic View Creation
Both views created via `CREATE SEMANTIC VIEW` DDL with TABLES, RELATIONSHIPS, FACTS, DIMENSIONS clauses.

### 12.4 RBAC & Masking
`CREATE ROLE`, `GRANT USAGE/SELECT`, `CREATE MASKING POLICY`, `ALTER TABLE MODIFY COLUMN SET MASKING POLICY`.

### 12.5 Evaluation Dataset
`CREATE TABLE` + `INSERT ... SELECT ... FROM VALUES` with `TO_VARIANT(OBJECT_CONSTRUCT(...))` for GROUND_TRUTH column. Registered via `CALL SYSTEM$CREATE_EVALUATION_DATASET(...)`.

---

## 13. What's Next

Potential next steps for this project:
- **Run the evaluation** — Execute the eval against EDIE to get baseline GPA scores
- **Build the Streamlit app** — Conversational chat with data visualizations, source citations, and Data Trust Badges
- **Add Data Trust Guardrails** — Auto-execute DQ_SCORES health checks before every output; badge each insight with freshness/null-rate
- **Add verified queries (VQRs)** — Improve Cortex Analyst accuracy with gold SQL examples
- **Optimize semantic views** — Run agentic optimization to auto-improve the models
- **Mount Marketplace data** — Cybersyn (NOAA weather, Census demographics, FRED CPI) for claims severity and underwriting risk enrichment
- **Update agent instructions** — Refine orchestration routing for edge cases found in eval
- **Deploy to CoWork** — Make EDIE available in Snowflake Intelligence for end users
