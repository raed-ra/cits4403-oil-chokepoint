# Oil Chokepoint Model — Real-World Data & Sources
### CITS4403 Project (Option 2) — Raed

This document records every real-world figure used to calibrate the model, with
its source. All sources are publicly available and downloadable. The model is a
**stylised** representation calibrated to these aggregates — not a reconstruction
of every cargo movement (the same stance taken by the published Hormuz-cascade
paper, Zhang et al. 2026).

---

## 1. Strait of Hormuz flow
| Quantity | Value | Source |
|---|---|---|
| Total oil flow | 20 mb/d (2024–25) | EIA, IEA [S1,S2] |
| Crude + condensate | ~15 mb/d | EIA [S3] |
| Refined products | ~5.5 mb/d | EIA [S3] |
| Share of global consumption | ~20% | EIA, IER [S1,S2] |
| Saudi share of Hormuz exports | ~40% | IER [S3] |

## 2. Bypass capacity (limits on rerouting)
| Quantity | Value | Source |
|---|---|---|
| Max bypass (Saudi E-W + UAE ADCOP) | 3.5–5.5 mb/d | EIA [S2,S4] |
| Coverage of Hormuz flow | ~a quarter (max) | EIA [S4] |
| Gulf producers with **zero** bypass | Iraq, Kuwait, Qatar, Bahrain, Iran | EIA [S4] |

## 3. US Strategic Petroleum Reserve (reserve-release lever)
| Quantity | Value | Source |
|---|---|---|
| Pre-crisis level (Feb 2026) | 415.4 Mb | EIA WPSR [S5] |
| Current level (Sep 2026) | 285.0 Mb (lowest since 1982) | EIA/DOE [S5,S6] |
| Drawdown Feb→Sep 2026 | 130.5 Mb | EIA [S5] |
| Design capacity | 714 Mb | DOE [S6] |
| **Max withdrawal rate** | 2.7 mb/d | DOE [S7] |
| IEA coordinated release (11 Mar 2026) | 400 Mb (US share 172.2 Mb) | IEA [S8] |

## 4. Persian Gulf crude grades (the grade axis)
Gulf crude is overwhelmingly **medium-heavy sour**. API gravity and sulphur %:

| Grade | API | Sulphur % | Source |
|---|---|---|---|
| Arab Light | 33.0 | 1.8 | OILCOM [S9] |
| Arab Medium | 27.8 | 2.75 | S&P [S10] |
| Basrah Light | 31.4 | 2.74 | S&P Platts [S10] |
| Basrah Medium | 27.9 | 3.0 | S&P Platts [S10] |
| Basrah Heavy | 24.0 | 4.05 | S&P Platts [S10] |
| Iranian Heavy | ~30 | ~1.9 | [S11] |
| Dubai | 31.0 | 2.0 | [S11] |

Contrast (non-Gulf, reachable if strait closes — note how different):
| Grade | API | Sulphur % |
|---|---|---|
| WTI (US light sweet) | 39.6 | 0.24 |
| Brent | 38.0 | 0.37 |
| Venezuela Merey (heavy sour) | 16.0 | 2.5 |

Classification: heavy <25 API; medium 25–34; light >34. Sour if S >0.5%.
**Why this matters:** a refiner built for Gulf medium-sour cannot simply switch
to US light-sweet — that is the grade-matching constraint the model captures.

## 5. Production & consumption (2025, EIA)
Top producers (crude incl. condensate, mb/d): USA 13.59, Russia 9.89,
Saudi 9.56, Canada 4.94, China 4.34, Iraq 4.30, Brazil 3.74, Iran 3.30,
UAE 3.20, Kuwait 2.60. [S12,S13]

Top consumers (petroleum liquids, mb/d): USA 20.61, China 16.37, India 5.60,
Russia 3.60, Japan 3.30. [S12,S14]

World consumption ~102.8 mb/d (2024); ~105 mb/d demand (2025). [S14,S15]

---

## Sources (all publicly downloadable)
- **[S1]** EIA, World Oil Transit Chokepoints — https://www.eia.gov/
- **[S2]** IEA, Strait of Hormuz — https://www.iea.org/about/oil-security-and-emergency-response/strait-of-hormuz
- **[S3]** Institute for Energy Research, Persian Gulf Oil Exports & Hormuz — https://www.instituteforenergyresearch.org/
- **[S4]** EIA World Oil Transit Chokepoints (bypass capacity) — https://www.eia.gov/
- **[S5]** EIA Weekly Petroleum Status Report, SPR series WCSSTUS1 — https://www.eia.gov/petroleum/weekly/
- **[S6]** DOE SPR Quick Facts — https://www.energy.gov/hgeo/opr/spr-quick-facts
- **[S7]** DOE via Wikipedia SPR entry — https://en.wikipedia.org/wiki/Strategic_Petroleum_Reserve_(United_States)
- **[S8]** IEA coordinated release, 11 March 2026
- **[S9]** OILCOM crude profiles — https://www.oilcom.de/en/grades/
- **[S10]** S&P Global Platts, Iraq SOMO Basrah specs — https://www.spglobal.com/
- **[S11]** OilMonster / Middle East Insider crude grades — https://www.oilmonster.com/oil-grades
- **[S12]** EIA International Energy Statistics — https://www.eia.gov/international/data/world
- **[S13]** Visual Capitalist / EIA 2025 production ranking — https://www.visualcapitalist.com/ranked-worlds-biggest-producers-of-crude-oil/
- **[S14]** Worldometer / EIA world oil statistics — https://www.worldometers.info/oil/
- **[S15]** Statista / OPEC global crude demand — https://www.statista.com/statistics/271823/global-crude-oil-demand/

## Key papers this project builds on
- Zhang et al. (2026), "A Network-Cascade Framework for Short-Run Production
  Failure Under Maritime-Energy Chokepoint Disruption," *Mathematics* 14(10):1708.
  https://doi.org/10.3390/math14101708 — threshold cascade, edge inventories,
  operability bands; OECD ICIO data; finds critical blockade intensity.
- "Securing the Flow: Maritime Energy Resilience under Correlated and
  Decision-Dependent Disruptions," arXiv:2605.11990 (2026) — stochastic
  multi-commodity flow, 16-node network, EIA/UNCTAD/World Bank data.
- "Non-Substitutable Chokepoints and Global Supply Chain Disruption" (2026) —
  conceptual; **names the open gap** this project fills: route substitutability
  as a severity determinant, and comparing reserve release vs demand reduction
  vs diversification (their Proposition 6).
