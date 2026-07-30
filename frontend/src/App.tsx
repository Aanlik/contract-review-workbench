import { useEffect, useState } from "react";

import { listCases } from "./api/client";
import type { ReviewCase } from "./api/types";
import { AppShell } from "./components/AppShell";
import { CasesPage } from "./pages/CasesPage";
import { NewCasePage } from "./pages/NewCasePage";
import { ReviewWorkspacePage } from "./pages/ReviewWorkspacePage";
import { SettingsPage } from "./pages/SettingsPage";
import { loadWorkspaceState, saveWorkspaceState } from "./state/workspace";

export default function App() {
  const [activePage, setActivePage] = useState("cases");
  const [cases, setCases] = useState<ReviewCase[]>([]);

  useEffect(() => {
    listCases().then(setCases).catch(() => setCases([]));
  }, []);

  function openCase(caseId: number) {
    const state = loadWorkspaceState();
    saveWorkspaceState({ ...state, selectedCaseId: caseId });
    setActivePage("workspace");
  }

  return (
    <AppShell activePage={activePage} onNavigate={setActivePage}>
      {activePage === "cases" && <CasesPage cases={cases} onOpen={openCase} />}
      {activePage === "new" && <NewCasePage />}
      {activePage === "settings" && <SettingsPage />}
      {activePage === "workspace" && <ReviewWorkspacePage />}
    </AppShell>
  );
}
