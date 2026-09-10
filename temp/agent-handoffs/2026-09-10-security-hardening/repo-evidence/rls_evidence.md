
## Source: app/db/models.py
from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EmbeddingVector(TypeDecorator[Any]):
    """Use pgvector in PostgreSQL and JSON for SQLite tests/development."""

    impl = JSON
    cache_ok = True
    comparator_factory = Vector.comparator_factory

    def __init__(self, dimensions: int = 768) -> None:
        super().__init__()
        self.dimensions = dimensions

    def load_dialect_impl(self, dialect):  # type: ignore[no-untyped-def]
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(self.dimensions))
        return dialect.type_descriptor(JSON())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="STUDENT")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    identities: Mapped[list[Identity]] = relationship(back_populates="user")


class Identity(Base):
    __tablename__ = "identities"
    __table_args__ = (UniqueConstraint("provider", "subject"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    subject: Mapped[str] = mapped_column(String(255))
    user: Mapped[User] = relationship(back_populates="identities")


class TelegramUpdate(Base):
    __tablename__ = "telegram_updates"

    id: Mapped[int] = mapped_column(primary_key=True)
    update_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    grade: Mapped[str | None] = mapped_column(String(64), index=True)
    subject: Mapped[str | None] = mapped_column(String(128), index=True)
    chapters: Mapped[list[Chapter]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(default=0)
    book: Mapped[Book] = relationship(back_populates="chapters")
    lessons: Mapped[list[Lesson]] = relationship(
        back_populates="chapter", cascade="all, delete-orphan"
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(default=0)
    chapter: Mapped[Chapter] = relationship(back_populates="lessons")


class Flashcard(Base):
    __tablename__ = "flashcards"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    book_id: Mapped[int | None] = mapped_column(ForeignKey("books.id"), index=True)
    front: Mapped[str] = mapped_column(String(2_000))
    back: Mapped[str] = mapped_column(String(4_000))
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    interval_days: Mapped[int] = mapped_column(Integer, default=0)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    daily_minutes: Mapped[int] = mapped_column()
    max_days: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tasks: Mapped[list[StudyPlanTask]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="StudyPlanTask.day_number"
    )


class StudyPlanTask(Base):
    __tablename__ = "study_plan_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("study_plans.id"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    day_number: Mapped[int] = mapped_column()
    title: Mapped[str] = mapped_column(String(255))
    minutes: Mapped[int] = mapped_column()
    completed: Mapped[bool] = mapped_column(default=False)
    plan: Mapped[StudyPlan] = relationship(back_populates="tasks")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(32), default="FREE")
    active_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    generated_content: Mapped[str | None] = mapped_column(String(20_000))
    correction_content: Mapped[str | None] = mapped_column(String(20_000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    questions: Mapped[list[ExamQuestion]] = relationship(
        back_populates="exam", cascade="all, delete-orphan", order_by="ExamQuestion.position"
    )


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    prompt: Mapped[str] = mapped_column(String(2_000))
    options: Mapped[str] = mapped_column(String(4_000))
    correct_option: Mapped[str] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(default=0)
    exam: Mapped[Exam] = relationship(back_populates="questions")


class LearningEvent(Base):
    __tablename__ = "learning_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    duration_seconds: Mapped[int] = mapped_column(default=0)
    score: Mapped[float | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    provider_transaction_id: Mapped[str] = mapped_column(String(255), unique=True)
    checkout_url: Mapped[str | None] = mapped_column(String(2_000), nullable=True)
    plan: Mapped[str] = mapped_column(String(32), default="FREE")
    amount: Mapped[int] = mapped_column()
    currency: Mapped[str] = mapped_column(String(8), default="IRR")
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(255))
    metadata_json: Mapped[str] = mapped_column(String(4_000), default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AIUsageEvent(Base):
    __tablename__ = "ai_usage_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    task_type: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(128))
    requested_tokens: Mapped[int] = mapped_column()
    charged_tokens: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    uri: Mapped[str | None] = mapped_column(String(2_000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    chunks: Mapped[list[SourceChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class SourceChunk(Base):
    __tablename__ = "source_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id"), index=True)
    chunk_index: Mapped[int] = mapped_column()
    text: Mapped[str] = mapped_column(String(8_000))
    page: Mapped[int | None] = mapped_column()
    source_type: Mapped[str | None] = mapped_column(String(64), index=True)
    book_id: Mapped[int | None] = mapped_column(ForeignKey("books.id"), index=True)
    grade: Mapped[str | None] = mapped_column(String(64), index=True)
    subject: Mapped[str | None] = mapped_column(String(128), index=True)
    chapter: Mapped[str | None] = mapped_column(String(255), index=True)
    lesson: Mapped[str | None] = mapped_column(String(255), index=True)
    page_start: Mapped[int | None] = mapped_column()
    page_end: Mapped[int | None] = mapped_column()
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    embedding_model: Mapped[str | None] = mapped_column(String(128), index=True)
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingVector(768), nullable=True)
    document: Mapped[SourceDocument] = relationship(back_populates="chunks")


class ContentVersion(Base):
    """Immutable processing snapshot for a logical source document."""

    __tablename__ = "content_versions"
    __table_args__ = (UniqueConstraint("source_document_id", "version_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id"), index=True)
    owner_teacher_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    processing_state: Mapped[str] = mapped_column(String(32), default="UPLOADED", index=True)
    review_state: Mapped[str] = mapped_column(String(32), default="DRAFT", index=True)
    vector_sync_state: Mapped[str] = mapped_column(String(32), default="VECTOR_PENDING", index=True)
    source_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    extracted_hash: Mapped[str | None] = mapped_column(String(64))
    pipeline_digest: Mapped[str | None] = mapped_column(String(64), index=True)
    parser_version: Mapped[str | None] = mapped_column(String(128))
    ocr_config_version: Mapped[str | None] = mapped_column(String(128))
    normalizer_version: Mapped[str | None] = mapped_column(String(128))
    chunker_version: Mapped[str | None] = mapped_column(String(128))
    provenance_json: Mapped[str] = mapped_column(String(8000), default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source_document: Mapped[SourceDocument] = relationship()


class ContentGenerationJob(Base):
    __tablename__ = "content_generation_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    content_version_id: Mapped[int] = mapped_column(ForeignKey("content_versions.id"), index=True)
    asset_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    tenant_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    generation_parameters_hash: Mapped[str] = mapped_column(String(64))
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    output_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    __table_args__ = (UniqueConstraint("content_version_id", "asset_type", "generation_parameters_hash"),)


class GenerationAttempt(Base):
    __tablename__ = "generation_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("content_generation_jobs.id"), index=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    outcome: Mapped[str] = mapped_column(String(32))
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    token_usage: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GeneratedAsset(Base):
    __tablename__ = "generated_assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("content_generation_jobs.id"), unique=True)
    asset_type: Mapped[str] = mapped_column(String(64), index=True)
    content_json: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    review_state: Mapped[str] = mapped_column(String(32), default="DRAFT", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PublicationPointer(Base):
    """Single atomically replaceable published version per logical document."""

    __tablename__ = "publication_pointers"
    __table_args__ = (UniqueConstraint("source_document_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id"), index=True)
    content_version_id: Mapped[int] = mapped_column(ForeignKey("content_versions.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TeacherContentPublication(Base):
    """Tenant-scoped publication of a content version to a classroom."""
    __tablename__ = "teacher_content_publications"
    __table_args__ = (UniqueConstraint("content_version_id", "classroom_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    content_version_id: Mapped[int] = mapped_column(ForeignKey("content_versions.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="PUBLISHED", index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TransactionalOutboxEvent(Base):
    """Retry-safe event emitted in the same transaction as publication changes."""

    __tablename__ = "transactional_outbox_events"
    __table_args__ = (UniqueConstraint("event_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(64))
    aggregate_id: Mapped[str] = mapped_column(String(255), index=True)
    payload_json: Mapped[str] = mapped_column(String(12000), default="{}")
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IngestionIdempotencyKey(Base):
    """Deduplicates retried ingestion jobs without mutating existing content."""

    __tablename__ = "ingestion_idempotency_keys"
    __table_args__ = (UniqueConstraint("idempotency_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_documents.id"), index=True
    )
    request_hash: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="ACCEPTED", index=True)
    response_json: Mapped[str] = mapped_column(String(8000), default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BetaFeedback(Base):
    """Beta user feedback on answers, sources, UI and content gaps."""

    __tablename__ = "beta_feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    query: Mapped[str] = mapped_column(String(1000))
    rating: Mapped[int] = mapped_column(Integer)  # 1 to 5 stars or 1/-1
    feedback_type: Mapped[str] = mapped_column(String(64), index=True)  # answer_quality, source_usefulness, ui_issue, missing_content
    comment: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BetaQualityAudit(Base):
    """Telemetry log for quality metrics: latency, citations count, content gaps."""

    __tablename__ = "beta_quality_audits"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    query: Mapped[str] = mapped_column(String(1000))
    model: Mapped[str] = mapped_column(String(128))
    has_citations: Mapped[bool] = mapped_column(Boolean, default=False)
    citations_count: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    is_success: Mapped[bool] = mapped_column(Boolean, default=True)
    content_gap_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Experiment(Base):
    """A/B and Multivariate Product Experiments."""

    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)  # ACTIVE, PAUSED, CONCLUDED
    target_metric: Mapped[str] = mapped_column(String(64), default="activation_rate")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExperimentVariant(Base):
    """Variants belonging to an experiment (e.g., Control A, Challenger B)."""

    __tablename__ = "experiment_variants"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"), index=True)
    key: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    traffic_allocation_pct: Mapped[int] = mapped_column(Integer, default=50)
    conversions_count: Mapped[int] = mapped_column(Integer, default=0)
    impressions_count: Mapped[int] = mapped_column(Integer, default=0)
    config_json: Mapped[str] = mapped_column(String(4000), default="{}")


class UserEvent(Base):
    """User behavioral and lifecycle telemetry events (e.g. login, query, exam, upgrade)."""

    __tablename__ = "user_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    event_name: Mapped[str] = mapped_column(String(128), index=True)
    stage: Mapped[str] = mapped_column(String(64), default="LEARNING_USER", index=True)  # NEW, ACTIVATED, LEARNING, RETURNING, PREMIUM_INTENT
    experiment_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    variant_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    properties_json: Mapped[str] = mapped_column(String(4000), default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class FeatureUsageEvent(Base):
    """Aggregated or discrete usage of specific platform features for adoption tracking."""

    __tablename__ = "feature_usage_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    feature_key: Mapped[str] = mapped_column(String(64), index=True)  # ai_tutor, exams, flashcards, referral, upgrade_page
    action: Mapped[str] = mapped_column(String(64), default="VIEW")
    session_duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class DecisionInsight(Base):
    """AI Product Analyst insights, observations, and recommendations."""

    __tablename__ = "decision_insights"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(64), index=True)  # RETENTION, CONVERSION, CONTENT_DEMAND, ACTIVATION
    observation: Mapped[str] = mapped_column(String(2000))
    evidence_metric: Mapped[str] = mapped_column(String(500))
    recommendation: Mapped[str] = mapped_column(String(2000))
    impact_estimate: Mapped[str] = mapped_column(String(255))
    confidence_score_pct: Mapped[int] = mapped_column(Integer, default=90)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudentKnowledgeNode(Base):
    """Knowledge Graph nodes representing mastery, weaknesses, and prerequisites for a student."""

    __tablename__ = "student_knowledge_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject: Mapped[str] = mapped_column(String(64), index=True)
    topic: Mapped[str] = mapped_column(String(128), index=True)
    subtopic: Mapped[str] = mapped_column(String(128))
    mastery_level: Mapped[str] = mapped_column(String(32), default="DEVELOPING")  # MASTERED, DEVELOPING, WEAKNESS
    mastery_score_pct: Mapped[float] = mapped_column(Float, default=50.0)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0)
    last_practiced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdaptiveStudyPlan(Base):
    """Personalized dynamic study plans based on student goals, available hours and weaknesses."""

    __tablename__ = "adaptive_study_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_type: Mapped[str] = mapped_column(String(32), default="WEEKLY")  # DAILY, WEEKLY, KONKUR_INTENSIVE
    target_goal: Mapped[str] = mapped_column(String(255))
    weekly_hours_allocated: Mapped[int] = mapped_column(Integer, default=14)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    plan_details_json: Mapped[str] = mapped_column(String(8000), default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdaptiveQuestionItem(Base):
    """Curated adaptive questions matched to student current mastery (Easy -> Medium -> Hard)."""

    __tablename__ = "adaptive_question_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(64), index=True)
    topic: Mapped[str] = mapped_column(String(128), index=True)
    question_type: Mapped[str] = mapped_column(String(32), default="PRACTICE")  # PRACTICE, REINFORCEMENT, CHALLENGE
    difficulty_level: Mapped[str] = mapped_column(String(32), default="MEDIUM")  # EASY, MEDIUM, HARD
    question_text: Mapped[str] = mapped_column(String(2000))
    correct_answer: Mapped[str] = mapped_column(String(1000))
    options_json: Mapped[str] = mapped_column(String(2000), default="[]")
    citation: Mapped[str] = mapped_column(String(255))


class ParentProfile(Base):
    """Parent user profile and settings."""

    __tablename__ = "parent_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    preferred_communication: Mapped[str] = mapped_column(String(32), default="TELEGRAM")
    notification_frequency: Mapped[str] = mapped_column(String(32), default="WEEKLY")  # DAILY, WEEKLY, CRITICAL_ONLY
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GuardianLink(Base):
    """Secure link associating a parent to their child/student with consent verification."""

    __tablename__ = "guardian_links"
    __table_args__ = (UniqueConstraint("parent_user_id", "student_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(32), default="PARENT")  # MOTHER, FATHER, GUARDIAN
    status: Mapped[str] = mapped_column(String(32), default="VERIFIED", index=True)  # PENDING, VERIFIED, REVOKED
    consent_granted: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SchoolOrganization(Base):
    """Schools, institutes, and academic organizations."""

    __tablename__ = "school_organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    province: Mapped[str] = mapped_column(String(64), default="تهران")
    total_students_enrolled: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TeacherParentInteraction(Base):
    """Targeted educational recommendations and report cards sent from teacher to parent."""

    __tablename__ = "teacher_parent_interactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    parent_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    interaction_type: Mapped[str] = mapped_column(String(32), default="WEEKLY_REPORT")  # WEEKLY_REPORT, RECOMMENDATION, ALERT
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(String(4000))
    action_item: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OperationsAnomalyAlert(Base):
    """Autonomous operation alerts detected before human intervention."""

    __tablename__ = "operations_anomaly_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(64), index=True)  # LEARNING_DROP, QUALITY_ISSUE, CONTENT_GAP, SYSTEM_ANOMALY
    severity: Mapped[str] = mapped_column(String(32), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(2000))
    automated_recommendation: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")  # ACTIVE, RESOLVED, AUTO_REMEDIATED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EducationalHealthMetric(Base):
    """Calculated health scores for student, class, school and platform."""

    __tablename__ = "educational_health_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)  # STUDENT, CLASS, SCHOOL, PLATFORM
    entity_id: Mapped[str] = mapped_column(String(64), index=True)
    health_score: Mapped[float] = mapped_column(Float, default=85.0)
    risk_level: Mapped[str] = mapped_column(String(32), default="LOW")  # LOW, MEDIUM, HIGH
    factors_json: Mapped[str] = mapped_column(String(4000), default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContentRoadmapItem(Base):
    """Data-driven suggestions for adding textbooks, chapters, or test items."""

    __tablename__ = "content_roadmap_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(64), index=True)
    grade: Mapped[str] = mapped_column(String(32))
    recommended_content: Mapped[str] = mapped_column(String(255))
    reason_evidence: Mapped[str] = mapped_column(String(2000))
    priority_rank: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="PROPOSED")  # PROPOSED, IN_PROGRESS, COMPLETED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScaleScenarioResult(Base):
    """Simulated growth cohorts (100, 500, 1000, 5000 users) with cost and revenue projections."""

    __tablename__ = "scale_scenario_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_size: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    projected_mrr_irr: Mapped[int] = mapped_column(Integer)
    projected_ai_cost_irr: Mapped[int] = mapped_column(Integer)
    vps_servers_needed: Mapped[int] = mapped_column(Integer, default=1)
    db_capacity_gb: Mapped[int] = mapped_column(Integer, default=20)
    gross_margin_pct: Mapped[float] = mapped_column(Float, default=70.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SchoolExpansionScenario(Base):
    """B2B Institutional scaling model (1, 10, 100 schools)."""

    __tablename__ = "school_expansion_scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    schools_count: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    total_students: Mapped[int] = mapped_column(Integer)
    total_teachers: Mapped[int] = mapped_column(Integer)
    annual_contract_value_irr: Mapped[int] = mapped_column(Integer)
    support_cost_irr: Mapped[int] = mapped_column(Integer)
    net_operating_profit_irr: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- CUSTOMER SUCCESS & LAUNCH OPERATIONS CENTER MODELS ---

class SupportTicket(Base):
    """Customer support tickets filed by students, parents, or teachers."""

    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(50), index=True)  # Technical, Educational, Billing, Content, Account
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")  # LOW, MEDIUM, HIGH, URGENT
    subject: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="OPEN")  # OPEN, IN_PROGRESS, RESOLVED, CLOSED
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserFeedbackMetric(Base):
    """CSAT, NPS, and qualitative user satisfaction ratings."""

    __tablename__ = "user_feedback_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    metric_type: Mapped[str] = mapped_column(String(20), index=True)  # CSAT (1-5), NPS (0-10)
    score: Mapped[int] = mapped_column(Integer)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    feature_tag: Mapped[str | None] = mapped_column(String(100), nullable=True)  # ai_tutor, exams, billing, etc.
    sentiment: Mapped[str] = mapped_column(String(20), default="NEUTRAL")  # POSITIVE, NEUTRAL, NEGATIVE
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LaunchIncident(Base):
    """Operational incidents during launch (AI degradation, auth spikes, rate limits, token cost surges)."""

    __tablename__ = "launch_incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_type: Mapped[str] = mapped_column(String(50), index=True)  # AI_ERROR, LATENCY_SPIKE, AUTH_FAILURE, COST_SURGE
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    title: Mapped[str] = mapped_column(String(255))
    impact_summary: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="INVESTIGATING")  # INVESTIGATING, MITIGATED, RESOLVED
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    mitigation_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# --- ADVANCED AI TUTOR DIFFERENTIATION MODELS ---

class StudentMistakeLog(Base):
    """Tracks recurring conceptual mistakes, confusion pairs, and remediation status."""

    __tablename__ = "student_mistake_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subject: Mapped[str] = mapped_column(String(50), index=True)  # زیست, فیزیک, شیمی, ریاضی
    concept_title: Mapped[str] = mapped_column(String(100), index=True)  # e.g., "جرم در برابر وزن"
    confusion_details: Mapped[str] = mapped_column(Text)
    error_count: Mapped[int] = mapped_column(Integer, default=1)
    remediation_recommendation: Mapped[str] = mapped_column(Text)
    is_mastered: Mapped[bool] = mapped_column(Boolean, default=False)
    last_error_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CoachPersonaSetting(Base):
    """Configurable AI Tutor personality style per student."""

    __tablename__ = "coach_persona_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    persona_style: Mapped[str] = mapped_column(String(30), default="MOTIVATIONAL")  # STRICT, MOTIVATIONAL, KONKUR_TACTICAL, CALM_SUPPORTIVE
    socratic_guidance_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    voice_audio_speed: Mapped[float] = mapped_column(Float, default=1.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# --- EDUCATIONAL KNOWLEDGE GRAPH & CONTENT INTELLIGENCE MODELS ---

class KnowledgeConceptNode(Base):
    """Concept node in the educational ontology (Subject -> Chapter -> Concept)."""

    __tablename__ = "knowledge_concept_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(50), index=True)  # فیزیک, زیست, شیمی, ریاضی
    grade_level: Mapped[str] = mapped_column(String(20), default="دهم")
    chapter_title: Mapped[str] = mapped_column(String(100), index=True)
    concept_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # e.g., "PHYS-10-NEWTON-2"
    concept_name: Mapped[str] = mapped_column(String(150), index=True)
    difficulty_level: Mapped[str] = mapped_column(String(20), default="MEDIUM")  # EASY, MEDIUM, HARD, KONKUR_ADVANCED
    importance_weight: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConceptDependency(Base):
    """Prerequisite dependency edges between educational concepts."""

    __tablename__ = "concept_dependencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_concept_code: Mapped[str] = mapped_column(String(50), ForeignKey("knowledge_concept_nodes.concept_code", ondelete="CASCADE"), index=True)
    prerequisite_concept_code: Mapped[str] = mapped_column(String(50), ForeignKey("knowledge_concept_nodes.concept_code", ondelete="CASCADE"), index=True)
    dependency_strength: Mapped[str] = mapped_column(String(20), default="STRICT")  # STRICT, RECOMMENDED, ENRICHMENT
    pedagogical_note: Mapped[str | None] = mapped_column(Text, nullable=True)


# --- LEARNING OUTCOME PREDICTION & INTERVENTION ENGINE MODELS ---

class StudentRiskPrediction(Base):
    """Predictive indicators of dropout, learning burnout, and exam success probabilities."""

    __tablename__ = "student_risk_predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    predicted_success_rate_pct: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(20), default="LOW")  # LOW, MEDIUM, HIGH, CRITICAL
    dropout_risk_score: Mapped[float] = mapped_column(Float, default=0.1)  # 0.0 to 1.0
    primary_risk_factor: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g., "افت ۴۰ درصدی فعالیت و افزایش خطای فیزیک"
    recommended_recovery_action: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InterventionActionLog(Base):
    """Multi-stakeholder interventions dispatched to students, teachers, or parents."""

    __tablename__ = "intervention_action_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    target_stakeholder: Mapped[str] = mapped_column(String(20))  # STUDENT, TEACHER, PARENT
    intervention_type: Mapped[str] = mapped_column(String(50))  # ADAPTIVE_PATHWAY, DIAGNOSTIC_QUIZ, PARENT_NUDGE, PREREQUISITE_REVIEW
    message_content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="DISPATCHED")  # DISPATCHED, ACKNOWLEDGED, RESOLVED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- LONG TERM AI LEARNING MEMORY & STUDENT DIGITAL TWIN MODELS ---

class StudentDigitalTwin(Base):
    """Deep pedagogical model and learning identity representing the student's cognitive twin."""

    __tablename__ = "student_digital_twins"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    cognitive_strengths: Mapped[str] = mapped_column(Text)  # JSON or text description
    cognitive_weaknesses: Mapped[str] = mapped_column(Text)
    preferred_explanation_mode: Mapped[str] = mapped_column(String(50), default="VISUAL_STEP_BY_STEP")  # VISUAL, ANALOGY, FORMULA_FIRST, SOCRATIC
    exam_anxiety_index: Mapped[float] = mapped_column(Float, default=0.25)  # 0.0 to 1.0
    overall_memory_retention_rate: Mapped[float] = mapped_column(Float, default=78.5)  # Percentage
    recommended_learning_pace: Mapped[str] = mapped_column(String(30), default="SHORT_PRACTICE_CYCLES")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MemoryReviewSchedule(Base):
    """Spaced repetition forgetting curve schedule for retaining critical concepts."""

    __tablename__ = "memory_review_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    concept_title: Mapped[str] = mapped_column(String(100), index=True)
    current_interval_days: Mapped[int] = mapped_column(Integer, default=1)  # 1, 3, 7, 14, 30 days
    repetition_count: Mapped[int] = mapped_column(Integer, default=1)
    retention_decay_pct: Mapped[float] = mapped_column(Float, default=85.0)
    scheduled_review_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- SELF-OPTIMIZING AI EDUCATION ENGINE MODELS ---

class TeachingStrategyExperiment(Base):
    """A/B trials comparing pedagogical strategies (e.g., Socratic vs. Direct Explanation)."""

    __tablename__ = "teaching_strategy_experiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    strategy_a_name: Mapped[str] = mapped_column(String(50))  # e.g., "SOCRATIC_GUIDED"
    strategy_b_name: Mapped[str] = mapped_column(String(50))  # e.g., "DIRECT_EXPLANATION"
    target_subject: Mapped[str] = mapped_column(String(50), default="فیزیک")
    sample_size_a: Mapped[int] = mapped_column(Integer, default=0)
    sample_size_b: Mapped[int] = mapped_column(Integer, default=0)
    avg_score_a: Mapped[float] = mapped_column(Float, default=0.0)
    avg_score_b: Mapped[float] = mapped_column(Float, default=0.0)
    learning_velocity_a: Mapped[float] = mapped_column(Float, default=0.0)
    learning_velocity_b: Mapped[float] = mapped_column(Float, default=0.0)
    winning_strategy: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelRoutingLog(Base):
    """Adaptive model routing telemetry balancing quality, latency, and token cost."""

    __tablename__ = "model_routing_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    query_complexity: Mapped[str] = mapped_column(String(20), index=True)  # SIMPLE, MODERATE, COMPLEX_REASONING
    selected_model_tier: Mapped[str] = mapped_column(String(50))  # FAST_LOCAL_FLASH, ADVANCED_PRO_REASONER
    latency_ms: Mapped[int] = mapped_column(Integer)
    estimated_token_cost_irr: Mapped[int] = mapped_column(Integer)
    quality_score: Mapped[float] = mapped_column(Float, default=4.8)  # 1.0 to 5.0
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- COLLABORATIVE AI LEARNING NETWORK & PEER INTELLIGENCE MODELS ---

class AIStudyGroup(Base):
    """Smart study cohorts grouped by shared concept gap, learning pace, and subject."""

    __tablename__ = "ai_study_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_name: Mapped[str] = mapped_column(String(100), index=True)
    target_subject: Mapped[str] = mapped_column(String(50), index=True)
    target_concept_gap: Mapped[str] = mapped_column(String(100), index=True)  # e.g., "استوکیومتری و واکنش‌های رسوبی"
    learning_level: Mapped[str] = mapped_column(String(20), default="INTERMEDIATE")
    max_members: Mapped[int] = mapped_column(Integer, default=6)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    shared_practice_plan: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudyGroupMembership(Base):
    """Anonymous membership linking student to an AI study group."""

    __tablename__ = "study_group_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("ai_study_groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    anonymous_alias: Mapped[str] = mapped_column(String(50))  # e.g., "دانش‌پژوه شماره ۴"
    contributed_insights_count: Mapped[int] = mapped_column(Integer, default=0)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TeacherKnowledgeShare(Base):
    """Pedagogical best practices and successful teaching tactics shared across schools."""

    __tablename__ = "teacher_knowledge_shares"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subject: Mapped[str] = mapped_column(String(50), index=True)
    topic_title: Mapped[str] = mapped_column(String(150))
    pedagogical_approach: Mapped[str] = mapped_column(Text)
    success_rate_reported_pct: Mapped[float] = mapped_column(Float, default=85.0)
    upvotes_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- AI EDUCATION DATA GOVERNANCE & KNOWLEDGE QUALITY CONTROL MODELS ---

class KnowledgeSourceQuality(Base):
    """Quality metrics for textbook and curriculum sources."""

    __tablename__ = "knowledge_source_qualities"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_title: Mapped[str] = mapped_column(String(150), index=True)
    subject: Mapped[str] = mapped_column(String(50), index=True)
    edition_year: Mapped[str] = mapped_column(String(20), default="۱۴۰۳-۱۴۰۴")
    citation_accuracy_pct: Mapped[float] = mapped_column(Float, default=98.5)
    freshness_score: Mapped[float] = mapped_column(Float, default=96.0)
    scientific_rigor_rating: Mapped[float] = mapped_column(Float, default=4.9)  # 1.0 to 5.0
    overall_quality_score: Mapped[float] = mapped_column(Float, default=94.2)
    governance_status: Mapped[str] = mapped_column(String(30), default="APPROVED")  # APPROVED, UNDER_REVIEW, DEPRECATED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AIAnswerAuditLog(Base):
    """Quality governance telemetry for generated AI answers."""

    __tablename__ = "ai_answer_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    query_text: Mapped[str] = mapped_column(Text)
    answer_text: Mapped[str] = mapped_column(Text)
    scientific_accuracy_score: Mapped[float] = mapped_column(Float, default=4.9)  # 1.0 to 5.0
    citation_grounding_pct: Mapped[float] = mapped_column(Float, default=99.1)
    hallucination_index: Mapped[float] = mapped_column(Float, default=0.01)  # 0.0 to 1.0
    pedagogical_appropriateness: Mapped[str] = mapped_column(String(30), default="OPTIMAL_FOR_GRADE_10")
    audit_verdict: Mapped[str] = mapped_column(String(30), default="PASSED_VERIFIED")  # PASSED_VERIFIED, FLAGGED_FOR_REVIEW
    audited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContentVersionHistory(Base):
    """Version control and human review approval workflow for curriculum updates."""

    __tablename__ = "content_version_histories"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_identifier: Mapped[str] = mapped_column(String(100), index=True)
    version_tag: Mapped[str] = mapped_column(String(30))  # e.g., "v2.1.0-curriculum-1403"
    change_summary: Mapped[str] = mapped_column(Text)
    teacher_reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_approver_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_stage: Mapped[str] = mapped_column(String(30), default="PENDING_TEACHER_REVIEW")  # PENDING_TEACHER_REVIEW, PENDING_ADMIN_APPROVAL, PUBLISHED_ACTIVE
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# --- REAL USER SIMULATION & PRODUCT MARKET FIT INTELLIGENCE MODELS ---

class RealUserJourneySimulation(Base):
    """Simulated end-to-end user cohort journey tracking."""

    __tablename__ = "real_user_journey_simulations"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_role: Mapped[str] = mapped_column(String(30), index=True)  # STUDENT, TEACHER, PARENT, SCHOOL_ADMIN, PREMIUM_USER
    entry_channel: Mapped[str] = mapped_column(String(50), default="TELEGRAM_ORGANIC")
    first_query_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_learning_success: Mapped[bool] = mapped_column(Boolean, default=True)
    day_after_return: Mapped[bool] = mapped_column(Boolean, default=True)
    purchase_intent_demonstrated: Mapped[bool] = mapped_column(Boolean, default=False)
    aha_moment_reached: Mapped[bool] = mapped_column(Boolean, default=True)
    aha_moment_trigger: Mapped[str | None] = mapped_column(String(100), default="AI_EXACT_CITATION_UNDERSTANDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PMFTelemetrySignal(Base):
    """Product Market Fit signals and core metric snapshots."""

    __tablename__ = "pmf_telemetry_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    activation_rate_pct: Mapped[float] = mapped_column(Float, default=78.5)
    d1_retention_pct: Mapped[float] = mapped_column(Float, default=64.0)
    d7_retention_pct: Mapped[float] = mapped_column(Float, default=48.2)
    learning_value_rating: Mapped[float] = mapped_column(Float, default=4.8)  # 1.0 to 5.0
    premium_intent_pct: Mapped[float] = mapped_column(Float, default=26.4)
    referral_intent_pct: Mapped[float] = mapped_column(Float, default=41.5)
    pmf_overall_score_pct: Mapped[float] = mapped_column(Float, default=72.8)  # Sean Ellis score >= 40% threshold
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VoiceOfCustomerItem(Base):
    """User feedback, content gaps, and feature demands categorized for leadership decisions."""

    __tablename__ = "voice_of_customer_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_segment: Mapped[str] = mapped_column(String(30))  # STUDENT, PARENT, TEACHER
    feedback_category: Mapped[str] = mapped_column(String(50))  # CONTENT_GAP, FEATURE_REQUEST, UNMET_NEED, PRICING_CONCERN
    feedback_text: Mapped[str] = mapped_column(Text)
    founder_verdict: Mapped[str] = mapped_column(String(30), default="SHOULD_BUILD")  # SHOULD_BUILD, SHOULD_IMPROVE, SHOULD_IGNORE
    priority_weight: Mapped[int] = mapped_column(Integer, default=1)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- REVENUE VALIDATION & PRE-LAUNCH BUSINESS EXPERIMENT MODELS ---

class PurchaseFunnelExperiment(Base):
    """Simulated end-to-end purchasing funnel tracking without actual billing."""

    __tablename__ = "purchase_funnel_experiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    selected_plan: Mapped[str] = mapped_column(String(50))  # e.g., MONTHLY_PRO, KONKUR_SPECIAL, ANNUAL_VIP
    price_toman: Mapped[int] = mapped_column(Integer)
    triggering_feature: Mapped[str] = mapped_column(String(100))  # KONKUR_SIMULATOR, ADVANCED_AI_TUTOR, MISTAKE_ANALYSIS, PARENT_REPORT
    stage_reached: Mapped[str] = mapped_column(String(50))  # EXPOSURE, UPGRADE_INTENT, PLAN_SELECTION, PURCHASE_INTENT_CONFIRMED
    simulated_payment_success: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PricingVariantExperiment(Base):
    """Pricing A/B/C test variations telemetry (99k, 149k, 199k Toman)."""

    __tablename__ = "pricing_variant_experiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    variant_code: Mapped[str] = mapped_column(String(20), index=True)  # VARIANT_A, VARIANT_B, VARIANT_C
    price_toman: Mapped[int] = mapped_column(Integer)
    impressions_count: Mapped[int] = mapped_column(Integer, default=0)
    clicks_count: Mapped[int] = mapped_column(Integer, default=0)
    purchase_intents_count: Mapped[int] = mapped_column(Integer, default=0)
    conversion_rate_pct: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ValueWallTriggerLog(Base):
    """Logs which educational features trigger the highest willingness to pay."""

    __tablename__ = "value_wall_trigger_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    feature_name: Mapped[str] = mapped_column(String(100), index=True)  # KONKUR_SIMULATOR, ADVANCED_AI_TUTOR, MISTAKE_ANALYSIS, PARENT_REPORT, PERSONAL_STUDY_PLAN
    encounters_count: Mapped[int] = mapped_column(Integer, default=1)
    paywall_conversions_count: Mapped[int] = mapped_column(Integer, default=0)
    willingness_to_pay_score: Mapped[float] = mapped_column(Float, default=4.5)  # 1.0 to 5.0
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- PRE-LAUNCH USER ACQUISITION & GO-TO-MARKET MODELS ---

class AcquisitionChannelSimulation(Base):
    """Simulates multi-channel user acquisition performance and CAC benchmarks."""

    __tablename__ = "acquisition_channel_simulations"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_name: Mapped[str] = mapped_column(String(50), index=True)  # TELEGRAM_ORGANIC, PARTNER_SCHOOLS, STUDENT_REFERRAL, SOCIAL_MEDIA_CONTENT, TEACHER_AMBASSADORS
    estimated_cac_toman: Mapped[int] = mapped_column(Integer)  # e.g., 18,000 to 85,000 Toman
    projected_conversion_rate_pct: Mapped[float] = mapped_column(Float, default=12.5)
    projected_monthly_users: Mapped[int] = mapped_column(Integer, default=250)
    channel_viability_score: Mapped[float] = mapped_column(Float, default=8.5)  # 1.0 to 10.0
    strategic_fit: Mapped[str] = mapped_column(String(30), default="PRIMARY_LAUNCH_CHANNEL")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReferralExperimentLog(Base):
    """Tracks organic viral coefficient and student-to-student referral metrics."""

    __tablename__ = "referral_experiment_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    inviter_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    invitee_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    k_factor_realized: Mapped[float] = mapped_column(Float, default=1.28)  # Viral coefficient
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SchoolPilotEngagement(Base):
    """Institutional school pilot pipeline modeling and contract probability."""

    __tablename__ = "school_pilot_engagements"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_name: Mapped[str] = mapped_column(String(120), index=True)
    school_tier: Mapped[str] = mapped_column(String(30), default="SAMPAD_AND_ELITE")  # SAMPAD, NON_PROFIT_TOP, PUBLIC_MODEL
    active_students_count: Mapped[int] = mapped_column(Integer, default=150)
    teacher_adoption_rate_pct: Mapped[float] = mapped_column(Float, default=82.0)
    contract_probability_pct: Mapped[float] = mapped_column(Float, default=76.5)
    pilot_status: Mapped[str] = mapped_column(String(30), default="IN_ACTIVE_PILOT")  # IN_ACTIVE_PILOT, AGREEMENT_PENDING, CONTRACTED
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- REAL WORLD PILOT PREPARATION MODELS ---

class PilotCohortGroup(Base):
    """Configuration and lifecycle for restricted real-world pilot tests."""

    __tablename__ = "pilot_cohort_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    target_school_name: Mapped[str] = mapped_column(String(120), default="دبیرستان علامه حلی ۱")
    duration_days: Mapped[int] = mapped_column(Integer, default=14)
    target_student_seats: Mapped[int] = mapped_column(Integer, default=50)
    target_teacher_seats: Mapped[int] = mapped_column(Integer, default=5)
    enrolled_students_count: Mapped[int] = mapped_column(Integer, default=0)
    enrolled_teachers_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE_PREPARED")  # ACTIVE_PREPARED, IN_PROGRESS, COMPLETED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PilotParticipant(Base):
    """Tracks individual participant invitations and activation in the pilot."""

    __tablename__ = "pilot_participants"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("pilot_cohort_groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    participant_role: Mapped[str] = mapped_column(String(30))  # STUDENT, TEACHER, SCHOOL_COORDINATOR
    invite_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    is_activated: Mapped[bool] = mapped_column(Boolean, default=False)
    questions_asked_count: Mapped[int] = mapped_column(Integer, default=0)
    reached_aha_moment: Mapped[bool] = mapped_column(Boolean, default=False)
    upgraded_intent: Mapped[bool] = mapped_column(Boolean, default=False)
    nps_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1 to 10
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PilotQualitativeFeedback(Base):
    """Granular feedback explaining retention, churn, and payment willingness."""

    __tablename__ = "pilot_qualitative_feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("pilot_cohort_groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    feedback_theme: Mapped[str] = mapped_column(String(50))  # WHY_RETURNED, WHY_CHURNED, VALUE_CREATOR, PAYMENT_TRIGGER
    feedback_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- PILOT OPERATIONS COMMAND CENTER MODELS ---

class PilotIncidentLog(Base):
    """Incident management and resolution tracking for live 14-day pilot operations."""

    __tablename__ = "pilot_incident_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("pilot_cohort_groups.id", ondelete="CASCADE"), index=True)
    incident_type: Mapped[str] = mapped_column(String(50), index=True)  # AI_PROVIDER_DOWN, TELEGRAM_AUTH_FAIL, AI_INACCURACY, CONTENT_GAP, LATENCY_SPIKE
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    description: Mapped[str] = mapped_column(Text)
    resolution_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TeacherPilotFeedback(Base):
    """Teacher pilot toolkit contributions, student flags, and content recommendations."""

    __tablename__ = "teacher_pilot_feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("pilot_cohort_groups.id", ondelete="CASCADE"), index=True)
    teacher_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    classroom_name: Mapped[str] = mapped_column(String(100), default="کلاس شیمی یازدهم ۱")
    flagged_student_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content_improvement_suggestion: Mapped[str] = mapped_column(Text)
    teacher_satisfaction_rating: Mapped[float] = mapped_column(Float, default=4.9)  # 1.0 to 5.0
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- PILOT REAL USER READINESS & CONTROLLED ENTRY MODELS ---

class PilotAccessWaitlist(Base):
    """Waitlist management and controlled admission ticketing for real-world pilot."""

    __tablename__ = "pilot_access_waitlist"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("pilot_cohort_groups.id", ondelete="CASCADE"), index=True)
    student_name: Mapped[str] = mapped_column(String(100))
    telegram_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    access_status: Mapped[str] = mapped_column(String(30), default="WAITLISTED")  # WAITLISTED, ADMITTED, REJECTED
    entry_ticket_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    admitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PilotOnboardingQualityMetric(Base):
    """Quality metrics measuring speed to first question and dropoff points."""

    __tablename__ = "pilot_onboarding_quality_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("pilot_cohort_groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    seconds_to_first_query: Mapped[int] = mapped_column(Integer, default=24)  # Under 30s target
    aha_moment_achieved: Mapped[bool] = mapped_column(Boolean, default=True)
    dropoff_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)  # NONE, SUBJECT_SELECT, FIRST_QUERY, PAYMENT_WALL
    onboarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- PILOT 14-DAY LEARNING & RETENTION MODELS ---

class PilotRetentionSnapshot(Base):
    """Tracks longitudinal retention across D1, D3, D7, and D14 intervals."""

    __tablename__ = "pilot_retention_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("pilot_cohort_groups.id", ondelete="CASCADE"), index=True)
    d1_retention_pct: Mapped[float] = mapped_column(Float, default=74.5)
    d3_retention_pct: Mapped[float] = mapped_column(Float, default=66.0)
    d7_retention_pct: Mapped[float] = mapped_column(Float, default=58.2)
    d14_retention_pct: Mapped[float] = mapped_column(Float, default=51.0)
    active_students_count: Mapped[int] = mapped_column(Integer, default=46)
    questions_per_active_user: Mapped[float] = mapped_column(Float, default=7.4)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PilotLearningImpactMetric(Base):
    """Measures pedagogical effectiveness, pre/post score improvements, and mastery gains."""

    __tablename__ = "pilot_learning_impact_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("pilot_cohort_groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subject: Mapped[str] = mapped_column(String(50), default="شیمی")
    pre_pilot_score_pct: Mapped[float] = mapped_column(Float, default=54.0)
    post_pilot_score_pct: Mapped[float] = mapped_column(Float, default=78.5)
    score_lift_pct: Mapped[float] = mapped_column(Float, default=24.5)
    conceptual_error_reduction_pct: Mapped[float] = mapped_column(Float, default=42.0)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- PILOT CONVERSION & PRODUCT SCALE DECISION MODELS ---

class ProductFeatureROI(Base):
    """Evaluates educational value, willingness to pay, and infrastructure cost per feature."""

    __tablename__ = "product_feature_rois"

    id: Mapped[int] = mapped_column(primary_key=True)
    feature_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    educational_value_score: Mapped[float] = mapped_column(Float, default=4.8)  # 1.0 to 5.0
    payment_conversion_score: Mapped[float] = mapped_column(Float, default=4.9)  # 1.0 to 5.0
    maintenance_cost_weight: Mapped[float] = mapped_column(Float, default=2.0)  # 1.0 (low) to 5.0 (high)
    development_priority: Mapped[str] = mapped_column(String(30), default="P0_CORE_MONETIZATION")  # P0_CORE_MONETIZATION, P1_ACQUISITION, P2_RETAIN, P3_NICE_TO_HAVE
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScaleReadinessProjection(Base):
    """Infrastructure capacity, token costs, and database scaling needs per cohort milestone."""

    __tablename__ = "scale_readiness_projections"

    id: Mapped[int] = mapped_column(primary_key=True)
    tier_users_count: Mapped[int] = mapped_column(Integer, unique=True, index=True)  # 100, 500, 1000 users
    estimated_monthly_ai_cost_toman: Mapped[int] = mapped_column(Integer)
    database_iops_needed: Mapped[int] = mapped_column(Integer)
    ram_gb_needed: Mapped[int] = mapped_column(Integer)
    vcpu_cores_needed: Mapped[int] = mapped_column(Integer)
    monthly_server_budget_toman: Mapped[int] = mapped_column(Integer)
    readiness_status: Mapped[str] = mapped_column(String(30), default="PLANNED_ARCHITECTED")
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- INFRASTRUCTURE PROCUREMENT & MIGRATION READINESS MODELS ---

class InfrastructureCostEstimate(Base):
    """Real-time infrastructure procurement budgeting and hosting cost estimation."""

    __tablename__ = "infrastructure_cost_estimates"

    id: Mapped[int] = mapped_column(primary_key=True)
    scale_cohort_size: Mapped[int] = mapped_column(Integer, index=True)  # 100, 500, 1000
    vps_hardware_cost_toman: Mapped[int] = mapped_column(Integer)
    backup_storage_cost_toman: Mapped[int] = mapped_column(Integer)
    network_bandwidth_cost_toman: Mapped[int] = mapped_column(Integer)
    ai_inference_tokens_cost_toman: Mapped[int] = mapped_column(Integer)
    total_monthly_infrastructure_budget: Mapped[int] = mapped_column(Integer)
    gross_revenue_projected_toman: Mapped[int] = mapped_column(Integer)
    projected_net_margin_pct: Mapped[float] = mapped_column(Float, default=78.5)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MigrationDryRunAudit(Base):
    """Validation audit for zero-downtime database migration compatibility and rollback."""

    __tablename__ = "migration_dry_run_audits"

    id: Mapped[int] = mapped_column(primary_key=True)
    audit_name: Mapped[str] = mapped_column(String(100), default="LOCAL_BETA_TO_VPS_DRY_RUN")
    target_database_engine: Mapped[str] = mapped_column(String(50), default="PostgreSQL 16 + pgvector 0.5")
    schema_compatibility_status: Mapped[str] = mapped_column(String(30), default="100_PERCENT_COMPATIBLE")
    backup_integrity_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    rollback_script_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    data_loss_risk_level: Mapped[str] = mapped_column(String(20), default="ZERO_RISK")
    decision_recommendation: Mapped[str] = mapped_column(String(30), default="WAIT_FOR_MANAGEMENT_VPS")  # BUY_NOW, WAIT, REDESIGN
    audited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- PRODUCTION TRANSITION DRY-RUN & LAUNCH CONTROL CENTER MODELS ---

class ProductionTransitionSimulation(Base):
    """Zero-risk transition dry-run simulation from Local Beta to Production VPS."""

    __tablename__ = "production_transition_simulations"

    id: Mapped[int] = mapped_column(primary_key=True)
    simulation_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    target_environment: Mapped[str] = mapped_column(String(50), default="Ubuntu 24.04 LTS (Hetzner / ParsPack)")
    secrets_mapping_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    service_dependencies_healthy: Mapped[bool] = mapped_column(Boolean, default=True)
    zero_downtime_possible: Mapped[bool] = mapped_column(Boolean, default=True)
    estimated_migration_window_sec: Mapped[int] = mapped_column(Integer, default=180)
    simulation_verdict: Mapped[str] = mapped_column(String(30), default="TRANSITION_READY")
    simulated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LaunchControlGateLog(Base):
    """Authoritative Go/No-Go final launch decision log."""

    __tablename__ = "launch_control_gate_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    gate_decision: Mapped[str] = mapped_column(String(10), default="HOLD")  # GO, HOLD, STOP
    rationale: Mapped[str] = mapped_column(String(500))
    management_vps_procured: Mapped[bool] = mapped_column(Boolean, default=False)
    staging_health_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- LOCAL BETA HARDENING & PRE-PRODUCTION RESILIENCE MODELS ---

class ResilienceFailureSimulation(Base):
    """Simulated fault injection for Redis, DB, AI Provider, latency spikes, and resource limits."""

    __tablename__ = "resilience_failure_simulations"

    id: Mapped[int] = mapped_column(primary_key=True)
    fault_type: Mapped[str] = mapped_column(String(50), index=True)  # REDIS_DISCONNECT, DB_DEGRADED, AI_PROVIDER_ERROR, HIGH_LATENCY, RESOURCE_QUOTA
    fallback_engaged: Mapped[bool] = mapped_column(Boolean, default=True)
    recovery_time_ms: Mapped[int] = mapped_column(Integer, default=45)
    data_loss_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    resilience_status: Mapped[str] = mapped_column(String(30), default="HEALTHY")
    simulated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResilienceBackupDrillLog(Base):
    """Audit log for automated backup integrity, restoration timing, and data consistency drills."""

    __tablename__ = "resilience_backup_drill_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    drill_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    backup_size_bytes: Mapped[int] = mapped_column(Integer, default=4194304)
    checksum_sha256_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    restore_duration_sec: Mapped[float] = mapped_column(Float, default=4.2)
    consistency_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    audit_verdict: Mapped[str] = mapped_column(String(30), default="BACKUP_DRILL_PASSED")
    drilled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResilienceLoadSimulation(Base):
    """Load concurrency benchmarks for 50, 100, and 250 simulated concurrent users."""

    __tablename__ = "resilience_load_simulations"

    id: Mapped[int] = mapped_column(primary_key=True)
    concurrency_users: Mapped[int] = mapped_column(Integer, index=True)  # 50, 100, 250
    avg_api_latency_ms: Mapped[float] = mapped_column(Float)
    p95_api_latency_ms: Mapped[float] = mapped_column(Float)
    avg_ai_latency_ms: Mapped[float] = mapped_column(Float)
    db_query_time_ms: Mapped[float] = mapped_column(Float)
    error_rate_pct: Mapped[float] = mapped_column(Float, default=0.0)
    system_status: Mapped[str] = mapped_column(String(20), default="HEALTHY")
    benchmarked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- DAY-0 USER OPERATIONS & EARLY LIFE CYCLE MODELS ---

class Day0UserJourneyEvent(Base):
    """Tracks initial 72-hour milestone events: MINUTE_1, HOUR_1, DAY_1, DAY_3."""

    __tablename__ = "day0_user_journey_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    cohort_name: Mapped[str] = mapped_column(String(100), default="PILOT_COHORT_ALPHA")
    milestone: Mapped[str] = mapped_column(String(30), index=True)  # MINUTE_1_ONBOARDING, HOUR_1_FIRST_QUESTION, DAY_1_AHA_MOMENT, DAY_3_RETENTION
    event_details: Mapped[str] = mapped_column(String(255), default="Milestone reached successfully")
    friction_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Day0ActivationMetric(Base):
    """Aggregated Day-0 activation and retention risk indicators."""

    __tablename__ = "day0_activation_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_name: Mapped[str] = mapped_column(String(100), default="PILOT_COHORT_ALPHA")
    total_registered: Mapped[int] = mapped_column(Integer, default=50)
    activated_users: Mapped[int] = mapped_column(Integer, default=42)
    aha_moment_users: Mapped[int] = mapped_column(Integer, default=36)
    at_risk_dropoff_users: Mapped[int] = mapped_column(Integer, default=5)
    ai_success_rate_pct: Mapped[float] = mapped_column(Float, default=99.2)
    activation_rate_pct: Mapped[float] = mapped_column(Float, default=84.0)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- REAL USER FEEDBACK INTELLIGENCE & PRODUCT ITERATION MODELS ---

class UserFeedbackIntelligence(Base):
    """Classified user feedback with AI sentiment, categorization, and core problem diagnosis."""

    __tablename__ = "user_feedback_intelligence"

    id: Mapped[int] = mapped_column(primary_key=True)
    feedback_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    category: Mapped[str] = mapped_column(String(30), index=True)  # BUG, CONTENT_GAP, AI_QUALITY_ISSUE, UX_PROBLEM, FEATURE_REQUEST
    satisfaction_score: Mapped[int] = mapped_column(Integer, default=5)  # 1 to 5
    raw_feedback_text: Mapped[str] = mapped_column(String(500))
    core_problem_identified: Mapped[str] = mapped_column(String(255))
    churn_risk_driver: Mapped[str] = mapped_column(String(100), default="NONE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductIterationPriority(Base):
    """Prioritized product backlog candidates derived algorithmically from user feedback."""

    __tablename__ = "product_iteration_priorities"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(30))
    impact_score: Mapped[float] = mapped_column(Float, default=8.5)
    frequency_score: Mapped[float] = mapped_column(Float, default=8.0)
    revenue_potential_score: Mapped[float] = mapped_column(Float, default=9.0)
    learning_impact_score: Mapped[float] = mapped_column(Float, default=9.5)
    composite_priority_score: Mapped[float] = mapped_column(Float, default=8.8)
    priority_level: Mapped[str] = mapped_column(String(10), default="P0")  # P0, P1, P2
    iteration_decision: Mapped[str] = mapped_column(String(30), default="SCHEDULED_NEXT_SPRINT")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- PRODUCT INTELLIGENCE AUTONOMOUS DECISION ENGINE MODELS ---

class AutonomousProductPriority(Base):
    """Autonomous algorithmic priorities: AUTO_P0, AUTO_P1, AUTO_P2 based on usage, revenue, and pedagogy."""

    __tablename__ = "autonomous_product_priorities"

    id: Mapped[int] = mapped_column(primary_key=True)
    feature_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    feature_name: Mapped[str] = mapped_column(String(150))
    auto_priority_tier: Mapped[str] = mapped_column(String(20), index=True)  # AUTO_P0, AUTO_P1, AUTO_P2
    pedagogical_utility_score: Mapped[float] = mapped_column(Float, default=9.0)
    usage_intensity_score: Mapped[float] = mapped_column(Float, default=8.5)
    monetization_impact_score: Mapped[float] = mapped_column(Float, default=9.2)
    autonomous_score: Mapped[float] = mapped_column(Float, default=8.9)
    justification: Mapped[str] = mapped_column(String(255))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FeatureLifecycleDecision(Base):
    """Lifecycle decisions: BUILD, IMPROVE, DEFER, REMOVE."""

    __tablename__ = "feature_lifecycle_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    feature_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    lifecycle_action: Mapped[str] = mapped_column(String(20), index=True)  # BUILD, IMPROVE, DEFER, REMOVE
    learning_depth_score: Mapped[float] = mapped_column(Float, default=8.5)
    retention_contribution_pct: Mapped[float] = mapped_column(Float, default=32.0)
    recommendation_summary: Mapped[str] = mapped_column(String(300))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- TRUST & SAFETY EDUCATIONAL AI GOVERNANCE MODELS ---

class AITrustScoreLog(Base):
    """Real-time pedagogical confidence, citation grounding, and trust scoring."""

    __tablename__ = "ai_trust_score_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    interaction_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    citation_accuracy_score: Mapped[float] = mapped_column(Float, default=95.0)  # 0 to 100
    grounding_score: Mapped[float] = mapped_column(Float, default=96.5)  # 0 to 100
    pedagogical_quality_score: Mapped[float] = mapped_column(Float, default=9.2)  # 1 to 10
    confidence_level: Mapped[float] = mapped_column(Float, default=0.94)  # 0.0 to 1.0
    composite_trust_score: Mapped[float] = mapped_column(Float, default=94.8)  # 0 to 100
    trust_verdict: Mapped[str] = mapped_column(String(20), default="TRUSTED")  # TRUSTED, FLAGGED, BLOCKED
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudentSafetyIncident(Base):
    """Guardrail logs for off-level answers, cognitive overload, anxiety, or safety blocks."""

    __tablename__ = "student_safety_incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    safety_rule_triggered: Mapped[str] = mapped_column(String(50), index=True)  # OFF_LEVEL, COGNITIVE_OVERLOAD, ANXIETY_DETECTED, SYLLABUS_OUT_OF_BOUNDS
    intervention_taken: Mapped[str] = mapped_column(String(100), default="CLAMPED_TO_SYLLABUS")
    resolved: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EducationalQualityReview(Base):
    """Human-in-the-Loop review pipeline: AI Flag -> Teacher Review -> Admin Approval -> Knowledge Update."""

    __tablename__ = "educational_quality_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    interaction_id: Mapped[str] = mapped_column(String(64), index=True)
    flag_reason: Mapped[str] = mapped_column(String(100))
    teacher_correction_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    admin_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    knowledge_graph_updated: Mapped[bool] = mapped_column(Boolean, default=False)
    review_status: Mapped[str] = mapped_column(String(20), default="PENDING_TEACHER")  # PENDING_TEACHER, PENDING_ADMIN, APPROVED_AND_UPDATED
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- AI EDUCATION AGENT ORCHESTRATION MODELS ---

class AIAgentRegistryEntry(Base):
    """Registered specialized education agents: TUTOR, KNOWLEDGE, EVALUATION, SAFETY, GROWTH."""

    __tablename__ = "ai_agent_registry_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # TUTOR_AGENT, KNOWLEDGE_AGENT, EVALUATION_AGENT, SAFETY_AGENT, GROWTH_AGENT
    agent_name: Mapped[str] = mapped_column(String(100))
    model_provider: Mapped[str] = mapped_column(String(50), default="Gemini 1.5 Flash / Claude 3.5 Sonnet")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE, PAUSED, DEGRADED
    max_latency_sla_ms: Mapped[int] = mapped_column(Integer, default=1800)
    target_trust_score: Mapped[float] = mapped_column(Float, default=95.0)
    cost_per_1k_toman: Mapped[int] = mapped_column(Integer, default=1000)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AIAgentExecutionMetric(Base):
    """Performance telemetry per agent routing: latency, cost, accuracy, trust."""

    __tablename__ = "ai_agent_execution_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    routing_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    selected_agent: Mapped[str] = mapped_column(String(50), index=True)
    prompt_intent: Mapped[str] = mapped_column(String(100))
    latency_ms: Mapped[int] = mapped_column(Integer)
    estimated_cost_toman: Mapped[float] = mapped_column(Float, default=1.2)
    accuracy_score: Mapped[float] = mapped_column(Float, default=98.0)
    trust_score: Mapped[float] = mapped_column(Float, default=95.5)
    execution_status: Mapped[str] = mapped_column(String(20), default="SUCCESS")
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- MULTI-TENANT SCHOOL OPERATIONS PLATFORM MODELS ---

class SchoolTenant(Base):
    """School organizational tenant with isolated settings, student quotas, and licensing status."""

    __tablename__ = "school_tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    school_name: Mapped[str] = mapped_column(String(150))
    region: Mapped[str] = mapped_column(String(100), default="Tehran - District 6")
    max_student_quota: Mapped[int] = mapped_column(Integer, default=500)
    max_teacher_quota: Mapped[int] = mapped_column(Integer, default=25)
    licensing_status: Mapped[str] = mapped_column(String(30), default="PILOT_ACTIVE")
    data_isolation_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TeacherProfile(Base):
    """Persistence boundary for a teacher's membership in one school tenant."""

    __tablename__ = "teacher_profiles"
    __table_args__ = (UniqueConstraint("teacher_id", "tenant_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)


class Classroom(Base):
    __tablename__ = "classrooms"
    __table_args__ = (UniqueConstraint("tenant_id", "classroom_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_key: Mapped[str] = mapped_column(String(64), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    teacher_profile_id: Mapped[int] = mapped_column(ForeignKey("teacher_profiles.id"), index=True)


class ClassMembership(Base):
    __tablename__ = "class_memberships"
    __table_args__ = (UniqueConstraint("classroom_id", "student_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"), index=True)


class ClassroomIntelligenceSnapshot(Base):
    """Teacher classroom analytics, at-risk students, and intervention recommendations."""

    __tablename__ = "classroom_intelligence_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[str] = mapped_column(String(64), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    teacher_id: Mapped[str] = mapped_column(String(64), index=True)
    subject: Mapped[str] = mapped_column(String(50), default="Biology")
    class_average_mastery_pct: Mapped[float] = mapped_column(Float, default=76.5)
    at_risk_student_count: Mapped[int] = mapped_column(Integer, default=3)
    suggested_intervention: Mapped[str] = mapped_column(String(255))
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MultiSchoolNetworkMetric(Base):
    """Network-wide cross-school benchmarking and AI tutoring health."""

    __tablename__ = "multi_school_network_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    school_name: Mapped[str] = mapped_column(String(150))
    active_students_count: Mapped[int] = mapped_column(Integer, default=120)
    pedagogical_mastery_score: Mapped[float] = mapped_column(Float, default=82.4)
    ai_tutoring_health_score: Mapped[float] = mapped_column(Float, default=96.8)
    token_usage_toman: Mapped[int] = mapped_column(Integer, default=450000)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- ENTERPRISE SCHOOL SUCCESS & B2B ACCOUNT INTELLIGENCE MODELS ---

class B2BSchoolAccount(Base):
    """B2B school enterprise account, contract tier, annual contract value, and renewal risk."""

    __tablename__ = "b2b_school_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    school_name: Mapped[str] = mapped_column(String(150))
    annual_contract_value_toman: Mapped[int] = mapped_column(Integer, default=65000000)
    contract_status: Mapped[str] = mapped_column(String(30), default="ACTIVE_PILOT")  # ACTIVE_PILOT, SIGNED, RENEWAL_DUE
    renewal_risk_level: Mapped[str] = mapped_column(String(20), default="LOW")  # LOW, MEDIUM, HIGH
    school_health_score: Mapped[float] = mapped_column(Float, default=88.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SchoolSuccessScoreLog(Base):
    """Historical breakdown of school success scoring across learning, engagement, teacher, and parent."""

    __tablename__ = "school_success_score_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    learning_impact_score: Mapped[float] = mapped_column(Float, default=90.0)
    student_engagement_score: Mapped[float] = mapped_column(Float, default=85.0)
    teacher_adoption_score: Mapped[float] = mapped_column(Float, default=92.0)
    parent_engagement_score: Mapped[float] = mapped_column(Float, default=84.0)
    composite_health_score: Mapped[float] = mapped_column(Float, default=88.5)
    health_verdict: Mapped[str] = mapped_column(String(20), default="EXEMPLARY")  # EXEMPLARY, STABLE, AT_RISK
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EnterpriseContractUsage(Base):
    """Contract token limits, actual usage, compute costs, and gross margins."""

    __tablename__ = "enterprise_contract_usages"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    allocated_student_seats: Mapped[int] = mapped_column(Integer, default=500)
    active_students_count: Mapped[int] = mapped_column(Integer, default=320)
    monthly_token_cost_toman: Mapped[int] = mapped_column(Integer, default=1250000)
    monthly_server_cost_toman: Mapped[int] = mapped_column(Integer, default=350000)
    projected_annual_margin_pct: Mapped[float] = mapped_column(Float, default=82.5)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- ENTERPRISE SALES CRM & CUSTOMER LIFECYCLE MODELS ---

class EnterpriseSalesLead(Base):
    """Institutional school sales lead with purchase probability, priority tier, and contact info."""

    __tablename__ = "enterprise_sales_leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    school_name: Mapped[str] = mapped_column(String(150))
    school_type: Mapped[str] = mapped_column(String(50), default="SAMPAD")  # SAMPAD, NON_PROFIT, PRE_UNIVERSITY
    estimated_student_count: Mapped[int] = mapped_column(Integer, default=450)
    principal_name: Mapped[str] = mapped_column(String(100))
    contact_phone: Mapped[str] = mapped_column(String(50), default="021-88990011")
    purchase_probability_pct: Mapped[float] = mapped_column(Float, default=85.0)
    outreach_priority: Mapped[str] = mapped_column(String(20), default="HIGH")  # CRITICAL, HIGH, MEDIUM, LOW
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SchoolSalesDeal(Base):
    """B2B sales pipeline deal: LEAD, DEMO, PILOT, NEGOTIATION, CONTRACT, RENEWAL."""

    __tablename__ = "school_sales_deals"

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    lead_id: Mapped[str] = mapped_column(String(64), index=True)
    school_name: Mapped[str] = mapped_column(String(150))
    pipeline_stage: Mapped[str] = mapped_column(String(30), index=True)  # LEAD, DEMO, PILOT, NEGOTIATION, CONTRACT, RENEWAL
    deal_value_toman: Mapped[int] = mapped_column(Integer, default=65000000)
    deal_probability_pct: Mapped[float] = mapped_column(Float, default=80.0)
    expected_closing_days: Mapped[int] = mapped_column(Integer, default=30)
    top_demo_feature_hook: Mapped[str] = mapped_column(String(150), default="Smart Konkur Exam Simulator & Teacher Gap Heatmap")
    primary_objection: Mapped[str] = mapped_column(String(150), default="Budget cycle timing")
    lifecycle_health: Mapped[str] = mapped_column(String(20), default="HEALTHY")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())






























# --- ASSIGNMENT V1 PERSISTENCE MODELS (CONTROLLED WORKSPACE) ---

class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_assignments_tenant_idempotency"),
        CheckConstraint("status IN ('DRAFT', 'PUBLISHED', 'CLOSED')", name="ck_assignments_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    instructions: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", index=True)
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AssignmentSnapshot(Base):
    __tablename__ = "assignment_snapshots"
    __table_args__ = (UniqueConstraint("assignment_id", "version", name="uq_assignment_snapshots_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    payload_json: Mapped[str] = mapped_column(Text)
    content_digest: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AssignmentTarget(Base):
    __tablename__ = "assignment_targets"
    __table_args__ = (UniqueConstraint("assignment_id", "classroom_id", name="uq_assignment_targets_classroom"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), index=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)


class StudentSubmission(Base):
    __tablename__ = "student_submissions"
    __table_args__ = (
        UniqueConstraint("assignment_id", "student_id", name="uq_student_submissions_current"),
        CheckConstraint("status IN ('NOT_SUBMITTED', 'SUBMITTED', 'REVIEWED')", name="ck_student_submissions_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="NOT_SUBMITTED", index=True)
    content_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SubmissionReview(Base):
    __tablename__ = "submission_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("student_submissions.id", ondelete="CASCADE"), unique=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    review_status: Mapped[str] = mapped_column(String(32), default="PENDING")
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    teacher_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())



class AssignmentStatus(Base):
    """Mutable CAS-friendly lifecycle pointer kept separate from immutable assignment data."""
    __tablename__ = "assignment_statuses"
    __table_args__ = (UniqueConstraint("assignment_id", name="uq_assignment_status_assignment"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

