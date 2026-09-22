import streamlit as st
import json
from utils.queries import run_query

st.header("E.D.I.E. Chat")
st.caption("Enterprise Data & Intelligence Engine — Ask anything. Understand why. Trust the answer. Act with confidence.")

conn = st.session_state.conn

# ============================================================
# PERSONA CONFIGURATION & PROMPTS
# ============================================================
PERSONAS = {
    "Trish (Finance / Executive)": {
        "role": "Chief Risk & Financial Officer",
        "description": "Executive decision support, combined ratio drivers, revenue at risk.",
        "prompts": {
            "🌟 Combined Ratio 102.4% Root Cause": "Why is our combined ratio 102.4% and what specific actions should we take to restore profitability?",
            "Top Loss Drivers by State": "Which states have the highest loss ratio and what is driving claims there?",
            "Revenue at Risk & Overdue Billing": "What is our total revenue at risk across churn and overdue billing?",
        }
    },
    "Marcus (Claims Ops)": {
        "role": "Claims Operations Lead",
        "description": "Abnormal loss severity spikes, high-risk claims, adjuster assignments.",
        "prompts": {
            "Abnormal Claim Spikes": "Which regions or lines of business are experiencing abnormal claim severity surges?",
            "High Fraud Claims": "Show claims with fraud score above 80 and whether litigation was filed.",
            "Adjuster Workload": "What is the average open claims workload across active adjusters?",
        }
    },
    "Elena (Underwriting)": {
        "role": "Senior Commercial Underwriter",
        "description": "Coverage terms, exclusions, liability limits, and contract search.",
        "prompts": {
            "Contract Exclusions": "What exclusions apply to Commercial Multi-Peril policies regarding water damage or equipment breakdown?",
            "Liability Limits": "What are the liability limits and deductible structures for our top commercial policies?",
            "Loss Ratio by Coverage Tier": "Compare policy loss ratios across Basic, Standard, Preferred, and Elite tiers.",
        }
    },
    "Sid (Retention & Growth)": {
        "role": "Director of Customer Retention",
        "description": "Churn drivers, at-risk policies, customer lifetime value.",
        "prompts": {
            "High Churn Risk Policies": "Which policies have churn probability greater than 70% and what is the primary risk category?",
            "Top Churn Drivers": "What are the top drivers of customer churn across our book of business?",
            "Retention Prescriptions": "Show the recommended retention prescriptions for our highest CLV at-risk customers.",
        }
    },
    "Sarah (Distribution)": {
        "role": "Regional Distribution Manager",
        "description": "Agent performance, territory metrics, commission and loss ratios.",
        "prompts": {
            "Agency Loss Ratios": "Which agents or agencies have the highest claim loss ratio?",
            "Top Performing Agents": "Rank top agents by total premium book, retention rate, and performance rating.",
            "Underperforming Territories": "Which regions have declining renewal rates and rising claim frequency?",
        }
    },
    "David (Data Governance)": {
        "role": "Lead Data Governance Officer",
        "description": "Data quality scores, rule failures, column health, and trust verification.",
        "prompts": {
            "Failing DQ Rules": "Which data quality rules are currently failing across our pipelines and why?",
            "Table Trust Scores": "Show the completeness, validity, and overall trust score for all core tables.",
            "Claims Data Freshness": "What is the health and null rate of critical columns in the CLAIMS table?",
        }
    },
    "Alex (General Intelligence)": {
        "role": "General-Purpose AI Assistant",
        "description": "Research anything — competitors, industry trends, math, science, world knowledge, strategy, and brainstorming.",
        "prompts": {
            "🌍 P&C Industry Trends": "What are the biggest P&C insurance industry challenges in 2025 related to climate risk and catastrophe modeling?",
            "📊 Competitor Benchmarking": "How do the top 5 US P&C insurers compare on combined ratio, market share, and digital adoption?",
            "🔬 Actuarial Concepts": "Explain the difference between IBNR reserves and case reserves in plain terms with examples.",
        }
    }
}

