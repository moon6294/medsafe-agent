from pathlib import Path
from typing import Dict

import chromadb
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[1]

VECTOR_DB_PATH = PROJECT_ROOT / "rag" / "chroma_db"
LOCAL_MODEL_PATH = PROJECT_ROOT / "models" / "bge-small-zh-v1.5"

COLLECTION_MEDICAL = "medical_knowledge"
COLLECTION_DRUG = "drug_safety"


class MedicalKnowledgeRetriever:
    def __init__(self):
        self.embedder = self._load_embedder()
        self.client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))

    def _load_embedder(self) -> SentenceTransformer:
        if LOCAL_MODEL_PATH.exists():
            return SentenceTransformer(str(LOCAL_MODEL_PATH))

        return SentenceTransformer("BAAI/bge-small-zh-v1.5")

    def _search_collection(
        self,
        collection_name: str,
        query: str,
        top_k: int = 4,
        distance_threshold: float = 0.90,
    ) -> Dict:
        collection = self.client.get_collection(collection_name)
        query_embedding = self.embedder.encode(query).tolist()

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        for i in range(len(results["ids"][0])):
            metadata = results["metadatas"][0][i] or {}
            distance = float(results["distances"][0][i])

            hits.append({
                "rank": i + 1,
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "source": metadata.get("source", ""),
                "category": metadata.get("category", ""),
                "chunk_index": metadata.get("chunk_index", -1),
                "distance": distance,
                "reliable": distance <= distance_threshold,
            })

        return {
            "query": query,
            "collection": collection_name,
            "top_k": top_k,
            "distance_threshold": distance_threshold,
            "has_reliable_evidence": any(hit["reliable"] for hit in hits),
            "hits": hits,
        }

    def search_medical(
        self,
        query: str,
        top_k: int = 4,
        distance_threshold: float = 0.90,
    ) -> Dict:
        return self._search_collection(
            COLLECTION_MEDICAL,
            query,
            top_k=top_k,
            distance_threshold=distance_threshold,
        )

    def search_drug_safety(
        self,
        query: str,
        top_k: int = 4,
        distance_threshold: float = 0.90,
    ) -> Dict:
        return self._search_collection(
            COLLECTION_DRUG,
            query,
            top_k=top_k,
            distance_threshold=distance_threshold,
        )


retriever = MedicalKnowledgeRetriever()


if __name__ == "__main__":
    print("测试医疗科普检索：")
    print(retriever.search_medical("高血压日常怎么管理？", top_k=2))

    print("\n测试用药安全检索：")
    print(retriever.search_drug_safety("布洛芬有哪些注意事项？", top_k=2))
