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

import os                                                               # file paths
import numpy as np                                                      # maths
import matplotlib.pyplot as plt                                         # drawing

from oil_model_data import (CHOKEPOINTS, PRODUCTION_BY_REGION, REGIONAL_RESERVES)  # data the tables show
from oil_network_model import OilNetworkModel, ROUTES, REGIONS, REGION_DEMAND, ORIGIN_SUPPLY  # the network model

FIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figures")  # the project's figures/ folder
os.makedirs(FIG_DIR, exist_ok=True)                                     # create it if missing

# Schematic positions (roughly longitude, latitude). Producer nodes are offset
# from their region's consumer node so both can be seen.
POS = {                                                                 # map position of every node
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
LABEL = {                                                               # label positions for crowded nodes
    "Danish Straits": (0, 4, "center", "bottom"),
    "Turkish Straits": (4, 0, "left", "center"),
    "Suez+SUMED": (-4, 0, "right", "center"),
    "MidEast_P": (4, 0, "left", "center"),
    "CIS_P": (0, 4, "center", "bottom"),
    "CISEast_P": (0, 4, "center", "bottom"),
}

def _label(ax, node, x, y, text, **kw):
    """Write a node's label, using LABEL's offset for crowded nodes."""
    dx, dy, ha, va = LABEL.get(node, (0, -5, "center", "top"))          # this node's label offset (default: below)
    ax.text(x + dx, y + dy, text, ha=ha, va=va, zorder=5, **kw)         # write the label


_BASE = {}                                                              # cache: the normal flows, worked out once
def _model_normal():
    """The model's own flow through each passage with Hormuz fully open - its
    equilibrium. Used as 'normal' when colouring how busy a passage is."""
    if not _BASE:                                                       # not worked out yet?
        m = OilNetworkModel()                                           # a fresh model
        _, used, _ = m.allocate_flows(1.0)                              # one day with Hormuz fully open
        _BASE.update(used)                                              # remember each passage's normal flow
    return _BASE                                                        # the normal flows


def snapshot(hormuz_open=1.0, extra_closed=None, days=150, reserves=False):
    """Run one scenario to steady state; return the value of every node and edge.

    reserves=False : shortfalls BEFORE any strategic reserve is drawn (the network
                     model itself has no reserves).
    reserves=True  : each region draws on its own reserve every day, at its maximum
                     rate, until it runs out; the snapshot shows the result on the
                     final day.
    """
    from oil_model_data import REGIONAL_DRAW_RATE                       # reserve draw rates
    m = OilNetworkModel()                                               # fresh model
    left = dict(REGIONAL_RESERVES)                                      # reserves remaining
    draw = {r: 0.0 for r in REGIONS}                                    # reserve oil drawn per region
    for _ in range(days):                                               # run the scenario day by day
        unserved, used, delivered = m.step(hormuz_open, extra_closed=extra_closed)  # one day of routing
        if reserves:                                                    # if reserves are switched on...
            for r, miss in unserved.items():                            # each region's shortfall
                draw[r] = min(miss, REGIONAL_DRAW_RATE.get(r, 0.0), max(0.0, left.get(r, 0.0)))  # draw: the need, the rate limit, what is left
                left[r] = left.get(r, 0.0) - draw[r]                    # take it out of the reserve
    delivered = {r: delivered[r] + draw[r] for r in REGIONS}            # reserve oil counts as delivered
    unserved = {r: unserved[r] - draw[r] for r in REGIONS}              # ...and reduces the shortfall

    # allowed flow through each passage: canals have a capacity, straits do not;
    # a closure lets through (% open) x normal flow - same rule as the model
    cap = {c: CHOKEPOINTS[c][1] for c in CHOKEPOINTS}                   # each passage's capacity (None = no limit)
    open_frac = {c: 1.0 for c in CHOKEPOINTS}                           # how open each passage is (1.0 = fully)
    open_frac["Hormuz"] = hormuz_open                                   # Hormuz's open share
    cap["Hormuz"] = CHOKEPOINTS["Hormuz"][0] * hormuz_open              # Hormuz limit = normal flow x open share
    for c, f in (extra_closed or {}).items():                           # any other passage closed
        open_frac[c] = f                                                # its open share
        lim = CHOKEPOINTS[c][0] * f                                     # its limit, from its normal flow
        cap[c] = lim if cap[c] is None else min(cap[c], lim)            # keep the tighter limit
    base = _model_normal()                                              # the normal flows, for comparison

    regions = {}                                                        # one entry per region
    for r in REGIONS:                                                   # for each region...
        domestic = min(PRODUCTION_BY_REGION[r], REGION_DEMAND[r])       # how much it covers from its own production
        regions[r] = dict(produces=PRODUCTION_BY_REGION[r], consumes=REGION_DEMAND[r],  # everything the region table shows
                          domestic=domestic, imported=delivered[r] - domestic,
                          delivered=delivered[r], unserved=unserved[r],
                          # same definition the model uses for damage: share of demand
                          # met AFTER the refinery-complexity uplift
                          supplied=1.0 - unserved[r] / REGION_DEMAND[r],  # share of demand met
                          reserve=REGIONAL_RESERVES.get(r, 0.0),        # its reserve size
                          reserve_draw=draw[r], reserve_left=left.get(r, 0.0))
    chokepoints = {}                                                    # one entry per chokepoint
    for c in CHOKEPOINTS:                                               # for each passage...
        b = base[c]                                                     # its normal flow in the model
        if b > 0.05:                                                    # normally used?
            stress = used[c] / b                       # 1.0 = same as normal
        else:                                                           # normally unused:
            stress = 2.0 if used[c] > 0.05 else 0.0    # normally unused
        chokepoints[c] = dict(normal=CHOKEPOINTS[c][0], model_normal=b, capacity=cap[c],  # everything the chokepoint table shows
                              open=open_frac[c], used=used[c], stress=stress,
                              closed=(cap[c] is not None and cap[c] < 1e-9))
    routes = {k: dict(origin=v[0], dest=v[1], via=v[2], days=v[3],      # one entry per route, with its flow
                      flow=m.last_route_flow.get(k, 0.0)) for k, v in ROUTES.items()}
    exports = {o: sum(rt["flow"] for rt in routes.values() if rt["origin"] == o)  # total exports of each producer
               for o in ORIGIN_SUPPLY}
    return dict(regions=regions, chokepoints=chokepoints, routes=routes,  # the whole snapshot
                exports=exports, hormuz_open=hormuz_open, extra_closed=extra_closed,
                reserves=reserves, days=days)


def print_tables(snap, active_only=True):
    """Print three tables from a snapshot: regions, chokepoints, routes."""
    tag = (f"WITH reserves drawn (day {snap['days']})" if snap["reserves"]  # say whether reserves are included
           else "BEFORE any reserve release")
    print(f"REGIONS (consumer nodes), mb/d  -  {tag}")                  # table 1: regions
    print(f"{'region':<12}{'produce':>8}{'consume':>8}{'domestic':>9}{'import':>8}"  # column headings
          f"{'reserve':>8}{'got':>7}{'short':>7}{'met':>6}{'reserve left':>13}")
    for r, d in snap["regions"].items():                                # one row per region
        print(f"{r:<12}{d['produces']:8.1f}{d['consumes']:8.1f}{d['domestic']:9.1f}"  # its numbers
              f"{d['delivered']-d['domestic']-d['reserve_draw']:8.1f}{d['reserve_draw']:8.1f}"
              f"{d['delivered']:7.1f}{d['unserved']:7.2f}{d['supplied']:6.0%}"
              f"{d['reserve_left']:10.0f} Mb")

    print("  'got' is crude received; 'short' and 'met' include the refinery-complexity\n"  # a note on the columns
          "  uplift (complex refineries get up to 15% more product per barrel), so\n"
          "  got + short can be slightly less than consume.")
    print("\nCHOKEPOINTS (passage nodes), mb/d")                        # table 2: chokepoints
    print(f"{'chokepoint':<20}{'EIA normal':>11}{'model normal':>13}{'open':>6}"  # column headings
          f"{'limit now':>10}{'flow':>7}{'vs normal':>10}")
    for c, d in snap["chokepoints"].items():                            # one row per passage
        lim = "none" if d["capacity"] is None else f"{d['capacity']:.1f}"  # 'none' for open straits
        vs = "closed" if d["closed"] else (f"{d['stress']:.0%}" if d["model_normal"] > 0.05  # traffic compared with normal
                                           else ("new" if d["used"] > 0.05 else "-"))
        print(f"{c:<20}{d['normal']:11.1f}{d['model_normal']:13.2f}{d['open']:6.0%}"  # its numbers
              f"{lim:>10}{d['used']:7.2f}{vs:>10}")
    print("  Straits have no capacity limit (open water); canals (Suez, Panama) do.\n"  # a note on the columns
          "  'vs normal' = flow now / the model's own flow with Hormuz open.")

    print("\nROUTES (edges), mb/d" + ("  - only routes carrying oil" if active_only else ""))  # table 3: routes
    print(f"{'route':<24}{'via':<36}{'days':>5}{'flow':>7}")            # column headings
    for k, d in sorted(snap["routes"].items(), key=lambda x: -x[1]["flow"]):  # busiest route first
        if active_only and d["flow"] < 0.01:                            # skip routes carrying no oil
            continue
        via = ", ".join(d["via"]) if d["via"] else "(direct)"           # passages on the way
        print(f"{k:<24}{via:<36}{d['days']:5d}{d['flow']:7.2f}")        # its numbers
    print(f"{'TOTAL traded':<65}{sum(d['flow'] for d in snap['routes'].values()):7.2f}")  # total oil traded between regions


def _segments(snap):
    """Add up route flows on each segment of each route's path."""
    seg = {}                                                            # flow on each map segment
    for d in snap["routes"].values():                                   # every route...
        if d["flow"] < 0.01:                                            # ...that carries oil
            continue
        path = [d["origin"]] + list(d["via"]) + [d["dest"]]             # its full path of nodes
        for a, b in zip(path[:-1], path[1:]):                           # each neighbouring pair on the path
            key = tuple(sorted((a, b)))                                 # the segment (same key whichever direction)
            seg[key] = seg.get(key, 0.0) + d["flow"]                    # add this route's flow to it
    return seg                                                          # all segments


def draw_panel(ax, snap, title, legend=False):
    """Draw one map: routes as lines, chokepoints, producers and regions."""
    seg = _segments(snap)                                               # flow on every map segment
    placed = [POS[n] for n in POS]          # keep labels off the markers too
    def free(x, y):                                                     # is a spot clear of other labels?
        # distance in map units, with y stretched to match the panel's shape
        return all(((x - px) / 270) ** 2 + ((y - py) / 124) ** 2 > 0.035 ** 2  # (distance check against every placed label)
                   for px, py in placed)
    # edges: width = flow
    for (a, b), f in seg.items():                                       # for each segment...
        (x1, y1), (x2, y2) = POS[a], POS[b]                             # its two end positions
        lw = 0.6 + 0.55 * f                                             # line width grows with flow
        pac = "Panama" in (a, b) and max(x1, x2) > 90                   # a trans-Pacific Panama segment?
        if pac:
            # trans-Pacific: a flat map cannot draw it as one line, so leave
            # the left edge westward and re-enter from the right edge
            (px, py), (qx, qy) = ((x1, y1), (x2, y2)) if POS[a][0] < 0 else ((x2, y2), (x1, y1))  # which end is in the Americas
            ax.plot([px, -118], [py, py + 6], color="#8a95a3", lw=lw, alpha=0.55, ls="--", zorder=1)
            ax.plot([152, qx], [qy + 6, qy], color="#8a95a3", lw=lw, alpha=0.55, ls="--", zorder=1)
            ax.text(-104, py + 9, f"{f:.1f} via Pacific", fontsize=8, color="#13253a", zorder=4,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
            continue                                                    # done with this segment
        ax.plot([x1, x2], [y1, y2], color="#8a95a3", lw=lw,
                alpha=0.55, solid_capstyle="round", zorder=1)
        if f >= 1.5:                                                    # busy enough to label?
            spot = None                                                 # no spot found yet
            for t in (0.5, 0.38, 0.62, 0.28, 0.72, 0.2, 0.8):           # try points along the line, middle first
                tx, ty = x1 + t * (x2 - x1), y1 + t * (y2 - y1)         # that point
                if free(tx, ty):                                        # clear of other labels?
                    spot = (tx, ty); break                              # use it
            if spot is None:
                continue                      # nowhere clear: leave it to the table
            placed.append(spot)                                         # remember it, so later labels avoid it
            ax.text(spot[0], spot[1], f"{f:.1f}", fontsize=8,           # write the flow number
                    ha="center", va="center", color="#13253a", zorder=4,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
    # chokepoints: diamond. Colour = traffic compared with the model's own normal:
    # pale = at or below normal, darkening only as it carries MORE than normal.
    cmap_c = plt.get_cmap("Blues")                                      # blue colour scale
    for c, d in snap["chokepoints"].items():                            # each chokepoint
        x, y = POS[c]                                                   # its position
        if d["closed"]:                                                 # closed?
            ax.scatter(x, y, marker="D", s=170, c="#c1272d", edgecolors="#13253a", zorder=3)
            lab = f"{c}\nCLOSED"                                        # its label
        else:
            over = max(0.0, min(d["stress"] - 1.0, 1.0))      # 0 at normal, 1 at double
            ax.scatter(x, y, marker="D", s=170, c=[cmap_c(0.15 + 0.8 * over)],  # blue diamond, darker = busier
                       edgecolors="#13253a", zorder=3)
            nm = d["model_normal"]                                      # its normal flow
            if d["open"] < 1.0:                                         # partly closed?
                lab = f"{c}  {d['open']:.0%} open\n{d['used']:.1f} (normally {nm:.1f})"  # show % open
            elif d["capacity"] is not None and d["used"] >= d["capacity"] - 0.01:  # at a canal's limit?
                lab = f"{c}  AT LIMIT\n{d['used']:.1f} of {d['capacity']:.1f} (normally {nm:.1f})"  # say so
            else:
                lab = f"{c}\n{d['used']:.1f} (normally {nm:.1f})"       # flow and normal flow
        _label(ax, c, x, y, lab, fontsize=7.5, color="#13253a")
    # producers: square
    for o, ex in snap["exports"].items():                               # each producer and its exports
        if o not in POS or ex < 0.01:                                   # skip those exporting nothing
            continue
        x, y = POS[o]                                                   # its position
        ax.scatter(x, y, marker="s", s=150, c="#e8a046", edgecolors="#13253a", zorder=3)
        dx, dy, ha, va = LABEL.get(o, (0, 3.5, "center", "bottom"))     # label offset
        ax.text(x + dx, y + dy, f"{o.replace('_P', '')} exports\n{ex:.1f}", fontsize=7.5,  # label: exports in mb/d
                ha=ha, va=va, color="#96560a", zorder=5)
    # consumers: circle, colour = share unserved
    cmap_r = plt.get_cmap("Oranges")                                    # orange colour scale
    for r, d in snap["regions"].items():                                # each region
        x, y = POS[r]                                                   # its position
        short = 1 - d["supplied"]                                       # share of demand unmet
        ax.scatter(x, y, marker="o", s=330, c=[cmap_r(0.12 + 0.85 * min(short * 2, 1))],  # circle, darker = more unmet
                   edgecolors="#13253a", linewidths=1.2, zorder=3)
        _label(ax, r, x, y, f"{r}\n{d['supplied']:.0%} of demand met", fontsize=8,  # label: share of demand met
               fontweight="bold", color="#13253a")
    # legend: what each shape and colour means
    from matplotlib.lines import Line2D                                 # legend entries
    handles = [                                                         # one entry per symbol
        Line2D([], [], marker="o", ls="", ms=11, mfc="#fde7d4", mec="#13253a", label="Region (consumer): all demand met"),
        Line2D([], [], marker="o", ls="", ms=11, mfc="#e0590b", mec="#13253a", label="Region (consumer): darker = more demand unmet"),
        Line2D([], [], marker="s", ls="", ms=10, mfc="#e8a046", mec="#13253a", label="Region's export side (producer)"),
        Line2D([], [], marker="D", ls="", ms=9, mfc="#9ecae1", mec="#13253a", label="Chokepoint (sea passage, not a region): normal traffic or less"),
        Line2D([], [], marker="D", ls="", ms=9, mfc="#08519c", mec="#13253a", label="Chokepoint: darker = more traffic than normal"),
        Line2D([], [], marker="D", ls="", ms=9, mfc="#c1272d", mec="#13253a", label="Chokepoint: closed"),
        Line2D([], [], color="#8a95a3", lw=4, label="Route: thicker = more oil (mb/d)"),
    ]
    if legend:   # once per figure, below the map so it covers nothing
        ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.02),  # ...placed below the map
                  ncol=4, fontsize=8.5, frameon=False)
    ax.set_title(title, fontsize=12, loc="left")                        # title
    ax.set_xlim(-118, 152); ax.set_ylim(-48, 76)                        # map limits
    ax.set_xticks([]); ax.set_yticks([])                                # no axis numbers
    for sp in ax.spines.values():                                       # border colour
        sp.set_color("#d8cfc0")
    ax.set_facecolor("#f5f2ec")


def draw(scenarios, fname="network_map.png", out=None):
    """scenarios: list of (title, snapshot). One panel each, stacked."""
    out = out or FIG_DIR                                                # default save folder
    fig, axes = plt.subplots(len(scenarios), 1, figsize=(16, 7.2 * len(scenarios)))  # one panel per scenario, stacked
    axes = np.atleast_1d(axes)                                          # works even for a single panel
    for i, (ax, (title, snap)) in enumerate(zip(axes, scenarios)):      # each panel and its scenario
        draw_panel(ax, snap, title, legend=(i == len(scenarios) - 1))   # draw it; legend on the last one
    fig.tight_layout()                                                  # tidy spacing
    path = os.path.join(out, fname)                                     # where to save
    fig.savefig(path, dpi=110, bbox_inches="tight")   # keeps the legend below the map
    return fig, path                                                    # the figure and its path


if __name__ == "__main__":                                              # only when run directly
    normal = snapshot(1.0)                                              # Hormuz open
    q2 = snapshot(4.9 / 20.9)                                           # the Q2 2026 closure
    print("=" * 30, "NORMAL (Hormuz open)", "=" * 30)
    print_tables(normal)                                                # tables for the normal case
    print("\n" + "=" * 25, "Q2 2026 (Hormuz 77% blocked)", "=" * 25)
    print_tables(q2)                                                    # tables for Q2 2026
    draw([("Normal: Hormuz open", normal),                              # draw both maps
          ("Q2 2026: Hormuz 77% blocked (4.9 of 20.9 mb/d flowing)", q2)])
    print("\nSaved figures/network_map.png")
