const tg = window.Telegram?.WebApp;
const statusNode = document.querySelector("#status");
const answerCard = document.querySelector("#answer");
const answerContent = document.querySelector("#answer-content");
const modelTag = document.querySelector("#model-tag");
const citationsCard = document.querySelector("#citations-card");
const citationsList = document.querySelector("#citations-list");
const form = document.querySelector("#tutor-form");
const submitButton = document.querySelector("#submit-btn");
const btnText = submitButton.querySelector(".btn-text");
const btnSpinner = submitButton.querySelector(".btn-spinner");
const queryInput = document.querySelector("#query");
const compactFeedback = document.querySelector("#compact-feedback");

let isRequestInProgress = false;
let accessToken = sessionStorage.getItem("accessToken") || null;
function setAccessToken(token) {
  accessToken = token || null;
  if (accessToken) sessionStorage.setItem("accessToken", accessToken);
  else sessionStorage.removeItem("accessToken");
}
function clearAccessToken() { setAccessToken(null); }

// Workspace-only diagnostics: coarse lifecycle events, never user or payload data.
const DIAGNOSTIC_BUILD_ID = "mini-app-20260912-01";
const diagnosticEvents = [];
function recordDiagnostic(state, errorType = null, component = null) {
  const event = { state, build_id: DIAGNOSTIC_BUILD_ID, timestamp: new Date().toISOString() };
  if (errorType) event.error_type = String(errorType).slice(0, 80);
  if (component) event.component = component;
  diagnosticEvents.push(event);
  if (diagnosticEvents.length > 30) diagnosticEvents.shift();
  window.__miniAppDiagnostics = { build_id: DIAGNOSTIC_BUILD_ID, events: diagnosticEvents.slice() };
}
recordDiagnostic("LOAD");

let diagnosticTapCount = 0;
let diagnosticTapReset = null;
const diagnosticPanel = document.querySelector("#diagnostic-readout");
const diagnosticContent = document.querySelector("#diagnostic-readout-content");
const diagnosticCopyButton = document.querySelector("#copy-diagnostics-btn");
const diagnosticCopyStatus = document.querySelector("#diagnostic-copy-status");
const appTitle = document.querySelector(".header-titles h1");

function refreshDiagnosticReadout() {
  if (diagnosticContent) diagnosticContent.textContent = JSON.stringify(window.__miniAppDiagnostics || {}, null, 2);
}

function openDiagnosticReadout() {
  refreshDiagnosticReadout();
  if (diagnosticPanel) diagnosticPanel.hidden = false;
}

appTitle?.addEventListener("click", () => {
  diagnosticTapCount += 1;
  clearTimeout(diagnosticTapReset);
  diagnosticTapReset = setTimeout(() => { diagnosticTapCount = 0; }, 1800);
  if (diagnosticTapCount >= 5) {
    diagnosticTapCount = 0;
    openDiagnosticReadout();
  }
});

diagnosticCopyButton?.addEventListener("click", async () => {
  refreshDiagnosticReadout();
  try {
    await navigator.clipboard.writeText(diagnosticContent?.textContent || "{}");
    if (diagnosticCopyStatus) {
      diagnosticCopyStatus.hidden = false;
      setTimeout(() => { diagnosticCopyStatus.hidden = true; }, 1500);
    }
  } catch {
    if (diagnosticCopyStatus) diagnosticCopyStatus.textContent = "Copy unavailable";
  }
});

// Subject Title mapping for clean educational UX
const SOURCE_TITLE_MAP = {
  "physics10-work-energy": "فیزیک دهم — فصل ۳: کار، توان و انرژی جنبشی",
  "physics-grade10-newton": "فیزیک دهم — فصل ۲: قوانین حرکت نیوتون",
  "biology10-cell-membrane": "زیست‌شناسی دهم — فصل ۱: غشای یاخته و انتقال فعال",
  "biology-grade10-photosynthesis": "زیست‌شناسی دهم — فصل ۵: فتوسنتز و تولید انرژی",
  "math-foundation-quadratic": "ریاضیات پایه دهم — معادله درجه دوم و بررسی دلتا (Δ)",
  "history11-iran-contemporary": "تاریخ یازدهم معاصر — فصل تحولات ایران در دوره معاصر و پهلوی",
  "sociology12-humanities": "جامعه‌شناسی دوازدهم علوم انسانی — جهان‌های اجتماعی و هویت فرهنگی",
};

