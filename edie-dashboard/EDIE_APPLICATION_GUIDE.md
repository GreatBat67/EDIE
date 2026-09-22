# E.D.I.E. — Enterprise Data & Intelligence Engine
## Complete Application Guide

**Version:** 3.0  
**Platform:** Streamlit-in-Snowflake (Container Runtime)  
**Database:** `INSURANCE_AI_HUB`  
**Client:** Apex National P&C Insurance Company  

---

## Architecture Overview

E.D.I.E. is a 12-page insurance enterprise cockpit built on Snowflake's native AI stack. It combines operational dashboards, conversational AI, document intelligence, and self-service analytics into a single Streamlit application running on a Snowflake compute pool.

**Key technology:**
- Snowflake Cortex LLM functions (Claude Sonnet 4.6) for natural language features
- Snowflake ML for time-series forecasting
- Cortex Agent object (`INSURANCE_AI_HUB.PUBLIC.EDIE`) for multi-tool orchestration
- Snowflake Marketplace data (NWS weather, FEMA disasters, BLS CPI, FRED economic indicators)
- Role-based access control across 7 roles

**Schemas:**
| Schema | Purpose |
|--------|---------|
| `ANALYTICS` | Core business tables (28 tables) — policies, claims, customers, agents, forecasts, pricing |
| `EXTERNAL_DATA` | Marketplace-backed views (5 views) + reference tables (2 tables) |
| `DOCUMENTS` | RAG corpus — document chunks, policy documents, query logs |
| `DATA_QUALITY` | DQ rules, results, scores, column health |

---

## Role-Based Access

| Role | Access Level |
|------|-------------|
| `ACCOUNTADMIN` | All 12 pages |
| `EXECUTIVE` | All 12 pages |
| `CLAIMS_ANALYST` | Claims, VoC, Risk Map, Chat, Analytics, Research, Doc Intake |
| `UNDERWRITER` | Claims, Pricing, Risk Map, Chat, Analytics, Research, Doc Intake |
| `RETENTION_MANAGER` | Retention, VoC, Chat, Analytics, Research |
| `AGENCY_MANAGER` | Retention, Pricing, Risk Map, Chat, Analytics, Research |
| `DATA_GOVERNANCE` | Data Quality, Alerts, Chat, Analytics, Research |

---

## Pages

### Analytics Section

---

### 1. Executive KPIs

**Purpose:** C-suite dashboard with cross-domain financial, risk, and underwriting performance.

**Top-line metrics:**
- Gross Written Premium (sum of all policy premiums)
- Total Incurred Claims
- Loss Ratio (incurred / premium × 100, color-coded: >70% critical, >50% elevated)
- Active Policies count
- Revenue at Risk (sum from at-risk policies)

**Charts and tables:**
- Premium Revenue — Actual vs Forecast (line chart, blue actual / amber forecast)
- Claims Incurred Cost — Actual vs Forecast (line chart, red actual / orange forecast)
- Predicted Loss Ratio (next 6 months with cost bounds)
- Loss Ratio Anomalies (flagged deviations from expected)
- Top 10 States by Severe Weather Alerts (horizontal bar)
- CPI Inflation Trend 2022–present (area chart)
- Loss Ratio by Policy Type breakdown

**AI feature:** "Generate Executive Summary" button calls `CORTEX.COMPLETE` (Claude Sonnet 4.6) to produce a 4–5 paragraph board-ready briefing from live KPIs.

**Data sources:** `POLICIES`, `CLAIMS`, `CUSTOMERS`, `AT_RISK_POLICIES`, `PREMIUM_FORECAST`, `CLAIMS_COST_FORECAST`, `LOSS_RATIO_ANOMALIES`, `LIVE_NWS_WEATHER_ALERTS`, `LIVE_BLS_CPI_DATA`

---

### 2. Claims Forecasting & Intelligence

**Purpose:** Severity surges, fraud scoring, FNOL bottlenecks, weather-correlated risk, and ML forecasting.

**Top-line metrics:**
- Total Claims Processed
- Total Incurred Losses
- Avg Fraud Score
- Avg Resolution Cycle (days)

**Charts and tables:**
- Claims Volume Forecast by policy type (line chart with historical + forecast)
- Forecast Details with Confidence Intervals (lower/upper bounds)
- Claims Cost Forecast — monthly incurred cost trend
- Weather-Correlated Claims Risk — state-level table with claims count, total claimed, severe weather alerts, and computed risk level
- Fraud Score Distribution (5 bands: Low 0–20, Medium-Low 20–40, Medium 40–60, High 60–80, Critical 80–100)
- Friction Reasons distribution

