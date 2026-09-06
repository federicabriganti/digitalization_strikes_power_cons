# AI & Data Center Energy Dashboard — EU

Analysis of the energy exposure of EU countries to the growth of data centers
(AI/cloud). Portfolio project for a data officer application (IEA/OECD).

## Structure

```
data/raw/          original source files
data/processed/    intermediate output (csv)
scripts/           one script per step
output/            one Excel file per step
```

## Steps

| Step | Description | Input | Script | Output |
|---|---|---|---|---|
| 1 | Energy exposure per country **+ EU27 aggregate (25 countries available, Cyprus and Malta missing from the colocation file)**. Years: 2024-2026 (current IEA data) + 2028/2030 (ENTSO-E ERAA projection). 2027/2029/2031 excluded | colocation csv, CONSUMI_ELETTRICI_ENTSO.xlsx, MES_0526.csv | `step1_energy_exposure.py` | `step1_energy_exposure.xlsx` |
| 2 | Three digitalization factors per country **per year** (cloud, AI, hosting turnover), missing values filled with linear interpolation inside the observed range (never extrapolated) **+ EU aggregate** + composite KPI on the common 2021-2024 window (1 Low/2 Medium/3 High: how many of the 3 factors grow faster than the EU average) | isoc_cicce_usen2, isoc_eb_ain2, sbs_sc_ovw (Eurostat xlsx files) | `step2_digitalization_kpi.py` | `step2_digitalization_kpi.xlsx` |
| 3 | Anomalies in monthly electricity consumption, 27 EU countries + EU27 aggregate, with **recency weighting** (exponential weight, halved every 5 years: a recent anomaly counts more than an old one) | MES_0526.csv (IEA) | `step3_consumption_anomalies.py` | `step3_consumption_anomalies.xlsx` |
| 4 | Matrix of exposure (Step 1) x recency-weighted instability (Step 3) x **digitalization KPI (Step 2)**, years 2026/2028/2030. Exposure threshold: EU27 aggregate (per year). Instability threshold: median across countries | step1 + step2 + step3 (output of this same project) | `step4_matrix.py` | `step4_exposure_instability_matrix.xlsx` |

## Project rule

Every step also computes the EU total, where possible, instead of leaving it for later.

## Known limits

- Step 1: ERAA only covers 2028/2030; for the other years national consumption is
  kept constant (no own projection). "Other Southern Europe" (a regional aggregate
  in the colocation file) is excluded, as there is no matching source for it.
- Step 2: the Eurostat AI indicator only covers the manufacturing sector (not
  general "AI adoption"). EU27-level hosting turnover is confidential in Eurostat:
  a bottom-up aggregate is used instead, based on the countries with public data
  (Ireland and Luxembourg excluded, confidential even at country level). For
  Ireland and Luxembourg the KPI is computed in a partial version (cloud+AI only,
  labeled "partial, 2/3 factors") instead of N/A.
- Step 3: `contamination="auto"` (scikit-learn decides the threshold for each
  series based on its own anomaly score distribution), not a fixed value — so both
  the count and the intensity of anomalies are genuinely comparable across
  countries.
- Step 4: the exposure axis is a single point per year (2026/2028/2030); the
  instability axis summarizes the whole IEA history available per country (back to
  2010 for the longest series), recency weighted but not tied to one specific
  year.

## Conclusions

From the two-way matrix (Step 4), across all three years considered (2026, 2028,
2030), three distinct profiles stand out:

- **Portugal is the country needing the most attention.** It is the only country
  whose energy exposure grows faster than any other (4.34% -> 10.61% -> 14.74%, the
  steepest jump in the whole sample), stays in the High exposure/High instability
  quadrant in all three years, and has a **Low** digitalization KPI: its
  infrastructure growth is not matched by a comparable growth of its domestic
  digital economy — a pattern worth flagging to grid planners.
- **Ireland and Luxembourg have high exposure but a historically stable grid.**
  They stay in the High exposure/Low instability quadrant every year, with a
  Medium KPI (partial, due to missing turnover data). The highest exposure in the
  whole sample (Ireland: 14.33% -> 17.58%) has not so far translated into grid
  instability.
- **Germany is the most balanced profile.** High KPI (growing faster than the EU
  average on all three digitalization factors), moderate and steadily growing
  energy exposure, low consumption instability: no warning signal on any of the
  three indicators.
- **The Netherlands, Denmark and Finland** enter or settle into the highest
  attention quadrant (High exposure/High instability) as the EU threshold itself
  rises over time (2.56% in 2026 -> 4.40% in 2030), showing a wider group of
  countries becoming energy-relevant, not just the already well-known case of
  Ireland.

## Hypothesis to check (not proven by the data in this project)

The mismatch between fast capacity growth and slow domestic digitalization
(Portugal: MW growing fast, KPI Low) might reflect data centers built to serve
international demand rather than the domestic digital economy. No data in this
project measures the real origin of traffic or customers of these data centers, so
this idea remains a hypothesis, not a proven conclusion. An equally plausible
alternative explanation: the KPI measures growth rate relative to the EU average,
so an already digitalized country can score "Low" simply due to a saturation
effect (high starting base), not because its capacity serves other economies.
