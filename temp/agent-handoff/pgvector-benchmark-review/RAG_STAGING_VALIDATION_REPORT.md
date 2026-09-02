# RAG STAGING VALIDATION REPORT

تاریخ بررسی: 2026-09-02

## Environment

- Docker CLI: `29.5.3`، context: `desktop-linux`
- Docker Compose configuration: معتبر (`docker compose config --quiet`)
- Docker daemon: **فعال و سالم**؛ Docker Desktop `4.77.0` و Engine `29.5.3`.

پس از فعال‌شدن Docker، validation واقعی staging در همین محیط اجرا شد.

## Migration و pgvector status

| بررسی | نتیجه |
| --- | --- |
| PostgreSQL container | موفق؛ `pgvector/pgvector:pg16` و healthy |
| `alembic upgrade head` روی PostgreSQL | موفق؛ head `e2f3a4b5c6d7` |
| فعال‌سازی extension `vector` | موفق؛ نسخه `0.8.6` |
| rollback روی PostgreSQL | موفق؛ downgrade به `d1e2f3a4b5c6` |
| re-upgrade روی PostgreSQL | موفق؛ بازگشت به `e2f3a4b5c6d7` |
| health check staging | موفق؛ `status=ready` |
| compose schema/config | موفق |
| SQLite migration upgrade/downgrade/re-upgrade | قبلاً موفق ثبت شده است |

## Retrieval tests قابل‌اجرا

- `tests/test_document_ingestion.py`: **2 passed in 0.94s**؛ این تست lexical retrieval
  و ingestion روی SQLite است و جایگزین pgvector integration نیست.
- `tests/test_vector_store.py`: **3 passed in 0.64s**؛ این تست guard، اعتبارسنجی و
  compile شدن نوع `VECTOR(768)` را پوشش می‌دهد.
- SQL staging: درج ۳ embedding، cosine top-K و فیلتر subject موفق شد؛ دو نتیجه اول
  similarity برابر `1.000000` و `0.993884` داشتند و فیلتر science دو رکورد برگرداند.
  داده داخل transaction آزمایشی rollback شد.

## Benchmark results

### Baseline محلی (غیرقابل‌مقایسه با staging)

تنها baseline قابل‌اجرا، اجرای تست SQLite lexical بود: 2 تست در 0.94 ثانیه. این عدد
شامل setup تست است و latency هر query محسوب نمی‌شود؛ بنابراین برای P50/P95، memory
impact، query plan یا رفتار index قابل‌استفاده نیست.

### اندازه‌گیری staging واقعی

- روی ۲۰ رکورد آزمایشی و بدون index اختصاصی، `EXPLAIN ANALYZE` از Seq Scan و top-N
  heapsort استفاده کرد.
- Planning Time: `0.118 ms`؛ Execution Time: `0.083 ms`؛ shared buffers hit: `44`.
- این اعداد فقط smoke benchmark کوچک هستند و برای production یا مقایسه index کافی نیستند.

### موارد خارج از این checkpoint

- warm/cold latency تفکیک نشده است؛
- رفتار mismatch فیلتر به‌صورت مستقل اندازه‌گیری نشده است؛
- مصرف RAM/CPU، حجم index و reindex بررسی نشده‌اند؛
- fixture شامل تنوع ZWNJ/OCR و املای فارسی نیست.

## Issues

دو ناسازگاری Docker image در validation کشف و اصلاح شد: migration files و `alembic.ini`
در image نبودند، و dependencyهای `pgvector` و `reportlab` نصب نمی‌شدند. پس از اصلاح،
build و staging موفق شدند.

## Recommendation

Foundation فعلی بدون تغییر معماری حفظ شود. پس از فراهم‌شدن runtime:

1. `docker compose up -d db migrate api` اجرا شود.
2. migration head `e2f3a4b5c6d7` و health readiness بررسی شود.
3. چند chunk با embedding واقعی درج و cosine top-K و metadata filters بررسی شوند.
4. benchmark با dataset کوچک فارسی و queryهای دارای expected chunk اجرا شود.
5. P50/P95، Recall@K، citation accuracy، memory و index behavior ثبت شود.

با وجود موفقیت smoke validation، benchmark کیفیت روی dataset واقعی فارسی، latency
در مقیاس بالاتر، memory impact و index behavior production هنوز انجام نشده‌اند؛ هیچ
optimization index یا feature جدیدی در این checkpoint پیشنهاد نمی‌شود.

## Controlled pgvector benchmark execution

در یک کانتینر موقت و ایزوله `pgvector/pgvector:pg16`، با fixture سه‌منبعی
(`exact`، `related` و `noise`) و query «نیرو چیست»، runner مصوب lexical و
`PgVectorStore` هرکدام پنج بار اجرا شدند. زمان seed و cleanup از اندازه‌گیری حذف شد.

| Retriever | Recall@2 | Precision@2 | MRR | Citation Accuracy | P50 (ms) | P95 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Lexical | 1.0 | 0.5 | 1.0 | 1.0 | 2.157 | 7.048 |
| Vector | 1.0 | 0.5 | 1.0 | 1.0 | 2.542 | 5.861 |

Rollback پس از اجرا انجام شد و شمارش منابع با prefix benchmark صفر بود؛ کانتینر
موقت نیز حذف شد. این fixture کوچک و synthetic است و نتیجه production یا gate نیست.
تفکیک warm/cold، رفتار mismatch فیلتر، ZWNJ/OCR و ارزیابی روی corpus واقعی فارسی
در این checkpoint پوشش داده نشده‌اند.

