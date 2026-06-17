from pathlib import Path
import sys
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def medical_rag_search(
    query: str,
    top_k: int = 3,
    distance_threshold: float = 0.90
) -> Dict:
    """
    医疗科普知识库检索工具。

    功能：
    1. 接收用户提出的医疗健康科普问题；
    2. 调用 RAG 检索器，在 medical_knowledge 集合中进行语义检索；
    3. 返回最相关的知识片段、来源文件、距离分数和可信标记；
    4. 为 Agent 回答提供可追溯的知识依据。

    参数：
        query: 用户问题，例如“高血压日常怎么管理？”
        top_k: 返回前几个最相关片段
        distance_threshold: 距离阈值，distance 越小越相关

    返回：
        dict: 标准化检索结果
    """
    if not query or not query.strip():
        return {
            "query": query,
            "tool": "medical_rag_search",
            "success": False,
            "message": "查询内容不能为空",
            "results": [],
        }

    from rag.retriever import retriever

    result = retriever.search_medical(
        query=query.strip(),
        top_k=top_k,
        distance_threshold=distance_threshold
    )

    hits: List[Dict] = []
    for item in result.get("hits", []):
        hits.append({
            "rank": item.get("rank"),
            "content": item.get("content"),
            "source": item.get("source"),
            "category": item.get("category"),
            "chunk_index": item.get("chunk_index"),
            "distance": item.get("distance"),
            "reliable": item.get("reliable"),
        })

    reliable_hits = [item for item in hits if item.get("reliable")]
    evidence = reliable_hits or hits
    answer_basis = "\n\n".join(
        f"[{item.get('source') or 'unknown'}] {item.get('content') or ''}"
        for item in evidence
        if item.get("content")
    )

    return {
        "query": result.get("query", query),
        "tool": "medical_rag_search",
        "collection": result.get("collection"),
        "top_k": result.get("top_k"),
        "distance_threshold": result.get("distance_threshold"),
        "has_reliable_evidence": result.get("has_reliable_evidence"),
        "success": True,
        "results": hits,
        "evidence": hits,
        "answer_basis": answer_basis,
    }


def run(query: str, top_k: int = 3, distance_threshold: float = 0.90) -> Dict:
    """
    Agent-facing entry point.
    """
    return medical_rag_search(
        query=query,
        top_k=top_k,
        distance_threshold=distance_threshold,
    )


if __name__ == "__main__":
    test_query = "高血压日常怎么管理？"
    output = medical_rag_search(test_query, top_k=3)

    print("查询：", output["query"])
    print("是否有可靠依据：", output["has_reliable_evidence"])

    for item in output["results"]:
        print("\n" + "-" * 60)
        print("排名：", item["rank"])
        print("来源：", item["source"])
        print("距离：", item["distance"])
        print("可靠：", item["reliable"])
        print("内容：", item["content"][:300].replace("\n", " "))