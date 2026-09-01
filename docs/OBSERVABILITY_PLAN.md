# برنامه Observability

این سند طرح اجرایی observability سبک برای محیط staging و production است؛ سرویس
سنگین جدیدی در این مرحله اضافه نمی‌شود.

## سیگنال‌ها

### Structured logs

تمام logهای application باید JSON و شامل این فیلدهای غیرمحرمانه باشند:

- `timestamp`, `level`, `logger`, `event`
- `request_id`, `method`, `path`, `status_code`, `duration_ms`
- `user_id` فقط در صورت مجاز بودن و به‌صورت شناسه‌ی داخلی
- `task_type`, `model`, `usage_tokens` برای رویدادهای AI
- `source_id` و `page` برای citation، بدون متن کامل منبع

توکن، API key، Authorization header، cookie، prompt کامل، متن کتاب و payload پرداخت
نباید log شوند. خطاها باید با exception type و پیام پاک‌سازی‌شده ثبت شوند.

### Metrics

endpoint فعلی `/metrics/prometheus` باید منبع scrape باشد. حداقل سنجه‌ها:

- تعداد و latency درخواست بر اساس route/status؛
- نرخ 4xx/5xx و خطاهای readiness؛
- نرخ hit/miss و rejection برای rate limit؛
- latency و خطای DB/Redis؛
- تعداد درخواست، خطا، latency و token usage برای هر `task_type/model`؛
- مدت migration و نتیجه‌ی backup/restore drill.

برچسب‌ها باید bounded باشند؛ `user_id`، prompt، source text و URL کامل label نیستند.

### Health monitoring

- `/health` فقط liveness است و باید بدون dependency خارجی پاسخ دهد.
- `/health/ready` باید DB، migration head و Redis را بررسی کند.
- healthcheck کانتینر API باید readiness را هدف بگیرد.
- alert برای چند شکست متوالی readiness، افزایش 5xx، latency P95، خطای provider و
  کمبود فضای backup تعریف شود.

## Error tracking

در صورت اضافه‌شدن error tracker، فقط exceptionهای ناشناس‌شده و context حداقلی ارسال شود؛
ارسال secret، prompt، متن منبع یا داده‌ی شخصی ممنوع است. ابتدا logging و metrics فعلی
فعال بماند و vendor با یک adapter قابل تعویض اضافه شود.

## داشبورد حداقلی

1. API availability: نرخ موفقیت، 5xx، P95 latency؛
2. Dependencies: DB/Redis readiness و connection errors؛
3. AI: provider errors، latency، token usage و budget؛
4. Telegram/payment: webhook errors، idempotency conflicts و callback failures؛
5. Operations: migration، backup و restore drill.

## Runbook واکنش

1. ابتدا dashboard و `request_id` را بررسی کنید؛
2. readiness و dependency را از liveness جدا کنید؛
3. در خطای provider، retry و rate limit را بررسی کنید و secret را چاپ نکنید؛
4. در خطای migration یا backup، release را متوقف و طبق runbook عملیات اقدام کنید؛
5. پس از رفع، یک test رفتاری و یک health check ثبت کنید.

## معیار پذیرش

در staging باید بتوان با یک `request_id` یک درخواست را از API تا dependency دنبال کرد،
متریک‌ها را scrape کرد، و بدون مشاهده‌ی secret یا متن حساس علت خطا را تشخیص داد.
