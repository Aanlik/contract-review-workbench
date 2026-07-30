export function ReviewWorkspacePage() {
  return (
    <section className="workspace-grid">
      <aside className="issue-column">
        <h2>问题清单</h2>
        <p>等待审核结果或人工标记。</p>
      </aside>
      <section className="evidence-column">
        <h2>合同与证据</h2>
        <p>选择问题后定位到合同、签报或会议纪要原文。</p>
      </section>
      <aside className="detail-column">
        <h2>问题详情</h2>
        <p>AI 建议、重新分析和互动窗口会显示在这里。</p>
      </aside>
    </section>
  );
}
