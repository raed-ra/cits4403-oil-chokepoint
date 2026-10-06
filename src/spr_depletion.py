"""
spr_depletion.py - strategic reserves: how long can they hold the line?
CITS4403 - Raed

Each region holds its own reserve and can draw on it only for its OWN
shortfall, at its own maximum rate - the US reserve cannot be shipped to
China. Totals: ~2,400 Mb across six regions (China ~1,400, Japan/Korea 449,
US 285, Europe 179, Other Asia 50, India 39).

  simulate_with_reserve()  day-by-day run with reserves drawn, returns the price
                           path and reserves remaining
  regional=False           a hypothetical single pooled reserve, for comparison
"""

import numpy as np                                     # maths: clip
import matplotlib                                      # plotting library
import matplotlib.pyplot as plt                        # plotting interface

from oil_model_data import (SPR_CURRENT, SPR_PRECRISIS, SPR_MAX_WITHDRAW,
                            PRICE_ELASTICITY, WORLD_CONSUMPTION,
                            REGIONAL_RESERVES, REGIONAL_DRAW_RATE)   # reserve and price constants
from oil_network_model import OilNetworkModel, REGION_DEMAND          # the network model

import os as _os                                       # file paths
FIG_DIR = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "figures")   # project's figures/ folder
_os.makedirs(FIG_DIR, exist_ok=True)                   # create it if missing


BRENT_BASE = 69.0      # $/bbl before the crisis: price index 1.0 = $69
PRICE_ALARM = 200.0    # $/bbl: a level of interest for "time to crisis"


def simulate_with_reserve(blockade, reserve_mb=None,
                          draw_rate=SPR_MAX_WITHDRAW, days=400,
                          hoarding=False, regional=True, scale=1.0):
    """Run a disruption with finite, rate-limited strategic reserves.

    blockade       share of Hormuz CLOSED (0..1)
    regional=True  each region draws only on its own reserve (realistic)
    regional=False one pooled reserve of `reserve_mb`, drawn at `draw_rate`
                   (NOTE: reserve_mb and draw_rate are only used when regional=False)
    scale          multiply every reserve (0 = no reserves at all)
    Returns a dict of daily lists: price, brent, reserve, unserved, drawn.
    """
    m = OilNetworkModel(hoarding=hoarding)                 # fresh model
    if regional:
        reserves = {r: REGIONAL_RESERVES[r] * scale for r in REGIONAL_RESERVES}   # each region's own reserve, Mb
    else:
        reserves = {"GLOBAL": (reserve_mb if reserve_mb is not None
                               else SPR_CURRENT) * scale}  # one pooled reserve
    reserve = sum(reserves.values())                       # total remaining
    price = 1.0                                            # price index (1.0 = $69)
    prev = 1.0                                             # yesterday's price
    destroyed = 0.0                                        # demand destroyed by price
    hist = dict(price=[], brent=[], reserve=[], unserved=[], drawn=[])   # daily record

    for d in range(days):                                  # one loop = one day
        trend = max(0.0, price - prev)                     # price momentum (used only by hoarding)
        prev = price
        unserved, _, _ = m.step(1.0 - blockade, price_trend=trend)   # today's shortfalls (step takes the OPEN share)

        short = 0.0                                        # world shortfall AFTER reserves
        if regional:
            for r, miss in unserved.items():               # each region separately
                rate = REGIONAL_DRAW_RATE.get(r, 1.0)      # its maximum draw rate
                draw = min(miss, rate, max(0.0, reserves.get(r, 0.0)))   # need, rate limit, what's left
                reserves[r] = reserves.get(r, 0.0) - draw  # 1 mb/d for 1 day = 1 Mb out
                short += max(0.0, miss - draw)             # what the reserve couldn't cover
        else:
            tot = sum(unserved.values())                   # pooled: one world shortfall
            draw = min(tot, draw_rate, max(0.0, reserves["GLOBAL"]))   # one draw, wherever needed
            reserves["GLOBAL"] -= draw
            short = tot - draw
        reserve = sum(reserves.values())                   # total left

        # Price: the market-clearing price for the PHYSICAL shortfall. clear_market()
        # already contains the demand response, so it must not be subtracted first.
        base = sum(REGION_DEMAND.values())                 # normal world demand
        target, _ = m.clear_market(base - short)           # clearing price index
        price += 0.12 * (target - price)                   # move 12% of the way each day
        price = float(np.clip(price, 1.0, 40.0))           # keep within 1x..40x

        destroyed = sum(REGION_DEMAND[r] * (1.0 - price ** PRICE_ELASTICITY[r])   # demand lost at this price
                        for r in REGION_DEMAND)

        hist["price"].append(price)                        # record the day
        hist["brent"].append(price * BRENT_BASE)           # in $/bbl
        hist["reserve"].append(max(0.0, reserve))
        hist["unserved"].append(short)
        hist["drawn"].append(draw)                         # (last region's draw - for reference only)
    return hist


