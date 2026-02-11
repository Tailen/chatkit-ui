# PLANS.md — ExecPlan Framework

## What are ExecPlans?

ExecPlans are self-contained living design documents that enable an agent to implement a feature or task end-to-end without prior repository knowledge. They evolve as work progresses, capturing discoveries, decisions, and outcomes alongside the implementation plan.

## When to Create One

Before starting any task from `docs/tasks.md`, create an ExecPlan. The plan serves as both a pre-implementation design document and a post-implementation record.

## Where They Live

Plans live in the `plans/` directory, named by task ID:

```
plans/1.1-protocol-types.md
plans/1.2-config-types.md
plans/2.1-provider-context.md
```

## Writing Principles

- **Observable outcomes over internal attributes**: Prefer "running `pnpm build` produces no errors" over "added correct TypeScript types"
- **Self-contained**: Include all file paths, reference locations, and context needed. A reader should not need to search the repo to understand the plan.
- **Define specialized terms**: If you use a term like "SSE" or "zustand store", define it in context on first use.
- **Living document**: Update Progress, Surprises, and Decision Log as work happens — not after the fact.

## Template

Copy this template when creating a new ExecPlan:

---

# ExecPlan: Task {id} — {title}

## Purpose

What this task achieves and why it matters. Describe the observable outcome — what will a developer or user see when this is done?

## Context

Current repository state relevant to this task:

- What exists already (files, packages, patterns)
- Reference files to consult (with paths)
- Dependencies on prior tasks
- Key design decisions from `docs/brief.md` that affect this work

## Plan of Work

Concrete sequence of changes:

1. **Create `packages/core/src/types/foo.ts`** — Description of what goes in this file
2. **Modify `packages/core/src/index.ts`** — Add exports for new types
3. ...

For each step, include:

- The file path
- What to add, modify, or remove
- Why (if not obvious from context)

## Validation & Acceptance

Behavior-based criteria. Each criterion should be a command you can run or an observable outcome:

- [ ] `pnpm build` completes with no errors
- [ ] `pnpm test` — all new tests pass
- [ ] Types match the shapes in `reference/chatkit-python/chatkit/types.py`
- [ ] Importing `{ Foo }` from `@chatkit-ui/core` compiles without errors

## Progress

Update this section as you work. Timestamp each entry.

- [ ] Step 1 description
- [ ] Step 2 description
- [ ] ...

## Surprises & Discoveries

Record unexpected findings here with evidence (error messages, file contents, etc.)

_None yet._

## Decision Log

Record decisions with rationale.

| Date | Decision | Rationale |
| ---- | -------- | --------- |
|      |          |           |

## Outcomes & Retrospective

_Fill this section when the task is complete._

**What was built:**

**What went well:**

**What was surprising or difficult:**

**Lessons for future tasks:**

---
