---
name: pwf-work
description: >
  Execute free-form work. Reads existing docs, researches context, derives concrete tasks,
  implements, builds, and updates documentation. For plan-driven work use /pwf-work-plan.
argument-hint: "[description of what to do, e.g. fix X, improve Y, add Z]"
disable-model-invocation: true
---

# Execute Unplanned Work (Fast Path)

Use this command for small fixes, minor adjustments, and focused tasks outside formal plans. For phase execution from `docs/plans/`, use `/pwf-work-plan`.
Apply `skills/using-psters-workflow/SKILL.md` at start.

## Documentation Intent (Read This First)

Documentation in `docs/` is operational memory for future AI and engineers, not a release note.

Every documentation update must help a future implementation answer quickly:

- Where is the source of truth?
- What is implemented now vs only planned?
- Which invariants/rules cannot be broken?
- Which files/methods must change together?
- What are the known gotchas and safe change steps?

Avoid generic text that could apply to any project.

## ⛔ MANDATORY WORKFLOW — NEVER SKIP ANY STEP

You MUST execute steps 1 through 6 IN ORDER. Do NOT jump to implementation.
Your FIRST action must be reading documentation (Step 1), NOT editing code.
If you skip Step 1 or Step 5, the workflow is BROKEN.

---

## Input

<work_description> #$ARGUMENTS </work_description>

If empty, ask: "What would you like me to work on?"

---

## Step 1: Research (BLOCKING — must complete before any code changes)

**Your first tool calls MUST be Read calls to load documentation. Do NOT start implementing.**

Before Step 1 execution details, resolve extension guidance for `before_work`:
- `node ${CURSOR_PLUGIN_ROOT}/scripts/resolve-workflow-extensions.mjs before_work`

1. If the description is vague, ask one or two clarifying questions first.

0. **Classify scope first (trivial vs non-trivial):**
   - Trivial: <=2 files, no entities/migrations/endpoints/auth model changes.
   - If trivial, use lightweight path:
     - read only `docs/solutions/patterns/critical-patterns.md` (if exists) and directly relevant doc,
     - skip mandatory research-agent spawning,
     - keep focused implementation + verification evidence.
   - If non-trivial, follow full workflow below.

2. **Load docs baseline via skill (REQUIRED):**
   - Apply `skills/docs-baseline-loading/SKILL.md`.
   - Read mandatory baseline docs before implementation.
   - Create any missing canonical baseline docs immediately using the skill's required minimum sections.
   - Then read scope-specific docs:
     - `docs/solutions/patterns/critical-patterns.md` (if exists)
     - `docs/modules/<module>.md` (backend scope)
     - `docs/features/<feature>.md` (frontend scope)
     - `docs/lambdas/<repo>.md` (Lambda scope)
     - `docs/runbooks/README.md` (operational/deploy scope)
   - Search `docs/solutions/` by feature keywords for known gotchas.
   - **If any other expected doc file is missing:** create it immediately with a useful baseline (not placeholders). Minimum sections:
     - `Purpose` (business scope)
     - `Source of Truth Files` (exact paths)
     - `Current Implementation Snapshot` (what exists now)
     - `Planned/Upcoming Contract` (only if plan exists; clearly marked as planned)
     - `Invariants and Gotchas`
     - `Safe Change Checklist for Future AI Work`
     - `Related Plan and Docs`

3. **Check existing context:**
   - `docs/brainstorms/` — recent brainstorm for this feature?
   - `docs/plans/` — existing plan? If work belongs to a plan phase, suggest `/pwf-work-plan` instead.

4. **Spawn research agents (REQUIRED for non-trivial scope — use Task tool, `subagent_type: generalPurpose`):**
   - **repo-research-analyst** (`agents/research/repo-research-analyst.md`) — maps file paths, existing patterns, rules, existing enums, migration state
   - **learnings-researcher** (`agents/research/learnings-researcher.md`) — surfaces relevant solutions from `docs/solutions/`

   Spawn both **simultaneously**. Wait for both to complete.
   Use collision-safe agent naming in prompts: `psters-ai-workflow:<category>:<agent-name>`.

5. **Conditional research (spawn in parallel via Task tool if applicable, non-trivial scope):**
   - Entity changes detected → **migration-impact-planner** (`agents/research/migration-impact-planner.md`)
   - Multi-step or UI flows → **spec-flow-analyzer** (`agents/workflow/spec-flow-analyzer.md`)
   - Security, payments, new tech → **best-practices-researcher**, **framework-docs-researcher**

