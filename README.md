# Liebherr Fridge Monitoring

This project collects Liebherr fridge telemetry, visualizes it in Grafana, and
exports periodic CSV and PDF reports. The poller reads the SmartModule Local API
and writes the measurements to a dedicated InfluxDB instance. Grafana and the
exporter read the same time-series data.

The production InfluxDB is a separate service and is not managed by this
project. It must be configured with a retention period of 720 days. This keeps
approximately two years of fridge history available for operational review and
reporting while allowing the database to remove older data automatically.

## Data Flow

The system follows this flow:

1. The poller periodically requests appliance information and zone state from
   the Liebherr SmartModule Local API.
2. Each successful poll is written to the dedicated InfluxDB bucket configured
   by `INFLUX_BUCKET`.
3. Grafana queries the time series for live status tiles, temperature trends,
   alarm states, door state, and longer-range operational statistics.
4. The exporter queries completed reporting periods and sends CSV and PDF
   reports by email.

The poller currently collects zone `0` and writes measurement
`fridge_zone_state`. The series is tagged with `device_serial`, `model`, and
`zone`. Fields include:

| Field | Description |
| --- | --- |
| `temp_displayed` | Current displayed temperature |
| `temp_setpoint` | Configured temperature setpoint |
| `door` | Door state, `0` closed or `1` open |
| `upper_alarm_state` | Upper temperature alarm state |
| `upper_alarm_limit` | Upper alarm limit |
| `upper_alarm_temp` | Upper alarm temperature value |
| `lower_alarm_state` | Lower temperature alarm state |
| `lower_alarm_limit` | Lower alarm limit |
| `lower_alarm_temp` | Lower alarm temperature value |
| `powerfail_upper` | Upper power-failure alarm value |
| `powerfail_lower` | Lower power-failure alarm value |
| `emergency_alarm` | Emergency alarm state |

Boolean-like states are stored as integer values so they can be queried and
aggregated consistently in Grafana and the exporter.

## Applications

### Poller

The poller calls the Liebherr Local API at the configured interval and writes the
zone status to InfluxDB measurement `fridge_zone_state`. It records the displayed
temperature, temperature setpoint, door status, alarm states, and power-failure
values. A successful poll writes one point containing the current values and the
device identity tags. It is published as:

```text
startthefire/lh-fridge-poller:v2.0
```

Required poller settings:

| Variable | Description |
| --- | --- |
| `LIEBHERR_API_URL` | Fridge API URL, including host and port |
| `LIEBHERR_API_TOKEN` | Optional API bearer token |
| `POLL_INTERVAL` | Polling interval in seconds |
| `INFLUX_URL` | InfluxDB URL |
| `INFLUX_TOKEN` | InfluxDB access token |
| `INFLUX_ORG` | InfluxDB organization |
| `INFLUX_BUCKET` | InfluxDB bucket |

### Grafana

Grafana is the operational visualization layer. It uses the InfluxDB Flux
datasource and provides two provisioned dashboards:

- `Liebherr Fridge - Overview` shows current temperature, setpoint, door and
  alarm status, a temperature trend, and door/alarm timelines. It is intended
  for daily monitoring and rapid status checks.
- `Liebherr Fridge - Operations` shows average, minimum, and maximum
  temperature, sample counts, door-open samples, alarm samples, a seven-day
  temperature trend, and state timelines. It is intended for operational
  analysis and troubleshooting.

The dashboards compare displayed temperature with the configured setpoint and
upper/lower alarm limits. They use the Grafana time-range selector, so the same
views can be used for recent checks or historical analysis within the 720-day
retention period.

Grafana is built from `grafana/Dockerfile`. At startup it provisions the Flux
datasource and renders the dashboard templates using the InfluxDB connection
settings. On a new customer deployment, the dashboards and container image can
remain unchanged; the InfluxDB URL, credentials, organization, bucket, and
Grafana credentials are site-specific.

Grafana settings:

| Variable | Description |
| --- | --- |
| `GRAFANA_ADMIN_USER` | Initial Grafana administrator username |
| `GRAFANA_ADMIN_PASSWORD` | Initial Grafana administrator password |
| `INFLUX_URL` | Dedicated InfluxDB URL |
| `INFLUX_TOKEN` | InfluxDB access token with query permission |
| `INFLUX_ORG` | InfluxDB organization |
| `INFLUX_BUCKET` | InfluxDB bucket, normally `fridge` |

The production InfluxDB instance is external to this project. Ensure the Grafana
datasource points to that instance and that its bucket has the required 720-day
retention policy. The `influxdb` service in the example Compose file is a local
demonstration layout; it should not be treated as the managed production storage
service when InfluxDB is operated separately.

For manual dashboard imports, use the JSON files under `test/grafana/` and map
`DS_INFLUXDB` to the existing customer InfluxDB datasource. These files use the
literal bucket `fridge` and are intended for testing or manual import. The
container uses the provisioned templates under `grafana/templates/`.

### Exporter

The exporter queries the completed reporting period from the dedicated InfluxDB
and sends an email with two attachments:

- A CSV containing `_time`, `temp_displayed`, and `temp_setpoint`.
- A PDF containing a graph of displayed temperature and setpoint, an average
  temperature line, and a paginated table.

