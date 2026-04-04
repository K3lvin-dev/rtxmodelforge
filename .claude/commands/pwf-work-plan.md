---
name: pwf-work-plan
description: >
  Execute a plan phase from docs/plans/. Reads existing docs first, executes tasks directly from the plan,
  builds, then updates documentation. No intermediate planning. No tests.
argument-hint: "[path to plan file] [optional: Phase N]"
disable-model-invocation: true
---

# Step 3 — Execute One Planned Phase

Use this command to execute one phase from `docs/plans/` with full discipline: read docs first, implement, build, and update docs.
Apply `skills/using-psters-workflow/SKILL.md` at start.

## Documentation Intent (Read This First)

Docs updated during `/pwf-work-plan` must become reliable implementation memory for future phases and future AI runs.

Do not write generic summaries. Document:

- what is already implemented in code after this phase,
- what remains planned in later phases,
- where to edit safely next time,
- and which constraints must not be violated.

## ⛔ MANDATORY WORKFLOW — NEVER SKIP ANY STEP

You MUST execute steps 1 through 5 IN ORDER. Do NOT jump to implementation.
Your FIRST action must be reading the plan file and documentation (Step 1), NOT editing code.
If you skip Step 1 or Step 4, the workflow is BROKEN.

---

## Input

<plan_input> #$ARGUMENTS </pwf-plan_input>

If empty or not pointing to a plan file, ask: "Which plan file? (e.g. `docs/plans/20260312-feat-xyz-plan.md`)"

---

## Step 1: Load Context (BLOCKING — must complete before any code changes)

**Your first tool calls MUST be Read calls. Do NOT start implementing.**

Before Step 1 execution details, resolve extension guidance for `before_work_plan`:
- `node ${CURSOR_PLUGIN_ROOT}/scripts/resolve-workflow-extensions.mjs before_work_plan`

1. **Read the plan file** fully.
   - Validate task format in target phase:
     - `- [ ] T### [P?] [USx?] Description with file path`
   - If format is inconsistent, normalize the phase task list before execution (or ask user to run `/pwf-plan` refinement).

2. **Identify the target phase** — first ⬜ Pending phase, or the one specified by the user. If the argument names a phase number (e.g. "Phase 2"), start at that phase.

3. **Load docs baseline via skill (REQUIRED):**
   - Apply `skills/docs-baseline-loading/SKILL.md`.
   - Read mandatory baseline docs before implementation.
   - Create missing canonical baseline docs immediately using the skill's required minimum sections.
   - Then read phase-specific docs:
     - `docs/solutions/patterns/critical-patterns.md` (if exists)
     - `docs/modules/<module>.md` (backend scope)
     - `docs/features/<feature>.md` (frontend scope)
     - `docs/lambdas/<repo>.md` (Lambda scope)
     - `docs/runbooks/README.md` (operational/deploy scope)
     - relevant `docs/solutions/` entries by feature keywords
   - **If any other expected doc file is missing:** create it immediately with a useful baseline. Minimum sections:
     - `Purpose`
     - `Source of Truth Files`
     - `Current Implementation Snapshot`
     - `Phase Scope (Current Plan)` with explicit `planned` markers
     - `Invariants and Gotchas`
     - `Safe Change Checklist for Future AI Work`
     - `Related Plan and Docs`

4. **Present summary to user:** Phase name, objective, task count. Get confirmation to proceed.

5. **Ticket number:** If not in plan frontmatter, ask once: "Do you have a ticket number (TICKET-XXXX) for commit messages?"

6. **Create TodoWrite** task list directly from the plan phase task IDs (T001, T002...) in dependency order.
   - Preserve `[P]` markers as parallel opportunities.
   - Preserve `[USx]` labels for traceability in status updates.
   - If user explicitly requested TDD and plan contains test-first tasks, preserve red-green-refactor order.

### Definition of Ready (BLOCKING)

Before Step 2, confirm all are true:

1. Critical ambiguities resolved (or explicitly marked with `[NEEDS CLARIFICATION]`).
2. Tasks have IDs + file paths and executable scope.
3. Acceptance criteria are measurable for this phase.
4. Main risks/dependencies are explicit.
5. Required docs/pattern references were loaded.

---

## Step 2: Execute

