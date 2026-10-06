"""
oil_model_data.py — every number the model uses, and nothing else.
CITS4403 — Raed

Each constant below is read by at least one model function, test, or the
notebook. The comment on each says WHERE it is used, so every number can be
traced from source to code.

Units: mb/d = million barrels per day; Mb = million barrels.

Constants are marked:
  [DATA]       published figure, source given
  [ASSUMPTION] our modelling choice - tested in sensitivity.py where possible
"""

# ======================================================================
# 1. WORLD PRODUCTION AND CONSUMPTION BY REGION                [DATA]
#    TOTAL LIQUIDS on both sides (crude + NGLs + biofuels + refinery gain).
#    The earlier model mixed crude-only production with total-liquids
#    consumption; using one basis throughout is what makes them balance.
#
#    Production: EIA / Visual Capitalist regional totals, 2025
#      (N.America 31.8, Middle East 31.0, Asia-Pacific 9.4, Africa 7.6,
#       Europe 4.0; CIS and Latin America make up the remainder).
#    Consumption: Energy Institute Statistical Review 2024 (world 102.8).
#    Regional splits within these totals are our grouping of country data.
# ======================================================================
PRODUCTION_BY_REGION = {      # mb/d
    "NAmerica":   31.8,   # US 21.9 + Canada 6.2 + Mexico 1.7 (approx)
    "LatAm":       8.4,   # Brazil 4.3, Venezuela, Argentina, Colombia, other
    "Europe":      4.0,   # Norway, UK, other North Sea
    "CIS":        13.8,   # Russia 10.7, Kazakhstan 2.0, Azerbaijan, other
    "MidEast":    31.0,   # Saudi, Iraq, Iran, UAE, Kuwait, Qatar, Oman
    "Africa":      7.6,   # Nigeria, Angola, Libya, Algeria, other
    "China":       5.3,
    "India":       0.9,
    "JapanKorea":  0.1,
    "OtherAsia":   3.1,   # SE Asia, Australia
}
CONSUMPTION_BY_REGION = {     # mb/d
    "NAmerica":   24.6,   # US 20.46, Canada 2.4, Mexico 1.7
    "LatAm":       6.5,
    "Europe":     14.5,   # (the old model used Germany x 4 = 8.2 - too low)
    "CIS":         4.8,   # Russia 3.8 + others
    "MidEast":     9.5,
    "Africa":      4.4,
    "China":      16.4,
    "India":       5.6,
    "JapanKorea":  5.7,   # Japan 3.1, South Korea 2.6
    "OtherAsia":  10.0,
}
# Production (~106) exceeds consumption (~102) by ~4 mb/d: the 2025
# oversupply plus statistical differences. Most of the surplus is in the
# Middle East - so in a Hormuz closure it is trapped behind the strait.

WORLD_CONSUMPTION = 102.8   # mb/d, 2024 [DATA, EIA]

# East Siberian production (ESPO system) - counted in CIS above, but it can
# only physically reach China and the Pacific, never Europe.  [DATA, approx]
CIS_EAST_PRODUCTION = 1.8   # mb/d

# ======================================================================
# 2. CHOKEPOINTS                                       [DATA + ASSUMPTION]
#    Used by allocate_flows() as the capacity limit on every route,
#    and by topology_comparison.py to build the network graph.
#
#    (normal flow, capacity) in mb/d
#    - normal flow is EIA data (World Oil Transit Chokepoints, 2023)
#    - capacity is OUR ASSUMPTION: observed flow plus a margin. A sea strait
#      has no hard physical ceiling the way a pipeline does; for Hormuz the
#      real limit is upstream production, not strait width.
# ======================================================================
CHOKEPOINTS = {
    "Hormuz":            (20.9, 21.5),
    "Malacca":           (23.7, 25.0),
    "Suez+SUMED":        (8.8,  10.0),
    "Bab el-Mandeb":     (8.6,  10.0),
    "Cape of Good Hope": (6.0,  15.0),   # open ocean - large margin
    "Danish Straits":    (4.9,  5.5),
    "Turkish Straits":   (3.4,  4.0),
    "Panama":            (2.1,  3.5),
}

