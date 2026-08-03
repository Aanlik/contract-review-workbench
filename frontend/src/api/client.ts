import type {
  AiConversation,
  AiConnectionTestResult,
  AiSettings,
  CaseDocument,
  CaseSearchParams,
  EvidenceRef,
  Issue,
  IssueUpdatePayload,
  ManualIssuePayload,
  OcrInstallResponse,
  OcrInstallTarget,
  OcrRetryResponse,
  OcrRuntimeStatus,
  ReviewCase,
  ReviewVersion,
  SystemSettings,
  TaskStatus,
  UploadedFile,
  VersionDiffResponse,
} from "./types";

const API_BASE = "/api";

function fromSnakeCaseCase(item: any): ReviewCase {
  return {
    id: item.id,
    title: item.title,
    note: item.note,
    status: item.status,
    currentVersion: item.current_version,
    highestRiskLevel: item.highest_risk_level,
    issueCount: item.issue_count,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  };
}

function fromSnakeCaseIssue(item: any): Issue {
  return {
    id: item.id,
    caseId: item.case_id,
    issueType: item.issue_type,
    source: item.source,
    riskLevel: item.risk_level,
    title: item.title,
    description: item.description,
    suggestion: item.suggestion,
    replacementClause: item.replacement_clause,
    status: item.status,
    evidenceRefs: (item.evidence_refs ?? []).map(fromSnakeCaseEvidence),
  };
}

function fromSnakeCaseEvidence(item: any): EvidenceRef {
  return {
    id: item.id,
    fileId: item.file_id,
    pageNumber: item.page_number,
    ocrBlockId: item.ocr_block_id,
    originalText: item.original_text,
    bbox: item.bbox,
    note: item.note,
    confidence: item.confidence,
  };
}

function fromSnakeCaseFile(item: any): UploadedFile {
  return {
    id: item.id,
    caseId: item.case_id,
    fileType: item.file_type,
    fileName: item.file_name,
    parseStatus: item.parse_status,
  };
}

function fromSnakeCaseConversation(item: any): AiConversation {
  return {
    id: item.id,
    caseId: item.case_id,
    issueId: item.issue_id,
    scope: item.scope,
    messages: (item.messages ?? []).map((message: any) => ({
      id: message.id,
      role: message.role,
      content: message.content,
      model: message.model,
      isApplied: message.is_applied,
      createdAt: message.created_at,
    })),
  };
}

function fromSnakeCaseDocument(item: any): CaseDocument {
  return {
    id: item.id,
    fileType: item.file_type,
    fileName: item.file_name,
    parseMethod: item.parse_method,
    parseStatus: item.parse_status,
    pages: (item.pages ?? []).map((page: any) => ({
      id: page.id,
      pageNumber: page.page_number,
      imagePath: page.image_path,
      width: page.width,
      height: page.height,
      hasTextLayer: page.has_text_layer,
      ocrStatus: page.ocr_status,
      blocks: (page.blocks ?? []).map((block: any) => ({
        id: block.id,
        text: block.text,
        bbox: block.bbox,
        confidence: block.confidence,
        orderIndex: block.order_index,
        source: block.source,
      })),
    })),
  };
}

async function parseJsonResponse(response: Response) {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json();
}

// Cases
export async function listCases(params?: CaseSearchParams): Promise<ReviewCase[]> {
  const searchParams = new URLSearchParams();
  if (params?.q) searchParams.set("q", params.q);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.riskLevel) searchParams.set("risk_level", params.riskLevel);
  if (params?.sortBy) searchParams.set("sort_by", params.sortBy);
  if (params?.sortOrder) searchParams.set("sort_order", params.sortOrder);
  const qs = searchParams.toString();
  const response = await fetch(`${API_BASE}/cases${qs ? `?${qs}` : ""}`);
  const data = await parseJsonResponse(response);
  return data.map(fromSnakeCaseCase);
}

