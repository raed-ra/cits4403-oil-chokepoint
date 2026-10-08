"""
layer_diagrams.py - Layers 2 and 3 drawn as networks of nodes and edges.
CITS4403 - Raed

Layer 2 (market):     one world price node linked to every region; each region's
                      edge is labelled with its price elasticity. Strategic
                      reserves are nodes attached to their OWN region only.
Layer 3 (production): five sector nodes. Oil (from Layer 1) feeds every sector;
                      sector-to-sector edges are the supplier needs (DEPENDS_ON).
Run from src/:  python layer_diagrams.py
"""
import os                                                               # file paths
import numpy as np                                                      # maths: angles
import matplotlib.pyplot as plt                                         # drawing
from matplotlib.patches import FancyArrowPatch                          # curved arrows
from oil_model_data import PRICE_ELASTICITY, REGIONAL_RESERVES, REGIONAL_DRAW_RATE  # Layer 2 data
from production_cascade import SECTORS, OIL_DEPENDENCE, DEPENDS_ON, OPERABLE_MIN  # Layer 3 data

FIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figures")  # the project's figures/ folder
os.makedirs(FIG_DIR, exist_ok=True)                                     # create it if missing
NAVY, AMBER, RED, BLUE, GREY = "#13253a", "#e8a046", "#c1272d", "#2b6cb0", "#8a95a3"


def _arrow(ax, a, b, text="", color=GREY, lw=1.6, rad=0.0, fs=9, frac=0.5, dashed=False):
    """Draw an arrow from point a to point b, with an optional label."""
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=14, lw=lw, color=color,  # add an arrow shape from a to b
                                 connectionstyle=f"arc3,rad={rad}", shrinkA=26, shrinkB=26,
                                 linestyle="--" if dashed else "-", zorder=1))
    if text:                                                            # if a label was given...
        x, y = a[0] + frac * (b[0] - a[0]), a[1] + frac * (b[1] - a[1])  # ...place it part-way along the arrow
        ax.text(x, y, text, fontsize=fs, ha="center", va="center", color=NAVY, zorder=4,  # draw the label on a white box
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9))


def _node(ax, xy, text, color, size=0.075, tc="white", fs=10):
    """A round node with a label inside it."""
    ax.add_patch(plt.Circle(xy, size, color=color, zorder=2))           # a filled circle
    ax.text(*xy, text, ha="center", va="center", fontsize=fs, color=tc, fontweight="bold", zorder=3)  # its label, centred inside


def draw_layer2(ax):
    """Layer 2: the world market."""
    centre = (0.0, 0.0)                                                 # the middle of the picture
    _node(ax, centre, "ONE world\nprice", NAVY, size=0.17, fs=11)       # the world-price node
    regions = list(PRICE_ELASTICITY)                                    # the ten region names
    for i, r in enumerate(regions):                                   # regions in a circle
        ang = 2 * np.pi * i / len(regions) + np.pi / 2                  # angle for region i, spread evenly round a circle
        xy = (0.62 * np.cos(ang), 0.62 * np.sin(ang))                   # its position on the circle
        _node(ax, xy, r.replace("JapanKorea", "Japan/\nKorea").replace("OtherAsia", "Other\nAsia").replace("NAmerica", "North\nAmerica").replace("MidEast", "Middle\nEast"),  # a node for the region (with a nicer name)
              BLUE, size=0.085, fs=8)
        _arrow(ax, xy, centre, f"e = {PRICE_ELASTICITY[r]:.2f}", frac=0.45, fs=8)  # arrow region -> price, labelled with its elasticity
        if REGIONAL_RESERVES.get(r, 0) > 0:                           # reserve attached to its own region
            rxy = (0.98 * np.cos(ang), 0.98 * np.sin(ang))              # a little further out, same angle
            ax.add_patch(plt.Rectangle((rxy[0] - 0.10, rxy[1] - 0.05), 0.20, 0.10, color=AMBER, zorder=2))  # an amber box for the reserve
            ax.text(*rxy, f"{REGIONAL_RESERVES[r]:.0f} Mb\n{REGIONAL_DRAW_RATE[r]:.1f}/day",  # its size and draw rate
                    ha="center", va="center", fontsize=7, color=NAVY, zorder=3)
            _arrow(ax, rxy, xy, color=AMBER, lw=1.4)                    # arrow reserve -> its own region
    ax.text(0, -1.24, "Circles + lines = clear_market() in oil_network_model.py: regions' demand (elasticity e) -> ONE price.\n"  # the caption underneath
            "Squares = strategic reserves, applied BEFORE it in spr_depletion.py: each covers ONLY its own region's shortfall.\n"
            "Demand cut by price is NOT sent back to Layer 1.",
            ha="center", va="center", fontsize=9, color=NAVY)
    ax.set_title("Layer 2 - the market: reserves, then the price", fontsize=13, loc="left")  # title
    ax.set_xlim(-1.25, 1.25); ax.set_ylim(-1.38, 1.18); ax.set_aspect("equal"); ax.axis("off")  # fit the picture; hide the axes


