#!/usr/bin/env python3
"""Emit src/data/skill-levels.json — every source that can raise a skill's level.

Sources, all read from the Global LST client pull (2026-09-21):
  * skill points     1-10, universal (not in the pull; a rule of the game)
  * daevanion        the crystal boards that carry skill nodes (four: Nezekan,
                     Zikel, Vaizel, Triniel), +4 total. Actives take one node
                     per board; passives take TWO on either Nezekan or Zikel
                     and none on the other. Read from src/data/daevanion.json,
                     which is a verified-lossless copy of the raw boards, so
                     the class list (Brawler excluded as stale) and the graph
                     are the same ones the board page shows.
  * soul bind lines  items.json: equipmentInfo.soulbindRandomSkillCount per
                     grade, split by itemStats.subSkillGroup —
                     Active_EnchantEffect (weapons, guards, rings) or
                     Passive_EnchantEffect (earrings, necklace, armor).
  * arcana lines     items.json: the arcana cards, soulbindRandomSkillCount per
                     grade and which card types exist.

What the Global pull does NOT carry, and is therefore no longer emitted (the
lib and component tolerate the absence):
  * per-skill pool membership. The Taiwan dump had substat_skill_pools with
    every skill's random_prob per pool and the small-card (Parchment / Compass
    / Bell / Mirror) membership. The Global items only name the group
    (`subSkillGroup`); `subStats` holds stat lines only. So the row fields
    `card` (which small card carries the skill) and `p` (exact per-line odds)
    are gone, and `cardPool.small` with them.

Usage:  python3 scripts/build-skill-levels.py
"""
import collections
import heapq
import json
import os
import sys

RAW = "/home/claude/aion2-data/raw"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAEVANION = os.path.join(ROOT, "src/data/daevanion.json")
OUT = os.path.join(ROOT, "src/data/skill-levels.json")
ICON_DIR = os.path.join(ROOT, "public/icons/skills")     # <class>_<skill|passive>_<slug>.webp
BOARD_ICON_DIR = os.path.join(ROOT, "public/skills")     # <class>/<slug>.webp (board page)

# arcana subCategory -> in-game card name. Only the ones the item DB carries are
# emitted; the Taiwan dump also had libra (Scales), which Global does not.
CARD_NAME = {"parchment": "Parchment", "compass": "Compass", "bell": "Bell",
             "mirror": "Mirror", "grail": "Chalice", "libra": "Scales"}
GRADE_NAME = {11: "Common", 21: "Rare", 31: "Legend", 41: "Unique", 51: "Mythic", 71: "Heroic"}

# One soul bind line in five lands on a skill, the rest on a stat. This is an
# in-game observation (Soul Binding window, Taiwan client, 2026-08-31), not a
# field of any pull; the Global pull has nothing that confirms or denies it.
SKILL_DRAW_CHANCE = 0.2


def load(name):
    with open(os.path.join(RAW, name)) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# path costs on a board
# ---------------------------------------------------------------------------

def dijkstra(src, adj, w):
    """Node-weighted shortest paths. dist[v] counts the cost of v but not of the
    free centre."""
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


def board_graph(dv, cls, god):
    """(adj, weights, start, skill_nodes) for one class x board, rebuilt from the
    normalized daevanion file: shared layout + class patches + skill overlay,
    4-neighbour adjacency (the dump has no link field; see src/data/README.md).
    skill_nodes is [(node, skillId)] in row-major order."""
    nodes = {(n["r"], n["c"]): n for n in dv["layouts"][god]["nodes"]}
    for p in dv.get("patches", {}).get(cls, {}).get(god, []):
        nodes[(p["r"], p["c"])] = p
    adj = {k: [nb for nb in ((k[0] - 1, k[1]), (k[0] + 1, k[1]), (k[0], k[1] - 1), (k[0], k[1] + 1))
               if nb in nodes] for k in nodes}
    w = {k: dv["gradeCost"][str(n["g"])] for k, n in nodes.items()}
    start = next(k for k, n in nodes.items() if n["t"] == 0)
    overlay = iter(dv["overlays"][cls].get(god, []))
    skill_nodes = [(k, next(overlay)) for k in sorted(nodes) if nodes[k]["t"] == 2]
    assert next(overlay, None) is None, f"{cls}/{god}: overlay longer than the skill nodes"
    return adj, w, start, skill_nodes


