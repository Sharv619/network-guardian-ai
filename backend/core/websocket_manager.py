"""
WebSocket Connection Manager for Real-Time Communication.

This module provides:
- Connection lifecycle management
- Event broadcasting to multiple clients
- Channel-based subscriptions
- Authentication for WebSocket connections
- Role-based broadcast filtering
"""
import asyncio
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from fastapi import WebSocket

from backend.core.logging_config import get_logger

if TYPE_CHECKING:
    from backend.core.deps import AuthenticatedUser

logger = get_logger(__name__)


class EventType(StrEnum):
    THREAT_DETECTED = "threat_detected"
    ALERT_CREATED = "alert_created"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"
    SYSTEM_STATUS = "system_status"
    ANOMALY_DETECTED = "anomaly_detected"
    DOMAIN_ANALYZED = "domain_analyzed"
    CLASSIFIER_UPDATE = "classifier_update"
    CACHE_UPDATE = "cache_update"
    CONNECTION_ACK = "connection_ack"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


@dataclass
class WebSocketMessage:
    event_type: EventType
    data: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    correlation_id: str | None = None

    def to_json(self) -> str:
        return json.dumps({
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        })


@dataclass
class ConnectionInfo:
    websocket: WebSocket
    client_id: str
    user: "AuthenticatedUser | None" = None
    connected_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    subscriptions: set[str] = field(default_factory=lambda: {"all"})

    @property
    def connection_duration(self) -> float:
        return time.time() - self.connected_at

    @property
    def user_role(self) -> str | None:
        return self.user.role if self.user else None

    @property
    def username(self) -> str | None:
        return self.user.identity if self.user else None


ROLE_HIERARCHY = {
    "admin": 3,
    "user": 2,
    "viewer": 1,
}


def has_role_or_higher(user_role: str | None, required_role: str) -> bool:
    """Check if user has the required role or higher."""
    if user_role is None:
        return False
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    return user_level >= required_level