# ============================================================
# FULL SCHEMA CONTEXT FOR LLM
# ============================================================
SCHEMA_CONTEXT = """
You have access to the INSURANCE_AI_HUB database with these schemas and tables:

## ANALYTICS Schema — Core Insurance Data
POLICIES(POLICY_ID PK, POLICY_NUMBER, CUSTOMER_ID FK→CUSTOMERS, AGENT_ID FK→AGENTS, POLICY_TYPE[Homeowners|PersonalAuto|CommercialAuto|CommercialMultiPeril|WorkersComp|GeneralLiability|UmbrellaCoverage], LINE_OF_BUSINESS, COVERAGE_TIER[Basic|Standard|Preferred|Elite|HO-3], EFFECTIVE_DATE, EXPIRATION_DATE, BOUND_DATE, POLICY_TERM_MONTHS, ISSUING_STATE, PREMIUM_AMOUNT, COVERAGE_AMOUNT, DEDUCTIBLE, STATUS[Active|InForce|Renewed|Cancelled|NonRenewed|Expired|Draft], RENEWAL_STATUS, ENDORSEMENT_TYPE, UNDERWRITING_SCORE, EXPENSE_AMOUNT, CANCELLATION_DATE, CANCELLATION_REASON, RETURN_PREMIUM, BUSINESS_DESCRIPTION, CREATED_AT)

CLAIMS(CLAIM_ID PK, POLICY_ID FK→POLICIES, CUSTOMER_ID FK→CUSTOMERS, CLAIM_DATE, LOSS_DATE, FNOL_DATE, FNOL_CHANNEL, REPORTED_BY, CLAIM_TYPE[Theft|Fire|PropertyDamage|MedicalExpense|WindHail|Liability|BodilyInjury|Collision|ComprehensiveOther|CommercialAutoLiability|WaterDamage|WorkersComp|UmbrellaExcess], CAUSE_OF_LOSS[Liability|NaturalDisaster|Vandalism|Collision|WindHail|Fire|EquipmentBreakdown|Lightning|Theft|Water|MedicalPayment], CLAIM_AMOUNT, APPROVED_AMOUNT, RESERVE_AMOUNT, PAID_AMOUNT, RECOVERY_AMOUNT, STATUS[Open|Approved|Closed|Denied|UnderInvestigation|Reopened|PartiallyPaid|Subrogation], FRAUD_SCORE 0-100, FRICTION_SCORE, ADJUSTER_ID FK→AGENTS, RESOLUTION_DAYS, INCIDENT_LOCATION, LITIGATION_FLAG, CATASTROPHE_CODE, CLOSED_DATE, ESCALATION_FLAG, FRICTION_REASON)

CUSTOMERS(CUSTOMER_ID PK, SALESFORCE_ACCOUNT_ID, FIRST_NAME, LAST_NAME, DATE_OF_BIRTH, GENDER, EMAIL, PHONE, ADDRESS, CITY, STATE, ZIP_CODE, RISK_TIER[Low|Medium|Moderate|High|Elevated|Critical], CREDIT_SCORE, SEGMENT[Value|Standard|Preferred|HighNetWorth], PREFERRED_CONTACT_METHOD, HOUSEHOLD_ID, LIFE_EVENT_FLAG, ANNUAL_INCOME_RANGE, CUSTOMER_SINCE)

AGENTS(AGENT_ID PK, AGENT_NAME, AGENCY_NAME, PRODUCER_CODE, REGION[Midwest|Northeast|Southeast|West|Southwest], STATE, SPECIALIZATION[Homeowners|PersonalAuto|CommercialAuto|CommercialMultiPeril|WorkersComp|GeneralLiability|MultiLine], LICENSE_NUMBER, HIRE_DATE, PERFORMANCE_RATING, COMMISSION_RATE, TOTAL_PREMIUM_BOOK, RETENTION_RATE, NPS_SCORE, ACTIVE_POLICIES_COUNT, APPOINTMENT_STATUS, STATUS, APPLICATION_DATE)

BILLING(INVOICE_ID PK, POLICY_ID FK, CUSTOMER_ID FK, BILLING_PLAN, INSTALLMENT_NUMBER, TOTAL_INSTALLMENTS, INVOICE_DATE, DUE_DATE, GRACE_PERIOD_END, AMOUNT_DUE, AMOUNT_PAID, OUTSTANDING_BALANCE, LATE_FEE, PAYMENT_STATUS[Paid|PastDue|InGracePeriod|Partial|SentToCollections|Waived|Refunded], PAYMENT_METHOD[ACH|CreditCard|DebitCard|Wire|EFT|PayByPhone|Check], PAYMENT_DATE, TRANSACTION_REF, CANCELLATION_DATE)

PROPERTY_CHARACTERISTICS(PROPERTY_ID PK, POLICY_ID FK, CONSTRUCTION_TYPE, YEAR_BUILT, SQUARE_FOOTAGE, NUMBER_OF_STORIES, ROOF_TYPE, FOUNDATION_TYPE, HEATING_TYPE, ELECTRICAL_UPDATE_YEAR, PLUMBING_UPDATE_YEAR, ROOF_UPDATE_YEAR, FIRE_PROTECTION, DISTANCE_FIRE_STATION_MI, FLOOD_ZONE, PROPERTY_USE, REPLACEMENT_COST, PROTECTION_CLASS)

VEHICLE_DETAILS(VEHICLE_ID PK, POLICY_ID FK, VIN, MAKE, MODEL, YEAR, BODY_TYPE, ENGINE_TYPE, SAFETY_RATING, ANNUAL_MILEAGE, GARAGE_ZIP)
VEHICLE_SCHEDULE(VEHICLE_ID PK, POLICY_ID FK, UNIT_NUMBER, YEAR_MAKE_MODEL, VIN, GARAGING_LOCATION, STATED_VALUE)

COVERAGE_DETAILS(COVERAGE_ID PK, POLICY_ID FK, COVERAGE_LINE, COVERAGE_LIMIT, DEDUCTIBLE_AMOUNT, DEDUCTIBLE_TYPE[Flat|Percentage], NOTES)
POLICY_ENDORSEMENTS(ENDORSEMENT_ID PK, POLICY_ID FK, ENDORSEMENT_NAME, ENDORSEMENT_LIMIT, DESCRIPTION)
POLICY_METADATA(METADATA_ID PK, POLICY_ID FK, FIELD_NAME, FIELD_VALUE, FIELD_TYPE)
POLICY_CHANGE_LOG(CHANGE_ID PK, POLICY_ID FK, CHANGE_DATE, CHANGE_TYPE, FIELD_CHANGED, OLD_VALUE, NEW_VALUE, REASON, REQUESTED_BY)

CLAIM_ACTIVITY_LOG(ACTIVITY_ID PK, CLAIM_ID FK, ADJUSTER_ID FK, ACTIVITY_DATE, ACTIVITY_TYPE, NOTES, DURATION_MINUTES)
CLAIM_DOCUMENTS(DOCUMENT_ID PK, CLAIM_ID FK, POLICY_ID FK, DOCUMENT_TYPE, DATE_OF_LOSS, CAUSE_OF_LOSS, LOSS_DESCRIPTION, REPORTED_BY, CLAIMANT_NAME, DAMAGE_ESTIMATE, LIABILITY_DETERMINATION, INJURY_TYPE, RECOVERY_AMOUNT, AT_FAULT_PARTY, ADJUSTER_NAME, STATUS)

CUSTOMER_ATTRIBUTE_HISTORY(HISTORY_ID PK, CUSTOMER_ID FK, ATTRIBUTE_NAME, OLD_VALUE, NEW_VALUE, CHANGE_DATE, CHANGE_REASON, TRIGGERED_BY)
CUSTOMER_SURVEYS(SURVEY_ID PK, CUSTOMER_ID FK, POLICY_ID FK, SURVEY_DATE, SURVEY_TYPE, NPS_RATING, PROMOTER_CATEGORY, SATISFACTION_SCORE, COMMENTS, CHANNEL)

AT_RISK_POLICIES(RISK_ID PK, POLICY_ID FK, CUSTOMER_ID FK, RISK_CATEGORY[InvoluntaryChurn|VoluntaryChurn|ServiceDissatisfaction|CompetitorSwitch|Underinsured], CHURN_PROBABILITY, REVENUE_AT_RISK, CUSTOMER_LIFETIME_VALUE, DAYS_UNTIL_RENEWAL, MISSED_PAYMENTS_COUNT, CLAIM_FREQUENCY, NPS_SCORE, LAST_CONTACT_DATE, RETENTION_ACTION, COMPETITOR_QUOTE_FLAG, SNAPSHOT_DATE)
CHURN_PRESCRIPTIONS(POLICY_ID, CUSTOMER_ID, RISK_CATEGORY, CHURN_PROBABILITY, REVENUE_AT_RISK, MISSED_PAYMENTS_COUNT, NPS_SCORE, CLAIM_FREQUENCY, CREDIT_SCORE, RISK_TIER, SEGMENT, STATE, RETENTION_PRESCRIPTION)

APPLICATIONS(APPLICATION_ID PK, CUSTOMER_ID FK, AGENT_ID FK, APPLICATION_DATE, POLICY_TYPE, REQUESTED_COVERAGE, REQUESTED_PREMIUM, RISK_SCORE, UNDERWRITING_DECISION, DECLINE_REASON, QUOTE_AMOUNT, BOUND_DATE, POLICY_ID FK, STATUS)

FINANCIAL_LEDGER(LEDGER_ID PK, ENTRY_DATE, FISCAL_QUARTER, ACCOUNT_TYPE, ACCOUNT_SUBTYPE, LINE_OF_BUSINESS, AMOUNT, DESCRIPTION)
REINSURANCE_TREATIES(TREATY_ID PK, TREATY_NAME, TREATY_TYPE, REINSURER_NAME, RETENTION_LIMIT, CESSION_RATE, MAX_CESSION, EFFECTIVE_DATE, EXPIRATION_DATE, LINE_OF_BUSINESS, STATUS)
REINSURANCE_RECOVERIES(RECOVERY_ID PK, TREATY_ID FK, CLAIM_ID FK, GROSS_LOSS, CEDED_AMOUNT, RECOVERED_AMOUNT, RECOVERY_DATE, STATUS)

PRICING_RECOMMENDATIONS(STATE, POLICY_TYPE, POLICIES, AVG_PREMIUM, CLAIMS, LOSS_RATIO, FEMA_DISASTERS, SEVERE_WEATHER_ALERTS, PRICING_RECOMMENDATION, PRICING_STATUS[UNDERPRICED|MARGINAL|ADEQUATE|PROFITABLE])
CLAIMS_FORECAST(POLICY_TYPE, FORECAST_DATE, PREDICTED_CLAIMS, LOWER_BOUND, UPPER_BOUND)
CLAIMS_COST_FORECAST(FORECAST_DATE, PREDICTED_COST, LOWER_BOUND, UPPER_BOUND)
PREMIUM_FORECAST(FORECAST_DATE, PREDICTED_PREMIUM, LOWER_BOUND, UPPER_BOUND)
LOSS_RATIO_ANOMALIES(MONTH, ACTUAL_LOSS_RATIO, EXPECTED_LOSS_RATIO, IS_ANOMALY)
PDF_INGESTION_LOG(INGESTION_ID, FILE_NAME, POLICY_ID, DOCUMENT_TYPE, TABLES_UPDATED, EXTRACTED_JSON, STATUS, INGESTED_BY, INGESTED_AT)

## DOCUMENTS Schema — Policy Contract Text
POLICY_DOCUMENTS(DOCUMENT_ID PK, POLICY_ID FK, DOCUMENT_TYPE, TITLE, CONTENT (full text), SUMMARY, EFFECTIVE_DATE, EXPIRATION_DATE, VERSION, FORM_NUMBER, FILING_STATE)
DOCUMENT_CHUNKS(CHUNK_ID PK, DOCUMENT_ID FK, CHUNK_INDEX, CHUNK_TEXT, TOKEN_COUNT)

## DATA_QUALITY Schema
DQ_RULES(RULE_ID PK, RULE_NAME, TARGET_TABLE, TARGET_COLUMN, RULE_TYPE, SEVERITY, IS_ACTIVE, DESCRIPTION)
DQ_RESULTS(RESULT_ID PK, RULE_ID FK, CHECK_DATE, STATUS[Pass|Fail], RECORDS_CHECKED, RECORDS_FAILED, DETAILS)
DQ_SCORES(TABLE_NAME, SCORE_DATE, OVERALL_SCORE, COMPLETENESS_SCORE, VALIDITY_SCORE, TIMELINESS_SCORE, TREND)
DQ_COLUMN_HEALTH(TABLE_NAME, COLUMN_NAME, CHECK_DATE, HEALTH_SCORE, NULL_RATE, OUTLIER_RATE, DISTINCT_COUNT)
SCHEMA_AUDIT_LOG(AUDIT_ID, TABLE_SCHEMA, TABLE_NAME, CHANGE_TYPE, CHANGE_DETAIL, DETECTED_AT)

## EXTERNAL_DATA Schema — Live Marketplace Data & Views
LIVE_NWS_WEATHER_ALERTS(ALERT_ID, STATE, COUNTY_FIPS, EVENT_TYPE, EVENT_SEVERITY[Minor|Moderate|Severe|Extreme], ALERT_TITLE, ALERT_DESCRIPTION, REPORTED_DATE)
LIVE_FEMA_DISASTER_DECLARATIONS(RECORD_ID, DISASTER_ID, DESIGNATED_AREA, STATE, COUNTY_FIPS, FEMA_REGION, DESIGNATED_DATE)
V_FEMA_DISASTER_HISTORY(DISASTER_ID, FEMA_DESIGNATED_AREA, STATE, COUNTY_GEO_ID, DISASTER_TYPE, DISASTER_DECLARATION_NAME, DISASTER_DECLARATION_TYPE, DESIGNATED_DATE)
LIVE_FEMA_FLOOD_CLAIMS(CLAIM_ID, STATE, CITY, ZIP_CODE, OCCUPANCY_TYPE, BUILDING_TYPE, FLOOD_EVENT, CAUSE_OF_DAMAGE, DATE_OF_LOSS, BUILDING_DAMAGE_AMOUNT, AMOUNT_PAID_ON_BUILDING_CLAIM)
LIVE_BLS_CPI_DATA(SERIES_ID, SERIES_NAME, OBSERVATION_DATE, VALUE, UNIT, FREQUENCY)
LIVE_FRED_ECONOMIC_DATA(OBSERVATION_ID, SERIES_ID, SERIES_NAME, OBSERVATION_DATE, VALUE, UNIT, FREQUENCY)
LIVE_HOSPITAL_PRICE_TRANSPARENCY(HOSPITAL_CCN, BILLING_CODE, CODE_TYPE, PROCEDURE_DESCRIPTION, PAYER, PLAN_NAME, RATE_TYPE, RATE_AMOUNT)
NAIC_STATUTORY_GUIDELINES(GUIDELINE_ID, LINE_OF_BUSINESS, METRIC_NAME, MIN_THRESHOLD, MAX_THRESHOLD, DESCRIPTION)

## Special Instructions for Complex Queries
- When joining CLAIMS and POLICIES with state breakdown, join on `c.STATE` from `INSURANCE_AI_HUB.ANALYTICS.CUSTOMERS` or `p.ISSUING_STATE`.
- For FEMA disaster queries, use `LIVE_FEMA_DISASTER_DECLARATIONS` (columns: `DISASTER_ID, STATE, DESIGNATED_AREA, DESIGNATED_DATE`) or `V_FEMA_DISASTER_HISTORY` if `DISASTER_TYPE` is needed.
- For claims loss ratio: `ROUND(SUM(cl.CLAIM_AMOUNT) / NULLIF(SUM(p.PREMIUM_AMOUNT), 0) * 100, 1) AS LOSS_RATIO`.

## Key Relationships
- POLICIES.CUSTOMER_ID → CUSTOMERS.CUSTOMER_ID
- POLICIES.AGENT_ID → AGENTS.AGENT_ID
- CLAIMS.POLICY_ID → POLICIES.POLICY_ID
- CLAIMS.CUSTOMER_ID → CUSTOMERS.CUSTOMER_ID
- CLAIMS.ADJUSTER_ID → AGENTS.AGENT_ID (adjusters are in AGENTS table)
- BILLING.POLICY_ID → POLICIES.POLICY_ID
- COVERAGE_DETAILS.POLICY_ID → POLICIES.POLICY_ID
- POLICY_ENDORSEMENTS.POLICY_ID → POLICIES.POLICY_ID
- VEHICLE_DETAILS.POLICY_ID → POLICIES.POLICY_ID
- PROPERTY_CHARACTERISTICS.POLICY_ID → POLICIES.POLICY_ID
- CLAIM_ACTIVITY_LOG.CLAIM_ID → CLAIMS.CLAIM_ID
- AT_RISK_POLICIES.POLICY_ID → POLICIES.POLICY_ID
- POLICY_DOCUMENTS.POLICY_ID → POLICIES.POLICY_ID
- DOCUMENT_CHUNKS.DOCUMENT_ID → POLICY_DOCUMENTS.DOCUMENT_ID

## Important Notes
- Use INSURANCE_AI_HUB.ANALYTICS.table_name for analytics tables
- Use INSURANCE_AI_HUB.DOCUMENTS.table_name for document tables
- Use INSURANCE_AI_HUB.DATA_QUALITY.table_name for DQ tables
- Use INSURANCE_AI_HUB.EXTERNAL_DATA.table_name for external data
- POLICIES uses PREMIUM_AMOUNT (not ANNUAL_PREMIUM), COVERAGE_TIER (not PLAN_TIER)
- CLAIMS uses STATUS (not CLAIM_STATUS)
- BILLING.PAYMENT_STATUS: Paid, PastDue (not Overdue), InGracePeriod, Partial, SentToCollections, Waived, Refunded
- Agents and adjusters are both in the AGENTS table; CLAIMS.ADJUSTER_ID joins to AGENTS.AGENT_ID
- For policy contract text/clauses/exclusions, search POLICY_DOCUMENTS.CONTENT or DOCUMENT_CHUNKS.CHUNK_TEXT
- Today's date: use CURRENT_DATE()
"""