HORMUZ_TOTAL_FLOW = 20.0    # mb/d [DATA, EIA]  used: production_cascade
# ~20% of world consumption - now also ~20% of the modelled system.
HORMUZ_SHARE_GLOBAL = 0.20

# ======================================================================
# 3. (PRE-LOADING REMOVED)
#    With the whole world's production and consumption now modelled,
#    corridors start empty and fill with real routed traffic. No
#    unmodelled traffic needs to be reserved.
# ======================================================================

# ======================================================================
# 4. BYPASS PIPELINES                                        [DATA]
#    SAUDI_EASTWEST_CAPACITY limits the two Red Sea pipeline routes in
#    allocate_flows() (they share one budget). Source: EIA chokepoints.
#    The UAE ADCOP limit (1.5 mb/d) is set directly on its route.
# ======================================================================
SAUDI_EASTWEST_CAPACITY = 7.0   # [DATA] 2026: second line converted from NGL
                                # to crude, raising stated capacity from 5 to 7
                                # mb/d. NOTE: actual 2026 throughput was lower -
                                # a drone strike cut 0.7 mb/d (Apr) and Yanbu
                                # loadings halted (Sep).
BYPASS_CAPACITY_MIN = 3.5   # notebook context: EIA total bypass range
BYPASS_CAPACITY_MAX = 5.5

# ======================================================================
# 5. CONTESTABLE SUPPLY                                      [ASSUMPTION]
#    allocate_flows() Stage 1 hands out the non-contestable share by
#    route speed; Stage 2 auctions the contestable share by bid.
# ======================================================================
CONTESTABLE_FRACTION = {    # share of a region's EXPORTS sold on the spot market
    "NAmerica":   0.60,   # US exports are largely spot
    "LatAm":      0.80,
    "Europe":     0.50,
    "CIS":        0.50,   # high - post-2022 redirection from Europe to Asia
    "CISEast":    0.30,   # ESPO largely term-contracted to China
    "MidEast":    0.35,   # mostly term contracts
    "Africa":     0.90,   # West African crude is almost entirely spot
    "China":      0.00, "India": 0.00, "JapanKorea": 0.00, "OtherAsia": 0.00,
}
# Domestic consumption is ALWAYS served from own production first and can
# never be bid away - contestability applies only to the exportable surplus.

# ======================================================================
# 6. REFINERY BEHAVIOUR                                      [ASSUMPTION]
#    All used in step().
# ======================================================================
MIN_OPERATING_RATE = 0.55  # refineries cannot run below ~55% (industry norm)
RESTART_DAYS       = 14    # days to restart a shut refinery
NCI_MIN, NCI_MAX   = 5.0, 21.0   # Nelson Complexity Index span (OGJ/EIA)
                                 # scales the small NCI efficiency uplift
BASE_VOYAGE_DAYS   = 20    # typical Gulf-Asia voyage; sizes the tanker fleet

REGION_NCI = {   # average Nelson Complexity Index   [ASSUMPTION]
    "NAmerica": 11.0, "Europe": 8.5, "China": 8.0, "India": 11.0,
    "JapanKorea": 9.0, "OtherAsia": 6.5, "LatAm": 7.0, "Africa": 5.0,
    "MidEast": 7.0, "CIS": 6.0,
}

# ======================================================================
# 7. MARKET BEHAVIOUR
#    PRICE_ELASTICITY used in step(), price_dynamics, spr_depletion.
# ======================================================================
HOARDING_SENSITIVITY = 0.6     # [ASSUMPTION] how hard buyers over-order

