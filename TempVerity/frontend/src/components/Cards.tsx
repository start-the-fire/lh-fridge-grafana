type StatCardProps = {
  label: string;
  value: number | string;
  tone?: "neutral" | "success" | "warning" | "danger";
};

function StatIcon({ tone }: { tone: StatCardProps["tone"] }) {
  if (tone === "success") return <svg className="stat-icon" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="24" /><path d="m20 32 8 8 16-17" /></svg>;
  if (tone === "warning") return <svg className="stat-icon" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="24" /><path d="m32 18 16 28H16zM32 28v9M32 42v.1" /></svg>;
  if (tone === "danger") return <svg className="stat-icon" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="24" /><circle cx="24" cy="32" r="2" /><circle cx="32" cy="32" r="2" /><circle cx="40" cy="32" r="2" /></svg>;
  return <svg className="stat-icon" viewBox="0 0 64 64" aria-hidden="true"><path d="M18 11h28v42H18zM23 18h18M23 27h18M23 36h18M23 45h10" /><path d="M14 53h36" /></svg>;
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
  if (kind === "door") return <svg className="device-metric-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h11v18H6zM17 7h2v10h-2M9 6v12" /></svg>;
  if (kind === "alarm") return <svg className="device-metric-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 16h12l-1.5-2.5V9a4.5 4.5 0 0 0-9 0v4.5zM9.5 19h5" /></svg>;
  return <svg className="device-metric-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4a2 2 0 0 0-2 2v7.2a4 4 0 1 0 4 0V6a2 2 0 0 0-2-2zM12 16v-5" /></svg>;
}

export function DeviceCard({ device, expanded = false }: DeviceCardProps) {
  const hasAlarm = device.zones.some((zone) => Boolean(zone.alarm));
  const updatedAt = device.last_seen_at ? new Date(device.last_seen_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }) : "Not updated";
  return (
    <article className={`device-card${expanded ? " expanded" : ""}`}>
      <div className="device-card-image">
        <img className="device-image" src={device.image_url ?? "/fridge-fallback.svg"} alt={device.image_url ? `${device.model} appliance` : "Generic refrigerator image"} />
      </div>

      <div className="device-card-body">
        <div className="device-card-heading">
          <div className="device-row">
            <span className={`status-pill ${device.status}`}>{device.status === "ok" ? "Online" : device.status}</span>
            <span className="muted">{device.zone_count} zone{device.zone_count === 1 ? "" : "s"}</span>
          </div>
          <h3>{device.name}</h3>
          <p className="device-meta muted"><span>{device.model}</span><span>{device.location || "No location"}</span></p>
        </div>

        <div className="metric-strip">
          <div>
            <DeviceMetricIcon kind="temperature" /><span className="metric-copy"><span className="metric-label">Current</span><strong>{formatTemperature(device.temperature_c)}</strong><small>Target: {formatTemperature(device.target_c)}</small></span>
          </div>
          <div>
            <DeviceMetricIcon kind="door" /><span className="metric-copy"><span className="metric-label">Door</span><strong>{device.door_open ? "Open" : "Closed"}</strong></span>
          </div>
          <div>
            <DeviceMetricIcon kind="alarm" /><span className="metric-copy"><span className="metric-label">Alarms</span><strong>{hasAlarm ? "Active" : "None"}</strong></span>
          </div>
        </div>

        <div className="device-card-footer"><span>{device.zone_count} zone{device.zone_count === 1 ? "" : "s"}</span><span className="footer-divider" /><span>Updated: {updatedAt}</span></div>
      </div>
    </article>
  );
}
