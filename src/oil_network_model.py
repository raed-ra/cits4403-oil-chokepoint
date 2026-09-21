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
    "Gulf->Asia (Hormuz+Malacca)":  ("Gulf", "Asia",   ["Hormuz", "Malacca"], 20),
    "Gulf->Europe (Hormuz+Suez)":   ("Gulf", "Europe", ["Hormuz", "Bab el-Mandeb", "Suez+SUMED"], 18),
    "Gulf->Asia (Cape detour)":     ("Gulf", "Asia",   ["Hormuz", "Cape of Good Hope"], 34),
    "Gulf->Europe (Cape detour)":   ("Gulf", "Europe", ["Hormuz", "Cape of Good Hope"], 33),
    "RedSea->Asia (bypass pipe)":   ("Gulf", "Asia",   ["Bab el-Mandeb", "Malacca"], 24),
    "RedSea->Europe (bypass pipe)": ("Gulf", "Europe", ["Bab el-Mandeb", "Suez+SUMED"], 16),
    "Atlantic->Europe":             ("Atlantic", "Europe", [], 10),
    "Atlantic->Asia (Cape)":        ("Atlantic", "Asia", ["Cape of Good Hope"], 30),
    "Domestic->NAmerica":           ("NAmDomestic", "NAmerica", [], 3),
    "Atlantic->NAmerica":           ("Atlantic", "NAmerica", [], 6),
    "Russia->Europe (Danish)":      ("Russia", "Europe", ["Danish Straits"], 5),
    "Russia->Asia":                 ("Russia", "Asia", ["Malacca"], 18),
}

# consuming regions and their demand (mb/d), aggregated from EIA country data
REGION_DEMAND = {
    "Asia":     CONSUMPTION["China"] + CONSUMPTION["India"] + CONSUMPTION["Japan"]
                + CONSUMPTION["South Korea"],
    "Europe":   CONSUMPTION["Germany"] * 4.0,        # proxy for European total
    "NAmerica": CONSUMPTION["USA"] + CONSUMPTION["Canada"],
}
# regional refinery complexity (average NCI) -> substitution ability
REGION_NCI = {"Asia": 8.5, "Europe": 8.5, "NAmerica": 11.0}

# supply available at each origin (mb/d)
ORIGIN_SUPPLY = {
    "Gulf":     sum(PRODUCTION[c] for c in GULF_PRODUCERS if c in PRODUCTION),
    # US domestic crude serves North America first (it is domestic, not traded
    # for on the open market in a crisis). Only the EXPORT SURPLUS is contested.
    "NAmDomestic": PRODUCTION["USA"] + PRODUCTION["Canada"],
    "Atlantic":    PRODUCTION["Brazil"] + 3.0,   # Brazil + West Africa/other exports
    "Russia":      PRODUCTION["Russia"],
}


class OilNetworkModel:
    def __init__(self, hoarding=True, min_rate=MIN_OPERATING_RATE,
                 restart_days=RESTART_DAYS, tanker_fleet_days=None,
                 bid_steepness=4.0, redistribution=0.6, seed=0):
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
        for r, (o, d, cps, days) in ROUTES.items():
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
        """Two-stage allocation.

        Stage 1 - dedicated supply: each region draws on origins only it can
        practically reach, cheapest route first, subject to chokepoint capacity.

        Stage 2 - CONTESTED supply (Atlantic barrels, reachable by everyone):
        allocated by WILLINGNESS TO PAY. A region short of oil bids up, and
        can outbid a comfortable region for cargoes it was previously getting.
        This is the price-mediated contagion channel: Asia loses Gulf crude,
        bids for Atlantic crude, and Europe is squeezed even though none of
        its own shipping routes were touched.
        """
        cap = {c: CHOKEPOINTS[c][1] for c in CHOKEPOINTS}
        cap["Hormuz"] *= hormuz_open_fraction
        for c, frac in (extra_closed or {}).items():
            cap[c] *= frac

        used = {c: 0.0 for c in CHOKEPOINTS}
        delivered = {r: 0.0 for r in REGION_DEMAND}
        fleet_used = 0.0
        supply_left = dict(ORIGIN_SUPPLY)
        want = {r: REGION_DEMAND[r] * self.order_mult[r] for r in REGION_DEMAND}

        def push(rname, amount):
            """Send `amount` down a route if capacity and fleet allow."""
            nonlocal fleet_used
            origin, dest, cps, days = ROUTES[rname]
            headroom = min([cap[c] - used[c] for c in cps], default=1e9)
            fleet_headroom = (self.fleet - fleet_used) / days
            flow = max(0.0, min(amount, supply_left.get(origin, 0.0),
                                headroom, fleet_headroom))
            if flow <= 0:
                return 0.0
            for c in cps:
                used[c] += flow
            supply_left[origin] -= flow
            delivered[dest] += flow
            fleet_used += flow * days
            return flow

        # ---- Stage 1: dedicated (non-Atlantic) supply, fastest route first ----
        dedicated = [k for k in ROUTES if ROUTES[k][0] != "Atlantic"]
        for rname in sorted(dedicated, key=lambda k: ROUTES[k][3]):
            dest = ROUTES[rname][1]
            if dest not in delivered:
                continue
            need = want[dest] - delivered[dest]
            if need > 0:
                push(rname, need)

        # ---- Stage 2: CONTESTED Atlantic supply, allocated by bid ----
        atlantic_routes = {ROUTES[k][1]: k for k in ROUTES
                           if ROUTES[k][0] == "Atlantic"}
        shortfall = {r: max(0.0, want[r] - delivered[r]) for r in REGION_DEMAND}

        # willingness to pay rises steeply with scarcity (desperate buyers bid up)
        self.premium = {}
        for r in REGION_DEMAND:
            frac_short = shortfall[r] / REGION_DEMAND[r] if REGION_DEMAND[r] else 0
            # relative scarcity premium index (NOT a $ price forecast)
            self.premium[r] = 1.0 + self.bid_steepness * frac_short ** 2

        # allocate the contested pool in order of who bids most
        for r in sorted(REGION_DEMAND, key=lambda x: -self.premium[x]):
            if shortfall[r] <= 0 or r not in atlantic_routes:
                continue
            push(atlantic_routes[r], shortfall[r])

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
        price = 1.0
        for _ in range(400):
            demand = {r: REGION_DEMAND[r] * (1 + PRICE_ELASTICITY[r] * (price - 1))
                      for r in REGION_DEMAND}
            demand = {r: max(0.0, d) for r, d in demand.items()}
            total = sum(demand.values())
            if total <= available + 1e-6:
                break
            price *= 1.01                       # bid price up until it clears
            if price > 50:                      # runaway: demand too inelastic
                break
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
