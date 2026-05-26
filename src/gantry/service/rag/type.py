from gantry.service.file_storage.types import FileRecord

import enum
import uuid
from typing import Any, Literal, Sequence, TypedDict
from datetime import datetime


class RagQueryRecord(TypedDict):
    file_info: FileRecord | None
    text: str
    embedding: Sequence[float]
    created_at: datetime
    rerank_score: float | None
    bm25_score: float | None
    vector_distance: float | None
    metadata: dict | None


class ChunkSplitterType(str, enum.Enum):
    simple = "simple"
    character = "character"
    recursive = "recursive"
    token = "token"
    markdown = "markdown"
    markdown_header = "markdown_header"
    html = "html"
    html_header = "html_header"
    html_semantic_preserving = "html_semantic_preserving"
    html_section = "html_section"
    recursive_json = "recursive_json"
    experimental_markdown_syntax = "experimental_markdown_syntax"
    code_language_c = "code_language_c"
    code_language_cobol = "code_language_cobol"
    code_language_cpp = "code_language_cpp"
    code_language_csharp = "code_language_csharp"
    code_language_go = "code_language_go"
    code_language_haskell = "code_language_haskell"
    code_language_html = "code_language_html"
    code_language_java = "code_language_java"
    code_language_jsx = "code_language_jsx"
    code_language_kotlin = "code_language_kotlin"
    code_language_latex = "code_language_latex"
    code_language_lua = "code_language_lua"
    code_language_markdown = "code_language_markdown"
    code_language_perl = "code_language_perl"
    code_language_php = "code_language_php"
    code_language_proto = "code_language_proto"
    code_language_python = "code_language_python"
    code_language_rst = "code_language_rst"
    code_language_ruby = "code_language_ruby"
    code_language_rust = "code_language_rust"
    code_language_scala = "code_language_scala"
    code_language_sol = "code_language_sol"
    code_language_swift = "code_language_swift"
    code_language_ts = "code_language_ts"
    code_language_js = "code_language_js"
    latex = "latex"
    nltk = "nltk"
    spacy = "spacy"
    konlpy = "konlpy"
    sentence_transformers_token = "sentence_transformers_token"
    paragraph = "paragraph"
    line = "line"


class CharacterTextSplitterOptions(TypedDict, total=False):
    separator: str
    is_separator_regex: bool
    chunk_size: int
    chunk_overlap: int
    keep_separator: bool | Literal["start", "end"]


class RecursiveCharacterTextSplitterOptions(TypedDict, total=False):
    separators: list[str]
    keep_separator: bool | Literal["start", "end"]
    is_separator_regex: bool
    chunk_size: int
    chunk_overlap: int


class RecursiveCharacterLanguageTextSplitterOptions(
    RecursiveCharacterTextSplitterOptions
):
    pass


class TokenTextSplitterOptions(TypedDict, total=False):
    encoding_name: str
    model_name: str | None
    allowed_special: Literal["all"] | set[str] | None
    disallowed_special: Literal["all"] | list[str]
    chunk_size: int
    chunk_overlap: int


class MarkdownHeaderTextSplitterOptions(TypedDict, total=False):
    headers_to_split_on: list[tuple[str, str]]
    return_each_line: bool
    strip_headers: bool
    custom_header_patterns: dict[str, int]


class MarkdownTextSplitterOptions(RecursiveCharacterTextSplitterOptions):
    pass


class ExperimentalMarkdownSyntaxTextSplitterOptions(
    MarkdownHeaderTextSplitterOptions
):
    pass


class HTMLHeaderTextSplitterOptions(TypedDict, total=False):
    headers_to_split_on: list[tuple[str, str]]
    return_each_element: bool


class HTMLSemanticPreservingSplitterOptions(TypedDict, total=False):
    headers_to_split_on: list[tuple[str, str]]
    max_chunk_size: int
    chunk_overlap: int
    separators: list[str]
    elements_to_preserve: list[str]
    preserve_links: bool
    preserve_images: bool
    preserve_videos: bool
    preserve_audio: bool
    custom_handlers: dict[str, Any]
    stopword_removal: bool
    stopword_lang: str
    normalize_text: bool
    external_metadata: dict[str, str]
    allowlist_tags: list[str]
    denylist_tags: list[str]
    preserve_parent_metadata: bool
    keep_separator: bool | Literal["start", "end"]


class HTMLSectionSplitterOptions(HTMLHeaderTextSplitterOptions):
    pass


class RecursiveJsonSplitterOptions(TypedDict, total=False):
    max_chunk_size: int
    min_chunk_size: int
    convert_lists: bool


class NLTKTextSplitterOptions(TypedDict, total=False):
    separator: str
    language: str
    use_span_tokenize: bool
    chunk_size: int
    chunk_overlap: int


class SpacyTextSplitterOptions(TypedDict, total=False):
    separator: str
    pipeline: str
    max_length: int
    strip_whitespace: bool
    chunk_size: int
    chunk_overlap: int


class KonlpyTextSplitterOptions(TypedDict, total=False):
    separator: str
    chunk_size: int
    chunk_overlap: int


class SentenceTransformersTokenTextSplitterOptions(TypedDict, total=False):
    chunk_overlap: int
    model_name: str
    tokens_per_chunk: int
    model_kwargs: dict[str, Any]
    chunk_size: int


ChunkSplitterOptions = (
    CharacterTextSplitterOptions
    | RecursiveCharacterTextSplitterOptions
    | TokenTextSplitterOptions
    | MarkdownHeaderTextSplitterOptions
    | MarkdownTextSplitterOptions
    | ExperimentalMarkdownSyntaxTextSplitterOptions
    | HTMLHeaderTextSplitterOptions
    | HTMLSemanticPreservingSplitterOptions
    | HTMLSectionSplitterOptions
    | RecursiveJsonSplitterOptions
    | NLTKTextSplitterOptions
    | SpacyTextSplitterOptions
    | KonlpyTextSplitterOptions
    | SentenceTransformersTokenTextSplitterOptions
    | RecursiveCharacterLanguageTextSplitterOptions
)


class EmbeddingTask(TypedDict):
    type: Literal["file", "text"]
    task_id: str
    file_id: int | None
    file_uid: uuid.UUID | None
    text: str | list[str] | None
    metadata: dict | None
    project_id: int
    project_uuid: uuid.UUID
    chunk_splitter: ChunkSplitterType
    chunk_splitter_options: ChunkSplitterOptions
    chunk_size: int
    chunk_overlap: int
    status: Literal[
        "pending", "completed", "failed_and_retrying", "failed_and_dropped"
    ]
    failed_reason: str | None
