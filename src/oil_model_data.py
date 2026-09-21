"""
oil_model_data.py  —  CALIBRATED REAL-WORLD DATA FOUNDATION
CITS4403 Project (Option 2: Oil Chokepoint Disruption) — Raed

Every constant below is a REAL, published figure with its source recorded in
SOURCES (bottom of file). This is the calibration layer: the model imports
these instead of using invented numbers.

Units: mb/d = million barrels per day; Mb = million barrels.
All figures are 2024-2026 vintage (see each source). The model is a STYLISED
representation calibrated to these aggregates — not a reconstruction of every
cargo movement (same stance as Zhang et al. 2026, Mathematics 14:1708).
"""

# ======================================================================
# 1. STRAIT OF HORMUZ FLOW
# ======================================================================
HORMUZ_TOTAL_FLOW   = 20.0    # mb/d total oil (crude + products), 2024-25   [S1,S2,S3]
HORMUZ_CRUDE_FLOW   = 15.0    # mb/d crude oil + condensate                  [S3]
HORMUZ_PRODUCT_FLOW = 5.5     # mb/d refined products                        [S3]
HORMUZ_SHARE_GLOBAL = 0.20    # ~20% of global petroleum liquids consumption [S1,S2]

# ======================================================================
# 2. BYPASS CAPACITY (the real cap on rerouting)
# ======================================================================
BYPASS_CAPACITY_MIN = 3.5     # mb/d  (Saudi East-West + UAE ADCOP, low est.) [S2,S4]
BYPASS_CAPACITY_MAX = 5.5     # mb/d  (same, high/max theoretical est.)       [S2,S4]
# Note: covers only ~a quarter of Hormuz flow; 5 Gulf producers (Iraq, Kuwait,
# Qatar, Bahrain, Iran) have ZERO pipeline bypass.                           [S4]

# ======================================================================
# 3. US STRATEGIC PETROLEUM RESERVE (SPR)  — the reserve-release lever
# ======================================================================
SPR_PRECRISIS       = 415.4   # Mb, week ending 2026-02-27 (pre-closure)     [S5]
SPR_CURRENT         = 285.0   # Mb, week ending 2026-09-11 (lowest since '82)[S5,S6]
SPR_DRAWDOWN        = 130.5   # Mb released Feb->Sep 2026                     [S5]
SPR_CAPACITY        = 714.0   # Mb design capacity                           [S6]
SPR_MAX_WITHDRAW    = 2.7     # mb/d  MAXIMUM withdrawal rate (key constraint)[S7]
# IEA coordinated release announced 2026-03-11: 400 Mb (426 Mb confirmed),
# largest in IEA history; US share 172.2 Mb.                                 [S5,S8]

# ======================================================================
# 4. PERSIAN GULF CRUDE GRADES  (the grade axis: API gravity, sulphur %)
#    Gulf crude is overwhelmingly MEDIUM-HEAVY SOUR.
# ======================================================================
# grade name -> (API gravity, sulphur %)                                    [S9,S10,S11]
CRUDE_GRADES = {
    "Arab Light":    (33.0, 1.8),
    "Arab Medium":   (27.8, 2.75),
    "Arab Heavy":    (27.0, 2.8),
    "Basrah Light":  (31.4, 2.74),
    "Basrah Medium": (27.9, 3.0),
    "Basrah Heavy":  (24.0, 4.05),
    "Iranian Heavy": (30.0, 1.9),
    "Dubai":         (31.0, 2.0),
}
# Classification: heavy < 25 API; medium 25-34 API; light > 34 API.
# Sour if sulphur > 0.5%. (All Gulf grades above are sour.)                  [S10]
# Contrast grades reachable if the strait closes (non-Gulf):
NON_GULF_GRADES = {
    "WTI (US light sweet)":    (39.6, 0.24),   # very different -> hard to substitute [S11]
    "Brent (North Sea)":       (38.0, 0.37),                                   # [S11]
    "Venezuela Merey (heavy)": (16.0, 2.5),    # heavy sour; US Gulf refiners  [S11]
}

