type HeaderProps = {
  greeting: string;
  description?: string;
  generatedAt: string;
  onRefresh: () => void;
  isRefreshing: boolean;
};

export function Header({ greeting, description = "Current status, state cache, and device controls in one place.", generatedAt, onRefresh, isRefreshing }: HeaderProps) {
  const date = new Date(generatedAt);
  return (
    <header className="header">
      <div>
        <p className="eyebrow">Operations dashboard</p>
        <h1>{greeting}!</h1>
        <p className="lede">{description}</p>
      </div>

      <div className="header-actions">
        <div className="timestamp">
          <small>Last updated</small>
          <span>{date.toLocaleDateString(undefined, { weekday: "long", year: "numeric", month: "long", day: "numeric" })}</span>
          <strong>{date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}</strong>
        </div>
        <button className="primary-button" type="button" onClick={onRefresh} disabled={isRefreshing}>
          {isRefreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>
    </header>
  );
}