PRICE_ELASTICITY = {           # short-run, by region
    "NAmerica":   -0.05,  # [DATA] Ghouri (2001): USA -0.045, Canada -0.06
    "Europe":     -0.09,  # [DATA] within Cooper (2003) range
    "JapanKorea": -0.06,  # [ASSUMPTION] developed economy
    "China":      -0.12,  # [ASSUMPTION]
    "India":      -0.20,  # [ASSUMPTION] developing - fuel a larger income share
    "OtherAsia":  -0.20,  # [ASSUMPTION]
    "LatAm":      -0.15,  # [ASSUMPTION]
    "Africa":     -0.25,  # [ASSUMPTION] most price-sensitive
    "MidEast":    -0.08,  # [ASSUMPTION] heavily subsidised fuel
    "CIS":        -0.10,  # [ASSUMPTION]
}

# ======================================================================
# 8. STRATEGIC RESERVES                                [DATA + ASSUMPTION]
#    Used by simulate_with_reserve() in spr_depletion.py.
#    Each region draws ONLY on its own reserve.
# ======================================================================
SPR_PRECRISIS    = 415.4   # Mb, US SPR Feb 2026        [DATA, EIA WPSR]
SPR_CURRENT      = 285.0   # Mb, US SPR Sep 2026        [DATA, EIA WPSR]
SPR_MAX_WITHDRAW = 2.7     # mb/d, US physical limit    [DATA, DOE]

REGIONAL_RESERVES = {      # Mb
    "China":      1400.0,  # [DATA*] EIA estimate - China publishes nothing
    "JapanKorea":  449.0,  # [DATA] Japan 380 (govt+industry) + S.Korea 69
    "NAmerica":    285.0,  # [DATA] US SPR
    "Europe":      179.0,  # [DATA] OECD Europe government stocks (IEA)
    "India":        39.0,  # [DATA] ISPRL
    "OtherAsia":    50.0,  # [ASSUMPTION] small national stocks
    "LatAm": 0.0, "Africa": 0.0, "MidEast": 0.0, "CIS": 0.0,
    # producers hold their oil in the ground, not in strategic tanks
}
REGIONAL_DRAW_RATE = {     # mb/d
    "NAmerica":   2.7,     # [DATA] DOE physical limit
    "China":      4.0,     # [ASSUMPTION] scaled by stock size
    "JapanKorea": 2.0,     # [ASSUMPTION]
    "Europe":     1.5,     # [ASSUMPTION]
    "India":      0.5,     # [ASSUMPTION]
    "OtherAsia":  0.3,     # [ASSUMPTION]
    "LatAm": 0.0, "Africa": 0.0, "MidEast": 0.0, "CIS": 0.0,
}

# ======================================================================
# 9. VALIDATION TARGETS                                      [DATA]
#    NOT fed into the model. Used only in the notebook to check the
#    model's predictions against what actually happened.
#    Source: EIA Short-Term Energy Outlook, Aug 2026 (Q2 2026 flows).
# ======================================================================
OBSERVED_2026_Q2 = {
    "Hormuz": 4.9, "Malacca": 16.6, "Cape of Good Hope": 9.4,
    "Bab el-Mandeb": 8.1, "Suez+SUMED": 5.8, "Danish Straits": 4.7,
    "Turkish Straits": 4.1, "Panama": 3.2,
}

# ======================================================================
# COVERAGE NOTE
# The model now covers the whole world: ~106 mb/d production, ~102 mb/d
# consumption across ten regions. Hormuz (20 mb/d) is ~20% of the modelled
# system, matching its real share. Percentages are now world-relative.
# ======================================================================

# ======================================================================
# SOURCES (full list with links in data/DATA_AND_SOURCES.md)
#   EIA International Energy Statistics (production, consumption)
#   EIA World Oil Transit Chokepoints, 2024 (chokepoint flows, bypass)
#   EIA Short-Term Energy Outlook, Aug 2026 (observed Q2 2026 flows)
#   EIA Weekly Petroleum Status Report (US SPR levels)
#   EIA Today in Energy, Apr 2026 (China, Japan, Europe reserves)
#   DOE SPR Quick Facts (2.7 mb/d withdrawal limit)
#   Cooper (2003); Ghouri (2001) (price elasticities)
#   Oil & Gas Journal; EIA (Nelson Complexity Index range)
# ======================================================================
