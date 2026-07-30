import type { ReviewCase } from "../api/types";

type CasesPageProps = {
  cases: ReviewCase[];
  onOpen: (caseId: number) => void;
  onRename: (item: ReviewCase) => void;
  onDelete: (caseId: number) => void;
  onExport: (caseId: number) => void;
};

export function CasesPage({ cases, onDelete, onExport, onOpen, onRename }: CasesPageProps) {
  return (
    <section className="records-page">
      <header className="page-header">
        <div>
          <p className="section-kicker">Review Records</p>
          <h1>审核记录</h1>
        </div>
        <span className="page-note">{cases.length} 条记录</span>
      </header>
      <div className="table">
        {cases.map((item) => (
          <div className="table-row" key={item.id}>
            <div>
              <strong>{item.title}</strong>
              {item.note && <p>{item.note}</p>}
            </div>
            <span>{item.status}</span>
            <span>{item.issueCount} 个问题</span>
            <span>{item.highestRiskLevel ?? "未评级"}</span>
            <div className="row-actions">
              <button onClick={() => onOpen(item.id)} type="button">打开</button>
              <button onClick={() => onRename(item)} type="button">重命名</button>
              <button onClick={() => onExport(item.id)} type="button">导出</button>
              <button onClick={() => onDelete(item.id)} type="button">删除</button>
            </div>
          </div>
        ))}
        {!cases.length && <p className="empty-state">还没有审核记录，请先新建一次合同审查。</p>}
      </div>
    </section>
  );
}
