# Oil Chokepoint Model — Data and Sources
### CITS4403 Research Project — Raed

Every number the model uses, where it comes from, and whether it is published
**[DATA]** or our modelling choice **[ASSUMPTION]**. The values themselves live in
`src/oil_model_data.py` (and the sector parameters in `src/production_cascade.py`);
this document explains them. Source tags such as [S1] refer to the list at the end.

Units: **mb/d** = million barrels per day; **Mb** = million barrels.

---

## 1. Production and consumption by region

### Why regions, and how they were built

The model works with **ten regions**, not countries, for three reasons:

1. **Routes are between regions.** A tanker from the Gulf to Japan uses the same
   chokepoints whichever Gulf country loaded it, so modelling 200 countries would add
   detail without changing the flows.
2. **The regions are chosen by Hormuz exposure.** Sources usually report "Asia-Pacific"
   as one block, but China, India, Japan/Korea and the rest of Asia depend on Hormuz
   very differently and hold very different reserves. So Asia is split into four.
3. **No source uses these exact ten regions.** Each published table has its own
   groupings, so the model's regions had to be assembled: some taken directly, some
   added up from countries, some split from a larger total, and two (CIS and Latin
   America) worked out as the remainder of the world total.

Both sides are **total liquids**: crude oil, lease condensate, natural gas plant
liquids (NGLs: ethane, propane, butane), biofuels and refinery processing gain — the
definition EIA uses for world oil supply [S12]. Liquefied natural gas (LNG) is natural
gas, not oil, and is not included. Using one basis on both sides is what makes supply
and demand balance.

### What we found — production

| Figure | Value (mb/d) | Year, basis | Source |
|---|---|---|---|
| North America | 31.8 | 2025, crude + other liquids | Visual Capitalist / EIA regional chart [S21] |
| Middle East | 31.0 | 2025, crude + other liquids | [S21] |
| Asia-Pacific (one block) | 9.4 | 2025, crude + other liquids | [S21] |
| Africa | 7.6 | 2025, crude + other liquids | [S21] |
| Europe | 4.0 | 2025, crude + other liquids | [S21] |
| United States | 23.14 | 2025, total liquids | EIA STEO Table 3b [S16] |
| Canada | 6.06 | 2025, total liquids | [S16] |
| Mexico | 1.93 | 2025, total liquids | [S16] |
| Russia | 10.7 | 2025, total liquids | World Population Review / EI [S22] |
| World | ≈106 | 2025 | implied by [S21] (North America 31.8 = 29.9% of total) |

Also found but **not used**, because it is crude oil only: the 2025 crude ranking —
USA 13.59, Russia 9.89, Saudi Arabia 9.56, Canada 4.94, China 4.34, Iraq 4.30,
Brazil 3.74, Iran 3.30, UAE 3.20, Kuwait 2.60 mb/d [S12, S13]. Mixing these crude-only
figures with total-liquids consumption was the error behind the retracted "North
America contagion" finding.

### What we found — consumption

| Figure | Value (mb/d) | Year | Source |
|---|---|---|---|
| United States | 20.46 | 2024 | Energy Institute data via Statbase [S23] |
| China | 16.37 | 2024 | [S23] |
| India | 5.60 | 2024 | [S23] |
| World | 102.81 | 2024 | [S23] |
| Russia | 3.86 | 2024 | EIA, country list [S25] |
| Japan | 3.14 | 2024 | [S25] (another source gives 3.24) |
| South Korea | 2.54 | 2024 | [S25] (another source gives 2.89) |
| Canada | 2.38 | 2024 | [S25] |
| Europe | 13.9 | **2023** | Energy Institute Statistical Review 2024 [S17] |

### What the model uses, and how each number was obtained

