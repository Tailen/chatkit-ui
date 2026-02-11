# chatkit-ui — Project Brief

## What this is

A fully open-source React frontend that implements the ChatKit wire protocol,
serving as a drop-in replacement for OpenAI's closed-source chatkit.js Web Component.
Compatible with the chatkit-python SDK backend.

## Design principles

1. Drop-in compatible — same import API as @openai/chatkit-react
2. Progressively customizable — three tiers (drop-in → component overrides → headless hooks)
3. Self-hostable — no CDN dependency, no domain allowlist, works air-gapped
4. Protocol-first — core logic is framework-agnostic, React is a layer on top

## Package structure

- `@chatkit-ui/core` — Protocol client, SSE handling, state management (no React)
- `chatkit-ui` — React hooks, components, drop-in ChatKit component (re-exports core)

## Three-tier DX

### Tier 1: Drop-in (matches chatkit.js API exactly)

import { ChatKit, useChatKit } from 'chatkit-ui';
Same ChatKitOptions shape, same behavior.

### Tier 2: Component overrides (shadcn-style whole-component replacement)

<ChatKit control={control} components={{ MessageBubble: MyBubble }} />
Whole-component replacement. Each slot has exported prop types so replacement
components receive the same data. Design tokens (CSS custom properties) are
also customizable for styling without component replacement.

### Tier 3: Headless

  <ChatKitProvider value={chatkit}>
    Use useMessages(), useComposer(), useThread() hooks with complete UI freedom.
  </ChatKitProvider>

## Key implementation details

- Styling: Tailwind v4 + CSS custom properties (design tokens). Tailwind v4 @theme directive consumes CSS vars. Matches the official chatkit.js approach.
- Widgets: JSON → React component renderer, overridable via WidgetRenderer slot
- SSE client: POST-based streaming (not EventSource), with reconnection
- State: zustand/vanilla store in core (framework-agnostic), React hooks subscribe via useSyncExternalStore
- Component registry: Context-based, defaults replaced by user-provided components
- Markdown: remark → rehype → React pipeline, with KaTeX math support ($..$ inline, $$...$$ block)

## Protocol reference

- `reference/chatkit-python/chatkit/types.py` — canonical type reference (987 lines)
- `reference/chatkit-python/chatkit/server.py` — server implementation (937 lines)
- `reference/chatkit-python/chatkit/store.py` — store interface
- `reference/chatkit-python/chatkit/widgets.py` — widget Python types (1192 lines)
- `reference/chatkit-python/chatkit/errors.py` — error types
- `reference/chatkit-python/chatkit/actions.py` — action system
- `reference/chatkit-python/chatkit/icons.py` — icon name enum
- `reference/chatkit-python/tests/helpers/mock_store.py` — SQLiteStore reference implementation
- `reference/chatkit-js/packages/chatkit/types/index.d.ts` — frontend config types to replicate
- `reference/chatkit-js/packages/chatkit/types/widgets.d.ts` — widget types to replicate
- `reference/chatkit-js/packages/chatkit-react/src/useChatKit.ts` — React hook API to match
- `reference/chatkit-js-bundle/ck1/index-BQ1T8qgK.css` — design token reference (362KB, CSS custom properties, Tailwind v4)
- The single POST /chatkit endpoint handles all request types (JSON body with `type` discriminator)

## SSE streaming protocol

- POST-based (NOT browser EventSource API — that only supports GET)
- Wire format: `data: {json}\n\n` per event
- Reconnection: exponential backoff, max 10s, 5 retries, jittered (50-100% of base interval)
- 4xx errors = fatal (immediate failure), other errors = retry
- Stream events: ThreadStreamEvent union — thread.created, thread.updated, thread.item.added, thread.item.updated (text deltas), thread.item.done, thread.item.removed, thread.item.replaced, stream_options, progress_update, error, notice, client_effect

## Request types

### Streaming (produce SSE event streams):

- `threads.create` — create thread + add user message + generate response
- `threads.add_user_message` — append user message to existing thread
- `threads.add_client_tool_output` — provide client tool result
- `threads.retry_after_item` — retry after a specific item
- `threads.custom_action` — execute widget/client action