class WebSocketManager:
    """Manages WebSocket connections and event broadcasting."""

    def __init__(self, max_connections: int = 100, heartbeat_interval: float = 30.0):
        self.max_connections = max_connections
        self.heartbeat_interval = heartbeat_interval
        self._connections: dict[str, ConnectionInfo] = {}
        self._event_handlers: dict[EventType, list[Callable]] = {}
        self._lock = asyncio.Lock()
        self._broadcast_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._heartbeat_task: asyncio.Task | None = None
        self._broadcast_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the WebSocket manager background tasks."""
        if self._running:
            return

        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._broadcast_task = asyncio.create_task(self._process_broadcast_queue())
        logger.info("WebSocket manager started")

    async def stop(self) -> None:
        """Stop the WebSocket manager and close all connections."""
        self._running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass

        async with self._lock:
            for _client_id, conn_info in list(self._connections.items()):
                try:
                    await conn_info.websocket.close(code=1001, reason="Server shutting down")
                except Exception:
                    pass
            self._connections.clear()

        logger.info("WebSocket manager stopped")

    async def connect(
        self,
        websocket: WebSocket,
        client_id: str,
        user: "AuthenticatedUser | None" = None,
    ) -> bool:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection object
            client_id: Unique identifier for this connection
            user: AuthenticatedUser object from the authentication dependency

        Returns:
            True if connection was accepted, False if rejected (max connections)
        """
        async with self._lock:
            if len(self._connections) >= self.max_connections:
                logger.warning(
                    "WebSocket connection rejected - max connections reached",
                    extra={"client_id": client_id, "max_connections": self.max_connections}
                )
                await websocket.close(code=1013, reason="Max connections reached")
                return False

            await websocket.accept()

            conn_info = ConnectionInfo(
                websocket=websocket,
                client_id=client_id,
                user=user,
            )
            self._connections[client_id] = conn_info

        logger.info(
            "WebSocket connected",
            extra={
                "client_id": client_id,
                "user_role": conn_info.user_role,
                "username": conn_info.username,
                "total_connections": len(self._connections),
            }
        )

        ack_message = WebSocketMessage(
            event_type=EventType.CONNECTION_ACK,
            data={
                "client_id": client_id,
                "message": "Connected to Network Guardian AI",
                "subscriptions": list(conn_info.subscriptions),
                "user_role": conn_info.user_role,
                "username": conn_info.username,
            },
            correlation_id=client_id,
        )
        await self._send_to_connection(client_id, ack_message)

        return True

    async def disconnect(self, client_id: str) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if client_id in self._connections:
                conn_info = self._connections.pop(client_id)
                logger.info(
                    "WebSocket disconnected",
                    extra={
                        "client_id": client_id,
                        "connection_duration": conn_info.connection_duration,
                        "remaining_connections": len(self._connections),
                    }
                )

    async def subscribe(self, client_id: str, channels: list[str]) -> bool:
        """Subscribe a client to specific event channels."""
        async with self._lock:
            if client_id not in self._connections:
                return False

            conn_info = self._connections[client_id]
            conn_info.subscriptions.update(channels)
            logger.debug(
                "Client subscribed to channels",
                extra={"client_id": client_id, "channels": channels}
            )
            return True

    async def unsubscribe(self, client_id: str, channels: list[str]) -> bool:
        """Unsubscribe a client from specific event channels."""
        async with self._lock:
            if client_id not in self._connections:
                return False

            conn_info = self._connections[client_id]
            conn_info.subscriptions.difference_update(channels)
            return True

    async def broadcast(
        self,
        event_type: EventType,
        data: dict[str, Any],
        channel: str = "all",
        exclude_client: str | None = None,
        min_role: str | None = None,
    ) -> int:
        """
        Broadcast an event to all subscribed clients.

        Args:
            event_type: The type of event being broadcast
            data: The event data payload
            channel: Channel to broadcast to (default: "all")
            exclude_client: Optional client_id to exclude from broadcast
            min_role: Optional minimum role required to receive the message.
                      If provided, only users with this role or higher will receive it.
                      Role hierarchy: admin > user > viewer

        Returns:
            Number of clients that received the message
        """
        if not self._connections:
            return 0

        message = WebSocketMessage(event_type=event_type, data=data)
        delivered_count = 0

        async with self._lock:
            for client_id, conn_info in list(self._connections.items()):
                if exclude_client and client_id == exclude_client:
                    continue

                if min_role and not has_role_or_higher(conn_info.user_role, min_role):
                    continue

                if channel in conn_info.subscriptions or "all" in conn_info.subscriptions:
                    try:
                        await conn_info.websocket.send_text(message.to_json())
                        delivered_count += 1
                    except Exception as e:
                        logger.warning(
                            "Failed to send message to client",
                            extra={"client_id": client_id, "error": str(e)}
                        )

        logger.debug(
            "Event broadcasted",
            extra={
                "event_type": event_type.value,
                "channel": channel,
                "delivered_count": delivered_count,
                "min_role": min_role,
            }
        )
        return delivered_count

    async def broadcast_queued(self, event_type: EventType, data: dict[str, Any]) -> None:
        """Queue an event for broadcasting (non-blocking)."""
        await self._broadcast_queue.put((event_type, data))

    async def _process_broadcast_queue(self) -> None:
        """Process queued broadcast messages."""
        while self._running:
            try:
                event_type, data = await asyncio.wait_for(
                    self._broadcast_queue.get(),
                    timeout=1.0
                )
                await self.broadcast(event_type, data)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Broadcast queue error", extra={"error": str(e)})

    async def _send_to_connection(self, client_id: str, message: WebSocketMessage) -> bool:
        """Send a message to a specific connection."""
        async with self._lock:
            if client_id not in self._connections:
                return False

            conn_info = self._connections[client_id]
            try:
                await conn_info.websocket.send_text(message.to_json())
                return True
            except Exception as e:
                logger.warning(
                    "Failed to send message",
                    extra={"client_id": client_id, "error": str(e)}
                )
                return False

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to all connections."""
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                if not self._connections:
                    continue

                heartbeat_message = WebSocketMessage(
                    event_type=EventType.HEARTBEAT,
                    data={"timestamp": datetime.now(UTC).isoformat()}
                )

                stale_clients = []
                async with self._lock:
                    for client_id, conn_info in list(self._connections.items()):
                        try:
                            await conn_info.websocket.send_text(heartbeat_message.to_json())
                            conn_info.last_heartbeat = time.time()
                        except Exception:
                            stale_clients.append(client_id)

                for client_id in stale_clients:
                    await self.disconnect(client_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Heartbeat error", extra={"error": str(e)})

    def register_handler(self, event_type: EventType, handler: Callable) -> None:
        """Register a handler for a specific event type."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    async def handle_message(self, client_id: str, message: str) -> dict[str, Any] | None:
        """Handle an incoming message from a client."""
        try:
            data = json.loads(message)
            action = data.get("action")

            if action == "subscribe":
                channels = data.get("channels", [])
                if await self.subscribe(client_id, channels):
                    return {"status": "subscribed", "channels": channels}
                return {"status": "error", "message": "Subscription failed"}

            elif action == "unsubscribe":
                channels = data.get("channels", [])
                if await self.unsubscribe(client_id, channels):
                    return {"status": "unsubscribed", "channels": channels}
                return {"status": "error", "message": "Unsubscription failed"}

            elif action == "ping":
                return {"status": "pong", "timestamp": datetime.now(UTC).isoformat()}

            else:
                return {"status": "error", "message": f"Unknown action: {action}"}

        except json.JSONDecodeError:
            return {"status": "error", "message": "Invalid JSON"}
        except Exception as e:
            logger.error("Message handling error", extra={"client_id": client_id, "error": str(e)})
            return {"status": "error", "message": str(e)}

    def get_stats(self) -> dict[str, Any]:
        """Get WebSocket manager statistics."""
        return {
            "total_connections": len(self._connections),
            "max_connections": self.max_connections,
            "heartbeat_interval": self.heartbeat_interval,
            "is_running": self._running,
            "connections": [
                {
                    "client_id": conn.client_id,
                    "user_role": conn.user_role,
                    "username": conn.username,
                    "connected_at": datetime.fromtimestamp(
                        conn.connected_at, tz=UTC
                    ).isoformat(),
                    "connection_duration": round(conn.connection_duration, 2),
                    "subscriptions": list(conn.subscriptions),
                }
                for conn in self._connections.values()
            ],
        }


ws_manager = WebSocketManager()
