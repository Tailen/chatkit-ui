"""Mock ChatKitServer with keyword-triggered test scenarios."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from chatkit.actions import Action
from chatkit.errors import CustomStreamError
from chatkit.server import ChatKitServer
from chatkit.store import default_generate_id
from chatkit.types import (
    Annotation,
    AssistantMessageContent,
    AssistantMessageContentPartAdded,
    AssistantMessageContentPartDone,
    AssistantMessageContentPartTextDelta,
    AssistantMessageItem,
    ClientToolCallItem,
    CustomTask,
    EndOfTurnItem,
    ErrorEvent,
    FeedbackKind,
    FileSource,
    NoticeEvent,
    ProgressUpdateEvent,
    SearchTask,
    ThoughtTask,
    ThreadItemAddedEvent,
    ThreadItemDoneEvent,
    ThreadItemUpdatedEvent,
    ThreadMetadata,
    ThreadStreamEvent,
    URLSource,
    UserMessageItem,
    WidgetItem,
    Workflow,
    WorkflowItem,
    WorkflowTaskAdded,
    WorkflowTaskUpdated,
)
from chatkit.widgets import (
    Button,
    Card,
    Col,
    Input,
    Markdown,
    Text,
    Title,
)

from memory_store import InMemoryStore, RequestContext

LOREM_PARAGRAPHS = [
    "This is a test response from the chatkit-ui dev server. "
    "The server echoes your message and streams back a multi-paragraph response "
    "to help you develop and test the frontend streaming implementation.",
    "Each paragraph is streamed as a series of text deltas, "
    "simulating how a real LLM backend would generate tokens incrementally. "
    "You can observe how the UI handles progressive text rendering.",
    "The dev server supports several test scenarios. "
    "Try sending messages with keywords like 'widget', 'error', 'long', "
    "'tool', 'workflow', 'notice', 'slow', or 'annotations' to trigger "
    "different response types.",
]

LONG_PARAGRAPHS = [
    f"Paragraph {i+1}: This is sentence {i*3+1} of the long response. "
    f"This is sentence {i*3+2} of the long response. "
    f"This is sentence {i*3+3} of the long response."
    for i in range(17)
]


def _extract_user_text(user_message: UserMessageItem | None) -> str:
    """Extract plain text from user message content."""
    if user_message is None:
        return ""
    parts = []
    for content in user_message.content:
        if hasattr(content, "text"):
            parts.append(content.text)
    return " ".join(parts).lower().strip()


class MockChatKitServer(ChatKitServer[RequestContext]):
    """Dev server with keyword-triggered mock responses."""

    def __init__(self, store: InMemoryStore) -> None:
        super().__init__(store=store)

    async def respond(
        self,
        thread: ThreadMetadata,
        input_user_message: UserMessageItem | None,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        user_text = _extract_user_text(input_user_message)
        print(f"  [respond] user_text={user_text!r}")

        if "error" in user_text:
            async for event in self._scenario_error(thread, context):
                yield event
        elif "widget" in user_text:
            async for event in self._scenario_widget(thread, context):
                yield event
        elif "tool" in user_text:
            async for event in self._scenario_tool(thread, context):
                yield event
        elif "workflow" in user_text:
            async for event in self._scenario_workflow(thread, context):
                yield event
        elif "notice" in user_text:
            async for event in self._scenario_notice(thread, context):
                yield event
        elif "slow" in user_text:
            async for event in self._scenario_slow(thread, user_text, context):
                yield event
        elif "long" in user_text:
            async for event in self._scenario_long(thread, context):
                yield event
        elif "annotations" in user_text:
            async for event in self._scenario_annotations(thread, context):
                yield event
        else:
            async for event in self._scenario_default(thread, user_text, context):
                yield event

    async def add_feedback(
        self,
        thread_id: str,
        item_ids: list[str],
        feedback: FeedbackKind,
        context: RequestContext,
    ) -> None:
        print(f"  [feedback] thread={thread_id} items={item_ids} kind={feedback}")

    def action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        sender: WidgetItem | None,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        return self._handle_action(thread, action, sender, context)

    async def _handle_action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        sender: WidgetItem | None,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        print(f"  [action] type={action.type} payload={action.payload}")
        # Echo the action back as an assistant message
        text = f"Received action: type=`{action.type}`, payload=`{action.payload}`"
        async for event in self._stream_text(thread, text, context):
            yield event

    # ── Scenarios ──────────────────────────────────────────────────────

    async def _scenario_default(
        self,
        thread: ThreadMetadata,
        user_text: str,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Echo user message + stream lorem paragraphs."""
        echo = f"You said: *{user_text}*\n\n" if user_text else ""
        full_text = echo + "\n\n".join(LOREM_PARAGRAPHS)
        async for event in self._stream_text(thread, full_text, context):
            yield event

    async def _scenario_error(
        self,
        thread: ThreadMetadata,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Yield an error event."""
        raise CustomStreamError(
            message="This is a test error from the dev server. "
            "The 'error' keyword triggered this intentional failure.",
            allow_retry=True,
        )

    async def _scenario_widget(
        self,
        thread: ThreadMetadata,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Respond with a Card widget containing form elements."""
        item_id = default_generate_id("message")
        widget = Card(
            children=[
                Title(value="Test Widget Form", size="lg"),
                Text(value="This is a test widget rendered by the dev server.", id="desc", streaming=False),
                Input(name="user_name", placeholder="Enter your name", inputType="text"),
                Input(name="email", placeholder="Enter your email", inputType="email"),
                Button(
                    label="Submit",
                    style="primary",
                    onClickAction={"type": "form.submit", "payload": {}},
                ),
            ],
            size="md",
        )
        yield ThreadItemDoneEvent(
            item=WidgetItem(
                id=item_id,
                thread_id=thread.id,
                created_at=datetime.now(),
                widget=widget,
                copy_text="Test widget form",
            ),
        )

    async def _scenario_tool(
        self,
        thread: ThreadMetadata,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Yield a client tool call."""
        item_id = default_generate_id("tool_call")
        tool_item = ClientToolCallItem(
            id=item_id,
            thread_id=thread.id,
            created_at=datetime.now(),
            status="pending",
            call_id=f"call_{item_id}",
            name="get_weather",
            arguments={"city": "San Francisco", "units": "fahrenheit"},
        )
        yield ThreadItemDoneEvent(item=tool_item)

    async def _scenario_workflow(
        self,
        thread: ThreadMetadata,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Yield a workflow with multiple tasks that update over time."""
        item_id = default_generate_id("workflow")
        workflow = Workflow(
            type="custom",
            tasks=[
                CustomTask(
                    title="Analyzing request",
                    icon="sparkle",
                    status_indicator="loading",
                ),
            ],
        )
        workflow_item = WorkflowItem(
            id=item_id,
            thread_id=thread.id,
            created_at=datetime.now(),
            workflow=workflow,
        )
        yield ThreadItemAddedEvent(item=workflow_item)

        await asyncio.sleep(0.5)

        # Complete first task, add second
        yield ThreadItemUpdatedEvent(
            item_id=item_id,
            update=WorkflowTaskUpdated(
                task_index=0,
                task=CustomTask(
                    title="Analyzing request",
                    icon="sparkle",
                    status_indicator="complete",
                ),
            ),
        )
        yield ThreadItemUpdatedEvent(
            item_id=item_id,
            update=WorkflowTaskAdded(
                task_index=1,
                task=SearchTask(
                    title="Searching the web",
                    title_query="chatkit protocol",
                    queries=["chatkit wire protocol", "chatkit-python SSE"],
                    status_indicator="loading",
                    sources=[
                        URLSource(
                            title="ChatKit Python Docs",
                            url="https://openai.github.io/chatkit-python/",
                            attribution="OpenAI",
                        ),
                    ],
                ),
            ),
        )

        await asyncio.sleep(0.8)

        # Complete second task, add third
        yield ThreadItemUpdatedEvent(
            item_id=item_id,
            update=WorkflowTaskUpdated(
                task_index=1,
                task=SearchTask(
                    title="Searching the web",
                    title_query="chatkit protocol",
                    queries=["chatkit wire protocol", "chatkit-python SSE"],
                    status_indicator="complete",
                    sources=[
                        URLSource(
                            title="ChatKit Python Docs",
                            url="https://openai.github.io/chatkit-python/",
                            attribution="OpenAI",
                        ),
                    ],
                ),
            ),
        )
        yield ThreadItemUpdatedEvent(
            item_id=item_id,
            update=WorkflowTaskAdded(
                task_index=2,
                task=ThoughtTask(
                    title="Synthesizing results",
                    content="Combining search results with user context...",
                    status_indicator="loading",
                ),
            ),
        )

        await asyncio.sleep(0.5)

        yield ThreadItemUpdatedEvent(
            item_id=item_id,
            update=WorkflowTaskUpdated(
                task_index=2,
                task=ThoughtTask(
                    title="Synthesizing results",
                    content="Combining search results with user context...",
                    status_indicator="complete",
                ),
            ),
        )

        # Finalize workflow
        workflow_item.workflow.tasks = [
            CustomTask(title="Analyzing request", icon="sparkle", status_indicator="complete"),
            SearchTask(
                title="Searching the web",
                title_query="chatkit protocol",
                queries=["chatkit wire protocol", "chatkit-python SSE"],
                status_indicator="complete",
                sources=[
                    URLSource(
                        title="ChatKit Python Docs",
                        url="https://openai.github.io/chatkit-python/",
                        attribution="OpenAI",
                    ),
                ],
            ),
            ThoughtTask(
                title="Synthesizing results",
                content="Combining search results with user context...",
                status_indicator="complete",
            ),
        ]
        yield ThreadItemDoneEvent(item=workflow_item)

        # Follow up with a text response
        async for event in self._stream_text(
            thread,
            "The workflow completed successfully with 3 tasks: "
            "analysis, web search, and synthesis.",
            context,
        ):
            yield event

    async def _scenario_notice(
        self,
        thread: ThreadMetadata,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Yield notice events followed by a normal response."""
        yield NoticeEvent(
            level="info",
            title="Information",
            message="This is an **info** notice from the dev server.",
        )
        yield NoticeEvent(
            level="warning",
            title="Warning",
            message="This is a **warning** notice. Something might need attention.",
        )
        async for event in self._stream_text(
            thread,
            "Two notices were sent before this response (info and warning).",
            context,
        ):
            yield event

    async def _scenario_slow(
        self,
        thread: ThreadMetadata,
        user_text: str,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Stream with 500ms delays between chunks."""
        async for event in self._stream_text(
            thread,
            "This response has artificial delays between chunks to test loading states. "
            "Each chunk takes 500ms to arrive.",
            context,
            chunk_delay=0.5,
        ):
            yield event

    async def _scenario_long(
        self,
        thread: ThreadMetadata,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Stream a very long response for scroll/performance testing."""
        full_text = "\n\n".join(LONG_PARAGRAPHS)
        async for event in self._stream_text(thread, full_text, context):
            yield event

    async def _scenario_annotations(
        self,
        thread: ThreadMetadata,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Stream a response with source annotations."""
        item_id = default_generate_id("message")
        annotations = [
            Annotation(
                source=URLSource(
                    title="ChatKit Python Documentation",
                    url="https://openai.github.io/chatkit-python/",
                    attribution="OpenAI",
                    description="Official documentation for the ChatKit Python SDK.",
                ),
                index=0,
            ),
            Annotation(
                source=FileSource(
                    title="Protocol Types Reference",
                    filename="types.py",
                    description="Canonical type definitions for the ChatKit wire protocol.",
                ),
                index=1,
            ),
        ]

        text = (
            "Here is a response with source annotations. "
            "The ChatKit protocol is documented in the official Python SDK[0]. "
            "The type definitions are in the protocol reference file[1]."
        )

        content = AssistantMessageContent(
            text=text,
            annotations=annotations,
        )

        item = AssistantMessageItem(
            id=item_id,
            thread_id=thread.id,
            created_at=datetime.now(),
            content=[content],
        )
        yield ThreadItemDoneEvent(item=item)

    # ── Helpers ────────────────────────────────────────────────────────

    async def _stream_text(
        self,
        thread: ThreadMetadata,
        full_text: str,
        context: RequestContext,
        chunk_delay: float = 0.03,
        chunk_size: int = 12,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Stream text as an assistant message with realistic deltas."""
        item_id = default_generate_id("message")

        # Create empty assistant message
        item = AssistantMessageItem(
            id=item_id,
            thread_id=thread.id,
            created_at=datetime.now(),
            content=[],
        )
        yield ThreadItemAddedEvent(item=item)

        # Add first content part
        yield ThreadItemUpdatedEvent(
            item_id=item_id,
            update=AssistantMessageContentPartAdded(
                content_index=0,
                content=AssistantMessageContent(text=""),
            ),
        )

        # Stream text deltas
        offset = 0
        while offset < len(full_text):
            chunk = full_text[offset : offset + chunk_size]
            yield ThreadItemUpdatedEvent(
                item_id=item_id,
                update=AssistantMessageContentPartTextDelta(
                    content_index=0,
                    delta=chunk,
                ),
            )
            offset += chunk_size
            await asyncio.sleep(chunk_delay)

        # Finalize content part
        yield ThreadItemUpdatedEvent(
            item_id=item_id,
            update=AssistantMessageContentPartDone(
                content_index=0,
                content=AssistantMessageContent(text=full_text),
            ),
        )

        # Done
        item.content = [AssistantMessageContent(text=full_text)]
        yield ThreadItemDoneEvent(item=item)

        # End of turn
        eot_id = default_generate_id("message")
        yield ThreadItemDoneEvent(
            item=EndOfTurnItem(
                id=eot_id,
                thread_id=thread.id,
                created_at=datetime.now(),
            ),
        )
