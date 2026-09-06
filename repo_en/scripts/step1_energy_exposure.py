"""
Step 1 - Energy exposure indicator per country (2024-2031)

Input:
  - data/raw/colocation_and_scale_colocation_data_center_it_power_supply_in_europe_from_2024_to_2031_by_country_in_megawatts.csv
  - data/raw/CONSUMI_ELETTRICI_ENTSO.xlsx (ENTSO-E ERAA 2025, electricity demand for 2028/2030, TWh)
  - data/raw/MES_0526.csv (IEA Monthly Electricity Statistics, used for years not covered by ERAA)

Method:
  exposure_% = (planned MW * 24 * 365 / 1000) / annual national electricity consumption (GWh)

  Denominator:
  - 2028 and 2030: ENTSO-E ERAA (real projection for that exact year)
  - all other years (2024-2027, 2029, 2031): IEA, last 12 months available,
    kept constant (no own projection: see limit in README)

  The two denominators are different in nature (one is a projection for the exact
  year, the other is the current value kept fixed) and are labeled separately in the
  output (column Denominator_source) so they are never mixed silently.

Output:
  output/step1_energy_exposure.xlsx
"""

import pandas as pd

COLO_CSV = "data/raw/colocation_and_scale_colocation_data_center_it_power_supply_in_europe_from_2024_to_2031_by_country_in_megawatts.csv"
IEA_CSV = "data/raw/MES_0526.csv"
ENTSOE_XLSX = "data/raw/CONSUMI_ELETTRICI_ENTSO.xlsx"
OUTPUT_XLSX = "output/step1_energy_exposure.xlsx"

NAME_MAP_IEA = {
    "Iceland (EEA)": "Iceland",
    "Slovakia": "Slovak Republic",
    "Other Southern Europe": None,
}

NAME_FIX_ENTSOE = {
    "Irelanf": "Ireland",
    "Slovack": "Slovakia",
    "Czech rep": "Czech Republic",
    "Luxemburg": "Luxembourg",
}

# EU27 countries present as a column in the colocation file (Cyprus and Malta are
# missing from that file, so they are excluded here too)
EU27_IN_COLO = {
    "Belgium", "Bulgaria", "Czech Republic", "Denmark", "Germany", "Estonia", "Ireland",
    "Greece", "Spain", "France", "Croatia", "Italy", "Latvia", "Lithuania", "Luxembourg",
    "Hungary", "Netherlands", "Austria", "Poland", "Portugal", "Romania", "Slovenia",
    "Slovakia", "Finland", "Sweden",
}
EU27_MISSING = {"Cyprus", "Malta"}  # not present in the colocation file


def load_colocation():
    df = pd.read_csv(COLO_CSV)
    df = df.rename(columns={df.columns[0]: "Year"})
    df["Year"] = df["Year"].astype(str).str.replace("*", "", regex=False)
    return df.set_index("Year")


def load_iea_annual_consumption():
    df = pd.read_csv(IEA_CSV, skiprows=7, encoding="cp1252", low_memory=False)
    df.columns = ["Country", "Time", "Balance", "Product", "Value", "Unit"]
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df["Date"] = pd.to_datetime(df["Time"], format="%B %Y", errors="coerce")
    cons = df[
        (df["Balance"] == "Final Consumption (Calculated)") & (df["Product"] == "Electricity")
    ].dropna(subset=["Date", "Value"])
    result = {}
    for country, sub in cons.groupby("Country"):
        last12 = sub.sort_values("Date").tail(12)
        if len(last12) == 12:
            result[country] = last12["Value"].sum()  # GWh per year
    return result


def load_entsoe_demand():
    df = pd.read_excel(ENTSOE_XLSX)
    df["country"] = df["country"].replace(NAME_FIX_ENTSOE)
    df = df.set_index("country")
    return {
        "2028": (df["TWh 2028"] * 1000).to_dict(),  # TWh -> GWh
        "2030": (df["TWh 2030"] * 1000).to_dict(),
    }


def build_exposure_table():
    colo = load_colocation()
    iea_annual = load_iea_annual_consumption()
    entsoe_demand = load_entsoe_demand()

    # current years (2024-2026): current IEA data, valid as is, no projection
    # future years (2027-2031): only 2028/2030 have a reliable projection (ENTSO-E);
    # 2027, 2029, 2031 are dropped (no reliable denominator available)
    CURRENT_YEARS = {"2024", "2025", "2026"}
    VALID_FUTURE_YEARS = {"2028", "2030"}
    YEARS_TO_KEEP = CURRENT_YEARS | VALID_FUTURE_YEARS

    rows = []
    for country in colo.columns:
        for year in colo.index:
            if year not in YEARS_TO_KEEP:
                continue
            mw = colo.loc[year, country]
            if pd.isna(mw):
                continue
            gwh_equiv = mw * 24 * 365 / 1000

            if year in entsoe_demand and country in entsoe_demand[year]:
                consumption_gwh = entsoe_demand[year][country]
                source = "ENTSO-E ERAA 2025 (projection for this year)"
            else:
                iea_name = NAME_MAP_IEA.get(country, country)
                consumption_gwh = iea_annual.get(iea_name) if iea_name else None
                source = "IEA (current data, last 12 months)" if consumption_gwh is not None else "N/A"

            exposure_pct = 100 * gwh_equiv / consumption_gwh if consumption_gwh else None

            rows.append(
                {
                    "Country": country,
                    "Year": year,
                    "IT_power_MW": mw,
                    "Annual_GWh_equivalent": round(gwh_equiv, 1),
                    "National_annual_consumption_GWh": round(consumption_gwh, 1) if consumption_gwh else None,
                    "Denominator_source": source,
                    "Exposure_pct": round(exposure_pct, 2) if exposure_pct else None,
                }
            )

    return pd.DataFrame(rows)


def add_eu27_aggregate(table):
    """Adds one 'EU27 (25 countries available)' row per year: sum of the EU27
    countries present in the colocation file AND with a valid national consumption
    that year. Cyprus and Malta are always excluded (missing from the colocation
    file)."""
    agg_rows = []
    for year, sub in table.groupby("Year"):
        sub_eu = sub[sub["Country"].isin(EU27_IN_COLO) & sub["National_annual_consumption_GWh"].notna()]
        if sub_eu.empty:
            continue
        included_countries = set(sub_eu["Country"])
        excluded_countries = (EU27_IN_COLO - included_countries) | EU27_MISSING
        gwh_total = sub_eu["Annual_GWh_equivalent"].sum()
        consumption_total = sub_eu["National_annual_consumption_GWh"].sum()
        sources = sorted(sub_eu["Denominator_source"].unique())
        agg_rows.append(
            {
                "Country": "EU27 (25 countries available)",
                "Year": year,
                "IT_power_MW": None,
                "Annual_GWh_equivalent": round(gwh_total, 1),
                "National_annual_consumption_GWh": round(consumption_total, 1),
                "Denominator_source": " + ".join(sources),
                "Exposure_pct": round(100 * gwh_total / consumption_total, 2),
                "Excluded_countries": ", ".join(sorted(excluded_countries)),
            }
        )
    return pd.concat([table, pd.DataFrame(agg_rows)], ignore_index=True)


def main():
    table = build_exposure_table()
    table = add_eu27_aggregate(table)
    table.to_excel(OUTPUT_XLSX, index=False, sheet_name="Energy exposure")
    table.to_csv("data/processed/step1_energy_exposure.csv", index=False)
    print(f"Rows generated: {len(table)}")
    print(table["Denominator_source"].value_counts())


if __name__ == "__main__":
    main()
