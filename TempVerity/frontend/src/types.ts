export type ZoneSnapshot = {
  zone_index: number;
  name: string;
  temperature_c: number | null;
  target_c: number | null;
  door_open: boolean;
  alarm: string | null;
  cooling_on: boolean;
  last_seen_at: string | null;
  parameters: Record<string, unknown>;
};

export type DeviceSnapshot = {
  id: string;
  name: string;
  manufacturer: string;
  model: string;
  location: string;
  adapter_kind: string;
  api_url: string;
  api_token_present: boolean;
  polling_interval_minutes: number;
  is_online: boolean;
  last_seen_at: string | null;
  status: "ok" | "alarm" | "offline" | "stale";
  temperature_c: number | null;
  target_c: number | null;
  door_open: boolean;
  zone_count: number;
  image_url: string | null;
  zones: ZoneSnapshot[];
  capabilities: Record<string, string[]>;
  appliance_state: Record<string, unknown>;
};

export type AlertRead = {
  id: number;
  device_id: string;
  zone_index: number | null;
  severity: string;
  title: string;
  detail: string;
  status: string;
  grace_minutes: number;
  activated_at: string;
  resolved_at: string | null;
};

export type EventRead = {
  id: number;
  device_id: string | null;
  zone_index: number | null;
  kind: string;
  status: string;
  detail: string;
  created_at: string;
};

export type NotificationRead = {
  id: number;
  alert_id: number;
  kind: string;
  recipient: string;
  status: string;
  attempts: number;
  attempted_at: string | null;
  next_attempt_at: string | null;
  sent_at: string | null;
  error_message: string | null;
};

export type BootstrapResponse = {
  generated_at: string;
  greeting: string;
  summary: {
    total_devices: number;
    online_devices: number;
    alarm_devices: number;
    offline_devices: number;
  };
  devices: DeviceSnapshot[];
  alerts: AlertRead[];
  events: EventRead[];
  settings: Record<string, unknown>;
  read_only: boolean;
};

export type HealthResponse = {
  status: string;
  app: string;
  version: string;
  devices: number;
  read_only: boolean;
};

export type AppMetadata = {
  version: string;
  support_email: string;
  grafana_url: string;
};

export type AuthStatus = {
  enabled: boolean;
  dashboard_requires_auth: boolean;
  authenticated: boolean;
  username: string | null;
  role: "admin" | "viewer" | null;
};
