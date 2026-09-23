#!/usr/bin/env python3
"""Generate src/data/wings.json from the Global LST client pull.

Input:  RAW (below) = {list:[...], detail:[...], ...} as written by the pull recipe
        in /home/claude/aion2-data/tools/pull-recipe.md.
Output: src/data/wings.json, already in the shape WingFinder.astro fetches
        (served verbatim by src/pages/data/wings.json.ts):

  rows[]        one per wing NAME (Elyos/Asmodian mirrors merged; they are
                byte-identical apart from id/race), grade desc then name asc
    stats[]     {id, base, max, pct}: value at enchant +0 and at levelMax,
                percent stats already divided out of basis points, sorted by
                glossary label
    ids[]       stat ids in the same order (the filter key)
    levelMax    highest enchant level, 0 when no stat changes with enchanting
  stats[]       {id, label} for every stat in use, alphabetical by label
  statsByGrade  {all|<grade>: [ids]} alphabetical by id

Only `equipStats.enchants` feeds the table. The raw detail also carries an
`equipStats.mainStats` map on 50 of the 66 wings; it is not part of this
payload (see src/data/README.md, "wings.json").
"""
import json
import os
import re
import sys
from collections import defaultdict

RAW = '/home/claude/aion2-data/raw/wings.json'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'src', 'data', 'wings.json')
GLOSSARY = os.path.join(HERE, '..', 'src', 'data', 'stats-glossary.json')

GRADE_NAME = {11: 'Common', 21: 'Rare', 31: 'Legendary', 41: 'Unique', 51: 'Mythic', 71: 'Special'}


def slugify(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def main():
    raw = json.load(open(RAW, encoding='utf-8'))
    if raw.get('fail'):
        print(f'warning: raw pull reports {raw["fail"]} failures', file=sys.stderr)
    glossary = json.load(open(GLOSSARY, encoding='utf-8'))['stats']
    label = lambda sid: glossary[sid]['label']
    is_pct = lambda sid: bool(glossary[sid].get('isPercentBasisPoints'))
    scale = lambda sid, v: v / 100 if is_pct(sid) else v

    # name -> list of (race, grade, enchants) so mirrors can be checked
    by_name = defaultdict(list)
    for d in raw['detail']:
        if d.get('isDisabled'):
            continue
        ench = (d.get('equipStats') or {}).get('enchants') or []
        ench = sorted(ench, key=lambda e: e['level'])
        by_name[d['name']].append((d.get('race'), int(d['grade']), ench))

    used = set()
    rows = []
    for name, variants in by_name.items():
        race, grade, ench = variants[0]
        for r2, g2, e2 in variants[1:]:
            if g2 != grade or e2 != ench:
                raise SystemExit(f'faction mirrors of {name!r} differ; merge by hand')
        base = ench[0]['stats'] if ench else {}
        top = ench[-1]['stats'] if ench else {}
        changes = any(e['stats'] != base for e in ench)
        level_max = ench[-1]['level'] if (ench and changes) else 0
        ids = sorted(set(base) | set(top), key=lambda sid: (label(sid), sid))
        missing = [sid for sid in ids if sid not in glossary]
        if missing:
            raise SystemExit(f'stat ids missing from stats-glossary.json: {missing}')
        used.update(ids)
        rows.append({
            'name': name,
            'slug': slugify(name),
            'grade': grade,
            'gradeName': GRADE_NAME[grade],
            'levelMax': level_max,
            'stats': [
                {'id': sid, 'base': scale(sid, base.get(sid, 0)), 'max': scale(sid, top.get(sid, 0)), 'pct': is_pct(sid)}
                for sid in ids
            ],
            'ids': ids,
        })
    rows.sort(key=lambda r: (-r['grade'], r['name']))

    by_grade = defaultdict(set)
    for r in rows:
        by_grade['all'].update(r['ids'])
        by_grade[str(r['grade'])].update(r['ids'])
    grade_keys = ['all'] + sorted((k for k in by_grade if k != 'all'), key=int, reverse=True)

    out = {
        'rows': rows,
        'stats': sorted(({'id': sid, 'label': label(sid)} for sid in used), key=lambda s: (s['label'], s['id'])),
        'statsByGrade': {k: sorted(by_grade[k]) for k in grade_keys},
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write('\n')
    stat_rows = sum(1 for r in rows if r['stats'])
    print(f'wrote {len(rows)} wings ({stat_rows} with stats, {len(used)} stat ids) from {len(raw["detail"])} raw records -> {os.path.relpath(OUT)}')


if __name__ == '__main__':
    main()
