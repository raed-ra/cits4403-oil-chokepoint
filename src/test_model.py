"""
test_model.py - correctness checks and boundary-case analysis
CITS4403 - Raed

Run from the src/ folder:   python test_model.py
(The notebook's section 0b runs this same file.)

Every check follows one pattern: set up a scenario, run the real model, and
compare the result with something we know must be true from OUTSIDE the code -
physics, arithmetic or common sense. Each check must be able to fail.

Four groups:
  1. CONSERVATION   nothing is created or lost, nothing exceeds a limit
  2. BOUNDARY       behaviour at the extremes (0%, 100%, empty reserves)
  3. MONOTONICITY   the model moves in the right direction
  4. EXCEPTIONAL    odd inputs do not crash, and results repeat exactly
"""

import numpy as np                                                    # isfinite, arange

from oil_model_data import (CHOKEPOINTS, SPR_CURRENT,
                            SPR_MAX_WITHDRAW, WORLD_CONSUMPTION,
                            PRICE_ELASTICITY)                         # constants the checks compare against
from oil_network_model import OilNetworkModel, REGION_DEMAND, ORIGIN_SUPPLY   # the network model
from production_cascade import run_production_cascade, operability           # Layer 3
from price_dynamics import simulate_price                                     # price over time
from spr_depletion import simulate_with_reserve, runway_days                  # reserves

PASS, FAIL = [], []                                   # names of checks that passed / failed


def check(name, condition, detail=""):
    """Record one check: `condition` True = PASS, False = FAIL. Print the result."""
    (PASS if condition else FAIL).append(name)        # add the name to the right list
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {name}" + (f"  — {detail}" if detail else ""))   # e.g. [PASS] name - detail


# ----------------------------------------------------------------------
# 1. CONSERVATION - nothing appears from nowhere or exceeds a physical limit
# ----------------------------------------------------------------------
def test_conservation():
    print("\n1. CONSERVATION CHECKS")

    m = OilNetworkModel()                             # fresh model
    delivered, used, want = m.allocate_flows(1.0)     # one day, Hormuz open

    check("delivered <= demand for every region",     # nobody receives more than they asked for
          all(delivered[r] <= want[r] + 1e-6 for r in delivered))   # (1e-6 allows for rounding)

    over = [c for c in used if CHOKEPOINTS[c][1] is not None          # passages WITH a capacity (canals, Hormuz)...
            and used[c] > CHOKEPOINTS[c][1] + 1e-6]                   # ...that carry more than it
    check("no canal exceeds its capacity", not over,
          f"violations: {over}" if over else "all within capacity")

    import oil_network_model as NM
    bad = []                                          # any route or pipeline over its limit
    for frac in (1.0, 0.5, 0.0):                      # open, half closed, fully closed
        mm = NM.OilNetworkModel()
        mm.allocate_flows(frac)                       # one day at that closure
        for k, f in mm.last_route_flow.items():       # each route's total flow (both stages)
            rc = NM.ROUTES[k][4]                      # its own limit, if it has one
            if rc is not None and f > rc + 1e-6:
                bad.append(f"{k} {f:.2f}>{rc}")
        for p, budget in NM.SHARED_PIPELINES.items(): # each shared pipeline
            used_p = sum(f for k, f in mm.last_route_flow.items() if k.startswith(p))   # all its legs together
            if used_p > budget + 1e-6:
                bad.append(f"{p} {used_p:.2f}>{budget}")
    check("no route or pipeline exceeds its own capacity", not bad,
          "violations: " + "; ".join(bad) if bad else "all within capacity")

    check("total delivered <= total supply",          # can't deliver oil nobody produced
          sum(delivered.values()) <= sum(ORIGIN_SUPPLY.values()) + 1e-6,
          f"{sum(delivered.values()):.1f} <= {sum(ORIGIN_SUPPLY.values()):.1f}")

    m2 = OilNetworkModel()
    for _ in range(50):
        u, _, _ = m2.step(0.5)                        # 50 days, Hormuz half open
    check("unserved demand is never negative", all(v >= 0 for v in u.values()))   # negative = got more than needed


