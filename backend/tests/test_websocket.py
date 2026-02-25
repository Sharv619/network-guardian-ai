"""
Tests for WebSocket real-time communication.

Tests the WebSocket connection manager, authentication, and event broadcasting.
"""
import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from backend.core.websocket_manager import (
    WebSocketManager,
    EventType,
    WebSocketMessage,
    ConnectionInfo,
    has_role_or_higher,
    ws_manager,
)
from backend.core.deps import AuthenticatedUser


def create_mock_user(identity: str = "testuser", role: str = "viewer") -> AuthenticatedUser:
    """Helper to create a mock AuthenticatedUser."""
    return AuthenticatedUser(identity=identity, role=role, auth_type="jwt")


class TestEventType:
    def test_event_type_values(self):
        assert EventType.THREAT_DETECTED == "threat_detected"
        assert EventType.ALERT_CREATED == "alert_created"
        assert EventType.ALERT_ACKNOWLEDGED == "alert_acknowledged"
        assert EventType.SYSTEM_STATUS == "system_status"
        assert EventType.ANOMALY_DETECTED == "anomaly_detected"
        assert EventType.DOMAIN_ANALYZED == "domain_analyzed"
        assert EventType.CONNECTION_ACK == "connection_ack"
        assert EventType.HEARTBEAT == "heartbeat"
        assert EventType.ERROR == "error"

    def test_event_type_string_usage(self):
        event_type = EventType.THREAT_DETECTED
        assert str(event_type) == "threat_detected"
        assert event_type.value == "threat_detected"


class TestWebSocketMessage:
    def test_message_creation(self):
        message = WebSocketMessage(
            event_type=EventType.THREAT_DETECTED,
            data={"domain": "example.com", "risk_score": "High"},
        )
        assert message.event_type == EventType.THREAT_DETECTED
        assert message.data["domain"] == "example.com"
        assert message.timestamp is not None

    def test_message_to_json(self):
        message = WebSocketMessage(
            event_type=EventType.ALERT_CREATED,
            data={"message": "Test alert"},
            correlation_id="test-123",
        )
        json_str = message.to_json()
        parsed = json.loads(json_str)

        assert parsed["event_type"] == "alert_created"
        assert parsed["data"]["message"] == "Test alert"
        assert parsed["correlation_id"] == "test-123"
        assert "timestamp" in parsed


class TestRoleHierarchy:
    def test_admin_has_all_roles(self):
        assert has_role_or_higher("admin", "admin") is True
        assert has_role_or_higher("admin", "user") is True
        assert has_role_or_higher("admin", "viewer") is True

    def test_user_has_viewer_role(self):
        assert has_role_or_higher("user", "admin") is False
        assert has_role_or_higher("user", "user") is True
        assert has_role_or_higher("user", "viewer") is True

    def test_viewer_only_has_viewer(self):
        assert has_role_or_higher("viewer", "admin") is False
        assert has_role_or_higher("viewer", "user") is False
        assert has_role_or_higher("viewer", "viewer") is True

    def test_none_role_fails(self):
        assert has_role_or_higher(None, "viewer") is False


class TestConnectionInfo:
    def test_connection_info_creation_with_user(self):
        websocket = MagicMock()
        user = create_mock_user("testuser", "admin")
        conn_info = ConnectionInfo(
            websocket=websocket,
            client_id="test-client",
            user=user,
        )
        assert conn_info.client_id == "test-client"
        assert conn_info.user_role == "admin"
        assert conn_info.username == "testuser"
        assert "all" in conn_info.subscriptions
        assert conn_info.connection_duration >= 0

    def test_connection_info_creation_without_user(self):
        websocket = MagicMock()
        conn_info = ConnectionInfo(
            websocket=websocket,
            client_id="test-client",
            user=None,
        )
        assert conn_info.client_id == "test-client"
        assert conn_info.user_role is None
        assert conn_info.username is None
        assert "all" in conn_info.subscriptions

    def test_connection_info_subscriptions(self):
        conn_info = ConnectionInfo(
            websocket=MagicMock(),
            client_id="test-client",
        )
        conn_info.subscriptions.add("threats")
        conn_info.subscriptions.add("alerts")

        assert "threats" in conn_info.subscriptions
        assert "alerts" in conn_info.subscriptions
        assert "all" in conn_info.subscriptions


