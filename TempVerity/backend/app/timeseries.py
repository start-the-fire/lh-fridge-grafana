from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic
from typing import Any

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from .core.config import Settings
from .models import Device


def _number(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _state(value: object) -> int:
    return 1 if value not in (0, False, None, "", "0", "closed") else 0


class HistoricalDataWriter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def configured(self) -> bool:
        return all(
            [
                self.settings.influx_url,
                self.settings.influx_org,
                self.settings.influx_bucket,
                self.settings.influx_token,
            ]
        )

    def status(self) -> dict[str, object]:
        if not self.settings.influx_enabled:
            return {"state": "disabled", "message": "InfluxDB historical storage is disabled"}
        if not self.configured:
            return {"state": "missing_config", "message": "InfluxDB connection details are incomplete"}
        try:
            with InfluxDBClient(
                url=self.settings.influx_url,
                token=self.settings.influx_token,
                org=self.settings.influx_org,
                timeout=5000,
            ) as client:
                bucket_api = client.buckets_api()
                bucket = bucket_api.find_bucket_by_name(self.settings.influx_bucket)
                if bucket is None:
                    return {"state": "bucket_missing", "message": "InfluxDB is reachable, but the bucket was not found"}
                ok = client.ping()
        except Exception as exc:
            return {"state": "unreachable", "message": f"InfluxDB check failed: {type(exc).__name__}"}
        return {"state": "ok" if ok else "unreachable", "message": "InfluxDB is reachable"}

    def write_device_state(self, device: Device, state: dict[str, Any], now: datetime | None = None) -> dict[str, object]:
        if not self.settings.influx_enabled:
            return {"ok": False, "skipped": True, "message": "Historical storage disabled"}
        if not self.configured:
            return {"ok": False, "skipped": True, "message": "InfluxDB configuration incomplete"}
        zones = state.get("zones")
        if not isinstance(zones, list) or not zones:
            return {"ok": False, "skipped": True, "message": "No zones to write"}
        timestamp = now or datetime.now(timezone.utc)
        points = [self._point_for_zone(device, zone, timestamp) for zone in zones if isinstance(zone, dict)]
        if not points:
            return {"ok": False, "skipped": True, "message": "No valid zone points to write"}
        started = monotonic()
        with InfluxDBClient(
            url=self.settings.influx_url,
            token=self.settings.influx_token,
            org=self.settings.influx_org,
        ) as client:
            client.write_api(write_options=SYNCHRONOUS).write(
                bucket=self.settings.influx_bucket,
                org=self.settings.influx_org,
                record=points,
            )
        return {"ok": True, "skipped": False, "points": len(points), "duration_ms": round((monotonic() - started) * 1000)}

    def _point_for_zone(self, device: Device, zone: dict[str, Any], timestamp: datetime) -> Point:
        parameters = zone.get("parameters")
        parameters = parameters if isinstance(parameters, dict) else {}
        temperature_alarm = parameters.get("temperature_alarm")
        temperature_alarm = temperature_alarm if isinstance(temperature_alarm, dict) else {}
        upper_alarm = temperature_alarm.get("upper")
        upper_alarm = upper_alarm if isinstance(upper_alarm, dict) else {}
        lower_alarm = temperature_alarm.get("lower")
        lower_alarm = lower_alarm if isinstance(lower_alarm, dict) else {}
        power_failure_alarm = parameters.get("power_failure_alarm")
        power_failure_alarm = power_failure_alarm if isinstance(power_failure_alarm, dict) else {}

        point = (
            Point("fridge_zone_state")
            .tag("device_id", device.id)
            .tag("device_name", device.name)
            .tag("model", device.model)
            .tag("location", device.location or "")
            .tag("zone", str(zone.get("zone_index", 0)))
            .field("online", _state(device.is_online))
            .field("temp_displayed", _number(zone.get("temperature_c")) or 0.0)
            .field("temp_setpoint", _number(zone.get("target_c")) or 0.0)
            .field("door_open", _state(zone.get("door_open")))
            .field("cooling_on", _state(zone.get("cooling_on")))
            .field("any_alarm_state", _state(zone.get("alarm")))
            .field("upper_alarm_state", _state(upper_alarm.get("state")))
            .field("lower_alarm_state", _state(lower_alarm.get("state")))
            .field("upper_alarm_limit", _number(upper_alarm.get("limit")) or 0.0)
            .field("lower_alarm_limit", _number(lower_alarm.get("limit")) or 0.0)
            .field("emergency_alarm_state", _state(parameters.get("emergency_alarm_state")))
            .field("manual_defrost", _state(parameters.get("manual_defrost")))
            .field("powerfail_upper_limit", _number(power_failure_alarm.get("upper_limit_c")) or 0.0)
            .field("powerfail_lower_limit", _number(power_failure_alarm.get("lower_limit_c")) or 0.0)
            .time(timestamp)
        )
        return point
