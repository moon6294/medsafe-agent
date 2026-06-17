# backend_api.py
# 完整的后端 API 服务，提供健康问答、用药安全、风险检测、说明书上传与解析等功能

import os
import uvicorn
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# 导入 Agent
from agents.main_agent import main_agent
from agents.instruction_agent import instruction_agent

# 导入 schemas
from schemas.tool_schemas import (
    SourceItem,
    ToolCallItem, 
    RagToolOutput,
    RiskCheckOutput,
    InstructionParseOutput,
    InstructionSectionOutput,
)

# ========== 初始化 FastAPI ==========
app = FastAPI(title="MedSafe Agent API", version="1.0")

# ========== CORS 配置（允许本地开发与云端访问） ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",      # 本地 Vite 开发
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:6006",      # 通过 SSH 隧道访问
        "http://127.0.0.1:6006",
        # 如需部署到公网，可添加你的 AutoDL 域名
        # "https://your-autodl-domain.seetacloud.com",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 请求模型 ==========
class ChatRequest(BaseModel):
    query: str
    top_k: int = 3

class RiskCheckRequest(BaseModel):
    query: str

class InstructionUploadRequest(BaseModel):
    query: str = "请帮我解读这份药品说明书"

# ========== 工具函数：将 main_agent 返回的 dict 转为标准响应 ==========
def agent_result_to_rag_output(result: Dict[str, Any], query: str) -> RagToolOutput:
    """将 main_agent 的返回字典转换为 RagToolOutput"""
    sources = []
    for s in result.get("sources", []):
        if isinstance(s, dict):
            sources.append(SourceItem(
                title=s.get("title", ""),
                content=s.get("content", ""),
                source=s.get("source"),
                score=s.get("score"),
            ))
        elif hasattr(s, "title"):
            sources.append(s)

    # --- 新增：转换 tool_called 为 tool_calls ---
    tool_calls = []
    for idx, tool_name in enumerate(result.get("tool_called", [])):
        tool_calls.append(ToolCallItem(
            id=f"tc-{idx}",
            tool=tool_name,
            input="",   # 可根据需要填充，如 query
            output="执行完成",
            duration=0,
            status="success"
        ))
    # 如果子 Agent 返回了更详细的 tool_calls（含 input/output/duration），优先使用
    if "tool_calls" in result and isinstance(result["tool_calls"], list) and result["tool_calls"]:
        tool_calls = []
        for i, tc in enumerate(result["tool_calls"]):
            tool_calls.append(ToolCallItem(
                id=tc.get("id", f"tc-{i}"),
                tool=tc.get("tool", "unknown"),
                input=tc.get("input", ""),
                output=tc.get("output", ""),
                duration=tc.get("duration", 0),
                status=tc.get("status", "success")
            ))

    # --- 新增：获取推理步骤 ---
    reasoning_steps = result.get("reasoning_steps", [])

    return RagToolOutput(
        success=result.get("success", True),
        query=query,
        answer=result.get("answer", "抱歉，未能生成有效回答。"),
        sources=sources,
        tool_calls=tool_calls,                # 新增字段
        reasoning_steps=reasoning_steps,      # 新增字段
        error_message=result.get("error_message"),
    )

# ========== 接口 1：统一问答入口（健康科普 / 用药安全 / 风险路由） ==========
@app.post("/api/chat", response_model=RagToolOutput)
async def chat(request: ChatRequest):
    """
    统一问答接口，内部通过 main_agent 自动路由到对应的子 Agent。
    输入：query（问题文本），top_k（检索数量，默认3）
    输出：包含 answer、sources、risk_level 等字段
    """
    if not request.query or not request.query.strip():
        return RagToolOutput(
            success=False,
            query=request.query,
            answer="请输入具体的医疗健康或用药安全问题。",
            sources=[],
            error_message="empty query"
        )
    
    result = main_agent(query=request.query, top_k=request.top_k)
    return agent_result_to_rag_output(result, request.query)

