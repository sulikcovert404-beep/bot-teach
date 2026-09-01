# RAG ARCHITECTURE PROPOSAL

وضعیت این سند: **پیشنهاد معماری برای بررسی فرمانده**. این سند تصمیم نهایی، migration،
dependency یا تغییر production ایجاد نمی‌کند.

## 1. اهداف و مرزها

RAG باید پاسخ‌های آموزشی را به نسخه و صفحه‌ی مشخص کتاب درسی ایران متصل کند، از نشت
دستورهای موجود در متن منبع جلوگیری کند، و امکان تعویض embedding provider و vector
store را بدون بازنویسی سرویس‌های آموزشی فراهم کند.

منبع حقیقت برای هویت کتاب، فصل، درس و مجوز انتشار در دیتابیس رابطه‌ای باقی می‌ماند؛
vector store فقط index قابل بازسازی است و نباید تنها محل نگهداری متن یا metadata باشد.

## 2. جریان پیشنهادی ingestion

```text
PDF / Book / Trusted URL
        |
        v
Parser + MIME/size/security validation
        |
        v
Cleaning + normalization (Unicode/Persian digits/whitespace)
        |
        v
Structure and metadata extraction
        |
        v
Semantic chunking with page/section boundaries
        |
        v
EmbeddingService (provider-neutral)
        |
        v
Vector index + relational source record
        |
        v
Hybrid retrieval (vector + lexical filters)
        |
        v
Optional reranking + deduplication
        |
        v
Source Guardian context boundary
        |
        v
LLM generation with citations and confidence
```

هر ingestion باید idempotency key داشته باشد: `source_id + content_hash + parser_version +
embedding_model`. تغییر parser یا embedding model یک index generation جدید می‌سازد و
index قبلی تا پایان reindex قابل استفاده می‌ماند.

## 3. Metadata مدل کتاب‌های درسی ایران

| فیلد | سطح | توضیح | الزام |
| --- | --- | --- | --- |
| `grade` | کتاب | پایه تحصیلی | required |
| `field` | کتاب | رشته/شاخه | optional |
| `book` | کتاب | عنوان رسمی کتاب | required |
| `subject` | کتاب | درس | required |
| `publisher` | کتاب | ناشر/مرجع رسمی | required برای منبع رسمی |
| `year` | کتاب | سال انتشار | optional |
| `curriculum_version` | کتاب | نسخه برنامه درسی | required برای نسخه‌بندی |
| `chapter` | chunk | شماره و عنوان فصل | required |
| `lesson` | chunk | شماره و عنوان درس | required |
| `topic` | chunk | موضوع استخراج‌شده | optional |
| `page` | chunk | صفحه چاپی | required اگر PDF صفحه‌دار باشد |
| `source_type` | document | `official_book`, `teacher_note`, `approved_reference` | required |

شناسه‌ی پایدار chunk پیشنهادی: `document_version_id + page + chunk_index + chunk_hash`.
متن خام، متن پاک‌سازی‌شده، metadata و embedding version باید قابل ردیابی و حذف باشند؛
حذف منبع باید از پاسخ‌های آینده نیز جلوگیری کند.

## 4. قراردادهای سرویس

```python
class EmbeddingService(Protocol):
    async def embed(self, request: EmbeddingRequest) -> list[float]: ...

class Retriever(Protocol):
    async def retrieve(self, request: RetrievalRequest) -> list[RetrievedChunk]: ...
```

`EmbeddingRequest` شامل متن، `task_type`، مدل و ابعاد خروجی است. provider نباید API key
را در log یا exception قرار دهد. provider فعلی Gemini با endpoint رسمی
`models.embedContent` سازگار است؛ providerهای OpenAI و local در آینده باید همین قرارداد
را پیاده کنند.

`RetrievalRequest` باید شامل `query`, `top_k`, فیلترهای metadata، `tenant/scope` و حداقل
`index_generation` باشد. `RetrievedChunk` شامل متن، source id، صفحه، امتیاز خام، امتیاز
نرمال‌شده، مدل embedding و نسخه‌ی index است.

## 5. Retrieval و Source Guardian

1. query نرمال‌سازی و از نظر طول/نرخ محدود می‌شود.
2. فیلترهای مجوز، پایه، درس و نسخه curriculum پیش از جست‌وجو اعمال می‌شوند.
3. جست‌وجوی vector و lexical به‌صورت hybrid انجام می‌شود؛ نتیجه‌ها deduplicate می‌شوند.
4. reranker اختیاری فقط روی top-N محدود اجرا می‌شود.
5. آستانه‌ی confidence و حداقل evidence بررسی می‌شود؛ نبود evidence باید پاسخ
   «اطلاعات کافی وجود ندارد» تولید کند.
6. Source Guardian متن را به‌عنوان داده‌ی غیرقابل‌اعتماد داخل مرز مشخص قرار می‌دهد،
   دستورات داخل منبع را بی‌اثر می‌کند و source id/page را کنار هر قطعه نگه می‌دارد.
7. خروجی باید citationهای منبع و page را برگرداند؛ confidence به‌تنهایی نباید به‌عنوان
   حقیقت آموزشی نمایش داده شود.

