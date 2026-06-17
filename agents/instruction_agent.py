# agents/instruction_agent.py
from typing import Any, Dict, List

try:
    from config.llm_client import call_llm
except Exception:
    call_llm = None

from agents.safety_agent import safety_agent


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _section_to_dict(section_result: Any) -> Dict[str, Any]:
    if hasattr(section_result, "model_dump"):
        return section_result.model_dump()
    if isinstance(section_result, dict):
        return section_result
    return {}


def _build_instruction_context(sections: Dict[str, Any]) -> str:
    labels = {
        "drug_name": "药品名称",
        "indication": "适应症/功能主治",
        "dosage": "用法用量",
        "contraindications": "禁忌",
        "adverse_reactions": "不良反应",
        "precautions": "注意事项",
        "special_population": "特殊人群用药",
        "interactions": "药物相互作用",
        "storage": "贮藏",
    }

    parts: List[str] = []

    for key, label in labels.items():
        value = sections.get(key)
        if value:
            parts.append(f"【{label}】\n{value}")

    if not parts and sections.get("raw_text"):
        parts.append(f"【说明书原文节选】\n{sections.get('raw_text')}")

    return "\n\n".join(parts)


def _generate_instruction_explanation(
    user_query: str,
    instruction_context: str,
) -> str:
    if call_llm is None:
        return (
            "已从上传说明书中提取到以下内容：\n\n"
            f"{instruction_context}\n\n"
            "请结合医生或药师建议理解说明书内容。"
        )

    messages = [
        {
            "role": "system",
            "content": (
                "你是 MedSafe Agent 的药品说明书解读 Agent。\n"
                "你的任务是基于用户上传的药品说明书内容，用通俗中文解释说明书。\n"
                "必须遵守：\n"
                "1. 只能基于上传说明书中提取到的内容回答，不要补充说明书中没有的信息。\n"
                "2. 不提供个性化用药剂量，不说用户具体应该吃几片。\n"
                "3. 对“用法用量”只能解释说明书写了什么，不能替用户决定用药方案。\n"
                "4. 对禁忌、不良反应、注意事项、孕妇儿童老人等特殊人群要重点提醒。\n"
                "5. 如果说明书中缺少某一项，请明确说“上传说明书中未识别到该部分”。\n"
                "6. 回答要结构清晰、通俗易懂。\n"
                "7. 不要引用上传说明书之外的指南、数据库、临床原则或其他资料来源。\n"
                "8. 如果某项内容不是从上传说明书中识别到的，请不要写入回答。\n"
                "9. 如果上传说明书中已经出现规格、成分、有效期等信息，不要说未提供。\n"
            ),
        },
        {
            "role": "user",
            "content": (
                f"用户问题：{user_query or '请帮我解读这份药品说明书'}\n\n"
                f"上传说明书提取内容：\n{instruction_context}\n\n"
                "请基于以上内容进行说明书解读。"
            ),
        },
    ]

    return call_llm(messages)


def instruction_agent(
    file_path: str,
    query: str = "请帮我解读这份药品说明书",
) -> Dict[str, Any]:
    """
    药品说明书上传解读 Agent。

    流程：
    1. instruction_file_parser：解析 PDF / 图片，得到说明书文本。
    2. instruction_section_extractor：提取说明书栏目。
    3. Qwen-Plus：基于提取内容生成通俗解读。
    4. safety_agent：做最终安全审查。
    """
    tool_called = []

    # 1. 解析上传文件
    try:
        from tools.instruction_file_parser import run as file_parser_run

        parse_result = file_parser_run(file_path)
        tool_called.append("instruction_file_parser")

    except Exception as exc:
        return safety_agent(
            query=query,
            risk_result={"risk_level": "low", "risk_reason": "说明书文件解析工具异常。"},
            draft_answer=f"说明书文件解析工具运行失败：{str(exc)}",
            sources=[],
            route="instruction_agent",
            tool_called=tool_called,
        )

    if not _get_value(parse_result, "success", False):
        return safety_agent(
            query=query,
            risk_result={"risk_level": "low", "risk_reason": "说明书文件未能成功解析。"},
            draft_answer=_get_value(parse_result, "error_message", "未能解析上传说明书。"),
            sources=[],
            route="instruction_agent",
            tool_called=tool_called,
        )

    instruction_text = _get_value(parse_result, "text", "")

    # 2. 提取说明书栏目
    try:
        from tools.instruction_section_extractor import run as section_extractor_run

        section_result = section_extractor_run(instruction_text)
        tool_called.append("instruction_section_extractor")

    except Exception as exc:
        return safety_agent(
            query=query,
            risk_result={"risk_level": "low", "risk_reason": "说明书栏目提取工具异常。"},
            draft_answer=f"说明书栏目提取工具运行失败：{str(exc)}",
            sources=[],
            route="instruction_agent",
            tool_called=tool_called,
        )

    if not _get_value(section_result, "success", False):
        return safety_agent(
            query=query,
            risk_result={"risk_level": "low", "risk_reason": "说明书栏目提取失败。"},
            draft_answer=_get_value(section_result, "error_message", "未能从说明书中提取有效栏目。"),
            sources=[],
            route="instruction_agent",
            tool_called=tool_called,
        )

    sections = _section_to_dict(section_result)
    instruction_context = _build_instruction_context(sections)

    if not instruction_context.strip():
        draft_answer = "系统未能从上传说明书中提取到可用于解读的有效内容。"
    else:
        try:
            draft_answer = _generate_instruction_explanation(
                user_query=query,
                instruction_context=instruction_context,
            )
        except Exception as exc:
            draft_answer = (
                "已从说明书中提取到部分内容，但大模型解读时出现异常。"
                "以下为提取到的说明书内容：\n\n"
                f"{instruction_context}\n\n"
                f"错误信息：{str(exc)}"
            )

    sources = [
        {
            "source": file_path,
            "content": instruction_context[:1000],
            "reliable": True,
        }
    ]

    # 3. 最终安全审查
    result = safety_agent(
        query=query,
        risk_result={"risk_level": "low", "risk_reason": "说明书解读场景。"},
        draft_answer=draft_answer,
        sources=sources,
        route="instruction_agent",
        tool_called=tool_called,
    )

    result["intent"] = "instruction_upload"
    result["parsed_sections"] = sections
    return result


if __name__ == "__main__":
    test_file = "tests/sample_instructions/sample.pdf"
    response = instruction_agent(test_file, "帮我解释这份说明书")
    print("路由：", response.get("route"))
    print("工具：", response.get("tool_called"))
    print("回答：", response.get("answer"))