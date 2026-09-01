# SOURCE GUARDIAN و RETRIEVAL CONTRACT — پیشنهاد طراحی

وضعیت: **Proposal برای بررسی فرمانده**

این سند در این مرحله فقط قرارداد و رفتار مورد انتظار را تعریف می‌کند. هیچ migration،
dependency، ingestion pipeline یا تغییر runtime را تصویب یا اجرا نمی‌کند.

## 1. هدف و مرز

هدف، محدودکردن پاسخ آموزشی به منابع مجاز و قابل‌استناد است؛ نه جایگزین‌کردن مدل زبانی
یا تصمیم‌گیری خودکار درباره اعتبار محتوای کتاب. متن و metadata منبع در دیتابیس رابطه‌ای
منبع حقیقت باقی می‌ماند و vector index فقط نمایه‌ای قابل‌بازسازی است.

قرارداد باید با Modular Monolith فعلی سازگار باشد و امکان تعویض retriever، embedding
provider و vector store را بدون تغییر consumerهای آموزشی حفظ کند.

## 2. قرارداد Retrieval

```python
@dataclass(frozen=True)
class RetrievalRequest:
    query: str
    limit: int = 5
    grade: str | None = None
    subject: str | None = None
    book_id: int | None = None
    curriculum_version: str | None = None
    source_types: tuple[str, ...] = ()
    scope: str = "public"
    index_generation: str | None = None

@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    text: str
    source_id: str
    page: int | None
    score: float
    score_kind: str
    embedding_model: str | None
    index_generation: str | None

class Retriever(Protocol):
    async def retrieve(self, request: RetrievalRequest) -> list[RetrievedChunk]: ...
```

قواعد قرارداد:

- `query` پس از نرمال‌سازی Unicode و حذف whitespace اضافی، حداقل یک نویسه معنادار داشته باشد.
- `limit` در بازه ۱ تا ۲۰ محدود شود؛ مقدار ورودی هرگز مستقیماً به SQL یا provider منتقل نشود.
- scope و فیلترهای مجوز باید پیش از ranking اعمال شوند، نه بعد از بازگرداندن نتایج.
- نتیجه‌ها بر اساس `chunk_id` یا hash پایدار deduplicate شوند و ترتیب قطعی داشته باشند.
- `score` فقط امتیاز retrieval است و به‌تنهایی confidence یا صحت علمی محسوب نمی‌شود.
- نتیجه فاقد `source_id` معتبر قابل‌استفاده برای پاسخ grounded نیست.
- retriever در صورت نبود نتیجه، `[]` برگرداند؛ خطای provider، timeout و داده ناسازگار
  باید با خطای قابل‌تشخیص به لایه بالاتر منتقل شوند و به «نبود منبع» تبدیل نشوند.

در نسخه اول، adapter موجود `DatabaseRetriever` برای lexical retrieval و `PgVectorStore`
برای vector retrieval در پشت همین abstraction قرار می‌گیرند. hybrid ranking و reranking
تا پیش از تأیید این Proposal پیاده‌سازی نمی‌شوند.

## 3. قرارداد Source Metadata و Citation

هر قطعه قابل‌استناد باید حداقل این اطلاعات را داشته باشد:

| فیلد | الزام | کاربرد |
| --- | --- | --- |
| `chunk_id` | required | trace و deduplication |
| `source_id` | required | شناسه قابل نمایش و audit |
| `source_type` | required | policy منبع رسمی/تأییدشده |
| `book_id` | required برای کتاب | اتصال به هویت رابطه‌ای کتاب |
| `grade`, `subject` | required برای محتوای آموزشی | اعمال scope |
| `curriculum_version` | required برای نسخه‌بندی | جلوگیری از اختلاط نسخه‌ها |
| `chapter`, `lesson` | required در صورت وجود | citation دقیق |
| `page_start`, `page_end` | required برای PDF صفحه‌دار | ارجاع کاربر |
| `content_hash` | required | idempotency و invalidation |
| `index_generation` | required در نتیجه | trace نسخه index |

خروجی grounded باید citation ساختاریافته داشته باشد، نه فقط متن آزاد:

```json
{
  "source_id": "official-book-7-science",
  "page": 42,
  "chunk_id": 123,
  "quote_ref": "chunk-123"
}
```

مدل فقط citationهایی را می‌تواند اعلام کند که در context دریافت‌شده وجود دارند. اگر
صفحه یا شناسه موجود نیست، نباید حدس زده شود؛ citation ناقص باید حذف یا به‌عنوان ناقص
علامت‌گذاری شود.

## 4. Confidence و تصمیم پاسخ

confidence یک سیگنال عملیاتی برای gate کردن پاسخ است، نه ادعای احتمال درست‌بودن علمی.
در نسخه اول از ترکیب قابل‌ردیابی زیر استفاده می‌شود:

```text
evidence_score = weighted retrieval score
                 + metadata/scope validity
                 + source agreement
```

وزن‌ها و آستانه‌ها باید با مجموعه ارزیابی فارسی و بازخورد معلم calibrate شوند. تا قبل
از benchmark، مقدار ثابت نباید به‌عنوان آستانه production معرفی شود. تصمیم‌ها:

- **Enough evidence**: حداقل دو قطعه مستقل یا یک قطعه مستقیم و معتبر، citation معتبر و
  score بالاتر از آستانه کالیبره‌شده؛ پاسخ grounded مجاز است.
