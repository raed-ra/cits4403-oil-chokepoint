"""
oil_network_model.py - the physical model of the world oil network (Layers 1 and 2)
CITS4403 - Raed

WHAT IT REPRESENTS
  Nodes   10 consuming regions, 11 producing nodes (each region's export side,
          plus East Siberia), and 8 maritime chokepoints.
  Edges   37 routes. Each route goes producer -> (chokepoints) -> consumer, takes
          a number of days, and may have its own limit (pipelines, terminals).
  Limits  Only engineered things have a capacity: the Saudi and UAE bypass
          pipelines, Russia's Baltic terminals, and the Suez and Panama canals.
          Open sea straits have no limit, only a normal flow. Hormuz is the
          passage we close: x% open lets through x% of its normal flow.

WHAT ONE SIMULATED DAY DOES (step -> allocate_flows)
  1. Domestic first   each region uses its own production before trading.
  2. Split exports    each exporter's surplus is part contracted, part spot.
  3. Stage 1          contracted oil fills the fastest routes first.
  4. Stage 2          spot oil goes to short regions in one queue, ordered by
                      netback (scarcity bid minus freight).
  5. Score the day    shortfall = demand - oil delivered (after the refinery
                      complexity uplift).

SWITCHED OFF BY DEFAULT (implemented, but found to be wrong or never active)
  hoarding        counted stockpiled oil as consumption - starved other regions
  redistribution  stranded domestic oil at shut refineries - impossible result
  refinery shutdown / restart lag - triggers only at deep closures (e.g. Other
  Asia at full closure), and never changes the result: the refineries still
  running process all the oil that arrives (redistribution = 1.0).
"""

import numpy as np                      # maths: clip, mean
from oil_model_data import *            # every number the model uses (see that file)


# ----------------------------------------------------------------------
# THE ROUTES (the edges of the network)
# Each entry:  name: (origin, destination, [chokepoints passed], days, route limit)
#   origin       a producing node; "_P" marks a region's export side
#   destination  a consuming region
#   chokepoints  the passages the voyage goes through, in order
#   days         voyage length - used to order routes and to use up tankers
#   route limit  mb/d limit of the route itself, or None for no limit
# ----------------------------------------------------------------------
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
    # The legs have no cap of their own: crude arriving at Yanbu can be loaded
    # for any destination. They share ONE budget (SHARED_PIPELINES, 7.0 mb/d).
    "SaudiPipe->Europe":    ("MidEast_P", "Europe",     ["Bab el-Mandeb", "Suez+SUMED"], 16, None),
    "SaudiPipe->India":     ("MidEast_P", "India",      ["Bab el-Mandeb"], 10, None),
    "SaudiPipe->China":     ("MidEast_P", "China",      ["Bab el-Mandeb", "Malacca"], 24, None),
    "SaudiPipe->OtherAsia": ("MidEast_P", "OtherAsia",  ["Bab el-Mandeb", "Malacca"], 18, None),
    "SaudiPipe->JapanKorea":("MidEast_P", "JapanKorea", ["Bab el-Mandeb", "Malacca"], 26, None),
    # UAE ADCOP to Fujairah - avoids Hormuz AND Bab el-Mandeb. Shared 1.5 budget.
    "ADCOP->India":         ("MidEast_P", "India",      [], 6, None),
    "ADCOP->China":         ("MidEast_P", "China",      ["Malacca"], 21, None),
    "ADCOP->OtherAsia":     ("MidEast_P", "OtherAsia",  ["Malacca"], 14, None),
    "ADCOP->JapanKorea":    ("MidEast_P", "JapanKorea", ["Malacca"], 22, None),

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

# Pipelines that feed several routes: all their legs share ONE daily budget.
# e.g. every route starting "SaudiPipe..." draws from the same 7.0 mb/d.
SHARED_PIPELINES = {"SaudiPipe": SAUDI_EASTWEST_CAPACITY, "ADCOP": ADCOP_CAPACITY}

