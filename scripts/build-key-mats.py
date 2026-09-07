#!/usr/bin/env python3
"""Generate src/data/key-mats.json — item -> every source we hold.

Inputs (outside the repo):
  /root/aion2/data/raw/aion2_ql_quests_en.json   QuestLog quest rewards (1,416 quests)
  /root/aion2/data/curated/dungeons.json         dungeon cube tables parsed from screenshots

The roster below is curated by hand (what counts as a key mat, category, subtype,
community-sourced activities). Data-backed sources (dungeon drops, quest rewards,
Trade Shop stock) are joined in automatically by exact item name.
"""
import json, re
from collections import defaultdict

Q = json.load(open('/root/aion2/data/raw/aion2_ql_quests_en.json'))['quests']
D = json.load(open('/root/aion2/data/curated/dungeons.json'))

# ---------------------------------------------------------------- roster
# (name, category, subtype, icon path or None, extra community sources)
# Community sources: (label, detail, cap). Tagged conf=community in output.
A = lambda label, detail='', cap=None: {'kind': 'activity', 'label': label, 'detail': detail, 'cap': cap, 'conf': 'community'}
S = lambda label, detail='', cap=None: {'kind': 'shop', 'label': label, 'detail': detail, 'cap': cap, 'conf': 'community'}

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
     [A('Reshanta Monolith', 'feathers → monolith rewards'), S('Abyss Trade Shop', '50,000 AP', '4 / character')]),
  # --- Transfer / Potential
  ('Transfer Stone Fragment', 'Transfer', 'Transfer', '/icons/materials/sync-stone-fragment.webp',
     [A('Break down Unique gear', 'Unique: 1–5 fragments by item level; 20 weapon / 15 armor / 10 accessory per stone'),
      A('Break down Heroic gear', 'Heroic: always 5 fragments')]),
  ('Potential Stone', 'Transfer', 'Potential', '/icons/materials/philosophers-stone.webp',
     [A('Break down Unique gear', 'type-locked: weapon → weapon stones, and so on')]),
  # --- Stigma
  ('Unstable Stigma Shard (Bound)', 'Stigma', None, '/icons/currency/stigma-shard.webp',
     [A('Combine', 'combines into Stigma Shards; ratio unknown')]),
  ('Stigma Shard (Bound)', 'Stigma', None, '/icons/currency/stigma-shard.webp',
     [S('Abyss Point shop'), A('Abyss commands', 'reroll toward shards', '20 / week'),
      A('Ascension Trial', 'character-bound', '3 / week'), S('Abyssal Token shop')]),
  ('Superior Stigma Shard', 'Stigma', None, '/icons/currency/stigma-shard.webp',
     [A('Stigma to 20', 'one per stigma raised to 20; levels 21–25. Post level-50 patch, not in Global yet')]),
  # --- Daevanion
  ('Daevanion Crystal (Bound)', 'Daevanion', 'Boards 1–4', '/icons/currency/daevanion-crystal.webp',
     [A('Sealed dungeons', 'one-time per character, both faction maps via rifts'), A('Map exploration', '122 per faction'),
      A('Regional missions', '85 per faction'), S('Shugo Festival shop'), S('Nightmare shop')]),
  ('Daevanion Crystal: Ariel (Bound)', 'Daevanion', 'Ariel (PvE)', '/icons/currency/daevanion-crystal.webp',
     [S('Nightmare shop', 'Phantasmal Fragments'), A('Ascension Trial', 'as Ariel fragments')]),
  ("Fragment: Yustiel's Trace (Bound)", 'Daevanion', 'Yustiel', '/icons/currency/daevanion-crystal.webp', []),
  ("Fragment: Marchutan's Trace (Bound)", 'Daevanion', 'Marchutan', '/icons/currency/daevanion-crystal.webp', []),
  ('Azphel Fragment', 'Daevanion', 'Azphel (PvP)', '/icons/currency/daevanion-crystal.webp',
     [A('Battlefield', '30 per win; 90 a week ≈ 1 crystal. Crystals are tradeable', '3 wins / week')]),
  ('Phantasmal Fragment', 'Daevanion', 'Nightmare currency', '/icons/currency/phantasmal-fragment.webp',
     [A('Nightmare', 'first-clears 540 → 900', '+2 tickets / day, cap 14')]),
  # --- Arcana
  ('Arcana card', 'Arcana', None, '/icons/equip/arcana-chalice.webp',
     [A('Transcendence', 'the only source. 40 odyle a cube; push to +3 or higher before looting')]),
  ('Mysterious Crystal', 'Arcana', 'Transmute', '/icons/arcana/chalice-of-punishment.webp',
     [A('Extract junk cards'), A('Tower of Trials', 'Season → Challenges'), S('Season Shop › Growth')]),
  ('Splendent Noble Crystal (Bound)', 'Arcana', 'Transmute', '/icons/arcana/chalice-of-punishment.webp', []),
  ('Shard: Noble Crystal', 'Arcana', 'Transmute', '/icons/arcana/chalice-of-punishment.webp', []),
  ('Superior Training Arcana (Bound)', 'Arcana', 'Leveling', '/icons/arcana/parchment-of-punishment.webp', []),
  # --- Manastones / Theostones / Runes
  ('Manastone', 'Stones', 'Manastone', '/icons/stones/superior-manastone.webp',
     [A('Ascension Trial', 'chest', '3 / week')], {'Superior': 'Superior Manastone (Bound)'}),
  ('Abyssal Manastone', 'Stones', 'Manastone', '/icons/stones/superior-abyssal-manastone.webp',
     [S('Abyss Point shop', 'craft to higher tier, sells into whale demand')]),
  ('Superior Abyssal Soulstone (Bound)', 'Stones', 'Soulstone', '/icons/stones/superior-abyssal-soulstone.webp', []),
  ('Rare Theostone Chest (Bound)', 'Stones', 'Theostone', '/icons/materials/rare-theostone-chest.webp',
     [A('Transcendence', 'loot from rank 4–5 minimum; blues at rank 6')]),
  ('Clash Rune Chest (Bound)', 'Stones', 'Rune', '/icons/equip/clash-rune.webp', []),
  ('Devotion Rune Chest (Bound)', 'Stones', 'Rune', '/icons/equip/devotion-rune.webp', []),
  # --- Pantheon
  ('Artwork Scrap', 'Pantheon', 'Artwork', '/icons/pantheon/artwork.webp', []),   # expanded per dungeon below
  ('Artwork', 'Pantheon', 'Artwork', '/icons/pantheon/artwork.webp', []),         # named pieces from quests
  ('Statue', 'Pantheon', 'Statue', '/icons/pantheon/statue.webp',
     [A('Nightmare', 'season final boss unlocks a purchasable statue')]),
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
  ('Skin (breakdown)', 'Skins', None, None,
     [A('Break down any gear', '10% converts to a skin; closet is account-wide'),
      A('Break down Abyss PvP gear', '100% converts and refunds 80% of the AP')]),
  # --- Currencies
  ('Abyss Points', 'Currency', None, '/icons/currency/abyss-points.webp',
     [A('Portals / Corridors', 'one entry per Artifact held, per siege', '~50k each'), A('Supply requests', 'exempt from the weekly cap'),
      A('Battlefield', '', '3 wins / week'), A('Arena', '', '30 wins / week each'), A('Spacetime Rift', 'double under cap'),
      A('Abyss kills', 'players and mobs; cap accumulates, never resets')]),
  ('Abyssal Token', 'Currency', None, '/icons/currency/centuryroot-token.webp',
     [A('Abyss deliveries (Alt+J)', 'weekly + emergencies'), A('Ascension Trial', '? turn-ins')]),
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
    for x in Q:
        for r in x['rewards']:
            if r['name'] == name:
                e = by[x['cat']]; e['n'] += 1; e['races'].add(x['race'])
                if len(e['ex']) < 3 and x['cat'] not in ('dutyscroll', 'dutymission'): e['ex'].append(f"{x['name']} (Lv {x['lvl']})")
    lab = {'dutyscroll': 'Command scrolls', 'dutymission': 'Duty quests', 'district': 'District quests', 'hero': 'Story quests',
           'exploration': 'Sealed dungeons', 'ascension': 'Ascension quests'}
    rows = []
    for cat, e in by.items():
        detail = '; '.join(e['ex']) if e['ex'] else ''
        rows.append({'kind': 'quest', 'label': lab.get(cat, cat), 'detail': detail, 'cap': f"{e['n']} quests", 'conf': 'data'})
    return rows

