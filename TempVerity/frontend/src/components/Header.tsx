import { useTranslation } from "../i18n";
import { parseBackendDate } from "../date";

type HeaderProps = {
  greeting: string;
  description?: string;
  generatedAt: string;
  onRefresh: () => void;
  isRefreshing: boolean;
};

export function Header({ greeting, description = "Current status, state cache, and device controls in one place.", generatedAt, onRefresh, isRefreshing }: HeaderProps) {
  const { t } = useTranslation();
  const date = parseBackendDate(generatedAt);
  return (
    <header className="header">
      <div>
        <p className="eyebrow">{t("Operations dashboard")}</p>
        <h1>{t(greeting)}</h1>
        <p className="lede">{t(description)}</p>
      </div>

      <div className="header-actions">
        <div className="timestamp">
          <small>{t("Last updated")}</small>
          <span>{date.toLocaleDateString(undefined, { weekday: "long", year: "numeric", month: "long", day: "numeric" })}</span>
          <strong>{date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}</strong>
        </div>
        <button className="primary-button" type="button" onClick={onRefresh} disabled={isRefreshing}>
          {isRefreshing ? t("Refreshing...") : t("Refresh")}
        </button>
      </div>
    </header>
  );
}
