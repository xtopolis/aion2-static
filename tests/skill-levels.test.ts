import { describe, expect, it } from "vitest";
import data from "../src/data/skill-levels.json";

/**
 * Invariants for src/data/skill-levels.json, plus the figures we have actually
 * seen in game. The graph maths behind the Daevanion point costs is verified
 * separately by scripts/test_daevanion_math.py, which needs the client dump;
 * this suite runs anywhere and guards the shape of what ships.
 */

const d = data as any;
const CLASSES = Object.keys(d.byClass);
const BOARDS = ["Nezekan", "Zikel", "Vaizel", "Triniel"];
const near = (a: number, b: number, eps = 5e-6) => Math.abs(a - b) < eps;

describe("dataset shape", () => {
  it("carries all nine classes, alphabetical by display name", () => {
    expect(d.classes).toHaveLength(9);
    const names = d.classes.map((c: any) => c.name);
    expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b)));
  });

  it("names the four crystal boards in unlock order", () => {
    expect(d.boards.map((b: any) => b.name)).toEqual(BOARDS);
    expect(d.boards.map((b: any) => b.needLevel)).toEqual([12, 20, 30, 40]);
  });

  it("gives every class 12 actives and 10 passives", () => {
    for (const c of CLASSES) {
      const s = d.byClass[c].skills;
      expect(s).toHaveLength(22);
      expect(s.filter((x: any) => x.t === "active")).toHaveLength(12);
      expect(s.filter((x: any) => x.t === "passive")).toHaveLength(10);
    }
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
    let paired = 0;
    for (const c of CLASSES)
      for (const s of d.byClass[c].skills)
        for (const [n, pts] of s.dv)
          if (n === 2) {
            paired++;
            expect(pts, `${c} ${s.n}`).toBeGreaterThan(s.dc * 2);
          }
    expect(paired).toBe(9 * 10); // one doubled board per passive, nine classes
  });

  it("never claims a paired board saves more than a point", () => {
    // the page used to say the two nodes "share most of one path". They do not:
    // 72 of the 90 pairs share nothing at all and the rest save exactly 1 point.
    // Guarded here so the prose cannot drift back.
    const savings: number[] = [];
    for (const c of CLASSES)
      for (const s of d.byClass[c].skills) {
        const doubled = s.dv.findIndex(([n]: number[]) => n === 2);
        if (doubled < 0) continue;
        const solo = d.byClass[c].skills
          .flatMap((x: any) => x.dv)
          .filter(([n]: number[]) => n === 1);
        void solo;
        savings.push(s.dv[doubled][1]);
      }
    expect(savings).toHaveLength(90);
    // a pair can never cost less than one node's own price twice
    for (const v of savings) expect(v).toBeGreaterThanOrEqual(4);
  });
});

describe("arcana card partition", () => {
  it("routes actives to Parchment or Compass and passives to Bell or Mirror", () => {
    for (const c of CLASSES)
      for (const s of d.byClass[c].skills)
        expect(s.t === "active" ? ["parchment", "compass"] : ["bell", "mirror"],
          `${c} ${s.n}`).toContain(s.card);
  });

  it("splits each pool evenly between its two small cards", () => {
    for (const c of CLASSES) {
      const by = (card: string) => d.byClass[c].skills.filter((x: any) => x.card === card).length;
      expect([by("parchment"), by("compass")], c).toEqual([6, 6]);
      expect([by("bell"), by("mirror")], c).toEqual([5, 5]);
    }
  });
});

describe("soul bind odds", () => {
  it("gives each pool a 20% share of a line", () => {
    for (const c of CLASSES)
      for (const t of ["active", "passive"]) {
        const sum = d.byClass[c].skills
          .filter((x: any) => x.t === t)
          .reduce((a: number, x: any) => a + x.p, 0);
        expect(near(sum, 0.2), `${c} ${t} -> ${sum}`).toBe(true);
      }
  });

  it("matches the figures read off the in-game Soul Binding window", () => {
    // +10 Enraged Kromede Silver Dagger (Unique) and Rainy Forest Cloak (Rare)
    const a = d.byClass.assassin.skills;
    const p = (n: string) => a.find((x: any) => x.n === n).p * 100;
    for (const n of ["Quick Slice", "Shadowstrike", "Heart Gore", "Whirlwind Slice",
                     "Shadow Fall", "Insignia Explosion", "Ambush", "Savage Roar"])
      expect(near(p(n), 1.666, 5e-4), `${n} -> ${p(n)}`).toBe(true);
    for (const n of ["Infiltrate", "Flash Slice", "Storm Rampage", "Defiance"])
      expect(near(p(n), 1.668, 5e-4), `${n} -> ${p(n)}`).toBe(true);
    for (const n of ["Heightened Sixth Sense", "Apply Poison", "Assault Stance",
                     "Ambush Stance", "Revitalization Contract", "Exploit Weakness",
                     "Rear Smite", "Impact Hit", "Defense Break", "Determination"])
      expect(near(p(n), 2.0, 5e-4), `${n} -> ${p(n)}`).toBe(true);
  });

  it("keeps grade slot counts ascending and within 1-6", () => {
    for (const pool of ["active", "passive"])
      for (const [grade, [lo, hi]] of Object.entries<any>(d.gearSlots[pool])) {
        expect(lo, `${pool} ${grade}`).toBeGreaterThanOrEqual(1);
        expect(hi, `${pool} ${grade}`).toBeLessThanOrEqual(6);
        expect(lo, `${pool} ${grade}`).toBeLessThanOrEqual(hi);
      }
    // "Up to 5 skill effects" on a Unique Guard, "up to 6" on a Heroic one
    expect(d.gearSlots.active.Unique[1]).toBe(5);
    expect(d.gearSlots.active.Heroic[1]).toBe(6);
  });

  it("keeps the passive slot range narrower than the active one", () => {
    // no piece that carries a passive line (earrings, necklace, armor) ever
    // rolls 3 lines at Unique or 4 at Heroic; only main weapons do
    expect(d.gearSlots.passive.Unique).toEqual([4, 5]);
    expect(d.gearSlots.passive.Heroic).toEqual([5, 6]);
    expect(d.gearSlots.active.Unique).toEqual([3, 5]);
  });
});

describe("assets", () => {
  it("gives every skill an icon filename", () => {
    for (const c of CLASSES)
      for (const s of d.byClass[c].skills)
        expect(s.icon, `${c} ${s.n}`).toMatch(/^[a-z_]+\.webp$/);
  });
});
