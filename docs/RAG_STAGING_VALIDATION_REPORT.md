# RAG STAGING VALIDATION REPORT

تاریخ بررسی: 2026-09-02

## Environment

- Docker CLI: `29.5.3`، context: `desktop-linux`
- Docker Compose configuration: معتبر (`docker compose config --quiet`)
- Docker daemon: **در دسترس نیست**؛ `docker version` با نبودن
  `dockerDesktopLinuxEngine` شکست خورد.
- تلاش برای راه‌اندازی غیرمخرب Docker Desktop انجام شد، اما daemon در پایان بررسی
  فعال نشد.

در نتیجه، این گزارش نتیجه اجرای PostgreSQL واقعی یا pgvector runtime نیست و هیچ ادعایی
درباره صحت staging واقعی ارائه نمی‌کند.

## Migration و pgvector status

| بررسی | نتیجه |
| --- | --- |
| PostgreSQL container | اجرا نشد؛ daemon unavailable |
| `alembic upgrade head` روی PostgreSQL | اجرا نشد |
| فعال‌سازی extension `vector` | اجرا نشد |
| rollback روی PostgreSQL | اجرا نشد |
| health check staging | اجرا نشد |
| compose schema/config | موفق |
| SQLite migration upgrade/downgrade/re-upgrade | قبلاً موفق ثبت شده است |

## Retrieval tests قابل‌اجرا

- `tests/test_document_ingestion.py`: **2 passed in 0.94s**؛ این تست lexical retrieval
  و ingestion روی SQLite است و جایگزین pgvector integration نیست.
- `tests/test_vector_store.py`: **3 passed in 0.64s**؛ این تست guard، اعتبارسنجی و
  compile شدن نوع `VECTOR(768)` را پوشش می‌دهد، اما similarity query واقعی PostgreSQL
  اجرا نمی‌کند.

## Benchmark results

### Baseline محلی (غیرقابل‌مقایسه با staging)

تنها baseline قابل‌اجرا، اجرای تست SQLite lexical بود: 2 تست در 0.94 ثانیه. این عدد
شامل setup تست است و latency هر query محسوب نمی‌شود؛ بنابراین برای P50/P95، memory
impact، query plan یا رفتار index قابل‌استفاده نیست.

### موارد اندازه‌گیری‌نشده

- latency واقعی vector similarity و P50/P95؛
- top-K روی embedding واقعی؛
- metadata filtering در PostgreSQL؛
- مصرف RAM/CPU و حجم index؛
- رفتار index و زمان reindex؛
- migration/rollback روی PostgreSQL.

## Issues

Blocker محیطی فعلی: Docker daemon قابل‌دسترسی نیست. این blocker کد نیست و با تغییر
کد امن قابل‌دورزدن نیست. برای ادامه validation باید Docker Desktop/engine فعال شود یا
یک PostgreSQL دارای pgvector در محیط staging در دسترس قرار گیرد.

## Recommendation

Foundation فعلی بدون تغییر معماری حفظ شود. پس از فراهم‌شدن runtime:

1. `docker compose up -d db migrate api` اجرا شود.
2. migration head `e2f3a4b5c6d7` و health readiness بررسی شود.
3. چند chunk با embedding واقعی درج و cosine top-K و metadata filters بررسی شوند.
4. benchmark با dataset کوچک فارسی و queryهای دارای expected chunk اجرا شود.
5. P50/P95، Recall@K، citation accuracy، memory و index behavior ثبت شود.

تا انجام این مراحل، staging validation و retrieval benchmark را **ناقص/محیط‌مسدود**
در نظر بگیرید؛ هیچ optimization index یا feature جدیدی پیشنهاد نمی‌شود.
