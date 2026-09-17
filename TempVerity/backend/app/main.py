from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime, timezone
from pathlib import Path
from random import randint

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from .core.config import get_settings
from .db import Base, SessionLocal, engine, get_db
from .auth import COOKIE_NAME, auth_enabled, configure_auth, current_user, ensure_admin, login, session_lifetime_minutes
from .models import Device, User
from .schemas import AlertAcknowledge, AlertRead, AuthConfigure, BootstrapResponse, ControlRequest, DeviceCreate, DeviceSnapshot, DeviceUpdate, EventRead, LoginRequest, NotificationRead, SettingPatch, ZoneSnapshot
from .services import AppService

settings = get_settings()
APP_VERSION = settings.app_version
SUPPORT_EMAIL = settings.support_email

app = FastAPI(title=settings.app_name, version=APP_VERSION)
poller_task: asyncio.Task[None] | None = None
notification_task: asyncio.Task[None] | None = None
historical_report_task: asyncio.Task[None] | None = None
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
assets_dir = settings.frontend_dist / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")


@app.on_event("startup")
def on_startup() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        if "users" in inspect(connection).get_table_names():
            columns = {column["name"] for column in inspect(connection).get_columns("users")}
            if "role" not in columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(24) NOT NULL DEFAULT 'admin'"))
        if "alerts" in inspect(connection).get_table_names():
            columns = {column["name"] for column in inspect(connection).get_columns("alerts")}
            additions = {
                "condition_key": "VARCHAR(160) NOT NULL DEFAULT ''",
                "recovery_started_at": "DATETIME",
                "acknowledged_at": "DATETIME",
                "acknowledged_by": "INTEGER",
                "acknowledgement_comment": "TEXT",
            }
            for name, definition in additions.items():
                if name not in columns:
                    connection.execute(text(f"ALTER TABLE alerts ADD COLUMN {name} {definition}"))
    with SessionLocal() as session:
        service = AppService(session)
        service.seed_if_empty()
        ensure_admin(session)


async def poll_one(device_id: str) -> None:
    await asyncio.sleep(randint(0, 12))
    with SessionLocal() as session:
        await AppService(session).poll_device(device_id)


async def poll_loop() -> None:
    while True:
        with SessionLocal() as session:
            devices = list(session.scalars(select(Device)).all())
            now = datetime.now(timezone.utc)
            device_ids = []
            for device in devices:
                if device.last_seen_at is None:
                    device_ids.append(device.id)
                    continue
                last_seen = device.last_seen_at
                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(tzinfo=timezone.utc)
                if (now - last_seen).total_seconds() >= device.polling_interval_minutes * 60:
                    device_ids.append(device.id)
        await asyncio.gather(*(poll_one(device_id) for device_id in device_ids), return_exceptions=True)
        await asyncio.sleep(60)


@app.on_event("startup")
async def start_poller() -> None:
    global poller_task
    poller_task = asyncio.create_task(poll_loop())


async def notification_loop() -> None:
    while True:
        try:
            with SessionLocal() as session:
                await AppService(session).process_notifications()
        except Exception:
            # Notification failures must not stop appliance polling.
            pass
        await asyncio.sleep(30)


@app.on_event("startup")
async def start_notifications() -> None:
    global notification_task
    notification_task = asyncio.create_task(notification_loop())


async def historical_report_loop() -> None:
    while True:
        try:
            with SessionLocal() as session:
                await AppService(session).process_historical_reports()
        except Exception:
            pass
        await asyncio.sleep(3600)


@app.on_event("startup")
async def start_historical_reports() -> None:
    global historical_report_task
    historical_report_task = asyncio.create_task(historical_report_loop())


@app.on_event("shutdown")
async def stop_poller() -> None:
    if poller_task is not None:
        poller_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await poller_task
    if notification_task is not None:
        notification_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await notification_task
    if historical_report_task is not None:
        historical_report_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await historical_report_task


def service_from_db(db: Session = Depends(get_db)) -> AppService:
    return AppService(db)


def require_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    return current_user(request, db)


def require_admin(request: Request, db: Session = Depends(get_db)) -> User | None:
    user = current_user(request, db)
    if user is not None and user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


@app.post("/api/auth/login")
def auth_login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> dict[str, object]:
    token = login(db, payload.username, payload.password)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", secure=request.url.scheme == "https", max_age=session_lifetime_minutes(db) * 60)
    return {"ok": True}


