"""
closure_sensitivity.py — how damage and price respond to closing Hormuz,
Bab el-Mandeb, or both together.
CITS4403 — Raed

For every combination of closure levels the model runs to steady state and
records:
  - unserved demand (mb/d), total and by region
  - the market-clearing oil price (constant-elasticity demand)

Real-world reference points are marked on every chart so the model's
operating point in 2026 can be read directly off the results.
"""

import numpy as np                                                      # maths, grids
import matplotlib                                                       # plotting library
import matplotlib.pyplot as plt                                         # plotting interface

from oil_network_model import OilNetworkModel, REGION_DEMAND, REGIONS   # the network model


import os as _os                                                        # file paths
# Save figures into the project's own figures/ folder, wherever it is run from.
FIG_DIR = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "figures")  # the project's figures/ folder
_os.makedirs(FIG_DIR, exist_ok=True)                                    # create it if missing

BRENT_PRECRISIS = 69.0     # $/bbl, Feb 2026, before the closure

# ----------------------------------------------------------------------
# Real-world operating points (closure = fraction BLOCKED, 0..1)
#   Q2 2026: EIA observed Hormuz 4.9 of 20.9 mb/d flowing -> 77% blocked.
#            Bab el-Mandeb 8.1 of 8.6 -> effectively open (~6%).
#            Observed Brent ~$105.
#   Sep 2026 (approximate): convoys and pipelines narrowed crude losses to
#            ~45% of pre-war; Yanbu (Red Sea) loadings halted. Recorded here
#            as Hormuz ~45% blocked with the Red Sea route heavily impaired.
# ----------------------------------------------------------------------
REAL_POINTS = {                                                         # the two real 2026 situations, as closure levels
    "Q2 2026 (EIA)":     dict(hormuz=1 - 4.9 / 20.9, bab=1 - 8.1 / 8.6, brent=105),  # 77% / 6% closed; observed price $105
    "Sep 2026 (approx)": dict(hormuz=0.45, bab=0.60, brent=None),       # approximate; no price recorded
}


def steady_state(hormuz_closed, bab_closed, days=120):
    """Run to steady state for one pair of closure levels.

    Returns (total unserved mb/d, {region: unserved}, Brent $/bbl).
    """
    m = OilNetworkModel()                                               # fresh model
    extra = {"Bab el-Mandeb": 1.0 - bab_closed}                         # Bab el-Mandeb open share (1 - closed)
    for _ in range(days):                                               # run 120 days...
        unserved, _, _ = m.step(1.0 - hormuz_closed, extra_closed=extra)  # ...with both closures (step takes OPEN shares)
    total = sum(unserved.values())                                      # total world shortfall
    available = sum(REGION_DEMAND.values()) - total                     # oil that still reaches buyers
    price_index, _ = m.clear_market(available)                          # Layer 2: the clearing price (no reserves)
    return total, dict(unserved), BRENT_PRECRISIS * price_index         # (shortfall, per region, Brent $/bbl)


def grid(n=11):
    """Evaluate the full Hormuz x Bab el-Mandeb grid."""
    levels = np.linspace(0, 1, n)                                       # 0%, 10%, ... 100% closed
    U = np.zeros((n, n)); P = np.zeros((n, n))                          # empty 11x11 tables: damage U, price P
    for i, h in enumerate(levels):                                      # each Hormuz level (rows)...
        for j, b in enumerate(levels):                                  # ...times each Bab el-Mandeb level (columns)
            U[i, j], _, P[i, j] = steady_state(h, b)                    # run it; store damage and price
    return levels, U, P                                                 # 121 results


