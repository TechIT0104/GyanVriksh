"""In-process WebSocket connection manager, keyed by channel (e.g. doc file_id)."""
import asyncio
import json
from collections import defaultdict

from fastapi import WebSocket


class WSManager:
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, channel: str, ws: WebSocket):
        await ws.accept()
        self.connections[channel].append(ws)

    def disconnect(self, channel: str, ws: WebSocket):
        if ws in self.connections[channel]:
            self.connections[channel].remove(ws)

    async def broadcast(self, channel: str, payload: dict):
        dead = []
        for ws in self.connections[channel]:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(channel, ws)


doc_status_manager = WSManager()
