import { AlertTriangle, Phone, X } from "lucide-react";
import { useState } from "react";

interface SafetyAlertProps {
  trigger: string;
  onDismiss: () => void;
}

export function SafetyAlert({ trigger, onDismiss }: SafetyAlertProps) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 shadow-sm">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-100">
        <AlertTriangle className="h-4 w-4 text-red-600" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-red-800" style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "0.875rem" }}>
          ⚠️ 高风险症状识别 — 请立即寻求医疗帮助
        </p>
        <p className="mt-1 text-red-700" style={{ fontFamily: "'Inter', sans-serif", fontSize: "0.8rem", lineHeight: 1.5 }}>
          您描述的症状（<span className="font-semibold">{trigger}</span>）可能提示紧急医疗情况。请勿仅依赖本系统，立即拨打急救电话或前往最近急诊室。
        </p>
        <div className="mt-2 flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-md bg-red-600 px-2.5 py-1 text-white" style={{ fontSize: "0.75rem", fontWeight: 600 }}>
            <Phone className="h-3 w-3" />
            急救电话：120
          </span>
          <span className="text-red-500" style={{ fontSize: "0.75rem" }}>本内容不构成医疗诊断</span>
        </div>
      </div>
      <button onClick={onDismiss} className="shrink-0 text-red-400 hover:text-red-600 transition-colors">
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
