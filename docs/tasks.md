# chatkit-ui — Implementation Tasks

Each task is self-contained for one agent session. Work in order — later tasks depend on earlier ones.
Read `docs/brief.md` for full project context, design decisions, and reference file locations.
Add markdown documentations to the docs/ directory as decisions are made and features are implemented.

## Phase 1: Core Protocol Layer (`@chatkit-ui/core`)

### Task 1.1 — Define TypeScript protocol types

- Mirror chatkit-python `types.py` as TypeScript types in `packages/core/src/types/`
- Request types (ChatKitReq, all streaming + non-streaming request variants)
- Response types (ThreadStreamEvent union, all event types)
- Thread item types (UserMessageItem, AssistantMessageItem, WidgetItem, etc.)
- Thread item update types (text delta, content part added, widget updates, etc.)
- Thread and ThreadMetadata types
- Source and annotation types
- Verification: Types compile, match the shapes in `reference/chatkit-python/chatkit/types.py`

### Task 1.2 — Define config types

- Mirror `reference/chatkit-js/packages/chatkit/types/index.d.ts` for ChatKitOptions
- CustomApiConfig (our only supported API config)
- HostedApiConfig type (exists for compat, throws at validation)
- All option types: HeaderOption, HistoryOption, StartScreenOption, ComposerOption, etc.
- ThemeOption, ColorScheme, typography, color types
- Widget types from `widgets.d.ts`
- ChatKitEvents map
- Verification: Types compile, a test ChatKitOptions object type-checks

### Task 1.3 — Implement SSE client

- POST-based SSE client (NOT browser EventSource API — that only supports GET)
- `packages/core/src/sse/client.ts`
- Uses fetch with `ReadableStream` to parse `text/event-stream` format
- Parses `data: {json}\n\n` lines into typed ThreadStreamEvent objects
- Supports abort via AbortController
- Reconnection with exponential backoff (match chatkit.js: max 10s, 5 retries, jitter)
- 4xx errors = fatal, other errors = retry
- Exports: `createSSEStream(url, body, options) → AsyncIterable<ThreadStreamEvent>`
- Verification: Unit tests with mock fetch, integration test against dev server

### Task 1.4 — Implement protocol client

- `packages/core/src/client.ts`
- High-level API that wraps SSE client + fetch for non-streaming requests
- Methods map to chatkit request types:
  - `createThread(input)` → SSE stream
  - `addUserMessage(threadId, input)` → SSE stream
  - `addClientToolOutput(threadId, result)` → SSE stream
  - `retryAfterItem(threadId, itemId)` → SSE stream
  - `customAction(threadId, action, itemId?)` → SSE stream
  - `getThread(threadId)` → Thread
  - `listThreads(params)` → Page<ThreadMetadata>
  - `deleteThread(threadId)` → void
  - `updateThread(threadId, title)` → Thread
  - `listItems(threadId, params)` → Page<ThreadItem>
  - `addFeedback(threadId, itemIds, kind)` → void
- Handles CustomApiConfig (url, custom fetch)
- Validates config: throws on HostedApiConfig, warns on domainKey/frameTitle
- Verification: Integration tests against dev server for each method

### Task 1.5 — Implement vanilla state store

- `packages/core/src/store/`
- Uses zustand/vanilla (peer dependency)
- Store shape:
  - `threads: Map<string, ThreadMetadata>`
  - `currentThreadId: string | null`
  - `items: Map<string, ThreadItem[]>` (thread_id → items)
  - `isStreaming: boolean`
  - `streamError: Error | null`
  - `composerValue: ComposerState`
  - `pendingItems: Map<string, ThreadItem>` (items added but not done)
- Actions:
  - `processStreamEvent(event: ThreadStreamEvent)` — applies all event types to store state
  - `setCurrentThread(threadId)`, `resetComposer()`, etc.
- `processStreamEvent` handles:
  - `thread.created` → add to threads map, set currentThreadId
  - `thread.updated` → update threads map
  - `thread.item.added` → add to items + pendingItems
  - `thread.item.updated` → apply delta to pending item (text delta, widget delta, etc.)
  - `thread.item.done` → move from pending to items, remove from pendingItems
  - `thread.item.removed` → remove from items
  - `thread.item.replaced` → replace in items
  - `stream_options` → store allow_cancel flag
  - `progress_update` → store progress text/icon
  - `error` → store error, set isStreaming=false
  - `notice` → store notice for display
