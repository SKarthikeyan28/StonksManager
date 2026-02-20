from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from src.database import Base, engine
from src.auth.routes import router as auth_router
from src.tasks.routes import router as tasks_router
from src.portfolios.routes import router as portfolios_router

# Import models so Base.metadata knows about all tables before create_all() runs
import src.auth.models  # noqa: F401
import src.portfolios.models  # noqa: F401

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all SQLite tables on startup — safe to re-run, no-op if tables exist
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="StonksManager Gateway", lifespan=lifespan)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS — allows the React frontend (different port/domain) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict to frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers
app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(portfolios_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "gateway"}