# ========== 接口 2：风险检测（独立调用） ==========
@app.post("/api/risk/check", response_model=RiskCheckOutput)
async def check_risk(request: RiskCheckRequest):
    """
    仅检测输入文本的风险等级，不生成完整回答。
    """
    result = main_agent(query=request.query, top_k=1)
    return RiskCheckOutput(
        success=True,
        risk_level=result.get("risk_level", "low"),
        risk_reason=result.get("risk_reason", "未检测到明确风险信号。"),
        suggestion=result.get("answer", "请咨询医生或药师获取专业建议。")[:200],
        error_message=result.get("error_message"),
    )

# ========== 接口 3：说明书上传与完整解读 ==========
@app.post("/api/instruction/upload", response_model=InstructionParseOutput)
async def upload_instruction(
    file: UploadFile = File(...),
    query: str = Form("请帮我解读这份药品说明书")
):
    """
    上传图片或 PDF 说明书，调用 instruction_agent 进行：
    1. OCR/PDF 解析
    2. 栏目提取
    3. LLM 生成通俗解读
    4. 安全审查
    """
    # 保存文件
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        result = instruction_agent(file_path=file_path, query=query)
    except Exception as e:
        return InstructionParseOutput(
            success=False,
            file_path=file_path,
            file_type=file.filename.split('.')[-1].lower(),
            text="",
            error_message=f"Agent 调用异常：{str(e)}"
        )

    return InstructionParseOutput(
        success=result.get("success", True),
        file_path=file_path,
        file_type=file.filename.split('.')[-1].lower(),
        text=result.get("answer", ""),
        error_message=result.get("error_message")
    )

# ========== 接口 4：说明书栏目提取（仅结构化，不生成解读） ==========
@app.post("/api/instruction/sections", response_model=InstructionSectionOutput)
async def extract_sections(data: dict):
    """
    仅提取说明书中的结构化栏目（药品名称、适应症、用法用量等），
    适用于前端需要单独展示栏目信息的场景。
    """
    text = data.get("text", "")
    if not text.strip():
        return InstructionSectionOutput(
            success=False,
            error_message="未提供说明书文本内容"
        )

    try:
        from tools.instruction_section_extractor import run as section_extractor_run
        section_result = section_extractor_run(text)
    except Exception as e:
        return InstructionSectionOutput(
            success=False,
            error_message=f"栏目提取工具调用失败：{str(e)}"
        )

    return InstructionSectionOutput(
        success=section_result.get("success", False),
        drug_name=section_result.get("drug_name"),
        indication=section_result.get("indication"),
        dosage=section_result.get("dosage"),
        contraindications=section_result.get("contraindications"),
        adverse_reactions=section_result.get("adverse_reactions"),
        precautions=section_result.get("precautions"),
        special_population=section_result.get("special_population"),
        interactions=section_result.get("interactions"),
        storage=section_result.get("storage"),
        raw_text=section_result.get("raw_text"),
        error_message=section_result.get("error_message")
    )

# ========== 接口 5：健康检查（用于前端探测后端是否存活） ==========
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "MedSafe Agent API"}


# Serve the Vite build from the same FastAPI service in production.
FRONTEND_DIST = Path(__file__).resolve().parent / "frontend-react" / "dist"


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str = ""):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")

    index_file = FRONTEND_DIST / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend build not found")

    frontend_root = FRONTEND_DIST.resolve()
    requested_path = (frontend_root / full_path).resolve()

    if requested_path == frontend_root or frontend_root in requested_path.parents:
        if requested_path.is_file():
            return FileResponse(requested_path)

    return FileResponse(index_file)

# ========== 启动服务 ==========

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))  # Render provides PORT in production.
    # 解析命令行参数 --port
    for i, arg in enumerate(sys.argv):
        if arg.startswith("--port") and "=" in arg:
            port = int(arg.split("=")[1])
        elif arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
