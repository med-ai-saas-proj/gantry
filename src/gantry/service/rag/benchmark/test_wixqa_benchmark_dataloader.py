from __future__ import annotations

from gantry.service.rag.benchmark.test_shared import (
    DatasetLoader,
    DatasetDocument,
    DatasetQuestion,
)

from typing import Any, Iterable, TypedDict, cast

from datasets import load_dataset


class QuestionRow(TypedDict):
    question: str
    answer: str
    article_ids: list[str]


class DocumentRow(TypedDict):
    id: str
    url: str
    contents: str
    article_type: str


DATASET_NAME = "Wix/WixQA"
DOCUMENT_CONFIG_NAME = "wix_kb_corpus"
QUESTION_CONFIG_NAMES = ["wixqa_expertwritten", "wixqa_simulated"]


class WixQaDatasetLoader(DatasetLoader):
    def load_questions(
        self,
    ) -> list[DatasetQuestion]:
        questions: list[DatasetQuestion] = []
        for config_name in QUESTION_CONFIG_NAMES:
            question_rows: Iterable[Any] = load_dataset(
                DATASET_NAME,
                config_name,
                split="train",
            )
            for index, row in enumerate(question_rows):
                qrow = cast(QuestionRow, row)
                questions.append(
                    {
                        "question_id": f"{config_name}:{index}",
                        "question_type": config_name,
                        "question": str(qrow["question"]),
                        "expected_doc_ids": [
                            str(article_id)
                            for article_id in qrow.get("article_ids", [])
                        ],
                        "gold_answer": str(qrow.get("answer", "")),
                        "answer_facts": [str(qrow.get("answer", ""))]
                        if qrow.get("answer")
                        else [],
                    }
                )

        if not questions:
            raise RuntimeError("No questions were loaded from WixQA.")
        return questions

    def load_all_documents(
        self, offset: int | None = None, limit: int | None = None
    ) -> list[DatasetDocument]:
        """Load all documents from the dataset `wix_kb_corpus` split."""
        document_rows: Iterable[Any] = load_dataset(
            DATASET_NAME,
            DOCUMENT_CONFIG_NAME,
            split="train",
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
                    "title": str(drow.get("url", "")),
                    "source_type": str(drow.get("article_type", "corpus")),
                    "content": str(drow.get("contents", "")),
                }
            )

        if not docs:
            raise RuntimeError("No documents were loaded from WixQA.")
        return docs

    def load_all_documents_with_ids(
        self, ids: list[str]
    ) -> list[DatasetDocument]:
        """Load all documents from the dataset `wix_kb_corpus` split."""
        document_rows: Iterable[Any] = load_dataset(
            DATASET_NAME,
            DOCUMENT_CONFIG_NAME,
            split="train",
        )

        docs: list[DatasetDocument] = []
        for row in document_rows:
            drow = cast(DocumentRow, row)
            if str(drow["id"]) not in ids:
                continue
            docs.append(
                {
                    "doc_id": str(drow["id"]),
                    "title": str(drow.get("url", "")),
                    "source_type": str(drow.get("article_type", "corpus")),
                    "content": str(drow.get("contents", "")),
                }
            )

        if not docs:
            raise RuntimeError("No documents were loaded from WixQA.")
        return docs
