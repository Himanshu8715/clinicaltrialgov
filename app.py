import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import time

# ==============================
# PAGE CONFIG
# ==============================

st.set_page_config(
    page_title="Clinical Trial Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================
# CUSTOM STYLING
# ==============================

st.markdown("""
<style>
.ai-box {
    background-color: #1C1F26;
    padding: 20px;
    border-radius: 12px;
    border-left: 5px solid #00BFFF;
    margin-top: 20px;
}
</style>
""", unsafe_allow_html=True)

st.title("🧠 Clinical Trial Intelligence Dashboard")

# ==============================
# FETCH DATA FROM CLINICALTRIALS.GOV
# ==============================

def fetch_trials(disease):
    base_url = "https://clinicaltrials.gov/api/v2/studies"

    params = {
        "query.term": disease,
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
            "Phase": str(protocol.get("designModule", {}).get("phases")),
            "Sponsor": protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
            "Status": protocol.get("statusModule", {}).get("overallStatus"),
            "Enrollment": protocol.get("designModule", {}).get("enrollmentInfo", {}).get("count"),
            "Country": None
        }

        # Extract first country if available
        locations = protocol.get("contactsLocationsModule", {}).get("locations")
        if locations and isinstance(locations, list):
            record["Country"] = locations[0].get("country")

        records.append(record)

    df = pd.DataFrame(records)

    df["Enrollment"] = pd.to_numeric(df["Enrollment"], errors="coerce")

    return df


# ==============================
# SIDEBAR FILTERS
# ==============================

st.sidebar.header("🔍 Search Filters")

disease = st.sidebar.text_input("Disease")

phase_filter = st.sidebar.selectbox(
    "Phase",
    ["All", "PHASE1", "PHASE2", "PHASE3", "PHASE4"]
)

country_filter = st.sidebar.text_input("Country")

with st.sidebar.expander("⚙ Advanced Filters"):
    sponsor_filter = st.text_input("Sponsor")
    status_filter = st.selectbox(
        "Recruitment Status",
        ["All", "RECRUITING", "COMPLETED", "ACTIVE_NOT_RECRUITING", "TERMINATED"]
    )
    enrollment_range = st.slider("Enrollment Range", 0, 5000, (0, 1000))


# ==============================
# ANIMATED METRIC FUNCTION
# ==============================

def animated_metric(label, value):
    placeholder = st.empty()
    for i in range(0, int(value)+1, max(1, int(value)//50 if value > 50 else 1)):
        placeholder.metric(label, i)
        time.sleep(0.01)
    placeholder.metric(label, value)


# ==============================
# GENERATE DASHBOARD
# ==============================

if st.sidebar.button("Generate Dashboard"):

    with st.spinner("Fetching Clinical Trial Data..."):
        df = fetch_trials(disease)

    if df.empty:
        st.warning("No trials found.")
    else:

        # Apply Filters
        if phase_filter != "All":
            df = df[df["Phase"].str.contains(phase_filter, na=False)]

        if country_filter:
            df = df[df["Country"].str.contains(country_filter, case=False, na=False)]

        if sponsor_filter:
            df = df[df["Sponsor"].str.contains(sponsor_filter, case=False, na=False)]

        if status_filter != "All":
            df = df[df["Status"] == status_filter]

        df = df[(df["Enrollment"] >= enrollment_range[0]) &
                (df["Enrollment"] <= enrollment_range[1])]

        # ==============================
        # KPI METRICS
        # ==============================

        st.markdown("## 📊 Key Metrics")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            animated_metric("Total Trials", len(df))

        with col2:
            animated_metric("Unique Sponsors", df["Sponsor"].nunique())

        with col3:
            animated_metric("Countries Covered", df["Country"].nunique())

        with col4:
            animated_metric("Avg Enrollment", int(df["Enrollment"].mean() if not df["Enrollment"].isna().all() else 0))

        # ==============================
        # INTERACTIVE WORLD MAP
        # ==============================

        st.markdown("## 🌍 Global Distribution")

        country_counts = df["Country"].value_counts().reset_index()
        country_counts.columns = ["Country", "Trials"]

        fig_map = px.choropleth(
            country_counts,
            locations="Country",
            locationmode="country names",
            color="Trials",
            color_continuous_scale="Blues"
        )

        st.plotly_chart(fig_map, use_container_width=True)

        # ==============================
        # CHARTS
        # ==============================

        st.markdown("## 📈 Trial Breakdown")

        colA, colB = st.columns(2)

        with colA:
            st.subheader("Phase Distribution")
            st.bar_chart(df["Phase"].value_counts())

        with colB:
            st.subheader("Status Distribution")
            st.bar_chart(df["Status"].value_counts())

        colC, colD = st.columns(2)

        with colC:
            st.subheader("Top Sponsors")
            st.bar_chart(df["Sponsor"].value_counts().head(10))

        with colD:
            st.subheader("Enrollment Distribution")
            st.bar_chart(df["Enrollment"].fillna(0))

        # ==============================
        # AI INSIGHT PANEL (Basic Auto Insight)
        # ==============================

        st.markdown("## 🧠 AI Strategic Insight")

        summary_text = f"""
        Total Trials: {len(df)}
        Top Sponsors: {df["Sponsor"].value_counts().head(3).to_string()}
        Phase Distribution: {df["Phase"].value_counts().to_string()}
        Countries Covered: {df["Country"].nunique()}
        """

        # Simple built-in AI-style summary (no external API required)
        ai_summary = f"""
        The dataset shows {len(df)} active clinical trials.
        Phase concentration suggests strong development focus in dominant phases.
        Sponsor diversity indicates competitive landscape.
        Geographic spread across {df["Country"].nunique()} countries reflects international research activity.
        """

        st.markdown(f"""
        <div class="ai-box">
            <h4>Executive Intelligence Summary</h4>
            <p>{ai_summary}</p>
        </div>
        """, unsafe_allow_html=True)

        # ==============================
        # DATA TABLE & DOWNLOAD
        # ==============================

        st.markdown("## 📄 Data Preview")
        st.dataframe(df.head(20))

        st.download_button(
            "Download Full Dataset (CSV)",
            df.to_csv(index=False),
            "clinical_trials.csv"
        )
