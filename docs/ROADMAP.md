# Product Roadmap

این پروژه یک Modular Monolith API-first است؛ کلاینت‌های Telegram Mini App، وب و
اندروید باید از قراردادهای versioned زیر `/api/v1` استفاده کنند.

## وضعیت فعلی

- زیرساخت FastAPI، تنظیمات، logging، rate limiting، Docker و CI پایه موجود است.
- JWT و احراز هویت Telegram Web App با اعتبارسنجی HMAC موجود است.
- مدل‌های User، Identity، Book، Chapter، Lesson، Flashcard و AI usage موجودند.
- Gemini Gateway، Model Router، RAG boundary، خلاصه‌سازی، تولید سؤال و health checks پایه موجودند.
- احراز هویت Telegram، entitlement، پرداخت، audit، آزمون، analytics، teacher assistant،
  worksheet PDF، فلش‌کارت review، Study Planner پایدار و authoring نقش‌محور Curriculum
  نیز پیاده‌سازی و با تست‌های خودکار پوشش داده شده‌اند.

## شکاف‌های باقی‌مانده برای Production

1. اجرای staging واقعی با PostgreSQL، migration و health smoke test.
2. تکمیل چرخهٔ webhook Telegram و اتصال پیام متنی به جریان‌های آموزشی با entitlement.
3. embedding store و retrieval مقیاس‌پذیر برای RAG.
4. payment provider واقعی، پنل admin کامل و گزارش‌گیری production.
5. rate limit مشترک بین replicaها، secret manager و observability متمرکز.
6. backup/restore drill واقعی، deployment staging و تست‌های end-to-end روی محیط اجرا.
7. audit requirement-by-requirement پیش از اعلام Production readiness.

هر مرحله باید با migration، تست رفتاری، lint، type-check، مستندات و health evidence
تکمیل شود. وجود این فهرست به‌تنهایی به معنی پیاده‌سازی قابلیت‌های باقی‌مانده نیست.
