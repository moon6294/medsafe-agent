# MedSafe Agent：医疗健康科普与用药安全助手

## 一、项目简介

MedSafe Agent 是一个基于 **RAG + 工具调用 + Multi-Agent 协作** 的医疗健康科普与用药安全助手。

本项目面向公众日常健康咨询场景，支持常见健康科普问答、常见药品用药安全问答、高风险医疗信号识别，以及药品说明书 PDF / 图片上传解读。

系统强调医疗安全边界：本系统仅用于健康科普和说明书辅助阅读，不能替代医生诊断、处方或药师指导。对于胸痛、呼吸困难、严重过敏、药物误服等高风险问题，系统会优先触发安全提醒，建议用户及时线下就医。

------

## 二、主要功能

### 1. 医疗健康科普问答

用户可以咨询常见健康管理问题，例如：

- 高血压日常怎么管理？
- 糖尿病患者饮食要注意什么？
- 感冒和流感有什么区别？
- 胃痛和消化不良怎么处理？

系统会调用医疗健康 RAG 检索工具，从知识库中查找相关依据，并结合大模型生成通俗回答。

------

### 2. 用药安全问答

用户可以咨询常见药品的用药安全问题，例如：

- 布洛芬有哪些注意事项？
- 对乙酰氨基酚有哪些不良反应？
- 阿莫西林有哪些禁忌？
- 孕妇可以吃布洛芬吗？

系统会调用用药安全检索工具，从药品安全知识库中检索相关内容，并经过依据检查和安全审查后输出回答。

------

### 3. 高风险医疗信号识别

系统内置 `risk_signal_checker` 风险信号检测工具，可以识别以下高风险场景：

- 胸痛、胸闷、呼吸困难
- 意识不清、昏迷、说话不清、一侧肢体无力
- 严重过敏、喉咙肿胀、面部肿胀
- 大量出血、严重外伤
- 药物误服、过量服用、中毒
- 自伤、自杀风险表达

对于高风险问题，系统不会直接给出诊断或治疗方案，而是优先提示用户及时就医或联系急救。

------

### 4. 药品说明书上传解读

系统支持用户上传药品说明书文件，目前支持：

- PDF 文件
- 图片文件：`.jpg`、`.jpeg`、`.png`、`.bmp`、`.webp`

处理流程如下：

```text
用户上传说明书
→ instruction_file_parser 解析文件
→ pdf_parser / image_ocr_parser 提取文本
→ instruction_section_extractor 提取说明书栏目
→ instruction_agent 生成通俗解读
→ safety_agent 进行安全审查
→ 输出最终回答
```

可提取和解读的栏目包括：

- 药品名称
- 适应症
- 用法用量
- 不良反应
- 禁忌
- 注意事项
- 特殊人群用药
- 药物相互作用
- 贮藏等

------

### 5. 回答依据检查

系统通过 `grounding_checker` 对 RAG 检索结果进行依据检查：

- 如果检索到可靠依据，允许继续生成回答；
- 如果没有可靠依据，系统会拒绝给出确定性结论；
- 该机制用于减少大模型幻觉，提高医疗类回答的可靠性。

------

## 三、技术路线

本项目选择课程大作业方向 B：**Agent 工具调用**。

核心技术包括：

| 模块       | 技术                                   |
| ---------- | -------------------------------------- |
| 主大模型   | Qwen-Plus，阿里云百炼 API              |
| Agent 架构 | Multi-Agent 协作                       |
| 工具调用   | 自定义 Python 工具函数                 |
| RAG 检索   | 向量检索 + 医疗健康 / 用药安全知识库   |
| PDF 解析   | PyMuPDF                                |
| 图片 OCR   | EasyOCR                                |
| 前端界面   | Gradio / Streamlit（待补充）           |
| 安全控制   | 风险信号检测 + 依据检查 + Safety Agent |

------

## 四、项目结构

