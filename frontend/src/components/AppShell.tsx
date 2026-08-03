import { useEffect, useState, type ReactNode } from "react";

import { loadWorkspaceState, saveWorkspaceState } from "../state/workspace";

type AppShellProps = {
  activePage: string;
  onNavigate: (page: string) => void;
  children: ReactNode;
};

const items = [
  ["cases", "审核记录", "📋"],
  ["new", "新建审核", "➕"],
  ["settings", "设置", "⚙"],
  ["audit", "审计日志", "📑"],
];

export function AppShell({ activePage, onNavigate, children }: AppShellProps) {
  const [collapsed, setCollapsed] = useState(() => loadWorkspaceState().sidebarCollapsed ?? false);
  const [theme, setTheme] = useState<string>(() => loadWorkspaceState().theme ?? "light");

  useEffect(() => {
    const state = loadWorkspaceState();
    saveWorkspaceState({ ...state, sidebarCollapsed: collapsed });
  }, [collapsed]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    const state = loadWorkspaceState();
    saveWorkspaceState({ ...state, theme });
  }, [theme]);

  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      <aside className="sidebar">
        <div className="sidebar-head">
          {!collapsed && <div className="brand">合同智能审查</div>}
          <div style={{ display: "flex", gap: 4 }}>
            <button
              className="theme-toggle"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              title={theme === "dark" ? "切换亮色" : "切换暗色"}
              type="button"
            >
              {theme === "dark" ? "☀" : "🌙"}
            </button>
            <button
              className="sidebar-toggle"
              onClick={() => setCollapsed(!collapsed)}
              title={collapsed ? "展开侧栏" : "折叠侧栏"}
              type="button"
            >
              {collapsed ? "▶" : "◀"}
            </button>
          </div>
        </div>
        {items.map(([key, label, icon]) => (
          <button
            className={activePage === key ? "nav-item active" : "nav-item"}
            key={key}
            onClick={() => onNavigate(key)}
            title={collapsed ? label : undefined}
            type="button"
          >
            <span className="nav-icon">{icon}</span>
            {!collapsed && <span className="nav-label">{label}</span>}
          </button>
        ))}
      </aside>
      <main className="main-panel">{children}</main>
    </div>
  );
}
