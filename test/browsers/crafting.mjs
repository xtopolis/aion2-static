/**
 * Runs the built recipe browser in a DOM against the built payloads.
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

const html = readFileSync(`${DIST}/crafting/recipes/index.html`, "utf8");
const { window, document } = parseHTML(html);

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
// linkedom provides no location/history. A small working pair lets the URL-state
// code run for real and lets the tests assert what lands in the query string.
let fakeUrl = new URL("http://local/crafting/recipes/");
Object.defineProperty(window, "location", {
  configurable: true,
  get: () => ({ pathname: fakeUrl.pathname, search: fakeUrl.search, hash: fakeUrl.hash,
                href: fakeUrl.href, toString: () => fakeUrl.href }),
});
window.history = {
  replaceState: (_s, _t, u) => { fakeUrl = new URL(u, fakeUrl); },
  pushState: (_s, _t, u) => { fakeUrl = new URL(u, fakeUrl); },
};
const params = () => Object.fromEntries(new URLSearchParams(fakeUrl.search));

// linkedom tracks neither activeElement nor text selection, so the focus-restore
// path would silently never run. A minimal shim lets the tests exercise it.
let activeEl = null;
Object.defineProperty(document, "activeElement", { configurable: true, get: () => activeEl });
const proto = window.HTMLElement?.prototype ?? window.Element.prototype;
proto.focus = function () { activeEl = this; this.dispatchEvent(new window.Event("focus")); };
proto.blur = function () { if (activeEl === this) activeEl = null; };
proto.setSelectionRange = function (a, b) { this.__sel = [a, b]; };
Object.defineProperty(proto, "selectionStart", {
  configurable: true,
  get() { return this.__sel ? this.__sel[0] : (this.value ?? "").length; },
});

window.clearTimeout = () => {};

const ctx = vm.createContext(window);
const cache = new Map();
const loadChunk = (file) => {
  if (!cache.has(file)) {
    cache.set(file, new vm.SourceTextModule(readFileSync(`${DIST}/_astro/${file}`, "utf8"), {
      context: ctx, identifier: file,
    }));
  }
  return cache.get(file);
};
const inline = [...html.matchAll(/<script type="module">([\s\S]*?)<\/script>/g)]
  .map((m) => m[1]).find((s) => s.includes("rbReady"));
const external = html.match(/src="\/_astro\/(RecipeBrowser[^"]+\.js)"/)?.[1];
const mod = inline
  ? new vm.SourceTextModule(inline, { context: ctx, identifier: "rb.js" })
  : loadChunk(external);
await mod.link((s) => loadChunk(path.basename(s)));
await mod.evaluate();

const settle = async () => { for (let i = 0; i < 30; i++) await new Promise((r) => setImmediate(r)); };
await settle();

const root = document.querySelector(".rb");
const q = (s) => root.querySelector(s);
const qa = (s) => [...root.querySelectorAll(s)];
const qInput = root.querySelector(".fx-q");

console.log("\n=== recipe browser ===");
check("widget root present", !!root);
check("faction control has no counts",
  qa('[aria-label="Choose a faction"] .fx-seg').map((b) => b.textContent).join(",") === "Elyos,Asmodian",
  qa('[aria-label="Choose a faction"] .fx-seg').map((b) => b.textContent).join(","));
check("grade filter present", qa('[aria-label="Filter by grade"] .fx-seg').length === 6);
check("mastery is a tier filter, not a slider",
  qa('[aria-label="Filter by mastery tier"] .fx-seg').length === 4 && !q(".rb-mastery"));
check("rows rendered", qa("tbody tr.rb-row").length === 60, `${qa("tbody tr.rb-row").length}`);
check("only index + one faction fetched", requested.length === 2, requested.join(" "));

// --- table columns ---------------------------------------------------------
// verified against the client: intermediate 115 shows as Professional Lv. 65
{
  const known = qa("tbody tr.rb-row").map((r) => r.children[2].textContent);
  check("no raw 1-115 levels leak into the UI",
    !known.some((t) => /Lv\. (5[1-9]|[6-9]\d|1[01]\d)$/.test(t) && /Novice/.test(t)),
    known.find((t) => /Novice Lv\. (5[1-9]|[6-9]\d)/.test(t)) ?? "clean");
}
check("table has 6 columns", qa("thead th").length === 6,
  qa("thead th").map((t) => t.textContent).join(","));
check("mastery filter is labelled Mastery",
  [...root.querySelectorAll(".fx-label")].some((l) => l.textContent === "Mastery"),
  [...root.querySelectorAll(".fx-label")].map((l) => l.textContent).join(","));
check("materials list is not repeated in the table", qa("tbody .rb-mat").length === 0);
check("proc column removed", !qa("thead th").some((t) => /proc/i.test(t.textContent)));
const row = qa("tbody tr.rb-row")[0];
check("mats column is a count", /^\d+$/.test(row.children[3].textContent), row.children[3].textContent);
check("kinah column shows a number or TBD",
  qa("tbody tr.rb-row").every((r) => /^[\d,]+$|^TBD$/.test(r.children[4].textContent)),
  row.children[4].textContent);
check("some recipes have a real kinah cost",
  qa("tbody tr.rb-row").some((r) => /^[\d,]+$/.test(r.children[4].textContent)));
check("icons exist on disk",
  qa("tbody .rb-icon").every((i) => existsSync(`${DIST}${i.getAttribute("src")}`)));

// --- focus mode (?r=<id>) --------------------------------------------------
const links = qa("tbody a.rb-open");
check("every row has a Focus link", links.length === 60, `${links.length}`);
check("links are real, copyable hrefs", links.every((a) => /^\?r=\d+$/.test(a.getAttribute("href"))),
  links[0]?.getAttribute("href"));
check("no per-recipe pages were built", !existsSync(`${DIST}/crafting/recipes/311052009/index.html`));

const focusTarget = links[0].getAttribute("href").slice(3);
links[0].dispatchEvent(new window.Event("click", { bubbles: true, cancelable: true }));
await settle();
check("focus hides the browsing UI", q(".rb-browse").hasAttribute("hidden"));
check("focus shows the recipe on its own", !q(".rb-focus").hasAttribute("hidden"));
check("focused panel rendered", !!q(".rb-focus .rb-detail-standalone"));
check("focus is in the URL", params().r === focusTarget, JSON.stringify(params()));
check("focused panel still has the craft stepper", !!q(".rb-focus .rb-qty"));
check("focused panel lists materials", q(".rb-focus .rb-mat-list > li") !== null);

q(".rb-back").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
check("back returns to the list", !q(".rb-browse").hasAttribute("hidden") && q(".rb-focus").hasAttribute("hidden"));
check("back clears r from the URL", params().r === undefined, JSON.stringify(params()));

// --- filter persistence ----------------------------------------------------
console.log("\n=== url state ===");
qa('[aria-label="Filter by profession"] .fx-seg').find((b) => b.textContent === "Cooking")
  .dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
check("profession lands in the URL", params().p !== undefined, JSON.stringify(params()));
qa('[aria-label="Filter by grade"] .fx-seg').find((b) => b.textContent === "Rare")
  .dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
check("grade lands in the URL", params().g === "21", JSON.stringify(params()));
qInput.value = "spice";
qInput.dispatchEvent(new window.Event("input", { bubbles: true }));
await settle();
check("search text lands in the URL", params().q === "spice", JSON.stringify(params()));

q(".fx-clear").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
check("clearing empties the query string", Object.keys(params()).length === 0, JSON.stringify(params()));

qa('[aria-label="Choose a faction"] .fx-seg').find((b) => b.textContent === "Asmodian")
  .dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
check("faction lands in the URL", params().f === "dark", JSON.stringify(params()));
check("default faction stays out of the URL",
  (qa('[aria-label="Choose a faction"] .fx-seg').find((b) => b.textContent === "Elyos")
    .dispatchEvent(new window.Event("click", { bubbles: true })), true));
await settle();
check("returning to the default cleans the URL", params().f === undefined, JSON.stringify(params()));

// --- detail panel ----------------------------------------------------------
check("no panel until clicked", qa("tbody tr.rb-detail").length === 0);
row.dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
let panel = q("tbody tr.rb-detail");
check("clicking a row opens a panel", !!panel);
check("open row is marked",
  qa("tbody tr.rb-row")[0].classList.contains("is-open"));
check("panel names the output", /x /.test(panel.querySelector(".rb-out-name").textContent),
  panel.querySelector(".rb-out-name").textContent);
check("materials listed with sources",
  panel.querySelectorAll(".rb-mat-list > li").length > 0 &&
  [...panel.querySelectorAll(".rb-mat-list > li > .rb-line")].every((l) => l.querySelector(".rb-src")));
check("source labels use the known kinds",
  [...panel.querySelectorAll(".rb-src")].every((s) => /craftable|gathered|buy\/drop|^buy [\d,]+$/.test(s.textContent)),
  [...panel.querySelectorAll(".rb-src")].map((s) => s.textContent).join(","));
check("currencies are not listed as materials",
  ![...panel.querySelectorAll(".rb-mat-list .nm")].some((n) => /Kina \(All\)|Abyss Points|Medal of Merit/.test(n.textContent)));
check("kinah appears as a fact instead",
  /Kinah/.test(panel.querySelector(".rb-facts").textContent), panel.querySelector(".rb-facts").textContent);
check("only one panel open at a time", qa("tbody tr.rb-detail").length === 1);

// --- craft multiplier ------------------------------------------------------
const firstQty = [...panel.querySelectorAll(".rb-mat-list > li > .rb-line .q")].map((e) => e.textContent);
panel.querySelector(".rb-qty .rb-step:last-of-type").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
panel = q("tbody tr.rb-detail");
const twoQty = [...panel.querySelectorAll(".rb-mat-list > li > .rb-line .q")].map((e) => e.textContent);
const n = (s) => Number(s.replace(/[x,]/g, ""));
check("craft +1 doubles every material",
  twoQty.length === firstQty.length && twoQty.every((v, i) => n(v) === n(firstQty[i]) * 2),
  `${firstQty[0]} -> ${twoQty[0]}`);
check("output quantity scales too", /^2x |^[2-9]\d*x /.test(panel.querySelector(".rb-out-name").textContent),
  panel.querySelector(".rb-out-name").textContent);

// --- sub-expansion ---------------------------------------------------------
// close this one, then hunt for a row that actually has a craftable input
qa("tbody tr.rb-row")[0].dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
// Target a known multi-layer recipe rather than hunting: the top-grade rows are
// all drop/reward gear, so the first page has nothing craftable to expand.
qInput.value = "Pilgrim Bracelet";
qInput.dispatchEvent(new window.Event("input", { bubbles: true }));
await settle();
qa("tbody tr.rb-row")[0].dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
const expander = q("tbody tr.rb-detail .rb-expand");
check("found a recipe with a craftable material", !!expander);
const beforeSub = q("tbody tr.rb-detail").querySelectorAll(".rb-sub-list > li").length;
expander.dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
panel = q("tbody tr.rb-detail");
check("expanding a craftable material shows its own materials",
  beforeSub === 0 && panel.querySelectorAll(".rb-sub-list > li").length > 0,
  `${panel.querySelectorAll(".rb-sub-list > li").length} sub-materials`);
check("sub-materials also state a source",
  [...panel.querySelectorAll(".rb-sub-list .rb-line")].every((l) => l.querySelector(".rb-src")));
check("sub-material quantities account for the parent's needs",
  [...panel.querySelectorAll(".rb-sub-list .q")].every((e) => /^x[\d,]+$/.test(e.textContent)),
  [...panel.querySelectorAll(".rb-sub-list .q")].map((e) => e.textContent).join(","));

// --- nested expansion + expand all ----------------------------------------
// --- empty state / hidden by filters --------------------------------------
// --- vendor prices --------------------------------------------------------
console.log("\n=== vendor prices ===");
q(".fx-clear").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
qInput.value = "Pilgrim Bracelet";
qInput.dispatchEvent(new window.Event("input", { bubbles: true }));
await settle();
if (!qa("tbody tr.rb-row")[0].classList.contains("is-open")) {
  qa("tbody tr.rb-row")[0].dispatchEvent(new window.Event("click", { bubbles: true }));
  await settle();
}
let vp = q("tbody tr.rb-detail");
vp.querySelector(".rb-expand-all").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
vp = q("tbody tr.rb-detail");
const buys = [...vp.querySelectorAll(".rb-src.s-buy")];
check("vendor-priced materials are labelled buy with a total", buys.length > 0 &&
  buys.every((b) => /^buy [\d,]+$/.test(b.textContent)), buys.map((b) => b.textContent).join(","));
check("buy tags carry the unit price in a tooltip",
  buys.every((b) => /kinah each/.test(b.getAttribute("title"))), buys[0]?.getAttribute("title"));
check("gathered materials are still identified",
  [...vp.querySelectorAll(".rb-src.s-gather")].length > 0 ||
  [...vp.querySelectorAll(".rb-line")].some((l) => /Odyle|Ore/.test(l.textContent)),
  [...vp.querySelectorAll(".rb-src")].map((x) => x.textContent).join(","));
check("Catalyst (Bound) is now a buy, not a drop",
  [...vp.querySelectorAll(".rb-line")].some((l) =>
    /Catalyst/.test(l.textContent) && l.querySelector(".rb-src.s-buy")));
check("unknown sources now read buy/drop",
  [...vp.querySelectorAll(".rb-src.s-drop")].every((s) => s.textContent === "buy/drop"),
  [...vp.querySelectorAll(".rb-src.s-drop")].map((s) => s.textContent).join(","));
check("craft gauge is gone from the panel",
  !/[Cc]raft gauge/.test(vp.querySelector(".rb-facts").textContent),
  vp.querySelector(".rb-facts").textContent);
check("panel totals the vendor materials across the whole chain",
  /Vendor mats \(\d+\)/.test(vp.querySelector(".rb-facts").textContent),
  vp.querySelector(".rb-facts").textContent);

// the craft-count multiplier must scale the vendor spend too
const oneBuy = buys.map((b) => b.textContent);
vp.querySelector(".rb-qty .rb-step:last-of-type").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
vp = q("tbody tr.rb-detail");
const twoBuy = [...vp.querySelectorAll(".rb-src.s-buy")].map((b) => b.textContent);
const kn = (t) => Number(t.replace(/[^\d]/g, ""));
check("vendor spend scales with craft count",
  twoBuy.length === oneBuy.length && twoBuy.every((v, i) => kn(v) === kn(oneBuy[i]) * 2),
  `${oneBuy[0]} -> ${twoBuy[0]}`);

// --- typing in the craft box must not lose focus ---------------------------
console.log("\n=== craft quantity input ===");
q(".fx-clear").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
qInput.value = "Pilgrim Bracelet";
qInput.dispatchEvent(new window.Event("input", { bubbles: true }));
await settle();
// a previous block may already have this row open; only click if it is closed
if (!qa("tbody tr.rb-row")[0].classList.contains("is-open")) {
  qa("tbody tr.rb-row")[0].dispatchEvent(new window.Event("click", { bubbles: true }));
  await settle();
}

const box = q("tbody tr.rb-detail .rb-qty-in");
box.focus();
check("the craft box can hold focus", document.activeElement === box);
box.value = "12";
box.dispatchEvent(new window.Event("input", { bubbles: true }));
await settle();
const box2 = q("tbody tr.rb-detail .rb-qty-in");
// the fix is that the input is never detached — restoring focus afterwards does
// not work, because the browser blurs it during the detach
check("the input element survives typing", box2 === box);
check("it still holds focus", document.activeElement === box2);
check("the typed quantity took effect", box2.value === "12", box2.value);
check("materials scaled to the typed quantity",
  /x\d/.test(q("tbody tr.rb-detail .rb-mat-list .q").textContent),
  q("tbody tr.rb-detail .rb-mat-list .q").textContent);
check("the output line scaled too",
  /^12x /.test(q("tbody tr.rb-detail .rb-out-name").textContent),
  q("tbody tr.rb-detail .rb-out-name").textContent);
check("the vendor total scaled too",
  /Vendor mats \(\d+\) [\d,]+/.test(q("tbody tr.rb-detail .rb-facts").textContent),
  q("tbody tr.rb-detail .rb-facts").textContent);
check("expanders still work after an in-place update",
  !!q("tbody tr.rb-detail .rb-expand"));

// clearing the box mid-edit must not snap it back to 1
box2.focus();
box2.value = "";
box2.dispatchEvent(new window.Event("input", { bubbles: true }));
await settle();
// --- buttons and box stay in step ------------------------------------------
{
  const qb = () => q("tbody tr.rb-detail .rb-qty-in").value;
  const out = () => q("tbody tr.rb-detail .rb-out-name").textContent;
  const step = (last) => q(`tbody tr.rb-detail .rb-qty .rb-step${last ? ":last-of-type" : ""}`)
    .dispatchEvent(new window.Event("click", { bubbles: true }));
  box.value = "1";
  box.dispatchEvent(new window.Event("input", { bubbles: true }));
  await settle();
  step(true); await settle();
  check("the + button updates the box, not just the totals", qb() === "2" && /^2x /.test(out()),
    `box ${qb()} / ${out()}`);
  step(true); await settle();
  check("it keeps counting up", qb() === "3" && /^3x /.test(out()), `box ${qb()} / ${out()}`);
  step(false); await settle();
  check("the − button updates the box too", qb() === "2" && /^2x /.test(out()), `box ${qb()} / ${out()}`);
}

// --- every quantity-dependent surface must agree ---------------------------
{
  const setBox = async (v) => {
    const b = q("tbody tr.rb-detail .rb-qty-in");
    b.value = String(v); b.dispatchEvent(new window.Event("input", { bubbles: true })); await settle();
  };
  await setBox(1);
  const base = qa("tbody tr.rb-detail .rb-mat-list > li > .rb-line .q").map((e) => e.textContent);
  const baseVendor = q("tbody tr.rb-detail .rb-facts").textContent.match(/Vendor mats \(\d+\) ([\d,]+)/)?.[1];
  await setBox(7);
  const n = (t) => Number(String(t).replace(/[^\d]/g, ""));
  check("every top-level material scales by the craft count",
    qa("tbody tr.rb-detail .rb-mat-list > li > .rb-line .q")
      .every((e, i) => n(e.textContent) === n(base[i]) * 7),
    `${base[0]} -> ${qa("tbody tr.rb-detail .rb-mat-list > li > .rb-line .q")[0].textContent}`);
  check("the output line agrees", /^7x /.test(q("tbody tr.rb-detail .rb-out-name").textContent),
    q("tbody tr.rb-detail .rb-out-name").textContent);
  const vendor7 = q("tbody tr.rb-detail .rb-facts").textContent.match(/Vendor mats \(\d+\) ([\d,]+)/)?.[1];
  check("the vendor total agrees", baseVendor && n(vendor7) === n(baseVendor) * 7,
    `${baseVendor} -> ${vendor7}`);
  // expanding rebuilds the panel; the quantity must survive it. A previous block
  // may have left it expanded, so drive it to expanded rather than toggling.
  if (q("tbody tr.rb-detail .rb-expand-all").textContent === "+") {
    q("tbody tr.rb-detail .rb-expand-all").dispatchEvent(new window.Event("click", { bubbles: true }));
    await settle();
  }
  check("the quantity survives a panel rebuild",
    q("tbody tr.rb-detail .rb-qty-in").value === "7" &&
    /^7x /.test(q("tbody tr.rb-detail .rb-out-name").textContent),
    `box ${q("tbody tr.rb-detail .rb-qty-in").value}`);
  check("sub-materials scale with it too",
    qa("tbody tr.rb-detail .rb-sub-list .q").length > 0 &&
    qa("tbody tr.rb-detail .rb-sub-list .q").every((e) => n(e.textContent) > 0));
  if (q("tbody tr.rb-detail .rb-expand-all").textContent === "−") {
    q("tbody tr.rb-detail .rb-expand-all").dispatchEvent(new window.Event("click", { bubbles: true }));
    await settle();
  }
  await setBox(1);
}

// --- range clamping --------------------------------------------------------
const rangeBox = q("tbody tr.rb-detail .rb-qty-in");
check("the box declares its range",
  rangeBox.getAttribute("min") === "1" && rangeBox.getAttribute("max") === "999",
  `${rangeBox.getAttribute("min")}-${rangeBox.getAttribute("max")}`);
rangeBox.value = "5000";
rangeBox.dispatchEvent(new window.Event("input", { bubbles: true }));
await settle();
check("typing past the cap clamps to 999", q("tbody tr.rb-detail .rb-qty-in").value === "999",
  q("tbody tr.rb-detail .rb-qty-in").value);
check("the panel costs the clamped amount",
  /^999x /.test(q("tbody tr.rb-detail .rb-out-name").textContent),
  q("tbody tr.rb-detail .rb-out-name").textContent);
q("tbody tr.rb-detail .rb-qty .rb-step:last-of-type")
  .dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
check("the + button stops at the cap", q("tbody tr.rb-detail .rb-qty-in").value === "999",
  q("tbody tr.rb-detail .rb-qty-in").value);
{
  const b = q("tbody tr.rb-detail .rb-qty-in");
  b.value = "1"; b.dispatchEvent(new window.Event("input", { bubbles: true }));
}
await settle();
q("tbody tr.rb-detail .rb-qty .rb-step").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
check("the − button stops at 1", q("tbody tr.rb-detail .rb-qty-in").value === "1",
  q("tbody tr.rb-detail .rb-qty-in").value);

const emptyBox = q("tbody tr.rb-detail .rb-qty-in");
emptyBox.focus();
emptyBox.value = "";
emptyBox.dispatchEvent(new window.Event("input", { bubbles: true }));
await settle();
check("an empty box is left alone while editing",
  q("tbody tr.rb-detail .rb-qty-in").value === "", q("tbody tr.rb-detail .rb-qty-in").value);
q("tbody tr.rb-detail .rb-qty-in").dispatchEvent(new window.Event("blur", { bubbles: true }));
await settle();
check("leaving the box empty settles back to 1",
  q("tbody tr.rb-detail .rb-qty-in").value === "1", q("tbody tr.rb-detail .rb-qty-in").value);
q("tbody tr.rb-row.is-open").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();

// --- upgrade tag ------------------------------------------------------------
q(".fx-clear").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
qInput.value = "Lava Heart Flamesword";
qInput.dispatchEvent(new window.Event("input", { bubbles: true }));
await settle();
const titles = qa("tbody tr.rb-row .rb-title").map((t) => t.textContent);
check("the two same-named recipes are now distinguishable",
  titles.filter((t) => /\(Upgrade\)$/.test(t)).length === 1 &&
  titles.filter((t) => !/\(Upgrade\)/.test(t)).length >= 1, titles.join(" | "));
const upRow = qa("tbody tr.rb-row").find((r) => /\(Upgrade\)/.test(r.textContent));
upRow.dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
check("the panel carries the tag too",
  /\(Upgrade\)$/.test(q("tbody tr.rb-detail .rb-out-name").textContent),
  q("tbody tr.rb-detail .rb-out-name").textContent);
upRow.dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();

// --- excluded recipes -------------------------------------------------------
q(".fx-clear").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
qInput.value = "Corroded Sovereign";
qInput.dispatchEvent(new window.Event("input", { bubbles: true }));
await settle();
check("gear-change-voucher recipes are excluded",
  !JSON.parse(readFileSync(`${DIST}/data/crafting/recipes-light.json`, "utf8"))
    .some((r) => r.in.some(([id]) => id === "632510022")));
check("faction counts reflect the exclusion (943, not 954)",
  JSON.parse(readFileSync(`${DIST}/data/crafting/index.json`, "utf8")).counts.light === 943);
q(".fx-clear").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();

console.log("\n=== empty state ===");
q(".fx-clear").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
check("empty state is hidden while there are results", q(".fx-empty").hasAttribute("hidden"));
check("empty state has display:none when hidden (not just the attribute)",
  /\.fx \[hidden\][^}]*display:\s*none/.test(
    readFileSync(`${DIST}/_astro/${(html.match(/href="\/_astro\/([^"]+\.css)"/g) || [])
      .map((m) => m.match(/_astro\/([^"]+)/)[1])
      .find((f) => readFileSync(`${DIST}/_astro/${f}`, "utf8").includes(".fx [hidden]"))}`, "utf8")));

// the exact trap: a real match, invisible because a filter is set
qa('[aria-label="Filter by profession"] .fx-seg').find((b) => b.textContent === "Cooking")
  .dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
qInput.value = "Pilgrim Bracelet";
qInput.dispatchEvent(new window.Event("input", { bubbles: true }));
await settle();
check("no results while the wrong filter is set", qa("tbody tr.rb-row").length === 0);
check("empty state is visible now", !q(".fx-empty").hasAttribute("hidden"));
check("empty state reports what the filters are hiding",
  /hidden by your filters/.test(q(".rb-empty-title").textContent), q(".rb-empty-title").textContent);
check("the count is highlighted so the message reads as recoverable",
  q(".rb-empty-title .rb-hi")?.textContent === "1 recipe",
  q(".rb-empty-title .rb-hi")?.textContent);
check("empty state offers to clear the filters", !q(".rb-empty-clear").hasAttribute("hidden"));

q(".rb-empty-clear").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
check("clearing filters reveals the hidden match", qa("tbody tr.rb-row").length > 0,
  `${qa("tbody tr.rb-row").length} rows`);
check("the search text survives the clear", q(".fx-q").value === "Pilgrim Bracelet", q(".fx-q").value);

// a genuine no-match must not claim things are hidden
qInput.value = "zzzznope";
qInput.dispatchEvent(new window.Event("input", { bubbles: true }));
await settle();
check("a real no-match says so plainly",
  /Nothing matches/.test(q(".rb-empty-title").textContent), q(".rb-empty-title").textContent);
check("a real no-match is not highlighted", !q(".rb-empty-title .rb-hi"));
check("no clear-filters button when nothing is hidden", q(".rb-empty-clear").hasAttribute("hidden"));

// results present, but filters still cutting some out
q(".fx-clear").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
qInput.value = "bracelet";
qInput.dispatchEvent(new window.Event("input", { bubbles: true }));
await settle();
qa('[aria-label="Filter by grade"] .fx-seg').find((b) => b.textContent === "Common")
  .dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
check("count line reports hidden results alongside visible ones",
  /hidden by filters/.test(q(".fx-count").textContent) || qa("tbody tr.rb-row").length === 0,
  q(".fx-count").textContent);
q(".fx-clear").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();

console.log("\n=== nested expansion ===");
// Pilgrim Bracelet is the only 3-layer chain in the set, so it is the case that
// proves expansion is not capped at one level.
qInput.value = "Pilgrim Bracelet";
qInput.dispatchEvent(new window.Event("input", { bubbles: true }));
await settle();
const pilgrim = qa("tbody tr.rb-row").find((r) => /Pilgrim Bracelet/.test(r.textContent));
check("found Pilgrim Bracelet", !!pilgrim);
// the previous block may have left this row open; only click if it is closed
if (!pilgrim.classList.contains("is-open")) {
  pilgrim.dispatchEvent(new window.Event("click", { bubbles: true }));
  await settle();
}
let pp = q("tbody tr.rb-detail");
check("expand-all toggle sits beside the Materials label",
  pp.querySelector(".rb-sec-title .rb-expand-all")?.textContent === "+",
  pp.querySelector(".rb-sec-title")?.textContent);
check("toggle explains itself for screen readers",
  /Expand all 3 sub-materials/.test(pp.querySelector(".rb-expand-all").getAttribute("aria-label")),
  pp.querySelector(".rb-expand-all").getAttribute("aria-label"));
pp.querySelector(".rb-expand-all").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
pp = q("tbody tr.rb-detail");
const nesting = (el, d = 0) => {
  const lists = [...el.querySelectorAll(":scope > li > .rb-sub-list")];
  return lists.length ? Math.max(...lists.map((l) => nesting(l, d + 1))) : d;
};
check("expand all reaches three nested layers", nesting(pp.querySelector(".rb-mat-list")) === 3,
  `${nesting(pp.querySelector(".rb-mat-list"))} layers`);
check("toggle flips to collapse", pp.querySelector(".rb-expand-all").textContent === "−" &&
  pp.querySelector(".rb-expand-all").getAttribute("aria-expanded") === "true",
  pp.querySelector(".rb-expand-all").textContent);
check("deep chain shows Magic Crystal's own materials",
  /Spiritstone/.test(pp.textContent) && /Catalyst/.test(pp.textContent));
pp.querySelector(".rb-expand-all").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
pp = q("tbody tr.rb-detail");
check("collapse all closes every layer", pp.querySelectorAll(".rb-sub-list").length === 0);

// self-referencing recipes must not nest forever
qInput.value = "Lava Heart Flamesword";
qInput.dispatchEvent(new window.Event("input", { bubbles: true }));
await settle();
const upgrade = qa("tbody tr.rb-row").find((r) => /Lava Heart Flamesword/.test(r.textContent));
upgrade.dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
const up = q("tbody tr.rb-detail");
const allBtn = up.querySelector(".rb-expand-all");
if (allBtn) {
  allBtn.dispatchEvent(new window.Event("click", { bubbles: true }));
  await settle();
}
check("self-referencing recipe terminates rather than nesting forever",
  q("tbody tr.rb-detail").querySelectorAll(".rb-sub-list").length < 12,
  `${q("tbody tr.rb-detail").querySelectorAll(".rb-sub-list").length} nested lists`);

qInput.value = "";
qInput.dispatchEvent(new window.Event("input", { bubbles: true }));
await settle();

const stillOpen = q("tbody tr.rb-row.is-open");
if (stillOpen) { stillOpen.dispatchEvent(new window.Event("click", { bubbles: true })); await settle(); }
check("clicking again closes the panel",
  qa("tbody tr.rb-detail").length === 0 && qa("tbody tr.rb-row.is-open").length === 0);

// --- filters ---------------------------------------------------------------
const cook = qa('[aria-label="Filter by profession"] .fx-seg').find((b) => b.textContent === "Cooking");
cook.dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
check("profession filter narrows the list", /of 23 recipes/.test(q(".fx-count").textContent),
  q(".fx-count").textContent);

qa('[aria-label="Filter by mastery tier"] .fx-seg').find((b) => /Novice/.test(b.textContent))
  .dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
const beg = Number(q(".fx-count").textContent.match(/of (\d+)/)?.[1] ?? -1);
check("mastery tier filters", beg > 0 && beg < 23, `${beg} Novice cooking recipes`);
// the game shows tier + level within tier, not the raw 1-115 bar
check("mastery reads the way the game does",
  qa("tbody tr.rb-row").every((r) => /^(Novice|Professional) Lv\. \d+$|^no requirement$/.test(r.children[2].textContent)),
  qa("tbody tr.rb-row")[0]?.children[2].textContent);

q(".fx-clear").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
check("clear restores everything", /of 943 recipes/.test(q(".fx-count").textContent), q(".fx-count").textContent);

qa('[aria-label="Filter by grade"] .fx-seg').find((b) => b.textContent === "Mythic")
  .dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
check("grade filter works", /of \d+ recipes/.test(q(".fx-count").textContent), q(".fx-count").textContent);
q(".fx-clear").dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();

// --- faction switch --------------------------------------------------------
// dark was already fetched by the URL-state block above, so this asserts the
// cache holds rather than that a new request goes out
const before = requested.length;
qa('[aria-label="Choose a faction"] .fx-seg').find((b) => b.textContent === "Asmodian")
  .dispatchEvent(new window.Event("click", { bubbles: true }));
await settle();
check("a seen faction is not refetched", requested.length === before, requested.slice(before).join(" "));
check("dark faction has its own 943", /of 943 recipes/.test(q(".fx-count").textContent), q(".fx-count").textContent);
check("each faction was fetched exactly once",
  requested.filter((u) => /recipes-light/.test(u)).length === 1 &&
  requested.filter((u) => /recipes-dark/.test(u)).length === 1,
  requested.join(" "));

// --- state survives a reload ----------------------------------------------
// A fresh mount with a preset query string is exactly what a reload or a shared
// link does, and it is the whole point of putting state in the URL.
console.log("\n=== restore from a shared URL ===");
{
  const { window: w2, document: d2 } = parseHTML(html);
  let u2 = new URL("http://local/crafting/recipes/?f=dark&g=41&q=sword");
  Object.defineProperty(w2, "location", {
    configurable: true,
    get: () => ({ pathname: u2.pathname, search: u2.search, hash: u2.hash, href: u2.href }),
  });
  w2.history = { replaceState: (_s, _t, u) => { u2 = new URL(u, u2); },
                 pushState: (_s, _t, u) => { u2 = new URL(u, u2); } };
  w2.fetch = async (url) => {
    const file = `${DIST}${String(url).split("?")[0]}`;
    if (!existsSync(file)) return { ok: false, status: 404, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => JSON.parse(readFileSync(file, "utf8")) };
  };
  w2.console = console; w2.Math = Math; w2.JSON = JSON;
  w2.setTimeout = (fn) => { fn(); return 0; };
  w2.clearTimeout = () => {};

  const c2 = vm.createContext(w2);
  const cache2 = new Map();
  const load2 = (f) => {
    if (!cache2.has(f)) cache2.set(f, new vm.SourceTextModule(
      readFileSync(`${DIST}/_astro/${f}`, "utf8"), { context: c2, identifier: f }));
    return cache2.get(f);
  };
  const m2 = inline
    ? new vm.SourceTextModule(inline, { context: c2, identifier: "rb2.js" })
    : load2(external);
  await m2.link((sp) => load2(path.basename(sp)));
  await m2.evaluate();
  for (let i = 0; i < 30; i++) await new Promise((r) => setImmediate(r));

  const r2 = d2.querySelector(".rb");
  const qa2 = (sel) => [...r2.querySelectorAll(sel)];
  check("faction restored from the URL",
    qa2('[aria-label="Choose a faction"] .fx-seg.is-active')[0]?.textContent === "Asmodian",
    qa2('[aria-label="Choose a faction"] .fx-seg.is-active')[0]?.textContent);
  check("grade restored from the URL",
    qa2('[aria-label="Filter by grade"] .fx-seg.is-active')[0]?.textContent === "Unique",
    qa2('[aria-label="Filter by grade"] .fx-seg.is-active')[0]?.textContent);
  check("search box repopulated", r2.querySelector(".fx-q").value === "sword",
    r2.querySelector(".fx-q").value);
  check("results reflect the restored filters",
    /Showing \d+ of \d+ recipes/.test(r2.querySelector(".fx-count").textContent),
    r2.querySelector(".fx-count").textContent);
  check("every restored row matches the search",
    qa2("tbody tr.rb-row .rb-title").every((t) => /sword/i.test(t.textContent)),
    qa2("tbody tr.rb-row .rb-title")[0]?.textContent);
}

console.log(`\n${failures === 0 ? "ALL CHECKS PASSED" : `${failures} FAILURE(S)`}`);
process.exit(failures ? 1 : 0);
