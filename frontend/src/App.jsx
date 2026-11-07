// HackMatrix dashboard shell: header with nav, page switch, footer.
// Routes: / (scan), /demo (one-click URLs), /community (GET /reports).
import { apiConfig } from "./api.js";
import { Link, useRoute } from "./router.jsx";
import Home from "./pages/Home.jsx";
import Demo from "./pages/Demo.jsx";
import Community from "./pages/Community.jsx";

const { apiBase, useMock } = apiConfig();

const NAV = [
  { to: "/", label: "Scan" },
  { to: "/demo", label: "Demo" },
  { to: "/community", label: "Community" },
];

export default function App() {
  const route = useRoute();
  const isActive = (to) => (to === "/" ? route === "/" : route.startsWith(to));

  let page = <Home />;
  if (route.startsWith("/demo")) page = <Demo />;
  else if (route.startsWith("/community")) page = <Community />;

  return (
    <div className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-4 py-6 md:py-8">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-baseline gap-3">
          <h1 className="text-2xl font-bold tracking-tight">
            Hack<span className="text-sky-400">Matrix</span>
          </h1>
          <span className="hidden text-sm text-slate-400 sm:inline">URL trust dashboard</span>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
              useMock
                ? "bg-violet-500/15 text-violet-300 ring-violet-500/30"
                : "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30"
            }`}
            title={apiBase}
          >
            {useMock ? "mock mode" : `API · ${apiBase}`}
          </span>
          <nav className="flex gap-1 rounded-lg bg-slate-900 p-1 ring-1 ring-slate-800">
            {NAV.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
                  isActive(item.to) ? "bg-sky-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>

      {page}

      <footer className="mt-auto pt-2 text-center text-[11px] text-slate-600">
        Engines are passive (HTTP/DNS/TLS only) · page content is untrusted data · the dashboard sends
        only the URL
      </footer>
    </div>
  );
}
