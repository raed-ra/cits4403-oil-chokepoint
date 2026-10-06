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

import numpy as np
import matplotlib
import matplotlib.pyplot as plt

from oil_network_model import OilNetworkModel, REGION_DEMAND, REGIONS


import os as _os
# Save figures into the project's own figures/ folder, wherever it is run from.
FIG_DIR = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "figures")
_os.makedirs(FIG_DIR, exist_ok=True)

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
REAL_POINTS = {
    "Q2 2026 (EIA)":     dict(hormuz=1 - 4.9 / 20.9, bab=1 - 8.1 / 8.6, brent=105),
    "Sep 2026 (approx)": dict(hormuz=0.45, bab=0.60, brent=None),
}


def steady_state(hormuz_closed, bab_closed, days=120):
    """Run to steady state for one pair of closure levels.

    Returns (total unserved mb/d, {region: unserved}, Brent $/bbl).
    """
    m = OilNetworkModel()
    extra = {"Bab el-Mandeb": 1.0 - bab_closed}
    for _ in range(days):
        unserved, _, _ = m.step(1.0 - hormuz_closed, extra_closed=extra)
    total = sum(unserved.values())
    available = sum(REGION_DEMAND.values()) - total
    price_index, _ = m.clear_market(available)
    return total, dict(unserved), BRENT_PRECRISIS * price_index


def grid(n=11):
    """Evaluate the full Hormuz x Bab el-Mandeb grid."""
    levels = np.linspace(0, 1, n)
    U = np.zeros((n, n)); P = np.zeros((n, n))
    for i, h in enumerate(levels):
        for j, b in enumerate(levels):
            U[i, j], _, P[i, j] = steady_state(h, b)
    return levels, U, P


def plot_all(levels, U, P, out=None):
    out = out or FIG_DIR
    pct = levels * 100
    cols = ["#0072b2", "#e69f00", "#c1272d", "#009e73"]
    pick = [0, 3, 6, 10]          # 0%, 30%, 60%, 100%

    # ---- Figure 1: damage ----
    fig, ax = plt.subplots(1, 3, figsize=(17, 5))
    for k, c in zip(pick, cols):
        ax[0].plot(pct, U[:, k], "o-", ms=3, color=c,
                   label=f"Bab el-Mandeb {levels[k]:.0%} closed")
    ax[0].set_xlabel("Hormuz closed (%)"); ax[0].set_ylabel("Unserved demand (mb/d)")
    ax[0].set_title("Damage vs Hormuz closure"); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)

    for k, c in zip(pick, cols):
        ax[1].plot(pct, U[k, :], "o-", ms=3, color=c,
                   label=f"Hormuz {levels[k]:.0%} closed")
    ax[1].set_xlabel("Bab el-Mandeb closed (%)"); ax[1].set_ylabel("Unserved demand (mb/d)")
    ax[1].set_title("Damage vs Bab el-Mandeb closure"); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)

    im = ax[2].imshow(U, origin="lower", aspect="auto", cmap="Reds",
                      extent=[0, 100, 0, 100])
    fig.colorbar(im, ax=ax[2], label="Unserved demand (mb/d)")
    for lab, pt in REAL_POINTS.items():
        ax[2].plot(pt["bab"] * 100, pt["hormuz"] * 100, "k*", ms=15)
        ax[2].annotate(lab, (pt["bab"] * 100, pt["hormuz"] * 100),
                       xytext=(5, 6), textcoords="offset points", fontsize=8)
    ax[2].set_xlabel("Bab el-Mandeb closed (%)"); ax[2].set_ylabel("Hormuz closed (%)")
    ax[2].set_title("Combined closure: damage")
    fig.suptitle("Supply damage under single and combined chokepoint closures")
    fig.tight_layout(); fig.savefig(f"{out}/closure_damage.png", dpi=130); plt.close(fig)

    # ---- Figure 2: price ----
    fig, ax = plt.subplots(1, 3, figsize=(17, 5))
    for k, c in zip(pick, cols):
        ax[0].plot(pct, P[:, k], "o-", ms=3, color=c,
                   label=f"Bab el-Mandeb {levels[k]:.0%} closed")
    ax[0].axhline(105, ls="--", color="grey", lw=1)
    ax[0].annotate("observed Q2 2026 ~$105", (2, 108), fontsize=8, color="grey")
    ax[0].set_xlabel("Hormuz closed (%)"); ax[0].set_ylabel("Brent ($/bbl)")
    ax[0].set_title("Oil price vs Hormuz closure"); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)

    for k, c in zip(pick, cols):
        ax[1].plot(pct, P[k, :], "o-", ms=3, color=c,
                   label=f"Hormuz {levels[k]:.0%} closed")
    ax[1].set_xlabel("Bab el-Mandeb closed (%)"); ax[1].set_ylabel("Brent ($/bbl)")
    ax[1].set_title("Oil price vs Bab el-Mandeb closure"); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)

    im = ax[2].imshow(P, origin="lower", aspect="auto", cmap="YlOrRd",
                      extent=[0, 100, 0, 100])
    fig.colorbar(im, ax=ax[2], label="Brent ($/bbl)")
    for lab, pt in REAL_POINTS.items():
        ax[2].plot(pt["bab"] * 100, pt["hormuz"] * 100, "k*", ms=15)
        ax[2].annotate(lab, (pt["bab"] * 100, pt["hormuz"] * 100),
                       xytext=(5, 6), textcoords="offset points", fontsize=8)
    ax[2].set_xlabel("Bab el-Mandeb closed (%)"); ax[2].set_ylabel("Hormuz closed (%)")
    ax[2].set_title("Combined closure: price")
    fig.suptitle("Equilibrium Brent price under single and combined chokepoint closures")
    fig.tight_layout(); fig.savefig(f"{out}/closure_price.png", dpi=130); plt.close(fig)


if __name__ == "__main__":
    print("Real-world points:")
    for lab, pt in REAL_POINTS.items():
        tot, by, brent = steady_state(pt["hormuz"], pt["bab"])
        obs = f"  observed ${pt['brent']}" if pt["brent"] else ""
        print(f"  {lab:<20} Hormuz {pt['hormuz']:.0%}  Bab {pt['bab']:.0%}  "
              f"-> unserved {tot:5.2f}  Brent ${brent:5.0f}{obs}")
    levels, U, P = grid()
    plot_all(levels, U, P)
    print("\nSaved closure_damage.png and closure_price.png")
