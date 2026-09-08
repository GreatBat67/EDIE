import streamlit as st
import json
import tempfile
import os
from utils.queries import run_query

st.header("Document Intake")
st.caption("Upload policy or claims PDFs → AI extracts all fields → review/edit → commit to database.")

conn = st.session_state.conn
session = conn.session()

def _clean(val, default=""):
    if val is None:
        return default
    s = str(val).strip().strip('"').strip("'").strip()
    return s if s else default

def _num(val, default=0):
    v = _clean(val)
    if not v:
        return default
    try:
        return float(v.replace(",", "").replace("$", "").replace("%", ""))
    except (ValueError, TypeError):
        return default

def _upload_and_parse(file):
    """Upload PDF to stage and parse with CORTEX.PARSE_DOCUMENT. Returns parsed text."""
    file_name = file.name
    pdf_bytes = file.read()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, prefix=file_name.replace(".pdf", "_")) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
        tmp_basename = os.path.basename(tmp_path)

    session.sql(f"REMOVE @INSURANCE_AI_HUB.ANALYTICS.PDF_INTAKE_STAGE/{file_name}").collect()
    session.sql(f"PUT 'file://{tmp_path}' @INSURANCE_AI_HUB.ANALYTICS.PDF_INTAKE_STAGE/{file_name}/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE").collect()
    os.unlink(tmp_path)

    stage_file_path = f"{file_name}/{tmp_basename}"
    parse_result = session.sql(f"""
        SELECT SNOWFLAKE.CORTEX.PARSE_DOCUMENT(
            '@INSURANCE_AI_HUB.ANALYTICS.PDF_INTAKE_STAGE',
            '{stage_file_path}',
            {{'mode': 'LAYOUT'}}
        ):content::VARCHAR AS PARSED
    """).collect()

    doc_text = parse_result[0]["PARSED"] if parse_result and parse_result[0]["PARSED"] else ""
    if not doc_text:
        raise ValueError("PARSE_DOCUMENT returned empty content.")
    return doc_text

# ============================================================
# LLM EXTRACTION PROMPTS
# ============================================================
POLICY_EXTRACT_PROMPT = """Extract ALL important fields from this insurance policy document.
Return ONLY a valid JSON object with these exact top-level keys. Use null for any field not found.
For dates use YYYY-MM-DD format. For money amounts return numbers only (no $ or commas).

{
  "policy_number": "The policy number",
  "policy_type": "Type (Homeowners, CommercialAuto, CommercialMultiPeril, WorkersComp, GeneralLiability, ProfessionalLiability, Umbrella, BOP, Flood, etc.)",
  "policy_status": "Active, Cancelled, Expired, etc. Default Active if not stated",
  "named_insured": "Full name of named insured (person or business)",
  "first_name": "First name if a person, empty string if business",
  "last_name": "Last name if a person, empty string if business",
  "business_description": "Business description if commercial policy, null if personal",
  "address": "Street address",
  "city": "City",
  "state": "Two-letter state code",
  "zip_code": "ZIP code",
  "effective_date": "Policy start date YYYY-MM-DD",
  "expiration_date": "Policy end date YYYY-MM-DD",
  "annual_premium": "Annual premium as number",
  "cancellation_date": "Cancellation date YYYY-MM-DD if cancelled, null otherwise",
  "cancellation_reason": "Reason for cancellation if cancelled, null otherwise",
  "return_premium": "Return premium amount if cancelled, null otherwise",
  "agent_name": "Agent name",
  "agent_license": "Agent license number if shown",
  "issue_date": "Date of issue YYYY-MM-DD",
  "coverages": [
    {"line": "Coverage name (e.g. Coverage A - Dwelling)", "limit": 0, "deductible": 0, "deductible_type": "Flat or Percentage", "notes": "any extra detail"}
  ],
  "property": {
    "year_built": null,
    "construction_type": "e.g. Brick Veneer, Frame",
    "protection_class": "e.g. Class 3",
    "square_footage": null,
    "number_of_stories": null,
    "roof_type": null,
    "foundation_type": null
  },
  "vehicles": [
    {"unit": 1, "year_make_model": "2021 Ford F-250", "vin": "...", "garaging_location": "City, ST", "stated_value": 0}
  ],
  "endorsements": [
    {"name": "Endorsement name", "limit": 0, "description": "brief description"}
  ],
  "extra_metadata": [
    {"field": "field_name", "value": "field_value", "type": "TEXT or NUMBER or DATE"}
  ]
}

IMPORTANT:
- Include ALL coverage lines found (Coverage A through F, Liability CSL, UM/UIM, Med Pay, Comp, Collision, etc.)
- Include ALL endorsements listed
- Include ALL scheduled vehicles if auto policy
- For extra_metadata, capture ANY policy-specific fields not covered above: experience_mod_rate, retroactive_date, claims_made_basis, NCCI_code, payroll_class, underlying_policies, attachment_point, community_number, waiting_period, building_vs_contents_split, business_income_limit, equipment_breakdown_limit, etc.
- If a field is not present in the document, use null
- For deductible_type, use "Percentage" if it says "2% of Coverage A" etc., otherwise "Flat"
- Return coverages, vehicles, endorsements, extra_metadata as empty arrays [] if none found

DOCUMENT TEXT:
"""

CLAIMS_EXTRACT_PROMPT = """Extract ALL important fields from this insurance claims document.
This could be a First Notice of Loss (FNOL), adjuster report, proof of loss, subrogation letter, or medical bill.
Return ONLY a valid JSON object. Use null for any field not found.
For dates use YYYY-MM-DD format. For money amounts return numbers only (no $ or commas).

{
  "document_type": "FNOL, Adjuster Report, Proof of Loss, Subrogation Letter, Medical Bill, Estimate, Correspondence, or Other",
  "claim_number": "Claim number or reference if shown",
  "policy_number": "Related policy number if shown",
  "date_of_loss": "Date the loss/incident occurred YYYY-MM-DD",
  "cause_of_loss": "Cause (Fire, Water Damage, Wind/Hail, Theft, Collision, Slip and Fall, etc.)",
  "loss_description": "Detailed description of what happened",
  "loss_location": "Address where loss occurred",
  "reported_by": "Who reported the claim",
  "report_date": "Date claim was reported YYYY-MM-DD",
  "claimant_name": "Name of the claimant (may differ from insured)",
  "claimant_contact": "Phone/email of claimant if shown",
  "insured_name": "Name of the insured on the policy",
  "damage_estimate": "Total estimated damage amount as number",
  "repair_estimate": "Repair/replacement cost estimate as number",
  "actual_cash_value": "ACV if stated as number",
  "replacement_cost_value": "RCV if stated as number",
  "liability_determination": "At fault, not at fault, shared, pending, etc.",
  "injury_type": "Type of injury if any (bodily injury, property damage, both, none)",
  "injury_description": "Description of injuries if applicable",
  "medical_provider": "Medical provider name if medical bill",
  "medical_amount_billed": "Amount billed if medical document",
  "medical_amount_paid": "Amount paid if medical document",
  "recovery_amount": "Subrogation recovery amount if applicable",
  "at_fault_party": "At-fault party name if applicable",
  "adjuster_name": "Name of adjuster if shown",
  "adjuster_recommendation": "Adjuster's recommendation if stated",
  "status": "Open, Closed, Under Investigation, Denied, Settled, etc.",
  "settlement_amount": "Settlement amount if resolved",
  "deductible_applied": "Deductible amount applied",
  "items": [
    {"description": "Damaged item or line item", "quantity": 1, "amount": 0}
  ],
  "extra_fields": [
    {"field": "any other important field name", "value": "value"}
  ]
}

IMPORTANT: Extract EVERY data point. For FNOL, focus on loss details. For adjuster reports, focus on assessment and recommendation. For proof of loss, focus on itemized damages. For medical bills, focus on CPT codes and amounts.

DOCUMENT TEXT:
"""

