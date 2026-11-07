// Scanning progress: engine names appear one by one as they finish.
export default function EngineProgress({ finished, done }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <p className="mb-3 text-sm text-slate-400">
        {done ? "Scan complete" : "Running trust engines…"}
      </p>
      <ul className="flex flex-wrap gap-2">
        {finished.map((name) => (
          <li
            key={name}
            className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-sm text-emerald-300 ring-1 ring-emerald-500/30"
          >
            <span aria-hidden="true">✓</span>
            {name}
          </li>
        ))}
        {!done && (
          <li className="flex items-center gap-1.5 rounded-full bg-slate-800 px-3 py-1 text-sm text-slate-400 ring-1 ring-slate-700">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-slate-400" aria-hidden="true" />
            working…
          </li>
        )}
      </ul>
    </div>
  );
}
