import asyncio
import atexit
import json
import os
import threading
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.auth_router import router as auth_router
from backend.api.router import router
from backend.core.config import settings
from backend.db.database import close_db, init_db
from backend.scripts.knowledge_persistence import load_knowledge_base, save_knowledge_base
from backend.services.adguard_poller import poll_adguard
from backend.system_intelligence import display_system_intelligence
from backend.core.tenant_middleware import TenantMiddleware

from .core.websocket_manager import ws_manager


# Register shutdown handler for knowledge base persistence
def shutdown_handler():
    """Handle application shutdown to save knowledge base"""
    print("Saving knowledge base on shutdown...")
    save_knowledge_base()


# Register the shutdown handler
atexit.register(shutdown_handler)


# Rate Limiter Implementation
class RateLimiter:
    def __init__(self, limit: int = 10, window: int = 60):
        self.limit = limit
        self.window = window
        self.requests: dict[str, list] = {}

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        if key not in self.requests:
            self.requests[key] = []

        # Remove requests outside the time window
        self.requests[key] = [
            req_time for req_time in self.requests[key] if now - req_time < self.window
        ]

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
            media_type="application/json",
        )
    return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database on startup
    print("Initializing database...")
    await init_db()

    # Display system intelligence on startup
    print("\n" + "=" * 80)
    display_system_intelligence()
    print("=" * 80 + "\n")

    # Load knowledge base on startup
    print("Loading knowledge base...")
    load_knowledge_base()

    # Seed demo data if no threats exist
    from backend.core.state import automated_threats

    if not automated_threats:
        print("Seeding demo data...")
        import time

        from backend.core.utils import get_iso_timestamp
        from backend.logic.ml_heuristics import calculate_entropy, extract_domain_features

        domains = [
            (
                "api.stripe.com",
                "High",
                "Malware Pattern",
                "SOC GUARD ACTIVE: Suspicious payment gateway",
            ),
            ("cdn.jsdelivr.net", "Low", "Safe CDN", "Normal content delivery"),
            ("graph.facebook.com", "Medium", "Tracker", "Cross-site tracking beacon"),
            ("metrics.google.com", "Medium", "Analytics", "Usage telemetry detected"),
            ("push.apple.com", "Low", "Service Notification", "Normal APNS traffic"),
            ("tracker.ads.twitter.com", "High", "Adware", "Behavioral tracking detected"),
            ("location.services.android.com", "High", "Privacy Risk", "GPS location exfiltration"),
            ("firebaselogging.googleapis.com", "Medium", "Logger", "Firebase telemetry"),
            ("crashlytics.com", "Low", "Developer Tool", "Crash reporting service"),
            ("data.mongodb.com", "Medium", "Cloud Sync", "Database sync traffic"),
        ]

        # Also seed database for Isolation Forest training
        from backend.db.database import get_session
        from backend.db.repository import DomainRepository

        async def seed_database():
            async with get_session() as session:
                repo = DomainRepository(session, tenant_id=1)
                for i, (domain, risk, category, summary) in enumerate(domains):
                    entropy = calculate_entropy(domain)
                    features = extract_domain_features(domain)
                    analysis = {
                        "domain": domain,
                        "entropy": entropy,
                        "risk_score": risk,
                        "category": category,
                        "summary": summary,
                        "is_anomaly": i % 3 == 0,
                        "anomaly_score": round(0.8 + i * 0.02, 4) if i % 3 == 0 else 0.0,
                        "analysis_source": "demo_seed",
                        "timestamp": get_iso_timestamp(),
                        "features": {
                            "length": len(domain),
                            "digit_ratio": sum(c.isdigit() for c in domain) / max(len(domain), 1),
                            "vowel_ratio": sum(c.lower() in "aeiou" for c in domain)
                            / max(len(domain), 1),
                            "non_alphanumeric": sum(not c.isalnum() for c in domain),
                        },
                    }
                    await repo.create_domain_from_analysis(analysis)
                await session.commit()
                print(f"Seeded {len(domains)} demo threats to database")

        # Run database seeding in the existing event loop
        try:
            await seed_database()
        except Exception as e:
            print(f"Database seeding error: {e}")

        # NOTE: Don't seed automated_threats - only show LIVE AdGuard data

    # Blocklist Knowledge Base Initialization (non-blocking)
    def run_blocklist_init():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            from backend.services.blocklist_loader import blocklist_loader

            print("Starting initial blocklist sync (all sources)...")
            results = loop.run_until_complete(blocklist_loader.sync_all())
            for r in results:
                if r.success:
                    print(f"  ✓ {r.source}: {r.total_entries} entries")
                else:
                    print(f"  ✗ {r.source}: {r.error_message or 'Failed'}")
            total = sum(r.total_entries for r in results)
            print(f"Initial blocklist sync complete: {total} total entries")
        except Exception as e:
            print(f"Blocklist init error: {e}")
        finally:
            loop.close()

    if settings.BLOCKLIST_ENABLED:
        print("Blocklist knowledge base enabled. Initializing...")
        init_thread = threading.Thread(
            target=run_blocklist_init, daemon=True, name="blocklist-init"
        )
        init_thread.start()

        # Start background scheduler
        def blocklist_sync_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            while True:
                time.sleep(settings.BLOCKLIST_SYNC_INTERVAL)
                try:
                    from backend.services.blocklist_loader import blocklist_loader

                    results = loop.run_until_complete(blocklist_loader.sync_all())
                    total = sum(r.total_entries for r in results)
                    print(f"[Blocklist Scheduler] Sync complete: {total} entries")
                except Exception as e:
                    print(f"[Blocklist Scheduler] Error: {e}")

        scheduler_thread = threading.Thread(
            target=blocklist_sync_loop, daemon=True, name="blocklist-sync"
        )
        scheduler_thread.start()

    # Start WebSocket manager
    print("Starting WebSocket manager...")
    await ws_manager.start()

    # Start background poller only if configured
    if settings.has_adguard:
        print("AdGuard configured. Starting poller...")
        t = threading.Thread(target=poll_adguard, daemon=True)
        t.start()
    else:
        print("AdGuard NOT configured. Poller disabled.")
    yield

    # Stop WebSocket manager on shutdown
    print("Stopping WebSocket manager...")
    await ws_manager.stop()

    # Close database connections
    print("Closing database connections...")
    await close_db()

    # Save knowledge base on shutdown
    print("Saving knowledge base...")
    save_knowledge_base()


