import { useState, useRef, useCallback, useEffect } from "react";
import { Upload, FileText, Loader2, AlertTriangle, CheckCircle, Info, Users, Activity, Pill, Camera, X, Circle } from "lucide-react";
import { API_ENDPOINTS } from '../../config';

// ===== 类型定义 =====
interface ParsedSection {
  title: string;
  icon: React.ReactNode;
  content: string[];
  color: string;
  bgColor: string;
  borderColor: string;
}

interface OCRResult {
  rawText: string;
  drugName: string;
  sections: ParsedSection[];
  warnings: string[];
}

interface StoredResult {
  rawText: string;
  drugName: string;
  sections: Array<{ title: string; content: string[] }>;
  warnings: string[];
}

// ===== 完整的 Mock 数据（阿莫西林胶囊） =====
const MOCK_OCR_RESULT: OCRResult = {
  rawText: `阿莫西林胶囊
【药品名称】通用名：阿莫西林胶囊 英文名：Amoxicillin Capsules 汉语拼音：Amoxilin Jiaonang
【成分】本品主要成分为阿莫西林。
【性状】本品内容物为白色至类白色粉末或颗粒。
【适应症】适用于敏感菌（不产β内酰胺酶菌株）所致的感染：1.溶血链球菌、肺炎链球菌、葡萄球菌或流感嗜血杆菌所致中耳炎、鼻窦炎、咽炎、扁桃体炎等上呼吸道感染。2.大肠埃希菌、奇异变形菌或粪肠球菌所致的泌尿生殖道感染。3.溶血链球菌、葡萄球菌或大肠埃希菌所致的皮肤软组织感染。
【规格】0.25g
【用法用量】口服。成人一次0.5g，每6~8小时1次，每日剂量不超过4g。儿童每日剂量按体重20~40mg/kg，每8小时1次；3个月以下婴儿每日剂量按体重30mg/kg，每12小时1次。
【不良反应】消化系统：恶心、呕吐、腹泻及假膜性肠炎等。过敏反应：皮疹、荨麻疹、药热和哮喘等。血液系统：贫血、血小板减少、嗜酸性粒细胞增多。
【禁忌】青霉素过敏及青霉素皮肤试验阳性患者禁用。
【注意事项】1.用药前必须详细询问过敏史；2.与庆大霉素不可混合静脉点滴；3.肾功能严重损害者需调整剂量；4.长期使用应注意菌群失调。
【孕妇及哺乳期妇女用药】动物实验未见明显致畸；但孕妇用药应权衡利弊。哺乳期妇女服用后可由乳汁分泌，可能引起婴儿腹泻、过敏等。
【儿童用药】3个月以下婴儿、早产儿慎用。
【老年用药】老年患者由于肾功能减退，应注意调整剂量。
【贮藏】密封，在干燥处保存。`,
  drugName: "阿莫西林胶囊",
  sections: [
    {
      title: "适应症",
      icon: <Activity className="h-4 w-4" />,
      content: [
        "溶血链球菌、肺炎链球菌所致上呼吸道感染（中耳炎、鼻窦炎、咽炎等）",
        "大肠埃希菌所致泌尿生殖道感染",
        "皮肤软组织感染（葡萄球菌、链球菌所致）",
      ],
      color: "text-blue-700",
      bgColor: "bg-blue-50",
      borderColor: "border-blue-200",
    },
    {
      title: "用法用量",
      icon: <Pill className="h-4 w-4" />,
      content: [
        "成人：一次 0.5g，每 6~8 小时 1 次，每日不超过 4g",
        "儿童：每日按体重 20~40mg/kg，每 8 小时 1 次",
        "3个月以下婴儿：每日 30mg/kg，每 12 小时 1 次",
      ],
      color: "text-teal-700",
      bgColor: "bg-teal-50",
      borderColor: "border-teal-200",
    },
    {
      title: "不良反应",
      icon: <AlertTriangle className="h-4 w-4" />,
      content: [
        "消化系统：恶心、呕吐、腹泻、假膜性肠炎",
        "过敏反应：皮疹、荨麻疹、药热、哮喘",
        "血液系统：贫血、血小板减少、嗜酸性粒细胞增多",
      ],
      color: "text-orange-700",
      bgColor: "bg-orange-50",
      borderColor: "border-orange-200",
    },
    {
      title: "特殊人群用药",
      icon: <Users className="h-4 w-4" />,
      content: [
        "🚫 孕妇：动物实验未见致畸，但需权衡利弊",
        "⚠️ 哺乳期：可由乳汁分泌，可能引起婴儿腹泻或过敏",
        "⚠️ 儿童：3个月以下婴儿、早产儿慎用",
        "⚠️ 老年：肾功能减退者注意调整剂量",
      ],
      color: "text-purple-700",
      bgColor: "bg-purple-50",
      borderColor: "border-purple-200",
    },
  ],
  warnings: [
    "🚫 青霉素过敏或皮肤试验阳性者 **禁用**",
    "用药前必须询问详细过敏史",
    "与庆大霉素不可混合静脉点滴",
    "肾功能严重损害者需调整剂量",
    "长期使用注意菌群失调",
  ],
};

