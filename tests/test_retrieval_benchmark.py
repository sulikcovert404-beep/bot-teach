from pathlib import Path

from app.services.rag import SourceChunk
from app.services.retrieval_benchmark import lexical_retrieve, persist_run_artifact, run_benchmark
from app.services.retrieval_dataset import load_evaluation_dataset


def test_controlled_benchmark_runs_lexical_fixture() -> None:
    cases = load_evaluation_dataset(Path("data/rag_eval_v1.json"))
    chunks = [
        SourceChunk("نیرو برهم‌کنش میان اجسام است", "physics10:v1:p12:c1", page=12),
        SourceChunk("انرژی جنبشی با مجذور سرعت متناسب است", "physics10:v1:p44:c2", page=44),
        SourceChunk("منبع نامرتبط", "other:p1", page=1),
    ]
    retriever = lambda case, limit: lexical_retrieve(chunks, case, limit)
    result = run_benchmark(cases[:1], {"lexical": retriever}, k=2)[0]
    assert result.provider == "lexical"
    assert result.evaluations[0].recall_at_k == 1.0
    report = result.to_report()
    raw = report["raw_cases"][0]
    assert raw["query_id"] == "physics10_ch1_001"
    assert raw["retrieved_source_ids"]
    assert "latency_ms" in raw and "metrics" in raw

    artifact = persist_run_artifact(
        (result,),
        dataset_version="rag-eval-v1.1-synthetic",
        retriever_version="lexical-baseline-v1",
        execution_metadata={"environment": "test"},
        run_id="run-test-001",
        timestamp="2026-09-02T00:00:00+00:00",
    )
    report = artifact.to_report()
    assert report["run_id"] == "run-test-001"
    assert report["dataset_version"] == "rag-eval-v1.1-synthetic"
    assert report["metric_snapshot"]["lexical"]["recall_at_k"] == 1.0
    assert report["execution_metadata"] == {"environment": "test"}
