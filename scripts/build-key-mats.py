#!/usr/bin/env python3
"""Generate src/data/key-mats.json — item -> every source we hold.

Inputs (outside the repo):
  RAW/quests.json          Global LST client quest pull (2026-09-21):
                           {list, detail}; rewards in detail[].questRewardsItems[]
  DUNGEONS_PATH            dungeon cube tables + Ordeal rewards parsed by hand from
                           screenshots (curated; not in the client pull)

When DUNGEONS_PATH is missing, the dungeon-drop and Ordeal rows are carried over
unchanged from the committed src/data/key-mats.json (frozen), keyed by item name.

The roster below is curated by hand (what counts as a key mat, category, subtype,
community-sourced activities). Data-backed sources (dungeon drops, quest rewards,
Trade Shop stock) are joined in automatically by exact item name.
"""
import json, os, re
from collections import defaultdict

RAW = '/home/claude/aion2-data/raw'
QUESTS_PATH = os.environ.get('KEYMATS_QUESTS', f'{RAW}/quests.json')
DUNGEONS_PATH = os.environ.get('KEYMATS_DUNGEONS', '/root/aion2/data/curated/dungeons.json')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'data', 'key-mats.json')

# Quests: one record per quest per race (light/dark mirrors are separate records and
# are counted separately, as the Taiwan pull did). Level = recommendedLevel.
Q = [{'name': d['name'], 'cat': d['mainCategory'], 'race': d.get('race'), 'lvl': d.get('recommendedLevel') or 0,
      'id': int(d['id']), 'rewards': d.get('questRewardsItems') or []}
     for d in json.load(open(QUESTS_PATH))['detail']]

D = json.load(open(DUNGEONS_PATH)) if os.path.exists(DUNGEONS_PATH) else None
# Frozen dungeon / Ordeal rows from the previous build, used only when D is absent.
FROZEN = {}
if D is None:
    if not os.path.exists(OUT):
        raise SystemExit(f'{DUNGEONS_PATH} is missing and there is no previous {OUT} to freeze dungeon rows from')
    for it in json.load(open(OUT))['items']:
        FROZEN[it['name']] = [{'kind': s['kind'], 'label': s['label'], 'detail': s['detail'], 'cap': s['cap'], 'conf': s['conf']}
                              for s in it['sources'] if s['kind'] == 'dungeon' or s['label'].startswith('Ordeal')]
    print(f'NOTE: {DUNGEONS_PATH} not found; dungeon/Ordeal rows frozen from previous key-mats.json '
          f'({sum(len(v) for v in FROZEN.values())} rows on {sum(1 for v in FROZEN.values() if v)} items)')

# ---------------------------------------------------------------- roster
# (name, category, subtype, icon path or None, extra community sources)
# Community sources: (label, detail, cap). Tagged conf=community in output.
A = lambda label, detail='', cap=None: {'kind': 'activity', 'label': label, 'detail': detail, 'cap': cap, 'conf': 'community'}
S = lambda label, detail='', cap=None: {'kind': 'shop', 'label': label, 'detail': detail, 'cap': cap, 'conf': 'community'}
C = lambda label, detail='', cap=None: {'kind': 'activity', 'label': label, 'detail': detail, 'cap': cap, 'conf': 'data'}

