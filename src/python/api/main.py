"""FastAPI application for the HITL UI backend."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.python.api.routers import auth, phases, workflows
from src.python.utils.database import init_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    init_tables()
    yield


app = FastAPI(
    title="Claude Clinical Bridge API",
    description="Human-in-the-Loop UI backend for clinical documentation pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for React dev server (Vite runs on 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(workflows.router)
app.include_router(phases.router)


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
