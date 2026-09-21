"""
topology_comparison.py — is the real oil network unusually vulnerable?
CITS4403 — Raed

Connects the project back to the network-science tools from Lectures 2-3:
Erdos-Renyi, Watts-Strogatz, Barabasi-Albert, plus degree-preserving
randomisation (the standard null model).

IMPORTANT CAVEAT on "the real network":
  The chokepoints, their capacities and their observed flows are EIA data.
  The ROUTES (which origin-destination pairs use which chokepoints) are
  constructed from geography, not from a bilateral-trade dataset. The
  evidence they are approximately right is that the model reproduces
  observed chokepoint flows both before and after the 2026 disruption
  (Hormuz 5.0 vs 4.9 observed; Malacca 16.7 vs 16.6 observed).
  A fully data-driven version would build routes from UN Comtrade bilateral
  flows - that is left as future work.

Question:
  Is the real (geographically constrained) network MORE vulnerable to
  chokepoint removal than comparable random networks with the same size?
"""

import numpy as np
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from oil_model_data import CHOKEPOINTS
from oil_network_model import ROUTES, REGION_DEMAND, ORIGIN_SUPPLY


# ----------------------------------------------------------------------
# 1. Build the real network as a GRAPH (chokepoints as intermediate nodes)
# ----------------------------------------------------------------------
def build_real_graph():
    """Origins and destinations are nodes; chokepoints are intermediate nodes
    on the path. This lets us compute betweenness centrality for chokepoints."""
    G = nx.Graph()
    for rname, (origin, dest, cps, days) in ROUTES.items():
        path = [origin] + list(cps) + [dest]
        for a, b in zip(path[:-1], path[1:]):
            G.add_edge(a, b)
    return G


def chokepoint_betweenness(G):
    """Which nodes lie on the most paths? A high-betweenness node is a
    structural bottleneck - this QUANTIFIES why a chokepoint is critical
    rather than assuming it."""
    bc = nx.betweenness_centrality(G)
    return {n: bc[n] for n in G.nodes() if n in CHOKEPOINTS}


# ----------------------------------------------------------------------
# 2. Vulnerability measure: how much does removing the best node hurt?
# ----------------------------------------------------------------------
def vulnerability(G, sources=None, sinks=None):
    """Fraction of origin-destination pairs disconnected when the single
    highest-betweenness node is removed (a targeted attack)."""
    if sources is None:
        sources = [n for n in ORIGIN_SUPPLY if n in G]
    if sinks is None:
        sinks = [n for n in REGION_DEMAND if n in G]
    if not sources or not sinks:
        return np.nan

    def connected_pairs(H):
        c = 0
        for s in sources:
            for t in sinks:
                if s in H and t in H and nx.has_path(H, s, t):
                    c += 1
        return c

    before = connected_pairs(G)
    if before == 0:
        return np.nan
    bc = nx.betweenness_centrality(G)
    # do not delete the origins/destinations themselves
    cand = {n: v for n, v in bc.items() if n not in sources and n not in sinks}
    if not cand:
        return np.nan
    worst = max(cand, key=cand.get)
    H = G.copy(); H.remove_node(worst)
    after = connected_pairs(H)
    return (before - after) / before


# ----------------------------------------------------------------------
# 3. Comparison networks (the taught generators + a proper null model)
# ----------------------------------------------------------------------
def capacity_vulnerability(G, sources=None, sinks=None, cap=1.0):
    """Fraction of total FLOW CAPACITY lost when the highest-betweenness node
    is removed. Connectivity alone is misleading here: a path usually still
    exists, but it may not be able to carry the volume."""
    if sources is None:
        sources = [n for n in ORIGIN_SUPPLY if n in G]
    if sinks is None:
        sinks = [n for n in REGION_DEMAND if n in G]
    H = G.copy()
    for u, v in H.edges():
        H[u][v]["capacity"] = cap
    def total_flow(J):
        J = J.copy()
        J.add_node("SRC"); J.add_node("SNK")
        for s_ in sources:
            if s_ in J: J.add_edge("SRC", s_, capacity=1e6)
        for t_ in sinks:
            if t_ in J: J.add_edge(t_, "SNK", capacity=1e6)
        try:
            return nx.maximum_flow_value(J, "SRC", "SNK", capacity="capacity")
        except Exception:
            return 0.0
    before = total_flow(H)
    if before == 0:
        return np.nan
    bc = nx.betweenness_centrality(G)
    cand = {n: v for n, v in bc.items() if n not in sources and n not in sinks}
    if not cand:
        return np.nan
    worst = max(cand, key=cand.get)
    H2 = H.copy(); H2.remove_node(worst)
    return (before - total_flow(H2)) / before