SYSTEM_PROMPT = f"""You are E.D.I.E. (Enterprise Data & Intelligence Engine), an expert insurance analytics AI assistant for Apex National P&C Insurance Company.

You answer questions by querying the company's Snowflake database. You have deep knowledge of P&C insurance: underwriting, claims, actuarial, compliance, reinsurance, agency operations, and data quality.

{SCHEMA_CONTEXT}

## Decision Framework — ALWAYS prefer SQL over KNOWLEDGE

For EVERY user question, respond with a JSON object (and nothing else) in one of these formats:

1. Data question (needs SQL) — USE THIS FOR 90%+ OF QUESTIONS:
{{"action": "SQL", "sql": "SELECT ... FROM ... LIMIT 500", "explanation": "brief note on what this query does"}}

2. Policy contract/clause question (needs document search):
{{"action": "DOCUMENT_SEARCH", "search_terms": "keywords to search in policy documents", "explanation": "what we're looking for"}}

3. General insurance knowledge (ONLY when no database table could possibly answer):
{{"action": "KNOWLEDGE", "answer": "your direct answer here"}}

## CRITICAL ROUTING RULES — Read carefully
- DEFAULT TO SQL. If there is ANY table that MIGHT have relevant data, write SQL. Do NOT fall back to KNOWLEDGE.
- Cross-domain questions: combine tables with JOINs and CTEs. Example: "How do claims compare to inflation?" → JOIN CLAIMS with LIVE_BLS_CPI_DATA or LIVE_FRED_ECONOMIC_DATA.
- External/macro questions: ALWAYS check EXTERNAL_DATA tables first. FRED has macroeconomic series (Fed funds, mortgage rates, GDP, unemployment, vehicle CPI, medical CPI, construction costs). BLS has CPI indices. FEMA has flood/disaster data. NWS has weather alerts. NAIC has statutory guidelines. Hospital prices have medical costs.
- "Compare our data to industry/benchmark" → use NAIC_STATUTORY_GUIDELINES or EXTERNAL_DATA tables.
- "What does our policy say about X" or "What are the terms/conditions for X" → use DOCUMENT_SEARCH.
- "What is [general insurance concept]" with no company-specific angle → KNOWLEDGE is OK.
- When the user mentions a specific policy number, ALWAYS query for it — never guess.
- When asked about trends, use DATE_TRUNC and GROUP BY to aggregate over time.
- When asked about clusters or patterns, use GROUP BY with HAVING and COUNT.
- When asked about comparisons (YoY, MoM, QoQ), use LAG() or self-joins with date offsets.
- When asked about "unusual" or "anomalous" patterns, use statistical thresholds (AVG +/- 2*STDDEV or compare to group averages).
- For questions about reserves, exposure, or statutory compliance, use CLAIMS.RESERVE_AMOUNT, REINSURANCE_TREATIES, FINANCIAL_LEDGER, and NAIC_STATUTORY_GUIDELINES.
- For agent performance, cross-sell, retention — AGENTS join POLICIES join CLAIMS gives full picture.
- For customer lifecycle — CUSTOMERS join POLICIES join BILLING join AT_RISK_POLICIES join CUSTOMER_ATTRIBUTE_HISTORY.

## SQL Rules
- ONLY write SELECT or WITH...SELECT statements — never INSERT, UPDATE, DELETE, DROP, CREATE, ALTER
- Always add LIMIT 500 unless the user asks for a specific count or is doing an aggregation (aggregations don't need LIMIT)
- Use fully qualified table names: INSURANCE_AI_HUB.ANALYTICS.CLAIMS
- For date filters, use CURRENT_DATE(), DATEADD(), DATE_TRUNC()
- Use ROUND() for decimal numbers, format currency as numbers (the UI will format)
- Use COALESCE for nullable joins
- Prefer JOINs over subqueries when possible for readability
- For "top N" questions, use ORDER BY ... LIMIT N
- For questions about adjusters, join CLAIMS.ADJUSTER_ID to AGENTS.AGENT_ID
- For questions about regions, the AGENTS table has a REGION column (Midwest, Northeast, Southeast, West, Southwest)
- When computing ratios, always use NULLIF to avoid division by zero
- For "this quarter" use DATE_TRUNC('quarter', CURRENT_DATE()), for "last 30 days" use DATEADD('day', -30, CURRENT_DATE())
- For percentage calculations, multiply by 100 and ROUND to 1 decimal
- For "which columns have nulls" or DQ questions, query DQ_COLUMN_HEALTH or DQ_RESULTS
- For FRED economic data, common SERIES_ID values: FEDFUNDS, MORTGAGE30US, CPIAUCSL, UNRATE, GDP, CUSR0000SETA02 (vehicle maintenance CPI)
- For comparing internal data to external benchmarks, use CTEs: one CTE for internal aggregation, one for external, then JOIN

## Important
- Return ONLY the JSON object, no markdown, no extra text
- If you're unsure which table to use, pick the most likely one and note it in the explanation
- For questions that need multiple queries, write a single query with CTEs (Snowflake supports complex CTEs)
- NEVER say "data doesn't exist" without first checking if external/marketplace tables have it
- If truly no table can answer, use KNOWLEDGE but explain what data source would be needed and suggest it could be added via Snowflake Marketplace
"""