```text
医疗健康agent/
├── data/
│   ├── raw/
│   │   ├── medical/                           # 医疗健康科普原始资料
│   │   └── drug/                              # 药品安全原始资料
│   └── cleaned/                               # 原始资料与清洗后文本（建库前的准备区）
│
├── agents/                                    # Agent 实现（成员A）
│   ├── drug_safety_agent.py                   # 用药安全Agent
│   ├── health_agent.py                        # 健康科普Agent
│   ├── instruction_agent.py                   # 说明书解读Agent
│   ├── main_agent.py                          # 主控Agent（意图路由）
│   └── safety_agent.py                        # 高风险场景检测Agent
│
├── tools/                                     # 工具模块（成员B+C）
│   ├── drug_safety_search.py                  # 用药安全检索工具（B）
│   ├── grounding_checker.py                   # 异常兜底工具（C）
│   ├── instruction_file_parser.py             # 说明书文件解析（B/C）
│   ├── instruction_section_extractor.py       # 说明书栏目提取
│   ├── medical_rag_search.py                  # 健康科普检索工具（B）
│   └── risk_signal_checker.py                 # 风险信号检测（A）
│
├── parsers/                                   # 文件解析模块（OCR/PDF）
│   ├── __init__.py
│   ├── image_ocr_parser.py                    # 图片OCR
│   └── pdf_parser.py                          # PDF解析
│
├── rag/                                       # RAG知识库模块（成员B）
│   ├── chroma_db/                             # 向量数据库存储（建库后自动生成）
│   ├── build_vector_db.py                     # 构建向量库（读取 data/raw/medical 和 data/raw/drug）
│   └── retriever.py                           # 检索接口
│
├── schemas/                                   # 数据结构定义
│   └── tool_schemas.py                        # 工具输入输出结构
│
├── front-end/                                 # React 前端（由 figmx 生成，与后端 API 配合）
│   ├── src/
│   │   ├── app/
│   │   │   └── components/                    # React 组件
│   │   │       ├── QAChat.tsx                # 健康问答组件
│   │   │       ├── DrugOCR.tsx               # 药品说明书解析组件
│   │   │       ├── SafetyAlert.tsx           # 安全提醒组件
│   │   │       └── ToolCall.tsx              # 工具调用日志组件
│   │   ├── styles/                           # CSS 样式文件
│   │   ├── main.tsx                          # React 入口文件
│   │   └── config.ts                         # API 地址配置（指向后端）
│   ├── public/                                # 静态资源
│   ├── index.html                             # HTML 模板
│   ├── package.json                           # npm 依赖
│   ├── package-lock.json                      # 依赖锁定
│   ├── vite.config.ts                         # Vite 构建配置
│   ├── postcss.config.mjs                     # PostCSS 配置
│   ├── tsconfig.json                          # TypeScript 配置
│   ├── README.md                              # React 前端说明文档
│   └── ATTRIBUTIONS.md                        # 版权与归属说明
│
├── config/                                    # 配置模块（成员C整合）
│   ├── llm_client.py                          # LLM客户端封装
│   ├── prompts.py                             # 各Agent提示词
│   └── settings.py                            # 全局配置（API Key、路径等）
│
├── tests/                                     # 测试模块
│   ├── sample_instructions/                   # 测试用说明书样本
│   └── test_risk_signal_checker.py            # 风险检测器测试
│
├── hf_cache/                                  # HuggingFace 缓存（自动生成）
├── models/                                    # 本地模型存放目录
├── modelscope_cache/                          # ModelScope 缓存
├── uploads/                                   # 用户上传文件暂存目录（backend_api.py 自动创建）
├── download_bge_modelscope.py                 # [可选] BGE模型下载脚本（ModelScope）
├── download_bge.py                            # [可选] BGE模型下载脚本
├── backend_api.py                             # FastAPI 后端服务（核心入口）
├── requirements.txt                           # Python 依赖列表
└── README.md                                  # 项目说明文档
```

------

## 五、核心模块说明

### 1. agents/

`agents/` 目录负责系统的 Multi-Agent 协作逻辑。

| 文件                   | 说明                                                         |
| ---------------------- | ------------------------------------------------------------ |
| `main_agent.py`        | 主控 Agent，负责意图识别、风险前置检查和任务路由             |
| `health_agent.py`      | 健康科普 Agent，处理疾病预防、健康管理、护理建议等问题       |
| `drug_safety_agent.py` | 用药安全 Agent，处理药品注意事项、禁忌、不良反应等问题       |
| `safety_agent.py`      | 安全审查 Agent，处理高风险医疗问题和最终回答安全改写         |
| `instruction_agent.py` | 药品说明书上传解读 Agent，负责 PDF / 图片说明书解析后的通俗解读 |

