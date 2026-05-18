import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
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
from api.routes.health import router as health_router
from api.routes.alerts import router as alerts_router
from api.routes.debug import router as debug_router
from api.routes.compliance import router as compliance_router
from api.routes.traces import router as traces_router
from api.routes.billing import router as billing_router
from api.routes.waitlist import router as waitlist_router
from api.routes.demo import router as demo_router
from api.routes.admin import router as admin_router, seed_demo_on_startup
from api.routes.portal_auth import router as portal_auth_router, admin_router as portal_admin_router
from api.routes.self_host import router as self_host_router
from pipeline.worker import start_worker, stop_worker
from storage.database import init_db


_AIRGAP_EGRESS_VARS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "RESEND_API_KEY",
    "SENDGRID_API_KEY",
    "DEMO_REQUEST_WEBHOOK_URL",
    "SIGNUP_NOTIFY_WEBHOOK_URL",
    "BILLING_EVENT_WEBHOOK_URL",
)


def _enforce_airgap() -> None:
    """When AGENTLENS_AIRGAP=1, hard-clear every env var that any code path could
    use to reach an external service. This is defense-in-depth on top of the
    per-call-site checks in pipeline/worker.py and the empty defaults in
    .env.airgap.example. the pilot customer's hard requirement is zero outbound; one stray
    env var must never be enough to break that promise."""
    if os.environ.get("AGENTLENS_AIRGAP", "").strip().lower() not in ("1", "true", "yes"):
        return
    import logging
    log = logging.getLogger("airgap")
    cleared = []
    for var in _AIRGAP_EGRESS_VARS:
        if os.environ.pop(var, None):
            cleared.append(var)
    log.warning("AGENTLENS_AIRGAP=1 active — cleared egress env vars: %s", cleared or "none set")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _enforce_airgap()
    await init_db()
    try:
        await seed_demo_on_startup()
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger("startup").warning("seed_demo_on_startup failed (non-fatal): %s", exc)
    await start_worker()
    yield
    await stop_worker()


app = FastAPI(title="LLM Observability MVP", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(BodySizeLimitMiddleware)


def _allowed_cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ALLOWED_ORIGINS", "").strip()
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return [
        "https://www.agentlens.one",
        "https://agentlens.one",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'; "
        "form-action 'self'"
    )
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if response.headers.get("content-type", "").startswith("application/json"):
        response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(ingest_router)
app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(alerts_router)
app.include_router(debug_router)
app.include_router(compliance_router)
app.include_router(traces_router)
app.include_router(billing_router)
app.include_router(waitlist_router)
app.include_router(demo_router)
app.include_router(admin_router)
app.include_router(portal_auth_router)
app.include_router(portal_admin_router)
app.include_router(self_host_router)


# Public entry point: landing page. Dashboard moves to /dashboard.
@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("dashboard/landing.html")


@app.api_route("/dashboard", methods=["GET", "HEAD"], include_in_schema=False)
async def dashboard_page():
    return FileResponse("dashboard/index.html")


# Clean-URL SEO comparison pages (no .html suffix — better for sharing + rankings).
# Pages are generated by scripts/generate_seo_pages.py — single template, all
# competitors live in COMPETITORS dict there. Adding a new competitor = edit
# that dict + add a route here.

@app.api_route("/vs/{slug}", methods=["GET", "HEAD"], include_in_schema=False)
async def vs_page(slug: str):
    allowed = {"langsmith", "langfuse", "helicone", "arize-phoenix", "portkey", "lunary"}
    if slug not in allowed:
        return JSONResponse(status_code=404, content={"detail": "comparison page not found"})
    return FileResponse(f"dashboard/vs/{slug}.html")


@app.api_route("/alternatives/{slug}", methods=["GET", "HEAD"], include_in_schema=False)
async def alternatives_page(slug: str):
    allowed = {"langsmith", "langfuse", "helicone", "datadog-llm"}
    if slug not in allowed:
        return JSONResponse(status_code=404, content={"detail": "alternatives page not found"})
    return FileResponse(f"dashboard/alternatives/{slug}.html")


@app.api_route("/impressum", methods=["GET", "HEAD"], include_in_schema=False)
async def impressum():
    return FileResponse("dashboard/impressum.html")


@app.api_route("/datenschutz", methods=["GET", "HEAD"], include_in_schema=False)
async def datenschutz():
    return FileResponse("dashboard/datenschutz.html")


@app.api_route("/nutzungsbedingungen", methods=["GET", "HEAD"], include_in_schema=False)
async def nutzungsbedingungen():
    return FileResponse("dashboard/nutzungsbedingungen.html")


@app.api_route("/success", methods=["GET", "HEAD"], include_in_schema=False)
async def success():
    return FileResponse("dashboard/success.html")


@app.api_route("/book-demo", methods=["GET", "HEAD"], include_in_schema=False)
async def book_demo():
    return FileResponse("dashboard/book-demo.html")


@app.api_route("/app", methods=["GET", "HEAD"], include_in_schema=False)
async def app_portal():
    return FileResponse("dashboard/app.html")


@app.api_route("/app/start", methods=["GET", "HEAD"], include_in_schema=False)
async def app_start():
    return FileResponse("dashboard/start.html")


@app.api_route("/app/deploy", methods=["GET", "HEAD"], include_in_schema=False)
async def app_deploy():
    return FileResponse("dashboard/deploy.html")


def _serve_shell_script(path: str, filename: str) -> Response:
    """Serve a shell script, stripping any CRs that may have crept in from a
    Windows checkout. `curl ... | bash` is unforgiving about CR — `\\r` on the
    shebang or after a command name produces `bash\\r: No such file or
    directory` or `$'\\r': command not found` and breaks every pilot install."""
    try:
        with open(path, "rb") as f:
            body = f.read()
    except FileNotFoundError:
        return JSONResponse(
            status_code=500,
            content={"detail": f"installer asset missing: {path}"},
        )
    body = body.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return Response(
        content=body,
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f"inline; filename={filename}",
        },
    )


