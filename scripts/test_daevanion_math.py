#!/usr/bin/env python3
"""Verify the Daevanion board graph and the path-cost maths built on it.

Reads the Global LST client pull (boards + nodes + skills) and the normalized
src/data/daevanion.json. Skips cleanly when the raw pull is not present, so it
only runs where the data lives.

Checks, in increasing order of how much they could hurt if wrong:

  1. src/data/daevanion.json reproduces the raw boards: every emitted class x
     board is rebuilt (shared layout + class patches + skill overlay) and its
     positions, grades, kinds, stats and skill ids match the raw node records.
     Nothing about the board count or class count is assumed; both are read.
  2. The 4-neighbour prerequisite graph is connected on every board — every
     node is buyable from the free centre. (The dump carries no link field, so
     adjacency is the model; an island would mean the model is wrong.)
  3. The per-class skill layout is what the skill-levels page claims: actives
     once per skill board, passives twice on exactly one of the first two and
     absent from the other, four nodes per skill in total.
  4. Every paired-board cost is ACHIEVABLE — the tree is reconstructed, checked
     for connectivity, and its node weights re-summed independently.
  5. Every paired-board cost is OPTIMAL. A Steiner tree over three terminals has
     at most one branch vertex, so enumerating every vertex as the branch point
     is exhaustive; this is bounded below by the costliest single terminal and
     above by the naive per-node sum.
  6. src/data/skill-levels.json carries the same per-board node counts and
     costs (`dv`). This is a cross-dataset check: it fails whenever that file
     was built from older boards than these, and says so.
"""
import collections
import heapq
import json
import os
import sys

RAW = "/home/claude/aion2-data/raw"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE_TYPE = {"start": 0, "stat": 1, "skilllevel": 2}

fails, checks = [], 0


def check(cond, msg):
    global checks
    checks += 1
    if not cond:
        fails.append(msg)


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
    assert len(targets) == 2, "solver is exact for at most two targets plus the centre"
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


def graph_of(nodes, cost_of):
    """(adj, weights, start) from raw node records, 4-neighbour adjacency."""
    pos = {(n["row"], n["col"]): n["id"] for n in nodes}
    adj = {}
    for (r, c), nid in pos.items():
        adj[nid] = [pos[k] for k in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)) if k in pos]
    w = {n["id"]: cost_of(n["grade"]) for n in nodes}
    start = next(n["id"] for n in nodes if n["nodeType"] == "start")
    return adj, w, start


