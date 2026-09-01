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
- webhook متنی Telegram با entitlement و idempotency، migration async و rate limit مشترک
  مبتنی بر Redis نیز در مخزن پیاده‌سازی و تست شده‌اند.
- endpoint metrics سازگار با Prometheus برای اتصال به observability متمرکز موجود است.
- payment provider contract و adapter HTTP قابل‌تنظیم، شامل checkout URL و مدیریت خطا،
  در مخزن موجود و تست شده است.

## شکاف‌های باقی‌مانده برای Production

1. اجرای staging واقعی با PostgreSQL، migration و health smoke test.
2. embedding store و retrieval مقیاس‌پذیر برای RAG.
3. اتصال adapter پرداخت به provider واقعی/sandbox، پنل admin کامل و گزارش‌گیری production.
4. secret manager و اتصال واقعی endpoint metrics به observability متمرکز.
5. backup/restore drill واقعی، deployment staging و تست‌های end-to-end روی محیط اجرا.
6. audit requirement-by-requirement پیش از اعلام Production readiness.

هر مرحله باید با migration، تست رفتاری، lint، type-check، مستندات و health evidence
تکمیل شود. وجود این فهرست به‌تنهایی به معنی پیاده‌سازی قابلیت‌های باقی‌مانده نیست.
