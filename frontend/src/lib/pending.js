// One-click demo flow: the demo page stores a request and the home page
// picks it up on arrival. sessionStorage survives the route change.
export const PENDING_SCAN_KEY = "hackmatrix_pending_scan";

export function setPendingScan(url) {
  try {
    sessionStorage.setItem(PENDING_SCAN_KEY, url);
  } catch {
    // storage disabled: user can still paste the URL manually
  }
}

/** Returns the pending URL and clears it. */
export function takePendingScan() {
  try {
    const url = sessionStorage.getItem(PENDING_SCAN_KEY);
    if (url) sessionStorage.removeItem(PENDING_SCAN_KEY);
    return url;
  } catch {
    return null;
  }
}
