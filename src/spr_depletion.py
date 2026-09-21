"""
spr_depletion.py — how long can the strategic reserve hold the line?
CITS4403 — Raed

Real data:
  SPR was 415.4 Mb (Feb 2026), now 285.0 Mb (Sep 2026)  [EIA WPSR]
  Maximum withdrawal rate: 2.7 mb/d                      [DOE]
  Pre-crisis Brent ~ $69/bbl; observed peak ~ $105/bbl

Questions:
  1. How many days of runway does the reserve give at each draw rate?
  2. What happens to price when the reserve runs out?
  3. Under what closure does Brent exceed $200/bbl, and when?
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from oil_model_data import (SPR_CURRENT, SPR_PRECRISIS, SPR_MAX_WITHDRAW,
                            PRICE_ELASTICITY, WORLD_CONSUMPTION)
from oil_network_model import OilNetworkModel, REGION_DEMAND

BRENT_BASE = 69.0      # $/bbl pre-crisis
PRICE_ALARM = 200.0    # $/bbl threshold of interest


def simulate_with_reserve(blockade, reserve_mb=SPR_CURRENT,
                          draw_rate=SPR_MAX_WITHDRAW, days=400,
                          hoarding=True):
    """Run the disruption with a finite, rate-limited strategic reserve."""
    m = OilNetworkModel(hoarding=hoarding)
    reserve = reserve_mb
    price = 1.0
    prev = 1.0
    destroyed = 0.0
    hist = dict(price=[], brent=[], reserve=[], unserved=[], drawn=[])

    for d in range(days):
        trend = max(0.0, price - prev)
        prev = price
        unserved, _, _ = m.step(1.0 - blockade, price_trend=trend)
        short = sum(unserved.values())

        # --- reserve draws down, rate-limited and finite ---
        draw = min(short, draw_rate, max(0.0, reserve))
        reserve -= draw                      # 1 mb/d for 1 day = 1 Mb
        short -= draw

        # demand already destroyed by price closes the gap
        short = max(0.0, short - destroyed)

        # price moves toward the market-clearing level
        base = sum(REGION_DEMAND.values())
        avg_e = np.mean([abs(PRICE_ELASTICITY[r]) for r in REGION_DEMAND])
        target = (max(0.01, 1.0 - short / base) ** (1.0 / (-avg_e))) if short > 0 else 1.0
        price += 0.12 * (target - price)
        price = float(np.clip(price, 1.0, 40.0))

        # constant-elasticity form: q = q0 * price^e  (e negative)
        destroyed = sum(REGION_DEMAND[r] * (1.0 - price ** PRICE_ELASTICITY[r])
                        for r in REGION_DEMAND)

        hist["price"].append(price)
        hist["brent"].append(price * BRENT_BASE)
        hist["reserve"].append(max(0.0, reserve))
        hist["unserved"].append(short)
        hist["drawn"].append(draw)
    return hist


def runway_days(reserve_mb=SPR_CURRENT, draw_rate=SPR_MAX_WITHDRAW):
    """Simple physical runway: how long the reserve lasts at a given rate."""
    return reserve_mb / draw_rate


def days_to_price(hist, threshold=PRICE_ALARM):
    for d, b in enumerate(hist["brent"]):
        if b >= threshold:
            return d
    return None


if __name__ == "__main__":
    print("STRATEGIC RESERVE RUNWAY\n" + "=" * 55)
    print(f"Reserve now: {SPR_CURRENT} Mb (was {SPR_PRECRISIS} Mb pre-crisis)")
    for rate in [1.0, 1.5, 2.0, SPR_MAX_WITHDRAW]:
        print(f"  draw {rate:4.1f} mb/d -> runway {runway_days(draw_rate=rate):5.0f} days "
              f"({runway_days(draw_rate=rate)/30:.1f} months)")

    print("\nTIME TO CRISIS under different closure levels")
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

    for b, c in zip([0.5, 0.7, 1.0], cols):
        h = simulate_with_reserve(b)
        ax[0].plot(h["reserve"], color=c, label=f"{b:.0%} closed")
        ax[1].plot(h["brent"], color=c, label=f"{b:.0%} closed")
    ax[0].set_xlabel("Day"); ax[0].set_ylabel("SPR remaining (Mb)")
    ax[0].set_title(f"Reserve depletion from {SPR_CURRENT} Mb\n"
                    f"(max draw {SPR_MAX_WITHDRAW} mb/d)")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)

    ax[1].axhline(PRICE_ALARM, ls="--", color="grey", lw=1)
    ax[1].annotate("$200/bbl", xy=(10, PRICE_ALARM + 5), fontsize=8, color="grey")
    ax[1].axhline(105, ls=":", color="green", lw=1)
    ax[1].annotate("observed 2026 peak ~$105", xy=(10, 110), fontsize=8, color="green")
    ax[1].set_xlabel("Day"); ax[1].set_ylabel("Brent ($/bbl)")
    ax[1].set_title("Price trajectory\n(jump when the reserve empties)")
    ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)

    # with vs without the reserve, at full closure
    h_with = simulate_with_reserve(1.0, reserve_mb=SPR_CURRENT)
    h_without = simulate_with_reserve(1.0, reserve_mb=0.0)
    h_full = simulate_with_reserve(1.0, reserve_mb=SPR_PRECRISIS)
    ax[2].plot(h_without["brent"], color="#c1272d", label="no reserve")
    ax[2].plot(h_with["brent"], color="#e69f00", label=f"current SPR ({SPR_CURRENT:.0f} Mb)")
    ax[2].plot(h_full["brent"], color="#009e73", label=f"pre-crisis SPR ({SPR_PRECRISIS:.0f} Mb)")
    ax[2].axhline(PRICE_ALARM, ls="--", color="grey", lw=1)
    ax[2].set_xlabel("Day"); ax[2].set_ylabel("Brent ($/bbl)")
    ax[2].set_title("What the reserve buys you\n(full closure)")
    ax[2].legend(fontsize=8); ax[2].grid(alpha=.3)

    fig.suptitle("Strategic reserve depletion and time to crisis")
    fig.tight_layout()
    fig.savefig("/mnt/user-data/outputs/spr_depletion.png", dpi=130)
    print("\nSaved figure to spr_depletion.png")
