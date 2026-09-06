#!/bin/sh
set -eu

TEMPLATE_ROOT="/etc/grafana-templates"
PROVISIONING_ROOT="/etc/grafana/provisioning"
DASHBOARD_ROOT="/var/lib/grafana/dashboards"

mkdir -p "$PROVISIONING_ROOT/datasources" "$PROVISIONING_ROOT/dashboards" "$DASHBOARD_ROOT"

render() {
  envsubst '$INFLUX_URL $INFLUX_TOKEN $INFLUX_ORG $INFLUX_BUCKET' < "$1" > "$2"
  # Manual imports use Grafana's datasource input token; provisioning uses our stable UID.
  sed -i 's/\${DS_INFLUXDB}/influxdb/g' "$2"
}

render "$TEMPLATE_ROOT/provisioning/datasources/influxdb.yml.tpl" \
  "$PROVISIONING_ROOT/datasources/influxdb.yml"
cp "$TEMPLATE_ROOT/provisioning/dashboards/dashboards.yml" \
  "$PROVISIONING_ROOT/dashboards/dashboards.yml"
render "$TEMPLATE_ROOT/dashboards/fridge-overview.json.tpl" \
  "$DASHBOARD_ROOT/fridge-overview.json"
render "$TEMPLATE_ROOT/dashboards/fridge-operations.json.tpl" \
  "$DASHBOARD_ROOT/fridge-operations.json"

exec /run.sh "$@"