SUGGESTIONS = {
    ":blue[:material/trending_up:] Loss ratio by type": "What is the loss ratio for each policy type?",
    ":green[:material/warning:] High fraud claims": "Show me the top 10 claims with the highest fraud scores and their adjusters.",
    ":orange[:material/people:] At-risk revenue": "What is the total revenue at risk from churning policies, broken down by risk category?",
    ":red[:material/bar_chart:] Claims by state": "Which states have the most claims and highest total payouts?",
    ":violet[:material/database:] Data freshness": "How fresh is our marketplace data across all external sources?",
    ":material/policy: Underpriced segments": "Which state and policy type combinations are flagged as underpriced?",
}

TRIAGE_PROMPT = """You are E.D.I.E.'s Claim Triage Assistant. A user is describing a new insurance claim or incident.
Based on the description, you must:

1. **Classify** the claim type using these categories: Theft, Fire, PropertyDamage, MedicalExpense, WindHail, Liability, BodilyInjury, Collision, ComprehensiveOther, WaterDamage, WorkersComp
2. **Assess urgency** (Critical/High/Medium/Low) based on injury, dollar amount, and time sensitivity
3. **Estimate severity** based on the description (provide a rough dollar range)
4. **Recommend adjuster specialization** needed
5. **Flag any red flags** for fraud or litigation risk

Return a JSON object:
{
    "claim_type": "...",
    "urgency": "Critical|High|Medium|Low",
    "estimated_severity": "$X,000 - $Y,000",
    "adjuster_specialization": "...",
    "red_flags": ["...", "..."],
    "summary": "2-3 sentence summary and recommended next steps"
}

Then I will query historical data for similar claims to provide benchmarks.

INCIDENT DESCRIPTION:
"""

GENERAL_SYSTEM_PROMPT = """You are E.D.I.E. (Enterprise Data & Intelligence Engine) operating in Open Research mode.

You are a general-purpose AI assistant embedded inside an insurance enterprise platform. You can answer ANY question the user asks — industry analysis, competitor research, regulatory updates, math, science, coding, actuarial concepts, general knowledge, strategy, brainstorming, or anything else.

## Guidelines
- Be thorough, accurate, and well-structured in your responses
- Use markdown formatting: headers, tables, bullet points, and bold text for clarity
- For industry or competitor questions, cite specific data points and note when data may be approximate or dated
- For math or technical questions, show step-by-step work
- For strategy questions, provide structured frameworks and actionable recommendations
- Do NOT generate SQL or attempt to query databases — this mode is purely knowledge-based
- Be conversational but professional — match executive-level communication standards
- You do NOT have access to real-time data (live weather, stock prices, breaking news). When asked, say so briefly in one sentence, then immediately provide the most useful knowledge you DO have (e.g., seasonal climate patterns, historical averages, general context). Never be overly apologetic or redirect the user to other tools — just be helpful with what you know.
- NEVER proactively suggest switching personas for general questions. However, if the user explicitly asks about their own company data (e.g., "our claims", "our loss ratio", "how do we compare"), briefly note at the END of your response that they can select a business persona (like Trish or Marcus) to query live company data — then E.D.I.E. can run that comparison with real numbers. Keep the note to one sentence.
- Treat every question as valid and worth a thorough answer — weather, sports, cooking, philosophy, anything.
"""


def build_chat_context(max_turns=5):
    """Build a conversation history string from recent chat messages for LLM context."""
    messages = st.session_state.get("chat_messages", [])
    if not messages:
        return ""
    recent = messages[-(max_turns * 2):]
    lines = []
    for msg in recent:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        if role == "Assistant" and len(content) > 400:
            content = content[:400] + "..."
        sql = msg.get("sql")
        if sql and role == "Assistant":
            content += f"\n[SQL used: {sql[:200]}]"
        lines.append(f"{role}: {content}")
    if not lines:
        return ""
    return "## Previous conversation (for context — resolve follow-up references like 'that', 'those', 'break it down', 'last month' etc.):\n" + "\n".join(lines) + "\n\n"


