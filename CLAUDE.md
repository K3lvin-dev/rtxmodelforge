<!-- PSTERS-WORKFLOW-RULES:START -->
# Psters Workflow Rules (managed block)

Do not edit manually. Re-run `install-workflow-bridge.mjs` to refresh.

## Rule: commits.mdc

# Commit Messages

- **ALWAYS write commit messages in English**
- **ALWAYS put a [TICKET-XXXX] prefix to the commit message** — ASK the user for the ticket number if not provided (e.g. at the start of /pwf-work or before the first commit).
- **During /pwf-work (and /pwf-work-plan):** Follow this rule for every commit; if the user has not given a ticket number, ask once before the first commit (e.g. "Do you have a ticket number [TICKET-XXXX] for this work?").
- Use conventional commit format with emojis when appropriate
- Format: `[TICKET-XXXX] <emoji> <type>(<scope>): <subject>`

## Commit Types

- `🚀 feat`: New feature
- `🐛 fix`: Bug fix
- `📝 docs`: Documentation changes
- `♻️ refactor`: Code refactoring
- `✅ test`: Adding or updating tests
- `⚡ perf`: Performance improvements
- `🔧 chore`: Maintenance tasks
- `🎨 style`: Code style changes (formatting, etc.)
- `🔒 security`: Security fixes
- `🚧 wip`: Work in progress

## Examples

- `[TICKET-1234] 🚀 feat(auth): add JWT authentication`
- `[TICKET-1234] 🐛 fix(api): resolve CORS configuration issue`
- `[TICKET-1234] 📝 docs: update README with deployment instructions`
- `[TICKET-1234] ♻️ refactor(users): improve service structure`
- `[TICKET-1234] ✅ test: add unit tests for auth service`
- `[TICKET-1234] ⚡ perf(database): optimize query performance`

## Guidelines

- Keep subject line under 50 characters when possible
- Use imperative mood ("add" not "added" or "adds")
- First line should be a summary
- Add detailed description in body if needed (separated by blank line)

---

## Rule: context7-documentation.mdc

# Context7 — Library Documentation First

**Always** use the Context7 MCP to fetch up-to-date documentation before implementing features or debugging issues that involve libraries or frameworks.

## How to Use

1. **Resolve library ID:** Call `resolve-library-id` (Context7 MCP server) with `libraryName` and `query`.
2. **Fetch docs:** Call `query-docs` with the resolved `libraryId` and a specific `query`.

## Known Library IDs

- `/nestjs/docs.nestjs.com` — NestJS official docs
- `/nestjs/nest` — NestJS core library

For other libraries, resolve the ID first with `resolve-library-id`.

## When to Use

- Before implementing with NestJS, Angular, TypeORM, or any external library
- When checking decorator usage, DI patterns, or API references
- When debugging framework-specific behavior
- When verifying migration guides or version-specific patterns

---

## Rule: operational-guardrails.mdc

# Operational Guardrails

Use this file as the default source of truth for repeated operational rules.

## Policy hierarchy (who decides what)

1. User explicit instruction in the current chat
2. Project override file (if present): `docs/workflow/operational-overrides.md`
3. This file (`rules/operational-guardrails.mdc`) as default policy

If a project override exists, follow it for project-specific behavior.
If no override exists, use the defaults below.

## Default AWS operations policy (recommended, not forced)

- Run `aws sso login --profile <aws-profile>` before AWS CLI commands when applicable.
- Do not deploy through IAC/CDK unless project-specific rules explicitly allow it.

## Default Lambda deployment policy

- Lambda deployment uses project deployment scripts only.
- Use command `/pwf-aws-lambda-deploy` for guided Lambda deploy flow.

## Completion claims (always required)

- No "done/fixed/passing" claims without fresh verification evidence.
- Include command, exit status, and key output in the completion message.

## Verification evidence format

- `Command:` executed command
- `Result:` exit code/status
- `Evidence:` key output lines
- `Limitation:` partial coverage or constraints (if any)

## TypeORM migration discipline (default)

TypeORM migrations follow this atomic chain:

1. Generate migration (`typeorm:generate`)
2. Drift-check new migration (`schema-drift-detector`)
3. Run migration locally immediately (`typeorm:run`)

If step 3 fails, stop and fix before continuing other tasks.

---

## Rule: agent-namespace.mdc

# Agent Namespace Convention

When referencing plugin agents in prompts, use a fully-qualified namespace:

- `psters-ai-workflow:research:<agent-name>`
- `psters-ai-workflow:review:<agent-name>`
- `psters-ai-workflow:docs:<agent-name>`
- `psters-ai-workflow:workflow:<agent-name>`
- `psters-ai-workflow:design:<agent-name>`

Avoid short names alone when multiple plugins can be loaded.
<!-- PSTERS-WORKFLOW-RULES:END -->
