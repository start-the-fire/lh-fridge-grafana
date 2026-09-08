from backend.app.adapters import LiebherrAdapter


def test_normalize_zone_maps_temperature_door_alarm_and_capabilities() -> None:
    zone = LiebherrAdapter._normalize_zone(
        1,
        {"name": "Upper chamber", "caps": {"doorAlarm": True, "light": False}, "temperature": {"setpoint": True}},
        {"temperature": {"displayed": 4.25, "setpoint": 5}, "door": "closed", "doorAlarm": {"state": True}, "state": 1},
    )

    assert zone["zone_index"] == 1
    assert zone["temperature_c"] == 4.25
    assert zone["target_c"] == 5
    assert zone["door_open"] is False
    assert zone["alarm"] == "Door alarm"
    assert "doorAlarm" in zone["capabilities"]
    assert "temperature" in zone["capabilities"]


def test_enabled_capabilities_excludes_disabled_values() -> None:
    assert LiebherrAdapter._enabled_capabilities({"temperature": True, "light": False, "missing": None}) == ["temperature"]