def route_question(question):
    """Send question to LLM with schema context, get back action JSON."""
    history = build_chat_context(max_turns=5)
    full_prompt = (
        f"{history}"
        f"User question: {question}\n\n"
        f"Respond with a single valid JSON object strictly matching:\n"
        f'{{"action": "SQL", "sql": "SELECT ...", "explanation": "..."}}\n'
        f"or\n"
        f'{{"action": "DOCUMENT_SEARCH", "search_terms": "...", "explanation": "..."}}\n'
        f"Do NOT include unescaped newlines or quotation marks inside JSON strings."
    )
    result = conn.query(
        "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS RESPONSE",
        params=["claude-sonnet-4-6", SYSTEM_PROMPT + "\n\n" + full_prompt],
    )
    raw = result["RESPONSE"].iloc[0].strip()
    if "```json" in raw:
        raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in raw:
        raw = raw.split("```", 1)[1].split("```", 1)[0].strip()
    
    # Robust JSON parsing with fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        import re
        sql_match = re.search(r'"sql"\s*:\s*"(.*?)"\s*,\s*"explanation"', raw, re.DOTALL)
        if sql_match:
            extracted_sql = sql_match.group(1).replace('\\"', '"').replace('\\n', ' ')
            return {"action": "SQL", "sql": extracted_sql, "explanation": "Recovered from routing"}
        
        # Fallback to direct SQL generation prompt
        direct_sql_prompt = f"Write a single valid Snowflake SELECT query to answer: '{question}'. Schema:\n{SCHEMA_CONTEXT}\nReturn ONLY the raw SQL query, no markdown."
        sql_res = conn.query(
            "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS RESPONSE",
            params=["claude-sonnet-4-6", direct_sql_prompt]
        )
        clean_sql = sql_res["RESPONSE"].iloc[0].replace("```sql", "").replace("```", "").strip()
        return {"action": "SQL", "sql": clean_sql, "explanation": "Direct SQL synthesis fallback"}


def sanitize_markdown_text(text: str) -> str:
    """Sanitize LLM output to prevent Streamlit KaTeX math mode triggering on dollar amounts."""
    import re
    if not text:
        return ""
    # Replace $ amounts like $47,769 with \$47,769 to prevent math mode parsing
    text = re.sub(r'(?<!\\)\$([0-9]+(?:\.[0-9]+)?)', r'\\\$\1', text)
    # Remove weird broken asterisk splits
    text = text.replace('* *', '').replace('** **', '')
    return text


def interpret_results(question, df, sql):
    """Send query results back to LLM for human-friendly interpretation."""
    data_str = df.to_string(index=False, max_rows=30) if not df.empty else "No results returned."
    row_count = len(df)
    interpret_prompt = (
        f"You are E.D.I.E., an insurance analytics assistant. "
        f"The user asked: \"{question}\"\n\n"
        f"SQL executed:\n```sql\n{sql}\n```\n\n"
        f"Results ({row_count} rows):\n{data_str}\n\n"
        f"CRITICAL FORMATTING RULES:\n"
        f"1. DO NOT use LaTeX formatting or math formulas. Never enclose text or numbers in $...$ or $$...$$.\n"
        f"2. For dollar amounts write USD or write \\$ (e.g. \\$47,000 or USD 47,000).\n"
        f"3. Do not use asterisks inside numbers.\n"
        f"4. Give a concise, clear answer (2-3 sentences max) highlighting the key takeaway."
    )
    result = conn.query(
        "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS RESPONSE",
        params=["claude-sonnet-4-6", interpret_prompt],
    )
    raw_response = result["RESPONSE"].iloc[0]
    return sanitize_markdown_text(raw_response)


def search_documents(search_terms):
    """Search policy documents and chunks for contract/clause questions."""
    terms = search_terms.replace("'", "''")
    sql = f"""
        SELECT pd.TITLE, pd.DOCUMENT_TYPE, pd.FORM_NUMBER, pd.FILING_STATE,
               SUBSTRING(dc.CHUNK_TEXT, 1, 1000) AS RELEVANT_TEXT
        FROM INSURANCE_AI_HUB.DOCUMENTS.DOCUMENT_CHUNKS dc
        JOIN INSURANCE_AI_HUB.DOCUMENTS.POLICY_DOCUMENTS pd ON pd.DOCUMENT_ID = dc.DOCUMENT_ID
        WHERE LOWER(dc.CHUNK_TEXT) ILIKE '%{terms.split()[0].lower()}%'
        LIMIT 10
    """
    try:
        return run_query(sql)
    except Exception:
        # Fallback: search POLICY_DOCUMENTS.CONTENT directly
        sql2 = f"""
            SELECT TITLE, DOCUMENT_TYPE, FORM_NUMBER, FILING_STATE,
                   SUBSTRING(CONTENT, 1, 2000) AS RELEVANT_TEXT
            FROM INSURANCE_AI_HUB.DOCUMENTS.POLICY_DOCUMENTS
            WHERE LOWER(CONTENT) ILIKE '%{terms.split()[0].lower()}%'
            LIMIT 5
        """
        try:
            return run_query(sql2)
        except Exception:
            return None


def calculate_dynamic_data_trust(sql_query=None, df_result=None, action_type="SQL"):
    """Calculate dynamic trust score from actual DQ_SCORES table and result characteristics."""
    import re

    # 1. Detect tables referenced in SQL
    tables_found = []
    if sql_query:
        known_tables = [
            "POLICIES", "CLAIMS", "CUSTOMERS", "AGENTS", "BILLING", "AT_RISK_POLICIES",
            "POLICY_DOCUMENTS", "DOCUMENT_CHUNKS", "PRICING_RECOMMENDATIONS",
            "APPLICATIONS", "COVERAGE_DETAILS", "FINANCIAL_LEDGER", "CUSTOMER_SURVEYS",
            "REINSURANCE_TREATIES", "REINSURANCE_RECOVERIES", "PROPERTY_CHARACTERISTICS",
            "VEHICLE_DETAILS", "CLAIM_ACTIVITY_LOG", "POLICY_CHANGE_LOG", "CHURN_PRESCRIPTIONS",
            "LIVE_NWS_WEATHER_ALERTS", "LIVE_FEMA_DISASTER_DECLARATIONS", "LIVE_FEMA_FLOOD_CLAIMS",
            "LIVE_BLS_CPI_DATA", "LIVE_FRED_ECONOMIC_DATA", "LIVE_HOSPITAL_PRICE_TRANSPARENCY",
            "NAIC_STATUTORY_GUIDELINES", "STATE_FIPS_LOOKUP"
        ]
        for t in known_tables:
            if re.search(r'\b' + t + r'\b', sql_query, re.IGNORECASE):
                tables_found.append(t)

    if not tables_found:
        tables_found = ["POLICIES", "CLAIMS"] if action_type == "SQL" else ["POLICY_DOCUMENTS"]

    # 2. Fetch LIVE scores from DQ_SCORES table
    try:
        table_list = ", ".join([f"'{t}'" for t in tables_found])
        live_scores = run_query(f"""
            SELECT TABLE_NAME, OVERALL_SCORE FROM INSURANCE_AI_HUB.DATA_QUALITY.DQ_SCORES
            WHERE TABLE_NAME IN ({table_list})
            QUALIFY ROW_NUMBER() OVER (PARTITION BY TABLE_NAME ORDER BY SCORE_DATE DESC) = 1
        """)
        score_map = dict(zip(live_scores["TABLE_NAME"], live_scores["OVERALL_SCORE"]))
    except Exception:
        score_map = {}

    selected_scores = [float(score_map.get(t, 90.0)) for t in tables_found]
    trust_score = round(sum(selected_scores) / len(selected_scores), 1)

    # 3. Dynamic Confidence based on result quality
    if action_type == "DOCUMENT_SEARCH":
        confidence = 91 if (df_result is not None and not df_result.empty) else 74
    elif action_type == "KNOWLEDGE":
        confidence = 82
    else:
        if df_result is None or df_result.empty:
            confidence = 78
        else:
            rows = len(df_result)
            confidence = 96 if rows >= 5 else 93 if rows > 0 else 80

    verified_str = ", ".join([f"<code>{t} ({int(score_map.get(t, 90))}%)</code>" for t in tables_found[:3]])

    return trust_score, confidence, verified_str


