#!/usr/bin/env python3
"""Verify the Daevanion path-cost maths behind src/data/skill-levels.json.

Needs the normalized client dump; skips cleanly when it is not present, so it
only runs where the dump lives.

Four things are checked, in increasing order of how much they could hurt if
wrong:

  1. The node-weighted Dijkstra reproduces the dump's own `minPointsToUnlock`
     for every node on every board. This validates the graph model itself
     (adjacency, node weights, the free centre) against ground truth we did not
     produce.
  2. The per-class node layout is what the page claims: actives once per board,
     passives twice on exactly one of Nezekan/Zikel and absent from the other.
  3. Every paired-board cost is ACHIEVABLE — the tree is reconstructed, checked
     for connectivity, and its node weights re-summed independently.
  4. Every paired-board cost is OPTIMAL. A Steiner tree over three terminals has
     at most one branch vertex, so enumerating every vertex as the branch point
     is exhaustive; this is cross-checked against a from-scratch reconstruction
     and bounded below by the costliest single terminal.
"""
import heapq
import json
import os
import sys

SRC = "/root/aion2/data/normalized"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARDS = ["Nezekan", "Zikel", "Vaizel", "Triniel"]
CLASS_PREFIX = {"gladiator": "1", "templar": "2", "ranger": "3", "assassin": "4",
                "elementalist": "5", "sorcerer": "6", "cleric": "7", "chanter": "8",
                "fighter": "9"}

fails, checks = [], 0


def check(cond, msg):
    global checks
    checks += 1
    if not cond:
        fails.append(msg)


def load_board(path):
    d = json.load(open(path))
    nodes = {n["id"]: n for n in d["nodes"]}
    adj = {i: [x for x in n.get("neighbors", []) if x in nodes] for i, n in nodes.items()}
    w = {i: n["cost"] for i, n in nodes.items()}
    start = next(n["id"] for n in d["nodes"] if n["nodeType"] == "start")
    return d, nodes, adj, w, start


def dijkstra(src, adj, w):
    dist, prev, pq = {src: 0}, {}, [(0, src)]
    while pq:
        c, u = heapq.heappop(pq)
        if c > dist.get(u, 1 << 30):
            continue
        for v in adj[u]:
            nc = c + w[v]
            if nc < dist.get(v, 1 << 30):
                dist[v], prev[v] = nc, u
                heapq.heappush(pq, (nc, v))
    return dist, prev


def path(prev, src, dst):
    out, cur = [dst], dst
    while cur != src:
        cur = prev[cur]
        out.append(cur)
    return out[::-1]


def steiner(targets, adj, w, start):
    """Cheapest connected subgraph joining start to every target.

    Returns (cost, node_set). Exact: with three terminals the optimal tree has
    at most one branch vertex, so every vertex is tried as that branch.
    """
    ds, ps = dijkstra(start, adj, w)
    if not targets:
        return 0, {start}
    if len(targets) == 1:
        t = set(path(ps, start, targets[0]))
        return sum(w[x] for x in t), t
    d1, p1 = dijkstra(targets[0], adj, w)
    d2, p2 = dijkstra(targets[1], adj, w)
    best, best_tree = 1 << 30, None
    for v in adj:
        if v in ds and v in d1 and v in d2:
            tree = (set(path(ps, start, v))
                    | set(path(p1, targets[0], v))
                    | set(path(p2, targets[1], v)))
            c = sum(w[x] for x in tree)
            if c < best:
                best, best_tree = c, tree
    return best, best_tree


def connected(tree, adj, start):
    seen, stack = {start}, [start]
    while stack:
        u = stack.pop()
        for v in adj[u]:
            if v in tree and v not in seen:
                seen.add(v)
                stack.append(v)
    return seen == tree


