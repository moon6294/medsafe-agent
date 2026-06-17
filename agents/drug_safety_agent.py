from typing import Any, Dict, List

try:
    from config.llm_client import call_llm
except Exception:
    call_llm = None

from agents.safety_agent import safety_agent
from schemas.tool_schemas import GroundingCheckInput


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    """兼容 dict 和 Pydantic 对象。"""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _make_friendly_title(source: str) -> str:
    if source.startswith("data/raw/medical/"):
        return "医疗科普"
    elif source.startswith("data/raw/drug/"):
        return "用药安全"
    elif source.startswith("data/raw/instruction/"):
        return "药品说明书"
    else:
        return "参考资料"


def _extract_reliable_sources(tool_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从 RAG 工具返回结果中提取 reliable=True 的证据，并转为友好标题。"""
    evidence = tool_result.get("evidence", []) or []
    reliable_sources = []

    for item in evidence:
        if item.get("reliable", True):
            source = item.get("source", "")
            reliable_sources.append({
                "title": _make_friendly_title(source),   # 友好名称
                "source": source,                         # 保留原始路径
                "content": item.get("content", ""),
                "distance": item.get("distance", None),
                "score": item.get("distance", None),
                "reliable": item.get("reliable", True),
            })

    return reliable_sources


def _call_grounding_checker(tool_result: Dict[str, Any]):
    """
    调用 grounding_checker 工具。

    grounding_checker 不生成答案，只判断当前检索依据是否足够可靠。
    """
    try:
        from tools.grounding_checker import run as grounding_checker_run

        grounding_input = GroundingCheckInput(
            has_reliable_evidence=bool(tool_result.get("has_reliable_evidence", False)),
            answer_basis=tool_result.get("answer_basis", ""),
            evidence=tool_result.get("evidence", []) or [],
        )

        return grounding_checker_run(grounding_input)

    except Exception as e:
        return {
            "success": False,
            "grounded": False,
            "reason": "grounding_checker 调用失败。",
            "suggestion": f"系统依据检查工具暂时不可用，请稍后重试。错误信息：{str(e)}",
            "evidence_count": 0,
            "error_message": str(e),
        }


def _generate_answer_by_llm(
    query: str,
    answer_basis: str,
    risk_level: str,
    risk_reason: str,
) -> str:
    """
    基于检索资料生成用药安全回答。
    如果 LLM 不可用，则直接返回检索依据。
    """
    if call_llm is None:
        return (
            "根据当前检索到的用药安全资料，整理如下：\n\n"
            f"{answer_basis}"
        )

    messages = [
        {
            "role": "system",
            "content": (
                "你是 MedSafe Agent 的用药安全 Agent。\n"
                "你的任务是基于检索到的资料，回答常见药品的注意事项、禁忌、"
                "不良反应、特殊人群提醒等问题。\n"
                "必须遵守：\n"
                "1. 只能基于给定资料回答，不要编造资料中没有的信息。\n"
                "2. 不提供个性化用药剂量，不说“你应该吃几片”。\n"
                "3. 不建议用户自行加量、减量、停药或联合用药。\n"
                "4. 涉及孕妇、儿童、老人、肝肾功能异常、药物过敏等情况，"
                "要建议咨询医生或药师。\n"
                "5. 用通俗中文回答，可以分点说明。\n"
            ),
        },
        {
            "role": "user",
            "content": (
                f"用户问题：{query}\n\n"
                f"风险等级：{risk_level}\n"
                f"风险原因：{risk_reason}\n\n"
                f"检索资料：\n{answer_basis}\n\n"
                "请基于以上资料生成用药安全回答。"
            ),
        },
    ]

    return call_llm(messages)


def drug_safety_agent(
    query: str,
    risk_result: Any = None,
    top_k: int = 3,
) -> Dict[str, Any]:
    """
    用药安全 Agent。

    流程：
    1. 调用 drug_safety_search 工具。
    2. 调用 grounding_checker 检查依据是否可靠。
    3. 如果没有可靠依据，不调用大模型生成确定回答，直接进入兜底。
    4. 如果依据可靠，调用 Qwen-Plus 生成回答。
    5. 最后交给 safety_agent 做医疗安全审查。
    """
    tool_called = ["drug_safety_search"]

    # 1. 调用用药安全检索工具
    try:
        from tools.drug_safety_search import run as drug_safety_search_run
        tool_result = drug_safety_search_run(query=query, top_k=top_k)

    except Exception as e:
        draft_answer = (
            "用药安全检索工具暂时不可用，无法基于资料库给出可靠回答。"
            "请咨询医生或药师，不要自行调整用药。"
        )

        return safety_agent(
            query=query,
            risk_result=risk_result,
            draft_answer=draft_answer,
            sources=[],
            route="drug_safety_agent",
            tool_called=tool_called,
        )

    answer_basis = tool_result.get("answer_basis", "")
    sources = _extract_reliable_sources(tool_result)

    # 2. 调用 grounding_checker
    grounding_result = _call_grounding_checker(tool_result)
    tool_called.append("grounding_checker")

    grounded = _get_value(grounding_result, "grounded", False)
    grounding_suggestion = _get_value(
        grounding_result,
        "suggestion",
        "当前资料库未检索到可靠依据，请咨询医生或药师。",
    )

    # 3. 没有可靠依据：不生成正式回答，直接进入安全兜底
    if not grounded:
        return safety_agent(
            query=query,
            risk_result=risk_result,
            draft_answer=grounding_suggestion,
            sources=sources,
            route="drug_safety_agent",
            tool_called=tool_called,
        )

    # 4. 有可靠依据：调用 LLM 生成回答
    risk_level = _get_value(risk_result, "risk_level", "low")
    risk_reason = _get_value(risk_result, "risk_reason", "")

    try:
        draft_answer = _generate_answer_by_llm(
            query=query,
            answer_basis=answer_basis,
            risk_level=risk_level,
            risk_reason=risk_reason,
        )

    except Exception as e:
        draft_answer = (
            "根据当前检索到的用药安全资料，整理如下：\n\n"
            f"{answer_basis}\n\n"
            f"说明：大模型生成回答时出现异常，已返回原始检索依据。错误信息：{str(e)}"
        )

    # 5. 最终交给 safety_agent 审查
    return safety_agent(
        query=query,
        risk_result=risk_result,
        draft_answer=draft_answer,
        sources=sources,
        route="drug_safety_agent",
        tool_called=tool_called,
    )