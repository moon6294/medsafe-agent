from pathlib import Path
import sys
import re
from typing import Dict, Optional, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from schemas.tool_schemas import InstructionSectionInput, InstructionSectionOutput


SECTION_ALIASES: Dict[str, List[str]] = {
    "drug_name": ["药品名称", "通用名称", "商品名称"],
    "indication": ["适应症", "功能主治", "主治功能"],
    "dosage": ["用法用量", "用法与用量", "用量用法", "用法", "用量"],
    "contraindications": ["禁忌"],
    "adverse_reactions": ["不良反应"],
    "precautions": ["注意事项"],
    "special_population": [
        "孕妇及哺乳期妇女用药",
        "儿童用药",
        "老年用药",
        "特殊人群用药",
    ],
    "interactions": ["药物相互作用"],
    "storage": ["贮藏", "储藏"],
}

EXTRA_HEADERS = [
    "成份",
    "成分",
    "性状",
    "作用类别",
    "规格",
    "药理作用",
    "包装",
    "有效期",
    "执行标准",
    "批准文号",
    "说明书修订日期",
    "生产企业",
    "企业名称",
    "生产地址",
    "邮政编码",
    "电话号码",
    "传真号码",
    "网址",
    "电子信箱",
]

# header -> field
HEADER_TO_FIELD: Dict[str, str] = {}
for field, aliases in SECTION_ALIASES.items():
    for alias in aliases:
        HEADER_TO_FIELD[alias] = field

for h in EXTRA_HEADERS:
    HEADER_TO_FIELD[h] = "__extra__"

ALL_HEADERS = sorted(HEADER_TO_FIELD.keys(), key=len, reverse=True)


