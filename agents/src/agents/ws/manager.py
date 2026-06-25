"""WebSocket connection manager with Redis pub/sub for horizontal scaling."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket
from redis.asyncio import Redis
from agents.logging_setup import get_logger, log_payload, ws_log_level
from agents.settings import get_settings

logger = get_logger("agents.ws.redis")

_manager: ChatWebSocketManager | None = None


class ChatWebSocketManager:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self._local: dict[str, set[WebSocket]] = {}
        self._listener_tasks: dict[WebSocket, asyncio.Task] = {}

    def _channel(self, thread_id: str) -> str:
        return f"chat:thread:{thread_id}"

    async def connect(self, websocket: WebSocket, thread_id: str) -> None:
        await websocket.accept()
        self._local.setdefault(thread_id, set()).add(websocket)
        self._listener_tasks[websocket] = asyncio.create_task(
            self._listen(thread_id, websocket)
        )

    async def disconnect(self, websocket: WebSocket, thread_id: str) -> None:
        task = self._listener_tasks.pop(websocket, None)
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        sockets = self._local.get(thread_id)
        if sockets is not None:
            sockets.discard(websocket)
            if not sockets:
                del self._local[thread_id]

    async def publish(self, thread_id: str, payload: dict[str, Any]) -> None:
        settings = get_settings()
        event_type = str(payload.get("type", "unknown"))
        log_payload(
            logger,
            "ws.message.out",
            payload,
            level=ws_log_level(event_type, settings=settings),
            thread_id=thread_id,
        )
        await self.redis.publish(self._channel(thread_id), json.dumps(payload))

    async def _listen(self, thread_id: str, websocket: WebSocket) -> None:
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self._channel(thread_id))
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = json.loads(message["data"])
                await websocket.send_json(data)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        finally:
            await pubsub.unsubscribe(self._channel(thread_id))
            await pubsub.aclose()


def init_ws_manager(redis: Redis) -> ChatWebSocketManager:
    global _manager
    _manager = ChatWebSocketManager(redis)
    return _manager


def get_ws_manager() -> ChatWebSocketManager:
    if _manager is None:
        raise RuntimeError("WebSocket manager not initialized")
    return _manager