For each task in the phase:

- Mark in progress in TodoWrite.
- Read the referenced files. Follow project rules and existing patterns from docs read in Step 1.
- Implement the task.
- Mark task completed in TodoWrite.

If a task is primarily bug/debug oriented, follow `skills/systematic-debugging/SKILL.md` before attempting larger fixes.
Playbook mapping:
- deep stack/source uncertainty -> `skills/systematic-debugging/root-cause-tracing.md`
- async timing/flaky behavior -> `skills/systematic-debugging/condition-based-waiting.md`
- regression hardening after fix -> `skills/systematic-debugging/defense-in-depth.md`

If user explicitly requested TDD for this phase, apply `skills/test-driven-development/SKILL.md` for relevant tasks only.

### ⚠️ CRITICAL: TypeORM Migration Atomic Chain (when applicable)

Follow the migration chain defined in `rules/operational-guardrails.mdc` (generate -> drift-check -> local run).
Treat this as blocking. Do not continue other tasks until the chain succeeds.

### Built-in capabilities (use as needed during execution):

- **Operational policy source:** `rules/operational-guardrails.mdc`
- **Project overrides (optional):** `docs/workflow/operational-overrides.md` (if present, it overrides defaults from guardrails)
- **Database access:** Load DB vars from `backend/.env` (or project-specific env) for psql queries when applicable. Never display credentials.
- **Context7:** Use the Context7 MCP (`resolve-library-id` then `query-docs`) before implementing with external libraries.

### After all tasks:

1. **Build** — `npm run build` in every affected repo. Fix ALL errors before continuing.
2. **Update plan file:**
   - Mark the phase as `✅ Completed` in the Implementation Plan table.
   - In the `## ✅ Master Checklist`, mark each completed task: `- [ ]` → `- [x]`.

---

## Step 3: Quality Review

**Only run if the phase changed 5+ files or touched multiple repos.** Otherwise skip to Step 4.

If triggered, spawn review agents **in parallel** using the Task tool (`subagent_type: generalPurpose`). For each, tell the subagent to read its agent file and review the implementation.
Use collision-safe agent naming in prompts: `psters-ai-workflow:<category>:<agent-name>`.
Use the canonical mapping in `assets/review-agent-selection-mapping.md` to select agents by changed scope.

Address **critical** findings before finishing. Informational findings are noted but don't block.

---

## Step 4: Documentation Maintenance (MANDATORY — never skip)

**This step is MANDATORY even for small changes.**

Apply `skills/docs-maintenance-after-work/SKILL.md` and execute its full flow:
- always run `doc-shepherd`,
- run `plan-sync` for plan/work-plan synchronization,
- run specialized doc writers conditionally,
- run `pattern-extractor` when applicable,
- pass the documentation quality gate before Step 5.

---

## Step 5: Finish

Summarize: what was implemented, files changed, any deferred items.

### Verification Evidence (MANDATORY before completion claims)

Before claiming phase completion/fix success, apply `skills/verification-before-completion/SKILL.md` and use the evidence format from `rules/operational-guardrails.mdc`.

Include a dedicated **Documentation updates** subsection:

- docs files updated/created
- what high-value operational knowledge was added
- checklist/phase sync status
- any explicit doc debt left for next phase

Suggest next steps:
- **Next phase** → continue with `/pwf-work-plan [same plan path] Phase N+1`
- **Commit** with ticket number
- **`/pwf-review`** for full PR review (if all phases done or before merge)
- **`/pwf-doc-capture`** if a non-trivial bug was fixed during the phase
- **`/pwf-aws-lambda-deploy`** reminder if Lambda repos were touched
- **`/pwf-analyze [same plan path]`** if inconsistencies emerge during execution
- apply `skills/finishing-a-development-branch/SKILL.md` when phase/branch work is fully complete

Before finalizing, resolve extension guidance for `after_work_plan`:
- `node ${CURSOR_PLUGIN_ROOT}/scripts/resolve-workflow-extensions.mjs after_work_plan`

---

## Conventions

- Follow canonical policy in `rules/operational-guardrails.mdc`.
- Follow commit policy in `rules/commits.mdc`.
- Use optional project overrides in `docs/workflow/operational-overrides.md` when present.
