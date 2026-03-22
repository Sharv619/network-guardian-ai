"""
WebSocket Router for Real-Time Communication.

This module provides:
- WebSocket endpoint for live threat updates
- JWT token and API Key authentication for WebSocket connections
- Channel-based subscriptions for different event types
- Role-based access control for broadcasts
"""

import uuid

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from backend.core.auth import UserRole
from backend.core.deps import (
    AuthenticatedUser,
    generate_client_id,
    get_current_user_ws,
    require_admin,
)
from backend.core.logging_config import get_logger
from backend.core.websocket_manager import EventType, WebSocketMessage, ws_manager

logger = get_logger(__name__)


async def _extract_tenant_id_from_websocket(websocket: WebSocket) -> int:
    """
    Extract tenant ID from a WebSocket connection using various methods.
    Returns the tenant ID if found, defaults to 1 for backward compatibility.
    """
    # Method 1: Subdomain extraction
    # Format: tenant1.app.domain.com -> tenant1
    host = websocket.url.hostname or ""
    if host and "." in host:
        subdomain = host.split(".")[0]
        if subdomain not in ["www", "app", "api", "localhost"]:
            # Look up tenant by subdomain
            try:
                from sqlalchemy import select

                from ..db.database import get_session
                from ..db.models import Tenant

                async def get_tenant_by_subdomain():
                    async with get_session() as session:
                        result = await session.execute(
                            select(Tenant.id).where(Tenant.subdomain == subdomain, Tenant.is_active)
                        )
                        tenant = result.scalar_one_or_none()
                        return tenant.id if tenant else None

                # Run the async function
                tenant_id = await get_tenant_by_subdomain()
                if tenant_id:
                    return tenant_id
            except Exception:
                # If database lookup fails, continue to other methods
                pass

    # Method 2: Custom headers
    tenant_id_header = websocket.headers.get("X-Tenant-ID")
    if tenant_id_header:
        try:
            return int(tenant_id_header)
        except ValueError:
            pass

    api_key_header = websocket.headers.get("X-Tenant-API-Key")
    if api_key_header:
        try:
            from sqlalchemy import select

            from ..db.database import get_session
            from ..db.models import Tenant

            async def get_tenant_by_api_key():
                async with get_session() as session:
                    result = await session.execute(
                        select(Tenant.id).where(Tenant.api_key == api_key_header, Tenant.is_active)
                    )
                    tenant = result.scalar_one_or_none()
                    return tenant.id if tenant else None

            tenant_id = await get_tenant_by_api_key()
            if tenant_id:
                return tenant_id
        except Exception:
            pass

    # Method 3: Query parameter
    api_key_param = websocket.query_params.get("api_key")
    if api_key_param:
        try:
            from sqlalchemy import select

            from ..db.database import get_session
            from ..db.models import Tenant

            async def get_tenant_by_api_key_param():
                async with get_session() as session:
                    result = await session.execute(
                        select(Tenant.id).where(Tenant.api_key == api_key_param, Tenant.is_active)
                    )
                    tenant = result.scalar_one_or_none()
                    return tenant.id if tenant else None

            tenant_id = await get_tenant_by_api_key_param()
            if tenant_id:
                return tenant_id
        except Exception:
            pass

    # Method 4: Default tenant for development/testing
    # In production, this should be removed or disabled
    import os

    if os.getenv("ENVIRONMENT", "production").lower() == "development":
        # Return a default tenant ID (1) for development
        return 1

    return 1


