"""
Step 2 - Three digitalization factors per country, per year + composite KPI

Factors:
  1. Cloud computing adoption (% of enterprises, 10+ employees, all activities), 2014-2025
  2. AI adoption (% of enterprises using AI for marketing/sales), 2021-2025
  3. Turnover of the "Data processing, hosting and related activities; web portals"
     sector (million euro), 2021-2024

Missing values: filled with LINEAR interpolation between known points for each
country, only inside the observed range (never extrapolated beyond the first/last
available year). Every filled value is marked in a *_filled column.

KPI: computed on the 2021-2024 window, the only one common to all three factors
(limited by turnover, the shortest series). For each country, count how many of the
3 factors grow (2021->2024, original or filled values) faster than the EU growth in
the same period. 3/3 -> level 3 "High", 2/3 -> level 2 "Medium", 0-1/3 -> level 1
"Low". If only turnover is missing (usually confidential data), a partial KPI is
computed using cloud+AI only, clearly labeled as partial. Countries missing 2021 or
2024 data on more than one factor: KPI = N/A.

Input:
  - data/raw/isoc_cicce_usen2__custom_22542778_spreadsheet.xlsx
  - data/raw/isoc_eb_ain2__custom_22542850_page_spreadsheet.xlsx
  - data/raw/sbs_sc_ovw__custom_22542826_spreadsheet.xlsx

Output:
  output/step2_digitalization_kpi.xlsx
"""

import pandas as pd
import openpyxl

CLOUD_XLSX = "data/raw/isoc_cicce_usen2__custom_22542778_spreadsheet.xlsx"
AI_XLSX = "data/raw/isoc_eb_ain2__custom_22542850_page_spreadsheet.xlsx"
SBS_XLSX = "data/raw/sbs_sc_ovw__custom_22542826_spreadsheet.xlsx"
OUTPUT_XLSX = "output/step2_digitalization_kpi.xlsx"

EU27_LABEL = "European Union - 27 countries (from 2020)"
CONFIDENTIAL_TURNOVER = {"Ireland", "Luxembourg"}


def load_cloud():
    wb = openpyxl.load_workbook(CLOUD_XLSX, data_only=True)
    ws = wb["Sheet 6"]
    years = ["2014", "2015", "2016", "2017", "2018", "2020", "2021", "2023", "2024", "2025"]
    result = {}
    for row in ws.iter_rows(min_row=13, max_row=51, values_only=True):
        country = row[0]
        if country is None:
            continue
        series = {y: (None if v in (None, ":") else float(v)) for y, v in zip(years, row[1 : 1 + len(years)])}
        result[country] = series
    return result


def load_ai():
    """File with flag columns in between (year, flag, year, flag, ...), different
    from the cloud file layout."""
    wb = openpyxl.load_workbook(AI_XLSX, data_only=True)
    ws = wb["Sheet 1"]
    years = ["2021", "2023", "2024", "2025"]
    result = {}
    for row in ws.iter_rows(min_row=13, max_row=46, values_only=True):
        country = row[0]
        if country is None:
            continue
        series = {y: (None if row[1 + i * 2] in (None, ":") else float(row[1 + i * 2])) for i, y in enumerate(years)}
        result[country] = series
    return result


def load_turnover():
    wb = openpyxl.load_workbook(SBS_XLSX, data_only=True)
    ws = wb["Data"]
    years = ["2021", "2022", "2023", "2024"]
    result, flags = {}, {}
    for row in ws.iter_rows(min_row=12, max_row=44, values_only=True):
        country = row[0]
        if country is None:
            continue
        series, confidential = {}, False
        for i, year in enumerate(years):
            val, flag = row[1 + i * 2], row[2 + i * 2]
            if val == ":" or flag == "C":
                series[year] = None
                confidential = confidential or (flag == "C")
            else:
                series[year] = float(val) if val is not None else None
        result[country] = series
        flags[country] = confidential
    return result, flags


def interpolate_series(series_by_year):
    """Linear interpolation inside the observed range, never extrapolated beyond
    the first/last known year. Also rebuilds years missing as a whole row in the
    source (e.g. cloud has no row for 2022) by reindexing on every integer year
    between the first and the last known year."""
    if not series_by_year:
        return {}, {}
    years_sorted = sorted(int(y) for y in series_by_year)
    full_range = range(years_sorted[0], years_sorted[-1] + 1)
    s = pd.Series({int(y): v for y, v in series_by_year.items()}, dtype="float64")
    s = s.reindex(full_range).sort_index()
    original_notna = s.notna()
    s_interp = s.interpolate(method="linear", limit_area="inside")
    filled = (~original_notna) & s_interp.notna()
    return s_interp.to_dict(), filled.to_dict()