# ======================================================================
# 5. PRODUCTION & CONSUMPTION BY COUNTRY (2025, EIA)
# ======================================================================
# country -> crude production mb/d (incl. lease condensate)                  [S12,S13]
PRODUCTION = {
    "USA": 13.59, "Russia": 9.89, "Saudi Arabia": 9.56, "Canada": 4.94,
    "China": 4.34, "Iraq": 4.30, "Iran": 3.30, "UAE": 3.20,
    "Brazil": 3.74, "Kuwait": 2.60,
}
# country -> petroleum liquids consumption mb/d                              [S12,S14]
CONSUMPTION = {
    "USA": 20.31, "China": 16.19, "India": 5.27, "Russia": 3.86,
    "Saudi Arabia": 3.52, "Brazil": 3.16, "Japan": 3.14,
    "South Korea": 2.54, "Iran": 2.42, "Canada": 2.38, "Germany": 2.06,
}
WORLD_CONSUMPTION = 102.8     # mb/d, 2024                                    [S14]
WORLD_DEMAND_2025 = 105.0     # mb/d, 2025 demand incl. biofuels             [S15]

# Gulf producers whose exports transit Hormuz (behind the chokepoint):
GULF_PRODUCERS = ["Saudi Arabia", "Iraq", "Iran", "UAE", "Kuwait", "Qatar"]
SAUDI_HORMUZ_SHARE = 0.40     # Saudi ~40% of Hormuz oil exports             [S3]

# ======================================================================
# 6. REFINERIES — capacity and NELSON COMPLEXITY INDEX (NCI)
#    NCI is the real-world measure of refinery FLEXIBILITY: it scores
#    secondary conversion capacity. Higher NCI => can process heavier,
#    sourer crude => more able to substitute grades.                  [S16,S17]
# ======================================================================
WORLD_REFINING_CAPACITY = 74.0   # mb/d global distillation capacity         [S16]
WORLD_AVG_NCI           = 5.9    # global average complexity index           [S16]

# Real refineries: name -> (capacity mb/d, NCI, region)                 [S17-S20]
REFINERIES = {
    "Jamnagar (India)":      (1.24, 21.1, "Asia"),    # world's largest, most complex
    "Vadinar (India)":       (0.405, 11.8, "Asia"),   # upgraded to run 80% heavy/ultra-heavy
    "Beaumont (USA)":        (0.634, 9.0,  "N.America"),
    "Gdansk (Poland)":       (0.210, 11.1, "Europe"),
    "Nanticoke (Canada)":    (0.1135, 9.82, "N.America"),
    "Montreal (Canada)":     (0.137, 9.0,  "N.America"),
    "PBF average (USA)":     (1.00, 13.2, "N.America"),
    "Ferndale (USA)":        (0.105, 7.0,  "N.America"),  # low end, Phillips 66
    "Los Angeles (USA)":     (0.139, 14.1, "N.America"),  # high end, Phillips 66
}
# NCI interpretation used in the model:
#   NCI ~5-7   : simple (hydroskimming) - needs light sweet crude, LOW flexibility
#   NCI ~9-12  : moderately complex - can take medium sour
#   NCI 13-21  : highly complex (coking/hydrocracking) - can take heavy sour,
#                HIGH flexibility (can substitute almost any grade)
NCI_MIN, NCI_MAX = 5.0, 21.0     # observed real range                       [S17-S20]


# ======================================================================
# 7. HORMUZ FLOWS BY DESTINATION  (EIA, Q1 2025) — who actually depends on it
#    This is what makes the impact ASYMMETRIC: Asia is devastated, the US
#    barely notices.                                                    [S21-S23]
# ======================================================================
HORMUZ_DESTINATION_SHARE = {
    "China":       0.377,   # largest single destination by a wide margin
    "India":       0.147,
    "South Korea": 0.120,
    "Japan":       0.109,
    "Other Asia":  0.139,
    "USA":         0.025,   # only 2.5% - diversified supply, domestic production
    "Europe":      0.040,   # ~600 kb/d
}
HORMUZ_ASIA_SHARE = 0.892   # 89.2% of Hormuz crude goes to Asia         [S21]
# Cross-check: EIA puts China+India+Japan+S.Korea at 69% of Hormuz crude  [S23]
# Japan is extreme: ~95% of its crude comes from the Middle East          [S24]

