import { ControlModeBadge } from "./components/ControlModeBadge";
import { Icon } from "./components/Icon";
import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { BrowserRouter, Link, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchJson } from "./api/client";
import { Header } from "./components/Header";
import { DeviceCard, StatCard } from "./components/Cards";
import { Sidebar } from "./components/Sidebar";
import { useTranslation } from "./i18n";
import type { AlertRead, AppMetadata, AuthStatus, BootstrapResponse, DeviceSnapshot, EventRead, HealthResponse, HistoricalDataStatus, NotificationRead } from "./types";

function humanStatus(status: string, t: (text: string) => string): string {
  return t(({ success: "Successful", failed: "Failed", pending: "Pending", active: "Active", recovery: "Recovering", resolved: "Resolved" } as Record<string, string>)[status] ?? status.replace(/[-_]/g, " "));
}

function eventTitle(event: EventRead, t: (text: string) => string): string {
  if (event.kind === "poll" && event.status === "failed") return t("Device refresh failed");
  if (event.kind === "poll") return t("Device state refreshed");
  if (event.kind === "device-created") return t("Device added");
  if (event.kind === "device-updated") return t("Device updated");
  if (event.kind === "device-deleted") return t("Device removed");
  return event.detail;
}

function eventContext(event: EventRead, t: (text: string) => string): string {
  const technicalDetail = event.kind === "poll" && event.status === "failed" ? event.detail.split(": ").slice(1).join(": ") : "";
  return [event.kind === "poll" ? t("Automatic refresh") : t("System activity"), event.device_id ?? t("System"), technicalDetail].filter(Boolean).join(" | ");
}

function HelpIndicator({ text }: { text: string }) {
  return <span className="help-indicator" title={text} aria-label={text} tabIndex={0}>?</span>;
}

function parameterNumber(value: unknown) {
  return typeof value === "number" ? `${value} °C` : "Not reported";
}

function ZoneParameters({ parameters }: { parameters: Record<string, unknown> }) {
  const { t } = useTranslation();
  const range = parameters.temperature_range_c as { min?: unknown; max?: unknown } | undefined;
  const temperatureAlarm = parameters.temperature_alarm as { upper?: Record<string, unknown>; lower?: Record<string, unknown>; refresh_time?: unknown } | undefined;
  const upper = temperatureAlarm?.upper ?? {};
  const lower = temperatureAlarm?.lower ?? {};
  const powerFailure = parameters.power_failure_alarm as { upper_limit_c?: unknown; lower_limit_c?: unknown } | undefined;
  return <div className="appliance-parameters"><div className="parameter-group"><strong>{t("Temperature limits")}</strong><span>{t("Setpoint range:")} {parameterNumber(range?.min)} {t("to")} {parameterNumber(range?.max)}</span><span>{t("Upper alarm limit:")} {parameterNumber(upper.limit)} | {t("Lower alarm limit:")} {parameterNumber(lower.limit)}</span><span>{t("Alarm refresh interval:")} {typeof temperatureAlarm?.refresh_time === "number" ? `${temperatureAlarm.refresh_time} ${t("min")}` : t("Not reported")}</span><small>{t("Alarm limits are reported by the appliance. The available API does not provide an endpoint to change them.")}</small></div><div className="parameter-group"><strong>{t("Safety parameters")}</strong><span>{t("Power-failure upper threshold:")} {parameterNumber(powerFailure?.upper_limit_c)}</span><span>{t("Power-failure lower threshold:")} {parameterNumber(powerFailure?.lower_limit_c)}</span><span>{t("Emergency alarm:")} {parameters.emergency_alarm_state ? t("Active") : t("Normal")}</span><span>{t("Manual defrost:")} {parameters.manual_defrost ? t("Active") : t("Inactive")}</span></div></div>;
}

function AlarmRefreshControl({ parameters, readOnly, pending, onApply }: { parameters: Record<string, unknown>; readOnly: boolean; pending: boolean; onApply: (value: number) => void }) {
  const { t } = useTranslation();
  const temperatureAlarm = parameters.temperature_alarm as { refresh_time?: unknown } | undefined;
  const refreshTime = temperatureAlarm?.refresh_time;
  const [value, setValue] = useState(typeof refreshTime === "number" ? String(refreshTime) : "");
  useEffect(() => { if (typeof refreshTime === "number") setValue(String(refreshTime)); }, [refreshTime]);
  if (typeof refreshTime !== "number") return null;
  return <form className="parameter-control" onSubmit={(event) => { event.preventDefault(); const next = Number(value); if (Number.isFinite(next) && next >= 0 && window.confirm(`${t("Change the temperature alarm refresh time to")} ${next} ${t("minutes?")}`)) onApply(next); }}><label>{t("Temperature alarm refresh time")}<input type="number" min="0" max="1440" step="1" value={value} onChange={(event) => setValue(event.target.value)} disabled={readOnly || pending} /> {t("min")}</label><button className="secondary-button" type="submit" disabled={readOnly || pending || !value}>{pending ? t("Applying...") : t("Apply alarm timing")}</button></form>;
}

function LoginPage() {
  const { t } = useTranslation();
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const login = useMutation({ mutationFn: () => fetchJson("/api/auth/login", { method: "POST", body: JSON.stringify({ password }) }), onSuccess: () => window.location.reload(), onError: () => setError("Unable to sign in.") });
  return <main className="login-shell"><section className="login-card"><div className="login-brand"><img className="login-logo" src="/tempverity-logo-v2.png" alt="TempVerity" /></div><div className="login-content"><p className="eyebrow">{t("Protected website")}</p><h1>{t("Welcome back")}</h1><p className="lede">{t("Enter the website password to access TempVerity.")}</p><form className="login-form" onSubmit={(event) => { event.preventDefault(); setError(""); login.mutate(); }}><label>{t("Password")}<span className="password-field"><input type={showPassword ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} autoFocus autoComplete="current-password" /><button className="password-toggle" type="button" onClick={() => setShowPassword((visible) => !visible)}>{showPassword ? t("Hide") : t("Show")}</button></span></label>{error ? <div className="banner error">{error}</div> : null}<button className="primary-button login-submit" type="submit" disabled={login.isPending}>{login.isPending ? t("Signing in...") : t("Continue to TempVerity")}</button></form><p className="login-note">{t("Access remains active on this browser for the configured session duration.")}</p></div></section></main>;
}

