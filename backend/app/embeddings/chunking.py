"""Splits generated documentation / schema text into embedding-sized chunks."""
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def chunk_text(text: str, metadata: dict) -> list[Document]:
    """Split `text` into overlapping chunks, each tagged with `metadata` so
    retrieved chunks can always be traced back to their source table/doc."""
    if not text or not text.strip():
        return []
    chunks = _splitter.split_text(text)
    return [Document(page_content=chunk, metadata=metadata) for chunk in chunks]


def chunk_documents(items: list[tuple[str, dict]]) -> list[Document]:
    """Bulk variant of chunk_text over a list of (text, metadata) pairs."""
    documents: list[Document] = []
    for text, metadata in items:
        documents.extend(chunk_text(text, metadata))
    return documents