- **Low confidence**: شواهد ضعیف یا غیرمستقیم؛ پاسخ باید عدم قطعیت را آشکار کند و از
  ادعای قطعی پرهیز کند.
- **No evidence**: نتیجه‌ای پس از policy/scope باقی نمانده؛ پاسخ استاندارد «اطلاعات
  کافی در منابع مجاز یافت نشد» و بدون تولید واقعیت جدید.
- **Conflict**: منابع معتبر با نسخه یا ادعای متفاوت؛ پاسخ باید تعارض و citation هر دو
  منبع را گزارش کند و در صورت نیاز از کاربر نسخه/سال را بپرسد.

## 5. Source Guardian و مرز prompt

Source Guardian مسئول ساخت context است، نه داوری محتوای علمی. ورودی منبع همیشه داده
غیرقابل‌اعتماد تلقی می‌شود. قواعد اجباری:

1. متن منبع در delimiter مستقل قرار گیرد و با escaping مناسب وارد prompt شود.
2. دستورهای داخل منبع، حتی اگر شبیه system/developer message باشند، هرگز authority
   پیدا نکنند.
3. پرسش کاربر و دستور policy خارج از مرز source قرار گیرند.
4. context فقط از نتایج مجاز همان scope و index generation ساخته شود.
5. طول متن، تعداد قطعه و مجموع token پیش از ارسال به AI Gateway محدود شود.
6. خروجی مدل از نظر وجود citationهای اعلام‌شده با context تطبیق داده شود؛ citation
   خارج از context رد یا پاسخ به حالت unsupported منتقل شود.
7. متن کامل منبع در log ذخیره نشود؛ فقط شناسه، صفحه، generation و latency ثبت شود.

## 6. نقطه اتصال به AI Gateway

جریان پیشنهادی:

```text
Tutor/Exam/Teacher feature
        -> RetrievalRequest
        -> Retriever
        -> Source Guardian
        -> grounded prompt + citation manifest
        -> AI Gateway / Model Router
        -> output citation validation
        -> response + grounding status
```

AI Gateway نباید مستقیماً به دیتابیس یا vector store متصل شود. سرویس‌های آموزشی نیز
نباید prompt boundary را خودشان بازسازی کنند؛ یک Source Guardian مشترک باید مسئول آن
باشد. ثبت AI usage باید مانند مسیرهای فعلی ادامه پیدا کند و secret یا متن حساس را ثبت نکند.

## 7. خطا و رفتار قابل مشاهده

| وضعیت | رفتار backend | رفتار کاربر |
| --- | --- | --- |
| no source | پاسخ کنترل‌شده، بدون call غیرضروری به مدل | «منبع کافی پیدا نشد» |
| low confidence | پاسخ مشروط یا درخواست clarification | نمایش عدم قطعیت و citationهای موجود |
| conflicting sources | گزارش تعارض، اولویت نسخه صریح | درخواست انتخاب نسخه/سال |
| retriever timeout | خطای قابل‌ردیابی و retry policy محدود | خطای موقت، بدون hallucinated answer |
| AI timeout/error | حفظ grounding status و audit event | تلاش دوباره کنترل‌شده |
| invalid citation | پاسخ unsupported یا حذف citation | عدم نمایش ارجاع ساختگی |

## 8. امنیت و isolation

- scope/tenant باید در query و policy اجباری باشد؛ فیلترکردن پس از retrieval کافی نیست.
- URI، credential، prompt و متن خام منبع نباید در log یا telemetry عمومی قرار گیرد.
- حذف یا اصلاح سند باید generation قبلی را invalidate کند تا نتیجه stale به پاسخ نرسد.
- منبع خارجی فقط پس از validation نوع، اندازه، scheme و policy ingest قابل استفاده است.
- prompt injection، داده خصوصی و cross-tenant leakage در تست‌های منفی پوشش داده شوند.

## 9. معیار پذیرش Proposal در مرحله implementation

پس از تأیید فرمانده، implementation باید حداقل این تست‌ها را اضافه کند:

- contract tests برای empty query، limit، scope و deterministic ordering؛
- tests برای no-source، low-confidence و conflicting-source؛
- citation validation و رد citation خارج از context؛
- prompt-injection regression با متن فارسی و انگلیسی؛
- isolation بین scopeها و invalidation generation؛
- integration test برای PostgreSQL/pgvector و lexical fallback؛
- benchmark فارسی برای Recall@K، nDCG@K، citation accuracy و P50/P95 latency.

## 10. مشاوره تیمی و محدودیت این نشست

طبق پروتکل پروژه، این موضوع نیازمند بررسی معماری و امنیتی Gemini، Claude، Qwen و GLM
است. کانال‌های مستقل این Agentها در محیط فعلی قابل‌دسترسی نیستند؛ بنابراین هیچ پاسخ
ساختگی یا نسبت‌داده‌شده‌ای در این سند وجود ندارد. این Proposal بر اساس repository واقعی،
`app/services/rag.py`، `app/services/document_ingestion.py`، `app/services/vector_store.py`
و `docs/RAG_ARCHITECTURE_PROPOSAL.md` تهیه شده و قبل از هر implementation به بررسی
فرمانده نیاز دارد.

## تصمیم موردنیاز فرمانده

آیا قرارداد Retrieval، Source Metadata، citation، confidence states، prompt boundary
و failure handling فوق تأیید می‌شود تا مرحله بعدی فقط به implementation contract tests
و adapterهای لازم اختصاص یابد؟
