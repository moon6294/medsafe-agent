# config/llm_client.py
from typing import List, Dict, Optional

from openai import OpenAI

from config.settings import (
    QWEN_API_KEY,
    QWEN_BASE_URL,
    QWEN_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    LLM_TIMEOUT,
    check_settings,
)


# 程序启动时先检查配置
check_settings()


client = OpenAI(
    api_key=QWEN_API_KEY,
    base_url=QWEN_BASE_URL,
    timeout=LLM_TIMEOUT,
)


def call_llm(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    统一的大模型调用函数。

    agents/ 目录下所有 Agent 都通过这个函数调用 Qwen-Plus，
    不要在每个 Agent 文件里重复写 OpenAI 客户端代码。
    """
    try:
        response = client.chat.completions.create(
            model=model or QWEN_MODEL,
            messages=messages,
            temperature=temperature if temperature is not None else LLM_TEMPERATURE,
            max_tokens=max_tokens or LLM_MAX_TOKENS,
        )

        return response.choices[0].message.content

    except Exception as e:
        # 先抛出异常，后面可以交给 grounding_checker.py 或 main.py 做统一兜底
        raise RuntimeError(f"Qwen API 调用失败：{str(e)}")


def simple_llm_test() -> None:
    """
    简单测试 Qwen API 是否能正常调用。
    """
    messages = [
        {
            "role": "system",
            "content": "你是 MedSafe Agent 项目的测试助手。"
        },
        {
            "role": "user",
            "content": "请用一句话说明你是否可以正常工作。"
        }
    ]

    answer = call_llm(messages)
    print(answer)


if __name__ == "__main__":
    simple_llm_test()