// Reasons, grouped by engine, with severity badges.
import { severityClasses } from "../lib/score.js";

const SEVERITIES = ["info", "low", "medium", "high"];

function percent(x0to1) {
  return `${Math.round((Number(x0to1) || 0) * 100)}%`;
}

export default function ReasonList({ result }) {
  const engines = (result?.engines || []).slice().sort((a, b) => (b.risk ?? 0) - (a.risk ?? 0));

  if (engines.length === 0) {
    return <p className="text-sm text-slate-500">No engine results in this response.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {engines.map((engine) => (
        <section key={engine.name} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <header className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
            <h4 className="font-mono text-sm font-semibold text-slate-200">{engine.name}</h4>
            <span className="text-xs text-slate-500">
              risk {percent(engine.risk)} · confidence {percent(engine.confidence)}
            </span>
          </header>

          {engine.error && (
            <p className="mb-2 rounded-lg bg-amber-500/10 px-2.5 py-1.5 text-xs text-amber-300 ring-1 ring-amber-500/25">
              Engine note: {engine.error}
            </p>
          )}

          <ul className="flex flex-col gap-1.5">
            {(engine.reasons || []).map((reason, i) => (
              <li key={i} className="flex items-start gap-2">
                <span
                  className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ring-1 ${severityClasses(
                    SEVERITIES.includes(reason.severity) ? reason.severity : "info"
                  )}`}
                >
                  {reason.severity}
                </span>
                <span className="text-sm leading-relaxed text-slate-300">{reason.text}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