# ======================================================================
# 8. REGIONAL REFINERY COMPLEXITY (average NCI by region)
#    Asian refineries were largely built to run Gulf medium-sour crude;
#    US Gulf Coast refineries were configured for heavy sour (Venezuelan/
#    Mexican). Simple hydroskimming refineries need light sweet.
#    NOTE: these are ESTIMATES informed by the refinery sample in
#    REFINERIES above and the world average of 5.9 - they are NOT a
#    published per-region series. State this as an assumption.      [S16-S20]
# ======================================================================
REGIONAL_NCI = {
    "China":       8.0,    # mixed fleet, large newer complex capacity
    "India":       11.0,   # Jamnagar 21.1 / Vadinar 11.8 pull this up
    "South Korea": 10.0,   # large export-oriented complex refineries
    "Japan":       7.5,    # older, less complex, very ME-dependent
    "Other Asia":  6.5,
    "USA":         11.0,   # Gulf Coast built for heavy sour  (PBF avg 13.2)
    "Europe":      8.5,
}


# ======================================================================
# 9. MARITIME CHOKEPOINT NETWORK  (EIA) — the real inter-regional routes
#    Each route between regions passes through one or more chokepoints,
#    each with a finite throughput. This is what creates CONGESTION
#    CASCADE: close one, flows pile onto others until they saturate. [S26,S27]
# ======================================================================
# chokepoint -> (normal flow mb/d 2023, practical capacity mb/d)
CHOKEPOINTS = {
    "Hormuz":       (20.9, 21.5),
    "Malacca":      (23.7, 25.0),
    "Suez+SUMED":   (8.8,  10.0),
    "Bab el-Mandeb":(8.6,  10.0),
    "Cape of Good Hope": (6.0, 15.0),   # not a chokepoint - spare capacity, but SLOW
    "Danish Straits":(4.9,  5.5),
    "Turkish Straits":(3.4, 4.0),
    "Panama":       (2.1,  3.5),
}
WORLD_MARITIME_TRADE = 77.5   # mb/d seaborne (2023); 76% of world supply    [S26]

# OBSERVED rerouting after the 2026 Hormuz closure (EIA STEO, Q2 2026).
# Used to VALIDATE the model's predicted flow shifts.                  [S27]
OBSERVED_2026_Q2 = {
    "Hormuz": 4.9, "Malacca": 16.6, "Cape of Good Hope": 9.4,
    "Bab el-Mandeb": 8.1, "Suez+SUMED": 5.8, "Danish Straits": 4.7,
    "Turkish Straits": 4.1, "Panama": 3.2,
}

# Transit-time penalties for rerouting (days added). Longer voyages tie up
# tanker capacity, reducing EFFECTIVE supply even if barrels exist.    [S28]
CAPE_EXTRA_DAYS_EUROPE = 15     # IEA: +15 days to Europe around Africa
CAPE_EXTRA_DAYS_US     = 9      # IEA: +8-10 days to the United States
CAPE_EXTRA_NM          = 3500   # nautical miles added
BASE_VOYAGE_DAYS       = 20     # typical Gulf->Asia voyage

# ======================================================================
# 10. REFINERY OPERATING CONSTRAINTS (create discontinuity)
# ======================================================================
MIN_OPERATING_RATE = 0.55   # refineries cannot run below ~55% of capacity;
                            # below this they SHUT DOWN entirely (not pro-rata)
RESTART_DAYS       = 14     # a shut refinery takes ~2 weeks to restart
                            # -> hysteresis: recovery path != collapse path
HOARDING_SENSITIVITY = 0.6  # how strongly buyers over-order when short
                            # (precautionary demand feedback)


# ======================================================================
# 11. PRICE ELASTICITY OF OIL DEMAND (the "tolerance" coefficient)
#     Short-run crude demand is very INELASTIC: consumers cannot quickly
#     change vehicles, heating or industry, so a large price rise buys only
#     a small demand cut. Developing economies are MORE elastic than
#     advanced ones, because fuel is a larger share of income.       [S29-S31]
# ======================================================================
# region -> short-run price elasticity of oil demand (negative)
PRICE_ELASTICITY = {
    "Asia":     -0.18,   # mixed: China/India more elastic than Japan/Korea
    "Europe":   -0.09,   # advanced, high fuel taxes already
    "NAmerica": -0.05,   # least elastic (Ghouri: USA -0.045, Canada -0.06)
}
ELASTICITY_RANGE = (-0.023, -0.33)   # published short-run span        [S29,S31]
OBSERVED_DEMAND_DESTRUCTION_2026 = 1.7   # mb/d needed in the 2026 crisis [S32]