- Verification: Unit tests for each event type, state transitions

### Task 1.6 — Wire client + store together

- `packages/core/src/chatkit.ts` — main orchestrator
- `createChatKit(options: ChatKitOptions)` → ChatKitInstance
- ChatKitInstance:
  - `store` — the zustand vanilla store
  - `sendMessage(params)` — creates thread if needed, calls client, pipes events to store
  - `switchThread(threadId)` — loads thread + items, updates store
  - `deleteThread(threadId)` — calls client, updates store
  - `retryMessage(itemId)` — calls retryAfterItem, pipes events
  - `cancelStream()` — aborts current SSE stream
  - `submitFeedback(itemIds, kind)` — calls client
  - `sendCustomAction(action, itemId?)` — calls client, pipes events
  - `destroy()` — cleanup
- Handles the full send flow: create/addMessage → stream events → processStreamEvent → store update
- Verification: Integration test: create chatkit instance, send message, verify store state changes through full stream lifecycle

## Phase 2: React Hooks Layer (`chatkit-ui`)

### Task 2.1 — ChatKitProvider and core context

- `packages/chatkit-ui/src/provider.tsx`
- `ChatKitProvider` component that creates/holds ChatKitInstance
- React context for ChatKitInstance
- `useChatKitInstance()` hook to access the instance from context
- Handles options changes (recreate instance on api change, update store on other option changes)
- Verification: Provider renders, instance accessible from child components

### Task 2.2 — useChatKit hook (Tier 1 API)

- `packages/chatkit-ui/src/hooks/useChatKit.ts`
- Match the API from `reference/chatkit-js/packages/chatkit-react/src/useChatKit.ts`:
  - Takes `UseChatKitOptions` (ChatKitOptions + event handlers)
  - Returns `{ control, ref, focusComposer, setThreadId, sendUserMessage, setComposerValue, fetchUpdates, sendCustomAction, showHistory, hideHistory }`
- `control` is an opaque token passed to `<ChatKit>` component
- Event handler naming: `onResponseStart`, `onResponseEnd`, `onThreadChange`, `onError`, etc.
- Includes `useStableOptions` for deep-compare memoization
- Verification: Hook compiles, returns correct shape, stable references

### Task 2.3 — Data hooks (Tier 3 API)

- `packages/chatkit-ui/src/hooks/`
- `useMessages(threadId?)` — subscribe to items for current/specified thread, returns sorted messages
- `useThread(threadId?)` — subscribe to thread metadata
- `useThreadList()` — subscribe to thread list
- `useComposer()` — subscribe to composer state + actions (setText, submit, setTool, setModel)
- `useStreaming()` — subscribe to streaming state (isStreaming, progress, error, cancel)
- All hooks use zustand's `useStore` with selectors for fine-grained re-renders
- Verification: Unit tests with mock store, each hook returns correct slices

## Phase 3: React Components Layer

### Task 3.1 — Component registry and slot system

- `packages/chatkit-ui/src/components/registry.tsx`
- Context-based component registry with defaults
- Slot names: MessageBubble, Composer, Header, ThreadList, ThreadItem, StartScreen, WidgetRenderer, etc.
- Tier 2 override: `<ChatKit components={{ MessageBubble: MyBubble }} />` — whole-component replacement (shadcn-style)
- Each slot has exported prop types so replacement components receive the same data
- `useComponent(slotName)` hook returns the resolved component (user-provided or default)
- Verification: Default components render, overrides replace defaults entirely

### Task 3.2 — Message components

- `UserMessage` — renders UserMessageItem (text content, tags, attachments, quoted text)
- `AssistantMessage` — renders AssistantMessageItem (streaming text with deltas, annotations/citations)
- `MessageList` — scrollable list of messages, auto-scroll on new content, scroll-to-bottom button
- `EndOfTurn` — visual separator between turns
- Tailwind v4 utility classes for styling, CSS custom properties for design tokens
- Verification: Renders against dev server responses, streaming text animates correctly

### Task 3.3 — Composer component

- Text input with auto-resize textarea
- Submit button (disabled during streaming)
- Tool selector menu (if options.composer.tools provided)
- Model selector (if options.composer.models provided)
- Attachment button + file picker (if options.composer.attachments.enabled)
- Sends message via useChatKit().sendUserMessage
- Verification: Can type and send messages, tool/model selection works

