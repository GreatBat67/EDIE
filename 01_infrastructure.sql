-- ============================================================
-- INSURANCE AI HUB (E.D.I.E.) - Infrastructure Setup
-- Phase 1: Warehouse, Database, and Schemas
-- ============================================================

-- Warehouse
CREATE WAREHOUSE IF NOT EXISTS INSURANCE_AI_HUB_WH
    WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Warehouse for Insurance AI Hub (E.D.I.E.) analytics and data generation';

USE WAREHOUSE INSURANCE_AI_HUB_WH;

-- Database
CREATE DATABASE IF NOT EXISTS INSURANCE_AI_HUB
    COMMENT = 'Insurance AI Hub (E.D.I.E.) - Enterprise Data & Intelligence Engine for insurance analytics, document intelligence, and data quality observability';

USE DATABASE INSURANCE_AI_HUB;

-- Schema: ANALYTICS - Core business tables (Customer 360, Policy, Claims, Billing, Risk)
CREATE SCHEMA IF NOT EXISTS ANALYTICS
    COMMENT = 'Core insurance analytics: customers, agents, policies, claims, billing, and retention risk';

-- Schema: DOCUMENTS - Policy documents and RAG chunks for AI/vector search
CREATE SCHEMA IF NOT EXISTS DOCUMENTS
    COMMENT = 'Policy document intelligence: full contract text and chunked embeddings for RAG/Cortex Search';

-- Schema: DATA_QUALITY - DQ rules, execution results, scores, and column health
CREATE SCHEMA IF NOT EXISTS DATA_QUALITY
    COMMENT = 'Data quality observability: rules, execution results, table scores, and column-level health metrics';

-- Verify
SHOW SCHEMAS IN DATABASE INSURANCE_AI_HUB;
