from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Tuple
import os
import sys


_easyocr_reader = None


SECTION_HINTS = [
    "drug",
    "dosage",
    "contraindication",
    "adverse",
    "precaution",
    "storage",
]


def _debug(message: str) -> None:
    if os.getenv("OCR_DEBUG", "").strip().lower() in {"1", "true", "yes"}:
        print(f"[OCR] {message}", file=sys.stderr)


def _get_easyocr_reader():
    global _easyocr_reader

    if _easyocr_reader is None:
        import easyocr

        try:
            _easyocr_reader = easyocr.Reader(["ch_sim", "en"], gpu=True)
        except Exception:
            _easyocr_reader = easyocr.Reader(["ch_sim", "en"], gpu=False)

    return _easyocr_reader


def _box_xy(box: Any) -> Tuple[float, float]:
    try:
        xs = [point[0] for point in box]
        ys = [point[1] for point in box]
        return min(xs), min(ys)
    except Exception:
        return 0.0, 0.0


def _sort_ocr_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
    if not text:
        return 0

    score = len(text)
    lower_text = text.lower()
    for hint in SECTION_HINTS:
        if hint in lower_text:
            score += 300
    return score


def _build_image_variants(image_path: Path, temp_dir: Path) -> List[Path]:
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

    except Exception as exc:
        _debug(f"image enhancement skipped: {exc}")

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


def parse_image_to_text(image_path: str) -> str:
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    best_text = ""

    with TemporaryDirectory(prefix="medsafe_ocr_") as tmp:
        temp_dir = Path(tmp)
        variants = _build_image_variants(path, temp_dir)

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
