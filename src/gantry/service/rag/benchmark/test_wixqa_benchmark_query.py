from __future__ import annotations

from gantry.service.rag.benchmark.test_shared import (
    RagBenchmark,
    write_summary,
    build_llm_clients,
    build_rag_clients,
)
from gantry.service.rag.benchmark.test_wixqa_benchmark_dataloader import (
    WixQaDatasetLoader,
)

import sys
import asyncio
from pathlib import Path


SUMMARY_FILE = "wixqa_benchmark_summary.json"

RAG_QUERY_TOP_K: int = 5
RAG_QUERY_HYBRID_SEARCH: bool = True
RAG_QUERY_HYBRID_SEARCH_BM25_TOP_K: int = 5
RAG_QUERY_HYBRID_SEARCH_SEMANTIC_TOP_K: int = 5

ANSWER_MODEL_BASE_URL: str = "https://api.groq.com/openai/v1"
ANSWER_MODEL = "openai/gpt-oss-20b"
ANSWER_MODEL_API_KEY: str = "test_api_key"

JUDGE_MODEL_BASE_URL: str = "https://api.groq.com/openai/v1"
JUDGE_MODEL = "openai/gpt-oss-120b"
JUDGE_MODEL_API_KEY: str = "test_api_key"


async def main(argv: list[str] | None = None) -> int:
    summary_file = Path(SUMMARY_FILE)

    dataset_loader = WixQaDatasetLoader()
    benchmark = RagBenchmark(dataset_loader)
    rag_client = build_rag_clients()
    summary = benchmark.run_queries(
        rag_client=rag_client,
        top_k=RAG_QUERY_TOP_K,
        hybrid_search=RAG_QUERY_HYBRID_SEARCH,
        hybrid_search_bm25_top_k=RAG_QUERY_HYBRID_SEARCH_BM25_TOP_K,
        hybrid_search_semantic_top_k=RAG_QUERY_HYBRID_SEARCH_SEMANTIC_TOP_K,
    )
    # answer_judge_clients = build_llm_clients(
    #     model_api_key=ANSWER_MODEL_API_KEY,
    #     model_base_url=ANSWER_MODEL_BASE_URL,
    # )
    # judge_clients = build_llm_clients(
    #     model_api_key=JUDGE_MODEL_API_KEY,
    #     model_base_url=JUDGE_MODEL_BASE_URL,
    # )
    # summary = benchmark.run_queries_with_llm(
    #     rag_client=rag_client,
    #     top_k=RAG_QUERY_TOP_K,
    #     hybrid_search=RAG_QUERY_HYBRID_SEARCH,
    #     hybrid_search_bm25_top_k=RAG_QUERY_HYBRID_SEARCH_BM25_TOP_K,
    #     hybrid_search_semantic_top_k=RAG_QUERY_HYBRID_SEARCH_SEMANTIC_TOP_K,
    #     answer_client=answer_judge_clients,
    #     judge_client=judge_clients,
    #     answer_model=ANSWER_MODEL,
    #     judge_model=JUDGE_MODEL,
    # )

    write_summary(summary_file, summary)
    print(f"summary written to {summary_file}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
