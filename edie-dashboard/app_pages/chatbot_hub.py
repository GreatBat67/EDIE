import streamlit as st
import json
from utils.queries import run_query

st.header("E.D.I.E. Chat")
st.caption("Enterprise Data & Intelligence Engine — Ask anything about your insurance data. E.D.I.E. writes SQL, queries the database, and interprets the results.")

conn = st.session_state.conn

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

## EXTERNAL_DATA Schema — Live Marketplace Data
LIVE_NWS_WEATHER_ALERTS(ALERT_ID, STATE, COUNTY, EVENT_TYPE, EVENT_SEVERITY[Minor|Moderate|Severe|Extreme], ALERT_TITLE, REPORTED_DATE)
LIVE_FEMA_DISASTER_DECLARATIONS(DISASTER_ID, STATE, DISASTER_TYPE, TITLE, DESIGNATED_DATE, INCIDENT_BEGIN_DATE, INCIDENT_END_DATE)
LIVE_FEMA_FLOOD_CLAIMS(CLAIM_ID, STATE, COUNTY, DATE_OF_LOSS, BUILDING_DAMAGE_AMOUNT, CONTENTS_DAMAGE_AMOUNT, TOTAL_PAID, FLOOD_ZONE, OCCUPANCY_TYPE)
LIVE_FEMA_FLOOD_POLICIES(POLICY_ID, STATE, COUNTY, POLICY_EFFECTIVE_DATE, POLICY_EXPIRATION_DATE, TOTAL_BUILDING_VALUE, TOTAL_CONTENTS_VALUE, FLOOD_ZONE, OCCUPANCY_TYPE)
LIVE_BLS_CPI_DATA(SERIES_NAME, OBSERVATION_DATE, VALUE)
LIVE_FRED_ECONOMIC_DATA(SERIES_ID, SERIES_NAME, OBSERVATION_DATE, VALUE)
LIVE_HOSPITAL_PRICE_TRANSPARENCY(HOSPITAL_NAME, STATE, PROCEDURE_CODE, PROCEDURE_DESCRIPTION, GROSS_CHARGE, NEGOTIATED_RATE, PAYER_NAME)
NAIC_STATUTORY_GUIDELINES(GUIDELINE_ID, LINE_OF_BUSINESS, METRIC_NAME, MIN_THRESHOLD, MAX_THRESHOLD, DESCRIPTION)

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


def route_question(question):
    """Send question to LLM with schema context, get back action JSON."""
    full_prompt = f"User question: {question}"
    result = conn.query(
        "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS RESPONSE",
        params=["claude-sonnet-4-6", SYSTEM_PROMPT + "\n\n" + full_prompt],
    )
    raw = result["RESPONSE"].iloc[0].strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(raw)


def interpret_results(question, df, sql):
    """Send query results back to LLM for human-friendly interpretation."""
    data_str = df.to_string(index=False, max_rows=30) if not df.empty else "No results returned."
    row_count = len(df)
    interpret_prompt = (
        f"You are E.D.I.E., an insurance analytics assistant. "
        f"The user asked: \"{question}\"\n\n"
        f"SQL executed:\n```sql\n{sql}\n```\n\n"
        f"Results ({row_count} rows):\n{data_str}\n\n"
        f"Give a concise, insightful answer based on this data. "
        f"Highlight the most important finding first. Use numbers with commas and $ for currency. "
        f"Keep it to 2-4 sentences max. If the data reveals a risk or opportunity, call it out."
    )
    result = conn.query(
        "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS RESPONSE",
        params=["claude-sonnet-4-6", interpret_prompt],
    )
    return result["RESPONSE"].iloc[0]


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


# ============================================================
# CHAT UI
# ============================================================
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# Mode toggle — in main area above pills
chat_mode = st.radio("Chat Mode", ["Analytics Q&A", "Cortex Agent", "Claim Triage"], horizontal=True, key="chat_mode", label_visibility="collapsed")

# Suggestion pills (only in Analytics mode)
if chat_mode == "Analytics Q&A":
    selected = st.pills("Quick questions:", list(SUGGESTIONS.keys()), label_visibility="collapsed", key="suggestions")
elif chat_mode == "Cortex Agent":
    selected = None
    st.caption(":material/hub: **Cortex Agent Mode** — E.D.I.E. agent with Semantic Views + Policy Document Search")
else:
    selected = None
    st.caption(":material/medical_services: **Claim Triage Mode** — describe the incident below")

# Chat input
typed_prompt = st.chat_input("Ask E.D.I.E. anything about your insurance data...")

# Display chat history
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"], avatar=":material/smart_toy:" if msg["role"] == "assistant" else None):
        st.markdown(msg["content"])
        if msg.get("data") is not None:
            st.dataframe(msg["data"], hide_index=True, use_container_width=True)
        if msg.get("sql"):
            with st.expander("View SQL", expanded=False):
                st.code(msg["sql"], language="sql")

# Determine prompt
prompt = None
if typed_prompt:
    prompt = typed_prompt
elif selected:
    pill_prompt = SUGGESTIONS[selected]
    already_asked = (
        st.session_state.chat_messages
        and st.session_state.chat_messages[-1].get("role") == "assistant"
        and len(st.session_state.chat_messages) >= 2
        and st.session_state.chat_messages[-2].get("content") == pill_prompt
    )
    if not already_asked:
        prompt = pill_prompt

if prompt:
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=":material/smart_toy:"):
        # === CORTEX AGENT MODE ===
        if chat_mode == "Cortex Agent":
            with st.spinner("E.D.I.E. Cortex Agent is processing..."):
                df = None
                sql_used = None
                answer = ""
                try:
                    import requests, os
                    token_path = os.environ.get("SNOWFLAKE_TOKEN_FILE_PATH", "/snowflake/session/token")
                    try:
                        with open(token_path) as f:
                            token = f.read().strip()
                    except FileNotFoundError:
                        token = None

                    if token:
                        host = os.environ.get("SNOWFLAKE_HOST", "")
                        url = f"https://{host}/api/v2/databases/INSURANCE_AI_HUB/schemas/PUBLIC/agents/EDIE:run"
                        payload = {
                            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
                            "stream": False,
                        }
                        resp = requests.post(url, json=payload, headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                        }, timeout=120)

                        if resp.status_code == 200:
                            agent_resp = resp.json()
                            # Extract text from agent response
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
                        else:
                            error_body = resp.text[:500]
                            answer = f"Agent API returned status {resp.status_code}: {error_body}"
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

                st.markdown(answer)

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
                            err_msg = str(e)[:300]
                            try:
                                fix_prompt = (
                                    f"The SQL query failed with error: {err_msg}\n"
                                    f"Original SQL:\n{sql_used}\n\n"
                                    f"Original question: {prompt}\n\n"
                                    f"Write a corrected SQL query. Return ONLY a JSON object: "
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
                                answer = f"I tried querying the database but encountered an error: {err_msg}\n\nI attempted a fix but it also failed."
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

            st.markdown(answer)
            if df is not None and not df.empty:
                st.dataframe(df, hide_index=True, use_container_width=True)
            if sql_used:
                with st.expander("View SQL", expanded=False):
                    st.code(sql_used, language="sql")

    msg_data = {"role": "assistant", "content": answer if "answer" in dir() else "", "sql": sql_used if "sql_used" in dir() else None}
    if "df" in dir() and df is not None:
        msg_data["data"] = df
    st.session_state.chat_messages.append(msg_data)

if st.session_state.chat_messages:
    if st.button("Clear chat", type="tertiary", icon=":material/delete:"):
        st.session_state.chat_messages = []
        st.rerun()
