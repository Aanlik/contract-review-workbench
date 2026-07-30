import type {
  AiConversation,
  AiSettings,
  EvidenceRef,
  Issue,
  IssueUpdatePayload,
  ManualIssuePayload,
  ReviewCase,
  UploadedFile,
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

async function parseJsonResponse(response: Response) {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json();
}

export async function listCases(): Promise<ReviewCase[]> {
  const response = await fetch(`${API_BASE}/cases`);
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

export async function deleteCase(caseId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/cases/${caseId}`, { method: "DELETE" });
  if (!response.ok) throw new Error(`Delete failed: ${response.status}`);
}

export async function uploadCaseFile(
  caseId: number,
  fileType: string,
  file: File,
): Promise<UploadedFile> {
  const data = new FormData();
  data.append("file_type", fileType);
  data.append("file", file);
  const response = await fetch(`${API_BASE}/cases/${caseId}/files`, {
    method: "POST",
    body: data,
  });
  return fromSnakeCaseFile(await parseJsonResponse(response));
}

export async function listIssues(caseId: number): Promise<Issue[]> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/issues`);
  const data = await parseJsonResponse(response);
  return data.map(fromSnakeCaseIssue);
}

export async function createManualIssue(
  caseId: number,
  payload: ManualIssuePayload,
): Promise<Issue> {
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
  const response = await fetch(`${API_BASE}/issues/${issueId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: payload.title,
      risk_level: payload.riskLevel,
      description: payload.description,
      suggestion: payload.suggestion,
      replacement_clause: payload.replacementClause,
      status: payload.status,
    }),
  });
  return fromSnakeCaseIssue(await parseJsonResponse(response));
}

export async function reanalyzeCase(caseId: number, instruction?: string): Promise<ReviewCase> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/reanalyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ instruction }),
  });
  return fromSnakeCaseCase(await parseJsonResponse(response));
}

export async function getCaseChat(caseId: number): Promise<AiConversation> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/chat`);
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

export async function exportCase(caseId: number): Promise<{ filePath: string }> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/exports`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ format: "markdown", scope: "final", include_ai_summary: false }),
  });
  const data = await parseJsonResponse(response);
  return { filePath: data.file_path };
}

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
