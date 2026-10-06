"""
network_view.py — see every node and edge of the network, as tables and a map.
CITS4403 — Raed

snapshot()      runs the model to steady state for one scenario and records
                the value of every node and every edge
print_tables()  prints three tables: regions, chokepoints, routes
draw()          draws the network: edge width = oil flow, colour = stress

Node types
  producer   (square)   a region's export supply, e.g. MidEast_P
  consumer   (circle)   a region's demand; colour = share of demand unserved
  chokepoint (diamond)  a sea passage; colour = how full it is
Edges
  each route is drawn as its path: producer -> chokepoint(s) -> consumer.
  Where routes share a segment their flows are added, so a thick line means
  many routes crowd through it.
"""

import os
import numpy as np
import matplotlib.pyplot as plt

from oil_model_data import (CHOKEPOINTS, PRODUCTION_BY_REGION, REGIONAL_RESERVES)
from oil_network_model import OilNetworkModel, ROUTES, REGIONS, REGION_DEMAND, ORIGIN_SUPPLY

FIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figures")
os.makedirs(FIG_DIR, exist_ok=True)

# Schematic positions (roughly longitude, latitude). Producer nodes are offset
# from their region's consumer node so both can be seen.
POS = {
    # consumers
    "NAmerica": (-100, 42), "LatAm": (-62, -14), "Europe": (-10, 52), "CIS": (74, 56),
    "MidEast": (22, 20), "Africa": (12, 0), "China": (110, 34), "India": (86, 16),
    "JapanKorea": (138, 40), "OtherAsia": (114, -4),
    # producers (export side)
    "NAmerica_P": (-86, 24), "LatAm_P": (-44, -28), "CIS_P": (46, 68),
    "CISEast_P": (124, 60), "MidEast_P": (56, 38), "Africa_P": (-6, 10),
    # chokepoints
    "Hormuz": (66, 27), "Malacca": (100, 6), "Suez+SUMED": (28, 35),
    "Bab el-Mandeb": (42, 10), "Cape of Good Hope": (18, -36),
    "Danish Straits": (6, 64), "Turkish Straits": (24, 48), "Panama": (-80, 9),
}

# Where each node's label sits: (dx, dy, horizontal align, vertical align).
# Default is centred below the marker.
LABEL = {
    "Danish Straits": (0, 4, "center", "bottom"),
    "Turkish Straits": (4, 0, "left", "center"),
    "Suez+SUMED": (-4, 0, "right", "center"),
    "MidEast_P": (4, 0, "left", "center"),
    "CIS_P": (0, 4, "center", "bottom"),
    "CISEast_P": (0, 4, "center", "bottom"),
}

def _label(ax, node, x, y, text, **kw):
    dx, dy, ha, va = LABEL.get(node, (0, -5, "center", "top"))
    ax.text(x + dx, y + dy, text, ha=ha, va=va, zorder=5, **kw)


_BASE = {}
def _model_normal():
    """The model's own flow through each passage with Hormuz fully open - its
    equilibrium. Used as 'normal' when colouring how busy a passage is."""
    if not _BASE:
        m = OilNetworkModel()
        _, used, _ = m.allocate_flows(1.0)
        _BASE.update(used)
    return _BASE


