# Product Roadmap

این پروژه یک Modular Monolith API-first است؛ کلاینت‌های Telegram Mini App، وب و
اندروید باید از قراردادهای versioned زیر `/api/v1` استفاده کنند.

## وضعیت فعلی

- زیرساخت FastAPI، تنظیمات، logging، rate limiting، Docker و CI پایه موجود است.
- JWT و احراز هویت Telegram Web App با اعتبارسنجی HMAC موجود است.
- مدل‌های User، Identity، Book، Chapter، Lesson، Flashcard و AI usage موجودند.
- Gemini Gateway، Model Router، RAG boundary، خلاصه‌سازی، تولید سؤال و health checks پایه موجودند.

## ترتیب اجرای بعدی

1. اتصال composition root به PostgreSQL و مدیریت lifecycle session/engine.
2. Entitlement پایدار در دیتابیس و middleware بررسی feature access.
3. تکمیل Telegram bot webhook و Mini App contract.
4. سرویس‌های Exam، Exam Corrector، Study Planner و Learning Analytics با event model.
5. ingestion اسناد، embedding store و Source Guardian قابل استناد.
6. پنل‌های admin، پرداخت و گزارش‌گیری audit-friendly.
7. export PDF/worksheet، observability production، backup restore drill و deployment staging.
8. تست‌های end-to-end و audit requirement-by-requirement پیش از اعلام Production readiness.

هر مرحله باید با migration، تست رفتاری، lint، type-check، مستندات و health evidence
تکمیل شود. وجود این فهرست به‌تنهایی به معنی پیاده‌سازی قابلیت‌های باقی‌مانده نیست.
