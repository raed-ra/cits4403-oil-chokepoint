"""
oil_network_model.py — NETWORK cascade model of chokepoint disruption
CITS4403 — Raed

This replaces the arithmetic version. It is a genuine complex-systems model:

  NETWORK      regions connected by maritime ROUTES, each route passing through
               real chokepoints with finite capacity (EIA data).
  CONGESTION   when a chokepoint closes, flows reroute onto alternatives until
               THOSE saturate -> second-wave failures (cascade through the net).
  DISCONTINUITY refineries cannot run below MIN_OPERATING_RATE; below it they
               SHUT DOWN entirely. Supply loss -> step changes, not pro-rata.
  CONTENTION   all regions bid for the same scarce non-Gulf supply; allocation
               is competitive, so some buyers are squeezed out completely.
  FEEDBACK     shortage -> precautionary hoarding -> effective demand RISES ->
               worse shortage. Positive feedback, like a bank run.
  HYSTERESIS   a shut refinery needs RESTART_DAYS to come back, so the system's
               state depends on its history, not just current supply.

None of these are predictable by subtraction; they interact.
"""

import numpy as np
import networkx as nx
from oil_model_data import *


# ----------------------------------------------------------------------
# Network definition: regions, routes, and which chokepoints each uses
# ----------------------------------------------------------------------
# route -> (origin, destination, [chokepoints used], transit days)
ROUTES = {
    # name: (origin, destination, chokepoints, days, route_capacity or None)
    # Origins carry a "_P" suffix so producer and consumer nodes stay distinct.
    # Domestic consumption is served before routing and needs no route.

    # ---- Middle East: through Hormuz ----
    "ME->India":            ("MidEast_P", "India",      ["Hormuz"], 6, None),
    "ME->OtherAsia":        ("MidEast_P", "OtherAsia",  ["Hormuz", "Malacca"], 16, None),
    "ME->China":            ("MidEast_P", "China",      ["Hormuz", "Malacca"], 20, None),
    "ME->JapanKorea":       ("MidEast_P", "JapanKorea", ["Hormuz", "Malacca"], 22, None),
    "ME->Europe (Suez)":    ("MidEast_P", "Europe",     ["Hormuz", "Bab el-Mandeb", "Suez+SUMED"], 18, None),
    "ME->Europe (Cape)":    ("MidEast_P", "Europe",     ["Hormuz", "Cape of Good Hope"], 33, None),
    "ME->Africa":           ("MidEast_P", "Africa",     ["Hormuz", "Bab el-Mandeb"], 14, None),
    "ME->NAmerica":         ("MidEast_P", "NAmerica",   ["Hormuz", "Bab el-Mandeb", "Suez+SUMED"], 35, None),
    # ---- Middle East: bypassing Hormuz ----
    # Saudi East-West pipeline to Yanbu, then out via the Red Sea.
    # All three legs share ONE 5.0 mb/d pipeline budget.
    "SaudiPipe->Europe":    ("MidEast_P", "Europe",     ["Bab el-Mandeb", "Suez+SUMED"], 16, 5.0),
    "SaudiPipe->India":     ("MidEast_P", "India",      ["Bab el-Mandeb"], 10, 5.0),
    "SaudiPipe->China":     ("MidEast_P", "China",      ["Bab el-Mandeb", "Malacca"], 24, 5.0),
    # UAE ADCOP to Fujairah - avoids Hormuz AND Bab el-Mandeb. Shared 1.5 budget.
    "ADCOP->India":         ("MidEast_P", "India",      [], 6, 1.5),
    "ADCOP->China":         ("MidEast_P", "China",      ["Malacca"], 21, 1.5),

    # ---- CIS (Russia, Kazakhstan) ----
    "CIS->Europe (Baltic)": ("CIS_P", "Europe",     ["Danish Straits"], 5, 2.5),
    "CIS->Europe (BlackSea)":("CIS_P", "Europe",    ["Turkish Straits"], 7, None),
    # East Siberian fields: ESPO pipeline + Kozmino port. Physically can only
    # reach China and the Pacific - a separate origin so Europe can't bid for it.
    "CISEast->China (ESPO)":("CISEast_P", "China",      [], 10, None),
    "CISEast->JapanKorea":  ("CISEast_P", "JapanKorea", [], 6, None),
    "CIS->India":           ("CIS_P", "India",      ["Turkish Straits", "Suez+SUMED", "Bab el-Mandeb"], 28, None),

    # ---- North America ----
    "NA->LatAm":            ("NAmerica_P", "LatAm",      [], 6, None),
    "NA->Europe":           ("NAmerica_P", "Europe",     [], 12, None),
    "NA->JapanKorea":       ("NAmerica_P", "JapanKorea", ["Panama"], 25, None),
    "NA->OtherAsia":        ("NAmerica_P", "OtherAsia",  ["Panama"], 25, None),
    "NA->India":            ("NAmerica_P", "India",      ["Cape of Good Hope"], 35, None),
    "NA->China":            ("NAmerica_P", "China",      ["Cape of Good Hope", "Malacca"], 45, None),

    # ---- Africa (mostly West African, Atlantic-facing) ----
    "AF->Europe":           ("Africa_P", "Europe",    [], 12, None),
    "AF->NAmerica":         ("Africa_P", "NAmerica",  [], 14, None),
    "AF->India":            ("Africa_P", "India",     ["Cape of Good Hope"], 22, None),
    "AF->OtherAsia":        ("Africa_P", "OtherAsia", ["Cape of Good Hope", "Malacca"], 28, None),
    "AF->China":            ("Africa_P", "China",     ["Cape of Good Hope", "Malacca"], 30, None),

    # ---- Latin America ----
    "LA->NAmerica":         ("LatAm_P", "NAmerica", [], 8, None),
    "LA->Europe":           ("LatAm_P", "Europe",   [], 15, None),
    "LA->India":            ("LatAm_P", "India",    ["Cape of Good Hope"], 35, None),
    "LA->China":            ("LatAm_P", "China",    ["Cape of Good Hope", "Malacca"], 40, None),
}

