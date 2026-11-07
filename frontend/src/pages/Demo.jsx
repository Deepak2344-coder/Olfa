// Demo page: one-click buttons for the three /shared/contracts example URLs.
import { navigate } from "../router.jsx";
import { setPendingScan } from "../lib/pending.js";

const DEMOS = [
  {
    verdict: "dangerous",
    url: "https://hsbc-internet-banking.secure-idverify.top/auth/signin",
    blurb: "A fake banking login: lookalike domain, fresh certificate, credentials posted off-site.",
  },
  {
    verdict: "suspicious",
    url: "http://free-crypto-giveaway-winners.example-bonus.click/",
    blurb: "Keyword-stuffed giveaway lure on a cheap TLD, served without HTTPS.",
  },
  {
    verdict: "safe",
    url: "https://en.wikipedia.org/wiki/Cat",
    blurb: "The Wikipedia article on cats — old domain, clean reputation, valid certificate.",
  },
];

function open(url) {
  setPendingScan(url);
  navigate("/");
}

const BADGE = {
  dangerous: "bg-red-500/15 text-red-300 ring-red-500/30",
  suspicious: "bg-amber-500/15 text-amber-300 ring-amber-500/30",
  safe: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
};

export default function Demo() {
  return (
    <main className="flex flex-col gap-4">
      <section className="flex flex-col gap-1 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <h2 className="text-lg font-semibold text-slate-100">Demo URLs</h2>
        <p className="text-sm text-slate-400">
          One click runs the scan on the dashboard and shows the full result,
          including the 3D certificate chain. In mock mode these map to the
          examples in <span className="font-mono">/shared/contracts</span>; with the
          real backend they are honest scans of those URLs.
        </p>
      </section>

      <div className="grid gap-4 sm:grid-cols-3">
        {DEMOS.map((demo) => (
          <section
            key={demo.url}
            className="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/60 p-4"
          >
            <span
              className={`self-start rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ring-1 ${BADGE[demo.verdict]}`}
            >
              {demo.verdict}
            </span>
            <p className="min-w-0 break-all font-mono text-xs text-slate-300">{demo.url}</p>
            <p className="text-sm text-slate-400">{demo.blurb}</p>
            <button
              type="button"
              onClick={() => open(demo.url)}
              className="mt-auto w-full rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-sky-500"
            >
              Scan it →
            </button>
            <p className="text-[11px] text-slate-600">
              Any URL containing a keyword like <span className="font-mono">hsbc</span>,{" "}
              <span className="font-mono">crypto</span> or <span className="font-mono">wikipedia</span>{" "}
              maps the same way in mock mode.
            </p>
          </section>
        ))}
      </div>
    </main>
  );
}
