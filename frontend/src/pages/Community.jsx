// Community page: lists GET /reports with status badges, confirmation counts
// and a Confirm button. Posting a Confirm sends only {report_id, reporter_id}.
// In mock mode it serves the /shared/contracts reports fixture.
import { useCallback, useEffect, useState } from "react";
import { apiConfig, confirmReport, fetchReports } from "../api.js";
import { getReporterId } from "../lib/history.js";
import { shortAge, statusClasses } from "../lib/score.js";
import { ReportsSkeleton } from "../components/Skeleton.jsx";
import { Link } from "../router.jsx";

const { useMock } = apiConfig();

export default function Community() {
  const [state, setState] = useState({ phase: "loading", data: null, error: null });
  const [confirmed, setConfirmed] = useState({}); // report id -> response
  const [confirming, setConfirming] = useState({}); // report id -> true while sending
  const [confirmErrors, setConfirmErrors] = useState({}); // report id -> message
  const [reporterId, setReporterId] = useState("");

  const load = useCallback(async () => {
    setState({ phase: "loading", data: null, error: null });
    setConfirmed({});
    setConfirmErrors({});
    setConfirming({});
    try {
      const data = await fetchReports();
      setState({ phase: "done", data, error: null });
    } catch (err) {
      setState({ phase: "error", data: null, error: err.message || "Loading the reports failed." });
    }
  }, []);

  useEffect(() => {
    load();
    try {
      setReporterId(getReporterId());
    } catch {
      // storage unavailable: report/confirm flows still work with a fresh id
    }
  }, [load]);

  async function onConfirm(report) {
    setConfirming((prev) => ({ ...prev, [report.id]: true }));
    setConfirmErrors((prev) => ({ ...prev, [report.id]: null }));
    try {
      const response = await confirmReport(report.id);
      setConfirmed((prev) => ({ ...prev, [report.id]: response }));
    } catch (err) {
      setConfirmErrors((prev) => ({ ...prev, [report.id]: err.message || "Confirmation failed." }));
    } finally {
      setConfirming((prev) => ({ ...prev, [report.id]: false }));
    }
  }

  const reports = state.data?.reports || [];

  return (
    <main className="flex flex-col gap-4">
      <section className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Community reports</h2>
          <p className="text-sm text-slate-400">
            {state.data
              ? `${state.data.total ?? reports.length} report${(state.data.total ?? reports.length) === 1 ? "" : "s"}${
                  state.data.generated_at ? ` · generated ${shortAge(state.data.generated_at)}` : ""
                }`
              : "Other users' verdicts about suspicious URLs. Confirm reports you have seen too."}
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={state.phase === "loading"}
          className="rounded-lg bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-100 ring-1 ring-slate-700 transition hover:bg-slate-700 disabled:opacity-50"
        >
          ⟳ Refresh
        </button>
      </section>

      {state.phase === "loading" && <ReportsSkeleton />}

      {state.phase === "error" && (
        <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
          <strong className="font-semibold">Could not load reports.</strong> {state.error}
        </div>
      )}

      {state.phase === "done" && reports.length === 0 && (
        <section className="rounded-xl border border-dashed border-slate-700 bg-slate-900/40 p-8 text-center">
          <p className="text-sm text-slate-400">No community reports yet.</p>
          <p className="mt-1 text-xs text-slate-500">
            Report a suspicious site from the dashboard and it will show up here, together with
            everyone else's confirmations.
          </p>
          <Link
            to="/"
            className="mt-3 inline-block rounded-lg bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-100 ring-1 ring-slate-700 transition hover:bg-slate-700"
          >
            Go scan a site
          </Link>
        </section>
      )}

      {reports.map((report) => (
        <ReportCard
          key={report.id}
          report={report}
          confirmed={Boolean(confirmed[report.id])}
          sending={Boolean(confirming[report.id])}
          error={confirmErrors[report.id] || null}
          onConfirm={onConfirm}
        />
      ))}

      {reporterId && state.phase === "done" && (
        <p className="text-center text-[11px] text-slate-600">
          Your reporter id: <span className="font-mono text-slate-500">{reporterId}</span> — generated
          once and kept in this browser's localStorage.{useMock ? " Mock mode serves the /shared/contracts reports fixture." : ""}
        </p>
      )}
    </main>
  );
}

function ReportCard({ report, confirmed, sending, error, onConfirm }) {
  const confirmations = (Number(report.confirmations) || 0) + (confirmed ? 1 : 0);
  const showStrength = report.confirming_reputation != null && Number.isFinite(Number(report.confirming_reputation));
  const confirmStrength = showStrength
    ? (Number(report.confirming_reputation) + (confirmed ? 0.3 : 0)).toFixed(1)
    : null;

  return (
    <article className="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-slate-500/15 px-2.5 py-1 text-[11px] font-semibold ring-1 ring-slate-500/30">
          {report.category}
        </span>
        <span
          className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ring-1 ${statusClasses(report.status)}`}
        >
          {report.status}
        </span>
        <span className="ml-auto text-[11px] text-slate-500">{shortAge(report.created_at)}</span>
      </div>

      <p className="min-w-0 break-all font-mono text-xs text-slate-300" title={report.url}>
        {report.url}
      </p>

      {report.note && (
        <p className="border-l-2 border-slate-700 pl-2.5 text-sm italic text-slate-400">“{report.note}”</p>
      )}

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
        <span>
          <strong className="tabular-nums text-slate-300">{confirmations}</strong> confirmations ·{" "}
          <strong className="tabular-nums text-slate-300">{Number(report.denials) || 0}</strong> denials
        </span>
        {confirmStrength != null && (
          <span className="tabular-nums">confirmation strength {confirmStrength}</span>
        )}
        {report.category_counts && (
          <span className="truncate">
            {Object.entries(report.category_counts)
              .map(([cat, n]) => `${n} ${cat}`)
              .join(", ")}
          </span>
        )}
      </div>

      {report.status_detail && (
        <p className="text-[11px] text-slate-600">{report.status_detail}</p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => onConfirm(report)}
          disabled={confirmed || sending}
          className={`ml-auto rounded-lg px-3.5 py-1.5 text-xs font-semibold transition ${
            confirmed
              ? "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30"
              : "bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-50"
          }`}
        >
          {confirmed ? "✓ You confirmed this" : sending ? "Confirming…" : "Confirm"}
        </button>
        {error && <p className="w-full text-xs text-red-400">{error}</p>}
      </div>
    </article>
  );
}
