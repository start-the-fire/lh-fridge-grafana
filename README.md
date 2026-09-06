# Liebherr Fridge Monitoring

This stack polls a Liebherr fridge through its SmartModule Local API, stores the
measurements in InfluxDB, and provides Grafana dashboards for monitoring and
alerting. The stack also includes a scheduled exporter that emails CSV and PDF
reports.

## Applications

### Poller

The poller calls the Liebherr Local API at the configured interval and writes the
zone status to InfluxDB measurement `fridge_zone_state`. It records the displayed
temperature, temperature setpoint, door status, alarm states, and power-failure
values. It is published as:

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

### Exporter

The exporter queries the completed reporting period from InfluxDB and sends an
email with two attachments:

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
