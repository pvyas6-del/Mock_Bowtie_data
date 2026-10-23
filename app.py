import json
import re
import pandas as pd
import altair as alt
import streamlit as st

st.set_page_config(page_title="Bowtie Insights", layout="wide")

css = """
<style>
.stApp {background: #f3f5f8;}
header[data-testid="stHeader"] {background: transparent; height: 2.5rem;}
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {display: none;}
[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"], [data-testid="stExpandSidebarButton"] {display: flex !important; visibility: visible !important; z-index: 1000000;}
#MainMenu, footer {visibility: hidden;}
.block-container {padding-top: 3rem; padding-bottom: 1rem; max-width: 1400px;}
section[data-testid="stSidebar"] {background: #e9eef5; border-right: 1px solid #d3dae6;}
div[data-testid="stVerticalBlockBorderWrapper"] {background: transparent; border: 1px solid #d3dae6 !important; border-radius: 10px; box-shadow: none;}
.brand {font-size: 26px; font-weight: 800; color: #14324a; letter-spacing: -0.5px;}
.brand span {color: #2a8fd6;}
.hero {background: transparent; border: 1px solid #d3dae6; border-radius: 10px; padding: 16px 20px; margin-bottom: 12px;}
.hero .title {font-size: 28px; font-weight: 800; color: #14324a; line-height: 1.2;}
.hero .sub {font-size: 12px; color: #6b7a90; margin-bottom: 8px;}
.hero .text {font-size: 15px; color: #2d3b4d; line-height: 1.5;}
.kpi {background: transparent; border: 1px solid #d3dae6; border-radius: 10px; padding: 12px 14px; min-height: 215px; border-top: 5px solid #6b7a90;}
.kpi .big {font-size: 30px; font-weight: 800; color: #14324a; margin-top: 6px; line-height: 1.1;}
.chip {display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 700; color: #ffffff;}
.topbar {background: #f3f5f8; border: 1px solid #d3dae6; border-radius: 10px; padding: 8px 14px; margin-bottom: 8px; font-size: 13px; color: #2d3b4d; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px;}
.topbar .tbk {margin-left: 14px; white-space: nowrap;}
.topbar .tbk b {color: #14324a; font-size: 15px;}
div[data-testid='stElementContainer']:has(.topbar), div.element-container:has(.topbar) {position: sticky; top: 2.5rem; z-index: 99; background: #f3f5f8;}
.jump {font-size: 12px; color: #6b7a90; margin-bottom: 6px;}
.jump a {color: #2a8fd6; text-decoration: none; margin: 0 4px;}
.pillf {display: inline-block; padding: 2px 10px; margin: 0 6px 6px 0; border: 1px solid #2a8fd6; color: #14324a; border-radius: 12px; font-size: 12px;}
.kpi .top {display: flex; justify-content: space-between; font-size: 11px; font-weight: 700;}
.kpi .tag {color: #6b7a90;}
.kpi .lab {font-size: 15px; font-weight: 700; color: #14324a; margin-top: 8px;}
.kpi .msg {font-size: 13px; color: #2d3b4d; margin-top: 6px; line-height: 1.4;}
.kpi .rule {font-size: 11px; color: #6b7a90; margin-top: 8px;}
.section {font-size: 13px; font-weight: 700; color: #6b7a90; text-transform: uppercase; letter-spacing: 0.5px; margin: 10px 0 6px 0;}
.rt {width: 100%; border-collapse: collapse; font-size: 13px; color: #2d3b4d;}
.rt th {text-align: left; padding: 8px 10px; border-bottom: 2px solid #e3e7ee; color: #6b7a90; font-size: 12px;}
.rt td {padding: 8px 10px; border-bottom: 1px solid #eef1f5;}
.pill {display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; color: #ffffff;}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

required = {
    "hazards": ["hazard_id", "bowtie_id", "hazard_name", "hazard_category", "definition_clear"],
    "top_events": ["top_event_id", "bowtie_id", "hazard_id", "top_event_name", "top_event_category"],
    "threats": ["threat_id", "bowtie_id", "top_event_id", "threat_name", "contribution", "human_error"],
    "consequences": ["consequence_id", "bowtie_id", "top_event_id", "consequence_name", "severity", "inherent_risk", "residual_risk"],
    "pathways": ["pathway_id", "bowtie_id", "top_event_id", "side", "element_id"],
    "barriers": ["barrier_id", "bowtie_id", "pathway_id", "barrier_name", "barrier_type", "function", "condition", "critical", "owner", "common_dependency", "auditable", "detect", "decide", "act"],
    "corrective_actions": ["action_id", "barrier_id", "action_description", "priority", "status", "due_date"],
    "degradation_factors": ["factor_id", "barrier_id", "factor_name", "factor_category"],
    "degradation_controls": ["control_id", "factor_id", "control_name", "control_condition"],
    "assurance_activities": ["activity_id", "barrier_id", "activity_type", "status", "result", "due_date", "completed_date", "planned_per_year", "actual_per_year"],
    "barrier_standards": ["link_id", "barrier_id", "standard_code", "verification_status", "conflict_flag"],
    "scoring_matrix": ["barrier_type", "function", "condition", "score"],
}
empty_ok = ["corrective_actions", "degradation_factors", "degradation_controls", "assurance_activities", "barrier_standards"]
nullable_fields = {
    "hazards": ["hazard_category"],
    "consequences": ["severity", "residual_risk"],
    "barriers": ["owner", "common_dependency", "detect", "decide", "act"],
    "degradation_factors": ["factor_category"],
    "assurance_activities": ["result", "completed_date"],
}
allowed = [
    ("barriers", "condition", ["Effective", "Partially Effective", "Not Effective", "Unknown"]),
    ("barriers", "critical", ["Yes", "No"]),
    ("barriers", "barrier_type", ["Passive Hardware", "Active Hardware", "Continuous Hardware", "Active Hardware + Human", "Active Human"]),
    ("barriers", "function", ["Elimination", "Prevention", "Control", "Mitigation"]),
    ("corrective_actions", "status", ["Completed", "Pending", "Overdue"]),
    ("corrective_actions", "priority", ["High", "Medium", "Low"]),
    ("pathways", "side", ["Threat", "Consequence"]),
    ("degradation_controls", "control_condition", ["Effective", "Partially Effective", "Not Effective", "Unknown"]),
    ("barriers", "auditable", ["Yes", "No"]),
    ("barriers", "detect", ["Yes", "No"]),
    ("barriers", "decide", ["Yes", "No"]),
    ("barriers", "act", ["Yes", "No"]),
    ("assurance_activities", "status", ["Completed", "Pending", "Overdue"]),
    ("assurance_activities", "result", ["Pass", "Fail"]),
    ("assurance_activities", "activity_type", ["Inspection", "Functional test", "Audit", "Drill"]),
    ("barrier_standards", "verification_status", ["Verified", "Pending", "Missing documentation"]),
    ("barrier_standards", "conflict_flag", ["Yes", "No"]),
]
id_columns = {
    "hazards": "hazard_id", "top_events": "top_event_id", "threats": "threat_id", "consequences": "consequence_id", "pathways": "pathway_id",
    "barriers": "barrier_id", "corrective_actions": "action_id", "degradation_factors": "factor_id", "degradation_controls": "control_id",
    "assurance_activities": "activity_id", "barrier_standards": "link_id",
}
links = [
    ("barriers", "pathway_id", "pathways", "pathway_id"),
    ("corrective_actions", "barrier_id", "barriers", "barrier_id"),
    ("degradation_factors", "barrier_id", "barriers", "barrier_id"),
    ("degradation_controls", "factor_id", "degradation_factors", "factor_id"),
    ("assurance_activities", "barrier_id", "barriers", "barrier_id"),
    ("barrier_standards", "barrier_id", "barriers", "barrier_id"),
    ("top_events", "hazard_id", "hazards", "hazard_id"),
    ("threats", "top_event_id", "top_events", "top_event_id"),
    ("consequences", "top_event_id", "top_events", "top_event_id"),
]
checks = []


def add_check(group, name, passed, detail):
    if passed:
        result = "Pass"
    else:
        result = "FAIL"
    checks.append({"group": group, "check": name, "result": result, "detail": detail})


def has_columns(table_name, cols):
    for c in cols:
        if c not in raw[table_name].columns:
            return False
    return True


try:
    with open("mock_bowtie_data.json") as f:
        data = json.load(f)
except FileNotFoundError:
    st.error("mock_bowtie_data.json was not found. Put it in the same folder as app.py and rerun.")
    st.stop()
except json.JSONDecodeError:
    st.error("mock_bowtie_data.json is not valid JSON.")
    st.stop()

raw = {}
for table_name in required:
    rows = data.get(table_name)
    if rows is None:
        add_check("Schema", table_name + ": table present", False, "table is missing from the JSON")
        raw[table_name] = pd.DataFrame(columns=required[table_name])
        continue
    frame = pd.DataFrame(rows)
    if len(frame) == 0 and table_name in empty_ok:
        frame = pd.DataFrame(columns=required[table_name])
    raw[table_name] = frame
    missing = [c for c in required[table_name] if c not in frame.columns]
    if missing:
        detail = "missing: " + ", ".join(missing)
    else:
        detail = "all " + str(len(required[table_name])) + " present, " + str(len(frame)) + " rows"
    add_check("Schema", table_name + ": required columns present", len(missing) == 0, detail)

as_of_text = data.get("as_of_date")
as_of = pd.to_datetime(as_of_text, errors="coerce")
add_check("Schema", "as_of_date is present and a real date", pd.notna(as_of), str(as_of_text))

for item in allowed:
    if has_columns(item[0], [item[1]]):
        values = raw[item[0]][item[1]].dropna().unique()
        bad = [str(v) for v in values if v not in item[2]]
        add_check("Allowed values", item[0] + "." + item[1], len(bad) == 0, "unexpected: " + ", ".join(bad) if bad else "all values allowed")
for table_name in id_columns:
    if has_columns(table_name, [id_columns[table_name]]):
        col = raw[table_name][id_columns[table_name]]
        add_check("IDs", table_name + ": ids not null and unique", bool(col.notna().all() and col.is_unique), str(len(col)) + " rows")
for link in links:
    if has_columns(link[0], [link[1]]) and has_columns(link[2], [link[3]]):
        parent = set(raw[link[2]][link[3]])
        orphans = [v for v in raw[link[0]][link[1]] if v not in parent]
        add_check("Links", link[0] + "." + link[1] + " exists in " + link[2], len(orphans) == 0, str(len(orphans)) + " orphans")

score_keys = ["barrier_type", "function", "condition"]
if has_columns("scoring_matrix", score_keys + ["score"]) and has_columns("barriers", score_keys):
    duplicate_keys = int(raw["scoring_matrix"].duplicated(subset=score_keys).sum())
    add_check("Scoring", "scoring matrix has one score per type, function and condition", duplicate_keys == 0, str(duplicate_keys) + " duplicate rows")
    matrix_keys = set(zip(raw["scoring_matrix"]["barrier_type"], raw["scoring_matrix"]["function"], raw["scoring_matrix"]["condition"]))
    unscored = [1 for k in zip(raw["barriers"]["barrier_type"], raw["barriers"]["function"], raw["barriers"]["condition"]) if k not in matrix_keys]
    add_check("Scoring", "every barrier has a score in the scoring matrix", len(unscored) == 0, str(len(unscored)) + " without a score")
    add_check("Scoring", "scores are numbers", bool(pd.to_numeric(raw["scoring_matrix"]["score"], errors="coerce").notna().all()), str(len(raw["scoring_matrix"])) + " rows")

for table_name in required:
    if has_columns(table_name, required[table_name]):
        for c in required[table_name]:
            if c in nullable_fields.get(table_name, []):
                continue
            missing_n = int(raw[table_name][c].isna().sum())
            add_check("Required values", table_name + "." + c + ": no missing values", missing_n == 0, str(missing_n) + " missing")

if has_columns("assurance_activities", ["planned_per_year", "actual_per_year"]):
    freq_ok = bool(pd.to_numeric(raw["assurance_activities"]["planned_per_year"], errors="coerce").notna().all() and pd.to_numeric(raw["assurance_activities"]["actual_per_year"], errors="coerce").notna().all())
    add_check("Assurance", "planned and actual test frequencies are numbers", freq_ok, str(len(raw["assurance_activities"])) + " rows")

if has_columns("scoring_matrix", ["score"]):
    scores_numeric = pd.to_numeric(raw["scoring_matrix"]["score"], errors="coerce")
    out_of_range = int((~scores_numeric.between(0, 100)).sum())
    add_check("Scoring", "scoring matrix scores are between 0 and 100", out_of_range == 0, str(out_of_range) + " outside 0 to 100")


def bowtie_match(group, name, child, child_key, parent, parent_key):
    if has_columns(child, [child_key, "bowtie_id"]) and has_columns(parent, [parent_key, "bowtie_id"]):
        lookup = raw[parent][[parent_key, "bowtie_id"]].rename(columns={"bowtie_id": "parent_bowtie"})
        joined = raw[child][[child_key, "bowtie_id"]].merge(lookup, left_on=child_key, right_on=parent_key, how="left", suffixes=("", "_p"))
        joined = joined[joined["parent_bowtie"].notna()]
        wrong = joined[joined["bowtie_id"] != joined["parent_bowtie"]]
        add_check(group, name, len(wrong) == 0, str(len(wrong)) + " mismatches")


bowtie_match("Bowtie consistency", "barrier bowtie matches its pathway bowtie", "barriers", "pathway_id", "pathways", "pathway_id")
bowtie_match("Bowtie consistency", "pathway bowtie matches its top event bowtie", "pathways", "top_event_id", "top_events", "top_event_id")
bowtie_match("Bowtie consistency", "top event bowtie matches its hazard bowtie", "top_events", "hazard_id", "hazards", "hazard_id")
bowtie_match("Bowtie consistency", "threat bowtie matches its top event bowtie", "threats", "top_event_id", "top_events", "top_event_id")
bowtie_match("Bowtie consistency", "consequence bowtie matches its top event bowtie", "consequences", "top_event_id", "top_events", "top_event_id")
if has_columns("pathways", ["side", "element_id", "bowtie_id"]) and has_columns("threats", ["threat_id", "bowtie_id"]) and has_columns("consequences", ["consequence_id", "bowtie_id"]):
    element_bowtie = {}
    for i in range(len(raw["threats"])):
        element_bowtie[("Threat", raw["threats"]["threat_id"][i])] = raw["threats"]["bowtie_id"][i]
    for i in range(len(raw["consequences"])):
        element_bowtie[("Consequence", raw["consequences"]["consequence_id"][i])] = raw["consequences"]["bowtie_id"][i]
    bad_elements = 0
    for i in range(len(raw["pathways"])):
        key = (raw["pathways"]["side"][i], raw["pathways"]["element_id"][i])
        if key not in element_bowtie or element_bowtie[key] != raw["pathways"]["bowtie_id"][i]:
            bad_elements = bad_elements + 1
    add_check("Bowtie consistency", "every pathway points to a threat or consequence of the same bowtie", bad_elements == 0, str(bad_elements) + " wrong")

blocking = pd.DataFrame(checks)
if (blocking["result"] == "FAIL").any():
    st.error("The data failed structural checks, so no dashboard is shown. Fix the items below and rerun.")
    st.dataframe(blocking[blocking["result"] == "FAIL"], use_container_width=True, hide_index=True)
    st.stop()

hazards = raw["hazards"].copy()
top_events = raw["top_events"].copy()
barriers = raw["barriers"].copy()
pathways = raw["pathways"].copy()
actions = raw["corrective_actions"].copy()
actions["due_parsed"] = pd.to_datetime(actions["due_date"], errors="coerce")
factors = raw["degradation_factors"].copy()
controls = raw["degradation_controls"].copy()
matrix = raw["scoring_matrix"].copy()
matrix["score"] = pd.to_numeric(matrix["score"], errors="raise")
matrix = matrix.rename(columns={"score": "barrier_score"})
assurance = raw["assurance_activities"].copy()
assurance["due_parsed"] = pd.to_datetime(assurance["due_date"], errors="coerce")
assurance["planned_per_year"] = pd.to_numeric(assurance["planned_per_year"], errors="raise")
assurance["actual_per_year"] = pd.to_numeric(assurance["actual_per_year"], errors="raise")
standards = raw["barrier_standards"].copy()

names = {}
for t in data["threats"]:
    names[t["threat_id"]] = t["threat_name"]
for c in data["consequences"]:
    names[c["consequence_id"]] = c["consequence_name"]

barriers = barriers.merge(matrix, on=["barrier_type", "function", "condition"], how="left", validate="many_to_one")
barriers["owner"] = barriers["owner"].fillna("Unassigned")
pathways["name"] = pathways["element_id"].map(names)
pathways["n_barriers"] = pathways["pathway_id"].map(barriers.groupby("pathway_id").size()).fillna(0).astype(int)
pathways["robustness"] = pathways["pathway_id"].map(barriers.groupby("pathway_id")["barrier_score"].mean()).fillna(0)

hazard_names = {}
for i in range(len(hazards)):
    hazard_names[hazards["bowtie_id"][i]] = hazards["hazard_name"][i]
top_event_names = {}
for i in range(len(top_events)):
    if top_events["bowtie_id"][i] not in top_event_names:
        top_event_names[top_events["bowtie_id"][i]] = top_events["top_event_name"][i]

view_names = ["Overview", "Condition", "Criticality", "Corrective Actions", "Type and Function", "Degradation", "Owner", "Validity", "Assurance", "KPIs", "Codes and Standards"]

presets = {"Custom": None, "Leadership": "Overview", "Operations": "Condition", "Assurance": "Assurance"}
if "view" not in st.session_state:
    st.session_state["view"] = "Overview"


def apply_preset():
    target = presets[st.session_state["preset"]]
    if target is not None:
        st.session_state["view"] = target


def reset_filters():
    for k in ["f_owner_", "f_condition_", "f_function_", "f_type_"]:
        st.session_state[k + st.session_state["bowtie"]] = []
    st.session_state["critical_only"] = False
    st.session_state["search"] = ""


st.sidebar.markdown("**1. Pick a bowtie**")
bowtie = st.sidebar.selectbox("Bowtie", list(hazard_names.keys()), format_func=lambda x: x + ": " + hazard_names[x], key="bowtie")
st.sidebar.markdown("**2. Pick a dashboard**")
st.sidebar.selectbox("Quick view by role", list(presets.keys()), key="preset", on_change=apply_preset)
view = st.sidebar.radio("Dashboard type", view_names, key="view")
st.sidebar.markdown("**3. Quick filters**")
critical_only = st.sidebar.toggle("Critical barriers only (charts and table; insight cards always use all barriers)", value=False, key="critical_only")
show_insights = st.sidebar.checkbox("Key insights", value=True)
show_charts = st.sidebar.checkbox("Charts", value=True)
show_table = st.sidebar.checkbox("Barriers ranked by risk", value=True)

barriers = barriers[barriers["bowtie_id"] == bowtie].reset_index(drop=True)
pathways = pathways[pathways["bowtie_id"] == bowtie].reset_index(drop=True)
actions = actions[actions["barrier_id"].isin(barriers["barrier_id"])].reset_index(drop=True)
factors = factors[factors["barrier_id"].isin(barriers["barrier_id"])].reset_index(drop=True)
assurance = assurance[assurance["barrier_id"].isin(barriers["barrier_id"])].reset_index(drop=True)
standards = standards[standards["barrier_id"].isin(barriers["barrier_id"])].reset_index(drop=True)
controls = controls[controls["factor_id"].isin(factors["factor_id"])].reset_index(drop=True)

if len(barriers) == 0 or len(pathways) == 0:
    st.warning("This bowtie has no barriers or pathways to analyse.")
    st.stop()

st.sidebar.markdown("**4. Advanced filters**")
with st.sidebar.expander("Owner, condition, function, type"):
    f_owner = st.multiselect("Owner", sorted(barriers["owner"].unique()), key="f_owner_" + bowtie)
    f_condition = st.multiselect("Condition", sorted(barriers["condition"].unique()), key="f_condition_" + bowtie)
    f_function = st.multiselect("Function", sorted(barriers["function"].unique()), key="f_function_" + bowtie)
    f_type = st.multiselect("Barrier type", sorted(barriers["barrier_type"].unique()), key="f_type_" + bowtie)
active_filters = []
if critical_only:
    active_filters.append("Critical barriers only")
if f_owner:
    active_filters.append("Owner: " + ", ".join(f_owner))
if f_condition:
    active_filters.append("Condition: " + ", ".join(f_condition))
if f_function:
    active_filters.append("Function: " + ", ".join(f_function))
if f_type:
    active_filters.append("Type: " + ", ".join(f_type))
scope_on = len(active_filters) > 0

condition_colors = {
    "Effective": "#2e9e5b",
    "Partially Effective": "#f2b632",
    "Not Effective": "#d64545",
    "Unknown": "#9aa0a6",
}
action_colors = {"Completed": "#2e9e5b", "Pending": "#f2b632", "Overdue": "#d64545"}
yes_no_colors = {"Yes": "#d64545", "No": "#a9c4d4"}
auditable_colors = {"Yes": "#2e9e5b", "No": "#d64545"}
result_colors = {"Pass": "#2e9e5b", "Fail": "#d64545", "Not done yet": "#9aa0a6"}
standard_colors = {"Verified": "#2e9e5b", "Pending": "#f2b632", "Missing documentation": "#d64545"}
kpi_colors = {"Planned": "#a9c4d4", "Actual": "#2a8fd6"}
band_colors = {"Strong": "#2e9e5b", "Moderate": "#9ccc65", "Weak": "#f2b632", "Critical": "#d64545"}
status_colors = {"ALERT": "#c62f2f", "OK": "#1f7a45", "INFO": "#5a6a80", "NA": "#7b8190"}
status_icons = {"ALERT": "\u25B2", "OK": "\u2714", "INFO": "\u25CF", "NA": "\u2013"}
status_words = {"ALERT": "Act now", "OK": "On track", "INFO": "For awareness", "NA": "Not applicable"}
risk_colors = {"Critical risk": "#d64545", "High risk": "#f08a24", "Medium risk": "#f2b632", "Low risk": "#2e9e5b"}
base_blue = "#2a8fd6"


def pct(a, b):
    if b == 0:
        return 0.0
    return a / b * 100


def safe_idxmax(series, default="None"):
    if len(series) == 0:
        return default
    return series.idxmax()


def safe_idxmin(series, default="None"):
    if len(series) == 0:
        return default
    return series.idxmin()


def get_status(value, rule, limit):
    if rule == "below":
        if value < limit:
            return "ALERT"
        return "OK"
    if rule == "above":
        if value > limit:
            return "ALERT"
        return "OK"
    return "INFO"


def band(score):
    if score >= 80:
        return "Strong"
    if score >= 60:
        return "Moderate"
    if score >= 40:
        return "Weak"
    return "Critical"


def risk_tag(row):
    if row["critical"] == "Yes" and row["condition"] != "Effective":
        return "Critical risk"
    if row["condition"] == "Not Effective" or row["condition"] == "Unknown":
        return "High risk"
    if row["condition"] == "Partially Effective":
        return "Medium risk"
    return "Low risk"


barriers["risk"] = barriers.apply(risk_tag, axis=1)
risk_order = {"Critical risk": 1, "High risk": 2, "Medium risk": 3, "Low risk": 4}
barriers["risk_rank"] = barriers["risk"].map(risk_order)
pathways["band"] = pathways["robustness"].apply(band)

barriers["verified"] = barriers["barrier_id"].isin(set(assurance[assurance["status"] == "Completed"]["barrier_id"]))
barriers["has_record"] = barriers["barrier_id"].isin(set(assurance["barrier_id"]))
barriers["overdue_check"] = barriers["barrier_id"].isin(set(assurance[assurance["status"] == "Overdue"]["barrier_id"]))
barriers["failed_check"] = barriers["barrier_id"].isin(set(assurance[assurance["result"] == "Fail"]["barrier_id"]))
barriers["short_tested"] = barriers["barrier_id"].isin(set(assurance[assurance["actual_per_year"] < assurance["planned_per_year"]]["barrier_id"]))
barriers["has_standard"] = barriers["barrier_id"].isin(set(standards["barrier_id"]))
barriers["std_unverified"] = barriers["barrier_id"].isin(set(standards[standards["verification_status"] != "Verified"]["barrier_id"]))
std_counts = standards.groupby("barrier_id").size()
barriers["multi_std"] = barriers["barrier_id"].isin(set(std_counts[std_counts >= 2].index))
barriers["std_conflict"] = barriers["barrier_id"].isin(set(standards[standards["conflict_flag"] == "Yes"]["barrier_id"]))
barriers["is_active"] = barriers["barrier_type"] != "Passive Hardware"
barriers["chain_missing"] = barriers["is_active"] & ((barriers["detect"] != "Yes") | (barriers["decide"] != "Yes") | (barriers["act"] != "Yes"))


def missing_elements(row):
    gone = []
    for e in ["detect", "decide", "act"]:
        if row[e] != "Yes":
            gone.append(e.capitalize())
    return ", ".join(gone)


def human_elements(row):
    present = 0
    for e in ["detect", "decide", "act"]:
        if row[e] == "Yes":
            present = present + 1
    if row["barrier_type"] == "Active Human":
        return present
    if row["barrier_type"] == "Active Hardware + Human":
        n = 0
        for e in ["decide", "act"]:
            if row[e] == "Yes":
                n = n + 1
        return n
    return 0


barriers["missing"] = barriers.apply(missing_elements, axis=1)
barriers["elements"] = barriers.apply(lambda r: sum([1 for e in ["detect", "decide", "act"] if r[e] == "Yes"]), axis=1)
barriers["human_elements"] = barriers.apply(human_elements, axis=1)
barriers["fails_audit_trait"] = (barriers["auditable"] != "Yes") | (~barriers["has_record"])
barriers["audit_ready"] = ~barriers["fails_audit_trait"]

hazard = hazard_names[bowtie]
top_event = top_event_names[bowtie]

total = len(barriers)
effective = len(barriers[barriers["condition"] == "Effective"])
partial = len(barriers[barriers["condition"] == "Partially Effective"])
not_working = total - effective - partial
eff_pct = pct(effective, total)
critical = barriers[barriers["critical"] == "Yes"]
critical_bad = critical[critical["condition"] != "Effective"]
avg_robust = pathways["robustness"].mean()

full_actions = actions.merge(barriers[["barrier_id", "barrier_name", "critical", "owner"]], on="barrier_id", how="left")
degraded = barriers[barriers["condition"] != "Effective"]
open_actions = actions[actions["status"].isin(["Pending", "Overdue"])]
no_action = degraded[~degraded["barrier_id"].isin(open_actions["barrier_id"])]
critical_actions = full_actions[full_actions["critical"] == "Yes"]
overdue_all = full_actions[full_actions["status"] == "Overdue"].sort_values("due_parsed")
overdue_critical = critical_actions[critical_actions["status"] == "Overdue"]
overdue_pct = pct(len(overdue_critical), len(critical_actions))
overdue_barriers = overdue_critical["barrier_id"].nunique()
low_critical = critical_actions[critical_actions["priority"] == "Low"]

unassigned = barriers[barriers["owner"] == "Unassigned"]
unassigned_critical = critical[critical["owner"] == "Unassigned"]
critical_by_owner = critical.groupby("owner").size()
if len(critical) > 0:
    top_owner = critical_by_owner.idxmax()
    top_share = pct(critical_by_owner.max(), len(critical))
else:
    top_owner = "Nobody"
    top_share = 0.0

human_types = ["Active Human", "Active Hardware + Human"]
human_pct = pct(len(barriers[barriers["barrier_type"].isin(human_types)]), total)
type_counts = barriers.groupby("barrier_type").size()
top_type = safe_idxmax(type_counts, "None")
top_type_pct = pct(type_counts.max(), total)
function_counts = barriers.groupby("function").size()
top_function = safe_idxmax(function_counts, "None")
top_function_pct = pct(function_counts.max(), total)
critical_type_counts = critical.groupby("barrier_type").size()
if len(critical) > 0:
    crit_type = critical_type_counts.idxmax()
    crit_type_pct = pct(critical_type_counts.max(), len(critical))
else:
    crit_type = "None"
    crit_type_pct = 0.0

n_functions = barriers.groupby("pathway_id")["function"].nunique()
pathways["n_functions"] = pathways["pathway_id"].map(n_functions).fillna(0).astype(int)
few_functions = pathways[pathways["n_functions"] < 2]
n_critical = critical.groupby("pathway_id").size()
pathways["n_critical"] = pathways["pathway_id"].map(n_critical).fillna(0).astype(int)
no_critical = pathways[pathways["n_critical"] == 0]
one_critical = pathways[pathways["n_critical"] == 1]
by_function = barriers.groupby("function")["condition"].apply(lambda s: (s == "Effective").mean() * 100)
weakest_function = safe_idxmin(by_function, "None")

effective_paths = set(barriers[barriers["condition"] == "Effective"]["pathway_id"])
threat_paths = pathways[pathways["side"] == "Threat"]
threats_no_eff = threat_paths[~threat_paths["pathway_id"].isin(effective_paths)]
threats_no_eff_pct = pct(len(threats_no_eff), len(threat_paths))

spof_ids = []
for pid in barriers["pathway_id"].unique():
    mine = barriers[barriers["pathway_id"] == pid]
    if len(mine) >= 2 and mine["owner"].nunique() == 1 and len(mine[mine["critical"] == "Yes"]) > 0:
        spof_ids.append(pid)
spof_paths = pathways[pathways["pathway_id"].isin(spof_ids)]

def owner_stats(bdf, adf):
    owner_rows = []
    for owner in bdf["owner"].unique():
        mine = bdf[bdf["owner"] == owner]
        acts = adf[adf["owner"] == owner]
        owner_rows.append({
            "owner": owner,
            "barriers": len(mine),
            "critical": len(mine[mine["critical"] == "Yes"]),
            "human_pct": round(pct(len(mine[mine["barrier_type"].isin(human_types)]), len(mine)), 1),
            "ineffective_pct": round(pct(len(mine[mine["condition"] != "Effective"]), len(mine)), 1),
            "reactive_pct": round(pct(len(mine[mine["function"].isin(["Control", "Mitigation"])]), len(mine)), 1),
            "overdue_pct": round(pct(len(acts[acts["status"] == "Overdue"]), len(acts)), 1),
        })
    return pd.DataFrame(owner_rows, columns=["owner", "barriers", "critical", "human_pct", "ineffective_pct", "reactive_pct", "overdue_pct"])


owner_df = owner_stats(barriers, full_actions)
owners_ineffective = owner_df[owner_df["ineffective_pct"] > 20]
owners_human = owner_df[owner_df["human_pct"] > 50]
owners_reactive = owner_df[owner_df["reactive_pct"] > 80]
owners_overdue = owner_df[owner_df["overdue_pct"] > 20]

fac = factors.merge(barriers[["barrier_id", "barrier_name", "critical"]], on="barrier_id", how="left")
working = controls[controls["control_condition"].isin(["Effective", "Partially Effective"])].groupby("factor_id").size()
fac["working_controls"] = fac["factor_id"].map(working).fillna(0).astype(int)
fac["has_control"] = fac["factor_id"].isin(controls["factor_id"])
unmanaged = fac[fac["working_controls"] == 0]
exposed = unmanaged[unmanaged["critical"] == "Yes"]
exposed_count = exposed["barrier_id"].nunique()
classified_pct = pct(fac["factor_category"].notna().sum(), len(fac))
control_pct = pct(fac["has_control"].sum(), len(fac))
unmanaged_pct = pct(len(unmanaged), len(fac))
weak_controls = controls[controls["control_condition"].isin(["Not Effective", "Unknown"])]
weak_pct = pct(len(weak_controls), len(controls))
fac["category"] = fac["factor_category"].fillna("Unclassified")
fac["controls_working"] = fac["working_controls"].clip(upper=2).map({0: "None working", 1: "One working", 2: "Two or more"})

ranked = barriers.sort_values(["risk_rank", "barrier_score"]).reset_index(drop=True)
weakest_path = pathways.sort_values("robustness").iloc[0]

active = barriers[barriers["is_active"]]
critical_active = active[active["critical"] == "Yes"]
chain_bad = active[active["chain_missing"]]
chain_bad_pct = pct(len(chain_bad), len(active))
critical_chain_bad = critical_active[critical_active["chain_missing"]]
critical_chain_pct = pct(len(critical_chain_bad), len(critical_active))
elements_all = int(active["elements"].sum())
human_all = int(active["human_elements"].sum())
human_element_pct = pct(human_all, elements_all)
crit_elements = int(critical_active["elements"].sum())
crit_human_elements = int(critical_active["human_elements"].sum())
crit_human_element_pct = pct(crit_human_elements, crit_elements)
human_active = active[active["human_elements"] > 0]

tested_ok = barriers[barriers["has_record"]]
passed_tests = tested_ok[(tested_ok["verified"]) & (~tested_ok["failed_check"])]
proven_pct = pct(len(passed_tests), len(tested_ok[tested_ok["verified"]]))
critical_tested = tested_ok[(tested_ok["critical"] == "Yes") & (tested_ok["verified"])]
critical_proven_pct = pct(len(critical_tested[~critical_tested["failed_check"]]), len(critical_tested))
failed_test_barriers = barriers[barriers["failed_check"]]

shared_rows = []
for pid in barriers["pathway_id"].unique():
    mine = barriers[barriers["pathway_id"] == pid]
    deps = mine["common_dependency"].dropna()
    if len(deps) >= 2 and deps.value_counts().max() >= 2:
        shared_rows.append({"pathway_id": pid, "dependency": deps.value_counts().idxmax(), "barriers_sharing": int(deps.value_counts().max()), "has_critical": (mine["critical"] == "Yes").any()})
shared_df = pd.DataFrame(shared_rows, columns=["pathway_id", "dependency", "barriers_sharing", "has_critical"])
shared_paths = pathways.merge(shared_df, on="pathway_id", how="inner")
shared_critical_paths = shared_paths[shared_paths["has_critical"]]
shared_barriers = barriers[barriers["common_dependency"].notna()]
shared_pct = pct(len(shared_barriers), total)

audit_fail = barriers[barriers["fails_audit_trait"]]
audit_fail_pct = pct(len(audit_fail), total)

recorded = barriers[barriers["has_record"]]
verified_b = barriers[barriers["verified"]]
unverified_b = barriers[~barriers["verified"]]
verified_pct = pct(len(verified_b), total)
critical_verified = critical[critical["verified"]]
critical_verified_pct = pct(len(critical_verified), len(critical))
critical_unverified = critical[~critical["verified"]]
short_b = barriers[barriers["short_tested"]]
short_pct = pct(len(short_b), len(recorded))
ass_full = assurance.merge(barriers[["barrier_id", "barrier_name", "critical", "owner"]], on="barrier_id", how="left")
done_ass = ass_full[ass_full["status"] == "Completed"]
failed_ass = ass_full[ass_full["result"] == "Fail"]
fail_rate = pct(len(failed_ass), len(done_ass))
crit_bad_ass = ass_full[(ass_full["critical"] == "Yes") & ((ass_full["status"] == "Overdue") | (ass_full["result"] == "Fail"))]
crit_bad_ass_barriers = crit_bad_ass["barrier_id"].nunique()
crit_overdue_ass = ass_full[(ass_full["critical"] == "Yes") & (ass_full["status"] == "Overdue")]
crit_failed_ass = ass_full[(ass_full["critical"] == "Yes") & (ass_full["result"] == "Fail")]


def assurance_owner_stats(bdf):
    owner_rows = []
    for owner in bdf["owner"].unique():
        mine = bdf[bdf["owner"] == owner]
        owner_rows.append({
            "owner": owner,
            "barriers": len(mine),
            "overdue_pct": round(pct(int(mine["overdue_check"].sum()), len(mine)), 1),
            "verified_pct": round(pct(int(mine["verified"].sum()), len(mine)), 1),
            "no_standard_pct": round(pct(int((~mine["has_standard"]).sum()), len(mine)), 1),
        })
    return pd.DataFrame(owner_rows, columns=["owner", "barriers", "overdue_pct", "verified_pct", "no_standard_pct"])


owner_ass = assurance_owner_stats(barriers)
owners_ass_overdue = owner_ass[owner_ass["overdue_pct"] > 20]
owners_no_std = owner_ass[owner_ass["no_standard_pct"] > 30]

documented_pct = pct(len(recorded), total)
critical_covered = critical[critical["has_standard"]]
critical_covered_pct = pct(len(critical_covered), len(critical))
audit_index = (documented_pct / 100) * (verified_pct / 100) * (critical_covered_pct / 100)
reliability_index = (effective - (total - effective)) / total
crit_open_actions = critical_actions[critical_actions["status"].isin(["Pending", "Overdue"])]
actions_closed_pct = pct(len(critical_actions[critical_actions["status"] == "Completed"]), len(critical_actions))
critical_kpi_bad = critical[(critical["failed_check"]) | (critical["overdue_check"]) | (critical["barrier_id"].isin(critical_actions[critical_actions["status"] == "Overdue"]["barrier_id"]))]
overdue_ass_all = ass_full[ass_full["status"] == "Overdue"]

std_full = standards.merge(barriers[["barrier_id", "barrier_name", "critical", "owner"]], on="barrier_id", how="left")
std_rate = pct(int(barriers["has_standard"].sum()), total)
no_std = barriers[~barriers["has_standard"]]
critical_no_std = critical[~critical["has_standard"]]
critical_std_pct = critical_covered_pct
std_pending = std_full[std_full["verification_status"] != "Verified"]
std_unverified_pct = pct(len(std_pending), len(std_full))
crit_std_unverified = critical[critical["std_unverified"]]
crit_with_std = critical[critical["has_standard"]]
crit_std_unverified_pct = pct(len(crit_std_unverified), len(crit_with_std))
multi_b = barriers[barriers["multi_std"]]
conflict_b = barriers[barriers["std_conflict"]]
multi_pct = pct(len(multi_b), total)


raw_actions = raw["corrective_actions"].copy()
raw_actions["due_parsed"] = pd.to_datetime(raw_actions["due_date"], errors="coerce")
add_check("Dates", "all due dates can be read as dates", bool(raw_actions["due_parsed"].notna().all()), str(int(raw_actions["due_parsed"].isna().sum())) + " unreadable")
overdue_wrong = raw_actions[(raw_actions["status"] == "Overdue") & (raw_actions["due_parsed"] >= as_of)]
add_check("Dates", "Overdue actions are past their due date", len(overdue_wrong) == 0, str(len(overdue_wrong)) + " wrong")
pending_wrong = raw_actions[(raw_actions["status"] == "Pending") & (raw_actions["due_parsed"] < as_of)]
add_check("Dates", "Pending actions are not past their due date", len(pending_wrong) == 0, str(len(pending_wrong)) + " wrong")
add_check("Scoring", "barrier scores are between 0 and 100", bool(barriers["barrier_score"].between(0, 100).all()), "min " + str(barriers["barrier_score"].min()) + ", max " + str(barriers["barrier_score"].max()))
add_check("Counts match", "condition counts add up to total barriers", effective + partial + not_working == total, str(effective) + " + " + str(partial) + " + " + str(not_working) + " = " + str(total))
add_check("Counts match", "critical working + not working = critical barriers", len(critical[critical["condition"] == "Effective"]) + len(critical_bad) == len(critical), str(len(critical)) + " critical")
add_check("Counts match", "barriers across paths = total barriers", int(pathways["n_barriers"].sum()) == total, str(int(pathways["n_barriers"].sum())) + " vs " + str(total))
add_check("Counts match", "action status counts add up to total actions", len(actions[actions["status"] == "Completed"]) + len(actions[actions["status"] == "Pending"]) + len(actions[actions["status"] == "Overdue"]) == len(actions), str(len(actions)) + " actions")
add_check("Counts match", "critical-action counts used in tiles match the data", len(overdue_critical) <= len(critical_actions) and len(critical_actions) == len(actions[actions["barrier_id"].isin(critical["barrier_id"])]), str(len(critical_actions)) + " critical actions")
add_check("Counts match", "owner table adds up to total barriers", int(owner_df["barriers"].sum()) == total, str(int(owner_df["barriers"].sum())) + " vs " + str(total))
add_check("Counts match", "factor and control counts used in tiles match the data", len(fac) == len(factors) and int(controls["factor_id"].isin(fac["factor_id"]).sum()) == len(controls), str(len(fac)) + " factors, " + str(len(controls)) + " controls")
raw_ass = raw["assurance_activities"].copy()
raw_ass["due_parsed"] = pd.to_datetime(raw_ass["due_date"], errors="coerce")
raw_ass["completed_parsed"] = pd.to_datetime(raw_ass["completed_date"], errors="coerce")
add_check("Dates", "all assurance due dates can be read as dates", bool(raw_ass["due_parsed"].notna().all()), str(int(raw_ass["due_parsed"].isna().sum())) + " unreadable")
ass_overdue_wrong = raw_ass[(raw_ass["status"] == "Overdue") & (raw_ass["due_parsed"] >= as_of)]
add_check("Dates", "Overdue assurance activities are past their due date", len(ass_overdue_wrong) == 0, str(len(ass_overdue_wrong)) + " wrong")
ass_pending_wrong = raw_ass[(raw_ass["status"] == "Pending") & (raw_ass["due_parsed"] < as_of)]
add_check("Dates", "Pending assurance activities are not past their due date", len(ass_pending_wrong) == 0, str(len(ass_pending_wrong)) + " wrong")
done_no_result = raw_ass[(raw_ass["status"] == "Completed") & (raw_ass["result"].isna() | raw_ass["completed_parsed"].isna())]
add_check("Assurance", "completed activities have a result and a completion date", len(done_no_result) == 0, str(len(done_no_result)) + " incomplete")
open_with_result = raw_ass[(raw_ass["status"] != "Completed") & raw_ass["result"].notna()]
add_check("Assurance", "open activities do not have a result yet", len(open_with_result) == 0, str(len(open_with_result)) + " wrong")
add_check("Counts match", "assurance status counts add up to total activities", len(assurance[assurance["status"] == "Completed"]) + len(assurance[assurance["status"] == "Pending"]) + len(assurance[assurance["status"] == "Overdue"]) == len(assurance), str(len(assurance)) + " activities")
add_check("Counts match", "verified + not verified = total barriers", len(verified_b) + len(unverified_b) == total, str(len(verified_b)) + " + " + str(len(unverified_b)) + " = " + str(total))
add_check("Counts match", "barriers with and without a standard add up to total", int(barriers["has_standard"].sum()) + len(no_std) == total, str(len(no_std)) + " without")
add_check("Counts match", "critical with and without a standard add up to critical barriers", len(critical_covered) + len(critical_no_std) == len(critical), str(len(critical)) + " critical")
add_check("Counts match", "active barriers are never more than total barriers", len(active) <= total, str(len(active)) + " of " + str(total))
check_table = pd.DataFrame(checks)
failed = check_table[check_table["result"] == "FAIL"]

vb = barriers
if critical_only:
    vb = vb[vb["critical"] == "Yes"]
if f_owner:
    vb = vb[vb["owner"].isin(f_owner)]
if f_condition:
    vb = vb[vb["condition"].isin(f_condition)]
if f_function:
    vb = vb[vb["function"].isin(f_function)]
if f_type:
    vb = vb[vb["barrier_type"].isin(f_type)]
vb = vb.reset_index(drop=True)
vb_actions = full_actions[full_actions["barrier_id"].isin(vb["barrier_id"])]
va = actions[actions["barrier_id"].isin(vb["barrier_id"])]
v_overdue = overdue_all[overdue_all["barrier_id"].isin(vb["barrier_id"])]
vfac = fac[fac["barrier_id"].isin(vb["barrier_id"])]
vc = controls[controls["factor_id"].isin(vfac["factor_id"])]
owner_view = owner_stats(vb, vb_actions)
vass = ass_full[ass_full["barrier_id"].isin(vb["barrier_id"])]
vstd = std_full[std_full["barrier_id"].isin(vb["barrier_id"])]
owner_ass_view = assurance_owner_stats(vb)
v_active = vb[vb["is_active"]]
unf = ""
if scope_on:
    unf = " (all paths)"

not_applicable = {
    "5.9": len(critical) == 0, "7.2": len(critical) == 0, "5.3": len(critical) == 0, "5.10": len(critical) == 0,
    "9.2": len(critical_actions) == 0, "9.4": len(critical) == 0, "9.7": len(critical_actions) == 0,
    "7.7": len(threat_paths) == 0, "12.4": len(controls) == 0, "12.1": len(fac) == 0, "12.2": len(fac) == 0, "12.7": len(fac) == 0,
    "12.5": len(critical) == 0 or len(fac) == 0, "3.6": len(critical) == 0, "6.3": len(critical) == 0, "9.5": len(actions) == 0,
    "4.1": len(tested_ok[tested_ok["verified"]]) == 0, "4.11": len(active) == 0, "4.13": len(critical_active) == 0 or crit_elements == 0,
    "8.2": len(recorded) == 0, "8.3": len(done_ass) == 0, "8.4": len(critical) == 0,
    "10.1": len(critical) == 0, "10.3": len(critical) == 0, "10.4": len(critical) == 0, "10.5": len(critical) == 0,
    "11.1": len(critical) == 0, "11.2": len(critical) == 0, "11.3": len(crit_with_std) == 0, "11.4": len(standards) == 0,
}

if weakest_path["n_barriers"] == 0:
    weakest_reason = "it has no barriers at all"
else:
    weakest_reason = "its barrier strength score is only " + str(round(weakest_path["robustness"])) + " out of 100"


def spec(irc, label, message, status, rule, risk, action, items=None, cols=None):
    if not_applicable.get(irc, False):
        status = "NA"
        message = "Nothing to measure here: no matching records for this bowtie."
        items = None
    return {"irc": irc, "label": label, "message": message, "status": status, "rule": rule, "risk": risk, "action": action, "items": items, "cols": cols}


def count_by(df, col, name):
    return df.groupby(col).size().reset_index(name=name)


def of(n, m, word="", plural=None):
    if word == "":
        return str(n) + " of " + str(m)
    if plural is None:
        plural = word + "s"
    if m == 1:
        return str(n) + " of " + str(m) + " " + word
    return str(n) + " of " + str(m) + " " + plural


def many(n, word, one_verb, many_verb, plural=None):
    if plural is None:
        plural = word + "s"
    if n == 1:
        return "1 " + word + " " + one_verb
    return str(n) + " " + plural + " " + many_verb


def isare(n):
    if n == 1:
        return "is"
    return "are"


def hashave(n):
    if n == 1:
        return "has"
    return "have"


def big_value(message):
    found = re.search(r"\d+ of \d+|-?\d+\.\d+|\d+%|\d+", message)
    if found is None:
        return ""
    return found.group(0)


def tile(s):
    color = status_colors[s["status"]]
    if s["status"] == "NA":
        big = "\u2013"
    else:
        big = big_value(s["message"])
    html = "<div class='kpi' style='border-top-color:" + color + ";'>"
    html = html + "<div class='top'><span class='tag' title='Insight Risk Card " + s["irc"] + " from the Analytics Framework'>IRC " + s["irc"] + "</span><span class='chip' style='background:" + color + ";'>" + status_icons[s["status"]] + " " + status_words[s["status"]] + "</span></div>"
    html = html + "<div class='lab'>" + s["label"] + "</div>"
    html = html + "<div class='big'>" + big + "</div>"
    html = html + "<div class='msg'>" + s["message"] + "</div>"
    html = html + "<div class='rule'>" + s["rule"] + "</div></div>"
    st.markdown(html, unsafe_allow_html=True)
    with st.popover("Why it matters and what to do", use_container_width=True):
        st.markdown("**Why it matters**  \n" + s["risk"])
        st.markdown("**What to do**  \n" + s["action"])
        if s["items"] is not None and len(s["items"]) > 0:
            st.markdown("**Affected items**")
            shown = s["items"][s["cols"]].rename(columns=lambda c: c.replace("_", " ").capitalize())
            st.dataframe(shown, use_container_width=True, hide_index=True)
        else:
            st.markdown("Nothing to fix here right now.")


def show(c, title, height):
    c = c.properties(height=height, title=title, background="rgba(0,0,0,0)")
    c = c.configure_title(anchor="start", fontSize=14, color="#14324a")
    c = c.configure_axis(labelColor="#3d4a5c", titleColor="#3d4a5c", grid=False)
    c = c.configure_legend(labelColor="#3d4a5c", titleColor="#3d4a5c")
    c = c.configure_view(stroke=None)
    st.altair_chart(c, use_container_width=True, theme=None)


def donut(df, label, value, title, colors=None):
    if len(df) == 0:
        st.caption(title + ": nothing to show.")
        return
    if colors is None:
        scale = alt.Scale(scheme="blues")
    else:
        scale = alt.Scale(domain=list(colors.keys()), range=list(colors.values()))
    pick = alt.selection_point(fields=[label], bind="legend")
    c = alt.Chart(df).mark_arc(innerRadius=50).encode(
        theta=alt.Theta(value + ":Q"),
        color=alt.Color(label + ":N", scale=scale, legend=alt.Legend(orient="right", title=None)),
        opacity=alt.condition(pick, alt.value(1), alt.value(0.25)),
        tooltip=[label, value],
    ).add_params(pick)
    show(c, title, 210)


def bars(df, cat, val, title, color=None, colors=None, horizontal=False):
    if len(df) == 0:
        st.caption(title + ": nothing to show.")
        return
    if color is None:
        enc_color = alt.value(base_blue)
    elif colors is None:
        enc_color = alt.Color(color + ":N", scale=alt.Scale(scheme="blues"), legend=alt.Legend(orient="bottom", title=None))
    else:
        enc_color = alt.Color(color + ":N", scale=alt.Scale(domain=list(colors.keys()), range=list(colors.values())), legend=alt.Legend(orient="bottom", title=None))
    if color is None:
        pick = alt.selection_point(on="mouseover", fields=[cat], clear="mouseout")
    else:
        pick = alt.selection_point(fields=[color], bind="legend")
    fade = alt.condition(pick, alt.value(1), alt.value(0.3))
    if horizontal:
        c = alt.Chart(df).mark_bar().encode(y=alt.Y(cat + ":N", title=None, sort=None), x=alt.X(val + ":Q", title=None), color=enc_color, opacity=fade, tooltip=list(df.columns))
    else:
        c = alt.Chart(df).mark_bar().encode(x=alt.X(cat + ":N", title=None, sort=None, axis=alt.Axis(labelAngle=0)), y=alt.Y(val + ":Q", title=None), color=enc_color, opacity=fade, tooltip=list(df.columns))
    c = c.add_params(pick)
    show(c, title, 210)


def card(fn):
    with st.container(border=True):
        fn()


def risk_table(n, query):
    rows = ""
    source = ranked[ranked["barrier_id"].isin(vb["barrier_id"])]
    if query:
        source = source[source["barrier_name"].str.contains(query, case=False, regex=False)]
    top = source.head(n)
    if len(top) == 0:
        st.info("No barriers match the selected filters.")
        return
    for i in range(len(top)):
        r = top.iloc[i]
        pill = "<span class='pill' style='background:" + risk_colors[r["risk"]] + ";'>" + r["risk"] + "</span>"
        rows = rows + "<tr><td>" + str(i + 1) + "</td><td>" + str(r["barrier_name"]) + "</td><td>" + pill + "</td><td>" + str(r["condition"]) + "</td><td>" + str(r["owner"]) + "</td><td>" + str(r["function"]) + "</td><td>" + str(r["barrier_type"]) + "</td></tr>"
    head = "<tr><th>#</th><th>Barrier</th><th>Risk</th><th>Condition</th><th>Owner</th><th>Function</th><th>Type</th></tr>"
    st.markdown("<table class='rt'>" + head + rows + "</table>", unsafe_allow_html=True)
    st.caption("Showing " + str(len(top)) + " of " + str(len(source)) + " barriers, highest risk first.")


def barrier_details():
    with st.expander("Look into one barrier"):
        if len(vb) == 0:
            st.caption("No barriers match the selected filters.")
            return
        pick = st.selectbox("Barrier", list(ranked[ranked["barrier_id"].isin(vb["barrier_id"])]["barrier_name"]))
        mine = barriers[barriers["barrier_name"] == pick]
        if len(mine) == 0:
            return
        bid = mine.iloc[0]["barrier_id"]
        r = mine.iloc[0]
        st.markdown("**" + str(r["barrier_name"]) + "**: " + str(r["condition"]) + ", " + str(r["function"]) + ", " + str(r["barrier_type"]) + ", owner " + str(r["owner"]) + ".")
        st.markdown("**Corrective actions**")
        st.dataframe(actions[actions["barrier_id"] == bid][["action_description", "priority", "status", "due_date"]], use_container_width=True, hide_index=True)
        st.markdown("**Assurance activities**")
        st.dataframe(assurance[assurance["barrier_id"] == bid][["activity_type", "status", "result", "due_date"]], use_container_width=True, hide_index=True)
        st.markdown("**Codes and standards**")
        st.dataframe(standards[standards["barrier_id"] == bid][["standard_code", "verification_status", "conflict_flag"]], use_container_width=True, hide_index=True)
        st.markdown("**Degradation factors**")
        st.dataframe(fac[fac["barrier_id"] == bid][["factor_name", "category", "working_controls"]], use_container_width=True, hide_index=True)


def page(text, kpis, charts):
    topbar = "<div class='topbar'><div><b>" + bowtie + "</b> " + hazard + " | Top event: " + top_event + " | As of " + data["as_of_date"] + "</div><div>"
    topbar = topbar + "<span class='tbk'>Critical not effective <b>" + str(len(critical_bad)) + "</b></span>"
    topbar = topbar + "<span class='tbk'>Overdue critical fixes <b>" + str(len(overdue_critical)) + "</b></span>"
    topbar = topbar + "<span class='tbk'>Overdue checks <b>" + str(len(overdue_ass_all)) + "</b></span></div></div>"
    st.markdown(topbar, unsafe_allow_html=True)
    if len(failed) > 0:
        st.warning("Data quality checks found " + str(len(failed)) + " issue(s), so some numbers may be off. Open the validation panel at the bottom for details.")
    hero = "<div class='hero'><div class='title'>" + hazard + "</div>"
    hero = hero + "<div class='sub'>" + view + " dashboard</div>"
    hero = hero + "<div class='text'>" + text + "</div></div>"
    st.markdown(hero, unsafe_allow_html=True)
    st.markdown("<div class='jump'>Jump to: <a href='#insights'>Insights</a> | <a href='#charts'>Charts</a> | <a href='#table'>Table</a> | <a href='#validation'>Validation</a></div>", unsafe_allow_html=True)
    if show_insights:
        st.markdown("<div class='section' id='insights'>Key insights</div>", unsafe_allow_html=True)
        cols = st.columns(len(kpis))
        for i in range(len(kpis)):
            with cols[i]:
                tile(kpis[i])
    if show_charts:
        st.markdown("<div class='section' id='charts'>Charts" + (" (filtered)" if scope_on else "") + "</div>", unsafe_allow_html=True)
        cols = st.columns(len(charts))
        for i in range(len(charts)):
            with cols[i]:
                card(charts[i])
    if show_table:
        st.markdown("<div class='section' id='table'>Barriers ranked by risk" + (" (filtered)" if scope_on else "") + "</div>", unsafe_allow_html=True)
        with st.container(border=True):
            if scope_on:
                st.markdown("".join(["<span class='pillf'>" + f + "</span>" for f in active_filters]), unsafe_allow_html=True)
                st.button("Clear all filters", on_click=reset_filters, key="clear_top")
            query = st.text_input("Search barrier name", key="search")
            risk_table(8, query)
            barrier_details()
    st.markdown("<div id='validation'></div>", unsafe_allow_html=True)
    with st.expander("Validation: consistency checks (BR-03), " + str(len(check_table) - len(failed)) + " of " + str(len(check_table)) + " passed"):
        st.caption("Checked against the mock schema. Replace the required columns and allowed values with the Canonical Schema when the converter team sends it. A path with no barriers is scored 0.")
        st.dataframe(check_table, use_container_width=True, hide_index=True)
    st.caption("Data as of " + data["as_of_date"] + ". Click Why it matters and what to do on any insight to see the affected items.")


def build_overview():
    text = "This bowtie has <b>" + str(total) + " barriers</b> defending against <b>" + hazard + "</b>. <b>" + str(len(critical)) + "</b> of them are critical, and <b>" + str(len(critical_bad)) + "</b> of those are not fully working. The weakest link is <b>" + str(weakest_path["name"]) + "</b>, because " + weakest_reason + "."
    kpis = [
        spec("13", "Path strength score (prototype)",
             "Paths average " + str(round(avg_robust)) + " out of 100 (" + band(avg_robust) + "). This is a comparative indicator, not a failure probability.",
             get_status(avg_robust, "below", 70), "Healthy is 70 or more",
             "Low scores point to paths whose barriers are weaker than others. Use it to compare paths, not to predict failure.", "Strengthen the weakest paths first.",
             pathways[pathways["robustness"] < 70].sort_values("robustness"), ["name", "side", "robustness", "n_barriers"]),
        spec("7.1", "Are barriers working?",
             of(effective, total, "barrier") + " work as designed (" + str(round(eff_pct)) + "%).",
             get_status(eff_pct, "below", 70), "Healthy is 70% or more",
             "Barriers that do not work reduce the reliability of the whole system.", "Restore or replace degraded barriers and find out the status of unknown ones.",
             degraded, ["barrier_name", "condition", "owner"]),
        spec("5.9", "Are critical barriers working?",
             of(len(critical_bad), len(critical), "critical barrier") + " " + isare(len(critical)) + " not fully working.",
             get_status(len(critical_bad), "above", 0), "Healthy is none",
             "The paths they protect are exposed to unmanaged risk.", "Escalate now and restore or replace these barriers.",
             critical_bad, ["barrier_name", "condition", "owner"]),
        spec("9.2", "Are critical fixes on time?",
             of(len(overdue_critical), len(critical_actions), "fix", "fixes") + " on critical barriers " + isare(len(critical_actions)) + " overdue (" + str(round(overdue_pct)) + "%).",
             get_status(overdue_pct, "above", 10), "Healthy is 10% or less",
             "Barriers stay degraded for longer.", "Finish overdue actions first and escalate to management.",
             overdue_critical, ["action_description", "barrier_name", "due_date"]),
        spec("12.5", "Are critical barriers protected from wear?",
             many(exposed_count, "critical barrier", "faces a degradation factor with no working control.", "face a degradation factor with no working control."),
             get_status(exposed_count, "above", 0), "Healthy is none",
             "These barriers can fail without warning.", "Add or repair controls on these barriers.",
             exposed, ["barrier_name", "factor_name", "factor_category"]),
    ]

    def c1():
        donut(count_by(vb, "condition", "barriers"), "condition", "barriers", "Are the barriers working?", condition_colors)

    def c2():
        weak = pathways.sort_values("robustness").head(6).copy()
        weak["path"] = weak["name"].astype(str).str.slice(0, 32)
        bars(weak[["path", "robustness", "band"]], "path", "robustness", "The six weakest paths (barrier strength score out of 100)" + unf, "band", band_colors, True)

    def c3():
        bars(count_by(vb, ["function", "condition"], "barriers"), "function", "barriers", "Does each kind of protection work?", "condition", condition_colors)

    return text, kpis, [c1, c2, c3]


def build_condition():
    text = "Of <b>" + str(total) + " barriers</b>, <b>" + str(effective) + "</b> work as designed, <b>" + str(partial) + "</b> work only partly and <b>" + str(not_working) + "</b> are not working or have an unknown status. The weakest kind of protection is <b>" + weakest_function + "</b>."
    kpis = [
        spec("7.1", "Are barriers working?",
             of(effective, total, "barrier") + " work as designed (" + str(round(eff_pct)) + "%).",
             get_status(eff_pct, "below", 70), "Healthy is 70% or more",
             "Barriers that do not work reduce the reliability of the whole system.", "Restore or replace degraded barriers and find out the status of unknown ones.",
             degraded, ["barrier_name", "condition", "owner"]),
        spec("7.2", "Are critical barriers working?",
             of(len(critical_bad), len(critical), "critical barrier") + " " + isare(len(critical)) + " not fully working.",
             get_status(len(critical_bad), "above", 0), "Healthy is none",
             "The paths they protect are exposed to unmanaged risk.", "Escalate now, assign corrective actions to restore or redesign them.",
             critical_bad, ["barrier_name", "condition", "owner"]),
        spec("7.3", "Do owners keep barriers healthy?",
             of(len(owners_ineffective), len(owner_df), "owner") + " " + hashave(len(owner_df)) + " more than one in five barriers not working.",
             get_status(len(owners_ineffective), "above", 0), "Healthy is none",
             "Accountability gap, barriers may fail unnoticed.", "Ask these owners to verify and document barrier condition.",
             owners_ineffective, ["owner", "barriers", "ineffective_pct"]),
        spec("7.5", "Which kind of protection is weakest?",
             weakest_function + " barriers are the weakest. Only " + str(round(by_function.min())) + "% of them work.",
             get_status(by_function.min(), "below", 50), "Healthy is 50% or more for every kind",
             "Weak coverage leaves hazards uncontrolled.", "Strengthen that function and rebalance away from reaction-only barriers.",
             by_function.reset_index().rename(columns={"condition": "percent_working"}).round(0), ["function", "percent_working"]),
        spec("7.7", "Is every threat covered?",
             of(len(threats_no_eff), len(threat_paths), "threat") + " " + hashave(len(threat_paths)) + " no working barrier at all.",
             get_status(threats_no_eff_pct, "above", 5), "Healthy is 5% or less",
             "These threats stay unmanaged and raise the chance of the top event.", "Add barriers or redesign these paths.",
             threats_no_eff, ["name", "n_barriers"]),
    ]

    def c1():
        donut(count_by(vb, "condition", "barriers"), "condition", "barriers", "Are the barriers working?", condition_colors)

    def c2():
        bars(count_by(vb, ["function", "condition"], "barriers"), "function", "barriers", "Condition by kind of protection", "condition", condition_colors)

    def c3():
        bars(owner_view[["owner", "ineffective_pct"]], "owner", "ineffective_pct", "Percent of each owner's barriers not working", None, None, True)

    return text, kpis, [c1, c2, c3]


def build_criticality():
    text = "<b>" + str(len(critical)) + "</b> barriers are critical. <b>" + str(len(critical_bad)) + "</b> of them are not fully working and <b>" + str(len(unassigned_critical)) + "</b> have no owner. <b>" + of(len(no_critical), len(pathways), "threat or consequence path") + "</b> " + hashave(len(pathways)) + " no critical barrier."
    kpis = [
        spec("5.3", "Does every critical barrier have an owner?",
             "No critical barrier is missing an owner." if len(unassigned_critical) == 0 else many(len(unassigned_critical), "critical barrier", "has no owner.", "have no owner."),
             get_status(len(unassigned_critical), "above", 0), "Healthy is none",
             "Nobody is accountable for these barriers.", "Assign an owner immediately.",
             unassigned_critical, ["barrier_name", "condition"]),
        spec("5.9", "Are critical barriers working?",
             of(len(critical_bad), len(critical), "critical barrier") + " " + isare(len(critical)) + " not fully working.",
             get_status(len(critical_bad), "above", 0), "Healthy is none",
             "The paths they protect are exposed to degradation.", "Escalate now and restore or replace these barriers.",
             critical_bad, ["barrier_name", "condition", "owner"]),
        spec("5.10", "Are critical barriers being fixed?",
             many(overdue_barriers, "critical barrier", "has a fix that is overdue.", "have a fix that is overdue."),
             get_status(overdue_barriers, "above", 0), "Healthy is none",
             "Degradation stays unmanaged and exposure grows.", "Escalate to leadership and enforce closure dates.",
             overdue_critical, ["action_description", "barrier_name", "due_date"]),
        spec("5.14", "Which paths have no critical barrier?",
             of(len(no_critical), len(pathways), "threat or consequence path") + " " + hashave(len(pathways)) + " no critical barrier.",
             "INFO", "Gap analysis, no alert level",
             "These paths are exposed without critical protection.", "Redesign these paths or assign a critical barrier.",
             no_critical, ["name", "side", "n_barriers"]),
        spec("5.15", "Where is there only one critical barrier?",
             many(len(one_critical), "path", "relies on a single critical barrier.", "rely on a single critical barrier."),
             "INFO", "Single point of failure, no alert level",
             "If that one barrier fails there is no critical backup.", "Add a second barrier or redesign the path.",
             one_critical, ["name", "side", "n_barriers"]),
    ]

    def c1():
        donut(count_by(critical, "condition", "barriers"), "condition", "barriers", "Are the critical barriers working?", condition_colors)

    def c2():
        counts = pathways.assign(label=pathways["n_critical"].clip(upper=2).map({0: "No critical barrier", 1: "One critical barrier", 2: "Two or more"}))
        bars(count_by(counts, "label", "paths"), "label", "paths", "How many critical barriers does each path have?" + unf)

    def c3():
        bars(count_by(critical, "owner", "critical barriers"), "owner", "critical barriers", "Who owns the critical barriers?", None, None, True)

    return text, kpis, [c1, c2, c3]


def build_actions():
    text = "There are <b>" + str(len(actions)) + " corrective actions</b>. <b>" + str(len(overdue_all)) + "</b> are overdue and <b>" + str(len(no_action)) + "</b> barriers that are not working have no open action planned."
    kpis = [
        spec("9.1", "Does every broken barrier have a fix planned?",
             of(len(no_action), len(degraded), "barrier") + " that " + isare(len(degraded)) + " not working " + hashave(len(degraded)) + " no open corrective action.",
             get_status(len(no_action), "above", 0), "Healthy is none",
             "These barriers stay degraded and may fail.", "Assign an action to each one and escalate the gaps.",
             no_action, ["barrier_name", "condition", "owner"]),
        spec("9.2", "Are critical fixes on time?",
             of(len(overdue_critical), len(critical_actions), "fix", "fixes") + " on critical barriers " + isare(len(critical_actions)) + " overdue (" + str(round(overdue_pct)) + "%).",
             get_status(overdue_pct, "above", 10), "Healthy is 10% or less",
             "Barriers stay degraded for longer.", "Finish overdue actions first and escalate to management.",
             overdue_critical, ["action_description", "barrier_name", "due_date"]),
        spec("9.4", "Which critical barriers are waiting on a fix?",
             many(overdue_barriers, "critical barrier", "has an overdue action.", "have an overdue action."),
             get_status(overdue_barriers, "above", 0), "Healthy is none",
             "Critical barriers stay exposed to degradation.", "Escalate to leadership and move resources to these actions.",
             overdue_critical, ["barrier_name", "action_description", "due_date"]),
        spec("9.5", "Do owners finish their fixes?",
             of(len(owners_overdue), len(owner_df), "owner") + " " + hashave(len(owner_df)) + " more than one in five of their actions overdue.",
             get_status(len(owners_overdue), "above", 0), "Healthy is none",
             "A slow owner is a weak spot across many barriers.", "Check in with these owners, reassign work or add support.",
             owners_overdue, ["owner", "overdue_pct"]),
        spec("9.7", "Are critical fixes given high priority?",
             of(len(low_critical), len(critical_actions), "fix", "fixes") + " on critical barriers " + isare(len(critical_actions)) + " marked Low priority.",
             "INFO", "Priority check, no alert level",
             "Critical risks may be left waiting.", "Re-check priorities and raise the urgent ones.",
             low_critical, ["action_description", "barrier_name", "priority"]),
    ]

    def c1():
        donut(count_by(va, "status", "actions"), "status", "actions", "What state are the actions in?", action_colors)

    def c2():
        bars(count_by(va, ["priority", "status"], "actions"), "priority", "actions", "Actions by priority and state", "status", action_colors)

    def c3():
        bars(count_by(v_overdue, "owner", "overdue actions"), "owner", "overdue actions", "Whose actions are overdue?", None, None, True)

    return text, kpis, [c1, c2, c3]


def build_type_function():
    text = "The biggest group of barriers is <b>" + top_type + "</b>. <b>" + str(round(human_pct)) + "%</b> of all barriers depend on people. <b>" + of(len(few_functions), len(pathways), "path") + "</b> " + ("uses" if len(pathways) == 1 else "use") + " fewer than two kinds of protection."
    kpis = [
        spec("3.1", "Is the mix of barrier types healthy?",
             top_type + " barriers make up " + str(round(top_type_pct)) + "% of all barriers.",
             get_status(top_type_pct, "above", 40), "Healthy is 40% or less in one type",
             "Relying on one type increases variability and error.", "Shift toward passive or active hardware barriers.",
             type_counts.reset_index(name="barriers"), ["barrier_type", "barriers"]),
        spec("3.3", "Does every path use two kinds of protection?",
             of(len(few_functions), len(pathways), "path") + " " + ("uses" if len(pathways) == 1 else "use") + " fewer than two kinds of protection.",
             get_status(len(few_functions), "above", 0), "Healthy is none",
             "Gaps in protection leave hazards uncontrolled until after escalation.", "Add preventive or detection barriers to these paths.",
             few_functions, ["name", "side", "n_barriers"]),
        spec("3.4", "Is one kind of protection doing all the work?",
             top_function + " makes up " + str(round(top_function_pct)) + "% of all barriers.",
             get_status(top_function_pct, "above", 50), "Healthy is 50% or less in one function",
             "One function type makes failure more likely.", "Introduce independent kinds of protection.",
             function_counts.reset_index(name="barriers"), ["function", "barriers"]),
        spec("3.5", "Do we depend too much on people?",
             str(round(human_pct)) + "% of barriers rely on people.",
             get_status(human_pct, "above", 50), "Healthy is 50% or less",
             "High dependency on people reduces reliability.", "Automate where possible and strengthen training and monitoring.",
             barriers[barriers["barrier_type"].isin(human_types)], ["barrier_name", "barrier_type", "owner"]),
        spec("3.6", "Are critical barriers well mixed?",
             str(round(crit_type_pct)) + "% of critical barriers are " + crit_type + ".",
             get_status(crit_type_pct, "above", 50), "Healthy is 50% or less in one type",
             "Too many critical barriers of one type is a fragile design.", "Add engineering or administrative barriers of other types.",
             critical_type_counts.reset_index(name="critical_barriers"), ["barrier_type", "critical_barriers"]),
    ]

    def c1():
        donut(count_by(vb, "barrier_type", "barriers"), "barrier_type", "barriers", "What kinds of barriers are there?")

    def c2():
        bars(count_by(vb, "function", "barriers"), "function", "barriers", "What do the barriers do?")

    def c3():
        bars(owner_view[["owner", "human_pct"]], "owner", "human_pct", "Percent of each owner's barriers that rely on people", None, None, True)

    return text, kpis, [c1, c2, c3]


def build_degradation():
    text = "<b>" + str(len(fac)) + " factors</b> can wear down these barriers, held back by <b>" + str(len(controls)) + " controls</b>. <b>" + str(len(weak_controls)) + "</b> controls are not working or unknown, and <b>" + str(exposed_count) + "</b> critical barriers are exposed."
    kpis = [
        spec("12.1", "Are wear-and-tear factors classified?",
             str(round(classified_pct)) + "% of factors have a category.",
             get_status(classified_pct, "below", 95), "Healthy is 95% or more",
             "Unidentified factors leave hidden weaknesses.", "Document and classify every factor.",
             fac[fac["factor_category"].isna()], ["factor_name", "barrier_name"]),
        spec("12.2", "Does every factor have a control?",
             str(round(control_pct)) + "% of factors have at least one control.",
             get_status(control_pct, "below", 95), "Healthy is 95% or more",
             "Factors without controls are left unmanaged.", "Assign a control to every identified factor.",
             fac[~fac["has_control"]], ["factor_name", "barrier_name", "critical"]),
        spec("12.4", "Do the controls work?",
             of(len(weak_controls), len(controls), "control") + " " + isare(len(controls)) + " not working or unknown (" + str(round(weak_pct)) + "%).",
             get_status(weak_pct, "above", 20), "Healthy is 20% or less",
             "Barriers wear down even though controls exist on paper.", "Redesign or strengthen these controls and find the root cause.",
             weak_controls, ["control_name", "control_condition"]),
        spec("12.5", "Are critical barriers protected from wear?",
             many(exposed_count, "critical barrier", "faces a factor with no working control.", "face a factor with no working control."),
             get_status(exposed_count, "above", 0), "Healthy is none (partly working controls count as working)",
             "These barriers can fail without warning.", "Escalate and fix controls on these barriers first.",
             exposed, ["barrier_name", "factor_name", "factor_category"]),
        spec("12.7", "Are degradation risks controlled?",
             of(len(unmanaged), len(fac), "factor") + " " + hashave(len(fac)) + " no working control (" + str(round(unmanaged_pct)) + "%).",
             get_status(unmanaged_pct, "above", 20), "Healthy is 20% or less (partly working controls count as working)",
             "Where controls are weak, risk goes up.", "Investigate, redesign or retrain on these controls.",
             unmanaged, ["factor_name", "barrier_name", "critical"]),
    ]

    def c1():
        donut(count_by(vc, "control_condition", "controls"), "control_condition", "controls", "Do the controls work?", condition_colors)

    def c2():
        bars(count_by(vfac, ["category", "critical"], "factors"), "category", "factors", "What wears barriers down? (red is critical)", "critical", yes_no_colors)

    def c3():
        bars(count_by(vfac, "controls_working", "factors"), "controls_working", "factors", "How many controls work for each factor?")

    return text, kpis, [c1, c2, c3]


def build_owner():
    text = "<b>" + str(len(unassigned)) + " barriers</b> have no owner. <b>" + top_owner + "</b> owns <b>" + str(round(top_share)) + "%</b> of the critical barriers, which is a lot of weight on one person."
    kpis = [
        spec("6.1", "Does every barrier have an owner?",
             of(len(unassigned), total, "barrier") + " " + hashave(total) + " no owner.",
             get_status(len(unassigned), "above", 0), "Healthy is none",
             "Nobody is accountable, so barriers may degrade unnoticed.", "Assign owners immediately.",
             unassigned, ["barrier_name", "critical", "condition"]),
        spec("6.2", "Does any path depend on one person?",
             many(len(spof_paths), "path", "depends on a single owner for all its barriers.", "depend on a single owner for all their barriers."),
             get_status(len(spof_paths), "above", 0), "Healthy is none",
             "If that owner is absent or struggling, the whole path is weak.", "Share ownership or name a backup.",
             spof_paths, ["name", "side", "n_barriers"]),
        spec("6.3", "Is critical work shared?",
             top_owner + " owns " + str(round(top_share)) + "% of the critical barriers.",
             get_status(top_share, "above", 40), "Healthy is 40% or less for one owner",
             "Too much critical work on one owner makes the system fragile.", "Spread critical barriers across owners and name backups.",
             owner_df.sort_values("critical", ascending=False), ["owner", "barriers", "critical"]),
        spec("6.6", "Do owners rely too much on people?",
             of(len(owners_human), len(owner_df), "owner") + " " + hashave(len(owner_df)) + " more than half their barriers depending on people.",
             get_status(len(owners_human), "above", 0), "Healthy is none",
             "Heavy reliance on people lowers reliability.", "Automate and manage human factors.",
             owners_human, ["owner", "barriers", "human_pct"]),
        spec("6.10", "Is each owner's protection balanced?",
             of(len(owners_reactive), len(owner_df), "owner") + " " + ("holds" if len(owner_df) == 1 else "hold") + " mostly reactive barriers.",
             get_status(len(owners_reactive), "above", 0), "Healthy is none over 80% reactive",
             "Paths that react instead of preventing leave hazards under-controlled.", "Reassign or add preventive barriers.",
             owners_reactive, ["owner", "barriers", "reactive_pct"]),
    ]

    def c1():
        donut(count_by(critical, "owner", "critical barriers"), "owner", "critical barriers", "Who owns the critical barriers?")

    def c2():
        bars(count_by(vb, ["owner", "function"], "barriers"), "owner", "barriers", "What does each owner's work look like?", "function", None, True)

    def c3():
        bars(owner_view[["owner", "ineffective_pct"]], "owner", "ineffective_pct", "Percent of each owner's barriers not working", None, None, True)

    return text, kpis, [c1, c2, c3]


def build_validity():
    text = "<b>" + of(len(audit_fail), total, "barrier") + "</b> cannot be fully audited. <b>" + many(len(chain_bad), "active barrier", "is missing a step of detect, decide, act.", "are missing a step of detect, decide, act.") + "</b> <b>" + many(len(shared_paths), "path", "has barriers that share a weak point.", "have barriers that share a weak point.") + "</b>"
    kpis = [
        spec("4.1", "Are barrier tests passing?",
             str(round(proven_pct)) + "% of tested barriers passed their last test (" + str(round(critical_proven_pct)) + "% for critical barriers).",
             "ALERT" if (proven_pct < 70 or (len(critical_tested) > 0 and critical_proven_pct < 90)) else "OK", "Healthy is 70% or more, and 90% or more for critical",
             "Barriers that fail tests give false comfort and leave paths exposed.", "Redesign or restore the failed barriers and escalate critical failures.",
             failed_test_barriers, ["barrier_name", "critical", "owner"]),
        spec("4.2", "Do barriers share the same weak point?",
             many(len(shared_paths), "path", "has barriers that depend on the same sensor, power or system.", "have barriers that depend on the same sensor, power or system.") + " " + str(len(shared_critical_paths)) + " of them " + ("includes" if len(shared_critical_paths) == 1 else "include") + " a critical barrier.",
             get_status(len(shared_critical_paths), "above", 0), "Healthy is none on paths with a critical barrier (prototype rule)",
             "One failure can take out several barriers at the same time.", "Use different sensors, power or logic so barriers fail independently.",
             shared_paths, ["name", "side", "dependency", "barriers_sharing"]),
        spec("4.3", "Can barriers be audited?",
             of(len(audit_fail), total, "barrier") + " lack a record or traceable evidence (" + str(round(audit_fail_pct)) + "%).",
             get_status(audit_fail_pct, "above", 20), "Healthy is 20% or less",
             "Barriers without evidence are hard to defend in an audit.", "Document criteria, test records and evidence for each one.",
             audit_fail, ["barrier_name", "auditable", "has_record"]),
        spec("4.11", "Is the detect, decide, act chain complete?",
             of(len(critical_chain_bad), len(critical_active), "active critical barrier") + " " + isare(len(critical_active)) + " missing a step (" + str(round(critical_chain_pct)) + "%). Across all active barriers it is " + str(round(chain_bad_pct)) + "%.",
             get_status(critical_chain_pct, "above", 10), "Healthy is 10% or less of critical barriers",
             "A barrier with a missing step cannot do its job from start to finish.", "Redesign the barrier to include the full chain.",
             chain_bad, ["barrier_name", "missing", "critical"]),
        spec("4.13", "Do critical steps depend on people?",
             str(round(crit_human_element_pct)) + "% of critical detect, decide and act steps depend on people.",
             get_status(crit_human_element_pct, "above", 50), "Healthy is 50% or less",
             "Human steps add variability and error. Prototype assumption: people do every step of a human barrier and the decide and act steps of a hardware plus human barrier.", "Automate where possible or add backup systems and train operators.",
             human_active, ["barrier_name", "barrier_type", "critical"]),
    ]

    def c1():
        donut(count_by(vb, "auditable", "barriers"), "auditable", "barriers", "Can the barriers be audited?", auditable_colors)

    def c2():
        rows = []
        for e in ["detect", "decide", "act"]:
            rows.append({"step": e.capitalize(), "state": "Present", "barriers": int((v_active[e] == "Yes").sum())})
            rows.append({"step": e.capitalize(), "state": "Missing", "barriers": int((v_active[e] != "Yes").sum())})
        bars(pd.DataFrame(rows), "step", "barriers", "Which steps of the chain exist? (active barriers)", "state", {"Present": "#2e9e5b", "Missing": "#d64545"})

    def c3():
        bars(count_by(vb[vb["common_dependency"].notna()], "common_dependency", "barriers"), "common_dependency", "barriers", "What do barriers depend on together?", None, None, True)

    return text, kpis, [c1, c2, c3]


def build_assurance():
    text = "<b>" + of(len(verified_b), total, "barrier") + "</b> have a completed check. <b>" + many(len(overdue_ass_all), "check", "is overdue", "are overdue") + "</b> and <b>" + many(len(failed_ass), "completed check", "failed.", "failed.") + "</b>"
    kpis = [
        spec("8.1", "Have barriers been checked?",
             str(round(verified_pct)) + "% of barriers have a completed check (" + str(round(critical_verified_pct)) + "% of critical barriers).",
             get_status(critical_verified_pct, "below", 90), "Healthy is 90% or more of critical barriers",
             "Unchecked barriers may fail unnoticed.", "Schedule the missing checks now and escalate overdue ones.",
             unverified_b, ["barrier_name", "critical", "owner"]),
        spec("8.2", "Are checks done as often as required?",
             of(len(short_b), len(recorded), "barrier") + " " + isare(len(recorded)) + " tested less often than required (" + str(round(short_pct)) + "%).",
             get_status(short_pct, "above", 10), "Healthy is 10% or less",
             "Fewer tests make unnoticed wear more likely.", "Follow the required frequency and adjust the schedule.",
             short_b, ["barrier_name", "critical", "owner"]),
        spec("8.3", "Do the checks pass?",
             of(len(failed_ass), len(done_ass), "completed check") + " failed (" + str(round(fail_rate)) + "%).",
             get_status(fail_rate, "above", 5), "Healthy is 5% or less",
             "Repeated failures point to a deeper weakness.", "Find the root cause, redesign or retrain.",
             failed_ass, ["barrier_name", "activity_type", "completed_date"]),
        spec("8.4", "Are critical barriers checked on time?",
             many(crit_bad_ass_barriers, "critical barrier", "has an overdue or failed check.", "have an overdue or failed check."),
             get_status(crit_bad_ass_barriers, "above", 0), "Healthy is none",
             "Critical paths are exposed to unmanaged risk.", "Escalate to leadership and check these barriers first.",
             crit_bad_ass, ["barrier_name", "activity_type", "status", "result"]),
        spec("8.5", "Do owners keep up with checks?",
             of(len(owners_ass_overdue), len(owner_ass), "owner") + " " + hashave(len(owner_ass)) + " more than one in five barriers with an overdue check.",
             get_status(len(owners_ass_overdue), "above", 0), "Healthy is none",
             "One owner falling behind weakens many barriers.", "Assign help, monitor and reassign work.",
             owners_ass_overdue, ["owner", "barriers", "overdue_pct"]),
    ]

    def c1():
        donut(count_by(vass, "status", "activities"), "status", "activities", "What state are the checks in?", action_colors)

    def c2():
        g = vass.groupby("activity_type")[["planned_per_year", "actual_per_year"]].sum().reset_index()
        long = pd.concat([
            pd.DataFrame({"activity_type": g["activity_type"], "kind": "Planned", "tests per year": g["planned_per_year"]}),
            pd.DataFrame({"activity_type": g["activity_type"], "kind": "Actual", "tests per year": g["actual_per_year"]}),
        ])
        bars(long, "activity_type", "tests per year", "Planned and actual checks per year", "kind", kpi_colors)

    def c3():
        bars(count_by(vass, ["owner", "status"], "activities"), "owner", "activities", "Check status for each owner", "status", action_colors, True)

    return text, kpis, [c1, c2, c3]


def build_kpis():
    crit_recorded = critical[critical["has_record"]]
    on_schedule = pct(len(crit_recorded[~crit_recorded["short_tested"]]), len(crit_recorded))
    lead_names = ["Checked", "Tested on schedule"]
    lead_values = [round(critical_verified_pct), round(on_schedule)]
    if len(critical_actions) > 0:
        lead_names.append("Fixes closed")
        lead_values.append(round(actions_closed_pct))
    leading = pd.DataFrame({"indicator": lead_names, "percent": lead_values})
    leading_low = leading[leading["percent"] < 90]
    crit_backlog = critical[(critical["overdue_check"]) | (critical["barrier_id"].isin(critical_actions[critical_actions["status"] == "Overdue"]["barrier_id"]))]
    crit_failed_b = critical[critical["failed_check"]]
    parts = pd.DataFrame({"part": ["Barriers with a record", "Barriers checked", "Critical barriers with a standard"], "percent": [round(documented_pct), round(verified_pct), round(critical_covered_pct)]})
    text = "Reliability index is <b>" + str(round(reliability_index, 2)) + "</b> (healthy is 0.7 or more). Audit readiness index is <b>" + str(round(audit_index, 2)) + "</b> (healthy is 0.75 or more). <b>" + many(len(crit_backlog), "critical barrier", "has an overdue check or fix.", "have an overdue check or fix.") + "</b>"
    kpis = [
        spec("10.1", "Are the leading indicators on target?",
             "For critical barriers: " + ", ".join([leading["indicator"][i].lower() + " " + str(leading["percent"][i]) + "%" for i in range(len(leading))]) + ".",
             "ALERT" if leading["percent"].min() < 90 else "OK", "Healthy is 90% or more on each",
             "Gaps in checks and fixes reduce confidence in the barriers.", "Schedule overdue checks and close open fixes on critical barriers first.",
             leading_low, ["indicator", "percent"]),
        spec("10.3", "Are critical barriers failing checks?",
             many(len(crit_failed_b), "critical barrier", "failed its latest check.", "failed their latest check.") + " Across all barriers, " + str(round(fail_rate)) + "% of completed checks failed.",
             get_status(len(crit_failed_b), "above", 0), "Healthy is none on critical barriers",
             "Repeated failures point to weaknesses in design or execution.", "Find the root cause and redesign or retrain.",
             crit_failed_ass, ["barrier_name", "activity_type", "completed_date"]),
        spec("10.4", "Is there a backlog on critical barriers?",
             many(len(crit_backlog), "critical barrier", "has an overdue check or fix.", "have an overdue check or fix."),
             get_status(len(crit_backlog), "above", 0), "Healthy is none",
             "Critical paths stay exposed to unmanaged risk.", "Escalate to leadership and prioritise the backlog.",
             crit_backlog, ["barrier_name", "owner", "overdue_check"]),
        spec("10.5", "Is the plant ready for an audit?",
             "Audit readiness index is " + str(round(audit_index, 2)) + ". It combines records, checks done and critical barriers with a standard.",
             get_status(audit_index, "below", 0.75), "Healthy is 0.75 or more (prototype uses the one threshold)",
             "An unprepared site risks failing an external audit.", "Document the missing records and prioritise the weakest part.",
             parts, ["part", "percent"]),
        spec("10.7", "How reliable are the barriers overall?",
             "Reliability index is " + str(round(reliability_index, 2)) + ". It is the share of working barriers minus the share that are not.",
             get_status(reliability_index, "below", 0.7), "Healthy is 0.7 or more",
             "Overall resilience is below the acceptable level.", "Start a fix programme and focus on the weakest paths.",
             degraded, ["barrier_name", "condition", "owner"]),
    ]

    def c1():
        bars(leading, "indicator", "percent", "Leading indicators for critical barriers (target 90%)")

    def c2():
        res = vass.copy()
        res["result"] = res["result"].fillna("Not done yet")
        donut(count_by(res, "result", "checks"), "result", "checks", "How did the checks turn out?", result_colors)

    def c3():
        a = count_by(vass[vass["status"] == "Overdue"], "owner", "items").assign(kind="Overdue checks")
        b = count_by(v_overdue, "owner", "items").assign(kind="Overdue fixes")
        both = pd.concat([a, b])
        bars(both, "owner", "items", "Overdue checks and fixes for each owner", "kind", {"Overdue checks": "#f08a24", "Overdue fixes": "#d64545"}, True)

    return text, kpis, [c1, c2, c3]


def build_codes():
    text = "<b>" + of(int(barriers["has_standard"].sum()), total, "barrier") + "</b> link to a recognised standard, and <b>" + many(len(critical_no_std), "critical barrier", "has none.", "have none.") + "</b> <b>" + many(len(std_pending), "link", "is not verified yet.", "are not verified yet.") + "</b>"
    kpis = [
        spec("11.1", "Do critical barriers have a standard?",
             many(len(critical_no_std), "critical barrier", "is not linked to any recognised standard.", "are not linked to any recognised standard."),
             get_status(len(critical_no_std), "above", 0), "Healthy is none",
             "A barrier without a standard may be uncertified or unsuitable.", "Map each one to the right code and escalate the gaps.",
             critical_no_std, ["barrier_name", "condition", "owner"]),
        spec("11.2", "How many barriers are covered by a standard?",
             str(round(std_rate)) + "% of barriers have a standard (" + str(round(critical_std_pct)) + "% of critical barriers).",
             get_status(critical_std_pct, "below", 90), "Healthy is 90% or more of critical barriers",
             "Barriers outside standards reduce audit confidence.", "Assign standards to uncovered barriers, critical ones first.",
             no_std, ["barrier_name", "critical", "owner"]),
        spec("11.3", "Are the standards verified?",
             of(len(crit_std_unverified), len(crit_with_std), "critical barrier") + " with a standard " + hashave(len(crit_with_std)) + " a link that is not verified (" + str(round(crit_std_unverified_pct)) + "%). Across all links it is " + str(round(std_unverified_pct)) + "%.",
             get_status(crit_std_unverified_pct, "above", 10), "Healthy is 10% or less of critical barriers",
             "Documented but unverified barriers may fail audits or inspections.", "Verify within 7 days and enforce deadlines.",
             std_pending, ["barrier_name", "standard_code", "verification_status"]),
        spec("11.4", "Do standards conflict?",
             many(len(conflict_b), "barrier", "has standards that overlap or conflict.", "have standards that overlap or conflict.") + " " + str(round(multi_pct)) + "% of barriers use more than one standard.",
             get_status(len(conflict_b), "above", 0), "Healthy is no conflicts",
             "Conflicts make compliance duties unclear.", "Resolve the conflict with the governing authority.",
             std_full[std_full["conflict_flag"] == "Yes"], ["barrier_name", "standard_code", "verification_status"]),
        spec("11.5", "Do owners know their standards?",
             of(len(owners_no_std), len(owner_ass), "owner") + " " + hashave(len(owner_ass)) + " more than 30% of barriers without a standard.",
             get_status(len(owners_no_std), "above", 0), "Healthy is none (prototype threshold 30%)",
             "Unclear duties raise the risk of uncertified barriers.", "Give these owners explicit standard references.",
             owners_no_std, ["owner", "barriers", "no_standard_pct"]),
    ]

    def c1():
        donut(count_by(vstd, "verification_status", "links"), "verification_status", "links", "Are the standard links verified?", standard_colors)

    def c2():
        cover = vb.assign(coverage=vb["has_standard"].map({True: "Has a standard", False: "No standard"}))
        bars(count_by(cover, ["coverage", "critical"], "barriers"), "coverage", "barriers", "Which barriers have a standard? (red is critical)", "critical", yes_no_colors)

    def c3():
        bars(count_by(vstd, "standard_code", "links"), "standard_code", "links", "Which standards are used?", None, None, True)

    return text, kpis, [c1, c2, c3]


builders = {
    "Overview": build_overview,
    "Condition": build_condition,
    "Criticality": build_criticality,
    "Corrective Actions": build_actions,
    "Type and Function": build_type_function,
    "Degradation": build_degradation,
    "Owner": build_owner,
    "Validity": build_validity,
    "Assurance": build_assurance,
    "KPIs": build_kpis,
    "Codes and Standards": build_codes,
}


def clean(text):
    return re.sub("<[^>]+>", "", text).replace("|", "/")


def make_report():
    lines = ["# Bowtie insights report", ""]
    lines.append("- Bowtie: " + bowtie + " | " + hazard)
    lines.append("- Top event: " + top_event)
    lines.append("- Data as of: " + data["as_of_date"])
    lines.append("- Scope: all barriers, pathways, actions, factors and controls of this bowtie. The critical-only switch in the app changes charts and the table only, not this report.")
    lines.append("- Counts: " + str(total) + " barriers, " + str(len(pathways)) + " paths, " + str(len(actions)) + " actions, " + str(len(fac)) + " degradation factors, " + str(len(controls)) + " controls, " + str(len(assurance)) + " assurance activities, " + str(len(standards)) + " standard links")
    lines.append("- Validation: " + str(len(check_table) - len(failed)) + " of " + str(len(check_table)) + " checks passed")
    if len(failed) == 0:
        lines.append("- Validation status: PASS")
    else:
        lines.append("- Validation status: FAIL")
        lines.append("- WARNING: validation has failures, so these metrics are provisional and for prototype use only.")
    rows = []
    for name in view_names:
        t, ks, cs = builders[name]()
        lines.append("")
        lines.append("## " + name)
        lines.append(clean(t))
        lines.append("")
        lines.append("| IRC | Question | Status | Finding | Healthy level | Affected items |")
        lines.append("|---|---|---|---|---|---|")
        for k in ks:
            affected = 0
            labels = ""
            if k["items"] is not None and len(k["items"]) > 0:
                affected = len(k["items"])
                labels = "; ".join([str(v) for v in k["items"][k["cols"][0]].head(15)])
            lines.append("| " + k["irc"] + " | " + clean(k["label"]) + " | " + status_words[k["status"]] + " | " + clean(k["message"]) + " | " + clean(k["rule"]) + " | " + str(affected) + " |")
            rows.append({
                "bowtie_id": bowtie, "hazard": hazard, "top_event": top_event, "as_of_date": data["as_of_date"], "dashboard": name,
                "irc": k["irc"], "question": k["label"], "status": status_words[k["status"]], "finding": k["message"], "healthy_level": k["rule"],
                "risk": k["risk"], "action": k["action"], "affected_count": affected, "affected_items": labels, "validation_status": "PASS" if len(failed) == 0 else "FAIL",
            })
    lines.append("")
    lines.append("## Validation")
    lines.append("| Group | Check | Result | Detail |")
    lines.append("|---|---|---|---|")
    for i in range(len(check_table)):
        r = check_table.iloc[i]
        lines.append("| " + r["group"] + " | " + clean(r["check"]) + " | " + r["result"] + " | " + clean(str(r["detail"])) + " |")
    return "\n".join(lines), pd.DataFrame(rows).to_csv(index=False)


report_md, report_csv = make_report()
st.sidebar.markdown("**5. Actions**")
st.sidebar.button("Reset filters", on_click=reset_filters, key="reset_side")
filtered_csv = ranked[ranked["barrier_id"].isin(vb["barrier_id"])][["barrier_id", "barrier_name", "risk", "condition", "owner", "function", "barrier_type", "critical"]].to_csv(index=False)
st.sidebar.download_button("Download filtered barriers (CSV)", filtered_csv, file_name="bowtie_filtered_barriers_" + bowtie + ".csv", mime="text/csv")
st.sidebar.download_button("Download report (Markdown)", report_md, file_name="bowtie_report_" + bowtie + ".md", mime="text/markdown")
st.sidebar.download_button("Download insights (CSV)", report_csv, file_name="bowtie_insights_" + bowtie + ".csv", mime="text/csv")
st.sidebar.caption("Reports cover every dashboard for the selected bowtie. They use all of its data, not the filters. Mock data for the prototype: the real Stress Test Bowtie JSON replaces mock_bowtie_data.json.")

page_text, page_kpis, page_charts = builders[view]()
page(page_text, page_kpis, page_charts)