# Shop stock read by hand from in-game screenshots (Sep 2026): (shop › tab, item, price, currency, cap)
SHUGO, NIGHT, WIND, ABYSS, EXP = 'Shugo Festival Shop', 'Nightmare Trade Shop', 'Wind Breeze Merchants (membership)', 'Abyss Trade Shop', 'Expedition Trade Shop'
SM = 'Subjugation Marks'
SHOPS = [
  (f'{EXP} › Consumables', 'Superior Manastone (Bound)', f'2,000 {SM}', '5 / week per character'),
  (f'{EXP} › Consumables', 'Superior Abyssal Manastone (Bound)', f'3,000 {SM}', '5 / week per character'),
  (f'{EXP} › Consumables', 'Superior Abyssal Soulstone (Bound)', f'6,000 {SM}', '5 / week per character'),
  (f'{EXP} › Growth', 'Clash Rune Chest (Bound)', f'700 {SM}', '20 / week per character'),
  (f'{EXP} › Growth', 'Devotion Rune Chest (Bound)', f'700 {SM}', '20 / week per character'),
  (f'{EXP} › Growth', 'Soul Codex (Bound)', f'30 {SM}', '500 / week per character'),
  (f'{EXP} › Growth', 'Soul Codex: Reset (Bound)', f'6,000 {SM}', '5 / week per character'),
  (f'{EXP} › Growth', 'Splendent Noble Crystal (Bound)', f'700 {SM}', '20 / week per character'),
  (f'{EXP} › Growth', 'Superior Training Arcana (Bound)', f'500 {SM}', '20 / week per character'),
  (f'{EXP} › Growth', 'Sync Stone Fragment (Unique) (Bound)', f'80 {SM}', '120 / week per character'),
  (f'{EXP} › Growth', 'Sync Stone Fragment (Heroic) (Bound)', f'400 {SM}', '60 / week per character'),
  (f'{EXP} › Growth', 'Amplify Stone Fragment (Unique) (Bound)', f'150 {SM}', '80 / week per character'),
  (f'{EXP} › Growth', 'Amplify Stone Fragment (Heroic) (Bound)', f'400 {SM}', '80 / week per character'),
  (f'{ABYSS} › Consumables', 'Rare Theostone Chest (Bound)', '35,000 AP', None),
  (f'{ABYSS} › Consumables', 'Lesser Abyssal Manastone (Bound)', '1,000 AP', None),
  (f'{ABYSS} › Consumables', 'Lesser Abyssal Soulstone (Bound)', '2,000 AP', None),
  (f'{ABYSS} › Growth', 'Fierce Battle Amulet Enhance Scroll', '50,000 AP (step 1/3)', '4 per character'),
  (f'{ABYSS} › Growth', 'Daevanion Crystal: Azphel (Bound)', '7,000 AP (step 1/4)', '10 per character'),
  (f'{ABYSS} › Growth', 'Devotion Rune Chest (Bound)', '5,000 AP', None),
  (f'{ABYSS} › Growth', 'Stigma Shard (Bound)', '25,000 AP', None),
  (f'{SHUGO} › Consumables', 'Soul Codex (Bound)', '200 Shugo Coin', '3 / week per character'),
  (f'{SHUGO} › Consumables', 'Daevanion Crystal (Bound)', '50 Shugo Coin (step 1/4)', '10 per character'),
  (f'{SHUGO} › Consumables', 'Soul Crystal (Bound)', '20 Shugo Coin', '10 / week per character'),
  (f'{SHUGO} › Skins', 'Skin sets (shops)', 'Lightpath Trace set, 530–1,100 Shugo Coin a piece; Twilight Loop earrings / necklace 530 / 680', '1 per character'),
  (f'{SHUGO} › Skins', 'Skin sets (shops)', 'Skilled Expert set, 2,650–5,400 Shugo Coin a piece; Starry Starry Night earrings / necklace 2,650 / 3,400', '1 per character'),
  (f'{NIGHT} › Consumables', 'Amplify Stone Fragment (Unique) (Bound)', '500 Phantasmal Fragments', None),
  (f'{NIGHT} › Consumables', 'Amplify Stone Fragment (Heroic) (Bound)', '2,000 Phantasmal Fragments', None),
  (f'{NIGHT} › Consumables', 'Soul Codex (Bound)', '400 Phantasmal Fragments', None),
  (f'{NIGHT} › Consumables', 'Soul Codex: Reset (Bound)', '8,000 Phantasmal Fragments', '3 / week per character'),
  (f'{NIGHT} › Consumables', 'Soul Crystal (Bound)', '50 Phantasmal Fragments', '10 / week per character'),
  (f'{NIGHT} › Growth', 'Clash Rune Chest (Bound)', '500 Phantasmal Fragments', None),
  (f'{NIGHT} › Growth', 'Daevanion Crystal: Ariel (Bound)', '800 Phantasmal Fragments (step 1/4)', '10 per character'),
  (f'{NIGHT} › Skins', 'Skin sets (shops)', 'Awakened set, 5,300–10,800 Phantasmal Fragments a piece', '1 per character'),
  (f'{NIGHT} › Statue', 'Statue', 'Gatekeeper Pinopi, Furious Feruk, Fafnir\'s Poison Blood, Wraith Giselle: 5,000 Phantasmal Fragments each, needs that Nightmare boss at level 10', '1 per character'),
  (f'{NIGHT} › Statue', 'Statue', 'Fortress Guardian Notun, Gerod: 8,000 Phantasmal Fragments each, needs that Nightmare boss at level 10', '1 per character'),
  (f'{NIGHT} › Statue', 'Statue', 'Colossus: Zikel\'s Apparition: 14,000 Phantasmal Fragments, needs Nightmare Zikel at level 1', '1 per character'),
  (f'{WIND} › Special', 'Odyle Energy', '100,000 kinah', '16 / week per server + 4 / week per character'),
  (f'{WIND} › Special', 'Soul Crystal (Bound)', '1,000 kinah', '1,000 / week per server'),
  (f'{WIND} › Special', 'Superior Training Arcana (Bound)', '10,000 kinah, limited-time listing', '200 / week per server'),
  (f'{WIND} › Special', 'Noble Crystal (Bound)', '5,000 kinah, limited-time listing', '200 / week per server'),
  (f'{WIND} › Special', 'Splendent Noble Crystal (Bound)', '10,000 kinah, limited-time listing', '200 / week per server'),
]