# Pipelines whose legs share one throughput budget
SHARED_PIPELINES = {"SaudiPipe": SAUDI_EASTWEST_CAPACITY, "ADCOP": 1.5}

REGIONS = list(CONSUMPTION_BY_REGION)
REGION_DEMAND = dict(CONSUMPTION_BY_REGION)
ORIGIN_SUPPLY = {r + "_P": PRODUCTION_BY_REGION[r] for r in REGIONS}
# East Siberian production is export-only to the Pacific (ESPO, ~1.8 mb/d)
ORIGIN_SUPPLY["CIS_P"]     -= CIS_EAST_PRODUCTION
ORIGIN_SUPPLY["CISEast_P"]  = CIS_EAST_PRODUCTION

class OilNetworkModel:
    def __init__(self, hoarding=False, min_rate=MIN_OPERATING_RATE,
                 restart_days=RESTART_DAYS, tanker_fleet_days=None,
                 bid_steepness=4.0, redistribution=1.0, seed=0):
        """
        hoarding=False  (default OFF) - when on, regions over-order up to 2x as
            prices rise. Disabled by default because hoarded orders compete for
            supply as if they were real demand, starving other regions
            (Japan/Korea fell to 79% unserved with it on, 2% with it off).
            Kept as a switch for sensitivity analysis.
        redistribution=1.0  (default OFF) - fraction of a region's oil that can
            be moved between refineries. Below 1.0, oil is stranded at shut
            plants. Disabled by default because it strands DOMESTIC production
            too, which feeds domestic refineries directly - it pushed China
            below its own production level. Kept as a switch.
        """
        self.rng = np.random.default_rng(seed)
        self.hoarding = hoarding
        self.bid_steepness = bid_steepness   # how hard scarcity drives bidding
        # How freely crude can be moved BETWEEN refineries within a region.
        # 1.0 = frictionless pooling (unrealistic: grades, pipelines and
        # bilateral contracts are fixed). <1.0 means some supply is STRANDED
        # at refineries that cannot reach minimum operating rate.
        self.redistribution = redistribution
        self.premium = {r: 1.0 for r in REGION_DEMAND}
        self.min_rate = min_rate
        self.restart_days = restart_days

        # build the graph (for structure + any network metrics we want)
        self.G = nx.DiGraph()
        for r, (o, d, cps, days, _rc) in ROUTES.items():
            self.G.add_edge(o, d, route=r, chokepoints=cps, days=days)

        # refinery state per region: fraction of capacity running
        self.running = {r: 1.0 for r in REGION_DEMAND}
        self.shut_timer = {r: 0 for r in REGION_DEMAND}   # days until restart
        self.n_refineries = 12                            # plants per region
        self.shut_count = {r: 0 for r in REGION_DEMAND}   # how many are down
        # precautionary ordering multiplier (hoarding feedback)
        self.order_mult = {r: 1.0 for r in REGION_DEMAND}

        # total tanker capacity, in barrel-days (fleet constraint).
        # Sized so the normal trade pattern just fits.
        if tanker_fleet_days is None:
            base = sum(ORIGIN_SUPPLY.values())
            self.fleet = base * BASE_VOYAGE_DAYS * 1.25   # 25% slack
        else:
            self.fleet = tanker_fleet_days

    # ---------------- routing with congestion + competition ----------------
    def allocate_flows(self, hormuz_open_fraction, extra_closed=None):
        """Allocate the world's oil across routes.

        Step 1 - DOMESTIC FIRST: each region consumes its own production
                 before anything is traded. Domestic oil can never be bid away.
        Step 2 - split each region's EXPORTABLE SURPLUS into a contracted share
                 and a spot (contestable) share.
        Step 3 - STAGE 1: contracted exports, fastest route first.
        Step 4 - STAGE 2: spot exports go to the highest netback (scarcity
                 premium minus freight cost) - desperation weighed against
                 distance, as a trader would.

        No pre-loading: every corridor starts empty and fills with real
        routed traffic.
        """
        cap = {c: CHOKEPOINTS[c][1] for c in CHOKEPOINTS}
        cap["Hormuz"] *= hormuz_open_fraction
        for c, frac in (extra_closed or {}).items():
            cap[c] *= frac

        used = {c: 0.0 for c in CHOKEPOINTS}
        delivered = {r: 0.0 for r in REGIONS}
        fleet_used = 0.0
        supply_left = dict(ORIGIN_SUPPLY)
        want = {r: REGION_DEMAND[r] * self.order_mult[r] for r in REGIONS}
        pipe_left = dict(SHARED_PIPELINES)

        def push(rname, amount):
            """Send `amount` down a route, limited by every constraint."""
            nonlocal fleet_used
            origin, dest, cps, days, route_cap = ROUTES[rname]
            headroom = min([cap[c] - used[c] for c in cps], default=1e9)
            fleet_headroom = (self.fleet - fleet_used) / max(days, 1)
            rc = route_cap if route_cap is not None else 1e9
            pipe = next((p for p in pipe_left if rname.startswith(p)), None)
            if pipe:
                rc = min(rc, pipe_left[pipe])
            flow = max(0.0, min(amount, supply_left.get(origin, 0.0),
                                headroom, fleet_headroom, rc))
            if flow <= 0:
                return 0.0
            for c in cps:
                used[c] += flow
            supply_left[origin] -= flow
            delivered[dest] += flow
            fleet_used += flow * days
            if pipe:
                pipe_left[pipe] -= flow
            return flow

        # ---- Step 1: domestic first ----
        for r in REGIONS:
            take = min(supply_left[r + "_P"], want[r])
            delivered[r] += take
            supply_left[r + "_P"] -= take

        # ---- Step 2: split exportable surplus ----
        spot = {o: supply_left[o] * CONTESTABLE_FRACTION.get(o[:-2], 0.0)
                for o in supply_left}
        for o in supply_left:
            supply_left[o] -= spot[o]

        # ---- Step 3 (Stage 1): contracted exports, fastest first ----
        for rname in sorted(ROUTES, key=lambda k: ROUTES[k][3]):
            dest = ROUTES[rname][1]
            need = want[dest] - delivered[dest]
            if need > 0:
                push(rname, need)

        # ---- Step 4 (Stage 2): spot exports by netback ----
        for o in supply_left:
            supply_left[o] += spot[o]
        shortfall = {r: max(0.0, want[r] - delivered[r]) for r in REGIONS}
        self.premium = {}
        for r in REGIONS:
            frac_short = shortfall[r] / REGION_DEMAND[r] if REGION_DEMAND[r] else 0
            self.premium[r] = 1.0 + self.bid_steepness * frac_short ** 2

        FREIGHT = 0.01            # premium-units per transit day
        for r in sorted(REGIONS, key=lambda x: -self.premium[x]):
            if shortfall[r] <= 0:
                continue
            cand = [k for k in ROUTES if ROUTES[k][1] == r]
            cand.sort(key=lambda k: -(self.premium[r] - FREIGHT * ROUTES[k][3]))
            for rname in cand:
                if shortfall[r] <= 0:
                    break
                shortfall[r] -= push(rname, shortfall[r])

        return delivered, used, want

    # ---------------- market clearing (price finds equilibrium) ----------------
    def clear_market(self, available):
        """Find the global price at which demand equals available supply.

        Oil is globally arbitraged, so there is ONE price. Price rises until
        enough demand is destroyed to match supply. Because short-run demand
        is very inelastic (-0.05 to -0.18), a small shortfall requires a LARGE
        price rise - which is why oil shocks produce price spikes.

        Regions with higher elasticity (more price-sensitive) bear more of the
        demand destruction: the burden falls on whoever can least afford to pay.
        """
        # Constant-elasticity demand, the standard form, matching
        # price_dynamics.py and spr_depletion.py:   demand_r = D_r * price^e_r
        # Solve sum_r D_r * price^e_r = available for price, by bisection.
        def total_demand(p):
            return sum(REGION_DEMAND[r] * p ** PRICE_ELASTICITY[r]
                       for r in REGION_DEMAND)
        if total_demand(1.0) <= available:
            price = 1.0
        else:
            lo, hi = 1.0, 2.0
            while total_demand(hi) > available and hi < 1e4:
                hi *= 2
            for _ in range(80):
                mid = 0.5 * (lo + hi)
                if total_demand(mid) > available:
                    lo = mid
                else:
                    hi = mid
            price = hi
        demand = {r: REGION_DEMAND[r] * price ** PRICE_ELASTICITY[r]
                  for r in REGION_DEMAND}
        return price, demand

    # ---------------- one timestep ----------------
    def step(self, hormuz_open_fraction, price_trend=0.0, extra_closed=None):
        delivered, used, want = self.allocate_flows(hormuz_open_fraction, extra_closed)

        unserved = {}
        for r in REGION_DEMAND:
            base_need = REGION_DEMAND[r]
            got = delivered[r]

            # --- grade substitution ability (regional refinery complexity) ---
            width = np.clip((REGION_NCI[r] - NCI_MIN) / (NCI_MAX - NCI_MIN), 0.02, 1)
            effective = got * (1.0 + 0.15 * width)   # complex refiners extract more

            # --- DISCONTINUITY: each region has N refineries, each with a
            # minimum operating rate. Operators CONCENTRATE scarce crude into
            # some plants and SHUT others, rather than running all at low rate.
            n_ref = self.n_refineries
            cap_each = base_need / n_ref
            supply = effective

            # refineries already down stay down until their restart timer ends
            down = self.shut_count[r]
            if down > 0:
                self.shut_timer[r] -= 1
                if self.shut_timer[r] <= 0:          # HYSTERESIS ends
                    self.shut_count[r] = 0
                    self.shut_timer[r] = 0

            available = n_ref - self.shut_count[r]
            # how many refineries can be run at >= min_rate on this supply?
            can_run = int(supply // (cap_each * self.min_rate))
            can_run = min(can_run, available)

            newly_shut = available - can_run
            if newly_shut > 0:
                self.shut_count[r] = min(n_ref, self.shut_count[r] + newly_shut)
                self.shut_timer[r] = self.restart_days

            # --- REDISTRIBUTION FRICTION ---
            # Only a fraction of regional supply can be pooled and steered to
            # the refineries that can still run; the rest is stranded at plants
            # that fall below minimum operating rate.
            if supply < n_ref * cap_each * self.min_rate:
                poolable = supply * self.redistribution
                can_run = min(available, int(poolable // (cap_each * self.min_rate)))
                served = min(poolable, can_run * cap_each)   # stranded share lost
            else:
                served = min(supply, can_run * cap_each)
            self.running[r] = served / base_need if base_need else 1.0
            unserved[r] = max(0.0, base_need - served)

            # --- FEEDBACK: precautionary hoarding ---
            # Driven by EXPECTED PRICE, not by a region's own shortfall.
            # A region that is fully supplied today still buys ahead when it
            # sees prices climbing - this is why hoarding is contagious in a
            # way physical shortage is not.
            if self.hoarding:
                own_short = unserved[r] / base_need if base_need else 0
                # price_trend = recent rate of price increase (global signal)
                expectation = HOARDING_SENSITIVITY * (price_trend * 8.0 + own_short)
                target = 1.0 + expectation
                self.order_mult[r] += 0.15 * (target - self.order_mult[r])
                self.order_mult[r] = float(np.clip(self.order_mult[r], 1.0, 2.0))

        return unserved, used, delivered

    def run(self, hormuz_open_fraction, days=180):
        hist = {"unserved": [], "chokepoints": [], "running": []}
        for _ in range(days):
            unserved, used, delivered = self.step(hormuz_open_fraction)
            hist["unserved"].append(sum(unserved.values()))
            hist["chokepoints"].append(dict(used))
            hist["running"].append(dict(self.running))
        return hist


if __name__ == "__main__":
    print("Regions:", list(REGION_DEMAND), "demand mb/d:",
          {k: round(v, 1) for k, v in REGION_DEMAND.items()})
    print("Origins:", {k: round(v, 1) for k, v in ORIGIN_SUPPLY.items()})
    print("Routes:", len(ROUTES), "| Chokepoints:", len(CHOKEPOINTS))

    # quick check: normal operation vs full closure
    for frac, label in [(1.0, "strait OPEN"), (0.0, "strait CLOSED")]:
        m = OilNetworkModel()
        h = m.run(frac, days=120)
        print(f"\n{label}: mean unserved {np.mean(h['unserved']):.2f} mb/d, "
              f"final {h['unserved'][-1]:.2f}")
        final_cp = h["chokepoints"][-1]
        print("  chokepoint use:", {k: round(v, 1) for k, v in final_cp.items() if v > 0.1})