function AuthGate({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const { data, isLoading } = useQuery({ queryKey: ["auth-status"], queryFn: () => fetchJson<AuthStatus>("/api/auth/status") });
  if (isLoading) return <div className="banner">{t("Loading authentication status...")}</div>;
  if (data?.enabled && !data.authenticated) return <LoginPage />;
  return <>{children}</>;
}

function Dashboard() {
  const { t } = useTranslation();
  const [deviceView, setDeviceView] = useState<"expanded" | "minimal">("expanded");
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["bootstrap"],
    queryFn: () => fetchJson<BootstrapResponse>("/api/bootstrap"),
    refetchInterval: 30000,
  });

  const devices = data?.devices ?? [];
  const alerts = data?.alerts ?? [];
  const events = data?.events ?? [];
  const dashboardEvents = events.slice(0, 5);
  const dashboardAlerts = alerts.slice(0, 5);

  const temperatureRows = useMemo(
    () =>
      devices.map((device) => ({
        device: device.name,
        zone: device.zones[0]?.name ?? "Zone 0",
        current: device.temperature_c,
        target: device.target_c,
        status: device.status,
      })),
    [devices],
  );

  return (
    <div className="shell">
      <Sidebar />
      <main className="main">
        {data ? (
          <Header greeting={data.greeting} generatedAt={data.generated_at} onRefresh={() => refetch()} isRefreshing={isFetching} />
        ) : (
          <Header greeting="TempVerity" generatedAt={new Date().toISOString()} onRefresh={() => refetch()} isRefreshing={isFetching} />
        )}
        {data?.read_only ? <div className="banner readonly-banner">{t("Read-only monitoring mode is active. Fridge controls are disabled.")}</div> : null}

        {error ? <div className="banner error">Unable to load dashboard: {String(error)}</div> : null}
        {isLoading && !data ? <div className="banner">Loading dashboard cache...</div> : null}

        <section className="stats-grid">
          <StatCard label={t("Total devices")} value={data?.summary.total_devices ?? 0} />
          <StatCard label={t("Online")} value={data?.summary.online_devices ?? 0} tone="success" />
          <StatCard label={t("With alarm")} value={data?.summary.alarm_devices ?? 0} tone="warning" />
          <StatCard label={t("Offline")} value={data?.summary.offline_devices ?? 0} tone="danger" />
        </section>

        <section className="content-grid">
          <div className="panel panel-wide">
            <div className="panel-header">
              <div><h2>{t("Devices")}</h2><span className="muted">{devices.length} {t("configured appliances")}</span></div>
              <div className="view-toggle" role="group" aria-label={t("Device card view")}><button className={deviceView === "expanded" ? "active" : ""} type="button" onClick={() => setDeviceView("expanded")} aria-pressed={deviceView === "expanded"}><Icon name="grid" />{t("Expanded")}</button><button className={deviceView === "minimal" ? "active" : ""} type="button" onClick={() => setDeviceView("minimal")} aria-pressed={deviceView === "minimal"}><Icon name="list" />{t("Minimal")}</button></div>
            </div>
            <div className={`device-grid ${deviceView}-view`}>
              {devices.map((device) => (
                <DeviceCard key={device.id} device={device} expanded={deviceView === "expanded"} />
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h2 className="section-title"><Icon name="events" />{t("Recent events")}</h2>
              <div className="panel-header-actions"><span className="muted">{dashboardEvents.length} {t("entries")}</span><Link className="panel-header-link" to="/events">{t("View all")}</Link></div>
            </div>
            <div className="list">
              {dashboardEvents.map((event) => (
                <div key={event.id} className="list-row recent-event-row">
                  <time dateTime={event.created_at}>{new Date(event.created_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}</time>
                  <div>
                    <strong>{eventTitle(event, t)}</strong>
                    <div className="muted">{eventContext(event, t)} | {humanStatus(event.status, t)}</div>
                  </div>
                  <span className={`status-pill ${event.status === "failed" ? "danger" : event.status === "active" ? "warning" : "ok"}`}>{humanStatus(event.status, t)}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h2 className="section-title"><Icon name="temperature" />{t("Temperature overview")}</h2>
              <span className="muted">{t("Current vs target")}</span>
            </div>
            <div className="table">
              <div className="table-row table-head">
                <span>{t("Device")}</span>
                <span>{t("Zone")}</span>
                <span>{t("Current")}</span>
                <span>{t("Target")}</span>
                <span>{t("Status")}</span>
              </div>
              {temperatureRows.map((row) => (
                <div key={`${row.device}-${row.zone}`} className="table-row">
                  <span>{row.device}</span>
                  <span>{row.zone}</span>
                  <span>{row.current == null ? "—" : `${row.current.toFixed(1)} °C`}</span>
                  <span>{row.target == null ? "—" : `${row.target.toFixed(1)} °C`}</span>
                  <span className={`status-pill ${row.status}`}>{row.status}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="panel panel-wide">
            <div className="panel-header">
              <h2 className="section-title"><Icon name="bell" />{t("Alerts")}</h2>
              <div className="panel-header-actions"><span className="muted">{dashboardAlerts.length} {t("tracked conditions")}</span><Link className="panel-header-link" to="/alarms">{t("View all")}</Link></div>
            </div>
            <div className="list">
              {dashboardAlerts.length === 0 ? <div className="empty-alerts"><Icon name="bell" /><strong>{t("No alerts to display")}</strong><p className="muted">{t("No conditions are currently tracked. Check device status for data availability.")}</p></div> : null}
              {dashboardAlerts.map((alert) => (
                <div key={alert.id} className="list-row">
                  <div>
                    <strong>{alert.title}</strong>
                    <div className="muted">{alert.detail} | Grace period: {alert.grace_minutes} min</div>
                  </div>
                  <span className={`status-pill ${alert.status === "active" ? "danger" : alert.status === "pending" ? "warning" : "ok"}`}>{humanStatus(alert.status, t)}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

function ReportsPage() {
  const { t } = useTranslation();
  const { data, isLoading } = useQuery({ queryKey: ["bootstrap"], queryFn: () => fetchJson<BootstrapResponse>("/api/bootstrap") });
  const { data: metadata } = useQuery({ queryKey: ["metadata"], queryFn: () => fetchJson<{ grafana_url: string }>("/api/metadata") });
  const devices = data?.devices ?? [];
  return <PageFrame title="Reports" body={t("Historical reporting remains connected to the existing InfluxDB and Grafana stack.")}>
    <div className="reports-grid">
      <section className="panel"><div className="panel-header"><h2 className="section-title"><Icon name="events" />{t("Historical reporting")}</h2><span className="status-pill ok">{t("External")}</span></div><p className="lede">{t("TempVerity does not duplicate the existing historical telemetry pipeline. InfluxDB and Grafana remain independent so monitoring continues even when either service is unavailable.")}</p>{metadata?.grafana_url ? <a className="primary-button report-link" href={metadata.grafana_url} target="_blank" rel="noreferrer">{t("Open Grafana reports")}</a> : <p className="muted">{t("Set TEMPVERITY_GRAFANA_URL to show the Grafana reports link here.")}</p>}</section>
      <section className="panel"><div className="panel-header"><h2 className="section-title"><Icon name="reports" />{t("Current-state snapshot")}</h2><span className="muted">{devices.length} {t("Devices")}</span></div>{isLoading ? <p className="lede">{t("Loading current state...")}</p> : <div className="report-table">{devices.map((device) => <div className="report-row" key={device.id}><div><strong>{device.name}</strong><span className="muted">{device.model} | {device.location || t("No location")}</span></div><div><strong>{device.temperature_c == null ? "—" : `${device.temperature_c.toFixed(1)} °C`}</strong><span className={`status-pill ${device.status}`}>{device.status}</span></div></div>)}</div>}</section>
    </div>
  </PageFrame>;
}

function AboutPage() {
  const { data: health, isError: healthError } = useQuery({ queryKey: ["health"], queryFn: () => fetchJson<HealthResponse>("/api/health"), refetchInterval: 30000 });
  const { t } = useTranslation();
  return <PageFrame title="About" body={t("Application information, features, and how it works.")}>
    <div className="about-grid">
      <section className="panel">
        <div className="panel-header"><h2 className="section-title"><Icon name="shield" />{t("What TempVerity does")}</h2>{health?.version ? <span className="about-version">{t("Version")} {health.version}</span> : null}</div>
        <p>{t("TempVerity is a self-hosted temperature monitoring application for professional refrigeration appliances in laboratories, pharmacies, healthcare facilities, and similar environments.")}</p>
        <p>{t("It brings device status, current and target temperatures, door conditions, alarms, and operational events into one interface, helping you identify conditions that need attention.")}</p>
      </section>
      <section className="panel">
        <div className="panel-header"><h2 className="section-title"><Icon name="settings" />{t("How it works")}</h2></div>
        <p>{t("TempVerity polls each configured appliance through its local API, stores the latest reported state locally, and evaluates available readings against configured software alarm rules. Update frequency depends on the polling interval and device connectivity.")}</p>
        <p>{t("Current-state monitoring, historical storage, reporting, and alert delivery can be configured independently so routine visibility and long-term records can use different intervals.")}</p>
      </section>
      <section className="panel">
        <div className="panel-header"><h2 className="section-title"><Icon name="reports" />{t("Historical data")}</h2></div>
        <p>{t("TempVerity can write long-term appliance samples to a dedicated InfluxDB bucket while keeping application state in its local database. Historical writes use their own interval and store one sample per reported device zone.")}</p>
        <p>{t("Grafana dashboard links can be added on the Historical Data page. Embedded dashboard cards are loaded only when that page is opened and can be hidden entirely through the deployment environment.")}</p>
      </section>
      <section className="panel">
        <div className="panel-header"><h2 className="section-title"><Icon name="mail" />{t("Email reports")}</h2></div>
        <p>{t("Scheduled historical reports can be generated from InfluxDB data and delivered as email attachments. Reports include CSV data and a PDF summary with temperature trends.")}</p>
        <p>{t("Report frequency and recipients are configured on the Historical Data page. Sender address, SMTP host, credentials, and transport security are reused from the SMTP notification settings.")}</p>
      </section>
      <section className="panel">
        <div className="panel-header"><h2 className="section-title"><Icon name="bell" />{t("Alerts and notifications")}</h2></div>
        <p>{t("TempVerity tracks connectivity problems, appliance-reported alarms, and configured software alarm conditions. Grace periods let you control how long a condition must persist before a notification is sent.")}</p>
        <p>{t("Alerts appear in the application and can be delivered by email when SMTP is configured and enabled. Recovery and repeat notifications follow your settings. Recorded alarms and events are available for review in their dedicated pages.")}</p>
      </section>
      <section className="panel">
        <div className="panel-header"><h2 className="section-title"><Icon name="shield" />{t("Safety mode")}</h2><ControlModeBadge readOnly={health?.read_only} unavailable={healthError} /></div>
        <p>{healthError ? t("The current operating mode could not be retrieved. Check the application connection before relying on the status shown here.") : !health ? t("Checking whether this installation allows appliance control actions.") : health.read_only ? t("Read-only monitoring mode is enabled. Appliance control actions are disabled, while monitoring and alerts remain available.") : t("Read-only monitoring mode is disabled. Authorized users can send supported control actions to connected appliances.")}</p>
        <p>{t("TempVerity supports operational awareness; it does not guarantee storage conditions, certify regulatory compliance, or replace appliance safety systems and established monitoring procedures.")}</p>
      </section>
    </div>
  </PageFrame>;
}

function SoftwareRuleHelper({ devices, value, onChange }: { devices: DeviceSnapshot[]; value: string; onChange: (value: string) => void }) {
  const [deviceId, setDeviceId] = useState(devices[0]?.id ?? "");
  const [zoneIndex, setZoneIndex] = useState(0);
  const [condition, setCondition] = useState("above");
  const [threshold, setThreshold] = useState("7");
  const [grace, setGrace] = useState("10");
  const [recoveryGrace, setRecoveryGrace] = useState("5");
  const device = devices.find((item) => item.id === deviceId) ?? devices[0];
  const zone = device?.zones.find((item) => item.zone_index === zoneIndex) ?? device?.zones[0];
  const alarm = zone?.parameters.temperature_alarm as { upper?: { limit?: unknown }; lower?: { limit?: unknown } } | undefined;
  const recommendedRules = () => devices.flatMap((item) => item.zones.flatMap((itemZone) => {
    const zoneAlarm = itemZone.parameters.temperature_alarm as { upper?: { limit?: unknown }; lower?: { limit?: unknown } } | undefined;
    const rules = [
      typeof zoneAlarm?.upper?.limit === "number" ? { id: `${item.id}-${itemZone.zone_index}-upper-temperature`, name: "Upper temperature limit", device_id: item.id, zone_index: itemZone.zone_index, condition: "above", threshold: zoneAlarm.upper.limit, grace_minutes: 10, recovery_grace_minutes: 5 } : null,
      typeof zoneAlarm?.lower?.limit === "number" ? { id: `${item.id}-${itemZone.zone_index}-lower-temperature`, name: "Lower temperature limit", device_id: item.id, zone_index: itemZone.zone_index, condition: "below", threshold: zoneAlarm.lower.limit, grace_minutes: 10, recovery_grace_minutes: 5 } : null,
      { id: `${item.id}-${itemZone.zone_index}-door-open`, name: "Door left open", device_id: item.id, zone_index: itemZone.zone_index, condition: "door_open", grace_minutes: 10, recovery_grace_minutes: 5 },
    ];
    return rules.filter(Boolean);
  }));
  const appendRules = (newRules: unknown[]) => {
    try {
      const current = JSON.parse(value);
      if (!Array.isArray(current)) throw new Error();
      const existingIds = new Set(current.map((rule) => rule?.id));
      onChange(JSON.stringify([...current, ...newRules.filter((rule) => !existingIds.has((rule as { id?: string }).id))], null, 2));
    } catch { onChange(JSON.stringify(newRules, null, 2)); }
  };
  const addRule = () => {
    if (!device || !zone) return;
    const rule = { id: `${device.id}-${zone.zone_index}-${condition}-${Date.now()}`, name: condition === "above" ? "Temperature above limit" : condition === "below" ? "Temperature below limit" : "Door left open", device_id: device.id, zone_index: zone.zone_index, condition, ...(condition === "door_open" ? {} : { threshold: Number(threshold) }), grace_minutes: Number(grace), recovery_grace_minutes: Number(recoveryGrace) };
    appendRules([rule]);
  };
  useEffect(() => {
    if (device && !deviceId) setDeviceId(device.id);
    const selectedZone = device?.zones.find((item) => item.zone_index === zoneIndex) ?? device?.zones[0];
    if (selectedZone && selectedZone.zone_index !== zoneIndex) setZoneIndex(selectedZone.zone_index);
    const selectedAlarm = selectedZone?.parameters.temperature_alarm as { upper?: { limit?: unknown }; lower?: { limit?: unknown } } | undefined;
    const suggested = condition === "above" ? selectedAlarm?.upper?.limit : selectedAlarm?.lower?.limit;
    if (typeof suggested === "number") setThreshold(String(suggested));
  }, [device, deviceId, zoneIndex, condition]);
  return <div className="rule-helper"><div className="rule-helper-header"><strong>Alarm rule helper</strong><button className="secondary-button" type="button" onClick={() => appendRules(recommendedRules())} disabled={devices.length === 0}>Add recommended rules</button></div><div className="rule-helper-grid"><label>Device<select value={device?.id ?? ""} onChange={(event) => { setDeviceId(event.target.value); setZoneIndex(0); }}><option value="">Select device</option>{devices.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>Zone<select value={zone?.zone_index ?? 0} onChange={(event) => setZoneIndex(Number(event.target.value))}>{device?.zones.map((item) => <option key={item.zone_index} value={item.zone_index}>{item.name}</option>)}</select></label><label>Condition<select value={condition} onChange={(event) => setCondition(event.target.value)}><option value="above">Temperature above</option><option value="below">Temperature below</option><option value="door_open">Door remains open</option></select></label>{condition !== "door_open" ? <label>Threshold (°C)<input type="number" step="0.1" value={threshold} onChange={(event) => setThreshold(event.target.value)} /></label> : null}<label>Grace period (min)<input type="number" min="0" value={grace} onChange={(event) => setGrace(event.target.value)} /></label><label>Recovery grace (min)<input type="number" min="0" value={recoveryGrace} onChange={(event) => setRecoveryGrace(event.target.value)} /></label></div><button className="secondary-button" type="button" onClick={addRule} disabled={!device || !zone}>Add alarm rule</button></div>;
}

function SettingsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: settings, isLoading } = useQuery({ queryKey: ["settings"], queryFn: () => fetchJson<Record<string, Record<string, unknown>>>("/api/settings") });
  const { data: devices = [] } = useQuery({ queryKey: ["devices"], queryFn: () => fetchJson<DeviceSnapshot[]>("/api/devices") });
  const { data: health } = useQuery({ queryKey: ["health"], queryFn: () => fetchJson<HealthResponse>("/api/health") });
  const [smtp, setSmtp] = useState({ enabled: false, host: "", port: 587, security: "STARTTLS", username: "", password: "", from: "", recipients: "" });
  const [alerts, setAlerts] = useState({ connectivityGraceMinutes: 10, alarmGraceMinutes: 5, recoveryGraceMinutes: 0, recovery: true, repeat: false });
  const [auth, setAuth] = useState({ enabled: false, dashboardRequiresAuth: false, sessionValue: 12, sessionUnit: "hours", adminPassword: "", viewerPassword: "" });
  const [softwareRulesText, setSoftwareRulesText] = useState("[]");
  const [softwareRulesError, setSoftwareRulesError] = useState("");
  useEffect(() => {
    const currentSmtp = settings?.smtp ?? {};
    const currentAlerts = settings?.alerts ?? {};
    setSmtp({ enabled: Boolean(currentSmtp.enabled), host: String(currentSmtp.host ?? ""), port: Number(currentSmtp.port ?? 587), security: String(currentSmtp.security ?? "STARTTLS"), username: String(currentSmtp.username ?? ""), password: "", from: String(currentSmtp.from ?? ""), recipients: Array.isArray(currentSmtp.recipients) ? currentSmtp.recipients.join(", ") : String(currentSmtp.recipients ?? "") });
    setAlerts({ connectivityGraceMinutes: Number(currentAlerts.connectivityGraceMinutes ?? 10), alarmGraceMinutes: Number(currentAlerts.alarmGraceMinutes ?? 5), recoveryGraceMinutes: Number(currentAlerts.recoveryGraceMinutes ?? 0), recovery: currentAlerts.recovery !== false, repeat: Boolean(currentAlerts.repeat) });
    setSoftwareRulesText(JSON.stringify(currentAlerts.softwareRules ?? [], null, 2));
    const currentAuth = settings?.auth ?? {};
    const sessionMinutes = Number(currentAuth.sessionMinutes ?? 720);
    const sessionUnit = sessionMinutes % (60 * 24 * 30) === 0 ? "months" : sessionMinutes % (60 * 24) === 0 ? "days" : "hours";
    const divisor = sessionUnit === "months" ? 60 * 24 * 30 : sessionUnit === "days" ? 60 * 24 : 60;
    setAuth({ enabled: Boolean(currentAuth.enabled), dashboardRequiresAuth: Boolean(currentAuth.dashboardRequiresAuth), sessionValue: Math.max(1, Math.round(sessionMinutes / divisor)), sessionUnit, adminPassword: "", viewerPassword: "" });
  }, [settings]);
  const save = useMutation({ mutationFn: ({ section, values }: { section: string; values: Record<string, unknown> }) => fetchJson(`/api/settings/${section}`, { method: "PATCH", body: JSON.stringify({ values }) }), onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ["settings"] }); void queryClient.invalidateQueries({ queryKey: ["historical-data-status"] }); } });
  const smtpTest = useMutation({ mutationFn: () => fetchJson<{ ok: boolean; message: string }>("/api/settings/smtp/test", { method: "POST" }) });
  const saveSmtp = (event: FormEvent) => { event.preventDefault(); save.mutate({ section: "smtp", values: { ...smtp, port: Number(smtp.port), password: smtp.password || undefined, recipients: smtp.recipients.split(",").map((item) => item.trim()).filter(Boolean) } }); };
  const saveAlerts = (event: FormEvent) => { event.preventDefault(); try { const softwareRules = JSON.parse(softwareRulesText); if (!Array.isArray(softwareRules)) throw new Error("Software alarm rules must be a JSON array."); setSoftwareRulesError(""); save.mutate({ section: "alerts", values: { ...alerts, softwareRules } }); } catch (error) { setSoftwareRulesError(error instanceof Error ? error.message : "Invalid software alarm rules."); } };
  const saveAuth = (event: FormEvent) => {
    event.preventDefault();
    const multiplier = auth.sessionUnit === "months" ? 60 * 24 * 30 : auth.sessionUnit === "days" ? 60 * 24 : 60;
    void fetchJson("/api/auth/configure", {
      method: "POST",
      body: JSON.stringify({
        enabled: auth.enabled,
        dashboard_requires_auth: auth.dashboardRequiresAuth,
        session_minutes: Math.max(5, Math.round(auth.sessionValue * multiplier)),
        admin_password: auth.adminPassword || undefined,
        viewer_password: auth.viewerPassword || undefined,
      }),
    }).then(() => queryClient.invalidateQueries({ queryKey: ["settings"] }));
  };
  return <PageFrame title="Settings" body={t("Application behavior and notification configuration. Changes here do not alter appliance parameters.")}>
    <div className="settings-grid">
      <section className="panel"><div className="panel-header"><h2 className="section-title"><Icon name="monitor" />Monitoring</h2><ControlModeBadge readOnly={health?.read_only} /></div><p className="lede">{health ? (health.read_only ? "Appliance controls are disabled by read-only mode." : "Read-only mode is disabled. Authorized control actions can change appliance settings.") : "Checking monitoring mode..."}</p><p className="muted">Polling runs independently for each configured device and uses the interval stored on that device.</p></section>
      <section className="panel"><div className="panel-header"><h2 className="section-title"><Icon name="mail" />SMTP notifications</h2><span className="muted">{smtpTest.data?.message ?? "No test sent"}</span></div><form className="form-grid" onSubmit={saveSmtp}><label>Enabled<input type="checkbox" checked={smtp.enabled} onChange={(event) => setSmtp({ ...smtp, enabled: event.target.checked })} /></label><label>Host<input value={smtp.host} onChange={(event) => setSmtp({ ...smtp, host: event.target.value })} /></label><label>Port<input type="number" min="1" max="65535" value={smtp.port} onChange={(event) => setSmtp({ ...smtp, port: Number(event.target.value) })} /></label><label>Security<select value={smtp.security} onChange={(event) => setSmtp({ ...smtp, security: event.target.value })}><option>None</option><option>STARTTLS</option><option>TLS</option></select></label><label>Sender username<input value={smtp.username} onChange={(event) => setSmtp({ ...smtp, username: event.target.value })} autoComplete="username" /></label><label>Sender password<input type="password" value={smtp.password} onChange={(event) => setSmtp({ ...smtp, password: event.target.value })} placeholder="Leave blank to keep current password" autoComplete="new-password" /></label><label>Sender address<input type="email" value={smtp.from} onChange={(event) => setSmtp({ ...smtp, from: event.target.value })} /></label><label>Recipients<input value={smtp.recipients} onChange={(event) => setSmtp({ ...smtp, recipients: event.target.value })} placeholder="alerts@example.com, lab@example.com" /></label><button className="primary-button" type="submit" disabled={save.isPending}>{save.isPending ? "Saving..." : "Save SMTP settings"}</button><button className="secondary-button" type="button" onClick={() => smtpTest.mutate()} disabled={smtpTest.isPending}>{smtpTest.isPending ? "Sending test..." : "Send test email"}</button></form>{smtpTest.error ? <div className="banner error">SMTP test failed.</div> : null}</section>
      <section className="panel"><div className="panel-header"><div><h2 className="section-title"><Icon name="bell" />Alert timing and rules</h2><span className="muted">Grace periods and software-defined limits</span></div><HelpIndicator text="Software rules are evaluated against cached zone temperatures and do not change appliance settings." /></div><form id="alert-settings" className="form-grid" onSubmit={saveAlerts}><label>Connectivity grace minutes<input type="number" min="0" value={alerts.connectivityGraceMinutes} onChange={(event) => setAlerts({ ...alerts, connectivityGraceMinutes: Number(event.target.value) })} /></label><label>Alarm grace minutes<input type="number" min="0" value={alerts.alarmGraceMinutes} onChange={(event) => setAlerts({ ...alerts, alarmGraceMinutes: Number(event.target.value) })} /></label><label>Recovery grace minutes<input type="number" min="0" value={alerts.recoveryGraceMinutes} onChange={(event) => setAlerts({ ...alerts, recoveryGraceMinutes: Number(event.target.value) })} /></label><label>Recovery notifications<input type="checkbox" checked={alerts.recovery} onChange={(event) => setAlerts({ ...alerts, recovery: event.target.checked })} /></label><label>Repeat notifications<input type="checkbox" checked={alerts.repeat} onChange={(event) => setAlerts({ ...alerts, repeat: event.target.checked })} /></label><SoftwareRuleHelper devices={devices} value={softwareRulesText} onChange={setSoftwareRulesText} />{softwareRulesError ? <div className="banner error">{softwareRulesError}</div> : null}<button className="primary-button" type="submit" disabled={save.isPending}>{save.isPending ? "Saving..." : "Save alert settings"}</button></form></section>
      <section className="panel"><div className="panel-header"><h2 className="section-title"><Icon name="lock" />Login access</h2><span className="muted">Optional administrator and viewer access</span></div><form className="form-grid" onSubmit={saveAuth}><label><span className="setting-label">Enable login <HelpIndicator text="When enabled, users must enter either the administrator or view-only password before accessing TempVerity." /></span><input type="checkbox" checked={auth.enabled} onChange={(event) => setAuth({ ...auth, enabled: event.target.checked })} /></label><label><span className="setting-label">Require login for dashboard <HelpIndicator text="Protects the dashboard when login is enabled. It has no effect while login is disabled." /></span><input type="checkbox" checked={auth.dashboardRequiresAuth} onChange={(event) => setAuth({ ...auth, dashboardRequiresAuth: event.target.checked })} /></label><label><span className="setting-label">Session duration <HelpIndicator text="How long a successful login remains active in this browser before the user must sign in again." /></span><input type="number" min="1" value={auth.sessionValue} onChange={(event) => setAuth({ ...auth, sessionValue: Number(event.target.value) })} /></label><label><span className="setting-label">Duration unit <HelpIndicator text="The unit used for the session duration: hours, days, or months. A month is treated as 30 days." /></span><select value={auth.sessionUnit} onChange={(event) => setAuth({ ...auth, sessionUnit: event.target.value })}><option value="hours">Hours</option><option value="days">Days</option><option value="months">Months</option></select></label><label><span className="setting-label">Administrator password <HelpIndicator text="Password for full access, including Devices and Settings. Leave blank to keep the current password." /></span><input type="password" value={auth.adminPassword} onChange={(event) => setAuth({ ...auth, adminPassword: event.target.value })} placeholder="Leave blank to keep current password" autoComplete="new-password" /></label><label><span className="setting-label">View-only password <HelpIndicator text="Password for monitoring access only. View-only users can see the dashboard, alarms, events, and reports, but not Devices or Settings." /></span><input type="password" value={auth.viewerPassword} onChange={(event) => setAuth({ ...auth, viewerPassword: event.target.value })} placeholder="Leave blank to keep current password" autoComplete="new-password" /></label><p className="muted">When login is enabled, all application pages require a password. The view-only account can see monitoring, alarms, events, and reports, but not Devices or Settings.</p><button className="primary-button" type="submit">Save login settings</button></form></section>
      <section className="panel software-rules-panel"><div className="panel-header"><h2 className="section-title"><Icon name="code" />Software alarm rules (JSON)</h2></div><div className="form-grid"><label>Advanced rule configuration<textarea form="alert-settings" rows={14} value={softwareRulesText} onChange={(event) => setSoftwareRulesText(event.target.value)} spellCheck={false} /></label><button className="primary-button" form="alert-settings" type="submit" disabled={save.isPending}>Save alert settings</button></div></section>
    </div>{isLoading ? <div className="banner">Loading settings...</div> : null}
  </PageFrame>;
}

function HistoricalDataPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: settings, isLoading } = useQuery({ queryKey: ["settings"], queryFn: () => fetchJson<Record<string, Record<string, unknown>>>("/api/settings") });
  const { data: historicalStatus } = useQuery({ queryKey: ["historical-data-status"], queryFn: () => fetchJson<HistoricalDataStatus>("/api/settings/historical-data/status"), refetchInterval: 30000 });
  const { data: metadata } = useQuery({ queryKey: ["metadata"], queryFn: () => fetchJson<AppMetadata>("/api/metadata") });
  const grafanaEmbedsEnabled = metadata?.grafana_embeds_enabled !== false;
  const [historicalData, setHistoricalData] = useState({ enabled: false, intervalMinutes: 60 });
  const [reportSettings, setReportSettings] = useState({ reportEnabled: false, reportFrequency: "monthly", reportRecipients: "" });
  const [grafanaCards, setGrafanaCards] = useState<{ title: string; url: string }[]>([]);
  useEffect(() => {
    const currentHistoricalData = settings?.historicalData ?? {};
    setHistoricalData({ enabled: Boolean(currentHistoricalData.enabled), intervalMinutes: Number(currentHistoricalData.intervalMinutes ?? 60) });
    setReportSettings({
      reportEnabled: Boolean(currentHistoricalData.reportEnabled),
      reportFrequency: String(currentHistoricalData.reportFrequency ?? "monthly"),
      reportRecipients: Array.isArray(currentHistoricalData.reportRecipients) ? currentHistoricalData.reportRecipients.join(", ") : String(currentHistoricalData.reportRecipients ?? ""),
    });
    const cards = Array.isArray(currentHistoricalData.grafanaCards) ? currentHistoricalData.grafanaCards : [];
    setGrafanaCards(cards.map((card) => {
      const value = card as Record<string, unknown>;
      return { title: String(value.title ?? "Grafana dashboard"), url: String(value.url ?? "") };
    }).filter((card) => card.url || card.title));
  }, [settings]);
  const save = useMutation({
    mutationFn: (values: Record<string, unknown>) => fetchJson("/api/settings/historicalData", { method: "PATCH", body: JSON.stringify({ values }) }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
      void queryClient.invalidateQueries({ queryKey: ["historical-data-status"] });
    },
  });
  const sendReport = useMutation({ mutationFn: () => fetchJson<{ ok: boolean; message: string }>("/api/settings/historical-data/report", { method: "POST" }), onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ["historical-data-status"] }); void queryClient.invalidateQueries({ queryKey: ["events"] }); } });
  const saveHistoricalData = (event: FormEvent) => {
    event.preventDefault();
    save.mutate({ enabled: historicalData.enabled, intervalMinutes: Math.max(1, Number(historicalData.intervalMinutes)) });
  };
  const saveReports = (event: FormEvent) => {
    event.preventDefault();
    save.mutate({
      reportEnabled: reportSettings.reportEnabled,
      reportFrequency: reportSettings.reportFrequency,
      reportRecipients: reportSettings.reportRecipients.split(",").map((item) => item.trim()).filter(Boolean),
    });
  };
  const saveGrafanaCards = (event: FormEvent) => {
    event.preventDefault();
    save.mutate({ grafanaCards: grafanaCards.map((card) => ({ title: card.title.trim() || "Grafana dashboard", url: card.url.trim() })).filter((card) => card.url) });
  };
  const addGrafanaCard = () => setGrafanaCards([...grafanaCards, { title: "Grafana dashboard", url: "" }]);
  const updateGrafanaCard = (index: number, values: Partial<{ title: string; url: string }>) => setGrafanaCards(grafanaCards.map((card, cardIndex) => cardIndex === index ? { ...card, ...values } : card));
  const removeGrafanaCard = (index: number) => setGrafanaCards(grafanaCards.filter((_, cardIndex) => cardIndex !== index));
  const reportsReady = historicalStatus?.state === "ok";
  const reportBadgeTone = !reportSettings.reportEnabled ? "stale" : reportsReady ? "ok" : "warning";
  const reportBadgeLabel = !reportSettings.reportEnabled ? "disabled" : reportsReady ? "enabled" : "history required";
  return <PageFrame title="Historical Data" body={t("Long-term temperature and appliance-state storage for Grafana and reporting. Connection details are provided by Docker Compose environment variables.")}>
    <div className="settings-detail-stack">
    <section className="panel settings-detail-panel">
      <div className="panel-header"><div><h2 className="section-title"><Icon name="mail" />{t("Email reports")}</h2><span className="muted">{t("Uses the SMTP sender configured in Settings")}</span></div><span className={`status-pill ${reportBadgeTone}`}>{t(reportBadgeLabel)}</span></div>
      <form className="form-grid" onSubmit={saveReports}>
        <label>{t("Enabled")}<input type="checkbox" checked={reportSettings.reportEnabled} onChange={(event) => setReportSettings({ ...reportSettings, reportEnabled: event.target.checked })} /></label>
        <label>{t("Export frequency")}<select value={reportSettings.reportFrequency} onChange={(event) => setReportSettings({ ...reportSettings, reportFrequency: event.target.value })}><option value="daily">{t("Daily")}</option><option value="weekly">{t("Weekly")}</option><option value="monthly">{t("Monthly")}</option><option value="quarterly">{t("Quarterly")}</option><option value="yearly">{t("Yearly")}</option><option value="all">{t("All")}</option></select></label>
        <label>{t("Target email address(es)")}<input type="text" value={reportSettings.reportRecipients} onChange={(event) => setReportSettings({ ...reportSettings, reportRecipients: event.target.value })} placeholder="lab@example.com, qa@example.com" /></label>
        {reportSettings.reportEnabled && !reportsReady ? <div className="banner warning">Email reports are enabled, but cannot run until the InfluxDB history connection is healthy. Current history status: {humanStatus(historicalStatus?.state ?? "checking", t)}.</div> : null}
        {reportSettings.reportEnabled && reportsReady ? <p className="muted">Next scheduled report: {historicalStatus?.nextReportAt ? new Date(historicalStatus.nextReportAt).toLocaleString() : "Not calculated"}</p> : null}
        {reportSettings.reportEnabled && historicalStatus?.lastReportSentAt ? <p className="muted">Last report: {new Date(historicalStatus.lastReportSentAt).toLocaleString()}</p> : null}
        {reportSettings.reportEnabled && reportsReady ? <p className="muted">{reportSettings.reportFrequency === "all" ? "All exports are sent at the next midnight run and then switch automatically to quarterly." : "Manual sending uses the last completed calendar period for the selected frequency."}</p> : null}
        {reportSettings.reportEnabled && (historicalStatus?.lastReportStatus || sendReport.data?.message) ? <p className="muted">{historicalStatus?.lastReportStatus ?? sendReport.data?.message}</p> : null}
        <button className="primary-button" type="submit" disabled={save.isPending}>{save.isPending ? t("Saving...") : t("Save report settings")}</button>
        {reportSettings.reportEnabled && reportsReady ? <button className="secondary-button" type="button" onClick={() => sendReport.mutate()} disabled={sendReport.isPending || reportSettings.reportFrequency === "all"}>{sendReport.isPending ? "Sending..." : reportSettings.reportFrequency === "all" ? "Scheduled overnight" : "Send report now"}</button> : null}
      </form>
      {sendReport.error ? <div className="banner error">Report delivery failed.</div> : null}
    </section>
    <section className="panel settings-detail-panel">
      <div className="panel-header"><div><h2 className="section-title"><Icon name="reports" />{t("InfluxDB history")}</h2><span className="muted">{historicalStatus?.bucket ? `Bucket: ${historicalStatus.bucket}` : t("InfluxDB connection from environment")}</span></div><span className={`status-pill ${historicalStatus?.state === "ok" ? "ok" : historicalStatus?.state === "disabled" ? "stale" : "danger"}`}>{t(historicalStatus?.state === "missing_config" ? "Missing Config" : humanStatus(historicalStatus?.state ?? "checking", t))}</span></div>
      <form className="form-grid" onSubmit={saveHistoricalData}>
        <label>{t("Enabled")}<input type="checkbox" checked={historicalData.enabled} onChange={(event) => setHistoricalData({ ...historicalData, enabled: event.target.checked })} /></label>
        <label>{t("Write interval minutes")}<input type="number" min="1" max="1440" value={historicalData.intervalMinutes} onChange={(event) => setHistoricalData({ ...historicalData, intervalMinutes: Number(event.target.value) })} /></label>
        <p className="muted">{historicalStatus?.message ?? t("Checking historical data status...")}</p>
        <p className="muted">{t("Last successful write: None recorded")}</p>
        <button className="primary-button" type="submit" disabled={save.isPending}>{save.isPending ? t("Saving...") : t("Save historical data settings")}</button>
      </form>
      {isLoading ? <div className="banner">Loading historical data settings...</div> : null}
    </section>
    {grafanaEmbedsEnabled ? <section className="panel settings-detail-panel grafana-embed-settings">
      <div className="panel-header"><div><h2 className="section-title"><Icon name="reports" />Grafana embeds</h2><span className="muted">{grafanaCards.length} configured card{grafanaCards.length === 1 ? "" : "s"}</span></div><button className="secondary-button" type="button" onClick={addGrafanaCard}>Add card</button></div>
      <form className="form-grid grafana-card-form" onSubmit={saveGrafanaCards}>
        <p className="muted">Embedded dashboards require Grafana to allow iframe display. If the browser blocks the card, enable embedding in Grafana or use Open.</p>
        {grafanaCards.length === 0 ? <p className="muted">Add a shared Grafana dashboard URL to show it below.</p> : null}
        {grafanaCards.map((card, index) => <div className="grafana-card-editor" key={index}>
          <label>Card title<input value={card.title} onChange={(event) => updateGrafanaCard(index, { title: event.target.value })} /></label>
          <label>Shared dashboard URL<input type="url" value={card.url} onChange={(event) => updateGrafanaCard(index, { url: event.target.value })} placeholder="https://monitor.example/public-dashboards/..." /></label>
          <button className="secondary-button" type="button" onClick={() => removeGrafanaCard(index)}>Remove</button>
        </div>)}
        <button className="primary-button" type="submit" disabled={save.isPending}>{save.isPending ? "Saving..." : "Save Grafana embeds"}</button>
      </form>
    </section> : null}
    {grafanaEmbedsEnabled ? grafanaCards.filter((card) => card.url.trim()).map((card, index) => <section className="panel settings-detail-panel grafana-embed-panel" key={`${card.url}-${index}`}>
      <div className="panel-header"><h2 className="section-title"><Icon name="reports" />{card.title || "Grafana dashboard"}</h2><a className="secondary-button" href={card.url} target="_blank" rel="noreferrer">Open</a></div>
      <p className="muted grafana-embed-note">If this dashboard is blocked here, Grafana is sending frame-protection headers. Open it in a new tab or enable embedding on the Grafana server.</p>
      <iframe title={card.title || `Grafana dashboard ${index + 1}`} src={card.url} loading="lazy" referrerPolicy="no-referrer-when-downgrade" />
    </section>) : null}
    </div>
  </PageFrame>;
}

function AlertsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: alerts = [], isLoading } = useQuery({ queryKey: ["alerts"], queryFn: () => fetchJson<AlertRead[]>("/api/alerts") });
  const { data: notifications = [] } = useQuery({ queryKey: ["notifications"], queryFn: () => fetchJson<NotificationRead[]>("/api/notifications") });
  const [comments, setComments] = useState<Record<number, string>>({});
  const acknowledge = useMutation({ mutationFn: ({ id, comment }: { id: number; comment: string }) => fetchJson<AlertRead>(`/api/alerts/${id}/acknowledge`, { method: "POST", body: JSON.stringify({ comment }) }), onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ["alerts"] }); void queryClient.invalidateQueries({ queryKey: ["events"] }); void queryClient.invalidateQueries({ queryKey: ["bootstrap"] }); } });
  const failedNotifications = notifications.filter((item) => item.status === "failed");
  return <PageFrame title="Alarms" body={t("Current and historical appliance conditions, including grace-period state.")}><section className="panel"><div className="panel-header"><h2 className="section-title"><Icon name="bell" />{t("Alarm history")}</h2><span className="muted">{alerts.length} records</span></div>{isLoading ? <p className="lede">Loading alarms...</p> : <div className="alert-grid">{alerts.map((alert) => <article className={`alert-card state-${alert.status}`} key={alert.id}><div className="device-row"><strong>{alert.title}</strong><span className={`status-pill ${alert.status === "active" ? "danger" : alert.status === "pending" || alert.status === "recovery" ? "warning" : "ok"}`}>{humanStatus(alert.status, t)}</span></div><p className="muted">{alert.detail}</p><p className="muted">Device: {alert.device_id} | Grace period: {alert.grace_minutes} minutes</p>{acknowledge.isError && acknowledge.variables?.id === alert.id ? <div className="banner error" role="alert">Unable to acknowledge alarm: {acknowledge.error.message}</div> : null}{alert.acknowledged_at ? <p className="muted" role="status">Acknowledged: {new Date(alert.acknowledged_at).toLocaleString()}{alert.acknowledgement_comment ? ` | ${alert.acknowledgement_comment}` : ""}</p> : null}{!alert.acknowledged_at && ["pending", "active", "recovery"].includes(alert.status) ? <form className="acknowledge-form" onSubmit={(event) => { event.preventDefault(); acknowledge.mutate({ id: alert.id, comment: comments[alert.id] ?? "" }); }}><input value={comments[alert.id] ?? ""} onChange={(event) => setComments({ ...comments, [alert.id]: event.target.value })} placeholder="Optional acknowledgement comment" /><button className="secondary-button" type="submit" disabled={acknowledge.isPending}>{acknowledge.isPending && acknowledge.variables?.id === alert.id ? "Acknowledging..." : "Acknowledge"}</button></form> : null}</article>)}</div>}</section>{failedNotifications.length > 0 ? <section className="panel"><div className="panel-header"><h2>Notification delivery</h2><span className="status-pill danger">{failedNotifications.length} Failed</span></div>{failedNotifications.map((item) => <p className="muted" key={item.id}>{item.recipient}: attempt {item.attempts} failed{item.error_message ? ` (${item.error_message})` : ""}</p>)}</section> : null}</PageFrame>;
}

function EventsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: events = [], isLoading } = useQuery({ queryKey: ["events"], queryFn: () => fetchJson<EventRead[]>("/api/events") });
  const purge = useMutation({ mutationFn: () => fetchJson<void>("/api/events", { method: "DELETE" }), onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ["events"] }); void queryClient.invalidateQueries({ queryKey: ["bootstrap"] }); } });
  return <PageFrame title="Events" body={t("Read-only operational and audit feed for TempVerity.")}><section className="panel"><div className="panel-header"><div><h2 className="section-title"><Icon name="events" />Event feed</h2><span className="muted">Showing the 25 most recent entries</span></div><button className="danger-button" type="button" disabled={purge.isPending || events.length === 0} onClick={() => { if (window.confirm("Purge all local TempVerity events? This does not contact or change any fridge.")) purge.mutate(); }}><Icon name="trash" />{purge.isPending ? "Purging..." : t("Purge events")}</button></div>{purge.error ? <div className="banner error">Unable to purge events: {String(purge.error)}</div> : null}{isLoading ? <p className="lede">Loading events...</p> : events.length === 0 ? <p className="lede">No events recorded.</p> : <div className="event-table-wrap"><table className="event-table"><thead><tr><th>Time</th><th>Event</th><th>Status</th></tr></thead><tbody>{events.map((event) => <tr key={event.id}><td><time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time></td><td><strong>{eventTitle(event, t)}</strong><div className="muted">{eventContext(event, t)}</div></td><td><span className={`status-pill ${event.status === "failed" ? "danger" : event.status === "active" ? "warning" : "ok"}`}>{humanStatus(event.status, t)}</span></td></tr>)}</tbody></table></div>}</section></PageFrame>;
}

