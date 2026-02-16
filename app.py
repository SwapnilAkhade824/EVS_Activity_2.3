import pandas as pd
import plotly.express as px
import streamlit as st

# --- 1. CONFIGURATION & DATA LOADING ---
st.set_page_config(page_title="Air Quality Analytics", layout="wide", page_icon="🏭")


@st.cache_data
def load_data():
    """Load preprocessed air quality data with AQI columns"""
    df = pd.read_parquet("Dataset/indian_air_quality.parquet")

    # Ensure datetime is correct format
    df["Datetime"] = pd.to_datetime(df["Datetime"])
    
    # Verify AQI columns exist (they should be precomputed)
    required_cols = ["AQI", "AQI_Category", "AQI_Color"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"⚠️  Missing AQI columns: {missing_cols}. Please run preprocess_data.py first!")
        st.stop()
    
    return df


df = load_data()


# --- 2. AQI HELPER FUNCTION ---
def get_aqi_category(aqi):
    """Return AQI category and color"""
    if aqi <= 50:
        return "Good", "#00E400"
    elif aqi <= 100:
        return "Satisfactory", "#FFFF00"
    elif aqi <= 200:
        return "Moderate", "#FF7E00"
    elif aqi <= 300:
        return "Poor", "#FF0000"
    elif aqi <= 400:
        return "Very Poor", "#8F3F97"
    else:
        return "Severe", "#7E0023"


# Note: AQI is now precomputed in the dataset during preprocessing
# No need to calculate it at runtime anymore!


# --- 3. SIDEBAR CONTROLS (The "User Functions") ---
st.sidebar.header("Control Panel")

# Show AQI option
# show_aqi = st.sidebar.checkbox("Show AQI Analysis", value=True)
show_aqi = False

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

# --- 4. MAIN DASHBOARD ---
st.title(f"🏭 {selected_metric_name} Analytics Dashboard")
st.markdown(f"**Standard:** CPCB (India) | **Safe Limit:** {safe_limit} µg/m³")
st.markdown("---")

# --- 5. KPI ROW (Comparative Metrics) ---
if show_aqi:
    # Display AQI metrics
    st.subheader("📊 Air Quality Index (AQI) Overview")
    aqi_cols = st.columns(len(selected_cities))
    
    for i, city in enumerate(selected_cities):
        city_data = filtered_df[filtered_df["City"] == city]
        if city_data.empty:
            continue
        
        avg_aqi = city_data["AQI"].mean()
        category, color = get_aqi_category(avg_aqi)
        
        with aqi_cols[i]:
            st.markdown(f"### {city}")
            st.markdown(
                f"<div style='background-color: {color}; padding: 20px; border-radius: 10px; text-align: center;'>"
                f"<h1 style='color: white; margin: 0;'>{avg_aqi:.0f}</h1>"
                f"<h3 style='color: white; margin: 0;'>{category}</h3>"
                f"</div>",
                unsafe_allow_html=True
            )
    st.markdown("---")

# Display pollutant-specific metrics
st.subheader(f"🔬 {selected_metric_name} Metrics")
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

# --- 6. ADVANCED ANALYSIS TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Trends", "Heatmap", "Distribution", "Policy", "Health Impact"])

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

