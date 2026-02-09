 
import threading
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.services.adguard_poller import poll_adguard
from backend.api.router import router
from typing import Dict
import time

from typing import Dict
import time
import json

# Rate Limiter Implementation
class RateLimiter:
    def __init__(self, limit: int = 10, window: int = 60):
        self.limit = limit
        self.window = window
        self.requests: Dict[str, list] = {}

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove requests outside the time window
        self.requests[key] = [req_time for req_time in self.requests[key] if now - req_time < self.window]
        
        if len(self.requests[key]) < self.limit:
            self.requests[key].append(now)
            return True
        return False

rate_limiter = RateLimiter(limit=100, window=60)

async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        return Response(
            status_code=429,
            content=json.dumps({"detail": "Rate limit exceeded. Try again later."}),
            media_type="application/json"
        )
    return await call_next(request)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background poller only if configured
    if settings.has_adguard:
        print("AdGuard configured. Starting poller...")
        t = threading.Thread(target=poll_adguard, daemon=True)
        t.start()
    else:
        print("AdGuard NOT configured. Poller disabled.")
    yield

app = FastAPI(title="Network Guardian AI Backend", lifespan=lifespan)

# Add rate limiting middleware
app.middleware("http")(rate_limit_middleware)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import json

# Include Routes
app.include_router(router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Serve Frontend Static Files
static_dir = os.path.join(os.path.dirname(__file__), "static")
assets_dir = os.path.join(static_dir, "assets")

if os.path.exists(static_dir):
    # Mount assets directory if it exists (Vite build output)
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    track e
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        # Serve API routes first (already handled by router above)
        if full_path.startswith("api"):
            return {"error": "API route not found"}
            
        # Serve static files if they exist directly
        file_path = os.path.join(static_dir, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # Fallback to index.html for React Router
        return FileResponse(os.path.join(static_dir, "index.html"))
else:
    print(f"WARNING: Static directory not found at {static_dir}. Frontend will not be served.")

if __name__ == "__main__":
    if not settings.is_valid:
        print("WARNING: Missing environment variables. Please check .env file.")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
