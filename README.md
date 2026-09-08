# E.D.I.E. — Enterprise Data & Intelligence Engine

## Insurance AI Hub

> A trusted, AI-enabled insurance data platform that gives the business a 360° view of customers and policies, helps manage claims and revenue, identifies risk, answers questions from policy documents, and continuously monitors data quality.

---

## What is E.D.I.E.?

**EDIE** (Enterprise Data & Intelligence Engine) is an AI-enabled insurance data platform that brings together customer, policy, claims, billing, risk, documents, and data-quality information to provide trusted insights and intelligent decision support.

| Word | Meaning |
|------|---------|
| **Enterprise** | Broad enough for the whole insurance organization |
| **Data** | Represents the integrated insurance data foundation |
| **Intelligence** | Covers analytics, AI, RAG and insights |
| **Engine** | Positions EDIE as a platform that powers multiple use cases |

---

## Architecture

```
                         INSURANCE AI HUB
                               │
              ┌────────────────┼────────────────┐
              │                │                │
         ANALYTICS        DOCUMENTS       DATA_QUALITY
              │                │                │
    ┌─────────┼─────────┐   ┌─┴──┐      ┌─────┼──────┐
    │    │    │    │     │   │    │      │     │      │
 CUST  AGT  POL  CLM  BILL DOCS CHUNKS RULES SCORES RESULTS
                   │                                   │
              AT_RISK                            COL_HEALTH
```

### Three Pillars (Track 6 Alignment)

| Pillar | Schema | Cortex Solution |
|--------|--------|-----------------|
| Self-Service Analytics | `ANALYTICS` | Cortex Analyst + Semantic View |
| Document Intelligence & RAG | `DOCUMENTS` | Cortex Search |
| Data Trust & Observability | `DATA_QUALITY` | Conversational DQ Agent |

---

## Database Inventory

| Schema | Table | Rows | Type | Purpose |
|--------|-------|------|------|---------|
| ANALYTICS | CUSTOMERS | 5,015 | Dimension | Customer profiles, demographics, risk tiers |
| ANALYTICS | AGENTS | 150 | Dimension | Agent profiles, regions, performance |
| ANALYTICS | POLICIES | 8,000 | Fact | Policy coverage, premiums, status |
| ANALYTICS | CLAIMS | 3,562 | Fact | Claims, fraud scores, resolution |
| ANALYTICS | BILLING | 20,000 | Fact | Invoices, payments, balances |
| ANALYTICS | AT_RISK_POLICIES | 1,200 | Snapshot | Churn probability, revenue at risk |
| DOCUMENTS | POLICY_DOCUMENTS | 2,000 | Document | Full policy contract text |
| DOCUMENTS | DOCUMENT_CHUNKS | 12,000 | RAG | Chunked text for vector search |
| DATA_QUALITY | DQ_RULES | 50 | Config | DQ rule definitions |
| DATA_QUALITY | DQ_RESULTS | 5,000 | Execution | Rule pass/fail history |
| DATA_QUALITY | DQ_SCORES | 1,000 | Scores | Table-level quality scores |
| DATA_QUALITY | DQ_COLUMN_HEALTH | 3,000 | Health | Column-level null/outlier metrics |

**Total: 12 tables, 149 columns, ~61,000 rows**

---

## Data Flow

```
Customer → Policy → Claim → Billing → Risk/Retention

    Agent supports Policy/Claims operations

    Policy Documents → Document Chunks → AI/RAG (Cortex Search)

    DQ Rules → DQ Results → DQ Scores → Data Quality Monitoring
```

---

## Business Use Cases

| Business Need | What the platform provides |
|---------------|---------------------------|
| Understand Customers | Profile, risk level, credit score, history |
| Understand Policies | Coverage, premiums, deductibles, exclusions |
| Manage Claims | Volume, amounts, fraud indicators, resolution |
| Monitor Billing | Outstanding payments, overdue, delinquency |
| Identify At-Risk Customers | Churn probability, revenue at risk |
| Ask Questions About Docs | AI/RAG over policy contracts and exclusions |
| Trust the Data | Automated DQ rules, scores, column health |
| Monitor Business Health | Trends, operational metrics, agent performance |

