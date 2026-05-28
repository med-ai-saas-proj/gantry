from __future__ import annotations

import re
import abc
import json
import time
import asyncio
from typing import Any, Iterable, Sequence, TypedDict
from pathlib import Path
from datetime import datetime

import httpx
from openai import OpenAI


RAG_BASE_URL = "http://localhost:8000"
RAG_API_KEY: str = "bypass_key"

RAG_TIMEOUT_SECONDS: int = 60


def build_llm_clients(
    model_api_key: str,
    model_base_url: str,
) -> OpenAI:
    client_kwargs: dict[str, Any] = (
        {"api_key": model_api_key} if model_api_key else {}
    )
    if model_base_url:
        client_kwargs["base_url"] = model_base_url
    llm_client = OpenAI(**client_kwargs)

    return llm_client


def build_rag_clients(
    rag_base_url: str = RAG_BASE_URL,
    rag_api_key: str = RAG_API_KEY,
    rag_timeout_seconds: int = RAG_TIMEOUT_SECONDS,
) -> httpx.Client:
    return httpx.Client(
        base_url=rag_base_url,
        timeout=httpx.Timeout(rag_timeout_seconds),
        headers={
            "Authorization": f"Bearer {rag_api_key}",
            "X-Api-Key": rag_api_key,
            "Content-Type": "application/json",
        },
    )


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Judge output did not contain JSON: {text}")
    return json.loads(stripped[start : end + 1])


class DatasetDocument(TypedDict):
    doc_id: str
    title: str
    source_type: str
    content: str


class DatasetQuestion(TypedDict):
    question_id: str
    question_type: str
    question: str
    expected_doc_ids: list[str]
    gold_answer: str
    answer_facts: list[str]


class DatasetLoader(abc.ABC):
    @abc.abstractmethod
    def load_questions(self) -> list[DatasetQuestion]:
        """Load questions from the dataset."""
        pass

    @abc.abstractmethod
    def load_all_documents(
        self, offset: int | None = None, limit: int | None = None
    ) -> list[DatasetDocument]:
        """Load all documents from the dataset, with optional pagination."""
        pass

    @abc.abstractmethod
    def load_all_documents_with_ids(
        self, ids: list[str]
    ) -> list[DatasetDocument]:
        """Load all documents from the dataset that match the given list of document IDs."""
        pass


def chunked(items: list[Any], size: int) -> Iterable[list[Any]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def wait_for_task(
    rag_client: httpx.Client,
    task_id: str,
    task_timeout_seconds: int,
    task_poll_interval_seconds: float,
) -> None:
    deadline = time.monotonic() + task_timeout_seconds
    while True:
        response = rag_client.get(f"/service/v1/rag/service/files/{task_id}")
        response.raise_for_status()
        task_info = response.json()
        status = str(task_info.get("status", ""))
        if status == "completed":
            return
        if status in {"failed_and_dropped"}:
            raise RuntimeError(
                f"Embedding task {task_id} did not complete successfully: {task_info}"
            )
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Timed out waiting for embedding task {task_id} to complete. Last status: {task_info}"
            )
        time.sleep(task_poll_interval_seconds)


def build_rag_db_api_call(
    rag_client: httpx.Client,
    documents: list[DatasetDocument],
    *,
    document_batch_size: int,
    chunk_size: int,
    chunk_overlap: int,
    chunk_splitter: str = "recursive",
    task_timeout_seconds: int,
    task_poll_interval_seconds: float,
) -> dict[str, Any]:
    if not documents:
        return {"documents_ingested": 0, "tasks": []}

    tasks: list[dict[str, Any]] = []
    for idx, batch in enumerate(chunked(documents, document_batch_size)):
        print(f"Ingesting batch {idx + 1} with {len(batch)} documents...")
        for document in batch:
            payload = {
                "text": document["content"],
                "metadata": {
                    "doc_id": document["doc_id"],
                    "title": document.get("title", ""),
                    "source_type": document.get("source_type", ""),
                },
                "lang": "simple",
                "chunk_splitter": chunk_splitter,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
            }
            response = rag_client.post(
                "/service/v1/rag/service/text", json=payload
            )
            response.raise_for_status()
            task_id = str(response.json())
            wait_for_task(
                rag_client,
                task_id,
                task_timeout_seconds,
                task_poll_interval_seconds,
            )
            tasks.append({"task_id": task_id, "documents": len(batch)})

    return {"documents_ingested": len(documents), "tasks": tasks}