# ============================================================
# TAB LAYOUT
# ============================================================
policy_tab, claims_tab, compare_tab = st.tabs([":material/policy: Policy Documents", ":material/assignment: Claims Documents", ":material/compare_arrows: Policy Comparison"])

# ============================================================
# POLICY DOCUMENTS TAB
# ============================================================
with policy_tab:
    if "extracted_policies" not in st.session_state:
        st.session_state.extracted_policies = []
    if "intake_step" not in st.session_state:
        st.session_state.intake_step = "upload"

    # --- STEP 1: UPLOAD ---
    if st.session_state.intake_step == "upload":
        st.subheader("Step 1  Upload Policy PDFs")
        uploaded_files = st.file_uploader("Drop policy PDF files here", type=["pdf"],
            accept_multiple_files=True, key="pdf_upload")

        if uploaded_files and st.button("Extract Policy Data", type="primary", icon=":material/document_scanner:", key="extract_pol"):
            st.session_state.extracted_policies = []
            progress = st.progress(0, text="Extracting...")

            for i, file in enumerate(uploaded_files):
                file_name = file.name
                progress.progress((i + 1) / len(uploaded_files), text=f"Processing {file_name}...")
                try:
                    doc_text = _upload_and_parse(file)
                    prompt = POLICY_EXTRACT_PROMPT + doc_text[:8000]
                    llm_result = conn.query("SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS RESPONSE",
                        params=["claude-sonnet-4-6", prompt])
                    raw_response = llm_result["RESPONSE"].iloc[0]
                    clean = raw_response.strip()
                    if clean.startswith("```"):
                        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                    extracted = json.loads(clean)
                    extracted["_file_name"] = file_name
                    extracted["_status"] = "Ready"
                    st.session_state.extracted_policies.append(extracted)
                except json.JSONDecodeError:
                    st.session_state.extracted_policies.append({
                        "_file_name": file_name, "_status": "PARSE ERROR",
                        "_raw": raw_response[:500] if "raw_response" in dir() else "No response",
                        "policy_number": None})
                except Exception as e:
                    st.session_state.extracted_policies.append({
                        "_file_name": file_name, "_status": f"ERROR: {str(e)}",
                        "policy_number": None})

            progress.empty()
            st.session_state.intake_step = "review"
            st.rerun()

    # --- STEP 2: REVIEW ---
    elif st.session_state.intake_step == "review":
        st.subheader("Step 2  Review Extracted Data")
        st.caption("Verify the extracted fields. Edit any incorrect values before committing.")

        if not st.session_state.extracted_policies:
            st.warning("No extracted data.")
            if st.button("Back to Upload"):
                st.session_state.intake_step = "upload"
                st.rerun()
        else:
            for idx, pol in enumerate(st.session_state.extracted_policies):
                status = pol.get("_status", "Unknown")
                icon = ":green[Ready]" if status == "Ready" else f":red[{status}]"

                with st.expander(f"{pol.get('_file_name', 'Unknown')} — {pol.get('policy_number', 'N/A')} — {icon}", expanded=(idx == 0)):
                    if status != "Ready":
                        st.error(f"Extraction failed: {status}")
                        if "_raw" in pol:
                            st.code(pol["_raw"][:500])
                        continue

                    # Policy & Insured
                    st.markdown("##### Policy & Insured")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        pol["policy_number"] = st.text_input("Policy Number", _clean(pol.get("policy_number")), key=f"pn_{idx}")
                        pol["policy_type"] = st.text_input("Policy Type", _clean(pol.get("policy_type")), key=f"pt_{idx}")
                        status_opts = ["Active", "Cancelled", "Expired", "Non-Renewed"]
                        cur_status = _clean(pol.get("policy_status"), "Active")
                        pol["policy_status"] = st.selectbox("Status", status_opts,
                            index=status_opts.index(cur_status) if cur_status in status_opts else 0, key=f"ps_{idx}")
                    with c2:
                        pol["named_insured"] = st.text_input("Named Insured", _clean(pol.get("named_insured")), key=f"ni_{idx}")
                        pol["first_name"] = st.text_input("First Name", _clean(pol.get("first_name")), key=f"fn_{idx}")
                        pol["last_name"] = st.text_input("Last Name", _clean(pol.get("last_name")), key=f"ln_{idx}")
                    with c3:
                        pol["address"] = st.text_input("Address", _clean(pol.get("address")), key=f"ad_{idx}")
                        pol["city"] = st.text_input("City", _clean(pol.get("city")), key=f"ci_{idx}")
                        sc1, sc2 = st.columns(2)
                        with sc1:
                            pol["state"] = st.text_input("State", _clean(pol.get("state")), key=f"st_{idx}")
                        with sc2:
                            pol["zip_code"] = st.text_input("ZIP", _clean(pol.get("zip_code")), key=f"zp_{idx}")

                    # Dates & Premiums
                    st.markdown("##### Dates & Premiums")
                    d1, d2, d3, d4 = st.columns(4)
                    with d1:
                        pol["effective_date"] = st.text_input("Effective", _clean(pol.get("effective_date")), key=f"ed_{idx}")
                    with d2:
                        pol["expiration_date"] = st.text_input("Expiration", _clean(pol.get("expiration_date")), key=f"xd_{idx}")
                    with d3:
                        pol["annual_premium"] = st.number_input("Premium ($)", value=_num(pol.get("annual_premium")), key=f"ap_{idx}")
                    with d4:
                        pol["issue_date"] = st.text_input("Issue Date", _clean(pol.get("issue_date")), key=f"id_{idx}")

                    if _clean(pol.get("policy_status")) == "Cancelled":
                        cx1, cx2, cx3 = st.columns(3)
                        with cx1:
                            pol["cancellation_date"] = st.text_input("Cancel Date", _clean(pol.get("cancellation_date")), key=f"cd_{idx}")
                        with cx2:
                            pol["cancellation_reason"] = st.text_input("Cancel Reason", _clean(pol.get("cancellation_reason")), key=f"cr_{idx}")
                        with cx3:
                            pol["return_premium"] = st.number_input("Return Premium ($)", value=_num(pol.get("return_premium")), key=f"rp_{idx}")

                    if _clean(pol.get("business_description")):
                        pol["business_description"] = st.text_input("Business Description", _clean(pol.get("business_description")), key=f"bd_{idx}")

                    pol["agent_name"] = st.text_input("Agent", _clean(pol.get("agent_name")), key=f"ag_{idx}")

                    # Coverages
                    coverages = pol.get("coverages") or []
                    if coverages:
                        st.markdown("##### Coverage Lines")
                        for ci, cov in enumerate(coverages):
                            cc1, cc2, cc3, cc4 = st.columns([3, 2, 2, 2])
                            with cc1:
                                cov["line"] = st.text_input("Line", _clean(cov.get("line")), key=f"cl_{idx}_{ci}")
                            with cc2:
                                cov["limit"] = st.number_input("Limit ($)", value=_num(cov.get("limit")), key=f"cv_{idx}_{ci}")
                            with cc3:
                                cov["deductible"] = st.number_input("Deductible", value=_num(cov.get("deductible")), key=f"cdd_{idx}_{ci}")
                            with cc4:
                                cov["deductible_type"] = st.selectbox("Ded. Type", ["Flat", "Percentage"],
                                    index=0 if _clean(cov.get("deductible_type"), "Flat") == "Flat" else 1, key=f"cdt_{idx}_{ci}")
                        pol["coverages"] = coverages

                    # Property
                    prop = pol.get("property") or {}
                    if prop and any(prop.get(k) for k in ["year_built", "construction_type", "protection_class"]):
                        st.markdown("##### Property Details")
                        p1, p2, p3, p4 = st.columns(4)
                        with p1:
                            prop["year_built"] = st.number_input("Year Built", value=int(_num(prop.get("year_built"))), key=f"yb_{idx}")
                            prop["construction_type"] = st.text_input("Construction", _clean(prop.get("construction_type")), key=f"ct_{idx}")
                        with p2:
                            prop["protection_class"] = st.text_input("Protection Class", _clean(prop.get("protection_class")), key=f"pc_{idx}")
                            prop["roof_type"] = st.text_input("Roof Type", _clean(prop.get("roof_type")), key=f"rt_{idx}")
                        with p3:
                            prop["square_footage"] = st.number_input("Sq Ft", value=int(_num(prop.get("square_footage"))), key=f"sf_{idx}")
                            prop["number_of_stories"] = st.number_input("Stories", value=int(_num(prop.get("number_of_stories"))), key=f"ns_{idx}")
                        with p4:
                            prop["foundation_type"] = st.text_input("Foundation", _clean(prop.get("foundation_type")), key=f"ft_{idx}")
                        pol["property"] = prop

                    # Vehicles
                    vehicles = pol.get("vehicles") or []
                    if vehicles:
                        st.markdown("##### Scheduled Vehicles")
                        for vi, veh in enumerate(vehicles):
                            v1, v2, v3, v4 = st.columns([1, 3, 3, 2])
                            with v1:
                                veh["unit"] = st.number_input("Unit", value=int(_num(veh.get("unit"), 1)), key=f"vu_{idx}_{vi}")
                            with v2:
                                veh["year_make_model"] = st.text_input("Year/Make/Model", _clean(veh.get("year_make_model")), key=f"vm_{idx}_{vi}")
                            with v3:
                                veh["vin"] = st.text_input("VIN", _clean(veh.get("vin")), key=f"vv_{idx}_{vi}")
                            with v4:
                                veh["stated_value"] = st.number_input("Value ($)", value=_num(veh.get("stated_value")), key=f"vs_{idx}_{vi}")
                        pol["vehicles"] = vehicles

                    # Endorsements
                    endorsements = pol.get("endorsements") or []
                    if endorsements:
                        st.markdown("##### Endorsements")
                        for ei, end in enumerate(endorsements):
                            e1, e2, e3 = st.columns([3, 2, 4])
                            with e1:
                                end["name"] = st.text_input("Name", _clean(end.get("name")), key=f"en_{idx}_{ei}")
                            with e2:
                                end["limit"] = st.number_input("Limit ($)", value=_num(end.get("limit")), key=f"el_{idx}_{ei}")
                            with e3:
                                end["description"] = st.text_input("Description", _clean(end.get("description")), key=f"ed2_{idx}_{ei}")
                        pol["endorsements"] = endorsements

                    # Extra Metadata
                    extra = pol.get("extra_metadata") or []
                    if extra:
                        st.markdown("##### Additional Metadata")
                        for mi, meta in enumerate(extra):
                            m1, m2, m3 = st.columns([3, 4, 2])
                            with m1:
                                meta["field"] = st.text_input("Field", _clean(meta.get("field")), key=f"mf_{idx}_{mi}")
                            with m2:
                                meta["value"] = st.text_input("Value", _clean(meta.get("value")), key=f"mv_{idx}_{mi}")
                            with m3:
                                meta["type"] = st.selectbox("Type", ["TEXT", "NUMBER", "DATE"],
                                    index=["TEXT", "NUMBER", "DATE"].index(_clean(meta.get("type"), "TEXT")) if _clean(meta.get("type"), "TEXT") in ["TEXT", "NUMBER", "DATE"] else 0,
                                    key=f"mt_{idx}_{mi}")
                        pol["extra_metadata"] = extra

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Back to Upload", icon=":material/arrow_back:", key="pol_back"):
                    st.session_state.intake_step = "upload"
                    st.session_state.extracted_policies = []
                    st.rerun()
            with col2:
                ready_count = sum(1 for p in st.session_state.extracted_policies if p.get("_status") == "Ready")
                st.markdown(f"**{ready_count} policy(s) ready to commit**")
            with col3:
                if st.button("Commit to Database", type="primary", icon=":material/database:", key="pol_commit"):
                    st.session_state.intake_step = "commit"
                    st.rerun()

    # --- STEP 3: COMMIT ---
    elif st.session_state.intake_step == "commit":
        st.subheader("Step 3  Committing to Database")
        success_count = 0
        error_count = 0

        for pol in st.session_state.extracted_policies:
            if pol.get("_status") != "Ready":
                continue

            policy_id = _clean(pol.get("policy_number"))
            if not policy_id:
                st.error(f"Skipping {pol.get('_file_name')} — no policy number")
                error_count += 1
                continue

            try:
                with st.spinner(f"Processing {policy_id}..."):
                    cust_id = f"CUST-PDF-{policy_id[-5:]}"
                    tables_updated = ["CUSTOMERS", "POLICIES"]

                    first = _clean(pol.get("first_name"))
                    last = _clean(pol.get("last_name"))
                    named = _clean(pol.get("named_insured"))
                    if not first and not last and named:
                        first = named
                    elif not first:
                        first = "Unknown"
                    addr = _clean(pol.get("address")).replace("'", "''")
                    city = _clean(pol.get("city")).replace("'", "''")
                    state = _clean(pol.get("state"))
                    zipcode = _clean(pol.get("zip_code"))
                    eff_date = _clean(pol.get("effective_date"))
                    exp_date = _clean(pol.get("expiration_date"))
                    ptype = _clean(pol.get("policy_type"), "Homeowners").replace("'", "''")
                    pstatus = _clean(pol.get("policy_status"), "Active")
                    premium = _num(pol.get("annual_premium"))
                    coverage = _num(pol.get("coverage_amount"))
                    if not coverage:
                        for cov in (pol.get("coverages") or []):
                            line = _clean(cov.get("line")).lower()
                            if "dwelling" in line or "building" in line or "coverage a" in line:
                                coverage = _num(cov.get("limit"))
                                break
                    deductible_val = _num(pol.get("deductible"))
                    if not deductible_val:
                        for cov in (pol.get("coverages") or []):
                            line = _clean(cov.get("line")).lower()
                            if "all-peril" in line or ("deductible" in line and "wind" not in line and "collision" not in line):
                                deductible_val = _num(cov.get("deductible"))
                                if deductible_val:
                                    break
                    construction = _clean((pol.get("property") or {}).get("construction_type"), "Unknown").replace("'", "''")
                    biz_desc = _clean(pol.get("business_description")).replace("'", "''")
                    cancel_date = _clean(pol.get("cancellation_date"))
                    cancel_reason = _clean(pol.get("cancellation_reason")).replace("'", "''")
                    return_prem = _num(pol.get("return_premium"))
                    lob = "Commercial Lines" if "commercial" in ptype.lower() else "Personal Lines"
                    renewal = "Auto-Renew"
                    if pstatus == "Cancelled":
                        renewal = "Cancelled"
                    elif pstatus == "Non-Renewed":
                        renewal = "Non-Renewed"

                    # MERGE CUSTOMERS
                    session.sql(f"""
                        MERGE INTO INSURANCE_AI_HUB.ANALYTICS.CUSTOMERS t
                        USING (SELECT
                            '{cust_id}' AS CUSTOMER_ID,
                            'SF-PDF-{policy_id[-5:]}' AS SALESFORCE_ACCOUNT_ID,
                            '{first.replace("'", "''")}' AS FIRST_NAME,
                            '{last.replace("'", "''")}' AS LAST_NAME,
                            '{addr}' AS ADDRESS, '{city}' AS CITY,
                            '{state}' AS STATE, '{zipcode}' AS ZIP_CODE
                        ) s ON t.CUSTOMER_ID = s.CUSTOMER_ID
                        WHEN NOT MATCHED THEN INSERT (CUSTOMER_ID, SALESFORCE_ACCOUNT_ID, FIRST_NAME, LAST_NAME, DATE_OF_BIRTH, ADDRESS, CITY, STATE, ZIP_CODE, RISK_TIER, SEGMENT, CREDIT_SCORE, CUSTOMER_SINCE)
                        VALUES (s.CUSTOMER_ID, s.SALESFORCE_ACCOUNT_ID, s.FIRST_NAME, s.LAST_NAME, '1990-01-01'::DATE, s.ADDRESS, s.CITY, s.STATE, s.ZIP_CODE, 'Medium', 'Standard', 700, CURRENT_DATE())
                    """).collect()

                    # MERGE POLICIES
                    cancel_date_sql = f"'{cancel_date}'::DATE" if cancel_date else "NULL"
                    cancel_reason_sql = f"'{cancel_reason}'" if cancel_reason else "NULL"
                    return_prem_sql = str(return_prem) if return_prem else "NULL"
                    biz_desc_sql = f"'{biz_desc}'" if biz_desc else "NULL"
                    session.sql(f"""
                        MERGE INTO INSURANCE_AI_HUB.ANALYTICS.POLICIES t
                        USING (SELECT
                            '{policy_id}' AS POLICY_ID, '{policy_id}' AS POLICY_NUMBER,
                            '{cust_id}' AS CUSTOMER_ID, 'AGT-PDF-001' AS AGENT_ID,
                            '{ptype}' AS POLICY_TYPE, '{lob}' AS LINE_OF_BUSINESS,
                            'HO-3' AS COVERAGE_TIER,
                            '{eff_date}'::DATE AS EFFECTIVE_DATE, '{exp_date}'::DATE AS EXPIRATION_DATE,
                            {premium} AS PREMIUM_AMOUNT, {coverage} AS COVERAGE_AMOUNT,
                            {deductible_val} AS DEDUCTIBLE, '{state}' AS ISSUING_STATE,
                            '{pstatus}' AS STATUS, '{renewal}' AS RENEWAL_STATUS,
                            {cancel_date_sql} AS CANCELLATION_DATE,
                            {cancel_reason_sql} AS CANCELLATION_REASON,
                            {return_prem_sql} AS RETURN_PREMIUM,
                            {biz_desc_sql} AS BUSINESS_DESCRIPTION
                        ) s ON t.POLICY_ID = s.POLICY_ID
                        WHEN MATCHED THEN UPDATE SET
                            t.PREMIUM_AMOUNT = s.PREMIUM_AMOUNT, t.COVERAGE_AMOUNT = s.COVERAGE_AMOUNT,
                            t.DEDUCTIBLE = s.DEDUCTIBLE, t.EFFECTIVE_DATE = s.EFFECTIVE_DATE,
                            t.EXPIRATION_DATE = s.EXPIRATION_DATE, t.STATUS = s.STATUS,
                            t.RENEWAL_STATUS = s.RENEWAL_STATUS, t.CANCELLATION_DATE = s.CANCELLATION_DATE,
                            t.CANCELLATION_REASON = s.CANCELLATION_REASON, t.RETURN_PREMIUM = s.RETURN_PREMIUM,
                            t.BUSINESS_DESCRIPTION = s.BUSINESS_DESCRIPTION
                        WHEN NOT MATCHED THEN INSERT (POLICY_ID, POLICY_NUMBER, CUSTOMER_ID, AGENT_ID, POLICY_TYPE, LINE_OF_BUSINESS, COVERAGE_TIER,
                            EFFECTIVE_DATE, EXPIRATION_DATE, BOUND_DATE, POLICY_TERM_MONTHS, ISSUING_STATE,
                            PREMIUM_AMOUNT, COVERAGE_AMOUNT, DEDUCTIBLE, STATUS, RENEWAL_STATUS,
                            CANCELLATION_DATE, CANCELLATION_REASON, RETURN_PREMIUM, BUSINESS_DESCRIPTION, CREATED_AT)
                        VALUES (s.POLICY_ID, s.POLICY_NUMBER, s.CUSTOMER_ID, s.AGENT_ID, s.POLICY_TYPE, s.LINE_OF_BUSINESS, s.COVERAGE_TIER,
                            s.EFFECTIVE_DATE, s.EXPIRATION_DATE, s.EFFECTIVE_DATE, 12, s.ISSUING_STATE,
                            s.PREMIUM_AMOUNT, s.COVERAGE_AMOUNT, s.DEDUCTIBLE, s.STATUS, s.RENEWAL_STATUS,
                            s.CANCELLATION_DATE, s.CANCELLATION_REASON, s.RETURN_PREMIUM, s.BUSINESS_DESCRIPTION, CURRENT_TIMESTAMP())
                    """).collect()

                    # MERGE PROPERTY_CHARACTERISTICS
                    prop = pol.get("property") or {}
                    yr = int(_num(prop.get("year_built")))
                    if yr > 0:
                        prop_id = f"PROP-PDF-{policy_id[-5:]}"
                        pclass = _clean(prop.get("protection_class")).replace("'", "''")
                        roof = _clean(prop.get("roof_type"), "Unknown").replace("'", "''")
                        foundation = _clean(prop.get("foundation_type"), "Unknown").replace("'", "''")
                        sqft = int(_num(prop.get("square_footage")))
                        stories = int(_num(prop.get("number_of_stories"), 1)) or 1
                        session.sql(f"""
                            MERGE INTO INSURANCE_AI_HUB.ANALYTICS.PROPERTY_CHARACTERISTICS t
                            USING (SELECT '{policy_id}' AS POLICY_ID) s ON t.POLICY_ID = s.POLICY_ID
                            WHEN MATCHED THEN UPDATE SET
                                t.YEAR_BUILT = {yr}, t.CONSTRUCTION_TYPE = '{construction}',
                                t.ROOF_TYPE = '{roof}', t.FOUNDATION_TYPE = '{foundation}',
                                t.SQUARE_FOOTAGE = {sqft}, t.NUMBER_OF_STORIES = {stories},
                                t.PROTECTION_CLASS = '{pclass}', t.REPLACEMENT_COST = {coverage}
                            WHEN NOT MATCHED THEN INSERT (
                                PROPERTY_ID, POLICY_ID, CONSTRUCTION_TYPE, YEAR_BUILT, SQUARE_FOOTAGE,
                                NUMBER_OF_STORIES, ROOF_TYPE, FOUNDATION_TYPE, FIRE_PROTECTION,
                                PROPERTY_USE, REPLACEMENT_COST, FLOOD_ZONE, PROTECTION_CLASS
                            ) VALUES (
                                '{prop_id}', '{policy_id}', '{construction}',
                                {yr}, {sqft}, {stories}, '{roof}', '{foundation}', 'Standard',
                                'Primary Residence', {coverage}, 'Unknown', '{pclass}'
                            )
                        """).collect()
                        tables_updated.append("PROPERTY_CHARACTERISTICS")

                    # COVERAGE_DETAILS
                    coverages = pol.get("coverages") or []
                    if coverages:
                        session.sql(f"DELETE FROM INSURANCE_AI_HUB.ANALYTICS.COVERAGE_DETAILS WHERE POLICY_ID = '{policy_id}'").collect()
                        for ci, cov in enumerate(coverages):
                            cov_id = f"COV-{policy_id[-5:]}-{ci+1:02d}"
                            line = _clean(cov.get("line")).replace("'", "''")
                            limit_val = _num(cov.get("limit"))
                            ded = _num(cov.get("deductible"))
                            ded_type = _clean(cov.get("deductible_type"), "Flat")
                            notes = _clean(cov.get("notes")).replace("'", "''")
                            session.sql(f"""
                                INSERT INTO INSURANCE_AI_HUB.ANALYTICS.COVERAGE_DETAILS
                                (COVERAGE_ID, POLICY_ID, COVERAGE_LINE, COVERAGE_LIMIT, DEDUCTIBLE_AMOUNT, DEDUCTIBLE_TYPE, NOTES)
                                VALUES ('{cov_id}', '{policy_id}', '{line}', {limit_val}, {ded}, '{ded_type}', '{notes}')
                            """).collect()
                        tables_updated.append("COVERAGE_DETAILS")

                    # VEHICLE_SCHEDULE
                    vehicles = pol.get("vehicles") or []
                    if vehicles:
                        session.sql(f"DELETE FROM INSURANCE_AI_HUB.ANALYTICS.VEHICLE_SCHEDULE WHERE POLICY_ID = '{policy_id}'").collect()
                        for vi, veh in enumerate(vehicles):
                            veh_id = f"VEH-{policy_id[-5:]}-{vi+1:02d}"
                            unit = int(_num(veh.get("unit"), vi+1))
                            ymm = _clean(veh.get("year_make_model")).replace("'", "''")
                            vin = _clean(veh.get("vin")).replace("'", "''")
                            garag = _clean(veh.get("garaging_location")).replace("'", "''")
                            sval = _num(veh.get("stated_value"))
                            session.sql(f"""
                                INSERT INTO INSURANCE_AI_HUB.ANALYTICS.VEHICLE_SCHEDULE
                                (VEHICLE_ID, POLICY_ID, UNIT_NUMBER, YEAR_MAKE_MODEL, VIN, GARAGING_LOCATION, STATED_VALUE)
                                VALUES ('{veh_id}', '{policy_id}', {unit}, '{ymm}', '{vin}', '{garag}', {sval})
                            """).collect()
                        tables_updated.append("VEHICLE_SCHEDULE")

                    # POLICY_ENDORSEMENTS
                    endorsements = pol.get("endorsements") or []
                    if endorsements:
                        session.sql(f"DELETE FROM INSURANCE_AI_HUB.ANALYTICS.POLICY_ENDORSEMENTS WHERE POLICY_ID = '{policy_id}'").collect()
                        for ei, end in enumerate(endorsements):
                            end_id = f"END-{policy_id[-5:]}-{ei+1:02d}"
                            ename = _clean(end.get("name")).replace("'", "''")
                            elimit = _num(end.get("limit"))
                            edesc = _clean(end.get("description")).replace("'", "''")
                            session.sql(f"""
                                INSERT INTO INSURANCE_AI_HUB.ANALYTICS.POLICY_ENDORSEMENTS
                                (ENDORSEMENT_ID, POLICY_ID, ENDORSEMENT_NAME, ENDORSEMENT_LIMIT, DESCRIPTION)
                                VALUES ('{end_id}', '{policy_id}', '{ename}', {elimit}, '{edesc}')
                            """).collect()
                        tables_updated.append("POLICY_ENDORSEMENTS")

                    # POLICY_METADATA
                    extra = pol.get("extra_metadata") or []
                    if extra:
                        session.sql(f"DELETE FROM INSURANCE_AI_HUB.ANALYTICS.POLICY_METADATA WHERE POLICY_ID = '{policy_id}'").collect()
                        for mi, meta in enumerate(extra):
                            meta_id = f"META-{policy_id[-5:]}-{mi+1:02d}"
                            fname = _clean(meta.get("field")).replace("'", "''")
                            fval = _clean(meta.get("value")).replace("'", "''")
                            ftype = _clean(meta.get("type"), "TEXT")
                            if fname:
                                session.sql(f"""
                                    INSERT INTO INSURANCE_AI_HUB.ANALYTICS.POLICY_METADATA
                                    (METADATA_ID, POLICY_ID, FIELD_NAME, FIELD_VALUE, FIELD_TYPE)
                                    VALUES ('{meta_id}', '{policy_id}', '{fname}', '{fval}', '{ftype}')
                                """).collect()
                        tables_updated.append("POLICY_METADATA")

                    # Audit Log
                    json_str = json.dumps({k: v for k, v in pol.items() if not k.startswith("_")}, default=str).replace("'", "''")
                    tables_arr = ", ".join([f"'{t}'" for t in tables_updated])
                    session.sql(f"""
                        INSERT INTO INSURANCE_AI_HUB.ANALYTICS.PDF_INGESTION_LOG
                        (FILE_NAME, POLICY_ID, DOCUMENT_TYPE, TABLES_UPDATED, EXTRACTED_JSON, STATUS, INGESTED_BY)
                        SELECT '{_clean(pol.get("_file_name")).replace("'", "''")}', '{policy_id}',
                            '{ptype}', ARRAY_CONSTRUCT({tables_arr}),
                            PARSE_JSON('{json_str}'), 'SUCCESS', CURRENT_USER()
                    """).collect()

                    st.success(f"**{policy_id}** — committed to {', '.join(tables_updated)}")
                    success_count += 1

            except Exception as e:
                st.error(f"**{policy_id}** — Error: {str(e)}")
                error_count += 1

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Committed", str(success_count), border=True)
        with c2:
            st.metric("Errors", str(error_count), border=True)

        if st.button("Ingest More Documents", icon=":material/upload_file:", key="pol_more"):
            st.session_state.intake_step = "upload"
            st.session_state.extracted_policies = []
            st.rerun()

