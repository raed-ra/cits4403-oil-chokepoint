"""
production_cascade.py - Layer 3: how an oil shortfall spreads through the economy,
plus the main experiments (the threshold, interventions, reserve hold time).
CITS4403 - Raed

Follows the structure of the threshold-cascade framework of An et al. (2026,
Mathematics 14:1708): sectors with "operability bands", linked so that one
sector's failure reduces the next sector's inputs. Used to find the closure
level at which a local oil shortage becomes SYSTEMIC production failure.

Main functions
  operability()                  input share -> output share for one sector
  run_production_cascade()       spread a shortfall through the 5 sectors
  regional_cascade()             run the network, then the cascade, per region
  critical_blockade_intensity()  the threshold, found by bisection
  compare_interventions()        bypass vs demand restraint vs reserves
  reserve_hold_time()            how long reserves keep the system below systemic
"""

import numpy as np                      # maths: exp, clip
from oil_model_data import *            # model constants

# Each sector's share of world oil use - also used as its WEIGHT in the loss.
SECTORS = {
    "Transport":      0.57,   # OPEC 2024: >57% of global oil demand
    "Petrochemicals": 0.21,   # oil used as raw material (plastics, chemicals)
    "Industry":       0.07,   # manufacturing
    "Agri/Residential": 0.11, # farming and heating
    "Power":          0.04,   # electricity generation
}

# How much of each sector's energy comes from oil (1 = no substitute at all).
OIL_DEPENDENCE = {
    "Transport":      0.92,   # oil is 92% of transport energy
    "Petrochemicals": 0.95,   # oil is the feedstock itself
    "Industry":       0.45,   # can partly use gas, coal, electricity
    "Agri/Residential": 0.40,
    "Power":          0.10,   # power has many alternatives
}

# How much each sector needs the OTHER sectors (a simple input-output table).
# e.g. Industry needs Transport 0.45, Petrochemicals 0.35, Power 0.30.
DEPENDS_ON = {
    "Transport":        {},                                                   # needs nothing from the others
    "Petrochemicals":   {"Transport": 0.30, "Power": 0.25},
    "Industry":         {"Transport": 0.45, "Petrochemicals": 0.35, "Power": 0.30},
    "Agri/Residential": {"Transport": 0.50, "Petrochemicals": 0.30},          # fertiliser comes from petrochemicals
    "Power":            {"Transport": 0.20},
}

OPERABLE_MIN   = 0.45     # [ASSUMPTION] a sector shuts down below ~45% of its normal inputs
BAND_SMOOTHNESS = 0.06    # [ASSUMPTION] how gradual that shutdown is (smaller = sharper)


def operability(input_ratio):
    """Turn a sector's input share (0..1) into its output share (0..1).

    Two effects multiplied together:
      input_ratio  proportional: 70% of the inputs gives about 70% of the output
      gate         an S-curve that is ~1 above OPERABLE_MIN and ~0 below it:
                   below a minimum, the sector cannot operate at all
    """
    gate = 1.0 / (1.0 + np.exp(-(input_ratio - OPERABLE_MIN) / BAND_SMOOTHNESS))   # the S-shaped on/off switch
    return float(np.clip(input_ratio, 0, 1) * gate)                                # proportional output x switch