async def build_rag_db_direct_call(
    documents: list[DatasetDocument],
    *,
    document_batch_size: int,
    chunk_size: int,
    chunk_overlap: int,
    chunk_splitter: str = "recursive",
) -> dict[str, Any]:
    from gantry.service.rag.factories import getRagService

    rag_service = getRagService()

    if not documents:
        return {"documents_ingested": 0}

    for idx, batch in enumerate(chunked(documents, document_batch_size)):
        print(f"Ingesting batch {idx + 1} with {len(batch)} documents...")
        tasks = []
        for document in batch:
            payload = {
                "text": document["content"],
                "metadata": {
                    "doc_id": document["doc_id"],
                    "title": document.get("title", ""),
                    "source_type": document.get("source_type", ""),
                },
                "lang": "simple",
                "chunk_splitter": chunk_splitter,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
            }
            task = rag_service.processEmbeddingText(
                project_id=0,
                text=payload["text"],
                metadata=payload["metadata"],
                lang=payload["lang"],
                chunk_splitter=payload["chunk_splitter"],
                chunk_size=payload["chunk_size"],
                chunk_overlap=payload["chunk_overlap"],
            )
            tasks.append(task)
        await asyncio.gather(*tasks)

    return {"documents_ingested": len(documents)}


def query_rag(
    rag_client: httpx.Client,
    question: str,
    *,
    top_k: int,
    hybrid_search: bool,
    hybrid_search_bm25_top_k: int,
    hybrid_search_semantic_top_k: int,
) -> list[dict[str, Any]]:
    response = rag_client.post(
        "/service/v1/rag/service/query/text",
        json={
            "query_text": question,
            "top_k": top_k,
            "hybrid_search": hybrid_search,
            "hybrid_search_bm25_top_k": hybrid_search_bm25_top_k,
            "hybrid_search_semantic_top_k": hybrid_search_semantic_top_k,
        },
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected RAG query response: {payload!r}")
    return payload


def unique_doc_ids(retrieved_chunks: Sequence[dict[str, Any]]) -> list[str]:
    """Extract unique document ids from retrieved chunks."""
    seen: set[str] = set()
    doc_ids: list[str] = []
    for chunk in retrieved_chunks:
        meta = chunk.get("metadata")
        doc_id = None
        if isinstance(meta, dict):
            doc_id = meta.get("doc_id")
        if not doc_id or doc_id in seen:
            continue
        seen.add(doc_id)
        doc_ids.append(str(doc_id))
    return doc_ids


def generate_answer(
    answer_client: OpenAI,
    *,
    model: str,
    question: str,
    retrieved_chunks: list[dict[str, Any]],
) -> str:
    context_lines: list[str] = []

    for index, chunk in enumerate(retrieved_chunks, start=1):
        chunk_text = str(chunk.get("text", "")).strip()

        metadata = chunk.get("metadata") or {}
        doc_id = metadata.get("doc_id")

        source_id = str(doc_id) if doc_id else f"chunk-{index}"

        context_lines.append(f"SOURCE: [{source_id}]\n{chunk_text}")

    context = (
        "\n\n".join(context_lines) if context_lines else "NO_RETRIEVED_CONTEXT"
    )

    system_prompt = """
You are an enterprise RAG assistant.

Your task:
- Answer the user's question ONLY using the provided context.
- Do NOT use external knowledge.
- Do NOT guess or infer unsupported facts.
- If the answer cannot be fully determined from the context, explicitly say so.
- Prefer concise, factual answers.
- Cite supporting sources using square brackets like [doc_id].
- Only cite sources actually used.
- If multiple sources support a statement, cite all relevant sources.
- Never fabricate citations.
- Mustn't call any tools or APIs, only use the provided context.

Output requirements:
- Produce only the final answer.
- Do not explain your reasoning process.
"""

    user_prompt = f"""
QUESTION:
{question}

CONTEXT:
{context}
"""

    response = answer_client.chat.completions.create(
        model=model,
        temperature=0,
        tools=[],
        tool_choice="none",
        messages=[
            {
                "role": "system",
                "content": system_prompt.strip(),
            },
            {
                "role": "user",
                "content": user_prompt.strip(),
            },
        ],
    )

    content = response.choices[0].message.content

    if content is None:
        raise RuntimeError("The answer model returned an empty response.")

    print(f"Generated answer: {content.strip()}")
    return content.strip()


def judge_answer(
    judge_client: OpenAI,
    *,
    model: str,
    question: DatasetQuestion,
    answer: str,
    retrieved_doc_ids: list[str],
) -> dict[str, Any]:

    system_prompt = """
You are a strict RAG evaluation judge.

Evaluate the assistant answer against:
1. the gold answer
2. required answer facts
3. retrieved documents

Evaluation criteria:

CORRECTNESS (boolean)
- true:
  - the answer is factually correct
  - no major hallucinations
  - no contradictions to the gold answer
- false:
  - contains incorrect claims
  - contradicts the gold answer
  - major hallucinations
  - misses the core answer

COMPLETENESS (0.0 - 1.0)
Measures how fully the assistant covered the expected answer facts.
Guidelines:
- 1.0 = all major facts covered
- 0.7 = most important facts covered
- 0.5 = partial answer
- 0.2 = minimal useful information
- 0.0 = completely missing answer

RECALL (0.0 - 1.0)
Measures whether the retrieved documents contained the necessary information.
This evaluates retrieval quality, NOT answer quality.
Use:
- expected_doc_ids
- retrieved_doc_ids

Guidelines:
- 1.0 = all required documents retrieved
- 0.5 = some required documents retrieved
- 0.0 = no required documents retrieved

Important:
- Penalize hallucinated information.
- Penalize unsupported claims.
- The assistant should not receive high completeness if key facts are missing.
- Be strict and consistent.
- Mustn't call any tools or APIs, only use the provided context.

Return ONLY valid JSON.

Required schema:
{
  "correctness": boolean,
  "completeness": number,
  "recall": number,
  "reason": string
}
"""

    user_payload = {
        "question_id": question["question_id"],
        "question": question["question"],
        "gold_answer": question["gold_answer"],
        "answer_facts": question["answer_facts"],
        "assistant_answer": answer,
        "expected_doc_ids": question["expected_doc_ids"],
        "retrieved_doc_ids": retrieved_doc_ids,
    }

    response = judge_client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        tools=[],
        tool_choice="none",
        messages=[
            {
                "role": "system",
                "content": system_prompt.strip(),
            },
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False),
            },
        ],
    )

    content = response.choices[0].message.content

    if content is None:
        raise RuntimeError("The judge model returned an empty response.")

    parsed = extract_json_object(content)
    print(
        f"Judge evaluation: {json.dumps(parsed, indent=2, ensure_ascii=False)}"
    )

    correctness = bool(parsed.get("correctness", False))
    completeness = float(parsed.get("completeness", 0.0))
    recall = float(parsed.get("recall", 0.0))
    reason = str(parsed.get("reason", ""))
    return {
        "correctness": correctness,
        "completeness": max(0.0, min(1.0, completeness)),
        "recall": max(0.0, min(1.0, recall)),
        "reason": reason,
    }


