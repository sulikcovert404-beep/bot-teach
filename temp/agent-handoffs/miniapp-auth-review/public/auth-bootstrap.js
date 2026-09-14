const TOKEN_KEYS = ["accessToken", "studentToken", "teacherToken"];
export function storedToken() { for (const key of TOKEN_KEYS) { const value=sessionStorage.getItem(key); if(value) return value; } return null; }
export async function ensureTelegramAuth() {
  const existing=storedToken(); if(existing) return {token:existing,role:null,reused:true};
  const tg=window.Telegram?.WebApp; if(!tg?.initData) throw new Error("لطفاً پنل را از طریق ربات تلگرام باز نمایید تا احراز هویت امن انجام شود.");
  tg.ready?.(); tg.expand?.();
  const response=await fetch("/api/v1/auth/telegram",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({init_data:tg.initData})});
  let body=null; try { body=await response.json(); } catch (_) {}
  if(!response.ok || !body?.access_token) { if(response.status===401) throw new Error("احراز هویت تلگرام نامعتبر یا منقضی شده است."); throw new Error(body?.detail||"ارتباط با سرور احراز هویت برقرار نشد."); }
  sessionStorage.setItem("accessToken",body.access_token); return {token:body.access_token,role:body.role||null,reused:false};
}
