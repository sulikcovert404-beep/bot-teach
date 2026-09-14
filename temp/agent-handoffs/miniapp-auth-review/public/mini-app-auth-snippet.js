// Sanitized auth-relevant excerpt from web/mini-app/app.js
const tg = window.Telegram?.WebApp;
let accessToken = sessionStorage.getItem("accessToken") || null;
function setToken(token) {
  accessToken = token || null;
  if (accessToken) sessionStorage.setItem("accessToken", accessToken);
  else sessionStorage.removeItem("accessToken");
}
async function authenticate() {
  if (accessToken) return accessToken;
  if (!tg?.initData) throw new Error("Telegram WebApp initData unavailable");
  tg.ready?.(); tg.expand?.();
  const response = await fetch("/api/v1/auth/telegram", {
    method: "POST", headers: {"Content-Type":"application/json"},
    body: JSON.stringify({init_data: tg.initData})
  });
  if (!response.ok) throw new Error(`auth failed: ${response.status}`);
  const body = await response.json();
  if (!body?.access_token) throw new Error("auth response missing token");
  setToken(body.access_token); return accessToken;
}
// Review the surrounding bootstrap, 401 handling, retry bounds, and route selection.

