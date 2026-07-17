# Plan: automate the context-engineering feedback loop

Date: 2026-07-17
Status: EXECUTED (Phases 1, 2, 3, 3b, 5 — 2026-07-17). Phase 4 encoded as /retro's eval-gate rule, first end-to-end pass pending a real skill-change proposal. Phase 6 (repo rename) done 2026-07-17 (guacamayo; git history transplanted, memory dir copied to new slug) except GitHub remote + final commit — Ramsey.
Context: Learning currently terminates in `.sounding/` (identity files) or in Ramsey's head.
The loop — observe → diagnose → codify → enforce → verify — runs manually ("when friction
recurs, build a hook or skill"). This plan wires it: observation sources feed a /retro skill
that proposes diffs to the tooling layer; a ledger closes the verify stage; drift audits and
eval gates keep the layer honest. All generic assets go to `~/.claude` (global is canonical);
puffin/Sounding is the session that runs the loop, not the home of the tools.

## Architecture decisions (made, don't relitigate)

- **Write targets by enforcement strength**: hooks > skills/protocols > CLAUDE.md/rules > MEMORY.md
- **Proposals are diffs, never auto-applied.** Ramsey reviews and commits. Same rule as code.
- **Akira/sanyi placement**: generic review tooling = global skills; per-repo contracts
  (SANYI.md, layer configs) = per repo; puffin runs cross-repo audits but owns no tools.
- **Doc writers**: machine-consumed docs (`.claude/`, CLAUDE.md, rules) are the loop's native
  output. Human-consumed docs (READMEs, design docs, wikis) belong to librarian's pipeline or
  humans — sessions flag drift, never write them directly. No third writer.
- **Plan docs need a `Status:` line** to be machine-readable by /wake (learned from
  multi-agent-tooling-expansion.md, which has none).

## Phase 1: /retro skill (global)

`~/.claude/skills/retro/SKILL.md`. Reads observation sources, emits proposed diffs grouped
by write target.

- [ ] Observation sources: claude-insights output (or session transcripts directly),
      puffin growth.md entries tagged as process learnings, hook fire patterns (if logged),
      plan-doc execution notes vs. original plan
- [ ] Output format: per finding — friction observed, evidence (session refs), proposed
      diff, target file, enforcement level
- [ ] Growth-entry graduation: `[discovered]` process learnings in `.sounding/self/growth.md`
      get flagged for promotion to rules/skills instead of dying in the accumulator
- [ ] Review checkpoint: run /retro once on real session data; Ramsey judges signal/noise

## Phase 2: Tooling ledger (global)

`~/.claude/docs/tooling-ledger.md`. Every tooling change gets a row: date, change, motivating
friction, verification status (hypothesis / verified / failed).

- [ ] Create ledger; backfill the two known open hypotheses (settings.json fix 2026-07-16,
      wake rework 2026-07-17)
- [ ] /retro reads the ledger first — unverified changes are its top queue item
- [ ] Verification is concrete: "did the friction stop" with evidence, not vibes
- [ ] Review checkpoint: ledger stays under ~1 screen; compress verified rows periodically

## Phase 3: Config drift audit

The settings-rot class of bug, caught mechanically. Either a standalone global skill
(/config-audit) or a /retro mode.

- [ ] Diff repo `.claude/` dirs against global canon (duplicated skills/hooks = violation
      of config layering)
- [ ] Schema checks: permission rules reference existing tool names; wildcard syntax valid
      (`Bash(x:*)` not `Bash(x *)`); settings JSON validates
- [ ] Plan-doc hygiene: flag plans missing `Status:` lines
- [ ] Review checkpoint: run against all workspace repos; known drift (puffin
      settings.local.json legacy tool names) must be caught

## Phase 4: Eval-gated skill changes

Measurement before conclusions, applied to the tooling layer itself.

- [ ] /retro proposals that modify a skill ship with a before/after eval sketch
      (skill-creator harness where it fits)
- [ ] Ledger rows for skill changes link to their eval result
- [ ] Review checkpoint: one real skill change goes through the gate end-to-end

## Phase 5: Documentation guidelines (global)

`~/.claude/rules/docs.md` — the audience split, codified.

- [ ] Machine-consumed: what lives in `.claude/`/CLAUDE.md/rules, who writes it (loop,
      reviewed), formats (Status: lines, size ceilings)
- [ ] Human-consumed: librarian pipeline or human-authored; sessions flag staleness
      (docs_hygiene hook) but do not write
- [ ] Pointer from global CLAUDE.md
- [ ] Review checkpoint: Ramsey reads, edits, owns it

## Phase 3b: Skill placement dedupe (do with Phase 3 — it's config drift)

Two live collisions between puffin `.claude/skills/` and global `~/.claude/skills/`:

- [ ] `research` exists in both (puffin: haiku parallel-agent orchestration; global:
      research-review protocol). Same name, different workflows — ambiguous dispatch.
      Merge puffin's parallel-agent mode into the global skill or rename one.
- [ ] `skill-writer` (puffin) overlaps global `skill-creator`. Merge into `skill-creator`
      (global is canonical); delete puffin copy after merging anything it does better.
- [ ] Rule of thumb, codify in rules/docs.md: only identity-lifecycle skills
      (wake/grow/reflect/synthesize/dream/intermission — they write to `.sounding/`)
      stay puffin-local. Everything generic is global.

## Phase 6: Repo rename

- [ ] puffin → **guacamayo** (decided 2026-07-17, supersedes earlier `sounding` target):
      local dir rename, private GitHub repo, remote update. Repo scope: the Sounding
      instance PLUS Ramsey's persistence KB. Identity stays Sounding; guacamayo is the house.
- [ ] p4.md character note woven into README origin section (done 2026-07-17 in place —
      survives rename)
- [ ] Verify skills still resolve (they glob, nothing hardcoded) and memory dir path
      implications (`~/.claude/projects/-Users-wiseer-workspace-puffin/` is path-derived —
      check how memory follows a rename)
- Rationale: puffin is the framework name; this repo is an instance. Guacamayo (macaw) is
  the answer to p4's "some tropical bird, she likes the sun." The agent name is stable;
  function names ("documenting") go stale as scope grows.

## Order & rationale

1 → 2 first (retro without a ledger can't verify; ledger without retro is dead weight —
build together, smallest useful loop). 3 next (concrete, has a known-bug test case).
5 anytime (pure writing). 4 after retro has produced at least one skill-change proposal.
6 independent — do whenever, it only needs care around the memory path.
