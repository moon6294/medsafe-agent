import json
import re
from typing import Dict, List, Optional

from schemas.tool_schemas import RiskCheckInput, RiskCheckOutput


HIGH_RISK_KEYWORDS: Dict[str, List[str]] = {
    "急性胸痛/心脑血管风险": [
        "胸痛", "胸闷", "心绞痛", "心梗", "心肌梗死",
        "一侧肢体无力", "口角歪斜", "说话不清", "昏迷", "意识不清",
    ],
    "呼吸困难/窒息风险": [
        "呼吸困难", "喘不上气", "窒息", "喉头水肿", "嘴唇发紫", "紫绀",
    ],
    "严重过敏风险": [
        "严重过敏", "过敏性休克", "全身皮疹", "喉咙肿", "脸肿", "眼睛肿",
    ],
    "严重出血/外伤风险": [
        "大量出血", "止不住血", "严重外伤", "头部受伤", "摔倒后昏迷",
    ],
    "中毒/过量用药风险": [
        "药吃多了", "误服", "中毒", "过量服用", "一次吃了很多", "喝了农药",
    ],
    "自伤风险": [
        "自杀", "不想活", "自残", "结束生命",
    ],
}


MEDIUM_RISK_KEYWORDS: Dict[str, List[str]] = {
    "特殊人群用药": [
        "孕妇", "怀孕", "哺乳期", "儿童", "婴儿", "老人", "老年人",
    ],
    "慢性病或基础病": [
        "肝功能异常", "肾功能异常", "肝病", "肾病", "胃溃疡",
        "高血压", "糖尿病", "哮喘", "心脏病",
    ],
    "药物过敏/禁忌": [
        "药物过敏", "青霉素过敏", "阿司匹林过敏", "过敏史", "禁忌",
    ],
    "处方药和剂量问题": [
        "处方药", "剂量", "吃几片", "一天几次", "能不能加量", "减量", "停药",
    ],
}


LOW_RISK_KEYWORDS: Dict[str, List[str]] = {
    "普通健康科普": [
        "预防", "注意事项", "怎么护理", "怎么缓解", "健康管理", "饮食建议",
    ],
    "普通用药安全": [
        "不良反应", "副作用", "药品说明", "用药注意", "能不能一起吃",
    ],
}


RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def _find_matched_keywords(query: str, keyword_groups: Dict[str, List[str]]) -> List[str]:
    matched = []
    for keywords in keyword_groups.values():
        for keyword in keywords:
            if keyword in query:
                matched.append(keyword)
    return matched


def _find_medium_non_chronic_keywords(query: str) -> List[str]:
    matched = []
    for group_name, keywords in MEDIUM_RISK_KEYWORDS.items():
        if group_name == "慢性病或基础病":
            continue
        for keyword in keywords:
            if keyword in query:
                matched.append(keyword)
    return matched


def _rule_based_risk_check(query: str) -> RiskCheckOutput:
    high_matches = _find_matched_keywords(query, HIGH_RISK_KEYWORDS)
    if high_matches:
        return RiskCheckOutput(
            success=True,
            risk_level="high",
            risk_reason=f"用户问题中包含高风险信号：{', '.join(high_matches)}。",
            suggestion=(
                "该情况可能存在急症或严重风险。本系统不能替代医生诊断，"
                "建议尽快前往医院急诊、联系医生，或在紧急情况下拨打当地急救电话。"
            ),
            matched_keywords=high_matches,
            classification_source="rules",
        )

    low_matches = _find_matched_keywords(query, LOW_RISK_KEYWORDS)
    medium_non_chronic_matches = _find_medium_non_chronic_keywords(query)
    if low_matches and not medium_non_chronic_matches:
        return RiskCheckOutput(
            success=True,
            risk_level="low",
            risk_reason=f"用户问题属于一般健康科普或普通用药安全咨询：{', '.join(low_matches)}。",
            suggestion=(
                "可以继续调用健康科普检索工具或用药安全检索工具，"
                "基于知识库资料进行回答，并保留不能替代医生诊断的提示。"
            ),
            matched_keywords=low_matches,
            classification_source="rules",
        )

    medium_matches = _find_matched_keywords(query, MEDIUM_RISK_KEYWORDS)
    if medium_matches:
        return RiskCheckOutput(
            success=True,
            risk_level="medium",
            risk_reason=f"用户问题中包含需要谨慎处理的风险因素：{', '.join(medium_matches)}。",
            suggestion=(
                "该问题涉及特殊人群、基础疾病、药物过敏或具体剂量调整。"
                "建议不要自行决定用药方案，应咨询医生或药师，并结合药品说明书和个人病史判断。"
            ),
            matched_keywords=medium_matches,
            classification_source="rules",
        )

    return RiskCheckOutput(
        success=True,
        risk_level="low",
        risk_reason="未检测到明显高风险医疗信号。",
        suggestion="可以根据问题类型继续调用健康科普检索工具或用药安全检索工具。",
        matched_keywords=[],
        classification_source="rules",
    )