| Region | Produces | How obtained | Consumes | How obtained |
|---|---|---|---|---|
| North America | **31.1** | **Direct**: US + Canada + Mexico, EIA [S16]. Replaced the 31.8 regional figure during review: EIA's own table is the primary source | **24.6** | **Summed**: US 20.46 + Canada 2.4 + Mexico 1.7 (Mexico: no source recorded) |
| Middle East | **31.0** | **Direct** [S21] | **9.5** | **Estimate** — no source recorded |
| CIS | **13.8** | **Remainder**, split using Russia 10.7 + Kazakhstan ~2.0 + others. Includes East Siberia 1.8, modelled as its own node | **4.8** | **Summed**: Russia 3.86 + others ~0.9 (estimate) |
| Latin America | **8.4** | **Remainder** of the world total (Brazil ~4.3, Venezuela, Argentina, Colombia) | **6.5** | **Estimate** — no source recorded |
| Africa | **7.6** | **Direct** [S21] | **4.4** | **Estimate** — no source recorded |
| Europe | **4.0** | **Direct** [S21] | **14.5** | **Estimate**, about 0.6 above the EI figure of 13.9 (2023) — see limitation below |
| China | **5.3** | **Split** from Asia-Pacific 9.4 | **16.4** | **Direct**: 16.37 [S23] |
| India | **0.9** | **Split** from Asia-Pacific 9.4 | **5.6** | **Direct**: 5.60 [S23] |
| Japan/Korea | **0.1** | **Split** from Asia-Pacific 9.4 | **5.7** | **Summed**: Japan 3.14 + Korea 2.54 [S25] |
| Other Asia | **3.1** | **Split**: what is left of Asia-Pacific 9.4 | **10.0** | **Estimate** — no source recorded |
| **World** | **105.3** | | **102.0** | EIA/EI world: 102.8 |

Key: **Direct** = taken from a published figure. **Summed** = countries added
together. **Split** = a published total divided using country figures. **Remainder** =
what is left of the world total after the direct regions. **Estimate** = a plausible
value with no source recorded in the project; these should be checked before being
cited.

### Known limitations of these figures

- **Unverified consumption totals.** Middle East, Latin America, Africa and Other Asia
  consumption, and Mexico's 1.7, have no recorded source. Europe's 14.5 is about 0.6
  above the Energy Institute's 13.9. Europe is never short in the model, so this does
  not change who runs short, but it slightly reduces the oil available to others.
- **Mixed years.** Production is 2025 data and consumption 2024 data. The model's
  surplus (105.3 − 102.0 ≈ 3.3 mb/d) is about double EIA's 2025 balance (≈ 105.4 −
  103.7 ≈ 1.6) [S16], so the model has a little more spare oil than reality.
- **Remainder regions are the least precise.** CIS and Latin America absorb any error in
  the other regions' figures.

## 2. Chokepoints — normal flow [DATA], capacity [mixed]

Normal flows are EIA's 2023 figures [S1]. **Open sea straits have no capacity
limit** — only a normal flow. Only engineered passages have one. A passage that is
x% closed lets through (1 − x) of its normal flow.

| Passage | Normal flow | Capacity | Notes |
|---|---|---|---|
| Strait of Hormuz | 20.9 | 20.9 | Capacity = normal flow, so a closure fraction and the flow it scales share one basis [DATA] |
| Strait of Malacca | 23.7 | none | Open strait |
| Bab el-Mandeb | 8.6 | none | Open strait |
| Cape of Good Hope | 6.0 | none | Open ocean |
| Danish Straits | 4.9 | none | Open strait |
| Turkish Straits | 3.4 | none | Open strait (Bosphorus) |
| Suez Canal + SUMED | 8.8 | 10.0 | Canal plus pipeline [ASSUMPTION: limit] |
| Panama Canal | 2.1 | 3.5 | Locks limit transits; very large crude tankers cannot fit [ASSUMPTION: limit] |

## 3. Pipelines and route limits

| Item | Value | Status | Notes |
|---|---|---|---|
| Saudi East-West pipeline | 7.0 mb/d | [DATA] | Raised from 5.0 in 2026 when its second line was converted from NGLs to crude. Actual 2026 throughput was lower (a drone strike in April; Yanbu loadings halted in September) |
| UAE ADCOP pipeline (to Fujairah) | 1.5 mb/d | [DATA] [S4] | |
| Russia's Baltic terminals | 2.5 mb/d | [ASSUMPTION] | Limit on the CIS→Europe (Baltic) route |
| East Siberia (ESPO) | 1.8 mb/d | [DATA] | Can only reach China and the Pacific |

A pipeline's capacity is a **shared daily budget**: all routes that start from it
together cannot exceed it.

## 4. Trade behaviour — [ASSUMPTION]

**Share of each region's exports sold on the spot market** (the rest is contracted):
North America 0.60, Latin America 0.80, Europe 0.50, CIS 0.50, East Siberia 0.30,
Middle East 0.35, Africa 0.90. Importers have nothing to export.

**Tanker fleet:** sized as world supply × a typical 20-day voyage × 1.25 (25% slack).

## 5. Price — short-run elasticity of demand

