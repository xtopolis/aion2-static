
## daevanion.mjs

Covers the Daevanion board page. Astro inlines that component's script rather than
emitting a chunk, so this one pulls the inline module out of the built HTML.

Beyond rendering, it asserts the **lazy-loading contract**: a first view fetches exactly
three files (index + one layout + one class), switching board fetches only that layout,
returning to a seen board refetches nothing, and switching class fetches only the
overlay. That contract is the whole reason the payload is split, and nothing else would
catch it regressing.
