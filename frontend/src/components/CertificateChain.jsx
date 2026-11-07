// Certificate chain, switchable between the 3D view (three.js blocks + links)
// and the plain vertical list. The 3D module is lazy-loaded so three.js is a
// separate chunk that only downloads when needed; browsers without WebGL (or
// with it failing at runtime) fall back to the list automatically.
import { Suspense, lazy, useMemo, useState } from "react";
import CertificateChainList from "./CertificateChainList.jsx";

const CertificateChain3D = lazy(() => import("./CertificateChain3D.jsx"));

const VIEW_KEY = "hackmatrix_cert_view";

function storageGet(key, fallback) {
  try {
    return window.localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}

function storageSet(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // private mode etc.: choice just isn't persisted
  }
}

function webglAvailable() {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(
      window.WebGLRenderingContext &&
        (canvas.getContext("webgl") || canvas.getContext("experimental-webgl"))
    );
  } catch {
    return false;
  }
}

export default function CertificateChain({ chain }) {
  const can3D = useMemo(webglAvailable, []);
  const [view, setView] = useState(() => {
    if (!can3D || !Array.isArray(chain) || chain.length === 0) return "list";
    return storageGet(VIEW_KEY, "3d") === "list" ? "list" : "3d";
  });

  const hasChain = Array.isArray(chain) && chain.length > 0;

  function choose(next) {
    setView(next);
    storageSet(VIEW_KEY, next);
  }

  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-300">Certificate chain</h3>

        {hasChain && can3D && (
          <div className="flex overflow-hidden rounded-lg ring-1 ring-slate-700" role="group" aria-label="Certificate chain view">
            <button
              type="button"
              onClick={() => choose("3d")}
              aria-pressed={view === "3d"}
              className={`px-3 py-1 text-xs font-semibold transition ${
                view === "3d" ? "bg-sky-600 text-white" : "bg-slate-900 text-slate-400 hover:text-slate-200"
              }`}
            >
              3D
            </button>
            <button
              type="button"
              onClick={() => choose("list")}
              aria-pressed={view === "list"}
              className={`px-3 py-1 text-xs font-semibold transition ${
                view === "list" ? "bg-sky-600 text-white" : "bg-slate-900 text-slate-400 hover:text-slate-200"
              }`}
            >
              List
            </button>
          </div>
        )}
      </div>

      {hasChain && view === "3d" && can3D ? (
        <Suspense
          fallback={
            <div className="flex h-64 items-center justify-center rounded-xl border border-slate-800 bg-slate-900/60 text-sm text-slate-500 md:h-72">
              loading 3D chain…
            </div>
          }
        >
          <CertificateChain3D chain={chain} />
        </Suspense>
      ) : (
        <CertificateChainList chain={chain} />
      )}
    </section>
  );
}
