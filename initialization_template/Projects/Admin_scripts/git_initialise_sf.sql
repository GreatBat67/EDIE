

-- ============================================================
-- CONFIGURATION VARIABLES
-- ============================================================
SET v_database_name     = 'DISHA_DCM';
SET v_schema_name       = 'INTEGRATION';
SET v_secret_name       = 'GIT_SECRET';
SET v_git_username      = 'Disha-16';
SET v_git_password      = '****************';
SET v_api_integration   = 'dcm_git_cicd_api_integration';
SET v_api_allowed_prefix = 'https://github.com/kipibi';
SET v_repo_name         = 'DCM_PROJECT_REPO';
SET v_repo_origin       = 'https://github.com/kipibi/CI_CD_STANDARD_TIER_OFFERING_TEMPLATE.git';

-- ============================================================
-- CREATE DATABASE & SCHEMA
-- ============================================================
CREATE DATABASE IF NOT EXISTS IDENTIFIER($v_database_name);
CREATE SCHEMA IF NOT EXISTS IDENTIFIER($v_database_name || '.' || $v_schema_name);

-- ============================================================
-- CREATE GIT SECRET
-- ============================================================
USE SCHEMA IDENTIFIER($v_database_name || '.' || $v_schema_name);

CREATE OR REPLACE SECRET IDENTIFIER($v_secret_name)
  TYPE = password
  USERNAME = $v_git_username
  PASSWORD = $v_git_password;

-- ============================================================
-- CREATE API INTEGRATION
-- ============================================================
CREATE OR REPLACE API INTEGRATION IDENTIFIER($v_api_integration)
  API_PROVIDER = git_https_api
  API_ALLOWED_PREFIXES = ($v_api_allowed_prefix)
  ALLOWED_AUTHENTICATION_SECRETS = (IDENTIFIER($v_database_name || '.' || $v_schema_name || '.' || $v_secret_name))
  ENABLED = TRUE;

-- ============================================================
-- CREATE GIT REPOSITORY
-- ============================================================
CREATE OR REPLACE GIT REPOSITORY IDENTIFIER($v_repo_name)
  API_INTEGRATION = IDENTIFIER($v_api_integration)
  GIT_CREDENTIALS = IDENTIFIER($v_database_name || '.' || $v_schema_name || '.' || $v_secret_name)
  ORIGIN = $v_repo_origin;
