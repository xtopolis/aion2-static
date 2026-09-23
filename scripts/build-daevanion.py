#!/usr/bin/env python3
"""Emit src/data/daevanion.json from the Global LST client pull.

Reads the two raw datasets (boards + nodes) plus the skills dataset for the
skill index, and writes the same lossless normalization the board page has
always consumed: one shared stat layout per god, a per-class skill overlay for
the boards that carry skill nodes, and — new with the Global data — a small
per-class node patch list for the handful of stat nodes that differ between
classes on the same board.

Losslessness is enforced, not assumed: every board of every included class is
rebuilt from the emitted structure and compared to the raw node records field
by field (everything except `name`, which the raw data itself gets wrong — see
the README). Any mismatch aborts the run.

Usage:  python3 scripts/build-daevanion.py            (writes the file)
        python3 scripts/build-daevanion.py --check    (verify only, no write)
"""
import collections
import json
import os
import re
import sys

RAW = "/home/claude/aion2-data/raw"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "src/data/daevanion.json")
ICON_DIR = os.path.join(ROOT, "public/skills")

SOURCE = "Aion 2 Global LST client, 2026-09-21, normalized"

# Node kinds as stored in the normalized file (mirrored in src/lib/daevanion.ts).
NODE_TYPE = {"start": 0, "stat": 1, "skilllevel": 2}
NODE_TYPE_NAME = {v: k for k, v in NODE_TYPE.items()}

GRADE_NAMES = {0: "None", 11: "Common", 21: "Rare", 31: "Legendary", 41: "Unique", 51: "Mythic"}
GRADE_ICON = {
    0: "/assets/UT_FWindow_Daevanion_Node_Start_Sprite.webp",
    11: "/assets/UT_FWindow_Daevanion_Node_Common_Sprite.webp",
    21: "/assets/UT_FWindow_Daevanion_Node_Rare_Sprite.webp",
    31: "/assets/UT_FWindow_Daevanion_Node_Legend_Sprite.webp",
    41: "/assets/UT_FWindow_Daevanion_Node_Unique_Sprite.webp",
}

# Display names; the raw boards only carry the class key.
CLASS_NAME = {
    "gladiator": "Gladiator", "templar": "Templar", "ranger": "Ranger",
    "assassin": "Assassin", "elementalist": "Elementalist", "sorcerer": "Sorcerer",
    "cleric": "Cleric", "chanter": "Chanter", "fighter": "Brawler",
}

# Classes present in the pull but NOT emitted, with the reason. A class whose
# board skills are missing from the Global skills DB cannot be described
# honestly (no name, type or icon key for those skills), so it is left out
# rather than padded from another data source. The build prints how many of
# the class's skills resolve so the exclusion stays justified run to run.
EXCLUDE_CLASSES = {
    "fighter": "5 boards are byte-identical to the Taiwan 2026-08 boards (old node "
               "values, 153 nodes each) and only 5 of its 22 board skills exist in "
               "the Global skills DB — stale carry-over, not Global data",
}

GRID = {"rows": 15, "cols": 15}


def load(name):
    with open(os.path.join(RAW, name)) as f:
        return json.load(f)


def slug_of(name):
    """`public/skills/<class>/<slug>.webp`: lower-case, apostrophes dropped,
    every other non-alphanumeric run becomes one underscore."""
    s = re.sub(r"'", "", name.lower())
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def node_effect(raw_node):
    """[[statId, value], ...] for a stat node, None otherwise."""
    if raw_node["nodeType"] != "stat":
        return None
    return [[e["statName"], e["statValue"]] for e in raw_node["effect"]]


def norm_node(raw_node):
    n = {"r": raw_node["row"], "c": raw_node["col"], "g": raw_node["grade"],
         "t": NODE_TYPE[raw_node["nodeType"]]}
    e = node_effect(raw_node)
    if e is not None:
        n["e"] = e
    return n


def node_key(n):
    return (n["r"], n["c"])


def sig(nodes):
    """Hashable, order-independent identity of a stat layout (skill ids excluded)."""
    return tuple(sorted(json.dumps(n, sort_keys=True) for n in nodes))


