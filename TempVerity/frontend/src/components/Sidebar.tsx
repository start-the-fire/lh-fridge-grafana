import { Link, NavLink } from "react-router-dom";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchJson } from "../api/client";
import type { AppMetadata, AuthStatus } from "../types";

const items = [
  { to: "/", label: "Dashboard", icon: "dashboard" },
  { to: "/devices", label: "Devices", icon: "devices" },
  { to: "/alarms", label: "Alarms", icon: "alarms" },
  { to: "/events", label: "Events", icon: "events" },
  { to: "/reports", label: "Reports", icon: "reports" },
  { to: "/settings", label: "Settings", icon: "settings" },
];

type SidebarIconName = (typeof items)[number]["icon"];

function SidebarIcon({ name }: { name: SidebarIconName }) {
  const paths: Record<SidebarIconName, string> = {
    dashboard: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
    devices: "M5 3h14v18H5zM8 7h8M8 11h8M8 15h4",
    alarms: "M12 4a5 5 0 0 0-5 5v3l-2 3h14l-2-3V9a5 5 0 0 0-5-5zM10 19h4",
    events: "M6 3h12v18H6zM9 7h6M9 11h6M9 15h4",
    reports: "M5 3h14v18H5zM8 16v-3M12 16V9M16 16v-5",
    settings: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM4 12h2m12 0h2M12 4v2m0 12v2M6.3 6.3l1.4 1.4m8.6 8.6 1.4 1.4m0-11.4-1.4 1.4m-8.6 8.6-1.4 1.4",
  };
  return <svg className="nav-icon" viewBox="0 0 24 24" aria-hidden="true"><path d={paths[name]} /></svg>;
}

function FooterIcon({ kind }: { kind: "help" | "about" }) {
  return <svg className="footer-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" />{kind === "help" ? <path d="M9.7 9a2.4 2.4 0 1 1 3.9 1.9c-1 .7-1.6 1.1-1.6 2.4M12 16.6v.1" /> : <path d="M12 10v6M12 7.3v.1" />}</svg>;
}

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(() => window.localStorage.getItem("tempverity-sidebar-collapsed") === "true");
  const { data: metadata } = useQuery({ queryKey: ["metadata"], queryFn: () => fetchJson<AppMetadata>("/api/metadata") });
  const { data: auth } = useQuery({ queryKey: ["auth-status"], queryFn: () => fetchJson<AuthStatus>("/api/auth/status") });
  const supportEmail = metadata?.support_email ?? "placeholder@placeholder.com";
  const visibleItems = auth?.role === "viewer" ? items.filter((item) => !["/devices", "/settings"].includes(item.to)) : items;
  return (
    <aside className={`sidebar${collapsed ? " collapsed" : ""}`}>
      <div className="brand">
        <img className="sidebar-logo" src={collapsed ? "/logo_square.png?v=1" : "/tempverity-logo-v3.png"} alt="TempVerity" />
        <button className="sidebar-toggle" type="button" aria-label={collapsed ? "Expand navigation" : "Collapse navigation"} title={collapsed ? "Expand navigation" : "Collapse navigation"} onClick={() => { const next = !collapsed; setCollapsed(next); window.localStorage.setItem("tempverity-sidebar-collapsed", String(next)); }}>
          <span aria-hidden="true">{collapsed ? "›" : "‹"}</span>
        </button>
      </div>

      <nav className="nav">
        {visibleItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            title={item.label}
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          >
            <SidebarIcon name={item.icon} /><span className="nav-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <a className="sidebar-footer-link support-link" href={`mailto:${supportEmail}`}><FooterIcon kind="help" /><span>Help &amp; Support</span></a>
        <Link className="sidebar-footer-link about-link" to="/about"><FooterIcon kind="about" /><span>About</span></Link>
        <span className="sidebar-version">v{metadata?.version ?? "1.0.0"}</span>
      </div>
    </aside>
  );
}
