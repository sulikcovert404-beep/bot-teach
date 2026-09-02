from pathlib import Path

from app.services.rag import SourceChunk
from app.services.retrieval_benchmark import lexical_retrieve, run_benchmark
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