---

## Key Questions E.D.I.E. Answers

- "Which customers are likely to leave?"
- "Which policies generate the most revenue?"
- "Where are claims getting delayed?"
- "Which claims have potential fraud indicators?"
- "What does this policy actually cover?"
- "Does Policy #1049 cover flood damage?"
- "Why did claims spike in the North Region?"
- "Where do we have bad or unreliable data?"

---

## Multi-Agent Architecture

```
                    ┌─────────────────────┐
                    │   E.D.I.E.          │
                    │   (Orchestrator)    │
                    └────────┬────────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
   ┌────────┴───────┐ ┌─────┴──────┐ ┌──────┴───────┐
   │ Analytics Agent │ │ Doc Agent  │ │   DQ Agent   │
   │ (Cortex Analyst)│ │(Cortex Srch)│ │(SQL Queries) │
   └────────────────┘ └────────────┘ └──────────────┘
            │                │                │
      ANALYTICS        DOCUMENTS       DATA_QUALITY
      (Semantic View)  (Search Service) (Direct SQL)
```

---

## Project Files

| File | Purpose |
|------|---------|
| `01_infrastructure.sql` | Warehouse, database, schemas |
| `02_tables.sql` | 12 table DDLs (149 columns) |
| `03_seed_dimensions.sql` | AGENTS + CUSTOMERS data |
| `04_generate_facts.sql` | POLICIES, CLAIMS, BILLING, AT_RISK |
| `05_generate_documents.sql` | Policy docs + RAG chunks |
| `06_generate_dq.sql` | DQ rules, results, scores, health |
| `07_inject_issues.sql` | Realistic data quality problems |
| `08_marketplace_enrichment.sql` | External dataset recommendations |
| `09_explore_data.sql` | Data exploration queries |
| `README.md` | This file |

---

## Injected Data Quality Issues

These deliberate issues support the "Data Trust" pillar demos:

| Issue | Count | Demo Story |
|-------|-------|------------|
| Null emails/phones | 200/150 | Completeness failures |
| Near-duplicate customers | 15 | Entity resolution needed |
| Extreme claim resolution | 313 | Operational friction |
| High fraud scores (>80) | 156 | Fraud detection pipeline |
| Hurricane claims spike | 50 | Seasonal analytics |
| Duplicate claim records | 12 | "Why did metrics spike?" |
| Low-perf high-volume agents | 16 | Agent investigation |
| Stale risk snapshots | 240 | Data freshness monitoring |
| Premium outliers | 11 | Outlier detection |
| Missing payment dates | 500 | Billing consistency |

---

## Setup Instructions

Run these scripts in order against your Snowflake account:

```sql
-- 1. Infrastructure
@01_infrastructure.sql

-- 2. Tables
@02_tables.sql

-- 3-7. Data (run sequentially)
@03_seed_dimensions.sql
@04_generate_facts.sql
@05_generate_documents.sql
@06_generate_dq.sql
@07_inject_issues.sql
```

---

## Technology Stack

- **Snowflake** — Data platform
- **Cortex Analyst** — Natural language SQL via Semantic Views
- **Cortex Search** — Vector search over document chunks
- **Cortex Agents** — Multi-agent orchestration
- **Streamlit in Snowflake** — Interactive dashboard

---

## Value Propositions

1. **Eliminating Decision Latency** — Business users get answers without waiting for data engineering
2. **Hybrid Intelligence** — Structured analytics + unstructured document RAG in one interface
3. **Data Trust by Design** — Real-time visibility into data quality ensures decisions are made on reliable data

---

*Built for Track 6: Unified Enterprise AI Agents Platform*
