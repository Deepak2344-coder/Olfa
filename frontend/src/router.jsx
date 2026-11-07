// Minimal history-API router — ~30 lines instead of pulling in react-router.
// Works with Vite dev server and `vite preview` (both do SPA fallback).
import { useEffect, useState } from "react";

const listeners = new Set();

/**
 * Navigate to a path and notify every mounted useRoute().
 * @param {string} path
 */
export function navigate(path) {
  try {
    window.history.pushState({}, "", path);
  } catch {
    // e.g. sandboxed iframe: fall back to a hard navigation via the <a> click
  }
  listeners.forEach((fn) => fn(path));
}

/** Subscribe to the current pathname. */
export function useRoute() {
  const [path, setPath] = useState(() => window.location.pathname);
  useEffect(() => {
    const update = () => setPath(window.location.pathname);
    listeners.add(update);
    window.addEventListener("popstate", update);
    return () => {
      listeners.delete(update);
      window.removeEventListener("popstate", update);
    };
  }, []);
  return path;
}

/**
 * <a> that uses the router for plain left-clicks and keeps
 * ctrl/cmd/shift-clicks (new tab / window) native.
 */
export function Link({ to, className = "", children, ...rest }) {
  return (
    <a
      href={to}
      onClick={(e) => {
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        e.preventDefault();
        navigate(to);
      }}
      className={className}
      {...rest}
    >
      {children}
    </a>
  );
}
