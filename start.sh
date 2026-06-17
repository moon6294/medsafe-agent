#!/bin/bash

# 进入项目根目录
cd "$(dirname "$0")"

echo "🚀 启动 MedSafe Agent 服务..."

# 1. 杀死可能占用端口的旧进程（可选）
echo "🔄 清理旧进程..."
pkill -f "python backend_api.py" 2>/dev/null
pkill -f "vite" 2>/dev/null

# 2. 启动后端（后台运行，日志输出到 backend.log）
echo "📡 启动后端服务 (端口 8000)..."
nohup python backend_api.py > backend.log 2>&1 &

# 3. 启动前端（后台运行，日志输出到 frontend.log）
echo "💻 启动前端服务 (端口 5173)..."
cd frontend-react
nohup npm run dev -- --host > frontend.log 2>&1 &

echo "✅ 服务已启动！"
echo "📋 查看后端日志: tail -f backend.log"
echo "📋 查看前端日志: tail -f frontend.log"
echo "🌐 访问前端: http://localhost:5173 (需 SSH 隧道映射)"
echo "🛑 停止服务: ./stop.sh"