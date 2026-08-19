/**
 * Runs the built Daevanion board page in a DOM against the built payloads.
 *
 * The component's script is small enough that Astro inlines it, so this pulls
 * the inline module out of the HTML rather than loading a chunk from _astro/.
 */
import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseHTML } from "linkedom";
import vm from "node:vm";

const ROOT = path.resolve(fileURLToPath(import.meta.url), "../../..");
const DIST = `${ROOT}/dist`;

let failures = 0;
const check = (label, ok, detail = "") => {
  if (!ok) failures++;
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${label}${detail ? ` — ${detail}` : ""}`);
};

const html = readFileSync(`${DIST}/daevanion/boards/index.html`, "utf8");
const { window, document } = parseHTML(html);

// Serve the real built payloads; record what was requested so we can assert the
// split actually behaves lazily.
const requested = [];
window.fetch = async (url) => {
  requested.push(url);
  const file = `${DIST}${String(url).split("?")[0]}`;
  if (!existsSync(file)) return { ok: false, status: 404, json: async () => ({}) };
  return { ok: true, status: 200, json: async () => JSON.parse(readFileSync(file, "utf8")) };
};
window.console = console;
window.Math = Math;
window.JSON = JSON;
window.setTimeout = (fn) => { fn(); return 0; };
// linkedom has no layout engine. Feed the placement code plausible geometry so
// it exercises the real branches instead of dividing by an absent rect.
const rect = (l, t, w, h) => ({ left: l, top: t, width: w, height: h, right: l + w, bottom: t + h });
Object.defineProperty(window.Element.prototype, "getBoundingClientRect", {
  configurable: true,
  value() {
    if (this.classList?.contains("db-stage")) return rect(0, 0, 640, 640);
    if (this.classList?.contains("db-tip")) return rect(0, 0, 200, 90);
    const m = /grid-area:\s*(\d+)\s*\/\s*(\d+)/.exec(this.getAttribute?.("style") ?? "");
    if (m) return rect((+m[2] - 1) * 42 + 8, (+m[1] - 1) * 42 + 8, 38, 38);
    return rect(0, 0, 0, 0);
  },
});

const ctx = vm.createContext(window);

// Astro inlines small scripts and emits larger ones as chunks; this component has
// crossed that threshold before, so handle both rather than assuming either.
const cache = new Map();
const loadChunk = (file) => {
  if (!cache.has(file)) {
    cache.set(file, new vm.SourceTextModule(readFileSync(`${DIST}/_astro/${file}`, "utf8"), {
      context: ctx, identifier: file,
    }));
  }
  return cache.get(file);
};
const linker = (specifier) => loadChunk(path.basename(specifier));

const inline = [...html.matchAll(/<script type="module">([\s\S]*?)<\/script>/g)]
  .map((m) => m[1])
  .find((s) => s.includes("dbReady"));
const external = html.match(/src="\/_astro\/(DaevanionBoard[^"]+\.js)"/)?.[1];
if (!inline && !external) throw new Error("could not find the board script in the built page");

const mod = inline
  ? new vm.SourceTextModule(inline, { context: ctx, identifier: "db.js" })
  : loadChunk(external);
await mod.link(linker);
await mod.evaluate();

const settle = async () => { for (let i = 0; i < 20; i++) await new Promise((r) => setImmediate(r)); };
await settle();

const root = document.querySelector(".db");
const q = (s) => root.querySelector(s);
const qa = (s) => [...root.querySelectorAll(s)];

console.log("\n=== Daevanion board ===");
check("widget root present", !!root);
check("class dropdown filled with 9 classes", qa(".db-class option").length === 9,
  `${qa(".db-class option").length}`);
check("first class selected, not the loading stub", q(".db-class").value === "gladiator",
  q(".db-class").value);
check("board control has 8 gods", qa('[aria-label="Choose a Daevanion board"] .fx-seg').length === 8);
check("board buttons are the god names",
  qa('[aria-label="Choose a Daevanion board"] .fx-seg').map((b) => b.textContent).join(",") ===
    "Nezekan,Zikel,Vaizel,Triniel,Ariel,Azphel,Marchutan,Yustiel");
check("Nezekan active by default",
  q('[aria-label="Choose a Daevanion board"] .fx-seg.is-active')?.textContent === "Nezekan");

// --- the grid itself -------------------------------------------------------
const cells = qa(".db-cell");
check("153 occupied cells rendered", cells.length === 153, `${cells.length}`);
check("empty cells produce no DOM", cells.length < 225);

const areas = cells.map((c) => c.getAttribute("style"));
check("every cell is explicitly placed", areas.every((a) => /grid-area:\s*\d+\s*\/\s*\d+/.test(a)));
const coords = areas.map((a) => a.match(/grid-area:\s*(\d+)\s*\/\s*(\d+)/).slice(1).map(Number));
check("all coordinates inside a 15x15 grid",
  coords.every(([r, c]) => r >= 1 && r <= 15 && c >= 1 && c <= 15));
check("no two cells share a position", new Set(coords.map(String)).size === 153);

const start = qa(".db-cell.is-start");
check("exactly one start cell", start.length === 1);
check("start cell is at the centre (8,8)",
  /grid-area:\s*8\s*\/\s*8/.test(start[0].getAttribute("style")), start[0].getAttribute("style"));
check("start cell is labelled free", /free/i.test(start[0].getAttribute("aria-label")),
  start[0].getAttribute("aria-label"));

// --- skill nodes carry the artwork ----------------------------------------
const skillCells = qa(".db-cell.is-skill");
check("22 skill nodes on Nezekan", skillCells.length === 22, `${skillCells.length}`);
check("every skill node has an image", skillCells.every((c) => c.querySelector("img")));
const srcs = skillCells.map((c) => c.querySelector("img").getAttribute("src"));
check("images point at the chosen class", srcs.every((s) => s.startsWith("/skills/gladiator/")),
  srcs[0]);
check("every skill image exists on disk", srcs.every((s) => existsSync(`${DIST}${s}`)),
  srcs.find((s) => !existsSync(`${DIST}${s}`)) ?? "");
check("skill images lazy-load", skillCells.every((c) => c.querySelector("img").getAttribute("loading") === "lazy"));
check("skill nodes name the skill", /\+1 level/.test(skillCells[0].getAttribute("aria-label")),
  skillCells[0].getAttribute("aria-label"));

// --- stat nodes ------------------------------------------------------------
const statCells = cells.filter((c) => !c.classList.contains("is-skill") && !c.classList.contains("is-start"));
check("130 stat nodes on Nezekan", statCells.length === 130, `${statCells.length}`);
check("every cell carries a grade class", cells.every((c) => /\bg-\d+\b/.test(c.className)));
check("stat labels resolve (no raw stat ids)",
  statCells.every((c) => !/\b(hpmax|combatspeed|cooltimedecrease)\b/.test(c.getAttribute("aria-label"))),
  statCells.find((c) => /\bhpmax\b/.test(c.getAttribute("aria-label")))?.getAttribute("aria-label") ?? "");
check("stat nodes state grade and cost",
  /· (Common|Rare|Legendary|Unique) · \d+ pts?$/.test(statCells[0].getAttribute("aria-label")),
  statCells[0].getAttribute("aria-label"));

// --- floating tooltip ------------------------------------------------------
console.log("\n=== tooltip ===");
const tip = q(".db-tip");
check("tooltip exists and starts hidden", !!tip && tip.hasAttribute("hidden"));
check("cells carry no native title (would double up)", cells.every((c) => !c.hasAttribute("title")));

const skillCell = skillCells[0];
skillCell.dispatchEvent(new window.Event("mouseenter", { bubbles: false }));
check("tooltip shows on hover", !tip.hasAttribute("hidden"));
check("tooltip names the skill", tip.querySelector(".db-tip-title").textContent.startsWith("Protection Armor"),
  tip.querySelector(".db-tip-title").textContent);
check("tooltip shows the skill icon", !!tip.querySelector(".db-tip-icon"));
check("tooltip states the level gain", /\+1/.test(tip.querySelector(".db-tip-list").textContent),
  tip.querySelector(".db-tip-list").textContent);
check("tooltip carries a grade chip", /\bg-21\b/.test(tip.querySelector(".fx-grade").className),
  tip.querySelector(".fx-grade").className);
check("tooltip states the cost", /2 points/.test(tip.querySelector(".db-tip-meta").textContent),
  tip.querySelector(".db-tip-meta").textContent);
check("tooltip is positioned", /\d/.test(tip.style.left) && /\d/.test(tip.style.top),
  `left ${tip.style.left} top ${tip.style.top}`);
skillCell.dispatchEvent(new window.Event("mouseleave", { bubbles: false }));
check("tooltip hides on leave", tip.hasAttribute("hidden"));

// a top-row cell has no room above, so the tooltip must flip below it
const topCell = cells.find((c) => /grid-area:\s*1\s*\//.test(c.getAttribute("style")));
topCell.dispatchEvent(new window.Event("mouseenter", { bubbles: false }));
check("tooltip flips below near the top edge", tip.classList.contains("is-below"));
const midCell = cells.find((c) => /grid-area:\s*1[02]\s*\//.test(c.getAttribute("style")));
midCell.dispatchEvent(new window.Event("mouseenter", { bubbles: false }));
check("tooltip sits above elsewhere", !tip.classList.contains("is-below"));
// left-edge cell: the clamp must keep half the tooltip inside the stage
const edgeCell = cells.find((c) => /grid-area:\s*8\s*\/\s*1\b/.test(c.getAttribute("style")));
edgeCell.dispatchEvent(new window.Event("mouseenter", { bubbles: false }));
check("tooltip clamped inside the stage", parseFloat(tip.style.left) >= 100,
  `left ${tip.style.left} (half-width is 100)`);

// a two-stat node must list both lines
const twoStat = cells.find((c) => (c.getAttribute("aria-label").match(/,/g) ?? []).length >= 1
  && !c.classList.contains("is-skill"));
if (twoStat) {
  twoStat.dispatchEvent(new window.Event("mouseenter", { bubbles: false }));
  check("multi-stat node lists every stat", tip.querySelectorAll(".db-tip-list li").length >= 1);
}

// --- layout order ----------------------------------------------------------
const kids = [...root.children].map((e) => e.className.split(" ")[0] || e.tagName.toLowerCase());
check("picker sits above the board", kids.indexOf("db-picker") < kids.indexOf("db-stage"), kids.join(" > "));
check("legend sits below the board", kids.indexOf("db-legend") > kids.indexOf("db-stage"), kids.join(" > "));
check("old totals section and rule are gone",
  !kids.includes("db-totals") && !kids.includes("db-rule"), kids.join(" > "));
check("heading renamed", q(".db-picker .fx-section-title").textContent === "Available skills and stats",
  q(".db-picker .fx-section-title").textContent);

// --- totals ----------------------------------------------------------------
console.log("\n=== picker ===");
// Golden values taken from the untouched package's own summary.statTotals for
// Nezekan, so this catches the normalization drifting from the source.
const EXPECTED = {
  "Attack Bonus": "+205", "Combat Speed": "+5%", "Cooldown Reduction": "+5%",
  "Critical Hit": "+200", "Critical Hit Resist": "+200", "Defense Bonus": "+2050",
  "HP": "+2000", "MP": "+1000",
};
const statChips = qa(".db-chips-stats .db-chip");
const statRows = Object.fromEntries(statChips.map((c) =>
  [c.querySelector(".lbl").textContent, c.querySelector(".v").textContent]));
check("stat totals match the source package exactly",
  JSON.stringify(statRows) === JSON.stringify(EXPECTED), JSON.stringify(statRows));

const skillChips = qa(".db-chips-skills .db-chip");
check("one chip per skill", skillChips.length === 17, `${skillChips.length} skills`);
check("skill levels sum to the 22 skill nodes",
  skillChips.reduce((s, c) => s + Number(c.querySelector(".v").textContent.replace("+", "")), 0) === 22);
check("skills sorted alphabetically",
  skillChips.map((c) => c.querySelector(".lbl").textContent)
    .every((v, i, a) => i === 0 || a[i - 1].localeCompare(v) <= 0),
  skillChips.slice(0, 3).map((c) => c.querySelector(".lbl").textContent).join(", "));
check("stats sorted alphabetically",
  statChips.map((c) => c.querySelector(".lbl").textContent)
    .every((v, i, a) => i === 0 || a[i - 1].localeCompare(v) <= 0),
  statChips.slice(0, 3).map((c) => c.querySelector(".lbl").textContent).join(", "));
check("skill chips show icons", skillChips.every((c) => c.querySelector(".db-chip-icon")));
check("every chip has a checkbox", [...skillChips, ...statChips].every((c) => c.querySelector("input[type=checkbox]")));
check("a skill on two nodes reads +2", skillChips.some((c) => c.querySelector(".v").textContent === "+2"));
check("cost line is points only, no reset gold",
  q(".db-cost").textContent.trim() === "210 points", q(".db-cost").textContent);

// --- highlighting ---------------------------------------------------------
console.log("\n=== highlighting ===");
const board = q(".db-board");
check("nothing dimmed by default", !board.classList.contains("is-focusing"));
check("no cells lit by default", qa(".db-cell.is-lit").length === 0);

// hovering a chip previews without committing
const twoNodeChip = skillChips.find((c) => c.querySelector(".v").textContent === "+2");
twoNodeChip.dispatchEvent(new window.Event("mouseenter", { bubbles: false }));
check("hovering a chip focuses the board", board.classList.contains("is-focusing"));
check("hovering lights exactly the nodes granting it", qa(".db-cell.is-lit").length === 2,
  `${qa(".db-cell.is-lit").length} lit for a +2 skill`);
check("lit nodes are the skill nodes", qa(".db-cell.is-lit").every((c) => c.classList.contains("is-skill")));
twoNodeChip.dispatchEvent(new window.Event("mouseleave", { bubbles: false }));
check("leaving clears the preview", qa(".db-cell.is-lit").length === 0 && !board.classList.contains("is-focusing"));

// checking one keeps it lit
const cb = twoNodeChip.querySelector("input");
cb.checked = true;
cb.dispatchEvent(new window.Event("change", { bubbles: true }));
check("checking a chip keeps nodes lit", qa(".db-cell.is-lit").length === 2);
check("checked chip is marked", twoNodeChip.classList.contains("is-on"));

// hovering a second chip adds to the checked one rather than replacing it
const statChip = statChips.find((c) => c.querySelector(".lbl").textContent === "HP");
statChip.dispatchEvent(new window.Event("mouseenter", { bubbles: false }));
const hpNodes = qa(".db-cell").filter((c) => c.getAttribute("aria-label").startsWith("HP ")).length;
check("hover stacks on top of checked", qa(".db-cell.is-lit").length === 2 + hpNodes,
  `${qa(".db-cell.is-lit").length} lit, expected ${2 + hpNodes}`);
statChip.dispatchEvent(new window.Event("mouseleave", { bubbles: false }));
check("checked selection survives the hover leaving", qa(".db-cell.is-lit").length === 2);

cb.checked = false;
cb.dispatchEvent(new window.Event("change", { bubbles: true }));
check("unchecking clears it", qa(".db-cell.is-lit").length === 0 && !board.classList.contains("is-focusing"));

check("meta line names the board and unlock level",
  q(".db-meta").textContent.trim() === "Nezekan · unlocks at level 12", q(".db-meta").textContent);
check("meta line drops board number, points and node count",
  !/board \d of 8|points to fill|skill nodes/.test(q(".db-meta").textContent), q(".db-meta").textContent);

// --- lazy loading ----------------------------------------------------------
console.log("\n=== lazy loading ===");
check("only index + one class + one layout fetched", requested.length === 3, requested.join(" "));
check("did not fetch all 8 layouts", requested.filter((u) => u.includes("layout-")).length === 1);
check("did not fetch all 9 classes", requested.filter((u) => u.includes("class-")).length === 1);

// switching board fetches exactly one more file
const before = requested.length;
const ariel = qa('[aria-label="Choose a Daevanion board"] .fx-seg').find((b) => b.textContent === "Ariel");
ariel.dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
check("switching board fetches only that layout", requested.length === before + 1,
  requested.slice(before).join(" "));
check("Ariel has no skill nodes", qa(".db-cell.is-skill").length === 0);
check("Ariel still renders 153 cells", qa(".db-cell").length === 153);
check("class picker disabled on a class-agnostic board", q(".db-class").disabled === true);
check("picker drops the skills group on a stats-only board",
  q(".db-picker").classList.contains("is-stats-only"));
check("no skill chips on a stats-only board", qa(".db-chips-skills .db-chip").length === 0);
check("stat chips still listed", qa(".db-chips-stats .db-chip").length > 0,
  `${qa(".db-chips-stats .db-chip").length}`);
check("cost line follows the board", q(".db-cost").textContent.trim() === "232 points", q(".db-cost").textContent);
check("picks reset when the board changes", qa(".db-cell.is-lit").length === 0);
// Ariel is full of Rare nodes granting two stats at once — the tooltip must show both
const pair = qa(".db-cell").find((c) => c.getAttribute("aria-label").includes(","));
pair.dispatchEvent(new window.Event("mouseenter", { bubbles: false }));
check("two-stat node shows two tooltip lines", q(".db-tip-list").querySelectorAll("li").length === 2,
  `${q(".db-tip-list").querySelectorAll("li").length}: ${q(".db-tip-list").textContent}`);
check("meta says the board is class-agnostic", /identical for every class/.test(q(".db-meta").textContent),
  q(".db-meta").textContent);

// returning to a seen board must not refetch
const before2 = requested.length;
qa('[aria-label="Choose a Daevanion board"] .fx-seg').find((b) => b.textContent === "Nezekan")
  .dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
check("returning to a seen board refetches nothing", requested.length === before2,
  requested.slice(before2).join(" "));
check("class picker re-enabled on a skill board", q(".db-class").disabled === false);

// switching class fetches one class file and reuses the layout
const before3 = requested.length;
const sel = q(".db-class");
// Only mark the target. Setting `selected = false` on later options clears the
// selection entirely in linkedom, which a real browser does not do.
[...sel.querySelectorAll("option")].find((o) => o.value === "cleric").selected = true;
sel.dispatchEvent(new window.Event("change", { bubbles: true }));
await settle();
check("switching class fetches only the class overlay", requested.length === before3 + 1,
  requested.slice(before3).join(" "));
check("skill images follow the new class",
  qa(".db-cell.is-skill img").every((i) => i.getAttribute("src").startsWith("/skills/cleric/")),
  qa(".db-cell.is-skill img")[0]?.getAttribute("src"));
check("new class images exist on disk",
  qa(".db-cell.is-skill img").every((i) => existsSync(`${DIST}${i.getAttribute("src")}`)));

console.log(`\n${failures === 0 ? "ALL CHECKS PASSED" : `${failures} FAILURE(S)`}`);
process.exit(failures ? 1 : 0);
