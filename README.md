# Chokepoint Disruption in the Global Oil Network

**CITS4403 Computational Modelling — Research Project**
Author: Raed (solo project, coordinator approved)

A network cascade model of the 2026 Strait of Hormuz closure, calibrated to
published data, used to locate the critical closure threshold and compare the
three real policy interventions.

## Research question

> As the fraction of Hormuz flow blocked increases, is there a **critical
> closure level** at which localised shortfall becomes systemic production
> failure — and which intervention (strategic reserve release, demand
> reduction, bypass capacity) most raises that threshold?

## Setup

```bash
pip install -r requirements.txt
jupyter notebook notebooks/main_analysis.ipynb
```

Then **Run All**. Total runtime approximately 3–5 minutes. Figures are written
to `figures/`.

## Repository structure

```
├── src/                      model code
│   ├── oil_model_data.py       all real-world constants + sources
│   ├── oil_network_model.py    routing, congestion, competitive allocation
│   ├── production_cascade.py   downstream sector cascade
│   ├── price_dynamics.py       price equilibrium + hoarding feedback
│   ├── spr_depletion.py        strategic reserve runway
│   ├── sensitivity.py          parameter sweeps
│   └── topology_comparison.py  network analysis vs ER/WS/BA null models
├── utils/paths.py            import helper for notebooks
├── data/DATA_AND_SOURCES.md  every figure used, with its source
├── notebooks/main_analysis.ipynb   the full analysis (run this)
├── figures/                  generated output
└── requirements.txt
```

Each module also runs standalone: `python src/spr_depletion.py`.

## Changing parameters

All real-world constants live in `src/oil_model_data.py`. Edit there and re-run
the notebook — no notebook changes needed.

## Data

Calibrated to EIA, IEA, DOE, S&P Global Platts, Oil & Gas Journal, and
published elasticity estimates (Cooper 2003; Ghouri 2001; EIA working papers).
Full list with links in `data/DATA_AND_SOURCES.md`.

Validation: the model reproduces observed EIA Q2 2026 chokepoint flows
(Hormuz 5.0 vs 4.9 observed; Malacca 16.7 vs 16.6 observed) and the observed
Brent price move.

## Main findings

1. Critical blockade intensity ~54% (An et al. 2026 report 32–46%).
2. Correlated chokepoint failure (Hormuz + Bab el-Mandeb) roughly triples damage.
3. Price-mediated contagion: North America loses supply despite ~2.5% Hormuz
   exposure, because Asia outbids it for Atlantic crude.
4. Strategic reserve runway is rate-limited at ~105 days regardless of severity.
5. Demand destruction falls on the most price-elastic regions.
6. Topology alone does not explain vulnerability — capacity concentration does.
7. Oscillating disruption does ~40% more damage than a smooth ramp of equal
   total exposure.

## Honest limitations

Routes are constructed from geography rather than bilateral trade data; the
operability band and price adjustment speed are our calibration choices;
regional refinery complexity values are estimated; refinery shutdown hysteresis
is implemented but never activates in the scenarios tested. See section 10 of
the notebook.

## Literature

- An et al. (2026), *A Network-Cascade Framework for Short-Run Production
  Failure Under Maritime-Energy Chokepoint Disruption*, Mathematics 14(10):1708.
- Sharma & Lau (2026), *Securing the Flow*, arXiv:2605.11990.
- *Non-Substitutable Chokepoints and Global Supply Chain Disruption* (2026).
