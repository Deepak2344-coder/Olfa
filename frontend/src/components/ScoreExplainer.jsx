// "How this score was calculated" panel: explains the trust score, gauge
// bands and severity badges; with a result, shows each engine's risk and
// confidence as small bars.
import { scoreBand } from "../lib/score.js";

const RISK_BAR_COLOR = { green: "bg-emerald-500/60", amber: "bg-amber-500/60", red: "bg-red-500/60" };

function riskColor(risk0to1) {
  const r = Number(risk0to1) || 0;
  if (r >= 0.66) return RISK_BAR_COLOR.red;
  if (r >= 0.33) return RISK_BAR_COLOR.amber;
  return RISK_BAR_COLOR.green;
}

export default function ScoreExplainer({ result }) {
  const engines = result?.engines || [];

  return (
    <details className="rounded-xl border border-slate-800 bg-slate-900/60">
      <summary className="cursor-pointer select-none px-4 py-3 text-sm font-semibold text-slate-300">
        How this score was calculated
      </summary>
      <div className="flex flex-col gap-4 border-t border-slate-800 px-4 py-4 text-sm text-slate-400">
        <p>
          Every trust engine looks at one aspect of the URL — certificate, domain age, reputation
          lists, page behaviour, transport security, DNS history, redirects — and returns a{" "}
          <strong className="text-slate-200">risk</strong> (0–1, higher = riskier) and a{" "}
          <strong className="text-slate-200">confidence</strong> (0–1). The backend combines the
          weighted answers into a <strong className="text-slate-200">trust score of 0–100</strong>{" "}
          (higher = safer) and picks a verdict.
        </p>

        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <p className="mb-1.5 font-semibold text-slate-300">Gauge bands (trust score)</p>
            <ul className="flex flex-col gap-1">
              <li className="flex items-center gap-2">
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-400" />{" "}
                <span className="tabular-nums text-slate-300">80–100</span> — trusted
              </li>
              <li className="flex items-center gap-2">
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-amber-400" />{" "}
                <span className="tabular-nums text-slate-300">35–79</span> — be careful
              </li>
              <li className="flex items-center gap-2">
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-red-400" />{" "}
                <span className="tabular-nums text-slate-300">0–34</span> — likely malicious
              </li>
            </ul>
          </div>
          <div>
            <p className="mb-1.5 font-semibold text-slate-300">Severity badges</p>
            <ul className="flex flex-col gap-1">
              <li><span className="rounded bg-red-500/15 px-1.5 py-0.5 text-[10px] font-bold uppercase text-red-300 ring-1 ring-red-500/30">high</span> — strong danger signal</li>
              <li><span className="rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-bold uppercase text-amber-300 ring-1 ring-amber-500/30">medium</span> — noteworthy signal</li>
              <li><span className="rounded bg-sky-500/15 px-1.5 py-0.5 text-[10px] font-bold uppercase text-sky-300 ring-1 ring-sky-500/30">low</span> — weak signal</li>
              <li><span className="rounded bg-slate-500/15 px-1.5 py-0.5 text-[10px] font-bold uppercase text-slate-300 ring-1 ring-slate-500/30">info</span> — neutral context</li>
            </ul>
          </div>
        </div>

        {engines.length > 0 && (
          <div className="flex flex-col gap-2">
            <p className="font-semibold text-slate-300">Engine contributions for this scan:</p>
            <ul className="flex flex-col gap-1.5">
              {engines.map((engine) => {
                const risk = Number(engine.risk) || 0;
                return (
                  <li key={engine.name} className="flex items-center gap-3">
                    <span className="w-40 shrink-0 truncate font-mono text-xs text-slate-300" title={engine.name}>
                      {engine.name}
                    </span>
                    <span className="h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-slate-800">
                      <span
                        className={`block h-full rounded-full ${riskColor(risk)}`}
                        style={{ width: `${Math.round(risk * 100)}%` }}
                      />
                    </span>
                    <span className="w-36 shrink-0 text-right text-xs tabular-nums text-slate-500">
                      risk {Math.round(risk * 100)}% · conf {Math.round((engine.confidence || 0) * 100)}%
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        <p className="text-xs text-slate-500">
          The dashboard sends only the URL. The backend performs its own passive HTTP / DNS / TLS
          checks and treats everything it receives as untrusted data.
        </p>
      </div>
    </details>
  );
}