def snapshot(hormuz_open=1.0, extra_closed=None, days=150, reserves=False):
    """Run one scenario to steady state; return the value of every node and edge.

    reserves=False : shortfalls BEFORE any strategic reserve is drawn (the network
                     model itself has no reserves).
    reserves=True  : each region draws on its own reserve every day, at its maximum
                     rate, until it runs out; the snapshot shows the result on the
                     final day.
    """
    from oil_model_data import REGIONAL_DRAW_RATE
    m = OilNetworkModel()
    left = dict(REGIONAL_RESERVES)
    draw = {r: 0.0 for r in REGIONS}
    for _ in range(days):
        unserved, used, delivered = m.step(hormuz_open, extra_closed=extra_closed)
        if reserves:
            for r, miss in unserved.items():
                draw[r] = min(miss, REGIONAL_DRAW_RATE.get(r, 0.0), max(0.0, left.get(r, 0.0)))
                left[r] = left.get(r, 0.0) - draw[r]
    delivered = {r: delivered[r] + draw[r] for r in REGIONS}
    unserved = {r: unserved[r] - draw[r] for r in REGIONS}

    # allowed flow through each passage: canals have a capacity, straits do not;
    # a closure lets through (% open) x normal flow - same rule as the model
    cap = {c: CHOKEPOINTS[c][1] for c in CHOKEPOINTS}
    open_frac = {c: 1.0 for c in CHOKEPOINTS}
    open_frac["Hormuz"] = hormuz_open
    cap["Hormuz"] = CHOKEPOINTS["Hormuz"][0] * hormuz_open
    for c, f in (extra_closed or {}).items():
        open_frac[c] = f
        lim = CHOKEPOINTS[c][0] * f
        cap[c] = lim if cap[c] is None else min(cap[c], lim)
    base = _model_normal()

    regions = {}
    for r in REGIONS:
        domestic = min(PRODUCTION_BY_REGION[r], REGION_DEMAND[r])
        regions[r] = dict(produces=PRODUCTION_BY_REGION[r], consumes=REGION_DEMAND[r],
                          domestic=domestic, imported=delivered[r] - domestic,
                          delivered=delivered[r], unserved=unserved[r],
                          # same definition the model uses for damage: share of demand
                          # met AFTER the refinery-complexity uplift
                          supplied=1.0 - unserved[r] / REGION_DEMAND[r],
                          reserve=REGIONAL_RESERVES.get(r, 0.0),
                          reserve_draw=draw[r], reserve_left=left.get(r, 0.0))
    chokepoints = {}
    for c in CHOKEPOINTS:
        b = base[c]
        if b > 0.05:
            stress = used[c] / b                       # 1.0 = same as normal
        else:
            stress = 2.0 if used[c] > 0.05 else 0.0    # normally unused
        chokepoints[c] = dict(normal=CHOKEPOINTS[c][0], model_normal=b, capacity=cap[c],
                              open=open_frac[c], used=used[c], stress=stress,
                              closed=(cap[c] is not None and cap[c] < 1e-9))
    routes = {k: dict(origin=v[0], dest=v[1], via=v[2], days=v[3],
                      flow=m.last_route_flow.get(k, 0.0)) for k, v in ROUTES.items()}
    exports = {o: sum(rt["flow"] for rt in routes.values() if rt["origin"] == o)
               for o in ORIGIN_SUPPLY}
    return dict(regions=regions, chokepoints=chokepoints, routes=routes,
                exports=exports, hormuz_open=hormuz_open, extra_closed=extra_closed,
                reserves=reserves, days=days)


def print_tables(snap, active_only=True):
    tag = (f"WITH reserves drawn (day {snap['days']})" if snap["reserves"]
           else "BEFORE any reserve release")
    print(f"REGIONS (consumer nodes), mb/d  -  {tag}")
    print(f"{'region':<12}{'produce':>8}{'consume':>8}{'domestic':>9}{'import':>8}"
          f"{'reserve':>8}{'got':>7}{'short':>7}{'met':>6}{'reserve left':>13}")
    for r, d in snap["regions"].items():
        print(f"{r:<12}{d['produces']:8.1f}{d['consumes']:8.1f}{d['domestic']:9.1f}"
              f"{d['delivered']-d['domestic']-d['reserve_draw']:8.1f}{d['reserve_draw']:8.1f}"
              f"{d['delivered']:7.1f}{d['unserved']:7.2f}{d['supplied']:6.0%}"
              f"{d['reserve_left']:10.0f} Mb")

    print("  'got' is crude received; 'short' and 'met' include the refinery-complexity\n"
          "  uplift (complex refineries get up to 15% more product per barrel), so\n"
          "  got + short can be slightly less than consume.")
    print("\nCHOKEPOINTS (passage nodes), mb/d")
    print(f"{'chokepoint':<20}{'EIA normal':>11}{'model normal':>13}{'open':>6}"
          f"{'limit now':>10}{'flow':>7}{'vs normal':>10}")
    for c, d in snap["chokepoints"].items():
        lim = "none" if d["capacity"] is None else f"{d['capacity']:.1f}"
        vs = "closed" if d["closed"] else (f"{d['stress']:.0%}" if d["model_normal"] > 0.05
                                           else ("new" if d["used"] > 0.05 else "-"))
        print(f"{c:<20}{d['normal']:11.1f}{d['model_normal']:13.2f}{d['open']:6.0%}"
              f"{lim:>10}{d['used']:7.2f}{vs:>10}")
    print("  Straits have no capacity limit (open water); canals (Suez, Panama) do.\n"
          "  'vs normal' = flow now / the model's own flow with Hormuz open.")

    print("\nROUTES (edges), mb/d" + ("  - only routes carrying oil" if active_only else ""))
    print(f"{'route':<24}{'via':<36}{'days':>5}{'flow':>7}")
    for k, d in sorted(snap["routes"].items(), key=lambda x: -x[1]["flow"]):
        if active_only and d["flow"] < 0.01:
            continue
        via = ", ".join(d["via"]) if d["via"] else "(direct)"
        print(f"{k:<24}{via:<36}{d['days']:5d}{d['flow']:7.2f}")
    print(f"{'TOTAL traded':<65}{sum(d['flow'] for d in snap['routes'].values()):7.2f}")