### Task 3.4 — Header component

- Shows thread title (or options.header.title.text)
- Left/right action buttons (if configured)
- New thread button
- History toggle button (if options.history.enabled)
- Verification: Renders correctly, buttons trigger correct actions

### Task 3.5 — Thread history panel

- Slide-in panel showing thread list (from useThreadList)
- Thread items with title, date, delete/rename actions
- Click to switch thread
- Pagination (load more on scroll)
- Verification: Lists threads from dev server, switching works, delete works

### Task 3.6 — Start screen component

- Greeting text (options.startScreen.greeting)
- Starter prompt chips (options.startScreen.prompts)
- Click prompt → send as message
- Shown when no thread is selected or thread is empty
- Verification: Renders greeting and prompts, clicking prompt sends message

### Task 3.7 — Thread item actions

- Feedback buttons (thumbs up/down) — if options.threadItemActions.feedback
- Retry button — if options.threadItemActions.retry
- Copy button for assistant messages
- Verification: Feedback sends to server, retry re-streams response

### Task 3.8 — Widget renderer

- JSON → React component renderer for all widget types
- `packages/chatkit-ui/src/components/widgets/`
- Root types: Card, ListView, BasicRoot
- Layout: Box, Row, Col, Form, Spacer, Divider
- Text: Text, Title, Caption, Markdown, Label
- Content: Badge, Icon, Image, Button
- Form controls: Input, Textarea, Select, Checkbox, RadioGroup, DatePicker
- Action handling: onClickAction → sendCustomAction
- Streaming text support (Text/Markdown with streaming=true + value deltas)
- Verification: Send "widget" to dev server, widget renders with interactive form

## Phase 4: Theming & Design Tokens

### Task 4.1 — CSS custom property system + Tailwind v4 @theme

- `packages/chatkit-ui/src/theme/`
- Map ThemeOption → CSS custom properties (set on root element)
- Tailwind v4 `@theme` directive consumes the CSS custom properties so utilities resolve to tokens
- Color scheme (light/dark) — toggle via `data-color-scheme` attribute or media query
- Typography tokens (font-family, sizes: text-lg/md/sm/xs/2xs/3xs, heading sizes)
- Radius tokens (pill, round, soft, sharp → CSS var values)
- Density tokens (compact, normal, spacious → spacing scale multiplier)
- Color tokens (grayscale from hue with 25-1000 steps, accent primary with level, surface bg/fg)
- Reference: `reference/chatkit-js-bundle/ck1/index-BQ1T8qgK.css` for official token names and values
- Verification: Changing theme options updates CSS variables, Tailwind utilities reflect new values, visual changes apply

## Phase 5: Drop-in Assembly

### Task 5.1 — ChatKit drop-in component (Tier 1)

- `packages/chatkit-ui/src/ChatKit.tsx`
- `<ChatKit control={control} className={...} style={...} />`
- Assembles all components: Header + MessageList + Composer + StartScreen + History
- Accepts `control` from useChatKit()
- Applies theme via CSS custom properties on root element
- Disclaimer footer (if options.disclaimer provided)
- Verification: Full end-to-end flow against dev server — render ChatKit, type message, see streaming response, switch threads, use history

### Task 5.2 — Package exports and public API

- `packages/core/src/index.ts` — export all types, createChatKit, store types
- `packages/chatkit-ui/src/index.ts` — export ChatKit, useChatKit, all hooks, all component types, re-export core
- Ensure tree-shaking works (ESM exports)
- Verify package.json exports field configuration
- Verification: `pnpm build` succeeds, output bundles are reasonable size, imports work from consuming project

## Phase 6: Testing & Polish

### Task 6.1 — Unit tests for core

- SSE parser tests (well-formed, malformed, reconnection)
- Protocol client tests (each request type)
- Store tests (each event type → state transition)
- Orchestrator tests (send flow, cancel, retry)

### Task 6.2 — Component tests

- Vitest + React Testing Library
- MessageList rendering
- Composer interaction
- Widget rendering for each type
- Theme application

### Task 6.3 — Integration tests

- Full flow against dev server
- Send message → stream response → verify rendered output
- Thread CRUD operations
- Error handling and retry
- Widget interaction (send "widget", interact with form, verify action sent)