def _normalize_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = text.replace("（", "(").replace("）", ")")
    text = text.replace("【", "[").replace("】", "]")
    text = text.replace("〔", "[").replace("〕", "]")
    text = text.replace("［", "[").replace("］", "]")
    text = text.replace("「", "]").replace("」", "]")
    text = text.replace("：", ":")

    # 统一 OCR 常见括号
    bracket_pairs = {
        "【": "[",
        "】": "]",
        "［": "[",
        "］": "]",
        "〔": "[",
        "〕": "]",
        "（": "(",
        "）": ")",
        "「": "[",
        "」": "]",
        "『": "[",
        "』": "]",
    }
    for old, new in bracket_pairs.items():
        text = text.replace(old, new)

    # 修正常见 OCR 空格
    replacements = {
        "药 品 名 称": "药品名称",
        "通 用 名 称": "通用名称",
        "英 文 名 称": "英文名称",
        "汉 语 拼 音": "汉语拼音",
        "用 法 用 量": "用法用量",
        "不 良 反 应": "不良反应",
        "注 意 事 项": "注意事项",
        "药 物 相 互 作 用": "药物相互作用",
        "适 应 症": "适应症",
        "禁 忌": "禁忌",
        "贮 藏": "贮藏",
        "成 份": "成份",
        "成 分": "成分",
        "性 状": "性状",
        "规 格": "规格",
        "作 用 类 别": "作用类别",
        "药 理 作 用": "药理作用",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # 把 [禁 忌]、[注 意 事 项] 这种括号内空格去掉
    def clean_bracket(match):
        inner = match.group(1)
        inner = re.sub(r"\s+", "", inner)
        return f"[{inner}]"

    text = re.sub(r"\[([^\]]{1,30})\]", clean_bracket, text)
    text = re.sub(r"\(([^\)\]\n]{1,30})[\)\]]", clean_bracket, text)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def _extract_drug_name(text: str) -> Optional[str]:
    """
    药品名称优先从“通用名称”提取。
    避免从大标题中把品牌名一起提取出来。
    """

    # 1. 优先从通用名称提取：通用名称：对乙酰氨基酚片
    generic_match = re.search(
        r"通用名称\s*[:：]\s*([^\n\[\]]{2,60})",
        text,
    )
    if generic_match:
        name = generic_match.group(1).strip()
        name = re.split(r"(英文名称|汉语拼音|商品名称|成份|成分)", name)[0].strip()
        name = re.sub(r"\s+", "", name)
        if len(name) >= 2:
            return name

    # 2. 再从 [药品名称] 后附近提取
    drug_block_match = re.search(
        r"\[?药品名称\]?\s*(?:通用名称\s*[:：])?\s*([^\n\[\]]{2,60})",
        text,
    )
    if drug_block_match:
        name = drug_block_match.group(1).strip()
        name = re.split(r"(英文名称|汉语拼音|商品名称|成份|成分)", name)[0].strip()
        name = re.sub(r"\s+", "", name)

        if name not in ["通用名称", "英文名称", "汉语拼音"]:
            return name

    # 3. 最后从大标题提取：xxx说明书
    title_match = re.search(
        r"([一-龥A-Za-z0-9（）()·\-\s]{2,60}?(?:片|胶囊|颗粒|口服液|混悬液|滴丸|丸|散|注射液|软膏|乳膏))\s*说明书",
        text,
    )
    if title_match:
        name = title_match.group(1).strip()
        name = re.sub(r"\s+", "", name)

        # 去掉常见品牌/标识
        for prefix in ["万通", "OTC", "乙类"]:
            if name.startswith(prefix):
                name = name[len(prefix):]

        if len(name) >= 2:
            return name

    return None


def _find_headers(text: str) -> List[Tuple[int, int, str, str]]:
    """
    找到所有说明书标题位置。
    返回：(start, end, header, field)
    支持：
    [用法用量]
    用法用量：
    用法用量
    """
    headers_found: List[Tuple[int, int, str, str]] = []

    for header in ALL_HEADERS:
        field = HEADER_TO_FIELD[header]

        patterns = [
            rf"[\[(]\s*{re.escape(header)}\s*[\])]?\s*[:：]?",
            rf"\[{re.escape(header)}\]\s*[:：]?",
            rf"(?m)^\s*{re.escape(header)}\s*[:：]",
            rf"(?m)^\s*{re.escape(header)}\s*$",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                headers_found.append((match.start(), match.end(), header, field))

    # 排序并去重：同一位置只保留最长标题
    headers_found.sort(key=lambda x: (x[0], -(x[1] - x[0])))

    deduped: List[Tuple[int, int, str, str]] = []
    used_starts = set()

    for item in headers_found:
        start = item[0]
        if start in used_starts:
            continue
        used_starts.add(start)
        deduped.append(item)

    deduped.sort(key=lambda x: x[0])
    return deduped


def _extract_sections_by_positions(text: str) -> Dict[str, Optional[str]]:
    """
    通过标题位置切分说明书。
    比正则 lookahead 更适合 OCR 文本。
    """
    result: Dict[str, Optional[str]] = {field: None for field in SECTION_ALIASES.keys()}

    headers = _find_headers(text)

    for idx, (start, end, header, field) in enumerate(headers):
        if field == "__extra__":
            continue

        next_start = len(text)
        if idx + 1 < len(headers):
            next_start = headers[idx + 1][0]

        content = text[end:next_start].strip()
        content = content.strip(" ：:\n\t")
        content = re.sub(r"\n{2,}", "\n", content)

        if not content:
            continue

        # drug_name 单独提取，不用这里的标题切片
        if field == "drug_name":
            continue

        # 同一字段如果已经有内容，不覆盖
        if result.get(field):
            continue

        result[field] = content[:1500]

    result["drug_name"] = _extract_drug_name(text)

    return result


def _postprocess_sections(sections: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    """
    对 OCR 识别后的栏目做修正：
    1. OCR 漏识别 [注意事项] 时，从禁忌字段里切出编号列表作为注意事项。
    2. OCR 文本顺序混乱时，从用法用量中切出不良反应相关内容。
    """

    # 1. 禁忌字段里混入注意事项
    contraindications = sections.get("contraindications")

    if contraindications:
        # 很多说明书注意事项是从 1. / 1、 / 1． 开始
        match = re.search(r"(\n|\s)*(1[\.\．、]\s*)", contraindications)

        if match:
            split_pos = match.start()

            true_contra = contraindications[:split_pos].strip()
            precautions_part = contraindications[split_pos:].strip()

            if true_contra:
                sections["contraindications"] = true_contra

            if precautions_part:
                old_precautions = sections.get("precautions")
                if old_precautions:
                    sections["precautions"] = old_precautions + "\n" + precautions_part
                else:
                    sections["precautions"] = precautions_part

    # 2. 用法用量字段里混入不良反应
    dosage = sections.get("dosage")

    if dosage:
        adverse_markers = [
            "药热及粒细胞减少",
            "粒细胞减少",
            "荨麻疹",
            "长期大量用药",
        ]

        split_positions = [
            dosage.find(marker)
            for marker in adverse_markers
            if marker in dosage
        ]

        if split_positions:
            split_pos = min(split_positions)

            true_dosage = dosage[:split_pos].strip()
            adverse_part = dosage[split_pos:].strip()

            if true_dosage:
                sections["dosage"] = true_dosage

            if adverse_part:
                old_adverse = sections.get("adverse_reactions")
                if old_adverse:
                    sections["adverse_reactions"] = adverse_part + "\n" + old_adverse
                else:
                    sections["adverse_reactions"] = adverse_part

    return sections
    

def instruction_section_extractor(
    tool_input: InstructionSectionInput,
) -> InstructionSectionOutput:
    """
    从说明书全文中提取关键栏目。
    """
    try:
        text = _normalize_text(tool_input.text)

        if not text or len(text) < 20:
            return InstructionSectionOutput(
                success=False,
                raw_text=text,
                error_message="说明书文本过短，无法提取栏目。",
            )

        sections = _extract_sections_by_positions(text)
        sections = _postprocess_sections(sections)

        return InstructionSectionOutput(
            success=True,
            drug_name=sections.get("drug_name"),
            indication=sections.get("indication"),
            dosage=sections.get("dosage"),
            contraindications=sections.get("contraindications"),
            adverse_reactions=sections.get("adverse_reactions"),
            precautions=sections.get("precautions"),
            special_population=sections.get("special_population"),
            interactions=sections.get("interactions"),
            storage=sections.get("storage"),
            raw_text=text[:5000],
            error_message=None,
        )

    except Exception as exc:
        return InstructionSectionOutput(
            success=False,
            raw_text=tool_input.text[:1000],
            error_message=str(exc),
        )


def run(text: str) -> InstructionSectionOutput:
    """兼容 Agent 工具调用。"""
    return instruction_section_extractor(InstructionSectionInput(text=text))


if __name__ == "__main__":
    sample = """
对乙酰氨基酚片说明书
[药品名称]
通用名称：对乙酰氨基酚片
英文名称：Paracetamol Tablets
[用法用量]
口服。4～6岁儿童，一次0.5片；7～12岁儿童，一次1片。
[不良反应]
偶见皮疹、荨麻疹。
[禁忌]
严重肝肾功能不全者禁用。
[注意事项]
本品为对症治疗药，用于解热连续使用不超过3天。
"""
    result = run(sample)
    print(result.model_dump())
