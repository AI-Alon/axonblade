"""
playground/backend/main.py — AxonBlade playground API (V2 Phase 5.1).

POST /run   { "code": "..." }  → text/event-stream of output lines
GET  /health                   → { "status": "ok" }

Each SSE event is one output line.  The stream ends with:
    data: [DONE]

Deploy on Render: see README.md
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Project root is two directories above playground/backend/
_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

TIMEOUT_SECS = 5
_BLOCKED_MODULES = {"io", "http"}

app = FastAPI(title="AxonBlade Playground API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-alon.github.io",
        "http://localhost",
        "http://localhost:5500",
        "http://127.0.0.1",
        "http://127.0.0.1:5500",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    code: str


async def _stream(code: str):
    """Async generator that runs AxonBlade code and yields SSE data lines."""
    for mod in _BLOCKED_MODULES:
        if f"uselib -{mod}-" in code:
            yield f"data: \x1b[31mPlayground: '{mod}' module is disabled here\x1b[0m\n\n"
            yield "data: [DONE]\n\n"
            return

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".axb", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp = f.name

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(_ROOT / "main.py"),
            "run",
            tmp,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(_ROOT),
        )

        try:
            async with asyncio.timeout(TIMEOUT_SECS):
                async for raw in proc.stdout:
                    line = raw.decode("utf-8", errors="replace").rstrip("\n")
                    yield f"data: {line}\n\n"
                await proc.wait()
        except asyncio.TimeoutError:
            proc.kill()
            yield f"data: \x1b[31mTimeout: execution exceeded {TIMEOUT_SECS} seconds\x1b[0m\n\n"

    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass

    yield "data: [DONE]\n\n"


@app.post("/run")
async def run_code(body: RunRequest):
    return StreamingResponse(
        _stream(body.code),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