def comparison_networks(G_real, n_samples=200, seed=0):
    rng = np.random.default_rng(seed)
    n, m = G_real.number_of_nodes(), G_real.number_of_edges()
    k = max(2, int(round(2 * m / n)))          # average degree
    out = {"Erdos-Renyi": [], "Watts-Strogatz": [], "Barabasi-Albert": [],
           "Degree-preserving rewire": []}

    n_src = len([x for x in ORIGIN_SUPPLY if x in G_real])
    n_snk = len([x for x in REGION_DEMAND if x in G_real])
    # in a random graph, designate the first n_src nodes as origins and the
    # last n_snk as destinations, so the comparison is like-for-like
    src_idx = list(range(n_src))
    snk_idx = list(range(n - n_snk, n))

    for i in range(n_samples):
        s = int(rng.integers(1e6))
        for name, Gr in [
                ("Erdos-Renyi", nx.gnm_random_graph(n, m, seed=s)),
                ("Watts-Strogatz", nx.watts_strogatz_graph(
                    n, k if k % 2 == 0 else k + 1, 0.1, seed=s)),
                ("Barabasi-Albert", nx.barabasi_albert_graph(
                    n, max(1, k // 2), seed=s))]:
            out[name].append(capacity_vulnerability(Gr, src_idx, snk_idx))
        H = G_real.copy()
        try:
            nx.double_edge_swap(H, nswap=3 * m, max_tries=100 * m, seed=s)
            out["Degree-preserving rewire"].append(capacity_vulnerability(H))
        except Exception:
            pass
    return out


if __name__ == "__main__":
    G = build_real_graph()
    print(f"Real network: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges\n")

    print("CHOKEPOINT BETWEENNESS CENTRALITY")
    print("(how often each chokepoint lies on a path - structural criticality)")
    bc = chokepoint_betweenness(G)
    for cp, v in sorted(bc.items(), key=lambda x: -x[1]):
        bar = "#" * int(v * 60)
        print(f"  {cp:<20}{v:6.3f}  {bar}")

    v_conn = vulnerability(G)
    v_real = capacity_vulnerability(G)
    print(f"\nREAL NETWORK, targeted removal of most-central node:")
    print(f"  connectivity lost: {v_conn:.1%}  (paths still exist!)")
    print(f"  CAPACITY lost:     {v_real:.1%}  <- the measure that matters")

    print("\nCOMPARISON WITH RANDOM NETWORKS (same size)")
    comps = comparison_networks(G)
    print(f"{'network':<28}{'mean':>8}{'std':>8}   verdict")
    for name, vals in comps.items():
        vals = [v for v in vals if not np.isnan(v)]
        if not vals:
            continue
        mu, sd = np.mean(vals), np.std(vals)
        verdict = ("real is MORE vulnerable" if v_real > mu + sd else
                   "real is LESS vulnerable" if v_real < mu - sd else
                   "comparable")
        print(f"  {name:<26}{mu:>8.1%}{sd:>8.1%}   {verdict}")

    # ---- figure ----
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    names = list(bc.keys())
    ax[0].barh(names, [bc[n] for n in names], color="#c1272d")
    ax[0].set_xlabel("Betweenness centrality")
    ax[0].set_title("Which chokepoints are structurally critical?\n"
                    "(betweenness on the real route network)")
    ax[0].grid(alpha=.3, axis="x")

    labels, means, stds = [], [], []
    for name, vals in comps.items():
        vals = [v for v in vals if not np.isnan(v)]
        if vals:
            labels.append(name.replace(" ", "\n"))
            means.append(np.mean(vals)); stds.append(np.std(vals))
    x = np.arange(len(labels))
    ax[1].bar(x, means, yerr=stds, capsize=4, color="#888", label="random networks")
    ax[1].axhline(v_real, color="#c1272d", lw=2, label=f"real network ({v_real:.0%})")
    ax[1].set_xticks(x); ax[1].set_xticklabels(labels, fontsize=8)
    ax[1].set_ylabel("Fraction of flow CAPACITY lost")
    ax[1].set_title("Is the real oil network unusually vulnerable?")
    ax[1].legend(fontsize=8); ax[1].grid(alpha=.3, axis="y")

    fig.suptitle("Network topology analysis (Lectures 2-3 tools applied to real infrastructure)")
    fig.tight_layout()
    fig.savefig("/mnt/user-data/outputs/topology_comparison.png", dpi=130)
    print("\nSaved figure to topology_comparison.png")
