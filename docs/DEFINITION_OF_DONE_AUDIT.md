# Definition of Done Audit

این سند وضعیت واقعی مخزن را نشان می‌دهد. `IMPLEMENTED` به‌تنهایی به معنی
`DEPLOYED` یا `PRODUCTION VERIFIED` نیست.

## وضعیت فعلی

| Requirement | Repository evidence | Status |
| --- | --- | --- |
| Backend و API versioning | FastAPI و `/api/v1` | TESTED |
| Telegram Mini App و integration | static Mini App، auth و webhook | TESTED |
| Authentication، authorization و roles | JWT، Telegram HMAC، role/entitlement dependencies | TESTED |
| Subscription و entitlement | models، service و routeها | TESTED |
| AI Gateway، router و Gemini | provider، retry، timeout، token cap و usage metadata | TESTED |
| RAG و Source Guardian | retrieval، PostgreSQL similarity، prompt boundary escaping | TESTED |
| Curriculum | Book/Chapter/Lesson و authoring audit | TESTED |
| Tutor و قابلیت‌های آموزشی AI | tutor، summary، question، exam و correction | TESTED |
| Flashcards و Study Planner | model، service و routeها | TESTED |
| Analytics و Adaptive Learning | summary، events و recommendation | TESTED |
| Teacher Assistant | lesson-plan route و usage logging | TESTED |
| PDF / Worksheet | renderer و routeها | TESTED |
| Admin foundations | audit، billing و AI usage summary | TESTED |
| Payment foundations | intent، callback، provider adapter و plan binding | TESTED |
| Logging، metrics و security headers | middleware و Prometheus endpoint | TESTED |
| Rate limiting | in-memory و Redis middleware | TESTED |
| Tests، lint، type-check و dependency audit | CI و local validation | TESTED |
| Docker deployment | Dockerfile و Compose config | IMPLEMENTED; ENVIRONMENT-VERIFIED PENDING |
| Documentation | README، operations، migration و security runbooks | IMPLEMENTED |
| Backup / migration strategy | Alembic chain، backup script و CI archive check | IMPLEMENTED; RESTORE DRILL PENDING |
| Production health checks | liveness/readiness و migration/Redis checks | TESTED; STAGING PENDING |

## موارد لازم پیش از اعلام Production

1. اجرای staging واقعی با Docker daemon، PostgreSQL و Redis.
2. اجرای backup/restore drill روی PostgreSQL جداگانه و ثبت نتیجه.
3. revoke/rotate credential افشاشده و remediation تاریخچهٔ Git طبق
   [`SECURITY_ROTATION.md`](SECURITY_ROTATION.md).
4. اتصال و آزمون Gemini، Telegram و payment provider واقعی در sandbox/staging.
5. secret manager و observability متمرکز، شامل metrics و alerting.
6. ارزیابی مقیاس‌پذیر embedding/vector store برای RAG.
7. اجرای audit نهایی روی محیط staging و تأیید همهٔ مسیرهای اصلی end-to-end.

تا وقتی موارد این بخش شواهد اجرایی نداشته باشند، وضعیت پروژه
`Production-ready` اعلام نمی‌شود.
