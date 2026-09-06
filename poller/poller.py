import os
import time
import requests
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.rest import ApiException

# -----------------------------------------
# Environment Variables
# -----------------------------------------
API_URL = os.getenv("LIEBHERR_API_URL")
API_TOKEN = os.getenv("LIEBHERR_API_TOKEN")

try:
    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
except ValueError as exc:
    raise ValueError("POLL_INTERVAL must be a positive integer") from exc

INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

if not API_URL:
    raise ValueError("Missing environment variable: LIEBHERR_API_URL")
if POLL_INTERVAL <= 0:
    raise ValueError("POLL_INTERVAL must be a positive integer")

missing_influx_config = [
    name
    for name, value in {
        "INFLUX_URL": INFLUX_URL,
        "INFLUX_TOKEN": INFLUX_TOKEN,
        "INFLUX_ORG": INFLUX_ORG,
        "INFLUX_BUCKET": INFLUX_BUCKET,
    }.items()
    if not value
]
if missing_influx_config:
    raise ValueError(
        "Missing environment variable(s): " + ", ".join(missing_influx_config)
    )

headers = {}
if API_TOKEN:
    headers["Authorization"] = f"Bearer {API_TOKEN}"

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

# -----------------------------------------
# Helpers
# -----------------------------------------
def as_float(v, default=0.0):
    """Safely convert values (int/float/str/None) to float."""
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default

def as_int(v, default=0):
    """Safely convert values to int."""
    try:
        if v is None:
            return default
        return int(v)
    except (TypeError, ValueError):
        return default

# -----------------------------------------
# Helper to fetch JSON from Local API
# -----------------------------------------
def fetch_json(path):
    try:
        r = requests.get(f"{API_URL.rstrip('/')}{path}", headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        print("API error:", e, flush=True)
        return None

# -----------------------------------------
# Main polling logic
# -----------------------------------------
def poll_once():
    appliance_info = fetch_json("/appliance/info")
    zone_state = fetch_json("/zones/0/state")

    if not appliance_info or not zone_state:
        print("Could not read all data.", flush=True)
        return

    serial = appliance_info.get("serialNo", "unknown")
    model = appliance_info.get("name", "unknown")

    temp = zone_state.get("temperature", {})
    alarms = zone_state.get("temperatureAlarm", {})
    upper = alarms.get("upper", {})
    lower = alarms.get("lower", {})
    power = zone_state.get("powerFailureAlarm", {})

    point = (
        Point("fridge_zone_state")
        .tag("device_serial", serial)
        .tag("model", model)
        .tag("zone", "0")
        # ONLY temp_displayed as float
        .field("temp_displayed", as_float(temp.get("displayed")))
        # Everything else int, EXCEPT the ones that are already float in Influx
        .field("temp_setpoint", as_int(temp.get("setpoint")))
        .field("door", as_int(zone_state.get("door", 0)))
        .field("upper_alarm_state", as_int(upper.get("state", 0)))
        # Influx already has this as FLOAT -> keep it float
        .field("upper_alarm_limit", as_float(upper.get("limit")))
        .field("upper_alarm_temp", as_int(upper.get("temperature", {}).get("value")))
        .field("lower_alarm_state", as_int(lower.get("state", 0)))
        # Influx already has this as FLOAT -> keep it float
        .field("lower_alarm_limit", as_float(lower.get("limit")))
        .field("lower_alarm_temp", as_int(lower.get("temperature", {}).get("value")))
        .field("powerfail_upper", as_int(power.get("upper", {}).get("temperature", {}).get("value")))
        .field("powerfail_lower", as_int(power.get("lower", {}).get("temperature", {}).get("value")))
        .field("emergency_alarm", as_int(zone_state.get("emergencyAlarm", {}).get("state", 0)))
    )

    try:
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        print("Data written.", flush=True)
    except (ApiException, OSError, RuntimeError, ValueError) as e:
        print("Error writing to InfluxDB:", e, flush=True)

# -----------------------------------------
# Main loop
# -----------------------------------------
def main():
    print(f"Starting poller: interval={POLL_INTERVAL}s, API={API_URL}", flush=True)
    try:
        while True:
            poll_once()
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("Poller stopped.", flush=True)
    finally:
        client.close()

if __name__ == "__main__":
    main()
