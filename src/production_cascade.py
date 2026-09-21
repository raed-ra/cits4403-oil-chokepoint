"""
production_cascade.py — downstream THRESHOLD CASCADE into the economy
CITS4403 — Raed

Replicates the structure of Zhang et al. (2026, Mathematics 14:1708):
a threshold-cascade framework with sector inventories and *smooth operability
bands*, used to find the BLOCKADE INTENSITY at which a localised chokepoint
shock becomes systemic production loss. They report a critical band of 32-46%.

Our version:
  - sectors weighted by real oil shares (IEA/OPEC/EIA)
  - each sector has an operability band: output falls smoothly as input drops,
    and the sector FAILS below a minimum operable level
  - sectors depend on each other (input-output style), so failure PROPAGATES
  - transport is the hub: 92% of its energy is oil and nearly every other
    sector needs it to move goods -> transport failure cascades widely

Extension beyond the paper: we compare the three real interventions
(reserve release, demand restraint, bypass capacity) by how much each shifts
the critical blockade intensity.
"""

import numpy as np
from oil_model_data import *

# --- sector oil shares (fraction of total oil demand) -------------- [S33-S35]
SECTORS = {
    "Transport":      0.57,   # OPEC 2024: >57% of global oil demand
    "Petrochemicals": 0.21,   # "non-energy uses" (feedstock)
    "Industry":       0.07,
    "Agri/Residential": 0.11,
    "Power":          0.04,
}

# How substitutable is oil in each sector? (1 = no substitute at all)
# Oil is 92% of transport energy -> essentially no substitute.
OIL_DEPENDENCE = {
    "Transport":      0.92,
    "Petrochemicals": 0.95,   # feedstock: cannot be substituted at all
    "Industry":       0.45,
    "Agri/Residential": 0.40,
    "Power":          0.10,   # power has many alternatives
}

# Inter-sector dependency: sector -> {supplier: how much it needs them}
# (simplified input-output structure)
DEPENDS_ON = {
    "Transport":        {},
    "Petrochemicals":   {"Transport": 0.30, "Power": 0.25},
    "Industry":         {"Transport": 0.45, "Petrochemicals": 0.35, "Power": 0.30},
    "Agri/Residential": {"Transport": 0.50, "Petrochemicals": 0.30},  # fertiliser
    "Power":            {"Transport": 0.20},
}

# Operability band: a sector keeps running (degraded) down to this input level;
# below it, the sector cannot operate at all.  (Zhang et al. use "smooth
# operability bands" - we use a logistic band rather than a hard cutoff.)
OPERABLE_MIN   = 0.45     # below 45% of normal input -> failure
BAND_SMOOTHNESS = 0.06    # width of the smooth transition


def operability(input_ratio):
    """Smooth operability band: output fraction given input fraction.

    Two effects combine:
      - PROPORTIONAL degradation: with 70% of its fuel a sector does ~70% of
        its work (an essential input with no substitute cannot be stretched).
      - CATASTROPHIC failure: below OPERABLE_MIN the sector cannot run at all
        (minimum technical operating level), smoothed rather than a hard step.
    """
    gate = 1.0 / (1.0 + np.exp(-(input_ratio - OPERABLE_MIN) / BAND_SMOOTHNESS))
    return float(np.clip(input_ratio, 0, 1) * gate)


def run_production_cascade(oil_available_fraction, max_rounds=50,
                           inventory_rounds=0):
    """Propagate an oil shortfall through the production network.

    oil_available_fraction : fraction of normal oil supply still delivered
    inventory_rounds       : sector inventories delay the onset of failure
    returns (systemic_output_loss, per-sector output)
    """
    output = {s: 1.0 for s in SECTORS}

    for rnd in range(max_rounds):
        new_output = {}
        for s in SECTORS:
            # 1. direct oil input to this sector
            oil_input = oil_available_fraction
            # a sector only suffers to the extent it depends on oil
            direct = 1.0 - OIL_DEPENDENCE[s] * (1.0 - oil_input)

            # 2. inputs from OTHER sectors (this is the cascade channel)
            upstream = 1.0
            for supplier, intensity in DEPENDS_ON[s].items():
                upstream -= intensity * (1.0 - output[supplier])
            upstream = max(0.0, upstream)

            # 3. the binding input is the worse of the two
            effective_input = min(direct, upstream)

            # 4. inventories delay failure in the early rounds
            if rnd < inventory_rounds:
                effective_input = min(1.0, effective_input + 0.2)

            new_output[s] = float(operability(effective_input))

        # converged?
        if max(abs(new_output[s] - output[s]) for s in SECTORS) < 1e-6:
            output = new_output
            break
        output = new_output

    # systemic loss, weighted by each sector's economic weight (oil share proxy)
    systemic = sum(SECTORS[s] * (1.0 - output[s]) for s in SECTORS)
    return systemic, output


