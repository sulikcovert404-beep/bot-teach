# عملیات production

## Backup

`DATABASE_URL` را فقط از secret manager یا محیط اجرای production بخوانید و
هرگز در فایل backup، log یا issue ثبت نکنید. نمونهٔ backup فشرده:

تنظیمات از environment و secretهای mounted (مسیر پیش‌فرض `/run/secrets`) خوانده
می‌شوند؛ environment بر secret file اولویت دارد. در production secret fileها را
با نام فیلدهای تنظیمات مانند `jwt_secret`، `telegram_bot_token` و `gemini_api_key`
از secret manager نصب کنید و `.env` را استفاده نکنید.

```powershell
pg_dump --format=custom --file=education-$(Get-Date -Format yyyyMMdd-HHmm).dump $env:DATABASE_URL
```

فایل dump باید در object storage رمزنگاری‌شده با retention مناسب نگهداری شود.

برای ایجاد و اعتبارسنجی non-destructive یک archive محلی، `DATABASE_URL` را فقط در
محیط قرار دهید و اجرا کنید:

```powershell
.\scripts\backup-verify.ps1 -OutputDirectory .\backups
```

این ابزار `pg_dump` با فرمت custom، `pg_restore --list` و SHA-256 را اجرا می‌کند؛
restore باید طبق بخش بعدی روی یک PostgreSQL جداگانه انجام شود.

## Local disposable restore drill

Restore drill فعلاً فقط روی PostgreSQL محلی و disposable مجاز است. تا زمان معرفی
Environment B و صدور Gate مستقل، backup production را منتقل یا restore نکنید. مقصد
باید loopback و نام آن با `gate738aa_restore_` شروع شود؛ مقصد مبهم یا remote رد می‌شود.
برای جلوگیری از اجرای restore خارج از guard، `pg_restore` را دستی اجرا نکنید؛ از wrapper
پایین استفاده کنید.

```powershell
createdb gate738aa_restore_example
```

اسکریپت wrapper archive را بررسی می‌کند، سپس `pg_restore --clean` را فقط روی مقصدی اجرا
می‌کند که از guard loopback و Gate-owned name عبور کرده است. تا Environment B فراهم
نشود backup production وارد این فرآیند نمی‌شود.

برای اجرای قابل‌تکرار از اسکریپت زیر استفاده کنید. اسکریپت قبل از هر restore، host
را به loopback، database name را به Gate-owned disposable prefix و target را به
canonical migration allowlist محدود می‌کند. Migration از Gate738P runner عبور
می‌کند؛ پس از اجرا readiness باید دقیقاً همان `MigrationTarget` را گزارش کند.

```powershell
.\scripts\restore-drill.ps1 `
  -DumpPath .\backups\education-20260901-220000.dump `
  -RestoreDatabaseUrl $env:RESTORE_DATABASE_URL `
  -MigrationTarget 20261003_0029 `
  -ReadinessUrl http://localhost:8000/health/ready
```

`pg_restore --clean` فقط از داخل wrapper و پس از عبور از تمام guardهای مقصد disposable
اجرا می‌شود. Restore success به‌تنهایی مجوز rollout migration یا انتشار نیست. پاسخ readiness نیز
باید `status=ready` و `migration_head` برابر target صریح باشد.

## Release sequence

1. backup موفق و قابل‌خواندن تهیه کنید؛
2. image را build و در staging smoke-test کنید؛
3. فقط target revision صریحی را از migration-gate runner اجرا کنید که Gate انتشار مجاز کرده است؛
4. readiness و مسیرهای اصلی API را بررسی کنید؛
5. ترافیک را به release جدید منتقل کنید؛
6. در صورت خطا، ابتدا ترافیک را برگردانید و سپس rollback سازگار با migration را
   طبق runbook اجرا کنید.

برای اجرای همین چرخه در محیط staging می‌توان از اسکریپت قابل تکرار زیر استفاده کرد:

```powershell
.\scripts\staging-smoke.ps1
```

این اسکریپت سرویس‌های `db`، migration یک‌باره و `api` را بالا می‌آورد
و تا موفقیت readiness و تأیید migration head منتظر می‌ماند. در صورت خطا با exit
غیرصفر متوقف می‌شود.

healthcheck خود کانتینر API نیز readiness را هدف می‌گیرد؛ بنابراین کانتینر پیش از
اتصال موفق دیتابیس و هم‌سطح بودن migrationها با head، healthy اعلام نمی‌شود.
image سرویس API نیز با کاربر غیرroot (`appuser`, UID 10001) اجرا می‌شود.

SQLite فقط برای development و test است و نباید محل دادهٔ production باشد.

`alembic upgrade head` مسیر انتشار یا production نیست. برای lineage فعلی،
ترتیب staged و کنترل‌شده در گزارش Gate738P ثبت شده است؛ contract بدون
آمادگی candidate و اثبات drain/fence/quiescence مجاز نیست.
