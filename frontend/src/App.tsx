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
    if (!window.confirm("确认删除这条审核记录吗？")) return;
    const deleteFiles = window.confirm("是否同时删除该记录的本地上传文件、OCR 中间结果和导出材料？");
    await deleteCase(caseId, deleteFiles);
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
    const scope = window.prompt(
      "请选择导出范围：final / all / high_and_medium / confirmed",
      "final",
    ) as "final" | "all" | "high_and_medium" | "confirmed" | null;
    if (!scope) return;
    const format = window.prompt("请选择导出格式：markdown / docx / pdf", "markdown") as
      | "markdown"
      | "docx"
      | "pdf"
      | null;
    if (!format) return;
    const result = await exportCase(caseId, scope, format);
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
