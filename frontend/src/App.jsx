// HackMatrix dashboard: scan a URL, show the trust score, reasons and
// certificate chain, report suspicious sites, keep local scan history.
import { useState } from "react";
import { analyze, apiConfig } from "./api.js";
import { normalizeUrl } from "./lib/validate.js";
import { addHistory, clearHistory, loadHistory } from "./lib/history.js";
import { clampScore } from "./lib/score.js";
import ScoreGauge from "./components/ScoreGauge.jsx";
import EngineProgress from "./components/EngineProgress.jsx";
import ReasonList from "./components/ReasonList.jsx";
import CertificateChain from "./components/CertificateChain.jsx";
import ReportSection from "./components/ReportSection.jsx";
import ScanHistory from "./components/ScanHistory.jsx";

const { apiBase, useMock } = apiConfig();

export default function App() {
  const [url, setUrl] = useState("");
  const [inputError, setInputError] = useState(null);
  const [scanError, setScanError] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [finishedEngines, setFinishedEngines] = useState([]);
  const [result, setResult] = useState(null);
  const [scannedUrl, setScannedUrl] = useState(null);
  const [history, setHistory] = useState(() => loadHistory());

  async function scan(target) {
    const check = normalizeUrl(target);
    if (!check.ok) {
      setInputError(check.error);
      return;
    }
    setInputError(null);
    setScanError(null);
    setResult(null);
    setFinishedEngines([]);
    setScannedUrl(check.url);
    setScanning(true);
    try {
      const data = await analyze(check.url, (engineName) =>
        setFinishedEngines((prev) => [...prev, engineName])
      );
      setResult(data);
      setHistory(
        addHistory({
          url: check.url,
          score: clampScore(data.score),
          verdict: data.verdict || "",
          scanned_at: data.scanned_at || new Date().toISOString(),
        })
      );
    } catch (err) {
      setScanError(err.message || "The scan failed.");
    } finally {
      setScanning(false);
    }
  }

  function onSubmit(e) {
    e.preventDefault();
    if (!scanning) scan(url);
  }

  function pickHistory(url) {
    setUrl(url);
    if (!scanning) scan(url);
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-4 py-8">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Hack<span className="text-sky-400">Matrix</span>
          </h1>
          <p className="text-sm text-slate-400">URL trust dashboard</p>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
            useMock
              ? "bg-violet-500/15 text-violet-300 ring-violet-500/30"
              : "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30"
          }`}
          title={apiBase}
        >
          {useMock ? "mock mode" : `API · ${apiBase}`}
        </span>
      </header>

      <form onSubmit={onSubmit} className="flex flex-col gap-1.5">
        <div className="flex gap-2">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com — try a URL containing safe, suspicious or dangerous"
            spellCheck={false}
            className={`min-w-0 flex-1 rounded-lg border bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none ${
              inputError ? "border-red-500/60 focus:border-red-400" : "border-slate-700 focus:border-sky-500"
            }`}
          />
          <button
            type="submit"
            disabled={scanning}
            className="shrink-0 rounded-lg bg-sky-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-sky-500 disabled:opacity-50"
          >
            {scanning ? "Scanning…" : "Scan"}
          </button>
        </div>
        {inputError && <p className="px-1 text-xs text-red-400">{inputError}</p>}
      </form>

      {scanError && (
        <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
          <strong className="font-semibold">Scan failed.</strong> {scanError}
        </div>
      )}

      {scanning && <EngineProgress finished={finishedEngines} done={false} />}

      {result && !scanning && (
        <main className="flex flex-col gap-6">
          <section className="grid gap-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 md:grid-cols-[240px_1fr]">
            <ScoreGauge score={result.score} verdict={result.verdict} />
            <div className="flex flex-col gap-3">
              <div className="min-w-0">
                <p className="truncate font-mono text-sm text-slate-300" title={scannedUrl || result.url}>
                  {scannedUrl || result.url}
                </p>
                {result.scanned_at && (
                  <p className="mt-0.5 text-xs text-slate-500">Scanned {result.scanned_at}</p>
                )}
              </div>
              <ReportSection url={scannedUrl || result.url} verdict={result.verdict} />
            </div>
          </section>

          <section className="flex flex-col gap-3">
            <h3 className="text-sm font-semibold text-slate-300">Certificate chain</h3>
            <CertificateChain chain={result.certificate_chain} />
          </section>

          <section className="flex flex-col gap-3">
            <h3 className="text-sm font-semibold text-slate-300">
              Reasons by engine {result.reasons ? `(${result.reasons.length} total)` : ""}
            </h3>
            <ReasonList result={result} />
          </section>
        </main>
      )}

      <ScanHistory
        items={history}
        now={new Date()}
        onPick={pickHistory}
        onClear={() => {
          clearHistory();
          setHistory([]);
        }}
      />

      <footer className="mt-auto pt-2 text-center text-[11px] text-slate-600">
        Engines are passive (HTTP/DNS/TLS only) · page content is untrusted data
      </footer>
    </div>
  );
}
