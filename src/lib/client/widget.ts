/**
 * Helpers shared by the dataset browsers' client scripts.
 *
 * ⚠ This module ships to the BROWSER. It must never import anything from
 * `src/data/` or from the build-time transforms in `src/lib/` — a single such
 * import would pull a multi-hundred-KB dump into the client bundle. Keep it to
 * pure functions and DOM work.
 */

/** Formats a display-scaled stat value: `+5`, `-3`, `+0.1%`. */
export const fmt = (n: number, pct: boolean): string =>
  `${n < 0 ? "" : "+"}${Number(n.toFixed(2))}${pct ? "%" : ""}`;

/** True when every character of `needle` appears in `hay`, in order. */
export function subseq(hay: string, needle: string): boolean {
  let i = 0;
  for (let j = 0; j < hay.length && i < needle.length; j++) {
    if (hay[j] === needle[i]) i++;
  }
  return i === needle.length;
}

/**
 * Relevance score for a name against search terms, or -1 if any term misses.
 *
 * Deliberately name-only. Matching longer prose (a title's obtain text) buried
 * real name hits under formulaic boilerplate, and fuzzy subsequence matching
 * over it returned nearly the whole dataset for short queries.
 */
export function scoreName(name: string, terms: string[]): number {
  if (!terms.length) return 0;
  const n = name.toLowerCase();
  let total = 0;
  for (const t of terms) {
    let best = 0;
    if (n.startsWith(t)) best = 100;
    else if (n.includes(t)) best = 70;
    else if (t.length >= 3 && subseq(n, t)) best = 25;
    if (!best) return -1;
    total += best;
  }
  return total;
}

/** Splits a raw query into lowercase terms. */
export const terms = (q: string): string[] =>
  q.trim().toLowerCase().split(/\s+/).filter(Boolean);

export interface SegItem {
  key: string;
  label: string;
}

/**
 * Fills a segmented control with buttons and wires up selection. Marking the
 * active button is left to `setActive` so callers that rebuild the control (or
 * drive it from elsewhere, like the slot chips) stay in sync.
 */
export function segmented(
  bar: HTMLElement,
  items: SegItem[],
  active: string,
  onPick: (key: string) => void
): void {
  bar.replaceChildren(
    ...items.map((it) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "fx-seg" + (it.key === active ? " is-active" : "");
      b.dataset.key = it.key;
      b.textContent = it.label;
      b.addEventListener("click", () => onPick(it.key));
      return b;
    })
  );
}

/** Moves the active marker in a segmented control. */
export function setActive(bar: HTMLElement, key: string): void {
  for (const b of bar.querySelectorAll<HTMLElement>(".fx-seg")) {
    b.classList.toggle("is-active", b.dataset.key === key);
  }
}