| Region | Elasticity | Status |
|---|---|---|
| North America | −0.05 | [DATA] Ghouri (2001): USA −0.045, Canada −0.06 |
| Europe | −0.09 | [DATA] within the range of Cooper (2003) |
| Japan/Korea | −0.06 | [ASSUMPTION] |
| China | −0.12 | [ASSUMPTION] |
| India, Other Asia | −0.20 | [ASSUMPTION] |
| Latin America | −0.15 | [ASSUMPTION] |
| Africa | −0.25 | [ASSUMPTION] most price-sensitive |
| Middle East | −0.08 | [ASSUMPTION] subsidised fuel |
| CIS | −0.10 | [ASSUMPTION] |

Pre-crisis Brent: **$69/bbl** (February 2026); observed Q2 2026: **~$105/bbl**.

## 6. Refineries — [ASSUMPTION]

| Item | Value | Notes |
|---|---|---|
| Minimum operating rate | 0.55 | A refinery shuts below 55% of capacity. Triggers only at deep closures (e.g. Other Asia at full closure, 5 of 12 shut), and never changes the result: the remaining refineries process all the oil available |
| Restart lag | 14 days | |
| Nelson Complexity Index | NA 11.0, India 11.0, Japan/Korea 9.0, Europe 8.5, China 8.0, LatAm 7.0, MidEast 7.0, Other Asia 6.5, CIS 6.0, Africa 5.0 | Range 5–21 [S18]. Used only for a **proxy**: complex refineries get up to 15% more usable product per barrel. Removing it lowers the threshold from 53% to 51% |

## 7. Strategic reserves

| Region | Reserve (Mb) | Max draw (mb/d) | Status |
|---|---|---|---|
| China | 1,400 | 4.0 | Reserve: [DATA, EIA estimate — China does not publish]. Rate: [ASSUMPTION] |
| Japan/Korea | 449 | 2.0 | Reserve: [DATA] Japan 380 + Korea 69. Rate: [ASSUMPTION] |
| North America | 285 | 2.7 | Both [DATA]: US SPR, September 2026 [S5]; DOE physical limit [S6, S7] |
| Europe | 179 | 1.5 | Reserve: [DATA] OECD Europe government stocks. Rate: [ASSUMPTION] |
| Other Asia | 50 | 0.3 | Both [ASSUMPTION] |
| India | 39 | 0.5 | Reserve: [DATA] ISPRL. Rate: [ASSUMPTION] |

Each region draws only on its own reserve. Producers hold none.
US context [S5, S8]: the SPR fell from 415.4 Mb (February 2026) to 285.0 Mb
(September 2026); the IEA coordinated release of 11 March 2026 was 400 Mb. That
partial release is why the observed price lies between the model's with- and
without-reserves prices.

## 8. Production cascade (Layer 3)

| Sector | Share of oil use (weight) | Oil dependence | Status |
|---|---|---|---|
| Transport | 0.57 | 0.92 | [DATA] OPEC 2024: over 57% of oil demand; oil is 92% of transport energy |
| Petrochemicals | 0.21 | 0.95 | Share [DATA]; dependence [ASSUMPTION] |
| Agriculture/Residential | 0.11 | 0.40 | [ASSUMPTION] |
| Industry | 0.07 | 0.45 | [ASSUMPTION] |
| Power | 0.04 | 0.10 | [ASSUMPTION] |

Inter-sector dependencies (e.g. Industry needs Transport 0.45) [ASSUMPTION].
A sector shuts down below **45%** of its normal inputs (smoothness 0.06)
[ASSUMPTION]; varying this from 30% to 60% moves the threshold only between 52.6%
and 53.1%. "Systemic" = the worst region loses more than **10%** of weighted output
[ASSUMPTION; An et al. use 50%].

## 9. Validation targets — [DATA]

**Not fed into the model.** Used only to check its output.

Observed flows, Q2 2026 (EIA Short-Term Energy Outlook, August 2026) [S16]:
Hormuz 4.9, Malacca 16.6, Cape of Good Hope 9.4, Bab el-Mandeb 8.1, Suez+SUMED 5.8,
Danish Straits 4.7, Turkish Straits 4.1, Panama 3.2 mb/d.

Hormuz is used to **set** the closure level (4.9 ÷ 20.9 = 23% open), so it is not
a test. The other passages are.

Crude share of each passage's oil traffic, used to compare crude with crude:
Hormuz ~73% [S16], Bab el-Mandeb ~72% [S1], Suez ~52% [S19], Panama ~5% [S20].