function DevicesPage() {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ name: "", location: "", api_url: "", api_token: "" });
  const { data: devices = [], isLoading, error } = useQuery({ queryKey: ["devices"], queryFn: () => fetchJson<DeviceSnapshot[]>("/api/devices") });
  const addDevice = useMutation({
    mutationFn: () => fetchJson<DeviceSnapshot>("/api/devices", { method: "POST", body: JSON.stringify({ ...form, manufacturer: "Liebherr", model: "Unknown", adapter_kind: "liebherr" }) }),
    onSuccess: () => {
      setForm({ name: "", location: "", api_url: "", api_token: "" });
      void queryClient.invalidateQueries({ queryKey: ["devices"] });
      void queryClient.invalidateQueries({ queryKey: ["bootstrap"] });
    },
  });

  return (
    <PageFrame title="Devices" body={t("Connect appliances, inspect their discovered zones, and manage their current-state cache.")}>
      <div className="device-management-grid">
        <section className="panel">
          <div className="panel-header"><h2 className="section-title"><Icon name="devices" />{t("Configured appliances")}</h2><span className="muted">{devices.length} total</span></div>
          {isLoading ? <p className="lede">{t("Loading devices...")}</p> : null}
          {error ? <div className="banner error">{t("Unable to load devices.")}</div> : null}
          <div className="device-search-field"><Icon name="search" /><input className="device-search" aria-label={t("Search devices...")} placeholder={t("Search devices...")} value={search} onChange={(event) => setSearch(event.target.value)} /></div>
          <div className="managed-device-list">
            {devices.filter((device) => `${device.name} ${device.model} ${device.location}`.toLowerCase().includes(search.toLowerCase())).map((device) => (
              <Link className="managed-device" key={device.id} to={`/devices/${device.id}`} title={`Open settings for ${device.name}`}>
                <span className="managed-device-image"><img src={device.image_url ?? "/fridge-fallback.svg"} alt="" /></span>
                <div className="managed-device-copy"><strong>{device.name}</strong><span className="muted managed-device-meta">{device.model}<span aria-hidden="true"> · </span>{device.location || t("No location")}</span><span className="muted">{device.zone_count} {t(device.zone_count === 1 ? "Zone" : "Zones")}</span></div>
                <span className={`status-pill ${device.status}`}>{device.status === "ok" ? t("Online") : humanStatus(device.status, t)}</span>
                <Icon name="chevronRight" className="managed-device-chevron" />
              </Link>
            ))}
          </div>
        </section>
        <section className="panel">
          <div className="panel-header"><h2 className="section-title"><Icon name="plus" />{t("Add appliance")}</h2><span className="muted">{t("Discovery runs immediately")}</span></div>
          <form className="form-grid" onSubmit={(event) => { event.preventDefault(); addDevice.mutate(); }}>
            {(["name", "location", "api_url", "api_token"] as const).map((field) => (
              <label key={field}>{t({ name: "Name", location: "Location", api_url: "Local API URL", api_token: "API token" }[field])}
                <input required={field === "name" || field === "api_url"} type={field === "api_token" ? "password" : "text"} value={form[field]} onChange={(event) => setForm({ ...form, [field]: event.target.value })} placeholder={field === "api_url" ? "http://192.168.1.50:8080" : ""} />
              </label>
            ))}
            {addDevice.error ? <div className="banner error">{String(addDevice.error)}</div> : null}
            <button className="primary-button" type="submit" disabled={addDevice.isPending}>{addDevice.isPending ? t("Discovering...") : t("Add and discover")}</button>
          </form>
        </section>
      </div>
    </PageFrame>
  );
}

