# agents/safety_agent.py
from typing import Any, Dict, List, Optional


try:
    from config.llm_client import call_llm
except Exception:
    call_llm = None


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    """兼容 dict 和 Pydantic 对象。"""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _ensure_tool_called(tool_called: Optional[List[str]], tool_name: str) -> List[str]:
    tools = list(tool_called or [])
    if tool_name not in tools:
        tools.append(tool_name)
    return tools


def _append_medical_disclaimer(answer: str) -> str:
    disclaimer = (
        "\n\n安全提示：本系统仅用于医疗健康科普与用药安全信息查询，"
        "不能替代医生诊断、处方或药师指导。如症状严重、持续加重或涉及特殊人群用药，"
        "请及时咨询医生或药师。"
    )

    if "不能替代医生诊断" in answer or "不能替代医生" in answer:
        return answer

    return answer.strip() + disclaimer


def safety_agent(
    query: str,
    risk_result: Any = None,
    draft_answer: str = "",
    sources: Optional[List[Dict[str, Any]]] = None,
    route: str = "safety_agent",
    tool_called: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    安全审查 Agent。

    作用：
    1. 对 high 风险问题直接给出安全提醒，不继续做普通问答。
    2. 对普通回答进行安全审查，避免诊断、处方、个性化剂量建议等风险。
    3. 最终统一追加医疗免责声明。
    """
    sources = sources or []
    tool_called = _ensure_tool_called(tool_called, "safety_agent")

    risk_level = _get_value(risk_result, "risk_level", "low")
    risk_reason = _get_value(risk_result, "risk_reason", "")
    suggestion = _get_value(risk_result, "suggestion", "")

    # 高风险情况：直接返回安全提醒
    if risk_level == "high":
        answer = suggestion or (
            "你的描述可能涉及急症或较高医疗风险。"
            "本系统不能替代医生诊断，建议尽快前往医院急诊、联系医生，"
            "或在紧急情况下拨打当地急救电话。"
        )

        return {
            "success": True,
            "route": "safety_agent",
            "answer": _append_medical_disclaimer(answer),
            "tool_called": tool_called,
            "sources": sources,
            "risk_level": risk_level,
            "risk_reason": risk_reason,
            "has_reliable_evidence": False,
            "error_message": None,
        }

    # 没有草稿回答时，返回一个安全兜底
    if not draft_answer or not draft_answer.strip():
        answer = (
            "当前系统没有生成可审查的回答。"
            "建议补充更具体的问题，或咨询医生、药师等专业人士。"
        )

        return {
            "success": True,
            "route": route,
            "answer": _append_medical_disclaimer(answer),
            "tool_called": tool_called,
            "sources": sources,
            "risk_level": risk_level,
            "risk_reason": risk_reason,
            "has_reliable_evidence": bool(sources),
            "error_message": None,
        }

    # 如果没有 LLM，就直接追加免责声明
    if call_llm is None:
        return {
            "success": True,
            "route": route,
            "answer": _append_medical_disclaimer(draft_answer),
            "tool_called": tool_called,
            "sources": sources,
            "risk_level": risk_level,
            "risk_reason": risk_reason,
            "has_reliable_evidence": bool(sources),
            "error_message": None,
        }

    # 使用大模型做安全改写
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 MedSafe Agent 的医疗安全审查 Agent。\n"
                    "你的任务是对已经生成的回答进行安全改写，但最终只输出给用户看的回答。\n"
                    "必须遵守：\n"
                    "1. 不要输出“以下是安全审查结果”“我已进行改写”“原回答存在问题”等内部过程说明。\n"
                    "2. 不新增原回答中没有的医学事实、检查项目、剂量、时间间隔、临床指南或外部来源。\n"
                    "3. 不声称内容来自某个指南、数据库或权威文件，除非原回答中已经明确提供。\n"
                    "4. 不做疾病诊断，不给出处方或个性化用药剂量。\n"
                    "5. 不建议用户自行加量、减量、停药或联合用药。\n"
                    "6. 可以保留必要的安全提醒，例如咨询医生或药师、严重症状及时就医。\n"
                    "7. 最终回答要直接面向用户，语言通俗清晰。\n"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"用户问题：{query}\n\n"
                    f"风险等级：{risk_level}\n"
                    f"风险原因：{risk_reason}\n\n"
                    f"待审查回答：\n{draft_answer}\n\n"
                    "请只输出最终给用户看的安全版回答，不要输出审查过程。"
                ),
            },
        ]

        safe_answer = call_llm(messages)
        safe_answer = _clean_safety_meta_text(safe_answer)

        return {
            "success": True,
            "route": route,
            "answer": _append_medical_disclaimer(safe_answer),
            "tool_called": tool_called,
            "sources": sources,
            "risk_level": risk_level,
            "risk_reason": risk_reason,
            "has_reliable_evidence": bool(sources),
            "error_message": None,
        }

    except Exception as e:
        return {
            "success": True,
            "route": route,
            "answer": _append_medical_disclaimer(draft_answer),
            "tool_called": tool_called,
            "sources": sources,
            "risk_level": risk_level,
            "risk_reason": risk_reason,
            "has_reliable_evidence": bool(sources),
            "error_message": f"safety_agent LLM 审查失败，已返回兜底安全回答：{str(e)}",
        }


def _clean_safety_meta_text(answer: str) -> str:
    """
    清理 Safety Agent 可能输出的内部审查说明。
    """
    remove_phrases = [
        "以下是对原回答的安全审查与合规改写。",
        "以下是对原回答的安全审查与合规改写：",
        "已严格遵循医疗安全审查要求：",
        "以下是安全审查后的最终回答：",
        "以下是改写后的回答：",
    ]

    cleaned = answer.strip()

    for phrase in remove_phrases:
        cleaned = cleaned.replace(phrase, "")

    # 如果开头还有多余分隔线，也清理一下
    cleaned = cleaned.lstrip("-— \n")

    return cleaned.strip()