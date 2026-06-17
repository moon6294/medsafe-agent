# config/settings.py
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()


# =========================
# Qwen / 阿里云百炼配置
# =========================

QWEN_API_KEY = os.getenv("QWEN_API_KEY")

QWEN_BASE_URL = os.getenv(
    "QWEN_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 主模型：用于 Agent 意图识别、回答生成、安全审查
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")


# =========================
# 生成参数
# =========================

LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1500"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))


# =========================
# RAG 默认参数
# =========================

DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "3"))


def check_settings() -> None:
    """
    检查必要配置是否存在。
    在程序启动时调用，避免运行到一半才发现 API Key 没配。
    """
    if not QWEN_API_KEY:
        raise ValueError(
            "未检测到 QWEN_API_KEY。请先在终端执行：\n"
            'export QWEN_API_KEY="你的阿里云百炼API Key"'
        )