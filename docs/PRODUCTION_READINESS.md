# ممیزی آمادگی Production

این سند وضعیت واقعی مخزن را ثبت می‌کند و به‌تنهایی به معنی آمادگی Production نیست.

## تأییدشده در مخزن

- Backend FastAPI با API versioned زیر `/api/v1`
- JWT، نقش‌ها و احراز هویت Telegram WebApp با بررسی HMAC و عمر `auth_date`
- Subscription/entitlement، payment foundation و audit log
- AI Gateway، Gemini adapter، RAG و Source Guardian
- Curriculum شامل Book/Chapter/Lesson و authoring نقش‌محور
- Tutor، خلاصه‌سازی، تولید سؤال، آزمون و تصحیح آزمون
- Flashcards با spaced repetition و Study Planner پایدار
- Learning Analytics و adaptive recommendation
- Teacher Assistant و PDF worksheet
- logging، request metrics، rate limiting و HTTP security headers
- metrics سازگار با Prometheus در `/metrics/prometheus` و rate limit مشترک Redis
- پشتیبانی تنظیمات از secret fileهای mounted در `/run/secrets` با اولویت environment
- migration chain تا `e2f3a4b5c6d7` با upgrade و rollback یک‌مرحله‌ای
- Docker compose با سرویس migration و اجرای API با کاربر غیرroot
- رمز PostgreSQL در compose از `POSTGRES_PASSWORD` اجباری محیطی خوانده می‌شود و hardcode نیست
- تست‌های خودکار، Ruff، mypy و CI dependency audit
- طراحی RAG، برنامه observability، checklist staging و بررسی Secret Manager مستند شده‌اند؛
  این اسناد جایگزین اجرای واقعی محیطی نیستند.

## نیازمند اجرای محیطی قبل از اعلام Production

- اجرای واقعی `docker compose up` و `scripts/staging-smoke.ps1` روی Docker daemon فعال
- اتصال به PostgreSQL staging و اجرای query/readiness واقعی
- تأیید provider واقعی Gemini و Telegram با secret manager؛ secretها نباید در Git باشند
- اتصال payment provider واقعی و آزمون callback در محیط sandbox
- تنظیم `PAYMENT_PROVIDER_URL` و `PAYMENT_PROVIDER_API_KEY` و تطبیق قرارداد `/v1/checkout`
- backup/restore drill روی PostgreSQL جداگانه
- اجرای runbook چرخش secret و پاک‌سازی history طبق `docs/SECURITY_ROTATION.md`
- بررسی rate limit مشترک بین replicaها و observability متمرکز
- تست end-to-end روی staging و audit نهایی requirement-by-requirement

راهنمای اجرای staging در [`STAGING_CHECKLIST.md`](STAGING_CHECKLIST.md)، برنامه‌ی
observability در [`OBSERVABILITY_PLAN.md`](OBSERVABILITY_PLAN.md)، و طراحی RAG در
[`RAG_ARCHITECTURE_PROPOSAL.md`](RAG_ARCHITECTURE_PROPOSAL.md) نگهداری می‌شوند.

تا زمانی که موارد بخش دوم اجرا و ثبت نشده‌اند، پروژه را Production-ready اعلام نکنید.
