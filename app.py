import pandas as pd
import plotly.express as px
import streamlit as st

# --- 1. CONFIGURATION & DATA LOADING ---
st.set_page_config(page_title="Air Quality Analytics", layout="wide", page_icon="🏭")


@st.cache_data
def load_data():
    df = pd.read_parquet("Dataset/indian_air_quality.parquet")

    # Ensure datetime is correct format
    df["Datetime"] = pd.to_datetime(df["Datetime"])
    return df


df = load_data()

# --- 2. SIDEBAR CONTROLS (The "User Functions") ---
st.sidebar.header("🎛️ Control Panel")

# A. Multi-City Selection
city_list = sorted(df["City"].unique())
selected_cities = st.sidebar.multiselect(
    "Select Cities to Compare",
    options=city_list,
    default=["Delhi", "Mumbai"],  # Default to comparing these two
)

# B. Date Range Filter
min_date = df["Datetime"].min().date()
max_date = df["Datetime"].max().date()
date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

# C. Filter Data based on selection
if not selected_cities:
    st.warning("Please select at least one city from the sidebar.")
    st.stop()

mask = (
    (df["City"].isin(selected_cities))
    & (df["Datetime"].dt.date >= date_range[0])
    & (df["Datetime"].dt.date <= date_range[1])
)
filtered_df = df.loc[mask]

# --- 3. MAIN DASHBOARD ---
st.title("🏭 Air Pollution Analytics Dashboard")
st.markdown("**System:** Compliance Monitoring & Forecast | **Standard:** CPCB (India)")
st.markdown("---")

# --- 4. KPI ROW (Comparative Metrics) ---
# Calculate averages for the selected period
kpi_cols = st.columns(len(selected_cities))

for i, city in enumerate(selected_cities):
    city_data = filtered_df[filtered_df["City"] == city]
    avg_pm = city_data["PM2_5_ugm3"].mean()
    max_pm = city_data["PM2_5_ugm3"].max()

    # Determine Color Status
    if avg_pm <= 60:
        color = "normal"
    elif avg_pm <= 120:
        color = "off"
    else:
        color = "inverse"  # Red for danger

    with kpi_cols[i]:
        st.metric(
            label=f"{city} Avg PM2.5",
            value=f"{avg_pm:.1f}",
            delta=f"Peak: {max_pm:.0f}",
            delta_color=color,
        )

# --- 5. ADVANCED ANALYSIS TABS ---
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Comparative Trends |",
        "Heatmap Analysis |",
        "Distribution |",
        "Policy Report",
    ]
)

with tab1:
    st.subheader("Temporal Variation Analysis")
    # Interactive Line Chart
    fig_line = px.line(
        filtered_df,
        x="Datetime",
        y="PM2_5_ugm3",
        color="City",
        title="PM2.5 Levels Over Time (Comparative)",
        labels={"PM2_5_ugm3": "PM2.5 Concentration (µg/m³)"},
    )
    # Add CPCB Limit Line
    fig_line.add_hline(
        y=60, line_dash="dash", line_color="red", annotation_text="CPCB Safe Limit (60)"
    )
    st.plotly_chart(fig_line, width="stretch")

with tab2:
    st.subheader("Identify Pollution Hotspots (Hour vs. Day)")
    # Let user pick which city to view heatmap for
    heatmap_city = st.selectbox("Select City for Heatmap", selected_cities)

    # Prepare Pivot Table for Heatmap
    hm_data = filtered_df[filtered_df["City"] == heatmap_city].copy()
    hm_data["Hour"] = hm_data["Datetime"].dt.hour
    hm_data["Day"] = hm_data["Datetime"].dt.day_name()

    # Aggregate data
    heatmap_pivot = hm_data.pivot_table(
        index="Day", columns="Hour", values="PM2_5_ugm3", aggfunc="mean"
    )

    # Sort days correctly
    days_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    heatmap_pivot = heatmap_pivot.reindex(days_order)

    fig_hm = px.imshow(
        heatmap_pivot,
        labels=dict(x="Hour of Day", y="Day of Week", color="PM2.5 Level"),
        x=heatmap_pivot.columns,
        y=heatmap_pivot.index,
        color_continuous_scale="RdYlGn_r",  # Red is bad, Green is good
        title=f"Pollution Intensity Heatmap: {heatmap_city}",
    )
    st.plotly_chart(fig_hm, width="stretch")
    st.info(
        "💡 Insight: Dark red spots indicate the exact time traffic or industrial activity peaks."
    )

with tab3:
    st.subheader("Statistical Distribution & Compliance")
    col1, col2 = st.columns(2)

    with col1:
        # Box Plot for Range
        fig_box = px.box(
            filtered_df,
            x="City",
            y="PM2_5_ugm3",
            color="City",
            title="Pollution Range (Min/Max/Median)",
        )
        st.plotly_chart(fig_box, width="stretch")

    with col2:
        # Histogram
        fig_hist = px.histogram(
            filtered_df,
            x="PM2_5_ugm3",
            color="City",
            barmode="overlay",
            title="Frequency of Pollution Levels",
        )
        fig_hist.add_vline(x=60, line_dash="dash", line_color="red")
        st.plotly_chart(fig_hist, width="stretch")

with tab4:
    st.subheader("Policy Recommendation Report")

    for city in selected_cities:
        city_slice = filtered_df[filtered_df["City"] == city]
        avg_val = city_slice["PM2_5_ugm3"].mean()
        compliance_pct = (city_slice["PM2_5_ugm3"] <= 60).mean() * 100

        # Dynamic Risk Assessment Logic
        if avg_val < 30:
            status = "GOOD"
            action = "Maintain current green cover. No action needed."
            color = "green"
        elif avg_val < 60:
            status = "SATISFACTORY"
            action = "Routine monitoring. Enforce dust control measures."
            color = "blue"
        elif avg_val < 90:
            status = "MODERATE RISK"
            action = "Activate GRAP Stage 1 (Mechanized sweeping, water sprinkling)."
            color = "orange"
        elif avg_val < 120:
            status = "POOR"
            action = "Activate GRAP Stage 2 (Ban diesel generators, parking fee hike)."
            color = "brown"
        else:
            status = "SEVERE EMERGENCY"
            action = "Activate GRAP Stage 3/4 (Close schools, ban construction, odd-even traffic)."
            color = "red"

        with st.expander(f"Report for {city} (Status: {status})", expanded=True):
            st.markdown(f"""
            * **Average PM2.5:** {avg_val:.2f} µg/m³
            * **Compliance Rate:** {compliance_pct:.1f}% of hours were safe.
            * **Legislation:** Air (Prevention and Control of Pollution) Act, 1981
            * **Recommended Action:** :{color}[**{action}**]
            """)

# --- 6. FOOTER ---
st.markdown("---")
st.caption(
    "Data Source: CPCB & Satellite Monitoring | Dashboard v2.0 | Developed by AI/ML Engineering Team"
)
