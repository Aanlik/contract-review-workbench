export function NewCasePage() {
  return (
    <section>
      <header className="page-header">
        <h1>新建审核</h1>
      </header>
      <div className="form-grid">
        <label>
          合同名称
          <input placeholder="输入合同名称" />
        </label>
        <label>
          我方立场
          <select defaultValue="party_a">
            <option value="party_a">甲方</option>
            <option value="party_b">乙方</option>
            <option value="other">其他</option>
          </select>
        </label>
        <label>
          审核重点
          <textarea placeholder="例如：重点关注付款、违约责任和流程合规" />
        </label>
      </div>
    </section>
  );
}