def run_queries(
    rag_client: httpx.Client,
    questions: list[DatasetQuestion],
    top_k: int,
    hybrid_search: bool,
    hybrid_search_bm25_top_k: int,
    hybrid_search_semantic_top_k: int,
):
    results: list[dict[str, Any]] = []
    for question in questions:
        start_time = datetime.now()
        retrieved_chunks = query_rag(
            rag_client,
            question["question"],
            top_k=top_k,
            hybrid_search=hybrid_search,
            hybrid_search_bm25_top_k=hybrid_search_bm25_top_k,
            hybrid_search_semantic_top_k=hybrid_search_semantic_top_k,
        )
        end_time = datetime.now()
        latency_seconds = (end_time - start_time).total_seconds()
        print(
            f"Question ID {question['question_id']} retrieved {len(retrieved_chunks)} chunks in {latency_seconds} seconds."
        )
        retrieved_doc_ids = unique_doc_ids(retrieved_chunks)
        expected_doc_ids = set(question["expected_doc_ids"])
        retrieved_doc_recall = (
            len(expected_doc_ids & set(retrieved_doc_ids))
            / len(expected_doc_ids)
            if expected_doc_ids
            else None
        )

        results.append(
            {
                "question_id": question["question_id"],
                "question_type": question["question_type"],
                "question": question["question"],
                "expected_doc_ids": question["expected_doc_ids"],
                "retrieved_documents": retrieved_chunks,
                "retrieved_doc_ids": retrieved_doc_ids,
                "retrieved_doc_recall": retrieved_doc_recall,
                "latency_seconds": latency_seconds,
            }
        )

    not_none_results = [
        item for item in results if item.get("retrieved_doc_recall") is not None
    ]
    average_retrieved_doc_recall = sum(
        float(item["retrieved_doc_recall"]) for item in not_none_results
    ) / len(not_none_results)

    average_latency_seconds = sum(
        float(item["latency_seconds"]) for item in results
    ) / len(results)

    return {
        "questions_processed": len(results),
        "average_retrieved_doc_recall": average_retrieved_doc_recall,
        "results": results,
        "average_latency_seconds": average_latency_seconds,
    }


