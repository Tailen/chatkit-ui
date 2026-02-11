# AGENTS.md — Agent Guide

## Project Overview

chatkit-ui is an open-source React frontend that implements the ChatKit wire protocol, serving as a drop-in replacement for OpenAI's closed-source chatkit.js Web Component. Compatible with the chatkit-python SDK backend.

Read `docs/brief.md` for full project context, design decisions, and reference file locations.
Read `docs/tasks.md` for the implementation task list.
Read `PLANS.md` for the ExecPlan framework used when implementing tasks.

## Project Structure

```
packages/core/          @chatkit-ui/core — framework-agnostic protocol client, SSE, store
packages/chatkit-ui/    chatkit-ui — React hooks, components, drop-in ChatKit
tools/dev-server/       Python mock backend (FastAPI + chatkit-python) for development testing
tools/playground/       Vite React app for manual testing (proxy /chatkit → dev server)
reference/              Read-only reference implementations (DO NOT MODIFY)
docs/                   Project documentation (brief, tasks)
plans/                  ExecPlan living documents for each task
```

## Development Commands

```bash
pnpm install          # Install all dependencies
pnpm build            # Build all packages (core -> chatkit-ui -> playground)
pnpm test             # Run all tests (vitest from root)
pnpm test:watch       # Run tests in watch mode
pnpm test:coverage    # Run tests with v8 coverage
pnpm lint             # ESLint check
pnpm lint:fix         # ESLint auto-fix
pnpm format:check     # Prettier check (no writes)
pnpm format           # Prettier auto-fix

# Dev server (Python)
cd tools/dev-server && uv sync && uv run python main.py
# -> http://localhost:8000, POST /chatkit

# Playground (needs dev server running)
pnpm dev              # Starts all dev watchers including playground on :5173
```

## ExecPlan Workflow

Before starting any task from `docs/tasks.md`, create an ExecPlan in `plans/` following the template in `PLANS.md`. The ExecPlan is a living document — update it as work progresses with discoveries, decisions, and outcomes.

1. Read the task description in `docs/tasks.md`
2. Read relevant reference files listed in the task
3. Create `plans/{task-id}-{short-name}.md` using the PLANS.md template
4. Fill in Purpose, Context, Plan of Work, Validation & Acceptance
5. Begin implementation, updating Progress as you go
6. Record surprises in Surprises & Discoveries, decisions in Decision Log
7. On completion, fill Outcomes & Retrospective

## Code Conventions

- TypeScript strict mode, ESM only (`"type": "module"`)
- Tailwind v4 + CSS custom properties for styling (packages/chatkit-ui)
- zustand/vanilla for state management (packages/core)
- Tests co-located with source: `foo.ts` -> `foo.test.ts` in the same directory
- Use `describe`/`it` blocks with descriptive names
- Unused variables prefixed with `_` (e.g., `_unused`)
- Single quotes, 2-space indent (enforced by Prettier)

## Testing

- Framework: Vitest (root workspace config runs all packages)
- Tests live next to source files: `src/foo.ts` -> `src/foo.test.ts`
- Run all: `pnpm test`
- Run single package: `pnpm -F @chatkit-ui/core test`
- Coverage: `pnpm test:coverage`

## Verification Checklist

Before considering work complete, run:

1. `pnpm build` — all packages compile
2. `pnpm test` — all tests pass
3. `pnpm lint` — no lint errors
4. `pnpm format:check` — formatting is consistent

## Key Reference Files

| File                                                            | Purpose                          |
| --------------------------------------------------------------- | -------------------------------- |
| `reference/chatkit-python/chatkit/types.py`                     | Protocol types (source of truth) |
| `reference/chatkit-python/chatkit/server.py`                    | Server implementation            |
| `reference/chatkit-python/chatkit/widgets.py`                   | Widget Python types              |
| `reference/chatkit-js/packages/chatkit/types/index.d.ts`        | Config types to replicate        |
| `reference/chatkit-js/packages/chatkit/types/widgets.d.ts`      | Widget types to replicate        |
| `reference/chatkit-js/packages/chatkit-react/src/useChatKit.ts` | React hook API to match          |
| `reference/chatkit-js-bundle/ck1/index-BQ1T8qgK.css`            | Design token reference           |

## What NOT to Do

- Do not modify files under `reference/` — they are read-only
- Do not add HostedApiConfig support — throw at config time
- Do not build iframe/Web Component/postMessage — we render natively in React
- Do not add i18n, dictation, or image generation
- Do not add Chart/CardCarousel/Favicon/CardLinkItem/Map widgets (internal/unreleased)