ROSTER = [
  # --- Enhancement
  ('Enhance Stone', 'Enhancement', None, '/icons/currency/enhance-stone.webp',
     [A('Daily Dungeon', 'enhance-stone variant', '14 / week'), A('Ascension Trial', 'character-bound', '3 / week'),
      A('Supply requests'), A('Command scrolls', 'per server', '12 / week'), A('Abyss commands', 'per server', '20 / week')]),
  ('Sync Stone Fragment', 'Enhancement', 'Sync', '/icons/materials/sync-stone-fragment.webp', [],
     {'Unique': 'Sync Stone Fragment (Unique) (Bound)', 'Heroic': 'Sync Stone Fragment (Heroic) (Bound)', 'Whole stone (Unique)': 'Sync Stone (Unique) (Bound)'}),
  ('Amplify Stone Fragment', 'Enhancement', 'Amplify', '/icons/materials/amplify-stone-fragment.webp', [],
     {'Unique': 'Amplify Stone Fragment (Unique) (Bound)', 'Heroic': 'Amplify Stone Fragment (Heroic) (Bound)'}),
  ("Philosopher's Stone", 'Enhancement', "Philosopher's Stone", '/icons/materials/philosophers-stone.webp', [],
     {'Power': "Philosopher's Stone: Power (Bound)", 'Revelation': "Philosopher's Stone: Revelation (Bound)"}),
  ('Soul Codex (Bound)', 'Enhancement', 'Soul bind', '/icons/materials/soul-codex.webp', []),
  ('Soul Codex: Reset (Bound)', 'Enhancement', 'Soul bind', '/icons/materials/soul-codex-reset.webp', []),
  ('Noble Belt Enhance Scroll', 'Enhancement', 'Belt / Amulet', '/icons/equip/noble-belt.webp',
     [A('Strongholds', 'one-time per character, both faction maps via rifts')]),
  ('Fierce Battle Amulet Enhance Scroll', 'Enhancement', 'Belt / Amulet', '/icons/equip/fierce-battle-amulet.webp',
     [A('Reshanta Monolith', 'feathers → monolith rewards')]),
  # --- Transfer / Potential
  ('Transfer Stone Fragment', 'Transfer', 'Transfer', '/icons/materials/sync-stone-fragment.webp',
     [A('Break down Unique gear', 'Unique: 1–5 fragments by item level; 20 weapon / 15 armor / 10 accessory per stone'),
      A('Break down Heroic gear', 'Heroic: always 5 fragments')]),
  ('Potential Stone', 'Transfer', 'Potential', '/icons/materials/philosophers-stone.webp',
     [A('Break down Unique gear', 'type-locked: weapon → weapon stones, and so on')]),
  # --- Stigma
  ('Unstable Stigma Shard (Bound)', 'Stigma', None, '/icons/currency/stigma-shard.webp',
     [C('Substance Morph', '12 + 50,000 kinah → 1 Stigma Shard at 25%, or 48 + 200,000 kinah at 100%')]),
  ('Stigma Shard (Bound)', 'Stigma', None, '/icons/currency/stigma-shard.webp',
     [C('Substance Morph', '12 Unstable Stigma Shards + 50,000 kinah at 25%, or 48 + 200,000 kinah at 100%'),
      A('Abyss commands', 'reroll toward shards', '20 / week'), A('Ascension Trial', 'character-bound', '3 / week')]),
  ('Superior Stigma Shard', 'Stigma', None, '/icons/currency/stigma-shard.webp',
     [A('Stigma to 20', 'one per stigma raised to 20; levels 21–25. Post level-50 patch, not in Global yet')]),
  # --- Daevanion
  ('Daevanion Crystal (Bound)', 'Daevanion', 'Boards 1–4', '/icons/currency/daevanion-crystal.webp',
     [A('Sealed dungeons', 'one-time per character, both faction maps via rifts'), A('Map exploration', '122 per faction'),
      A('Regional missions', '85 per faction')]),
  ('Daevanion Crystal: Ariel (Bound)', 'Daevanion', 'Ariel (PvE)', '/icons/currency/daevanion-crystal.webp',
     [A('Ascension Trial', 'as Ariel fragments')]),
  ("Fragment: Yustiel's Trace (Bound)", 'Daevanion', 'Yustiel', '/icons/currency/daevanion-crystal.webp', []),
  ("Fragment: Marchutan's Trace (Bound)", 'Daevanion', 'Marchutan', '/icons/currency/daevanion-crystal.webp', []),
  ('Daevanion Crystal: Azphel (Bound)', 'Daevanion', 'Azphel (PvP)', '/icons/currency/daevanion-crystal.webp', []),
  ('Azphel Fragment', 'Daevanion', 'Azphel (PvP)', '/icons/currency/daevanion-crystal.webp',
     [A('Battlefield', '30 per win; 90 a week ≈ 1 crystal. Crystals are tradeable', '3 wins / week')]),
  ('Phantasmal Fragment', 'Daevanion', 'Nightmare currency', '/icons/currency/phantasmal-fragment.webp',
     [A('Nightmare', 'first-clears 540 → 900', '+2 tickets / day, cap 14')]),
  # --- Arcana
  ('Arcana card', 'Arcana', None, '/icons/equip/arcana-chalice.webp',
     [A('Transcendence', 'the only source. 40 odyle a cube; push to +3 or higher before looting')]),
  ('Mysterious Crystal', 'Arcana', 'Transmute', '/icons/arcana/chalice-of-punishment.webp',
     [A('Extract arcana cards', 'chance-based: a gold Chalice of Vigor showed 20%; other grades unread'), A('Tower of Trials', 'Season → Challenges')]),
  ('Noble Crystal (Bound)', 'Arcana', 'Transmute', '/icons/arcana/chalice-of-punishment.webp',
     [C('Substance Morph', '10 Shard: Noble Crystal, or 3 Mysterious Crystals, or 1 Splendent Noble Crystal → 1')]),
  ('Splendent Noble Crystal (Bound)', 'Arcana', 'Transmute', '/icons/arcana/chalice-of-punishment.webp',
     [C('Substance Morph', '10 Shard: Splendent Noble Crystal, or 4 Noble Crystals → 1')]),
  ('Superior Training Arcana (Bound)', 'Arcana', 'Leveling', '/icons/arcana/parchment-of-punishment.webp', []),
  # --- Manastones / Theostones / Runes
  ('Manastone', 'Stones', 'Manastone', '/icons/stones/superior-manastone.webp',
     [A('Ascension Trial', 'chest', '3 / week')], {'Superior': 'Superior Manastone (Bound)'}),
  ('Abyssal Manastone', 'Stones', 'Manastone', '/icons/stones/superior-abyssal-manastone.webp',
     [A('Craft', 'Lesser → higher tiers; sells into whale demand')], {'Lesser': 'Lesser Abyssal Manastone (Bound)', 'Superior': 'Superior Abyssal Manastone (Bound)'}),
  ('Abyssal Soulstone', 'Stones', 'Soulstone', '/icons/stones/superior-abyssal-soulstone.webp', [],
     {'Lesser': 'Lesser Abyssal Soulstone (Bound)', 'Superior': 'Superior Abyssal Soulstone (Bound)'}),
  ('Rare Theostone Chest (Bound)', 'Stones', 'Theostone', '/icons/materials/rare-theostone-chest.webp',
     [A('Transcendence', 'loot from rank 4–5 minimum; blues at rank 6')]),
  ('Clash Rune Chest (Bound)', 'Stones', 'Rune', '/icons/equip/clash-rune.webp', []),
  ('Devotion Rune Chest (Bound)', 'Stones', 'Rune', '/icons/equip/devotion-rune.webp', []),
  # --- Pantheon
  ('Artwork Scrap', 'Pantheon', 'Artwork', '/icons/pantheon/artwork.webp', []),   # expanded per dungeon below
  ('Artwork', 'Pantheon', 'Artwork', '/icons/pantheon/artwork.webp', []),         # named pieces from quests
  ('Statue', 'Pantheon', 'Statue', '/icons/pantheon/statue.webp', []),
  # --- Wings
  ('Wing Featherdown', 'Wings', None, '/icons/wings/glittering-galaxy-wings.webp', []),  # expanded per dungeon below
  # --- Pets
  ('Soul Crystal (Bound)', 'Pets', None, '/icons/materials/soul-crystal.webp',
     [A('Daily Dungeon', 'pet-crystal variant, ~5 min solo', '14 / week'), A('Duty quests', 'reroll for crystals', '5 / day')]),
  ('Pet crystal (per family)', 'Pets', 'Genus Insight', '/icons/materials/soul-crystal.webp',
     [A('Kill beyond max pet level', 'levels Genus Insight to 10 and rolls its stats')]),
  # --- Skins
  ('Skin Chest (10 times)', 'Skins', None, None, [],
     {'Weapon': 'Skin Chest: Weapon (10 times) (Bound)', 'Armor': 'Skin Chest: Armor (10 times) (Bound)', 'Accessory': 'Skin Chest: Accessory (10 times) (Bound)'}),
  ('Skin sets (shops)', 'Skins', None, None, []),
  ('Skin (breakdown)', 'Skins', None, None,
     [A('Break down any gear', '10% converts to a skin; closet is account-wide'),
      A('Break down Abyss PvP gear', '100% converts and refunds 80% of the AP')]),
  # --- Currencies
  ('Abyss Points', 'Currency', None, '/icons/currency/abyss-points.webp',
     [A('Portals / Corridors', 'one entry per Artifact held, per siege', '~50k each'), A('Supply requests', 'exempt from the weekly cap'),
      A('Battlefield', '', '3 wins / week'), A('Arena', '', '30 wins / week each'), A('Spacetime Rift', 'double under cap'),
      A('Abyss kills', 'players and mobs; cap accumulates, never resets')]),
  ('Abyssal Token', 'Currency', None, '/icons/currency/centuryroot-token.webp',
     [A('Abyss deliveries (Alt+J)', 'weekly + emergencies')]),
  ('Subjugation Mark', 'Currency', None, '/icons/currency/wisdom-stone.webp', []),
  ('Shugo Coin', 'Currency', None, '/icons/currency/shugo-coin.webp',
     [A('Shugo Festival', 'hourly minigames, key-limited', '+2 keys / day, cap 14')]),
  ('Oath Coin', 'Currency', None, '/icons/currency/oath-coin.webp', [A('Seasonal track', 'fed by all content')]),
  ('Silentium', 'Currency', None, '/icons/currency/kinah.webp', [A('Ascension Trial', 'sells for bound kinah', '3 / week')]),
  ('Odyle Energy', 'Currency', None, '/icons/currency/odyle-energy.webp',
     [A('Regen', '15 per 3 h, cap 840'), A('Craft (Substance Morph)', 'two recipes', 'up to 40 / week'),
      A('Events, achievements, season missions', 'banked as items, exempt from the cap')]),
]

