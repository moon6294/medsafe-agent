# agents/main_agent.py
from typing import Any, Dict, List


try:
    from config.llm_client import call_llm
except Exception:
    call_llm = None


from agents.drug_safety_agent import drug_safety_agent
from agents.health_agent import health_agent
from agents.safety_agent import safety_agent


DRUG_KEYWORDS = [
    "药", "用药", "吃药", "服用", "禁忌", "不良反应", "副作用",
    "注意事项", "能不能一起吃", "相互作用", "剂量", "吃几片",
    "一天几次", "布洛芬", "对乙酰氨基酚", "阿莫西林", "头孢",
    "感冒药", "退烧药", "止痛药", "抗生素"
]

SAFETY_KEYWORDS = [
    "胸痛", "呼吸困难", "喘不上气", "昏迷", "意识不清",
    "严重过敏", "过敏性休克", "大量出血", "中毒", "误服",
    "药吃多了", "自杀", "自残", "不想活"
]


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _call_risk_signal_checker(query: str) -> Any:
    """
    调用风险检测工具。
    兼容两种写法：
    1. risk_signal_checker(RiskCheckInput(query=query))
    2. risk_signal_checker(query)
    """
    try:
        from tools.risk_signal_checker import risk_signal_checker

        try:
            from schemas.tool_schemas import RiskCheckInput
            return risk_signal_checker(RiskCheckInput(query=query))
        except Exception:
            return risk_signal_checker(query)

    except Exception as e:
        return {
            "success": False,
            "risk_level": "low",
            "risk_reason": "风险检测工具调用失败，默认按低风险处理。",
            "suggestion": "建议谨慎回答，并提示用户必要时咨询医生或药师。",
            "matched_keywords": [],
            "error_message": str(e),
        }


def _keyword_classify(query: str) -> str:
    """
    规则分类兜底。
    返回：drug_safety / health / safety
    """
    if any(keyword in query for keyword in SAFETY_KEYWORDS):
        return "safety"

    if any(keyword in query for keyword in DRUG_KEYWORDS):
        return "drug_safety"

    return "health"


def _llm_classify(query: str) -> str:
    """
    使用 Qwen-Plus 做意图识别。
    如果 LLM 不可用或输出异常，则使用关键词规则兜底。
    """
    fallback_intent = _keyword_classify(query)

    if call_llm is None:
        return fallback_intent

    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 MedSafe Agent 的主控 Agent，负责判断用户问题应该交给哪个子 Agent。\n"
                    "请只返回以下三个标签之一，不要输出其他内容：\n"
                    "1. drug_safety：药品注意事项、禁忌、不良反应、服用方式、剂量、联合用药、用药安全相关问题。\n"
                    "2. health：疾病预防、健康管理、日常护理、饮食运动、普通健康科普问题。\n"
                    "3. safety：急症、严重症状、中毒、严重过敏、自伤风险等需要优先安全提醒的问题。\n"
                ),
            },
            {
                "role": "user",
                "content": f"用户问题：{query}\n\n请判断意图标签：",
            },
        ]

        result = call_llm(messages).strip().lower()

        if "drug_safety" in result:
            return "drug_safety"
        if "safety" in result:
            return "safety"
        if "health" in result:
            return "health"

        return fallback_intent

    except Exception:
        return fallback_intent