# ---------------------------------------------------------------------------

def main():
    skills_raw = {s["id"]: s for s in load("skills.json")["detail"]}
    with open(DAEVANION) as f:
        dv = json.load(f)

    classes = [c["key"] for c in dv["classes"]]
    display = {c["key"]: c["name"] for c in dv["classes"]}
    boards = [g for g in sorted(dv["gods"], key=lambda g: g["order"]) if g["hasSkills"]]
    board_keys = [g["key"] for g in boards]

    # classes in the skills DB that are not emitted, with what the DB has for
    # them, so the exclusion is re-justified by data on every run
    per_class = collections.defaultdict(collections.Counter)
    for s in skills_raw.values():
        if s.get("mainCategory"):
            per_class[s["mainCategory"]][s["subCategory"]] += 1
    for cls in sorted(per_class):
        if cls in classes or cls == "tutorial":
            continue
        have = per_class[cls]
        print(f"not emitted: {cls} — daevanion.json leaves it out (stale boards) and the skills DB "
              f"has only {have.get('active', 0)} active / {have.get('passive', 0)} passive / "
              f"{have.get('stigma', 0)} stigma skills for it")

    missing_icons = []
    out_classes, by_class = [], {}
    for cls in classes:
        # the class's non-stigma skills, straight from the skills DB
        skills = {sid: s for sid, s in skills_raw.items()
                  if s.get("mainCategory") == cls and s["subCategory"] in ("active", "passive")}
        slug_of = {sid: v["s"] for sid, v in dv["skills"].items() if v["c"] == cls}

        # class weapon, from any skill that names one
        weapons = collections.Counter()
        for s in skills.values():
            for wpn in s.get("requiredWeapons") or []:
                weapons[wpn] += 1
        weapon = weapons.most_common(1)[0][0] if weapons else None

        # daevanion: which nodes each board carries, then the true cost to take them
        hits = collections.defaultdict(lambda: [[] for _ in boards])
        graphs, dvgrade = [], {}
        for i, god in enumerate(board_keys):
            adj, w, start, skill_nodes = board_graph(dv, cls, god)
            graphs.append((adj, w, start))
            for key, sid in skill_nodes:
                hits[sid][i].append(key)
                dvgrade[sid] = w[key]

        assert set(hits) == set(skills), (
            f"{cls}: board skills and skills-DB skills disagree — "
            f"{sorted(set(hits) ^ set(skills))}"
        )

        # [[node count, points], ...] per board — 0 nodes means the board skips it
        dvcost = {sid: [[len(ids), board_cost(ids, *graphs[i])] for i, ids in enumerate(per)]
                  for sid, per in hits.items()}

        rows = []
        for sid in sorted(skills, key=lambda i: (skills[i]["name"], i)):
            s = skills[sid]
            assert s["type"] == s["subCategory"], (sid, s["type"], s["subCategory"])
            icon = f"{cls}_{'passive' if s['type'] == 'passive' else 'skill'}_{slug_of[sid]}.webp"
            for p in (os.path.join(ICON_DIR, icon),
                      os.path.join(BOARD_ICON_DIR, cls, f"{slug_of[sid]}.webp")):
                if not os.path.exists(p):
                    missing_icons.append(p)
            rows.append({
                "id": sid,
                "n": s["name"],
                "t": s["type"],
                "icon": icon,
                "dv": dvcost[sid],
                "lv": sum(c for c, _ in dvcost[sid]),
                "dc": dvgrade[sid],
            })
        n_active = sum(r["t"] == "active" for r in rows)
        n_passive = sum(r["t"] == "passive" for r in rows)
        assert (n_active, n_passive) == (12, 10), f"{cls}: {n_active} actives / {n_passive} passives"
        for r in rows:
            assert r["lv"] == 4, f"{cls} {r['n']}: boards grant {r['lv']}, expected 4"
            counts = [c for c, _ in r["dv"]]
            if r["t"] == "active":
                assert counts == [1] * len(boards), f"{cls} {r['n']}: active layout {counts}"
            else:
                assert sorted(counts[:2]) == [0, 2] and counts[2:] == [1] * (len(boards) - 2), \
                    f"{cls} {r['n']}: passive layout {counts}"

        out_classes.append({"key": cls, "name": display[cls]})
        by_class[cls] = {"weapon": weapon, "skills": rows}

    out_classes.sort(key=lambda c: c["name"])
    pools = {(len([r for r in v["skills"] if r["t"] == "active"]),
              len([r for r in v["skills"] if r["t"] == "passive"])) for v in by_class.values()}
    assert len(pools) == 1, f"pool sizes differ between classes: {pools}"
    active_pool, passive_pool = next(iter(pools))

    # ---- items: soul bind and arcana line counts by grade --------------------
    # Indexed by id once; only the equipment with skill lines is read.
    items = {it["id"]: it for it in load("items.json")["detail"]}
    gear_slots = {"active": collections.defaultdict(set), "passive": collections.defaultdict(set)}
    slot_group = collections.defaultdict(set)      # (mainCategory, subCategory) -> groups seen
    arcana_lines, card_types = collections.defaultdict(set), set()
    for it in items.values():
        eq = it.get("equipmentInfo") or {}
        if not eq.get("useSubStatSkill"):
            continue
        n, grade = eq["soulbindRandomSkillCount"], GRADE_NAME[it["grade"]]
        group = (it.get("itemStats") or {}).get("subSkillGroup") or ""
        if it["mainCategory"] == "arcana":
            assert group == f"Arcana_Skill_Random_{it['subCategory'].title()}_{grade}_1", (it["id"], group)
            arcana_lines[grade].add(n)
            card_types.add(it["subCategory"])
            continue
        slot_group[(it["mainCategory"], it["subCategory"])].add(group)
        if group.startswith("Active"):
            gear_slots["active"][grade].add(n)
        elif group.startswith("Passive"):
            gear_slots["passive"][grade].add(n)
        else:
            raise AssertionError(f"{it['id']}: unexpected subSkillGroup {group!r}")
    for slot, groups in sorted(slot_group.items()):
        assert len(groups) == 1, f"{slot} draws from more than one pool: {groups}"
    print("soul bind pools by slot:")
    for slot, groups in sorted(slot_group.items()):
        print(f"  {slot[0]:<10} {slot[1]:<11} {next(iter(groups))}")
    assert set(card_types) <= set(CARD_NAME), card_types
    print("arcana card types in the item DB:", sorted(card_types),
          "— absent:", sorted(set(CARD_NAME) - card_types))
    grade_order = list(GRADE_NAME.values())
    by_grade = lambda by: {g: [min(by[g]), max(by[g])] for g in grade_order if g in by}

    doc = {
        "classes": out_classes,
        "boards": [{"name": g["key"], "needLevel": g["needLevel"]} for g in boards],
        "cards": {k: v for k, v in CARD_NAME.items() if k in card_types},
        "skillDrawChance": SKILL_DRAW_CHANCE,
        "activePool": active_pool,
        "passivePool": passive_pool,
        # `small` (Parchment/Compass = 6 actives each, Bell/Mirror = 5 passives
        # each) came from the Taiwan pool tables; the Global pull has no pool
        # membership, so only the class-wide count remains.
        "cardPool": {"union": active_pool + passive_pool},
        # every grade that can carry a skill line, and how many it holds
        "gearSlots": {k: by_grade(by) for k, by in gear_slots.items()},
        "arcanaLines": by_grade(arcana_lines),
        "byClass": by_class,
    }

    if missing_icons:
        print(f"MISSING ICONS ({len(missing_icons)}):")
        for p in missing_icons:
            print("  ", os.path.relpath(p, ROOT))
    else:
        print(f"icons: every emitted skill has both {os.path.relpath(ICON_DIR, ROOT)}/ and "
              f"{os.path.relpath(BOARD_ICON_DIR, ROOT)}/ files")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(doc, f, separators=(",", ":"))
    print(f"wrote {os.path.relpath(OUT, ROOT)}  {os.path.getsize(OUT):,} bytes  "
          f"{len(out_classes)} classes x {active_pool + passive_pool} skills, "
          f"{len(boards)} boards")
    print("class order:", [c["name"] for c in out_classes])
    print("gearSlots:", json.dumps(doc["gearSlots"]))
    print("arcanaLines:", json.dumps(doc["arcanaLines"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
