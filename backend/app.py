from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .layout_engine import ForceLayout3D
from .signal_engine import SignalEngine
from .wifi_scanner import WifiScanner

app = FastAPI(title="Matrix WiFi Radar")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scanner = WifiScanner(scan_interval_s=1.5)
engine = SignalEngine(window_size=40, min_points=8)
layout = ForceLayout3D()

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

if FRONTEND.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND)), name="assets")


@app.get("/style.css")
async def style_css() -> FileResponse:
    return FileResponse(FRONTEND / "style.css")


@app.get("/app.js")
async def app_js() -> FileResponse:
    return FileResponse(FRONTEND / "app.js")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND / "index.html")


@app.get("/health")
async def health() -> dict:
    return {"ok": True}


@app.websocket("/ws")
async def ws_radar(ws: WebSocket) -> None:
    await ws.accept()
    paused = False
    try:
        while True:
            # Non-blocking receive for control messages
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=0.01)
                payload = json.loads(msg)
                if payload.get("type") == "pause":
                    paused = bool(payload.get("value", False))
            except asyncio.TimeoutError:
                pass
            except Exception:
                pass

            if not paused:
                samples = await scanner.scan()
                engine.ingest_batch(samples)
            corr = engine.correlation_matrix()
            positions, edges = layout.step(corr)

            packet = {
                "type": "snapshot",
                "timestamp": time.time(),
                "nodes": engine.to_payload_nodes(),
                "edges": edges,
                "positions": positions,
            }
            await ws.send_text(json.dumps(packet))
            await asyncio.sleep(scanner.scan_interval_s)
    except Exception:
        await ws.close()