def _extract_json_object(text: str) -> Dict:
    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        raise ValueError("LLM did not return a JSON object")

    return json.loads(match.group(0))


def _normalize_risk_level(value: str) -> Optional[str]:
    level = (value or "").strip().lower()
    if level in RISK_ORDER:
        return level
    if "high" in level or "高" in level:
        return "high"
    if "medium" in level or "中" in level:
        return "medium"
    if "low" in level or "低" in level:
        return "low"
    return None


def _llm_safety_classify(query: str) -> Optional[RiskCheckOutput]:
    try:
        from config.llm_client import call_llm
    except Exception:
        return None

    messages = [
        {
            "role": "system",
            "content": (
                "你是 MedSafe Agent 的医疗安全风险分类器，只负责判断用户问题的安全风险等级，不做诊断。\n"
                "请把用户输入分为 low、medium、high 三档：\n"
                "- high：疑似急症、严重症状、中毒/过量、自伤风险、严重过敏、呼吸困难、胸痛、中风征象、严重出血等，需要优先安全提醒。\n"
                "- medium：特殊人群用药、孕妇/儿童/老人、慢病或肝肾功能异常、药物过敏史、禁忌、处方药、具体剂量调整、停药/加量、联合用药风险等，需要谨慎处理。\n"
                "- low：一般健康科普、疾病预防、日常护理、普通药品注意事项或不良反应查询，未出现明确急症或个体化用药决策。\n"
                "必须只返回 JSON，不要 Markdown，不要额外解释。JSON 字段："
                "risk_level, risk_reason, suggestion, matched_keywords。"
            ),
        },
        {
            "role": "user",
            "content": f"用户问题：{query}",
        },
    ]

    try:
        raw = call_llm(messages, temperature=0, max_tokens=500)
        data = _extract_json_object(raw)
        risk_level = _normalize_risk_level(str(data.get("risk_level", "")))
        if risk_level is None:
            return None

        matched_keywords = data.get("matched_keywords", [])
        if not isinstance(matched_keywords, list):
            matched_keywords = [str(matched_keywords)]

        return RiskCheckOutput(
            success=True,
            risk_level=risk_level,
            risk_reason=str(data.get("risk_reason") or "LLM safety classifier completed."),
            suggestion=str(data.get("suggestion") or "请结合问题类型继续处理，并保留必要的医疗安全提示。"),
            matched_keywords=[str(item) for item in matched_keywords if str(item).strip()],
            classification_source="llm",
        )
    except Exception:
        return None


def _merge_risk_results(rule_result: RiskCheckOutput, llm_result: Optional[RiskCheckOutput]) -> RiskCheckOutput:
    if llm_result is None:
        return rule_result

    if RISK_ORDER[llm_result.risk_level] > RISK_ORDER[rule_result.risk_level]:
        selected = llm_result
    else:
        selected = rule_result

    matched_keywords = []
    for item in list(rule_result.matched_keywords or []) + list(llm_result.matched_keywords or []):
        if item not in matched_keywords:
            matched_keywords.append(item)

    selected.matched_keywords = matched_keywords
    selected.classification_source = "llm+rules"

    if selected is rule_result and llm_result.risk_level != rule_result.risk_level:
        selected.risk_reason = (
            f"{rule_result.risk_reason} LLM 分类结果为 {llm_result.risk_level}，"
            "系统按更保守的风险等级处理。"
        )

    return selected


def risk_signal_checker(tool_input: RiskCheckInput) -> RiskCheckOutput:
    """
    Hybrid safety classifier:
    1. Rule-based high-risk guardrail for obvious emergencies.
    2. LLM safety classifier for broader natural-language coverage.
    3. Conservative merge: use the higher risk level.
    """
    try:
        query = tool_input.query.strip()

        if not query:
            return RiskCheckOutput(
                success=False,
                risk_level="low",
                risk_reason="输入为空，无法判断风险。",
                suggestion="请重新输入具体问题。",
                matched_keywords=[],
                classification_source="rules",
                error_message="empty query",
            )

        rule_result = _rule_based_risk_check(query)

        if rule_result.risk_level == "high":
            return rule_result

        llm_result = _llm_safety_classify(query)
        return _merge_risk_results(rule_result, llm_result)

    except Exception as e:
        return RiskCheckOutput(
            success=False,
            risk_level="low",
            risk_reason="风险检测工具运行异常。",
            suggestion="建议进入兜底流程，提示用户稍后重试或咨询专业人士。",
            matched_keywords=[],
            classification_source="fallback",
            error_message=str(e),
        )


if __name__ == "__main__":
    test_queries = [
        "我胸痛还呼吸困难怎么办？",
        "孕妇可以吃布洛芬吗？",
        "布洛芬有哪些注意事项？",
        "高血压日常怎么预防？",
        "",
    ]

    for q in test_queries:
        result = risk_signal_checker(RiskCheckInput(query=q))
        print("=" * 60)
        print("用户问题：", q)
        print(result.model_dump())
