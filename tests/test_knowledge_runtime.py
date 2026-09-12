from app.services.knowledge_runtime import KnowledgeCandidate, retrieve_scoped


def candidates():
    return [
        KnowledgeCandidate("قانون نیوتن و نیرو", "a", 1, "tenant-a", 10, "دهم", "APPROVED", "PUBLISHED"),
        KnowledgeCandidate("محتوای در انتظار بررسی", "a", 2, "tenant-a", 10, "دهم", "PENDING", "PUBLISHED"),
        KnowledgeCandidate("محتوای مردود", "a", 3, "tenant-a", 10, "دهم", "REJECTED", "PUBLISHED"),
        KnowledgeCandidate("محتوای مدرسه دیگر", "b", 4, "tenant-b", 10, "دهم", "APPROVED", "PUBLISHED"),
        KnowledgeCandidate("فیزیک پایه یازدهم", "a", 5, "tenant-a", 10, "یازدهم", "APPROVED", "PUBLISHED"),
        KnowledgeCandidate("نسخه قدیمی", "a", 6, "tenant-a", 10, "دهم", "APPROVED", "REVOKED"),
    ]


def test_scope_and_review_state_apply_before_search():
    result = retrieve_scoped("قانون نیرو", candidates(), tenant_id="tenant-a", classroom_id=10, grade="دهم")
    assert [item.candidate.chunk_id for item in result] == [1]


def test_persian_glyph_variants_retrieve_same_candidate():
    result = retrieve_scoped("قانون نیرو", [KnowledgeCandidate("قانون نیرو در كتاب", "a", 1, "tenant-a", 10, "دهم", "APPROVED", "PUBLISHED")], tenant_id="tenant-a", classroom_id=10, grade="دهم")
    assert result and result[0].candidate.chunk_id == 1


def test_no_evidence_returns_empty_without_fake_citation():
    assert retrieve_scoped("زیست", candidates(), tenant_id="tenant-a", classroom_id=10, grade="دهم") == ()
