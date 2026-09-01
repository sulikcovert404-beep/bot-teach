const tg = window.Telegram?.WebApp;
const statusNode = document.querySelector("#status");
const answerNode = document.querySelector("#answer");

function setStatus(text) { statusNode.textContent = text; }

async function authenticate() {
  if (!tg?.initData) throw new Error("این صفحه باید از داخل Telegram باز شود.");
  const response = await fetch("/api/v1/auth/telegram", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ init_data: tg.initData }),
  });
  if (!response.ok) throw new Error("احراز هویت انجام نشد.");
  return (await response.json()).access_token;
}

let accessToken;
document.querySelector("#tutor-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = document.querySelector("#query").value.trim();
  if (!query || !accessToken) return;
  setStatus("در حال دریافت پاسخ مستند…");
  try {
    const response = await fetch("/api/v1/tutor/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify({ query }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "پاسخ دریافت نشد.");
    answerNode.textContent = payload.text;
    answerNode.hidden = false;
    setStatus("پاسخ آماده است.");
  } catch (error) { setStatus(error.message); }
});

(async () => {
  try {
    tg?.ready();
    accessToken = await authenticate();
    setStatus("آمادهٔ پاسخ‌گویی مستند.");
  } catch (error) { setStatus(error.message); }
})();
