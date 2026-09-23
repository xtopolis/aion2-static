import { describe, expect, it } from "vitest";
import data from "../src/data/skill-levels.json";

/**
 * Invariants for src/data/skill-levels.json as built from the Global LST pull
 * (2026-09-21), plus the figures we have actually seen in game. The graph maths
 * behind the Daevanion point costs is verified separately by
 * scripts/test_daevanion_math.py, which needs the raw pull; this suite runs
 * anywhere and guards the shape of what ships.
 */

const d = data as any;
const CLASSES = Object.keys(d.byClass);
const BOARDS = ["Nezekan", "Zikel", "Vaizel", "Triniel"];
// every grade of equipment or arcana card that exists in the Global item DB;
// there is no Heroic (71) or Mythic (51) gear in it
const GRADES = ["Common", "Rare", "Legend", "Unique"];
const near = (a: number, b: number, eps = 5e-6) => Math.abs(a - b) < eps;

describe("dataset shape", () => {
  it("carries the eight Global classes, alphabetical by display name", () => {
    // Brawler (`fighter`) is excluded on purpose: its boards in the pull are the
    // stale Taiwan ones and the Global skills DB has only 3 actives, 2 passives
    // and 3 stigmas for it, so its 22 board skills cannot be described.
    expect(d.classes).toHaveLength(8);
    expect(d.classes.map((c: any) => c.key)).not.toContain("fighter");
    expect(d.classes.map((c: any) => c.key).sort()).toEqual(CLASSES.sort());
    const names = d.classes.map((c: any) => c.name);
    expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b)));
  });

  it("names the four crystal boards in unlock order", () => {
    expect(d.boards.map((b: any) => b.name)).toEqual(BOARDS);
    expect(d.boards.map((b: any) => b.needLevel)).toEqual([12, 20, 30, 40]);
  });

  it("gives every class 12 actives and 10 passives, and a weapon", () => {
    for (const c of CLASSES) {
      const s = d.byClass[c].skills;
      expect(s).toHaveLength(22);
      expect(s.filter((x: any) => x.t === "active")).toHaveLength(12);
      expect(s.filter((x: any) => x.t === "passive")).toHaveLength(10);
      expect(d.byClass[c].weapon, c).toMatch(/^[a-z]+$/);
    }
    expect(d.activePool).toBe(12);
    expect(d.passivePool).toBe(10);
  });
});

describe("daevanion layout", () => {
  it("grants exactly +4 per skill, and never from a seasonal board", () => {
    for (const c of CLASSES)
      for (const s of d.byClass[c].skills) {
        expect(s.lv, `${c} ${s.n}`).toBe(4);
        expect(s.dv, `${c} ${s.n}`).toHaveLength(4);
        expect(s.dv.reduce((a: number, [n]: number[]) => a + n, 0)).toBe(4);
      }
  });

  it("puts actives once on every board", () => {
    for (const c of CLASSES)
      for (const s of d.byClass[c].skills.filter((x: any) => x.t === "active"))
        expect(s.dv.map(([n]: number[]) => n), `${c} ${s.n}`).toEqual([1, 1, 1, 1]);
  });

  it("doubles passives on exactly one of Nezekan or Zikel", () => {
    for (const c of CLASSES)
      for (const s of d.byClass[c].skills.filter((x: any) => x.t === "passive")) {
        const counts = s.dv.map(([n]: number[]) => n);
        expect([[2, 0, 1, 1], [0, 2, 1, 1]], `${c} ${s.n} -> ${counts}`).toContainEqual(counts);
      }
  });

  it("charges nothing for a board with no node, and something for one with", () => {
    for (const c of CLASSES)
      for (const s of d.byClass[c].skills)
        for (const [n, pts] of s.dv) {
          if (n === 0) expect(pts, `${c} ${s.n}`).toBe(0);
          else expect(pts, `${c} ${s.n}`).toBeGreaterThanOrEqual(n * s.dc);
        }
  });

  it("prices actives as Legendary nodes and passives as Rare", () => {
    for (const c of CLASSES)
      for (const s of d.byClass[c].skills)
        expect(s.dc, `${c} ${s.n}`).toBe(s.t === "active" ? 3 : 2);
  });

  it("prices a doubled board above the cost of its two nodes alone", () => {
    // A Steiner cost can never be below the two terminals' own weights, and no
    // skill node sits next to the free centre, so it is strictly above. On the
    // Global boards the two paths share nothing at all (every pair costs
    // exactly the sum of its two solo paths; scripts/test_daevanion_math.py
    // check [5] proves each one optimal).
    let paired = 0;
    for (const c of CLASSES)
      for (const s of d.byClass[c].skills)
        for (const [n, pts] of s.dv)
          if (n === 2) {
            paired++;
            expect(pts, `${c} ${s.n}`).toBeGreaterThan(s.dc * 2);
          }
    expect(paired).toBe(CLASSES.length * 10); // one doubled board per passive
  });

  it("keeps every board cost within the board's own point total", () => {
    // Nezekan, Zikel and Vaizel hold 134 points, Triniel 168 (daevanion.json);
    // a path to one or two nodes must be a small fraction of that
    const total = [134, 134, 134, 168];
    for (const c of CLASSES)
      for (const s of d.byClass[c].skills)
        s.dv.forEach(([, pts]: number[], i: number) =>
          expect(pts, `${c} ${s.n} ${BOARDS[i]}`).toBeLessThan(total[i] / 4),
        );
  });
});