**Controls:** Policy Type selectbox filters the volume forecast chart.

**Data sources:** `CLAIMS`, `POLICIES`, `CUSTOMERS`, `CLAIMS_FORECAST`, `CLAIMS_COST_FORECAST`, `LIVE_NWS_WEATHER_ALERTS`

---

### 3. Pricing Optimization & Competitive Intelligence

**Purpose:** AI-driven pricing recommendations, flood risk benchmarking, macro-economic outlook, and product matching.

**Top-line metrics (dynamic based on filters):**
- Segments Filtered (X of total)
- Underpriced Segments count
- Marginal Segments count
- Avg Segment Loss Ratio
- Avg Written Premium

**Charts and tables:**
- Pricing Recommendation Cards (up to 15) — color-coded status badges (UNDERPRICED, MARGINAL, ADEQUATE, PROFITABLE) with AI-generated prescription text
- Flood Risk Benchmark — your avg premium vs FEMA avg payout per state, with underpriced flag
- Federal Funds Rate trend (2020–present)
- 30-Year Mortgage Rate trend (2020–present)
- Multi-Strategy Product Matching table (Exact, Fuzzy, Semantic, Hybrid scoring)

**Controls:** State filter, Policy Line of Business filter, Pricing Status multiselect, Min Loss Ratio slider (0–150%).

**AI feature:** Each pricing recommendation includes a pre-computed LLM-generated prescription.

**Data sources:** `PRICING_RECOMMENDATIONS`, `POLICIES`, `CUSTOMERS`, `LIVE_FEMA_FLOOD_CLAIMS`, `LIVE_FRED_ECONOMIC_DATA`

---

### 4. Voice of Customer & Sentiment Analytics

**Purpose:** Real-time AI sentiment analysis and theme classification on policyholder feedback.

**Top-line metrics:**
- Total Surveys
- Avg NPS Rating (1–10 scale)
- Avg CSAT (satisfaction / 5)
- Promoters count
- Detractors count

**Tab 1 — Sentiment Analysis:**
- NPS Category Distribution (bar chart)
- Avg Satisfaction by Survey Type (horizontal bar)
- "Run AI Sentiment Scoring" button — applies `AI_SENTIMENT()` on 50 recent comments, shows band distribution + most negative comments table
- Claims Friction Reasons (bar chart + table)

**Tab 2 — Theme Classification:**
- "Run AI Theme Classification" button — applies `AI_CLASSIFY()` with 8 categories: Claims Speed, Premium Pricing, Coverage Gaps, Agent Service, Billing Issues, Policy Renewal, Communication, General Satisfaction
- Theme Distribution (bar chart)
- Avg NPS by Theme (horizontal bar)
- Classified comments table

**Tab 3 — AI Insights:**
- `AI_AGG` / `AI_SUMMARIZE_AGG` across 4 selectable scopes: all recent surveys, detractor feedback, claims friction reasons, high-value customer feedback

**Data sources:** `CUSTOMER_SURVEYS`, `CUSTOMERS`, `CLAIMS`

---

### 5. Risk Map — US Geographic Risk Intelligence

**Purpose:** Interactive map overlaying claims density, NWS weather severity, and FEMA exposure across US states.

**Top-line metrics:**
- States Tracked
- Critical Risk count
- High Risk count
- Total Exposure (incurred)

**Visualizations:**
- PyDeck Scatterplot Map — US-centered, color-coded bubbles by risk level (red=Critical, orange=High, yellow=Elevated, green=Normal), bubble size proportional to claims, tooltips with state/risk/claims/incurred/loss ratio
- Risk Matrix table — all state data filterable by risk level

**Risk scoring logic:**
- CRITICAL: Loss Ratio >70% AND Severe Alerts >1,000
- HIGH: Loss Ratio >50% OR Severe Alerts >5,000
- ELEVATED: Severe Alerts >1,000 OR FEMA Disasters >10
- NORMAL: Everything else

**State Drill-Down (per state):**
- Portfolio panel: Policies, Total Premium, Loss Ratio
- Claims panel: Total Claims, Total Incurred, Risk Level
- External Risk panel: Severe Weather Alerts, FEMA Disasters, Avg Flood Payout
- Top 10 active agents in state
- Coverage Gap Analysis by policy type

**Controls:** Risk Level multiselect, State Drill-Down selectbox.

**Data sources:** `CUSTOMERS`, `POLICIES`, `CLAIMS`, `LIVE_NWS_WEATHER_ALERTS`, `LIVE_FEMA_DISASTER_DECLARATIONS`, `LIVE_FEMA_FLOOD_CLAIMS`, `AGENTS`