# ----------------------------------------------------------------------
# 2. BOUNDARY CASES - behaviour at the extremes
# ----------------------------------------------------------------------
def test_boundaries():
    print("\n2. BOUNDARY CASES")

    m = OilNetworkModel()
    for _ in range(150):
        u_open, _, _ = m.step(1.0)                    # 150 days, Hormuz OPEN
    check("fully open strait: unserved is near zero", # a healthy system shows no shortage
          sum(u_open.values()) < 2.0, f"{sum(u_open.values()):.2f} mb/d")

    m = OilNetworkModel()
    for _ in range(150):
        u_shut, _, _ = m.step(0.0)                    # 150 days, Hormuz CLOSED
    total_demand = sum(REGION_DEMAND.values())
    check("fully closed strait: unserved <= total demand",   # can't lose more than the world uses
          sum(u_shut.values()) <= total_demand + 1e-6,
          f"{sum(u_shut.values()):.1f} <= {total_demand:.1f}")
    check("fully closed causes more damage than fully open",
          sum(u_shut.values()) > sum(u_open.values()))

    m = OilNetworkModel()
    _, used, _ = m.allocate_flows(0.0)                # one day, fully closed
    check("closed strait carries zero flow", used["Hormuz"] < 1e-9)   # the closure is really applied

    from production_cascade import reserve_hold_time
    from oil_model_data import REGIONAL_RESERVES, REGIONAL_DRAW_RATE
    h = simulate_with_reserve(1.0, days=400)          # 400 days: long enough for reserves to run out
    worst, exhausted = reserve_hold_time(1.0, days=400)   # which reserves ran dry, and on which day
    check("reserves drain to zero and never below",   # must actually empty, and never go negative
          min(h["reserve"]) >= 0 and len(exhausted) > 0,
          f"{len(exhausted)} regions emptied, lowest total {min(h['reserve']):.0f} Mb")

    import math
    off = {r: d - math.ceil(REGIONAL_RESERVES[r] / REGIONAL_DRAW_RATE[r])   # simulated day minus predicted day
           for r, d in exhausted.items()}                                     # predicted = volume / rate, rounded up
    check("reserves empty on the day volume / rate predicts",
          all(abs(x) <= 1 for x in off.values()),     # within one day
          ", ".join(f"{r} day {exhausted[r]}" for r in exhausted))

    h = simulate_price(0.0, days=50)                  # Hormuz fully OPEN (simulate_price takes the CLOSED share)
    check("price index never drops below 1.0 (guard on the clip)",   # guaranteed by the code's clip - a guard, not economics
          min(h["price"]) >= 1.0 - 1e-9)

    check("operability(0) == 0", abs(operability(0.0)) < 0.01)       # no inputs -> no output
    check("operability(1) ~ 1", operability(1.0) > 0.95)             # full inputs -> full output
    check("operability is monotonic in input",                       # more input never gives less output
          all(operability(x) <= operability(x + 0.05) + 1e-9
              for x in np.arange(0, 0.95, 0.05)))                    # tested in steps of 0.05

    sysl, out = run_production_cascade(1.0)           # full oil supply
    check("full supply -> no systemic loss", sysl < 0.01, f"{sysl:.3f}")

    sysl0, _ = run_production_cascade(0.0)            # no oil at all
    check("zero supply -> systemic loss bounded in [0,1]", 0 <= sysl0 <= 1.0,   # can't lose more than 100%
          f"{sysl0:.3f}")


