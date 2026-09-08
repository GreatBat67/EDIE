
import os
import re
import sys
from pathlib import Path
import yaml

# ============================================================
# LOCATE project_config.yml
# ============================================================

try:
    # Works when running as a standard Python script
    SCRIPT_DIR = Path(__file__).resolve().parent
except NameError:
    # Fallback for interactive environments (Snowflake Workspaces/Notebooks)
    SCRIPT_DIR = Path.cwd()

CONFIG_FILE = SCRIPT_DIR.parent / "config" / "project_config.yml"

if not CONFIG_FILE.exists():
    raise FileNotFoundError(f"project_config.yml not found: {CONFIG_FILE}")

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    project_config = yaml.safe_load(f)

# ============================================================
# READ CONFIG
# ============================================================

DCM_PROJECT_NAME = project_config.get("dcm_project_name", "dcm_automation")
DBT_PROJECT_NAME = re.sub(r"(?i)^dcm", "dbt", DCM_PROJECT_NAME)

SNOWFLAKE = project_config.get("snowflake_global", {})
BRANCH_DATA = project_config.get("branch_data", {})

ACCOUNT = SNOWFLAKE.get("account_identifier", "")
WAREHOUSE = SNOWFLAKE.get("warehouse", "")

DEFAULT_TARGET = "dev"

WORKSPACE = SCRIPT_DIR.parent.parent.parent
DCM_DIR = WORKSPACE / DCM_PROJECT_NAME
DBT_DIR = DCM_DIR / "sources" / DBT_PROJECT_NAME
DEFINITIONS_DIR = DCM_DIR / "sources" / "definitions"

DIRS = [
    DBT_DIR,
    DBT_DIR / "analyses",
    DBT_DIR / "macros",
    DBT_DIR / "models",
    DBT_DIR / "models" / "staging",
    DBT_DIR / "models" / "marts",
    DBT_DIR / "tests",
    DBT_DIR / "seeds",
    DBT_DIR / "snapshots",
    DEFINITIONS_DIR,
]

def mkdirs():
    for d in DIRS:
        d.mkdir(parents=True, exist_ok=True)

def gitkeeps():
    for d in DIRS:
        if not any(d.iterdir()):
            (d / ".gitkeep").touch()

def dbt_project():
    txt=f"""name: '{DBT_PROJECT_NAME}'
version: '1.0'
config-version: 2

profile: '{DBT_PROJECT_NAME}'

model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

clean-targets:
  - target
  - dbt_packages

models:
  {DBT_PROJECT_NAME}:
    staging:
      +materialized: view
    marts:
      +materialized: table
"""
    (DBT_DIR/"dbt_project.yml").write_text(txt,encoding="utf-8")

def profiles():
    # Find the default target
    default_target = None

    for branch_name, branch_cfg in BRANCH_DATA.items():
        if isinstance(branch_cfg, dict) and branch_cfg.get("is_default_target", False):
            default_target = branch_name
            break

    if not default_target:
        default_target = "dev"

    lines = [
        f"{DBT_PROJECT_NAME}:",
        f"  target: {default_target}",
        "",
        "  outputs:",
        ""
    ]

    # Generate an output for every branch
    for branch_name, branch in BRANCH_DATA.items():

        if not isinstance(branch, dict):
            continue

        database = (branch.get("sf_databases") or [""])[0]
        schema = (branch.get("sf_schemas") or ["PUBLIC"])[0]
        role = (branch.get("sf_roles") or [""])[0]
        user = branch.get("sf_user", "")

        lines.extend([
            f"    {branch_name}:",
            "      type: snowflake",
            f"      account: \"{ACCOUNT}\"",
            f"      user: \"{user}\"",
            f"      role: \"{role}\"",
            f"      warehouse: \"{WAREHOUSE}\"",
            f"      database: \"{database}\"",
            f"      schema: \"{schema}\"",
            "      threads: 4",
            ""
        ])

    (DBT_DIR / "profiles.yml").write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

def sources():
    dev=BRANCH_DATA.get("dev",{})
    db=(dev.get("sf_databases") or [""])[0]
    sch=(dev.get("sf_schemas") or ["PUBLIC"])[0]
    txt=f"""version: 2

sources:
  - name: raw
    database: {db}
    schema: {sch}
    tables: []
"""
    (DBT_DIR/"models"/"sources.yml").write_text(txt,encoding="utf-8")

def pipeline():
    # Find the default target branch
    target_config = None
    default_target = None

    for branch_name, branch_cfg in BRANCH_DATA.items():
        if isinstance(branch_cfg, dict) and branch_cfg.get("is_default_target", False):
            target_config = branch_cfg
            default_target = branch_name
            break

    if not target_config:
        raise RuntimeError(
            "No branch with 'is_default_target: true' found in project_config.yml."
        )

    # Read database and schema
    sf_databases = target_config.get("sf_databases", [])
    if not sf_databases:
        raise RuntimeError(
            "sf_databases must be defined for the default target."
        )

    database = sf_databases[0]

    sf_schemas = target_config.get("sf_schemas", [])
    schema = sf_schemas[0] if sf_schemas else "PUBLIC"

    txt = f"""DEFINE DBT PROJECT {database}.{schema}.{DBT_PROJECT_NAME.upper()}
    FROM 'sources/{DBT_PROJECT_NAME}'
    DEFAULT_TARGET = '{default_target.upper()}'
;
"""

    (DEFINITIONS_DIR / "DBT_PIPELINE.sql").write_text(
        txt,
        encoding="utf-8"
    )
    (DEFINITIONS_DIR/"DBT_PIPELINE.sql").write_text(txt,encoding="utf-8")

def main():
    print("="*60)
    print("INITIALIZE DBT PROJECT")
    print("="*60)
    mkdirs()
    dbt_project()
    profiles()
    sources()
    pipeline()
    gitkeeps()
    print(f"DCM Project : {DCM_PROJECT_NAME}")
    print(f"DBT Project : {DBT_PROJECT_NAME}")
    print(f"Location    : {DBT_DIR}")
    print("Completed successfully.")

if __name__=="__main__":
    main()
