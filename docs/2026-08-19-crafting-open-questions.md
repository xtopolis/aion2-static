# Crafting — open questions

Only unresolved items. Anything settled has moved into
[`src/data/README.md`](../src/data/README.md) as a dataset fact.

Numbers are from the served payload (1,886 recipes, after excluding the 22
gear-change-voucher entries). Branch: `feat/crafting`.

---

## 1. Kinah costs of exactly `1`

**718 recipes carry a kinah cost. 342 of them say `1`** — almost certainly a placeholder,
not a price. The other 376 range 500,000 → 100,000,000, and the remaining 1,168 recipes
have no kinah line at all and show "TBD".

The UI currently prints `1`, which reads as "this craft is basically free".

**Decision:** show `1` as-is, or treat it as "TBD" like the missing ones?

---

## 2. Why 58% of recipes have no mastery requirement

**1,100 of 1,886 carry no `masteryLevel`.** Every one is grade 41 or 51 — but that is not
the explanation, because plenty of grade 41 recipes *do* have one (True Dragon Lord
Pauldrons is Professional Lv. 5). Something else decides it. `learnType` is `auto` on 738
and `null` on 384, which doesn't settle it either.

**To check:** open a Corroded Sovereign's or Lava Heart weapon in the client. If it shows a
proficiency line, the dump is omitting it for that class of recipe rather than those crafts
being genuinely ungated.

---

## 3. Transfer stones — 242 recipes gated by six unsourced items

Left alone deliberately (2026-08-19: *"I don't know enough to remove them"*). Recording the
shape so the decision is easy later.

| Stone | Recipes | Grade |
|---|--:|---|
| Crafting Transfer Stone: Weapon (Unique) | 82 | 41 |
| Crafting Transfer Stone: Armor (Unique) | 56 | 41 |
| Crafting Transfer Stone: Accessory (Unique) | 24 | 41 |
| Transfer Stone: Weapon (Heroic) | 80 | 51 |
| Transfer Stone: Armor (Heroic) | 14 | 51 |
| Transfer Stone: Accessory (Heroic) | 8 | 51 |

All six are unsourced, and they cover **only** grade 41/51 equipment — every weapon type,
every armour slot, and accessories. Nothing else uses them.

Notable: **160 of the 162 Unique (41) recipes carry no kinah cost at all**, while the
Heroic (51) ones cost 20M–100M. If the Unique stones are themselves bought, that price is
effectively the whole cost of those recipes.

**Decision:** price the stones if they turn up in a shop, exclude these recipes the way the
voucher ones were, or leave as-is.

---

## 4. 84 materials still have no source

After the vendor pass, 84 non-currency items remain unsourced. They show as **buy/drop**,
and look like drop/dungeon materials rather than shop stock — but nothing confirms it.

Worth checking, ordered by how many recipes depend on them:

| Item | Recipes |
|---|--:|
| Artisan's Ultimate Refining Stone | 866 |
| Wrathful Mind | 360 |
| Wrathful Will | 358 |
| Wrathful Ego | 278 |
| Wrathful Wish | 238 |

*Artisan's Ultimate Refining Stone alone gates 866 of 1,886 recipes* — by far the most
valuable single price to capture. The "Wrathful" line behind it is another ~1,800
recipe-uses across seven items.

Adding any to [`vendor-prices.json`](../src/data/vendor-prices.json) picks them up
automatically — no code change.

---

## 5. Two profession names still unverified

The dump's keys are not what the client shows. Two are confirmed wrong and corrected:
`tailoring` → **Armorsmithing**, `jewelcrafting` → **Handicrafting**. `blacksmithing` is
right as-is.

**`alchemy` and `cooking` have not been checked** and currently display as-is. Opening any
alchemy or cooking recipe in the client would settle both.

---

## 6. What the dataset simply cannot show

Not decisions, just limits worth knowing before designing anything on top:

- **No descriptions or effect text**, on recipes or items. A recipe view can only show
  identity, materials, costs and proc odds. Item **stats** live in a different dataset and
  would need joining on item id.
- **Proc odds are materials-only.** "About 4 crafts on average" costs the attempts in
  materials but says nothing about kinah per attempt — 20M a go on the upgrade ladder.
  Blocked on §1.

---

## Not built yet

- Shopping-list calculator flattening a target to base materials across recipes (the
  per-recipe tree does one recipe at a time).
- Gatherables page — `gatherables.json` is normalized and shipped in the index payload but
  nothing renders it.
- "Where do I get this" reverse lookup from an item to everything that makes or drops it.