def draw_layer3(ax):
    """Layer 3: the sector cascade inside ONE region."""
    pos = {"Transport": (0.0, 0.62), "Petrochemicals": (-0.72, 0.05), "Power": (0.72, 0.05),  # where each sector sits
           "Industry": (-0.42, -0.72), "Agri/Residential": (0.42, -0.72)}
    oil = (0.0, 1.30)                                                   # where the oil box sits
    ax.add_patch(plt.Rectangle((oil[0] - 0.42, oil[1] - 0.09), 0.84, 0.18, color=AMBER, zorder=2))  # the amber oil box
    ax.text(*oil, "OIL AVAILABLE (from Layer 1)", ha="center", va="center", fontsize=9,  # its label
            color=NAVY, fontweight="bold", zorder=3)
    for s, xy in pos.items():                                          # oil -> every sector
        _arrow(ax, oil, xy, f"dep {OIL_DEPENDENCE[s]:.2f}", color=AMBER, lw=1.4, frac=0.62, fs=8,  # ...an amber arrow from oil, labelled with oil dependence
               rad=0.0 if s == "Transport" else (0.12 if xy[0] < 0 else -0.12))
    for user, needs in DEPENDS_ON.items():                             # supplier -> user
        for supplier, k in needs.items():                               # each supplier and how much it is needed
            rad = 0.18 if (supplier, user) in [("Transport", "Industry"), ("Power", "Petrochemicals")] else -0.12  # curve some arrows so they do not overlap
            _arrow(ax, pos[supplier], pos[user], f"{k:.2f}", color=RED, lw=1.0 + 2.5 * k, rad=rad, fs=8)  # red arrow supplier -> user; thicker = more needed
    for s, xy in pos.items():                                           # draw each sector node...
        _node(ax, xy, f"{s.replace('/', '/' + chr(10))}\nweight {SECTORS[s]:.2f}", NAVY, size=0.17, fs=8)  # ...with its name and weight
    ax.text(0, -1.20,                                                   # the caption underneath
            "Amber arrows: how oil-dependent each sector is.   Red arrows: supplier sector -> user sector,\n"
            "labelled with how much the user needs it.   Each sector: output = min(direct, upstream) x gate,\n"
            f"gate shuts a sector below ~{OPERABLE_MIN:.0%} of inputs.   OUT: systemic loss = sum(weight x lost output)",
            ha="center", va="center", fontsize=9, color=NAVY)
    ax.set_title("Layer 3 - the production cascade, one region (run_production_cascade)", fontsize=13, loc="left")  # title
    ax.set_xlim(-1.25, 1.25); ax.set_ylim(-1.34, 1.48); ax.set_aspect("equal"); ax.axis("off")  # fit the picture; hide the axes


def draw_all(out=None):
    """Draw both diagrams and save them as PNG files; return their paths."""
    out = out or FIG_DIR                                                # default save folder
    paths = []                                                          # the saved file paths
    for fn, name in [(draw_layer2, "layer2_market.png"), (draw_layer3, "layer3_cascade.png")]:  # each diagram and its file name
        fig, ax = plt.subplots(figsize=(8.4, 8.4))                      # a square canvas
        fn(ax)                                                          # draw the diagram on it
        fig.tight_layout()                                              # tidy spacing
        p = os.path.join(out, name)                                     # where to save it
        fig.savefig(p, dpi=120, bbox_inches="tight")                    # save the picture
        plt.close(fig)                                                  # free the memory
        paths.append(p)                                                 # remember the path
    return paths                                                        # both file paths


if __name__ == "__main__":                                              # only when run directly
    print("saved:", draw_all())                                         # draw both and print where they went
