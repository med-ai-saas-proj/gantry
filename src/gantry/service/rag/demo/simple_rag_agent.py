"""
Simple RAG Agent with Groq LLM

This agent demonstrates how to:
1. Query the RAG API to retrieve relevant documents
2. Use Groq (via OpenAI client) to generate responses based on retrieved context

Example usage:
    python simple_rag_agent.py
"""

import os
from typing import Optional
from dataclasses import dataclass

import requests
from openai import OpenAI


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY environment variable not set. Please set it to your Groq API key."
    )

GANTRY_API_KEY = "bypass_key"  # Or use your actual API key from Gantry
GANTRY_BASE_URL = "http://localhost:8000"


# ==============================================================================
# Groq LLM Configuration
# ==============================================================================
groq_client = OpenAI(
    api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1"
)

MODEL = "openai/gpt-oss-20b"


@dataclass
class RagDocument:
    """Represents a document retrieved from RAG"""

    text: str
    filename: str
    file_id: str
    mime_type: str
    size: int
    created_at: str
    chunk_start: int = 0  # Character position where chunk starts
    chunk_end: int = 0  # Character position where chunk ends

    def get_reference(self) -> str:
        """Get formatted reference for this document with chunk info"""
        chunk_info = (
            f"chunk [{self.chunk_start}-{self.chunk_end}]"
            if self.chunk_end > 0
            else "full document"
        )
        return f"[{self.filename} (ID: {self.file_id}, {self.size} bytes, {self.mime_type}, {chunk_info})]"

    def get_short_reference(self) -> str:
        """Get short reference for inline citations"""
        return f"[{self.filename}]"

    def get_chunk_preview(self, max_length: int = 150) -> str:
        """Get a preview of the chunk used"""
        preview = self.text[:max_length]
        if len(self.text) > max_length:
            preview += "..."
        return preview


def query_rag_by_text(
    query_text: str, top_k: int = 5, include_embedding: bool = False
) -> list[RagDocument]:
    """
    Query the RAG API by text.

    Args:
        query_text: The text query to search for
        top_k: Maximum number of results to return (1-100)
        include_embedding: Whether to include embedding vectors

    Returns:
        List of RagDocument objects
    """
    endpoint = f"{GANTRY_BASE_URL}/service/v1/rag/service/query/text"

    headers = {"X-Api-Key": GANTRY_API_KEY, "Content-Type": "application/json"}

    payload = {
        "query_text": query_text,
        "top_k": min(top_k, 100),
    }

    params = {"include_embedding": str(include_embedding).lower()}

    try:
        response = requests.post(
            endpoint, headers=headers, json=payload, params=params, timeout=30
        )
        response.raise_for_status()

        results = response.json()
        documents = [
            RagDocument(
                text=result.get("text", ""),
                filename=result.get("file_info", {}).get("filename", ""),
                file_id=result.get("file_info", {}).get("id", ""),
                mime_type=result.get("file_info", {}).get(
                    "mime_type", "unknown"
                ),
                size=result.get("file_info", {}).get("size", 0),
                created_at=result.get("created_at", ""),
                chunk_start=result.get("chunk_start", 0),
                chunk_end=result.get("chunk_end", len(result.get("text", ""))),
            )
            for result in results
        ]
        return documents

    except requests.exceptions.RequestException as e:
        print(f"Error querying RAG API: {e}")
        return []


def generate_response(
    user_query: str,
    rag_documents: list[RagDocument],
    system_prompt: Optional[str] = None,
    include_citations: bool = True,
) -> tuple[str, list[RagDocument]]:
    """
    Generate a response using Groq LLM with RAG context.

    Args:
        user_query: The original user query
        rag_documents: Documents retrieved from RAG
        system_prompt: Optional system prompt
        include_citations: Whether to include document citations

    Returns:
        Tuple of (generated response, list of documents used)
    """

    if not system_prompt:
        system_prompt = (
            "You are a helpful assistant that answers questions based on "
            "the provided documents. Always cite your sources by including "
            "the document filename in brackets when referencing information. "
            "If the documents don't contain relevant information, say so clearly."
        )

    # Format documents as context with references and chunk info
    context = ""
    if rag_documents:
        formatted_docs = []
        for idx, doc in enumerate(rag_documents, 1):
            doc_header = f"\n[Document {idx}] {doc.get_reference()}\n"
            chunk_range = (
                f"Chunk Position: chars {doc.chunk_start}-{doc.chunk_end} ({doc.chunk_end - doc.chunk_start} characters)\n"
                if doc.chunk_end > 0
                else ""
            )
            doc_content = f"Content: {doc.text}\n"
            doc_metadata = f"File ID: {doc.file_id} | MIME: {doc.mime_type} | Size: {doc.size} bytes | Created: {doc.created_at}\n"
            formatted_docs.append(
                doc_header + chunk_range + doc_content + doc_metadata
            )
        context = "---".join(formatted_docs)
    else:
        context = "No relevant documents were found."

    # Build the prompt with citation instructions
    user_message = f"""Based on the following documents, please answer the question.

IMPORTANT: When citing information, include the document reference in brackets like [Document 1] or [filename].

DOCUMENTS:
{context}

QUESTION: {user_query}

Please provide a clear and concise answer based on the documents provided, citing your sources."""

    try:
        message = groq_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=1024,
            temperature=0.7,
        )
        response_text = message.choices[0].message.content
        if response_text is None:
            response_text = (
                "Sorry, I couldn't generate a response at this time."
            )
        return response_text, rag_documents

    except Exception as e:
        print(f"Error generating response: {e}")
        return (
            "Sorry, I couldn't generate a response at this time.",
            rag_documents,
        )


def run_agent_loop():
    """Run an interactive agent loop"""
    print("=" * 80)
    print("Simple RAG Agent with Groq")
    print("=" * 80)
    print("\nThis agent will:")
    print("1. Query the RAG API for relevant documents")
    print("2. Generate a response using Groq LLM")
    print("\nType 'quit' or 'exit' to stop.\n")

    while True:
        try:
            user_query = input("\nYou: ").strip()

            if user_query.lower() in ["quit", "exit", "q"]:
                print("\nGoodbye!")
                break

            if not user_query:
                print("Please enter a question.")
                continue

            print("\nSearching RAG documents...")
            documents = query_rag_by_text(user_query, top_k=5)

            if documents:
                print(f"\nFound {len(documents)} relevant document(s):")
                for i, doc in enumerate(documents, 1):
                    print(f"  {i}. {doc.get_reference()}")
                    print(f"     📄 Chunk: {doc.get_chunk_preview()}")
            else:
                print("No documents found in RAG.")

            print("\nGenerating response...")
            response, docs_used = generate_response(user_query, documents)
            print(f"\nAgent: {response}")

            if docs_used:
                print(f"\n📚 Sources ({len(docs_used)} document(s) used):")
                for i, doc in enumerate(docs_used, 1):
                    print(f"   {i}. {doc.get_reference()}")
                    print(
                        f"      Position: chars {doc.chunk_start}-{doc.chunk_end}"
                    )
                    print(f"      Preview: {doc.get_chunk_preview()}")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
            continue


if __name__ == "__main__":
    run_agent_loop()