def _segments(snap):
    """Add up route flows on each segment of each route's path."""
    seg = {}
    for d in snap["routes"].values():
        if d["flow"] < 0.01:
            continue
        path = [d["origin"]] + list(d["via"]) + [d["dest"]]
        for a, b in zip(path[:-1], path[1:]):
            key = tuple(sorted((a, b)))
            seg[key] = seg.get(key, 0.0) + d["flow"]
    return seg


def draw_panel(ax, snap, title, legend=False):
    seg = _segments(snap)
    placed = [POS[n] for n in POS]          # keep labels off the markers too
    def free(x, y):
        # distance in map units, with y stretched to match the panel's shape
        return all(((x - px) / 270) ** 2 + ((y - py) / 124) ** 2 > 0.035 ** 2
                   for px, py in placed)
    # edges: width = flow
    for (a, b), f in seg.items():
        (x1, y1), (x2, y2) = POS[a], POS[b]
        lw = 0.6 + 0.55 * f
        pac = "Panama" in (a, b) and max(x1, x2) > 90
        if pac:
            # trans-Pacific: a flat map cannot draw it as one line, so leave
            # the left edge westward and re-enter from the right edge
            (px, py), (qx, qy) = ((x1, y1), (x2, y2)) if POS[a][0] < 0 else ((x2, y2), (x1, y1))
            ax.plot([px, -118], [py, py + 6], color="#8a95a3", lw=lw, alpha=0.55, ls="--", zorder=1)
            ax.plot([152, qx], [qy + 6, qy], color="#8a95a3", lw=lw, alpha=0.55, ls="--", zorder=1)
            ax.text(-104, py + 9, f"{f:.1f} via Pacific", fontsize=8, color="#13253a", zorder=4,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
            continue
        ax.plot([x1, x2], [y1, y2], color="#8a95a3", lw=lw,
                alpha=0.55, solid_capstyle="round", zorder=1)
        if f >= 1.5:
            spot = None
            for t in (0.5, 0.38, 0.62, 0.28, 0.72, 0.2, 0.8):
                tx, ty = x1 + t * (x2 - x1), y1 + t * (y2 - y1)
                if free(tx, ty):
                    spot = (tx, ty); break
            if spot is None:
                continue                      # nowhere clear: leave it to the table
            placed.append(spot)
            ax.text(spot[0], spot[1], f"{f:.1f}", fontsize=8,
                    ha="center", va="center", color="#13253a", zorder=4,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
    # chokepoints: diamond. Colour = traffic compared with the model's own normal:
    # pale = at or below normal, darkening only as it carries MORE than normal.
    cmap_c = plt.get_cmap("Blues")
    for c, d in snap["chokepoints"].items():
        x, y = POS[c]
        if d["closed"]:
            ax.scatter(x, y, marker="D", s=170, c="#c1272d", edgecolors="#13253a", zorder=3)
            lab = f"{c}\nCLOSED"
        else:
            over = max(0.0, min(d["stress"] - 1.0, 1.0))      # 0 at normal, 1 at double
            ax.scatter(x, y, marker="D", s=170, c=[cmap_c(0.15 + 0.8 * over)],
                       edgecolors="#13253a", zorder=3)
            nm = d["model_normal"]
            if d["open"] < 1.0:
                lab = f"{c}  {d['open']:.0%} open\n{d['used']:.1f} (normally {nm:.1f})"
            elif d["capacity"] is not None and d["used"] >= d["capacity"] - 0.01:
                lab = f"{c}  AT LIMIT\n{d['used']:.1f} of {d['capacity']:.1f} (normally {nm:.1f})"
            else:
                lab = f"{c}\n{d['used']:.1f} (normally {nm:.1f})"
        _label(ax, c, x, y, lab, fontsize=7.5, color="#13253a")
    # producers: square
    for o, ex in snap["exports"].items():
        if o not in POS or ex < 0.01:
            continue
        x, y = POS[o]
        ax.scatter(x, y, marker="s", s=150, c="#e8a046", edgecolors="#13253a", zorder=3)
        dx, dy, ha, va = LABEL.get(o, (0, 3.5, "center", "bottom"))
        ax.text(x + dx, y + dy, f"{o.replace('_P', '')} exports\n{ex:.1f}", fontsize=7.5,
                ha=ha, va=va, color="#96560a", zorder=5)
    # consumers: circle, colour = share unserved
    cmap_r = plt.get_cmap("Oranges")
    for r, d in snap["regions"].items():
        x, y = POS[r]
        short = 1 - d["supplied"]
        ax.scatter(x, y, marker="o", s=330, c=[cmap_r(0.12 + 0.85 * min(short * 2, 1))],
                   edgecolors="#13253a", linewidths=1.2, zorder=3)
        _label(ax, r, x, y, f"{r}\n{d['supplied']:.0%} of demand met", fontsize=8,
               fontweight="bold", color="#13253a")
    # legend: what each shape and colour means
    from matplotlib.lines import Line2D
    handles = [
        Line2D([], [], marker="o", ls="", ms=11, mfc="#fde7d4", mec="#13253a", label="Region (consumer): all demand met"),
        Line2D([], [], marker="o", ls="", ms=11, mfc="#e0590b", mec="#13253a", label="Region (consumer): darker = more demand unmet"),
        Line2D([], [], marker="s", ls="", ms=10, mfc="#e8a046", mec="#13253a", label="Region's export side (producer)"),
        Line2D([], [], marker="D", ls="", ms=9, mfc="#9ecae1", mec="#13253a", label="Chokepoint (sea passage, not a region): normal traffic or less"),
        Line2D([], [], marker="D", ls="", ms=9, mfc="#08519c", mec="#13253a", label="Chokepoint: darker = more traffic than normal"),
        Line2D([], [], marker="D", ls="", ms=9, mfc="#c1272d", mec="#13253a", label="Chokepoint: closed"),
        Line2D([], [], color="#8a95a3", lw=4, label="Route: thicker = more oil (mb/d)"),
    ]
    if legend:   # once per figure, below the map so it covers nothing
        ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.02),
                  ncol=4, fontsize=8.5, frameon=False)
    ax.set_title(title, fontsize=12, loc="left")
    ax.set_xlim(-118, 152); ax.set_ylim(-48, 76)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color("#d8cfc0")
    ax.set_facecolor("#f5f2ec")


def draw(scenarios, fname="network_map.png", out=None):
    """scenarios: list of (title, snapshot). One panel each, stacked."""
    out = out or FIG_DIR
    fig, axes = plt.subplots(len(scenarios), 1, figsize=(16, 7.2 * len(scenarios)))
    axes = np.atleast_1d(axes)
    for i, (ax, (title, snap)) in enumerate(zip(axes, scenarios)):
        draw_panel(ax, snap, title, legend=(i == len(scenarios) - 1))
    fig.tight_layout()
    path = os.path.join(out, fname)
    fig.savefig(path, dpi=110, bbox_inches="tight")   # keeps the legend below the map
    return fig, path


if __name__ == "__main__":
    normal = snapshot(1.0)
    q2 = snapshot(4.9 / 20.9)
    print("=" * 30, "NORMAL (Hormuz open)", "=" * 30)
    print_tables(normal)
    print("\n" + "=" * 25, "Q2 2026 (Hormuz 77% blocked)", "=" * 25)
    print_tables(q2)
    draw([("Normal: Hormuz open", normal),
          ("Q2 2026: Hormuz 77% blocked (4.9 of 20.9 mb/d flowing)", q2)])
    print("\nSaved figures/network_map.png")