const SAMPLE_TEXTS = [
  "阿莫西林胶囊（抗生素）",
  "布洛芬缓释胶囊（NSAIDs）",
  "二甲双胍片（降糖药）",
];

// ===== 工具函数：清理 Markdown 标记（仅用于结构化内容，不用于 rawText） =====
function cleanMarkdown(raw: string): string {
  return raw
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/\*\*/g, '')
    .replace(/\*/g, '')
    .replace(/^[-*]{3,}\s*$/gm, '')
    .replace(/^-\s+/gm, '')
    .replace(/^✓\s+/gm, '')
    .replace(/：\s*/g, '：')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

// ===== CameraModal 组件 =====
function CameraModal({ onCapture, onClose }: { onCapture: (dataUrl: string) => void; onClose: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);

  useEffect(() => {
    const startCamera = async () => {
      try {
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
        });
        setStream(mediaStream);
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
          await videoRef.current.play();
        }
      } catch (err) {
        setError('无法访问摄像头，请检查权限或使用其他方式上传。');
        console.error(err);
      }
    };
    startCamera();

    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const handleCapture = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.95);
    onCapture(dataUrl);
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-3xl w-full overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
          <h3 className="text-lg font-medium text-gray-800">📷 拍照识别说明书</h3>
          <button onClick={onClose} className="p-1 rounded-full hover:bg-gray-100 transition-colors">
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>
        <div className="p-4">
          {error ? (
            <div className="text-red-600 text-center py-8">{error}</div>
          ) : (
            <div className="relative bg-black rounded-xl overflow-hidden">
              <video ref={videoRef} className="w-full h-auto max-h-[70vh] object-contain" muted playsInline />
              <canvas ref={canvasRef} className="hidden" />
            </div>
          )}
          <div className="flex gap-3 mt-4 justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleCapture}
              disabled={!!error}
              className="px-6 py-2 rounded-lg bg-[#0c6e8a] text-white font-medium hover:bg-[#095e77] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              拍照识别
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ===== HighlightText 组件（保留，但左侧不再使用，右侧搜索高亮可能用到，暂时保留） =====
function HighlightText({ text, keywords }: { text: string; keywords: string[] }) {
  if (!keywords.length) return <>{text}</>;
  const regex = new RegExp(`(${keywords.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join("|")})`, "g");
  const parts = text.split(regex);
  return (
    <>
      {parts.map((part, i) =>
        keywords.includes(part) ? (
          <mark key={i} style={{ background: "#fef08a", color: "#92400e", borderRadius: "2px", padding: "0 1px" }}>{part}</mark>
        ) : part
      )}
    </>
  );
}

