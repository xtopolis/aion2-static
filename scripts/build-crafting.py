#!/usr/bin/env python3
"""Generate src/data/crafting.json from the Global LST client pull.

Inputs (outside the repo):
  RAW/recipes.json      {list, detail, ...} recipe pull
  RAW/gatherables.json  {list, detail, ...} gatherable pull

Output schema (unchanged from the Taiwan-dump normalization, see src/data/README.md):
  professions  sorted mainCategory keys; recipes index into it via `p`
  icons        sorted icon basenames; recipes/items/gatherables index into it via `c`
  recipes      [{i, n, c, p, t, g, f, gauge, in, out, m?, mg?, cp?, co?}] sorted by id
  items        {id: [name, iconIndex, grade, sourceKind, isCurrency]} sorted by id
  gatherables  [{i, n, c, g, cat, m, d}] sorted by id

Combo stubs (learnType "combo", no inputs: the proc *result* listed as its own
recipe) are dropped here; the Taiwan handoff had already dropped them upstream.
Deterministic and idempotent; the file is minified like the original.
"""
import json
import os

RAW = "/home/claude/aion2-data/raw"
OUT = os.path.join(os.path.dirname(__file__), "..", "src", "data", "crafting.json")

SOURCE = "Aion 2 Global LST client, 2026-09-21, normalized"
NOTE = (
    "Combo stubs dropped at build time (learnType \"combo\", no inputs; they are proc results "
    "listed as their own recipe). craftedBy / comboOf / usedIn are dropped: they are indexes over "
    "these same recipes and gatherables, rebuilt client-side. See src/data/README.md."
)

# The only currency-like items the dataset has ever listed as inputs. Flagged so the
# UI shows them as a cost rather than a material; matching is by the item's own
# mainCategory, with these ids as a fallback in case a future pull drops the category.
CURRENCY_IDS = {"930100003", "930100013", "930100014", "930100015", "930100030"}


def load(name):
    with open(os.path.join(RAW, name)) as f:
        return json.load(f)["detail"]


def icon_base(path):
    """'/assets/.../Icon_WP_SW_0052_T04.Icon_WP_SW_0052_T04' -> 'Icon_WP_SW_0052_T04'."""
    return path.rsplit(".", 1)[-1] if path else ""


def main():
    raw_recipes = load("recipes.json")
    raw_gather = load("gatherables.json")

    recipes = [r for r in raw_recipes if r["learnType"] != "combo" and r["recipeInputItems"]]
    assert all(not r["recipeInputItems"] for r in raw_recipes if r["learnType"] == "combo")

    professions = sorted({r["mainCategory"] for r in recipes})
    prof_index = {p: i for i, p in enumerate(professions)}

    # ---- collect items (name, icon, grade) from every place they are mentioned
    items = {}  # id -> [name, iconBase, grade]
    is_currency = set()

    def see(entry):
        iid = entry["id"]
        if iid not in items:
            items[iid] = [entry["name"], icon_base(entry["icon"]), entry["grade"]]
        if entry.get("mainCategory") == "currency" or iid in CURRENCY_IDS:
            is_currency.add(iid)

    crafted = set()
    gathered = set()
    for r in recipes:
        for inp in r["recipeInputItems"]:
            see(inp)
        out = r["recipeOutputItems"]
        see(out["productItem"])
        crafted.add(out["productItem"]["id"])
        if out.get("comboProductItem"):
            see(out["comboProductItem"])
            crafted.add(out["comboProductItem"]["id"])
    for g in raw_gather:
        for d in g["gatherableDropsItems"]:
            see(d)
            gathered.add(d["id"])

    # ---- icon table
    icon_names = {v[1] for v in items.values()}
    icon_names |= {icon_base(r["icon"]) for r in recipes}
    icon_names |= {icon_base(g["icon"]) for g in raw_gather}
    icons = sorted(icon_names)
    icon_index = {n: i for i, n in enumerate(icons)}

    # ---- recipes
    out_recipes = []
    for r in sorted(recipes, key=lambda r: r["id"]):
        race = r["qualificationRace"]
        assert race in ("light", "dark"), r["id"]
        assert r["id"][1] == ("1" if race == "light" else "2"), r["id"]
        out = r["recipeOutputItems"]
        rec = {
            "i": r["id"],
            "n": r["name"],
            "c": icon_index[icon_base(r["icon"])],
            "p": prof_index[r["mainCategory"]],
            "t": r["subTab"],
            "g": r["grade"],
            "f": 0 if race == "light" else 1,
            "gauge": r["craftGauge"],
            "in": [[i["id"], i["quantity"]] for i in r["recipeInputItems"]],
            "out": [out["productItem"]["id"], out["productItem"]["quantity"]],
        }
        if r.get("masteryLevel") is not None:
            rec["m"] = r["masteryLevel"]
            rec["mg"] = r["masteryGrade"]
        # `cp` without `co` is meaningless to the UI (it needs the proc product to
        # name). Two Status Effect Resist Scroll recipes carry a 10% chance with no
        # product in this pull; they are treated as non-proccing.
        if out.get("comboProbability") and out.get("comboProductItem"):
            assert out["comboProbability"] % 100 == 0
            rec["cp"] = out["comboProbability"] // 100  # 2500 -> 25 (%)
            rec["co"] = out["comboProductItem"]["id"]
        out_recipes.append(rec)

    # ---- items
    out_items = {}
    for iid in sorted(items):
        name, icon, grade = items[iid]
        kind = "craft" if iid in crafted else "gather" if iid in gathered else "unsourced"
        out_items[iid] = [name, icon_index[icon], grade, kind, 1 if iid in is_currency else 0]

    # ---- gatherables
    out_gather = []
    for g in sorted(raw_gather, key=lambda g: g["id"]):
        out_gather.append({
            "i": g["id"],
            "n": g["name"],
            "c": icon_index[icon_base(g["icon"])],
            "g": g["grade"],
            "cat": g["mainCategory"],
            "m": g["masteryLevel"],
            "d": [[d["id"], d["count"], 1 if d["isBonus"] else 0] for d in g["gatherableDropsItems"]],
        })

    payload = {
        "schemaVersion": 1,
        "source": SOURCE,
        "note": NOTE,
        "professions": professions,
        "icons": icons,
        "recipes": out_recipes,
        "items": out_items,
        "gatherables": out_gather,
    }
    with open(OUT, "w") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    light = sum(1 for r in out_recipes if r["f"] == 0)
    print(
        f"recipes {len(out_recipes)} (light {light}, dark {len(out_recipes) - light}; "
        f"{len(raw_recipes) - len(recipes)} combo stubs dropped of {len(raw_recipes)} raw), "
        f"items {len(out_items)}, icons {len(icons)}, gatherables {len(out_gather)}"
    )


if __name__ == "__main__":
    main()
