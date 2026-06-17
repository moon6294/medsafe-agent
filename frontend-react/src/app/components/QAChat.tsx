import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2, Info } from "lucide-react";
import { SafetyAlert } from "./SafetyAlert";
import { ToolCallLog, ToolCall, RetrievalSource } from "./ToolCallLog";
import { API_ENDPOINTS } from '../../config';

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCall[];
  sources?: RetrievalSource[];
  isUncertain?: boolean;
  safetyTrigger?: string;
  timestamp: Date;
}

const HIGH_RISK_KEYWORDS = ["胸痛", "胸闷", "呼吸困难", "呼吸急促", "严重过敏", "休克", "晕厥", "意识丧失", "大量出血", "心跳停止", "中毒", "窒息"];

const QUICK_QUESTIONS = [
  "高血压患者日常用药注意事项有哪些？",
  "布洛芬和对乙酰氨基酚可以同时服用吗？",
  "糖尿病患者如何预防低血糖？",
  "阿莫西林青霉素过敏患者可以服用吗？",
  "儿童发烧超过多少度需要就医？",
];

// 模拟数据（仅用于开发环境，实际会调用后端）
const MOCK_RESPONSES: Record<string, { content: string; toolCalls: ToolCall[]; sources: RetrievalSource[]; safetyTrigger?: string }> = {
  default_uncertain: {
    content: "❓ **不确定 / 当前资料库未检索到可靠依据**\n\n针对您的问题，本系统在现有知识库中未能检索到具有可靠循证依据的相关信息。\n\n**建议您：**\n- 咨询执业医师或药师获取专业建议\n- 参考官方医疗机构发布的健康指南\n- 如症状紧急，请拨打 120 急救电话",
    toolCalls: [
      { id: "t1", tool: "rag_retrieve", input: "用户查询", output: "未检索到匹配文档（相似度 < 0.60）", duration: 312, status: "empty" },
      { id: "t2", tool: "safety_check", input: "关键词扫描", output: "未检测到高风险词汇", duration: 45, status: "success" },
    ],
    sources: [],
  },
};

