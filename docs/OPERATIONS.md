# عملیات production

## Backup

`DATABASE_URL` را فقط از secret manager یا محیط اجرای production بخوانید و
هرگز در فایل backup، log یا issue ثبت نکنید. نمونهٔ backup فشرده:

```powershell
pg_dump --format=custom --file=education-$(Get-Date -Format yyyyMMdd-HHmm).dump $env:DATABASE_URL
```

فایل dump باید در object storage رمزنگاری‌شده با retention مناسب نگهداری شود.

## Restore drill

Restore را ابتدا روی یک PostgreSQL جداگانه انجام دهید، نه روی دیتابیس اصلی:

```powershell
createdb education_restore
pg_restore --clean --if-exists --dbname=$env:RESTORE_DATABASE_URL .\education-backup.dump
$env:DATABASE_URL = $env:RESTORE_DATABASE_URL
python -m alembic upgrade head
Invoke-WebRequest http://localhost:8000/health/ready
```

موفقیت restore زمانی تأیید می‌شود که migration head، readiness و یک query نمونهٔ
خواندنی همگی موفق باشند. نتیجه و زمان آخرین restore drill باید ثبت شود.

## Release sequence

1. backup موفق و قابل‌خواندن تهیه کنید؛
2. image را build و در staging smoke-test کنید؛
3. `alembic upgrade head` را اجرا کنید؛
4. readiness و مسیرهای اصلی API را بررسی کنید؛
5. ترافیک را به release جدید منتقل کنید؛
6. در صورت خطا، ابتدا ترافیک را برگردانید و سپس rollback سازگار با migration را
   طبق runbook اجرا کنید.

برای اجرای همین چرخه در محیط staging می‌توان از اسکریپت قابل تکرار زیر استفاده کرد:

```powershell
.\scripts\staging-smoke.ps1
```

این اسکریپت ابتدا migrationها را اجرا می‌کند، سرویس‌های `db` و `api` را بالا می‌آورد
و تا موفقیت readiness و تأیید migration head منتظر می‌ماند. در صورت خطا با exit
غیرصفر متوقف می‌شود.

healthcheck خود کانتینر API نیز readiness را هدف می‌گیرد؛ بنابراین کانتینر پیش از
اتصال موفق دیتابیس و هم‌سطح بودن migrationها با head، healthy اعلام نمی‌شود.
image سرویس API نیز با کاربر غیرroot (`appuser`, UID 10001) اجرا می‌شود.

SQLite فقط برای development و test است و نباید محل دادهٔ production باشد.
