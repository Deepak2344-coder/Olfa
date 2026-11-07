// Main scan page: URL input, scanning progress + skeletons, result view and
// scan history. Also honors a pending one-click scan from the demo page.
import { useEffect, useRef, useState } from "react";
import { analyze } from "../api.js";
import { normalizeUrl } from "../lib/validate.js";
import { addHistory, clearHistory, loadHistory } from "../lib/history.js";
import { clampScore } from "../lib/score.js";
import { takePendingScan } from "../lib/pending.js";
import ScoreGauge from "../components/ScoreGauge.jsx";
import EngineProgress from "../components/EngineProgress.jsx";
import ReasonList from "../components/ReasonList.jsx";
import CertificateChain from "../components/CertificateChain.jsx";
import ReportSection from "../components/ReportSection.jsx";
import ScanHistory from "../components/ScanHistory.jsx";
import ScoreExplainer from "../components/ScoreExplainer.jsx";
import { ResultSkeleton, ReasonsSkeleton, Skeleton } from "../components/Skeleton.jsx";

export default function Home() {
  const [url, setUrl] = useState("");
  const [inputError, setInputError] = useState(null);
  const [scanError, setScanError] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [finishedEngines, setFinishedEngines] = useState([]);
  const [result, setResult] = useState(null);
  const [scannedUrl, setScannedUrl] = useState(null);
  const [history, setHistory] = useState(() => loadHistory());
  const pendingConsumed = useRef(false);

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

  // One-click demo scans arrive via sessionStorage before this page mounts.
  useEffect(() => {
    if (pendingConsumed.current) return;
    pendingConsumed.current = true;
    const pending = takePendingScan();
    if (pending) {
      setUrl(pending);
      scan(pending);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function onSubmit(e) {
    e.preventDefault();
    if (!scanning) scan(url);
  }

  function pickHistory(entryUrl) {
    setUrl(entryUrl);
    if (!scanning) scan(entryUrl);
  }

  return (
    <main className="flex flex-col gap-6">
      <form onSubmit={onSubmit} className="flex flex-col gap-1.5">
        <div className="flex flex-col gap-2 sm:flex-row">
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
            className="rounded-lg bg-sky-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-sky-500 disabled:opacity-50 sm:w-32"
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

      {scanning && (
        <>
          <EngineProgress finished={finishedEngines} done={false} />
          <ResultSkeleton />
          <ReasonsSkeleton />
        </>
      )}

      {!scanning && !result && !scanError && (
        <section className="rounded-xl border border-dashed border-slate-700 bg-slate-900/40 p-8 text-center">
          <p className="text-sm text-slate-400">
            Type a URL above and press <span className="font-semibold text-slate-200">Scan</span> to
            get a trust score from the engines.
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Or open the <span className="font-semibold">Demo</span> page for one-click example URLs.
          </p>
        </section>
      )}

      {result && !scanning && (
        <>
          <section className="grid gap-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 md:p-6 md:grid-cols-[240px_1fr]">
            <ScoreGauge score={result.score} verdict={result.verdict} />
            <div className="flex min-w-0 flex-col gap-3">
              <div className="min-w-0">
                <p className="break-all font-mono text-sm text-slate-300" title={scannedUrl || result.url}>
                  {scannedUrl || result.url}
                </p>
                {result.scanned_at && (
                  <p className="mt-0.5 text-xs text-slate-500">Scanned {result.scanned_at}</p>
                )}
              </div>
              <ReportSection url={scannedUrl || result.url} verdict={result.verdict} />
            </div>
          </section>

          <ScoreExplainer result={result} />

          <CertificateChain chain={result.certificate_chain} />

          <section className="flex flex-col gap-3">
            <h3 className="text-sm font-semibold text-slate-300">
              Reasons by engine {result.reasons ? `(${result.reasons.length} total)` : ""}
            </h3>
            <ReasonList result={result} />
          </section>
        </>
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
    </main>
  );
}