The email includes the fridge model, serial number, reporting period, and average
displayed temperature. The current deployed image is:

```text
startthefire/lh-exporter:v1.3
```

Image `v1.4` contains the later yearly/all frequency modes and the average line.

Exporter settings:

| Variable | Description |
| --- | --- |
| `EXPORT_FREQUENCY` | `monthly`, `quarterly`, `yearly`, or `all` |
| `EXPORT_CRON` | Cron expression for the scheduler, in UTC |
| `INFLUX_URL` | InfluxDB URL |
| `INFLUX_TOKEN` | InfluxDB access token |
| `INFLUX_ORG` | InfluxDB organization |
| `INFLUX_BUCKET` | InfluxDB bucket |
| `EXPORT_EMAIL_FROM` | Sender address |
| `EXPORT_EMAIL_TO` | Recipient address |
| `SMTP_SERVER` | SMTP server hostname |
| `SMTP_PORT` | SMTP submission port, normally `587` |
| `SMTP_USERNAME` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |

Frequency behavior:

- `monthly`: previous completed month.
- `quarterly`: previous three completed months, sent in January, April, July,
  and October.
- `yearly`: previous twelve completed months, sent in January.
- `all`: all available data up to the current month boundary, sent according to
  `EXPORT_CRON`.

## Compose Usage

The following example matches the deployed service layout. The `interstate`
network must already exist with a subnet that contains the assigned addresses,
or the network definition must be adapted to the local environment.

```yaml
services:
  influxdb:
    image: influxdb:latest
    container_name: influxdb_liebherr
    restart: unless-stopped
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_USERNAME: admin
      DOCKER_INFLUXDB_INIT_PASSWORD: "dummy-influx-password"
      DOCKER_INFLUXDB_INIT_ORG: fridge-demo
      DOCKER_INFLUXDB_INIT_BUCKET: fridge
      DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: "dummy-influx-token-change-me"
    volumes:
      - /mnt/influx_data_liebherr:/var/lib/influxdb2
    networks:
      interstate:
        ipv4_address: 172.19.0.90

  lh-poller:
    image: startthefire/lh-fridge-poller:v2.0
    container_name: lh-poller
    restart: unless-stopped
    environment:
      LIEBHERR_API_URL: "http://192.0.2.10:8080"
      LIEBHERR_API_TOKEN: ""
      POLL_INTERVAL: "3600"
      INFLUX_URL: "http://influxdb:8086"
      INFLUX_TOKEN: "dummy-influx-token-change-me"
      INFLUX_ORG: "fridge-demo"
      INFLUX_BUCKET: "fridge"
    networks:
      interstate:
        ipv4_address: 172.19.0.91

  lh-exporter:
    image: startthefire/lh-exporter:v1.3
    container_name: lh_exporter
    restart: unless-stopped
    environment:
      EXPORT_FREQUENCY: "quarterly"
      EXPORT_CRON: "0 3 1 * *"
      EXPORT_EMAIL_FROM: "fridge@example.invalid"
      EXPORT_EMAIL_TO: "operator@example.invalid"
      SMTP_SERVER: "smtp.example.invalid"
      SMTP_PORT: "587"
      SMTP_USERNAME: "fridge@example.invalid"
      SMTP_PASSWORD: "dummy-smtp-password"
      INFLUX_URL: "http://influxdb:8086"
      INFLUX_TOKEN: "dummy-influx-token-change-me"
      INFLUX_ORG: "fridge-demo"
      INFLUX_BUCKET: "fridge"
    depends_on:
      - influxdb
    networks:
      interstate:
        ipv4_address: 172.19.0.93

  grafana:
    build: ./grafana
    image: startthefire/lh-grafana:latest
    container_name: grafana_liebherr
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      GRAFANA_ADMIN_USER: "admin"
      GRAFANA_ADMIN_PASSWORD: "change-me"
      INFLUX_URL: "http://influxdb:8086"
      INFLUX_TOKEN: "dummy-influx-token-change-me"
      INFLUX_ORG: "fridge-demo"
      INFLUX_BUCKET: "fridge"
    volumes:
      - /mnt/grafana_data:/var/lib/grafana
    depends_on:
      - influxdb
    networks:
      interstate:
        ipv4_address: 172.19.0.92

networks:
  interstate:
    external: true
```

Use a protected `env_file` or Docker secrets for tokens and SMTP credentials
instead of committing them directly in the Compose file.

The values above are documentation-only dummy values. The `192.0.2.10` address
is a reserved documentation address, and the `.invalid` email/SMTP domains are
not expected to deliver mail. Replace them before deploying. The external
`interstate` network must also be created separately with the `172.19.0.0/24`
subnet (or the static addresses must be changed).

To start or update the stack:

```sh
docker compose pull
docker compose up -d --force-recreate
```

To trigger one test report manually from the host:

```sh
docker compose exec lh-exporter python -u /app/export.py --test
```

The test command sends a real report for the configured reporting period and
then exits; it does not start the scheduler.

The exporter uses the same InfluxDB URL, organization, bucket, and token as the
poller and Grafana. Reports therefore reflect the same retained telemetry that
is visible in the dashboards.
