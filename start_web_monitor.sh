#!/bin/bash
# DCMMS技能性能监控Web界面启动脚本

echo "🚀 启动DCMMS技能性能监控Web界面..."
echo "=========================================="

# 激活虚拟环境
source venv/bin/activate

# 检查端口是否被占用
PORT=8080
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  端口 $PORT 已被占用，尝试使用 8081..."
    PORT=8081
fi

# 启动Web服务器
echo "📡 启动Web服务器在端口: $PORT"
echo "🌐 访问地址: http://localhost:$PORT"
echo "📊 API端点:"
echo "  http://localhost:$PORT/           - 主监控面板"
echo "  http://localhost:$PORT/api/health - 系统健康状态"
echo "  http://localhost:$PORT/api/metrics - 性能指标"
echo "  http://localhost:$PORT/api/recent - 最近性能数据"
echo "=========================================="
echo "按 Ctrl+C 停止服务器"
echo ""

# 启动服务器
python web_monitor.py $PORT