def run_production_cascade(oil_available_fraction, max_rounds=50,
                           inventory_rounds=0):
    """Spread an oil shortfall through the five sectors until it settles.

    oil_available_fraction  share of the region's oil need that is met (0..1)
    inventory_rounds        rounds in which stocks soften the hit (0 = not used)
    Returns (systemic loss, output of each sector).
    """
    output = {s: 1.0 for s in SECTORS}                    # start: every sector at full output

    for rnd in range(max_rounds):                         # repeat until nothing changes (fixed-point iteration)
        new_output = {}                                   # this round's outputs
        for s in SECTORS:                                               # for each of the 5 sectors
            oil_input = oil_available_fraction            # how much of its oil this sector gets
            direct = 1.0 - OIL_DEPENDENCE[s] * (1.0 - oil_input)   # damage from its OWN oil shortage

            upstream = 1.0                                # start with full supply from other sectors...
            for supplier, intensity in DEPENDS_ON[s].items():           # each sector it depends on, and how much
                upstream -= intensity * (1.0 - output[supplier])   # ...minus damage from each supplier that has failed
            upstream = max(0.0, upstream)                 # can't go below zero

            effective_input = min(direct, upstream)       # the WORSE of the two limits it

            if rnd < inventory_rounds:                    # optional: stocks soften early rounds (off by default)
                effective_input = min(1.0, effective_input + 0.2)       # stocks soften the hit (only if inventory_rounds > 0; off by default)

            new_output[s] = float(operability(effective_input))   # inputs -> output through the gate

        if max(abs(new_output[s] - output[s]) for s in SECTORS) < 1e-6:   # settled? (nothing moved)
            output = new_output                                         # not settled: these outputs become next round's inputs
            break                                         # stop iterating
        output = new_output                               # otherwise use these outputs as next round's inputs

    systemic = sum(SECTORS[s] * (1.0 - output[s]) for s in SECTORS)   # SYSTEMIC LOSS: weighted lost output
    return systemic, output                                             # (systemic loss, each sector's output)


def regional_cascade(blockade_intensity, supply_buffer=0.0, intervention=None):
    """Run the network to steady state, then the sector cascade for EACH region.

    blockade_intensity  share of Hormuz CLOSED (0..1)
    intervention        optional {"bypass_extra": mb/d, "demand_cut": share,
                        "reserve_scale": multiplier} - each through its real channel
    Returns {region: {oil_available, systemic_loss, sectors}}.
    """
    import oil_network_model as NM                        # the network model
    from oil_model_data import REGIONAL_DRAW_RATE         # reserve draw rates
    iv = intervention or {}                               # no intervention = empty dict
    old_pipes, old_demand = dict(NM.SHARED_PIPELINES), dict(NM.REGION_DEMAND)   # save originals so we can restore them
    try:                                                                # change things temporarily...
        NM.SHARED_PIPELINES["SaudiPipe"] = old_pipes["SaudiPipe"] + iv.get("bypass_extra", 0.0)   # BYPASS: a bigger Saudi pipeline
        cut = iv.get("demand_cut", 0.0)                   # DEMAND RESTRAINT: share every region cuts
        for r in NM.REGION_DEMAND:                                      # every region
            NM.REGION_DEMAND[r] = old_demand[r] * (1.0 - cut)   # applied inside the network, so freed oil can move
        m = NM.OilNetworkModel()                          # fresh model for this scenario
        for _ in range(150):                              # run 150 days to steady state
            unserved, _, _ = m.step(1.0 - blockade_intensity)   # step() takes the OPEN share, so 1 - closed
        demand = dict(NM.REGION_DEMAND)                   # demand used in this run
    finally:                                                            # ...and ALWAYS put them back, even after an error
        NM.SHARED_PIPELINES.update(old_pipes)             # always put the originals back
        NM.REGION_DEMAND.update(old_demand)                             # restore demand

    out = {}                                                            # results, one entry per region
    for r, short in unserved.items():                     # for each region's shortfall...
        relief = demand[r] * supply_buffer                # optional generic buffer (0 by default)
        rate = REGIONAL_DRAW_RATE.get(r, 0.0) * iv.get("reserve_scale", 0.0)   # RESERVES: own reserve's draw rate
        relief += min(short, rate)                        # a reserve can't cover more than the shortfall
        net_short = max(0.0, short - relief)              # what is still missing
        avail = 1.0 - net_short / demand[r] if demand[r] else 1.0   # share of oil need met
        sysl, sectors = run_production_cascade(avail)     # spread it through the economy
        out[r] = dict(oil_available=avail, systemic_loss=sysl, sectors=sectors)  # store this region's results
    return out                                                          # every region's oil_available, systemic loss and sectors