------

### 2. tools/

`tools/` 目录负责具体工具函数。

| 工具                               | 功能                            |
| ---------------------------------- | ------------------------------- |
| `medical_rag_search.py`            | 医疗健康科普知识检索            |
| `drug_safety_search.py`            | 常见药品安全知识检索            |
| `risk_signal_checker.py`           | 高风险医疗信号识别              |
| `grounding_checker.py`             | 检查回答是否有可靠依据          |
| `instruction_file_parser.py`       | 解析上传的 PDF / 图片说明书文件 |
| `instruction_section_extractor.py` | 从说明书文本中提取关键栏目      |

------

### 3. parsers/

`parsers/` 目录负责底层文件解析。

| 文件                  | 功能                                                  |
| --------------------- | ----------------------------------------------------- |
| `pdf_parser.py`       | 使用 PyMuPDF 提取 PDF 文本；扫描版 PDF 可转图片后 OCR |
| `image_ocr_parser.py` | 使用 EasyOCR 对说明书图片进行文字识别                 |

------

### 4. rag/

`rag/` 目录负责知识库构建与检索。

| 文件                 | 功能 |
| -------------------- | ---- |
| `build_vector_db.py` | 读取原始资料，完成文本清洗、切片、向量化，并写入 ChromaDB |
| `retriever.py`       | 封装统一检索逻辑，向上为检索工具提供稳定接口 |

该模块负责把原始医疗与药品资料整理成可检索的知识库，并向上为 Agent 提供统一的语义检索接口。

------

### 5. schemas/

`schemas/tool_schemas.py` 统一定义工具输入输出格式，避免 Agent、工具和前端之间接口不一致。

主要包括：

- `RiskCheckInput`
- `RiskCheckOutput`
- `GroundingCheckInput`
- `GroundingCheckOutput`
- `InstructionParseInput`
- `InstructionParseOutput`
- `InstructionSectionInput`
- `InstructionSectionOutput`

------

### 6. frontend/

`frontend/app.py` 负责前端界面。

> 【C 同学补充】
> 请在这里补充前端框架、页面功能、启动方式、截图展示和部署地址。

------

## 六、环境配置方法

### 1. 创建 Python 环境

推荐使用 Python 3.10 或 3.11。

```bash
conda create -n medsafe python=3.10 -y
conda activate medsafe
```

如果已经在 AutoDL 的 base 环境中开发，也可以直接使用：

```bash
conda activate base
```

------

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

如果没有 `requirements.txt`，可以先手动安装核心依赖：

```bash
pip install openai python-dotenv pydantic pymupdf pillow easyocr gradio
```

核心依赖说明：

| 依赖 | 作用 |
| ---- | ---- |
| `openai` | 以 OpenAI 兼容接口调用阿里云百炼 Qwen-Plus，用作主 Agent 的大模型能力 |
| `python-dotenv` | 从 `.env` 文件读取 API Key、模型名称、向量库路径等环境变量，避免把密钥写进代码 |
| `pydantic` | 定义工具输入输出结构，保证 Agent、工具和前端之间的数据格式一致 |
| `pymupdf` | 解析用户上传的药品说明书 PDF，提取说明书中的文本内容 |
| `pillow` | 处理上传的说明书图片，为 OCR 识别做基础图像读取与格式转换 |
| `easyocr` | 对图片版说明书进行 OCR 文字识别 |
| `gradio` | 构建可视化 Web 前端，用于展示问答、工具调用日志和检索依据 |

RAG 知识库与检索工具需要额外安装以下依赖：

```bash
pip install chromadb sentence-transformers huggingface_hub -i https://pypi.tuna.tsinghua.edu.cn/simple
```

RAG 依赖说明：

| 依赖 | 作用 |
| ---- | ---- |
| `chromadb` | 本项目使用的向量数据库，用于持久化保存医疗科普和药品安全文档向量，并支持相似度检索 |
| `sentence-transformers` | 用于加载 `models/bge-small-zh-v1.5` 向量模型，并将用户问题和知识库文本编码成向量 |
| `huggingface_hub` | 用于下载和缓存 Hugging Face 模型资源；如果模型已经放在本地 `models/` 目录，则运行时会优先读取本地模型 |