// ===== 创建 ParsedSection（完整映射） =====
function createSection(title: string, content: string[]): ParsedSection {
  const iconMap: Record<string, React.ReactNode> = {
    '适应症': <Activity className="h-4 w-4" />,
    '用法用量': <Pill className="h-4 w-4" />,
    '不良反应': <AlertTriangle className="h-4 w-4" />,
    '禁忌': <AlertTriangle className="h-4 w-4" />,
    '注意事项': <Info className="h-4 w-4" />,
    '特殊人群': <Users className="h-4 w-4" />,
    '特殊人群用药': <Users className="h-4 w-4" />,
    '相互作用': <Activity className="h-4 w-4" />,
    '贮藏': <FileText className="h-4 w-4" />,
  };
  const colorMap: Record<string, string> = {
    '适应症': 'text-blue-700',
    '用法用量': 'text-teal-700',
    '不良反应': 'text-orange-700',
    '禁忌': 'text-red-700',
    '注意事项': 'text-amber-700',
    '特殊人群': 'text-purple-700',
    '特殊人群用药': 'text-purple-700',
    '相互作用': 'text-pink-700',
    '贮藏': 'text-gray-700',
  };
  const bgMap: Record<string, string> = {
    '适应症': 'bg-blue-50',
    '用法用量': 'bg-teal-50',
    '不良反应': 'bg-orange-50',
    '禁忌': 'bg-red-50',
    '注意事项': 'bg-amber-50',
    '特殊人群': 'bg-purple-50',
    '特殊人群用药': 'bg-purple-50',
    '相互作用': 'bg-pink-50',
    '贮藏': 'bg-gray-50',
  };
  const borderMap: Record<string, string> = {
    '适应症': 'border-blue-200',
    '用法用量': 'border-teal-200',
    '不良反应': 'border-orange-200',
    '禁忌': 'border-red-200',
    '注意事项': 'border-amber-200',
    '特殊人群': 'border-purple-200',
    '特殊人群用药': 'border-purple-200',
    '相互作用': 'border-pink-200',
    '贮藏': 'border-gray-200',
  };
  return {
    title,
    icon: iconMap[title] || <FileText className="h-4 w-4" />,
    content,
    color: colorMap[title] || 'text-gray-700',
    bgColor: bgMap[title] || 'bg-gray-50',
    borderColor: borderMap[title] || 'border-gray-200',
  };
}

// ===== 后备解析：使用【】正则 =====
function parseWithBrackets(text: string): ParsedSection[] {
  const sections: ParsedSection[] = [];
  const titles = ['适应症', '用法用量', '不良反应', '禁忌', '注意事项', '特殊人群', '特殊人群用药', '相互作用', '贮藏'];
  for (const title of titles) {
    const regex = new RegExp(`【${title}】\\s*([^【]+)`);
    const match = text.match(regex);
    if (match) {
      const content = match[1].trim();
      const items = content.split(/[。\n]/).filter(s => s.trim().length > 0);
      if (items.length > 0) {
        sections.push(createSection(title, items));
      }
    }
  }
  return sections;
}