امتیاز نهایی پیشنهادی ابتدا با وزن‌های قابل تنظیم محاسبه شود:
`final = w_vector * vector_score + w_lexical * lexical_score + w_metadata * filter_match`.
این وزن‌ها باید با مجموعه‌ی ارزیابی فارسی و بازخورد معلم calibrate شوند، نه با حدس.

## 6. مقایسه‌ی گزینه‌های vector store

| گزینه | هزینه/نگهداری | مقیاس و latency | سازگاری با معماری فعلی | VPS کوچک |
| --- | --- | --- | --- | --- |
| PostgreSQL + pgvector | کمترین اجزای عملیاتی؛ backup واحد | مناسب شروع و متوسط؛ با index/partition نیازمند tuning | بیشترین؛ metadata و transaction مشترک | مناسب |
| Supabase Vector | عملیات کمتر در صورت استفاده از Supabase؛ هزینه‌ی سرویس و وابستگی بیرونی | مناسب متوسط تا بالا، تابع plan/region | متوسط؛ نیازمند شبکه و secret خارجی | مناسب فقط با سرویس بیرونی |
| Qdrant | یک سرویس جدا؛ self-host یا managed | مناسب برای retrieval برداری و رشد مستقل | متوسط؛ sync و consistency باید طراحی شود | ممکن، ولی RAM/backup اضافه |
| Pinecone | کمترین عملیات زیرساختی؛ هزینه‌ی مصرف و vendor lock-in | مناسب scale بالا و latency قابل پیش‌بینی با plan | پایین‌تر؛ metadata و داده‌ی اصلی جدا می‌مانند | برای VPS محلی مناسب نیست |
| Weaviate | سرویس/cluster مستقل و پیچیدگی بیشتر | مناسب scale بالا و قابلیت‌های غنی | متوسط؛ integration و عملیات بیشتر | برای شروع کوچک سنگین‌تر |

### پیشنهاد مرحله‌ای برای تصمیم‌گیری

برای V1 روی VPS کوچک، گزینه‌ی پیش‌فرض قابل بررسی **PostgreSQL + pgvector** است، چون
با دیتابیس فعلی، backup/restore و فیلترهای رابطه‌ای هم‌راستا می‌ماند. `VectorStore` باید
از ابتدا به‌صورت interface طراحی شود تا در صورت عبور از ظرفیت یا نیاز به latency مستقل،
Qdrant یا سرویس managed بدون تغییر `Retriever` جایگزین شود. این پیشنهاد تا تأیید فرمانده
تصمیم نهایی محسوب نمی‌شود.

## 7. ظرفیت و هزینه

هزینه‌ی اصلی شامل embedding در زمان ingestion، storage/index، query و عملیات backup است.
برای کنترل هزینه:

- embedding فقط هنگام تغییر content hash تولید شود؛
- batch و retry با backoff استفاده شود؛
- ابعاد embedding و top-K با benchmark فارسی انتخاب شود؛
- cache query با invalidation بر اساس index generation داشته باشیم؛
- reindex در background و با محدودیت concurrency انجام شود؛
- متن اصلی در storage رابطه‌ای بماند و vector index قابل بازسازی باشد.

آستانه‌ی مهاجرت از PostgreSQL باید با benchmark واقعی تعیین شود: تعداد chunk، حجم RAM،
P95 latency، نرخ query، زمان reindex و هزینه‌ی ماهانه. قبل از داشتن این اعداد، ادعای
مقیاس‌پذیری یا انتخاب قطعی storage معتبر نیست.

## 8. امنیت و حریم خصوصی

- فقط URIهای `https`/منابع مجاز ingest شوند و credential داخل URI ممنوع باشد.
- فایل و متن با سقف اندازه و MIME واقعی بررسی شوند؛ parser sandbox شود.
- هر chunk همراه با tenant/scope و policy دسترسی ذخیره شود.
- حذف/اصلاح منبع، index generation را invalidate کند.
- API keyها فقط از secret manager/environment خوانده شوند و هرگز در vector payload یا log
  قرار نگیرند.
- prompt injection داخل منبع تهدید داده‌ای است و باید در Source Guardian مهار شود.

## 9. سنجه‌ها و معیار پذیرش implementation

قبل از انتخاب نهایی، مجموعه‌ی ارزیابی شامل queryهای فارسی هر پایه/درس تهیه شود و حداقل
این موارد اندازه‌گیری شوند:

- Recall@K و nDCG@K برای source/page درست؛
- citation accuracy و نرخ پاسخ بدون evidence؛
- P50/P95 retrieval latency؛
- زمان و هزینه‌ی reindex؛
- نرخ خطای provider و موفقیت retry؛
- مصرف RAM/CPU و حجم index؛
- صحت حذف و isolation بین scopeها.

Implementation بعدی فقط پس از تأیید این سند باید migration، adapter منتخب، hybrid retriever،
benchmark و end-to-end tests را اضافه کند.

## منابع فنی

- [Gemini Embeddings API](https://ai.google.dev/api/embeddings)
- [Gemini Embedding model](https://ai.google.dev/gemini-api/docs/models/gemini-embedding-001)
- [pgvector](https://github.com/pgvector/pgvector)
- [Qdrant documentation](https://qdrant.tech/documentation/)
- [Pinecone documentation](https://docs.pinecone.io/)
- [Weaviate documentation](https://weaviate.io/developers/weaviate)
