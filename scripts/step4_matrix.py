"""
Step 4 - Matrix: energy exposure x consumption instability x digitalization KPI

Combines:
  - Step 1: energy exposure per country, years 2026/2028/2030
  - Step 2: digitalization KPI per country (used as point size in the chart)
  - Step 3: instability of monthly electricity consumption per country (recency
    weighted intensity)

Thresholds: instead of an arbitrary cut (e.g. median), the EU27 aggregate value is
used for the exposure axis, for consistency with the rest of the project (Step 2
uses the same idea for its KPI). For the instability axis the EU27 aggregate is NOT
used, because it is a fundamentally smoother series (country-level anomalies cancel
out in the sum) and is not comparable to single-country series on this axis; the
median across countries is used instead.

Quadrants:
  - High exposure, high instability: highest attention priority
  - High exposure, low instability: exposed but with a historically stable grid
  - Low exposure, high instability: unstable grid but weakly linked to data centers
  - Low exposure, low instability: no particular signal

Input:
  - output/step1_energy_exposure.xlsx
  - output/step2_digitalization_kpi.xlsx
  - output/step3_consumption_anomalies.xlsx (sheet 'Summary per country')

Output:
  output/step4_exposure_instability_matrix.xlsx
"""

import pandas as pd

STEP1_XLSX = "output/step1_energy_exposure.xlsx"
STEP2_XLSX = "output/step2_digitalization_kpi.xlsx"
STEP3_XLSX = "output/step3_consumption_anomalies.xlsx"
OUTPUT_XLSX = "output/step4_exposure_instability_matrix.xlsx"

NAME_FIX_STEP3_TO_STEP1 = {
    "Slovak Republic": "Slovakia",
    "EU27": "EU27 (25 countries available)",
}


def load_exposure_multi_year():
    df = pd.read_excel(STEP1_XLSX)
    df = df[df["Year"].isin([2026, 2028, 2030])][["Country", "Year", "Exposure_pct"]]
    return df


def load_instability():
    df = pd.read_excel(STEP3_XLSX, sheet_name="Summary per country")
    df["Country"] = df["Country"].replace(NAME_FIX_STEP3_TO_STEP1)
    return df[["Country", "Pct_anomalous_months", "Average_intensity_recency_weighted"]]


def load_kpi():
    df = pd.read_excel(STEP2_XLSX)
    df = df.drop_duplicates("Country")[["Country", "KPI_level", "KPI_label"]]
    return df


def classify_quadrant(row, exposure_threshold, instability_threshold):
    high_exposure = row["Exposure_pct"] >= exposure_threshold
    high_instability = row["Average_intensity_recency_weighted"] >= instability_threshold
    if high_exposure and high_instability:
        return "High exposure / High instability"
    if high_exposure and not high_instability:
        return "High exposure / Low instability"
    if not high_exposure and high_instability:
        return "Low exposure / High instability"
    return "Low exposure / Low instability"


def build_year(table, year):
    sub = table[table["Year"] == year].copy()
    eu_label = "EU27 (25 countries available)"
    eu_row = sub[sub["Country"] == eu_label]
    exposure_threshold = eu_row["Exposure_pct"].iloc[0]

    countries = sub[sub["Country"] != eu_label].copy()
    instability_threshold = countries["Average_intensity_recency_weighted"].median()
    countries["Year"] = year
    countries["EU_exposure_threshold"] = round(exposure_threshold, 2)
    countries["Median_instability_threshold"] = round(instability_threshold, 2)
    countries["Quadrant"] = countries.apply(
        classify_quadrant, axis=1, exposure_threshold=exposure_threshold, instability_threshold=instability_threshold
    )
    return countries.sort_values("Exposure_pct", ascending=False)


def main():
    exposure = load_exposure_multi_year()
    instability = load_instability()
    kpi = load_kpi()
    table = exposure.merge(instability, on="Country", how="inner").merge(kpi, on="Country", how="left")

    results = [build_year(table, year) for year in [2026, 2028, 2030]]
    final = pd.concat(results, ignore_index=True)

    final.to_excel(OUTPUT_XLSX, index=False, sheet_name="Country matrix")
    final.to_csv("data/processed/step4_matrix.csv", index=False)

    for year, df_year in zip([2026, 2028, 2030], results):
        print(f"--- {year}: exposure threshold={df_year['EU_exposure_threshold'].iloc[0]}%, "
              f"instability threshold={df_year['Median_instability_threshold'].iloc[0]}% ---")
        print(df_year[["Country", "Exposure_pct", "Average_intensity_recency_weighted", "KPI_label", "Quadrant"]].to_string(index=False))
        print()


if __name__ == "__main__":
    main()
