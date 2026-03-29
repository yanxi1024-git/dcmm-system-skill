#!/bin/bash
# DCMMS技能轻量级监控启动脚本

echo "🚀 启动DCMMS技能轻量级监控..."
echo "=========================================="

# 激活虚拟环境
source venv/bin/activate

# 检查并停止可能冲突的进程
echo "🛑 检查并停止可能冲突的进程..."
pkill -f "web_monitor.py 8080" 2>/dev/null || true
pkill -f "web_monitor_simple.py" 2>/dev/null || true

# 等待一下
sleep 1

# 启动轻量级监控
echo "📡 启动轻量级监控服务器..."
echo "🌐 访问地址: http://localhost:8081"
echo "📊 特点: 轻量快速，避免卡顿"
echo "🔄 自动刷新: 每30秒"
echo "🎯 键盘快捷键: R键刷新，F键点击刷新按钮"
echo "=========================================="
echo "按 Ctrl+C 停止服务器"
echo ""

# 启动服务器
python web_monitor_simple.py