# ---------------------------------------------------------------- data joins
def dungeon_sources(name):
    if D is None: return []
    out = defaultdict(lambda: {'bosses': set(), 'pct': None, 'pmin': None, 'diffs': set()})
    for key, dg in D['dungeons'].items():
        tier, dname, diff = key.split('|')
        for boss, pools in (dg.get('bosses') or {}).items():
            for pid, p in pools.items():
                for it in p.get('items', []):
                    if it['name'] == name or (name.startswith('Artwork Scrap:') and it['name'].endswith('...') and name.startswith(it['name'][:-3].rstrip())):
                        e = out[(tier, dname)]
                        e['bosses'].add(boss); e['diffs'].add(diff or 'Normal')
                        if it.get('pct') is not None:
                            e['pct'] = it['pct'] if e['pct'] is None else max(e['pct'], it['pct'])
                            e['pmin'] = it['pct'] if e['pmin'] is None else min(e['pmin'], it['pct'])
                        e.setdefault('qty', it.get('qty'))
    # merge Conquest + Exploration of the same dungeon
    merged = {}
    for (tier, dname), e in out.items():
        m = merged.setdefault(dname, {'tiers': set(), 'bosses': set(), 'pct': None, 'pmin': None, 'qtys': set()})
        m['tiers'].add(tier); m['bosses'] |= e['bosses']
        if e['pct'] is not None: m['pct'] = e['pct'] if m['pct'] is None else max(m['pct'], e['pct'])
        if e['pmin'] is not None: m['pmin'] = e['pmin'] if m['pmin'] is None else min(m['pmin'], e['pmin'])
        if e.get('qty'): m['qtys'].add(str(e['qty']))
    fmt = lambda p: (f"{p:.0f}%" if p >= 1 else f"{p:.2f}%") if p else None
    def qty_range(qs):
        nums = []
        for q in qs:
            for part in str(q).replace(',', '').split('-'):
                try: nums.append(float(part))
                except ValueError: pass
        if not nums: return ''
        lo, hi = min(nums), max(nums)
        f = lambda v: f"{int(v):,}" if v == int(v) else str(v)
        return f" ×{f(lo)}" if lo == hi else f" ×{f(lo)}–{f(hi)}"
    def prange(lo, hi):
        if lo is None and hi is None: return None
        if lo is None or hi is None or abs(lo - hi) < 0.01: return fmt(hi if hi is not None else lo)
        return f"{fmt(lo)}–{fmt(hi)} by boss"
    all_names = {k.split('|')[1] for k in D['dungeons']}
    if merged and set(merged) == all_names:
        his = [m['pct'] for m in merged.values() if m['pct'] is not None]
        los = [m['pmin'] for m in merged.values() if m['pmin'] is not None]
        cap = prange(min(los) if los else None, max(his) if his else None)
        qty = qty_range({q for m in merged.values() for q in m['qtys']})
        return [{'kind': 'dungeon', 'label': 'All 12 dungeons', 'detail': f"Conquest and Exploration, every boss cube{qty}", 'cap': cap, 'conf': 'data'}]
    rows = []
    for dname, m in sorted(merged.items()):
        tiers = ' + '.join(sorted(m['tiers']))
        detail = ', '.join(sorted(m['bosses'])) + f" ({tiers})"
        detail += qty_range(m['qtys'])
        rows.append({'kind': 'dungeon', 'label': dname, 'detail': detail, 'cap': prange(m['pmin'], m['pct']), 'conf': 'data'})
    return rows