def run_queries_with_llm(
    rag_client: httpx.Client,
    questions: list[DatasetQuestion],
    top_k: int,
    hybrid_search: bool,
    hybrid_search_bm25_top_k: int,
    hybrid_search_semantic_top_k: int,
    answer_client: OpenAI,
    answer_model: str,
    judge_client: OpenAI,
    judge_model: str,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for question in questions:
        start_time = datetime.now()
        retrieved_chunks = query_rag(
            rag_client,
            question["question"],
            top_k=top_k,
            hybrid_search=hybrid_search,
            hybrid_search_bm25_top_k=hybrid_search_bm25_top_k,
            hybrid_search_semantic_top_k=hybrid_search_semantic_top_k,
        )
        end_time = datetime.now()
        latency_seconds = (end_time - start_time).total_seconds()
        print(
            f"Question ID {question['question_id']} retrieved {len(retrieved_chunks)} chunks in {latency_seconds} seconds."
        )
        retrieved_doc_ids = unique_doc_ids(retrieved_chunks)
        expected_doc_ids = set(question["expected_doc_ids"])
        retrieved_doc_recall = (
            len(expected_doc_ids & set(retrieved_doc_ids))
            / len(expected_doc_ids)
            if expected_doc_ids
            else None
        )

        answer = generate_answer(
            answer_client,
            model=answer_model,
            question=question["question"],
            retrieved_chunks=retrieved_chunks,
        )
        judgement = judge_answer(
            judge_client,
            model=judge_model,
            question=question,
            answer=answer,
            retrieved_doc_ids=retrieved_doc_ids,
        )

        results.append(
            {
                "question_id": question["question_id"],
                "question_type": question["question_type"],
                "question": question["question"],
                "expected_doc_ids": question["expected_doc_ids"],
                "retrieved_documents": retrieved_chunks,
                "retrieved_doc_ids": retrieved_doc_ids,
                "retrieved_doc_recall": retrieved_doc_recall,
                "latency_seconds": latency_seconds,
                "response": answer,
                "judgement": judgement,
            }
        )

    average_correctness = sum(
        1.0 if item["judgement"]["correctness"] else 0.0 for item in results
    ) / len(results)
    average_completeness = sum(
        float(item["judgement"]["completeness"]) for item in results
    ) / len(results)
    average_llm_judge_recall = sum(
        float(item["judgement"]["recall"]) for item in results
    ) / len(results)

    not_none_results = [
        item for item in results if item.get("retrieved_doc_recall") is not None
    ]
    average_retrieved_doc_recall = sum(
        float(item["retrieved_doc_recall"]) for item in not_none_results
    ) / len(not_none_results)

    average_latency_seconds = sum(
        float(item["latency_seconds"]) for item in results
    ) / len(results)

    return {
        "questions_processed": len(results),
        "average_correctness": average_correctness,
        "average_completeness": average_completeness,
        "average_llm_judge_recall": average_llm_judge_recall,
        "average_retrieved_doc_recall": average_retrieved_doc_recall,
        "results": results,
        "average_latency_seconds": average_latency_seconds,
    }


def write_summary(summary_file: Path, payload: dict[str, Any]) -> None:
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


class RagBenchmark:
    def __init__(self, dataset_loader: DatasetLoader):
        self.dataset_loader = dataset_loader

    async def build_rag_api(
        self,
        rag_client: httpx.Client,
        task_timeout_seconds: int,
        task_poll_interval_seconds: float,
        offset: int | None,
        limit: int | None,
        document_batch_size: int,
        chunk_size: int,
        chunk_overlap: int,
        chunk_splitter: str = "recursive",
    ):
        documents = self.dataset_loader.load_all_documents(
            offset=offset, limit=limit
        )
        build_rag_db_api_call(
            rag_client,
            documents,
            document_batch_size=document_batch_size,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            task_timeout_seconds=task_timeout_seconds,
            task_poll_interval_seconds=task_poll_interval_seconds,
            chunk_splitter=chunk_splitter,
        )

        questions = self.dataset_loader.load_questions()

        required_docs = set()
        for question in questions:
            for doc_id in question["expected_doc_ids"]:
                required_docs.add(doc_id)
        print(
            f"Loading required {len(required_docs)} documents required for questions..."
        )

        documents_for_required_docs = (
            self.dataset_loader.load_all_documents_with_ids(list(required_docs))
        )
        build_rag_db_api_call(
            rag_client,
            documents_for_required_docs,
            document_batch_size=document_batch_size,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            task_timeout_seconds=task_timeout_seconds,
            task_poll_interval_seconds=task_poll_interval_seconds,
            chunk_splitter=chunk_splitter,
        )

    async def build_rag_direct(
        self,
        offset: int | None,
        limit: int | None,
        document_batch_size: int,
        chunk_size: int,
        chunk_overlap: int,
        chunk_splitter: str = "recursive",
    ):
        documents = self.dataset_loader.load_all_documents(
            offset=offset, limit=limit
        )
        await build_rag_db_direct_call(
            documents,
            document_batch_size=document_batch_size,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunk_splitter=chunk_splitter,
        )

        questions = self.dataset_loader.load_questions()

        required_docs = set()
        for question in questions:
            for doc_id in question["expected_doc_ids"]:
                required_docs.add(doc_id)
        print(
            f"Loading required {len(required_docs)} documents required for questions..."
        )

        documents_for_required_docs = (
            self.dataset_loader.load_all_documents_with_ids(list(required_docs))
        )
        await build_rag_db_direct_call(
            documents_for_required_docs,
            document_batch_size=document_batch_size,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunk_splitter=chunk_splitter,
        )

    def run_queries_with_llm(
        self,
        rag_client: httpx.Client,
        top_k: int,
        hybrid_search: bool,
        hybrid_search_bm25_top_k: int,
        hybrid_search_semantic_top_k: int,
        answer_client: OpenAI,
        judge_client: OpenAI,
        answer_model: str,
        judge_model: str,
    ) -> dict[str, Any]:
        questions = self.dataset_loader.load_questions()
        return run_queries_with_llm(
            rag_client,
            questions,
            top_k=top_k,
            hybrid_search=hybrid_search,
            hybrid_search_bm25_top_k=hybrid_search_bm25_top_k,
            hybrid_search_semantic_top_k=hybrid_search_semantic_top_k,
            answer_client=answer_client,
            answer_model=answer_model,
            judge_client=judge_client,
            judge_model=judge_model,
        )

    def run_queries(
        self,
        rag_client: httpx.Client,
        top_k: int,
        hybrid_search: bool,
        hybrid_search_bm25_top_k: int,
        hybrid_search_semantic_top_k: int,
    ) -> dict[str, Any]:
        questions = self.dataset_loader.load_questions()
        return run_queries(
            rag_client,
            questions,
            top_k=top_k,
            hybrid_search=hybrid_search,
            hybrid_search_bm25_top_k=hybrid_search_bm25_top_k,
            hybrid_search_semantic_top_k=hybrid_search_semantic_top_k,
        )