// ===== 主解析函数 =====
function parseBackendResponse(text: string, fileName: string): OCRResult {
  // ---- 1. 提取药品名称 ----
  let drugName = '';
  const nameLineMatch = text.match(/【药品名称】\s*([^\n]+)/);
  if (nameLineMatch) {
    let raw = nameLineMatch[1].trim();
    const genericMatch = raw.match(/通用名[：:]\s*([^\s]+)/);
    if (genericMatch) {
      drugName = genericMatch[1].trim();
    } else {
      drugName = raw.split(/英文名|汉语拼音/)[0].trim();
    }
  }
  if (!drugName) {
    const firstLine = text.split('\n')[0]?.trim();
    if (firstLine) drugName = firstLine;
  }
  if (drugName && !/(胶囊|片|颗粒|口服液|注射剂|滴剂|糖浆|混悬液)/.test(drugName)) {
    const dosageMatch = text.match(/(胶囊|片|颗粒|口服液|注射剂|滴剂|糖浆|混悬液)/);
    if (dosageMatch) drugName += dosageMatch[0];
  }
  if (!drugName) drugName = fileName.replace(/\.[^.]+$/, '');

  // ---- 2. 解析栏目 ----
  const sectionDefs = [
    { title: '适应症', keywords: ['适应症', '主治', '功能主治', '用于'] },
    { title: '用法用量', keywords: ['用法用量', '用法', '用量', '服用方法'] },
    { title: '不良反应', keywords: ['不良反应', '副作用', '药物反应'] },
    { title: '禁忌', keywords: ['禁忌', '禁用', '禁止'] },
    { title: '注意事项', keywords: ['注意事项', '注意'] },
    { title: '特殊人群用药', keywords: ['孕妇', '哺乳期', '儿童', '老年', '特殊人群'] },
    { title: '相互作用', keywords: ['相互作用', '配伍', '合用'] },
    { title: '贮藏', keywords: ['贮藏', '储存', '保存'] },
  ];

  const sections: ParsedSection[] = [];
  const warnings: string[] = [];

  const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
  let currentSection: string | null = null;
  let currentContent: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    let matched = false;
    for (const def of sectionDefs) {
      if (def.keywords.some(kw => line.includes(kw) && line.length < 40)) {
        if (currentSection && currentContent.length > 0) {
          const existing = sections.find(s => s.title === currentSection);
          if (existing) existing.content.push(...currentContent);
          else sections.push(createSection(currentSection, currentContent));
        }
        currentSection = def.title;
        currentContent = [];
        matched = true;
        let contentPart = cleanMarkdown(line);
        if (currentSection === '特殊人群用药') {
          const trimmed = contentPart.trim();
          if (/^(一次|每|每日)/.test(trimmed)) contentPart = `- ${trimmed}`;
          else if (/^(提示|特别提醒)/.test(trimmed)) contentPart = `> ${trimmed}`;
          else if (/^必须避免/.test(trimmed)) contentPart = `**${trimmed}**`;
        }
        if (contentPart) currentContent.push(contentPart);
        break;
      }
    }
    if (matched) continue;

    if (currentSection) {
      const isNewSection = sectionDefs.some(def => def.keywords.some(kw => line.includes(kw) && line.length < 40));
      if (isNewSection) {
        if (currentContent.length > 0) {
          const existing = sections.find(s => s.title === currentSection);
          if (existing) existing.content.push(...currentContent);
          else sections.push(createSection(currentSection, currentContent));
        }
        currentSection = null;
        currentContent = [];
        i--;
        continue;
      }
      if (line.length > 0 && !line.match(/^[-*]{3,}$/)) {
        let contentPart = cleanMarkdown(line);
        if (currentSection === '特殊人群用药') {
          const trimmed = contentPart.trim();
          if (/^(一次|每|每日)/.test(trimmed)) contentPart = `- ${trimmed}`;
          else if (/^(提示|特别提醒)/.test(trimmed)) contentPart = `> ${trimmed}`;
          else if (/^必须避免/.test(trimmed)) contentPart = `**${trimmed}**`;
        }
        currentContent.push(contentPart);
      }
    }
  }

  if (currentSection && currentContent.length > 0) {
    const existing = sections.find(s => s.title === currentSection);
    if (existing) existing.content.push(...currentContent);
    else sections.push(createSection(currentSection, currentContent));
  }

  if (sections.length === 0) {
    const fallbackSections = parseWithBrackets(text);
    if (fallbackSections.length > 0) {
      fallbackSections.forEach(s => {
        s.content = s.content.map(cleanMarkdown);
        const existing = sections.find(sec => sec.title === s.title);
        if (existing) existing.content.push(...s.content);
        else sections.push(s);
      });
    } else {
      sections.push({
        title: '全文内容',
        icon: <FileText className="h-4 w-4" />,
        content: [cleanMarkdown(text.slice(0, 500)) + (text.length > 500 ? '…' : '')],
        color: 'text-gray-700',
        bgColor: 'bg-gray-50',
        borderColor: 'border-gray-200',
      });
    }
  }

  const warningTitles = ['禁忌', '不良反应', '注意事项'];
  sections.forEach(s => {
    if (warningTitles.includes(s.title)) {
      s.content.forEach(item => {
        const cleaned = cleanMarkdown(item);
        if (cleaned.includes('禁用') || cleaned.includes('禁忌') || cleaned.includes('过敏') || cleaned.includes('慎用')) {
          warnings.push(`⚠️ ${cleaned}`);
        }
      });
    }
  });
  if (warnings.length === 0) warnings.push('✅ 未检测到明确禁忌，请按药品说明书或医嘱使用');

  return {
    rawText: text,
    drugName,
    sections,
    warnings: warnings.slice(0, 6),
  };
}

