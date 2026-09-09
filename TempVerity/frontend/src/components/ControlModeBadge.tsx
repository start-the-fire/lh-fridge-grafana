export function ControlModeBadge({ readOnly, unavailable = false }: { readOnly?: boolean; unavailable?: boolean }) {
  const unknown = unavailable || readOnly === undefined;
  const tone = unknown ? "offline" : readOnly ? "mode-readonly" : "mode-controls";
  const label = unavailable ? "Status unavailable" : unknown ? "Checking status" : readOnly ? "Read-only enabled" : "Controls enabled";
  return <span role="status" className={`status-pill ${tone}`}>{label}</span>;
}
