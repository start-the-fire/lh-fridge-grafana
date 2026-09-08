from __future__ import annotations

import json
from datetime import datetime, timezone

from .models import Alert, Device, Event, Setting


def demo_device_state(
    *,
    status: str,
    temperature_c: float,
    target_c: float,
    door_open: bool,
    alarm: str | None,
    zones: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "summary_status": status,
        "temperature_c": temperature_c,
        "target_c": target_c,
        "door_open": door_open,
        "alarm": alarm,
        "zones": zones,
        "last_refresh_at": datetime.now(timezone.utc).isoformat(),
    }


def seed_settings() -> list[Setting]:
    return [
        Setting(key="ui", value_json='{"theme":"tempverity","refreshSeconds":30}'),
        Setting(
            key="auth",
            value_json='{"enabled":false,"sessionMinutes":720,"adminUsername":"administrator"}',
        ),
        Setting(
            key="smtp",
            value_json='{"enabled":false,"from":"alerts@example.invalid","host":"localhost","port":587,"security":"STARTTLS","recipients":[]}',
        ),
        Setting(key="alerts", value_json='{"connectivityGraceMinutes":10,"alarmGraceMinutes":5,"recovery":true,"repeat":false}'),
        Setting(key="integrations", value_json='{"influxEnabled":false,"grafanaEnabled":false}'),
    ]


def seed_devices() -> list[Device]:
    now = datetime.now(timezone.utc)
    return [
        Device(
            id="srpvg-6501",
            name="SRPvg 6501 Performance",
            manufacturer="Liebherr",
            model="SRPvg 6501",
            location="Lab 1 | Room 2.01",
            adapter_kind="demo",
            api_url="http://192.0.2.10:8080",
            polling_interval_minutes=10,
            is_online=True,
            last_seen_at=now,
            state_json='{"summary_status":"ok","temperature_c":5.2,"target_c":5.0,"door_open":false,"alarm":null,"zones":[{"zone_index":0,"name":"Main chamber","temperature_c":5.2,"target_c":5.0,"door_open":false,"alarm":null,"cooling_on":true}]}',
            image_path=None,
        ),
        Device(
            id="sfffg-5501",
            name="SFFfg 5501",
            manufacturer="Liebherr",
            model="SFFfg 5501",
            location="Storage | Room 0.12",
            adapter_kind="demo",
            api_url="http://192.0.2.11:8080",
            polling_interval_minutes=10,
            is_online=True,
            last_seen_at=now,
            state_json='{"summary_status":"alarm","temperature_c":8.1,"target_c":5.0,"door_open":false,"alarm":"Temp. high","zones":[{"zone_index":0,"name":"Main chamber","temperature_c":8.1,"target_c":5.0,"door_open":false,"alarm":"Temp. high","cooling_on":true}]}',
            image_path=None,
        ),
        Device(
            id="sufsg-5001",
            name="SUFsg 5001",
            manufacturer="Liebherr",
            model="SUFsg 5001",
            location="Pharmacy | Room 1.05",
            adapter_kind="demo",
            api_url="http://192.0.2.12:8080",
            polling_interval_minutes=10,
            is_online=True,
            last_seen_at=now,
            state_json='{"summary_status":"ok","temperature_c":-18.2,"target_c":-18.0,"door_open":false,"alarm":null,"zones":[{"zone_index":0,"name":"Freezer","temperature_c":-18.2,"target_c":-18.0,"door_open":false,"alarm":null,"cooling_on":true}]}',
            image_path=None,
        ),
    ]


def full_capability_demo_device() -> Device:
    now = datetime.now(timezone.utc)
    capabilities = [
        "childLock", "ecoMode", "temperatureUnit", "acousticAlarm", "presentationLight",
        "temperature", "humidity", "humidityReminder", "cooling", "superCool", "superFrost",
        "humidifier", "doorAlarm", "doorLock", "upperTemperatureAlarm", "lowerTemperatureAlarm",
        "upperPowerFailureAlarm", "lowerPowerFailureAlarm", "emergencyAlarm", "manualDefrost",
    ]
    zones = [
        {
            "zone_index": 0, "name": "Refrigerator", "temperature_c": 5.3, "target_c": 5.0,
            "door_open": False, "alarm": None, "cooling_on": True, "capabilities": capabilities,
            "parameters": {"temperature_range_c": {"min": 3, "max": 20}, "temperature_alarm": {"upper": {"state": 0, "delay": 1, "limit": 7.5, "temperature_c": 7.5}, "lower": {"state": 0, "delay": 1, "limit": 2.5, "temperature_c": 2.5}, "refresh_time": 15}, "power_failure_alarm": {"upper_limit_c": -55, "lower_limit_c": 70}, "emergency_alarm_state": 0, "manual_defrost": 0},
        },
        {
            "zone_index": 1, "name": "Freezer", "temperature_c": -18.2, "target_c": -18.0,
            "door_open": False, "alarm": None, "cooling_on": True, "capabilities": capabilities,
            "parameters": {"temperature_range_c": {"min": -28, "max": -14}, "temperature_alarm": {"upper": {"state": 0, "delay": 1, "limit": -15, "temperature_c": -15}, "lower": {"state": 0, "delay": 1, "limit": -25, "temperature_c": -25}, "refresh_time": 15}, "power_failure_alarm": {"upper_limit_c": -5, "lower_limit_c": -55}, "emergency_alarm_state": 0, "manual_defrost": 0},
        },
    ]
    state = {"summary_status": "ok", "temperature_c": 5.3, "target_c": 5.0, "door_open": False, "alarm": None, "temperatureUnit": 0, "childLock": 1, "ecoMode": 1, "acousticAlarm": 1, "presentationLight": {"value": 50}, "zones": zones, "capabilities": {"appliance": capabilities, "zone": capabilities}, "last_refresh_at": now.isoformat()}
    return Device(id="demo-full", name="Demo Full Capability", manufacturer="Liebherr", model="ICBNdi 5173 Demo", location="Test lab", adapter_kind="demo", api_url="http://demo.invalid", polling_interval_minutes=10, is_online=True, last_seen_at=now, state_json=json.dumps(state), image_path=None)


def seed_alerts() -> list[Alert]:
    now = datetime.now(timezone.utc)
    return [
        Alert(
            device_id="sfffg-5501",
            zone_index=0,
            severity="high",
            title="Temperature above limit",
            detail="Zone 0 is above the configured target temperature.",
            status="active",
            grace_minutes=12,
            activated_at=now,
        ),
        Alert(
            device_id="srpvg-6501",
            zone_index=0,
            severity="info",
            title="Door open",
            detail="Door open alert cleared after the previous maintenance event.",
            status="resolved",
            grace_minutes=5,
            activated_at=now,
            resolved_at=now,
        ),
    ]


def seed_events() -> list[Event]:
    now = datetime.now(timezone.utc)
    return [
        Event(
            device_id="sfffg-5501",
            zone_index=0,
            kind="alarm",
            status="active",
            detail="Temperature above limit",
            created_at=now,
        ),
        Event(
            device_id="sufsg-5001",
            zone_index=0,
            kind="power-failure",
            status="cleared",
            detail="Power failure event cleared",
            created_at=now,
        ),
        Event(
            device_id="srpvg-6501",
            zone_index=0,
            kind="door",
            status="cleared",
            detail="Door open event cleared",
            created_at=now,
        ),
    ]