def main():
    if not os.path.isdir(RAW):
        print(f"SKIP — Global LST pull not found at {RAW}")
        print("      (this test only runs where the raw data is available)")
        return 0

    with open(os.path.join(RAW, "daevanion_boards.json")) as f:
        boards = {b["id"]: b for b in json.load(f)["detail"]}
    with open(os.path.join(RAW, "daevanion_nodes.json")) as f:
        by_board = collections.defaultdict(list)
        for n in json.load(f)["detail"]:
            by_board[n["boardId"]].append(n)
    with open(os.path.join(RAW, "skills.json")) as f:
        skill_type = {s["id"]: s["type"] for s in json.load(f)["detail"]}
    with open(os.path.join(ROOT, "src/data/daevanion.json")) as f:
        dv = json.load(f)

    cost_of = lambda g: dv["gradeCost"][str(g)]
    gods = [g["key"] for g in sorted(dv["gods"], key=lambda g: g["order"])]
    skill_gods = [g["key"] for g in sorted(dv["gods"], key=lambda g: g["order"]) if g["hasSkills"]]
    classes = [c["key"] for c in dv["classes"]]
    board_of = {(b["classId"], b["name"]): bid for bid, b in boards.items()}

    # 1 — the normalized file rebuilds every raw board it covers
    n_nodes = 0
    for cls in classes:
        for god in gods:
            raw = sorted(by_board[board_of[(cls, god)]], key=lambda n: (n["row"], n["col"]))
            nodes = {(n["r"], n["c"]): n for n in dv["layouts"][god]["nodes"]}
            for p in dv.get("patches", {}).get(cls, {}).get(god, []):
                nodes[(p["r"], p["c"])] = p
            overlay = iter(dv["overlays"][cls].get(god, []))
            check(len(raw) == len(nodes), f"{cls}/{god}: {len(raw)} raw nodes vs {len(nodes)} rebuilt")
            for rn in raw:
                n_nodes += 1
                en = nodes.get((rn["row"], rn["col"]))
                if not en:
                    check(False, f"{cls}/{god}: raw node at {rn['row']},{rn['col']} missing")
                    continue
                check(en["g"] == rn["grade"] and en["t"] == NODE_TYPE[rn["nodeType"]],
                      f"{cls}/{god} {rn['row']},{rn['col']}: grade/kind mismatch")
                if rn["nodeType"] == "stat":
                    want = [[e["statName"], e["statValue"]] for e in rn["effect"]]
                    check(en.get("e") == want, f"{cls}/{god} {rn['row']},{rn['col']}: {en.get('e')} != {want}")
                elif rn["nodeType"] == "skilllevel":
                    check(next(overlay, None) == rn["effect"][0]["skillId"],
                          f"{cls}/{god} {rn['row']},{rn['col']}: overlay skill mismatch")
            check(next(overlay, None) is None, f"{cls}/{god}: overlay has extra entries")
    print(f"  [1] daevanion.json rebuilds {len(classes) * len(gods)} boards / {n_nodes} nodes "
          f"({len(classes)} classes x {len(gods)} boards)")

    # 2 — the adjacency model reaches every node from the centre
    n_boards = 0
    for cls in classes:
        for god in gods:
            adj, w, start = graph_of(by_board[board_of[(cls, god)]], cost_of)
            ds, _ = dijkstra(start, adj, w)
            n_boards += 1
            check(len(ds) == len(adj), f"{cls}/{god}: {len(adj) - len(ds)} nodes unreachable from the centre")
    print(f"  [2] 4-neighbour graph is connected on all {n_boards} boards")

    # 3-5 — skill layout and path costs
    with open(os.path.join(ROOT, "src/data/skill-levels.json")) as f:
        emitted = json.load(f)
    first_two = skill_gods[:2]
    n_layout = n_reach = n_pair = n_dv = 0
    stale = []
    for cls in classes:
        hits, graphs = {}, {}
        for god in skill_gods:
            nodes = by_board[board_of[(cls, god)]]
            graphs[god] = graph_of(nodes, cost_of)
            for n in nodes:
                if n["nodeType"] != "skilllevel":
                    continue
                sid = n["effect"][0]["skillId"]
                hits.setdefault(sid, {g: [] for g in skill_gods})[god].append(n["id"])

        by_id = {s["id"]: s for s in emitted.get("byClass", {}).get(cls, {}).get("skills", [])}
        for sid, per in hits.items():
            counts = [len(per[g]) for g in skill_gods]
            n_layout += 1
            if skill_type.get(sid) == "active":
                check(counts == [1] * len(skill_gods), f"{cls} {sid}: active layout {counts}")
            else:
                two = [g for g in first_two if len(per[g]) == 2]
                none = [g for g in first_two if len(per[g]) == 0]
                rest = [len(per[g]) for g in skill_gods[2:]]
                check(len(two) == 1 and len(none) == 1 and rest == [1] * len(rest),
                      f"{cls} {sid}: passive layout {counts} not 2/0/1/1 or 0/2/1/1")
            check(sum(counts) == 4, f"{cls} {sid}: {sum(counts)} nodes, expected 4")

            for i, god in enumerate(skill_gods):
                ids = per[god]
                adj, w, start = graphs[god]
                cost, tree = steiner(ids, adj, w, start)

                if sid in by_id and i < len(by_id[sid]["dv"]):
                    n_dv += 1
                    e_count, e_cost = by_id[sid]["dv"][i]
                    if (e_count, e_cost) != (len(ids), cost):
                        stale.append(f"{cls} {sid} {god}: skill-levels.json dv {e_count}/{e_cost} vs boards {len(ids)}/{cost}")

                if not ids:
                    check(cost == 0, f"{cls} {sid} {god}: empty board should cost 0")
                    continue

                n_reach += 1
                check(connected(tree, adj, start), f"{cls} {sid} {god}: tree not connected")
                check(all(t in tree for t in ids), f"{cls} {sid} {god}: tree misses a target")
                check(sum(w[x] for x in tree) == cost,
                      f"{cls} {sid} {god}: tree weight {sum(w[x] for x in tree)} != cost {cost}")

                ds, _ = dijkstra(start, adj, w)
                check(cost >= max(ds[t] for t in ids),
                      f"{cls} {sid} {god}: cost below the costliest single terminal")
                if len(ids) > 1:
                    n_pair += 1
                    naive = sum(ds[t] for t in ids)
                    check(cost <= naive, f"{cls} {sid} {god}: paired cost {cost} exceeds naive sum {naive}")
    print(f"  [3] node layout correct for {n_layout} skills across {len(classes)} classes")
    print(f"  [4] {n_reach} board costs are achievable (tree rebuilt, connected, re-summed)")
    print(f"  [5] {n_pair} paired costs beat the naive sum and clear the lower bound")

    # 6 — cross-dataset: skill-levels.json must agree with these boards
    check(not stale, f"skill-levels.json disagrees with the boards on {len(stale)} of {n_dv} dv entries "
                     "— it was built from older boards; regenerate it")
    if stale:
        print(f"  [6] skill-levels.json is STALE: {len(stale)}/{n_dv} dv entries differ, e.g.")
        for s in stale[:5]:
            print("        ", s)
    else:
        print(f"  [6] skill-levels.json agrees on all {n_dv} dv entries")

    print(f"\n{checks} assertions, {len(fails)} failures")
    for f in fails[:20]:
        print("   FAIL:", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
