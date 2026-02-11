"""In-memory Store implementation for the dev backend server."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from chatkit.store import NotFoundError, Store
from chatkit.types import (
    Attachment,
    Page,
    ThreadItem,
    ThreadMetadata,
)


class RequestContext:
    """Simple request context — single-user dev server."""

    user_id: str = "dev-user"


class InMemoryStore(Store[RequestContext]):
    """Dict-based in-memory store. Resets on server restart."""

    def __init__(self) -> None:
        # thread_id → ThreadMetadata
        self._threads: OrderedDict[str, ThreadMetadata] = OrderedDict()
        # thread_id → OrderedDict[item_id → ThreadItem]
        self._items: dict[str, OrderedDict[str, ThreadItem]] = {}
        # attachment_id → Attachment
        self._attachments: dict[str, Attachment] = {}

    async def load_thread(
        self, thread_id: str, context: RequestContext
    ) -> ThreadMetadata:
        thread = self._threads.get(thread_id)
        if thread is None:
            raise NotFoundError(f"Thread {thread_id} not found")
        return thread

    async def save_thread(
        self, thread: ThreadMetadata, context: RequestContext
    ) -> None:
        self._threads[thread.id] = thread
        if thread.id not in self._items:
            self._items[thread.id] = OrderedDict()

    async def load_thread_items(
        self,
        thread_id: str,
        after: str | None,
        limit: int,
        order: str,
        context: RequestContext,
    ) -> Page[ThreadItem]:
        thread_items = self._items.get(thread_id, OrderedDict())
        items_list = list(thread_items.values())

        if order == "desc":
            items_list = list(reversed(items_list))

        # Apply cursor-based pagination
        if after is not None:
            found = False
            filtered = []
            for item in items_list:
                if found:
                    filtered.append(item)
                if item.id == after:
                    found = True
            items_list = filtered

        has_more = len(items_list) > limit
        result = items_list[:limit]
        next_after = result[-1].id if has_more and result else None

        return Page[ThreadItem](data=result, has_more=has_more, after=next_after)

    async def save_attachment(
        self, attachment: Attachment, context: RequestContext
    ) -> None:
        self._attachments[attachment.id] = attachment

    async def load_attachment(
        self, attachment_id: str, context: RequestContext
    ) -> Attachment:
        attachment = self._attachments.get(attachment_id)
        if attachment is None:
            raise NotFoundError(f"Attachment {attachment_id} not found")
        return attachment

    async def delete_attachment(
        self, attachment_id: str, context: RequestContext
    ) -> None:
        self._attachments.pop(attachment_id, None)

    async def load_threads(
        self,
        limit: int,
        after: str | None,
        order: str,
        context: RequestContext,
    ) -> Page[ThreadMetadata]:
        threads_list = list(self._threads.values())

        if order == "desc":
            threads_list = list(reversed(threads_list))

        if after is not None:
            found = False
            filtered = []
            for thread in threads_list:
                if found:
                    filtered.append(thread)
                if thread.id == after:
                    found = True
            threads_list = filtered

        has_more = len(threads_list) > limit
        result = threads_list[:limit]
        next_after = result[-1].id if has_more and result else None

        return Page[ThreadMetadata](data=result, has_more=has_more, after=next_after)

    async def add_thread_item(
        self, thread_id: str, item: ThreadItem, context: RequestContext
    ) -> None:
        if thread_id not in self._items:
            self._items[thread_id] = OrderedDict()
        self._items[thread_id][item.id] = item

    async def save_item(
        self, thread_id: str, item: ThreadItem, context: RequestContext
    ) -> None:
        if thread_id not in self._items:
            self._items[thread_id] = OrderedDict()
        self._items[thread_id][item.id] = item

    async def load_item(
        self, thread_id: str, item_id: str, context: RequestContext
    ) -> ThreadItem:
        thread_items = self._items.get(thread_id, {})
        item = thread_items.get(item_id)
        if item is None:
            raise NotFoundError(f"Item {item_id} not found in thread {thread_id}")
        return item

    async def delete_thread(
        self, thread_id: str, context: RequestContext
    ) -> None:
        self._threads.pop(thread_id, None)
        self._items.pop(thread_id, None)

    async def delete_thread_item(
        self, thread_id: str, item_id: str, context: RequestContext
    ) -> None:
        thread_items = self._items.get(thread_id, {})
        thread_items.pop(item_id, None)
