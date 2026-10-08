# How the program runs — start to finish

A walkthrough of what happens when you press **Run All**, which function calls which,
and what each one does — with one worked example (**Hormuz 70% closed**) carried all the
way through. Words in **bold** the first time they appear are explained in the glossary at
the end.

To see every number below for yourself:  `cd src` then `python trace_model.py 0.70`

---

## 1. Where it starts

The program is the **notebook**, `notebooks/main_analysis.ipynb`. **Run All** runs its
**cells** from top to bottom, like reading a recipe in order.

1. **Section 0, setup.** Tells Python where the `src/` folder is, then **imports** the data
   file. Importing a file loads its numbers and **functions** into memory — nothing is
   simulated yet.
2. **Section 0b, tests.** Runs `src/test_model.py` as a separate program. It builds the
   model many times and checks 25 things that must be true.
3. **Every later section** imports what it needs and **runs the model fresh** for its own
   scenario. There is no single "run" at the top; each experiment builds its own model.

---

## 2. The big picture: who calls whom

The headline result — the 53% threshold — comes from this chain:

```
notebook cell
 └─ critical_blockade_intensity()            production_cascade.py   finds the threshold
      └─ regional_cascade(closure)           production_cascade.py   one closure level
           ├─ OilNetworkModel()              oil_network_model.py    build a fresh world
           ├─ model.step()  x 150 days       oil_network_model.py    one simulated day
           │    └─ allocate_flows()          oil_network_model.py    LAYER 1: route the oil
           │         └─ push()  many times                            send oil down one route
           └─ run_production_cascade()       production_cascade.py   LAYER 3, once per region
                └─ operability()             production_cascade.py   the gate
```

`clear_market()` (**Layer 2**, the price) is called **beside** this chain — by the price and
reserve sections — not inside it. Price does not feed back into routing in the main model.

---

## 3. One closure level, step by step (Hormuz 70% closed)

### 3.1 `regional_cascade(0.70)` — the manager

**Input:** 0.70, the share of Hormuz *closed*.
It builds a fresh model, runs it for 150 days, then hands each region's shortfall to
Layer 3. Notice it passes `1 − 0.70 = 0.30` to the model, because the model works with the
share *open*.

### 3.2 `OilNetworkModel()` → `__init__` — build the world

Creating the model runs its **constructor**. It sets every region to "normal": nobody
short, every bid at 1.0, no refineries shut. It also sizes the tanker fleet. Nothing moves
yet.

### 3.3 `step(0.30)` — one day, called 150 times

**Input:** the open share. **Output:** each region's shortfall.
Each call does two things: routes the oil (`allocate_flows`), then scores the day.

### 3.4 `allocate_flows(0.30)` — LAYER 1, the heart of the model

**Limits today.** Hormuz lets through its normal flow × the open share:
20.9 × 0.30 = **6.27 mb/d**. Open straits have no limit; canals do (Panama 3.5).

**Step 1 — domestic first.** Each region uses its own oil before trading:

| Region | Produces | Needs | Uses own | Left to export | Must import |
|---|---|---|---|---|---|
| North America | 31.1 | 24.6 | 24.6 | **6.5** | 0 |
| Middle East | 31.0 | 9.5 | 9.5 | **21.5** | 0 |
| China | 5.3 | 16.4 | 5.3 | 0 | **11.1** |
| Japan/Korea | 0.1 | 5.7 | 0.1 | 0 | **5.6** |
| Other Asia | 3.1 | 10.0 | 3.1 | 0 | **6.9** |

**Step 2 — split the exports.** Middle East: 21.5 = **13.98 contracted** + **7.52 spot**
(spot share 35%). North America: 6.5 = 2.60 contracted + 3.90 spot.

**Step 3 — Stage 1: contracted oil, fastest route first.** Routes are sorted by voyage
days. Each one calls `push()`, which sends the *smallest* of: what the buyer still needs,
what the producer has left, room on the path, tankers, and the route's own limit.

| Days | Route | Sent |
|---|---|---|
| 6 | Gulf → India (via Hormuz) | 4.70 |
| 16 | Gulf → Other Asia (via Hormuz) | 1.57 — Hormuz now full: 4.70 + 1.57 = 6.27 |
| 16 | Saudi pipeline → Europe | 3.60 |
| 18 | Saudi pipeline → Other Asia | 2.60 |

**China, 20 days away, gets nothing** — Hormuz is already full by the time its route comes up.
Still short after Stage 1: **China 11.1, Japan/Korea 4.34, Other Asia 1.22**.

**Step 4 — Stage 2: spot oil, one queue.** Each short region bids:
`premium = 1 + 4 × (shortfall ÷ demand)²`

- Japan/Korea: 1 + 4 × (4.34/5.7)² = **3.32**
- China: 1 + 4 × (11.10/16.4)² = **2.83**
- Other Asia: 1 + 4 × (1.22/10.0)² = **1.06**

Every (region, route) pair gets a **netback** = premium − 0.01 × days, and the queue is
served from the top. Japan/Korea's routes come first — which is why North American oil goes
to Japan/Korea via Panama rather than to China.

### 3.5 Back in `step()` — score the day

Each region's crude is scaled by the refinery-complexity uplift (a **proxy**), then:
`shortfall = demand − effective oil`

