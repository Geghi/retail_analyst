# Workflow rules

How to work in this repo. Linked from [CLAUDE.md](../../CLAUDE.md).

- **Dev server** — never run it without asking first.
- **Git stash** — always named: `git stash push -u -m "<name>"` /
  `git stash pop "stash^{/<name>}"`. Never bare stash/pop.
- **Docs hygiene** — delete it in the code, delete it in the docs: no doc names a
  symbol, file or route that no longer exists. Only `docs/adr/` and `docs/prd/`
  keep history.
- **Prose docs** — one sentence per line (`CONTEXT.md`, map cards, `docs/agents/`), so parallel branches rebase without conflicts.
- **Stale deps** — the post-checkout / post-rewrite hook re-runs the install when a lockfile changed; after a rebase never "fix" a gate failure by hand before it has run.

## Layout

```
src/retail_analyst/  agent package; each folder is a module, imported through its __init__.py only
golden/              synthetic Golden Knowledge trios (question, SQL, report)
config/              users and product scopes, persona text (editable without redeploy)
tests/               unit, integration, acceptance
docs/                HLD, architecture diagram, assumptions, ADRs, PRDs, agent docs
scripts/             sync-deps.sh
.scratch/            task files: todo, in-progress, done
```

- **Env vars** — copy `.env.example` to a local env file yourself; agents never read it.
- **Live services** — Gemini and BigQuery calls cost quota; run acceptance tests only when asked.
- **Tasks** — track work in `.scratch/` as described in [issue-tracker.md](issue-tracker.md).
- **CI** — no CI workflow yet; when one is added it runs on PRs only when the `run-ci` label is added.
