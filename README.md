# AI Education Platform Iran

پایه‌ی یک Modular Monolith با API مرکزی برای ساخت AI Learning Operating System آموزش ایران.
این مخزن در مرحله‌ی foundation قابل‌تست است و هنوز ادعای Production readiness کامل ندارد.

## اجرا

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

برای شروع، `.env.example` را به `.env` کپی کنید و مقادیر secret را فقط در محیط
محلی یا secret manager وارد کنید؛ `.env` در Git نادیده گرفته می‌شود.

Health: `GET /health` و readiness: `GET /health/ready`

Telegram Mini App: `GET /mini-app/` (در محیط Telegram با `initData` معتبر اجرا شود).

Platform API: `GET /api/v1/platform`

مسیرهای اصلی فعلی:

- `POST /api/v1/auth/telegram` — اعتبارسنجی Telegram Web App و صدور JWT
- `GET /api/v1/curriculum/books` — کتاب‌ها، فصل‌ها و درس‌ها
- `POST /api/v1/curriculum/books` و مسیرهای `/chapters` و `/lessons` — authoring برای مدرس/ادمین
- `GET|POST /api/v1/flashcards` و `POST /api/v1/flashcards/{id}/review` — کارت و مرور فاصله‌دار
- `GET|POST /api/v1/study-plan` — ساخت و بازیابی آخرین برنامهٔ مطالعه
- `PATCH /api/v1/study-plan/tasks/{id}` — ثبت تکمیل وظیفه
- `GET /api/v1/subscription` — پلن مؤثر و قابلیت‌های فعال
- `POST /api/v1/ai/generate` — gateway عمومی Gemini
- `POST /api/v1/ai/summarize` — خلاصه‌سازی هوشمند
- `POST /api/v1/ai/questions` — تولید سؤال
- `POST /api/v1/ai/exam` و `/api/v1/ai/exam/correct` — تولید و تصحیح آزمون

## اصول

- API-first و آماده برای چند client
- domain modules مستقل از transport
- configuration فقط از environment
- providerهای AI پشت gateway و Model Router قرار دارند
- secrets در `.env` محلی، نه در Git

## توسعه و اعتبارسنجی

```powershell
.\.venv\Scripts\python.exe -m ruff check app tests migrations
.\.venv\Scripts\python.exe -m mypy app
.\.venv\Scripts\python.exe -m pytest -q
```

CI علاوه بر quality gates، migration chain، audit آسیب‌پذیری dependency و ساخت Docker image را نیز بررسی می‌کند. Readiness علاوه بر
اتصال دیتابیس، migration head مورد انتظار را نیز کنترل می‌کند.

نقشه‌ی راه و تفکیک وضعیت واقعی قابلیت‌ها در [`docs/ROADMAP.md`](docs/ROADMAP.md) است.