export async function createCase(payload: { title: string; note?: string }): Promise<ReviewCase> {
  const response = await fetch(`${API_BASE}/cases`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return fromSnakeCaseCase(await parseJsonResponse(response));
}

export async function updateCase(
  caseId: number,
  payload: { title?: string; note?: string },
): Promise<ReviewCase> {
  const response = await fetch(`${API_BASE}/cases/${caseId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return fromSnakeCaseCase(await parseJsonResponse(response));
}

export async function deleteCase(caseId: number, deleteFiles = false): Promise<void> {
  const response = await fetch(`${API_BASE}/cases/${caseId}?delete_files=${deleteFiles}`, { method: "DELETE" });
  if (!response.ok) throw new Error(`Delete failed: ${response.status}`);
}

// Files
export type UploadProgressCallback = (percent: number) => void;

function xhrErrorMessage(xhr: XMLHttpRequest, fallback: string): string {
  try {
    const payload = JSON.parse(xhr.responseText);
    if (typeof payload?.detail === "string") {
      return `${fallback}: ${payload.detail}`;
    }
  } catch {
    // Keep the original status-only message when the server did not return JSON.
  }
  return fallback;
}

export function uploadCaseFile(
  caseId: number,
  fileType: string,
  file: File,
  onProgress?: UploadProgressCallback,
): Promise<UploadedFile> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file_type", fileType);
    formData.append("file", file);

    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          resolve(fromSnakeCaseFile(data));
        } catch {
          reject(new Error("Invalid response"));
        }
      } else {
        reject(new Error(xhrErrorMessage(xhr, `Upload failed: ${xhr.status}`)));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Network error")));
    xhr.addEventListener("abort", () => reject(new Error("Upload aborted")));

    xhr.open("POST", `${API_BASE}/cases/${caseId}/files`);
    xhr.send(formData);
  });
}

export async function listCaseFiles(caseId: number): Promise<UploadedFile[]> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/files`);
  const data = await parseJsonResponse(response);
  return data.map(fromSnakeCaseFile);
}

export async function listCaseDocuments(caseId: number): Promise<CaseDocument[]> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/documents`);
  const data = await parseJsonResponse(response);
  return data.map(fromSnakeCaseDocument);
}

export function documentPageImageUrl(caseId: number, fileId: number, pageNumber: number): string {
  return `${API_BASE}/cases/${caseId}/documents/${fileId}/pages/${pageNumber}/image`;
}

export async function retryOcr(caseId: number, fileId: number): Promise<OcrRetryResponse> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/files/${fileId}/retry-ocr`, { method: "POST" });
  const data = await parseJsonResponse(response);
  return { taskId: data.task_id, fileId: data.file_id };
}

// Issues
export async function listIssues(caseId: number): Promise<Issue[]> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/issues`);
  const data = await parseJsonResponse(response);
  return data.map(fromSnakeCaseIssue);
}

export async function createManualIssue(caseId: number, payload: ManualIssuePayload): Promise<Issue> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/issues/manual`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: payload.title,
      risk_level: payload.riskLevel,
      description: payload.description,
      suggestion: payload.suggestion,
      evidence_text: payload.evidenceText,
    }),
  });
  return fromSnakeCaseIssue(await parseJsonResponse(response));
}

export async function updateIssue(issueId: number, payload: IssueUpdatePayload): Promise<Issue> {
  const body: Record<string, unknown> = {};
  if (payload.title !== undefined) body.title = payload.title;
  if (payload.riskLevel !== undefined) body.risk_level = payload.riskLevel;
  if (payload.description !== undefined) body.description = payload.description;
  if (payload.suggestion !== undefined) body.suggestion = payload.suggestion;
  if (payload.replacementClause !== undefined) body.replacement_clause = payload.replacementClause;
  if (payload.status !== undefined) body.status = payload.status;
  const response = await fetch(`${API_BASE}/issues/${issueId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return fromSnakeCaseIssue(await parseJsonResponse(response));
}

export async function applyAiMessageToIssue(
  issueId: number,
  messageId: number,
  action: string,
): Promise<Issue> {
  const response = await fetch(`${API_BASE}/issues/${issueId}/apply-ai-message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_id: messageId, action }),
  });
  return fromSnakeCaseIssue(await parseJsonResponse(response));
}

export async function applyAiMessageAsNewIssue(messageId: number): Promise<Issue> {
  const response = await fetch(`${API_BASE}/ai-messages/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_id: messageId, action: "new_issue" }),
  });
  return fromSnakeCaseIssue(await parseJsonResponse(response));
}

export async function batchUpdateIssues(
  issueIds: number[],
  updates: { status?: string; riskLevel?: string },
): Promise<Issue[]> {
  const response = await fetch(`${API_BASE}/issues/batch-update`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      issue_ids: issueIds,
      status: updates.status,
      risk_level: updates.riskLevel,
    }),
  });
  const data = await parseJsonResponse(response);
  return data.map(fromSnakeCaseIssue);
}

export async function batchDeleteIssues(issueIds: number[]): Promise<void> {
  const response = await fetch(`${API_BASE}/issues/batch-delete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ issue_ids: issueIds }),
  });
  if (!response.ok) throw new Error(`Batch delete failed: ${response.status}`);
}

