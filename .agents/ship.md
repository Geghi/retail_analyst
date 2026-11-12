# ship config — opsfleet-task-assignment

## Repo facts

- Base branch: `main` (solo repo, no remote yet)
- Branch naming: `feature/<kebab-slug>`
- Commit convention: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`)
- Commit messages carry the Co-Authored-By line given by the harness.

## Reviewers

| Level | claude |
| ----- | ------ |
| light | sonnet, low |
| standard | sonnet, high |
| deep | disabled |

| Role | Category | Responsibility / scope | Prompt |
| ---- | -------- | ---------------------- | ------ |
| `review-general` | bundled | General review of the diff | `.agents/ship/references/review-general.md` |
| `verifier` | verifier | Runtime verification | `.agents/ship/references/verifier.md` |
| `docs-engineer` | docs | Update repo documentation | `.agents/ship/agents/docs-engineer/docs-engineer.md` |

## Commands

- Install: `pip install -r requirements-dev.txt`
- Lint: `ruff check .` and `ruff format --check .` (fix: `ruff check --fix . && ruff format .`)
- Complexity: `complexipy -f src`
- Test: `pytest tests/unit`
- Test: `pytest tests/integration` — serial, needs `docker compose up -d db`; db down → report "not run"
- Never run automatically: `pytest tests/acceptance -m integration` (live Gemini and BigQuery, costs quota)

## Verify

- `verifiers: 1`. How to run and drive the app: `.agents/verify.md`.

## Never fix

- `golden/` trios: curated content, only the user edits them.
- Per-user product scopes (TBD: file once it exists): authorization decisions are the user's.
- Guardrail logic (SQL validation, PII masking, delete confirmation): report, never auto-fix.

## Ignore patterns

- `.claude/skills/**`, `.agents/ship/**`, `.agents/skills/**`

## Delivery

- No push, no PR. After all gates pass, squash-merge the branch into `main` and delete the branch.
- **Gate:** anything still blocking, or checks failing → do not merge; leave the branch and ask first.
