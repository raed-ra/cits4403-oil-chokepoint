# Chokepoint Disruption in the Global Oil Network

**CITS4403 Computational Modelling — Research Project**
Author: Raed (solo project, coordinator approved)

A network cascade model of the 2026 Strait of Hormuz closure. Ten world regions
trade oil over 37 routes through eight maritime chokepoints; a closure's shortfall
is passed into a five-sector production model to find the point at which a local
oil shortage becomes systemic production failure, and to compare real
interventions.

## Research question

> As the fraction of Hormuz flow blocked increases, is there a **critical closure
> level** at which localised shortfall becomes systemic production failure — and
> which intervention (strategic reserve release, demand restraint, bypass capacity)
> most raises that threshold?

## Setup

```bash
pip install -r requirements.txt
python src/test_model.py                      # 25 correctness checks - all should pass
jupyter notebook notebooks/main_analysis.ipynb
```

Then **Restart and Run All**. The full run takes about **10–15 minutes** (the
11 × 11 closure grid and the intervention comparison are the slow parts).
Figures are written to `figures/`.

## Repository structure

```
├── src/
│   ├── oil_model_data.py        every number the model uses, marked [DATA] or [ASSUMPTION]
│   ├── oil_network_model.py     Layers 1-2: routes, daily allocation, market price
│   ├── production_cascade.py    Layer 3: sector cascade; threshold; interventions
│   ├── price_dynamics.py        price path over time
│   ├── spr_depletion.py         regional strategic reserves
│   ├── network_view.py          node and edge tables, network maps
│   ├── closure_sensitivity.py   Hormuz x Bab el-Mandeb closure grid
│   ├── sensitivity.py           parameter sweeps, path dependence
│   ├── topology_comparison.py   network metrics vs ER / WS / BA null models
│   ├── layer_diagrams.py        Layers 2 and 3 drawn as networks
│   ├── experiment_feedback.py   experimental extension: price feedback
│   ├── trace_model.py           step-by-step printout of one scenario (python trace_model.py 0.7)
│   ├── debug_trace.py           debugger-style trace of the real program -> PROGRAM_TRACE.md
│   └── test_model.py            25 correctness and boundary-case checks
├── utils/paths.py               lets the notebook find src/ and figures/
├── HOW_THE_PROGRAM_RUNS.md      walkthrough of one run, function by function
├── PROGRAM_TRACE.md             every push of one simulated day (made by debug_trace.py)
├── data/DATA_AND_SOURCES.md     every figure used, with its source
├── notebooks/main_analysis.ipynb   the full analysis (run this)
├── figures/                     generated output
└── requirements.txt
```

Each module also runs on its own, e.g. `python src/network_view.py`.
Published data and the main assumptions live in `src/oil_model_data.py`: change one there
and re-run. The route network (which routes exist, the chokepoints each passes, voyage days)
and a few behavioural parameters (bid steepness 4, freight factor 0.01, complexity uplift
0.15, 12 refineries per region, 25% tanker slack, 12% daily price adjustment) are defined in
the model files, as part of the model's structure.

## Main findings

1. **Critical closure ≈ 53%.** The worst-hit region first loses 10% of its output
   when 53% of Hormuz is blocked. Robust to the sector-shutdown assumption
   (52.6–53.1%); 51% without the refinery-complexity proxy. An et al. (2026) report
   32–46% using a different definition of failure. The value moved between 38% and
   56% across structural revisions of the model, so treat it as this model's
   estimate rather than a property of the world.
2. **Which intervention raises the threshold most.** Per barrel (~3 mb/d each):
   bypass capacity +14 points, demand restraint +7, reserves +5. At realistic
   sizes: reserves +19, but only until regional stocks run out (at 71% closure,
   China's on day 350); bypass +10 and restraint +7 are permanent. All three: +38.
3. **Damage is confined to Asia.** At full closure Other Asia loses 67% of its
   demand and China 37%; Europe, India and North America remain fully supplied.
4. **Correlated failure.** Closing Bab el-Mandeb as well as 70% of Hormuz raises
   unserved demand by 49% (6.6 → 9.9 mb/d): the main Hormuz bypass, the Saudi
   East-West pipeline, exits through the Red Sea.
5. **Reserves are in the wrong place.** At full closure, day 100: Brent ~$236 with
   no reserves, ~$151 with realistic regional reserves, ~$81 if all could be pooled.
   About 500 Mb (US, Europe, India) is never drawn.
6. **The real network is more robust than random graphs** of the same size:
   removing its most central chokepoint costs 5.6% of capacity against 12–24% (averages over 200 random graphs).
7. **Volatility matters.** On-off disruption does ~31% more damage than a smooth
   ramp with the same total exposure; the order of events alone makes no difference.

## Extension (experimental): price feedback

`src/experiment_feedback.py` (notebook section 9c) fixes the main limitation: demand cut by
high prices is returned to the market, and price-driven cuts count as lost oil. The
threshold rises from 53% to 64% and the worst region's loss at full closure falls from 89%
to 23% - the shortage is shared by every region instead of being concentrated in Asia.
This takes about a month to happen: in the first weeks the shortage is still concentrated in
Asia, so 53% describes the start of a closure and 64% the situation once markets adjust.
Robust to the cut cap (20-30%).

## Validation

- **Not a test:** Hormuz flow (4.9 mb/d) is set from the observed Q2 2026 value.
- **Corridors the model works out itself**, Q2 2026: Bab el-Mandeb 7.0 vs 8.1
  observed, Suez 3.6 vs 5.8, Malacca 9.9 vs 16.6. The direction of rerouting is
  right; the size is under-predicted, mainly because refined products are not
  modelled.
- **Price:** at the Q2 2026 closure the model gives $94 with full reserves and
  $143 with none; the observed ~$105 lies inside that bracket.
- **Retracted finding:** an earlier claim that North America was hurt by
  "contagion" was an artefact of mixing crude-only production with total-liquids
  consumption. North America is a net exporter.

## Limitations

Routes are built from geography, not bilateral trade data. Allocation is a single
greedy pass, not a market equilibrium, and there is no price feedback into routing:
demand cut by high prices is never offered to other buyers, so damage is concentrated in
Asia more than it would be in reality. All liquids are treated as interchangeable
(no refined products, no crude grades). Regional production uses 2025 data and
consumption 2024 data, and several regional consumption totals are estimates (how each
figure was obtained is set out in `data/DATA_AND_SOURCES.md`). Several parameters are assumptions (see
`data/DATA_AND_SOURCES.md`). Hoarding and redistribution friction are implemented
but switched off; refinery shutdown triggers only at deep closures, and never changes the result. Full list in
section 10 of the notebook.

## Literature

- An, F., Ren, S., Liu, X., Liu, S. & Cui, J. (2026). A Network-Cascade Framework
  for Short-Run Production Failure Under Maritime-Energy Chokepoint Disruption.
  *Mathematics*, 14(10), 1708. https://doi.org/10.3390/math14101708
- Sharma, M. & Lau, H.C. (2026). Securing the Flow: Maritime Energy Resilience under
  Correlated and Decision-Dependent Disruptions. arXiv:2605.11990.
- *Non-Substitutable Chokepoints and Global Supply Chain Disruption* (2026).
