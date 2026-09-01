# Payment Provider Contract

این سند قرارداد provider پرداخت را برای sandbox و production تعریف می‌کند. در این
مرحله اتصال به provider واقعی یا تغییر دیتابیس انجام نمی‌شود.

## مرز abstraction

```text
PaymentProvider
  create_payment(amount, plan, merchant_transaction_id) -> Checkout
  verify_payment(provider_transaction_id, amount) -> Verification
  refund(provider_transaction_id, amount) -> RefundResult
```

پیاده‌سازی فعلی `create_checkout` را از طریق adapter HTTP ارائه می‌کند. نام و payload
provider-specific نباید به routeهای API یا domain model نشت کند.

## Create payment

ورودی‌ها:

- مبلغ صحیح و مثبت در واحد رسمی سیستم؛
- شناسه‌ی plan معتبر؛
- `merchant_transaction_id` یکتا و غیرقابل حدس.

خروجی حداقل شامل `provider_transaction_id` و در صورت وجود `checkout_url` است. پاسخ
provider باید schema و نوع داده را validate کند؛ URL پرداخت فقط از scheme مجاز و مقصد
تأییدشده پذیرفته شود.

## Verify payment

callback هرگز صرفاً بر اساس مبلغ یا شناسه‌ی ارسالی کاربر معتبر نمی‌شود. verification باید:

1. امضای callback و webhook secret را بررسی کند؛
2. شناسه‌ی merchant و provider را با intent داخلی تطبیق دهد؛
3. مبلغ، ارز، plan و وضعیت نهایی را از provider یا callback معتبر تأیید کند؛
4. عملیات را idempotent انجام دهد؛
5. entitlement را فقط پس از وضعیت نهایی موفق فعال کند؛
6. payload خام حساس را log نکند.

## Refund

refund فقط برای تراکنش موفق و با policy دسترسی مجاز است. نتیجه باید وضعیت صریح، شناسه‌ی
refund provider و خطای پاک‌سازی‌شده داشته باشد. retry باید با idempotency key انجام شود تا
دو بار refund نشود.

## خطا و retry

- timeout و خطای شبکه با backoff محدود retry می‌شوند؛
- خطای 4xx قابل retry نیست مگر provider صراحتاً اعلام کند؛
- خطای 5xx و timeout باید با شناسه‌ی داخلی قابل پیگیری باشد؛
- API key، Authorization header و payload پرداخت در exception یا log نیاید؛
- اگر وضعیت provider نامشخص است، intent به حالت pending بماند و دوباره verify شود.

## قرارداد callback داخلی

callback داخلی باید شامل `merchant_transaction_id`، `provider_transaction_id`، status،
amount، currency و signature باشد. endpoint باید در برابر replay، duplicate delivery و
ترتیب متفاوت eventها مقاوم باشد. هر event با شناسه‌ی یکتا ثبت و دوباره‌پردازش‌نشدنی شود.

## Sandbox acceptance criteria

- create، verify موفق، verify ناموفق و refund تست شوند؛
- duplicate callback فقط یک entitlement ایجاد کند؛
- مبلغ/plan ناهماهنگ رد شود؛
- timeout و provider 5xx retry محدود داشته باشند؛
- secret در log، response و artifact دیده نشود؛
- تمام تراکنش‌ها با audit log و request id قابل پیگیری باشند.

## تصمیم‌های باز

- provider و endpoint sandbox؛
- ارز و واحد مبلغ؛
- سیاست refund و پنجره‌ی زمانی؛
- منبع حقیقت وضعیت تراکنش در اختلاف callback/provider؛
- روش secret manager و rotation.

این تصمیم‌ها باید پیش از اتصال production در staging تأیید و در قرارداد provider ثبت شوند.
