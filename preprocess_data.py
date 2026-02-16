"""
Preprocessing script to calculate and add AQI columns to the air quality dataset.
This script reads the parquet file, calculates AQI, AQI_Category, and AQI_Color,
and saves the updated dataset back to the parquet file.
"""

import pandas as pd
from tqdm import tqdm


def calculate_aqi(row):
    """
    Calculate AQI based on CPCB standards (India)
    Returns overall AQI (0-500)
    """

    def get_sub_index(concentration, breakpoints):
        """Calculate sub-index for a pollutant"""
        # Check all breakpoint ranges
        for i in range(len(breakpoints)):
            if breakpoints[i][0] <= concentration <= breakpoints[i][1]:
                c_low, c_high, i_low, i_high = breakpoints[i]
                sub_i = ((i_high - i_low) / (c_high - c_low)) * (
                    concentration - c_low
                ) + i_low
                return round(sub_i)
        # If concentration exceeds all limits, return 500
        return 500

    # CPCB AQI Breakpoints: [C_low, C_high, I_low, I_high]
    pm25_bp = [
        [0, 30, 0, 50],
        [31, 60, 51, 100],
        [61, 90, 101, 200],
        [91, 120, 201, 300],
        [121, 250, 301, 400],
        [251, 500, 401, 500],
    ]
    pm10_bp = [
        [0, 50, 0, 50],
        [51, 100, 51, 100],
        [101, 250, 101, 200],
        [251, 350, 201, 300],
        [351, 430, 301, 400],
        [431, 600, 401, 500],
    ]
    no2_bp = [
        [0, 40, 0, 50],
        [41, 80, 51, 100],
        [81, 180, 101, 200],
        [181, 280, 201, 300],
        [281, 400, 301, 400],
        [401, 600, 401, 500],
    ]
    so2_bp = [
        [0, 40, 0, 50],
        [41, 80, 51, 100],
        [81, 380, 101, 200],
        [381, 800, 201, 300],
        [801, 1600, 301, 400],
        [1601, 2000, 401, 500],
    ]
    co_bp = [
        [0, 1.0, 0, 50],
        [1.1, 2.0, 51, 100],
        [2.1, 10, 101, 200],
        [10.1, 17, 201, 300],
        [17.1, 34, 301, 400],
        [34.1, 50, 401, 500],
    ]
    o3_bp = [
        [0, 50, 0, 50],
        [51, 100, 51, 100],
        [101, 168, 101, 200],
        [169, 208, 201, 300],
        [209, 748, 301, 400],
        [749, 1000, 401, 500],
    ]

    sub_indices = []

    # Calculate sub-index for each pollutant
    if pd.notna(row.get("PM2_5_ugm3")):
        sub_indices.append(get_sub_index(row["PM2_5_ugm3"], pm25_bp))
    if pd.notna(row.get("PM10_ugm3")):
        sub_indices.append(get_sub_index(row["PM10_ugm3"], pm10_bp))
    if pd.notna(row.get("NO2_ugm3")):
        sub_indices.append(get_sub_index(row["NO2_ugm3"], no2_bp))
    if pd.notna(row.get("SO2_ugm3")):
        sub_indices.append(get_sub_index(row["SO2_ugm3"], so2_bp))
    if pd.notna(row.get("CO_ugm3")):
        sub_indices.append(get_sub_index(row["CO_ugm3"], co_bp))
    if pd.notna(row.get("O3_ugm3")):
        sub_indices.append(get_sub_index(row["O3_ugm3"], o3_bp))

    # Overall AQI is the maximum of sub-indices
    return max(sub_indices) if sub_indices else None


def get_aqi_category(aqi):
    """Return AQI category and color"""
    if pd.isna(aqi):
        return None, None
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


def main():
    """Main preprocessing function"""
    print("🔄 Loading air quality data...")
    df = pd.read_parquet("Dataset/indian_air_quality.parquet")
    
    print(f"📊 Loaded {len(df):,} records")
    print(f"📅 Date range: {df['Datetime'].min()} to {df['Datetime'].max()}")
    
    # Check if AQI columns already exist
    if "AQI" in df.columns:
        print("⚠️  AQI column already exists. Recalculating...")
        df = df.drop(columns=["AQI", "AQI_Category", "AQI_Color"], errors="ignore")
    
    print("\n🧮 Calculating AQI for all records...")
    # Use tqdm for progress bar
    tqdm.pandas(desc="Processing rows")
    df["AQI"] = df.progress_apply(calculate_aqi, axis=1)
    
    print("🏷️  Adding AQI categories and colors...")
    df[["AQI_Category", "AQI_Color"]] = df["AQI"].apply(
        lambda x: pd.Series(get_aqi_category(x))
    )
    
    # Display statistics
    print("\n📈 AQI Statistics:")
    print(f"  - Mean AQI: {df['AQI'].mean():.1f}")
    print(f"  - Median AQI: {df['AQI'].median():.1f}")
    print(f"  - Min AQI: {df['AQI'].min():.1f}")
    print(f"  - Max AQI: {df['AQI'].max():.1f}")
    print(f"  - Records with AQI: {df['AQI'].notna().sum():,} ({df['AQI'].notna().sum()/len(df)*100:.1f}%)")
    
    print("\n📊 AQI Category Distribution:")
    category_counts = df["AQI_Category"].value_counts()
    for category, count in category_counts.items():
        print(f"  - {category}: {count:,} ({count/len(df)*100:.1f}%)")
    
    print("\n💾 Saving updated dataset...")
    df.to_parquet("Dataset/indian_air_quality.parquet", index=False)
    
    print("✅ Preprocessing complete! AQI columns added successfully.")
    print(f"📁 Updated file: Dataset/indian_air_quality.parquet")
    print(f"📦 New columns: AQI, AQI_Category, AQI_Color")


if __name__ == "__main__":
    main()
