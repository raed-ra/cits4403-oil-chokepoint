"""
sensitivity.py — how much do our uncertain assumptions change the results?
CITS4403 — Raed

Several model parameters are NOT taken from published data; they are our own
calibration choices. This module sweeps each one and reports how far the
headline results move. A result that survives its parameter being varied is
defensible; one that doesn't must be reported as assumption-driven.

Parameters swept (with why each is uncertain):
  OPERABLE_MIN      0.45  - sector failure floor. OUR CHOICE. An et al.
                            calibrate theirs to OECD ICIO tables; we cannot.
                            This is the weakest parameter in the model.
  BAND_SMOOTHNESS   0.06  - width of the failure transition. OUR CHOICE.
  MIN_OPERATING_RATE 0.55 - refinery minimum run rate. Loosely grounded in the
                            industry norm of 50-60% of capacity.
  REGIONAL_NCI            - refinery complexity per region. ESTIMATED from a
                            9-refinery sample; no published per-region series.
  PRICE_ELASTICITY        - published range is wide (-0.023 to -0.33).
  RESTART_DAYS      14    - refinery restart lag. Order-of-magnitude estimate.
"""

import numpy as np
import matplotlib
import matplotlib.pyplot as plt

import oil_model_data as D
import production_cascade as PC
import oil_network_model as NM

import os as _os
# Save figures into the project's own figures/ folder, wherever it is run from.
FIG_DIR = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "figures")
_os.makedirs(FIG_DIR, exist_ok=True)



# ----------------------------------------------------------------------
def critical_threshold():
    """Blockade intensity at which the worst region exceeds 10% systemic loss."""
    return PC.critical_blockade_intensity()                    # the same bisection as the headline 53%


def sweep_operability_min(values=np.linspace(0.30, 0.60, 7)):
    """Vary the sector shutdown line (normally 0.45) from 0.30 to 0.60 and
    find the threshold for each. Result: 52.6-53.1% - barely moves."""
    out = []                                                   # one threshold per value
    original = PC.OPERABLE_MIN                                 # remember the real setting
    for v in values:                                           # 0.30, 0.35, ... 0.60
        PC.OPERABLE_MIN = float(v)                             # change the assumption
        out.append(critical_threshold())                       # re-run the whole threshold search
    PC.OPERABLE_MIN = original                                 # put the real setting back
    return values, out


def sweep_band_smoothness(values=np.linspace(0.02, 0.15, 7)):
    """Vary how sharp the gate's S-curve is (normally 0.06) and find the
    threshold for each."""
    out = []
    original = PC.BAND_SMOOTHNESS                              # remember
    for v in values:
        PC.BAND_SMOOTHNESS = float(v)                          # change
        out.append(critical_threshold())                       # re-run
    PC.BAND_SMOOTHNESS = original                              # restore
    return values, out


def sweep_min_operating_rate(values=np.linspace(0.40, 0.70, 7), blockade=0.65):
    """Refinery minimum run rate -> unserved demand.
    Tested at an INTERMEDIATE blockade: at full closure the shortfall is so
    severe that every refinery fails regardless, saturating this parameter."""
    out = []
    for v in values:                                           # 0.40 ... 0.70
        m = NM.OilNetworkModel(min_rate=float(v))              # a model built with that refinery minimum
        for _ in range(150):
            u, _, _ = m.step(1.0 - blockade)                   # 150 days at 65% closed
        out.append(sum(u.values()))                            # total world shortfall
    return values, out


def sweep_restart_days(values=[3, 7, 14, 21, 30, 45], blockade=0.65):
    """Restart lag -> damage under a RECOVERING disruption (where hysteresis
    can actually show up: the strait partially reopens after 60 days)."""
    out = []
    for v in values:                                           # restart lag in days
        m = NM.OilNetworkModel(restart_days=int(v))            # model with that lag
        tot = []                                               # daily shortfall
        for d in range(180):                                   # 180 days
            b = blockade if d < 60 else 0.25      # partial recovery
            u, _, _ = m.step(1.0 - b)                          # 65% closed for 60 days, then 25%
            tot.append(sum(u.values()))
        out.append(float(np.mean(tot)))                        # average shortfall over the 180 days
    return values, out


def sweep_regional_nci(scales=np.linspace(0.6, 1.4, 7)):
    """Scale ALL regional NCI estimates up/down together."""
    out = []
    original = dict(NM.REGION_NCI)                             # a copy of the real complexity values
    for s in scales:                                           # x0.6 ... x1.4
        for r in NM.REGION_NCI:
            NM.REGION_NCI[r] = original[r] * float(s)          # every region's NCI scaled together
        m = NM.OilNetworkModel()
        for _ in range(150):
            u, _, _ = m.step(0.0)                              # full closure
        out.append(sum(u.values()))                            # total world shortfall
    NM.REGION_NCI.update(original)                             # restore the real values
    return scales, out


def sweep_elasticity(scales=np.linspace(0.3, 2.0, 7)):
    """Scale all price elasticities; report the peak price at full closure."""
    from price_dynamics import simulate_price
    out = []
    original = dict(D.PRICE_ELASTICITY)                        # a copy of the real elasticities
    for s in scales:                                           # x0.3 ... x2.0
        for r in D.PRICE_ELASTICITY:
            D.PRICE_ELASTICITY[r] = original[r] * float(s)     # every region scaled together
        h = simulate_price(1.0, days=200)                      # price path at full closure
        out.append(max(h["price"]))                            # its peak
    D.PRICE_ELASTICITY.update(original)                        # restore
    return scales, out