class TestWebSocketManager:
    def test_initial_state(self):
        manager = WebSocketManager()
        assert manager._running is False
        assert len(manager._connections) == 0
        assert manager.max_connections == 100
        assert manager.heartbeat_interval == 30.0

    def test_initial_state_with_custom_params(self):
        manager = WebSocketManager(max_connections=50, heartbeat_interval=15.0)
        assert manager.max_connections == 50
        assert manager.heartbeat_interval == 15.0

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        manager = WebSocketManager()
        await manager.start()
        assert manager._running is True
        assert manager._heartbeat_task is not None
        assert manager._broadcast_task is not None

        await manager.stop()
        assert manager._running is False
        assert len(manager._connections) == 0

    @pytest.mark.asyncio
    async def test_connect_success(self):
        manager = WebSocketManager()
        websocket = AsyncMock()
        websocket.accept = AsyncMock()

        user = create_mock_user("testuser", "admin")
        connected = await manager.connect(
            websocket=websocket,
            client_id="test-client",
            user=user,
        )

        assert connected is True
        assert "test-client" in manager._connections
        websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_max_connections_reached(self):
        manager = WebSocketManager(max_connections=1)

        websocket1 = AsyncMock()
        websocket1.accept = AsyncMock()
        await manager.connect(websocket1, "client-1")

        websocket2 = AsyncMock()
        websocket2.close = AsyncMock()
        connected = await manager.connect(websocket2, "client-2")

        assert connected is False
        websocket2.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self):
        manager = WebSocketManager()
        websocket = AsyncMock()
        websocket.accept = AsyncMock()

        await manager.connect(websocket, "test-client")
        assert "test-client" in manager._connections

        await manager.disconnect("test-client")
        assert "test-client" not in manager._connections

    @pytest.mark.asyncio
    async def test_subscribe(self):
        manager = WebSocketManager()
        websocket = AsyncMock()
        websocket.accept = AsyncMock()

        await manager.connect(websocket, "test-client")
        result = await manager.subscribe("test-client", ["threats", "alerts"])

        assert result is True
        conn_info = manager._connections["test-client"]
        assert "threats" in conn_info.subscriptions
        assert "alerts" in conn_info.subscriptions

    @pytest.mark.asyncio
    async def test_subscribe_nonexistent_client(self):
        manager = WebSocketManager()
        result = await manager.subscribe("nonexistent", ["threats"])
        assert result is False

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        manager = WebSocketManager()
        websocket = AsyncMock()
        websocket.accept = AsyncMock()

        await manager.connect(websocket, "test-client")
        await manager.subscribe("test-client", ["threats", "alerts"])
        result = await manager.unsubscribe("test-client", ["alerts"])

        assert result is True
        conn_info = manager._connections["test-client"]
        assert "threats" in conn_info.subscriptions
        assert "alerts" not in conn_info.subscriptions

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self):
        manager = WebSocketManager()
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()

        await manager.connect(websocket, "test-client")
        websocket.send_text.reset_mock()

        delivered = await manager.broadcast(
            event_type=EventType.THREAT_DETECTED,
            data={"domain": "example.com"},
        )

        assert delivered == 1
        websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_with_channel_filter(self):
        manager = WebSocketManager()
        websocket1 = AsyncMock()
        websocket1.accept = AsyncMock()
        websocket1.send_text = AsyncMock()

        websocket2 = AsyncMock()
        websocket2.accept = AsyncMock()
        websocket2.send_text = AsyncMock()

        await manager.connect(websocket1, "client-1")
        await manager.connect(websocket2, "client-2")

        await manager.unsubscribe("client-2", ["all"])
        await manager.subscribe("client-2", ["alerts"])

        websocket1.send_text.reset_mock()
        websocket2.send_text.reset_mock()

        delivered = await manager.broadcast(
            event_type=EventType.THREAT_DETECTED,
            data={"domain": "example.com"},
            channel="threats",
        )

        assert delivered == 1
        websocket1.send_text.assert_called_once()
        websocket2.send_text.assert_not_called()

        websocket1.send_text.reset_mock()
        websocket2.send_text.reset_mock()

        delivered = await manager.broadcast(
            event_type=EventType.ALERT_CREATED,
            data={"message": "Test"},
            channel="alerts",
        )

        assert delivered == 2

    @pytest.mark.asyncio
    async def test_broadcast_exclude_client(self):
        manager = WebSocketManager()
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()

        await manager.connect(websocket, "test-client")
        websocket.send_text.reset_mock()

        delivered = await manager.broadcast(
            event_type=EventType.THREAT_DETECTED,
            data={"domain": "example.com"},
            exclude_client="test-client",
        )

        assert delivered == 0
        websocket.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_with_role_filter(self):
        manager = WebSocketManager()
        
        admin_ws = AsyncMock()
        admin_ws.accept = AsyncMock()
        admin_ws.send_text = AsyncMock()
        
        user_ws = AsyncMock()
        user_ws.accept = AsyncMock()
        user_ws.send_text = AsyncMock()
        
        viewer_ws = AsyncMock()
        viewer_ws.accept = AsyncMock()
        viewer_ws.send_text = AsyncMock()

        admin_user = create_mock_user("admin_user", "admin")
        user_user = create_mock_user("regular_user", "user")
        viewer_user = create_mock_user("viewer_user", "viewer")

        await manager.connect(admin_ws, "admin-client", user=admin_user)
        await manager.connect(user_ws, "user-client", user=user_user)
        await manager.connect(viewer_ws, "viewer-client", user=viewer_user)

        admin_ws.send_text.reset_mock()
        user_ws.send_text.reset_mock()
        viewer_ws.send_text.reset_mock()

        delivered = await manager.broadcast(
            event_type=EventType.ALERT_CREATED,
            data={"message": "Admin only alert"},
            min_role="admin",
        )

        assert delivered == 1
        admin_ws.send_text.assert_called_once()
        user_ws.send_text.assert_not_called()
        viewer_ws.send_text.assert_not_called()

        admin_ws.send_text.reset_mock()
        user_ws.send_text.reset_mock()
        viewer_ws.send_text.reset_mock()

        delivered = await manager.broadcast(
            event_type=EventType.THREAT_DETECTED,
            data={"message": "User and above"},
            min_role="user",
        )

        assert delivered == 2
        admin_ws.send_text.assert_called_once()
        user_ws.send_text.assert_called_once()
        viewer_ws.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_to_unauthenticated_clients(self):
        manager = WebSocketManager()
        
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()

        await manager.connect(websocket, "anon-client", user=None)
        websocket.send_text.reset_mock()

        delivered = await manager.broadcast(
            event_type=EventType.THREAT_DETECTED,
            data={"domain": "example.com"},
            min_role="viewer",
        )

        assert delivered == 0
        websocket.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_subscribe(self):
        manager = WebSocketManager()
        websocket = AsyncMock()
        websocket.accept = AsyncMock()

        await manager.connect(websocket, "test-client")
        response = await manager.handle_message(
            "test-client",
            json.dumps({"action": "subscribe", "channels": ["threats", "alerts"]}),
        )

        assert response["status"] == "subscribed"
        assert "threats" in response["channels"]

    @pytest.mark.asyncio
    async def test_handle_message_ping(self):
        manager = WebSocketManager()
        response = await manager.handle_message(
            "test-client",
            json.dumps({"action": "ping"}),
        )

        assert response["status"] == "pong"
        assert "timestamp" in response

    @pytest.mark.asyncio
    async def test_handle_message_invalid_json(self):
        manager = WebSocketManager()
        response = await manager.handle_message("test-client", "not json")

        assert response["status"] == "error"
        assert "Invalid JSON" in response["message"]

    @pytest.mark.asyncio
    async def test_handle_message_unknown_action(self):
        manager = WebSocketManager()
        response = await manager.handle_message(
            "test-client",
            json.dumps({"action": "unknown"}),
        )

        assert response["status"] == "error"
        assert "Unknown action" in response["message"]

    def test_get_stats(self):
        manager = WebSocketManager()
        user = create_mock_user("testuser", "admin")
        manager._connections["test-client"] = ConnectionInfo(
            websocket=MagicMock(),
            client_id="test-client",
            user=user,
        )

        stats = manager.get_stats()

        assert stats["total_connections"] == 1
        assert stats["max_connections"] == 100
        assert stats["is_running"] is False
        assert len(stats["connections"]) == 1
        assert stats["connections"][0]["client_id"] == "test-client"

    @pytest.mark.asyncio
    async def test_broadcast_queued(self):
        manager = WebSocketManager()
        await manager.start()

        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()

        await manager.connect(websocket, "test-client")

        await manager.broadcast_queued(
            EventType.THREAT_DETECTED,
            {"domain": "example.com"},
        )

        await asyncio.sleep(0.1)

        websocket.send_text.assert_called()

        await manager.stop()


