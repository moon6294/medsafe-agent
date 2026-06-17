import { useState } from "react";
import { MessageSquare, FileText, ShieldCheck, Heart } from "lucide-react";
import { QAChat } from "./components/QAChat";
import { DrugOCR } from "./components/DrugOCR";

type Tab = "qa" | "ocr";

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>("qa");

  return (
    <div className="min-h-screen bg-background flex flex-col" style={{ fontFamily: "'Inter', sans-serif" }}>
      {/* Header */}
      <header className="shrink-0 border-b border-border bg-card px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "linear-gradient(135deg, #0c6e8a 0%, #1a8fa8 100%)" }}>
            <ShieldCheck className="h-4 w-4 text-white" />
          </div>
          <div>
            <h1 style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "1rem", color: "#1a2332", lineHeight: 1.2 }}>
              MedSafe Agent
            </h1>
            <p style={{ fontSize: "0.7rem", color: "#5a7289", lineHeight: 1 }}>医疗健康科普与用药安全助手</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 rounded-lg bg-muted p-1">
          <button
            onClick={() => setActiveTab("qa")}
            className={`flex items-center gap-2 rounded-md px-4 py-2 transition-all ${activeTab === "qa" ? "bg-card shadow-sm text-[#0c6e8a]" : "text-muted-foreground hover:text-foreground"}`}
            style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 500, fontSize: "0.85rem" }}
          >
            <MessageSquare className="h-4 w-4" />
            健康问答
          </button>
          <button
            onClick={() => setActiveTab("ocr")}
            className={`flex items-center gap-2 rounded-md px-4 py-2 transition-all ${activeTab === "ocr" ? "bg-card shadow-sm text-[#0c6e8a]" : "text-muted-foreground hover:text-foreground"}`}
            style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 500, fontSize: "0.85rem" }}
          >
            <FileText className="h-4 w-4" />
            药品说明书解析
          </button>
        </div>

        <div className="flex items-center gap-1.5">
          <Heart className="h-3.5 w-3.5 text-red-400" />
          <span style={{ fontSize: "0.75rem", color: "#5a7289" }}>Multi-Agent · RAG · Tool Calling</span>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 min-h-0 p-4" style={{ height: "calc(100vh - 57px)" }}>
        <div className="h-full max-w-7xl mx-auto">
          {activeTab === "qa" ? <QAChat /> : <DrugOCR />}
        </div>
      </main>
    </div>
  );
}