def shop_sources(name):
    rows = []
    for rec in D.get('tradeShop', []):
        sh = rec.get('shop') or {}
        tab = sh.get('activeTab') or 'Trade Shop'; sub = sh.get('activeSubTab') or ''
        for e in sh.get('entries', []):
            if e.get('item') == name:
                stock = (e.get('stock') or '').replace('Per Character Weekly 0/', '').replace('Per Character ', '')
                rows.append({'kind': 'shop', 'label': f"{tab} (Expedition) › {sub}", 'detail': (f"{e.get('price'):,} {e.get('currency') or 'Subjugation Mark (currency label unread)'}" if e.get('price') else 'price unread'),
                             'cap': f"{stock} / week" if stock else None, 'conf': 'data'})
    for rec in D.get('ordeal', []):
        for e in (rec.get('ordeal') or {}).get('rewardIcons', []):
            if e.get('item') == name:
                rows.append({'kind': 'activity', 'label': 'Ordeal', 'detail': f"weekly ladder, ×{e.get('qty')}", 'cap': '7 kills / week', 'conf': 'data'})
    return rows

items = []
def joined(name):
    return dungeon_sources(name) + quest_sources(name) + shop_sources(name)
def add(name, cat, sub, icon, extra, variants=None):
    srcs = []
    if variants:
        for vlabel, vname in variants.items():
            for r in joined(vname):
                r = dict(r); r['detail'] = f"{vlabel}: {r['detail']}" if r['detail'] else vlabel; srcs.append(r)
    else:
        srcs = joined(name)
    items.append({'name': name, 'cat': cat, 'sub': sub, 'icon': icon, 'sources': srcs + extra})

for entry in ROSTER:
    name, cat, sub, icon, extra = entry[:5]
    variants = entry[5] if len(entry) > 5 else None
    if name == 'Artwork Scrap':
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
json.dump({'generated': 'scripts/build-key-mats.py', 'items': items}, open('src/data/key-mats.json', 'w'), ensure_ascii=False, indent=1)
print(len(items), 'items;', sum(len(i['sources']) for i in items), 'sources;', sum(1 for i in items if not i['sources']), 'with no source')
for i in items:
    if not i['sources']: print('  NO SOURCE:', i['name'])
