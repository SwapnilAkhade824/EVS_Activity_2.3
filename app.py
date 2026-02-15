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

# A. Pollutant Selection (NEW FEATURE)
pollutant_dict = {
    "PM2.5 (Fine Particles)": "PM2_5_ugm3",
    "PM10 (Coarse Particles)": "PM10_ugm3",
    "NO2 (Nitrogen Dioxide)": "NO2_ugm3",
    "SO2 (Sulfur Dioxide)": "SO2_ugm3",
    "CO (Carbon Monoxide)": "CO_ugm3",
    "Ozone (O3)": "O3_ugm3",
}

selected_metric_name = st.sidebar.selectbox(
    "Select Pollutant", list(pollutant_dict.keys())
)
metric = pollutant_dict[selected_metric_name]

# Define CPCB Safety Limits (Standard 24-hr avg)
limits = {
    "PM2_5_ugm3": 60,
    "PM10_ugm3": 100,
    "NO2_ugm3": 80,
    "SO2_ugm3": 80,
    "CO_ugm3": 2,  # mg/m3
    "O3_ugm3": 100,  # 8-hr limit
}
safe_limit = limits.get(metric, 60)

# B. Multi-City Selection
city_list = sorted(df["City"].unique())
selected_cities = st.sidebar.multiselect(
    "Select Cities to Compare",
    options=city_list,
    default=["Delhi", "Mumbai"],
)

# C. Date Range Filter
min_date = df["Datetime"].min().date()
max_date = df["Datetime"].max().date()
date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

# D. Filter Data based on selection
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
st.title(f"🏭 {selected_metric_name} Analytics Dashboard")
st.markdown(f"**Standard:** CPCB (India) | **Safe Limit:** {safe_limit} µg/m³")
st.markdown("---")

# --- 4. KPI ROW (Comparative Metrics) ---
kpi_cols = st.columns(len(selected_cities))

for i, city in enumerate(selected_cities):
    city_data = filtered_df[filtered_df["City"] == city]
    if city_data.empty:
        continue

    avg_val = city_data[metric].mean()
    max_val = city_data[metric].max()

    # Dynamic Color Logic based on specific pollutant limit
    if avg_val <= safe_limit:
        color = "normal"
    elif avg_val <= (safe_limit * 2):
        color = "off"
    else:
        color = "inverse"  # Red for danger

    with kpi_cols[i]:
        st.metric(
            label=f"{city} Avg",
            value=f"{avg_val:.1f}",
            delta=f"Peak: {max_val:.0f}",
            delta_color=color,
        )

# --- 5. ADVANCED ANALYSIS TABS ---
tab1, tab2, tab3, tab4 = st.tabs(
    ["📈 Trends", "🔥 Heatmap", "📊 Distribution", "📋 Policy"]
)

with tab1:
    st.subheader(f"Temporal Variation: {selected_metric_name}")
    fig_line = px.line(
        filtered_df,
        x="Datetime",
        y=metric,
        color="City",
        title=f"{selected_metric_name} Levels Over Time",
        labels={metric: "Concentration (µg/m³)"},
    )
    fig_line.add_hline(
        y=safe_limit,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Limit ({safe_limit})",
    )
    st.plotly_chart(fig_line, width="stretch")

with tab2:
    st.subheader("Pollution Hotspots")
    heatmap_city = st.selectbox(
        "Select City for Heatmap", selected_cities, key="hm_city"
    )

    hm_data = filtered_df[filtered_df["City"] == heatmap_city].copy()
    if not hm_data.empty:
        hm_data["Hour"] = hm_data["Datetime"].dt.hour
        hm_data["Day"] = hm_data["Datetime"].dt.day_name()

        heatmap_pivot = hm_data.pivot_table(
            index="Day", columns="Hour", values=metric, aggfunc="mean"
        )
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
            labels=dict(x="Hour of Day", y="Day of Week", color="Concentration"),
            x=heatmap_pivot.columns,
            y=heatmap_pivot.index,
            color_continuous_scale="RdYlGn_r",
            title=f"Intensity Heatmap: {heatmap_city} ({selected_metric_name})",
        )
        st.plotly_chart(fig_hm, width="stretch")

with tab3:
    st.subheader("Statistical Distribution")
    col1, col2 = st.columns(2)

    with col1:
        fig_box = px.box(
            filtered_df,
            x="City",
            y=metric,
            color="City",
            title=f"{selected_metric_name} Range",
        )
        fig_box.add_hline(y=safe_limit, line_dash="dash", line_color="red")
        st.plotly_chart(fig_box, width="stretch")

    with col2:
        fig_hist = px.histogram(
            filtered_df,
            x=metric,
            color="City",
            barmode="overlay",
            title="Frequency Distribution",
        )
        fig_hist.add_vline(x=safe_limit, line_dash="dash", line_color="red")
        st.plotly_chart(fig_hist, width="stretch")

with tab4:
    st.subheader("Automated Policy Recommendation")

    for city in selected_cities:
        city_slice = filtered_df[filtered_df["City"] == city]
        if city_slice.empty:
            continue

        avg_val = city_slice[metric].mean()
        compliance_pct = (city_slice[metric] <= safe_limit).mean() * 100

        # Generalized Logic: 0.5x Limit (Good) -> 1x Limit (Satisfactory) -> 2x Limit (Poor)
        if avg_val <= (safe_limit * 0.5):
            status = "GOOD"
            color = "green"
            action = "Maintain current green cover."
        elif avg_val <= safe_limit:
            status = "SATISFACTORY"
            color = "blue"
            action = "Routine monitoring."
        elif avg_val <= (safe_limit * 1.5):
            status = "MODERATE RISK"
            color = "orange"
            action = f"Activate pollution control for {selected_metric_name} sources."
        elif avg_val <= (safe_limit * 2.0):
            status = "POOR"
            color = "brown"
            action = "Activate GRAP Stage 2 (Strict enforcement)."
        else:
            status = "SEVERE EMERGENCY"
            color = "red"
            action = "Emergency measures (GRAP Stage 4) required immediately."

        with st.expander(f"Report: {city} - {selected_metric_name}", expanded=True):
            st.markdown(f"""
            * **Status:** :{color}[**{status}**]
            * **Avg Level:** {avg_val:.1f} (Limit: {safe_limit})
            * **Compliance:** {compliance_pct:.1f}% safe hours.
            * **Action:** {action}
            """)

# --- 6. FOOTER ---
st.markdown("---")
st.caption(
    "Data Source: CPCB & Satellite Monitoring | Dashboard v2.0 | Developed by AI/ML Engineering Team"
)