describe("arcana cards", () => {
  it("lists the five card types the Global item DB has, and no Scales", () => {
    // 40 arcana items: Chalice (grail), Parchment, Compass, Bell, Mirror, each
    // "of Vigor" / "of Magic" at Common-Unique. Scales (libra), Hourglass and
    // Key do not exist in the Global data.
    expect(Object.keys(d.cards).sort()).toEqual(["bell", "compass", "grail", "mirror", "parchment"]);
    expect(d.cards.grail).toBe("Chalice");
    expect(d.cards).not.toHaveProperty("libra");
  });

  it("only ever names a small card that exists, when it names one at all", () => {
    // the Global pull carries no per-skill pool membership, so rows currently
    // have no `card`; if a future source restores it, it must be a real card
    const smallCards = ["parchment", "compass", "bell", "mirror"];
    for (const c of CLASSES)
      for (const s of d.byClass[c].skills)
        if (s.card !== undefined) expect(smallCards, `${c} ${s.n}`).toContain(s.card);
  });

  it("sizes the class-wide card pool as every active and passive", () => {
    expect(d.cardPool.union).toBe(d.activePool + d.passivePool);
    expect(d.cardPool.union).toBe(22);
    // small-card membership is not in the Global data; if it comes back it
    // must partition the pools (6+6 actives, 5+5 passives)
    if (d.cardPool.small) {
      expect(d.cardPool.small.active * 2).toBe(d.activePool);
      expect(d.cardPool.small.passive * 2).toBe(d.passivePool);
    }
  });

  it("rolls one skill line per grade step, up to four on Unique", () => {
    expect(Object.keys(d.arcanaLines).sort()).toEqual([...GRADES].sort());
    expect(d.arcanaLines).toEqual({ Common: [1, 1], Rare: [2, 2], Legend: [3, 3], Unique: [4, 4] });
  });
});

