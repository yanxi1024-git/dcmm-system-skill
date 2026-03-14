#!/usr/bin/env python3
"""
轻量级DCMMS技能性能监控Web界面
简化版本，避免浏览器卡顿
"""

import json
import sqlite3
import redis
import os
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser

class SimpleDCMMSMonitor:
    def __init__(self, host='localhost', port=8081):
        self.host = host
        self.port = port
        
        # 数据库连接
        self.db_path = "data/dcmm_system.db"
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    def get_system_status(self):
        """获取系统状态（简化版）"""
        try:
            # Redis状态
            redis_info = self.redis_client.info()
            
            # SQLite状态
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            conn.close()
            
            # 性能数据
            perf_keys = self.redis_client.keys("dcmm:performance:*")
            response_times = []
            token_usages = []
            cache_hits = []
            
            for key in perf_keys[-20:]:
                key_str = key.decode('utf-8')
                value = self.redis_client.get(key)
                
                if value:
                    if "response_time" in key_str:
                        response_times.append(float(value))
                    elif "token_usage" in key_str:
                        token_usages.append(int(value))
                    elif "cache_hit" in key_str:
                        cache_hits.append(int(value))
            
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "redis_memory_kb": redis_info.get('used_memory', 0) / 1024,
                    "redis_clients": redis_info.get('connected_clients', 0),
                    "sqlite_tables": table_count,
                    "sqlite_size_kb": os.path.getsize(self.db_path) / 1024
                },
                "performance": {
                    "response_time_avg": sum(response_times) / len(response_times) if response_times else 0,
                    "response_time_count": len(response_times),
                    "token_usage_avg": sum(token_usages) / len(token_usages) if token_usages else 0,
                    "cache_hit_rate": (sum(cache_hits) / len(cache_hits)) * 100 if cache_hits else 0,
                    "total_queries": len(cache_hits) if cache_hits else 0
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def generate_simple_html(self, data):
        """生成简化HTML"""
        status = data.get("status", "unknown")
        system = data.get("system", {})
        perf = data.get("performance", {})
        
        # 状态颜色
        status_color = "#10B981" if status == "healthy" else "#EF4444"
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DCMMS监控 - 轻量版</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f8fafc;
            color: #1e293b;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .status-badge {{
            display: inline-block;
            padding: 5px 15px;
            background: {status_color};
            color: white;
            border-radius: 20px;
            font-weight: bold;
            margin-top: 10px;
        }}
        .dashboard {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .card h3 {{
            margin-top: 0;
            color: #475569;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }}
        .metric {{
            margin: 15px 0;
        }}
        .metric-label {{
            font-size: 0.9rem;
            color: #64748b;
            margin-bottom: 5px;
        }}
        .metric-value {{
            font-size: 1.8rem;
            font-weight: bold;
            color: #1e293b;
        }}
        .metric-unit {{
            font-size: 1rem;
            color: #94a3b8;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #64748b;
            font-size: 0.9rem;
        }}
        .refresh-btn {{
            background: #3b82f6;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1rem;
            margin: 10px 0;
        }}
        .refresh-btn:hover {{
            background: #2563eb;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 DCMMS技能监控</h1>
            <p>轻量级性能监控面板</p>
            <div class="status-badge">{status.upper()}</div>
        </div>
        
        <div class="dashboard">
            <div class="card">
                <h3>🏥 系统状态</h3>
                <div class="metric">
                    <div class="metric-label">Redis内存</div>
                    <div class="metric-value">{system.get('redis_memory_kb', 0):.1f}<span class="metric-unit"> KB</span></div>
                </div>
                <div class="metric">
                    <div class="metric-label">Redis客户端</div>
                    <div class="metric-value">{system.get('redis_clients', 0)}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">SQLite表</div>
                    <div class="metric-value">{system.get('sqlite_tables', 0)}</div>
                </div>
            </div>
            
            <div class="card">
                <h3>⚡ 响应性能</h3>
                <div class="metric">
                    <div class="metric-label">平均响应时间</div>
                    <div class="metric-value">{perf.get('response_time_avg', 0):.1f}<span class="metric-unit"> ms</span></div>
                </div>
                <div class="metric">
                    <div class="metric-label">响应次数</div>
                    <div class="metric-value">{perf.get('response_time_count', 0)}</div>
                </div>
            </div>
            
            <div class="card">
                <h3>💰 Token效率</h3>
                <div class="metric">
                    <div class="metric-label">平均Token使用</div>
                    <div class="metric-value">{perf.get('token_usage_avg', 0):.0f}<span class="metric-unit"> tokens</span></div>
                </div>
            </div>
            
            <div class="card">
                <h3>📦 缓存性能</h3>
                <div class="metric">
                    <div class="metric-label">缓存命中率</div>
                    <div class="metric-value">{perf.get('cache_hit_rate', 0):.1f}<span class="metric-unit"> %</span></div>
                </div>
                <div class="metric">
                    <div class="metric-label">总查询数</div>
                    <div class="metric-value">{perf.get('total_queries', 0)}</div>
                </div>
            </div>
        </div>
        
        <div style="text-align: center;">
            <button class="refresh-btn" onclick="location.reload()">🔄 刷新数据</button>
            <p style="color: #64748b; margin-top: 10px;">
                最后更新: {data.get('timestamp', '')}
            </p>
        </div>
        
        <div class="footer">
            <p>DCMMS技能监控 | 轻量版 | 自动刷新: 30秒</p>
        </div>
    </div>
    
    <script>
        // 自动刷新
        setTimeout(() => location.reload(), 30000);
        
        // 键盘快捷键
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'r' || e.key === 'R') location.reload();
            if (e.key === 'f' || e.key === 'F') document.querySelector('.refresh-btn').click();
        }});
    </script>
</body>
</html>"""
        
        return html
    
    def start_server(self):
        """启动服务器"""
        class SimpleHandler(BaseHTTPRequestHandler):
            monitor = self
            
            def do_GET(self):
                if self.path == '/':
                    # 获取数据并生成HTML
                    data = self.monitor.get_system_status()
                    html = self.monitor.generate_simple_html(data)
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(html.encode('utf-8'))
                
                elif self.path == '/api':
                    # JSON API
                    data = self.monitor.get_system_status()
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
                
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'404 Not Found')
            
            def log_message(self, format, *args):
                # 禁用日志
                pass
        
        # 创建服务器
        server = HTTPServer((self.host, self.port), SimpleHandler)
        SimpleHandler.monitor = self
        
        print(f"轻量级监控服务器启动: http://{self.host}:{self.port}")
        print("按 Ctrl+C 停止")
        
        # 尝试打开浏览器
        try:
            webbrowser.open(f"http://{self.host}:{self.port}")
        except:
            print(f"请手动访问: http://{self.host}:{self.port}")
        
        # 启动服务器
        server.serve_forever()

def main():
    """主函数"""
    import sys
    
    port = 8081  # 使用不同端口避免冲突
    
    # 检查端口是否可用
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('localhost', port))
        sock.close()
    except socket.error:
        print(f"端口 {port} 已被占用，尝试 8082...")
        port = 8082
    
    monitor = SimpleDCMMSMonitor(port=port)
    
    print("=" * 50)
    print("DCMMS技能轻量级监控面板")
    print("=" * 50)
    print(f"地址: http://localhost:{port}")
    print("特点: 轻量快速，避免卡顿")
    print("=" * 50)
    
    try:
        monitor.start_server()
    except KeyboardInterrupt:
        print("\n服务器已停止")

if __name__ == "__main__":
    main()