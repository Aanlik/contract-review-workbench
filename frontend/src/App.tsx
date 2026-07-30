import { useEffect, useState } from "react";

import { deleteCase, exportCase, listCases, updateCase } from "./api/client";
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
  const [selectedCaseId, setSelectedCaseId] = useState<number | undefined>(
    loadWorkspaceState().selectedCaseId,
  );

  function refreshCases() {
    listCases().then(setCases).catch(() => setCases([]));
  }

  useEffect(() => {
    refreshCases();
  }, []);

  function openCase(caseId: number) {
    const state = loadWorkspaceState();
    saveWorkspaceState({ ...state, selectedCaseId: caseId });
    setSelectedCaseId(caseId);
    setActivePage("workspace");
  }

  function handleCreated(caseId: number) {
    refreshCases();
    openCase(caseId);
  }

  async function handleDelete(caseId: number) {
    if (!window.confirm("确认删除这条审核记录吗？本操作会从列表隐藏该记录，原始材料清理将在后续版本提供独立选项。")) return;
    await deleteCase(caseId);
    refreshCases();
  }

  async function handleRename(item: ReviewCase) {
    const title = window.prompt("请输入新的合同名称", item.title);
    if (title === null) return;
    const note = window.prompt("请输入备注", item.note ?? "");
    if (note === null) return;
    await updateCase(item.id, { title, note });
    refreshCases();
  }

  async function handleExport(caseId: number) {
    const result = await exportCase(caseId);
    window.alert(`报告已导出：${result.filePath}`);
  }

  return (
    <AppShell activePage={activePage} onNavigate={setActivePage}>
      {activePage === "cases" && (
        <CasesPage
          cases={cases}
          onDelete={handleDelete}
          onExport={handleExport}
          onOpen={openCase}
          onRename={handleRename}
        />
      )}
      {activePage === "new" && <NewCasePage onCreated={handleCreated} />}
      {activePage === "settings" && <SettingsPage />}
      {activePage === "workspace" && selectedCaseId && (
        <ReviewWorkspacePage caseId={selectedCaseId} onCaseChanged={refreshCases} />
      )}
    </AppShell>
  );
}