| Region | Got | Uplift | Effective | Short | Demand met |
|---|---|---|---|---|---|
| China | 10.60 | × 1.028 | 10.89 | **5.51** | **66%** |
| Other Asia | 8.78 | × 1.014 | 8.90 | **1.10** | **89%** |
| everyone else | | | | 0 | 100% |

The same thing happens on every one of the 150 days. Because nothing changes from day to
day here, the answer settles almost at once — it reaches **steady state** on day 1.

### 3.6 `clear_market()` — LAYER 2, the price (called by the price sections)

Total shortfall: 5.51 + 1.10 = **6.61 mb/d**. Find the price *p* at which the world would
cut demand by exactly that much: `Σ demand × p^elasticity = 102.0 − 6.61`.
Solved by **bisection** → **p = 1.84 × pre-crisis = Brent $127**.
At that price, China would cut 1.16, Other Asia 1.15, North America 0.74... (These cuts
are not fed back into Layer 1 — the main model's biggest limitation.)

### 3.7 `run_production_cascade()` — LAYER 3, once per region

**Input:** `oil_available = 1 − shortfall ÷ demand`. China: 1 − 5.51/16.4 = **0.664**.
**Output:** systemic loss, and each sector's output.

For each of the 5 sectors, every round:

```
direct    = 1 − oil_dependence × (1 − oil_available)        its OWN oil shortage
upstream  = 1 − Σ need × (1 − supplier sector's output)      its SUPPLIER SECTORS' damage
effective = min(direct, upstream)                            the worse of the two
output    = operability(effective)                           = effective × gate
```

Repeat until nothing changes (a **fixed point**), then
`systemic loss = Σ weight × (1 − output)`.

China at 66.4% oil → **systemic loss 30.5%** — above 10%, so **systemic**.
Other Asia at 89% → 9.6%, just under.

### 3.8 `operability()` — the gate

`gate = 1 / (1 + e^(−(effective − 0.45) / 0.06))`, an **S-curve**: about 1 above 60% of
inputs, 0.5 at 45%, about 0 below 30%. Output = effective × gate.

---

## 4. How the threshold is found — `critical_blockade_intensity()`

It doesn't try every closure level. It uses **bisection** — like guessing a number between
0 and 100 by always guessing the middle:

| Try | Closure | Worst region's loss | Verdict |
|---|---|---|---|
| 1 | 50% | 6.4% | under 10% → answer is higher |
| 2 | 75% | above 10% | → answer is lower |
| 3 | 62.5% | above 10% | → lower |
| ... | ... | ... | ... |
| 12 | 53.1% | just over 10% | **the threshold** |

Each "try" is a full `regional_cascade()` — 150 simulated days plus Layer 3. Twelve tries
narrow it down to about 0.02%.

---

## 5. The extension — where price feedback sits

`run_experiment()` in `experiment_feedback.py` **wraps around Layers 1 and 2**. Layer 1 runs
*inside* its daily loop:

```
before the loop:  supply_avail = demand − physical shortage   (from a normal run)
each day:
    today's demand = original demand − cut      ← yesterday's price decided this
    model.step()                                ← LAYER 1 runs here
    price moves 12% of the way to the price that matches demand to supply_avail
    cut = demand × min(1 − price^elasticity, 20%)    ← for tomorrow, every region
after the loop:
    oil_available = 1 − (cut + physical shortfall) ÷ demand
    run_production_cascade()                    ← LAYER 3
```

Each day's price, cut and shortfall are saved in `history`, so they can be graphed.

---

## Glossary

**Argument / parameter** — a value you hand to a function. In `step(0.30)`, 0.30 is the argument.
**Bisection** — finding an answer by repeatedly halving the range it must lie in.
**Cell** — one block of a notebook, run in one go.
**Class / object** — a class is a blueprint (`OilNetworkModel`); an object is one thing built from it (`m = OilNetworkModel()`). Each object keeps its own memory.
**Constructor (`__init__`)** — the function that runs automatically when an object is created, setting its starting values.
**Dictionary** — a lookup table: `REGION_DEMAND["China"]` gives 16.4.
**Elasticity** — how much demand falls when price rises; −0.12 means a 10% price rise cuts demand 1.2%.
**Fixed point** — the state where repeating a calculation no longer changes the answer.
**Function** — a named, reusable piece of code that takes inputs and returns an output.
**Import** — loading another file's numbers and functions so this file can use them.
**Layer 1 / 2 / 3** — routing (where oil goes) / market (the price) / production (damage to the economy).
**Loop** — code that repeats: `for _ in range(150)` runs 150 times, one per simulated day.
**Method** — a function that belongs to an object, such as `m.step()`.
**Netback** — a bid minus the freight cost for a route: premium − 0.01 × days.
**Premium** — a region's bid, rising with the square of its shortfall.
**Proxy** — a simple stand-in for something real that isn't modelled properly.
**Return value** — what a function hands back: `step()` returns each region's shortfall.
**`self`** — inside a method, "this object": `self.premium` is this model's own bids.
**Steady state** — when the model's daily results stop changing.
**S-curve** — a curve that is flat, then rises steeply, then flattens again; used for the gate.
**Systemic loss** — the share of a region's oil-weighted output lost; above 10% counts as systemic.
**Threshold** — the share of Hormuz closed at which the worst region first passes 10% systemic loss.