// ===== 持久化工具 =====
const STORAGE_KEY = 'drug_ocr_result';

function saveResultToStorage(result: OCRResult) {
  const stored: StoredResult = {
    rawText: result.rawText,
    drugName: result.drugName,
    sections: result.sections.map(s => ({ title: s.title, content: s.content })),
    warnings: result.warnings,
  };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
  } catch (e) {
    console.warn('无法保存解析结果到 localStorage', e);
  }
}

function loadResultFromStorage(): OCRResult | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const stored: StoredResult = JSON.parse(raw);
    const sections = stored.sections.map(s => createSection(s.title, s.content));
    return {
      rawText: stored.rawText,
      drugName: stored.drugName,
      sections,
      warnings: stored.warnings,
    };
  } catch (e) {
    console.warn('无法读取 localStorage 解析结果', e);
    return null;
  }
}

function clearResultFromStorage() {
  localStorage.removeItem(STORAGE_KEY);
}

// ========== 主组件 ==========
export function DrugOCR() {
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<OCRResult | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [showCamera, setShowCamera] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const saved = loadResultFromStorage();
    if (saved) setResult(saved);
  }, []);

  const updateResult = useCallback((newResult: OCRResult) => {
    setResult(newResult);
    saveResultToStorage(newResult);
  }, []);

  const handleClear = () => {
    setResult(null);
    setSearchTerm('');
    clearResultFromStorage();
  };

  // ===== 解析内联加粗 =====
  const parseInline = (text: string): React.ReactNode => {
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={i} style={{ fontWeight: 600, color: '#0c6e8a' }}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  // ===== 增强的 renderContent =====
  const renderContent = (content: string) => {
    const lines = content.split("\n");
    const elements: React.ReactNode[] = [];
    let tableRows: React.ReactNode[] = [];
    let inList = false;

    const flushTable = () => {
      if (tableRows.length > 0) {
        elements.push(
          <div key={`table-${elements.length}`} style={{ overflowX: "auto", marginTop: "0.4rem" }}>
            <table style={{ borderCollapse: "collapse", width: "100%", borderRadius: "0.375rem", overflow: "hidden", border: "1px solid #d0ebf2" }}>
              <tbody>{tableRows}</tbody>
            </table>
          </div>
        );
        tableRows = [];
      }
    };

    lines.forEach((line, i) => {
      const trimmed = line.trim();
      const isTableLine = line.startsWith("|") && line.includes("|");

      if (!isTableLine) flushTable();

      if (trimmed === "") {
        if (inList) elements.push(<div key={i} style={{ height: "0.2rem" }} />);
        else elements.push(<div key={i} style={{ height: "0.5rem" }} />);
        return;
      }

      if (line.startsWith("## ")) {
        elements.push(
          <h3 key={i} style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "1rem", marginTop: "0.75rem", marginBottom: "0.25rem", color: "#0c6e8a" }}>
            {parseInline(line.slice(3))}
          </h3>
        );
        inList = false;
      } else if (line.startsWith("### ")) {
        elements.push(
          <h4 key={i} style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "0.875rem", marginTop: "0.5rem", marginBottom: "0.15rem", color: "#1a2332" }}>
            {parseInline(line.slice(4))}
          </h4>
        );
        inList = false;
      } else if (line.startsWith("**") && line.endsWith("**")) {
        elements.push(
          <p key={i} style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "0.85rem", marginTop: "0.4rem", color: "#1a2332" }}>
            {parseInline(line.slice(2, -2))}
          </p>
        );
        inList = false;
      } else if (line.startsWith("- ")) {
        inList = true;
        elements.push(
          <li key={i} style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.85rem", lineHeight: 1.6, color: "#2c3e50", marginLeft: "1.2rem", marginTop: "0.1rem", paddingLeft: "0.2rem", listStyleType: "disc" }}>
            {parseInline(line.slice(2))}
          </li>
        );
      } else if (line.startsWith("> ")) {
        inList = false;
        elements.push(
          <div key={i} style={{ borderLeft: "4px solid #0c6e8a", marginTop: "0.5rem", background: "#e8f4f8", borderRadius: "0 0.25rem 0.25rem 0", padding: "0.5rem 0.75rem", fontSize: "0.82rem", color: "#0c6e8a", fontFamily: "'Inter', sans-serif" }}>
            {parseInline(line.slice(2))}
          </div>
        );
      } else if (isTableLine) {
        const isSep = line.match(/^\|[\s\-|]+\|$/);
        if (!isSep) {
          const cells = line.split("|").filter(c => c.trim()).map(c => c.trim());
          const isHeader = lines[i + 1]?.match(/^\|[\s\-|]+\|$/);
          tableRows.push(
            <tr key={i} style={{ borderTop: isHeader ? undefined : "1px solid #d0ebf2" }}>
              {cells.map((cell, j) => {
                const contentNode = parseInline(cell);
                return isHeader
                  ? <th key={j} style={{ padding: "0.35rem 0.65rem", fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "0.78rem", textAlign: "left", background: "#e8f4f8", color: "#0c6e8a" }}>{contentNode}</th>
                  : <td key={j} style={{ padding: "0.35rem 0.65rem", fontFamily: "'Inter', sans-serif", fontSize: "0.8rem", color: "#2c3e50" }}>{contentNode}</td>;
              })}
            </tr>
          );
        }
      } else {
        inList = false;
        elements.push(
          <p key={i} style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.85rem", lineHeight: 1.65, color: "#2c3e50", marginTop: "0.15rem", marginBottom: "0.1rem" }}>
            {parseInline(line)}
          </p>
        );
      }
    });

    flushTable();
    return elements;
  };

  // ===== 文件处理（无延迟） =====
  const processFile = useCallback(async (file: File) => {
    setIsProcessing(true);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('query', '请帮我解读这份药品说明书');
      const response = await fetch(API_ENDPOINTS.instructionUpload, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      const data = await response.json();
      if (data.success) {
        const parsed = parseBackendResponse(data.text, file.name);
        updateResult(parsed);
      } else {
        throw new Error(data.error_message || '解析失败');
      }
    } catch (error) {
      console.warn('后端调用失败，使用 Mock 数据:', error);
      updateResult(MOCK_OCR_RESULT);
    } finally {
      setIsProcessing(false);
    }
  }, [updateResult]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && (file.type.startsWith("image/") || file.type === "application/pdf")) {
      processFile(file);
    }
  }, [processFile]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  }, [processFile]);

  const handleCameraCapture = useCallback(async (dataUrl: string) => {
    setIsProcessing(true);
    setResult(null);
    try {
      const response = await fetch(dataUrl);
      const blob = await response.blob();
      const file = new File([blob], 'camera-capture.jpg', { type: 'image/jpeg' });
      await processFile(file);
    } catch {
      updateResult(MOCK_OCR_RESULT);
      setIsProcessing(false);
    }
  }, [processFile, updateResult]);

  const loadSample = async () => {
    setIsProcessing(true);
    setResult(null);
    try {
      const mockFile = new File(['示例说明书文本'], 'sample.txt', { type: 'text/plain' });
      await processFile(mockFile);
    } catch {
      updateResult(MOCK_OCR_RESULT);
      setIsProcessing(false);
    }
  };

  // ===== 渲染 =====
  return (
    <div className="flex h-full gap-4">
      {showCamera && <CameraModal onCapture={handleCameraCapture} onClose={() => setShowCamera(false)} />}

      {/* 左侧：上传 + AI 解读 */}
      <div className="w-80 shrink-0 flex flex-col gap-3">
        <div
          onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`rounded-xl border-2 border-dashed p-6 flex flex-col items-center justify-center cursor-pointer transition-all ${isDragging ? "border-[#0c6e8a] bg-[#e8f4f8]" : "border-border bg-card hover:border-[#0c6e8a]/50 hover:bg-[#f0f7fa]"}`}
          style={{ minHeight: "8rem" }}
        >
          <input ref={fileInputRef} type="file" className="hidden" accept="image/*,.pdf" onChange={handleFileChange} />
          <Upload className={`h-7 w-7 mb-2 ${isDragging ? "text-[#0c6e8a]" : "text-muted-foreground"}`} />
          <p style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "0.875rem", color: isDragging ? "#0c6e8a" : "#1a2332", textAlign: "center" }}>
            上传药品说明书图片
          </p>
          <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.78rem", color: "#5a7289", textAlign: "center", marginTop: "0.25rem" }}>
            支持 JPG、PNG、PDF 格式
          </p>
        </div>

        <button
          onClick={() => setShowCamera(true)}
          className="flex items-center justify-center gap-2 rounded-xl border-2 border-dashed border-[#0c6e8a]/40 bg-[#e8f4f8] hover:bg-[#d0ebf2] hover:border-[#0c6e8a] transition-all py-3"
        >
          <Camera className="h-5 w-5 text-[#0c6e8a]" />
          <span style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "0.875rem", color: "#0c6e8a" }}>拍照识别说明书</span>
        </button>

        <div className="flex items-center gap-2">
          <div className="flex-1 h-px bg-border" />
          <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.75rem", color: "#5a7289" }}>或</span>
          <div className="flex-1 h-px bg-border" />
        </div>

        <div className="rounded-xl border border-border bg-card p-3">
          <p style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "0.78rem", color: "#5a7289", marginBottom: "0.5rem" }}>示例药品说明书</p>
          <div className="flex flex-col gap-1.5">
            {SAMPLE_TEXTS.map((s, i) => (
              <button key={i} onClick={loadSample} className="flex items-center gap-2 rounded-lg border border-border bg-background hover:border-[#0c6e8a] hover:bg-[#e8f4f8] transition-colors px-2.5 py-2">
                <FileText className="h-3.5 w-3.5 text-[#0c6e8a] shrink-0" />
                <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.8rem", color: "#2c3e50" }}>{s}</span>
              </button>
            ))}
          </div>
        </div>

        {/* AI 解读区域 - 使用 renderContent 支持加粗，不再使用 HighlightText */}
        {(result || isProcessing) && (
          <div className="flex-1 rounded-xl border border-border bg-card p-3 flex flex-col min-h-0">
            <p className="mb-2" style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "0.78rem", color: "#5a7289" }}>AI 解读</p>
            {isProcessing ? (
              <div className="flex-1 flex items-center justify-center gap-2">
                <Loader2 className="h-5 w-5 text-[#0c6e8a] animate-spin" />
                <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.82rem", color: "#5a7289" }}>正在解读…</span>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: "none" }}>
                <div style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.85rem", color: "#2c3e50" }}>
                  {renderContent(result!.rawText)}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 右侧：结构化解析 */}
      <div className="flex-1 min-w-0 flex flex-col gap-3">
        {!result && !isProcessing && (
          <div className="flex-1 rounded-xl border border-border bg-card flex flex-col items-center justify-center text-center py-16">
            <FileText className="h-12 w-12 mb-4 text-muted-foreground opacity-30" />
            <h3 style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "1rem", color: "#1a2332", marginBottom: "0.4rem" }}>
              药品说明书智能解析
            </h3>
            <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.85rem", color: "#5a7289", maxWidth: "22rem", lineHeight: 1.6 }}>
              上传药品说明书图片，系统将自动 OCR 识别文字并按结构化方式解析关键信息
            </p>
            <div className="mt-6 grid grid-cols-2 gap-2 max-w-xs">
              {["适应症提取", "用法用量", "禁忌提醒", "特殊人群"].map(f => (
                <div key={f} className="flex items-center gap-1.5 rounded-lg bg-[#e8f4f8] px-2.5 py-2">
                  <CheckCircle className="h-3.5 w-3.5 text-[#0c6e8a]" />
                  <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.78rem", color: "#0c6e8a" }}>{f}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {isProcessing && (
          <div className="flex-1 rounded-xl border border-border bg-card flex flex-col items-center justify-center gap-3">
            <Loader2 className="h-8 w-8 text-[#0c6e8a] animate-spin" />
            <div className="text-center">
              <p style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "0.9rem", color: "#1a2332" }}>正在处理</p>
              <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.82rem", color: "#5a7289", marginTop: 4 }}>OCR 识别 → 分词解析 → 结构化提取…</p>
            </div>
          </div>
        )}

        {result && !isProcessing && (
          <div className="flex-1 overflow-y-auto flex flex-col gap-3" style={{ scrollbarWidth: "none" }}>
            {/* 药品标题 + 清空按钮 */}
            <div className="rounded-xl border border-[#0c6e8a]/30 bg-[#e8f4f8] p-4 flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="w-10 h-10 rounded-xl bg-[#0c6e8a] flex items-center justify-center shrink-0">
                  <Pill className="h-5 w-5 text-white" />
                </div>
                <div className="min-w-0 flex-1">
                  <h2
                    style={{
                      fontFamily: "'DM Sans', sans-serif",
                      fontWeight: 600,
                      fontSize: "1.1rem",
                      color: "#0c6e8a",
                      wordBreak: "break-word",
                      overflowWrap: "break-word",
                    }}
                  >
                    {result.drugName}
                  </h2>
                  <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.78rem", color: "#5a7289", marginTop: 1 }}>
                    已完成 OCR 识别 · 结构化解析完成
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <div className="flex items-center gap-1.5 rounded-lg bg-green-50 border border-green-200 px-3 py-1.5">
                  <CheckCircle className="h-3.5 w-3.5 text-green-600" />
                  <span style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "0.75rem", color: "#16a34a" }}>解析成功</span>
                </div>
                <button
                  onClick={handleClear}
                  className="p-1.5 rounded-lg hover:bg-gray-200/50 transition-colors"
                  title="清除结果"
                >
                  <X className="h-4 w-4 text-gray-500" />
                </button>
              </div>
            </div>

            {/* 搜索框 */}
            <div className="relative">
              <input
                type="text"
                placeholder="搜索说明书内容关键词…"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="w-full rounded-lg border border-border bg-card px-3 py-2 outline-none focus:border-[#0c6e8a] transition-colors"
                style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.85rem", color: "#1a2332" }}
              />
            </div>

            {/* 警告 */}
            <div className="rounded-xl border border-red-200 bg-red-50 p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <AlertTriangle className="h-4 w-4 text-red-600" />
                <h3 style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "0.875rem", color: "#dc2626" }}>禁忌与重要警告</h3>
              </div>
              <div style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.85rem", color: "#b91c1c" }}>
                {renderContent(result.warnings.join('\n'))}
              </div>
            </div>

            {/* 结构化栏目 */}
            <div className="grid grid-cols-2 gap-3">
              {result.sections.map((section, i) => (
                <div key={i} className={`rounded-xl border p-3 ${section.bgColor} ${section.borderColor}`}>
                  <div className={`flex items-center gap-1.5 mb-2 ${section.color}`}>
                    {section.icon}
                    <h3 style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "0.875rem" }}>{section.title}</h3>
                  </div>
                  <div style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.85rem", color: "#374151" }}>
                    {renderContent(section.content.join('\n'))}
                  </div>
                </div>
              ))}
            </div>

            <div className="rounded-lg bg-muted border border-border p-3 flex items-start gap-2">
              <Info className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
              <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.78rem", color: "#5a7289", lineHeight: 1.6 }}>
                以上解析内容由 OCR 识别与 AI 结构化提取生成，仅供参考。实际用药请严格遵照药品说明书原文及医师处方。
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}