function getMockResponse(query: string): { content: string; toolCalls: ToolCall[]; sources: RetrievalSource[]; safetyTrigger?: string } {
  const lowerQuery = query.toLowerCase();
  const safetyTrigger = HIGH_RISK_KEYWORDS.find(kw => query.includes(kw));

  if (query.includes("高血压") && query.includes("用药")) {
    return {
      safetyTrigger,
      content: `## 高血压患者日常用药注意事项

**一、按时规律服药**
高血压是慢性病，需长期甚至终生服药。请勿自行停药或减量，即使血压暂时正常也需坚持。

**二、常用药物类别及注意事项**
| 药物类别 | 代表药物 | 主要注意事项 |
|---------|---------|------------|
| ACEI | 依那普利、培哚普利 | 可能引起干咳，肾功能不全者慎用 |
| ARB | 缬沙坦、氯沙坦 | 禁止与ACEI联用，孕妇禁用 |
| CCB | 氨氯地平、硝苯地平 | 服用期间避免大量食用葡萄柚 |
| 利尿剂 | 氢氯噻嗪 | 注意监测血钾，避免脱水 |
| β受体阻滞剂 | 美托洛尔 | 不可骤然停药，哮喘患者禁用 |

**三、生活方式配合**
- 低盐饮食（< 6g/天）
- 戒烟限酒
- 坚持适度有氧运动

> ⚠️ 本内容仅供科普参考，具体用药方案请遵医嘱。`,
      toolCalls: [
        { id: "t1", tool: "safety_check", input: "高血压 用药 注意事项", output: "未检测到高风险词汇", duration: 38, status: "success" },
        { id: "t2", tool: "rag_retrieve", input: "高血压日常用药注意事项", output: "检索到 4 篇相关文档，最高相似度 0.91", duration: 287, status: "success" },
        { id: "t3", tool: "llm_generate", input: "综合检索文档生成回答", output: "生成完成，包含用药对照表和生活建议", duration: 1243, status: "success" },
      ],
      sources: [
        { id: "s1", title: "中国高血压防治指南（2023版）", content: "高血压患者应在医生指导下选择降压药物，常用药物包括ACEI、ARB、CCB、利尿剂和β受体阻滞剂五大类。起始治疗宜从小剂量开始，逐步调整至目标血压。", score: 0.91, category: "疾病科普" },
        { id: "s2", title: "抗高血压药物不良反应及处理", content: "ACEI类药物约10-15%的患者会出现干咳，与缓激肽积聚有关；CCB类药物可能导致踝部水肿；利尿剂应注意监测血钾及尿酸水平。", score: 0.86, category: "用药安全" },
        { id: "s3", title: "高血压特殊人群用药指导", content: "糖尿病合并高血压优先选用ACEI或ARB；老年高血压患者降压不宜过快；妊娠期高血压禁用ACEI和ARB，可选甲基多巴、拉贝洛尔。", score: 0.78, category: "用药安全" },
      ],
    };
  }

  if (query.includes("布洛芬") && query.includes("对乙酰氨基酚")) {
    return {
      safetyTrigger,
      content: `## 布洛芬与对乙酰氨基酚联用说明

**结论：通常不建议同时服用，但可以交替使用。**

### 作用机制差异
- **对乙酰氨基酚（泰诺）**：主要中枢作用，通过抑制前列腺素合成退热止痛，对胃刺激小
- **布洛芬（芬必得）**：外周抗炎+中枢作用，同时具有抗炎效果，但对胃有刺激

### 联用风险
同时服用可能增加：
- 胃肠道不良反应风险
- 肾脏负担加重
- 肝脏代谢压力（尤其对乙酰氨基酚过量风险）

### 交替使用方案（儿科常用）
若退热效果不足，可每隔 **3-4小时** 交替使用两种药物，但需严格控制剂量。

> ⚠️ **特别提醒**：对乙酰氨基酚每日总量不超过 4g（成人），否则有肝损伤风险。请在医师或药师指导下使用。`,
      toolCalls: [
        { id: "t1", tool: "safety_check", input: "布洛芬 对乙酰氨基酚 联用", output: "检测到药物相互作用查询，标记为重点关注", duration: 52, status: "success" },
        { id: "t2", tool: "rag_retrieve", input: "布洛芬与对乙酰氨基酚同时服用相互作用", output: "检索到 3 篇文档，最高相似度 0.88", duration: 231, status: "success" },
        { id: "t3", tool: "drug_interaction_check", input: "ibuprofen + acetaminophen", output: "相互作用等级：C（轻度，需监测）；无严重禁忌", duration: 178, status: "success" },
        { id: "t4", tool: "llm_generate", input: "综合药物相互作用数据库及检索文档", output: "生成包含机制、风险、交替方案的完整答复", duration: 987, status: "success" },
      ],
      sources: [
        { id: "s1", title: "非甾体抗炎药临床应用指南", content: "布洛芬和对乙酰氨基酚合用时，止痛效果略有增强，但胃肠道不良反应风险随之增加。对于需要更强镇痛效果的患者，可在医师监督下短期合用。", score: 0.88, category: "用药安全" },
        { id: "s2", title: "儿童退热药物使用规范", content: "儿科临床中，对乙酰氨基酚和布洛芬交替使用已有较多实践。通常建议间隔3-4小时交替，有助于维持较平稳的退热效果，避免单药剂量过大。", score: 0.82, category: "用药安全" },
      ],
    };
  }

  if (safetyTrigger) {
    return {
      safetyTrigger,
      content: `## 关于您提到的症状

您描述的**"${safetyTrigger}"**是需要立即重视的症状，可能提示紧急医疗情况。

**请立即：**
1. 🚨 拨打急救电话 **120**
2. 停止当前活动，保持平静
3. 解松衣物，保持呼吸通畅
4. 等待急救人员，不要独自驾车就医

> 本系统无法替代急诊医疗评估，当出现胸痛、呼吸困难、意识改变等症状时，请立即寻求专业医疗救助。`,
      toolCalls: [
        { id: "t1", tool: "safety_check", input: query, output: `检测到高风险词汇："${safetyTrigger}"，触发安全提醒流程`, duration: 41, status: "success" },
        { id: "t2", tool: "emergency_alert", input: `风险词汇: ${safetyTrigger}`, output: "已触发高风险提醒，返回急救引导内容", duration: 23, status: "success" },
      ],
      sources: [
        { id: "s1", title: "急症识别与院前急救指引", content: "胸痛、呼吸困难、意识改变是最需要立即评估的三大急症症状。其中胸痛伴出汗、放射至左臂或下颌时需高度怀疑急性心肌梗死，应立即启动急救系统。", score: 0.95, category: "急救指引" },
      ],
    };
  }

  if (query.includes("糖尿病") && query.includes("低血糖")) {
    return {
      safetyTrigger: undefined,
      content: `## 糖尿病患者预防低血糖指南

### 什么是低血糖？
血糖 < 3.9 mmol/L 即为低血糖。症状包括心慌、出汗、手抖、头晕、饥饿感等。

### 预防策略

**饮食管理**
- 定时定量进餐，不可随意跳餐
- 加强餐间和睡前血糖监测
- 运动前适当加餐（如半个苹果或几片饼干）

**用药注意**
- 严格按医嘱服用降糖药，切勿自行加量
- 磺脲类（格列本脲）和胰岛素低血糖风险最高
- 外出时随身携带糖果或葡萄糖片

**紧急处理（15克原则）**
出现低血糖症状后立即补充 **15g 快速糖分**：
- 3-4块方糖，或
- 150mL 果汁，或
- 3片葡萄糖片

15分钟后再测血糖，若仍未恢复重复上述步骤。`,
      toolCalls: [
        { id: "t1", tool: "safety_check", input: "糖尿病 低血糖 预防", output: "未检测到高风险词汇", duration: 35, status: "success" },
        { id: "t2", tool: "rag_retrieve", input: "糖尿病患者低血糖预防措施", output: "检索到 5 篇文档，最高相似度 0.93", duration: 264, status: "success" },
        { id: "t3", tool: "llm_generate", input: "生成低血糖预防及处理方案", output: "生成完成，包含15克原则和预防策略", duration: 1102, status: "success" },
      ],
      sources: [
        { id: "s1", title: "中国2型糖尿病防治指南（2023版）", content: "低血糖是糖尿病治疗中最常见的急性并发症，严重低血糖可导致昏迷甚至死亡。血糖<3.9mmol/L即需要处理，<3.0mmol/L提示严重低血糖。", score: 0.93, category: "疾病科普" },
        { id: "s2", title: "糖尿病患者低血糖识别与处理", content: "15克原则是处理轻中度低血糖的标准方案：摄入15克快速作用碳水化合物，等待15分钟后复测血糖。若15分钟后血糖仍<3.9mmol/L，重复上述步骤。", score: 0.89, category: "用药安全" },
      ],
    };
  }

  return MOCK_RESPONSES.default_uncertain;
}

