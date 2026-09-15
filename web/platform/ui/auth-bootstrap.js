export const AUTH_TOKEN = "AUTH_TOKEN";
let authPromise = null;
export function storedToken() { return sessionStorage.getItem(AUTH_TOKEN); }
export function clearStoredToken() { sessionStorage.removeItem(AUTH_TOKEN); }
export async function ensureTelegramAuth() {
  const existing=storedToken(); if(existing) return {token:existing,role:null,reused:true};
  if (authPromise) return authPromise;
  const tg=window.Telegram?.WebApp; if(!tg?.initData) throw new Error("لطفاً پنل را از طریق ربات تلگرام باز نمایید تا احراز هویت امن انجام شود.");
  tg.ready?.(); tg.expand?.();
  authPromise = (async () => {
    const response=await fetch("/api/v1/auth/telegram",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({init_data:tg.initData})});
    let body=null; try { body=await response.json(); } catch (_) {}
    if(!response.ok || !body?.access_token) { if(response.status===401) throw new Error("احراز هویت تلگرام نامعتبر یا منقضی شده است."); throw new Error(body?.detail||"ارتباط با سرور احراز هویت برقرار نشد."); }
    sessionStorage.setItem(AUTH_TOKEN,body.access_token); return {token:body.access_token,role:body.role||null,reused:false};
  })();
  try { return await authPromise; } finally { authPromise = null; }
}