function setStatus(text, type = "normal") {
  statusNode.textContent = text;
  statusNode.className = "status-badge " + (type || "");
}

function configureTelegramNavigation() {
  if (!tg) return;
  tg.ready?.();
  tg.expand?.();
  tg.BackButton?.onClick?.(() => {
    const active = document.querySelector(".nav-tab.active");
    if (active && active !== tabTutorBtn) tabTutorBtn?.click();
    else tg.close?.();
  });
  tg.BackButton?.show?.();
  tg.MainButton?.setText?.("پرسش از مدرس");
  tg.MainButton?.onClick?.(() => queryInput?.focus());
  tg.MainButton?.show?.();
}

function setViewState(container, state, message) {
  if (!container) return;
  container.dataset.state = state;
  let node = container.querySelector(".view-state-message");
  if (!node) {
    node = document.createElement("div");
    node.className = "view-state-message";
    container.prepend(node);
  }
  node.textContent = message;
  node.hidden = state === "ready";
  node.className = `view-state-message ${state}`;
}

// Support chip quick selection
document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    queryInput.value = chip.getAttribute("data-q");
    queryInput.focus();
  });
});

async function authenticate() {
  if (!tg?.initData) {
    // If opened directly outside Telegram for browser preview, inform clearly
    throw new Error("لطفاً برنامه را از طریق ربات تلگرام باز نمایید تا احراز هویت امن انجام شود.");
  }
  const response = await fetch("/api/v1/auth/telegram", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ init_data: tg.initData }),
  });
  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("احراز هویت تلگرام نامعتبر یا منقضی شده است.");
    }
    throw new Error("ارتباط با سرور احراز هویت برقرار نشد.");
  }
  const authPayload = await response.json();
  recordDiagnostic("AUTH_READY");
  return authPayload;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (!query || isRequestInProgress) return;

  if (!accessToken) {
    setStatus("ابتدا باید احراز هویت تلگرام تکمیل شود.", "error");
    return;
  }

  lastQuerySubmitted = query;

  recordDiagnostic("REQUEST_SENT");

  isRequestInProgress = true;
  submitButton.disabled = true;
  btnText.textContent = "در حال تحلیل و استخراج منبع…";
  btnSpinner.hidden = false;
  answerCard.hidden = true;
  citationsCard.hidden = true;
  compactFeedback.hidden = true;
  setStatus("در حال استخراج مستندات و فرمول‌ها…", "loading");

  try {
    const response = await fetch("/api/v1/tutor/answer", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ query }),
    });

    let payload = {};
    try {
      payload = await response.json();
    } catch {
      /* parse error guard */
    }

    if (!response.ok) {
      const msg = payload.detail || "خطایی در پردازش پاسخ آموزشی رخ داد.";
      throw new Error(msg);
    }

    recordDiagnostic("RESPONSE_RECEIVED");
    renderAnswer(payload);
    compactFeedback.hidden = false;
    setStatus("پاسخ مستند آموزشی با موفقیت رندر شد ✅", "success");
  } catch (error) {
    recordDiagnostic("RENDER_FAILED", error?.name || "Error", "tutor-submit");
    const message = error instanceof Error ? error.message : "خطای ارتباط با سامانه.";
    const isSourceGuard = /منبع|مستند|Source Guard/i.test(message);
    compactFeedback.hidden = !isSourceGuard;
    setStatus("خطا: " + message, "error");
  } finally {
    submitButton.disabled = false;
    btnText.textContent = "پرسش از مدرس هوشمند";
    btnSpinner.hidden = true;
    isRequestInProgress = false;
  }
});

