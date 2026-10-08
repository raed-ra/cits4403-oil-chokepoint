"""
experiment_feedback.py - EXPERIMENTAL extensions, run beside the main model.
CITS4403 - Raed

The main model stays exactly as it is. This file runs the same network with up to
three extensions switched on, so the results can be compared side by side:

  price_feedback  Each day every region cuts demand according to yesterday's
                  price (its elasticity), but never by more than `max_cut` of its
                  demand. The oil it no longer buys goes back into the routing for
                  others. A price cut counts as LOST oil in the production cascade,
                  exactly like oil that never arrived.
  market_reserves Whenever the world is short, every region with a reserve
                  releases it at its maximum rate as extra SUPPLY. It travels the
                  routes like any other oil, so US reserve oil can reach Asia.
  europe_13_9     Europe's consumption set to the Energy Institute's 13.9 mb/d.
"""
import numpy as np                                            # maths
import oil_network_model as NM                                # the main model (not modified)
from oil_model_data import PRICE_ELASTICITY, REGIONAL_RESERVES, REGIONAL_DRAW_RATE  # elasticities, reserves, draw rates
from production_cascade import run_production_cascade         # Layer 3


def run_experiment(closed, days=150, price_feedback=False, max_cut=0.20,  # closed = share of Hormuz CLOSED
                   market_reserves=False, europe_13_9=False):
    """Run one closure level (share CLOSED) with the chosen extensions.

    Returns a dict: price index, and for every region its demand, the cut made
    because of price, the physical shortfall, oil_available (after both), and
    systemic loss; plus the reserves released per day.
    """
    D0 = dict(NM.REGION_DEMAND)                               # original demand (to restore later)
    S0 = dict(NM.ORIGIN_SUPPLY)                               # original supply
    if europe_13_9:
        D0["Europe"] = 13.9                                   # corrected European demand
    m = NM.OilNetworkModel()                                  # fresh model
    cut = {r: 0.0 for r in D0}                                # demand each region cuts because of price
    left = dict(REGIONAL_RESERVES)                            # reserves remaining
    release = {r: 0.0 for r in D0}                            # reserve oil released today
    price = 1.0                                               # price index (1.0 = $69)
    history = dict(price=[], cut=[], physical=[], release=[], reserves_left=[])   # one entry per day, for graphs
    # The oil AVAILABLE to sell is fixed by geography, not by how much buyers want:
    # world demand minus the main model's physical shortage at full demand.
    base = NM.OilNetworkModel()                                         # a separate model run at FULL demand...
    for _ in range(days):                                               # ...to steady state
        u_full, _, _ = base.step(1.0 - closed)                          # its physical shortfall
    supply_avail = sum(D0.values()) - sum(u_full.values())              # oil that can actually reach buyers (whole world)
    try:                                                                # change the shared tables temporarily...
        for d in range(days):                                 # one loop = one day
            for r in D0:                                      # TODAY's demand and supply
                NM.REGION_DEMAND[r] = D0[r] - cut[r]          # price feedback: buy less
                NM.ORIGIN_SUPPLY[r + "_P"] = S0[r + "_P"] + release[r]   # reserves to market: sell more
            unserved, used, delivered = m.step(1.0 - closed)  # route the oil (step takes the OPEN share)

            # the market: one world price that makes demand equal the oil available,
            # including any reserve oil released onto the market today
            consumed = supply_avail + sum(release.values())             # oil available today (plus any reserve oil sold)
            def demand_at(p):                                 # demand at price p, never cut more than max_cut
                return sum(D0[r] * max(p ** PRICE_ELASTICITY[r], 1.0 - max_cut if price_feedback else 0.0)  # demand_r x price^e, but never below (1 - cap) of normal
                           for r in D0)                                 # summed over all regions
            if demand_at(1.0) <= consumed:                              # enough oil at the normal price?
                target = 1.0                                            # then the target price stays at $69
            else:
                lo, hi = 1.0, 2.0                                       # search range for the price index
                while demand_at(hi) > consumed and hi < 40:   # find an upper bound
                    hi *= 2
                for _ in range(60):                           # bisection
                    mid = 0.5 * (lo + hi)                               # try the middle
                    lo, hi = (mid, hi) if demand_at(mid) > consumed else (lo, mid)  # too much demand -> go higher, else lower
                target = min(hi, 40.0)                                  # the clearing price (never above 40x)
            price += 0.12 * (target - price)                  # move 12% of the way each day

            if price_feedback:                                # tomorrow's cuts from today's price
                for r in D0:                                            # every region...
                    cut[r] = D0[r] * min(1.0 - price ** PRICE_ELASTICITY[r], max_cut)  # cuts demand by its price response, at most the cap
            short_world = sum(unserved.values()) + sum(cut.values()) > 0.01 or price > 1.001  # is the world short at all today?
            for r in D0:                                      # tomorrow's reserve releases
                if market_reserves and short_world:                     # market-reserves option (tried, not adopted)
                    release[r] = min(REGIONAL_DRAW_RATE.get(r, 0.0), max(0.0, left.get(r, 0.0)))  # release at full rate while stock lasts
                    left[r] = left.get(r, 0.0) - release[r]             # take it out of the reserve
                else:
                    release[r] = 0.0                                    # option off: nothing released
            history["price"].append(price)                    # record today's values so they can be graphed
            history["cut"].append(sum(cut.values()))                    # total price-driven cut today
            history["physical"].append(sum(unserved.values()))          # total physical shortfall today
            history["release"].append(sum(release.values()))            # total reserve oil released
            history["reserves_left"].append(sum(left.values()))         # total reserves left
    finally:
        NM.REGION_DEMAND.update(dict(NM.CONSUMPTION_BY_REGION))   # always restore the main model
        NM.ORIGIN_SUPPLY.update(S0)                                     # restore supply

    out = {"price": price, "regions": {}, "reserve_left": left, "history": history}  # results to return
    for r in D0:                                                        # for each region...
        lost = cut[r] + unserved[r]                           # price cut + physical shortfall = oil not used
        oa = max(0.0, 1.0 - lost / D0[r])                               # share of its oil it can actually use
        out["regions"][r] = dict(demand=D0[r], price_cut=cut[r], physical=unserved[r],  # store its numbers and its systemic loss (Layer 3)
                                 oil_available=oa, systemic=run_production_cascade(oa)[0])
    return out                                                          # the results