def main_agent(query: str, top_k: int = 3) -> Dict[str, Any]:
    """
    主控 Agent。

    正式 Multi-Agent 流程：
    1. 先调用 risk_signal_checker 做医疗风险检测。
    2. high 风险直接交给 safety_agent。
    3. 非 high 风险再判断意图。
    4. 用药安全问题交给 drug_safety_agent。
    5. 健康科普问题交给 health_agent。
    6. safety_agent 负责最终安全审查。
    """
    query = (query or "").strip()

    # ===== 新增：推理步骤记录 =====
    reasoning_steps: List[Dict[str, Any]] = []

    if not query:
        reasoning_steps.append({
            "step": "input_validation",
            "description": "输入为空",
            "output": {"valid": False}
        })
        return {
            "success": False,
            "route": "main_agent",
            "answer": "请输入具体的医疗健康或用药安全问题。",
            "tool_called": [],
            "sources": [],
            "risk_level": "low",
            "risk_reason": "用户输入为空。",
            "has_reliable_evidence": False,
            "error_message": "empty query",
            "reasoning_steps": reasoning_steps,  # 新增
        }

    # 1. 前置风险检测
    reasoning_steps.append({
        "step": "risk_check",
        "description": "调用风险信号检测器",
        "input": query,
        "output": {"status": "调用中"}
    })
    risk_result = _call_risk_signal_checker(query)
    risk_level = _get_value(risk_result, "risk_level", "low")
    reasoning_steps[-1]["output"] = {
        "risk_level": risk_level,
        "risk_reason": _get_value(risk_result, "risk_reason", "")
    }

    # 2. high 风险直接走安全 Agent
    if risk_level == "high":
        reasoning_steps.append({
            "step": "route_decision",
            "description": f"风险等级为 {risk_level}，路由到 safety_agent",
            "output": {"route": "safety_agent"}
        })
        result = safety_agent(
            query=query,
            risk_result=risk_result,
            draft_answer="",
            sources=[],
            route="safety_agent",
            tool_called=["risk_signal_checker"],
        )
        result["intent"] = "safety"
        # 合并子 Agent 的推理步骤（如果存在）
        if "reasoning_steps" in result and isinstance(result["reasoning_steps"], list):
            reasoning_steps.extend(result["reasoning_steps"])
        result["reasoning_steps"] = reasoning_steps
        return result

    # 3. 意图分类
    reasoning_steps.append({
        "step": "intent_classification",
        "description": "LLM 意图分类",
        "input": query,
        "output": {"intent": "待分类"}
    })
    intent = _llm_classify(query)
    reasoning_steps[-1]["output"] = {"intent": intent}

    # 如果风险工具已经检测到安全关键词，但未达到 high，也可以走 safety
    if intent == "safety":
        reasoning_steps.append({
            "step": "route_decision",
            "description": f"意图为 {intent}，路由到 safety_agent",
            "output": {"route": "safety_agent"}
        })
        result = safety_agent(
            query=query,
            risk_result=risk_result,
            draft_answer=_get_value(
                risk_result,
                "suggestion",
                "该问题可能涉及医疗安全风险，建议咨询医生或药师。"
            ),
            sources=[],
            route="safety_agent",
            tool_called=["risk_signal_checker"],
        )
        result["intent"] = "safety"
        if "reasoning_steps" in result and isinstance(result["reasoning_steps"], list):
            reasoning_steps.extend(result["reasoning_steps"])
        result["reasoning_steps"] = reasoning_steps
        return result

    # 4. 用药安全 Agent
    if intent == "drug_safety":
        reasoning_steps.append({
            "step": "route_decision",
            "description": f"意图为 {intent}，路由到 drug_safety_agent",
            "output": {"route": "drug_safety_agent"}
        })
        result = drug_safety_agent(
            query=query,
            risk_result=risk_result,
            top_k=top_k,
        )
        result["intent"] = "drug_safety"

        tools = result.get("tool_called", [])
        if "risk_signal_checker" not in tools:
            result["tool_called"] = ["risk_signal_checker"] + tools

        # 尝试合并子 Agent 的推理步骤
        if "reasoning_steps" in result and isinstance(result["reasoning_steps"], list):
            reasoning_steps.extend(result["reasoning_steps"])
        result["reasoning_steps"] = reasoning_steps
        return result

    # 5. 默认健康科普 Agent
    reasoning_steps.append({
        "step": "route_decision",
        "description": f"默认路由到 health_agent（意图为 {intent}）",
        "output": {"route": "health_agent"}
    })
    result = health_agent(
        query=query,
        risk_result=risk_result,
        top_k=top_k,
    )
    result["intent"] = "health"

    tools = result.get("tool_called", [])
    if "risk_signal_checker" not in tools:
        result["tool_called"] = ["risk_signal_checker"] + tools

    if "reasoning_steps" in result and isinstance(result["reasoning_steps"], list):
        reasoning_steps.extend(result["reasoning_steps"])
    result["reasoning_steps"] = reasoning_steps
    return result


if __name__ == "__main__":
    test_queries = [
        "布洛芬有哪些注意事项？",
        "高血压日常怎么管理？",
        "我胸痛还呼吸困难怎么办？",
        "孕妇可以吃布洛芬吗？",
    ]

    for q in test_queries:
        print("=" * 80)
        print("用户问题：", q)
        response = main_agent(q)
        print("路由：", response.get("route"))
        print("意图：", response.get("intent"))
        print("风险等级：", response.get("risk_level"))
        print("调用工具：", response.get("tool_called"))
        print("回答：", response.get("answer"))
        # 打印推理步骤
        print("推理步骤：")
        for step in response.get("reasoning_steps", []):
            print(f"  - {step.get('description')}: {step.get('output')}")
        print()