### Non-streaming (immediate JSON response):

- `threads.get_by_id`, `threads.list`, `threads.update`, `threads.delete`
- `items.list`, `items.feedback`
- `attachments.create`, `attachments.delete`
- `input.transcribe`

## Thread item types

- `user_message` — user input (text content, tags, attachments, quoted text, inference options)
- `assistant_message` — AI response (streaming text with content parts, annotations/citations)
- `client_tool_call` — tool execution request (pending/completed status)
- `widget` — interactive widget (Card, ListView, BasicRoot with nested components)
- `generated_image` — image generation result
- `task` — background task (custom, web_search, thought, file, image)
- `workflow` — multi-step workflow with tasks and summary
- `end_of_turn` — turn completion marker

## How official chatkit.js works (for context)

The official chatkit.js is a Web Component that renders inside an iframe with Shadow DOM.
It uses a postMessage bridge for parent↔iframe communication and a custom event emitter.
State is driven entirely by backend SSE events — there is no client-side state store.
Since chatkit-ui replaces the iframe with native React rendering, we need a client-side
store (zustand/vanilla) to manage state that the official implementation delegates to
the iframe's internal rendering engine.

## Dev backend server

Located at `tools/dev-server/`. A FastAPI server that subclasses ChatKitServer from reference
chatkit-python with an in-memory store and multi-scenario mock responses.

Run: `cd tools/dev-server && uv sync && uv run python main.py` → http://localhost:8000

Mock response keyword triggers:

- Default: echo user message + stream multi-paragraph response with text deltas
- `"widget"` → Card widget with form elements
- `"error"` → ErrorEvent with allow_retry=True
- `"long"` → ~50 sentence streaming response (scroll/performance testing)
- `"tool"` → ClientToolCallItem (client tool flow testing)
- `"workflow"` → WorkflowItem with multiple tasks
- `"notice"` → NoticeEvent (info/warning)
- `"slow"` → 500ms delays between chunks (loading state testing)
- `"annotations"` → Response with URL and file source annotations

## What NOT to build

- No backend/server — that's chatkit-python's job (dev-server is for testing only)
- No managed mode — HostedApiConfig (getClientSecret) throws at config time
- No domain allowlist verification — domainKey accepted for compat but ignored with console.warn
- No iframe/Web Component/postMessage — we render natively in React
- No i18n — English only (start simple, add later)
- No dictation/transcription
- No image generation
- No Chart/CardCarousel/Favicon/CardLinkItem/Map widgets (internal/unreleased types found in bundle)

## Build tooling

- pnpm workspaces monorepo
- Vite + vite-plugin-dts for library builds
- Tailwind v4 (@tailwindcss/vite plugin + @theme directive)
- uv for Python dev-server dependencies
- Vitest for testing (root workspace config)
- ESLint v9 flat config + typescript-eslint + eslint-config-prettier
- Prettier for code formatting
- GitHub Actions CI (build, format, lint, test)

## Project structure (Phase 0 complete)

