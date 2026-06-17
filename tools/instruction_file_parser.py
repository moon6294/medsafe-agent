# tools/instruction_file_parser.py
# 统一判断上传文件类型
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from schemas.tool_schemas import InstructionParseInput, InstructionParseOutput
from parsers.pdf_parser import parse_pdf_to_text
from parsers.image_ocr_parser import parse_image_to_text


PDF_SUFFIXES = {".pdf"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def instruction_file_parser(
    tool_input: InstructionParseInput
) -> InstructionParseOutput:
    """
    解析用户上传的药品说明书文件。
    支持：
    - PDF
    - 图片 OCR
    """
    try:
        file_path = Path(tool_input.file_path)

        if not file_path.exists():
            return InstructionParseOutput(
                success=False,
                file_path=str(file_path),
                file_type="unknown",
                text="",
                error_message="上传文件不存在。",
            )

        suffix = file_path.suffix.lower()

        if suffix in PDF_SUFFIXES:
            text = parse_pdf_to_text(str(file_path))
            file_type = "pdf"

        elif suffix in IMAGE_SUFFIXES:
            text = parse_image_to_text(str(file_path))
            file_type = "image"

        else:
            return InstructionParseOutput(
                success=False,
                file_path=str(file_path),
                file_type="unsupported",
                text="",
                error_message=f"不支持的文件类型：{suffix}。当前仅支持 PDF 和图片。",
            )

        if not text or len(text.strip()) < 20:
            return InstructionParseOutput(
                success=False,
                file_path=str(file_path),
                file_type=file_type,
                text=text,
                error_message="未能从文件中提取到足够文本，请上传更清晰的说明书图片或 PDF。",
            )

        return InstructionParseOutput(
            success=True,
            file_path=str(file_path),
            file_type=file_type,
            text=text,
            error_message=None,
        )

    except Exception as exc:
        return InstructionParseOutput(
            success=False,
            file_path=tool_input.file_path,
            file_type="unknown",
            text="",
            error_message=str(exc),
        )


def run(file_path: str) -> InstructionParseOutput:
    """兼容 Agent 工具调用。"""
    return instruction_file_parser(InstructionParseInput(file_path=file_path))


if __name__ == "__main__":
    test_file = "tests/sample_instructions/sample.pdf"
    result = run(test_file)
    print(result.model_dump())