with tab5:
    st.subheader("🏥 Health Impact Assessment")
    
    st.markdown("""
    > [!WARNING]
    > Estimates based on WHO and ICMR studies. Actual health impacts vary by age, pre-existing conditions, and exposure duration.
    """)
    
    for city in selected_cities:
        city_slice = filtered_df[filtered_df["City"] == city]
        if city_slice.empty:
            continue
        
        avg_pm25 = city_slice["PM2_5_ugm3"].mean()
        avg_aqi = city_slice["AQI"].mean()
        
        # Health impact calculations based on research
        # Source: WHO Global Air Quality Guidelines, ICMR studies
        
        # 1. Premature deaths per 100,000 population
        # WHO: Every 10 µg/m³ increase in PM2.5 increases mortality by ~6%
        baseline_mortality = 700  # per 100,000 in India
        excess_pm25 = max(0, avg_pm25 - 10)  # WHO guideline is 10 µg/m³
        mortality_increase_pct = (excess_pm25 / 10) * 6
        premature_deaths = baseline_mortality * (mortality_increase_pct / 100)
        
        # 2. Life expectancy reduction
        # AQLI Study: 1 year lost per 10 µg/m³ above WHO guideline
        life_years_lost = (excess_pm25 / 10) * 1.0
        
        # 3. Disease risk multipliers
        copd_risk = 1 + (avg_pm25 / 100) * 0.8  # 80% increase per 100 µg/m³
        asthma_risk = 1 + (avg_pm25 / 50) * 0.3  # 30% increase per 50 µg/m³
        cardiovascular_risk = 1 + (avg_pm25 / 100) * 1.2
        
        # 4. WHO vs CPCB comparison
        who_guideline = 15  # Annual mean for PM2.5
        cpcb_standard = 40  # Annual mean for PM2.5
        
        with st.expander(f"🏥 Health Analysis: {city}", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("#### 💀 Mortality Impact")
                st.metric(
                    "Estimated Premature Deaths",
                    f"{premature_deaths:.0f}",
                    help="Per 100,000 population/year"
                )
                st.metric(
                    "Life Expectancy Reduction",
                    f"{life_years_lost:.1f} years",
                    help="Average years lost due to pollution"
                )
            
            with col2:
                st.markdown("#### 🫁 Disease Risk Multipliers")
                
                # Color code based on risk
                copd_color = "🔴" if copd_risk > 2 else "🟡" if copd_risk > 1.5 else "🟢"
                asthma_color = "🔴" if asthma_risk > 1.5 else "🟡" if asthma_risk > 1.2 else "🟢"
                cardio_color = "🔴" if cardiovascular_risk > 2 else "🟡" if cardiovascular_risk > 1.5 else "🟢"
                
                st.markdown(f"{copd_color} **COPD Risk:** {copd_risk:.2f}x baseline")
                st.markdown(f"{asthma_color} **Asthma Risk:** {asthma_risk:.2f}x baseline")
                st.markdown(f"{cardio_color} **Cardiovascular Risk:** {cardiovascular_risk:.2f}x baseline")
            
            with col3:
                st.markdown("#### 📊 Standards Comparison")
                
                # Create comparison chart
                comparison_data = pd.DataFrame({
                    "Standard": ["WHO Guideline", "CPCB Standard", f"{city} Current"],
                    "PM2.5 (µg/m³)": [who_guideline, cpcb_standard, avg_pm25]
                })
                
                fig_comp = px.bar(
                    comparison_data,
                    x="Standard",
                    y="PM2.5 (µg/m³)",
                    color="PM2.5 (µg/m³)",
                    color_continuous_scale=["green", "yellow", "red"],
                    title=f"PM2.5 Standards vs {city}"
                )
                st.plotly_chart(fig_comp, width="stretch")
            
            # Additional health guidance
            if avg_aqi > 300:
                st.error("⚠️ **SEVERE HEALTH RISK**: Avoid outdoor activities. Use N95 masks if going outside. Vulnerable groups should stay indoors with air purifiers.")
            elif avg_aqi > 200:
                st.warning("⚠️ **UNHEALTHY**: Limit outdoor exposure. Children, elderly, and people with respiratory conditions should stay indoors.")
            elif avg_aqi > 100:
                st.info("ℹ️ **MODERATE**: Sensitive individuals should consider reducing prolonged outdoor exertion.")
            else:
                st.success("✅ **SAFE**: Air quality is acceptable for most individuals.")
    
    # Add reference sources
    st.markdown("---")
    st.markdown("""
    **Data Sources & References:**
    - World Health Organization (WHO) Global Air Quality Guidelines 2021
    - Indian Council of Medical Research (ICMR) Air Pollution Studies
    - Air Quality Life Index (AQLI) - University of Chicago
    - Central Pollution Control Board (CPCB) Standards
    """)

# --- 7. FOOTER ---
st.markdown("---")
st.caption(
    "Data Source: CPCB & Satellite Monitoring | Dashboard v2.0 | Developed by AI/ML Engineering Team"
)