app = FastAPI(title="Network Guardian AI Backend", lifespan=lifespan)

# Add rate limiting middleware
app.middleware("http")(rate_limit_middleware)

# Add tenant identification middleware
app.add_middleware(TenantMiddleware)

# CORS Configuration - Use specific origins from config for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include Routes - MUST be at the top to avoid shadowing
app.include_router(router)

# Include Auth Routes
app.include_router(auth_router)

# Include Stats Routes
from backend.api.stats import router as stats_router

app.include_router(stats_router, prefix="/api/stats")

# Include WebSocket Routes
from .api.ws_router import router as ws_router

app.include_router(ws_router, prefix="")

# Include Blocklist Routes
try:
    from backend.api.blocklist_router import router as blocklist_router

    app.include_router(blocklist_router, prefix="/blocklist")
    print("Blocklist router included")
except ImportError as e:
    print(f"Blocklist router not available: {e}")

# Include ML Enhancement Routes
try:
    from backend.api.ml_router import router as ml_router

    app.include_router(ml_router)
    print("ML router included")
except ImportError as e:
    print(f"ML router not available: {e}")

# Include Tenant Management Routes
try:
    from backend.api.tenant_router import router as tenant_router

    app.include_router(tenant_router)
    print("Tenant router included")
except ImportError as e:
    print(f"Tenant router not available: {e}")

# Include Billing Routes
try:
    from backend.api.billing_router import router as billing_router

    app.include_router(billing_router)
    print("Billing router included")
except ImportError as e:
    print(f"Billing router not available: {e}")

# Include Registration Routes
try:
    from backend.api.registration_router import router as registration_router

    app.include_router(registration_router)
    print("Registration router included")
except ImportError as e:
    print(f"Registration router not available: {e}")

# Include Developer Portal Routes
try:
    from backend.api.developer_router import router as developer_router

    app.include_router(developer_router)
    print("Developer router included")
except ImportError as e:
    print(f"Developer router not available: {e}")


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/models")
def api_list_models():
    """SRE Discovery: List available models (Gemini + Ollama)."""
    from backend.core.config import settings
    from backend.services.gemini_analyzer import get_available_models
    from backend.services.ollama_analyzer import get_ollama_models

    models = []

    # Add Gemini models
    gemini_models = get_available_models()
    for m in gemini_models:
        models.append({"id": m, "provider": "gemini", "name": m})

    # Add Ollama models (if enabled)
    if settings.OLLAMA_ENABLED:
        ollama_models = get_ollama_models()
        for m in ollama_models:
            models.append({"id": f"ollama:{m}", "provider": "ollama", "name": m})

    return models


# Serve Frontend Static Files from Vite build output
backend_dir = os.path.dirname(__file__)
possible_paths = [
    os.path.join(backend_dir, "static"),
    os.path.join(backend_dir, "..", "frontend", "dist"),
]
frontend_dist = None
for path in possible_paths:
    if path and os.path.exists(path):
        frontend_dist = path
        break

if frontend_dist:
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    vite_svg_path = os.path.join(frontend_dist, "vite.svg")
    if os.path.exists(vite_svg_path):

        @app.get("/vite.svg")
        async def serve_vite_svg():
            from fastapi.responses import FileResponse

            return FileResponse(vite_svg_path)
else:
    print(
        f"WARNING: Frontend dist directory not found. Checked paths: {possible_paths}. Frontend will not be served."
    )


async def frontend_middleware(request: Request, call_next):
    if request.method == "GET" and not any(
        request.url.path.startswith(p)
        for p in [
            "/api/",
            "/alerts/",
            "/assets/",
            "/blocklist",
            "/database/",
            "/auth/",
            "/billing/",
            "/developer/",
            "/ws/",
            "/health",
            "/models",
            "/analyze",
            "/chat",
            "/history",
            "/system-chat",
            "/tenants",
            "/vite.svg",
        ]
    ):
        if frontend_dist:
            from fastapi.responses import FileResponse

            index_path = os.path.join(frontend_dist, "index.html")
            return FileResponse(index_path)
    return await call_next(request)


app.middleware("http")(frontend_middleware)


if __name__ == "__main__":
    if not settings.is_valid:
        print("WARNING: Missing environment variables. Please check .env file.")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
