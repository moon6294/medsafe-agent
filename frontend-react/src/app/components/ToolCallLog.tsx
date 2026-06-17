import { ChevronDown, ChevronRight, Database, Search, Shield, Zap } from "lucide-react";
import { useState } from "react";

export interface ToolCall {
  id: string;
  tool: string;
  input: string;
  output: string;
  duration: number;
  status: "success" | "empty" | "error";
}

export interface RetrievalSource {
  id: string;
  title: string;        // 后端返回的友好分类名（如“医疗科普”）
  content: string;
  score: number;
  category: string;     // 保留但不再使用
}

interface ToolCallLogProps {
  toolCalls: ToolCall[];
  sources: RetrievalSource[];
}

const toolIcon = (tool: string) => {
  if (tool.includes("rag") || tool.includes("search") || tool.includes("retrieve")) return <Database className="h-3.5 w-3.5" />;
  if (tool.includes("safety") || tool.includes("risk")) return <Shield className="h-3.5 w-3.5" />;
  if (tool.includes("llm") || tool.includes("generate")) return <Zap className="h-3.5 w-3.5" />;
  return <Search className="h-3.5 w-3.5" />;
};

const toolColor = (tool: string) => {
  if (tool.includes("rag") || tool.includes("retrieve")) return "text-blue-600 bg-blue-50 border-blue-200";
  if (tool.includes("safety") || tool.includes("risk")) return "text-orange-600 bg-orange-50 border-orange-200";
  if (tool.includes("llm") || tool.includes("generate")) return "text-purple-600 bg-purple-50 border-purple-200";
  return "text-teal-600 bg-teal-50 border-teal-200";
};

// 根据分类名返回样式颜色
const categoryColor = (category: string) => {
  const map: Record<string, string> = {
    "医疗科普": "bg-blue-50 text-blue-700 border-blue-200",
    "用药安全": "bg-teal-50 text-teal-700 border-teal-200",
    "急救指引": "bg-red-50 text-red-700 border-red-200",
    "药品说明书": "bg-purple-50 text-purple-700 border-purple-200",
    "参考资料": "bg-gray-50 text-gray-700 border-gray-200",
  };
  return map[category] || "bg-gray-50 text-gray-700 border-gray-200";
};

export function ToolCallLog({ toolCalls, sources }: ToolCallLogProps) {
  const [expandedCalls, setExpandedCalls] = useState<Set<string>>(new Set());
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());

  const toggleCall = (id: string) => {
    setExpandedCalls(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleSource = (id: string) => {
    setExpandedSources(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  if (toolCalls.length === 0 && sources.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center py-12" style={{ color: "#5a7289" }}>
        <Database className="h-10 w-10 mb-3 opacity-30" />
        <p style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 500, fontSize: "0.875rem" }}>发起对话后</p>
        <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.8rem", marginTop: 4 }}>工具调用记录和检索依据将在此显示</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 overflow-y-auto h-full pr-1" style={{ scrollbarWidth: "none" }}>
      {/* 工具调用链路 */}
      {toolCalls.length > 0 && (
        <div>
          <h3 className="mb-2 flex items-center gap-1.5" style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "0.75rem", color: "#5a7289", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            <Zap className="h-3 w-3" />
            工具调用链路
          </h3>
          <div className="flex flex-col gap-1.5">
            {toolCalls.map((call, i) => (
              <div key={call.id} className={`rounded-md border ${toolColor(call.tool)} overflow-hidden`}>
                <button
                  onClick={() => toggleCall(call.id)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-left hover:opacity-80 transition-opacity"
                >
                  <span className="shrink-0" style={{ color: "inherit" }}>{toolIcon(call.tool)}</span>
                  <span className="flex-1 truncate" style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "0.72rem", fontWeight: 500 }}>
                    {i + 1}. {call.tool}
                  </span>
                  <span className="shrink-0" style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "0.68rem", opacity: 0.7 }}>
                    {call.duration}ms
                  </span>
                  <span className={`shrink-0 inline-block w-1.5 h-1.5 rounded-full ${call.status === "success" ? "bg-green-500" : call.status === "empty" ? "bg-yellow-400" : "bg-red-500"}`} />
                  {expandedCalls.has(call.id) ? <ChevronDown className="h-3 w-3 shrink-0" /> : <ChevronRight className="h-3 w-3 shrink-0" />}
                </button>
                {expandedCalls.has(call.id) && (
                  <div className="px-3 pb-2.5 border-t border-current border-opacity-20">
                    <div className="mt-2">
                      <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "0.68rem", opacity: 0.6, marginBottom: 2 }}>INPUT</p>
                      <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "0.7rem", lineHeight: 1.5 }}>{call.input}</p>
                    </div>
                    <div className="mt-2">
                      <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "0.68rem", opacity: 0.6, marginBottom: 2 }}>OUTPUT</p>
                      <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "0.7rem", lineHeight: 1.5 }}>{call.output}</p>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 知识库检索依据 */}
      {sources.length > 0 && (
        <div>
          <h3 className="mb-2 flex items-center gap-1.5" style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "0.75rem", color: "#5a7289", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            <Database className="h-3 w-3" />
            知识库检索依据
          </h3>
          <div className="flex flex-col gap-1.5">
            {sources.map((src) => {
              // 用后端返回的 title（友好分类名）作为标签
              const displayCategory = src.title || src.category || "参考资料";
              return (
                <div key={src.id} className="rounded-md border border-border bg-card overflow-hidden">
                  <button
                    onClick={() => toggleSource(src.id)}
                    className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-muted transition-colors"
                  >
                    {/* 标签：使用友好分类名 */}
                    <span className={`shrink-0 inline-flex items-center rounded px-1.5 py-0.5 border text-[0.65rem] font-medium ${categoryColor(displayCategory)}`}>
                      {displayCategory}
                    </span>
                    {/* 不再显示文件名/路径 */}
                    <span className="flex-1" />
                    {/* 百分比 */}
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "0.68rem", color: "#0c6e8a", fontWeight: 600 }}>
                      {(src.score * 100).toFixed(0)}%
                    </span>
                    {expandedSources.has(src.id) ? <ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground" /> : <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground" />}
                  </button>
                  {expandedSources.has(src.id) && (
                    <div className="px-3 pb-3 border-t border-border bg-muted/30">
                      <p className="mt-2 text-foreground" style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.78rem", lineHeight: 1.6 }}>
                        {src.content}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}