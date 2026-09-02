# Admin Content Pipeline PRD (Draft)

وضعیت: Draft برای تصمیم Commander؛ این سند هیچ migration یا تغییر runtime را تصویب نمی‌کند.

## هدف

فراهم‌کردن مسیر قابل audit برای ورود محتوای آموزشی رسمی، از دریافت منبع تا انتشار قطعه‌های قابل retrieval، با حفظ traceability و امکان rollback.

## جریان پیشنهادی

1. **ثبت منبع**: ایجاد رکورد با `source_id` پایدار، عنوان، نوع منبع، پایه، درس، نسخه curriculum و URI مجاز.
2. **اعتبارسنجی**: بررسی نوع فایل، اندازه، scheme، نبود credential در URI و مجازبودن منبع.
3. **استخراج**: parser نسخه‌دار متن، صفحه و ترتیب را استخراج می‌کند؛ خطاها به وضعیت `failed` می‌روند و به‌عنوان نبود منبع پنهان نمی‌شوند.
4. **تقسیم**: تولید chunkهای deterministic با `content_hash`، شماره صفحه و شناسه فصل/درس در صورت وجود.
5. **بازبینی**: محتوای استخراج‌شده پیش از انتشار توسط نقش مجاز بازبینی و audit می‌شود.
6. **انتشار**: فقط نسخه approved وارد retrieval می‌شود؛ index generation قابل ردیابی است.
7. **بازگشت**: انتشار نسخه جدید باید امکان rollback به آخرین نسخه approved را داشته باشد.

## حداقل metadata

- `source_id`, `source_type`, `title`
- `book_id`, `grade`, `subject`, `curriculum_version`
- `chapter`, `lesson`, `page_start`, `page_end`
- `content_hash`, `parser_version`, `index_generation`
- وضعیت lifecycle: `pending`, `review`, `approved`, `rejected`, `failed`, `archived`

## نقش‌ها و کنترل‌ها

- uploader فقط ثبت و مشاهده وضعیت را انجام می‌دهد.
- reviewer محتوای استخراج‌شده و metadata را تأیید یا رد می‌کند.
- publisher نسخه approved را منتشر یا archive می‌کند.
- هر تغییر وضعیت با actor، زمان، علت و source version در audit ثبت می‌شود.

## معیارهای پذیرش آینده

- ingest تکراری با همان hash خروجی جدید تولید نکند.
- منبع rejected یا archived در retrieval ظاهر نشود.
- citation شامل source، chunk و page معتبر باشد.
- خطای parser قابل مشاهده و قابل retry باشد.
- rollback نسخه قبلی را بدون حذف دائمی داده ممکن کند.
- تست‌های authorization، idempotency، metadata validation و Persian text/OCR پوشش داده شوند.

## تصمیم‌های موردنیاز Commander

1. enum نهایی lifecycle و نقش reviewer/publisher.
2. اجباری‌بودن `book_id` و `curriculum_version` برای همه کتاب‌ها.
3. سیاست اندازه و قالب‌های مجاز PDF/HTML/متن.
4. راهبرد نگهداری نسخه‌ها و retention داده ردشده.
5. زمان‌بندی embedding و انتشار index.
