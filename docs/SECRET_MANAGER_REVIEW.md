# Secret Manager Review

این سند بررسی گزینه‌های تزریق secret برای staging و production است و انتخاب نهایی
محصول یا انتقال credential انجام نمی‌دهد.

## نیازمندی‌های غیرقابل‌مذاکره

- secret در Git، image، artifact، log یا issue ذخیره نشود؛
- rotation بدون rebuild کد و با کمترین downtime ممکن باشد؛
- دسترسی بر اساس محیط و least privilege محدود شود؛
- audit دسترسی و زمان انقضا قابل مشاهده باشد؛
- backup و restore secretها جدا از backup دیتابیس مدیریت شود؛
- برنامه‌ی revoke برای credential افشاشده وجود داشته باشد؛
- application فقط environment یا mounted secret file بخواند و مقدار را log نکند.

Secretهای فعلی شامل JWT، Telegram bot token، Telegram webhook secret، Gemini API key،
payment webhook secret و در صورت استفاده payment provider key هستند.

## گزینه‌ها

| گزینه | مزیت | هزینه/ریسک | مناسب برای |
| --- | --- | --- | --- |
| GitHub Actions Secrets | ساده برای CI و deploy؛ بدون فایل در repo | محدود به workflow؛ rotation و runtime access به pipeline وابسته | CI و محیط‌های کوچک |
| VPS environment / systemd or Compose secrets | ساده و کم‌هزینه؛ کنترل مستقیم روی VPS | مسئولیت rotation، audit و دسترسی با تیم است | staging ساده و VPS کوچک |
| Cloudflare/edge secret bindings | مناسب worker/edge و جداسازی از کد | برای secretهای داخل API روی VPS الزاماً مسیر مستقیم نیست | اجزای edge |
| Managed Secret Service | rotation، audit، IAM و دسترسی runtime بهتر | هزینه و وابستگی provider؛ نیازمند شبکه و bootstrap identity | production چندمحیطی |

هیچ گزینه‌ای بدون بررسی threat model، هزینه، محل استقرار و روش deploy انتخاب نمی‌شود.

## جریان پیشنهادی runtime

```text
Secret Manager
      |
  workload identity / protected deploy step
      |
 environment variables or /run/secrets/<name>
      |
 Settings validation at startup
      |
 application (no secret logging)
```

نام secret باید با فیلدهای `Settings` سازگار باشد. environment نسبت به mounted file
اولویت دارد تا رفتار فعلی قابل پیش‌بینی بماند؛ در production باید فقط یک منبع authoritative
فعال باشد و مقدار fallback نمونه‌ای رد شود.

## Rotation runbook

1. credential جدید را در secret manager ایجاد کنید؛
2. دسترسی/health check را در staging بررسی کنید؛
3. deploy کنترل‌شده انجام دهید و خطاهای provider را پایش کنید؛
4. credential قدیمی را revoke کنید؛
5. log، Git history و artifact scan را بدون نمایش مقدار بررسی کنید؛
6. زمان rotation، محیط و نتیجه را در change record ثبت کنید.

برای Telegram ابتدا token قدیمی revoke شود؛ برای Gemini و payment provider از revoke/key
rotation رسمی همان provider استفاده شود. مقدار credential هرگز در گزارش ثبت نشود.

## CI و deploy checklist

- [ ] secretها فقط از protected environment یا secret manager خوانده می‌شوند.
- [ ] pull request و fork به secret production دسترسی ندارند.
- [ ] startup با secret ناقص fail-closed است.
- [ ] secret در command line، process argument و log ظاهر نمی‌شود.
- [ ] دسترسی deploy محدود و قابل audit است.
- [ ] rotation و rollback مستند و روی staging آزموده شده است.
- [ ] secret scan روی tracked files و artifact اجرا می‌شود.

## تصمیم موردنیاز فرمانده

برای production، پس از مشخص‌شدن محل استقرار و مدل deploy، یک گزینه‌ی managed یا VPS
environment با کنترل‌های بالا انتخاب شود. تا آن زمان `.env` فقط برای توسعه‌ی محلی است،
`.env.example` فقط placeholder دارد، و هیچ migration یا تغییر runtime جدیدی بر اساس این
سند اعمال نمی‌شود.
