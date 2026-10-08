"""
trace_model.py - follow ONE scenario through the whole model, step by step,
printing every number and the formula that produced it.
CITS4403 - Raed

Run from src/:   python trace_model.py          (Hormuz 70% closed)
                 python trace_model.py 0.55     (any share CLOSED, 0..1)

The order of the printout is the order of the program:
  LAYER 1  routing      oil_network_model.py  allocate_flows() + step()
  LAYER 2  market       oil_network_model.py  clear_market()
  LAYER 3  production   production_cascade.py run_production_cascade()
"""
import sys                                                    # read the closure from the command line
import numpy as np                                            # maths
from oil_model_data import *                                  # every input number
from oil_network_model import OilNetworkModel, ROUTES, REGIONS, REGION_DEMAND, ORIGIN_SUPPLY
from production_cascade import run_production_cascade         # Layer 3

closed = float(sys.argv[1]) if len(sys.argv) > 1 else 0.70     # share of Hormuz CLOSED
open_frac = 1.0 - closed                                      # the model works with the OPEN share
line = "=" * 78

print(line); print(f"SCENARIO: Hormuz {closed:.0%} closed  ->  hormuz_open_fraction = {open_frac:.2f}"); print(line)

# ---- run the model to steady state, keeping the last day ----
m = OilNetworkModel()                                         # fresh model, everyone normal
for _ in range(150):                                          # 150 simulated days
    unserved, used, delivered = m.step(open_frac)             # each day: Layer 1 routing + shortfall

# ======================================================================
print("\nLAYER 1 - ROUTING  (oil_network_model.py: allocate_flows)\n")
print(f"Limits today: Hormuz = normal flow x open share = {CHOKEPOINTS['Hormuz'][0]} x {open_frac:.2f} "
      f"= {CHOKEPOINTS['Hormuz'][0]*open_frac:.2f} mb/d.  Straits: no limit.  Canals: Suez 10.0, Panama 3.5.")
print(f"Shared pipeline budgets: Saudi East-West {SAUDI_EASTWEST_CAPACITY}, ADCOP {ADCOP_CAPACITY} mb/d.\n")

print("STEP 1 - DOMESTIC FIRST:  take = min(own production, own demand)")
print(f"  {'region':<12}{'produces':>9}{'demands':>9}{'uses own':>10}{'left to export':>16}{'must import':>13}")
for r in REGIONS:
    p, d = PRODUCTION_BY_REGION[r], REGION_DEMAND[r]
    take = min(ORIGIN_SUPPLY[r + "_P"], d)                    # Russia-west only, for CIS
    print(f"  {r:<12}{p:9.1f}{d:9.1f}{take:10.1f}{max(0, ORIGIN_SUPPLY[r+'_P']-take):16.1f}{max(0, d-take):13.1f}")
print(f"  (East Siberia, {CIS_EAST_PRODUCTION} mb/d, is export-only and has no demand of its own)\n")

print("STEP 2 - SPLIT EACH EXPORTER'S SURPLUS:  spot = surplus x spot share; the rest is contracted")
for o in m.last_spot:
    tot = m.last_spot[o] + m.last_contracted[o]
    if tot > 0.01:
        print(f"  {o.replace('_P',''):<11} surplus {tot:5.2f} = contracted {m.last_contracted[o]:5.2f}"
              f" + spot {m.last_spot[o]:5.2f}   (spot share {CONTESTABLE_FRACTION.get(o[:-2],0):.2f})")

print("\nSTEP 3 - STAGE 1, CONTRACTED OIL, FASTEST ROUTE FIRST")
print("  each route sends: min(buyer still needs, producer's contracted oil left, room on the path,")
print("                        tankers left, route/pipeline room)")
for k in sorted(ROUTES, key=lambda k: ROUTES[k][3]):
    f = m.last_stage1_flow.get(k, 0.0)
    if f > 0.005:
        print(f"  {ROUTES[k][3]:3d} days  {k:<24}{f:6.2f}")
print("  Still short after Stage 1:",
      {r: round(v, 2) for r, v in m.last_stage1_shortfall.items() if v > 0.005} or "nobody")