6. **Present research summary to user:** Before implementing, show:
   - Files that will be changed (from research)
   - Relevant patterns/rules found
   - Any gotchas from `docs/solutions/`
   - Ask: "Do you have a ticket number (TICKET-XXXX) for commit messages?"

   Then proceed to Step 2.

---

## Step 2: Task List

1. Derive a **TodoWrite** task list — concrete, dependency-ordered.
   - Each task: **bold name + file path + sub-bullets** with method names, fields, classes.
   - No vague summaries. Every task must specify *what* to change in *which file*.

2. **Self-validate:** Review every task. Does it have a file path? Does it have specific method names or field names? If not, rewrite it.

3. **Debug route detection:** If this work is a bug/failure/regression fix:
   - First validate reproducibility with `bug-reproduction-validator` (`agents/workflow/bug-reproduction-validator.md`) when the report is ambiguous.
   - Then apply `skills/systematic-debugging/SKILL.md` (root-cause -> pattern -> hypothesis -> minimal fix) before implementing broad changes.
   - deep stack/source uncertainty -> `skills/systematic-debugging/root-cause-tracing.md`
   - async timing/flaky behavior -> `skills/systematic-debugging/condition-based-waiting.md`
   - regression hardening after fix -> `skills/systematic-debugging/defense-in-depth.md`

### Built-in capabilities (use as needed during execution):

- **Operational policy source:** `rules/operational-guardrails.mdc`
- **Project overrides (optional):** `docs/workflow/operational-overrides.md` (if present, it overrides defaults from guardrails)
- **Database access:** Load DB vars from `backend/.env` (or project-specific env) for psql queries when applicable. Never display credentials.
- **Context7:** Use the Context7 MCP (`resolve-library-id` then `query-docs`) before implementing with external libraries.

---

## Step 3: Execute

For each task:

- Mark in progress in TodoWrite.
- Read referenced files. Follow project rules and patterns from docs read in Step 1.
- Implement.
- Mark completed in TodoWrite.

### ⚠️ CRITICAL: TypeORM Migration Atomic Chain (when applicable)

Follow the migration chain defined in `rules/operational-guardrails.mdc` (generate -> drift-check -> local run).
Treat this as blocking. Do not continue other tasks until the chain succeeds.

After all tasks:
- **Build** — `npm run build` in every affected repo. Fix ALL errors.

---

## Step 4: Quality Review

**Only run if 5+ files changed or multiple repos touched.** Otherwise skip to Step 5.

If triggered, spawn review agents **in parallel** using the Task tool (`subagent_type: generalPurpose`). For each, tell the subagent to read its agent file and review the implementation.
Use the canonical mapping in `assets/review-agent-selection-mapping.md` to select agents by changed scope.

Address **critical** findings only. Informational findings are noted but don't block.

---

## Step 5: Documentation Maintenance (MANDATORY — never skip)

**This step is MANDATORY even for small changes.**

Apply `skills/docs-maintenance-after-work/SKILL.md` and execute its full flow:
- always run `doc-shepherd`,
- run `plan-sync` when plan context exists,
- run specialized doc writers conditionally,
- run `pattern-extractor` when applicable,
- pass the documentation quality gate before Step 6.

---

## Step 6: Finish

Summarize: what was implemented, files changed, any caveats.

### Verification Evidence (MANDATORY before completion claims)

Before any "done/fixed/passing" claim, apply `skills/verification-before-completion/SKILL.md` and use the evidence format from `rules/operational-guardrails.mdc`.

Include a dedicated **Documentation updates** subsection listing:

- docs files updated/created
- what concrete knowledge was added (source-of-truth files, invariants, checklists, contracts)
- any remaining doc gaps explicitly marked for follow-up

Suggest:
- **Commit** with ticket number
- **`/pwf-review`** for full PR review
- **`/pwf-doc-capture`** if a non-trivial bug was fixed
- **`/pwf-aws-lambda-deploy`** reminder if Lambda repos were touched

Before finalizing, resolve extension guidance for `after_work`:
- `node ${CURSOR_PLUGIN_ROOT}/scripts/resolve-workflow-extensions.mjs after_work`

---

## Conventions

- Follow canonical policy in `rules/operational-guardrails.mdc`.
- Follow commit policy in `rules/commits.mdc`.
- Use optional project overrides in `docs/workflow/operational-overrides.md` when present.

## Next Recommended Commands

- `/pwf-work-light` for future trivial/local-only changes
- `/pwf-review` for a full multi-agent review pass
- `/pwf-commit-changes` after review approval
- `/pwf-doc-capture` when a reusable fix/pattern emerged
- `/pwf-aws-lambda-deploy` when Lambda repos were changed
- apply `skills/finishing-a-development-branch/SKILL.md` when branch/worktree is ready to close
