# ProjectForge Product Audit — July 2026

**Scope:** Full-project review from a customer, product, business, and user-experience
perspective — not a code-correctness review.
**Version audited:** v0.5.0 plus the uncommitted Antigravity migration on `main`.
**Method:** Read the full user-facing surface (README, guides, help text), read the interactive
flow and setup code, ran `forge --dry-run`, `forge doctor`, `forge stats`, and `forge --help`
on this machine, and inspected the real `~/.forge/` state a user accumulates.

---

## Verdict in one paragraph

ProjectForge is a genuinely differentiated idea executed with unusual engineering discipline:
"conventions in, verified project out, with an audit trail" is a pitch no mainstream scaffolder
makes. The terminal craft, safety posture, and documentation honesty are portfolio-grade.
But the product currently optimizes for the auditor, not the customer: the funnel to first value
is long (Python 3.12 + uv/brew + a separately installed and authenticated AI CLI), the README
sells rigor before outcome, cost and time are opaque at the moment of commitment, and the
feedback surfaces a user actually sees (`forge stats`, `forge doctor`) are undermined by a real
data-hygiene bug — the test suite writes into the live `~/.forge/` and can skew real routing
decisions. Fix the trust-surface bugs, shorten time-to-first-scaffold, and decide who the
customer actually is before building more features.

---

## The Good