def quest_sources(name):
    by = defaultdict(lambda: {'n': 0, 'ex': [], 'races': set()})
    for x in sorted(Q, key=lambda x: (x['lvl'], x['id'])):
        if any(r['name'] == name for r in x['rewards']):
            e = by[x['cat']]; e['n'] += 1; e['races'].add(x['race'])
            ex = f"{x['name']} (Lv {x['lvl']})"   # light/dark mirrors share a name: one example, still counted twice
            if len(e['ex']) < 3 and ex not in e['ex'] and x['cat'] not in ('dutyscroll', 'dutymission'): e['ex'].append(ex)
    # one-time categories first, repeatables last (fixed order, so output is stable across pulls)
    lab = {'hero': 'Story quests', 'district': 'District quests', 'exploration': 'Sealed dungeons', 'ascension': 'Ascension quests',
           'gathercraftmastery': 'Crafting mastery quests', 'daevagauge': 'Daeva gauge quests',
           'dutymission': 'Duty quests', 'dutyscroll': 'Command scrolls'}
    order = {c: i for i, c in enumerate(lab)}
    rows = []
    for cat in sorted(by, key=lambda c: (order.get(c, len(order)), c)):
        e = by[cat]
        detail = '; '.join(e['ex']) if e['ex'] else ''
        rows.append({'kind': 'quest', 'label': lab.get(cat, cat), 'detail': detail, 'cap': f"{e['n']} quests", 'conf': 'data'})
    return rows