@app.post("/api/auth/logout")
def auth_logout(response: Response, token: str | None = Cookie(default=None, alias=COOKIE_NAME), db: Session = Depends(get_db)) -> dict[str, object]:
    if token:
        from hashlib import sha256
        from .models import Session as LoginSession
        session = db.query(LoginSession).filter(LoginSession.token_hash == sha256(token.encode()).hexdigest()).first()
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@app.post("/api/auth/configure")
def auth_configure(payload: AuthConfigure, request: Request, db: Session = Depends(get_db)) -> dict[str, object]:
    if auth_enabled(db):
        user = current_user(request, db)
        if user is None or user.role != "admin":
            raise HTTPException(status_code=403, detail="Administrator access required")
    configure_auth(db, enabled=payload.enabled, dashboard_requires_auth=payload.dashboard_requires_auth, session_minutes=payload.session_minutes, admin_password=payload.admin_password, viewer_password=payload.viewer_password)
    return {"ok": True}


@app.get("/api/auth/status")
def auth_status(request: Request, db: Session = Depends(get_db)) -> dict[str, object]:
    auth = AppService(db).get_settings().get("auth", {})
    auth_values = auth if isinstance(auth, dict) else {}
    user = current_user(request, db, required=False)
    return {
        "enabled": bool(auth_values.get("enabled", False)),
        "dashboard_requires_auth": bool(auth_values.get("dashboardRequiresAuth", False)),
        "authenticated": user is not None,
        "username": user.username if user else None,
        "role": user.role if user else None,
    }


@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict[str, object]:
    service = AppService(db)
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": APP_VERSION,
        "devices": len(service.list_devices()),
        "read_only": settings.read_only,
    }


@app.get("/api/metadata")
def metadata() -> dict[str, object]:
    return {"version": APP_VERSION, "support_email": SUPPORT_EMAIL, "grafana_url": settings.grafana_url, "grafana_embeds_enabled": settings.grafana_embeds_enabled}


@app.get("/api/bootstrap", response_model=BootstrapResponse)
def bootstrap(request: Request, db: Session = Depends(get_db), service: AppService = Depends(service_from_db)) -> BootstrapResponse:
    service.seed_if_empty()
    user = current_user(request, db, required=False)
    restricted = auth_enabled(db) and (user is None or user.role != "admin")
    return service.bootstrap(include_devices=not restricted, include_settings=not restricted)


@app.get("/api/devices", response_model=list[DeviceSnapshot])
def list_devices(service: AppService = Depends(service_from_db), _user: User | None = Depends(require_admin)) -> list[DeviceSnapshot]:
    return service.list_devices()


