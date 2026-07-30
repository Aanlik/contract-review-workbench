import { FormEvent, useEffect, useState } from "react";

import {
  getAiSettings,
  getSystemSettings,
  saveAiSettings,
  saveSystemSettings,
  testAiSettings,
} from "../api/client";
import type { AiSettings, SystemSettings } from "../api/types";

const emptySettings: AiSettings = {
  baseUrl: "",
  apiKey: "",
  model: "",
  temperature: 0.2,
  timeoutSeconds: 60,
};

export function SettingsPage() {
  const [settings, setSettings] = useState<AiSettings>(emptySettings);
  const [systemSettings, setSystemSettings] = useState<SystemSettings>({
    ocrEngine: "paddleocr",
    storageRoot: "./data/storage",
    ocrDpi: 260,
    preprocessImages: true,
  });
  const [status, setStatus] = useState("");
  const [isTesting, setIsTesting] = useState(false);

  useEffect(() => {
    getAiSettings()
      .then((value) => {
        if (value) setSettings(value);
      })
      .catch(() => setStatus("尚未读取到 AI 配置。"));
    getSystemSettings()
      .then(setSystemSettings)
      .catch(() => setStatus("尚未读取到系统配置。"));
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    await saveAiSettings(settings);
    await saveSystemSettings(systemSettings);
    setStatus("AI、OCR 和本地存储配置已保存。");
  }

  async function handleTestConnection() {
    setIsTesting(true);
    setStatus("正在测试 AI 接口连接...");
    try {
      const result = await testAiSettings(settings);
      setStatus(`${result.message} 模型：${result.model}，耗时 ${result.latencyMs}ms。`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "AI 接口测试失败。");
    } finally {
      setIsTesting(false);
    }
  }

  return (
    <section className="settings-page">
      <header className="page-header">
        <div>
          <p className="section-kicker">Provider & OCR</p>
          <h1>系统设置</h1>
        </div>
        <span className="page-note">合同文本会发送到你配置的第三方 AI 服务</span>
      </header>
      <form className="form-grid" onSubmit={handleSubmit}>
        <div className="settings-card">
          <div className="settings-card-head">
            <div>
              <h2>AI 接口</h2>
              <p>OpenAI-compatible Chat Completions 接口，用于合同风险审查和 AI 互动。</p>
            </div>
          </div>
          <label>
            AI Base URL
            <input
              onChange={(event) => setSettings((current) => ({ ...current, baseUrl: event.target.value }))}
              placeholder="https://api.example.com/v1"
              value={settings.baseUrl}
            />
          </label>
          <label>
            模型名
            <input
              onChange={(event) => setSettings((current) => ({ ...current, model: event.target.value }))}
              placeholder="model-name"
              value={settings.model}
            />
          </label>
          <label>
            API Key
            <input
              onChange={(event) => setSettings((current) => ({ ...current, apiKey: event.target.value }))}
              placeholder="sk-..."
              type="password"
              value={settings.apiKey}
            />
          </label>
          <div className="two-field-grid">
            <label>
              温度
              <input
                max="2"
                min="0"
                onChange={(event) =>
                  setSettings((current) => ({ ...current, temperature: Number(event.target.value) }))
                }
                step="0.1"
                type="number"
                value={settings.temperature}
              />
            </label>
            <label>
              超时秒数
              <input
                min="1"
                onChange={(event) =>
                  setSettings((current) => ({ ...current, timeoutSeconds: Number(event.target.value) }))
                }
                type="number"
                value={settings.timeoutSeconds}
              />
            </label>
          </div>
          <div className="form-actions">
            <button type="submit">保存配置</button>
            <button disabled={isTesting} onClick={handleTestConnection} type="button">
              {isTesting ? "测试中..." : "测试连接"}
            </button>
          </div>
        </div>
        <div className="settings-card compact">
          <div>
            <h2>OCR 与本地存储</h2>
            <p>第一版优先 PaddleOCR，预留 RapidOCR 作为轻量备选。</p>
          </div>
          <label>
            OCR 引擎
            <select
              onChange={(event) =>
                setSystemSettings((current) => ({
                  ...current,
                  ocrEngine: event.target.value as SystemSettings["ocrEngine"],
                }))
              }
              value={systemSettings.ocrEngine}
            >
              <option value="paddleocr">PaddleOCR（中文合同优先）</option>
              <option value="rapidocr">RapidOCR（轻量备选）</option>
            </select>
          </label>
          <label>
            本地存储位置
            <input
              onChange={(event) =>
                setSystemSettings((current) => ({ ...current, storageRoot: event.target.value }))
              }
              value={systemSettings.storageRoot}
            />
          </label>
          <div className="two-field-grid">
            <label>
              OCR DPI
              <input
                max="500"
                min="120"
                onChange={(event) =>
                  setSystemSettings((current) => ({ ...current, ocrDpi: Number(event.target.value) }))
                }
                step="10"
                type="number"
                value={systemSettings.ocrDpi}
              />
            </label>
            <label className="checkbox-label">
              <input
                checked={systemSettings.preprocessImages}
                onChange={(event) =>
                  setSystemSettings((current) => ({
                    ...current,
                    preprocessImages: event.target.checked,
                  }))
                }
                type="checkbox"
              />
              启用灰度/对比度/锐化预处理
            </label>
          </div>
          <p className="helper-text">当前上传文件、OCR 中间结果和导出报告保存在本机，不会自动上传到 OA。</p>
        </div>
        {status && <p className="status-line">{status}</p>}
      </form>
    </section>
  );
}
