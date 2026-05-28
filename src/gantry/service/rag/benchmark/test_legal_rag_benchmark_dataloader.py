from __future__ import annotations

from gantry.service.rag.benchmark.test_shared import (
    DatasetLoader,
    DatasetDocument,
    DatasetQuestion,
)

from typing import Any, Iterable, TypedDict, cast

from datasets import load_dataset


DATASET_NAME = "isaacus/legal-rag-bench"
DOCUMENT_CONFIG_NAME = "corpus"
QUESTION_CONFIG_NAME = "qa"


class QuestionRow(TypedDict):
    id: Any
    question: str
    answer: str
    relevant_passage_id: Any


class DocumentRow(TypedDict):
    id: Any
    text: str


class LegalRagDatasetLoader(DatasetLoader):
    def load_questions(
        self,
    ) -> list[DatasetQuestion]:
        question_rows: Iterable[Any] = load_dataset(
            DATASET_NAME,
            QUESTION_CONFIG_NAME,
            split="test",
        )

        questions: list[DatasetQuestion] = []
        for row in question_rows:
            qrow = cast(QuestionRow, row)
            questions.append(
                {
                    "question_id": str(qrow["id"]),
                    "question_type": "legal_qa",
                    "question": str(qrow["question"]),
                    "expected_doc_ids": [str(qrow["relevant_passage_id"])],
                    "gold_answer": str(qrow.get("answer", "")),
                    "answer_facts": [str(qrow.get("answer", ""))]
                    if qrow.get("answer")
                    else [],
                }
            )

        if not questions:
            raise RuntimeError("No questions were loaded from Legal RAG Bench.")
        return questions

    def load_all_documents(
        self, offset: int | None = None, limit: int | None = None
    ) -> list[DatasetDocument]:
        """Load all documents from the dataset `corpus` split."""
        document_rows: Iterable[Any] = load_dataset(
            DATASET_NAME,
            DOCUMENT_CONFIG_NAME,
            split="test",
        )

        start_offset = offset if offset is not None else 0

        docs: list[DatasetDocument] = []
        for idx, row in enumerate(document_rows):
            if idx < start_offset:
                continue

            if limit is not None and idx >= start_offset + limit:
                break

            drow = cast(DocumentRow, row)
            docs.append(
                {
                    "doc_id": str(drow["id"]),
                    "title": "",
                    "source_type": "corpus",
                    "content": str(drow["text"]),
                }
            )

        if not docs:
            raise RuntimeError("No documents were loaded from Legal RAG Bench.")
        return docs

    def load_all_documents_with_ids(
        self, ids: list[str]
    ) -> list[DatasetDocument]:
        """Load all documents from the dataset `corpus` split."""
        document_rows: Iterable[Any] = load_dataset(
            DATASET_NAME,
            DOCUMENT_CONFIG_NAME,
            split="test",
        )

        docs: list[DatasetDocument] = []
        for row in document_rows:
            drow = cast(DocumentRow, row)
            if str(drow["id"]) not in ids:
                continue
            docs.append(
                {
                    "doc_id": str(drow["id"]),
                    "title": "",
                    "source_type": "corpus",
                    "content": str(drow["text"]),
                }
            )

        if not docs:
            raise RuntimeError("No documents were loaded from Legal RAG Bench.")
        return docs
