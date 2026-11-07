// "Report this site" button + small inline form, POSTs to /report.
import { useState } from "react";
import { sendReport } from "../api.js";
import { getReporterId } from "../lib/history.js";

const CATEGORIES = ["phishing", "scam", "impersonation", "legitimate"];

export default function ReportSection({ url, verdict }) {
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(null);
  const [error, setError] = useState(null);

  function suggestedCategory() {
    return verdict === "safe" ? "legitimate" : CATEGORIES[0];
  }

  function openForm() {
    setCategory(suggestedCategory());
    setSent(null);
    setError(null);
    setOpen(true);
  }

  async function submit(e) {
    e.preventDefault();
    setSending(true);
    setError(null);
    try {
      const result = await sendReport({
        url,
        category,
        note: note.trim(),
        reporter_id: getReporterId(),
      });
      setSent(result);
      setOpen(false);
      setNote("");
    } catch (err) {
      setError(err.message || "Sending the report failed.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={openForm}
        className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-100 ring-1 ring-slate-700 transition hover:bg-slate-700 disabled:opacity-50"
        disabled={sending}
      >
        ⚑ Report this site
      </button>

      {error && (
        <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-300 ring-1 ring-red-500/25">{error}</p>
      )}
      {sent && (
        <p className="rounded-lg bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300 ring-1 ring-emerald-500/25">
          Report submitted (id {sent.id}, status {sent.status}).
        </p>
      )}

      {open && (
        <form onSubmit={submit} className="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/60 p-3">
          <label className="text-xs text-slate-400">
            Category
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-2 text-sm text-slate-200 focus:border-sky-500 focus:outline-none"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-slate-400">
            Note (optional)
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              maxLength={500}
              placeholder="What did you see?"
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-2 text-sm text-slate-200 focus:border-sky-500 focus:outline-none"
            />
          </label>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={sending}
              className="rounded-lg bg-rose-600 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-rose-500 disabled:opacity-50"
            >
              {sending ? "Sending…" : "Send report"}
            </button>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded-lg px-3 py-1.5 text-sm text-slate-400 transition hover:text-slate-200"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
