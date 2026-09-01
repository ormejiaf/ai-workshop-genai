from pathlib import Path

from config import EMBEDDING_MODEL, VECTOR_DB_DIR
from sqlite_compat import enable_modern_sqlite

enable_modern_sqlite()

import chromadb
from sentence_transformers import SentenceTransformer


COLLECTION_NAME = "university_policies"


def collection():
    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    return client.get_or_create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def embed(texts: list[str]) -> list[list[float]]:
    return SentenceTransformer(EMBEDDING_MODEL).encode(texts).tolist()


def split_text(text: str, size: int = 700) -> list[str]:
    return [text[index:index + size] for index in range(0, len(text), size)]


def index_files(files: list[Path]) -> int:
    documents, ids, metadata = [], [], []
    for file in files:
        text = file.read_text(encoding="utf-8")
        title = text.splitlines()[0].removeprefix("# ")
        for index, chunk in enumerate(split_text(text)):
            documents.append(chunk)
            ids.append(f"{file.stem}-{index}")
            metadata.append({"source": title})
    if documents:
        collection().upsert(
            ids=ids,
            documents=documents,
            metadatas=metadata,
            embeddings=embed(documents),
        )
    return len(documents)


def search(question: str, limit: int = 4) -> list[dict]:
    policy_collection = collection()
    if not policy_collection.count():
        raise RuntimeError("No hay políticas indexadas. Ejecuta 06_index_knowledge.py.")
    result = policy_collection.query(
        query_embeddings=embed([question]),
        n_results=min(limit, policy_collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    return [
        {
            "text": document,
            "source": metadata["source"],
            "distance": round(distance, 3),
        }
        for document, metadata, distance in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0]
        )
    ]
