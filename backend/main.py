 
import threading
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.services.adguard_poller import poll_adguard
from backend.api.router import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background poller
    t = threading.Thread(target=poll_adguard, daemon=True)
    t.start()
    yield

app = FastAPI(title="Network Guardian AI Backend", lifespan=lifespan)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routes
app.include_router(router)

if __name__ == "__main__":
    if not settings.is_valid:
        print("WARNING: Missing environment variables. Please check .env file.")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
