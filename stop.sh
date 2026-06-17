#!/bin/bash
echo "🛑 停止 MedSafe Agent 服务..."
pkill -f "python backend_api.py"
pkill -f "vite"
echo "✅ 已停止"