from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.limiter import limiter
from api.routes.ingest import router as ingest_router
from api.routes.dashboard import router as dashboard_router
from api.routes.alerts import router as alerts_router
from api.routes.debug import router as debug_router
from api.routes.compliance import router as compliance_router
from api.routes.traces import router as traces_router
from api.routes.billing import router as billing_router
from api.routes.waitlist import router as waitlist_router
from pipeline.worker import start_worker, stop_worker
from storage.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await start_worker()
    yield
    await stop_worker()


app = FastAPI(title="LLM Observability MVP", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(dashboard_router)
app.include_router(alerts_router)
app.include_router(debug_router)
app.include_router(compliance_router)
app.include_router(traces_router)
app.include_router(billing_router)
app.include_router(waitlist_router)


# Public entry point: landing page. Dashboard moves to /dashboard.
@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("dashboard/landing.html")


@app.get("/dashboard", include_in_schema=False)
async def dashboard_page():
    return FileResponse("dashboard/index.html")


# Serve all other static files (debug.html, traces.html, compliance.html, assets)
app.mount("/", StaticFiles(directory="dashboard", html=True), name="dashboard")