router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None),
    api_key: str | None = Query(None, alias="api_key"),
):
    """
    WebSocket endpoint for real-time updates (authenticated).

    Authentication:
    - Pass JWT token as query parameter: ?token=YOUR_JWT_TOKEN
    - Or pass API key as query parameter: ?api_key=YOUR_API_KEY

    Message Format (Client -> Server):
    {
        "action": "subscribe" | "unsubscribe" | "ping",
        "channels": ["threats", "alerts", "system"]  # for subscribe/unsubscribe
    }

    Message Format (Server -> Client):
    {
        "event_type": "threat_detected" | "alert_created" | ...,
        "data": {...},
        "timestamp": "2024-01-20T12:00:00+00:00",
        "correlation_id": "optional-correlation-id"
    }

    Available Channels:
    - "all": All events (default)
    - "threats": Threat detection events
    - "alerts": Alert notifications
    - "system": System status updates
    - "anomalies": Anomaly detection events
    - "analysis": Domain analysis results
    """
    user = await get_current_user_ws(websocket, token, api_key)

    if not user:
        await websocket.close(code=4001, reason="Unauthorized - Invalid or missing token/api_key")
        logger.warning("WebSocket authentication failed", extra={"client_id": None})
        return

    # Extract tenant ID from the WebSocket connection
    tenant_id = await _extract_tenant_id_from_websocket(websocket)

    client_id = generate_client_id(user)

    connected = await ws_manager.connect(
        websocket=websocket,
        client_id=client_id,
        user=user,
        tenant_id=tenant_id,
    )

    if not connected:
        return

    try:
        while True:
            message = await websocket.receive_text()
            response = await ws_manager.handle_message(client_id, message)

            if response:
                msg = WebSocketMessage(
                    event_type=EventType.CONNECTION_ACK,
                    data=response,
                    correlation_id=client_id,
                )
                await websocket.send_text(msg.to_json())

    except WebSocketDisconnect:
        logger.info(
            "Client disconnected", extra={"client_id": client_id, "username": user.identity}
        )
    except Exception as e:
        logger.error("WebSocket error", extra={"client_id": client_id, "error": str(e)})
    finally:
        await ws_manager.disconnect(client_id)


@router.websocket("/ws/public")
async def websocket_public_endpoint(websocket: WebSocket):
    """
    Public WebSocket endpoint (limited access).

    This endpoint allows unauthenticated connections with read-only access
    to public events only (system status, public alerts).

    Users connecting to this endpoint get viewer role by default.
    Recommended for dashboards that don't require user authentication.
    """
    client_id = f"public_{uuid.uuid4().hex[:8]}"

    connected = await ws_manager.connect(
        websocket=websocket,
        client_id=client_id,
        user=None,
    )

    if not connected:
        return

    # Subscribe to public channels including threats for real-time dashboard
    await ws_manager.subscribe(client_id, ["system", "alerts", "threats", "anomalies"])

    try:
        while True:
            message = await websocket.receive_text()
            response = await ws_manager.handle_message(client_id, message)

            if response:
                msg = WebSocketMessage(
                    event_type=EventType.CONNECTION_ACK,
                    data=response,
                    correlation_id=client_id,
                )
                await websocket.send_text(msg.to_json())

    except WebSocketDisconnect:
        logger.info("Public client disconnected", extra={"client_id": client_id})
    except Exception as e:
        logger.error("Public WebSocket error", extra={"client_id": client_id, "error": str(e)})
    finally:
        await ws_manager.disconnect(client_id)


@router.websocket("/ws/admin")
async def websocket_admin_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None),
    api_key: str | None = Query(None, alias="api_key"),
):
    """
    Admin-only WebSocket endpoint.

    Requires admin role to connect. Receives all broadcasts including
    admin-only notifications.

    Authentication:
    - Pass JWT token as query parameter: ?token=YOUR_JWT_TOKEN
    - Or pass API key as query parameter: ?api_key=YOUR_API_KEY
    """
    user = await get_current_user_ws(websocket, token, api_key)

    if not user:
        await websocket.close(code=4001, reason="Unauthorized - Invalid or missing token/api_key")
        return

    if user.role != UserRole.ADMIN:
        await websocket.close(code=4003, reason="Forbidden - Admin access required")
        logger.warning(
            "WebSocket admin access denied",
            extra={"client_id": None, "username": user.identity, "role": user.role},
        )
        return

    client_id = f"admin_{generate_client_id(user)}"

    connected = await ws_manager.connect(
        websocket=websocket,
        client_id=client_id,
        user=user,
    )

    if not connected:
        return

    try:
        while True:
            message = await websocket.receive_text()
            response = await ws_manager.handle_message(client_id, message)

            if response:
                msg = WebSocketMessage(
                    event_type=EventType.CONNECTION_ACK,
                    data=response,
                    correlation_id=client_id,
                )
                await websocket.send_text(msg.to_json())

    except WebSocketDisconnect:
        logger.info(
            "Admin client disconnected", extra={"client_id": client_id, "username": user.identity}
        )
    except Exception as e:
        logger.error("Admin WebSocket error", extra={"client_id": client_id, "error": str(e)})
    finally:
        await ws_manager.disconnect(client_id)


@router.get("/ws/stats")
async def get_websocket_stats(current_user: AuthenticatedUser = Depends(require_admin)):
    """Get WebSocket connection statistics (admin only)."""
    return ws_manager.get_stats()
