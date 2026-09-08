from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Protocol

import httpx


@dataclass(slots=True)
class DeviceDiscovery:
    manufacturer: str
    model: str
    zone_count: int
    capabilities: dict[str, list[str]]
    raw: dict[str, object]


@dataclass(slots=True)
class DeviceState:
    online: bool
    zones: list[dict[str, object]]
    raw: dict[str, object]
    capabilities: dict[str, list[str]]


class DeviceAdapter(Protocol):
    async def discover(self) -> DeviceDiscovery: ...

    async def refresh(self) -> DeviceState: ...

    async def write_control(self, action: str, payload: dict[str, object] | None = None) -> None: ...

    async def delete_control(self, action: str) -> None: ...


class LiebherrAdapter:
    def __init__(self, base_url: str, token: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._client = httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=10.0)
        self._discovery: DeviceDiscovery | None = None

    @staticmethod
    def _object(payload: Any) -> dict[str, object]:
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _zones_from_state(payload: dict[str, object]) -> list[dict[str, object]]:
        zones = payload.get("zones")
        return list(zones) if isinstance(zones, list) else []

    @staticmethod
    def _enabled_capabilities(values: object, prefix: str = "") -> list[str]:
        if not isinstance(values, dict):
            return []
        return [f"{prefix}{key}" for key, value in values.items() if value not in (0, False, None)]

    @staticmethod
    def _alarm_name(state: dict[str, object]) -> str | None:
        alarms = []
        temperature_alarm = state.get("temperatureAlarm")
        if isinstance(temperature_alarm, dict):
            for name in ("upper", "lower"):
                alarm = temperature_alarm.get(name)
                if isinstance(alarm, dict) and alarm.get("state"):
                    alarms.append(f"Temperature {name}")
        for key, label in (("doorAlarm", "Door alarm"), ("emergencyAlarm", "Emergency alarm"), ("powerFailureAlarm", "Power failure")):
            alarm = state.get(key)
            if isinstance(alarm, dict) and alarm.get("state"):
                alarms.append(label)
        return ", ".join(alarms) or None

    @classmethod
    def _normalize_zone(cls, zone_number: int, info: dict[str, object], state: dict[str, object]) -> dict[str, object]:
        temperature = state.get("temperature")
        limits = temperature if isinstance(temperature, dict) else {}
        temperature_alarm = state.get("temperatureAlarm")
        temperature_alarm = temperature_alarm if isinstance(temperature_alarm, dict) else {}
        upper_alarm = temperature_alarm.get("upper")
        upper_alarm = upper_alarm if isinstance(upper_alarm, dict) else {}
        lower_alarm = temperature_alarm.get("lower")
        lower_alarm = lower_alarm if isinstance(lower_alarm, dict) else {}
        power_failure_alarm = state.get("powerFailureAlarm")
        power_failure_alarm = power_failure_alarm if isinstance(power_failure_alarm, dict) else {}
        upper_power_failure = power_failure_alarm.get("upper")
        upper_power_failure = upper_power_failure if isinstance(upper_power_failure, dict) else {}
        lower_power_failure = power_failure_alarm.get("lower")
        lower_power_failure = lower_power_failure if isinstance(lower_power_failure, dict) else {}
        temperature_ranges = info.get("temperature")
        temperature_ranges = temperature_ranges if isinstance(temperature_ranges, dict) else {}
        celsius_range = temperature_ranges.get("celsius")
        celsius_range = celsius_range if isinstance(celsius_range, dict) else {}

        def temperature_value(value: object) -> object:
            return value.get("value") if isinstance(value, dict) else value

        caps = info.get("caps")
        capabilities = cls._enabled_capabilities(caps)
        if isinstance(info.get("temperature"), dict):
            capabilities.append("temperature")
        return {
            "zone_index": zone_number,
            "name": str(info.get("name") or f"Zone {zone_number}"),
            "temperature_c": limits.get("displayed"),
            "target_c": limits.get("setpoint"),
            "door_open": state.get("door") not in (0, False, "0", "closed"),
            "alarm": cls._alarm_name(state),
            "cooling_on": state.get("state") not in (0, False),
            "capabilities": sorted(set(capabilities)),
            "raw_info": info,
            "raw_state": state,
            "parameters": {
                "temperature_range_c": {"min": celsius_range.get("min"), "max": celsius_range.get("max")},
                "temperature_alarm": {
                    "upper": {"state": upper_alarm.get("state"), "delay": upper_alarm.get("delay"), "limit": upper_alarm.get("limit"), "temperature_c": temperature_value(upper_alarm.get("temperature"))},
                    "lower": {"state": lower_alarm.get("state"), "delay": lower_alarm.get("delay"), "limit": lower_alarm.get("limit"), "temperature_c": temperature_value(lower_alarm.get("temperature"))},
                    "refresh_time": temperature_alarm.get("refreshTime"),
                },
                "power_failure_alarm": {
                    "upper_limit_c": temperature_value(upper_power_failure.get("temperature")),
                    "lower_limit_c": temperature_value(lower_power_failure.get("temperature")),
                },
                "emergency_alarm_state": (state.get("emergencyAlarm") or {}).get("state") if isinstance(state.get("emergencyAlarm"), dict) else None,
                "manual_defrost": state.get("manualDefrost"),
                "reported_state": state,
                "reported_info": info,
            },
        }

    async def _get_json(self, path: str) -> dict[str, object]:
        response = await self._client.get(path)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError(f"Unexpected response shape from {path}")
        return payload

    async def discover(self) -> DeviceDiscovery:
        payload = await self._get_json("/appliance/info")
        listed_zones = payload.get("zones")
        zone_count = payload.get("zone_count") or payload.get("zones") or (len(listed_zones) if isinstance(listed_zones, list) else 1)
        capabilities = payload.get("capabilities") or payload.get("caps")
        normalized_capabilities = {"appliance": self._enabled_capabilities(capabilities)}
        if isinstance(capabilities, dict) and capabilities.get("fahrenheit") not in (None, False, 0):
            normalized_capabilities["appliance"].append("temperatureUnit")
        raw_payload = dict(payload)
        raw_payload["manufacturer"] = str(payload.get("manufacturer", "Liebherr"))
        raw_payload["model"] = str(payload.get("model", payload.get("name", "Unknown")))
        discovery = DeviceDiscovery(
            manufacturer=str(raw_payload["manufacturer"]),
            model=str(raw_payload["model"]),
            zone_count=max(int(zone_count), 1),
            capabilities=normalized_capabilities,
            raw=raw_payload,
        )
        self._discovery = discovery
        return discovery

    async def refresh(self) -> DeviceState:
        discovery = self._discovery or await self.discover()
        appliance = await self._get_json("/appliance/state")
        listed_zones = self._zones_from_state(appliance)
        zone_numbers = [
            int(zone.get("zone_index", index))
            for index, zone in enumerate(listed_zones)
            if isinstance(zone, dict)
        ] or list(range(discovery.zone_count))

        async def read_zone(zone_number: int) -> dict[str, object]:
            zone_info, zone_state = await self._client.get(f"/zones/{zone_number}/info"), await self._client.get(
                f"/zones/{zone_number}/state"
            )
            zone_info.raise_for_status()
            zone_state.raise_for_status()
            info_payload = self._object(zone_info.json())
            state_payload = self._object(zone_state.json())
            return self._normalize_zone(zone_number, info_payload, state_payload)

        zones = await asyncio.gather(*(read_zone(number) for number in zone_numbers))
        raw = {**appliance, "zones": zones, "appliance_info": discovery.raw}
        if zones:
            raw["temperature_c"] = zones[0].get("temperature_c")
            raw["target_c"] = zones[0].get("target_c")
            raw["door_open"] = zones[0].get("door_open", False)
        zone_capabilities = sorted({capability for zone in zones for capability in zone.get("capabilities", [])})
        capabilities = {**discovery.capabilities, "zone": zone_capabilities}
        return DeviceState(online=True, zones=zones, raw=raw, capabilities=capabilities)

    async def write_control(self, action: str, payload: dict[str, object] | None = None) -> None:
        payload = payload or {}
        if not action.startswith("/"):
            action = f"/{action}"
        response = await self._client.put(action, json=payload)
        response.raise_for_status()

    async def delete_control(self, action: str) -> None:
        response = await self._client.delete(action if action.startswith("/") else f"/{action}")
        response.raise_for_status()

    async def aclose(self) -> None:
        await self._client.aclose()