---

### Operations Section

---

### 6. Retention Rx

**Purpose:** Predictive churn scoring, CLV protection, and prescriptive retention interventions.

**Top-line metrics:**
- Total Customer Accounts
- At-Risk Policies count
- Revenue at Risk
- Avg Churn Probability

**Charts and tables:**
- AI Retention Prescription Cards (top 10 by revenue at risk) — each shows churn %, revenue, tier, segment, credit score, missed payments, NPS, plus a green prescription box with save actions
- Risk Tier Drift Analysis (FROM_TIER to TO_TIER transitions)
- Risk Tier Distribution (bar chart)
- At-Risk by Category (bar chart, revenue by risk category)

**Controls:** Risk Category selectbox filter.

**AI feature:** Pre-computed `RETENTION_PRESCRIPTION` field — Claude Sonnet 4.6-generated per-policy save actions.

**Data sources:** `CUSTOMERS`, `AT_RISK_POLICIES`, `CHURN_PRESCRIPTIONS`, `CUSTOMER_ATTRIBUTE_HISTORY`

---

### 7. Alerts & Automated Observability

**Purpose:** Threshold-based incident triggers, ML anomaly detection, weather warnings, and AI-generated briefings.

**Forecast-based alerts (3 cards):**
- Predicted Loss Ratio — >70% error, >50% warning
- Loss Ratio Anomalies — flagged IS_ANOMALY rows
- Underpriced Segments — count of underpriced pricing recommendations

**Operational alerts (3 cards):**
- High-Fraud Claims — FRAUD_SCORE > 80
- Overdue Invoices — PAYMENT_STATUS = 'Overdue'
- High-Churn Policies — CHURN_PROBABILITY > 0.7

**Additional sections:**
- Severe Weather (last 7 days) — recent Severe/Extreme NWS alerts table
- Daily Enrichment Tasks — 5 scheduled tasks (root + 4 children, 2 AM UTC)

**AI feature:** "Generate Executive Brief" button — configurable period (7/14/30 days), produces 4-section briefing: Claims Activity (`AI_AGG`), Customer Feedback (`AI_SUMMARIZE_AGG`), Key Metrics snapshot (SQL), Weather & Catastrophe summary (`AI_AGG`).

**Data sources:** `CLAIMS_FORECAST`, `CLAIMS_COST_FORECAST`, `PREMIUM_FORECAST`, `LOSS_RATIO_ANOMALIES`, `PRICING_RECOMMENDATIONS`, `CLAIMS`, `BILLING`, `AT_RISK_POLICIES`, `LIVE_NWS_WEATHER_ALERTS`

---

### 8. Data Quality & Governance Observability

**Purpose:** Automated DQ rules, table health scores, column-level monitoring, and marketplace data freshness.

**Top-line metrics:**
- Total DQ Rules
- Active Rules
- Rule Failures (90 days)
- Avg Table Trust

**Visualizations:**
- Latest Table Scores — OVERALL_SCORE, COMPLETENESS, VALIDITY, TIMELINESS, TREND per table
- Most Failing Rules — rule name, target table, severity, fail count (top 10)
- Unhealthiest Columns — table, column, avg health, null rate, outlier rate
- Marketplace Data Freshness — 5 external sources with latest date, row count, stale detection (>30 days)

**Data sources:** `DQ_RULES`, `DQ_RESULTS`, `DQ_SCORES`, `DQ_COLUMN_HEALTH`, all `EXTERNAL_DATA.*` views

---

### 9. Document Intake & Intelligent OCR

**Purpose:** End-to-end PDF processing pipeline with OCR, AI extraction, human review, and database commit.

**Tab 1 — Policy Documents (3-step wizard):**
1. Upload — multi-file PDF uploader, files staged to `@PDF_INTAKE_STAGE`
2. Review — editable extracted fields organized into sections:
   - Policy & Insured (policy number, type, status, named insured, address)
   - Dates & Premiums (effective, expiration, premium, issue date)
   - Cancellation details (if applicable)
   - Business description (if commercial)
   - Coverage Lines (line, limit, deductible, type — repeating)
   - Property Details (year built, construction, protection class, roof, sqft, stories, foundation)
   - Scheduled Vehicles (unit, year/make/model, VIN, garaging location, stated value — repeating)
   - Endorsements (name, limit, description — repeating)
   - Extra Metadata (arbitrary key-value pairs)
3. Commit — MERGE into 8 tables: `CUSTOMERS`, `POLICIES`, `PROPERTY_CHARACTERISTICS`, `COVERAGE_DETAILS`, `VEHICLE_SCHEDULE`, `POLICY_ENDORSEMENTS`, `POLICY_METADATA`, `PDF_INGESTION_LOG`

