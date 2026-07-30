import type { ReactNode } from "react";

type AppShellProps = {
  activePage: string;
  onNavigate: (page: string) => void;
  children: ReactNode;
};

export function AppShell({ activePage, onNavigate, children }: AppShellProps) {
  const items = [
    ["cases", "审核记录"],
    ["new", "新建审核"],
    ["settings", "设置"],
  ];
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">合同 AI 审查</div>
        {items.map(([key, label]) => (
          <button
            className={activePage === key ? "nav-item active" : "nav-item"}
            key={key}
            onClick={() => onNavigate(key)}
            type="button"
          >
            {label}
          </button>
        ))}
      </aside>
      <main className="main-panel">{children}</main>
    </div>
  );
}
