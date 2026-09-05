import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Activity, BookOpen, CircleAlert, FileText, LayoutDashboard, Menu, ShieldCheck, UserRound } from "lucide-react";
import { useState } from "react";

const navItems = [
  ["Overview", "/overview", LayoutDashboard], ["Reports", "/reports", FileText], ["Timeline", "/timeline", Activity], ["Conflicts", "/conflicts", CircleAlert], ["Evidence", "/evidence", BookOpen],
] as const;

export function AppShell() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const current = navItems.find(([, path]) => location.pathname.startsWith(path))?.[0] ?? "Overview";
  return <div className="shell">
    <aside className={`sidebar ${open ? "sidebar-open" : ""}`} aria-label="Primary navigation">
      <div className="brand"><span className="brand-mark"><ShieldCheck size={18} /></span><span>MEDLENS</span></div>
      <div className="side-label">Workspace</div>
      <nav>{navItems.map(([label, path, Icon]) => <NavLink key={path} to={path} onClick={() => setOpen(false)} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}><Icon size={17} strokeWidth={1.8} /><span>{label}</span></NavLink>)}</nav>
      <div className="sidebar-footer"><div className="patient-chip"><UserRound size={16} /><div><span className="eyebrow">Current patient</span><strong>Synthetic Patient 01</strong></div></div><p>Demo environment<br /><b>Synthetic data only</b></p></div>
    </aside>
    <div className="main-wrap">
      <header className="topbar"><button className="icon-button menu-button" aria-label="Open navigation" onClick={() => setOpen(!open)}><Menu size={20} /></button><div className="crumb"><span>Workspace</span><span>/</span><strong>{current}</strong></div><div className="demo-pill"><span className="pulse" /> DEMO ENVIRONMENT <b>SYNTHETIC DATA ONLY</b></div></header>
      <main><Outlet /></main>
    </div>
  </div>;
}
