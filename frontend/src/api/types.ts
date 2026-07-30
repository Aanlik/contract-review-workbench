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