def shop_sources(name):
    return [{'kind': 'shop', 'label': lab, 'detail': price, 'cap': cap, 'conf': 'data'} for lab, it, price, cap in SHOPS if it == name]

def ordeal_sources(name):
    rows = []
    for rec in (D or {}).get('ordeal', []):
        for e in (rec.get('ordeal') or {}).get('rewardIcons', []):
            if e.get('item') == name:
                rows.append({'kind': 'activity', 'label': 'Ordeal', 'detail': f"weekly ladder, ×{e.get('qty')}", 'cap': '7 kills / week', 'conf': 'data'})
    return rows

def frozen_sources(item, kind, vlabel=None):
    """Rows carried over from the previous build (only when DUNGEONS_PATH is absent)."""
    rows = [r for r in FROZEN.get(item.replace(' (Bound)', ''), [])
            if (r['kind'] == 'dungeon') == (kind == 'dungeon')]
    if vlabel is not None: rows = [r for r in rows if r['detail'].startswith(f'{vlabel}: ')]
    return [dict(r) for r in rows]

items = []
def add(name, cat, sub, icon, extra, variants=None):
    srcs = []
    for vlabel, vname in (variants.items() if variants else [(None, name)]):
        def pre(rows):
            out = []
            for r in rows:
                r = dict(r)
                if vlabel: r['detail'] = f"{vlabel}: {r['detail']}" if r['detail'] else vlabel
                out.append(r)
            return out
        srcs += pre(dungeon_sources(vname)) if D else frozen_sources(name, 'dungeon', vlabel)
        srcs += pre(quest_sources(vname))
        srcs += pre(shop_sources(vname))
        srcs += pre(ordeal_sources(vname)) if D else frozen_sources(name, 'ordeal', vlabel)
    seen=set(); dedup=[]
    for r in srcs + extra:
        k=(r['kind'], r['label'], r['detail'], r['cap'])
        if k in seen: continue
        seen.add(k); dedup.append(r)
    items.append({'name': name, 'cat': cat, 'sub': sub, 'icon': icon, 'sources': dedup})

