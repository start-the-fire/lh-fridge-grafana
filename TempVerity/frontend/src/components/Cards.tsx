import { Icon } from "./Icon";
import { useTranslation } from "../i18n";
import { parseBackendDate } from "../date";

type StatCardProps = {
  label: string;
  value: number | string;
  tone?: "neutral" | "success" | "warning" | "danger";
};

function StatIcon({ tone }: { tone: StatCardProps["tone"] }) {
  return <Icon className="stat-icon" name={tone === "success" ? "online" : tone === "warning" ? "alarm" : tone === "danger" ? "offline" : "devices"} />;
}

export function StatCard({ label, value, tone = "neutral" }: StatCardProps) {
  return (
    <article className={`stat-card ${tone}`}>
      <StatIcon tone={tone} />
      <div className="stat-copy"><div className="stat-value">{value}</div><div className="stat-label">{label}</div></div>
    </article>
  );
}

type DeviceCardProps = {
  expanded?: boolean;
  device: {
    id: string;
    name: string;
    model: string;
    location: string;
    status: string;
    temperature_c: number | null;
    target_c: number | null;
    door_open: boolean;
    zone_count: number;
    last_seen_at: string | null;
    image_url: string | null;
    zones: Array<{
      zone_index: number;
      name: string;
      temperature_c: number | null;
      target_c: number | null;
      door_open: boolean;
      alarm: string | null;
    }>;
  };
};

function formatTemperature(value: number | null) {
  return value == null ? "—" : `${value.toFixed(1)} °C`;
}

function DeviceMetricIcon({ kind }: { kind: "temperature" | "door" | "alarm" }) {
  return <Icon className="device-metric-icon" name={kind === "alarm" ? "bell" : kind} />;
}

export function DeviceCard({ device, expanded = false }: DeviceCardProps) {
  const { t } = useTranslation();
  const hasAlarm = device.zones.some((zone) => Boolean(zone.alarm));
  const updatedAt = device.last_seen_at ? parseBackendDate(device.last_seen_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }) : t("Not updated");
  return (
    <article className={`device-card${expanded ? " expanded" : ""}`}>
      <div className="device-card-image">
        <img className="device-image" src={device.image_url ?? "/fridge-fallback.svg"} alt={device.image_url ? `${device.model} appliance` : "Generic refrigerator image"} />
      </div>

      <div className="device-card-body">
        <div className="device-card-heading">
          <div className="device-row">
            <span className={`status-pill ${device.status}`}>{device.status === "ok" ? t("Online") : t(device.status)}</span>
            <span className="muted">{device.zone_count} {t(device.zone_count === 1 ? "Zone" : "Zones")}</span>
          </div>
          <h3>{device.name}</h3>
          <p className="device-meta muted"><span>{device.model}</span><span>{device.location || t("No location")}</span></p>
        </div>

        <div className="metric-strip">
          <div>
            <DeviceMetricIcon kind="temperature" /><span className="metric-copy"><span className="metric-label">{t("Current")}</span><strong>{formatTemperature(device.temperature_c)}</strong><small>{t("Target")}: {formatTemperature(device.target_c)}</small></span>
          </div>
          <div>
            <DeviceMetricIcon kind="door" /><span className="metric-copy"><span className="metric-label">{t("Door")}</span><strong>{t(device.door_open ? "Open" : "Closed")}</strong></span>
          </div>
          <div>
            <DeviceMetricIcon kind="alarm" /><span className="metric-copy"><span className="metric-label">{t("Alarms")}</span><strong>{t(hasAlarm ? "Active" : "None")}</strong></span>
          </div>
        </div>

        <div className="device-card-footer"><span>{device.zone_count} {t(device.zone_count === 1 ? "Zone" : "Zones")}</span><span className="footer-divider" /><span>{t("Updated")}: {updatedAt}</span></div>
      </div>
    </article>
  );
}
