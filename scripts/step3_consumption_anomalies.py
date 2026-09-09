"""
Step 3 - Anomalies in monthly electricity consumption, per EU country + EU aggregate

Method:
  1. Classic additive seasonal decomposition (2x12 moving average, no external
     statistics library needed)
  2. Isolation Forest on the residual (level, % of trend, month-over-month change)
  3. Recency weighting: each anomaly gets a weight = exp(-decay * years_ago), with
     decay chosen so the weight halves every 5 years. A recent anomaly counts more
     than an old one, but old anomalies are never fully ignored.

The output is structural (which months are anomalous, how large the anomaly is): it
does not try to explain each anomaly with a real-world event, since that would need
dedicated research for each of the 27 countries.

Input:
  - data/raw/MES_0526.csv (IEA Monthly Electricity Statistics)

EU27 aggregate: sum of the 27 EU countries (all present individually in the IEA
file, no country needs to be excluded here).

Output:
  output/step3_consumption_anomalies.xlsx
    - sheet 'Anomalies': one row per anomalous month, per country
    - sheet 'Summary per country': anomaly count and weighted intensity per country,
      used as the instability indicator in Step 4
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

IEA_CSV = "data/raw/MES_0526.csv"
OUTPUT_XLSX = "output/step3_consumption_anomalies.xlsx"

RANDOM_STATE = 42
CONTAMINATION = "auto"  # left to the model to decide, per series, not fixed

# recency weighting: weight = exp(-DECAY * years_ago), DECAY chosen so the weight
# halves every 5 years (ln(2)/5). An anomaly from 5 years ago counts half as much
# as one from today, one from 10 years ago a quarter, and so on.
DECAY_HALF_LIFE_YEARS = 5
DECAY = np.log(2) / DECAY_HALF_LIFE_YEARS

EU27 = [
    "Belgium", "Bulgaria", "Czech Republic", "Denmark", "Germany", "Estonia", "Ireland",
    "Greece", "Spain", "France", "Croatia", "Italy", "Cyprus", "Latvia", "Lithuania",
    "Luxembourg", "Hungary", "Malta", "Netherlands", "Austria", "Poland", "Portugal",
    "Romania", "Slovenia", "Slovak Republic", "Finland", "Sweden",
]


def load_all_series():
    df = pd.read_csv(IEA_CSV, skiprows=7, encoding="cp1252", low_memory=False)
    df.columns = ["Country", "Time", "Balance", "Product", "Value", "Unit"]
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df["Date"] = pd.to_datetime(df["Time"], format="%B %Y", errors="coerce")

    cons = df[
        (df["Balance"] == "Final Consumption (Calculated)") & (df["Product"] == "Electricity")
    ].dropna(subset=["Date", "Value"])

    series = {}
    for country in EU27:
        sub = cons[cons["Country"] == country].sort_values("Date")
        s = sub.set_index(sub["Date"].dt.to_period("M"))["Value"]
        series[country] = s

    # EU27 aggregate: sum of the months where all 27 countries have a value
    all_index = pd.concat(series.values(), axis=1, keys=series.keys())
    complete = all_index.dropna(how="any")
    series["EU27"] = complete.sum(axis=1)

    return series


def classical_deseasonalize(ts):
    ts2 = ts.copy()
    ts2.index = ts2.index.to_timestamp()
    trend = ts2.rolling(window=12, center=True).mean()
    trend = trend.rolling(window=2, center=True).mean()
    detrended = ts2 - trend
    seasonal_index = detrended.groupby(detrended.index.month).mean()
    seasonal_index = seasonal_index - seasonal_index.mean()
    seasonal = ts2.index.month.map(seasonal_index)
    seasadj = ts2 - seasonal
    residual = seasadj - trend
    out = pd.DataFrame({"value": ts2, "trend": trend, "residual": residual})
    out.index = out.index.to_period("M")
    return out


def detect_anomalies(decomposed):
    work = decomposed.dropna(subset=["residual", "trend"]).copy()
    if len(work) < 24:  # too short for a reliable seasonal analysis
        return work.iloc[0:0]
    work["residual_pct_trend"] = 100 * work["residual"] / work["trend"]
    work["delta_residual"] = work["residual"].diff()
    work = work.dropna(subset=["delta_residual"])
    if len(work) < 12:
        return work.iloc[0:0]

    features = work[["residual", "residual_pct_trend", "delta_residual"]]
    model = IsolationForest(n_estimators=300, contamination=CONTAMINATION, random_state=RANDOM_STATE)
    work["anomaly_flag"] = model.fit_predict(features)
    work["anomaly_score"] = model.decision_function(features)
    return work[work["anomaly_flag"] == -1].sort_values("anomaly_score")


def main():
    series = load_all_series()

    # reference month for the recency weight: the latest month available overall
    reference = max(ts.index.max() for ts in series.values() if not ts.dropna().empty)

    anomaly_rows = []
    summary_rows = []

    for country, ts in series.items():
        if ts.dropna().empty:
            continue
        decomposed = classical_deseasonalize(ts)
        anomalies = detect_anomalies(decomposed)
        n_valid_months = decomposed["residual"].notna().sum()

        weights = []
        for month, rec in anomalies.iterrows():
            years_ago = (reference - month).n / 12
            recency_weight = float(np.exp(-DECAY * max(years_ago, 0)))
            # combined weight = recency x severity, so a severe anomaly counts more
            # than a mild one even at the same age - a recency-only weight would let
            # a barely-flagged month (e.g. -1%) dilute the average as much as a real
            # shock (e.g. -28%) of the same age.
            combined_weight = recency_weight * abs(rec["residual_pct_trend"])
            weights.append(combined_weight)
            anomaly_rows.append(
                {
                    "Country": country,
                    "Month": str(month),
                    "Years_ago": round(years_ago, 2),
                    "Recency_weight": round(recency_weight, 4),
                    "Combined_weight_recency_severity": round(combined_weight, 4),
                    "Consumption_GWh": round(rec["value"], 1),
                    "Residual_GWh": round(rec["residual"], 1),
                    "Residual_pct_trend": round(rec["residual_pct_trend"], 2),
                    "Anomaly_score": round(rec["anomaly_score"], 4),
                }
            )

        weights = np.array(weights)
        abs_intensity = anomalies["residual_pct_trend"].abs().values if len(anomalies) else np.array([])

        summary_rows.append(
            {
                "Country": country,
                "Months_analyzed": int(n_valid_months),
                "N_anomalies": len(anomalies),
                "Pct_anomalous_months": round(100 * len(anomalies) / n_valid_months, 2) if n_valid_months else None,
                "Average_intensity_pct_trend": round(abs_intensity.mean(), 2) if len(anomalies) else None,
                "N_anomalies_recency_weighted": round(weights.sum(), 2) if len(weights) else 0,
                "Average_intensity_recency_severity_weighted": round(np.average(abs_intensity, weights=weights), 2) if len(weights) and weights.sum() > 0 else None,
            }
        )

    anomaly_table = pd.DataFrame(anomaly_rows)
    summary_table = pd.DataFrame(summary_rows).sort_values("Average_intensity_recency_severity_weighted", ascending=False)

    with pd.ExcelWriter(OUTPUT_XLSX) as writer:
        anomaly_table.to_excel(writer, index=False, sheet_name="Anomalies")
        summary_table.to_excel(writer, index=False, sheet_name="Summary per country")

    anomaly_table.to_csv("data/processed/step3_anomalies_detail.csv", index=False)
    summary_table.to_csv("data/processed/step3_anomalies_summary.csv", index=False)

    print(f"Countries analyzed: {len(series)}")
    print(f"Total anomalies found: {len(anomaly_table)}")
    print(summary_table.to_string(index=False))


if __name__ == "__main__":
    main()
