from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ZoneSnapshot(BaseModel):
    zone_index: int
    name: str
    temperature_c: float | None = None
    target_c: float | None = None
    door_open: bool = False
    alarm: str | None = None
    cooling_on: bool = True
    last_seen_at: datetime | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class DeviceSnapshot(BaseModel):
    id: str
    name: str
    manufacturer: str
    model: str
    location: str
    adapter_kind: str
    api_url: str
    api_token_present: bool
    polling_interval_minutes: int
    is_online: bool
    last_seen_at: datetime | None
    status: Literal["ok", "alarm", "offline", "stale"]
    temperature_c: float | None = None
    target_c: float | None = None
    door_open: bool = False
    zone_count: int = 0
    image_url: str | None = None
    zones: list[ZoneSnapshot] = Field(default_factory=list)
    capabilities: dict[str, list[str]] = Field(default_factory=dict)
    appliance_state: dict[str, Any] = Field(default_factory=dict)


class EventRead(BaseModel):
    id: int
    device_id: str | None
    zone_index: int | None
    kind: str
    status: str
    detail: str
    created_at: datetime


class NotificationRead(BaseModel):
    id: int
    alert_id: int
    kind: str
    recipient: str
    status: str
    attempts: int
    attempted_at: datetime | None
    next_attempt_at: datetime | None
    sent_at: datetime | None
    error_message: str | None


class AlertRead(BaseModel):
    id: int
    device_id: str
    zone_index: int | None
    severity: str
    title: str
    detail: str
    status: str
    grace_minutes: int
    activated_at: datetime
    resolved_at: datetime | None


class SettingPatch(BaseModel):
    values: dict[str, Any]


class DeviceCreate(BaseModel):
    name: str
    manufacturer: str = "Liebherr"
    model: str = "Unknown"
    location: str = ""
    adapter_kind: str = "demo"
    api_url: str = ""
    api_token: str = ""
    polling_interval_minutes: int = 10
    image_url: str | None = None


class DeviceUpdate(BaseModel):
    name: str | None = None
    model: str | None = None
    location: str | None = None
    api_url: str | None = None
    api_token: str | None = None
    polling_interval_minutes: int | None = Field(default=None, ge=1, le=1440)
    image_url: str | None = None


class ControlRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class LoginRequest(BaseModel):
    username: str | None = None
    password: str


class AuthConfigure(BaseModel):
    enabled: bool
    dashboard_requires_auth: bool = False
    session_minutes: int = Field(default=720, ge=5, le=525600)
    admin_password: str | None = None
    viewer_password: str | None = None


class BootstrapResponse(BaseModel):
    generated_at: datetime
    greeting: str
    summary: dict[str, int]
    devices: list[DeviceSnapshot]
    alerts: list[AlertRead]
    events: list[EventRead]
    settings: dict[str, Any]
    read_only: bool = True