def threshold(**kw):
    """Closure at which the worst region first passes 10% systemic loss (bisection)."""
    worst = lambda c: max(v["systemic"] for v in run_experiment(c, **kw)["regions"].values())  # worst region's systemic loss at closure c
    if worst(1.0) <= 0.10:                                              # even full closure not systemic?
        return None                                                     # then no threshold
    lo, hi = 0.0, 1.0                                                   # the answer lies between 0% and 100% closed
    for _ in range(11):                                                 # halve the range 11 times
        mid = 0.5 * (lo + hi)                                           # test the middle
        lo, hi = (lo, mid) if worst(mid) > 0.10 else (mid, hi)          # systemic -> answer lower, else higher
    return hi                                                           # the threshold


def plot_comparison(out=None):
    """Worst-region systemic loss vs Hormuz closure: main model vs price feedback."""
    import os                                                           # file paths
    import matplotlib.pyplot as plt                                     # charts
    out = out or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figures")  # default: the project's figures/ folder
    closures = [i / 20 for i in range(8, 21)]                     # 40% ... 100% closed
    fig, ax = plt.subplots(figsize=(9, 5))                              # one chart
    for lab, kw, col in [("Main model (no price feedback)", {}, "#c1272d"),
                         ("With price feedback (cap 20%)", dict(price_feedback=True), "#0072b2")]:
        worst = [max(v["systemic"] for v in run_experiment(c, **kw)["regions"].values()) for c in closures]  # worst region's loss at each closure level
        ax.plot([100 * c for c in closures], [100 * w for w in worst], "o-", color=col, label=lab, ms=4)  # draw the line (as percentages)
    ax.axhline(10, ls="--", color="grey", lw=1)                         # dashed line at 10% = systemic
    ax.annotate("10% = systemic", xy=(41, 11.5), fontsize=9, color="grey")  # label it
    ax.set_xlabel("Hormuz closed (%)"); ax.set_ylabel("Worst region's systemic loss (%)")  # axis labels
    ax.set_title("Letting high prices spread the shortage"); ax.legend(fontsize=9); ax.grid(alpha=.3)  # title, legend, grid
    fig.tight_layout()                                                  # tidy spacing
    path = os.path.join(out, "6_price_feedback.png")                    # where to save it
    fig.savefig(path, dpi=130)                                          # save the picture
    return fig, path                                                    # the figure and its file path
