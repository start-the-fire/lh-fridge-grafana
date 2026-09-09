from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from random import randint

from sqlalchemy import select
from sqlalchemy.orm import Session
import aiosmtplib

from .adapters import DemoAdapter, LiebherrAdapter
from .core.config import get_settings
from .models import Alert, ControlAction, Device, Event, Notification, Setting
from .schemas import AlertRead, BootstrapResponse, DeviceCreate, DeviceSnapshot, DeviceUpdate, EventRead, ZoneSnapshot
from .seed import seed_alerts, seed_devices, seed_events, seed_settings


class AppService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def seed_if_empty(self) -> None:
        if self.session.scalar(select(Device).limit(1)) is None:
            self.session.add_all(seed_settings())
            self.session.add_all(seed_devices())
            self.session.add_all(seed_alerts())
            self.session.add_all(seed_events())
            self.session.commit()

    def _parse_state(self, device: Device) -> dict[str, object]:
        try:
            return json.loads(device.state_json)
        except json.JSONDecodeError:
            return {"zones": []}

    def _device_snapshot(self, device: Device) -> DeviceSnapshot:
        state = self._parse_state(device)
        appliance_state = {key: value for key, value in state.items() if key != "zones"}
        zones = [
            ZoneSnapshot(
                zone_index=int(zone.get("zone_index", idx)),
                name=str(zone.get("name", f"Zone {idx}")),
                temperature_c=zone.get("temperature_c"),
                target_c=zone.get("target_c"),
                door_open=bool(zone.get("door_open", False)),
                alarm=zone.get("alarm"),
                cooling_on=bool(zone.get("cooling_on", True)),
                last_seen_at=device.last_seen_at,
                parameters=zone.get("parameters", {}) if isinstance(zone.get("parameters", {}), dict) else {},
            )
            for idx, zone in enumerate(state.get("zones", []))
        ]
        status = str(state.get("summary_status", "stale"))
        if device.last_seen_at is not None:
            last_seen = device.last_seen_at
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - last_seen
            stale_threshold = max(device.polling_interval_minutes * 2, 20)
            is_stale = age.total_seconds() > stale_threshold * 60
        else:
            is_stale = True
        return DeviceSnapshot(
            id=device.id,
            name=device.name,
            manufacturer=device.manufacturer,
            model=device.model,
            location=device.location,
            adapter_kind=device.adapter_kind,
            api_url=device.api_url,
            api_token_present=bool(device.api_token),
            polling_interval_minutes=device.polling_interval_minutes,
            is_online=device.is_online,
            last_seen_at=device.last_seen_at,
            status="offline" if not device.is_online else ("alarm" if status == "alarm" else ("stale" if is_stale else "ok")),
            temperature_c=state.get("temperature_c"),
            target_c=state.get("target_c"),
            door_open=bool(state.get("door_open", False)),
            zone_count=len(zones),
            image_url=f"/api/devices/{device.id}/image" if device.image_path and Path(device.image_path).is_file() else None,
            zones=zones,
            capabilities=state.get("capabilities", {}) if isinstance(state.get("capabilities", {}), dict) else {},
            appliance_state=appliance_state,
        )

    def _alert_read(self, alert: Alert) -> AlertRead:
        return AlertRead(
            id=alert.id,
            device_id=alert.device_id,
            zone_index=alert.zone_index,
            severity=alert.severity,
            title=alert.title,
            detail=alert.detail,
            status=alert.status,
            grace_minutes=alert.grace_minutes,
            activated_at=alert.activated_at,
            resolved_at=alert.resolved_at,
            condition_key=alert.condition_key,
            recovery_started_at=alert.recovery_started_at,
            acknowledged_at=alert.acknowledged_at,
            acknowledged_by=alert.acknowledged_by,
            acknowledgement_comment=alert.acknowledgement_comment,
        )

    def _event_read(self, event: Event) -> EventRead:
        return EventRead(
            id=event.id,
            device_id=event.device_id,
            zone_index=event.zone_index,
            kind=event.kind,
            status=event.status,
            detail=event.detail,
            created_at=event.created_at,
        )

    def _settings_dict(self) -> dict[str, object]:
        settings = self.session.scalars(select(Setting)).all()
        merged: dict[str, object] = {}
        for setting in settings:
            try:
                merged[setting.key] = json.loads(setting.value_json)
            except json.JSONDecodeError:
                merged[setting.key] = setting.value_json
        return merged

    def bootstrap(self, *, include_devices: bool = True, include_settings: bool = True) -> BootstrapResponse:
        devices = self.session.scalars(select(Device).order_by(Device.name)).all()
        alerts = self.session.scalars(select(Alert).order_by(Alert.id.desc())).all()
        events = self.session.scalars(select(Event).order_by(Event.id.desc()).limit(25)).all()
        now = datetime.now(timezone.utc)
        return BootstrapResponse(
            generated_at=now,
            greeting=self._greeting(now.hour),
            summary={
                "total_devices": len(devices),
                "online_devices": sum(1 for device in devices if device.is_online),
                "alarm_devices": sum(
                    1 for device in devices if self._parse_state(device).get("summary_status") == "alarm"
                ),
                "offline_devices": sum(1 for device in devices if not device.is_online),
            },
            devices=[self._device_snapshot(device) for device in devices] if include_devices else [],
            alerts=[self._alert_read(alert) for alert in alerts],
            events=[self._event_read(event) for event in events],
            settings=self._settings_dict() if include_settings else {},
            read_only=get_settings().read_only,
        )

    def _greeting(self, hour: int) -> str:
        if hour < 12:
            return "Good morning"
        if hour < 18:
            return "Good afternoon"
        return "Good evening"

    def list_devices(self) -> list[DeviceSnapshot]:
        return [self._device_snapshot(device) for device in self.session.scalars(select(Device)).all()]

    def get_device(self, device_id: str) -> DeviceSnapshot:
        device = self.session.get(Device, device_id)
        if device is None:
            raise KeyError(device_id)
        return self._device_snapshot(device)

    def create_device(self, payload: DeviceCreate) -> DeviceSnapshot:
        now = datetime.now(timezone.utc)
        device_id = payload.name.lower().replace(" ", "-")
        if self.session.get(Device, device_id) is not None:
            raise ValueError("A device with this name already exists")
        device = Device(
            id=device_id,
            name=payload.name,
            manufacturer=payload.manufacturer,
            model=payload.model,
            location=payload.location,
            adapter_kind=payload.adapter_kind,
            api_url=payload.api_url,
            api_token=payload.api_token,
            polling_interval_minutes=payload.polling_interval_minutes,
            is_online=True,
            last_seen_at=now,
            state_json=json.dumps(
                {
                    "summary_status": "ok",
                    "temperature_c": None,
                    "target_c": None,
                    "door_open": False,
                    "alarm": None,
                    "zones": [],
                }
            ),
            image_path=payload.image_url,
        )
        self.session.add(device)
        self.session.add(
            Event(
                device_id=device.id,
                zone_index=None,
                kind="device-created",
                status="active",
                detail=f"Device {payload.name} added to TempVerity",
                created_at=now,
            )
        )
        self.session.commit()
        return self._device_snapshot(device)

    def update_device(self, device_id: str, payload: DeviceUpdate) -> DeviceSnapshot:
        device = self.session.get(Device, device_id)
        if device is None:
            raise KeyError(device_id)
        for field in ("name", "model", "location", "api_url", "api_token", "polling_interval_minutes"):
            value = getattr(payload, field)
            if value is not None:
                setattr(device, field, value)
        if payload.image_url is not None:
            device.image_path = payload.image_url or None
        self.session.commit()
        return self._device_snapshot(device)

    def delete_device(self, device_id: str) -> None:
        device = self.session.get(Device, device_id)
        if device is None:
            raise KeyError(device_id)
        self.session.query(Alert).filter(Alert.device_id == device_id).delete()
        self.session.query(Event).filter(Event.device_id == device_id).delete()
        self.session.delete(device)
        self.session.commit()

    def refresh_device(self, device_id: str) -> DeviceSnapshot:
        device = self.session.get(Device, device_id)
        if device is None:
            raise KeyError(device_id)
        state = self._parse_state(device)
        now = datetime.now(timezone.utc)
        state["last_refresh_at"] = now.isoformat()
        device.last_seen_at = now
        device.state_json = json.dumps(state)
        self.session.add(
            Event(
                device_id=device.id,
                zone_index=None,
                kind="refresh",
                status="active",
                detail="Manual refresh completed",
                created_at=now,
            )
        )
        self.session.commit()
        return self._device_snapshot(device)

    async def poll_device(self, device_id: str) -> DeviceSnapshot:
        device = self.session.get(Device, device_id)
        if device is None:
            raise KeyError(device_id)
        now = datetime.now(timezone.utc)
        adapter = self.adapter_for(device)
        try:
            state = await adapter.refresh()
            state_json = dict(state.raw)
            state_json["zones"] = state.zones
            state_json["capabilities"] = state.capabilities
            state_json["summary_status"] = "alarm" if any(zone.get("alarm") for zone in state.zones) else "ok"
            appliance_info = state_json.get("appliance_info")
            if isinstance(appliance_info, dict):
                device.manufacturer = str(appliance_info.get("manufacturer", device.manufacturer))
                device.model = str(appliance_info.get("model", device.model))
            if (device.image_path is None or not Path(device.image_path).is_file()) and device.adapter_kind == "liebherr":
                await self._ensure_model_image(device)
            device.is_online = state.online
            device.last_seen_at = now
            device.state_json = json.dumps(state_json)
            self._apply_alerts(device, state_json, now)
            self.session.add(Event(device_id=device.id, kind="poll", status="success", detail="Device state refreshed", created_at=now))
            self.session.commit()
        except Exception as exc:
            device.is_online = False
            state_json = self._parse_state(device)
            self._apply_alerts(device, {**state_json, "connectivity_failure": True}, now)
            self.session.add(Event(device_id=device.id, kind="poll", status="failed", detail=f"Device poll failed: {type(exc).__name__}", created_at=now))
            self.session.commit()
        finally:
            close = getattr(adapter, "aclose", None)
            if close is not None:
                await close()
        return self._device_snapshot(device)

    async def _ensure_model_image(self, device: Device) -> None:
        """Attach a bundled official product image after model discovery."""
        if not device.model or device.model.lower() == "unknown":
            return
        model = "_".join(device.model.replace("  ", " ").strip().split())
        image_dir = get_settings().data_dir / "images" / "catalog"
        for image_path in image_dir.rglob(f"{model}.*"):
            if image_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                device.image_path = str(image_path)
                return

    async def refresh_model_image(self, device_id: str) -> DeviceSnapshot:
        device = self.session.get(Device, device_id)
        if device is None:
            raise KeyError(device_id)
        if (device.image_path is None or not Path(device.image_path).is_file()) and device.adapter_kind == "liebherr":
            await self._ensure_model_image(device)
            self.session.commit()
        return self._device_snapshot(device)

    def _validate_control(self, device: Device, action: str) -> None:
        capabilities = self._parse_state(device).get("capabilities", {})
        if not isinstance(capabilities, dict):
            return
        supported = {"".join(c.lower() for c in str(item) if c.isalnum()) for group in capabilities.values() if isinstance(group, list) for item in group}
        normalized = action.lower()
        action_name = "".join(c.lower() for c in action.rsplit("/", 1)[-1] if c.isalnum())
        mappings = (
            ("temperature/alarm/upper", "uppertemperaturealarm"),
            ("temperature/alarm/lower", "lowertemperaturealarm"),
            ("temperature/alarm/refresh-time", "temperaturealarm"),
            ("humidity/reminder", "humidityreminder"),
            ("humidity", "humidity"),
            ("humidifier/mode", "humidifiermode"),
            ("door/lock/alarm", "doorlockalarm"),
            ("door/alarm", "dooralarm"),
            ("door/lock", "doorlock"),
            ("power-failure-alarm/upper", "upperpowerfailurealarm"),
            ("power-failure-alarm/lower", "lowerpowerfailurealarm"),
            ("emergency-alarm", "emergencyalarm"),
            ("supercool", "supercool"),
            ("superfrost", "superfrost"),
            ("temperature", "temperature"),
        )
        for fragment, capability in mappings:
            if fragment in normalized:
                action_name = capability
                break
        if action_name == "temperaturealarm" and {"uppertemperaturealarm", "lowertemperaturealarm"} & supported:
            return
        if action_name == "doorlockalarm" and "doorlock" in supported:
            return
        if supported and action_name not in supported:
            raise ValueError(f"Control is not supported: {action}")

    async def _run_control(self, device_id: str, action: str, payload: dict[str, object] | None, method: str) -> DeviceSnapshot:
        device = self.session.get(Device, device_id)
        if device is None:
            raise KeyError(device_id)
        self._validate_control(device, action)
        adapter = self.adapter_for(device)
        try:
            if method == "delete":
                await adapter.delete_control(action)
            else:
                await adapter.write_control(action, payload)
            result = "success"
        except Exception:
            result = "failed"
            self.session.add(ControlAction(device_id=device_id, action=action, payload_json=json.dumps(payload or {}), result=result))
            self.session.commit()
            raise
        finally:
            close = getattr(adapter, "aclose", None)
            if close is not None:
                await close()
        self.session.add(ControlAction(device_id=device_id, action=action, payload_json=json.dumps(payload or {}), result=result))
        self.session.commit()
        return await self.poll_device(device_id)

    async def control_device(self, device_id: str, action: str, payload: dict[str, object] | None = None) -> DeviceSnapshot:
        return await self._run_control(device_id, action, payload, "put")

    async def delete_control(self, device_id: str, action: str) -> DeviceSnapshot:
        return await self._run_control(device_id, action, None, "delete")

    def _apply_alerts(self, device: Device, state: dict[str, object], now: datetime) -> None:
        alert_settings = self._settings_dict().get("alerts", {})
        if not isinstance(alert_settings, dict):
            alert_settings = {}
        connectivity_grace = max(0, int(alert_settings.get("connectivityGraceMinutes", 10)))
        alarm_grace = max(0, int(alert_settings.get("alarmGraceMinutes", 5)))
        recovery_grace = max(0, int(alert_settings.get("recoveryGraceMinutes", 0)))
        conditions: list[tuple[str, str, str, int, int]] = []
        if state.get("connectivity_failure"):
            conditions.append(("connectivity", "high", "Connectivity lost", connectivity_grace, recovery_grace))
        for index, zone in enumerate(state.get("zones", [])):
            if isinstance(zone, dict) and zone.get("alarm"):
                conditions.append((f"appliance:{index}:{zone.get('alarm')}", "high", str(zone.get("alarm")), alarm_grace, recovery_grace))
        rules = alert_settings.get("softwareRules", [])
        if isinstance(rules, list):
            for rule in rules:
                if not isinstance(rule, dict) or rule.get("enabled", True) is False:
                    continue
                if rule.get("device_id") not in (None, "", device.id):
                    continue
                try:
                    zone_index = int(rule.get("zone_index", 0))
                except (TypeError, ValueError):
                    continue
                zone = next((item for item in state.get("zones", []) if isinstance(item, dict) and int(item.get("zone_index", 0)) == zone_index), None)
                if not isinstance(zone, dict):
                    continue
                condition = str(rule.get("condition", "above")).lower()
                if condition == "door_open":
                    triggered = bool(zone.get("door_open"))
                else:
                    try:
                        threshold = float(rule["threshold"])
                    except (KeyError, TypeError, ValueError):
                        continue
                    if not isinstance(zone.get("temperature_c"), (int, float)):
                        continue
                    triggered = float(zone["temperature_c"]) > threshold if condition == "above" else float(zone["temperature_c"]) < threshold
                if triggered:
                    rule_id = str(rule.get("id") or f"rule-{zone_index}-{condition}-{threshold:g}")
                    title = str(rule.get("name") or f"Temperature {condition} limit exceeded")
                    conditions.append((f"software:{rule_id}", "high", title, max(0, int(rule.get("grace_minutes", alarm_grace))), max(0, int(rule.get("recovery_grace_minutes", recovery_grace)))))
        existing = self.session.scalars(select(Alert).where(Alert.device_id == device.id, Alert.status.in_(["pending", "active", "recovery"]))).all()
        current_keys = {key for key, *_ in conditions}
        for alert in existing:
            if alert.condition_key not in current_keys:
                if alert.status == "active":
                    alert.status = "recovery"
                    alert.recovery_started_at = now
                elif alert.status == "pending":
                    alert.status = "resolved"
                    alert.resolved_at = now
                elif alert.status == "recovery" and alert.recovery_started_at is not None and (now - alert.recovery_started_at).total_seconds() >= recovery_grace * 60:
                    alert.status = "resolved"
                    alert.resolved_at = now
        for key, severity, title, grace, recovery in conditions:
            zone_index = None if key == "connectivity" or key.startswith("software:") else int(key.split(":", 2)[1])
            alert = next((item for item in existing if item.condition_key == key), None)
            if alert is None:
                self.session.add(Alert(device_id=device.id, zone_index=zone_index, condition_key=key, severity=severity, title=title, detail=title, status="pending", grace_minutes=grace, activated_at=now))
                continue
            if alert.status == "pending" and (now - alert.activated_at).total_seconds() >= alert.grace_minutes * 60:
                alert.status = "active"
            elif alert.status == "recovery":
                alert.status = "active"
                alert.recovery_started_at = None
            elif alert.status == "recovery" and alert.recovery_started_at is not None and (now - alert.recovery_started_at).total_seconds() >= recovery * 60:
                alert.status = "resolved"
                alert.resolved_at = now

    def acknowledge_alert(self, alert_id: int, user_id: int | None, comment: str) -> AlertRead:
        alert = self.session.get(Alert, alert_id)
        if alert is None:
            raise KeyError(alert_id)
        if alert.status not in {"pending", "active", "recovery"}:
            raise ValueError("Only an open alarm can be acknowledged")
        if alert.acknowledged_at is not None:
            return self._alert_read(alert)
        now = datetime.now(timezone.utc)
        alert.acknowledged_at = now
        alert.acknowledged_by = user_id
        alert.acknowledgement_comment = comment.strip() or None
        self.session.add(Event(device_id=alert.device_id, zone_index=alert.zone_index, kind="alarm-acknowledged", status="active", detail=f"{alert.title} acknowledged", created_at=now))
        self.session.commit()
        return self._alert_read(alert)

    def device_zone(self, device_id: str, zone_index: int) -> ZoneSnapshot:
        device = self.session.get(Device, device_id)
        if device is None:
            raise KeyError(device_id)
        state = self._parse_state(device)
        for idx, zone in enumerate(state.get("zones", [])):
            if int(zone.get("zone_index", idx)) == zone_index:
                return ZoneSnapshot(
                    zone_index=zone_index,
                    name=str(zone.get("name", f"Zone {zone_index}")),
                    temperature_c=zone.get("temperature_c"),
                    target_c=zone.get("target_c"),
                    door_open=bool(zone.get("door_open", False)),
                    alarm=zone.get("alarm"),
                    cooling_on=bool(zone.get("cooling_on", True)),
                    last_seen_at=device.last_seen_at,
                    parameters=zone.get("parameters", {}) if isinstance(zone.get("parameters", {}), dict) else {},
                )
        raise KeyError(f"{device_id}:{zone_index}")

    def list_alerts(self) -> list[AlertRead]:
        return [self._alert_read(alert) for alert in self.session.scalars(select(Alert).order_by(Alert.id.desc())).all()]

    def list_events(self) -> list[EventRead]:
        events = self.session.scalars(select(Event).order_by(Event.id.desc()).limit(25)).all()
        return [self._event_read(event) for event in events]

    def list_notifications(self) -> list[Notification]:
        return list(self.session.scalars(select(Notification).order_by(Notification.id.desc()).limit(100)).all())

    def purge_events(self) -> None:
        self.session.query(Event).delete()
        self.session.commit()

    def get_settings(self) -> dict[str, object]:
        settings = self._settings_dict()
        smtp = settings.get("smtp")
        if isinstance(smtp, dict) and "password" in smtp:
            settings["smtp"] = {**smtp, "password": "configured"}
        return settings

    def patch_settings(self, section: str, values: Mapping[str, object]) -> dict[str, object]:
        setting = self.session.get(Setting, section)
        if setting is None:
            setting = Setting(key=section, value_json=json.dumps(dict(values)))
        else:
            current = json.loads(setting.value_json)
            if not isinstance(current, dict):
                current = {}
            safe_values = dict(values)
            if section == "smtp" and not str(safe_values.get("password", "")).strip():
                safe_values.pop("password", None)
            current.update(safe_values)
            setting.value_json = json.dumps(current)
        self.session.add(setting)
        self.session.commit()
        return self.get_settings()

    async def test_smtp(self) -> dict[str, object]:
        smtp = self._settings_dict().get("smtp", {})
        if not isinstance(smtp, dict) or not smtp.get("host"):
            return {"ok": False, "message": "SMTP host is not configured"}
        recipients = smtp.get("recipients", [])
        if isinstance(recipients, str):
            recipients = [recipients]
        if not recipients:
            return {"ok": False, "message": "No SMTP recipient is configured"}
        message = EmailMessage()
        message["From"] = str(smtp.get("from", "alerts@example.invalid"))
        message["To"] = ", ".join(str(item) for item in recipients)
        message["Subject"] = "[TempVerity] SMTP test"
        message.set_content("TempVerity SMTP delivery is configured correctly.")
        security = str(smtp.get("security", "STARTTLS")).upper()
        try:
            await aiosmtplib.send(
                message,
                hostname=str(smtp["host"]),
                port=int(smtp.get("port", 587)),
                username=str(smtp.get("username", "")) or None,
                password=str(smtp.get("password", "")) or None,
                start_tls=security == "STARTTLS",
                use_tls=security in {"TLS", "SSL", "TLS/SSL"},
                timeout=float(smtp.get("timeout", 10)),
            )
        except Exception as exc:
            return {"ok": False, "message": f"SMTP delivery failed: {type(exc).__name__}"}
        return {"ok": True, "message": "Test email sent"}

    async def process_notifications(self) -> None:
        smtp = self._settings_dict().get("smtp", {})
        if not isinstance(smtp, dict) or not smtp.get("enabled"):
            return
        recipients = smtp.get("recipients", [])
        if isinstance(recipients, str):
            recipients = [recipients]
        recipients = [str(item) for item in recipients if str(item).strip()]
        if not recipients:
            return
        now = datetime.now(timezone.utc)
        active_alerts = self.session.scalars(select(Alert).where(Alert.status == "active")).all()
        alert_settings = self._settings_dict().get("alerts", {})
        send_recovery = isinstance(alert_settings, dict) and alert_settings.get("recovery", True) is not False
        alerts_to_notify: list[tuple[Alert, str]] = [(alert, "alert") for alert in active_alerts]
        if send_recovery:
            resolved_alerts = self.session.scalars(select(Alert).where(Alert.status == "resolved", Alert.resolved_at.is_not(None))).all()
            for alert in resolved_alerts:
                was_sent = self.session.scalar(select(Notification.id).where(Notification.alert_id == alert.id, Notification.kind == "alert", Notification.status == "sent").limit(1))
                if was_sent is not None:
                    alerts_to_notify.append((alert, "recovery"))
        for alert, kind in alerts_to_notify:
            for recipient in recipients:
                notification = self.session.scalar(select(Notification).where(Notification.alert_id == alert.id, Notification.kind == kind, Notification.recipient == recipient).order_by(Notification.id.desc()))
                if notification is None:
                    notification = Notification(alert_id=alert.id, kind=kind, recipient=recipient, next_attempt_at=now)
                    self.session.add(notification)
                    self.session.flush()
                # An alert instance is notified once; only scheduled retries may run again.
                if notification.status in {"sent", "suppressed"} or (notification.next_attempt_at and notification.next_attempt_at > now):
                    continue
                await self._send_alert_notification(notification, alert, recipient, smtp, now, kind)
        self.session.commit()

    async def _send_alert_notification(self, notification: Notification, alert: Alert, recipient: str, smtp: dict[str, object], now: datetime, kind: str = "alert") -> None:
        device = self.session.get(Device, alert.device_id)
        if device is None:
            return
        message = EmailMessage()
        message["From"] = str(smtp.get("from", "alerts@example.invalid"))
        message["To"] = recipient
        if kind == "recovery":
            message["Subject"] = f"[TempVerity] Resolved - {device.name}: {alert.title}"
            message.set_content(f"The previously reported condition has been resolved.\n\nDevice: {device.name}\nPrevious condition: {alert.title}\nFirst detected: {alert.activated_at}\nResolved: {alert.resolved_at}\n\nPlease evaluate the appliance and stored contents according to local procedures.")
        else:
            message["Subject"] = f"[TempVerity] Alert - {device.name}: {alert.title}"
            message.set_content("TempVerity has detected an active alarm condition.\n\n" f"Device: {device.name}\nModel: {device.model}\nZone: {alert.zone_index if alert.zone_index is not None else 'connection'}\n" f"Alarm: {alert.title}\nFirst detected: {alert.activated_at}\n\n" f"The alarm remained active for the configured grace period of {alert.grace_minutes} minutes.")
        notification.attempts += 1
        notification.attempted_at = now
        try:
            security = str(smtp.get("security", "STARTTLS")).upper()
            await aiosmtplib.send(message, hostname=str(smtp["host"]), port=int(smtp.get("port", 587)), username=str(smtp.get("username", "")) or None, password=str(smtp.get("password", "")) or None, start_tls=security == "STARTTLS", use_tls=security in {"TLS", "SSL", "TLS/SSL"}, timeout=float(smtp.get("timeout", 10)))
            notification.status = "sent"
            notification.sent_at = now
            notification.error_message = None
        except Exception as exc:
            notification.status = "failed"
            notification.error_message = f"SMTP delivery failed: {type(exc).__name__}"
            retry_delays = [60, 300, 900]
            if notification.attempts <= len(retry_delays):
                notification.next_attempt_at = now + timedelta(seconds=retry_delays[notification.attempts - 1])
            else:
                notification.status = "suppressed"
                notification.next_attempt_at = None
                notification.error_message = f"SMTP delivery stopped after {notification.attempts} attempts: {type(exc).__name__}"

    def adapter_for(self, device: Device):
        if device.adapter_kind == "liebherr":
            return LiebherrAdapter(device.api_url, device.api_token)
        return DemoAdapter(self._parse_state(device))

    def random_jitter_seconds(self) -> int:
        return randint(2, 12)