function DevicePage() {
  const { t } = useTranslation();
  const { deviceId = "" } = useParams();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [showEdit, setShowEdit] = useState(false);
  const [showTechnicalState, setShowTechnicalState] = useState(false);
  const [editValues, setEditValues] = useState({ name: "", location: "", api_url: "", api_token: "" });
  const [setpointValues, setSetpointValues] = useState<Record<number, string>>({});
  const { data: device, isLoading, error } = useQuery({ queryKey: ["device", deviceId], queryFn: () => fetchJson<DeviceSnapshot>(`/api/devices/${deviceId}`), enabled: Boolean(deviceId) });
  const { data: health } = useQuery({ queryKey: ["health"], queryFn: () => fetchJson<HealthResponse>("/api/health"), staleTime: 30000 });
  const readOnly = health?.read_only ?? true;
  useEffect(() => {
    if (device) {
      setEditValues({ name: device.name, location: device.location, api_url: device.api_url, api_token: "" });
      setSetpointValues(Object.fromEntries(device.zones.map((zone) => [zone.zone_index, zone.target_c == null ? "" : String(zone.target_c)])));
    }
  }, [device]);
  const refresh = useMutation({ mutationFn: () => fetchJson<DeviceSnapshot>(`/api/devices/${deviceId}/refresh`, { method: "POST" }), onSuccess: (next) => queryClient.setQueryData(["device", deviceId], next) });
  const imageRefresh = useMutation({ mutationFn: () => fetchJson<DeviceSnapshot>(`/api/devices/${deviceId}/image/refresh`, { method: "POST" }), onSuccess: (next) => queryClient.setQueryData(["device", deviceId], next) });
  const control = useMutation({
    mutationFn: ({ action, payload, method = "POST" }: { action: string; payload?: Record<string, unknown>; method?: "POST" | "DELETE" }) => fetchJson<DeviceSnapshot>(`/api/devices/${deviceId}/controls/${action}`, { method, ...(method === "POST" ? { body: JSON.stringify({ payload: payload ?? {} }) } : {}) }),
    onSuccess: (next) => queryClient.setQueryData(["device", deviceId], next),
  });
  const update = useMutation({
    mutationFn: () => fetchJson<DeviceSnapshot>(`/api/devices/${deviceId}`, { method: "PATCH", body: JSON.stringify({ ...editValues, api_token: editValues.api_token || undefined }) }),
    onSuccess: (next) => {
      queryClient.setQueryData(["device", deviceId], next);
      void queryClient.invalidateQueries({ queryKey: ["devices"] });
      void queryClient.invalidateQueries({ queryKey: ["bootstrap"] });
      setEditValues({ ...editValues, api_token: "" });
    },
  });
  const remove = useMutation({
    mutationFn: () => fetchJson<void>(`/api/devices/${deviceId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ["device", deviceId] });
      void queryClient.invalidateQueries({ queryKey: ["devices"] });
      void queryClient.invalidateQueries({ queryKey: ["bootstrap"] });
      navigate("/devices", { replace: true });
    },
  });

  if (isLoading) return <PageFrame title="Device" body="Loading cached state..."><section className="panel"><p className="lede">Loading...</p></section></PageFrame>;
  if (error || !device) return <PageFrame title="Device unavailable" body="The requested appliance could not be loaded."><section className="panel"><Link className="primary-button" to="/devices">Back to devices</Link></section></PageFrame>;
  const allCapabilities = Object.values(device.capabilities).flat().map((capability) => capability.toLowerCase());
  const supports = (name: string) => allCapabilities.some((capability) => capability.includes(name));
  const controls = [
    ["child-lock", "Child lock", "appliance/setting/child-lock"],
    ["eco-mode", "Eco mode", "appliance/setting/eco-mode"],
    ["temperatureunit", "Temperature unit", "appliance/setting/temperature-unit"],
    ["acousticalarm", "Acoustic alarm", "appliance/setting/acoustic-alarm"],
    ["presentationlight", "Presentation light", "appliance/presentation-light"],
  ] as const;
  const zoneControls = [
    ["supercool", "SuperCool", "supercool", "POST"],
    ["superfrost", "SuperFrost", "superfrost", "POST"],
    ["cooling", "Cooling", "cooling", "POST"],
    ["humidity", "Humidity setpoint", "humidity", "POST"],
    ["humidityreminder", "Humidity reminder", "humidity/reminder", "POST"],
    ["humidifiermode", "Humidifier mode", "humidifier/mode", "POST"],
    ["doorlock", "Open door lock", "door/lock/open", "POST"],
    ["dooralarm", "Acknowledge door alarm", "door/alarm", "DELETE"],
    ["doorlockalarm", "Acknowledge door-lock alarm", "door/lock/alarm", "DELETE"],
    ["emergencyalarm", "Acknowledge emergency alarm", "alarm/emergency-alarm", "DELETE"],
    ["upperpowerfailurealarm", "Acknowledge upper power alarm", "alarm/power-failure-alarm/upper", "DELETE"],
    ["lowerpowerfailurealarm", "Acknowledge lower power alarm", "alarm/power-failure-alarm/lower", "DELETE"],
    ["uppertemperaturealarm", "Acknowledge upper temperature alarm", "temperature/alarm/upper", "DELETE"],
    ["lowertemperaturealarm", "Acknowledge lower temperature alarm", "temperature/alarm/lower", "DELETE"],
  ] as const;
  return (
    <PageFrame title={device.name} body={`${device.model} | ${device.location || t("No location configured")}`}>
      <div className="detail-actions"><Link className="secondary-button" to="/devices">All devices</Link><button className="primary-button" onClick={() => refresh.mutate()} disabled={refresh.isPending}>{refresh.isPending ? "Refreshing..." : "Refresh appliance"}</button><button className="secondary-button" onClick={() => imageRefresh.mutate()} disabled={imageRefresh.isPending || Boolean(device.image_url)}>{imageRefresh.isPending ? "Finding image..." : device.image_url ? "Image loaded" : "Find fridge image"}</button><button className="danger-button" onClick={() => { if (window.confirm("Remove this appliance and its cached history?")) remove.mutate(); }}>Remove</button></div>
      {imageRefresh.error ? <div className="banner error">No suitable automatic image was found. The fallback image remains available.</div> : null}
      {readOnly ? <div className="banner readonly-banner">{t("Read-only monitoring mode is active. Fridge controls are disabled.")}</div> : null}
      <div className="device-detail-sections">
      <section className="panel detail-summary">
        <div><span className={`status-pill ${device.status}`}>{device.status}</span><p className="muted">{device.api_url}</p><p className="muted">{t("Last successful update:")} {device.last_seen_at ? new Date(device.last_seen_at).toLocaleString() : t("Never")}</p></div>
        <div className="metric-strip"><div><span className="metric-label">{t("Current")}</span><strong>{device.temperature_c ?? "—"}°C</strong></div><div><span className="metric-label">{t("Target")}</span><strong>{device.target_c ?? "—"}°C</strong></div><div><span className="metric-label">{t("Door")}</span><strong>{device.door_open ? t("Open") : t("Closed")}</strong></div></div>
      </section>
      <section className="zone-detail-grid">
        {device.zones.map((zone) => <article className="panel" key={zone.zone_index}><div className="panel-header"><h2>{t(zone.name)}</h2><span className={`status-pill ${zone.alarm ? "alarm" : "ok"}`}>{zone.alarm ?? t("Normal")}</span></div><div className="zone-reading"><strong>{zone.temperature_c ?? "—"}°C</strong><span className="muted">{t("setpoint")} {zone.target_c ?? "—"}°C</span></div><p className="muted">{t("Door")} {t(zone.door_open ? "open" : "closed")} | {t("Cooling")} {t(zone.cooling_on ? "on" : "off")}</p>{supports("temperature") ? <form className="zone-configuration" onSubmit={(event) => { event.preventDefault(); const value = Number(setpointValues[zone.zone_index]); if (!Number.isFinite(value)) return; if (window.confirm(`Confirm changing the temperature setpoint for ${zone.name} to ${value.toFixed(1)} °C?`)) control.mutate({ action: `zones/${zone.zone_index}/temperature`, payload: { value } }); }}><label>{t("Temperature setpoint")} <input type="number" min="-50" max="50" step="0.1" value={setpointValues[zone.zone_index] ?? ""} onChange={(event) => setSetpointValues({ ...setpointValues, [zone.zone_index]: event.target.value })} disabled={readOnly || control.isPending} /></label><button className="secondary-button" type="submit" disabled={readOnly || control.isPending || !setpointValues[zone.zone_index]}>{control.isPending ? t("Applying...") : t("Apply setpoint")}</button></form> : null}<ZoneParameters parameters={zone.parameters} /><AlarmRefreshControl parameters={zone.parameters} readOnly={readOnly} pending={control.isPending} onApply={(value) => control.mutate({ action: `zones/${zone.zone_index}/temperature/alarm/refresh-time`, payload: { value } })} /><div className="control-list">{zoneControls.filter(([capability]) => supports(capability)).map(([, label, action, method]) => <button className="secondary-button" key={action} disabled={readOnly || control.isPending} onClick={() => { const target = method === "DELETE" ? "the acknowledged state" : "the configured API value"; if (window.confirm(`Confirm changing ${label} for ${zone.name} to ${target}?`)) control.mutate({ action: `zones/${zone.zone_index}/${action}`, method }); }}>{t(label)}</button>)}</div></article>)}
      </section>
      <section className="panel"><div className="panel-header"><h2 className="section-title"><Icon name="grid" />{t("Supported controls")}</h2><span className="muted">{readOnly ? t("Visible but disabled in read-only mode") : t("Only discovered capabilities are actionable")}</span></div><div className="control-list">{controls.filter(([capability]) => supports(capability)).map(([, label, action]) => <button className="secondary-button" key={action} disabled={readOnly || control.isPending} onClick={() => { if (window.confirm(`Confirm changing ${label} to the requested API value?`)) control.mutate({ action }); }}>{t(label)}</button>)}{controls.every(([capability]) => !supports(capability)) ? <p className="muted">{t("No matching controls were reported by this appliance.")}</p> : null}</div>{control.error ? <div className="banner error">Control failed: {String(control.error)}</div> : null}</section>
      <section className="panel"><div className="panel-header"><div><h2 className="section-title"><Icon name="lock" />Connection settings</h2><span className="muted">Change endpoint, token, or operator label</span></div><button className="secondary-button" type="button" onClick={() => setShowEdit(!showEdit)}>{showEdit ? "Hide" : "Show"}</button></div>{showEdit ? <form className="form-grid" onSubmit={(event) => { event.preventDefault(); update.mutate(); }}><label>Name<input required value={editValues.name} onChange={(event) => setEditValues({ ...editValues, name: event.target.value })} /></label><label>Location<input value={editValues.location} onChange={(event) => setEditValues({ ...editValues, location: event.target.value })} /></label><label>Local API URL<input required value={editValues.api_url} onChange={(event) => setEditValues({ ...editValues, api_url: event.target.value })} /></label><label>API token<input type="password" value={editValues.api_token} onChange={(event) => setEditValues({ ...editValues, api_token: event.target.value })} placeholder={device.api_token_present ? "Configured, unchanged" : "Optional"} /></label>{update.error ? <div className="banner error">Update failed: {String(update.error)}</div> : null}<button className="primary-button" type="submit" disabled={update.isPending}>{update.isPending ? "Saving..." : "Save connection"}</button></form> : null}</section>
      <section className="panel"><div className="panel-header"><div><h2 className="section-title"><Icon name="code" />{t("Technical API state")}</h2><span className="muted">{t("Read-only view of the latest reported values")}</span></div><button className="secondary-button" type="button" onClick={() => setShowTechnicalState((visible) => !visible)}>{showTechnicalState ? t("Hide") : t("Show")}</button></div>{showTechnicalState ? <pre className="technical-json">{JSON.stringify({ appliance: device.appliance_state, capabilities: device.capabilities, zones: device.zones.map((zone) => ({ name: zone.name, parameters: zone.parameters })) }, null, 2)}</pre> : null}</section>
      </div>
    </PageFrame>
  );
}

function PageFrame({ title, body, children }: { title: string; body: string; children: ReactNode }) {
  const { t } = useTranslation();
  const { data, refetch, isFetching } = useQuery({ queryKey: ["bootstrap"], queryFn: () => fetchJson<BootstrapResponse>("/api/bootstrap") });
  return <div className="shell"><Sidebar /><main className="main"><Header greeting={t(title)} description={body} generatedAt={data?.generated_at ?? new Date().toISOString()} onRefresh={() => refetch()} isRefreshing={isFetching} />{children}</main></div>;
}

export function App() {
  return (
    <BrowserRouter>
      <AuthGate><Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/devices" element={<DevicesPage />} />
        <Route path="/devices/:deviceId" element={<DevicePage />} />
        <Route path="/alarms" element={<AlertsPage />} />
        <Route path="/events" element={<EventsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/settings/historical-data" element={<HistoricalDataPage />} />
      </Routes></AuthGate>
    </BrowserRouter>
  );
}
