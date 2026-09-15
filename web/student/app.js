(() => {
  "use strict";

  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready?.();
    tg.expand?.();
  }

  const $ = (s) => document.querySelector(s);
  const state = { items: [], selected: null };

  const AUTH_TOKEN = "AUTH_TOKEN";
  let authPromise = null;
  const token = () => sessionStorage.getItem(AUTH_TOKEN) || "";
  const setToken = (t) => {
    sessionStorage.setItem(AUTH_TOKEN, t);
  };

  const headers = () =>
    token()
      ? { Authorization: `Bearer ${token()}`, "Content-Type": "application/json" }
      : { "Content-Type": "application/json" };

  async function authenticateTelegram() {
    if (authPromise) return authPromise;
    if (tg?.initData) {
      authPromise = (async () => { try {
        const res = await fetch("/api/v1/auth/telegram", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ init_data: tg.initData }),
        });
        if (res.ok) {
          const data = await res.json();
          if (data.access_token) {
            setToken(data.access_token);
            return true;
          }
        }
      } catch (err) {
        console.warn("Telegram auto-auth failed:", err);
      }
      return false;
      })();
      try { return await authPromise; } finally { authPromise = null; }
    }
    return false;
  }

  async function request(path, options = {}, retried = false) {
    const prefix = path === "/progress" ? "/api/v1/student" : "/api/v1/student/v1";
    const r = await fetch(`${prefix}${path}`, {
      ...options,
      headers: { ...headers(), ...(options.headers || {}) },
    });
    if (!r.ok) {
      if (r.status === 401 && tg?.initData && !retried) {
        sessionStorage.removeItem(AUTH_TOKEN);
        const reauthed = await authenticateTelegram();
        if (reauthed) {
          return request(path, options, true);
        }
      }
      throw Error(
        r.status === 401
          ? "نشست احراز هویت منقضی شده است"
          : r.status === 403
          ? "دسترسی به این بخش مجاز نیست"
          : r.status === 404
          ? "منبع در دسترس نیست"
          : r.status === 409
          ? "مهلت ارسال تکلیف پایان یافته است"
          : "خطا در ارتباط با سرویس"
      );
    }
    return r.json();
  }

  function safe(v) {
    return String(v ?? "—").replace(
      /[&<>"']/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );
  }

  function render() {
    const inbox = $("#inbox");
    inbox.innerHTML = state.items.length
      ? state.items
          .map(
            (a) =>
              `<article class="card" tabindex="0" data-id="${a.id}"><h2>${safe(a.title)}</h2><div class="meta">کلاس ${safe(
                a.classroom_id
              )} · <span class="state">${safe(a.status)}</span></div><div class="meta">مهلت: ${safe(
                a.close_at || a.due_at || "تعیین نشده"
              )}</div></article>`
          )
          .join("")
      : "<div class='panel'>تکلیف فعالی وجود ندارد.</div>";
  }

  async function load() {
    try {
      if (tg?.initData && !token()) {
        await authenticateTelegram();
      }
      state.items = (await request("/assignments")).assignments || [];
      $("#status").textContent = "آماده";
      $("#status").className = "badge ready";
      $("#notice").textContent = "";
      render();
    } catch (e) {
      $("#status").textContent = "آماده (حالت کلاینت)";
      $("#status").className = "badge ready";
      $("#notice").innerHTML = "";
      render();
    }
  }

  async function open(id) {
    try {
      const d = await request(`/assignments/${id}`);
      state.selected = d.assignment;
      $("#detail").hidden = false;
      $("#detail").innerHTML = `<h2>${safe(d.assignment.title)}</h2><p>${safe(
        d.assignment.instructions
      )}</p><p class="meta">وضعیت: ${safe(
        d.assignment.status
      )}</p><textarea id="answer" aria-label="پاسخ تکلیف" placeholder="پاسخ خود را بنویسید…"></textarea><br><button id="submit">ثبت پاسخ</button><div id="result" aria-live="polite"></div>`;
      $("#submit").onclick = async () => {
        const r = $("#result");
        try {
          const out = await request(`/assignments/${id}/submissions`, {
            method: "POST",
            body: JSON.stringify({ content: { answer: $("#answer").value } }),
          });
          r.textContent = `پاسخ ثبت شد؛ ویرایش شماره ${out.revision}`;
          r.className = "meta";
        } catch (e) {
          r.textContent = e.message;
          r.className = "error";
        }
      };
    } catch (e) {
      $("#notice").innerHTML = `<div class="error">${safe(e.message)}</div>`;
    }
  }

  $("#inbox").onclick = (e) => {
    const c = e.target.closest("[data-id]");
    if (c) open(c.dataset.id);
  };
  $("#refresh").onclick = load;

  $("#progressBtn").onclick = async () => {
    const p = $("#progress");
    p.hidden = false;
    p.textContent = "در حال بارگذاری…";
    try {
      const d = await request("/progress");
      p.innerHTML = `<h2>پیشرفت من</h2><pre style="direction:ltr;text-align:left;background:#f1f5f9;padding:12px;border-radius:8px;">${safe(
        JSON.stringify(d, null, 2)
      )}</pre>`;
    } catch (e) {
      p.innerHTML = `<div class="error">${safe(e.message)}</div>`;
    }
  };

  $("#contentBtn").onclick = async () => {
    const box = $("#content");
    box.hidden = false;
    box.textContent = "در حال بارگذاری محتوای کلاس…";
    try {
      const d = await request("/v2/classroom-content");
      const items = d.items || [];
      box.innerHTML = items.length
        ? `<h2>محتوای کلاس</h2>` +
          items.map((x) => `<p>📌 <strong>${safe(x.title || x.lesson_title || "محتوای آموزشی")}</strong></p>`).join("")
        : '<div class="empty">محتوای منتشرشده‌ای وجود ندارد.</div>';
    } catch (e) {
      box.innerHTML = `<div class="error">${safe(e.message)}</div>`;
    }
  };

  load();
})();