def main():
    check_only = "--check" in sys.argv

    boards_raw = load("daevanion_boards.json")["detail"]
    nodes_raw = load("daevanion_nodes.json")["detail"]
    skills_raw = {s["id"]: s for s in load("skills.json")["detail"]}

    boards = {b["id"]: b for b in boards_raw}
    by_board = collections.defaultdict(list)
    for n in nodes_raw:
        by_board[n["boardId"]].append(n)
    for lst in by_board.values():
        lst.sort(key=lambda n: (n["row"], n["col"]))

    assert set(by_board) == set(boards), "nodes reference boards that are not in the board list"

    # ---- sanity on the invariants the schema relies on -------------------
    for n in nodes_raw:
        assert 1 <= n["row"] <= GRID["rows"] and 1 <= n["col"] <= GRID["cols"], n["id"]
        assert n["mainCategory"] == n["nodeType"], n["id"]
        assert n["icon"] == GRADE_ICON[n["grade"]], (n["id"], n["icon"])
        assert n["isAutoLearn"] == (n["nodeType"] == "start"), n["id"]
        assert n["resetGold"] == (0 if n["nodeType"] == "start" else 500), n["id"]
        assert n["needLevel"] == boards[n["boardId"]]["needLevel"], n["id"]
        # id = boardId + zero-padded row-major cell index
        assert n["id"] == f"{n['boardId']}{(n['row'] - 1) * GRID['cols'] + n['col']:04d}", n["id"]
        if n["nodeType"] == "start":
            assert (n["row"], n["col"]) == (8, 8) and "effect" not in n, n["id"]
        elif n["nodeType"] == "skilllevel":
            (eff,) = n["effect"]
            assert eff["type"] == "skill_level" and eff["levelIncrease"] == 1, n["id"]
        else:
            assert all(e["type"] == "stat" for e in n["effect"]) and n["effect"], n["id"]

    grade_cost = {}
    for n in nodes_raw:
        grade_cost.setdefault(n["grade"], set()).add(n["costDaevanionPoint"])
    assert all(len(v) == 1 for v in grade_cost.values()), f"grade→cost is not a function: {grade_cost}"
    grade_cost = {g: next(iter(v)) for g, v in sorted(grade_cost.items())}

    # ---- gods (board slots) -----------------------------------------------
    per_god = collections.defaultdict(dict)  # god -> class -> board id
    for b in boards_raw:
        assert b["buffTitle"] == f"Daevanion {b['name']} Effects", b["id"]
        per_god[b["name"]][b["classId"]] = b["id"]

    classes_all = sorted({b["classId"] for b in boards_raw}, key=lambda c: min(
        int(b["id"]) for b in boards_raw if b["classId"] == c))
    classes = [c for c in classes_all if c not in EXCLUDE_CLASSES]

    gods = []
    for god, by_cls in per_god.items():
        metas = {(boards[bid]["order"], boards[bid]["needLevel"], boards[bid]["costPointType"])
                 for bid in by_cls.values()}
        assert len(metas) == 1, f"{god}: board meta differs per class: {metas}"
        assert set(by_cls) == set(classes_all), f"{god}: missing for some class"
        order, need, cost_type = next(iter(metas))
        gods.append({"key": god, "order": order, "needLevel": need, "costPointType": cost_type})
    gods.sort(key=lambda g: g["order"])

    # ---- layouts + per-class patches ---------------------------------------
    layouts, patches, overlays = {}, collections.defaultdict(dict), collections.defaultdict(dict)
    for g in gods:
        god = g["key"]
        variants = {cls: [norm_node(n) for n in by_board[per_god[god][cls]]] for cls in classes}
        # the most common stat layout is the shared one; ties go to class order
        counts = collections.Counter(sig(v) for v in variants.values())
        best = max(counts.values())
        base_cls = next(c for c in classes if counts[sig(variants[c])] == best)
        base = variants[base_cls]
        base_by_key = {node_key(n): n for n in base}
        layouts[god] = {"nodes": base}

        for cls in classes:
            v_by_key = {node_key(n): n for n in variants[cls]}
            assert set(v_by_key) == set(base_by_key), (
                f"{god}/{cls}: node positions differ from the shared layout; "
                "patches can only replace nodes, not add or remove them")
            diff = [v_by_key[k] for k in sorted(v_by_key) if v_by_key[k] != base_by_key[k]]
            if diff:
                patches[cls][god] = diff

            skill_ids = [n["effect"][0]["skillId"] for n in by_board[per_god[god][cls]]
                         if n["nodeType"] == "skilllevel"]
            if skill_ids:
                overlays[cls][god] = skill_ids

        g["points"] = sum(grade_cost[n["g"]] for n in base)
        g["hasSkills"] = any(n["t"] == NODE_TYPE["skilllevel"] for n in base)
    gods = [{k: g[k] for k in ("key", "order", "needLevel", "points", "costPointType", "hasSkills")}
            for g in gods]

    # ---- skill index --------------------------------------------------------
    skills = {}
    for cls in classes:
        for god, ids in overlays[cls].items():
            for sid in ids:
                s = skills_raw.get(sid)
                assert s, f"{cls}/{god}: skill {sid} is not in the skills DB"
                assert s["mainCategory"] == cls, (sid, s["mainCategory"], cls)
                assert s["type"] in ("active", "passive"), (sid, s["type"])
                slug = slug_of(s["name"])
                icon = os.path.join(ICON_DIR, cls, f"{slug}.webp")
                assert os.path.exists(icon), f"missing icon {icon}"
                skills[sid] = {"n": s["name"], "c": cls, "t": s["type"], "s": slug}
    skills = dict(sorted(skills.items()))

    # excluded classes: report how badly their skills resolve, so the exclusion
    # is re-justified by data on every run
    for cls, why in EXCLUDE_CLASSES.items():
        ids = set()
        for god, by_cls in per_god.items():
            for n in by_board[by_cls[cls]]:
                if n["nodeType"] == "skilllevel":
                    ids.add(n["effect"][0]["skillId"])
        have = [i for i in ids if i in skills_raw and skills_raw[i]["type"] in ("active", "passive")]
        print(f"excluded {cls}: {len(have)}/{len(ids)} board skills resolve in the skills DB — {why}")

    out = {
        "schemaVersion": 2,
        "source": SOURCE,
        "note": (
            f"Lossless refactor of the {len(classes) * len(gods)}-board package: "
            f"{len(gods)} shared layouts + a per-class skill overlay, plus per-class node "
            "patches for the few stat nodes that differ between classes on one board. "
            "Node ids, names, neighbors, cost, resetGold and needLevel are omitted because "
            "they are derivable — see src/data/README.md."
        ),
        "grid": {"rows": GRID["rows"], "cols": GRID["cols"], "origin": {"row": 8, "col": 8}},
        "gradeNames": {str(g): GRADE_NAMES[g] for g in grade_cost},
        "gradeCost": {str(g): c for g, c in grade_cost.items()},
        "classes": [{"key": c, "name": CLASS_NAME[c]} for c in classes],
        "gods": gods,
        "layouts": layouts,
        "patches": {c: dict(patches[c]) for c in classes if patches.get(c)},
        "skills": skills,
        "overlays": {c: dict(overlays[c]) for c in classes},
    }

    # ---- losslessness: rebuild every emitted board and diff against raw ------
    def rebuild(cls, god_meta):
        god = god_meta["key"]
        nodes = {node_key(n): dict(n) for n in out["layouts"][god]["nodes"]}
        for p in out["patches"].get(cls, {}).get(god, []):
            nodes[node_key(p)] = dict(p)
        overlay = iter(out["overlays"][cls].get(god, []))
        board_id = per_god[god][cls]
        rebuilt = []
        for key in sorted(nodes):
            n = nodes[key]
            kind = NODE_TYPE_NAME[n["t"]]
            rec = {
                "id": f"{board_id}{(n['r'] - 1) * GRID['cols'] + n['c']:04d}",
                "icon": GRADE_ICON[n["g"]],
                "grade": n["g"],
                "language": "en",
                "dbType": "daevanion-node",
                "mainCategory": kind,
                "boardId": board_id,
                "row": n["r"],
                "col": n["c"],
                "nodeType": kind,
                "isAutoLearn": kind == "start",
                "needLevel": god_meta["needLevel"],
                "costDaevanionPoint": out["gradeCost"][str(n["g"])],
                "resetGold": 0 if kind == "start" else 500,
                "isDisabled": False,
            }
            if kind == "stat":
                rec["effect"] = [{"type": "stat", "statName": s, "statValue": v} for s, v in n["e"]]
            elif kind == "skilllevel":
                rec["effect"] = [{"type": "skill_level", "skillId": next(overlay), "levelIncrease": 1}]
            rebuilt.append(rec)
        assert next(overlay, None) is None, f"{cls}/{god}: overlay longer than the skill nodes"
        return rebuilt

    IGNORE = {"name", "createdAt", "updatedAt"}
    boards_checked = nodes_checked = 0
    for cls in classes:
        for g in gods:
            raw = by_board[per_god[g["key"]][cls]]
            got = rebuild(cls, g)
            assert len(raw) == len(got), (cls, g["key"], len(raw), len(got))
            for a, b in zip(raw, got):
                a2 = {k: v for k, v in a.items() if k not in IGNORE}
                assert a2 == b, f"{cls}/{g['key']} node {a['id']}:\n raw {a2}\n out {b}"
                nodes_checked += 1
            boards_checked += 1
    print(f"lossless: {boards_checked} boards / {nodes_checked} nodes rebuilt and matched field-by-field")

    # points recomputed from data, per board slot
    for g in gods:
        print(f"  {g['key']:<8} order {g['order']} lv{g['needLevel']:<3} {len(out['layouts'][g['key']]['nodes']):>3} nodes "
              f"{g['points']:>3} pts  {g['costPointType']}  skills={g['hasSkills']}")
    print(f"  total per class: {sum(g['points'] for g in gods)}")
    print(f"classes {len(classes)}, layouts {len(layouts)}, skills {len(skills)}, "
          f"patched nodes {sum(len(v) for c in out['patches'].values() for v in c.values())}")

    if check_only:
        return 0
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {OUT}  {os.path.getsize(OUT):,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
