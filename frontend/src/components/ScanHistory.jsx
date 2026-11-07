// Previously scanned URLs, kept in localStorage. Click a row to re-scan it.
import { shortAge, verdictClasses, clampScore } from "../lib/score.js";

export default function ScanHistory({ items, onPick, onClear, now }) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <header className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-300">Recent scans</h3>
        {items.length > 0 && (
          <button
            type="button"
            onClick={onClear}
            className="text-xs text-slate-500 transition hover:text-red-300"
          >
            Clear history
          </button>
        )}
      </header>

      {items.length === 0 ? (
        <p className="text-sm text-slate-500">
          No scans yet — scan a URL and it will be remembered here.
        </p>
      ) : (
        <ul className="flex flex-col divide-y divide-slate-800">
          {items.map((entry) => (
            <li key={entry.url}>
              <button
                type="button"
                onClick={() => onPick(entry.url)}
                className="flex w-full items-center gap-3 py-2 text-left transition hover:bg-slate-800/40"
              >
                <span
                  className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ring-1 ${verdictClasses(
                    entry.verdict,
                    entry.score
                  )}`}
                >
                  {entry.verdict}
                </span>
                <span className="min-w-0 flex-1 truncate font-mono text-xs text-slate-300">{entry.url}</span>
                <span className="shrink-0 text-xs tabular-nums text-slate-400">{clampScore(entry.score)}</span>
                <span className="w-16 shrink-0 text-right text-[10px] text-slate-600">
                  {shortAge(entry.scanned_at, now)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
