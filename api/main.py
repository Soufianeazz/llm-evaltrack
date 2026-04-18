from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

MAX_BODY_BYTES = 256 * 1024  # 256 KB


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body exceeds {MAX_BODY_BYTES} bytes"},
            )
        return await call_next(request)

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

app.add_middleware(BodySizeLimitMiddleware)

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


# Clean-URL SEO comparison pages (no .html suffix — better for sharing + rankings)
@app.get("/vs/langsmith", include_in_schema=False)
async def vs_langsmith():
    return FileResponse("dashboard/vs/langsmith.html")


@app.get("/vs/langfuse", include_in_schema=False)
async def vs_langfuse():
    return FileResponse("dashboard/vs/langfuse.html")


@app.get("/vs/helicone", include_in_schema=False)
async def vs_helicone():
    return FileResponse("dashboard/vs/helicone.html")


@app.get("/alternatives/datadog-llm", include_in_schema=False)
async def alt_datadog_llm():
    return FileResponse("dashboard/alternatives/datadog-llm.html")


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap():
    return FileResponse("dashboard/sitemap.xml", media_type="application/xml")


@app.get("/robots.txt", include_in_schema=False)
async def robots():
    return FileResponse("dashboard/robots.txt", media_type="text/plain")


# Serve all other static files (debug.html, traces.html, compliance.html, assets)
app.mount("/", StaticFiles(directory="dashboard"), name="dashboard")