export function QAChat() {
  // ===== 持久化：从 localStorage 加载消息 =====
  const loadMessages = (): Message[] => {
    try {
      const stored = localStorage.getItem('chat_messages');
      if (stored) {
        const parsed = JSON.parse(stored);
        return parsed.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        }));
      }
    } catch (e) {
      console.warn('读取历史消息失败', e);
    }
    return [];
  };

  const [messages, setMessages] = useState<Message[]>(loadMessages);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeMessage, setActiveMessage] = useState<Message | null>(null);
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // ===== 组件挂载/卸载状态（用于忽略卸载后的响应） =====
  const mountedRef = useRef(true);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      // 不主动取消请求，让请求完成但忽略结果
      // 如果需要取消，可调用：abortControllerRef.current?.abort();
    };
  }, []);

  // ===== 自动保存到 localStorage =====
  useEffect(() => {
    try {
      localStorage.setItem('chat_messages', JSON.stringify(messages));
    } catch (e) {
      console.warn('保存消息失败', e);
    }
  }, [messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ===== 组件重新挂载时，自动恢复未完成的对话 =====
useEffect(() => {
  // 如果消息列表为空，不处理
  if (messages.length === 0) return;

  // 获取最后一条消息
  const lastMsg = messages[messages.length - 1];

  // 条件：最后一条是用户消息，且没有对应的助手回复（最后一条不是助手消息）
  if (lastMsg.role === "user") {
    // 检查是否有待处理的问题（防重复）
    const pendingId = localStorage.getItem('pending_question_id');
    
    // 如果存在待处理问题，且与当前最后一条消息 ID 一致，则重发
    if (pendingId === lastMsg.id) {
      // 检查是否正在加载中，避免重复发送
      if (!loading) {
        console.log('🔄 检测到未完成的对话，自动重发:', lastMsg.content);
        // 重新发送这条消息
        sendMessage(lastMsg.content);
        // 清除待处理标志（会在 sendMessage 中重新设置）
        localStorage.removeItem('pending_question_id');
      }
    }
  }
}, []); // 仅在挂载时执行一次

  // ===== 清空对话 =====
  const clearChat = () => {
    if (window.confirm('确定要清空所有对话记录吗？')) {
      setMessages([]);
      setActiveMessage(null);
      localStorage.removeItem('chat_messages');
    }
  };

  // ===== 发送消息 =====
  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, userMsg]);
    localStorage.setItem('pending_question_id', userMsg.id);
    setInput("");
    setLoading(true);

    // 创建 AbortController（仅用于可能在需要时取消，但不主动取消）
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await fetch(API_ENDPOINTS.chat, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text, top_k: 3 }),
        signal: controller.signal,
      });

      // 如果组件已卸载，忽略响应
      if (!mountedRef.current) {
        console.log('组件已卸载，忽略响应');
        return;
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('实际来源数量:', data.sources?.length);

      // 再次检查挂载状态
      if (!mountedRef.current) return;

      const assistantMsg: Message = {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: data.answer || "抱歉，未能生成有效回答。",
        toolCalls: data.tool_calls?.map((tc: any) => ({
          id: tc.id || `tc-${Date.now()}`,
          tool: tc.tool || "unknown",
          input: tc.input || "",
          output: tc.output || "",
          duration: tc.duration || 0,
          status: tc.status || "success",
        })) || [],
        sources: data.sources?.map((s: any, index: number) => ({
        id: s.id || `s-${Date.now()}-${index}-${Math.random().toString(36).substring(2, 6)}`,
        title: s.title || "资料来源",
        content: s.content || "",
        score: s.score || 0,
        category: s.category || "参考资料",
        })) || [],
        safetyTrigger: data.risk_level === "high" ? data.risk_reason : undefined,
        isUncertain: data.answer?.includes("不确定") || false,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMsg]);
      setActiveMessage(assistantMsg);
    } catch (error) {
      // 如果组件已卸载，忽略错误
      if (!mountedRef.current) return;

      const errorMsg: Message = {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: `❌ 请求失败：${error instanceof Error ? error.message : '未知错误'}\n\n请确保后端服务已启动（运行 python backend_api.py）且端口 8000 未被占用。`,
        toolCalls: [],
        sources: [],
        isUncertain: true,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);
      setActiveMessage(errorMsg);
    } finally {
      // 只有组件仍挂载时才重置 loading
      if (mountedRef.current) {
        setLoading(false);
        
      }
      // 在 finally 块中的 setLoading(false) 之后添加
localStorage.removeItem('pending_question_id');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const activeAlerts = messages.filter(m => m.role === "assistant" && m.safetyTrigger && !dismissedAlerts.has(m.id));

  // ===== 新增：解析行内 Markdown（加粗） =====
  const parseInline = (text: string): React.ReactNode => {
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={i} style={{ fontWeight: 600, color: '#0c6e8a' }}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };


  // ===== 自定义 Markdown 渲染 =====
  // ===== 修改后的 renderContent（仅修改了调用 parseInline 的地方） =====
  const renderContent = (content: string) => {
    const lines = content.split("\n");
    const elements: React.ReactNode[] = [];
    let tableRows: React.ReactNode[] = [];

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
      const isTableLine = line.startsWith("|") && line.includes("|");
      if (!isTableLine) flushTable();

      if (line.startsWith("## ")) {
        elements.push(
          <h3 key={i} style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "1rem", marginTop: elements.length > 0 ? "0.75rem" : 0, marginBottom: "0.25rem", color: "#0c6e8a" }}>
            {parseInline(line.slice(3))}
          </h3>
        );
      } else if (line.startsWith("### ")) {
        elements.push(
          <h4 key={i} style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "0.875rem", marginTop: "0.5rem", marginBottom: "0.15rem", color: "#1a2332" }}>
            {parseInline(line.slice(4))}
          </h4>
        );
      } else if (line.startsWith("**") && line.endsWith("**")) {
        // 整行加粗（保留原逻辑）
        elements.push(
          <p key={i} style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "0.85rem", marginTop: "0.4rem", color: "#1a2332" }}>
            {parseInline(line.slice(2, -2))}
          </p>
        );
      } else if (line.startsWith("- ")) {
        elements.push(
          <li key={i} style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.85rem", lineHeight: 1.6, color: "#2c3e50", marginLeft: "1rem", marginTop: "0.1rem" }}>
            {parseInline(line.slice(2))}
          </li>
        );
      } else if (line.startsWith("> ")) {
        elements.push(
          <div key={i} style={{ borderLeft: "3px solid #0c6e8a", marginTop: "0.5rem", background: "#e8f4f8", borderRadius: "0 0.25rem 0.25rem 0", padding: "0.5rem 0.75rem", fontSize: "0.82rem", color: "#0c6e8a", fontFamily: "'Inter', sans-serif" }}>
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
      } else if (line.trim() === "") {
        elements.push(<div key={i} style={{ height: "0.3rem" }} />);
      } else {
        elements.push(
          <p key={i} style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.85rem", lineHeight: 1.65, color: "#2c3e50", marginTop: "0.15rem" }}>
            {parseInline(line)}
          </p>
        );
      }
    });

    flushTable();
    return elements;
  };

  

  return (
    <div className="flex h-full gap-4">
      {/* Chat area */}
      <div className="flex flex-col flex-1 min-w-0 gap-3">
        {activeAlerts.length > 0 && (
          <div className="flex flex-col gap-2">
            {activeAlerts.map(m => (
              <SafetyAlert key={m.id} trigger={m.safetyTrigger!} onDismiss={() => setDismissedAlerts(prev => new Set([...prev, m.id]))} />
            ))}
          </div>
        )}

        {/* 清空按钮 */}
        {messages.length > 0 && (
          <div className="flex justify-end">
            <button
              onClick={clearChat}
              className="text-xs text-gray-500 hover:text-gray-700 transition-colors flex items-center gap-1 px-2 py-1 rounded hover:bg-red-50"
            >
              <span>🗑️</span> 清空对话
            </button>
          </div>
        )}

        <div
          className="flex-1 overflow-y-auto rounded-xl border border-border bg-card p-4 flex flex-col gap-4"
          style={{ scrollbarWidth: "none", minHeight: 0 }}
        >
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-8">
              <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4" style={{ background: "linear-gradient(135deg, #0c6e8a 0%, #1a8fa8 100%)" }}>
                <Bot className="h-7 w-7 text-white" />
              </div>
              <h2 style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "1.1rem", color: "#1a2332", marginBottom: "0.4rem" }}>
                MedSafe Agent
              </h2>
              <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.85rem", color: "#5a7289", maxWidth: "26rem", lineHeight: 1.6 }}>
                医疗健康科普与用药安全助手。您可以咨询疾病健康知识或用药相关问题。
              </p>
              <div className="mt-5 w-full max-w-md">
                <p style={{ fontFamily: "'DM Sans', sans-serif", fontSize: "0.75rem", fontWeight: 600, color: "#5a7289", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>快速提问</p>
                <div className="flex flex-col gap-1.5">
                  {QUICK_QUESTIONS.map((q, i) => (
                    <button key={i} onClick={() => sendMessage(q)} className="w-full text-left rounded-lg border border-border bg-background hover:border-[#0c6e8a] hover:bg-[#e8f4f8] transition-colors px-3 py-2" style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.82rem", color: "#2c3e50" }}>
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map(msg => (
                <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                  <div className={`w-7 h-7 rounded-full shrink-0 flex items-center justify-center ${msg.role === "user" ? "bg-[#0c6e8a]" : "bg-[#e8f4f8] border border-[#0c6e8a]/20"}`}>
                    {msg.role === "user" ? <User className="h-3.5 w-3.5 text-white" /> : <Bot className="h-3.5 w-3.5 text-[#0c6e8a]" />}
                  </div>
                  <div
                    className={`max-w-[78%] rounded-xl px-4 py-3 cursor-pointer transition-all ${msg.role === "user" ? "bg-[#0c6e8a] text-white" : `bg-background border ${activeMessage?.id === msg.id ? "border-[#0c6e8a] shadow-sm" : "border-border"}`}`}
                    onClick={() => msg.role === "assistant" && setActiveMessage(msg)}
                  >
                    {msg.role === "user" ? (
                      <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.875rem", lineHeight: 1.6 }}>{msg.content}</p>
                    ) : (
                      <div>
                        {msg.isUncertain && (
                          <div className="flex items-center gap-1.5 mb-2 text-amber-600" style={{ fontSize: "0.75rem", fontWeight: 600 }}>
                            <Info className="h-3.5 w-3.5" />
                            知识库未匹配
                          </div>
                        )}
                        <div>{renderContent(msg.content)}</div>
                        {(msg.toolCalls || msg.sources) && (
                          <div className="mt-2 flex items-center gap-1.5 text-[#5a7289]" style={{ fontSize: "0.72rem" }}>
                            <span className="inline-flex gap-1">
                              {msg.toolCalls?.map(tc => (
                                <span key={tc.id} className={`inline-block w-1.5 h-1.5 rounded-full ${tc.status === "success" ? "bg-green-400" : tc.status === "empty" ? "bg-yellow-400" : "bg-red-400"}`} />
                              ))}
                            </span>
                            {msg.toolCalls?.length ?? 0} 个工具调用 · {msg.sources?.length ?? 0} 条来源
                            <span className="ml-1 text-[#0c6e8a] cursor-pointer hover:underline" onClick={(e) => { e.stopPropagation(); setActiveMessage(msg); }}>
                              查看详情 →
                            </span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex gap-3">
                  <div className="w-7 h-7 rounded-full shrink-0 flex items-center justify-center bg-[#e8f4f8] border border-[#0c6e8a]/20">
                    <Bot className="h-3.5 w-3.5 text-[#0c6e8a]" />
                  </div>
                  <div className="rounded-xl px-4 py-3 bg-background border border-border flex items-center gap-2">
                    <Loader2 className="h-4 w-4 text-[#0c6e8a] animate-spin" />
                    <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.82rem", color: "#5a7289" }}>正在检索知识库并生成回答…</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        <div className="rounded-xl border border-border bg-card p-3 flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入您的健康或用药问题（Shift+Enter 换行）…"
            rows={2}
            className="flex-1 resize-none bg-transparent outline-none text-foreground placeholder:text-muted-foreground"
            style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.875rem", lineHeight: 1.6, scrollbarWidth: "none" }}
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || loading}
            className="shrink-0 w-9 h-9 rounded-lg flex items-center justify-center transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ background: input.trim() && !loading ? "#0c6e8a" : "#e4ecf2" }}
          >
            <Send className="h-4 w-4" style={{ color: input.trim() && !loading ? "white" : "#5a7289" }} />
          </button>
        </div>

        <p className="text-center" style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.72rem", color: "#5a7289" }}>
          ⚕️ 本系统仅供健康科普参考，不构成医疗诊断建议。如有紧急情况请拨打 120。
        </p>
      </div>

      {/* Right panel: Tool calls + sources */}
      <div className="w-72 shrink-0 flex flex-col rounded-xl border border-border bg-card p-4">
        <h2 className="mb-3 pb-2 border-b border-border" style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "0.875rem", color: "#1a2332" }}>
          推理过程 & 检索依据
        </h2>
        <div className="flex-1 min-h-0">
          <ToolCallLog
            key={activeMessage?.id || 'empty'}
            toolCalls={activeMessage?.toolCalls ?? []}
            sources={activeMessage?.sources ?? []}
          />
        </div>
      </div>
    </div>
  );
}