## 10. Modelling parameters defined in the code — [ASSUMPTION]

These are part of the model's structure rather than published data, so they are set in the
model files, not in `oil_model_data.py`:

| Parameter | Value | File |
|---|---|---|
| The 37 routes: chokepoints passed and voyage days | geographic estimates | `oil_network_model.py` (`ROUTES`) |
| Russia's Baltic route limit | 2.5 mb/d | `oil_network_model.py` (`ROUTES`) |
| Bid steepness | 4 (premium = 1 + 4 × (short/demand)²) | `oil_network_model.py` |
| Freight factor | 0.01 per voyage day | `oil_network_model.py` |
| Complexity uplift strength | up to 15% | `oil_network_model.py` |
| Refineries per region | 12 | `oil_network_model.py` |
| Tanker fleet slack | 25% | `oil_network_model.py` |
| Daily price adjustment | 12% of the gap to the clearing price | `price_dynamics.py`, `spr_depletion.py` |
| Price-feedback cap (extension) | 20% of demand | `experiment_feedback.py` |

## 11. Collected but not used

Persian Gulf crude grades (API gravity, sulphur), the heavy/medium/light
classification, and country-level production rankings were gathered for a
crude-grade-matching mechanism that was planned but **not built**. The model treats
all liquids as interchangeable; that is listed as a limitation.

---

## Sources

- **[S1]** EIA, *World Oil Transit Chokepoints* — https://www.eia.gov/
- **[S2]** IEA, *Strait of Hormuz* — https://www.iea.org/about/oil-security-and-emergency-response/strait-of-hormuz
- **[S4]** EIA, *World Oil Transit Chokepoints* (bypass pipelines) — https://www.eia.gov/
- **[S5]** EIA, *Weekly Petroleum Status Report*, SPR series — https://www.eia.gov/petroleum/weekly/
- **[S6]** DOE, *SPR Quick Facts* — https://www.energy.gov/hgeo/opr/spr-quick-facts
- **[S7]** Strategic Petroleum Reserve (United States) — https://en.wikipedia.org/wiki/Strategic_Petroleum_Reserve_(United_States)
- **[S8]** IEA, coordinated stock release, 11 March 2026
- **[S12]** EIA, *International Energy Statistics* — https://www.eia.gov/international/data/world
- **[S13]** Visual Capitalist / EIA, 2025 production ranking — https://www.visualcapitalist.com/ranked-worlds-biggest-producers-of-crude-oil/
- **[S16]** EIA, *Short-Term Energy Outlook* (Table 3b and 2026 editions) — https://www.eia.gov/outlooks/steo/
- **[S17]** Energy Institute, *Statistical Review of World Energy* 2024 — https://www.energyinst.org/statistical-review
- **[S18]** Oil & Gas Journal / EIA, Nelson Complexity Index
- **[S19]** IEA, Suez Canal oil flows (crude and products), 2023
- **[S20]** EIA / Kpler, Panama Canal petroleum traffic
- **[S21]** Visual Capitalist / EIA, *Charted: Where the World's Oil Comes From, by Region* (2025) — https://www.visualcapitalist.com/
- **[S22]** World Population Review, oil producing countries (Energy Institute data) — https://worldpopulationreview.com/country-rankings/oil-producing-countries
- **[S23]** Statbase, oil consumption by country 1965–2024 (Energy Institute data) — https://statbase.org/datasets/energy/oil-consumtion/
- **[S25]** List of countries by oil consumption (EIA data) — https://en.wikipedia.org/wiki/List_of_countries_by_oil_consumption
- Cooper, J.C.B. (2003). Price elasticity of demand for crude oil: estimates for 23 countries. *OPEC Review*.
- Ghouri, S.S. (2001). Oil demand in North America: 1980–2020. *OPEC Review*.

## Papers this project builds on

- **An, F., Ren, S., Liu, X., Liu, S. & Cui, J. (2026).** A Network-Cascade Framework
  for Short-Run Production Failure Under Maritime-Energy Chokepoint Disruption.
  *Mathematics*, 14(10), 1708. https://doi.org/10.3390/math14101708
- **Sharma, M. & Lau, H.C. (2026).** Securing the Flow: Maritime Energy Resilience
  under Correlated and Decision-Dependent Disruptions. arXiv:2605.11990.
- *Non-Substitutable Chokepoints and Global Supply Chain Disruption* (2026).
