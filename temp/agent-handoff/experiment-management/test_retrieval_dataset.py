from pathlib import Path

from app.services.retrieval_dataset import load_evaluation_dataset


def test_synthetic_dataset_v1_loads_and_covers_required_states() -> None:
    cases = load_evaluation_dataset(Path("data/rag_eval_v1.json"))
    assert len(cases) == 8
    assert {case.expected_state for case in cases} == {"sufficient", "no_source", "conflict"}
    assert any(case.multi_hop_sources for case in cases)
    assert all(case.dataset_version == "rag-eval-v1.1-synthetic" for case in cases)
    assert any("zwnj" in (case.provenance or "") for case in cases)
    assert any("ocr" in (case.provenance or "") for case in cases)