function renderAnswer(payload) {
  recordDiagnostic("RENDER_STARTED");
  let rawText = payload.text || "";
  modelTag.textContent = payload.model || "Gemini";

  // Extract citations like [physics10-work-energy] or [biology-grade10-photosynthesis]
  const citationRegex = /\[([a-zA-Z0-9_\-]+)\]/g;
  const foundSources = new Set();
  let match;
  while ((match = citationRegex.exec(rawText)) !== null) {
    foundSources.add(match[1]);
  }

  // Replace citations in text with friendly inline pill badges
  let processedText = rawText.replace(citationRegex, (full, id) => {
    const friendly = SOURCE_TITLE_MAP[id] || id;
    return ` <span class="citation-badge" title="${escapeHtml(id)}">📖 ${escapeHtml(friendly)}</span> `;
  });

  // Convert markdown-like paragraphs and line breaks
  const paragraphs = processedText.split(/\n\s*\n/);
  const formattedHtml = paragraphs
    .map((p) => `<p>${escapeHtmlWithMath(p)}</p>`)
    .join("");

  answerContent.innerHTML = formattedHtml;
  answerCard.hidden = false;

  // Render separate Distinct Citations Card
  if (foundSources.size > 0) {
    citationsList.innerHTML = "";
    foundSources.forEach((srcId) => {
      const title = SOURCE_TITLE_MAP[srcId] || srcId;
      const item = document.createElement("div");
      item.className = "citation-item";
      item.innerHTML = `<span class="citation-badge">منبع رسمی</span> <strong>${escapeHtml(title)}</strong>`;
      citationsList.appendChild(item);
    });
    citationsCard.hidden = false;
  } else {
    citationsCard.hidden = true;
  }

  // Render LaTeX math formulas via KaTeX if available
  if (window.renderMathInElement) {
    window.renderMathInElement(answerContent, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
        { left: "\\[", right: "\\]", display: true },
        { left: "\\(", right: "\\)", display: false },
      ],
      throwOnError: false,
    });
  }
  recordDiagnostic("RENDER_COMPLETED");
}

function escapeHtmlWithMath(str) {
  // Preserve $...$ and $$...$$ while escaping bare HTML
  const parts = str.split(/(\$\$[\s\S]*?\$\$|\$[^\$\n]+?\$)/g);
  return parts
    .map((part) => {
      if (part.startsWith("$") && part.endsWith("$")) {
        return part; // keep math intact for KaTeX
      }
      return escapeHtml(part).replace(/\n/g, "<br/>");
    })
    .join("");
}

function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

let lastQuerySubmitted = "";
let feedbackSubmissionInProgress = false;
let feedbackSubmittedForQuery = null;

document.querySelectorAll(".btn-feedback").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const feedbackQuery = lastQuerySubmitted || queryInput.value.trim() || "عمومی";
    if (feedbackSubmissionInProgress || feedbackSubmittedForQuery === feedbackQuery) return;
    const val = parseInt(btn.getAttribute("data-val") || "5", 10);
    const feedbackStatus = document.querySelector("#feedback-status");
    feedbackSubmissionInProgress = true;
    try {
      const response = await fetch("/api/v1/tutor/feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          query: feedbackQuery,
          rating: val,
          feedback_type: val >= 4 ? "answer_quality" : "missing_content",
          comment: `امتیاز ${val} ثبت شده از مینی‌اپ`,
        }),
      });
      if (!response.ok) {
        throw new Error(`Feedback request failed (${response.status})`);
      }
      feedbackSubmittedForQuery = feedbackQuery;
      if (feedbackStatus) {
        feedbackStatus.hidden = false;
      }
    } catch {
      if (feedbackStatus) {
        feedbackStatus.hidden = false;
        feedbackStatus.textContent = "ثبت بازخورد انجام نشد؛ دوباره تلاش کنید.";
        feedbackStatus.classList.add("error");
      }
    } finally {
      feedbackSubmissionInProgress = false;
    }
  });
});

// Navigation Tabs
const tabTutorBtn = document.querySelector("#tab-tutor-btn");
const tabStudentBtn = document.querySelector("#tab-student-btn");
const tabExamBtn = document.querySelector("#tab-exam-btn");
const tabPlansBtn = document.querySelector("#tab-plans-btn");
const tabGrowthBtn = document.querySelector("#tab-growth-btn");
const tutorView = document.querySelector("#tutor-view");
const studentView = document.querySelector("#student-view");
const examView = document.querySelector("#exam-view");
const plansView = document.querySelector("#plans-view");
const growthView = document.querySelector("#growth-view");

