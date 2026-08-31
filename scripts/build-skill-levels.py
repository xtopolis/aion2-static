#!/usr/bin/env python3
"""Emit src/data/skill-levels.json — every source that can raise a skill's level.

Sources, all verified against the normalized client dump:
  * skill points     1-10, universal
  * daevanion        4 crystal boards, +4 total. Actives take one node per
                     board; passives take TWO on either Nezekan or Zikel and
                     none on the other.
  * soul bind lines  Active_EnchantEffect (rings/weapons) | Passive_EnchantEffect
                     (earrings/necklace/armor); +1 each, level_max_value 1
  * arcana lines     small-pool card + Chalice + Scales; +1 base up to +4
"""
import glob
import heapq
import json, os, re, collections

SRC = "/root/aion2/data/normalized"
OUT = "src/data/skill-levels.json"

CLASS_BOARD_PREFIX = {"gladiator":"1","templar":"2","ranger":"3","assassin":"4",
                      "elementalist":"5","sorcerer":"6","cleric":"7","chanter":"8","fighter":"9"}
BOARDS = ["Nezekan", "Zikel", "Vaizel", "Triniel"]
# arcana slot key -> in-game card name
CARD_NAME = {"parchment":"Parchment","compass":"Compass","bell":"Bell",
             "mirror":"Mirror","grail":"Chalice","libra":"Scales"}

def j(p): return json.load(open(os.path.join(SRC, p)))


def dijkstra(src, adj, w):
    """Node-weighted shortest paths. dist[v] counts the cost of v but not of the
    free centre. Reproduces the dump's own minPointsToUnlock exactly."""
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
    """Node ids along src -> dst, inclusive of both ends."""
    out, cur = [dst], dst
    while cur != src:
        cur = prev[cur]
        out.append(cur)
    return out[::-1]


def board_cost(targets, adj, w, start):
    """Cheapest connected subgraph joining the centre to every target node.

    A skill has one node per board for actives, but passives carry TWO on either
    Nezekan or Zikel and none on the other. Two nodes share most of their path
    out from the centre, so adding their individual costs overstates the bill.

    With three terminals (the centre plus two nodes) an optimal Steiner tree has
    at most one branch vertex, so every vertex is tried as that branch. Each
    candidate is scored by REBUILDING the tree and summing its node weights,
    never by an inclusion-exclusion formula -- the arithmetic around shared
    endpoints is easy to get subtly wrong (it was, once: the terminals' own
    weights went missing and every paired cost came out 4 low), and a rebuilt
    tree cannot lie. See scripts/test_daevanion_math.py.
    """
    if not targets:
        return 0
    if len(targets) > 2:
        # the branch-vertex enumeration below is exact for three terminals
        # (start + two nodes) and NOT for more; fail loudly rather than
        # silently costing only the first two
        raise NotImplementedError(
            f"board_cost got {len(targets)} targets; the solver is exact for at "
            "most 2 (plus the centre). Use a general Steiner solver if the data "
            "ever grows a third node on one board."
        )
    ds, ps = dijkstra(start, adj, w)
    if len(targets) == 1:
        return sum(w[x] for x in path(ps, start, targets[0]))
    d1, p1 = dijkstra(targets[0], adj, w)
    d2, p2 = dijkstra(targets[1], adj, w)
    best = 1 << 30
    for v in adj:
        if v in ds and v in d1 and v in d2:
            tree = (set(path(ps, start, v))
                    | set(path(p1, targets[0], v))
                    | set(path(p2, targets[1], v)))
            best = min(best, sum(w[x] for x in tree))
    return best

pools = j("stats/substat_skill_pools.json")["groups"]

def pool_ids(group, cls):
    e = pools.get(group, {}).get("classes", {}).get(cls)
    return {s["skill_id"] for s in e["skills"]} if e else set()

# display names + class order come from the daevanion dataset the board page already uses
dv = json.load(open("src/data/daevanion.json"))
display = {c["key"]: c["name"] for c in dv["classes"]}

out_classes, by_class = [], {}