如果在 AutoDL 云服务器上开发，建议将项目、模型、数据库和缓存统一放到数据盘，避免占用系统盘：

```bash
cd /root/autodl-tmp
mkdir -p 医疗健康agent/{data/raw/medical,data/raw/drug,data/cleaned,rag/chroma_db,tools,models,pip_cache}
cd 医疗健康agent

export PIP_CACHE_DIR=/root/autodl-tmp/医疗健康agent/pip_cache
export HF_HOME=/root/autodl-tmp/医疗健康agent/hf_cache
export TRANSFORMERS_CACHE=/root/autodl-tmp/医疗健康agent/hf_cache
export HF_ENDPOINT=https://hf-mirror.com
```

------

### 3. 配置阿里云百炼 API Key

本项目使用阿里云百炼 Qwen-Plus 作为主大模型。

不要把真实 API Key 写进代码或 README。

推荐使用环境变量：

```bash
export QWEN_API_KEY="你的阿里云百炼API_KEY"
```

如果希望每次终端启动自动生效，可以写入 `~/.bashrc`：

```bash
echo 'export QWEN_API_KEY="你的阿里云百炼API_KEY"' >> ~/.bashrc
source ~/.bashrc
```

也可以创建 `.env` 文件：

```env
QWEN_API_KEY=你的阿里云百炼API_KEY
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=1500
LLM_TIMEOUT=60
```

------

### 4. 检查大模型调用

运行：

```bash
PYTHONPATH=. python config/llm_client.py
```

如果配置成功，应能看到 Qwen-Plus 返回测试回答。

------

## 七、如何运行

### 1. 运行主 Agent 测试

```bash
PYTHONPATH=. python agents/main_agent.py
```

该命令会测试几个典型问题，例如：

- 布洛芬有哪些注意事项？
- 高血压日常怎么管理？
- 我胸痛还呼吸困难怎么办？
- 孕妇可以吃布洛芬吗？

预期输出包括：

- 路由 Agent
- 意图识别结果
- 风险等级
- 工具调用链
- 最终回答

------

### 2. 运行风险信号检测工具

```bash
PYTHONPATH=. python tools/risk_signal_checker.py
```

示例：

```text
我胸痛还呼吸困难怎么办？
→ high

孕妇可以吃布洛芬吗？
→ medium

布洛芬有哪些注意事项？
→ low
```

------

### 3. 运行 Grounding Checker

```bash
PYTHONPATH=. python tools/grounding_checker.py
```

该工具用于判断当前回答是否具有可靠检索依据。

------

### 4. 测试说明书 PDF 解析

将测试 PDF 放入：

```text
tests/sample_instructions/
```

例如：

```text
tests/sample_instructions/medicine.pdf
```

运行：

```bash
PYTHONPATH=. python - <<'PY'
from parsers.pdf_parser import parse_pdf_to_text

text = parse_pdf_to_text("tests/sample_instructions/medicine.pdf")
print(text[:1500])
PY
```

------

### 5. 测试说明书图片 OCR

将测试图片放入：

```text
tests/sample_instructions/
```

例如：

```text
tests/sample_instructions/medicine.jpg
```

运行：

```bash
PYTHONPATH=. python - <<'PY'
from parsers.image_ocr_parser import parse_image_to_text

text = parse_image_to_text("tests/sample_instructions/medicine.jpg")
print(text[:1500])
PY
```

------

### 6. 测试说明书栏目提取

```bash
PYTHONPATH=. python - <<'PY'
from tools.instruction_file_parser import run as parse_file
from tools.instruction_section_extractor import run as extract_sections

parse_result = parse_file("tests/sample_instructions/medicine.jpg")
section_result = extract_sections(parse_result.text)
data = section_result.model_dump()

print("药品名称：", data.get("drug_name"))
print("用法用量：", data.get("dosage")[:300] if data.get("dosage") else None)
print("不良反应：", data.get("adverse_reactions")[:300] if data.get("adverse_reactions") else None)
print("禁忌：", data.get("contraindications"))
print("注意事项：", data.get("precautions")[:300] if data.get("precautions") else None)
PY
```