def critical_blockade_intensity(supply_buffer=0.0, threshold=0.10, intervention=None,
                                precision_steps=12):
    """THE THRESHOLD: the share of Hormuz closed at which the worst-hit region
    first loses more than 10% of its weighted output.

    Found by BISECTION: start with 0..1, test the middle, keep the half that
    contains the answer, repeat 12 times (precision ~0.02%). Valid because
    damage only rises as closure rises (checked in test_model.py).
    Returns None if even full closure stays below the threshold.
    """
    def worst(b):                                         # worst region's systemic loss at closure b
        res = regional_cascade(b, supply_buffer, intervention)          # run the network + Layer 3 at closure b
        return max(v["systemic_loss"] for v in res.values())            # the WORST region's systemic loss
    if worst(1.0) <= threshold:                           # even fully closed isn't systemic?
        return None                                       # then there is no threshold
    lo, hi = 0.0, 1.0                                     # the answer lies between 0% and 100% closed
    for _ in range(precision_steps):                                    # halve the range 12 times
        mid = 0.5 * (lo + hi)                             # test the middle
        if worst(mid) > threshold:                        # already systemic here?
            hi = mid                                      # then the threshold is at or below mid
        else:
            lo = mid                                      # otherwise it's above mid
    return hi                                             # the first closure found to be systemic


def compare_interventions():
    """How far each real intervention raises the threshold.
      equal size (~3 mb/d each) -> which is most effective per barrel?
      realistic size             -> which helps most in practice?
    """
    from oil_model_data import REGIONAL_DRAW_RATE                       # reserve draw rates
    total_rate = sum(REGIONAL_DRAW_RATE.values())         # all regions' reserve draw rates together (~11 mb/d)
    cases = [                                             # (label, size group, intervention)
        ("Baseline",                       "-",         {}),            # the reference: no intervention
        ("Bypass +3 mb/d",                 "equal",     dict(bypass_extra=3.0)),  # Saudi pipeline 7 -> 10 mb/d
        ("Demand restraint 2.9%",          "equal",     dict(demand_cut=3.0 / 102.0)),          # 2.9% of ~102 = 3 mb/d
        ("Reserves at 3 mb/d total",       "equal",     dict(reserve_scale=3.0 / total_rate)),  # scale rates down to 3 mb/d
        ("Bypass +2 mb/d",                 "realistic", dict(bypass_extra=2.0)),  # Saudi pipeline 7 -> 9 mb/d
        ("Demand restraint 3%",            "realistic", dict(demand_cut=0.03)),  # every region uses 3% less
        ("Reserves, realistic ~11 mb/d",   "realistic", dict(reserve_scale=1.0)),  # every reserve at its full draw rate
        ("All three combined",             "realistic", dict(bypass_extra=2.0, reserve_scale=1.0,
                                                             demand_cut=0.03)),
    ]
    rows, base = [], None                                               # results; base = the baseline threshold
    for name, size, iv in cases:                                        # each case in turn
        c = critical_blockade_intensity(intervention=iv)  # the threshold with this intervention
        base = c if base is None else base                # the first case (baseline) is the reference
        rows.append(dict(name=name, size=size, threshold=c, shift=c - base))   # how far it moved
    return rows                                                         # one row per case: name, size, threshold, shift


