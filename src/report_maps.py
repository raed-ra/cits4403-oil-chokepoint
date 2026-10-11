"""
report_maps.py - the two large network maps used in the report (Figures 2 and 3)
and on the slides: same drawing as network_view.py, but bigger text and a few
labels moved so nothing overlaps when the map is printed on one page.
CITS4403 - Raed

Run from src/:   python report_maps.py
Saves figures/map_normal.png (Hormuz open) and figures/map_q2.png (Q2 2026, 77% closed).
"""
import os                                                     # file paths
import matplotlib; matplotlib.use("Agg")                      # draw without opening a window
import matplotlib.pyplot as plt                               # plotting
import network_view as NV                                     # snapshot() and draw_panel()

FIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figures")  # the project's figures/ folder
SCALE = 1.35                                                  # text 35% bigger than network_view's default

NV.LABEL.update({                                             # move the labels that collide at the larger size
    "Europe": (-3, -1, "right", "top"),
    "LatAm": (0, 4, "center", "bottom"),
    "India": (3, 0, "left", "center"),
    "Malacca": (-3, -1, "right", "top"),
    "Hormuz": (3, 1, "left", "center"),
    "OtherAsia": (0, -5, "center", "top"),
    "China": (-3, 0, "right", "center"),
})

for name, title, open_share in [("map_normal.png", "Normal: Hormuz open", 1.0),
                                ("map_q2.png", "Q2 2026: Hormuz 77% blocked (4.9 of 20.9 mb/d flowing)", 4.9 / 20.9)]:
    snap = NV.snapshot(open_share)                            # run the network to steady state
    fig, ax = plt.subplots(figsize=(16, 10.4))                # a tall canvas spreads the labels out
    NV.draw_panel(ax, snap, title, legend=True)               # the same map as network_view.py
    for t in ax.texts:                                        # every label on the map...
        t.set_fontsize(t.get_fontsize() * SCALE)              # ...bigger
        if t.get_bbox_patch() is None:                        # labels without a box get a light backing
            t.set_bbox(dict(fc="#f5f2ec", ec="none", alpha=0.85, pad=0.4))   # so route lines don't cut through them
    for t in ax.get_legend().get_texts():                     # bigger legend text
        t.set_fontsize(t.get_fontsize() * 1.35)
    ax.title.set_fontsize(ax.title.get_fontsize() * 1.4)      # bigger title
    fig.tight_layout()                                        # tidy spacing
    fig.savefig(os.path.join(FIG_DIR, name), dpi=200, bbox_inches="tight")   # save at print quality
    plt.close(fig)                                            # free the memory
    print("saved", name)
