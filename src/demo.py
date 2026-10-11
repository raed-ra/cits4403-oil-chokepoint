"""
demo.py - live demo: run ANY closure and show the whole answer on one screen.
CITS4403 - Raed

Run from src/:   python demo.py 0.6          (Hormuz 60% closed)
                 python demo.py 0.7 1.0      (Hormuz 70% closed AND Bab el-Mandeb 100% closed)
From the notebook:   from demo import run_demo;  run_demo(0.6)

For each region it prints the share of demand met (Layer 1) and the systemic loss
(Layer 3); then the world shortfall, the Brent price with no reserves (Layer 2), and
whether the closure is systemic (worst region loses more than 10%).
"""
import sys                                                    # read the closures from the command line
from network_view import snapshot, draw                       # Layer 1 to steady state; the map
from closure_sensitivity import steady_state                  # Layer 2: the clearing price
from production_cascade import run_production_cascade         # Layer 3: the sector cascade
from oil_network_model import REGION_DEMAND                   # each region's normal demand

THRESHOLD = 0.531                                             # c* found by bisection (main model)


def run_demo(hormuz_closed=0.6, bab_closed=0.0, show_map=True):
    """Run one closure through all three layers and print the result."""
    extra = {"Bab el-Mandeb": 1.0 - bab_closed} if bab_closed > 0 else None   # the model takes OPEN shares
    snap = snapshot(1.0 - hormuz_closed, extra_closed=extra)  # Layer 1: route the oil, 150 days
    total, _, brent = steady_state(hormuz_closed, bab_closed)  # Layer 2: world shortfall and Brent (no reserves)

    print(f"Hormuz {hormuz_closed:.0%} closed" + (f", Bab el-Mandeb {bab_closed:.0%} closed" if bab_closed else ""))
    print(f"{'region':<12}{'demand met':>11}{'systemic loss':>15}")
    worst_name, worst = None, 0.0                             # the worst-hit region so far
    for r, d in snap["regions"].items():                      # every region...
        x = 1.0 - d["unserved"] / REGION_DEMAND[r]            # ...its share of oil available (Eq. 1, no reserves)
        loss, _ = run_production_cascade(x)                   # Layer 3: its systemic loss
        flag = "  <- systemic" if loss > 0.10 else ""         # more than 10% = systemic
        print(f"{r:<12}{x:>11.0%}{loss:>15.1%}{flag}")
        if loss > worst:                                      # remember the worst region
            worst_name, worst = r, loss
    print(f"\nWorld shortfall: {total:.1f} mb/d    Brent (no reserves): ${brent:.0f}/bbl")
    if worst > 0.10:                                          # the verdict
        print(f"SYSTEMIC: {worst_name} loses {worst:.0%} of its output")
    else:
        print("Not systemic: no region loses more than 10% of its output")
    print(f"(Main-model threshold: {THRESHOLD:.1%} of Hormuz closed)")
    if show_map:                                              # draw the network map
        _, path = draw([(f"Hormuz {hormuz_closed:.0%} closed", snap)], fname="demo_map.png")
        print("Map saved:", path)


if __name__ == "__main__":                                    # only when run directly
    h = float(sys.argv[1]) if len(sys.argv) > 1 else 0.6      # share of Hormuz CLOSED
    b = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0      # share of Bab el-Mandeb CLOSED
    run_demo(h, b)
