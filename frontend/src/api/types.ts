export type ReviewCase = {
  id: number;
  title: string;
  note: string | null;
  status: string;
  currentVersion: number;
  highestRiskLevel: string | null;
  issueCount: number;
  createdAt: string;
  updatedAt: string;
};

export type ReviewVersion = {
  id: number;
  caseId: number;
  versionNumber: number;
  trigger: string;
  reviewRequest: string | null;
  note: string | null;
  createdAt: string;
};

export type UploadedFile = {
  id: number;
  caseId: number;
  fileType: string;
  fileName: string;
  parseStatus: string;
};

export type OcrBlock = {
  id: number;
  text: string;
  bbox: number[] | null;
  confidence: number | null;
  orderIndex: number;
  source: string;
};

export type DocumentPage = {
  id: number;
  pageNumber: number;
  imagePath: string | null;
  width: number | null;
  height: number | null;
  hasTextLayer: boolean;
  ocrStatus: string;
  blocks: OcrBlock[];
};

export type CaseDocument = {
  id: number;
  fileType: string;
  fileName: string;
  parseMethod: string | null;
  parseStatus: string;
  pages: DocumentPage[];
};

export type EvidenceRef = {
  id: number;
  fileId: number | null;
  pageNumber: number | null;
  ocrBlockId: number | null;
  originalText: string | null;
  bbox: number[] | null;
  note: string | null;
  confidence: number | null;
};

export type Issue = {
  id: number;
  caseId?: number;
  issueType: string;
  source: string;
  riskLevel: string;
  title: string;
  description?: string;
  suggestion?: string | null;
  replacementClause?: string | null;
  status: string;
  evidenceRefs?: EvidenceRef[];
};

export type ManualIssuePayload = {
  title: string;
  riskLevel: "high" | "medium" | "low" | "info";
  description: string;
  suggestion?: string;
  evidenceText?: string;
};

export type IssueUpdatePayload = Partial<{
  title: string;
  riskLevel: "high" | "medium" | "low" | "info";
  description: string;
  suggestion: string;
  replacementClause: string;
  status: "pending" | "confirmed" | "modified" | "rejected" | "needs_review";
}>;

export type AiMessage = {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  model: string | null;
  isApplied: boolean;
  createdAt: string;
};

export type AiConversation = {
  id: number;
  caseId: number;
  issueId: number | null;
  scope: string;
  messages: AiMessage[];
};

export type AiSettings = {
  baseUrl: string;
  apiKey: string;
  model: string;
  temperature: number;
  timeoutSeconds: number;
};

export type AiConnectionTestResult = {
  ok: boolean;
  model: string;
  message: string;
  latencyMs: number;
};

export type SystemSettings = {
  ocrEngine: "paddleocr" | "rapidocr";
  storageRoot: string;
  ocrDpi: number;
  preprocessImages: boolean;
};

export type VersionDiffItem = {
  issueId: number;
  title: string;
  changeType: "added" | "removed" | "modified";
  riskLevel: string;
  description: string;
  oldRiskLevel: string | null;
};

export type VersionDiffResponse = {
  versionA: number;
  versionB: number;
  changes: VersionDiffItem[];
  summary: string;
};

export type TaskStatus = {
  taskId: string;
  status: "queued" | "running" | "completed" | "failed";
  result: unknown;
  error: string | null;
  progress: string;
  progressPercent: number;
  currentStep: number;
  totalSteps: number;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
};

export type CaseSearchParams = {
  q?: string;
  status?: string;
  riskLevel?: string;
  sortBy?: string;
  sortOrder?: string;
};