# ----------------------------------------------------------------------
# 3. MONOTONICITY - does the model move in the right direction?
# ----------------------------------------------------------------------
def test_monotonicity():
    print("\n3. MONOTONICITY CHECKS")

    vals = []
    for f in [1.0, 0.8, 0.6, 0.4, 0.2, 0.0]:          # Hormuz 100% open ... 0% open
        m = OilNetworkModel()
        for _ in range(150):
            u, _, _ = m.step(f)
        vals.append(sum(u.values()))                  # world shortfall at each level
    check("damage increases (weakly) as closure increases",   # each value >= the one before
          all(vals[i] <= vals[i + 1] + 1e-6 for i in range(len(vals) - 1)),
          " -> ".join(f"{v:.1f}" for v in vals))

    h_no  = simulate_with_reserve(1.0, scale=0.0, days=150)   # reserves OFF (scale 0)
    h_yes = simulate_with_reserve(1.0, scale=1.0, days=150)   # reserves ON
    check("strategic reserves strictly reduce peak price",    # strictly lower - would FAIL if reserves did nothing
          max(h_yes["brent"]) < max(h_no["brent"]),
          f"{max(h_yes['brent']):.0f} < {max(h_no['brent']):.0f}")

    import oil_network_model as NM
    def unserved_at(extra):                           # world shortfall with `extra` mb/d of Saudi pipeline
        old = dict(NM.SHARED_PIPELINES)               # save the real budgets
        NM.SHARED_PIPELINES["SaudiPipe"] = old["SaudiPipe"] + extra
        try:
            m = NM.OilNetworkModel()
            for _ in range(150):
                u, _, _ = m.step(0.3)                 # Hormuz 70% closed
        finally:
            NM.SHARED_PIPELINES.update(old)           # always restore them
        return sum(u.values())
    base, more = unserved_at(0.0), unserved_at(3.0)   # normal pipeline vs +3 mb/d
    check("more bypass capacity never increases damage",
          more <= base + 1e-6, f"{more:.2f} <= {base:.2f}")

    losses = [run_production_cascade(a)[0] for a in [1.0, 0.8, 0.6, 0.4]]   # loss at 100%, 80%, 60%, 40% of oil
    check("systemic loss increases as supply falls",
          all(losses[i] <= losses[i + 1] + 1e-9 for i in range(len(losses) - 1)),
          " -> ".join(f"{v:.2f}" for v in losses))


# ----------------------------------------------------------------------
# 4. EXCEPTIONAL INPUTS - odd values must not crash or produce nonsense
# ----------------------------------------------------------------------
def test_exceptional():
    print("\n4. EXCEPTIONAL CASES")

    try:
        h = simulate_price(0.5, days=0)               # ask for zero days
        ok = (len(h["price"]) == 0)                   # should return an empty history
    except Exception as e:
        ok = False                                    # a crash counts as failure
    check("zero-length simulation handled", ok)

    orig = dict(PRICE_ELASTICITY)                     # save the real elasticities
    try:
        for r in PRICE_ELASTICITY:
            PRICE_ELASTICITY[r] = -0.001              # people almost ignore price: 1/e = 1000 could explode
        h = simulate_price(1.0, days=60)
        finite = all(np.isfinite(p) for p in h["price"])   # no infinity, no NaN
    finally:
        PRICE_ELASTICITY.update(orig)                 # always restore them
    check("extreme inelasticity gives finite prices", finite)

    m1 = OilNetworkModel(); m2 = OilNetworkModel()    # two models, side by side
    for _ in range(150):
        u1, _, _ = m1.step(0.3)                                       # Hormuz 70% closed
        u2, _, _ = m2.step(0.3, extra_closed={"Bab el-Mandeb": 0.0})  # same + Bab el-Mandeb shut
    check("closing a second chokepoint cannot help",
          sum(u2.values()) >= sum(u1.values()) - 1e-6,
          f"{sum(u2.values()):.1f} >= {sum(u1.values()):.1f}")

    def run_once():                                   # one identical run
        m = OilNetworkModel()
        for _ in range(100):
            u, _, _ = m.step(0.4)
        return sum(u.values())
    check("model is deterministic (reproducible results)",   # same input -> exactly the same output
          abs(run_once() - run_once()) < 1e-12)


if __name__ == "__main__":                            # runs when the file is run directly
    print("=" * 62)
    print("MODEL CORRECTNESS AND BOUNDARY-CASE TESTS")
    print("=" * 62)
    test_conservation()                               # group 1
    test_boundaries()                                 # group 2
    test_monotonicity()                               # group 3
    test_exceptional()                                # group 4
    print("\n" + "=" * 62)
    print(f"RESULT: {len(PASS)} passed, {len(FAIL)} failed")   # the summary line
    if FAIL:
        print("Failed checks:")
        for f in FAIL:
            print("  -", f)                           # name every failure
    print("=" * 62)