for cls, pfx in CLASS_BOARD_PREFIX.items():
    skills = j(f"skills/{cls}.json")
    skills = skills if isinstance(skills, list) else skills["skills"]
    by_id = {str(s["id"]): s for s in skills}
    slug_of = {k: v["s"] for k, v in dv["skills"].items() if v["c"] == cls}

    # class weapon, from any skill that names one
    weapons = collections.Counter()
    for s in skills:
        for w in (s.get("requiredWeapons") or []): weapons[w] += 1
    weapon = weapons.most_common(1)[0][0] if weapons else None

    # which small-pool arcana card carries each skill
    card_of = {}
    for key in ("Parchment", "Compass", "Bell", "Mirror"):
        for sid in pool_ids(f"Arcana_Skill_Random_{key}_Unique_1", cls):
            card_of[sid] = key.lower()

    # daevanion: which nodes each board carries, then the true cost to take them
    hits = collections.defaultdict(lambda: [[] for _ in BOARDS])
    graphs, dvgrade = [], {}
    for i, b in enumerate(BOARDS):
        board = j(f"daevanion/nodes/{pfx}{i+1}.json")
        nodes = {n["id"]: n for n in board["nodes"]}
        graphs.append((
            {i2: [x for x in n.get("neighbors", []) if x in nodes] for i2, n in nodes.items()},
            {i2: n["cost"] for i2, n in nodes.items()},
            next(n["id"] for n in board["nodes"] if n["nodeType"] == "start"),
        ))
        for n in board["nodes"]:
            if n.get("nodeType") != "skilllevel": continue
            for e in n.get("effects", []):
                if e.get("type") != "skill_level": continue
                hits[e["skillId"]][i].append(n["id"])
                dvgrade[e["skillId"]] = n["cost"]

    # [[node count, points], ...] per board — 0 nodes means the board skips it
    dvcost = {}
    for sid, per in hits.items():
        dvcost[sid] = [
            [len(ids), board_cost(ids, *graphs[i])] for i, ids in enumerate(per)
        ]

    active = pool_ids("Active_EnchantEffect", cls)
    passive = pool_ids("Passive_EnchantEffect", cls)

    # random_prob is in 1/10000 and sums to 10000 within a pool; a line lands on
    # the pool at all 20% of the time, so a given skill is prob x 0.20
    draw = {}
    for grp in ("Active_EnchantEffect", "Passive_EnchantEffect"):
        e = pools.get(grp, {}).get("classes", {}).get(cls)
        for sk_ in (e["skills"] if e else []):
            draw[sk_["skill_id"]] = sk_["random_prob"] / 10000 * 0.20

    rows = []
    for sid in sorted(active | passive, key=lambda i: by_id[i]["name"]):
        s = by_id[sid]
        rows.append({
            "id": sid,
            "n": s["name"],
            "t": s["type"],
            # icons ship under class_type_slug.webp; the dump's ICON_* names
            # cover only part of the set, so they are not usable as the key
            "icon": f"{cls}_{'passive' if s['type'] == 'passive' else 'skill'}_{slug_of[sid]}.webp",
            "dv": dvcost[sid],
            "lv": sum(c for c, _ in dvcost[sid]),
            "dc": dvgrade[sid],
            "card": card_of.get(sid),
            "p": round(draw[sid], 8),
        })
    assert len(rows) == 22, f"{cls}: {len(rows)} skills"
    assert all(r["card"] for r in rows), f"{cls}: skill with no small-pool card"
    assert set(hits) == (active | passive), (
        f"{cls}: board skills and gear-pool skills disagree — "
        f"{sorted(set(hits) ^ (active | passive))}"
    )
    for r in rows:
        assert r["lv"] == 4, f"{cls} {r['n']}: boards grant {r['lv']}, expected 4"

    out_classes.append({"key": cls, "name": display.get(cls, cls.title())})
    by_class[cls] = {"weapon": weapon, "skills": rows}

out_classes.sort(key=lambda c: c["name"])

# slot / line counts by grade, straight from the items rather than assumed
# Slot / line counts by grade, straight from the items rather than assumed.
# Split by which pool the slot draws from: the slots that carry PASSIVE lines
# (earrings, necklace, armor) never roll 3 lines at Unique or 4 at Heroic, so a
# single combined range would overstate the passive row on the page.
gear_slots = {"active": collections.defaultdict(set), "passive": collections.defaultdict(set)}
arcana_lines = collections.defaultdict(set)
for item_file in glob.glob(os.path.join(SRC, "equipment/items/*.json")):
    for it in json.load(open(item_file))["items"]:
        eq = it.get("equipment") or {}
        if not eq.get("usesSubStatSkill"):
            continue
        n, grade = eq["randomSkillCount"], it.get("gradeName")
        if not grade:
            continue
        if "arcana__" in item_file:
            arcana_lines[grade].add(n)
            continue
        group = (it.get("stats") or {}).get("subSkillGroup") or ""
        if group.startswith("Active"):
            gear_slots["active"][grade].add(n)
        elif group.startswith("Passive"):
            gear_slots["passive"][grade].add(n)
rng = lambda v: [min(v), max(v)]

doc = {
    "classes": out_classes,
    "boards": [{"name": b, "needLevel": n} for b, n in zip(BOARDS, [12, 20, 30, 40])],
    "cards": CARD_NAME,
    # One soul bind line in five lands on a skill, the rest on a stat. VERIFIED
    # against the in-game Soul Binding window 2026-08-31: each skill displays
    # random_prob/10000 x 20%, and the dump's 833/834 split predicts exactly
    # which skills read 1.666% and which read 1.668% (8 of 8). The 12 actives
    # sum to 20.000%. Per-skill odds are emitted on each row as `p`.
    "skillDrawChance": 0.2,
    "activePool": 12,
    "passivePool": 10,
    "cardPool": {"small": {"active": 6, "passive": 5}, "union": 22},
    # every grade that can carry a skill line, and how many it holds
    "gearSlots": {k: {g: rng(v) for g, v in by.items() if g} for k, by in gear_slots.items()},
    "arcanaLines": {g: rng(v) for g, v in arcana_lines.items() if g},
    "byClass": by_class,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(doc, open(OUT, "w"), separators=(",", ":"))
print(f"wrote {OUT}  {os.path.getsize(OUT):,} bytes  {len(out_classes)} classes")
print("class order:", [c["name"] for c in out_classes])