**Tab 2 — Claims Documents (3-step wizard):**
1. Upload PDFs
2. Review — editable fields: document type (FNOL, Adjuster Report, Proof of Loss, etc.), claim/policy numbers, dates, cause of loss, financial details, liability, injury, medical, line items
3. Commit — MERGE into `CLAIM_DOCUMENTS` + `PDF_INGESTION_LOG`

**Tab 3 — Policy Comparison Engine:**
- Select 2 policies, fetches details + coverages + endorsements + property characteristics
- AI generates side-by-side comparison: coverage gaps, endorsement differences, risk assessment, recommendation

**AI/ML pipeline:**
- `CORTEX.PARSE_DOCUMENT()` — OCR with LAYOUT mode
- `CORTEX.COMPLETE('claude-sonnet-4-6')` — structured JSON extraction (~60 fields for policy, ~30 for claims)

**Sidebar:** Recent Ingestions expander showing last 10 from `PDF_INGESTION_LOG`.

---

### Tools Section

---

### 10. E.D.I.E. Chat

**Purpose:** Conversational AI assistant with persona-based routing, SQL generation, document search, claim triage, and multi-agent orchestration.

**6 Business Personas:**
| Persona | Role | Focus |
|---------|------|-------|
| Trish | CFO | Combined ratio, revenue at risk, overdue billing |
| Marcus | Claims Ops Lead | Severity spikes, fraud, adjuster workload |
| Elena | Sr. Underwriter | Contract exclusions, liability limits, coverage tiers |
| Sid | Director Retention | Churn drivers, at-risk policies, CLV |
| Sarah | Distribution Mgr | Agent performance, territory metrics, commissions |
| David | Data Gov Officer | DQ scores, rule failures, column health |

Each persona has 3 quick-prompt pills for common questions.

**3 Agent Engine Modes:**

*Mode 1 — Analytics & Decision Agent (default):*
- Routes questions through Claude Sonnet 4.6 with full schema context (30+ tables, all columns, relationships, SQL rules)
- Decision framework returns JSON with action type: SQL, DOCUMENT_SEARCH, or KNOWLEDGE
- SQL execution with auto-retry on failure (re-prompts LLM with error message)
- Result interpretation — sends query results back to LLM for human-friendly summary
- Dynamic Data Trust Badge per response (trust score based on queried tables, confidence based on row count, freshness, verified table list)

*Mode 2 — Cortex Agent (Multi-Tool):*
- Calls `INSURANCE_AI_HUB.PUBLIC.EDIE` agent via REST API
- Fallback to `DATA_AGENT_RUN()` SQL function
- Token refresh with 3 retry attempts on 401

*Mode 3 — Claim Triage Assistant:*
- AI classifies incident: claim type, urgency (Critical/High/Medium/Low), estimated severity, adjuster specialization, red flags
- Returns structured JSON triage results
- Queries historical similar claims for benchmarks (avg payout, avg resolution days)
- Recommends best available adjuster (lowest open claims + highest rating)

**Special features:**
- Combined Ratio Investigation — pre-built multi-agent demo with executive summary, root causes, prescriptive actions
- 6 suggestion pills for common queries
- SQL-only guardrail (SELECT/WITH only)
- Document search via ILIKE on `DOCUMENT_CHUNKS` and `POLICY_DOCUMENTS`
- Persistent chat history with SQL expanders and Clear button

---

### 11. Analytics Explorer

**Purpose:** Self-service, no-code analytics — pick domain, perspective, measure, and chart type.

**Tab 1 — Explore:**
- 7 domains: Claims, Policies, Customers, Billing, External: Weather, External: FEMA, External: Economic
- Per-domain perspectives (e.g., Claims: By State, By Policy Type, By Cause of Loss, By Claim Type, By Fraud Band, By Month, By Friction Reason)
- Per-domain measures (e.g., Claims: Count, Total/Avg/Max Claim Amount, Avg Fraud Score, Avg Resolution Days)
- Chart types: Bar, Horizontal Bar, Line, Area, Data Table
- Cross-Tab Heatmap — pick two perspectives + measure for pivot table matrix
- Auto-generated SQL viewable in expander

**Tab 2 — Compare & Correlate:**
- Cross-domain correlation (pick Domain A + Domain B, join by State or Month)
- Scatter chart (State join) or dual-line chart (Month join)
- AI Interpretation — Cortex Complete generates correlation analysis and business recommendation

