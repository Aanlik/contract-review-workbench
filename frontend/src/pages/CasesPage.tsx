import { useState } from "react";

import type { CaseSearchParams, ReviewCase } from "../api/types";
import { caseStatusLabels, labelOf, riskLabels } from "../ui/labels";

type CasesPageProps = {
  cases: ReviewCase[];
  onOpen: (caseId: number) => void;
  onRename: (item: ReviewCase) => void;
  onDelete: (caseId: number) => void;
  onExport: (caseId: number) => void;
  onSearch: (params: CaseSearchParams) => void;
};

const riskColors: Record<string, string> = {
  high: "#dc3545",
  medium: "#ff9800",
  low: "#2196f3",
  info: "#6c757d",
};

export function CasesPage({ cases, onDelete, onExport, onOpen, onRename, onSearch }: CasesPageProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [sortBy, setSortBy] = useState("updated_at");
  const [sortOrder, setSortOrder] = useState("desc");

  function applySearch() {
    onSearch({
      q: searchQuery || undefined,
      status: statusFilter || undefined,
      riskLevel: riskFilter || undefined,
      sortBy,
      sortOrder,
    });
  }

  function handleKeyDown(event: React.KeyboardEvent) {
    if (event.key === "Enter") applySearch();
  }

  return (
    <section className="records-page">
      <header className="page-header">
        <div>
          <p className="section-kicker">审核工作台</p>
          <h1>审核记录</h1>
        </div>
        <span className="page-note">{cases.length} 条记录</span>
      </header>

      <div className="search-bar">
        <input
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="搜索合同名称或备注..."
          type="text"
          value={searchQuery}
        />
        <select onChange={(e) => setStatusFilter(e.target.value)} value={statusFilter}>
          <option value="">全部状态</option>
          <option value="created">已创建</option>
          <option value="completed">已完成</option>
        </select>
        <select onChange={(e) => setRiskFilter(e.target.value)} value={riskFilter}>
          <option value="">全部风险</option>
          <option value="high">高风险</option>
          <option value="medium">中风险</option>
          <option value="low">低风险</option>
          <option value="info">提示</option>
        </select>
        <select onChange={(e) => setSortBy(e.target.value)} value={sortBy}>
          <option value="updated_at">按更新时间</option>
          <option value="created_at">按创建时间</option>
          <option value="title">按名称</option>
          <option value="issue_count">按问题数</option>
        </select>
        <button
          className={sortOrder === "desc" ? "sort-btn active" : "sort-btn"}
          onClick={() => {
            setSortOrder(sortOrder === "desc" ? "asc" : "desc");
          }}
          title={sortOrder === "desc" ? "降序" : "升序"}
          type="button"
        >
          {sortOrder === "desc" ? "↓" : "↑"}
        </button>
        <button onClick={applySearch} type="button">
          搜索
        </button>
      </div>

      <div className="table">
        {cases.map((item) => (
          <div className="table-row" key={item.id}>
            <div className="case-info">
              <strong>{item.title}</strong>
              {item.note && <p className="case-note">{item.note}</p>}
            </div>
            <span className="case-status">{labelOf(caseStatusLabels, item.status)}</span>
            <span className="case-issues">{item.issueCount} 个问题</span>
            <span
              className="case-risk"
              style={{ color: riskColors[item.highestRiskLevel ?? ""] ?? "#888" }}
            >
              {item.highestRiskLevel ? labelOf(riskLabels, item.highestRiskLevel) : "未评级"}
            </span>
            <div className="row-actions">
              <button onClick={() => onOpen(item.id)} type="button">打开</button>
              <button onClick={() => onRename(item)} type="button">重命名</button>
              <button onClick={() => onExport(item.id)} type="button">导出</button>
              <button className="danger" onClick={() => onDelete(item.id)} type="button">删除</button>
            </div>
          </div>
        ))}
        {!cases.length && <p className="empty-state">还没有审核记录，请先新建一次合同审查。</p>}
      </div>
    </section>
  );
}