------

### 7. 测试说明书上传解读 Agent

```bash
PYTHONPATH=. python - <<'PY'
from agents.instruction_agent import instruction_agent

r = instruction_agent(
    file_path="tests/sample_instructions/medicine.jpg",
    query="请帮我解释这份说明书"
)

print("路由：", r.get("route"))
print("工具：", r.get("tool_called"))
print("回答：\n", r.get("answer"))
PY
```

预期工具链：

```text
instruction_file_parser
→ instruction_section_extractor
→ safety_agent
```

------

### 8. 运行前端界面

> 【C 同学补充】
> 如果使用 Gradio，可以写：

```bash
PYTHONPATH=. python frontend/app.py
```

启动后访问：

```text
http://服务器IP:7860
```

> 【C 同学补充】
> 请在这里补充实际端口、访问地址、部署说明和截图。

------

## 八、示例问题

### 1. 健康科普类

```text
高血压日常怎么管理？
糖尿病患者饮食要注意什么？
感冒和流感有什么区别？
胃痛和消化不良怎么办？
```

------

### 2. 用药安全类

```text
布洛芬有哪些注意事项？
对乙酰氨基酚有哪些不良反应？
阿莫西林可以随便吃吗？
孕妇可以吃布洛芬吗？
```

------

### 3. 高风险边界测试

```text
我胸痛还呼吸困难怎么办？
我药吃多了怎么办？
我突然意识不清怎么办？
我严重过敏，喉咙肿了怎么办？
```

------

### 4. 说明书上传类

```text
请帮我解释这份说明书
请帮我解释这份说明书的用法用量
请帮我解释这份说明书的禁忌和注意事项
这份说明书里有哪些不良反应？
```

------

## 九、项目运行流程

### 1. 普通健康问答流程

```text
用户输入问题
→ main_agent
→ risk_signal_checker
→ health_agent / drug_safety_agent
→ medical_rag_search / drug_safety_search
→ grounding_checker
→ Qwen-Plus 生成回答
→ safety_agent 安全审查
→ 输出最终回答
```

------

### 2. 高风险问题流程

```text
用户输入高风险症状
→ main_agent
→ risk_signal_checker
→ safety_agent
→ 输出就医提醒
```

------

### 3. 说明书上传解读流程

```text
用户上传 PDF / 图片
→ instruction_agent
→ instruction_file_parser
→ pdf_parser / image_ocr_parser
→ instruction_section_extractor
→ Qwen-Plus 生成说明书解读
→ safety_agent 安全审查
→ 输出最终回答
```

------

## 十、错误处理机制

系统目前包含以下错误处理：

1. **风险问题优先处理**
   高风险症状不进入普通问答流程，直接触发安全提醒。
2. **RAG 无可靠依据时拒答**
   当检索不到可靠依据时，`grounding_checker` 会阻止系统生成确定性回答。
3. **工具调用失败兜底**
   当检索工具、OCR 工具或说明书解析工具失败时，系统返回可理解的错误提示。
4. **API 调用异常兜底**
   当大模型调用失败时，系统会尽量返回检索依据或安全提示。
5. **OCR 识别误差提示**
   说明书图片解析结果可能受拍摄角度、清晰度和 OCR 识别效果影响，系统会提示用户以原说明书、医生或药师指导为准。

------

## 十一、当前项目边界

本项目不提供以下功能：

- 不做疾病诊断；
- 不开具处方；
- 不提供个性化用药剂量决策；
- 不建议用户自行加量、减量、停药或联合用药；
- 不替代医生、药师或急救服务；
- 对资料库无依据的问题不强行回答；
- 对 OCR 识别不清的说明书不输出确定结论。

------

## 十二、分工说明