function resetTabs() {
  [tabTutorBtn, tabStudentBtn, tabExamBtn, tabPlansBtn, tabGrowthBtn].forEach(b => {
    if (b) {
      b.style.background = "var(--card-bg)";
      b.style.color = "var(--text)";
      b.classList.remove("active");
    }
  });
  if (tutorView) tutorView.hidden = true;
  if (studentView) studentView.hidden = true;
  if (examView) examView.hidden = true;
  if (plansView) plansView.hidden = true;
  if (growthView) growthView.hidden = true;
}

function switchTab(tabName) {
  resetTabs();
  if (tabName === "tutor" && tabTutorBtn && tutorView) {
    tabTutorBtn.style.background = "var(--primary)";
    tabTutorBtn.style.color = "#fff";
    tabTutorBtn.classList.add("active");
    tutorView.hidden = false;
  } else if (tabName === "student" && tabStudentBtn && studentView) {
    tabStudentBtn.style.background = "var(--primary)";
    tabStudentBtn.style.color = "#fff";
    tabStudentBtn.classList.add("active");
    studentView.hidden = false;
    loadStudentDashboard();
  } else if (tabName === "exam" && tabExamBtn && examView) {
    tabExamBtn.style.background = "var(--primary)";
    tabExamBtn.style.color = "#fff";
    tabExamBtn.classList.add("active");
    examView.hidden = false;
    loadExamQuestions();
  } else if (tabName === "plans" && tabPlansBtn && plansView) {
    tabPlansBtn.style.background = "var(--primary)";
    tabPlansBtn.style.color = "#fff";
    tabPlansBtn.classList.add("active");
    plansView.hidden = false;
    loadPlanCatalog();
  } else if (tabName === "growth" && tabGrowthBtn && growthView) {
    tabGrowthBtn.style.background = "var(--primary)";
    tabGrowthBtn.style.color = "#fff";
    tabGrowthBtn.classList.add("active");
    growthView.hidden = false;
    loadGrowthData();
  }
}

if (tabTutorBtn && tabStudentBtn && tabExamBtn && tabPlansBtn) {
  tabTutorBtn.addEventListener("click", () => switchTab("tutor"));
  tabStudentBtn.addEventListener("click", () => switchTab("student"));
  tabExamBtn.addEventListener("click", () => switchTab("exam"));
  tabPlansBtn.addEventListener("click", () => switchTab("plans"));
  if (tabGrowthBtn) {
    tabGrowthBtn.addEventListener("click", () => switchTab("growth"));
  }
}

function resolveInitialTab() {
  // Check URL query parameters or hash or tg.initDataUnsafe.start_param
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("tab") || params.get("view") || window.location.hash.replace("#", "") || tg?.initDataUnsafe?.start_param;
  if (!requested) return "student";
  const norm = requested.toLowerCase().trim();
  if (norm === "tutor" || norm === "ask" || norm === "class") return "tutor";
  if (norm === "exam" || norm === "quiz") return "exam";
  if (norm === "plans" || norm === "upgrade") return "plans";
  if (norm === "growth" || norm === "invite") return "growth";
  return "student";
}

let currentUserRole = "STUDENT";

(async () => {
  try {
    configureTelegramNavigation();
    setStatus("در حال احراز هویت تلگرام…", "loading");
    const authData = await authenticate();
    setAccessToken(authData.access_token);
    currentUserRole = (authData.role || "STUDENT").toUpperCase();

    // Role-based routing: redirect users to their dedicated dashboard
    if (currentUserRole === "TEACHER") {
      setStatus("هدایت به پنل معلمان…", "success");
      window.location.replace("/teacher-dashboard/");
      return;
    }
    if (currentUserRole === "SCHOOL_ADMIN") {
      setStatus("هدایت به پنل مدیریت مدرسه…", "success");
      window.location.replace("/admin-dashboard/");
      return;
    }
    if (currentUserRole === "SUPER_ADMIN") {
      setStatus("هدایت به داشبورد پلتفرم…", "success");
      window.location.replace("/platform/");
      return;
    }
    if (currentUserRole === "STUDENT") {
      const params = new URLSearchParams(window.location.search);
      const hasDirectTool = params.has("tab") || params.has("view") || window.location.hash;
      if (!hasDirectTool) {
        setStatus("هدایت به داشبورد دانش‌آموز…", "success");
        window.location.replace("/student-dashboard/");
        return;
      }
    }

    setStatus("سامانه آماده پاسخ‌گویی آموزشی است", "success");
    const initialTab = resolveInitialTab();
    switchTab(initialTab);
  } catch (error) {
    configureTelegramNavigation();
    const isNoTelegram = !tg?.initData;
    setStatus(error.message, "error");
    if (isNoTelegram) {
      setViewState(document.querySelector("#student-view") || document.querySelector("#tutor-view"), "error", error.message);
    } else {
      setViewState(document.querySelector("#student-view") || document.querySelector("#tutor-view"), "auth-expired", "احراز هویت تلگرام منقضی یا نامعتبر است؛ لطفاً مینی‌اپ را دوباره از داخل ربات باز کنید.");
    }
  }
})();

