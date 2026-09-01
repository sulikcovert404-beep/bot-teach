# Secret Rotation Runbook

این سند هیچ credential واقعی ندارد. هر secret افشاشده باید قبل از هرگونه
استقرار production، در سرویس صادرکننده revoke و با مقدار جدید جایگزین شود.

## Telegram bot token

1. در BotFather توکن فعلی را revoke کنید و یک توکن جدید بسازید.
2. مقدار جدید را فقط در secret manager یا محیط اجرای staging/production قرار دهید.
3. `TELEGRAM_BOT_TOKEN` را در محیط اجرا به‌روزرسانی و سرویس را restart کنید.
4. webhook را با `TELEGRAM_WEBHOOK_SECRET` جدید دوباره ثبت و با `/health/ready`
   و یک webhook آزمایشی بدون دادهٔ حساس بررسی کنید.

## Repository history

وجود secret در history به معنی افشای دائمی آن است، حتی اگر فایل فعلی پاک‌سازی
شده باشد. پس از revoke/rotate:

1. با ابزار تأییدشدهٔ تیم، history را با `git filter-repo` یا ابزار معادل پاک‌سازی
   کنید.
2. قبل از force-push، backup و هماهنگی با همهٔ cloneهای فعال را انجام دهید.
3. secret scan را روی کل history و working tree اجرا کنید.
4. branchهای remote و cacheهای CI را بررسی و در صورت نیاز invalidate کنید.
5. از این پس CI باید `scripts/secret_scan.py` را اجرا کند.

## Verification

- secret قدیمی دیگر در سرویس صادرکننده معتبر نیست.
- مقدار جدید در Git، logها، artifactها و issueها وجود ندارد.
- سرویس با secret manager و health checks موفق بالا می‌آید.
- هیچ token یا credentialی در گزارش‌ها، test fixtureها یا handoffها ثبت نشده است.
