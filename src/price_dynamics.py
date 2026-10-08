"""
price_dynamics.py - the oil price over time during a disruption
CITS4403 - Raed

Each simulated day: run the network, measure the world shortfall, find the
price that would clear the market, and move the actual price 12% of the way
toward it (markets adjust gradually, not instantly).

The demand response is inside clear_market(): as price rises, demand falls
with each region's price elasticity. Hoarding (a second, positive feedback)
can be switched on but is OFF by default.
"""
import numpy as np                                            # maths: clip, mean, argmax
from oil_model_data import *                                  # constants (elasticities, reserve figures)
from oil_network_model import OilNetworkModel, REGION_DEMAND  # the network model


def simulate_price(blockade, days=240, hoarding=False, reserve_days=0,
                   demand_policy=0.0):
    """Price path, day by day.

    blockade       share of Hormuz CLOSED (0..1)
    reserve_days   for this many days, take 2.7 mb/d off the shortfall
                   (a simple single-reserve option; the regional version is in
                   spr_depletion.py)
    demand_policy  share of world demand cut by policy (e.g. 0.03 = 3%)
    Returns a dict of daily lists: price, unserved, demand, hoard.
    """
    m = OilNetworkModel(hoarding=hoarding)          # fresh model for this scenario
    price = 1.0                                     # price index: 1.0 = pre-crisis ($69)
    destroyed = 0.0                                 # demand destroyed by high prices, mb/d
    hist = dict(price=[], unserved=[], demand=[], hoard=[])   # what we record each day

    prev_price = 1.0                                # yesterday's price (for the price trend)
    for d in range(days):                           # one loop = one day
        trend = price - prev_price                  # how fast price is rising (only used by hoarding)
        prev_price = price                          # remember today's price for tomorrow
        unserved, _, _ = m.step(1.0 - blockade, price_trend=max(0.0, trend))   # run the network (step takes the OPEN share)
        short = sum(unserved.values())              # total world shortfall today

        if d < reserve_days:                        # optional single reserve, for a limited window
            short = max(0.0, short - SPR_MAX_WITHDRAW)
        short = max(0.0, short - sum(REGION_DEMAND.values()) * demand_policy)   # optional demand restraint

        # The price that would make demand equal supply. clear_market() already
        # includes the demand response, so the physical shortfall goes in directly.
        # (An earlier version subtracted destroyed demand first, counting it twice.)
        base = sum(REGION_DEMAND.values())          # normal world demand
        target, _ = m.clear_market(base - short)    # supply available = demand - shortfall
        price += 0.12 * (target - price)            # move 12% of the way toward it each day
        price = float(np.clip(price, 1.0, 40.0))    # never below pre-crisis, never above 40x

        destroyed = sum(REGION_DEMAND[r] * (1.0 - price ** PRICE_ELASTICITY[r])   # demand lost at this price
                        for r in REGION_DEMAND)

        hist["price"].append(price)                 # record the day
        hist["unserved"].append(short)
        hist["demand"].append(base - destroyed)
        hist["hoard"].append(np.mean(list(m.order_mult.values())))   # average hoarding multiplier (1.0 when off)
    return hist


def shortage_two_views(blockade, days=150):
    """The same shortage seen two ways, at one closure level (share CLOSED).

    physical  oil each region could not obtain - from the routing (Layer 1)
    priced    how much each region would cut at the market-clearing price (Layer 2)

    The totals are equal by construction: the price is chosen so that the cuts
    add up to the shortfall. The split between regions is NOT the same, because
    the cuts are never fed back into the routing (a limitation of the model).
    Returns (price index, {region: (demand, physical shortfall, price-driven cut)}).
    """
    m = OilNetworkModel()                                   # fresh model
    for _ in range(days):
        unserved, _, _ = m.step(1.0 - blockade)             # settle the routing (step takes the OPEN share)
    short = sum(unserved.values())                          # total physical shortfall
    price, demand = m.clear_market(sum(REGION_DEMAND.values()) - short)   # price that removes that much demand
    return price, {r: (REGION_DEMAND[r], unserved[r], REGION_DEMAND[r] - demand[r])
                   for r in REGION_DEMAND}


if __name__ == "__main__":                          # only when run directly
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
                    ("no hoarding", dict(hoarding=False))]:   # (hoarding is off by default, so this equals "none")
        h = simulate_price(1.0, **kw)
        print(f"  {lab:<22} peak {max(h['price']):5.2f}x  final {h['price'][-1]:5.2f}x")
