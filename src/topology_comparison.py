"""
topology_comparison.py — is the real oil network unusually vulnerable?
CITS4403 — Raed

Connects the project back to the network-science tools from Lectures 2-3:
Erdos-Renyi, Watts-Strogatz, Barabasi-Albert, plus degree-preserving
randomisation (the standard null model).

IMPORTANT CAVEAT on "the real network":
  The chokepoints and their normal flows are EIA data.
  The ROUTES (which origin-destination pairs use which chokepoints) are
  constructed from geography, not from a bilateral-trade dataset. Under the
  2026 closure the model gets the direction of rerouting right but
  under-predicts its size (e.g. Malacca 9.9 vs 16.6 observed), mainly
  because refined products are not modelled.
  A fully data-driven version would build routes from UN Comtrade bilateral
  flows - that is left as future work.

Question:
  Is the real (geographically constrained) network MORE vulnerable to
  chokepoint removal than comparable random networks with the same size?
"""

import numpy as np
import networkx as nx
import matplotlib
import matplotlib.pyplot as plt

from oil_model_data import CHOKEPOINTS
from oil_network_model import ROUTES, REGION_DEMAND, ORIGIN_SUPPLY

import os as _os
# Save figures into the project's own figures/ folder, wherever it is run from.
FIG_DIR = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "figures")
_os.makedirs(FIG_DIR, exist_ok=True)



# ----------------------------------------------------------------------
# 1. Build the real network as a GRAPH (chokepoints as intermediate nodes)
# ----------------------------------------------------------------------
def build_real_graph():
    """Turn the 37 routes into an ordinary network-science graph.

    Producers, chokepoints and consumers are all NODES; each route becomes a
    chain of edges producer -> chokepoint(s) -> consumer. Result: 22 nodes,
    39 edges. Unlike the main model, chokepoints are nodes here, so their
    betweenness centrality can be measured.
    """
    G = nx.Graph()                                                       # an empty undirected graph
    for rname, (origin, dest, cps, days, *_extra) in ROUTES.items():     # every route; *_extra swallows the route limit
        path = [origin] + list(cps) + [dest]                             # e.g. [MidEast_P, Hormuz, Malacca, China]
        for a, b in zip(path[:-1], path[1:]):                            # each neighbouring pair on the path...
            G.add_edge(a, b)                                             # ...becomes an edge (a repeat is ignored)
    return G


def chokepoint_betweenness(G):
    """Betweenness centrality of each chokepoint (the Lecture 2-3 measure).

    For every pair of nodes, find the shortest path; a node's betweenness is
    the share of those paths that pass through it. High = structural
    bottleneck. Result: Malacca 0.31, Cape 0.30 ... Hormuz only 0.03.
    """
    bc = nx.betweenness_centrality(G)                                    # betweenness of EVERY node
    return {n: bc[n] for n in G.nodes() if n in CHOKEPOINTS}             # keep only the 8 chokepoints


# ----------------------------------------------------------------------
# 2. Vulnerability measure: how much does removing the best node hurt?
# ----------------------------------------------------------------------
def vulnerability(G, sources=None, sinks=None):
    """CONNECTIVITY test: share of producer-consumer pairs that can no longer
    reach each other once the most central chokepoint is removed.
    Real network: 0% - there is always another path."""
    if sources is None:
        sources = [n for n in ORIGIN_SUPPLY if n in G]                   # default: the producer nodes on the map
    if sinks is None:
        sinks = [n for n in REGION_DEMAND if n in G]                     # default: the consumer nodes on the map
    if not sources or not sinks:
        return np.nan                                                    # nothing to measure

    def connected_pairs(H):                                              # how many (producer, consumer) pairs are linked?
        c = 0
        for s in sources:
            for t in sinks:
                if s in H and t in H and nx.has_path(H, s, t):           # is there ANY path from s to t?
                    c += 1
        return c

    before = connected_pairs(G)                                          # pairs linked in the full network
    if before == 0:
        return np.nan
    bc = nx.betweenness_centrality(G)                                    # find the most central node...
    # do not delete the origins/destinations themselves
    cand = {n: v for n, v in bc.items() if n not in sources and n not in sinks}   # ...among the in-between nodes only
    if not cand:
        return np.nan
    worst = max(cand, key=cand.get)                                      # the highest-betweenness node (Malacca)
    H = G.copy(); H.remove_node(worst)                                   # remove it from a copy
    after = connected_pairs(H)                                           # pairs still linked
    return (before - after) / before                                     # share of pairs lost


