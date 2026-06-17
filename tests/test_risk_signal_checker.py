# tests/test_risk_signal_checker.py
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# tests/test_risk_signal_checker.py
from schemas.tool_schemas import RiskCheckInput
from tools.risk_signal_checker import risk_signal_checker


def test_high_risk_chest_pain():
    result = risk_signal_checker(RiskCheckInput(query="我胸痛还呼吸困难怎么办？"))
    assert result.success is True
    assert result.risk_level == "high"


def test_medium_risk_pregnancy():
    result = risk_signal_checker(RiskCheckInput(query="孕妇可以吃布洛芬吗？"))
    assert result.success is True
    assert result.risk_level == "medium"


def test_low_risk_general_question():
    result = risk_signal_checker(RiskCheckInput(query="高血压日常怎么预防？"))
    assert result.success is True
    assert result.risk_level == "low"


def test_empty_query():
    result = risk_signal_checker(RiskCheckInput(query=""))
    assert result.success is False