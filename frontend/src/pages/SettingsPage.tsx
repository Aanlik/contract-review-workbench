export function SettingsPage() {
  return (
    <section>
      <header className="page-header">
        <h1>设置</h1>
      </header>
      <div className="form-grid">
        <label>
          AI Base URL
          <input placeholder="https://api.example.com/v1" />
        </label>
        <label>
          模型名
          <input placeholder="model-name" />
        </label>
        <label>
          API Key
          <input placeholder="sk-..." type="password" />
        </label>
      </div>
    </section>
  );
}