class TestWebSocketManagerSingleton:
    def test_global_instance_exists(self):
        from backend.core.websocket_manager import ws_manager as manager
        assert manager is not None
        assert isinstance(manager, WebSocketManager)


class TestWebSocketIntegration:
    @pytest.mark.asyncio
    async def test_full_connection_lifecycle(self):
        manager = WebSocketManager()
        await manager.start()

        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()

        connected = await manager.connect(websocket, "test-client")
        assert connected is True

        await manager.subscribe("test-client", ["threats", "alerts"])

        delivered = await manager.broadcast(
            EventType.THREAT_DETECTED,
            {"domain": "malicious.com", "risk_score": "Critical"},
            channel="threats",
        )
        assert delivered == 1

        await manager.disconnect("test-client")
        assert "test-client" not in manager._connections

        await manager.stop()

    @pytest.mark.asyncio
    async def test_multiple_clients_broadcast(self):
        manager = WebSocketManager()

        websockets = []
        for i in range(3):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.send_text = AsyncMock()
            websockets.append(ws)
            await manager.connect(ws, f"client-{i}")

        for ws in websockets:
            ws.send_text.reset_mock()

        delivered = await manager.broadcast(
            EventType.SYSTEM_STATUS,
            {"status": "healthy", "uptime": 3600},
        )

        assert delivered == 3
        for ws in websockets:
            ws.send_text.assert_called_once()