# ----------------------------------------------------------------------
# 3. Comparison networks (the taught generators + a proper null model)
# ----------------------------------------------------------------------
def capacity_vulnerability(G, sources=None, sinks=None, cap=1.0):
    """CAPACITY test: share of total flow capacity lost when the most central
    node is removed. Every edge gets capacity 1 ("one lane"), so max-flow
    counts how many separate paths can carry oil at once.
    Real network: 18 lanes before, 17 after removing Malacca -> 5.6%."""
    if sources is None:
        sources = [n for n in ORIGIN_SUPPLY if n in G]                   # producers
    if sinks is None:
        sinks = [n for n in REGION_DEMAND if n in G]                     # consumers
    H = G.copy()
    for u, v in H.edges():
        H[u][v]["capacity"] = cap                                        # every road: one lane
    def total_flow(J):                                                   # max-flow from all producers to all consumers
        J = J.copy()
        J.add_node("SRC"); J.add_node("SNK")                             # one imaginary super-producer and super-consumer
        for s_ in sources:
            if s_ in J: J.add_edge("SRC", s_, capacity=1e6)              # huge road from SRC to every producer
        for t_ in sinks:
            if t_ in J: J.add_edge(t_, "SNK", capacity=1e6)              # huge road from every consumer to SNK
        try:
            return nx.maximum_flow_value(J, "SRC", "SNK", capacity="capacity")   # most that can flow SRC -> SNK
        except Exception:
            return 0.0                                                   # e.g. no path at all
    before = total_flow(H)                                               # 18 for the real network
    if before == 0:
        return np.nan
    bc = nx.betweenness_centrality(G)                                    # most central in-between node, as above
    cand = {n: v for n, v in bc.items() if n not in sources and n not in sinks}
    if not cand:
        return np.nan
    worst = max(cand, key=cand.get)
    H2 = H.copy(); H2.remove_node(worst)                                 # remove it
    return (before - total_flow(H2)) / before                            # share of capacity lost (1/18 = 5.6%)