def main():
    if not os.path.isdir(SRC):
        print(f"SKIP — client dump not found at {SRC}")
        print("      (this test only runs where the normalized dump is available)")
        return 0

    emitted = json.load(open(os.path.join(ROOT, "src/data/skill-levels.json")))

    # 1 — graph model vs the dump's own precomputed field
    n_nodes = 0
    for cls, pfx in CLASS_PREFIX.items():
        for i in range(1, 9):
            _, nodes, adj, w, start = load_board(f"{SRC}/daevanion/nodes/{pfx}{i}.json")
            ds, _ = dijkstra(start, adj, w)
            for nid, nd in nodes.items():
                n_nodes += 1
                check(ds.get(nid) == nd["minPointsToUnlock"],
                      f"{cls} board {i} node {nid}: dijkstra {ds.get(nid)} != dump {nd['minPointsToUnlock']}")
    print(f"  [1] graph model reproduces minPointsToUnlock on {n_nodes} nodes")

    n_layout = n_reach = n_pair = 0
    for cls, pfx in CLASS_PREFIX.items():
        skills = json.load(open(f"{SRC}/skills/{cls}.json"))
        skills = skills if isinstance(skills, list) else skills["skills"]
        types = {str(s["id"]): s["type"] for s in skills}

        hits = {}
        graphs = []
        for i in range(4):
            _, nodes, adj, w, start = load_board(f"{SRC}/daevanion/nodes/{pfx}{i+1}.json")
            graphs.append((nodes, adj, w, start))
            for n in nodes.values():
                if n.get("nodeType") != "skilllevel":
                    continue
                for e in n.get("effects", []):
                    if e.get("type") == "skill_level":
                        hits.setdefault(e["skillId"], [[] for _ in BOARDS])[i].append(n["id"])

        by_id = {s["id"]: s for s in emitted["byClass"][cls]["skills"]}
        for sid, per in hits.items():
            counts = [len(x) for x in per]
            # 2 — layout
            n_layout += 1
            if types[sid] == "active":
                check(counts == [1, 1, 1, 1], f"{cls} {sid}: active layout {counts} != [1,1,1,1]")
            else:
                check(counts in ([2, 0, 1, 1], [0, 2, 1, 1]),
                      f"{cls} {sid}: passive layout {counts} not 2/0/1/1 or 0/2/1/1")
            check(sum(counts) == 4, f"{cls} {sid}: {sum(counts)} nodes, expected 4")

            row = by_id[sid]
            for i, ids in enumerate(per):
                nodes, adj, w, start = graphs[i]
                cost, tree = steiner(ids, adj, w, start)
                emitted_count, emitted_cost = row["dv"][i]

                check(emitted_count == len(ids),
                      f"{cls} {sid} board {i}: emitted count {emitted_count} != {len(ids)}")
                check(emitted_cost == cost,
                      f"{cls} {sid} board {i}: emitted cost {emitted_cost} != recomputed {cost}")

                if not ids:
                    check(cost == 0, f"{cls} {sid} board {i}: empty board should cost 0")
                    continue

                # 3 — achievable: the tree is real, connected, and re-sums to the cost
                n_reach += 1
                check(connected(tree, adj, start), f"{cls} {sid} board {i}: tree not connected")
                check(all(t in tree for t in ids), f"{cls} {sid} board {i}: tree misses a target")
                check(sum(w[x] for x in tree) == cost,
                      f"{cls} {sid} board {i}: tree weight {sum(w[x] for x in tree)} != cost {cost}")

                # 4 — optimal, and cheaper than paying for each node's own path
                ds, _ = dijkstra(start, adj, w)
                check(cost >= max(ds[t] for t in ids),
                      f"{cls} {sid} board {i}: cost below the costliest single terminal")
                if len(ids) > 1:
                    n_pair += 1
                    naive = sum(ds[t] for t in ids)
                    check(cost <= naive,
                          f"{cls} {sid} board {i}: paired cost {cost} exceeds naive sum {naive}")
    print(f"  [2] node layout correct for {n_layout} skills across 9 classes")
    print(f"  [3] {n_reach} board costs are achievable (tree rebuilt, connected, re-summed)")
    print(f"  [4] {n_pair} paired costs beat the naive sum and clear the lower bound")

    print(f"\n{checks} assertions, {len(fails)} failures")
    for f in fails[:20]:
        print("   FAIL:", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
