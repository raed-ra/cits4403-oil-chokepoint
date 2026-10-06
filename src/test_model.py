"""
test_model.py — correctness checks and boundary-case analysis
CITS4403 — Raed

Establishes that the model behaves correctly, including at boundary and
exceptional conditions. Run with:   python src/test_model.py
(or `pytest src/test_model.py` if pytest is installed)

Checks fall into four groups:
  1. CONSERVATION   - nothing is created or destroyed incorrectly
  2. BOUNDARY       - behaviour at the extremes (0%, 100%, empty reserve)
  3. MONOTONICITY   - the model responds in the expected direction
  4. EXCEPTIONAL    - degenerate inputs do not crash or produce nonsense
"""

import numpy as np

from oil_model_data import (CHOKEPOINTS, HORMUZ_TOTAL_FLOW, SPR_CURRENT,
                            SPR_MAX_WITHDRAW, WORLD_CONSUMPTION,
                            PRICE_ELASTICITY)
from oil_network_model import OilNetworkModel, REGION_DEMAND, ORIGIN_SUPPLY
from production_cascade import run_production_cascade, operability
from price_dynamics import simulate_price
from spr_depletion import simulate_with_reserve, runway_days

PASS, FAIL = [], []


def check(name, condition, detail=""):
    (PASS if condition else FAIL).append(name)
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {name}" + (f"  — {detail}" if detail else ""))


# ----------------------------------------------------------------------
# 1. CONSERVATION
# ----------------------------------------------------------------------
def test_conservation():
    print("\n1. CONSERVATION CHECKS")

    m = OilNetworkModel()
    delivered, used, want = m.allocate_flows(1.0)

    # no region receives more than it asked for
    check("delivered <= demand for every region",
          all(delivered[r] <= want[r] + 1e-6 for r in delivered))

    # no chokepoint carries more than its capacity
    over = [c for c in used if used[c] > CHOKEPOINTS[c][1] + 1e-6]
    check("no chokepoint exceeds capacity", not over,
          f"violations: {over}" if over else "all within capacity")

    # total delivered cannot exceed total supply
    check("total delivered <= total supply",
          sum(delivered.values()) <= sum(ORIGIN_SUPPLY.values()) + 1e-6,
          f"{sum(delivered.values()):.1f} <= {sum(ORIGIN_SUPPLY.values()):.1f}")

    # unserved is never negative
    m2 = OilNetworkModel()
    for _ in range(50):
        u, _, _ = m2.step(0.5)
    check("unserved demand is never negative", all(v >= 0 for v in u.values()))


# ----------------------------------------------------------------------
# 2. BOUNDARY CASES
# ----------------------------------------------------------------------
def test_boundaries():
    print("\n2. BOUNDARY CASES")

    # strait fully OPEN -> system should be healthy
    m = OilNetworkModel()
    for _ in range(150):
        u_open, _, _ = m.step(1.0)
    check("fully open strait: unserved is near zero",
          sum(u_open.values()) < 2.0, f"{sum(u_open.values()):.2f} mb/d")

    # strait fully CLOSED -> damage is large but bounded by total demand
    m = OilNetworkModel()
    for _ in range(150):
        u_shut, _, _ = m.step(0.0)
    total_demand = sum(REGION_DEMAND.values())
    check("fully closed strait: unserved <= total demand",
          sum(u_shut.values()) <= total_demand + 1e-6,
          f"{sum(u_shut.values()):.1f} <= {total_demand:.1f}")
    check("fully closed causes more damage than fully open",
          sum(u_shut.values()) > sum(u_open.values()))

    # Hormuz capacity must actually be zero when closed
    m = OilNetworkModel()
    _, used, _ = m.allocate_flows(0.0)
    check("closed strait carries zero flow", used["Hormuz"] < 1e-9)

    # reserve: empty reserve must not go negative
    h = simulate_with_reserve(1.0, reserve_mb=0.0, days=50)
    check("empty reserve never goes negative", min(h["reserve"]) >= 0)

    # reserve runway matches the physical calculation
    expected = SPR_CURRENT / SPR_MAX_WITHDRAW
    check("reserve runway = volume / rate",
          abs(runway_days() - expected) < 1e-6, f"{runway_days():.0f} days")

    # price can never fall below the pre-crisis baseline
    h = simulate_price(0.0, days=50)
    check("price index never drops below 1.0", min(h["price"]) >= 1.0 - 1e-9)

    # operability band: boundary values
    check("operability(0) == 0", abs(operability(0.0)) < 0.01)
    check("operability(1) ~ 1", operability(1.0) > 0.95)
    check("operability is monotonic in input",
          all(operability(x) <= operability(x + 0.05) + 1e-9
              for x in np.arange(0, 0.95, 0.05)))

    # production cascade with full supply -> no loss
    sysl, out = run_production_cascade(1.0)
    check("full supply -> no systemic loss", sysl < 0.01, f"{sysl:.3f}")

    # production cascade with zero supply -> total loss, bounded at 1
    sysl0, _ = run_production_cascade(0.0)
    check("zero supply -> systemic loss bounded in [0,1]", 0 <= sysl0 <= 1.0,
          f"{sysl0:.3f}")


