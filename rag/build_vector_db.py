import argparse
import os
import re
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
CLEANED_DIR = PROJECT_DIR / "data" / "cleaned"
DB_DIR = PROJECT_DIR / "rag" / "chroma_db"

COLLECTIONS = {
    "medical": "medical_knowledge",
    "drug": "drug_safety",
}

DEFAULT_MODEL = os.environ.get(
    "EMBEDDING_MODEL",
    str(PROJECT_DIR / "models" / "bge-small-zh-v1.5")
)


def clean_text(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    text = clean_text(text)
    chunks = []
    start = 0

    while start < len(text):
        chunk = text[start:start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def load_raw_docs(category: str) -> list[dict]:
    folder = RAW_DIR / category
    if not folder.exists():
        raise FileNotFoundError(f"Raw data folder not found: {folder}")

    docs = []
    for path in sorted(folder.rglob("*")):
        if path.suffix.lower() not in {".txt", ".md"}:
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        cleaned = clean_text(text)
        if not cleaned:
            continue

        docs.append({
            "source": str(path.relative_to(PROJECT_DIR)),
            "category": category,
            "text": cleaned,
        })

    return docs


def save_cleaned_doc(category: str, source: str, text: str) -> None:
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = source.replace("/", "__").replace("\\", "__")
    out_path = CLEANED_DIR / f"{category}__{safe_name}.txt"
    out_path.write_text(text, encoding="utf-8")


def build_collection(category: str, chunk_size: int, overlap: int, model_name: str) -> None:
    collection_name = COLLECTIONS[category]
    print(f"\nBuilding collection: {collection_name}")

    docs = load_raw_docs(category)
    print(f"Loaded {len(docs)} raw documents from {RAW_DIR / category}")

    embedder = SentenceTransformer(model_name)
    client = chromadb.PersistentClient(path=str(DB_DIR))

    existing = [c.name for c in client.list_collections()]
    if collection_name in existing:
        client.delete_collection(collection_name)
        print(f"Deleted old collection: {collection_name}")

    collection = client.create_collection(
        name=collection_name,
        metadata={
            "category": category,
            "chunk_size": chunk_size,
            "overlap": overlap,
        },
    )

    ids, documents, embeddings, metadatas = [], [], [], []
    idx = 0

    for doc in docs:
        save_cleaned_doc(category, doc["source"], doc["text"])
        chunks = split_text(doc["text"], chunk_size=chunk_size, overlap=overlap)
        print(f"  {doc['source']} -> {len(chunks)} chunks")

        for chunk_index, chunk in enumerate(chunks):
            ids.append(f"{category}_{idx:05d}")
            documents.append(chunk)
            embeddings.append(embedder.encode(chunk).tolist())
            metadatas.append({
                "source": doc["source"],
                "category": category,
                "chunk_index": chunk_index,
            })
            idx += 1

    if ids:
        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    print(f"Done: {collection_name}, total chunks: {collection.count()}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-size", type=int, default=450)
    parser.add_argument("--overlap", type=int, default=80)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    DB_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Project dir: {PROJECT_DIR}")
    print(f"Raw data dir: {RAW_DIR}")
    print(f"ChromaDB dir: {DB_DIR}")
    print(f"Embedding model: {args.model}")

    build_collection("medical", args.chunk_size, args.overlap, args.model)
    build_collection("drug", args.chunk_size, args.overlap, args.model)


if __name__ == "__main__":
    main()
