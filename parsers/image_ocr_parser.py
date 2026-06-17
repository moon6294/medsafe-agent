from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Tuple
import os
import sys


_easyocr_reader = None
_paddle_ocr = None


SECTION_HINTS = [
    "药品名称",
    "成分",
    "性状",
    "适应症",
    "规格",
    "用法用量",
    "不良反应",
    "禁忌",
    "注意事项",
    "孕妇及哺乳期妇女用药",
    "儿童用药",
    "老年用药",
    "药物相互作用",
    "药理毒理",
    "药代动力学",
    "贮藏",
    "包装",
    "有效期",
]


def _debug(message: str) -> None:
    if os.getenv("OCR_DEBUG", "").strip() in {"1", "true", "True", "yes", "YES"}:
        print(f"[OCR] {message}", file=sys.stderr)


def _get_easyocr_reader():
    """
    Lazy-load EasyOCR as a fallback OCR engine.
    """
    global _easyocr_reader

    if _easyocr_reader is None:
        import easyocr

        try:
            _easyocr_reader = easyocr.Reader(["ch_sim", "en"], gpu=True)
        except Exception:
            _easyocr_reader = easyocr.Reader(["ch_sim", "en"], gpu=False)

    return _easyocr_reader


def _get_paddle_ocr():
    """
    Lazy-load PaddleOCR. PaddleOCR is usually better for dense Chinese drug
    instructions than EasyOCR.
    """
    global _paddle_ocr

    if _paddle_ocr is None:
        from paddleocr import PaddleOCR

        common_kwargs = {
            "lang": "ch",
            "use_angle_cls": True,
        }

        try:
            _paddle_ocr = PaddleOCR(show_log=False, **common_kwargs)
        except TypeError:
            _paddle_ocr = PaddleOCR(**common_kwargs)

    return _paddle_ocr


def _box_xy(box: Any) -> Tuple[float, float]:
    try:
        xs = [point[0] for point in box]
        ys = [point[1] for point in box]
        return min(xs), min(ys)
    except Exception:
        return 0.0, 0.0