def path_dependence_test():
    """Proper test: hold TOTAL blockade-days constant, vary the PATH.

    (An earlier version compared 'sudden' vs 'gradual' without matching total
    exposure - that difference was an artefact of unequal blockade-days, not
    genuine path dependence. This version matches exposure.)"""
    paths = {                                                  # four 150-day schedules of daily closure (share CLOSED)
        "sudden then ease":  [0.8] * 60 + [0.3] * 90,          # 80% for 60 days, then 30% for 90
        "ease then sudden":  [0.3] * 90 + [0.8] * 60,          # same days, opposite order
        "gradual ramp":      list(np.linspace(0.3, 0.8, 150)), # rises steadily 30% -> 80%
        "oscillating":       [0.8 if (d // 15) % 2 == 0 else 0.3 for d in range(150)],   # switches every 15 days
    }
    out = {}
    for lab, seq in paths.items():
        m = NM.OilNetworkModel(); t = []                       # fresh model; daily shortfalls
        for b in seq:                                          # one entry = one day's closure
            u, _, _ = m.step(1.0 - b); t.append(sum(u.values()))
        out[lab] = (sum(seq), float(np.mean(t)))               # (total exposure, average shortfall)
    return out


if __name__ == "__main__":                                              # only when run directly
    print("SENSITIVITY ANALYSIS\n" + "=" * 60)

    print("\n1. OPERABLE_MIN (sector failure floor) -> critical blockade")
    v, o = sweep_operability_min()                                      # sweep 1
    for a, b in zip(v, o):                                              # print each value and its threshold
        print(f"   floor {a:.2f} -> critical {b if b is None else f'{b:.0%}'}")

    print("\n2. BAND_SMOOTHNESS -> critical blockade")
    v2, o2 = sweep_band_smoothness()                                    # sweep 2
    for a, b in zip(v2, o2):
        print(f"   smoothness {a:.3f} -> critical {b if b is None else f'{b:.0%}'}")

    print("\n3. MIN_OPERATING_RATE -> unserved at 65% closure (mb/d)")
    v3, o3 = sweep_min_operating_rate()                                 # sweep 3
    for a, b in zip(v3, o3):
        print(f"   min rate {a:.2f} -> unserved {b:5.2f}")

    print("\n4. RESTART_DAYS -> average unserved, 65% closure easing to 25% (mb/d)")
    v4, o4 = sweep_restart_days()                                       # sweep 4
    for a, b in zip(v4, o4):
        print(f"   restart {a:3d} days -> unserved {b:5.2f}")

    print("\n5. REGIONAL_NCI scale -> unserved at full closure (mb/d)")
    v5, o5 = sweep_regional_nci()                                       # sweep 5
    for a, b in zip(v5, o5):
        print(f"   NCI x{a:.2f} -> unserved {b:5.2f}")

    print("\n6. PRICE_ELASTICITY scale -> peak price at full closure")
    v6, o6 = sweep_elasticity()                                         # sweep 6
    for a, b in zip(v6, o6):
        print(f"   elasticity x{a:.2f} -> peak price {b:5.2f}x")

    # ---- figure ----
    fig, ax = plt.subplots(2, 3, figsize=(15, 8))                       # six small charts, 2 rows x 3
    def plot(a, x, y, xl, yl, t, pct=False):                            # helper: draw one sweep
        yy = [np.nan if v is None else (v * 100 if pct else v) for v in y]  # missing results -> gaps; thresholds as %
        a.plot(x, yy, "o-", color="#c1272d")
        a.set_xlabel(xl); a.set_ylabel(yl); a.set_title(t, fontsize=10)  # labels and title
        a.grid(alpha=.3)                                                # grid

    plot(ax[0][0], v, o, "Sector failure floor", "Critical blockade (%)",  # chart 1
         "1. Operability floor\n(OUR weakest assumption)", pct=True)
    ax[0][0].axvspan(0.43, 0.47, alpha=.15, color="green")              # shade the value actually used (0.45)
    plot(ax[0][1], v2, o2, "Band smoothness", "Critical blockade (%)",  # chart 2
         "2. Transition width", pct=True)
    plot(ax[0][2], v3, o3, "Refinery min run rate", "Unserved (mb/d)",  # chart 3
         "3. Minimum operating rate\n(at 65% blockade)")
    plot(ax[1][0], v4, o4, "Restart lag (days)", "Unserved (mb/d)",     # chart 4
         "4. Restart lag\n(under recovery)")
    plot(ax[1][1], v5, o5, "NCI scale factor", "Unserved (mb/d)",       # chart 5
         "5. Regional refinery complexity\n(ESTIMATED values)")
    plot(ax[1][2], v6, o6, "Elasticity scale factor", "Peak price (x)",  # chart 6
         "6. Price elasticity\n(published range is wide)")

    print("\n7. PATH DEPENDENCE (matched total blockade-days)")
    pd_res = path_dependence_test()                                     # the volatility test
    for lab, (bd, val) in pd_res.items():                               # print each schedule's result
        print(f"   {lab:18s} blockade-days {bd:6.1f} -> unserved {val:5.2f}")

    fig.suptitle("Sensitivity analysis: how far do results move when "  # overall title
                 "uncertain assumptions are varied?")
    fig.tight_layout()                                                  # tidy spacing
    fig.savefig(_os.path.join(FIG_DIR, "sensitivity_analysis.png"), dpi=130)  # save the picture
    print("\nSaved figure to sensitivity_analysis.png")