for entry in ROSTER:
    name, cat, sub, icon, extra = entry[:5]
    variants = entry[5] if len(entry) > 5 else None
    if name in ('Artwork Scrap', 'Wing Featherdown') and D is None:
        items.append({'name': name, 'cat': cat, 'sub': 'one wing per dungeon' if name == 'Wing Featherdown' else sub, 'icon': icon,
                      'sources': frozen_sources(name, 'dungeon')})
    elif name == 'Artwork Scrap':
        srcs = []
        for key in sorted({k.split('|')[1] for k in D['dungeons']}):
            for r in dungeon_sources(f"Artwork Scrap: {key} (Bound)"):
                r = dict(r); r['detail'] = f"Artwork Scrap: {key}. " + r['detail']; srcs.append(r)
        items.append({'name': 'Artwork Scrap', 'cat': cat, 'sub': sub, 'icon': icon, 'sources': srcs})
    elif name == 'Artwork':
        names = sorted({r['name'] for x in Q for r in x['rewards'] if r['name'].startswith('Artwork:')})
        srcs = []
        for n in names:
            for r in quest_sources(n):
                r = dict(r); r['detail'] = f"{n.replace('Artwork: ', '').replace(' (Bound)', '')}: " + r['detail']; srcs.append(r)
        items.append({'name': 'Artwork (named pieces)', 'cat': cat, 'sub': sub, 'icon': icon, 'sources': srcs})
    elif name == 'Statue':
        add(name, cat, sub, icon, extra + [{'kind': 'quest', 'label': 'District quests', 'detail': '', 'cap': f"{sum(1 for x in Q for r in x['rewards'] if r['name'].startswith('Statue:'))} quests", 'conf': 'data'}])
    elif name == 'Wing Featherdown':
        names = set()
        for key, dg in D['dungeons'].items():
            for boss, pools in (dg.get('bosses') or {}).items():
                for p in pools.values():
                    for it in p.get('items', []):
                        if 'Featherdown' in it['name']: names.add(it['name'])
        srcs = []
        for n in sorted(names):
            wing = n.replace(' Wing Featherdown (Bound)', '').replace(' Wings Featherdown (Bound)', '')
            for r in dungeon_sources(n):
                r = dict(r); r['detail'] = f"{wing}: " + r['detail']; srcs.append(r)
        items.append({'name': 'Wing Featherdown', 'cat': cat, 'sub': 'one wing per dungeon', 'icon': icon, 'sources': srcs})
    else:
        add(name, cat, sub, icon, extra, variants)

REPEAT_QUESTS = ('Command scrolls', 'Duty quests')
for i in items:
    i['name'] = i['name'].replace(' (Bound)', '')
    for src in i['sources']:
        if src['kind'] == 'dungeon': src['group'] = 'dungeon'
        elif src['kind'] == 'quest' and src['label'] not in REPEAT_QUESTS: src['group'] = 'onetime'
        else: src['group'] = 'other'
items.sort(key=lambda i: i['name'].lower())
json.dump({'generated': 'scripts/build-key-mats.py', 'items': items}, open(OUT, 'w'), ensure_ascii=False, indent=1)
print(len(items), 'items;', sum(len(i['sources']) for i in items), 'sources;', sum(1 for i in items if not i['sources']), 'with no source')
for i in items:
    if not i['sources']: print('  NO SOURCE:', i['name'])
