---
title: Key Stats
description: Which stats actually move your damage, what the caps are, and the
  per-class exceptions.
---

Offense is what matters in PvE. The only defensive requirement is not dying in one hit, and
endgame mechanics increasingly deal fixed damage that ignores your defenses anyway.

## Most impactful

Everything worth stacking, best first. Two of these give you **more hits** rather than
bigger ones, which raises your damage just as much but cannot be expressed per percent,
so they read **n/a**.

| Stat | Tier | DPS per 1% <span class="src-mark">c</span> | Reason |
|---|---|---|---|
| <span class="g-heroic">Smite</span> | <span class="g-heroic">**S**</span> | **0.60 – 0.65%** | Doubles the hit, and reaches 0.8% once you are already at 50% smite |
| <span class="g-heroic">Combat Speed</span> | <span class="g-heroic">**S**</span> | **n/a** | More swings per second, so it scales everything else in this table. Take it from every slot that offers it |
| <span class="g-gold">Weapon Damage Boost</span> | <span class="g-gold">**A**</span> | **0.50 – 0.55%** | Multiplies Pure Attack before defense is subtracted |
| <span class="g-gold">Critical Damage Boost</span> | <span class="g-gold">**A**</span> | **0.40 – 0.60%** | Base 50%. The spread is class dependent: the more your damage crits, the higher it sits |
| <span class="g-gold">Cooldown Reduction</span> | <span class="g-gold">**A**</span> | **n/a** | More casts of your best skills. Worth stacking to **33 – 36%**, then it becomes filler |
| <span class="g-legend">Damage Boost</span> | <span class="g-legend">**B**</span> | 0.35% | Every Damage Boost variant lands in one pot that is already at 180 – 200%, so each new point is diluted |
| <span class="g-legend">Multi-Hit</span> | <span class="g-legend">**B**</span> | ~0.33% | 1 – 4 extra hits at 5% each. Good for fast hitters like Sorcerer |
| <span class="g-rare">Attack</span> (per 10) | <span class="g-rare">**C**</span> | 0.17% | The base everything else multiplies |
| Perfect | **D** | 0.10% | Forces a max weapon-range roll plus a hidden ~5% on Pure Attack |

<p class="src-note"><span class="src-mark">c</span> Community tested: one extensively
measured KR source, cross-checked against a second tested TW source. The ordering is
agreed on; the exact percentages are one player's measurements.</p>

**Why the two n/a rows have no number.** Both move in steps rather than smoothly, so a
per-percent rate would be misleading. Combat Speed advances in roughly 3% increments:
points between steps do nothing, and the point that crosses a step is worth the whole
step. Cooldown reduction rounds **up** on short cooldowns, so 1% off a 20 second cooldown
rounds back to 20 seconds and does nothing at all, while the same 1% off a 60 second
cooldown is a real 2 seconds. Neither is less valuable for it.

**Ping cuts into Combat Speed.** 150 – 200 ms costs 50 – 70% of your damage, measured,
across all classes roughly equally.

**Perfect is worth less than it looks.** Most community guides still chase it. Roll it
only where nothing better is on offer.

## Class specific tweaks

The order above is close to class agnostic. The exceptions:

| Class | Callout |
|---|---|
| Assassin | Accuracy is near worthless: back attacks cannot be parried, and that is where an assassin lives. Take every point of cooldown reduction available, since Illusive Clone cannot reach full uptime without it |
| Chanter, Sorcerer | Fast hitters, so Multi-Hit rolls well |
| Cleric | Needs exactly **34%** cooldown reduction for full uptime on Earth Punishment. Condemnation already forces Multi-Hit, so rolling more of it is redundant. The Healing Enhancement passive converts 10% of Attack into healing power, which is why a healer still stacks Attack |
| Gladiator, Templar | No forced Multi-Hit, so rolled Multi-Hit carries its full value |
| Ranger | Deadshot already forces Multi-Hit; take Attack over Multi-Hit rolls |

Elementalist and Brawler have no exception worth calling out yet: follow the general
table above.

Two stats change value with the boss rather than the class. **Multi-Hit's extra hits
ignore the target's defenses** <span class="src-mark">c</span>, so it scales up as bosses
stack damage tolerance late in a tier. **Smite is resisted 30%**
<span class="src-mark">c</span> by bosses from Dying Dramata's Nest onward, so its tier
above is a ceiling on those fights, not a constant.

<p class="src-note"><span class="src-mark">c</span> Both community tested. The client
confirms Multi-Hit adds up to 4 hits and that Smite Resist exists, but gives no damage
share for the extra hits and no boss stat tables, so neither number can be checked
against the data.</p>

## Attack Formula