REGIONS = list(CONSUMPTION_BY_REGION)            # the 10 consuming regions
REGION_DEMAND = dict(CONSUMPTION_BY_REGION)      # how much oil each region needs, mb/d
ORIGIN_SUPPLY = {r + "_P": PRODUCTION_BY_REGION[r] for r in REGIONS}   # each region's production, as a producer node
ORIGIN_SUPPLY["CIS_P"]     -= CIS_EAST_PRODUCTION   # take East Siberia out of Russia-west...
ORIGIN_SUPPLY["CISEast_P"]  = CIS_EAST_PRODUCTION   # ...and make it its own node (can only reach the Pacific)


class OilNetworkModel:
    """One copy of the world oil system. Create one per scenario, then call
    step() once per simulated day (or run() for many days)."""

    def __init__(self, hoarding=False, min_rate=MIN_OPERATING_RATE,
                 restart_days=RESTART_DAYS, tanker_fleet_days=None,
                 bid_steepness=4.0, redistribution=1.0, seed=0):
        """Set every region to its normal, undisrupted state.

        hoarding        False by default: when on, rising prices make regions
                        order up to 2x their need (found to starve others).
        redistribution  1.0 by default: share of a region's oil that can be moved
                        between its refineries; below 1.0 some is stranded.
        bid_steepness   how sharply a region's bid rises as it runs short.
        """
        self.rng = np.random.default_rng(seed)     # random generator (kept for future use; nothing is random now)
        self.hoarding = hoarding                   # is the hoarding feedback switched on?
        self.bid_steepness = bid_steepness         # the "4" in premium = 1 + 4 x (short/demand)^2
        self.redistribution = redistribution       # 1.0 = oil moves freely between a region's refineries
        self.premium = {r: 1.0 for r in REGION_DEMAND}   # every region starts bidding at 1.0 (not short)
        self.min_rate = min_rate                   # a refinery shuts below this share of its capacity (0.55)
        self.restart_days = restart_days           # days a shut refinery takes to restart


        self.running = {r: 1.0 for r in REGION_DEMAND}     # share of each region's refining that is running (1 = all)
        self.shut_timer = {r: 0 for r in REGION_DEMAND}    # days until shut refineries restart
        self.n_refineries = 12                             # each region is treated as 12 equal refineries
        self.shut_count = {r: 0 for r in REGION_DEMAND}    # how many of those 12 are shut
        self.order_mult = {r: 1.0 for r in REGION_DEMAND}  # hoarding multiplier on demand (1.0 = order exactly what you need)
        self.push_log = None                               # set to [] to record every push (used only by debug_trace.py)

        if tanker_fleet_days is None:                      # if no fleet size was given...
            base = sum(ORIGIN_SUPPLY.values())             # ...take total world supply...
            self.fleet = base * BASE_VOYAGE_DAYS * 1.25    # ...x a typical 20-day voyage x 25% slack = barrel-days of tankers
        else:
            self.fleet = tanker_fleet_days                 # otherwise use the size given

    # ------------------------------------------------------------------
    # LAYER 1: where does the oil go today?
    # ------------------------------------------------------------------
    def allocate_flows(self, hormuz_open_fraction, extra_closed=None):
        """Allocate one day of the world's oil across the routes.

        hormuz_open_fraction  1.0 = Hormuz open, 0.0 = fully closed
        extra_closed          optional {passage: fraction open}, e.g. Bab el-Mandeb
        Returns (delivered per region, flow per chokepoint, demand per region).
        """
        # The limit on each passage today. Straits have no limit (1e9 = effectively infinite);
        # canals keep their capacity.
        cap = {c: (CHOKEPOINTS[c][1] if CHOKEPOINTS[c][1] is not None else 1e9)
               for c in CHOKEPOINTS}
        cap["Hormuz"] = CHOKEPOINTS["Hormuz"][0] * hormuz_open_fraction   # Hormuz: x% open lets through x% of normal flow
        for c, frac in (extra_closed or {}).items():                        # any other passage being closed...
            cap[c] = min(cap[c], CHOKEPOINTS[c][0] * frac)                  # ...same rule, measured against its normal flow

        used = {c: 0.0 for c in CHOKEPOINTS}          # oil sent through each passage so far today
        delivered = {r: 0.0 for r in REGIONS}         # oil each region has received so far today
        fleet_used = 0.0                              # tanker capacity used so far today (barrel-days)
        supply_left = dict(ORIGIN_SUPPLY)             # oil each producer still has to sell
        want = {r: REGION_DEMAND[r] * self.order_mult[r] for r in REGIONS}   # what each region asks for (= demand unless hoarding)
        pipe_left = dict(SHARED_PIPELINES)            # each shared pipeline's budget, full again at the start of the day
        route_flow = {k: 0.0 for k in ROUTES}         # oil sent down each route today (for the tables and map)

        def push(rname, amount):
            """Send up to `amount` down one route; return how much actually went."""
            nonlocal fleet_used                                       # this changes the outer day's tanker total
            origin, dest, cps, days, route_cap = ROUTES[rname]        # unpack the route's definition
            headroom = min([cap[c] - used[c] for c in cps], default=1e9)   # room left in the tightest passage on the path
            fleet_headroom = (self.fleet - fleet_used) / max(days, 1) # tankers left, divided by voyage length
            rc = (route_cap - route_flow[rname]) if route_cap is not None else 1e9   # room left on the route itself (counts both stages)
            pipe = next((p for p in pipe_left if rname.startswith(p)), None)        # does this route draw on a shared pipeline?
            if pipe:
                rc = min(rc, pipe_left[pipe])                         # if so, it can't exceed what's left in that pipeline
            flow = max(0.0, min(amount, supply_left.get(origin, 0.0),  # send the SMALLEST of: what's asked for,
                                headroom, fleet_headroom, rc))         # producer's oil, passage room, tankers, route/pipe room
            if self.push_log is not None:                             # tracing only: record the five limits
                self.push_log.append(dict(route=rname, origin=origin, dest=dest, cps=list(cps), days=days,
                                          need=amount, producer_left=supply_left.get(origin, 0.0),
                                          passage_room=headroom, tanker_room=fleet_headroom,
                                          route_room=rc, pipe=pipe, sent=flow))
            if flow <= 0:
                return 0.0                                            # nothing could move: stop here
            for c in cps:
                used[c] += flow                                       # record the oil in every passage on the path
            supply_left[origin] -= flow                               # the producer has that much less to sell
            delivered[dest] += flow                                   # the buyer has received it
            fleet_used += flow * days                                 # longer voyages tie up more tankers
            if pipe:
                pipe_left[pipe] -= flow                               # and it comes out of the pipeline's shared budget
            route_flow[rname] += flow                                 # remember what this route carried
            return flow                                               # tell the caller how much went

        # ---- Step 1: DOMESTIC FIRST - a region always uses its own oil before trading ----
        for r in REGIONS:
            take = min(supply_left[r + "_P"], want[r])     # use own production, up to own demand
            delivered[r] += take                           # it counts as delivered
            supply_left[r + "_P"] -= take                  # whatever is left over is available to export

        # ---- Step 2: SPLIT each exporter's surplus into spot and contracted oil ----
        spot = {o: supply_left[o] * CONTESTABLE_FRACTION.get(o[:-2], 0.0)   # the spot share (e.g. 35% for the Middle East)
                for o in supply_left}
        for o in supply_left:
            supply_left[o] -= spot[o]                      # hold the spot oil back; only contracted oil is left for Stage 1
        self.last_spot = dict(spot)                        # remember the spot oil (for the trace tools)
        self.last_contracted = dict(supply_left)           # remember the contracted oil (for the trace tools)

        # ---- Step 3: STAGE 1 - contracted oil, fastest route first ----
        for rname in sorted(ROUTES, key=lambda k: ROUTES[k][3]):   # go through routes from shortest voyage to longest
            dest = ROUTES[rname][1]                                # who the route delivers to
            need = want[dest] - delivered[dest]                    # how much that region still needs
            if need > 0:
                push(rname, need)                                  # send as much of it as this route can



        self.last_stage1_flow = dict(route_flow)                   # route flows after Stage 1 (for the trace tools)
        if self.push_log is not None:
            self.push_log.append("STAGE 2")                          # tracing only: mark where Stage 2 starts

        # ---- Step 4: STAGE 2 - spot oil, to the highest bidder ----
        for o in supply_left:
            supply_left[o] += spot[o]                              # release the held-back spot oil
        shortfall = {r: max(0.0, want[r] - delivered[r]) for r in REGIONS}   # who is still short after Stage 1
        self.premium = {}                                          # recompute today's bids
        for r in REGIONS:
            frac_short = shortfall[r] / REGION_DEMAND[r] if REGION_DEMAND[r] else 0   # share of demand still missing
            self.premium[r] = 1.0 + self.bid_steepness * frac_short ** 2         # bid rises with the square of the shortfall

        FREIGHT = 0.01                                             # bid lost per voyage day (freight cost)
        bids = [(self.premium[ROUTES[k][1]] - FREIGHT * ROUTES[k][3], k)   # NETBACK for every (short region, route to it) pair
                for k in ROUTES if shortfall[ROUTES[k][1]] > 0]
        self.last_bids = sorted(bids, reverse=True)                # ONE queue, highest netback first (kept for the trace tools)
        self.last_stage1_shortfall = dict(shortfall)               # Stage-1 shortfalls (for the trace tools)
        for netback, rname in self.last_bids:                      # walk down the queue
            r = ROUTES[rname][1]                                   # the buyer on this route
            if shortfall[r] > 0:                                   # only if that buyer still needs oil...
                shortfall[r] -= push(rname, shortfall[r])          # ...send at most what it still needs, and reduce its need

        self.last_route_flow = route_flow                          # keep today's route flows (read by network_view.py)
        return delivered, used, want                               # oil received, passage flows, demand

    # ------------------------------------------------------------------
    # LAYER 2: what price balances supply and demand?
    # ------------------------------------------------------------------
    def clear_market(self, available):
        """Find the single world price at which total demand equals `available`.

        Demand falls as price rises: demand_r = D_r x price^e_r, where e_r is the
        region's (negative) price elasticity. Short-run demand is very
        inelastic, so a small shortage needs a big price rise.
        Returns (price index, demand per region); 1.0 = pre-crisis price.
        """
        def total_demand(p):                                       # world demand at price index p
            return sum(REGION_DEMAND[r] * p ** PRICE_ELASTICITY[r]
                       for r in REGION_DEMAND)
        if total_demand(1.0) <= available:                         # enough oil at the normal price?
            price = 1.0                                            # then the price doesn't move
        else:
            lo, hi = 1.0, 2.0                                      # search between these two prices
            while total_demand(hi) > available and hi < 1e4:       # double the upper guess until demand falls below supply
                hi *= 2
            for _ in range(80):                                    # bisection: halve the gap 80 times
                mid = 0.5 * (lo + hi)                              # try the middle price
                if total_demand(mid) > available:                  # still too much demand?
                    lo = mid                                       # then the answer is higher
                else:
                    hi = mid                                       # otherwise it's lower
            price = hi                                             # converged price index
        demand = {r: REGION_DEMAND[r] * price ** PRICE_ELASTICITY[r]   # each region's demand at that price
                  for r in REGION_DEMAND}
        return price, demand

    # ------------------------------------------------------------------
    # ONE SIMULATED DAY
    # ------------------------------------------------------------------
    def step(self, hormuz_open_fraction, price_trend=0.0, extra_closed=None):
        """Run one day: allocate oil, then work out each region's shortfall.
        Returns (shortfall per region, flow per chokepoint, delivered per region)."""
        delivered, used, want = self.allocate_flows(hormuz_open_fraction, extra_closed)   # Layer 1: route the oil

        unserved = {}                                      # each region's shortfall today
        for r in REGION_DEMAND:
            base_need = REGION_DEMAND[r]                   # what the region needs (ignoring any hoarding)
            got = delivered[r]                             # crude it actually received

            # Refinery-complexity uplift (a PROXY): complex refineries get up to 15% more
            # usable product per barrel. width = 0 for the simplest, 1 for the most complex.
            width = np.clip((REGION_NCI[r] - NCI_MIN) / (NCI_MAX - NCI_MIN), 0.02, 1)
            effective = got * (1.0 + 0.15 * width)         # crude received, scaled up by the uplift

            # Refinery shutdown: the region is 12 refineries, each needing at least
            # 55% of its capacity to run. (Only at deep closures; the rest then run harder.)
            n_ref = self.n_refineries                      # 12
            cap_each = base_need / n_ref                   # one refinery's capacity
            supply = effective                             # oil available to the refineries

            down = self.shut_count[r]                      # refineries already shut
            if down > 0:
                self.shut_timer[r] -= 1                    # one day closer to restarting
                if self.shut_timer[r] <= 0:                # restart lag over?
                    self.shut_count[r] = 0                 # bring them all back
                    self.shut_timer[r] = 0

            available = n_ref - self.shut_count[r]         # refineries able to run today
            can_run = int(supply // (cap_each * self.min_rate))   # how many could run at least at minimum rate
            can_run = min(can_run, available)              # can't run more than are available

            newly_shut = available - can_run               # the rest must shut
            if newly_shut > 0:
                self.shut_count[r] = min(n_ref, self.shut_count[r] + newly_shut)   # record them as shut
                self.shut_timer[r] = self.restart_days     # and start the restart clock

            if supply < n_ref * cap_each * self.min_rate:  # not enough to run every refinery at minimum?
                poolable = supply * self.redistribution    # oil that can be moved to the running plants (all of it, by default)
                can_run = min(available, int(poolable // (cap_each * self.min_rate)))
                served = min(poolable, can_run * cap_each) # demand those running refineries can meet
            else:
                served = min(supply, can_run * cap_each)   # normal case: meet demand up to refinery capacity
            self.running[r] = served / base_need if base_need else 1.0   # share of the region's demand being met
            unserved[r] = max(0.0, base_need - served)     # THE SHORTFALL: demand that goes unmet

            if self.hoarding:                              # hoarding feedback (off by default)
                own_short = unserved[r] / base_need if base_need else 0          # how short this region is
                expectation = HOARDING_SENSITIVITY * (price_trend * 8.0 + own_short)   # rising prices + own shortage
                target = 1.0 + expectation                                       # how much to over-order
                self.order_mult[r] += 0.15 * (target - self.order_mult[r])       # move 15% of the way towards it
                self.order_mult[r] = float(np.clip(self.order_mult[r], 1.0, 2.0))   # never below 1x or above 2x

        return unserved, used, delivered

    def run(self, hormuz_open_fraction, days=180):
        """Call step() for many days and keep a history of each day."""
        hist = {"unserved": [], "chokepoints": [], "running": []}   # one list per thing we record
        for _ in range(days):                                       # one loop = one simulated day
            unserved, used, delivered = self.step(hormuz_open_fraction)
            hist["unserved"].append(sum(unserved.values()))         # total world shortfall that day
            hist["chokepoints"].append(dict(used))                  # flow through each passage that day
            hist["running"].append(dict(self.running))              # share of demand met in each region
        return hist


if __name__ == "__main__":                                  # only runs when this file is run directly
    print("Regions:", list(REGION_DEMAND), "demand mb/d:",
          {k: round(v, 1) for k, v in REGION_DEMAND.items()})
    print("Origins:", {k: round(v, 1) for k, v in ORIGIN_SUPPLY.items()})
    print("Routes:", len(ROUTES), "| Chokepoints:", len(CHOKEPOINTS))
    for frac, label in [(1.0, "strait OPEN"), (0.0, "strait CLOSED")]:   # quick check: open vs closed
        m = OilNetworkModel()                                # fresh model
        h = m.run(frac, days=120)                            # run 120 days
        print(f"\n{label}: mean unserved {np.mean(h['unserved']):.2f} mb/d, "
              f"final {h['unserved'][-1]:.2f}")
        final_cp = h["chokepoints"][-1]                      # passage flows on the last day
        print("  chokepoint use:", {k: round(v, 1) for k, v in final_cp.items() if v > 0.1})
