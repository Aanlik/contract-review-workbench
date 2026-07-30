import type { ReviewCase } from "../api/types";

type CasesPageProps = {
  cases: ReviewCase[];
  onOpen: (caseId: number) => void;
  onDelete: (caseId: number) => void;
  onExport: (caseId: number) => void;
};

export function CasesPage({ cases, onDelete, onExport, onOpen }: CasesPageProps) {
  return (
    <section>
      <header className="page-header">
        <h1>审核记录</h1>
        <span>{cases.length} 条记录</span>
      </header>
      <div className="table">
        {cases.map((item) => (
          <div className="table-row" key={item.id}>
            <strong>{item.title}</strong>
            <span>{item.status}</span>
            <span>{item.issueCount} 个问题</span>
            <span>{item.highestRiskLevel ?? "未评级"}</span>
            <div className="row-actions">
              <button onClick={() => onOpen(item.id)} type="button">打开</button>
              <button onClick={() => onExport(item.id)} type="button">导出</button>
              <button onClick={() => onDelete(item.id)} type="button">删除</button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