# ----------------------------------------------------------------------
# 3. MONOTONICITY  (does the model respond in the right direction?)
# ----------------------------------------------------------------------
def test_monotonicity():
    print("\n3. MONOTONICITY CHECKS")

    # more closure -> more unserved demand (weakly)
    vals = []
    for f in [1.0, 0.8, 0.6, 0.4, 0.2, 0.0]:
        m = OilNetworkModel()
        for _ in range(150):
            u, _, _ = m.step(f)
        vals.append(sum(u.values()))
    check("damage increases (weakly) as closure increases",
          all(vals[i] <= vals[i + 1] + 1e-6 for i in range(len(vals) - 1)),
          " -> ".join(f"{v:.1f}" for v in vals))

    # more bypass capacity -> less damage
    low = OilNetworkModel(); high = OilNetworkModel()
    # (bypass enters via chokepoint capacity; use reserve as the proxy lever)
    h_no = simulate_with_reserve(1.0, reserve_mb=0.0, days=150)
    h_yes = simulate_with_reserve(1.0, reserve_mb=SPR_CURRENT, days=150)
    check("a strategic reserve reduces peak price",
          max(h_yes["brent"]) <= max(h_no["brent"]) + 1e-6,
          f"{max(h_yes['brent']):.0f} <= {max(h_no['brent']):.0f}")

    # more supply available -> less systemic loss
    losses = [run_production_cascade(a)[0] for a in [1.0, 0.8, 0.6, 0.4]]
    check("systemic loss increases as supply falls",
          all(losses[i] <= losses[i + 1] + 1e-9 for i in range(len(losses) - 1)),
          " -> ".join(f"{v:.2f}" for v in losses))


# ----------------------------------------------------------------------
# 4. EXCEPTIONAL / DEGENERATE INPUTS
# ----------------------------------------------------------------------
def test_exceptional():
    print("\n4. EXCEPTIONAL CASES")

    # zero-day simulation should not crash
    try:
        h = simulate_price(0.5, days=0)
        ok = (len(h["price"]) == 0)
    except Exception as e:
        ok = False
    check("zero-length simulation handled", ok)

    # extreme elasticity must not produce infinite or NaN prices
    orig = dict(PRICE_ELASTICITY)
    try:
        for r in PRICE_ELASTICITY:
            PRICE_ELASTICITY[r] = -0.001          # almost perfectly inelastic
        h = simulate_price(1.0, days=60)
        finite = all(np.isfinite(p) for p in h["price"])
    finally:
        PRICE_ELASTICITY.update(orig)
    check("extreme inelasticity gives finite prices", finite)

    # closing an extra chokepoint must not reduce damage
    m1 = OilNetworkModel(); m2 = OilNetworkModel()
    for _ in range(150):
        u1, _, _ = m1.step(0.3)
        u2, _, _ = m2.step(0.3, extra_closed={"Bab el-Mandeb": 0.0})
    check("closing a second chokepoint cannot help",
          sum(u2.values()) >= sum(u1.values()) - 1e-6,
          f"{sum(u2.values()):.1f} >= {sum(u1.values()):.1f}")

    # determinism: identical inputs must give identical outputs
    def run_once():
        m = OilNetworkModel()
        for _ in range(100):
            u, _, _ = m.step(0.4)
        return sum(u.values())
    check("model is deterministic (reproducible results)",
          abs(run_once() - run_once()) < 1e-12)


if __name__ == "__main__":
    print("=" * 62)
    print("MODEL CORRECTNESS AND BOUNDARY-CASE TESTS")
    print("=" * 62)
    test_conservation()
    test_boundaries()
    test_monotonicity()
    test_exceptional()
    print("\n" + "=" * 62)
    print(f"RESULT: {len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("Failed checks:")
        for f in FAIL:
            print("  -", f)
    print("=" * 62)