| 成员   | 负责模块                                               | 工作内容                                                     |
| ------ | ------------------------------------------------------ | :----------------------------------------------------------- |
| A 同学 | Agent 架构 + Multi-Agent + 风险检测 + 说明书解读 Agent | 负责 `agents/` 目录下主要 Agent 逻辑，包括主控 Agent、用药安全 Agent、健康科普 Agent、安全审查 Agent、说明书解读 Agent；负责 `risk_signal_checker.py` 和 Agent 工具调度逻辑 |
| B 同学 | RAG 知识库 + 检索工具                                  | 负责医疗健康科普资料和用药安全资料收集、清洗、向量化建库；负责 `medical_rag_search.py`、`drug_safety_search.py`、`build_vector_db.py`、`retriever.py` |
| C 同学 | 前端 + 部署 + Grounding Checker + 测试                 | 负责 `frontend/app.py`、`main.py`、`grounding_checker.py`、系统部署、测试用例、演示视频和 README 补充 |

------

## 十三、关键技术说明

### 1. RAG 知识库与检索实现

RAG 知识库用于补充大模型自身知识的不确定性，为健康科普回答和用药安全回答提供可检索、可追溯的原文依据。当前项目将知识库划分为两类：一类面向常见疾病、健康管理、预防护理等医疗科普问题；另一类面向常见药品适应症、禁忌、不良反应、注意事项等药品安全问题。

RAG 模块是本项目中“知识准备、向量建库、语义检索”这一整条链路的核心，采用“医疗科普知识库 + 药品安全知识库”双库方案。这样做的好处是：用户询问疾病管理、症状区分等问题时，只检索医疗科普集合；用户询问药品注意事项、过敏处理等问题时，只检索药品安全集合，从而减少不同主题资料混在一起造成的召回误差。

这里需要特别说明：`data/` 与真正的 RAG 知识库不是一回事。`data/raw/medical/` 和 `data/raw/drug/` 存放的是原始公开资料，`data/cleaned/` 存放的是清洗后的中间文本；这些文本经过切片、向量化和入库后，最终写入 `rag/chroma_db/`。因此，运行时真正供系统检索使用的 RAG 知识库，是 `rag/chroma_db/` 中持久化保存的 ChromaDB 向量数据库内容，而不是 `data/` 目录本身。

`rag/` 目录负责知识库构建与检索：

| 文件 | 功能 |
| ---- | ---- |
| `build_vector_db.py` | 从 `data/raw/medical/` 和 `data/raw/drug/` 读取 `.md` / `.txt` 文件，完成文本清洗、切片、向量化，并写入 ChromaDB |
| `retriever.py` | 加载向量模型和 ChromaDB，封装统一检索逻辑，向上为 `medical_rag_search.py` 与 `drug_safety_search.py` 提供稳定接口 |

当前实现参数如下：

- 向量模型：`models/bge-small-zh-v1.5`
- 模型来源名称：`BAAI/bge-small-zh-v1.5`
- 向量模型调用库：`sentence-transformers`
- 向量数据库：`ChromaDB`
- 向量库路径：`/root/autodl-tmp/医疗健康agent/rag/chroma_db`
- 原始资料目录：`data/raw/medical/`、`data/raw/drug/`
- 清洗后资料目录：`data/cleaned/`
- 医疗健康集合：`medical_knowledge`
- 药品安全集合：`drug_safety`
- 建库默认参数：`chunk_size = 450`，`overlap = 80`
- 检索默认参数：`top_k = 4`
- 距离阈值：`distance_threshold = 0.90`，`distance` 越小表示越相关；当命中结果距离大于阈值时，工具会将该片段标记为不可靠依据

其中，`bge-small-zh-v1.5` 是本项目使用的文本向量模型。它不是负责生成回答的大语言模型，而是负责把“用户问题”和“知识库文本片段”转换成向量。转换完成后，ChromaDB 会根据向量距离查找语义最接近的资料片段。`sentence-transformers` 则是加载和调用该向量模型的 Python 库，代码中通过 `SentenceTransformer(...)` 读取本地模型并执行 `encode()` 生成向量。

本项目当前使用的公开资料包括：

- 医疗科普资料：`hypertension.md`、`diabetes.md`、`influenza.md`、`common_cold.md`
- 药品安全资料：`ibuprofen.md`、`amoxicillin.md`

这些文件分别放在：