class DemoAdapter:
    def __init__(self, device_state: dict[str, object]) -> None:
        self.device_state = device_state

    async def discover(self) -> DeviceDiscovery:
        appliance_capabilities = self.device_state.get("capabilities", {})
        if not isinstance(appliance_capabilities, dict):
            appliance_capabilities = {}
        return DeviceDiscovery(
            manufacturer=str(self.device_state.get("manufacturer", "Liebherr")),
            model=str(self.device_state.get("model", "Demo")),
            zone_count=len(self.device_state.get("zones", [])) or 1,
            capabilities=appliance_capabilities or {"appliance": ["child-lock", "eco-mode"], "zone": ["temperature", "door"]},
            raw=self.device_state,
        )

    async def refresh(self) -> DeviceState:
        zones = self.device_state.get("zones", [])
        capabilities = self.device_state.get("capabilities", {})
        if not isinstance(capabilities, dict):
            capabilities = {}
        return DeviceState(
            online=bool(self.device_state.get("is_online", True)),
            zones=list(zones),
            raw=self.device_state,
            capabilities=capabilities or {"appliance": ["child-lock", "eco-mode"], "zone": ["temperature", "door"]},
        )

    async def write_control(self, action: str, payload: dict[str, object] | None = None) -> None:
        return None

    async def delete_control(self, action: str) -> None:
        return None
