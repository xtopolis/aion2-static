
## daevanion.mjs

Covers the Daevanion board page. Astro inlines that component's script rather than
emitting a chunk, so this one pulls the inline module out of the built HTML.

Beyond rendering, it asserts the **lazy-loading contract**: a first view fetches exactly
three files (index + one layout + one class), switching board fetches only that layout,
returning to a seen board refetches nothing, and switching class fetches only the
overlay. That contract is the whole reason the payload is split, and nothing else would
catch it regressing.

## crafting.mjs

Covers the recipe browser: rendering, row expansion with material sourcing, the proc
maths, filters, and that only one faction's recipes are fetched at a time.

The crafting suite also stubs `activeElement` and `focus`/`blur`, which linkedom does not
implement — they are what let it assert that typing in the craft-quantity box never
detaches the input.

Both suites stub `location` and `history`, which linkedom does not provide, with a small
working pair — so the URL-state code runs for real and the tests can assert what lands in
the query string, including restoring a shared link on a fresh mount.
