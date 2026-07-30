import type { Issue, ManualIssuePayload, ReviewCase } from "./types";

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
    evidenceRefs: item.evidence_refs ?? [],
  };
}

export async function listCases(): Promise<ReviewCase[]> {
  const response = await fetch(`${API_BASE}/cases`);
  const data = await response.json();
  return data.map(fromSnakeCaseCase);
}

export async function createCase(payload: { title: string; note?: string }): Promise<ReviewCase> {
  const response = await fetch(`${API_BASE}/cases`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return fromSnakeCaseCase(await response.json());
}

export async function listIssues(caseId: number): Promise<Issue[]> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/issues`);
  const data = await response.json();
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
  return fromSnakeCaseIssue(await response.json());
}
