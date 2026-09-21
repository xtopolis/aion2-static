#!/usr/bin/env python3
"""Generate src/data/titles.json from the Global LST client pull.

Input:  RAW (below) = {list:[...], detail:[...], ...} as written by the pull recipe
        in /home/claude/aion2-data/tools/pull-recipe.md.
Output: src/data/titles.json in the schema documented in src/data/README.md
        ("Titles dataset"), consumed by src/lib/titles.ts. One record per raw
        title (faction mirrors stay separate records; the lib merges them).

Deterministic: records sorted by id, stat keys sorted, 1-space indent.
Also verifies every stat id is present in src/data/stats-glossary.json.
"""
import json
import os
import sys

RAW = '/home/claude/aion2-data/raw/titles.json'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'src', 'data', 'titles.json')
GLOSSARY = os.path.join(HERE, '..', 'src', 'data', 'stats-glossary.json')

SOURCE = 'Aion 2 Global LST client, 2026-09-21'
GENERATED = '2026-09-21'

GRADE_NAME = {11: 'Common', 21: 'Rare', 31: 'Legendary', 41: 'Unique', 51: 'Mythic', 71: 'Special'}
FACTION = {'light': 'Elyos', 'dark': 'Asmodian', 'all': 'Both'}


def stats(obj):
    """Raw stat map -> sorted {id: int}. Empty/None -> {}."""
    if not obj:
        return {}
    return {k: obj[k] for k in sorted(obj)}


def convert(d):
    equip = stats(d.get('equipStats'))
    coll = stats(d.get('collectionStats'))
    equip_cat = d.get('equipCategory') or None
    if (equip or coll) and equip_cat is None:
        raise SystemExit(f'{d["id"]} grants stats but has no equipCategory')
    return {
        'id': str(d['id']),
        'name': d['name'],
        'description': d.get('description') or '',
        'grade': int(d['grade']),
        'grade_name': GRADE_NAME[int(d['grade'])],
        'main_category': d['mainCategory'],
        'equip_category': equip_cat,
        'race': d['race'],
        'faction': FACTION[d['race']],
        'is_visible': bool(d.get('isVisible', True)),
        'order': int(d.get('order') or 0),
        'icon': d.get('icon') or None,
        'grants_stats': bool(equip or coll),
        'equip_stats': equip,
        'collection_stats': coll,
    }


def main():
    raw = json.load(open(RAW, encoding='utf-8'))
    detail = raw['detail']
    if raw.get('fail'):
        print(f'warning: raw pull reports {raw["fail"]} failures', file=sys.stderr)

    seen = set()
    titles = []
    for d in detail:
        if d.get('isDisabled'):
            continue
        if d['id'] in seen:
            raise SystemExit(f'duplicate id {d["id"]}')
        seen.add(d['id'])
        titles.append(convert(d))
    titles.sort(key=lambda t: t['id'])

    glossary = json.load(open(GLOSSARY, encoding='utf-8'))['stats']
    used = set()
    for t in titles:
        used.update(t['equip_stats'])
        used.update(t['collection_stats'])
    missing = sorted(used - set(glossary))
    if missing:
        raise SystemExit(f'stat ids missing from stats-glossary.json: {missing}')

    out = {
        'schemaVersion': 1,
        'source': SOURCE,
        'generated': GENERATED,
        'count': len(titles),
        'titles': titles,
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write('\n')
    granting = sum(1 for t in titles if t['grants_stats'])
    print(f'wrote {len(titles)} titles ({granting} grant stats, {len(used)} stat ids) -> {os.path.relpath(OUT)}')


if __name__ == '__main__':
    main()
