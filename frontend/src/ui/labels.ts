export const riskLabels: Record<string, string> = {
  high: "高风险",
  medium: "中风险",
  low: "低风险",
  info: "提示",
};

export const statusLabels: Record<string, string> = {
  pending: "待处理",
  confirmed: "已确认",
  modified: "已修改",
  rejected: "不采纳",
  needs_review: "待复核",
  created: "已创建",
  analyzing: "分析中",
  completed: "已完成",
  queued: "排队中",
  running: "进行中",
  failed: "失败",
};

export const sourceLabels: Record<string, string> = {
  ai: "人工智能审查",
  manual: "人工标记",
  system: "系统规则",
};

export const issueTypeLabels: Record<string, string> = {
  contract_risk: "合同风险",
  process_audit: "流程审计",
  manual_mark: "人工标记",
};

export const parseStatusLabels: Record<string, string> = {
  uploaded: "已上传",
  processing: "解析中",
  parsed: "已解析",
  empty: "无识别内容",
  needs_ocr: "待扫描识别",
  ocr_failed: "扫描识别失败",
};

export const parseSourceLabels: Record<string, string> = {
  pdf_text: "文档文本",
  ocr: "扫描识别",
};

export const caseStatusLabels: Record<string, string> = {
  created: "已创建",
  analyzing: "分析中",
  completed: "已完成",
};

export const changeTypeLabels: Record<string, string> = {
  added: "新增",
  removed: "移除",
  modified: "变更",
};

export const materialTypeLabels: Record<string, string> = {
  contract: "合同扫描件",
  legal_review_report: "法审签报",
  contract_approval: "合同签批文件",
  matter_report: "事项签报 / 会议纪要",
  sign_report: "历史签报",
  meeting_minutes: "历史会议纪要",
  approval: "历史审批材料",
};

export function labelOf(labels: Record<string, string>, value: string | null | undefined, fallback = "其他"): string {
  return (value && labels[value]) || fallback;
}

export function localizeUiText(value: string): string {
  return value
    .replace(/\bAI Base URL\b/g, "智能审查接口地址")
    .replace(/\bAPI Key\b/g, "接口密钥")
    .replace(/\bAI 合同法律风险审查\b/g, "智能合同法律风险审查")
    .replace(/\bAI 接口\b/g, "智能审查接口")
    .replace(/\bAI 审查\b/g, "智能审查")
    .replace(/\bAI\b/g, "智能审查")
    .replace(/\bOCR\b/g, "扫描识别");
}