# ============================================================
# CLAIMS DOCUMENTS TAB
# ============================================================
with claims_tab:
    if "extracted_claims" not in st.session_state:
        st.session_state.extracted_claims = []
    if "claims_step" not in st.session_state:
        st.session_state.claims_step = "upload"

    # --- STEP 1: UPLOAD ---
    if st.session_state.claims_step == "upload":
        st.subheader("Step 1  Upload Claims Documents")
        st.caption("Upload FNOL forms, adjuster reports, proof of loss, subrogation letters, or medical bills.")

        claims_files = st.file_uploader("Drop claims PDF files here", type=["pdf"],
            accept_multiple_files=True, key="claims_upload")

        if claims_files and st.button("Extract Claims Data", type="primary", icon=":material/document_scanner:", key="extract_clm"):
            st.session_state.extracted_claims = []
            progress = st.progress(0, text="Extracting...")

            for i, file in enumerate(claims_files):
                file_name = file.name
                progress.progress((i + 1) / len(claims_files), text=f"Processing {file_name}...")
                try:
                    doc_text = _upload_and_parse(file)
                    prompt = CLAIMS_EXTRACT_PROMPT + doc_text[:8000]
                    llm_result = conn.query("SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS RESPONSE",
                        params=["claude-sonnet-4-6", prompt])
                    raw_response = llm_result["RESPONSE"].iloc[0]
                    clean = raw_response.strip()
                    if clean.startswith("```"):
                        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                    extracted = json.loads(clean)
                    extracted["_file_name"] = file_name
                    extracted["_status"] = "Ready"
                    st.session_state.extracted_claims.append(extracted)
                except json.JSONDecodeError:
                    st.session_state.extracted_claims.append({
                        "_file_name": file_name, "_status": "PARSE ERROR",
                        "_raw": raw_response[:500] if "raw_response" in dir() else "No response"})
                except Exception as e:
                    st.session_state.extracted_claims.append({
                        "_file_name": file_name, "_status": f"ERROR: {str(e)}"})

            progress.empty()
            st.session_state.claims_step = "review"
            st.rerun()

    # --- STEP 2: REVIEW ---
    elif st.session_state.claims_step == "review":
        st.subheader("Step 2  Review Claims Data")
        st.caption("Verify extracted fields before committing.")

        if not st.session_state.extracted_claims:
            st.warning("No extracted data.")
            if st.button("Back to Upload", key="clm_back_empty"):
                st.session_state.claims_step = "upload"
                st.rerun()
        else:
            for idx, clm in enumerate(st.session_state.extracted_claims):
                status = clm.get("_status", "Unknown")
                icon = ":green[Ready]" if status == "Ready" else f":red[{status}]"
                label = f"{clm.get('_file_name', 'Unknown')} — {_clean(clm.get('document_type', 'Unknown'))} — {icon}"

                with st.expander(label, expanded=(idx == 0)):
                    if status != "Ready":
                        st.error(f"Extraction failed: {status}")
                        if "_raw" in clm:
                            st.code(clm["_raw"][:500])
                        continue

                    # Document & Claim Info
                    st.markdown("##### Document & Claim Info")
                    r1, r2, r3 = st.columns(3)
                    with r1:
                        doc_types = ["FNOL", "Adjuster Report", "Proof of Loss", "Subrogation Letter", "Medical Bill", "Estimate", "Correspondence", "Other"]
                        cur_dt = _clean(clm.get("document_type"), "FNOL")
                        clm["document_type"] = st.selectbox("Document Type", doc_types,
                            index=doc_types.index(cur_dt) if cur_dt in doc_types else 0, key=f"cdt2_{idx}")
                        clm["claim_number"] = st.text_input("Claim #", _clean(clm.get("claim_number")), key=f"ccn_{idx}")
                        clm["policy_number"] = st.text_input("Policy #", _clean(clm.get("policy_number")), key=f"cpn_{idx}")
                    with r2:
                        clm["date_of_loss"] = st.text_input("Date of Loss", _clean(clm.get("date_of_loss")), key=f"cdol_{idx}")
                        clm["cause_of_loss"] = st.text_input("Cause of Loss", _clean(clm.get("cause_of_loss")), key=f"ccol_{idx}")
                        status_opts = ["Open", "Closed", "Under Investigation", "Denied", "Settled"]
                        cur_cs = _clean(clm.get("status"), "Open")
                        clm["status"] = st.selectbox("Claim Status", status_opts,
                            index=status_opts.index(cur_cs) if cur_cs in status_opts else 0, key=f"ccs_{idx}")
                    with r3:
                        clm["reported_by"] = st.text_input("Reported By", _clean(clm.get("reported_by")), key=f"crb_{idx}")
                        clm["claimant_name"] = st.text_input("Claimant", _clean(clm.get("claimant_name")), key=f"ccnm_{idx}")
                        clm["adjuster_name"] = st.text_input("Adjuster", _clean(clm.get("adjuster_name")), key=f"cadj_{idx}")

                    clm["loss_description"] = st.text_area("Loss Description", _clean(clm.get("loss_description")), height=80, key=f"cld_{idx}")

                    # Financial
                    st.markdown("##### Financial Details")
                    f1, f2, f3, f4 = st.columns(4)
                    with f1:
                        clm["damage_estimate"] = st.number_input("Damage Est ($)", value=_num(clm.get("damage_estimate")), key=f"cde_{idx}")
                    with f2:
                        clm["settlement_amount"] = st.number_input("Settlement ($)", value=_num(clm.get("settlement_amount")), key=f"csa_{idx}")
                    with f3:
                        clm["deductible_applied"] = st.number_input("Deductible ($)", value=_num(clm.get("deductible_applied")), key=f"cda_{idx}")
                    with f4:
                        clm["recovery_amount"] = st.number_input("Recovery ($)", value=_num(clm.get("recovery_amount")), key=f"cra_{idx}")

                    # Liability & Injury
                    li1, li2, li3 = st.columns(3)
                    with li1:
                        clm["liability_determination"] = st.text_input("Liability", _clean(clm.get("liability_determination")), key=f"clib_{idx}")
                    with li2:
                        clm["injury_type"] = st.text_input("Injury Type", _clean(clm.get("injury_type")), key=f"cit_{idx}")
                    with li3:
                        clm["at_fault_party"] = st.text_input("At-Fault Party", _clean(clm.get("at_fault_party")), key=f"cafp_{idx}")

                    # Medical (if applicable)
                    if _clean(clm.get("document_type")) == "Medical Bill" or _num(clm.get("medical_amount_billed")):
                        st.markdown("##### Medical Details")
                        md1, md2, md3 = st.columns(3)
                        with md1:
                            clm["medical_provider"] = st.text_input("Provider", _clean(clm.get("medical_provider")), key=f"cmp_{idx}")
                        with md2:
                            clm["medical_amount_billed"] = st.number_input("Billed ($)", value=_num(clm.get("medical_amount_billed")), key=f"cmb_{idx}")
                        with md3:
                            clm["medical_amount_paid"] = st.number_input("Paid ($)", value=_num(clm.get("medical_amount_paid")), key=f"cmpd_{idx}")

                    # Line Items
                    items = clm.get("items") or []
                    if items:
                        st.markdown("##### Damage Line Items")
                        for ii, item in enumerate(items):
                            i1, i2, i3 = st.columns([5, 1, 2])
                            with i1:
                                item["description"] = st.text_input("Item", _clean(item.get("description")), key=f"cid_{idx}_{ii}")
                            with i2:
                                item["quantity"] = st.number_input("Qty", value=int(_num(item.get("quantity"), 1)), key=f"ciq_{idx}_{ii}")
                            with i3:
                                item["amount"] = st.number_input("Amount ($)", value=_num(item.get("amount")), key=f"cia_{idx}_{ii}")
                        clm["items"] = items

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Back to Upload", icon=":material/arrow_back:", key="clm_back"):
                    st.session_state.claims_step = "upload"
                    st.session_state.extracted_claims = []
                    st.rerun()
            with col2:
                ready_count = sum(1 for c in st.session_state.extracted_claims if c.get("_status") == "Ready")
                st.markdown(f"**{ready_count} document(s) ready to commit**")
            with col3:
                if st.button("Commit to Database", type="primary", icon=":material/database:", key="clm_commit"):
                    st.session_state.claims_step = "commit"
                    st.rerun()

    # --- STEP 3: COMMIT ---
    elif st.session_state.claims_step == "commit":
        st.subheader("Step 3  Committing Claims to Database")
        success_count = 0
        error_count = 0

        for clm in st.session_state.extracted_claims:
            if clm.get("_status") != "Ready":
                continue

            doc_type = _clean(clm.get("document_type"), "Unknown")
            claim_num = _clean(clm.get("claim_number"))
            policy_num = _clean(clm.get("policy_number"))
            file_name = _clean(clm.get("_file_name"))

            try:
                with st.spinner(f"Processing {file_name}..."):
                    import hashlib
                    doc_id = f"CDOC-{hashlib.md5(file_name.encode()).hexdigest()[:12]}"

                    dol = _clean(clm.get("date_of_loss"))
                    dol_sql = f"'{dol}'::DATE" if dol else "NULL"
                    cause = _clean(clm.get("cause_of_loss")).replace("'", "''")
                    desc = _clean(clm.get("loss_description")).replace("'", "''")[:2000]
                    reported = _clean(clm.get("reported_by")).replace("'", "''")
                    claimant = _clean(clm.get("claimant_name")).replace("'", "''")
                    contact = _clean(clm.get("claimant_contact")).replace("'", "''")
                    dmg_est = _num(clm.get("damage_estimate"))
                    dmg_sql = str(dmg_est) if dmg_est else "NULL"
                    liability = _clean(clm.get("liability_determination")).replace("'", "''")
                    injury = _clean(clm.get("injury_type")).replace("'", "''")
                    recovery = _num(clm.get("recovery_amount"))
                    recovery_sql = str(recovery) if recovery else "NULL"
                    fault = _clean(clm.get("at_fault_party")).replace("'", "''")
                    adjuster = _clean(clm.get("adjuster_name")).replace("'", "''")
                    cstatus = _clean(clm.get("status"), "Open")
                    claim_sql = f"'{claim_num}'" if claim_num else "NULL"
                    policy_sql = f"'{policy_num}'" if policy_num else "NULL"

                    json_str = json.dumps({k: v for k, v in clm.items() if not k.startswith("_")}, default=str).replace("'", "''")

                    session.sql(f"""
                        MERGE INTO INSURANCE_AI_HUB.ANALYTICS.CLAIM_DOCUMENTS t
                        USING (SELECT '{doc_id}' AS DOCUMENT_ID) s ON t.DOCUMENT_ID = s.DOCUMENT_ID
                        WHEN MATCHED THEN UPDATE SET
                            t.DOCUMENT_TYPE = '{doc_type}', t.DATE_OF_LOSS = {dol_sql},
                            t.CAUSE_OF_LOSS = '{cause}', t.LOSS_DESCRIPTION = '{desc}',
                            t.DAMAGE_ESTIMATE = {dmg_sql}, t.STATUS = '{cstatus}'
                        WHEN NOT MATCHED THEN INSERT (
                            DOCUMENT_ID, CLAIM_ID, POLICY_ID, DOCUMENT_TYPE, DATE_OF_LOSS,
                            CAUSE_OF_LOSS, LOSS_DESCRIPTION, REPORTED_BY, CLAIMANT_NAME,
                            CLAIMANT_CONTACT, DAMAGE_ESTIMATE, LIABILITY_DETERMINATION,
                            INJURY_TYPE, RECOVERY_AMOUNT, AT_FAULT_PARTY, ADJUSTER_NAME,
                            STATUS, EXTRACTED_JSON, SOURCE_FILE, INGESTED_BY
                        ) VALUES (
                            '{doc_id}', {claim_sql}, {policy_sql}, '{doc_type}', {dol_sql},
                            '{cause}', '{desc}', '{reported}', '{claimant}',
                            '{contact}', {dmg_sql}, '{liability}',
                            '{injury}', {recovery_sql}, '{fault}', '{adjuster}',
                            '{cstatus}', PARSE_JSON('{json_str}'),
                            '{file_name.replace("'", "''")}', CURRENT_USER()
                        )
                    """).collect()

                    # Also log to PDF_INGESTION_LOG
                    session.sql(f"""
                        INSERT INTO INSURANCE_AI_HUB.ANALYTICS.PDF_INGESTION_LOG
                        (FILE_NAME, POLICY_ID, DOCUMENT_TYPE, TABLES_UPDATED, EXTRACTED_JSON, STATUS, INGESTED_BY)
                        SELECT '{file_name.replace("'", "''")}', {policy_sql},
                            '{doc_type}', ARRAY_CONSTRUCT('CLAIM_DOCUMENTS'),
                            PARSE_JSON('{json_str}'), 'SUCCESS', CURRENT_USER()
                    """).collect()

                    st.success(f"**{file_name}** ({doc_type}) — committed to CLAIM_DOCUMENTS")
                    success_count += 1

            except Exception as e:
                st.error(f"**{file_name}** — Error: {str(e)}")
                error_count += 1

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Committed", str(success_count), border=True)
        with c2:
            st.metric("Errors", str(error_count), border=True)

        if st.button("Ingest More Claims", icon=":material/upload_file:", key="clm_more"):
            st.session_state.claims_step = "upload"
            st.session_state.extracted_claims = []
            st.rerun()

