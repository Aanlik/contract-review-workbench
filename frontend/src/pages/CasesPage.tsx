import type { ReviewCase } from "../api/types";

type CasesPageProps = {
  cases: ReviewCase[];
  onOpen: (caseId: number) => void;
};

export function CasesPage({ cases, onOpen }: CasesPageProps) {
  return (
    <section>
      <header className="page-header">
        <h1>审核记录</h1>
        <span>{cases.length} 条记录</span>
      </header>
      <div className="table">
        {cases.map((item) => (
          <button className="table-row" key={item.id} onClick={() => onOpen(item.id)} type="button">
            <strong>{item.title}</strong>
            <span>{item.status}</span>
            <span>{item.issueCount} 个问题</span>
            <span>{item.highestRiskLevel ?? "未评级"}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