def comparison_networks(G_real, n_samples=200, seed=0):
    """Build n_samples random graphs of each kind, the SAME size as the real
    one, and measure capacity_vulnerability on each:
      Erdos-Renyi          edges placed at random
      Watts-Strogatz       a ring of neighbours, 10% of links rewired far away
      Barabasi-Albert      newcomers link to popular nodes -> hubs
      Degree-preserving    the real network with edges shuffled, every node
                           keeping its number of links (the standard null model)
    Returns {kind: [loss for each sample]}."""
    rng = np.random.default_rng(seed)                                    # random generator, fixed seed = reproducible
    n, m = G_real.number_of_nodes(), G_real.number_of_edges()            # 22 nodes, 39 edges
    k = max(2, int(round(2 * m / n)))          # average degree
    out = {"Erdos-Renyi": [], "Watts-Strogatz": [], "Barabasi-Albert": [],
           "Degree-preserving rewire": []}                               # results, one list per kind

    n_src = len([x for x in ORIGIN_SUPPLY if x in G_real])               # how many producers the real map has
    n_snk = len([x for x in REGION_DEMAND if x in G_real])               # how many consumers
    # in a random graph, designate the first n_src nodes as origins and the
    # last n_snk as destinations, so the comparison is like-for-like
    src_idx = list(range(n_src))
    snk_idx = list(range(n - n_snk, n))

    for i in range(n_samples):                                           # 200 rounds
        s = int(rng.integers(1e6))                                       # a new random seed each round
        for name, Gr in [
                ("Erdos-Renyi", nx.gnm_random_graph(n, m, seed=s)),      # n nodes, exactly m random edges
                ("Watts-Strogatz", nx.watts_strogatz_graph(
                    n, k if k % 2 == 0 else k + 1, 0.1, seed=s)),        # ring (k must be even), 10% rewired
                ("Barabasi-Albert", nx.barabasi_albert_graph(
                    n, max(1, k // 2), seed=s))]:                        # each newcomer adds k/2 links
            out[name].append(capacity_vulnerability(Gr, src_idx, snk_idx))   # same test as the real network
        H = G_real.copy()
        try:
            nx.double_edge_swap(H, nswap=3 * m, max_tries=100 * m, seed=s)   # shuffle edges, keep every node's degree
            out["Degree-preserving rewire"].append(capacity_vulnerability(H))
        except Exception:
            pass                                                         # a swap can occasionally fail; skip that round
    return out


if __name__ == "__main__":                                              # only when run directly
    G = build_real_graph()                                              # the real network as a graph
    print(f"Real network: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges\n")

    print("CHOKEPOINT BETWEENNESS CENTRALITY")
    print("(how often each chokepoint lies on a path - structural criticality)")
    bc = chokepoint_betweenness(G)                                      # betweenness of each chokepoint
    for cp, v in sorted(bc.items(), key=lambda x: -x[1]):               # most central first
        bar = "#" * int(v * 60)
        print(f"  {cp:<20}{v:6.3f}  {bar}")

    v_conn = vulnerability(G)                                           # connectivity test
    v_real = capacity_vulnerability(G)                                  # capacity test
    print(f"\nREAL NETWORK, targeted removal of most-central node:")
    print(f"  connectivity lost: {v_conn:.1%}  (paths still exist!)")
    print(f"  CAPACITY lost:     {v_real:.1%}  <- the measure that matters")

    print("\nCOMPARISON WITH RANDOM NETWORKS (same size)")
    comps = comparison_networks(G)                                      # 200 random graphs of each kind
    print(f"{'network':<28}{'mean':>8}{'std':>8}   verdict")
    for name, vals in comps.items():                                    # for each kind of random network...
        vals = [v for v in vals if not np.isnan(v)]                     # drop failed samples
        if not vals:                                                    # none left?
            continue
        mu, sd = np.mean(vals), np.std(vals)                            # average loss and its spread
        verdict = ("real is MORE vulnerable" if v_real > mu + sd else   # more than one spread away = a real difference
                   "real is LESS vulnerable" if v_real < mu - sd else
                   "comparable")
        print(f"  {name:<26}{mu:>8.1%}{sd:>8.1%}   {verdict}")          # print the verdict

    # ---- figure ----
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))                       # two charts side by side
    names = list(bc.keys())                                             # chokepoint names
    ax[0].barh(names, [bc[n] for n in names], color="#c1272d")
    ax[0].set_xlabel("Betweenness centrality")                          # left chart: betweenness
    ax[0].set_title("Which chokepoints are structurally critical?\n"
                    "(betweenness on the real route network)")
    ax[0].grid(alpha=.3, axis="x")

    labels, means, stds = [], [], []                                    # right chart: random vs real
    for name, vals in comps.items():                                    # each kind...
        vals = [v for v in vals if not np.isnan(v)]                     # drop failed samples
        if vals:
            labels.append(name.replace(" ", "\n"))                      # name, split over two lines
            means.append(np.mean(vals)); stds.append(np.std(vals))      # its average and spread
    x = np.arange(len(labels))                                          # bar positions
    ax[1].bar(x, means, yerr=stds, capsize=4, color="#888", label="random networks")
    ax[1].axhline(v_real, color="#c1272d", lw=2, label=f"real network ({v_real:.0%})")
    ax[1].set_xticks(x); ax[1].set_xticklabels(labels, fontsize=8)      # name each bar
    ax[1].set_ylabel("Fraction of flow CAPACITY lost")                  # axis label
    ax[1].set_title("Is the real oil network unusually vulnerable?")    # title
    ax[1].legend(fontsize=8); ax[1].grid(alpha=.3, axis="y")            # legend, grid

    fig.suptitle("Network topology analysis (Lectures 2-3 tools applied to real infrastructure)")  # overall title
    fig.tight_layout()                                                  # tidy spacing
    fig.savefig(_os.path.join(FIG_DIR, "topology_comparison.png"), dpi=130)  # save the picture
    print("\nSaved figure to topology_comparison.png")