### 1. A real, defensible value proposition
Every competitor (create-next-app, cookiecutter, copier, or just typing a prompt into Claude
Code) produces *files*. Forge produces *evidence*: `.forge/scaffold.json` provenance,
convention hashes, `verification.json`, and the honest distinction between **Project Ready**
(verification passed) and **Project Created** (it didn't run). For an agency or consultancy
handing projects to clients, that delivery-evidence story is the moat. Nobody else has it.

### 2. Terminal UX craft is top-tier
- Cold start is ~0.26s — instant for a Python CLI.
- Branded logo, coherent Rich panels, a review-and-edit screen before any provider call,
  smart defaults after repeated scaffolds, phase timeline, activity feed, post-scaffold
  dashboard, completion sound. This looks and feels like a commercial product, not a script.
- The questionnaire's edit-loop review screen ("Edit basics / Edit design and media / ...") is
  better UX than most funded CLI products ship.

### 3. Safety and privacy as product features, not disclaimers
Safe-by-default execution, a *two-flag* gate for unsafe mode (`--approval-mode unsafe
--allow-unsafe`), secrets scanning of extra instructions, credential-free `forge doctor`,
zero-call `--dry-run`. The security-privacy guide plainly states what leaves the machine.
This is a trust asset most AI tooling lacks — keep it.

### 4. Failure recovery respects the user's money
`--resume` with contract validation, a failure taxonomy with classified remediation, and
"preserve the partial output, don't blindly rerun" guidance all acknowledge that provider
calls cost real quota. That empathy is rare and worth advertising.

### 5. Documentation discipline
Keep-a-Changelog, a real migration guide, CI-enforced link checking and safety scanning,
honest phrasing everywhere ("Preview does not prove provider readiness"). Maintainer docs
(production-readiness plan/evidence, provider compatibility) show working-in-the-open rigor.

---

## The Bad

### 1. The funnel to first value is brutal
To get one scaffold, a new user must: have Python 3.12+, install uv or use a Homebrew tap,
install from a GitHub tarball URL (not PyPI, not `pipx install projectforge`), then separately
install *and authenticate* Claude Code, Codex, or Antigravity, then run `forge doctor`, then
scaffold. Each step sheds users. There is no demo GIF or screenshot in the README, so the
excellent terminal UX — the strongest first impression the product has — is invisible until
after all that friction. The showcase material exists (`docs/showcase/terminal-demo.sh`,
shot list) but was never turned into an asset the README shows.

### 2. The README sells rigor before outcome
The opening is accurate but engineer-brained: "bounded provider workspace modes",
"convention provenance", "separates provider finished from generated project verified" — all
in the first paragraph. The customer's question is "what do I get and how fast?" The current
copy answers "how carefully was this built?" Great for auditors and hiring managers, weak for
adoption. The same tone runs through the guides; they read like compliance documents.

### 3. Cost and time are opaque exactly when the user commits
The preflight panel warns of "possible provider quota or billing" and a "qualified duration
range", but never a number: how many provider calls, roughly how many tokens, roughly what
that costs on a typical plan, how long the last similar scaffold took on this machine (data
that exists in `~/.forge/`). Fear of unbounded spend is the #1 objection to agentic tools;
Forge has the data to answer it and doesn't.

### 4. Identity fragmentation
ProjectForge now aligns the product, command, formula, and Python namespace around
**projectforge**, but the PyPI distribution remains **matt-projectforge** and the short **forge**
alias remains available. The alias collides with Foundry's `forge`, one of the most installed tools
in the Ethereum ecosystem. Keep `projectforge` canonical and document the alias collision.

### 5. Prompt quality: phase prompts are not stack-aware
The dry run for a **FastAPI-only** project produced a Verify & Fix prompt full of Next.js
frontend instructions — Clerk, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, "do not change the
project's visual design", auth-provider bypass banners. That's wasted tokens on every backend
scaffold and a live risk of the model inventing frontend artifacts in an API project. The
"specialist prompt variants" system exists per backend; it needs to specialize per *stack* too.

### 6. Mixed signals in the interactive flow
The execution-mode prompt labels multi-agent "**(recommended)**: higher quality" while the
default selection is Standard ([prompts.py:370](../../src/projectforge/prompts.py)). Either
it's recommended — then default to it — or it isn't; recommending one thing and defaulting to
another erodes trust in every other default. The full question flow is also long (up to ~12
decisions before the review screen); smart defaults only kick in after 3+ scaffolds, which is
exactly the population that no longer needs help.

### 7. Evidence noise leaks into user-facing surfaces
Eleven full SHA-256 lines dominate the Scaffold Context panel on every run. Hashes are
evidence, and evidence already has a home (`.forge/scaffold.json`, `--verbose`). The default
panel should say "12 convention sources, 9.8k chars (hashes recorded)" and get out of the way.

---

## The Ugly

### 1. The test suite corrupts real user data — and real routing decisions
All 187 entries in this machine's `~/.forge/scaffold.log` are pytest temp-dir runs
("mocked-flow", "guided-first-run"), and `~/.forge/quality.jsonl` holds 980 synthetic entries
("Task A"/"Task B", 0.1s durations). Consequences:

- `forge stats` proudly reports **"187 scaffolds — 0% success rate"** — a self-own dashboard
  built entirely from garbage data.
- Quality-based routing consumes `quality.jsonl` and, per its own design, overrides backend
  selection at a >0.1 margin with as few as 8 data points. **Running the test suite can change
  which AI backend real scaffolds route to.** This crosses from cosmetic to
  behavior-corrupting.

There is no `FORGE_HOME`-style override and no autouse fixture isolating `~/.forge` in tests.
This is the single highest-priority fix in the repo.

### 2. The product's own analytics can't prove the product works
Zero recorded successful scaffolds on the maintainer's machine (every entry is synthetic).
Either real dogfooding isn't happening, or success signals aren't being recorded on real runs —
both are bad, and the polluted log makes it impossible to tell which. A product whose core
pitch is *verified evidence* cannot have an evidence store this untrustworthy.

### 3. Doctor's rough edges undermine its "trust me" role
`forge doctor` is the product's credibility surface, and on this machine it reports
"Editors: none found" (on a developer workstation) and `codex: check_inconclusive` with the
generic remediation "Recheck the provider-owned login flow" — which doesn't say what was
checked, what was inconclusive, or what specifically to do. The one command whose whole job is
diagnosis shouldn't shrug.

### 4. The provider treadmill is an existential business risk
The current uncommitted change deletes the entire Gemini backend and replaces it with
Antigravity across 40+ files — adapter, preflight, docs, prompts, tests. That's the second
provider migration in the project's short life. Forge's foundation is three fast-moving,
third-party CLIs it doesn't control, maintained by one person. Every provider flag rename,
auth change, or deprecation lands on this repo's plate. This doesn't invalidate the product,
but it caps how much surface one maintainer can afford: every new feature is a future
migration liability.

---

## Product-worthiness and business assessment

**Who is the customer?** The feature set answers three different people at once:
solo developer (speed, smart defaults, sounds, cards), team/org (conventions, drift checks,
audit evidence), and Forge's own maintainer (replay, showcase, maintainer docs). The moat —
conventions + verification + provenance — is a **team/agency delivery** story, but the
team features that would monetize it (shared conventions via git, convention locking, policy
packs, standard bundles) are all still roadmap items. Right now Forge is a solo tool wearing
an enterprise trust posture.

**Market reality.** The free alternative is not cookiecutter — it's typing "scaffold me a
FastAPI project following these conventions" into Claude Code directly. Forge's honest answer
to "why not just do that?" is: deterministic convention layering, phase routing across
providers, resume without re-spend, and verified evidence. That's a real answer, but it must
be *shown* (demo, before/after, a failed-verification story) rather than asserted.

**Monetization.** As an MIT CLI wrapping other companies' paid CLIs, the value accrues to the
providers. Realistic near-term value: (a) delivery-team leverage through consistent project starts
with evidence; (b) credibility as a production-grade agent-tooling product; and (c) a wedge to
validate whether "scaffold evidence for client delivery" is a paid team product. Gate investment
in team features on 3–5 external users actually adopting it.

**Feedback loop.** The no-telemetry stance is a genuine privacy differentiator, but it means
zero signal about real usage. Cheapest fix: a visible "was this scaffold good? (y/n)" prompt
feeding the *local* quality log (improving routing), plus a GitHub issue funnel; consider an
explicitly opt-in anonymous version ping later.

---

## What should change, and how

### P0 — trust-surface fixes (do before anything else)

1. **Isolate tests from `~/.forge`.** Add a `FORGE_HOME` (or `FORGE_DIR`) environment override
   consumed wherever `FORGE_DIR` is defined, and an autouse pytest fixture in `tests/conftest.py`
   pointing it at `tmp_path`. Ship a one-time cleanup: `forge stats --repair` (or a doctor
   check) that quarantines entries whose `directory` is under a pytest temp path from
   `scaffold.log` and `quality.jsonl`.
2. **Make phase prompts stack-aware.** In `prompt_builder.py`, branch the Verify & Fix (and
   frontend-flavored) instructions on stack family: no Clerk/Next.js content for
   `fastapi`/`python-cli`/`python-worker`/`ts-package` scaffolds.
3. **Fix the stats empty/garbage state.** With no real scaffolds, `forge stats` should say
   "No scaffolds recorded yet — run `forge` to create your first" instead of "0% success rate".
   Verify success signals are actually recorded on real successful runs.
4. **Show, don't tell, in the README.** Record the existing terminal demo
   (`docs/showcase/terminal-demo.sh`) as a GIF/SVG cast, put it at the top of the README, and
   rewrite the first three paragraphs outcome-first: what you type, what you get, how long it
   takes. Move the rigor language to a "Why trust the output" section — it's a strength, just
   not the headline.

### P1 — funnel and commitment moment

5. **Cut install friction.** Publish to PyPI (the "optional future channel" should be now) so
   `uv tool install projectforge` / `pipx install projectforge` works without a tarball URL.
   Keep the Homebrew tap.
6. **Put numbers in the preflight panel.** Provider call count is already known; add measured
   duration from local history ("last fastapi scaffold: 6m 40s") and an order-of-magnitude
   cost/quota statement per provider. Uncertainty stated with numbers beats vague warnings.
7. **Resolve the recommended-vs-default contradiction** in the execution-mode prompt, and
   collapse the hash block in Scaffold Context to a one-line summary (full hashes behind
   `--verbose` and in the manifest).
8. **Upgrade doctor messages.** Every non-`ready` status should state what command was run,
   what was observed, and one concrete next step. Fix or soften editor detection ("no editor
   CLI on PATH — set one with `forge --setup`").
9. **Address the `forge` name collision** (Foundry). Either document it prominently with an
   alias (`projectforge` as a second entry point costs nothing), or bite the bullet on a
   rename while the user base is small. Also converge the public naming story: one name in
   README, formula, package, and UI.

### P2 — product direction (decide, then build)

10. **Pick the customer.** If the answer is "maintainer portfolio + internal delivery": stop
    expanding stacks, harden the three that get used, and invest in the showcase. If the answer is
    "teams/agencies": prioritize shared conventions via git, convention locking, and standard
    packs — the roadmap items that make the moat real — and find 3–5 external design partners
    before writing code.
11. **Shorten repeat-use flow.** `--preset`/`--save-preset` and `forge --last` (both already
    on the roadmap) are the highest-leverage interactive improvements; smart defaults help
    the wrong cohort.
12. **Contain the provider treadmill.** Keep the adapter surface as thin as possible, add a
    compatibility smoke matrix in CI per provider version, and write down a support policy
    ("current major version of each provider CLI only") so migrations like Gemini→Antigravity
    are scheduled work, not fire drills.
13. **Add a local feedback signal.** Post-scaffold "good result? (y/n)" written to the quality
    log closes the routing loop with real data — the feature quality-based routing was built
    for but has never actually received.

---

## Scorecard

| Dimension | Grade | One-line reason |
| --- | --- | --- |
| Value proposition | A- | Verified-evidence scaffolding is genuinely differentiated; needs to be shown, not asserted |
| Terminal UX craft | A | Commercial-grade polish, fast startup, best-in-class review flow |
| Onboarding funnel | D+ | GitHub-tarball install + separate provider auth + no visual demo |
| Trust surfaces (doctor/stats) | C- | Undermined by test-data pollution and vague diagnostics |
| Cost/time transparency | C | Warns about spend, never quantifies it |
| Docs quality | A- | Honest and rigorous, but compliance-toned for newcomers |
| Safety/privacy posture | A | Safe-by-default, two-flag unsafe gate, credential-free checks |
| Business clarity | C | Customer undecided; moat features (team sharing) still on the roadmap |
| Maintainability risk | C+ | Three third-party CLI dependencies, one maintainer, second provider migration underway |

**Bottom line:** this is a product-worthy foundation with two must-fix credibility bugs
(test pollution of live data, non-stack-aware prompts) and one strategic decision pending
(who it's for). The engineering is ahead of the packaging; close that gap before adding
anything new.