@app.get("/install", include_in_schema=False)
async def install_script():
    """Serves the self-host installer. Used by:  curl -fsSL https://www.agentlens.one/install | bash"""
    return _serve_shell_script("scripts/install.sh", "install.sh")


@app.get("/install.sh", include_in_schema=False)
async def install_script_sh():
    return await install_script()


@app.get("/uninstall", include_in_schema=False)
async def uninstall_script():
    """Serves the self-host uninstaller. Usage:  curl -fsSL https://www.agentlens.one/uninstall | bash"""
    return _serve_shell_script("scripts/uninstall.sh", "uninstall.sh")


@app.get("/uninstall.sh", include_in_schema=False)
async def uninstall_script_sh():
    return await uninstall_script()


@app.get("/case-study", include_in_schema=False)
async def case_study():
    return FileResponse("dashboard/case_study.html")


@app.get("/security", include_in_schema=False)
async def security_page():
    return FileResponse("dashboard/security.html")


@app.get("/subprocessors", include_in_schema=False)
async def subprocessors_page():
    return FileResponse("dashboard/subprocessors.html")


@app.get("/enterprise", include_in_schema=False)
async def enterprise_page():
    return FileResponse("dashboard/enterprise.html")


@app.get("/security-questionnaire", include_in_schema=False)
async def security_questionnaire_page():
    return FileResponse("dashboard/security-questionnaire.html")


@app.get("/sla", include_in_schema=False)
async def sla_page():
    return FileResponse("dashboard/sla.html")


@app.get("/legal-pack", include_in_schema=False)
async def legal_pack_page():
    return FileResponse("dashboard/legal-pack.html")


@app.get("/security-questionnaire-v2", include_in_schema=False)
async def security_questionnaire_v2_page():
    return FileResponse("dashboard/security-questionnaire-v2.html")


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap():
    return FileResponse("dashboard/sitemap.xml", media_type="application/xml")


@app.get("/robots.txt", include_in_schema=False)
async def robots():
    return FileResponse("dashboard/robots.txt", media_type="text/plain")


# Serve all other static files (debug.html, traces.html, compliance.html, assets)
app.mount("/", StaticFiles(directory="dashboard"), name="dashboard")