def regional_cascade(blockade_intensity, supply_buffer=0.0):
    """Run the production cascade SEPARATELY for each region, using that
    region's actual shortfall from the network model.

    This is the key step: a Hormuz closure is not felt evenly. Asia loses a
    large share of its oil and its transport sector drops below the operability
    band; North America barely moves. Systemic loss is therefore concentrated.
    """
    from oil_network_model import OilNetworkModel, REGION_DEMAND
    m = OilNetworkModel()
    for _ in range(150):
        unserved, _, _ = m.step(1.0 - blockade_intensity)

    out = {}
    for r, short in unserved.items():
        relief = REGION_DEMAND[r] * supply_buffer
        net_short = max(0.0, short - relief)
        avail = 1.0 - net_short / REGION_DEMAND[r] if REGION_DEMAND[r] else 1.0
        sysl, sectors = run_production_cascade(avail)
        out[r] = dict(oil_available=avail, systemic_loss=sysl, sectors=sectors)
    return out


def critical_blockade_intensity(supply_buffer=0.0, threshold=0.10):
    """Find the blockade intensity at which systemic production loss exceeds
    `threshold` (10% of weighted output) - the paper's key quantity.

    supply_buffer: extra oil supply available from an intervention, as a
    fraction of Hormuz flow (reserves, demand restraint, bypass).
    """
    for b in np.linspace(0, 1.0, 51):
        res = regional_cascade(b, supply_buffer)
        # worst-affected region defines when the shock becomes systemic
        worst = max(v["systemic_loss"] for v in res.values())
        if worst > threshold:
            return b
    return None


if __name__ == "__main__":
    print("Sector oil shares:", SECTORS)
    print(f"Operability band: sectors fail below {OPERABLE_MIN:.0%} of input\n")

    print("Blockade intensity -> systemic production loss")
    print(f"{'blocked':>9}{'oil avail':>11}{'systemic loss':>15}   failed sectors")
    for b in [0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0]:
        avail = 1.0 - (HORMUZ_TOTAL_FLOW * b) / WORLD_CONSUMPTION
        sysl, out = run_production_cascade(avail)
        failed = [s for s, v in out.items() if v < 0.5]
        print(f"{b:>8.0%}{avail:>11.1%}{sysl:>15.1%}   {failed}")

    print("\n--- REGIONAL cascade (the shock is not felt evenly) ---")
    for b in [0.4, 0.6, 0.8, 1.0]:
        res = regional_cascade(b)
        line = "  ".join(f"{r}: {v['systemic_loss']:.0%}" for r, v in res.items())
        print(f"  blockade {b:>4.0%} | {line}")

    print("\n--- worst-affected region, sector by sector (full closure) ---")
    res = regional_cascade(1.0)
    worst = max(res, key=lambda r: res[r]["systemic_loss"])
    print(f"  {worst}: oil available {res[worst]['oil_available']:.0%}")
    for s, v in res[worst]["sectors"].items():
        flag = "  <-- FAILED" if v < 0.5 else ""
        print(f"    {s:<18} output {v:>6.1%}{flag}")

    crit = critical_blockade_intensity()
    print(f"\nCRITICAL BLOCKADE INTENSITY: {crit:.0%}" if crit else "\nno critical point found")
    print("(Zhang et al. 2026 report a critical band of 32-46%)")
