"""FastAPI interface. Clients choose fixtures, never actions or verdicts."""
from __future__ import annotations

import asyncio
import hmac
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from airlock.gateway import Gateway, ReviewConflict
from airlock.models import Metrics, ReviewResolution, Run, RunRequest, Scenario
from airlock.preset_attacks import get_presets
from airlock.proxy import ChatCompletionRequest, handle_chat_completion
from airlock.screen import ScreenRequest, screen_custom_input
from airlock.storage import Storage

load_dotenv(Path(__file__).resolve().parent / ".env")


def _positive_setting(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def create_app(*, storage=None, adapter=None, scenarios=None, review_token: Optional[str] = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application):
        if os.getenv("AIRLOCK_MODE", "live") != "live":
            raise RuntimeError("Only AIRLOCK_MODE=live is supported. Baseline is an explicitly labeled simulation.")
        from airlock.clocked_adapter import ClockedAdapter
        default_db = "sqlite:////tmp/airlock.db" if os.getenv("VERCEL") else "sqlite:///./airlock.db"
        current_storage = storage if storage is not None else Storage(os.getenv("DATABASE_URL", default_db))
        current_adapter = adapter if adapter is not None else ClockedAdapter()
        current_storage.recover_interrupted()
        application.state.storage = current_storage
        application.state.gateway = Gateway(current_storage, current_adapter, scenarios=scenarios)
        application.state.tasks = set()
        application.state.semaphore = asyncio.Semaphore(_positive_setting("AIRLOCK_CONCURRENCY", 2))
        application.state.rate_windows = defaultdict(deque)
        application.state.reviewer_token = review_token if review_token is not None else os.getenv("AIRLOCK_REVIEW_TOKEN", "")
        try:
            yield
        finally:
            tasks = list(application.state.tasks)
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            current_storage.recover_interrupted()
            if adapter is None:
                await current_adapter.aclose()
            if storage is None:
                current_storage.close()

    application = FastAPI(title="Agent Airlock", version="1.0.0", lifespan=lifespan, description="Synthetic agent replay with real Clocked security checks. No real scripts or messages execute.")
    origins = [origin.strip() for origin in os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").split(",") if origin.strip()]
    application.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization", "Last-Event-ID"])

    @application.middleware("http")
    async def response_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    def get_run_or_404(request: Request, run_id: str) -> Run:
        run = request.app.state.storage.get(run_id)
        if run is None:
            raise HTTPException(404, "run_not_found")
        return run

    def require_reviewer(request: Request, authorization: Optional[str] = Header(default=None)):
        expected = request.app.state.reviewer_token
        if not expected:
            raise HTTPException(503, "reviewer_auth_not_configured")
        prefix = "Bearer "
        supplied = authorization[len(prefix):] if authorization and authorization.startswith(prefix) else ""
        if not supplied or not hmac.compare_digest(supplied.encode(), expected.encode()):
            raise HTTPException(401, "reviewer_auth_required", headers={"WWW-Authenticate": "Bearer"})

    def reserve_budget(request: Request, protected: bool):
        if not protected:
            return
        windows = request.app.state.rate_windows
        now = time.monotonic()
        ip = request.client.host if request.client else "unknown"
        for name in list(windows):
            while windows[name] and windows[name][0] <= now - 3600:
                windows[name].popleft()
            if not windows[name]:
                del windows[name]
        pairs = [("global", _positive_setting("AIRLOCK_MAX_RUNS_PER_HOUR", 120)), ("ip:" + ip, _positive_setting("AIRLOCK_MAX_RUNS_PER_IP_HOUR", 30))]
        if any(len(windows[name]) >= limit for name, limit in pairs):
            raise HTTPException(429, "live_run_budget_exhausted", headers={"Retry-After": "3600"})
        for name, _ in pairs:
            windows[name].append(now)

    @application.get("/healthz")
    async def healthz():
        return {"status": "ok", "clocked_configured": bool(os.getenv("CLOCKED_API_KEY")), "mode": "live"}

    @application.get("/api/system/outbox")
    async def get_outbox(request: Request):
        return request.app.state.storage.list_outbox()

    @application.get("/api/system/tickets")
    async def get_tickets(request: Request):
        return request.app.state.storage.list_tickets()

    @application.post("/api/system/reset")
    async def reset_system_state(request: Request):
        request.app.state.storage.clear_system_state()
        return {"status": "ok", "cleared": True}

    @application.get("/api/presets")
    async def list_presets():
        return get_presets()

    @application.post("/api/screen")
    async def screen_input(payload: ScreenRequest, request: Request):
        return await screen_custom_input(request.app.state.gateway.adapter, payload)

    @application.get("/v1/models")
    async def list_models():
        return {
            "object": "list",
            "data": [
                {"id": "airlock-enforced", "object": "model", "owned_by": "airlock"},
                {"id": "gpt-4o-mini", "object": "model", "owned_by": "airlock"},
                {"id": "gpt-4o", "object": "model", "owned_by": "airlock"},
                {"id": "claude-3-5-sonnet", "object": "model", "owned_by": "airlock"},
            ],
        }

    @application.post("/v1/chat/completions")
    async def chat_completions(payload: ChatCompletionRequest, request: Request):
        from fastapi.responses import JSONResponse
        res = await handle_chat_completion(
            payload,
            request.app.state.gateway.adapter,
            request.app.state.storage,
        )
        if res.get("blocked"):
            return JSONResponse(
                status_code=res.get("status_code", 400),
                content={"error": res["error"]},
            )
        return JSONResponse(
            status_code=200,
            content=res["response"],
            headers=res.get("headers", {}),
        )

    @application.get("/api/scenarios", response_model=list[Scenario])
    async def list_scenarios(request: Request):
        order = {name: index for index, name in enumerate(["poisoned_document", "privacy_leak", "dangerous_script", "legitimate_request", "security_unavailable"])}
        return sorted(request.app.state.gateway.scenarios.values(), key=lambda scenario: order.get(scenario.id, 99))

    @application.post("/api/runs", response_model=Run, status_code=status.HTTP_202_ACCEPTED)
    async def create_run(payload: RunRequest, request: Request):
        gateway = request.app.state.gateway
        if payload.scenario_id not in gateway.scenarios:
            raise HTTPException(404, "scenario_not_found")
        if len(request.app.state.tasks) >= _positive_setting("AIRLOCK_MAX_PENDING_RUNS", 8):
            raise HTTPException(429, "run_queue_full", headers={"Retry-After": "5"})
        reserve_budget(request, payload.mode == "protected" and payload.scenario_id != "security_unavailable")
        run = gateway.create_run(payload.scenario_id, payload.mode)

        async def execute_queued():
            async with request.app.state.semaphore:
                await gateway.process(run.run_id)

        task = asyncio.create_task(execute_queued())
        request.app.state.tasks.add(task)
        task.add_done_callback(request.app.state.tasks.discard)
        return run

    @application.get("/api/runs", response_model=list[Run])
    async def list_runs(request: Request):
        return request.app.state.storage.list_runs()

    @application.get("/api/runs/{run_id}", response_model=Run)
    async def get_run(run_id: str, request: Request):
        return get_run_or_404(request, run_id)

    @application.get("/api/runs/{run_id}/events")
    async def stream_events(run_id: str, request: Request, last_event_id: Optional[str] = Header(default=None)):
        get_run_or_404(request, run_id)
        try:
            cursor = int(last_event_id or "0")
            if cursor < 0 or cursor > 100000000:
                raise ValueError
        except ValueError:
            raise HTTPException(400, "invalid_last_event_id")

        async def stream():
            nonlocal cursor
            heartbeat = time.monotonic()
            while not await request.is_disconnected():
                current = request.app.state.storage.get(run_id)
                if current is None:
                    return
                for event in current.events:
                    if event.id > cursor:
                        yield "id: " + str(event.id) + "\nevent: trace\ndata: " + event.model_dump_json() + "\n\n"
                        cursor = event.id
                if current.status != "RUNNING":
                    yield "event: complete\ndata: " + current.model_dump_json() + "\n\n"
                    return
                if time.monotonic() - heartbeat > 10:
                    yield ": heartbeat\n\n"
                    heartbeat = time.monotonic()
                await asyncio.sleep(0.15)

        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @application.get("/api/metrics", response_model=Metrics)
    async def get_metrics(request: Request):
        return request.app.state.storage.metrics()

    @application.get("/api/reviews", response_model=list[Run], dependencies=[Depends(require_reviewer)])
    async def list_reviews(request: Request):
        return request.app.state.storage.pending_reviews()

    @application.post("/api/reviews/{run_id}/resolve", response_model=Run, dependencies=[Depends(require_reviewer)])
    async def resolve_review(run_id: str, payload: ReviewResolution, request: Request):
        get_run_or_404(request, run_id)
        try:
            async with request.app.state.semaphore:
                return await request.app.state.gateway.resolve_review(run_id, payload)
        except ReviewConflict as conflict:
            raise HTTPException(409, str(conflict))

    out_candidates = [
        Path("/app/frontend/out"),
        Path(__file__).resolve().parents[1] / "frontend" / "out",
    ]
    static_dir = next((p for p in out_candidates if p.is_dir()), None)
    if static_dir is not None:
        next_static = static_dir / "_next"
        if next_static.is_dir():
            application.mount("/_next", StaticFiles(directory=str(next_static)), name="next_static")

        @application.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
        async def serve_static(request: Request, full_path: str):
            if full_path.startswith("api/") or full_path == "healthz":
                raise HTTPException(404, "not_found")
            if request.method not in ("GET", "HEAD"):
                raise HTTPException(404, "not_found")
            if not full_path:
                index_path = static_dir / "index.html"
                if index_path.is_file():
                    return FileResponse(index_path)
                raise HTTPException(404, "not_found")
            file_path = (static_dir / full_path).resolve()
            if not str(file_path).startswith(str(static_dir.resolve())):
                raise HTTPException(404, "not_found")
            if file_path.is_file():
                return FileResponse(file_path)
            html_path = static_dir / f"{full_path}.html"
            if html_path.is_file():
                return FileResponse(html_path)
            index_path = static_dir / full_path / "index.html"
            if index_path.is_file():
                return FileResponse(index_path)
            fallback = static_dir / "index.html"
            if fallback.is_file():
                return FileResponse(fallback)
            raise HTTPException(404, "not_found")

    return application


app = create_app()