@app.post("/api/devices", response_model=DeviceSnapshot)
async def create_device(payload: DeviceCreate, service: AppService = Depends(service_from_db), _user: User | None = Depends(require_admin)) -> DeviceSnapshot:
    try:
        snapshot = service.create_device(payload)
        if payload.adapter_kind == "liebherr":
            return await service.poll_device(snapshot.id)
        return snapshot
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.patch("/api/devices/{device_id}", response_model=DeviceSnapshot)
def update_device(device_id: str, payload: DeviceUpdate, service: AppService = Depends(service_from_db), _user: User | None = Depends(require_admin)) -> DeviceSnapshot:
    try:
        return service.update_device(device_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Device not found") from exc


@app.delete("/api/devices/{device_id}", status_code=204)
def delete_device(device_id: str, service: AppService = Depends(service_from_db), _user: User | None = Depends(require_admin)) -> None:
    try:
        service.delete_device(device_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Device not found") from exc


@app.get("/api/devices/{device_id}", response_model=DeviceSnapshot)
def get_device(device_id: str, service: AppService = Depends(service_from_db), _user: User | None = Depends(require_admin)) -> DeviceSnapshot:
    try:
        return service.get_device(device_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Device not found") from exc


@app.get("/api/devices/{device_id}/image")
def get_device_image(device_id: str, db: Session = Depends(get_db), _user: User | None = Depends(require_admin)) -> FileResponse:
    device = db.get(Device, device_id)
    if device is None or not device.image_path:
        raise HTTPException(status_code=404, detail="Device image not found")
    image_path = Path(device.image_path).resolve()
    image_root = settings.data_dir.resolve()
    if image_root not in image_path.parents or not image_path.is_file():
        raise HTTPException(status_code=404, detail="Device image not found")
    return FileResponse(image_path)


@app.post("/api/devices/{device_id}/image/refresh", response_model=DeviceSnapshot)
async def refresh_device_image(device_id: str, service: AppService = Depends(service_from_db), _user: User | None = Depends(require_admin)) -> DeviceSnapshot:
    try:
        return await service.refresh_model_image(device_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Device not found") from exc


@app.post("/api/devices/{device_id}/refresh", response_model=DeviceSnapshot)
async def refresh_device(device_id: str, service: AppService = Depends(service_from_db), _user: User | None = Depends(require_admin)) -> DeviceSnapshot:
    try:
        return await service.poll_device(device_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Device not found") from exc


@app.post("/api/devices/{device_id}/controls/{action:path}", response_model=DeviceSnapshot)
async def control_device(device_id: str, action: str, payload: ControlRequest, service: AppService = Depends(service_from_db), _user: User | None = Depends(require_admin)) -> DeviceSnapshot:
    if settings.read_only:
        raise HTTPException(status_code=403, detail="TempVerity is running in read-only monitoring mode")
    try:
        return await service.control_device(device_id, action, payload.payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Device not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.delete("/api/devices/{device_id}/controls/{action:path}", response_model=DeviceSnapshot)
async def delete_control(device_id: str, action: str, service: AppService = Depends(service_from_db), _user: User | None = Depends(require_admin)) -> DeviceSnapshot:
    if settings.read_only:
        raise HTTPException(status_code=403, detail="TempVerity is running in read-only monitoring mode")
    try:
        return await service.delete_control(device_id, action)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Device not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/devices/{device_id}/zones/{zone_index}", response_model=ZoneSnapshot)
def get_zone(device_id: str, zone_index: int, service: AppService = Depends(service_from_db), _user: User | None = Depends(require_admin)) -> ZoneSnapshot:
    try:
        return service.device_zone(device_id, zone_index)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Zone not found") from exc


@app.get("/api/alerts", response_model=list[AlertRead])
def list_alerts(service: AppService = Depends(service_from_db)) -> list[AlertRead]:
    return service.list_alerts()


@app.post("/api/alerts/{alert_id}/acknowledge", response_model=AlertRead)
def acknowledge_alert(alert_id: int, payload: AlertAcknowledge, service: AppService = Depends(service_from_db), user: User | None = Depends(require_admin)) -> AlertRead:
    try:
        return service.acknowledge_alert(alert_id, user.id if user else None, payload.comment)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Alarm not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/events", response_model=list[EventRead])
def list_events(service: AppService = Depends(service_from_db)) -> list[EventRead]:
    return service.list_events()


@app.get("/api/notifications", response_model=list[NotificationRead])
def list_notifications(service: AppService = Depends(service_from_db)) -> list[NotificationRead]:
    return [NotificationRead.model_validate(item, from_attributes=True) for item in service.list_notifications()]


@app.delete("/api/events", status_code=204)
def purge_events(service: AppService = Depends(service_from_db), _user: User | None = Depends(require_user)) -> None:
    service.purge_events()


@app.get("/api/settings")
def get_settings(service: AppService = Depends(service_from_db), _user: User | None = Depends(require_admin)) -> dict[str, object]:
    return service.get_settings()


@app.patch("/api/settings/{section}")
def patch_settings(section: str, payload: SettingPatch, service: AppService = Depends(service_from_db), _user: User | None = Depends(require_admin)) -> dict[str, object]:
    return service.patch_settings(section, payload.values)


@app.get("/api/settings/historical-data/status")
def historical_data_status(service: AppService = Depends(service_from_db), _user: User | None = Depends(require_admin)) -> dict[str, object]:
    return service.historical_data_status()


@app.post("/api/settings/historical-data/report")
async def send_historical_report(service: AppService = Depends(service_from_db), _user: User | None = Depends(require_admin)) -> dict[str, object]:
    return await service.send_historical_report()


@app.post("/api/settings/smtp/test")
async def test_smtp(service: AppService = Depends(service_from_db), _user: User | None = Depends(require_admin)) -> dict[str, object]:
    return await service.test_smtp()


@app.get("/", response_model=None)
def index() -> HTMLResponse | FileResponse:
    index_file = settings.frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse(
        "<html><body style='font-family:sans-serif;padding:2rem'>"
        "<h1>TempVerity</h1><p>Frontend build not found. Run the Vite build or use the frontend source in development.</p>"
        "</body></html>"
    )


@app.get("/tempverity-logo-small.png")
def tempverity_logo() -> FileResponse:
    return FileResponse(settings.frontend_dist / "tempverity-logo-small.png")


@app.get("/tempverity-logo-v3.png")
def tempverity_logo_v3() -> FileResponse:
    return FileResponse(settings.frontend_dist / "tempverity-logo-v3.png")


@app.get("/tempverity-logo-v2.png")
def tempverity_logo_v2() -> FileResponse:
    return FileResponse(settings.frontend_dist / "tempverity-logo-v2.png")


@app.get("/logo_square.png")
def logo_square() -> FileResponse:
    return FileResponse(settings.frontend_dist / "logo_square.png", media_type="image/png")


@app.get("/manifest.webmanifest")
def web_manifest() -> FileResponse:
    return FileResponse(settings.frontend_dist / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/fridge-fallback.svg")
def fridge_fallback() -> FileResponse:
    return FileResponse(settings.frontend_dist / "fridge-fallback.svg")


@app.get("/{path:path}", response_model=None)
def spa_fallback(path: str) -> HTMLResponse | FileResponse:
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    index_file = settings.frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Not found")


def main() -> None:
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
