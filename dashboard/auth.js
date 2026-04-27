/**
 * AgentLens — API key auth for dashboard pages.
 * Reads key from localStorage or URL param, injects into all fetch() calls.
 */
(function () {
  const STORAGE_KEY = "agentlens_api_key";

  // 1. Pick up key from URL param on first visit
  const urlKey = new URLSearchParams(window.location.search).get("api_key");
  if (urlKey) {
    localStorage.setItem(STORAGE_KEY, urlKey);
    // Clean key from URL without reload
    const url = new URL(window.location.href);
    url.searchParams.delete("api_key");
    window.history.replaceState({}, "", url.toString());
  }

  function getKey() {
    return localStorage.getItem(STORAGE_KEY);
  }

  // 2. Show prompt if no key stored
  function showKeyPrompt() {
    const overlay = document.createElement("div");
    overlay.id = "al-auth-overlay";
    overlay.style.cssText =
      "position:fixed;inset:0;background:rgba(0,0,0,0.85);display:flex;align-items:center;justify-content:center;z-index:9999;font-family:system-ui,sans-serif";
    overlay.innerHTML = `
      <div style="background:#1e1e2e;border:1px solid #3b3b52;border-radius:12px;padding:36px;max-width:420px;width:90%;text-align:center">
        <div style="font-size:28px;margin-bottom:8px">🔍</div>
        <h2 style="color:#e2e2f0;margin:0 0 8px;font-size:20px">AgentLens</h2>
        <p style="color:#8888aa;margin:0 0 24px;font-size:14px">Enter your API key to access your dashboard</p>
        <input id="al-key-input" type="text" placeholder="al_xxxxxxxxxxxxxxxxxxxxxxxx"
          style="width:100%;box-sizing:border-box;padding:10px 14px;border-radius:8px;border:1px solid #3b3b52;background:#13131f;color:#e2e2f0;font-size:14px;margin-bottom:16px;outline:none" />
        <button id="al-key-submit"
          style="width:100%;padding:10px;border-radius:8px;border:none;background:#6366f1;color:#fff;font-size:14px;font-weight:600;cursor:pointer">
          Access Dashboard
        </button>
        <p id="al-key-error" style="color:#f87171;font-size:13px;margin:12px 0 0;display:none">Invalid key — try again</p>
      </div>`;
    document.body.appendChild(overlay);

    document.getElementById("al-key-submit").addEventListener("click", async () => {
      const val = document.getElementById("al-key-input").value.trim();
      if (!val) return;
      // Quick validation: try a cheap API call
      try {
        const res = await window._origFetch("/requests/stats?api_key=" + encodeURIComponent(val));
        if (res.status === 403 || res.status === 401) {
          document.getElementById("al-key-error").style.display = "block";
          return;
        }
        localStorage.setItem(STORAGE_KEY, val);
        overlay.remove();
        window.location.reload();
      } catch {
        document.getElementById("al-key-error").style.display = "block";
      }
    });

    document.getElementById("al-key-input").addEventListener("keydown", (e) => {
      if (e.key === "Enter") document.getElementById("al-key-submit").click();
    });
  }

  // 3. Override fetch() to inject X-API-Key header on same-origin API calls
  window._origFetch = window.fetch.bind(window);
  window.fetch = function (input, init = {}) {
    const url = typeof input === "string" ? input : input.url;
    const isSameOrigin = !url.startsWith("http") || url.startsWith(window.location.origin);
    const isApiCall = isSameOrigin && !url.includes(".html") && !url.includes(".js") && !url.includes(".css");

    if (isApiCall) {
      const key = getKey();
      if (key) {
        init.headers = { ...(init.headers || {}), "X-API-Key": key };
      }
    }
    return window._origFetch(input, init);
  };

  // 4. On DOM ready — show prompt if no key
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => { if (!getKey()) showKeyPrompt(); });
  } else {
    if (!getKey()) showKeyPrompt();
  }

  // 5. Expose logout helper
  window.agentlensLogout = function () {
    localStorage.removeItem(STORAGE_KEY);
    window.location.reload();
  };
})();
