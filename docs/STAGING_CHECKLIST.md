# Staging Checklist

این checklist برای اجرای دستی یا CI روی محیط staging است. تا وقتی Docker daemon و
secretهای staging آماده نیستند، موارد اجراشده را حدس نزنید و به‌صورت `PENDING` ثبت کنید.

## پیش‌نیازها

- [ ] Docker daemon فعال و نسخه‌ی image ثبت شده است.
- [ ] secretها از secret manager/environment تزریق شده‌اند؛ `.env.example` استفاده نشده.
- [ ] `POSTGRES_PASSWORD`، JWT، Telegram، Gemini، Redis و payment webhook secret موجودند.
- [ ] provider URLها و callback URLها به sandbox/staging اشاره می‌کنند.
- [ ] مقصد backup و restore جدا از دیتابیس اصلی است.

## استقرار

- [ ] `docker compose config` بدون خطا اجرا شد.
- [ ] image با کاربر non-root build شد.
- [ ] سرویس‌های `db` و `redis` healthy شدند.
- [ ] migration container تا head (`e2f3a4b5c6d7`) موفق شد.
- [ ] API پس از migration بالا آمد.

## Smoke tests

- [ ] `/health` وضعیت liveness را برمی‌گرداند.
- [ ] `/health/ready` وضعیت `ready` و migration head صحیح را برمی‌گرداند.
- [ ] `/metrics/prometheus` بدون secret قابل scrape است.
- [ ] Telegram auth با fixture معتبر و نامعتبر بررسی شد.
- [ ] یک مسیر protected با نقش مجاز و غیرمجاز بررسی شد.
- [ ] یک مسیر AI با provider sandbox و usage logging بررسی شد.
- [ ] webhookهای Telegram/payment با idempotency و secret validation بررسی شدند.

## Backup و rollback

- [ ] backup custom-format تولید و با `pg_restore --list` validate شد.
- [ ] checksum و زمان backup ثبت شد؛ secret یا URL در log ثبت نشد.
- [ ] restore روی دیتابیس جدا با `scripts/restore-drill.ps1` انجام شد.
- [ ] migration head، readiness و یک query خواندنی در restore موفق شدند.
- [ ] نتیجه و زمان restore drill ثبت شد.

## Observability و امنیت

- [ ] logها structured و فاقد credential هستند.
- [ ] نرخ 4xx/5xx، latency و خطای DB/Redis/AI قابل مشاهده است.
- [ ] alertهای readiness و 5xx فعال یا به‌صراحت ثبت نشده‌اند.
- [ ] rate limit بین replicaها با Redis بررسی شد.
- [ ] هیچ secretی در image، artifact، log یا Git دیده نشد.

## خروجی اجباری

برای هر اجرای staging این موارد را ثبت کنید: commit SHA، زمان شروع/پایان، image digest،
migration head، نتیجه‌ی smoke test، backup/restore result، هشدارها و blockerها. فقط پس
از تکمیل موارد اجباری می‌توان status را از `STAGING-PENDING` به `STAGING-VERIFIED` تغییر داد.