Per Kanon's bible:

```
[[[(((Pure Attack x Weapon DB) x Multi-Hit x Power Shard) + Attack Bonus)
   x Attack Increase% + PvE Attack + Boss Attack + Species Attack]
  x Skill Coefficient]
 - [(Defense - Penetration) x 0.1]]
x (Damage Boost + PvE DB + Boss DB + Species DB)      <- one additive pot
x Critical DB x Smite x Perfect x Skill Added Damage  <- separate multipliers
```

Everything on the last row is its own multiplicative bucket, so it compounds against
everything you already have. Damage Boost and its variants all share a single additive
pot, so a fresh 1% is 1% of a pot that is already enormous. That single structural
difference is what sets the order above.

Two consequences worth acting on:

- **Attack variants do not get the percentage multipliers.** Critical Attack, Back
  Attack, Front Attack and PvE Attack all sit outside `Attack Increase%`, so plain
  Attack beats them once you own any multipliers at all.
- **Penetration is weak.** In PvE, defense is a flat subtract of 10% of
  (Defense - Penetration), so a point of Penetration removes a tenth of a point of
  damage. Attack is strictly better.

## Soft caps

| Stat | Cap | Measured against | Reached at <span class="src-mark">c</span> |
|---|---|---|---|
| Critical Hit | **80%** | the target's Critical Hit Resist | +1,200 over it |
| Accuracy | **80%** <span class="src-mark">c</span> | the target's Evasion | +1,200 over it |
| Evasion | **50%** | the attacker's Accuracy | — |

<p class="src-note"><span class="src-mark">c</span> Community tested, not stated in the
client. The client gives the 80% Critical Hit cap and the 50% Evasion cap in its own stat
descriptions; it says nothing about an Accuracy cap, and nothing about how many points
reach either one.</p>

Accuracy and Critical Hit are reported to run on one shared curve, roughly 6 to 7% per
100 points of difference, with diminishing returns along the way. That comes from one
tested source and supersedes the older and more widely repeated "10 points = 1%, cap at
800" model.

## Where the points come from

**Base attributes give 0.1% per point.**

| Attribute | Grants |
|---|---|
| Constitution | HP |
| Dexterity | Evasion, Block, Critical Hit Resist |
| Intelligence | Status Effect Chance |
| Might | Attack |
| Precision | Accuracy, Critical Hit |
| Willpower | Status Effect Resist |

**God stats give 0.2% per point**, twice the rate. Only the first of each god's two
effects is usually what you want.

| God stat | Deity | Effects | PvE read |
|---|---|---|---|
| <span class="g-gold">Destruction</span> | Zikel | Attack increase · Perfect Resist | Top pick. Raw <span class="g-rare">Attack</span> |
| <span class="g-gold">Time</span> | Siel | Combat Speed · Smite Resist | Top pick. Combat Speed is S-tier |
| <span class="g-gold">Wisdom</span> | Lumiel | MP cost reduction · Smite | <span class="g-heroic">Smite</span> is the top offensive stat |
| <span class="g-legend">Illusion</span> | Kaisinel | Cooldown reduction · Endurance Penetration | Take early, until you clear 33 – 36% CDR |
| <span class="g-legend">Death</span> | Triniel | Critical Hit increase · Regeneration Penetration | Useful while you are short of the crit cap |
| <span class="g-legend">Freedom</span> | Vaizel | Accuracy · Evasion | Useful while you are short of the accuracy cap |
| <span class="g-rare">Justice</span> | Nezekan | Defense · Perfect Chance | Both halves are low value in PvE |
| <span class="g-rare">Life</span> | Yustiel | HP · Regeneration chance | Survival only |
| <span class="g-rare">Space</span> | Israphel | Move Speed · Block | Quality of life |
| <span class="g-rare">Destiny</span> | Marchutan | MP · Endurance | Lowest value |

The practical ordering for bracelets, which always roll god stats, is
<span class="g-gold">**Destruction**</span> > <span class="g-gold">**Wisdom**</span> > <span class="g-legend">**Illusion**</span> > <span class="g-gold">**Time**</span>, with Freedom and Death as cap fillers and
Justice replacing them once you are capped.

Where these stats come from in practice: [Soul Binding](/gear-enhancement/soul-binding/)
rolls them per slot, [manastones](/gear-enhancement/manastones/) add them to weapons and
armor, and [enhance and exceed](/gear-enhancement/enhancing/) raise the base the
multipliers work on.

**Not live at Global launch:** Front/Back Attack Damage Boost sits second on the KR
order at 0.57 – 0.65% and has its own multiplicative bucket, which is why ranged
classes stack it there too. It arrives with the level 50 chapter. Ignore it until then.
