import streamlit as st
import pandas as pd
import requests
import re

# ============================================
# PAGE CONFIG
# ============================================

st.set_page_config(
    page_title="Clinical Trial Intelligence Platform",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Clinical Trial Intelligence & Eligibility Platform")

st.warning(
    "⚠️ For research and educational use only. "
    "Final clinical eligibility must be confirmed by investigators."
)

# ============================================
# FETCH DATA FROM CLINICALTRIALS.GOV
# ============================================

@st.cache_data(show_spinner=False)
def fetch_trials(disease):
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    params = {"query.term": disease, "pageSize": 200}
    response = requests.get(base_url, params=params)

    if response.status_code != 200:
        return pd.DataFrame()

    data = response.json()
    if "studies" not in data:
        return pd.DataFrame()

    records = []

    for study in data["studies"]:
        protocol = study.get("protocolSection", {})

        eligibility_text = protocol.get("eligibilityModule", {}).get("eligibilityCriteria")

        inclusion = None
        exclusion = None

        if eligibility_text:
            if "Exclusion Criteria:" in eligibility_text:
                inclusion = eligibility_text.split("Exclusion Criteria:")[0]
                exclusion = eligibility_text.split("Exclusion Criteria:")[1]
            else:
                inclusion = eligibility_text

        record = {
            "NCTId": protocol.get("identificationModule", {}).get("nctId"),
            "Title": protocol.get("identificationModule", {}).get("briefTitle"),
            "Phase": str(protocol.get("designModule", {}).get("phases")),
            "Sponsor": protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
            "Status": protocol.get("statusModule", {}).get("overallStatus"),
            "Enrollment": protocol.get("designModule", {}).get("enrollmentInfo", {}).get("count"),
            "Inclusion": inclusion,
            "Exclusion": exclusion
        }

        records.append(record)

    df = pd.DataFrame(records)
    df["Enrollment"] = pd.to_numeric(df["Enrollment"], errors="coerce")

    return df


# ============================================
# SIDEBAR GLOBAL SEARCH
# ============================================

st.sidebar.header("🔍 Search Trials")
disease = st.sidebar.text_input("Disease / Condition")

if not disease:
    st.info("Enter a disease in sidebar to begin.")
    st.stop()

df = fetch_trials(disease)

if df.empty:
    st.error("No trials found.")
    st.stop()

# ============================================
# TABS STRUCTURE
# ============================================

tab1, tab2 = st.tabs(["📊 Trial Intelligence", "🧬 Eligibility Matcher"])

# ============================================
# TAB 1 — TRIAL INTELLIGENCE DASHBOARD
# ============================================

with tab1:

    st.subheader("📊 Trial Analytics")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Trials", len(df))
    col2.metric("Unique Sponsors", df["Sponsor"].nunique())
    col3.metric("Phases Covered", df["Phase"].nunique())
    col4.metric("Avg Enrollment",
                int(df["Enrollment"].mean() if not df["Enrollment"].isna().all() else 0))

    st.markdown("### Phase Distribution")
    st.bar_chart(df["Phase"].value_counts())

    st.markdown("### Status Distribution")
    st.bar_chart(df["Status"].value_counts())

    st.markdown("### Top Sponsors")
    st.bar_chart(df["Sponsor"].value_counts().head(10))

    st.markdown("### Data Preview")
    st.dataframe(df[["NCTId", "Title", "Phase", "Sponsor", "Status"]].head(20))

    st.download_button(
        "Download Trial Dataset",
        df.to_csv(index=False),
        "trial_dataset.csv"
    )


# ============================================
# TAB 2 — ELIGIBILITY MATCHER
# ============================================

with tab2:

    st.subheader("🧬 Patient Eligibility Matching")

    colA, colB, colC = st.columns(3)

    patient_age = colA.number_input("Age", 0, 120, 45)
    patient_diagnosis = colB.text_input("Primary Diagnosis")
    pregnant = colC.selectbox("Pregnant?", ["No", "Yes"])

    renal_disease = st.selectbox("Renal Disease?", ["No", "Yes"])
    cancer_history = st.selectbox("History of Cancer?", ["No", "Yes"])

    def text_contains(text, keywords):
        if not text:
            return False
        text = text.lower()
        return any(k.lower() in text for k in keywords if k)

    def evaluate_eligibility(row):
        score = 0
        reasons = []

        inclusion = row["Inclusion"] or ""
        exclusion = row["Exclusion"] or ""

        # Inclusion match
        if text_contains(inclusion, [patient_diagnosis]):
            score += 3

        # Basic age heuristic
        if str(patient_age) in inclusion:
            score += 1

        # Exclusion checks
        if pregnant == "Yes" and text_contains(exclusion, ["pregnant"]):
            score -= 5
            reasons.append("Pregnancy exclusion")

        if renal_disease == "Yes" and text_contains(exclusion, ["renal", "kidney"]):
            score -= 4
            reasons.append("Renal exclusion")

        if cancer_history == "Yes" and text_contains(exclusion, ["cancer", "malignancy"]):
            score -= 4
            reasons.append("Cancer exclusion")

        if score >= 3:
            label = "Likely Eligible"
        elif score >= 1:
            label = "Possibly Eligible"
        else:
            label = "Not Eligible"

        return score, label, ", ".join(reasons)

    if st.button("Evaluate Patient"):

        df[["EligibilityScore", "EligibilityLabel", "ExclusionReasons"]] = df.apply(
            lambda row: pd.Series(evaluate_eligibility(row)),
            axis=1
        )

        df_sorted = df.sort_values("EligibilityScore", ascending=False)

        colX, colY, colZ = st.columns(3)

        colX.metric("Likely Eligible",
                    len(df_sorted[df_sorted["EligibilityLabel"] == "Likely Eligible"]))
        colY.metric("Possibly Eligible",
                    len(df_sorted[df_sorted["EligibilityLabel"] == "Possibly Eligible"]))
        colZ.metric("Not Eligible",
                    len(df_sorted[df_sorted["EligibilityLabel"] == "Not Eligible"]))

        st.markdown("### Top Matching Trials")

        st.dataframe(
            df_sorted[
                [
                    "NCTId",
                    "Title",
                    "Phase",
                    "Sponsor",
                    "EligibilityLabel",
                    "EligibilityScore",
                    "ExclusionReasons"
                ]
            ].head(20),
            use_container_width=True
        )

        with st.expander("📄 View Criteria for Top Trial"):
            top_trial = df_sorted.iloc[0]
            st.markdown("#### Inclusion Criteria")
            st.text(top_trial["Inclusion"])
            st.markdown("#### Exclusion Criteria")
            st.text(top_trial["Exclusion"])

        st.download_button(
            "Download Eligibility Results",
            df_sorted.to_csv(index=False),
            "eligibility_results.csv"
        )