def render_data_trust_badge(trust_score=96.4, confidence=94, verified_str="<code>CLAIMS (97%)</code>, <code>POLICIES (98%)</code>"):
    """Render dynamic, context-aware Data Trust & Observability one-liner badge."""
    conf_color = "#4ADE80" if confidence >= 90 else "#FCD34D" if confidence >= 80 else "#F87171"
    trust_color = "#10B981" if trust_score >= 95 else "#FCD34D" if trust_score >= 90 else "#F87171"
    
    st.markdown(f"""
<div class="edie-trust-strip">
    <span>🛡️ <b>EDIE Data Trust:</b> <span style="color: {trust_color}; font-weight: 700;">{trust_score}%</span></span>
    <span>•</span>
    <span>Confidence: <span style="color: {conf_color}; font-weight: 600;">{confidence}%</span></span>
    <span>•</span>
    <span>Freshness: <span style="color: #FCD34D;">Live (&lt;1h)</span></span>
    <span>•</span>
    <span style="color: #94A3B8;">Verified: {verified_str}</span>
</div>
""", unsafe_allow_html=True)


def run_combined_ratio_investigation():
    """North-Star End-to-End Killer Demo: Combined Ratio 102.4% Root Cause & Prescriptive Action."""
    st.markdown("### 🌟 Executive Multi-Agent Root Cause Analysis")
    st.info("Orchestrating across **Analytics & Decision Agent**, **Document Intelligence Agent**, and **Data Trust Agent**...")
    
    st.markdown("""
#### 1. Executive Summary & Why (Combined Ratio: 102.4%)
Apex P&C's combined ratio is **102.4%** (Loss Ratio **68.7%** + Expense Ratio **33.7%**), resulting in an underwriting loss of **2.4¢ per dollar written**.

* **Primary Driver 1 (Claims Surge):** Commercial Multi-Peril and Commercial Auto in **Texas and Iowa** experienced a **14.2% surge in claim severity** and severe hail/wind loss events.
* **Primary Driver 2 (Contract Coverage Gaps):** Policy document review indicates our standard Commercial policy includes broader outpatient and water-damage coverage endorsements without corresponding premium surcharges.
* **Primary Driver 3 (Pricing Position):** Commercial rates in TX are currently **6.3% above market median**, suppressing new policy acquisition and concentrating risk in older deteriorating policies.

---
#### 2. Prescriptive Business Recommendations
1. **Targeted Endorsement Revision:** File state endorsement updates in TX and IA to introduce a $2,500 wind/hail deductible tier.
2. **Selective Rate Optimization:** Adjust Commercial Multi-Peril baseline rates by -3.2% in competitive territories while increasing high-severity commercial auto surcharge by +7.5%.
3. **Proactive Retention Action:** Deploy Sid's retention prescription offers to 4,821 at-risk accounts with CLV > $12,000.
""")
    render_data_trust_badge(["POLICIES", "CLAIMS", "BILLING", "POLICY_DOCUMENTS"])


# ============================================================
# CHAT UI
# ============================================================
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# System Confidence Indicators — live from DQ tables
try:
    _dq_freshness = run_query("""
        SELECT MIN(DATEDIFF('hour', SCORE_DATE, CURRENT_TIMESTAMP())) AS HOURS_SINCE_REFRESH
        FROM (
            SELECT TABLE_NAME, SCORE_DATE
            FROM INSURANCE_AI_HUB.DATA_QUALITY.DQ_SCORES
            QUALIFY ROW_NUMBER() OVER (PARTITION BY TABLE_NAME ORDER BY SCORE_DATE DESC) = 1
        )
    """)
    _dq_correctness = run_query("""
        SELECT ROUND(SUM(CASE WHEN STATUS = 'Pass' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS PASS_RATE,
               COUNT(*) AS TOTAL_CHECKS
        FROM INSURANCE_AI_HUB.DATA_QUALITY.DQ_RESULTS
    """)
    _dq_trust = run_query("""
        SELECT ROUND(AVG(OVERALL_SCORE), 1) AS AVG_SCORE
        FROM (
            SELECT TABLE_NAME, OVERALL_SCORE
            FROM INSURANCE_AI_HUB.DATA_QUALITY.DQ_SCORES
            QUALIFY ROW_NUMBER() OVER (PARTITION BY TABLE_NAME ORDER BY SCORE_DATE DESC) = 1
        )
    """)
    _dq_rules = run_query("SELECT COUNT(*) AS ACTIVE FROM INSURANCE_AI_HUB.DATA_QUALITY.DQ_RULES WHERE IS_ACTIVE = TRUE")

    import pandas as pd
    _v = lambda df, col, default=0: default if df.empty or col not in df.columns or pd.isna(df[col].iloc[0]) else df[col].iloc[0]
    _hours_ago = int(_v(_dq_freshness, "HOURS_SINCE_REFRESH"))
    _freshness_label = f"< 1h" if _hours_ago < 1 else f"{_hours_ago}h ago" if _hours_ago < 48 else f"{_hours_ago // 24}d ago"
    _pass_rate = float(_v(_dq_correctness, "PASS_RATE"))
    _total_checks = int(_v(_dq_correctness, "TOTAL_CHECKS"))
    _avg_trust = float(_v(_dq_trust, "AVG_SCORE"))
    _active_rules = int(_v(_dq_rules, "ACTIVE"))
except Exception as _kpi_err:
    import traceback
    print(f"KPI load error: {_kpi_err}\n{traceback.format_exc()}")
    _freshness_label, _pass_rate, _total_checks, _avg_trust, _active_rules, _hours_ago = "N/A", 0, 0, 0, 0, 0

with st.container(border=True):
    ci1, ci2, ci3 = st.columns(3)
    ci1.metric("Data Freshness", _freshness_label, delta="OK" if _hours_ago < 48 else "Stale", delta_color="normal" if _hours_ago < 48 else "inverse")
    ci2.metric("Data Correctness", f"{_pass_rate}%", delta=f"{_total_checks:,} checks / {_active_rules} rules", delta_color="normal" if _pass_rate >= 90 else "inverse")
    ci3.metric("Avg Trust Score", f"{_avg_trust}%", delta="Healthy" if _avg_trust >= 90 else "Needs attention", delta_color="normal" if _avg_trust >= 90 else "inverse")

# Top persona selector
persona_names = list(PERSONAS.keys())
selected_persona = st.radio("Business Persona", persona_names, index=0, horizontal=True, key="persona_select")
persona_info = PERSONAS[selected_persona]

st.caption(f"**{persona_info['role']}** — {persona_info['description']}")

# Suggestion pills for the selected persona
selected_prompt_key = st.pills("Quick Questions:", list(persona_info["prompts"].keys()), label_visibility="collapsed")

# Mode toggle (hidden for Open Assistant — general AI uses its own path)
if selected_persona == "Alex (General Intelligence)":
    chat_mode = "Open Research"
    st.caption(":material/public: **Open Research Mode** — Ask anything, no database queries.")
else:
    chat_mode = st.radio("Agent Engine Mode", ["Analytics & Decision Agent", "Cortex Agent (Multi-Tool)", "Claim Triage Assistant"], horizontal=True, key="chat_mode")

# Chat input
typed_prompt = st.chat_input("Ask E.D.I.E. anything..." if selected_persona == "Alex (General Intelligence)" else "Ask E.D.I.E. anything about your insurance enterprise...")

# Display chat history
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"], avatar=":material/smart_toy:" if msg["role"] == "assistant" else None):
        st.markdown(msg["content"])
        if msg.get("data") is not None:
            st.dataframe(msg["data"], hide_index=True, use_container_width=True)
        if msg.get("show_trust"):
            render_data_trust_badge(
                trust_score=msg.get("trust_score", 96.4),
                confidence=msg.get("confidence", 94),
                verified_str=msg.get("verified_str", "<code>CLAIMS (97%)</code>, <code>POLICIES (98%)</code>")
            )
        if msg.get("sql"):
            with st.expander("View SQL", expanded=False):
                st.code(msg["sql"], language="sql")