**Tab 3 — My Workspace:**
- Build custom dashboard panels
- Configurable: domain, title, group-by, measures (1–3), chart type (Bar, Horizontal Bar, Stacked Bar, Line, Area, Scatter, Heatmap, Data Table, Metric Cards)
- Secondary group-by for Heatmap/Stacked Bar
- Top N slider (5–100)
- Add/delete/clear panels with session state persistence

---

### 12. Research & Predict

**Purpose:** Table profiling, AI-powered research, on-the-fly ML forecasting, and what-if scenario analysis.

**Tab 1 — Data Profile:**
- Schema and table selectors (16 ANALYTICS tables + 7 EXTERNAL_DATA tables)
- Column listing with data types
- "Run Column Profile" button — per-column: total rows, nulls, distinct values
- Sample data viewer (first 50 rows)

**Tab 2 — AI Research:**
- Free-text research question input
- Sends table columns + descriptive stats + sample rows to Claude Sonnet 4.6
- Returns analysis with patterns, anomalies, and actionable recommendations

**Tab 3 — Predict & Forecast:**
- Dynamic column detection (date columns, numeric columns)
- Snowflake ML Forecasting: `CREATE SNOWFLAKE.ML.FORECAST` trained on-the-fly
- Configurable: time column, target column, aggregation (SUM/AVG/COUNT), forecast periods (3–12)
- Historical + Forecast line chart
- Forecast details table with confidence intervals
- AI Interpretation of forecast results

**What-If Scenario Analysis (6 sliders):**
- Internal: Claims volume change, Premium rate change, Churn rate change
- External/Macro: CPI inflation, Catastrophe severity multiplier, Interest rate
- Calculates: Adjusted premium, incurred, claims, loss ratio, combined ratio, investment income, underwriting result, net result
- Side-by-side Baseline vs Adjusted vs Financial Impact
- AI Scenario Assessment evaluates sustainability, reserve impact, and macro assumptions

---

## AI/ML Features Summary

| Feature | Snowflake Function | Used In |
|---------|-------------------|---------|
| LLM text generation | `CORTEX.COMPLETE('claude-sonnet-4-6')` | Exec KPIs, Chat, Pricing, Retention, Analytics, Research, Doc Intake |
| Sentiment scoring | `AI_SENTIMENT()` | Voice of Customer |
| Zero-shot classification | `AI_CLASSIFY()` | Voice of Customer (8 categories) |
| Row-level aggregation | `AI_AGG()` | Voice of Customer, Alerts |
| Multi-row summarization | `AI_SUMMARIZE_AGG()` | Alerts |
| Document OCR | `CORTEX.PARSE_DOCUMENT()` | Document Intake |
| Time-series forecasting | `SNOWFLAKE.ML.FORECAST` | Research & Predict |
| Anomaly detection | Pre-computed | Loss Ratio Anomalies |
| Multi-tool agent | Cortex Agent REST API | Chat (EDIE agent) |
| Claim triage | `CORTEX.COMPLETE` (structured JSON) | Chat |

---

## External Data Sources (Snowflake Marketplace)

| View Name | Marketplace Source | Key Usage |
|-----------|-------------------|-----------|
| `LIVE_NWS_WEATHER_ALERTS` | Snowflake Public Data: Core Weather | Risk Map, Claims correlation, Alerts, Exec KPIs |
| `LIVE_FEMA_DISASTER_DECLARATIONS` | Snowflake Public Data (Free) | Risk Map, Analytics |
| `LIVE_FEMA_FLOOD_CLAIMS` | Snowflake Public Data (Free) | Risk Map, Pricing flood benchmark |
| `LIVE_BLS_CPI_DATA` | Snowflake Public Data (Free) | Exec KPIs inflation trend |
| `LIVE_FRED_ECONOMIC_DATA` | Snowflake Public Data (Free) + Freddie Mac | Pricing (Fed funds rate, 30-yr mortgage rate) |

---

## Deployment

**Runtime:** Streamlit-in-Snowflake on `SYSTEM_COMPUTE_POOL_CPU`  
**Warehouse:** `COMPUTE_WH`  
**Dependencies:** `streamlit[snowflake] >= 1.54.0`, `numba >= 0.56.0`  
**Files:** 17 source files (1 main + 12 pages + 2 utils + config + dependencies)

---

## Utility: PDF Watcher (`pdf_watcher.py`)

Standalone Python script (not deployed with Streamlit) that watches a local folder and auto-uploads PDFs to `@INSURANCE_AI_HUB.ANALYTICS.PDF_INTAKE_STAGE` via Snowflake PUT. Supports watchdog (event-based) or polling (5-second interval). Moves processed files to a `processed/` subfolder.
