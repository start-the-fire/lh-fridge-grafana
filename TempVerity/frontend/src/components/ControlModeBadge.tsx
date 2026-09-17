import { useTranslation } from "../i18n";

export function ControlModeBadge({ readOnly, unavailable = false }: { readOnly?: boolean; unavailable?: boolean }) {
  const { t } = useTranslation();
  const unknown = unavailable || readOnly === undefined;
  const tone = unknown ? "offline" : readOnly ? "mode-readonly" : "mode-controls";
  const label = unavailable ? "Status unavailable" : unknown ? "Checking status" : readOnly ? "Read-only enabled" : "Controls enabled";
  return <span role="status" className={`status-pill ${tone}`}>{t(label)}</span>;
}