// Review runs
export async function reanalyzeCase(caseId: number, instruction?: string): Promise<ReviewCase> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/reanalyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ instruction }),
  });
  return fromSnakeCaseCase(await parseJsonResponse(response));
}

export async function reanalyzeAsync(caseId: number, instruction?: string): Promise<{ taskId: string; caseId: number }> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/reanalyze-async`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ instruction }),
  });
  const data = await parseJsonResponse(response);
  return { taskId: data.task_id, caseId: data.case_id };
}

export async function listCaseVersions(caseId: number): Promise<ReviewVersion[]> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/versions`);
  const data = await parseJsonResponse(response);
  return data.map((item: any) => ({
    id: item.id,
    caseId: item.case_id,
    versionNumber: item.version_number,
    trigger: item.trigger,
    reviewRequest: item.review_request,
    note: item.note,
    createdAt: item.created_at,
  }));
}

export async function diffVersions(caseId: number, versionA: number, versionB: number): Promise<VersionDiffResponse> {
  const response = await fetch(
    `${API_BASE}/cases/${caseId}/versions/diff?version_a=${versionA}&version_b=${versionB}`,
  );
  const data = await parseJsonResponse(response);
  return {
    versionA: data.version_a,
    versionB: data.version_b,
    changes: (data.changes ?? []).map((c: any) => ({
      issueId: c.issue_id,
      title: c.title,
      changeType: c.change_type,
      riskLevel: c.risk_level,
      description: c.description,
      oldRiskLevel: c.old_risk_level,
    })),
    summary: data.summary,
  };
}

// AI Chat
export async function getCaseChat(caseId: number): Promise<AiConversation> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/chat`);
  return fromSnakeCaseConversation(await parseJsonResponse(response));
}

export async function getIssueChat(caseId: number, issueId: number): Promise<AiConversation> {
  const response = await fetch(`${API_BASE}/issues/${issueId}/chat?case_id=${caseId}`);
  return fromSnakeCaseConversation(await parseJsonResponse(response));
}

export async function sendCaseChat(caseId: number, message: string): Promise<AiConversation> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  return fromSnakeCaseConversation(await parseJsonResponse(response));
}

export async function sendIssueChat(
  caseId: number,
  issueId: number,
  message: string,
): Promise<AiConversation> {
  const response = await fetch(`${API_BASE}/issues/${issueId}/chat?case_id=${caseId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  return fromSnakeCaseConversation(await parseJsonResponse(response));
}

// Exports
export async function exportCase(
  caseId: number,
  scope: "final" | "all" | "high_and_medium" | "confirmed" = "final",
  format: "markdown" | "docx" | "pdf" = "markdown",
): Promise<{ filePath: string; fileName: string }> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/exports`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ format, scope, include_ai_summary: false }),
  });
  const data = await parseJsonResponse(response);
  return { filePath: data.file_path, fileName: data.file_name };
}

// Settings
export async function getAiSettings(): Promise<AiSettings | null> {
  const response = await fetch(`${API_BASE}/settings/ai`);
  const data = await parseJsonResponse(response);
  if (!data) return null;
  return {
    baseUrl: data.base_url,
    apiKey: data.api_key,
    model: data.model,
    temperature: data.temperature,
    timeoutSeconds: data.timeout_seconds,
  };
}

export async function saveAiSettings(payload: AiSettings): Promise<AiSettings> {
  const response = await fetch(`${API_BASE}/settings/ai`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      base_url: payload.baseUrl,
      api_key: payload.apiKey,
      model: payload.model,
      temperature: payload.temperature,
      timeout_seconds: payload.timeoutSeconds,
    }),
  });
  const data = await parseJsonResponse(response);
  return {
    baseUrl: data.base_url,
    apiKey: data.api_key,
    model: data.model,
    temperature: data.temperature,
    timeoutSeconds: data.timeout_seconds,
  };
}

export async function testAiSettings(payload: AiSettings): Promise<AiConnectionTestResult> {
  const response = await fetch(`${API_BASE}/settings/ai/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      base_url: payload.baseUrl,
      api_key: payload.apiKey,
      model: payload.model,
      temperature: payload.temperature,
      timeout_seconds: payload.timeoutSeconds,
    }),
  });
  const data = await parseJsonResponse(response);
  return {
    ok: data.ok,
    model: data.model,
    message: data.message,
    latencyMs: data.latency_ms,
  };
}