async function loadGrowthData() {
  if (!accessToken) return;
  try {
    const res = await fetch("/api/v1/growth/referral", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (res.ok) {
      const data = await res.json();
      const codeNode = document.querySelector("#referral-code-display");
      const invitesNode = document.querySelector("#ref-invites-count");
      const pointsNode = document.querySelector("#ref-points-count");
      if (codeNode) codeNode.textContent = data.referral_code;
      if (invitesNode) invitesNode.textContent = `${data.successful_invites_count} نفر`;
      if (pointsNode) pointsNode.textContent = `${data.growth_points_earned} XP`;
    }
  } catch (err) {
    console.error("Failed to load growth data:", err);
  }
}


async function loadPlanCatalog() {
  const container = document.querySelector("#plans-catalog-list");
  if (!container || !accessToken) return;
  try {
    const res = await fetch("/api/v1/subscription/catalog", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (res.ok) {
      const data = await res.json();
      container.innerHTML = data.plans.map(p => `
        <div style="border: 1px solid ${p.badge ? '#f59e0b' : '#e2e8f0'}; border-radius: 10px; padding: 12px; background: ${p.badge ? 'rgba(245,158,11,0.03)' : '#fff'};">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 700; font-size: 0.95rem;">${p.title}</span>
            <span style="font-size: 0.85rem; font-weight: 800; color: #2563eb;">${p.price_toman.toLocaleString()} تومان / ماه</span>
          </div>
          <ul style="margin: 8px 0; padding-right: 18px; font-size: 0.8rem; color: var(--text-muted);">
            ${p.features.map(f => `<li>${f}</li>`).join("")}
          </ul>
          ${p.plan_code !== 'FREE' ? `
            <button type="button" class="btn-upgrade-plan" data-plan="${p.plan_code}" style="width: 100%; padding: 8px; border-radius: 6px; border: none; background: #059669; color: #fff; font-weight: 700; cursor: pointer;">
              ارتقا به این طرح (شبیه‌ساز تستی)
            </button>
          ` : '<span style="font-size: 0.75rem; color: #16a34a; font-weight: bold;">طرح پیش‌فرض فعال ✅</span>'}
        </div>
      `).join("");

      document.querySelectorAll(".btn-upgrade-plan").forEach(btn => {
        btn.addEventListener("click", async () => {
          const plan = btn.getAttribute("data-plan");
          const msg = document.querySelector("#upgrade-status-msg");
          try {
            const subRes = await fetch("/api/v1/subscription/sandbox-subscribe", {
              method: "POST",
              headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
              body: JSON.stringify({ plan, duration_days: 30 }),
            });
            if (subRes.ok) {
              const r = await subRes.json();
              msg.textContent = `${r.message} ✅`;
              msg.hidden = false;
              setTimeout(() => (msg.hidden = true), 4000);
            }
          } catch (e) {
            console.error(e);
          }
        });
      });
    }
  } catch (err) {
    console.error("Failed to load catalog:", err);
  }
}

let activeExamQuestions = [];

async function loadExamQuestions() {
  const container = document.querySelector("#exam-questions-list");
  if (!container || !accessToken) return;
  try {
    const res = await fetch("/api/v1/exams/bank", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (res.ok) {
      const data = await res.json();
      activeExamQuestions = data.questions || [];
      container.innerHTML = activeExamQuestions.map((q, idx) => `
        <div style="background: rgba(0,0,0,0.02); border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;">
          <div style="font-weight: 600; font-size: 0.95rem; margin-bottom: 8px;">سوال ${idx + 1}: ${q.prompt}</div>
          <div style="display: flex; flex-direction: column; gap: 6px;">
            ${q.options.map(opt => `
              <label style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem; cursor: pointer;">
                <input type="radio" name="q_${q.id}" value="${opt}" />
                <span>${opt}</span>
              </label>
            `).join("")}
          </div>
        </div>
      `).join("");
    }
  } catch (err) {
    console.error("Failed to load questions:", err);
  }
}

const submitExamBtn = document.querySelector("#submit-exam-btn");
if (submitExamBtn) {
  submitExamBtn.addEventListener("click", () => {
    const reportCard = document.querySelector("#exam-report-card");
    const summary = document.querySelector("#exam-report-summary");
    const details = document.querySelector("#exam-report-details");
    
    let correct = 0;
    const total = activeExamQuestions.length;
    const results = [];

    activeExamQuestions.forEach(q => {
      const selected = document.querySelector(`input[name="q_${q.id}"]:checked`)?.value;
      const isCorrect = selected === q.correct_option;
      if (isCorrect) correct++;
      results.push({ prompt: q.prompt, selected, correct: q.correct_option, isCorrect });
    });

    const scorePct = total > 0 ? Math.round((correct / total) * 100) : 0;

    summary.innerHTML = `<strong>نمره کل شما: ${scorePct}٪ (${correct} از ${total} صحیح)</strong> — ${scorePct >= 70 ? 'قبولی با تسلط عالی ✅' : 'نیاز به مرور مباحث ⚠️'}`;
    details.innerHTML = results.map(r => `
      <div style="padding: 6px; border-radius: 6px; background: ${r.isCorrect ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)'};">
        <div>${r.prompt}</div>
        <div style="font-size: 0.75rem; color: ${r.isCorrect ? '#059669' : '#dc2626'};">
          پاسخ شما: ${r.selected || 'بدون پاسخ'} | پاسخ صحیح: ${r.correct}
        </div>
      </div>
    `).join("");

    reportCard.hidden = false;
  });
}

async function loadStudentDashboard() {
  const view = document.querySelector("#student-view");
  if (!accessToken) {
    setViewState(view, "auth-expired", "برای مشاهده پیشرفت، احراز هویت تلگرام لازم است.");
    return;
  }
  setViewState(view, "loading", "در حال بارگذاری وضعیت یادگیری…");
  try {
    const rProg = await fetch("/api/v1/student/progress", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (rProg.ok) {
      const prog = await rProg.json();
      renderMastery(prog.subject_mastery);
      renderRecommendations(prog.smart_recommendations);
    }

    const rProf = await fetch("/api/v1/student/profile", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (rProf.ok) {
      const prof = await rProf.json();
      const ap = prof.academic_profile;
      document.querySelector("#prof-grade").value = ap.grade || "دهم";
      document.querySelector("#prof-field").value = ap.field_of_study || "علوم تجربی";
      document.querySelector("#prof-level").value = ap.target_level || "متوسط";
      document.querySelector("#profile-badge").textContent = `${ap.grade} - ${ap.field_of_study}`;
    }

    // Load Gamification (Streak & Badges)
    const rStreak = await fetch("/api/v1/student/engagement/streak", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (rStreak.ok) {
      const st = await rStreak.json();
      document.querySelector("#streak-badge-text").textContent = st.streak_status;
      document.querySelector("#streak-quote-text").textContent = st.motivational_quote;
    }

    const rBadges = await fetch("/api/v1/student/engagement/badges", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (rBadges.ok) {
      const bd = await rBadges.json();
      document.querySelector("#user-xp-text").textContent = `${bd.total_xp} XP`;
      const badgesContainer = document.querySelector("#badges-container");
      if (badgesContainer && bd.badges) {
        badgesContainer.innerHTML = bd.badges.map(b => `
          <div style="min-width: 90px; text-align: center; padding: 8px 6px; border-radius: 8px; border: 1px solid ${b.unlocked ? '#10b981' : '#cbd5e1'}; background: ${b.unlocked ? 'rgba(16,185,129,0.08)' : '#f8fafc'}; opacity: ${b.unlocked ? '1' : '0.5'};">
            <div style="font-size: 1.5rem;">${b.icon}</div>
            <div style="font-size: 0.75rem; font-weight: 700; margin-top: 4px;">${b.title}</div>
          </div>
        `).join("");
      }
    }
    setViewState(view, "ready", "");
  } catch (err) {
    console.error("Failed to load dashboard:", err);
    setViewState(view, "error", "دریافت وضعیت یادگیری انجام نشد.");
    const retry = document.createElement("button");
    retry.type = "button";
    retry.textContent = "تلاش دوباره";
    retry.className = "view-retry";
    retry.addEventListener("click", () => loadStudentDashboard());
    view?.querySelector(".view-state-message")?.appendChild(retry);
  }
}

function renderMastery(mastery) {
  const container = document.querySelector("#mastery-list");
  if (!container || !mastery) return;
  container.innerHTML = Object.entries(mastery)
    .map(([subj, data]) => `
      <div style="display: flex; flex-direction: column; gap: 4px; padding: 6px 0; border-bottom: 1px solid rgba(0,0,0,0.05);">
        <div style="display: flex; justify-content: space-between; font-size: 0.9rem;">
          <span style="font-weight: 600;">${subj}</span>
          <span style="color: ${data.mastery_score_pct >= 70 ? '#16a34a' : '#2563eb'}; font-weight: bold;">${data.mastery_score_pct}%</span>
        </div>
        <div style="width: 100%; height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden;">
          <div style="width: ${data.mastery_score_pct}%; height: 100%; background: ${data.mastery_score_pct >= 70 ? '#16a34a' : '#2563eb'};"></div>
        </div>
        <span style="font-size: 0.75rem; color: var(--text-muted);">${data.status} (${data.queries_count} پرسش)</span>
      </div>
    `)
    .join("");
}

function renderRecommendations(recs) {
  const container = document.querySelector("#recommendations-list");
  if (!container || !recs) return;
  container.innerHTML = recs
    .map((r) => `
      <div style="padding: 8px 12px; border-radius: 8px; background: ${r.priority === 'HIGH' ? 'rgba(239, 68, 68, 0.08)' : 'rgba(37, 99, 235, 0.06)'}; border: 1px solid ${r.priority === 'HIGH' ? '#fca5a5' : '#bfdbfe'};">
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: bold; color: ${r.priority === 'HIGH' ? '#b91c1c' : '#1d4ed8'};">
          <span>${r.subject}</span>
          <span style="font-size: 0.75rem;">اولویت: ${r.priority}</span>
        </div>
        <div style="font-size: 0.85rem; margin-top: 2px;">${r.topic}</div>
        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">علت: ${r.reason}</div>
      </div>
    `)
    .join("");
}

const profileForm = document.querySelector("#profile-form");
if (profileForm) {
  profileForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!accessToken) return;
    const grade = document.querySelector("#prof-grade").value.trim();
    const field_of_study = document.querySelector("#prof-field").value.trim();
    const target_level = document.querySelector("#prof-level").value;
    const statusMsg = document.querySelector("#profile-save-status");
    try {
      const res = await fetch("/api/v1/student/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
        body: JSON.stringify({ grade, field_of_study, target_level, interests: ["زیست‌شناسی", "شیمی"] }),
      });
      if (res.ok) {
        statusMsg.hidden = false;
        document.querySelector("#profile-badge").textContent = `${grade} - ${field_of_study}`;
        setTimeout(() => (statusMsg.hidden = true), 3000);
      }
    } catch (err) {
      console.error(err);
    }
  });
}

// --- Product Experimentation & Event Tracking Helpers ---
async function trackEvent(eventName, stage = "LEARNING_USER", properties = {}) {
  try {
    if (!accessToken) return;
    await fetch("/api/v1/events/track", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify({
        event_name: eventName,
        stage: stage,
        properties: properties,
      }),
    });
  } catch (e) {
    console.debug("Telemetry track failed silently:", e);
  }
}

async function trackFeatureUsage(featureKey, action = "VIEW", durationSec = 0) {
  try {
    if (!accessToken) return;
    await fetch("/api/v1/events/feature-usage", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify({
        feature_key: featureKey,
        action: action,
        session_duration_sec: durationSec,
      }),
    });
  } catch (e) {
    console.debug("Feature usage track failed silently:", e);
  }
}







