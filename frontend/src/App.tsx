import { useEffect, useState } from "react";

import { deleteCase, downloadExport, exportCase, listCases, updateCase } from "./api/client";
import type { CaseSearchParams, ReviewCase } from "./api/types";
import { AppShell } from "./components/AppShell";
import { ConfirmDialog, ExportDialog, RenameDialog } from "./components/Modal";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { AuditLogPage } from "./pages/AuditLogPage";
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
  const [searchParams, setSearchParams] = useState<CaseSearchParams>({});

  // Modal state
  const [deleteTarget, setDeleteTarget] = useState<ReviewCase | null>(null);
  const [renameTarget, setRenameTarget] = useState<ReviewCase | null>(null);
  const [exportTarget, setExportTarget] = useState<number | null>(null);

  function refreshCases(params?: CaseSearchParams) {
    listCases(params ?? searchParams).then(setCases).catch(() => setCases([]));
  }

  useEffect(() => { refreshCases(); }, []);

  function handleSearch(params: CaseSearchParams) {
    setSearchParams(params);
    refreshCases(params);
  }

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

  async function handleDeleteConfirmed(deleteFiles: boolean) {
    if (!deleteTarget) return;
    await deleteCase(deleteTarget.id, deleteFiles);
    setDeleteTarget(null);
    refreshCases();
  }

  async function handleRenameSubmit(title: string, note: string) {
    if (!renameTarget) return;
    await updateCase(renameTarget.id, { title, note });
    setRenameTarget(null);
    refreshCases();
  }

  async function handleExportSubmit(scope: string, format: string) {
    if (exportTarget === null) return;
    const result = await exportCase(exportTarget, scope as any, format as any);
    await downloadExport(result.filePath);
    setExportTarget(null);
  }

  return (
    <ErrorBoundary>
    <AppShell activePage={activePage} onNavigate={setActivePage}>
      {activePage === "cases" && (
        <CasesPage
          cases={cases}
          onDelete={(id) => setDeleteTarget(cases.find((c) => c.id === id) ?? null)}
          onExport={(id) => setExportTarget(id)}
          onOpen={openCase}
          onRename={(item) => setRenameTarget(item)}
          onSearch={handleSearch}
        />
      )}
      {activePage === "new" && <NewCasePage onCreated={handleCreated} />}
      {activePage === "settings" && <SettingsPage />}
      {activePage === "audit" && <AuditLogPage />}
      {activePage === "workspace" && selectedCaseId && (
        <ReviewWorkspacePage caseId={selectedCaseId} onCaseChanged={() => refreshCases()} />
      )}

      {/* Modals */}
      <ConfirmDialog
        danger
        message="确认删除这条审核记录吗？此操作不可撤销。"
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => handleDeleteConfirmed(false)}
        open={!!deleteTarget}
        title="删除审核记录"
        confirmLabel="删除"
      />

      <RenameDialog
        defaultNote={deleteTarget?.note ?? renameTarget?.note ?? ""}
        defaultTitle={renameTarget?.title ?? ""}
        onClose={() => setRenameTarget(null)}
        onSubmit={handleRenameSubmit}
        open={!!renameTarget}
      />

      <ExportDialog
        onClose={() => setExportTarget(null)}
        onExport={handleExportSubmit}
        open={exportTarget !== null}
      />
    </AppShell>
    </ErrorBoundary>
  );
}
