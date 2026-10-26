# SKILLS.md — void-ptt-backend

Agent skills for this repo. Skills are **machine-local tools** (installed to
`~/.agents/skills/`), not source code — they are never committed. Any agent or
new teammate must install them once per machine.

> **Agents (Antigravity, Cursor, Claude Code, Copilot, Junie...)**: if a skill listed
> below is missing, install it before starting work, then continue the task.
> `AGENTS.md` is the authority on *when* each skill applies; `PLAN.md` on *what* to build.

## Install (copy-paste this block)

The skills CLI installs **one package per invocation**, so use this loop:

```bash
for p in \
  langchain-ai/langchain-skills@langchain-rag \
  anthropics/skills@claude-api \
  addyosmani/agent-skills@observability-and-instrumentation \
  supabase/agent-skills@supabase-postgres-best-practices \
  mattpocock/skills@code-review \
  callstackincubator/agent-skills@github-actions \
  openai/skills@gh-fix-ci \
  vercel-labs/skills@find-skills \
; do npx -y skills add "$p" -g -y; done
```

Verify:

```bash
npx skills list -g
```

Update all later:

```bash
npx skills update -g
```

## Backend / AI skills

| Skill | Source | Use when |
|---|---|---|
| `langchain-rag` | langchain-ai/langchain-skills | Building `src/ai/rag/` or `src/knowledge/` — chunking, embeddings, retrieval, reranking |
| `claude-api` | anthropics/skills | LLM provider calls: streaming, structured output, caching, tool use |
| `observability-and-instrumentation` | addyosmani/agent-skills | Anything in `src/observability/`, middleware, metrics, tracing, alerting |
| `supabase-postgres-best-practices` | supabase/agent-skills | Postgres schema design, pgvector, indexes, query performance, migrations |

## Shared process skills

| Skill | Source | Use when |
|---|---|---|
| `code-review` | mattpocock/skills | Before reporting any non-trivial task complete |
| `github-actions` | callstackincubator/agent-skills | Writing or changing `.github/workflows/` |
| `gh-fix-ci` | openai/skills | A CI check failed — diagnose from logs, fix, push |
| `find-skills` | vercel-labs/skills | A task needs a capability not covered here |

## Not required here (frontend-only)

`vercel-react-best-practices`, `vercel-composition-patterns`, `frontend-design`,
`web-design-guidelines`, the three `figma-*` skills, `deploy-to-vercel`, and
`wrangler` live in `../void-ppt-frontend/SKILLS.md`. Install them only if you are
also working on the client.

## Notes

- `claude-api` is installed because it is the best available reference for
  provider-agnostic LLM call patterns (streaming, caching, structured output) even
  though the default provider here is Gemini. Prefer it for API design questions,
  not as a vendor lock-in signal.
- Skills read `SKILL.md` frontmatter to decide relevance, so they cost nothing until
  a matching task appears — install the full set rather than guessing.