# ============================================================
# POLICY COMPARISON TAB
# ============================================================
with compare_tab:
    st.subheader("Policy Comparison Engine")
    st.caption("Select two policies to get an AI-generated comparison of coverages, endorsements, and gaps.")

    try:
        policies_list = run_query("""
            SELECT POLICY_ID, POLICY_TYPE, ISSUING_STATE, PREMIUM_AMOUNT, COVERAGE_AMOUNT
            FROM INSURANCE_AI_HUB.ANALYTICS.POLICIES
            ORDER BY CREATED_AT DESC LIMIT 100
        """)
    except Exception:
        policies_list = None

    if policies_list is not None and not policies_list.empty:
        policy_ids = policies_list["POLICY_ID"].tolist()

        col1, col2 = st.columns(2)
        with col1:
            pol_a = st.selectbox("Policy A", policy_ids, key="cmp_a")
        with col2:
            remaining = [p for p in policy_ids if p != pol_a]
            pol_b = st.selectbox("Policy B", remaining, key="cmp_b")

        if st.button("Compare Policies", type="primary", icon=":material/compare_arrows:"):
            with st.spinner("Loading policy details and running AI comparison..."):
                # Fetch details for both
                details = {}
                for pid in [pol_a, pol_b]:
                    pol_info = run_query(f"SELECT * FROM INSURANCE_AI_HUB.ANALYTICS.POLICIES WHERE POLICY_ID = '{pid}'")
                    cov_info = run_query(f"SELECT COVERAGE_LINE, COVERAGE_LIMIT, DEDUCTIBLE_AMOUNT, DEDUCTIBLE_TYPE FROM INSURANCE_AI_HUB.ANALYTICS.COVERAGE_DETAILS WHERE POLICY_ID = '{pid}'")
                    end_info = run_query(f"SELECT ENDORSEMENT_NAME, ENDORSEMENT_LIMIT, DESCRIPTION FROM INSURANCE_AI_HUB.ANALYTICS.POLICY_ENDORSEMENTS WHERE POLICY_ID = '{pid}'")
                    prop_info = run_query(f"SELECT * FROM INSURANCE_AI_HUB.ANALYTICS.PROPERTY_CHARACTERISTICS WHERE POLICY_ID = '{pid}'")

                    details[pid] = {
                        "policy": pol_info.to_string(index=False) if not pol_info.empty else "No policy data",
                        "coverages": cov_info.to_string(index=False) if not cov_info.empty else "No coverage details",
                        "endorsements": end_info.to_string(index=False) if not end_info.empty else "No endorsements",
                        "property": prop_info.to_string(index=False) if not prop_info.empty else "No property data",
                    }

                compare_prompt = (
                    f"You are an insurance policy comparison specialist. Compare these two policies in detail.\n\n"
                    f"=== POLICY A: {pol_a} ===\n"
                    f"Policy: {details[pol_a]['policy']}\n"
                    f"Coverages: {details[pol_a]['coverages']}\n"
                    f"Endorsements: {details[pol_a]['endorsements']}\n"
                    f"Property: {details[pol_a]['property']}\n\n"
                    f"=== POLICY B: {pol_b} ===\n"
                    f"Policy: {details[pol_b]['policy']}\n"
                    f"Coverages: {details[pol_b]['coverages']}\n"
                    f"Endorsements: {details[pol_b]['endorsements']}\n"
                    f"Property: {details[pol_b]['property']}\n\n"
                    f"Provide:\n"
                    f"1. **Side-by-Side Summary** — key differences in coverage, premium, deductible\n"
                    f"2. **Coverage Gaps** — what does Policy A cover that B doesn't, and vice versa\n"
                    f"3. **Endorsement Differences** — which endorsements are unique to each\n"
                    f"4. **Risk Assessment** — which policy provides better protection and why\n"
                    f"5. **Recommendation** — for an underwriter reviewing these policies\n"
                    f"Use specific numbers and coverage amounts."
                )

                result = conn.query(
                    "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS RESPONSE",
                    params=["claude-sonnet-4-6", compare_prompt],
                )

                with st.container(border=True):
                    st.markdown(f"### Comparison: {pol_a} vs {pol_b}")
                    st.markdown(result["RESPONSE"].iloc[0])

                # Show raw data side by side
                with st.expander("View Raw Coverage Data"):
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        st.markdown(f"**{pol_a} Coverages**")
                        cov_a = run_query(f"SELECT COVERAGE_LINE, COVERAGE_LIMIT, DEDUCTIBLE_AMOUNT FROM INSURANCE_AI_HUB.ANALYTICS.COVERAGE_DETAILS WHERE POLICY_ID = '{pol_a}'")
                        if not cov_a.empty:
                            st.dataframe(cov_a, hide_index=True, use_container_width=True)
                        else:
                            st.caption("No coverage details.")
                    with rc2:
                        st.markdown(f"**{pol_b} Coverages**")
                        cov_b = run_query(f"SELECT COVERAGE_LINE, COVERAGE_LIMIT, DEDUCTIBLE_AMOUNT FROM INSURANCE_AI_HUB.ANALYTICS.COVERAGE_DETAILS WHERE POLICY_ID = '{pol_b}'")
                        if not cov_b.empty:
                            st.dataframe(cov_b, hide_index=True, use_container_width=True)
                        else:
                            st.caption("No coverage details.")
    else:
        st.info("No policies found. Ingest policy PDFs first using the Policy Documents tab.")

# ============================================================
# SIDEBAR: INGESTION HISTORY
# ============================================================
with st.sidebar:
    with st.expander("Recent Ingestions"):
        try:
            log = run_query("""
                SELECT FILE_NAME, POLICY_ID, DOCUMENT_TYPE, STATUS, INGESTED_AT::DATE AS DATE
                FROM INSURANCE_AI_HUB.ANALYTICS.PDF_INGESTION_LOG
                ORDER BY INGESTED_AT DESC LIMIT 10
            """)
            if not log.empty:
                st.dataframe(log, hide_index=True, use_container_width=True)
            else:
                st.caption("No ingestions yet.")
        except Exception:
            st.caption("No ingestion history.")
