"""
price_dynamics.py — price trajectory over time during a disruption
CITS4403 — Raed

Couples the two feedback loops so price becomes DYNAMIC rather than a static
equilibrium:
    shortage -> price up -> demand destroyed -> shortage eases   (negative)
    shortage -> hoarding -> effective demand up -> worse shortage (positive)
plus refinery shutdown/restart lags, which make the path matter.

The question: does price spike and settle, overshoot, or oscillate?
"""
import numpy as np
from oil_model_data import *
from oil_network_model import OilNetworkModel, REGION_DEMAND


def simulate_price(blockade, days=240, hoarding=True, reserve_days=0,
                   demand_policy=0.0):
    m = OilNetworkModel(hoarding=hoarding)
    price = 1.0
    destroyed = 0.0          # demand destroyed by high prices (closes the loop)
    hist = dict(price=[], unserved=[], demand=[], hoard=[])

    prev_price = 1.0
    for d in range(days):
        trend = price - prev_price          # recent price momentum
        prev_price = price
        unserved, _, _ = m.step(1.0 - blockade, price_trend=max(0.0, trend))
        short = sum(unserved.values())

        # strategic reserve covers part of the gap for a limited window
        if d < reserve_days:
            short = max(0.0, short - SPR_MAX_WITHDRAW)
        # policy-driven demand restraint
        short = max(0.0, short - sum(REGION_DEMAND.values()) * demand_policy)
        # CLOSE THE LOOP: demand already destroyed by price reduces the gap
        short = max(0.0, short - destroyed)

        # --- price adjusts toward the level that would clear the market ---
        base = sum(REGION_DEMAND.values())
        target = 1.0
        if short > 0:
            # invert the elasticity relation to find the clearing price
            avg_elast = np.mean([PRICE_ELASTICITY[r] for r in REGION_DEMAND])
            target = 1.0 + (short / base) / abs(avg_elast)
        # price moves gradually (markets adjust, not instantly)
        price += 0.12 * (target - price)
        price = float(np.clip(price, 1.0, 40.0))

        # --- demand responds to price (negative feedback) ---
        # constant-elasticity form: q = q0 * price^e  (e negative)
        destroyed = sum(REGION_DEMAND[r] * (1.0 - price ** PRICE_ELASTICITY[r])
                        for r in REGION_DEMAND)

        hist["price"].append(price)
        hist["unserved"].append(short)
        hist["demand"].append(base - destroyed)
        hist["hoard"].append(np.mean(list(m.order_mult.values())))
    return hist


if __name__ == "__main__":
    for b, lab in [(0.4, "40% blocked"), (0.7, "70% blocked"), (1.0, "full closure")]:
        h = simulate_price(b)
        p = h["price"]
        print(f"{lab:<15} peak price {max(p):5.2f}x  settles {p[-1]:5.2f}x  "
              f"peak day {int(np.argmax(p))}")
    print()
    print("Effect of interventions at full closure:")
    for lab, kw in [("none", {}),
                    ("reserve (60d)", dict(reserve_days=60)),
                    ("demand restraint 3%", dict(demand_policy=0.03)),
                    ("no hoarding", dict(hoarding=False))]:
        h = simulate_price(1.0, **kw)
        print(f"  {lab:<22} peak {max(h['price']):5.2f}x  final {h['price'][-1]:5.2f}x")