# ======================================================================
# SOURCES  (for the report reference list; all publicly downloadable)
# ======================================================================
SOURCES = """
[S1] U.S. Energy Information Administration, "The Strait of Hormuz is the
     world's most important oil transit chokepoint" / World Oil Transit
     Chokepoints. https://www.eia.gov/
[S2] IEA, "Strait of Hormuz" overview.
     https://www.iea.org/about/oil-security-and-emergency-response/strait-of-hormuz
[S3] EIA / Institute for Energy Research, Persian Gulf oil exports & Hormuz
     (20 mb/d; ~15 crude + ~5.5 products; Saudi ~40%).
     https://www.instituteforenergyresearch.org/
[S4] EIA World Oil Transit Chokepoints; bypass capacity 3.5-5.5 mb/d, five
     Gulf producers with zero pipeline bypass.
     https://www.eia.gov/  (see also davemanuel.com/speedcommerce summaries)
[S5] EIA Weekly Petroleum Status Report, SPR series WCSSTUS1 (415.4 Mb Feb 2026;
     285.0 Mb Sep 2026). https://www.eia.gov/petroleum/weekly/
[S6] energyfactbook.com / worldoilmonitor.com SPR trackers citing EIA/DOE
     (285.0 Mb, lowest since Nov 1982; 714 Mb capacity).
[S7] Wikipedia, "Strategic Petroleum Reserve (United States)", citing DOE
     (max withdrawal 2.7 mb/d). https://en.wikipedia.org/wiki/Strategic_Petroleum_Reserve_(United_States)
[S8] IEA coordinated release announcement, 11 March 2026 (400 Mb; US 172.2 Mb).
[S9] OILCOM crude profiles (Arab Light ~33 API, 1.7-1.9% S).
     https://www.oilcom.de/en/grades/
[S10] S&P Global Platts, Iraq SOMO Basrah grade specifications (Basrah Light
     31.4 API 2.74% S; Medium 27.9 API 3.0% S; Heavy 24 API 4.05% S).
     https://www.spglobal.com/
[S11] The Middle East Insider / OilMonster, crude grades API & sulphur
     (Dubai, WTI, Brent, Venezuela). https://www.oilmonster.com/oil-grades
[S12] EIA International Energy Statistics (production & consumption by country).
     https://www.eia.gov/international/data/world
[S13] Visual Capitalist / EIA 2025 crude production ranking (US 13.59, Russia
     9.89, Saudi 9.56 mb/d). https://www.visualcapitalist.com/
[S14] Worldometer / EIA, world consumption 102.8 mb/d (2024); US 20.61, China
     16.37, India 5.60. https://www.worldometers.info/oil/
[S15] Statista / OPEC, global crude demand 105.16 mb/d (2025).
     https://www.statista.com/statistics/271823/global-crude-oil-demand/
[S16] Oil & Gas Journal, "Complexity index indicates refinery capability,
     value" (world refining ~74 mb/cd, average NCI 5.9).
     https://www.ogj.com/home/article/17234421/
[S17] EIA, "Petroleum refineries vary by level of complexity" (Nelson
     Complexity Index explained; Phillips 66 range 7.0-14.1).
     https://www.eia.gov/todayinenergy/detail.php?id=8330
[S18] Reliance Industries / Economic Times, Jamnagar NCI 21.1 (world's
     largest refinery). https://en.wikipedia.org/wiki/List_of_oil_refineries_in_India
[S19] Nayara Energy, Vadinar refinery NCI 11.8; upgrade enables 80% heavy /
     ultra-heavy crude basket. https://www.nayaraenergy.com/vadinar-refinery
[S21] Visual Capitalist / EIA (Q1 2025), "Charted: Oil Trade Through the
     Strait of Hormuz by Country" - China 37.7%, India 14.7%, S.Korea 12.0%,
     Japan 10.9%, USA 2.5%; Asia 89.2%.
     https://www.visualcapitalist.com/charted-oil-trade-through-the-strait-of-hormuz-by-country/
[S22] IEA Strait of Hormuz factsheet - China+India 44% of Hormuz crude; IEA
     countries 29%; Europe ~600 kb/d (4%).
     https://www.iea.org/about/oil-security-and-emergency-response/strait-of-hormuz
[S23] EIA Today in Energy, "84% of crude through Hormuz went to Asian markets
     in 2024; China, India, Japan, South Korea = 69%".
     https://eia.gov/todayinenergy/detail.php?id=65504
[S24] Atlas Institute / Koons (2025) - Japan: 95% of crude imports from the
     Middle East. (context for extreme regional exposure)
[S25] Wikipedia / EIA International Energy Statistics, oil consumption by
     country (USA 20.31, China 16.19, India 5.27, Russia 3.86, Saudi 3.52,
     Brazil 3.16, Japan 3.14, S.Korea 2.54, Iran 2.42, Canada 2.38 mb/d).
     https://en.wikipedia.org/wiki/List_of_countries_by_oil_consumption
[S26] EIA, "World Oil Transit Chokepoints" Country Analysis Brief (June 2024)
     - 2023 flows: Malacca 23.7, Hormuz 20.9, Suez+SUMED 8.8, Bab el-Mandeb
     8.6, Cape 6.0, Danish 4.9, Turkish 3.4, Panama 2.1 mb/d; world maritime
     trade 77.5 mb/d.
     https://www.eia.gov/international/content/analysis/special_topics/World_Oil_Transit_Chokepoints/wotc.pdf
[S27] EIA Short-Term Energy Outlook (August 2026) via Rigzone - OBSERVED Q2
     2026 flows after the Hormuz closure: Hormuz 4.9, Malacca 16.6, Cape 9.4,
     Bab el-Mandeb 8.1, Suez 5.8. Used here for model validation.
     https://www.rigzone.com/news/how_much_oil_transited_through_worlds_chokepoints_in_2q-12-aug-2026-184358-article/
[S28] EIA / IEA / US DOT - Cape of Good Hope rerouting adds ~3,500 nm,
     10-14 days (15 days to Europe, 8-10 to the US), ~$2.6M per cargo.
[S29] Cooper (2003), "Price elasticity of demand for crude oil: estimates
     for 23 countries" - short-run price elasticity -0.023 to -0.109.
[S30] Ghouri (2001) - USA -0.045, Canada -0.06, Mexico -0.13.
[S31] EIA Working Paper, "Review of Key International Demand Elasticities"
     - developing economies avg price elasticity -0.33; developed lower;
     crude-level short-run response ~-0.15.
     https://www.eia.gov/workingpapers/pdf/key_international_demand_elasticities.pdf
[S32] IEA Oil Market Report 2026 - ~1.7 mb/d of demand destruction required
     during the Hormuz disruption.
[S20] Refinery pages (capacity + NCI): ExxonMobil Beaumont 9.0, Gdansk 11.1,
     Nanticoke 9.82, Montreal 9.0, PBF Energy weighted avg 13.2.
     https://en.wikipedia.org/wiki/ (individual refinery articles)
"""

if __name__ == "__main__":
    print("Calibrated data foundation loaded.")
    print(f"Hormuz flow: {HORMUZ_TOTAL_FLOW} mb/d ({HORMUZ_SHARE_GLOBAL:.0%} of global)")
    print(f"Bypass cap:  {BYPASS_CAPACITY_MIN}-{BYPASS_CAPACITY_MAX} mb/d "
          f"({BYPASS_CAPACITY_MAX/HORMUZ_TOTAL_FLOW:.0%} of Hormuz at best)")
    print(f"SPR: {SPR_CURRENT} Mb now (was {SPR_PRECRISIS}); "
          f"max withdraw {SPR_MAX_WITHDRAW} mb/d")
    print(f"Crude grades: {len(CRUDE_GRADES)} Gulf grades on the API/sulphur axis")
    print(f"Producers: {len(PRODUCTION)}, Consumers: {len(CONSUMPTION)}")
    print(SOURCES)