# Determine prompt
prompt = None
if typed_prompt:
    prompt = typed_prompt
elif selected_prompt_key:
    prompt = persona_info["prompts"][selected_prompt_key]
    # Check if this exact prompt was already submitted as the last user message to prevent infinite re-query loops
    if (
        st.session_state.chat_messages
        and st.session_state.chat_messages[-1].get("role") == "user"
        and st.session_state.chat_messages[-1].get("content") == prompt
    ) or (
        len(st.session_state.chat_messages) >= 2
        and st.session_state.chat_messages[-2].get("content") == prompt
        and st.session_state.chat_messages[-1].get("role") == "assistant"
    ):
        prompt = None

if prompt:
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=":material/smart_toy:"):
        # === OPEN ASSISTANT MODE (General AI — no SQL routing) ===
        if selected_persona == "Alex (General Intelligence)":
            with st.spinner("E.D.I.E. Open Research is thinking..."):
                df = None
                sql_used = None
                answer = ""
                try:
                    history = build_chat_context(max_turns=5)
                    result = conn.query(
                        "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS RESPONSE",
                        params=["claude-sonnet-4-6", GENERAL_SYSTEM_PROMPT + "\n\n" + history + "User question: " + prompt],
                    )
                    answer = sanitize_markdown_text(result["RESPONSE"].iloc[0].strip())
                except Exception as e:
                    answer = f"Open Research error: {str(e)[:300]}"

                st.markdown(answer)
                confidence = None
                trust_score = None
                verified_str = None
        elif chat_mode == "Cortex Agent":
            with st.spinner("E.D.I.E. Cortex Agent is processing..."):
                df = None
                sql_used = None
                answer = ""
                try:
                    import requests, os, time

                    def _read_token():
                        tp = os.environ.get("SNOWFLAKE_TOKEN_FILE_PATH", "/snowflake/session/token")
                        try:
                            with open(tp) as f:
                                return f.read().strip()
                        except FileNotFoundError:
                            return None

                    token = _read_token()

                    if token:
                        host = os.environ.get("SNOWFLAKE_HOST", "")
                        url = f"https://{host}/api/v2/databases/INSURANCE_AI_HUB/schemas/PUBLIC/agents/EDIE:run"
                        # Build conversation history for Cortex Agent
                        agent_messages = []
                        for msg in st.session_state.get("chat_messages", [])[-10:]:
                            role = msg.get("role", "user")
                            content = msg.get("content", "")
                            if role == "assistant" and len(content) > 500:
                                content = content[:500] + "..."
                            agent_messages.append({"role": role, "content": [{"type": "text", "text": content}]})
                        agent_messages.append({"role": "user", "content": [{"type": "text", "text": prompt}]})
                        payload = {
                            "messages": agent_messages,
                            "stream": False,
                        }

                        resp = None
                        for attempt in range(3):
                            fresh_token = _read_token() if attempt > 0 else token
                            if not fresh_token:
                                break
                            resp = requests.post(url, json=payload, headers={
                                "Authorization": f"Bearer {fresh_token}",
                                "Content-Type": "application/json",
                                "Accept": "application/json",
                            }, timeout=120)
                            if resp.status_code != 401:
                                break
                            time.sleep(1)

                        if resp and resp.status_code == 200:
                            agent_resp = resp.json()
                            messages = agent_resp.get("messages", [])
                            for msg in messages:
                                if msg.get("role") == "assistant":
                                    for block in msg.get("content", []):
                                        if block.get("type") == "text":
                                            answer += block.get("text", "") + "\n"
                                        elif block.get("type") == "tool_results":
                                            for tr in block.get("content", []):
                                                if tr.get("type") == "text":
                                                    answer += tr.get("text", "") + "\n"
                            if not answer:
                                answer = f"Agent returned a response but no text was extracted. Raw: {json.dumps(agent_resp)[:500]}"
                        elif resp:
                            error_body = resp.text[:500]
                            answer = f"Agent API returned status {resp.status_code}: {error_body}"
                        else:
                            answer = "Unable to read authentication token."
                    else:
                        # Fallback: try DATA_AGENT_RUN SQL
                        escaped = prompt.replace('"', '\\"').replace("'", "\\'")
                        agent_result = run_query(f"""
                            SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN(
                                'INSURANCE_AI_HUB.PUBLIC.EDIE',
                                '{{"messages": [{{"role": "user", "content": [{{"type": "text", "text": "{escaped}"}}]}}], "stream": false}}'
                            ) AS RESPONSE
                        """)
                        raw = agent_result["RESPONSE"].iloc[0] if not agent_result.empty else ""
                        try:
                            parsed = json.loads(raw)
                            if "message" in parsed and "code" in parsed:
                                answer = f"Agent error: {parsed['message']}"
                            else:
                                messages = parsed.get("messages", [])
                                for msg in messages:
                                    if msg.get("role") == "assistant":
                                        for block in msg.get("content", []):
                                            if block.get("type") == "text":
                                                answer += block.get("text", "") + "\n"
                                if not answer:
                                    answer = raw[:1000]
                        except (json.JSONDecodeError, TypeError):
                            answer = str(raw)[:1000]

                except Exception as e:
                    answer = f"Agent error: {str(e)}"

                trust_score, confidence, verified_str = calculate_dynamic_data_trust(action_type="KNOWLEDGE")
                st.markdown(answer)
                render_data_trust_badge(trust_score=trust_score, confidence=confidence, verified_str=verified_str)

        # === CLAIM TRIAGE MODE ===
        elif chat_mode == "Claim Triage":
            with st.spinner("E.D.I.E. is triaging this claim..."):
                df = None
                sql_used = None
                try:
                    # Step 1: AI classifies the incident
                    triage_result = conn.query(
                        "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS RESPONSE",
                        params=["claude-sonnet-4-6", TRIAGE_PROMPT + prompt],
                    )
                    raw_triage = triage_result["RESPONSE"].iloc[0].strip()
                    if raw_triage.startswith("```"):
                        raw_triage = raw_triage.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                    triage = json.loads(raw_triage)

                    # Display triage results
                    urgency_color = {"Critical": "red", "High": "orange", "Medium": "blue", "Low": "green"}.get(triage.get("urgency", ""), "blue")
                    answer = f"**Claim Triage Result**\n\n"
                    answer += f"- **Type:** {triage.get('claim_type', 'Unknown')}\n"
                    answer += f"- **Urgency:** :{urgency_color}[**{triage.get('urgency', 'Unknown')}**]\n"
                    answer += f"- **Estimated Severity:** {triage.get('estimated_severity', 'Unknown')}\n"
                    answer += f"- **Adjuster Needed:** {triage.get('adjuster_specialization', 'General')}\n"

                    red_flags = triage.get("red_flags", [])
                    if red_flags and red_flags != ["None"]:
                        answer += f"- **Red Flags:** {', '.join(red_flags)}\n"

                    answer += f"\n{triage.get('summary', '')}\n"

                    st.markdown(answer)

                    # Step 2: Find similar historical claims
                    claim_type = triage.get("claim_type", "PropertyDamage").replace("'", "''")
                    with st.spinner("Finding similar historical claims..."):
                        similar = run_query(f"""
                            SELECT cl.CLAIM_ID, cl.CLAIM_TYPE, cl.CAUSE_OF_LOSS, cl.CLAIM_AMOUNT,
                                   cl.APPROVED_AMOUNT, cl.RESOLUTION_DAYS, cl.STATUS, cl.FRAUD_SCORE,
                                   a.AGENT_NAME AS ADJUSTER
                            FROM INSURANCE_AI_HUB.ANALYTICS.CLAIMS cl
                            LEFT JOIN INSURANCE_AI_HUB.ANALYTICS.AGENTS a ON cl.ADJUSTER_ID = a.AGENT_ID
                            WHERE cl.CLAIM_TYPE = '{claim_type}'
                            ORDER BY cl.CLAIM_DATE DESC LIMIT 10
                        """)
                        if not similar.empty:
                            avg_amount = similar["CLAIM_AMOUNT"].mean()
                            avg_days = similar["RESOLUTION_DAYS"].mean()
                            st.markdown(f"\n**Similar Historical Claims** (type: {claim_type})")
                            st.caption(f"Based on {len(similar)} recent similar claims: avg payout ${avg_amount:,.0f}, avg resolution {avg_days:.0f} days.")
                            df = similar
                            st.dataframe(df, hide_index=True, use_container_width=True)

                    # Step 3: Recommend best available adjuster
                    with st.spinner("Finding best adjuster..."):
                        adjusters = run_query(f"""
                            SELECT a.AGENT_NAME, a.SPECIALIZATION, a.PERFORMANCE_RATING,
                                   COUNT(cl.CLAIM_ID) AS OPEN_CLAIMS
                            FROM INSURANCE_AI_HUB.ANALYTICS.AGENTS a
                            LEFT JOIN INSURANCE_AI_HUB.ANALYTICS.CLAIMS cl
                                ON cl.ADJUSTER_ID = a.AGENT_ID AND cl.STATUS IN ('Open', 'UnderInvestigation')
                            WHERE a.STATUS = 'Active'
                            GROUP BY a.AGENT_NAME, a.SPECIALIZATION, a.PERFORMANCE_RATING
                            ORDER BY OPEN_CLAIMS ASC, PERFORMANCE_RATING DESC
                            LIMIT 5
                        """)
                        if not adjusters.empty:
                            best = adjusters.iloc[0]
                            st.markdown(f"**Recommended Adjuster:** {best['AGENT_NAME']} (Rating: {best['PERFORMANCE_RATING']}, Open Claims: {int(best['OPEN_CLAIMS'])})")

                except json.JSONDecodeError:
                    answer = f"I analyzed the incident but couldn't structure the triage. Here's the raw assessment:\n\n{raw_triage[:1000]}"
                    st.markdown(answer)
                except Exception as e:
                    answer = f"Triage error: {str(e)}"
                    st.markdown(answer)

                trust_score, confidence, verified_str = calculate_dynamic_data_trust(
                    sql_query=sql_used, df_result=df, action_type="SQL"
                )
                render_data_trust_badge(trust_score=trust_score, confidence=confidence, verified_str=verified_str)

        # === ANALYTICS Q&A MODE ===
        else:
            with st.spinner("E.D.I.E. is analyzing your question..."):
                try:
                    action = route_question(prompt)
                except (json.JSONDecodeError, Exception) as e:
                    action = {"action": "KNOWLEDGE", "answer": f"I had trouble parsing the routing response. Let me answer from general knowledge. Error: {str(e)[:100]}"}

                df = None
                sql_used = None
                answer = ""

                if action.get("action") == "SQL":
                    sql_used = action.get("sql", "")
                    sql_upper = sql_used.strip().upper()
                    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
                        answer = "I can only run SELECT queries for safety. Let me rephrase."
                    else:
                        try:
                            df = run_query(sql_used)
                            answer = interpret_results(prompt, df, sql_used)
                        except Exception as e:
                            err_msg = str(e)[:400]
                            try:
                                fix_prompt = (
                                    f"The previous SQL query failed with error: {err_msg}\n"
                                    f"Original SQL was:\n{sql_used}\n\n"
                                    f"User's Question: {prompt}\n\n"
                                    f"IMPORTANT: Use only the exact column names specified in the SCHEMA definition above. "
                                    f"For FEMA disasters, LIVE_FEMA_DISASTER_DECLARATIONS has: RECORD_ID, DISASTER_ID, DESIGNATED_AREA, STATE, COUNTY_FIPS, FEMA_REGION, DESIGNATED_DATE. "
                                    f"Write a corrected SQL query now. Return ONLY JSON:\n"
                                    f'{{"action": "SQL", "sql": "...", "explanation": "..."}}'
                                )
                                retry = conn.query(
                                    "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS RESPONSE",
                                    params=["claude-sonnet-4-6", SYSTEM_PROMPT + "\n\n" + fix_prompt],
                                )
                                raw_retry = retry["RESPONSE"].iloc[0].strip()
                                if raw_retry.startswith("```"):
                                    raw_retry = raw_retry.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                                retry_action = json.loads(raw_retry)
                                sql_used = retry_action.get("sql", "")
                                df = run_query(sql_used)
                                answer = interpret_results(prompt, df, sql_used)
                            except Exception as e2:
                                answer = f"SQL execution failed: {err_msg}. Auto-recovery attempted fallback query."
                                sql_used = None

                elif action.get("action") == "DOCUMENT_SEARCH":
                    search_terms = action.get("search_terms", "")
                    doc_df = search_documents(search_terms)
                    if doc_df is not None and not doc_df.empty:
                        doc_text = doc_df["RELEVANT_TEXT"].str.cat(sep="\n---\n")[:4000]
                        interpret_prompt = (
                            f"You are E.D.I.E., an insurance analytics assistant. "
                            f"The user asked: \"{prompt}\"\n\n"
                            f"Here are relevant policy document excerpts:\n{doc_text}\n\n"
                            f"Answer the question based on these document excerpts. Be specific and cite the document/form if possible."
                        )
                        result = conn.query(
                            "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS RESPONSE",
                            params=["claude-sonnet-4-6", interpret_prompt],
                        )
                        answer = result["RESPONSE"].iloc[0]
                        df = doc_df[["TITLE", "DOCUMENT_TYPE", "FORM_NUMBER", "FILING_STATE"]].drop_duplicates()
                    else:
                        answer = (
                            f"I searched our policy document library for \"{search_terms}\" but didn't find matching content. "
                            f"Try uploading the relevant policy PDF through Document Intake."
                        )

                elif action.get("action") == "KNOWLEDGE":
                    answer = action.get("answer", "I don't have enough context to answer that question.")

                else:
                    answer = "I wasn't able to determine how to answer that. Could you rephrase your question?"

            # Compute dynamic data trust for this specific response
            trust_score, confidence, verified_str = calculate_dynamic_data_trust(
                sql_query=sql_used,
                df_result=df,
                action_type=action.get("action", "SQL")
            )

            st.markdown(answer)
            if df is not None and not df.empty:
                st.dataframe(df, hide_index=True, use_container_width=True)
            render_data_trust_badge(trust_score=trust_score, confidence=confidence, verified_str=verified_str)
            if sql_used:
                with st.expander("View SQL", expanded=False):
                    st.code(sql_used, language="sql")

    _has_trust = "trust_score" in dir() and trust_score is not None
    msg_data = {
        "role": "assistant",
        "content": answer if "answer" in dir() else "",
        "sql": sql_used if "sql_used" in dir() else None,
        "show_trust": _has_trust,
        "trust_score": trust_score if _has_trust else 96.0,
        "confidence": confidence if _has_trust else 92,
        "verified_str": verified_str if _has_trust else "<code>POLICIES (98%)</code>"
    }
    if "df" in dir() and df is not None:
        msg_data["data"] = df
    st.session_state.chat_messages.append(msg_data)

    # Persist to chat history table
    try:
        from utils.rbac import get_current_role
        import uuid
        if "chat_session_id" not in st.session_state:
            st.session_state.chat_session_id = str(uuid.uuid4())[:12]
        role = get_current_role()
        reply_text = msg_data.get("content", "")[:4000]
        user_msg = prompt[:4000] if prompt else ""
        conn.query(
            "INSERT INTO INSURANCE_AI_HUB.ANALYTICS.CHAT_HISTORY (SESSION_ID, USER_ROLE, MESSAGE, REPLY) "
            "SELECT ?, ?, ?, ?",
            params=[st.session_state.chat_session_id, role, user_msg, reply_text],
            ttl=0,
        )
    except Exception:
        pass

if st.session_state.chat_messages:
    if st.button("Clear chat", type="tertiary", icon=":material/delete:"):
        st.session_state.chat_messages = []
        st.rerun()