def plot_all(levels, U, P, out=None):
    out = out or FIG_DIR                                                # default save folder
    pct = levels * 100                                                  # closure levels as percentages
    cols = ["#0072b2", "#e69f00", "#c1272d", "#009e73"]
    pick = [0, 3, 6, 10]          # 0%, 30%, 60%, 100%

    # ---- Figure 1: damage ----
    fig, ax = plt.subplots(1, 3, figsize=(17, 5))                       # three charts side by side
    for k, c in zip(pick, cols):                                        # one line per chosen Bab el-Mandeb level
        ax[0].plot(pct, U[:, k], "o-", ms=3, color=c,                   # damage as Hormuz closes
                   label=f"Bab el-Mandeb {levels[k]:.0%} closed")
    ax[0].set_xlabel("Hormuz closed (%)"); ax[0].set_ylabel("Unserved demand (mb/d)")  # axis labels
    ax[0].set_title("Damage vs Hormuz closure"); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)  # title, legend, grid

    for k, c in zip(pick, cols):                                        # one line per chosen Hormuz level
        ax[1].plot(pct, U[k, :], "o-", ms=3, color=c,                   # damage as Bab el-Mandeb closes
                   label=f"Hormuz {levels[k]:.0%} closed")
    ax[1].set_xlabel("Bab el-Mandeb closed (%)"); ax[1].set_ylabel("Unserved demand (mb/d)")  # axis labels
    ax[1].set_title("Damage vs Bab el-Mandeb closure"); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)  # title, legend, grid

    im = ax[2].imshow(U, origin="lower", aspect="auto", cmap="Reds",    # heatmap: darker = more damage
                      extent=[0, 100, 0, 100])
    fig.colorbar(im, ax=ax[2], label="Unserved demand (mb/d)")          # colour scale
    for lab, pt in REAL_POINTS.items():                                 # mark each real 2026 point...
        ax[2].plot(pt["bab"] * 100, pt["hormuz"] * 100, "k*", ms=15)    # ...with a star
        ax[2].annotate(lab, (pt["bab"] * 100, pt["hormuz"] * 100),      # ...and its label
                       xytext=(5, 6), textcoords="offset points", fontsize=8)
    ax[2].set_xlabel("Bab el-Mandeb closed (%)"); ax[2].set_ylabel("Hormuz closed (%)")  # axis labels
    ax[2].set_title("Combined closure: damage")                         # title
    fig.suptitle("Supply damage under single and combined chokepoint closures")  # overall title
    fig.tight_layout(); fig.savefig(f"{out}/closure_damage.png", dpi=130); plt.close(fig)  # save as closure_damage.png

    # ---- Figure 2: price ----
    fig, ax = plt.subplots(1, 3, figsize=(17, 5))                       # same three charts for PRICE
    for k, c in zip(pick, cols):                                        # one line per Bab el-Mandeb level
        ax[0].plot(pct, P[:, k], "o-", ms=3, color=c,                   # price as Hormuz closes
                   label=f"Bab el-Mandeb {levels[k]:.0%} closed")
    ax[0].axhline(105, ls="--", color="grey", lw=1)                     # dashed line: observed Q2 2026 price
    ax[0].annotate("observed Q2 2026 ~$105", (2, 108), fontsize=8, color="grey")  # label it
    ax[0].set_xlabel("Hormuz closed (%)"); ax[0].set_ylabel("Brent ($/bbl)")  # axis labels
    ax[0].set_title("Oil price vs Hormuz closure"); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)  # title, legend, grid

    for k, c in zip(pick, cols):                                        # one line per Hormuz level
        ax[1].plot(pct, P[k, :], "o-", ms=3, color=c,                   # price as Bab el-Mandeb closes
                   label=f"Hormuz {levels[k]:.0%} closed")
    ax[1].set_xlabel("Bab el-Mandeb closed (%)"); ax[1].set_ylabel("Brent ($/bbl)")  # axis labels
    ax[1].set_title("Oil price vs Bab el-Mandeb closure"); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)  # title, legend, grid

    im = ax[2].imshow(P, origin="lower", aspect="auto", cmap="YlOrRd",  # price heatmap
                      extent=[0, 100, 0, 100])
    fig.colorbar(im, ax=ax[2], label="Brent ($/bbl)")                   # colour scale
    for lab, pt in REAL_POINTS.items():                                 # stars for the real points
        ax[2].plot(pt["bab"] * 100, pt["hormuz"] * 100, "k*", ms=15)    # 
        ax[2].annotate(lab, (pt["bab"] * 100, pt["hormuz"] * 100),      # 
                       xytext=(5, 6), textcoords="offset points", fontsize=8)
    ax[2].set_xlabel("Bab el-Mandeb closed (%)"); ax[2].set_ylabel("Hormuz closed (%)")  # axis labels
    ax[2].set_title("Combined closure: price")                          # title
    fig.suptitle("Equilibrium Brent price under single and combined chokepoint closures")  # overall title
    fig.tight_layout(); fig.savefig(f"{out}/closure_price.png", dpi=130); plt.close(fig)  # save as closure_price.png


if __name__ == "__main__":                                              # only when run directly
    print("Real-world points:")
    for lab, pt in REAL_POINTS.items():                                 # each real point
        tot, by, brent = steady_state(pt["hormuz"], pt["bab"])          # run it
        obs = f"  observed ${pt['brent']}" if pt["brent"] else ""       # observed price, if known
        print(f"  {lab:<20} Hormuz {pt['hormuz']:.0%}  Bab {pt['bab']:.0%}  "  # print the result
              f"-> unserved {tot:5.2f}  Brent ${brent:5.0f}{obs}")
    levels, U, P = grid()                                               # run all 121 combinations
    plot_all(levels, U, P)                                              # draw both figures
    print("\nSaved closure_damage.png and closure_price.png")