print("\nSTEP 4 - STAGE 2, SPOT OIL, ONE QUEUE BY NETBACK")
print("  bid:      premium = 1 + 4 x (short / demand)^2")
for r, v in m.last_stage1_shortfall.items():
    if v > 0.005:
        print(f"            {r:<11} 1 + 4 x ({v:.2f}/{REGION_DEMAND[r]:.1f})^2 = {m.premium[r]:.2f}")
print("  netback:  premium - 0.01 x voyage days.  Top of the queue:")
for nb, k in m.last_bids[:8]:
    print(f"            {nb:6.3f}  {k}")
print("  Spot oil actually sent (final flow - Stage 1 flow):")
for k in ROUTES:
    s2 = m.last_route_flow[k] - m.last_stage1_flow.get(k, 0.0)
    if s2 > 0.005:
        print(f"            {k:<24}{s2:6.2f}")

print("\nSTEP 5 - SCORE THE DAY (step):  shortfall = demand - delivered x complexity uplift")
print(f"  uplift = 1 + 0.15 x (NCI - {NCI_MIN}) / ({NCI_MAX} - {NCI_MIN})")
print(f"  {'region':<12}{'demand':>8}{'got':>8}{'NCI':>6}{'uplift':>8}{'effective':>11}{'short':>8}{'met':>6}")
for r in REGIONS:
    w = np.clip((REGION_NCI[r] - NCI_MIN) / (NCI_MAX - NCI_MIN), 0.02, 1)
    print(f"  {r:<12}{REGION_DEMAND[r]:8.1f}{delivered[r]:8.2f}{REGION_NCI[r]:6.1f}{1+0.15*w:8.3f}"
          f"{delivered[r]*(1+0.15*w):11.2f}{unserved[r]:8.2f}{1-unserved[r]/REGION_DEMAND[r]:6.0%}")

print("\n  Flow through each chokepoint (normal = EIA 2023):")
for c in CHOKEPOINTS:
    print(f"            {c:<20}{used[c]:6.2f}   (normal {CHOKEPOINTS[c][0]})")

# ======================================================================
short = sum(unserved.values())
print(f"\n{line}\nLAYER 2 - MARKET  (oil_network_model.py: clear_market)\n")
print(f"Total physical shortfall from Layer 1: {short:.2f} mb/d")
price, dem = m.clear_market(sum(REGION_DEMAND.values()) - short)
print(f"Find the price p where  sum(demand_r x p^elasticity_r) = {sum(REGION_DEMAND.values()):.1f} - {short:.2f}")
print(f"  ->  p = {price:.2f}x pre-crisis  =  Brent ${69*price:.0f}/bbl")
print(f"  {'region':<12}{'elasticity':>11}{'demand at p':>13}{'cut by price':>14}")
for r in REGIONS:
    print(f"  {r:<12}{PRICE_ELASTICITY[r]:11.2f}{dem[r]:13.2f}{REGION_DEMAND[r]-dem[r]:14.2f}")
print("  NOTE: these cuts are NOT fed back into Layer 1 - the routing uses full demand every day.")

# ======================================================================
print(f"\n{line}\nLAYER 3 - PRODUCTION  (production_cascade.py: run_production_cascade)\n")
print("Input to Layer 3 for each region:  oil_available = 1 - short / demand   (from Layer 1)")
print(f"  {'region':<12}{'oil_available':>14}{'systemic loss':>15}")
worst_r, worst_l = None, -1
for r in REGIONS:
    oa = 1 - unserved[r] / REGION_DEMAND[r]
    sl, _ = run_production_cascade(oa)
    if sl > worst_l:
        worst_r, worst_l = r, sl
    print(f"  {r:<12}{oa:14.1%}{sl:15.1%}{'   <-- above 10%: SYSTEMIC' if sl > 0.10 else ''}")
print(f"\nWorst region: {worst_r}, systemic loss {worst_l:.1%}.")
print("The THRESHOLD (53.1%) is the closure at which this worst value first passes 10%.")
print("For one region's sector-by-sector detail:  from production_cascade import explain_cascade")