describe("soul bind odds", () => {
  // per-line odds the page shows when a row has no exact `p`
  const fallback = (t: string) => d.skillDrawChance / (t === "active" ? d.activePool : d.passivePool);

  it("gives skills a 20% share of a line, split evenly across the pool", () => {
    expect(d.skillDrawChance).toBe(0.2);
    for (const t of ["active", "passive"]) {
      const pool = t === "active" ? d.activePool : d.passivePool;
      expect(near(fallback(t) * pool, 0.2), t).toBe(true);
    }
  });

  it("sums any exact per-skill odds to the pool share", () => {
    // the Global pull has no per-skill weights, so `p` is absent; a source that
    // restores it must still hand each pool its 20%
    for (const c of CLASSES)
      for (const t of ["active", "passive"]) {
        const rows = d.byClass[c].skills.filter((x: any) => x.t === t);
        const withP = rows.filter((x: any) => x.p !== undefined);
        if (withP.length === 0) continue;
        expect(withP, `${c} ${t}: p on some rows but not all`).toHaveLength(rows.length);
        const sum = withP.reduce((a: number, x: any) => a + x.p, 0);
        expect(near(sum, 0.2), `${c} ${t} -> ${sum}`).toBe(true);
      }
  });

  it("reproduces the figures read off the in-game Soul Binding window", () => {
    // +10 Enraged Kromede Silver Dagger (Unique) and Rainy Forest Cloak (Rare),
    // Taiwan client 2026-08-31: actives read 1.666% or 1.668% (the client
    // splits 10000 across 12 as 833/834), passives 2.000%. The even split
    // must land within that rounding of every observed figure.
    const a = d.byClass.assassin.skills;
    const p = (n: string) => {
      const s = a.find((x: any) => x.n === n);
      expect(s, n).toBeDefined();
      return (s.p ?? fallback(s.t)) * 100;
    };
    for (const n of ["Quick Slice", "Shadowstrike", "Heart Gore", "Whirlwind Slice",
                     "Shadow Fall", "Insignia Explosion", "Ambush", "Savage Roar",
                     "Infiltrate", "Flash Slice", "Storm Rampage", "Defiance"])
      expect(near(p(n), 1.667, 1.5e-3), `${n} -> ${p(n)}`).toBe(true);
    for (const n of ["Heightened Sixth Sense", "Apply Poison", "Assault Stance",
                     "Ambush Stance", "Revitalization Contract", "Exploit Weakness",
                     "Rear Smite", "Impact Hit", "Defense Break", "Determination"])
      expect(near(p(n), 2.0, 5e-4), `${n} -> ${p(n)}`).toBe(true);
  });

  it("lists exactly the four gear grades the Global item DB has, no Heroic", () => {
    for (const pool of ["active", "passive"])
      expect(Object.keys(d.gearSlots[pool]).sort(), pool).toEqual([...GRADES].sort());
  });

  it("keeps grade slot counts ascending and within 1-5", () => {
    for (const pool of ["active", "passive"]) {
      let prevHi = 0;
      for (const grade of GRADES) {
        const [lo, hi] = d.gearSlots[pool][grade];
        expect(lo, `${pool} ${grade}`).toBeGreaterThanOrEqual(1);
        expect(hi, `${pool} ${grade}`).toBeLessThanOrEqual(5);
        expect(lo, `${pool} ${grade}`).toBeLessThanOrEqual(hi);
        expect(hi, `${pool} ${grade} not above ${prevHi}`).toBeGreaterThanOrEqual(prevHi);
        prevHi = hi;
      }
    }
    // one line per grade step below Unique, "up to 5 skill effects" on Unique
    for (const pool of ["active", "passive"]) {
      expect(d.gearSlots[pool].Common, pool).toEqual([1, 1]);
      expect(d.gearSlots[pool].Rare, pool).toEqual([2, 2]);
      expect(d.gearSlots[pool].Legend, pool).toEqual([3, 3]);
      expect(d.gearSlots[pool].Unique[1], pool).toBe(5);
    }
  });

  it("keeps the passive slot range narrower than the active one", () => {
    // no piece that carries a passive line (earrings, necklace, armor) ever
    // rolls 3 lines at Unique; only weapons do
    expect(d.gearSlots.active.Unique).toEqual([3, 5]);
    expect(d.gearSlots.passive.Unique).toEqual([4, 5]);
  });
});

describe("assets", () => {
  it("gives every skill an icon filename keyed by class and kind", () => {
    for (const c of CLASSES)
      for (const s of d.byClass[c].skills) {
        expect(s.icon, `${c} ${s.n}`).toMatch(/^[a-z_]+\.webp$/);
        expect(s.icon, `${c} ${s.n}`).toMatch(
          new RegExp(`^${c}_${s.t === "passive" ? "passive" : "skill"}_`),
        );
      }
  });
});