def runway_days(reserve_mb=SPR_CURRENT, draw_rate=SPR_MAX_WITHDRAW):
    """Simple arithmetic: days a reserve lasts at a fixed rate (volume / rate).
    Defaults are the US reserve (285 Mb at 2.7 mb/d)."""
    return reserve_mb / draw_rate


def days_to_price(hist, threshold=PRICE_ALARM):
    """First day Brent reaches `threshold`, or None if it never does."""
    for d, b in enumerate(hist["brent"]):                  # day number and price
        if b >= threshold:
            return d
    return None


if __name__ == "__main__":                                 # only when run directly
    print("REGIONAL STRATEGIC RESERVES\n" + "=" * 55)
    for r, mb in sorted(REGIONAL_RESERVES.items(), key=lambda x: -x[1]):   # each region's reserve
        if mb > 0:
            print(f"  {r:<11}{mb:6.0f} Mb at up to {REGIONAL_DRAW_RATE[r]:.1f} mb/d "
                  f"-> lasts {runway_days(mb, REGIONAL_DRAW_RATE[r]):4.0f} days if drawn flat out")

    print("\nTIME TO CRISIS under different closure levels (realistic regional reserves)")
    print(f"{'closure':>9}{'reserve empty':>15}{'$200 reached':>15}{'peak Brent':>13}")
    for b in [0.3, 0.5, 0.7, 0.85, 1.0]:
        h = simulate_with_reserve(b)
        empty = next((d for d, r in enumerate(h["reserve"]) if r <= 0), None)
        d200 = days_to_price(h)
        print(f"{b:>8.0%}{'day ' + str(empty) if empty else 'not emptied':>15}"
              f"{'day ' + str(d200) if d200 else 'not reached':>15}"
              f"{max(h['brent']):>12.0f}")

    # ---------------- figure ----------------
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.8))
    cols = ["#0072b2", "#e69f00", "#c1272d"]

    for b, c in zip([0.5, 0.7, 1.0], cols):                # three closure levels
        h = simulate_with_reserve(b)
        ax[0].plot(h["reserve"], color=c, label=f"{b:.0%} closed")
        ax[1].plot(h["brent"], color=c, label=f"{b:.0%} closed")
    total = sum(REGIONAL_RESERVES.values())
    ax[0].set_xlabel("Day"); ax[0].set_ylabel("Reserves remaining (Mb)")
    ax[0].set_title(f"Regional reserves remaining\n(from {total:.0f} Mb in six regions)")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)

    ax[1].axhline(PRICE_ALARM, ls="--", color="grey", lw=1)
    ax[1].annotate("$200/bbl", xy=(10, PRICE_ALARM + 5), fontsize=8, color="grey")
    ax[1].axhline(105, ls=":", color="green", lw=1)
    ax[1].annotate("observed 2026 peak ~$105", xy=(10, 110), fontsize=8, color="green")
    ax[1].set_xlabel("Day"); ax[1].set_ylabel("Brent ($/bbl)")
    ax[1].set_title("Price trajectory\n(jumps as regional reserves run out)")
    ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)

    # With vs without reserves at full closure. scale=0 switches reserves OFF;
    # regional=False pools them. (An earlier version passed reserve_mb here,
    # which regional mode ignores, so all three lines were identical.)
    h_none   = simulate_with_reserve(1.0, scale=0.0)
    h_region = simulate_with_reserve(1.0)
    h_pool   = simulate_with_reserve(1.0, regional=False, reserve_mb=total,
                                     draw_rate=sum(REGIONAL_DRAW_RATE.values()))
    ax[2].plot(h_none["brent"], color="#c1272d", label="no reserves")
    ax[2].plot(h_region["brent"], color="#e69f00", label="regional reserves (realistic)")
    ax[2].plot(h_pool["brent"], color="#009e73", label="hypothetical pooled reserve")
    ax[2].axhline(PRICE_ALARM, ls="--", color="grey", lw=1)
    ax[2].set_xlabel("Day"); ax[2].set_ylabel("Brent ($/bbl)")
    ax[2].set_title("What the reserves buy you\n(full closure)")
    ax[2].legend(fontsize=8); ax[2].grid(alpha=.3)

    fig.suptitle("Strategic reserve depletion and time to crisis")
    fig.tight_layout()
    fig.savefig(_os.path.join(FIG_DIR, "spr_depletion.png"), dpi=130)
    print("\nSaved figure to spr_depletion.png")
