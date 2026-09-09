# Impact of digitalization on power consumption - EU
The aim of this analysis is to identify the most vulnerable EU countries, whose power consumption may be influenced by digitalization. Based on raw data from Eurostat, IEA and ENTSO-E webpages, each EU country is examined from three different perspectives:
- how much its power consumption is related to data centers and IT demands
- how fast its economy is moving towards digitalization
- how unstable its power grid has been in the recent years.

## Structure

```
data/raw/          original source files
data/processed/    intermediate output (csv)
scripts/           one script per step
output/            one Excel file per step
```
Outside this folder, you will find the following files:
- `Impact of digitalization on power consumption.pbix`, a Power BI report showing the inputs, outputs, and main findings of the analysis.
- `Impact of digitalization on power consumption.pdf`, the PDF version of the Power BI report for those who do not have Power BI. Note that some interactive charts appear frozen in this static version.

## Step 1 — Energy exposure per country

### Inputs

**Colocation IT power file** (`colocation...megawatts.csv`)<br>
Source: [Statista/Petroc Taylor](https://www.statista.com/statistics/1659712/europe-colocation-data-center-power-by-country/) (Premium/paywalled), sourced from Colocation and Scale industry research.<br>
Definition: for each European country, the electrical power capacity (MW)
dedicated specifically to servers ("IT power", excluding cooling, lighting
and other site overhead) in *colocation* data centers — sites where a
provider rents capacity to multiple client companies, as opposed to a
company's own private data center. Covers 2024-2031; the later years are
provider-announced plans, not measured figures.<br>
Name in Power BI report: IT power Supply (MW)

**ENTSO-E electricity demand file** (`CONSUMI_ELETTRICI_ENTSO.xlsx`)<br>
Source: [ENTSO-E, European Resource Adequacy Assessment (ERAA) 2025](https://www.entsoe.eu/eraa/2025/).<br>
Definition: projected total national electricity demand (TWh/year) for two
specific future "Target Years", 2028 and 2030, as modeled by the European
association of electricity transmission system operators for their own grid
adequacy planning.<br>
Name in Power BI report: Yearly electricity demand (GWh) for 2028 and 2030


**IEA Monthly Electricity Statistics** (`MES_0526.csv`)<br>
Source: [International Energy Agency, Monthly Electricity Statistics](https://www.iea.org/data-and-statistics/data-product/monthly-electricity-statistics).<br>
Definition: measured (not projected) monthly electricity production and
consumption by country, by energy balance category and by product, from
2010 onwards. Used here for its "Final Consumption (Calculated)" /
"Electricity" series.<br>
Name in Power BI report: Monthly electricity demand (GWh) from 2015 onwards


### Output

**`step1_energy_exposure.xlsx`**<br>
Definition: one row per country and year, showing the country's planned
data center IT power converted into an annual electricity-equivalent (GWh),
the national annual electricity consumption used as the comparison base,
which source that consumption figure came from, and the resulting exposure
percentage. Includes an EU27 aggregate row per year (sum across the 25
countries available in the colocation file; Cyprus and Malta are missing
from that file and therefore from the aggregate).

### KPI

**Exposure_pct** = (planned IT power, MW, converted to an annual GWh equivalent) ÷ (national annual electricity consumption, GWh) × 100.<br>
Definition:  share of the country's current electricity demand related to planned data centers if they are built and running continuosly.<br>
Name in Power BI report: Energy exposure (%)

**Purpose:** a country with a small grid can be more exposed to the same
absolute number of megawatts than a country with a much larger grid. This
indicator corrects for that by expressing capacity relative to the size of
the national grid, instead of ranking countries by raw MW alone.

### Limits

- "Other Southern Europe", a regional aggregate column in the colocation
  file (not a single country), is excluded — there is no matching national
  consumption figure to divide it by.
- The EU27 aggregate in this step covers only 25 of the 27 EU countries
  (Cyprus and Malta are not present in the colocation source file at all).
- For 2024-2026, using current consumption as the denominator means the
  exposure figure for those years does not account for any future growth or
  decline in national consumption itself — only the numerator (planned MW)
  changes by year, not the denominator.

### Conclusions

Ireland has the highest exposure of any country in every year (14.33% in
2026, rising to 17.58% in 2030). Portugal shows the steepest growth of all
(4.34% → 10.61% → 14.74%), overtaking most other high-exposure countries by
2030. Most EU countries stay under 2% throughout. The EU27 aggregate itself
more than doubles over the period (1.78% in 2024 to 4.40% in 2030), showing
this is a rising trend at the EU level, not only a story about one or two
outlier countries.

---

## Step 2 — Digitalization factors and composite KPI

### Inputs

**Cloud adoption file** (`isoc_cicce_usen2...xlsx`)<br>
Source: [Eurostat, ICT usage in enterprises survey (isoc_cicce_use)](https://ec.europa.eu/eurostat/databrowser/view/isoc_cicce_usen2/default/table?lang=en).<br>
Definition: the percentage of enterprises (10 or more employees, all
economic activities) in each country that report buying cloud computing
services, surveyed roughly every one to two years from 2014 to 2025 (the
survey is not run every single year, so several years are structurally
missing, not just unreported).<br>
Name in Power BI report: Cloud adoption (%)

**AI adoption file** (`isoc_eb_ain2...xlsx`)<br>
Source: [Eurostat, ICT usage in enterprises survey (isoc_eb_ain2)](https://ec.europa.eu/eurostat/databrowser/view/isoc_eb_ain2/default/table?lang=en).<br>
Definition: the percentage of enterprises in each
country that report using artificial intelligence technologies for
marketing or sales purposes, surveyed in 2021, 2023, 2024 and 2025. <br>
Name in Power BI report: Cloud adoption (%)

**Hosting sector turnover file** (`sbs_sc_ovw...xlsx`)<br>
Source: [Eurostat, Structural Business Statistics (sbs_sc_ovw)](https://ec.europa.eu/eurostat/databrowser/view/sbs_sc_ovw/default/table?lang=en).<br>
Definition: the annual net turnover, in million euro, of enterprises
classified under "Data processing, hosting and related activities; web
portals" (NACE code 63.11-63.12), by country, from 2021 to 2024. This is a
measured economic figure (not a survey opinion), the only one of the three
Step 2 inputs based on business accounts rather than a questionnaire.<br>
Name in Power BI report: Hosting Data Turnover (million €)

### Output

**`step2_digitalization_kpi.xlsx`**<br>
Definition: one row per country and year (2014-2025, the full span across
all three inputs), with the cloud adoption %, AI adoption % and hosting
turnover (€ million) for that country/year — including values filled by
linear interpolation where the original survey had a gap, each flagged in
its own `*_filled` column. Every row also repeats that country's growth rate
for each of the three factors between 2021 and 2024 (the KPI computation
window), the matching EU benchmark growth rates, and the resulting KPI
level and label, so the KPI can be checked directly against the numbers in
the same row. Includes an EU aggregate row per year.

### KPI — Digitalization Velocity

Named "velocity" because it measures a growth *rate* relative to the EU
average, not an absolute digitalization level. A country can score high
here while still being less digitalized overall than a slower-growing peer.

**KPI_level (1-3)**: for each country, the growth of each of the three
factors between 2021 and 2024 — the only period covered by all three inputs
— is compared to the EU's own growth in the same period (cloud and AI:
difference in percentage points, since these are already percentages;
turnover: relative percentage growth, since this is a euro amount). The
level is simply how many of the three factors grew faster than the EU:
3 of 3 → level 3, "High". 2 of 3 → level 2, "Medium". 0-1 of 3 → level 1,
"Low". If only the turnover figure is missing (Ireland and Luxembourg: it is
confidential at Eurostat, for both the country and the EU aggregate), a
partial KPI is computed using cloud and AI growth only, and is explicitly
labeled "(partial, 2/3 factors)" rather than presented as a full result.<br>
Name in Power BI report: Digitalization Velocity

**Purpose:** turns three separate, differently-scaled indicators into one
comparable score, so it is possible to say "this country's digital economy
is growing faster/slower than the EU average" in a single number and,
combined with Step 1, to flag countries where physical infrastructure is
being built faster than the domestic digital economy is growing (see the
hypothesis at the end of this document).

### Limits

- EU27-level hosting turnover is confidential in Eurostat's publication;
  a bottom-up total (sum of the countries with public data) is used as a
  substitute, and Ireland and Luxembourg (both individually confidential
  too) are excluded from that sum.
- Missing values are filled only inside the range actually observed for
  each country (e.g. cloud data missing for 2022, sitting between known 2021
  and 2023 values, is interpolated).
- The partial KPI (cloud+AI only) uses a different, easier threshold to
  clear than the full 3-factor KPI (1 of 2 factors vs. 2 of 3), so it is not
  numerically equivalent to a full "Medium". It is a lower-confidence
  estimate, not a directly comparable score.

### Conclusions

Germany, Austria, Latvia and Poland are the only countries with a full
"High" KPI (growing faster than the EU average on all three factors
simultaneously). Most countries (16 of the countries with a full KPI) are
"Low". Growth on the three factors does not move together within a country:
Spain, for example, grows faster than the EU average only on turnover
(+79.6% vs. the EU's +48.6%) while growing slower than the EU average on
both cloud (+4.9pp vs. +8.1pp) and AI (+11.1pp vs. +13.6pp) adoption
showing the three factors can tell different stories about the same
country, which is the reason for tracking all three rather than one
combined figure alone.

---

## Step 3 — Instability of monthly electricity consumption

### Inputs

**IEA Monthly Electricity Statistics** (`MES_0526.csv`)<br>
Source: [International Energy Agency, Monthly Electricity Statistics](https://www.iea.org/data-and-statistics/data-product/monthly-electricity-statistics)<br>
(same file as Step 1, different series usage: here, the full monthly time
series for all 27 EU countries individually, rather than a single annual
total).

### Output

**`step3_consumption_anomalies.xlsx`**<br>
Definition: two sheets. "Anomalies" lists every month flagged as anomalous
for every country, with the consumption value, how far it deviates from the
expected (deseasonalized) trend, its recency weight, and its combined
recency+severity weight. "Summary per country" has one row per country (plus
the EU27 aggregate) with the count of anomalous months, the plain average
anomaly size, and the recency+severity-weighted average anomaly size — this
last figure is the one carried forward into Step 4.

### KPI — Instability

**Average_intensity_recency_severity_weighted**: each country's monthly
series is deseasonalized using a classic additive decomposition (a 12-month
centered moving average for the trend, average deviation by calendar month
for the seasonal component), producing a residual that isolates whatever is
not explained by trend or season. Isolation Forest is then run on that
residual to flag anomalous months, with its sensitivity (`contamination`)
set to "auto".
Each flagged anomaly then gets a weight built from two components
multiplied together: a recency component that decays exponentially with age
(halving every 5 years), and a severity component equal to the size of the
anomaly itself.<br>
Name in Power BI report: Anomaly Score Weighted Average

**Purpose:** acts as a proxy for how much resilience a national grid already
has. A country whose consumption has recently shown large, hard-to-explain
swings has, by this measure, less slack to absorb new load, such as data
center demand, without further instability, regardless of whether data
centers themselves are the cause of past anomalies.

### Limits

- No anomaly is matched to a specific real-world cause (a heatwave, a cold
  snap, an economic shock) for any of the 27 countries. It would require
  dedicated research per country. The output says which months were unusual
  and by how much, not why.
- This indicator summarizes each country's entire available IEA history.
  It is not a snapshot of any single year, even though the recency and
  severity weighting means large, recent months matter far more than small,
  old ones.

### Conclusions

With `contamination="auto"`, the share of anomalous months genuinely varies
by country (from 10.8% in Czechia to 21.6% in Slovakia) instead of clustering
around one fixed rate. Lithuania stands out with by far the
largest combined-weight average anomaly size (16.13%, well above the next
highest countries), while the EU27 aggregate's own anomalies are much
smaller (3.67%) than any individual country's. This is expected, since
country-level swings partly cancel out once summed at EU level, which is
also why the EU aggregate is not used as the threshold on this axis in
Step 4.

---

## Step 4 — Exposure x instability x digitalization matrix

### Inputs

**Step 1, 2 and 3 outputs** (`step1_energy_exposure.xlsx`,
`step2_digitalization_kpi.xlsx`, `step3_consumption_anomalies.xlsx`)
Source: this project's own prior steps, not an external source.

### Output

**`step4_exposure_instability_matrix.xlsx`**<br>
Definition: one row per country and year (2026, 2028, 2030), with that
country's exposure percentage, instability score, Digitalization Velocity, the
year's EU exposure threshold, the cross-country median instability
threshold, and the resulting quadrant label.

### KPI

**Quadrant**: each country/year is classified on two axes. On the exposure
axis, a country is "high" if its Exposure_pct (Step 1) is at or above that
year's EU27 aggregate exposure. On the instability axis, a country is "high" if its
Average_intensity_recency_severity_weighted (Step 3) is at or above the median value
across all countries. The median is used here instead of the EU aggregate,
because the EU aggregate consumption series is structurally smoother
(country-level anomalies partly cancel out when summed), which would make
almost every individual country look "unstable" by comparison.
Digitalization Velocity (Step 2) is layered onto the
same chart as point size, so all three indicators are visible together
without adding a dimension that would need its own threshold logic.

**Purpose:** on their own, exposure, instability and digitalization are
three separate rankings that do not tell you where to look first. Combining
them into one view answers a more direct question: which countries are
*both* energy-exposed *and* already showing consumption instability versus countries that are exposed but stable, or
unstable but not yet energy-relevant.

### Limits

- The exposure axis is a single value per year (2026, 2028 or 2030); the
  instability axis is not tied to any specific year. It summarizes a
  country's whole IEA history, recency and severity weighted. The two axes
  therefore sit on different time bases within the same chart, which is
  worth stating explicitly rather than leaving implicit.
- Countries missing a full KPI (Ireland, Luxembourg: partial; Bulgaria,
  Czech Republic: not available) still appear on the exposure/instability
  axe.

### Conclusions

- **Portugal** needs the most attention: the steepest exposure growth of any
  country in the sample, stays in the High exposure/High instability
  quadrant every year, and has a Low Digitalization Velocity. Its infrastructure
  growth is not matched by a comparable growth of its domestic digital
  economy.
- **Ireland and Luxembourg** have the highest exposure in the sample but
  stay in the High exposure/Low instability quadrant every year — high
  exposure has not, so far, come with grid instability.
- **Germany** is the most balanced profile: High Digitalization Velocity,
  moderate and steadily growing exposure, low consumption instability.
- **The Netherlands, Denmark and Finland** enter or settle into the High
  exposure/High instability quadrant as the EU exposure threshold itself
  rises over time.

---

## Hypothesis to check (not proven by the data in this project)

The mismatch seen for Portugal (fast capacity growth, low domestic
digitalization growth) might reflect data centers built to serve
international demand rather than the country's own digital economy. No data
in this project measures the actual origin of traffic or customers at these
data centers, so this remains a hypothesis, not a proven conclusion. An
equally plausible alternative explanation: the KPI measures growth *rate*
relative to the EU average, so an already highly digitalized country can
score "Low" simply from a saturation effect (a high starting base leaves
less room to grow), independent of who its data center capacity actually
serves.
