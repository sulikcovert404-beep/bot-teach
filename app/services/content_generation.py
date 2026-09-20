"""Provider-neutral, mock-backed content generation lifecycle."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContentGenerationJob, GeneratedAsset, GenerationAttempt
from app.services.ai_gateway import AIGateway, AIRequest


class GenerationProvider(Protocol):
    async def generate(self, asset_type: str, source_text: str) -> dict[str, object]: ...


class MockAIProvider:
    async def generate(self, asset_type: str, source_text: str) -> dict[str, object]:
        return {"asset_type": asset_type, "source_excerpt": source_text[:500], "items": []}


class GenerationService:
    def __init__(self, provider: GenerationProvider | None = None) -> None:
        self.provider = provider or MockAIProvider()

    async def create_or_reuse_job(
        self, session: AsyncSession, *, content_version_id: int, asset_type: str,
        generation_parameters: dict[str, object], requested_by: int | None = None,
    ) -> ContentGenerationJob:
        params = json.dumps(generation_parameters, sort_keys=True, ensure_ascii=False)
        fingerprint = hashlib.sha256(params.encode()).hexdigest()
        result = await session.execute(select(ContentGenerationJob).where(
            ContentGenerationJob.content_version_id == content_version_id,
            ContentGenerationJob.asset_type == asset_type,
            ContentGenerationJob.generation_parameters_hash == fingerprint,
        ))
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing
        job = ContentGenerationJob(content_version_id=content_version_id, asset_type=asset_type,
            generation_parameters_hash=fingerprint, requested_by=requested_by)
        session.add(job)
        await session.flush()
        return job

    async def run_mock(self, session: AsyncSession, job: ContentGenerationJob, source_text: str) -> GeneratedAsset:
        job.status = "PROCESSING"
        job.attempt_count += 1
        output = await self.provider.generate(job.asset_type, source_text)
        raw = json.dumps(output, sort_keys=True, ensure_ascii=False)
        if not isinstance(output, dict) or (job.asset_type == "QUESTION_BANK" and not output.get("items")):
            await self.mark_failed(session, job, "INVALID_OUTPUT")
            raise ValueError("INVALID_OUTPUT")
        asset = GeneratedAsset(job_id=job.id, asset_type=job.asset_type, content_json=raw,
            content_hash=hashlib.sha256(raw.encode()).hexdigest(), review_state="DRAFT")
        now = datetime.now(UTC)
        session.add(GenerationAttempt(job_id=job.id, outcome="COMPLETED", token_usage=0, started_at=now, completed_at=now, provider="mock", model="mock"))
        session.add(asset)
        job.status = "COMPLETED"
        job.completed_at = datetime.now(UTC)
        await session.flush()
        return asset

    async def run_with_gateway(
        self, session: AsyncSession, job: ContentGenerationJob, source_text: str,
        gateway: AIGateway,
    ) -> GeneratedAsset:
        """Run one job through the provider-neutral gateway and persist a draft asset."""
        job.status = "PROCESSING"
        job.attempt_count += 1
        started = datetime.now(UTC)
        try:
            response = await gateway.generate(
                AIRequest(content_context=source_text, task_type=job.asset_type,
                          parameters={})
            )
            payload = response.content if isinstance(response.content, dict) else {"content": response.content}
            raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
            asset = GeneratedAsset(job_id=job.id, asset_type=job.asset_type, content_json=raw,
                content_hash=hashlib.sha256(raw.encode()).hexdigest(), review_state="DRAFT")
            session.add(GenerationAttempt(job_id=job.id, outcome="COMPLETED", provider=response.provider,
                model=response.model, token_usage=response.input_tokens + response.output_tokens,
                started_at=started, completed_at=datetime.now(UTC), cost=response.estimated_cost))
            session.add(asset)
            job.provider, job.model = response.provider, response.model
            job.status = "COMPLETED"
            job.completed_at = datetime.now(UTC)
            await session.flush()
            return asset
        except Exception as exc:
            await self.mark_failed(session, job, getattr(exc, "code", "PROVIDER_ERROR"))
            raise

    async def claim_next(self, session: AsyncSession, *, worker_id: str = "worker", lease_seconds: int = 300) -> ContentGenerationJob | None:
        """Claim one pending job; the transaction boundary provides the lease."""
        now = datetime.now(UTC)
        result = await session.execute(select(ContentGenerationJob).where(
            (ContentGenerationJob.status == "PENDING") |
            ((ContentGenerationJob.status == "PROCESSING") & (ContentGenerationJob.lease_expires_at < now))
        ).order_by(ContentGenerationJob.created_at).limit(1))
        job = result.scalar_one_or_none()
        if job is None:
            return None
        # Conditional state transition prevents a second claimant from owning a pending row.
        claimed = await session.execute(update(ContentGenerationJob).where(
            ContentGenerationJob.id == job.id, ContentGenerationJob.status.in_(["PENDING", "PROCESSING"])
        ).values(status="PROCESSING", worker_id=worker_id, lease_expires_at=now + timedelta(seconds=lease_seconds)))
        if claimed.rowcount != 1:
            return None
        job.status = "PROCESSING"
        job.worker_id = worker_id
        job.lease_expires_at = now + timedelta(seconds=lease_seconds)
        await session.flush()
        return job

    async def mark_failed(self, session: AsyncSession, job: ContentGenerationJob, error_code: str) -> None:
        job.status = "FAILED"
        job.error_code = error_code
        session.add(GenerationAttempt(job_id=job.id, outcome="FAILED", error_code=error_code))
        await session.flush()

    async def retry_or_fail(self, session: AsyncSession, job: ContentGenerationJob, error_code: str, *, max_attempts: int = 3) -> None:
        job.error_code = error_code
        if job.attempt_count < max_attempts:
            job.status = "PENDING"
        else:
            job.status = "FAILED"
        session.add(GenerationAttempt(job_id=job.id, outcome=job.status, error_code=error_code))
        await session.flush()