```
chatkit-ui/
├── package.json              # Root monorepo (pnpm workspaces, type: module)
├── pnpm-workspace.yaml       # Workspaces: packages/*, tools/playground
├── .npmrc                    # shamefully-hoist, no strict peers
├── tsconfig.json             # Root TS config with @chatkit-ui/core path alias
├── .gitignore
├── AGENTS.md                 # Agent guidance — read this first for dev workflow
├── PLANS.md                  # ExecPlan framework — template for task plans
├── eslint.config.js          # ESLint v9 flat config (TS + Prettier)
├── .prettierrc               # Prettier config (single quotes, 2-space indent)
├── .prettierignore           # Prettier ignore (dist, node_modules, reference, css)
├── vitest.config.ts          # Root vitest workspace config with v8 coverage
├── .github/
│   └── workflows/
│       └── ci.yml            # GitHub Actions: build, format, lint, test
├── docs/
│   ├── brief.md              # This file — project context and design decisions
│   └── tasks.md              # Task list for implementation phases 1-6
├── plans/                    # ExecPlan living documents for each task
├── packages/                 # The product — publishable library packages
│   ├── core/                 # @chatkit-ui/core — framework-agnostic
│   │   ├── package.json      # ESM library, peer dep: zustand ^5.0.0
│   │   ├── tsconfig.json     # Extends root, composite: true
│   │   ├── vite.config.ts    # Library mode, rollupTypes: true, external: zustand
│   │   └── src/
│   │       └── index.ts      # Placeholder — export {}
│   └── chatkit-ui/           # chatkit-ui — React layer
│       ├── package.json      # ESM library, dep: @chatkit-ui/core, peers: react
│       ├── tsconfig.json     # Extends root, composite: true, refs core
│       ├── vite.config.ts    # Library mode, rollupTypes: false*, Tailwind plugin
│       └── src/
│           ├── index.ts      # Re-exports core + imports styles.css
│           └── styles.css    # Tailwind v4 @import + @theme design tokens
├── tools/                    # Dev-only infrastructure (not distributed)
│   ├── playground/           # Dev playground — Vite React app
│   │   ├── package.json      # Deps: chatkit-ui (workspace), react 19
│   │   ├── tsconfig.json
│   │   ├── vite.config.ts    # Proxy: /chatkit → localhost:8000
│   │   ├── index.html
│   │   └── src/
│   │       ├── main.tsx      # React root
│   │       ├── App.tsx       # Raw SSE chat UI (replace with ChatKit once built)
│   │       └── styles.css    # Reset styles
│   └── dev-server/           # Python dev backend
│       ├── pyproject.toml    # uv project, depends on openai-chatkit (local ref)
│       ├── main.py           # FastAPI app, POST /chatkit, GET /health
│       ├── server_impl.py    # MockChatKitServer with keyword-triggered scenarios
│       └── memory_store.py   # InMemoryStore (dict-based, cursor pagination)
└── reference/                # Read-only reference implementations
    ├── chatkit-python/       # openai-chatkit SDK (also dev-server dependency)
    ├── chatkit-js/           # chatkit.js source + TypeScript types
    └── chatkit-js-bundle/    # CDN bundles (CSS design tokens kept)
```

\*Note: chatkit-ui uses `rollupTypes: false` because `rollupTypes: true` fails on workspace re-exports (API Extractor can't resolve `@chatkit-ui/core` paths). This is fine — declaration files are still generated, just not rolled up into a single .d.ts.

## How to run (development)

### Dev backend server

```bash
cd tools/dev-server && uv sync && uv run python main.py
# → http://localhost:8000, POST /chatkit
```

### Playground (with dev server running)

```bash
pnpm install && pnpm dev
# playground runs on http://localhost:5173 (or next available port)
# Vite proxy forwards /chatkit → localhost:8000
```

The playground currently uses raw fetch + SSE parsing to talk to the dev server.
Once chatkit-ui components are built, it should switch to:

```tsx
import { ChatKit, useChatKit } from 'chatkit-ui';
const { control } = useChatKit({ api: { url: '/chatkit' } });
return <ChatKit control={control} />;
```

### Build all packages

```bash
pnpm build
# Builds: core → chatkit-ui → playground (in dependency order)
```

### Run tests

```bash
pnpm test             # Run all tests (vitest from root workspace config)
pnpm test:watch       # Watch mode
pnpm test:coverage    # With v8 coverage
```

### Lint & format

```bash
pnpm lint             # ESLint check
pnpm lint:fix         # ESLint auto-fix
pnpm format:check     # Prettier check
pnpm format           # Prettier auto-fix
```

## Verified end-to-end flow

The dev server + playground have been tested together:

1. Dev server starts on :8000, serves SSE streams for all keyword scenarios
2. Playground serves on :5173+, Vite proxy forwards `/chatkit` to dev server
3. `threads.create` produces correct SSE event sequence: thread.created → thread.item.done (user msg) → stream_options → thread.item.added (assistant) → text deltas → thread.item.done
4. `threads.runs.create` works for follow-up messages on existing threads
5. Error scenario produces error event
6. Playground renders streaming text deltas in real-time
