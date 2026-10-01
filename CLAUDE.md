# CLAUDE.md

Guidance for Claude Code working in this repository.

<!-- DOC-DOCTRINE v1 begin — identical in all twenty-four repositories; `check:docs` holds them equal. Edit one, sync all. -->
## Where truth lives, and what "update docs" means

Twenty-four repositories carry this project. The engine and the site:
`oceanlet.js`, `oceansensing.github.io` (the site, every fetch script, and
since 2026-09-26 the pipeline's code, `pipeline/`). The observations:
`realtime-data-repo`. And the data
repositories, which since 2026-08-30 split **currents from fields** per model,
and since 2026-09-27 add a **biogeochemistry** repository where a model has
one and an **atmosphere** repository for an atmospheric model:
`espc-model-repo` (the ESPC currents — a legacy name, see below),
`espc-model-fields-repo`, `eccofs-model-currents-repo`,
`eccofs-model-fields-repo`, `mercator-model-currents-repo`,
`mercator-model-fields-repo`, `mercator-model-bgc-repo`,
`cbefs-model-currents-repo`, `cbefs-model-fields-repo`,
`cbefs-model-bgc-repo`, `rtofs-model-currents-repo`,
`rtofs-model-fields-repo`, `gfs-model-atmosphere-repo`, and
`sentinel3-data-repo` (ocean color, which has no vector half to split). And
since 2026-09-27 the University of Delaware ORB lab's satellite products, one
repository per sensor: `orb-satellite-viirs-repo`, `orb-satellite-goes-repo`
and `orb-satellite-pace-repo` (the last set up, publishing nothing until its
upstream is live). And since 2026-09-30 four set up together: `enc-chart-repo`
(NOAA's nautical charts — their land now, a chart layer later),
`river-data-repo` (rivers — USGS's river outlines where no chart reaches and
its water gauges hourly, now; the world's rivers later), and `pace-satellite-repo` and
`viirs-satellite-repo` (satellite products, publishing nothing until their
sources are chosen). Each document answers exactly one question.

**`espc-model-repo` is the ESPC CURRENTS repository** despite its name — the
one exception to the convention, kept because its URL is a live origin and
GitHub Pages does not reliably redirect a renamed project site. Read it and
`eccofs-model-currents-repo` as the same kind of thing.

*(`eccofs-model-repo` was RENAMED to `eccofs-model-fields-repo` on 2026-08-30,
not superseded — GitHub redirects the old name, which is why a rename was
free there and is not free for `espc-model-repo`: that one has published
bytes behind a Pages URL, and Pages does not redirect what the API does.)*

**All twenty-four carry the same four documents, and since 2026-08-31 a gate holds
them to it** — `check:docs` requires a `DECISIONS.md` tracked in git in every
repository. The last two landed that day, the site's and
`realtime-data-repo`'s, reconstructed from records that already existed:
nothing was missing but the file, which is how the site went seven weeks
without one and `realtime-data-repo` eighteen days. **This block asserted
otherwise from the day it was written** — byte-compared in the eight places there were then, and
false in two of them, because a gate on a text is a gate on the text. What it
cost is measurable: the engine promotion's own rehearsal listed *"a dated
entry in this repo's decisions and oceanlet's"* as its ninth step, and the
half with nowhere to go was simply not written.

| file | answers | tense | it is stale when |
| --- | --- | --- | --- |
| `README.md` | what this is, how to run it | present | a reader types a command or trusts a number and is wrong |
| `CLAUDE.md` | what must not be got wrong here | imperative | the next session is about to repeat a mistake |
| `PLAN.md` | what happened, measured, and what is open | dated past | "why is it like this?" has no answer here |
| `DECISIONS.md` | which one-way door closed, and when | dated | a reversal would cost a migration and nothing says so |
| `docs/` | contracts, ledgers and the guide | present | it describes an interface, a divergence or a concept that has moved on |

**`docs/` is a first-class part of "all docs", not an appendix** — the owner
asked for that explicitly on 2026-08-28, and the reason is that these are the
documents everything else points AT. A frozen contract, a divergence ledger
whose rows are pinned by tests, a guide that introduces the model: each is
the thing a reader is sent to when the short answer will not do, so each is
the worst place for a claim that has quietly stopped being true.

**"Update docs" means a sweep of all twenty-four repositories, not the one in hand.**
Docs are part of the change, never a follow-up and never a separate ask. Six
questions, asked of every repository the change touched:

1. Did a command, a path, a script name or a number a reader would type or
   trust move? → `README.md`
2. Did a rule, a trap, or a things-that-must-move-together change or come to
   light? → `CLAUDE.md`
3. Did something *happen* — a measurement, a defect, a yield, a mechanism, an
   open question opened or answered? → `PLAN.md`
4. Did a one-way door close — **or has one already recorded stopped being
   fully true**? → `DECISIONS.md`, in **every** repository the change
   touched. All twenty-four carry one, so this is no longer the
   engine's question with seven exemptions; the amendment half is here
   because two entries needed one within a day of being written.
5. Did an interface, a deliberate divergence, or a concept the guide explains
   move? → the matching file under `docs/`
6. **Does a document in another repository now say something false because of
   this change?** → fix it there, in the same sitting.

**Question 6 is the one that gets missed, and it is why this block is
identical in twenty-four places.** Measured 2026-08-28: one tile-tier measurement
falsified `espc-model-repo`'s README, its `products.toml` header and the
site's README at once. Two were found; the third took a reminder from the
owner, who then asked for this doctrine.

**Two repositories are deliberately NOT in the list above, on opposite
grounds, and both are named because an exclusion nobody wrote down is
indistinguishable from an oversight.**

**A downstream consumer in a private repository** mirrors the site's
published contract. It is not swept by these six questions and does not carry
this block; it has a lighter mechanism instead, a pending list in its own
ledger, and the two repositories whose changes can reach it (the engine and
the site, both private) each name it in their own section. It is noted here
because "four" was read as "all of them" for two weeks while that ledger
drifted 176 commits behind with nothing noticing — question 6 failing at the
granularity of a whole repository rather than a document.

`hab-data-repo` is excluded on the opposite ground: **it does not touch the
ocean map at all** (the owner's call, 2026-08-31). It publishes the bloom
photographs for a different part of the website, reached through `HAB_DATA`
in `src/config.ts`, and carries no interface anything here codes against
beyond a URL and a filename convention. It needs no mechanism, not even a
lighter one — nothing in these twenty-four can falsify a claim in it, and it cannot
falsify one here. Do not mix it in.

Adding a repository to the list above is therefore a real act: it buys the
sweep, and leaving one off **silently** costs exactly what that consumer's
ledger cost.

A number in prose is only as good as its anchor. `check:docs` gates every
claim it can tie to a source constant and nothing else, so when a figure has
no anchor — a measurement, a live reading, a byte count off a build log —
write **where it was measured and when**, or the next reader cannot tell a
fact from a guess that aged.
<!-- DOC-DOCTRINE v1 end -->

## This repository

**The observations origin**: the products `pipeline/products.toml` declares
— storms, platforms, the analyses and the ECMWF fields — fetched on the
schedule in `.github/workflows/publish.yml` and published to
`https://oceansensing.org/realtime-data-repo/map/` (the README has the
layout). The static files CI cannot rebuild live in `map/`.

**The pipeline's code, its design and its decision record moved to the
site's repository on 2026-09-26**: the orchestrator, the R2 publish and their tests are
the site's `pipeline/` folder, private, with the manual that was this file,
the decision record D1–D13 and the running plan beside them. This
repository's history keeps what was here before that day. Every data repository runs the pipeline from its checkout of
the site, which it reads with a read-only deploy key.

**Working here**: a product's declaration is edited here, in
`pipeline/products.toml`; everything about how a run works — the
orchestrator, its tests, what must move together, what has gone wrong
before — is the site's `pipeline/CLAUDE.md`, and a change to it reaches
every origin on its next run. Pushes here carry `[skip ci]`; the workflow
runs on its schedule and by dispatch only.
