 # 统一定义所有工具输入输出格式

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class SourceItem(BaseModel):
    """RAG 检索到的资料来源"""
    title: str
    content: str
    source: Optional[str] = None
    score: Optional[float] = None


class RagToolInput(BaseModel):
    """医疗科普 / 用药安全检索工具的输入"""
    query: str
    top_k: int = 3
    
class ToolCallItem(BaseModel):          
    id: str
    tool: str
    input: str
    output: str
    duration: int
    status: str

class RagToolOutput(BaseModel):
    """医疗科普 / 用药安全检索工具的输出"""
    success: bool
    query: str
    answer: str
    sources: List[SourceItem]
    error_message: Optional[str] = None
    tool_calls: List[ToolCallItem] = []  
    reasoning_steps: Optional[List[Dict]] = []


class RiskCheckInput(BaseModel):
    """风险检测工具输入"""
    query: str


class RiskCheckOutput(BaseModel):
    """风险检测工具输出"""
    success: bool
    risk_level: Literal["low", "medium", "high"]
    risk_reason: str
    suggestion: str
    matched_keywords: List[str] = Field(default_factory=list)
    classification_source: Optional[str] = None
    error_message: Optional[str] = None



class GroundingCheckInput(BaseModel):
    """依据检查工具输入"""
    has_reliable_evidence: bool
    answer_basis: str
    evidence: List[Dict[str, Any]]


class GroundingCheckOutput(BaseModel):
    """依据检查工具输出"""
    success: bool
    grounded: bool
    reason: str
    suggestion: str
    evidence_count: int
    error_message: Optional[str] = None

# ========== 说明书上传解析相关 Schema ==========

class InstructionParseInput(BaseModel):
    """说明书文件解析工具输入"""
    file_path: str


class InstructionParseOutput(BaseModel):
    """说明书文件解析工具输出"""
    success: bool
    file_path: str
    file_type: str
    text: str
    error_message: Optional[str] = None


class InstructionSectionInput(BaseModel):
    """说明书栏目提取工具输入"""
    text: str


class InstructionSectionOutput(BaseModel):
    """说明书栏目提取工具输出"""
    success: bool
    drug_name: Optional[str] = None
    indication: Optional[str] = None
    dosage: Optional[str] = None
    contraindications: Optional[str] = None
    adverse_reactions: Optional[str] = None
    precautions: Optional[str] = None
    special_population: Optional[str] = None
    interactions: Optional[str] = None
    storage: Optional[str] = None
    raw_text: Optional[str] = None
    error_message: Optional[str] = None
