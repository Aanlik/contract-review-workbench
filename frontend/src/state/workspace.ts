export type WorkspaceState = {
  selectedCaseId?: number;
  selectedIssueId?: number;
  filters: Record<string, string>;
  sidebarCollapsed?: boolean;
  theme?: string;
  aiTestResult?: {
    ok: boolean;
    model: string;
    message: string;
    latencyMs: number;
    testedAt: string;
  };
  newCaseDraft?: {
    title: string;
    note: string;
    caseId?: number;
    activeStep: number;
    uploadProgress: number;
    taskProgress?: {
      taskId: string;
      progress: string;
      progressPercent: number;
      currentStep: number;
      totalSteps: number;
    };
    fileNames: string[];
    startedAt: string;
  };
};

const STORAGE_KEY = "contract-review-workbench.workspace";

export function loadWorkspaceState(): WorkspaceState {
  const fallback: WorkspaceState = { filters: {} };
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return fallback;
  try {
    return { ...fallback, ...JSON.parse(raw) };
  } catch {
    return fallback;
  }
}

export function saveWorkspaceState(state: WorkspaceState): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}
