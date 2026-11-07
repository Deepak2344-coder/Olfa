// Plain vertical list of TLS chain nodes (the non-3D view). Also the fallback
// for browsers/laptops without WebGL or with prefers-reduced-motion? — no,
// reduced motion only disables the animation; the list is the WebGL fallback.
import { certStatusClasses } from "../lib/score.js";

const ROLE_CLASSES = {
  root: "bg-slate-500/15 text-slate-300 ring-slate-500/30",
  intermediate: "bg-sky-500/15 text-sky-300 ring-sky-500/30",
  leaf: "bg-violet-500/15 text-violet-300 ring-violet-500/30",
};

export default function CertificateChainList({ chain }) {
  if (!Array.isArray(chain) || chain.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No certificate chain in this response (e.g. plain-HTTP sites have none).
      </p>
    );
  }

  return (
    <ol className="relative ml-2 flex list-none flex-col gap-3 border-l border-slate-700 pl-4">
      {chain.map((node, i) => {
        const status = certStatusClasses(node.status);
        return (
          <li key={i} className="relative">
            {/* status dot on the rail */}
            <span className={`absolute -left-[22px] top-2 h-3 w-3 rounded-full ring-2 ring-slate-900 ${status.dot}`} />
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
              <div className="mb-1.5 flex flex-wrap items-center gap-2">
                <span
                  className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ring-1 ${
                    ROLE_CLASSES[node.role] || ROLE_CLASSES.root
                  }`}
                >
                  {node.role || "cert"}
                </span>
                <span className={`text-xs font-semibold ${status.text}`}>
                  {node.status}
                </span>
              </div>
              <p className="break-all font-mono text-sm text-slate-200">{node.subject}</p>
              {node.issuer && node.issuer !== node.subject && (
                <p className="mt-0.5 break-all font-mono text-xs text-slate-500">issued by {node.issuer}</p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
