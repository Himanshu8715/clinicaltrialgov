import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Clinical Trial Intelligence", layout="wide")

st.title("🧠 Clinical Trial Intelligence Dashboard")

# ---------------------------------------------------
# Fetch ClinicalTrials.gov Data
# ---------------------------------------------------

def fetch_trials(disease):
    base_url = "https://clinicaltrials.gov/api/v2/studies"

    params = {
        "query.term": disease,
        "fields": "NCTId,Condition,Phase,LocationCountry,LeadSponsorName,OverallStatus,EnrollmentCount",
        "pageSize": 500
    }

    response = requests.get(base_url, params=params)

    if response.status_code != 200:
        return pd.DataFrame()

    data = response.json()

    if "studies" not in data:
        return pd.DataFrame()

    records = []

    for study in data["studies"]:
        protocol = study.get("protocolSection", {})

        record = {
            "NCTId": protocol.get("identificationModule", {}).get("nctId"),
            "Phase": protocol.get("designModule", {}).get("phases"),
            "Country": protocol.get("contactsLocationsModule", {}).get("locations"),
            "Sponsor": protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
            "Status": protocol.get("statusModule", {}).get("overallStatus"),
            "Enrollment": protocol.get("designModule", {}).get("enrollmentInfo", {}).get("count")
        }

        records.append(record)

    df = pd.DataFrame(records)

    # Clean columns
    df["Phase"] = df["Phase"].astype(str)
    df["Country"] = df["Country"].astype(str)
    df["Sponsor"] = df["Sponsor"].astype(str)
    df["Status"] = df["Status"].astype(str)
    df["Enrollment"] = pd.to_numeric(df["Enrollment"], errors="coerce")

    return df


# ---------------------------------------------------
# Main Filters
# ---------------------------------------------------

col1, col2, col3 = st.columns(3)

with col1:
    disease = st.text_input("Disease")

with col2:
    phase_filter = st.selectbox("Phase", ["All", "PHASE1", "PHASE2", "PHASE3", "PHASE4"])

with col3:
    country_filter = st.text_input("Country")

# ---------------------------------------------------
# Advanced Filters
# ---------------------------------------------------

with st.expander("⚙ Advanced Filters"):

    sponsor_filter = st.text_input("Sponsor Name")
    status_filter = st.selectbox("Recruitment Status", 
                                 ["All", "RECRUITING", "COMPLETED", "ACTIVE_NOT_RECRUITING", "TERMINATED"])
    enrollment_range = st.slider("Enrollment Range", 0, 5000, (0, 1000))


# ---------------------------------------------------
# Generate Dashboard
# ---------------------------------------------------

if st.button("Generate Dashboard"):

    df = fetch_trials(disease)

    if df.empty:
        st.warning("No trials found.")
    else:

        # Apply Main Filters
        if phase_filter != "All":
            df = df[df["Phase"].str.contains(phase_filter, na=False)]

        if country_filter:
            df = df[df["Country"].str.contains(country_filter, case=False, na=False)]

        # Apply Advanced Filters
        if sponsor_filter:
            df = df[df["Sponsor"].str.contains(sponsor_filter, case=False, na=False)]

        if status_filter != "All":
            df = df[df["Status"] == status_filter]

        df = df[(df["Enrollment"] >= enrollment_range[0]) & 
                (df["Enrollment"] <= enrollment_range[1])]

        # ------------------------------
        # Dashboard Metrics
        # ------------------------------

        st.subheader("📊 Key Metrics")

        colA, colB, colC = st.columns(3)

        colA.metric("Total Trials", len(df))
        colB.metric("Avg Enrollment", int(df["Enrollment"].mean() if not df["Enrollment"].isna().all() else 0))
        colC.metric("Unique Sponsors", df["Sponsor"].nunique())

        # ------------------------------
        # Charts
        # ------------------------------

        st.subheader("Phase Distribution")
        st.bar_chart(df["Phase"].value_counts())

        st.subheader("Status Distribution")
        st.bar_chart(df["Status"].value_counts())

        st.subheader("Top Sponsors")
        st.bar_chart(df["Sponsor"].value_counts().head(10))

        st.subheader("Country Distribution")
        st.bar_chart(df["Country"].value_counts().head(10))

        st.subheader("Trial Data Preview")
        st.dataframe(df.head(20))

        st.download_button("Download CSV", df.to_csv(index=False), "clinical_trials.csv")
