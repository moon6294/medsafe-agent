# tools/grounding_checker.py

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from schemas.tool_schemas import (
    GroundingCheckInput,
    GroundingCheckOutput,
)


def grounding_checker(
    tool_input: GroundingCheckInput
) -> GroundingCheckOutput:
    """
    检查回答是否具有可靠依据。

    不负责生成答案，
    只负责判断当前回答是否允许输出。
    """

    try:
        if not tool_input.has_reliable_evidence:
            return GroundingCheckOutput(
                success=True,
                grounded=False,
                reason="未检索到可靠依据。",
                suggestion=(
                    "当前资料库未检索到可靠依据，"
                    "建议咨询专业医生或药师，不要将本系统回答作为诊断依据。"
                ),
                evidence_count=len(tool_input.evidence),
            )

        if tool_input.answer_basis.strip() == "":
            return GroundingCheckOutput(
                success=True,
                grounded=False,
                reason="未生成有效回答。",
                suggestion="系统暂时无法生成可靠回答，请稍后重试。",
                evidence_count=len(tool_input.evidence),
            )

        return GroundingCheckOutput(
            success=True,
            grounded=True,
            reason="检索结果包含可靠依据。",
            suggestion="允许输出最终回答。",
            evidence_count=len(tool_input.evidence),
        )

    except Exception as exc:
        return GroundingCheckOutput(
            success=False,
            grounded=False,
            reason="Grounding Checker 运行异常。",
            suggestion="建议进入系统兜底流程，请稍后重试。",
            evidence_count=0,
            error_message=str(exc),
        )


def run(
    tool_input: GroundingCheckInput
) -> GroundingCheckOutput:
    """
    兼容 Agent 工具调用。
    """
    return grounding_checker(tool_input)


if __name__ == "__main__":

    test_input = GroundingCheckInput(
        has_reliable_evidence=True,
        answer_basis="建议低盐饮食并规律运动。",
        evidence=[
            {
                "source": "高血压健康管理指南",
                "content": "控制盐摄入。",
                "distance": 0.12,
                "reliable": True,
            }
        ],
    )

    result = grounding_checker(test_input)

    print(result.model_dump())