```text
data/
├── raw/
│   ├── medical/      # 高血压、糖尿病、流行性感冒、普通感冒等公开医疗科普页面
│   └── drug/         # 布洛芬、阿莫西林等公开药品页面
└── cleaned/          # build_vector_db.py 清洗后生成的中间文本

rag/
├── build_vector_db.py
├── retriever.py
└── chroma_db/        # ChromaDB 向量库持久化目录

tools/
├── medical_rag_search.py
└── drug_safety_search.py

models/
└── bge-small-zh-v1.5 # 本地向量模型目录
```

具体实现流程如下：

1. 资料收集与分类  
   将公开医疗科普资料放入 `data/raw/medical/`，将公开药品资料放入 `data/raw/drug/`。当前医疗部分围绕高血压、糖尿病、流行性感冒和普通感冒；药品部分围绕布洛芬和阿莫西林。

2. 文本清洗  
   `build_vector_db.py` 会对原始文本进行预处理，包括统一换行、压缩多余空格、过滤空文本，并保留来源文件名、知识类别、文本块序号等 metadata。清洗后的文本会写入 `data/cleaned/`，便于检查建库前的数据质量。

3. 文本切片  
   RAG 模块采用滑动窗口切片。`chunk_size` 控制每个文本块的最大长度，`overlap` 控制相邻文本块之间保留多少重叠内容。重叠的作用是减少关键信息恰好落在切片边界时造成的语义断裂。本项目统一使用默认值 `450/80`，即每个文本块最多约 450 个字符，相邻文本块之间保留约 80 个字符的重叠内容。

4. 向量化与建库  
   切片后的文本会通过 `models/bge-small-zh-v1.5` 生成向量，再写入 `rag/chroma_db/`。建库时分别创建 `medical_knowledge` 和 `drug_safety` 两个集合，从而实现按知识类型独立管理、独立检索。

5. 检索封装  
   `retriever.py` 统一封装查询向量生成、ChromaDB 相似度检索、距离阈值判断和结果格式化逻辑。`medical_rag_search.py` 与 `drug_safety_search.py` 是面向 Agent 的工具封装，分别调用医疗科普集合和药品安全集合，并返回统一结构的检索结果。

也就是说，这部分不是单纯“查数据库”，而是把“原始资料整理 → 文本清洗 → 可检索文本块构建 → 向量存储 → 查询结果标准化输出”完整串了起来。

向量库构建命令：

```bash
python rag/build_vector_db.py
```

医疗健康科普检索工具测试：

```bash
python tools/medical_rag_search.py
```

药品安全检索工具测试：

```bash
python tools/drug_safety_search.py
```

检索工具返回统一结构，便于 Agent 判断是否可以基于检索依据继续生成回答：

```python
{
    "query": "用户问题",
    "tool": "medical_rag_search 或 drug_safety_search",
    "collection": "medical_knowledge 或 drug_safety",
    "top_k": 4,
    "distance_threshold": 0.90,
    "has_reliable_evidence": True,
    "success": True,
    "results": [
        {
            "rank": 1,
            "content": "检索到的原文片段",
            "source": "资料来源文件",
            "category": "medical 或 drug",
            "chunk_index": 0,
            "distance": 0.32,
            "reliable": True
        }
    ]
}
```

如果 `has_reliable_evidence` 为 `False`，Agent 不应直接生成确定性医疗结论，而应提示“当前资料库未检索到可靠依据，建议咨询医生或药师”。该机制用于降低医疗问答中的幻觉风险。

------

### 2. 前端界面说明

> 【C 同学补充】

- 前端框架：
- 页面功能：
- 启动命令：
- 部署地址：
- 页面截图：

------

### 3. 系统部署说明

> 【C 同学补充】

- 部署平台：
- 服务器环境：
- 端口：
- 访问链接：
- 注意事项：

------

### 4. 测试用例与结果

> 【C 同学补充，A/B 配合】

- 核心知识测试：
- 延伸知识测试：
- 超出范围测试：
- 高风险边界测试：
- 说明书上传测试：

------

## 十四、项目声明

本项目为《大模型微调与优化》课程大作业，仅用于教学展示和技术实践。

系统输出内容仅供医疗健康科普和药品说明书辅助阅读，不构成医学诊断、治疗建议、处方建议或急救指导。

如存在身体不适、用药疑问或紧急情况，请及时咨询医生、药师或前往正规医疗机构。