def _sort_ocr_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort OCR boxes from top to bottom and left to right.
    """
    return sorted(items, key=lambda item: (_box_xy(item.get("box"))[1], _box_xy(item.get("box"))[0]))


def _items_to_text(items: List[Dict[str, Any]], min_confidence: float) -> str:
    lines: List[str] = []

    for item in _sort_ocr_items(items):
        text = str(item.get("text") or "").strip()
        confidence = float(item.get("confidence") or 0.0)
        if text and confidence >= min_confidence:
            lines.append(text)

    return "\n".join(lines).strip()


def _score_text(text: str) -> int:
    """
    Pick the OCR candidate that keeps the most useful instruction content.
    """
    if not text:
        return 0

    score = len(text)
    for hint in SECTION_HINTS:
        if hint in text:
            score += 300
    return score


def _build_image_variants(image_path: Path, temp_dir: Path) -> List[Path]:
    """
    Build OCR-friendly variants for dense, small-font instruction images.
    """
    variants = [image_path]

    try:
        from PIL import Image, ImageEnhance, ImageOps

        image = Image.open(image_path).convert("RGB")
        width, height = image.size

        scale = 1.0
        if width < 1800:
            scale = max(scale, 1800 / max(width, 1))
        if height < 2400:
            scale = max(scale, 2400 / max(height, 1))
        scale = min(scale, 3.0)

        if scale > 1.05:
            image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)

        enhanced = ImageOps.grayscale(image)
        enhanced = ImageOps.autocontrast(enhanced)
        enhanced = ImageEnhance.Contrast(enhanced).enhance(1.6)
        enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.4)

        enhanced_path = temp_dir / "ocr_enhanced.png"
        enhanced.save(enhanced_path)
        variants.append(enhanced_path)

    except Exception:
        pass

    return variants


def _read_with_easyocr(image_path: Path) -> str:
    reader = _get_easyocr_reader()
    results = reader.readtext(str(image_path), detail=1, paragraph=False)

    items = []
    for result in results or []:
        try:
            box, text, confidence = result[0], result[1], result[2]
            items.append({"box": box, "text": text, "confidence": confidence})
        except Exception:
            continue

    return _items_to_text(items, min_confidence=0.25)


def _extract_paddle_items(raw_result: Any) -> List[Dict[str, Any]]:
    """
    Support the common PaddleOCR 2.x result shape:
    [[box, (text, confidence)], ...]
    and tolerate some newer dict-like outputs.
    """
    items: List[Dict[str, Any]] = []

    if not raw_result:
        return items

    if isinstance(raw_result, dict):
        texts = raw_result.get("rec_texts") or raw_result.get("texts") or []
        scores = raw_result.get("rec_scores") or raw_result.get("scores") or []
        boxes = raw_result.get("rec_boxes") or raw_result.get("dt_polys") or raw_result.get("boxes") or []
        for idx, text in enumerate(texts):
            items.append({
                "box": boxes[idx] if idx < len(boxes) else None,
                "text": text,
                "confidence": scores[idx] if idx < len(scores) else 1.0,
            })
        return items

    if (
        isinstance(raw_result, list)
        and raw_result
        and isinstance(raw_result[0], (list, tuple))
        and len(raw_result[0]) >= 2
        and isinstance(raw_result[0][1], (list, tuple))
        and len(raw_result[0][1]) >= 2
        and isinstance(raw_result[0][1][0], str)
    ):
        for line in raw_result:
            try:
                items.append({
                    "box": line[0],
                    "text": line[1][0],
                    "confidence": line[1][1],
                })
            except Exception:
                continue
        return items

    for page in raw_result:
        if page is None:
            continue

        if isinstance(page, dict):
            items.extend(_extract_paddle_items(page))
            continue

        for line in page:
            try:
                box = line[0]
                text = line[1][0]
                confidence = line[1][1]
                items.append({"box": box, "text": text, "confidence": confidence})
            except Exception:
                continue

    return items


def _read_with_paddleocr(image_path: Path) -> str:
    ocr = _get_paddle_ocr()

    try:
        raw_result = ocr.ocr(str(image_path), cls=True)
    except TypeError:
        raw_result = ocr.ocr(str(image_path))
    except AttributeError:
        raw_result = ocr.predict(str(image_path))

    items = _extract_paddle_items(raw_result)
    return _items_to_text(items, min_confidence=0.35)


def parse_image_to_text(image_path: str) -> str:
    """
    OCR drug instruction images.

    Default engine:
    - PaddleOCR first, because it is usually stronger on dense Chinese documents.
    - EasyOCR fallback, so the old environment still works.

    Set OCR_ENGINE=easyocr to force EasyOCR.
    """
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"图片文件不存在：{image_path}")

    engine = os.getenv("OCR_ENGINE", "paddleocr").strip().lower()
    best_text = ""

    with TemporaryDirectory(prefix="medsafe_ocr_") as tmp:
        temp_dir = Path(tmp)
        variants = _build_image_variants(path, temp_dir)

        if engine in {"paddle", "paddleocr"}:
            try:
                for variant in variants:
                    text = _read_with_paddleocr(variant)
                    _debug(f"paddleocr variant={variant.name} length={len(text)} score={_score_text(text)}")
                    if _score_text(text) > _score_text(best_text):
                        best_text = text
                if best_text:
                    _debug("selected engine=paddleocr")
                    return best_text
            except Exception as exc:
                _debug(f"paddleocr failed: {exc}")

        for variant in variants:
            text = _read_with_easyocr(variant)
            _debug(f"easyocr variant={variant.name} length={len(text)} score={_score_text(text)}")
            if _score_text(text) > _score_text(best_text):
                best_text = text

    if best_text:
        _debug("selected engine=easyocr")

    return best_text.strip()


if __name__ == "__main__":
    test_path = "tests/sample_instructions/medicine.jpg"
    text = parse_image_to_text(test_path)
    print(text[:2000])



















