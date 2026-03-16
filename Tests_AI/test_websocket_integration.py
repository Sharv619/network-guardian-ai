#!/usr/bin/env python3
"""
Test script to verify WebSocket integration in Network Guardian AI
"""

import asyncio
import json
from typing import Dict, Any
import websockets
import threading
import time
from fastapi import FastAPI
from backend.main import app as fastapi_app
import uvicorn

# Global flag to track server status
server_running = False


def start_server():
    """Start the FastAPI server in a separate thread"""
    global server_running
    server_running = True

    # Start the Uvicorn server
    config = uvicorn.Config(
        fastapi_app, host="127.0.0.1", port=8000, log_level="info", loop="asyncio"
    )
    server = uvicorn.Server(config)

    # Run the server
    import asyncio
    import signal

    # Set up event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def serve():
        await server.serve()

    loop.run_until_complete(serve())


async def test_websocket_connection():
    """Test WebSocket connection and basic functionality"""
    print("Testing WebSocket connection...")

    try:
        # Connect to the public WebSocket endpoint
        uri = "ws://localhost:8000/ws/public"
        async with websockets.connect(uri) as websocket:
            print("✓ Connected to WebSocket server")

            # Send a test subscription message
            subscribe_msg = {"action": "subscribe", "channels": ["system", "alerts"]}
            await websocket.send(json.dumps(subscribe_msg))

            # Receive the response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response_data = json.loads(response)
            print(f"✓ Subscription response: {response_data}")

            # Test sending a ping
            ping_msg = {"action": "ping"}
            await websocket.send(json.dumps(ping_msg))
            ping_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            ping_data = json.loads(ping_response)
            print(f"✓ Ping response: {ping_data}")

            print("✓ WebSocket integration test passed!")
            return True

    except asyncio.TimeoutError:
        print("✗ WebSocket test timed out")
        return False
    except Exception as e:
        print(f"✗ WebSocket test failed: {str(e)}")
        return False


async def run_tests():
    """Run all WebSocket integration tests"""
    print("Starting WebSocket integration tests...")

    # Wait a moment for server to start if needed
    await asyncio.sleep(2)

    # Run the WebSocket connection test
    success = await test_websocket_connection()

    if success:
        print("\n✓ All WebSocket integration tests passed!")
    else:
        print("\n✗ Some WebSocket integration tests failed!")

    return success


if __name__ == "__main__":
    # Start server in a separate thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Wait for server to start
    time.sleep(3)

    # Run tests
    try:
        result = asyncio.run(run_tests())
        if not result:
            exit(1)
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\nError running tests: {str(e)}")
        exit(1)
