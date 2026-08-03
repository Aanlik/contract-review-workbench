import { FormEvent, useEffect, useState } from "react";

import {
  getAiSettings,
  getOcrRuntimeStatus,
  getSystemSettings,
  getTask,
  installOcrDependencies,
  saveAiSettings,
  saveSystemSettings,
  testAiSettings,
} from "../api/client";
import type { AiSettings, OcrInstallTarget, OcrRuntimeStatus, SystemSettings, TaskStatus } from "../api/types";
import { loadWorkspaceState, saveWorkspaceState } from "../state/workspace";
import { labelOf, statusLabels } from "../ui/labels";

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
  const [testResult, setTestResult] = useState(loadWorkspaceState().aiTestResult ?? null);
  const [ocrStatus, setOcrStatus] = useState<OcrRuntimeStatus | null>(null);
  const [isCheckingOcr, setIsCheckingOcr] = useState(false);
  const [isInstallingOcr, setIsInstallingOcr] = useState(false);
  const [ocrInstallTarget, setOcrInstallTarget] = useState<OcrInstallTarget>("rapid");
  const [ocrInstallTask, setOcrInstallTask] = useState<TaskStatus | null>(null);

  useEffect(() => {
    getAiSettings()
      .then((value) => {
        if (value) setSettings(value);
      })
      .catch(() => setStatus("尚未读取到智能审查配置。"));
    getSystemSettings()
      .then(setSystemSettings)
      .catch(() => setStatus("尚未读取到系统配置。"));
    refreshOcrStatus();
  }, []);

  useEffect(() => {
    if (!ocrInstallTask?.taskId || !["queued", "running"].includes(ocrInstallTask.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const task = await getTask(ocrInstallTask.taskId);
        setOcrInstallTask(task);
        if (task.status === "completed") {
          setIsInstallingOcr(false);
          setStatus("扫描识别依赖安装完成，正在重新检测。");
          await refreshOcrStatus();
        }
        if (task.status === "failed") {
          setIsInstallingOcr(false);
          setStatus("扫描识别依赖安装失败，请查看任务错误信息。");
        }
      } catch (error) {
        setIsInstallingOcr(false);
        setStatus(error instanceof Error ? error.message : "读取安装任务失败。");
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [ocrInstallTask?.taskId, ocrInstallTask?.status]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    await saveAiSettings(settings);
    await saveSystemSettings(systemSettings);
    setStatus("智能审查、扫描识别和本地存储配置已保存。");
  }

  async function handleTestConnection() {
    setIsTesting(true);
    setStatus("正在测试智能接口连接...");
    try {
      const result = await testAiSettings(settings);
      const persisted = { ...result, testedAt: new Date().toISOString() };
      setTestResult(persisted);
      const state = loadWorkspaceState();
      saveWorkspaceState({ ...state, aiTestResult: persisted });
      setStatus(`${result.message} 模型：${result.model}，耗时 ${result.latencyMs}ms。`);
    } catch (error) {
      const failResult = {
        ok: false,
        model: settings.model,
        message: error instanceof Error ? error.message : "智能接口测试失败。",
        latencyMs: 0,
        testedAt: new Date().toISOString(),
      };
      setTestResult(failResult);
      const state = loadWorkspaceState();
      saveWorkspaceState({ ...state, aiTestResult: failResult });
      setStatus(failResult.message);
    } finally {
      setIsTesting(false);
    }
  }

  async function refreshOcrStatus() {
    setIsCheckingOcr(true);
    try {
      const result = await getOcrRuntimeStatus();
      setOcrStatus(result);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "扫描识别安装状态检测失败。");
    } finally {
      setIsCheckingOcr(false);
    }
  }

  async function handleInstallOcr(target: OcrInstallTarget) {
    setIsInstallingOcr(true);
    setStatus("正在创建扫描识别依赖安装任务...");
    try {
      const result = await installOcrDependencies(target);
      const task = await getTask(result.taskId);
      setOcrInstallTask(task);
      setStatus(result.message);
    } catch (error) {
      setIsInstallingOcr(false);
      setStatus(error instanceof Error ? error.message : "扫描识别依赖安装任务创建失败。");
    }
  }

  function targetForCurrentEngine(): OcrInstallTarget {
    return systemSettings.ocrEngine === "paddleocr" ? "paddle" : "rapid";
  }

  function renderEngineStatus(key: string, label: string) {
    const item = ocrStatus?.engines[key];
    return (
      <div className="ocr-runtime-row" key={key}>
        <span>{label}</span>
        <strong className={item?.installed ? "ocr-installed" : "ocr-missing"}>
          {item?.installed ? "已安装" : "未安装"}
        </strong>
      </div>
    );
  }

  return (
    <section className="settings-page">
      <header className="page-header">
        <div>
          <p className="section-kicker">系统配置</p>
          <h1>系统设置</h1>
        </div>
        <span className="page-note">合同文本会发送到你配置的第三方智能服务</span>
      </header>
      <form className="form-grid" onSubmit={handleSubmit}>
        <div className="settings-card">
          <div className="settings-card-head">
            <div>
              <h2>智能审查接口</h2>
              <p>第三方对话接口，用于合同风险审查和人工智能互动。</p>
            </div>
          </div>
          <label>
            接口地址
            <input
              onChange={(event) => setSettings((s) => ({ ...s, baseUrl: event.target.value }))}
              placeholder="https://api.deepseek.com/v1"
              value={settings.baseUrl}
            />
          </label>
          <label>
            接口密钥
            <input
              onChange={(event) => setSettings((s) => ({ ...s, apiKey: event.target.value }))}
              placeholder="sk-..."
              type="password"
              value={settings.apiKey}
            />
          </label>
          <label>
            模型名称
            <input
              onChange={(event) => setSettings((s) => ({ ...s, model: event.target.value }))}
              placeholder="deepseek-chat"
              value={settings.model}
            />
          </label>
          <label>
            随机程度（0-2）
            <input
              max={2}
              min={0}
              onChange={(event) => setSettings((s) => ({ ...s, temperature: Number(event.target.value) }))}
              step={0.1}
              type="number"
              value={settings.temperature}
            />
          </label>
          <label>
            超时（秒）
            <input
              min={5}
              onChange={(event) => setSettings((s) => ({ ...s, timeoutSeconds: Number(event.target.value) }))}
              type="number"
              value={settings.timeoutSeconds}
            />
          </label>
          <div className="settings-test-row">
            <button disabled={isTesting} onClick={handleTestConnection} type="button">
              {isTesting ? "测试中..." : "测试连接"}
            </button>
            {testResult && (
              <div className={`test-result ${testResult.ok ? "test-ok" : "test-fail"}`}>
                <span className="test-status">{testResult.ok ? "✓ 连接正常" : "✗ 连接失败"}</span>
                <span className="test-detail">
                  模型：{testResult.model} · {testResult.latencyMs} 毫秒
                  {testResult.testedAt && ` · ${new Date(testResult.testedAt).toLocaleString("zh-CN")}`}
                </span>
                {!testResult.ok && <span className="test-error">{testResult.message}</span>}
              </div>
            )}
          </div>
        </div>

        <div className="settings-card">
          <div className="settings-card-head">
            <div>
              <h2>扫描识别与存储</h2>
              <p>扫描件识别引擎、预处理参数和本地文件存储路径。</p>
            </div>
          </div>
          <label>
            扫描识别引擎
            <select
              onChange={(event) =>
                setSystemSettings((s) => ({ ...s, ocrEngine: event.target.value as SystemSettings["ocrEngine"] }))}
              value={systemSettings.ocrEngine}
            >
              <option value="paddleocr">高精度中文识别引擎</option>
              <option value="rapidocr">轻量快速识别引擎</option>
            </select>
          </label>
          <label>
            本地存储路径
            <input
              onChange={(event) => setSystemSettings((s) => ({ ...s, storageRoot: event.target.value }))}
              value={systemSettings.storageRoot}
            />
          </label>
          <label>
            扫描清晰度（120-500）
            <input
              max={500}
              min={120}
              onChange={(event) => setSystemSettings((s) => ({ ...s, ocrDpi: Number(event.target.value) }))}
              type="number"
              value={systemSettings.ocrDpi}
            />
          </label>
          <label className="checkbox-label">
            <input
              checked={systemSettings.preprocessImages}
              onChange={(event) => setSystemSettings((s) => ({ ...s, preprocessImages: event.target.checked }))}
              type="checkbox"
            />
            图片预处理（灰度 + 自动对比度 + 锐化）
          </label>

          <div className="ocr-runtime-panel">
            <div className="ocr-runtime-head">
              <div>
                <h3>本机识别依赖</h3>
                <p>
                  当前引擎：{systemSettings.ocrEngine === "paddleocr" ? "高精度中文识别引擎" : "轻量快速识别引擎"}
                  {ocrStatus && ` · ${ocrStatus.currentEngineInstalled ? "可用" : "不可用"}`}
                </p>
              </div>
              <button disabled={isCheckingOcr} onClick={refreshOcrStatus} type="button">
                {isCheckingOcr ? "检测中..." : "重新检测"}
              </button>
            </div>

            <div className="ocr-runtime-list">
              {renderEngineStatus("rapidocr", "轻量快速识别引擎")}
              {renderEngineStatus("rapidocr_onnxruntime", "旧版兼容识别引擎")}
              {renderEngineStatus("onnxruntime", "本地推理运行环境")}
              {renderEngineStatus("paddleocr", "高精度中文识别引擎")}
            </div>

            {!ocrStatus?.installSupported && (
              <p className="ocr-runtime-warning">{ocrStatus?.installSupportedReason}</p>
            )}

            <div className="ocr-install-row">
              <select
                disabled={isInstallingOcr || ocrStatus?.installSupported === false}
                onChange={(event) => setOcrInstallTarget(event.target.value as OcrInstallTarget)}
                value={ocrInstallTarget}
              >
                <option value="rapid">轻量快速识别引擎</option>
                <option value="rapid-legacy">旧版兼容识别引擎</option>
                <option value="paddle">高精度中文识别引擎</option>
                <option value="all">全部识别依赖</option>
              </select>
              <button
                disabled={isInstallingOcr || ocrStatus?.installSupported === false}
                onClick={() => handleInstallOcr(ocrInstallTarget)}
                type="button"
              >
                {isInstallingOcr ? "安装中..." : "一键安装"}
              </button>
              <button
                className="secondary"
                disabled={isInstallingOcr || ocrStatus?.installSupported === false}
                onClick={() => handleInstallOcr(targetForCurrentEngine())}
                type="button"
              >
                安装当前引擎
              </button>
            </div>

            {ocrInstallTask && (
              <div className="task-card">
                <div className="task-header">
                  <span>安装任务：{labelOf(statusLabels, ocrInstallTask.status)}</span>
                  <strong>{ocrInstallTask.progressPercent}%</strong>
                </div>
                <div className="task-progress">
                  <div style={{ width: `${ocrInstallTask.progressPercent}%` }} />
                </div>
                <p>{ocrInstallTask.progress || "等待执行..."}</p>
                {ocrInstallTask.error && <p className="task-error">{ocrInstallTask.error}</p>}
              </div>
            )}
          </div>
        </div>

        <button type="submit">保存设置</button>
        {status && <p className="status-line">{status}</p>}
      </form>
    </section>
  );
}