export async function getSystemSettings(): Promise<SystemSettings> {
  const response = await fetch(`${API_BASE}/settings/system`);
  const data = await parseJsonResponse(response);
  return {
    ocrEngine: data.ocr_engine,
    storageRoot: data.storage_root,
    ocrDpi: data.ocr_dpi,
    preprocessImages: data.preprocess_images,
  };
}

export async function saveSystemSettings(payload: SystemSettings): Promise<SystemSettings> {
  const response = await fetch(`${API_BASE}/settings/system`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ocr_engine: payload.ocrEngine,
      storage_root: payload.storageRoot,
      ocr_dpi: payload.ocrDpi,
      preprocess_images: payload.preprocessImages,
    }),
  });
  const data = await parseJsonResponse(response);
  return {
    ocrEngine: data.ocr_engine,
    storageRoot: data.storage_root,
    ocrDpi: data.ocr_dpi,
    preprocessImages: data.preprocess_images,
  };
}

export async function getOcrRuntimeStatus(): Promise<OcrRuntimeStatus> {
  const response = await fetch(`${API_BASE}/settings/ocr/status`);
  const data = await parseJsonResponse(response);
  const engines: OcrRuntimeStatus["engines"] = {};
  for (const [key, value] of Object.entries(data.engines ?? {})) {
    const item = value as any;
    engines[key] = {
      installed: item.installed,
      package: item.package,
      importName: item.import_name,
      note: item.note,
    };
  }
  return {
    currentEngine: data.current_engine,
    currentEngineInstalled: data.current_engine_installed,
    installSupported: data.install_supported,
    installSupportedReason: data.install_supported_reason,
    engines,
  };
}

export async function installOcrDependencies(target: OcrInstallTarget): Promise<OcrInstallResponse> {
  const response = await fetch(`${API_BASE}/settings/ocr/install`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target }),
  });
  const data = await parseJsonResponse(response);
  return {
    taskId: data.task_id,
    target: data.target,
    message: data.message,
  };
}

// Tasks
export async function listTasks(): Promise<TaskStatus[]> {
  const response = await fetch(`${API_BASE}/tasks`);
  const data = await parseJsonResponse(response);
  return data.map((t: any) => ({
    taskId: t.task_id,
    status: t.status,
    result: t.result,
    error: t.error,
    progress: t.progress,
    progressPercent: t.progress_percent ?? 0,
    currentStep: t.current_step ?? 0,
    totalSteps: t.total_steps ?? 0,
    createdAt: t.created_at,
    startedAt: t.started_at,
    finishedAt: t.finished_at,
  }));
}

export async function getTask(taskId: string): Promise<TaskStatus> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}`);
  const data = await parseJsonResponse(response);
  return {
    taskId: data.task_id,
    status: data.status,
    result: data.result,
    error: data.error,
    progress: data.progress,
    progressPercent: data.progress_percent ?? 0,
    currentStep: data.current_step ?? 0,
    totalSteps: data.total_steps ?? 0,
    createdAt: data.created_at,
    startedAt: data.started_at,
    finishedAt: data.finished_at,
  };
}


export async function downloadExport(filePath: string): Promise<void> {
  const response = await fetch(`${API_BASE}/exports/download?file_path=${encodeURIComponent(filePath)}`);
  if (!response.ok) throw new Error(`Download failed: ${response.status}`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filePath.split("/").pop() || "export";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
// Audit Logs
export async function getAuditLogs(params?: {
  entityType?: string;
  entityId?: number;
  limit?: number;
}): Promise<any[]> {
  const searchParams = new URLSearchParams();
  if (params?.entityType) searchParams.set("entity_type", params.entityType);
  if (params?.entityId) searchParams.set("entity_id", String(params.entityId));
  if (params?.limit) searchParams.set("limit", String(params.limit));
  const qs = searchParams.toString();
  const response = await fetch(`${API_BASE}/audit/logs${qs ? `?${qs}` : ""}`);
  return parseJsonResponse(response);
}
