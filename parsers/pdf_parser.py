# parsers/pdf_parser.py
from pathlib import Path
from typing import List

import pymupdf as fitz  # PyMuPDF

from parsers.image_ocr_parser import parse_image_to_text


def _extract_text_from_pdf(pdf_path: str, max_pages: int = 10) -> str:
    """
    优先直接提取 PDF 内嵌文本。
    """
    doc = fitz.open(pdf_path)
    texts: List[str] = []

    page_count = min(len(doc), max_pages)

    for i in range(page_count):
        page = doc[i]
        text = page.get_text("text")
        if text:
            texts.append(text)

    doc.close()
    return "\n".join(texts).strip()


def _ocr_pdf_pages(pdf_path: str, max_pages: int = 5, zoom: float = 2.0) -> str:
    """
    对扫描版 PDF 进行 OCR。
    为了避免太慢，默认只识别前 5 页。
    """
    doc = fitz.open(pdf_path)
    texts: List[str] = []

    temp_dir = Path(pdf_path).parent / "_pdf_ocr_temp"
    temp_dir.mkdir(exist_ok=True)

    page_count = min(len(doc), max_pages)

    for i in range(page_count):
        page = doc[i]
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix)

        image_path = temp_dir / f"page_{i + 1}.png"
        pix.save(str(image_path))

        try:
            text = parse_image_to_text(str(image_path))
            if text:
                texts.append(text)
        finally:
            if image_path.exists():
                image_path.unlink()

    doc.close()

    try:
        temp_dir.rmdir()
    except Exception:
        pass

    return "\n".join(texts).strip()


def parse_pdf_to_text(pdf_path: str) -> str:
    """
    解析 PDF 说明书：
    1. 优先提取 PDF 内嵌文字；
    2. 如果提取结果太短，则认为可能是扫描件，改用 OCR。
    """
    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF 文件不存在：{pdf_path}")

    text = _extract_text_from_pdf(str(path))

    # 说明书正常文本通常不会太短；太短说明可能是扫描版 PDF
    if len(text) >= 100:
        return text

    ocr_text = _ocr_pdf_pages(str(path))
    return ocr_text