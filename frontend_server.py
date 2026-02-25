#!/usr/bin/env python3
"""
Simple Python-based dashboard server for Network Guardian AI
Serves the React frontend and provides API proxy to backend
"""

from flask import Flask, send_from_directory, jsonify, request
import requests
import os
import json
from pathlib import Path

app = Flask(__name__, static_folder="frontend/dist", template_folder="frontend/dist")

# Backend API URL
BACKEND_URL = "http://localhost:8000"


@app.route("/")
def serve_frontend():
    """Serve the React frontend"""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    """Serve static files (CSS, JS, etc.)"""
    return send_from_directory(app.static_folder, filename)


@app.route("/api/stats/system")
def proxy_system_stats():
    """Proxy the system stats API from backend"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/stats/system", timeout=10)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Backend API error: {str(e)}"}), 503


@app.route("/api/<path:path>")
def proxy_backend_api(path):
    """Proxy other backend API endpoints"""
    try:
        # Forward the request to backend (path already includes the correct route)
        url = f"{BACKEND_URL}/{path}"
        method = request.method
        headers = {k: v for k, v in request.headers if k.lower() not in ["host", "connection"]}

        if method == "GET":
            response = requests.get(url, headers=headers, params=request.args, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=request.get_json(), timeout=10)
        else:
            return jsonify({"error": "Method not supported"}), 405

        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Backend API error: {str(e)}"}), 503


if __name__ == "__main__":
    # Check if frontend build exists
    frontend_dist = Path("frontend/dist")
    if not frontend_dist.exists():
        print("Error: Frontend build directory not found!")
        print("Please build the frontend first:")
        print("cd frontend && npm run build")
        exit(1)

    print("🚀 Starting Network Guardian Dashboard Server...")
    print(f"📊 Backend API: {BACKEND_URL}")
    print(f"🌐 Frontend: http://localhost:5000")
    print(f"📈 System Stats: http://localhost:5000/api/stats/system")

    app.run(host="0.0.0.0", port=5000, debug=False)