def build_annual_table():
    cloud_raw = load_cloud()
    ai_raw = load_ai()
    turnover_raw, turnover_conf = load_turnover()

    countries = (set(cloud_raw) | set(ai_raw) | set(turnover_raw)) - {EU27_LABEL}
    all_years = sorted(
        set(int(y) for y in list(cloud_raw.values())[0].keys())
        | set(int(y) for y in list(ai_raw.values())[0].keys())
        | set(int(y) for y in list(turnover_raw.values())[0].keys())
    )

    rows = []
    for country in sorted(countries):
        cloud_i, cloud_fill = interpolate_series(cloud_raw.get(country, {}))
        ai_i, ai_fill = interpolate_series(ai_raw.get(country, {}))
        if country in CONFIDENTIAL_TURNOVER:
            turn_i, turn_fill = {}, {}
        else:
            turn_i, turn_fill = interpolate_series(turnover_raw.get(country, {}))

        for year in all_years:
            rows.append(
                {
                    "Country": country,
                    "Year": year,
                    "Cloud_pct": round(cloud_i[year], 2) if cloud_i.get(year) is not None else None,
                    "Cloud_filled": bool(cloud_fill.get(year, False)),
                    "AI_pct": round(ai_i[year], 2) if ai_i.get(year) is not None else None,
                    "AI_filled": bool(ai_fill.get(year, False)),
                    "Turnover_MEUR": round(turn_i[year], 1) if turn_i.get(year) is not None else None,
                    "Turnover_filled": bool(turn_fill.get(year, False)),
                }
            )

    # EU aggregate row: cloud/AI from Eurostat directly, turnover bottom-up
    eu_cloud_i, eu_cloud_fill = interpolate_series(cloud_raw.get(EU27_LABEL, {}))
    eu_ai_i, eu_ai_fill = interpolate_series(ai_raw.get(EU27_LABEL, {}))
    eu27_turnover_countries = [
        c for c in turnover_raw if c not in CONFIDENTIAL_TURNOVER and not turnover_conf.get(c, False)
    ]
    any_turnover_years = set(next(iter(turnover_raw.values())).keys())
    for year in all_years:
        year_str = str(year)
        turnover_total = None
        if year_str in any_turnover_years:
            values = [turnover_raw[c].get(year_str) for c in eu27_turnover_countries]
            values = [v for v in values if v is not None]
            turnover_total = sum(values) if values else None
        rows.append(
            {
                "Country": "EU27 (cloud/AI direct from Eurostat; turnover bottom-up on available countries)",
                "Year": year,
                "Cloud_pct": round(eu_cloud_i[year], 2) if eu_cloud_i.get(year) is not None else None,
                "Cloud_filled": bool(eu_cloud_fill.get(year, False)),
                "AI_pct": round(eu_ai_i[year], 2) if eu_ai_i.get(year) is not None else None,
                "AI_filled": bool(eu_ai_fill.get(year, False)),
                "Turnover_MEUR": round(turnover_total, 1) if turnover_total is not None else None,
                "Turnover_filled": False,
            }
        )

    return pd.DataFrame(rows)


def add_kpi(table):
    """KPI on the 2021-2024 common window (limited by turnover). Also exposes the
    underlying growth rates used for the comparison, as columns on every row."""
    pivot = table.pivot_table(index="Country", columns="Year", values=["Cloud_pct", "AI_pct", "Turnover_MEUR"])

    def growth(metric, country):
        try:
            v0 = pivot.loc[country, (metric, 2021)]
            v1 = pivot.loc[country, (metric, 2024)]
        except KeyError:
            return None
        if pd.isna(v0) or pd.isna(v1):
            return None
        if metric == "Turnover_MEUR":
            return None if v0 == 0 else 100 * (v1 - v0) / v0
        return v1 - v0  # percentage points for cloud/AI

    eu_label = "EU27 (cloud/AI direct from Eurostat; turnover bottom-up on available countries)"
    eu_cloud = growth("Cloud_pct", eu_label)
    eu_ai = growth("AI_pct", eu_label)
    eu_turnover = growth("Turnover_MEUR", eu_label)

    kpi_rows = []
    for country in pivot.index:
        c, a, t = growth("Cloud_pct", country), growth("AI_pct", country), growth("Turnover_MEUR", country)
        base_row = {
            "Country": country,
            "Cloud_growth_2021_2024_pp": round(c, 2) if c is not None else None,
            "AI_growth_2021_2024_pp": round(a, 2) if a is not None else None,
            "Turnover_growth_2021_2024_pct": round(t, 2) if t is not None else None,
            "EU_cloud_growth_2021_2024_pp": round(eu_cloud, 2),
            "EU_AI_growth_2021_2024_pp": round(eu_ai, 2),
            "EU_turnover_growth_2021_2024_pct": round(eu_turnover, 2),
        }

        if country == eu_label:
            kpi_rows.append({**base_row, "KPI_level": None, "KPI_label": "N/A (aggregate)"})
            continue

        if None not in (c, a, t):
            above = sum([c > eu_cloud, a > eu_ai, t > eu_turnover])
            level = 3 if above == 3 else (2 if above == 2 else 1)
            kpi_rows.append({**base_row, "KPI_level": level, "KPI_label": {3: "High", 2: "Medium", 1: "Low"}[level]})
        elif None not in (c, a) and t is None:
            # turnover missing (usually confidential): fallback on cloud+AI only.
            # Clearly labeled as partial - not the same as a full KPI, it is a
            # lower-confidence estimate based on 2 of 3 factors.
            above = sum([c > eu_cloud, a > eu_ai])
            level = 3 if above == 2 else (2 if above == 1 else 1)
            label = {3: "High", 2: "Medium", 1: "Low"}[level]
            kpi_rows.append({**base_row, "KPI_level": level, "KPI_label": f"{label} (partial, 2/3 factors: turnover missing)"})
        else:
            kpi_rows.append({**base_row, "KPI_level": None, "KPI_label": "N/A (not enough data even for a partial estimate)"})

    kpi_df = pd.DataFrame(kpi_rows)
    return table.merge(kpi_df, on="Country", how="left")


def main():
    table = build_annual_table()
    table = add_kpi(table)
    table.to_excel(OUTPUT_XLSX, index=False, sheet_name="Digitalization and KPI")
    table.to_csv("data/processed/step2_digitalization_kpi.csv", index=False)
    print(f"Rows generated: {len(table)}")
    print(table.drop_duplicates("Country")["KPI_label"].value_counts())


if __name__ == "__main__":
    main()
