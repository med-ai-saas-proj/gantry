from __future__ import annotations

from gantry.service.rag.benchmark.test_shared import (
    DatasetLoader,
    DatasetDocument,
    DatasetQuestion,
)

from typing import Any, Iterable, TypedDict, cast

from datasets import load_dataset


DATASET_NAME = "onyx-dot-app/EnterpriseRAG-Bench"
DOCUMENT_CONFIG_NAME = "documents"
QUESTION_CONFIG_NAME = "questions"


class QuestionRow(TypedDict):
    question_id: Any
    question_type: str
    question: str
    expected_doc_ids: list[Any]
    gold_answer: str
    answer_facts: list[Any]


class DocumentRow(TypedDict):
    doc_id: Any
    title: str
    source_type: str
    content: str


class EnterpriseRagDatasetLoader(DatasetLoader):
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
                    "question_id": str(qrow["question_id"]),
                    "question_type": str(qrow.get("question_type", "unknown")),
                    "question": str(qrow["question"]),
                    "expected_doc_ids": [
                        str(doc_id)
                        for doc_id in qrow.get("expected_doc_ids", [])
                    ],
                    "gold_answer": str(qrow.get("gold_answer", "")),
                    "answer_facts": [
                        str(fact) for fact in qrow.get("answer_facts", [])
                    ],
                }
            )
            # no limit; collect all questions from the dataset split

        if not questions:
            raise RuntimeError(
                "No questions were loaded from EnterpriseRAG-Bench."
            )
        return questions

    def load_all_documents(
        self, offset: int | None = None, limit: int | None = None
    ) -> list[DatasetDocument]:
        """Load all documents from the dataset `documents` split."""
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
                    "doc_id": str(drow["doc_id"]),
                    "title": str(drow.get("title", "")),
                    "source_type": str(drow.get("source_type", "unknown")),
                    "content": str(drow.get("content", "")),
                }
            )

        if not docs:
            raise RuntimeError(
                "No documents were loaded from EnterpriseRAG-Bench."
            )
        return docs

    def load_all_documents_with_ids(
        self, ids: list[str]
    ) -> list[DatasetDocument]:
        """Load all documents from the dataset `documents` split."""
        document_rows: Iterable[Any] = load_dataset(
            DATASET_NAME,
            DOCUMENT_CONFIG_NAME,
            split="test",
        )

        docs: list[DatasetDocument] = []
        for row in document_rows:
            drow = cast(DocumentRow, row)
            if str(drow["doc_id"]) not in ids:
                continue
            docs.append(
                {
                    "doc_id": str(drow["doc_id"]),
                    "title": str(drow.get("title", "")),
                    "source_type": str(drow.get("source_type", "unknown")),
                    "content": str(drow.get("content", "")),
                }
            )

        if not docs:
            raise RuntimeError(
                "No documents were loaded from EnterpriseRAG-Bench."
            )
        return docs
