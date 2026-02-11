"""Dev backend server for chatkit-ui.

Run: uv run python main.py
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response, StreamingResponse

from chatkit.server import NonStreamingResult, StreamingResult
from memory_store import InMemoryStore, RequestContext
from server_impl import MockChatKitServer

app = FastAPI(title="chatkit-ui dev server")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create server with in-memory store
store = InMemoryStore()
server = MockChatKitServer(store=store)


@app.post("/chatkit")
async def chatkit_endpoint(request: Request) -> Response:
    """Single ChatKit protocol endpoint.

    Receives JSON with a `type` discriminator field and routes to
    streaming (SSE) or non-streaming (JSON) handlers.
    """
    body = await request.body()
    print(f"[chatkit] received {len(body)} bytes")

    context = RequestContext()
    result = await server.process(body, context)

    if isinstance(result, StreamingResult):
        return StreamingResponse(
            result,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        return Response(
            content=result.json,
            media_type="application/json",
        )


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    print("Starting chatkit-ui dev server on http://localhost:8000")
    print("POST /chatkit — ChatKit protocol endpoint")
    print("GET  /health  — Health check")
    print()
    print("Test scenarios (send as user message text):")
    print("  (default)      — Echo + streaming lorem response")
    print("  'widget'       — Card widget with form elements")
    print("  'error'        — Error event with retry")
    print("  'long'         — ~50 sentence response (scroll testing)")
    print("  'tool'         — Client tool call")
    print("  'workflow'     — Multi-task workflow")
    print("  'notice'       — Info + warning notices")
    print("  'slow'         — 500ms delays between chunks")
    print("  'annotations'  — Response with source annotations")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000)