def explain_cascade(oil_available_fraction):
    """Every step of the sector cascade for one region, for display and teaching.

    Runs run_production_cascade() to get the settled outputs, then recomputes
    each intermediate quantity with the SAME formulas, so you can see why each
    sector ends where it does.
    Returns ({sector: {direct, upstream, effective, gate, output, weight, loss}},
             systemic loss).
    """
    systemic, out = run_production_cascade(oil_available_fraction)   # settled outputs
    rows = {}                                                           # one row per sector
    for s in SECTORS:                                                   # for each of the 5 sectors
        direct = 1.0 - OIL_DEPENDENCE[s] * (1.0 - oil_available_fraction)   # left after its OWN oil shortage
        upstream = 1.0                                                       # left after its SUPPLIERS' failures...
        for supplier, intensity in DEPENDS_ON[s].items():               # each supplier sector...
            upstream -= intensity * (1.0 - out[supplier])                    # ...each supplier's loss x how much it's needed
        upstream = max(0.0, upstream)                                   # never below zero
        effective = min(direct, upstream)                                    # the worse of the two
        gate = 1.0 / (1.0 + np.exp(-(effective - OPERABLE_MIN) / BAND_SMOOTHNESS))   # the shutdown switch
        rows[s] = dict(direct=direct, upstream=upstream, effective=effective, gate=gate,  # everything for this sector
                       output=out[s], weight=SECTORS[s], loss=SECTORS[s] * (1.0 - out[s]))
    return rows, systemic                                               # (the table, systemic loss)


if __name__ == "__main__":                                # only when run directly
    print("Sector oil shares:", SECTORS)
    print(f"Operability band: sectors fail below {OPERABLE_MIN:.0%} of input\n")

    print("\n--- REGIONAL cascade (the shock is not felt evenly) ---")
    for b in [0.4, 0.6, 0.8, 1.0]:                        # a few closure levels
        res = regional_cascade(b)
        line = "  ".join(f"{r}: {v['systemic_loss']:.0%}" for r, v in res.items())
        print(f"  blockade {b:>4.0%} | {line}")

    print("\n--- worst-affected region, sector by sector (full closure) ---")
    res = regional_cascade(1.0)
    worst = max(res, key=lambda r: res[r]["systemic_loss"])   # the hardest-hit region
    print(f"  {worst}: oil available {res[worst]['oil_available']:.0%}")
    for s, v in res[worst]["sectors"].items():
        flag = "  <-- FAILED" if v < 0.5 else ""
        print(f"    {s:<18} output {v:>6.1%}{flag}")

    crit = critical_blockade_intensity()
    print(f"\nCRITICAL BLOCKADE INTENSITY: {crit:.0%}" if crit else "\nno critical point found")
    print("(An et al. 2026 report a critical band of 32-46%)")


def reserve_hold_time(blockade, days=400):
    """How long realistic regional reserves keep a closure below systemic.

    Day by day, each region draws only on its OWN reserve. Records the worst
    region's systemic loss each day and the day each reserve runs out.
    Returns (list of daily worst loss, {region: day its reserve ran out}).
    """
    import oil_network_model as NM                                      # the network model
    from oil_model_data import REGIONAL_RESERVES, REGIONAL_DRAW_RATE    # reserves and draw rates
    m = NM.OilNetworkModel()                              # fresh model
    left = dict(REGIONAL_RESERVES)                        # each region's reserve remaining, Mb
    worst, exhausted = [], {}                             # daily worst loss; day each reserve emptied
    for d in range(1, days + 1):                          # one loop = one day
        unserved, _, _ = m.step(1.0 - blockade)           # today's shortfalls (step takes the OPEN share)
        w = 0.0                                           # worst loss today
        for r, miss in unserved.items():                                # each region's shortfall today
            draw = min(miss, REGIONAL_DRAW_RATE.get(r, 0.0), max(0.0, left.get(r, 0.0)))   # draw: need, rate limit, what's left
            left[r] = left.get(r, 0.0) - draw             # 1 mb/d for 1 day = 1 Mb out of the reserve
            if REGIONAL_RESERVES.get(r, 0) > 0 and left[r] <= 0.01 and r not in exhausted:  # first day this reserve is empty?
                exhausted[r] = d                          # record the first day it ran dry
            net = max(0.0, miss - draw)                   # shortfall after the reserve
            w = max(w, run_production_cascade(1.0 - net / NM.REGION_DEMAND[r])[0])   # that region's systemic loss
        worst.append(w)                                   # keep today's worst
    return worst, exhausted                                             # (daily worst loss, day each reserve ran out)
