#!/usr/bin/env python3
"""
DCMMS技能性能监控Web界面
提供实时性能数据可视化
"""

import json
import time
import sqlite3
import redis
import os
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import webbrowser

class DCMMSWebMonitor:
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.running = False
        
        # 数据库连接
        self.db_path = "data/dcmm_system.db"
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        
        # 性能数据缓存
        self.performance_cache = {
            "last_update": None,
            "system_health": {},
            "performance_metrics": {},
            "recent_data": []
        }
        
        # 确保数据目录存在
        os.makedirs("data/performance/web", exist_ok=True)
    
    def get_system_health(self):
        """获取系统健康状态"""
        try:
            # Redis状态
            redis_info = self.redis_client.info()
            
            # SQLite状态
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取表统计
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            # 获取数据库大小
            db_size = os.path.getsize(self.db_path) / 1024
            
            conn.close()
            
            # 记忆文件状态
            memory_dir = Path("/home/yan/.openclaw/workspace/memory")
            memory_file_count = 0
            memory_total_size = 0
            
            if memory_dir.exists():
                memory_files = list(memory_dir.glob("*.md"))
                memory_file_count = len(memory_files)
                memory_total_size = sum(f.stat().st_size for f in memory_files) / 1024
            
            health_data = {
                "redis": {
                    "memory_used_kb": redis_info.get('used_memory', 0) / 1024,
                    "connected_clients": redis_info.get('connected_clients', 0),
                    "uptime_seconds": redis_info.get('uptime_in_seconds', 0),
                    "instantaneous_ops_per_sec": redis_info.get('instantaneous_ops_per_sec', 0),
                    "status": "healthy"
                },
                "sqlite": {
                    "table_count": table_count,
                    "database_size_kb": db_size,
                    "connection_status": "healthy"
                },
                "memory_files": {
                    "file_count": memory_file_count,
                    "total_size_kb": memory_total_size,
                    "latest_file": max(memory_files, key=lambda f: f.stat().st_mtime).name if memory_files else None
                },
                "timestamp": datetime.now().isoformat()
            }
            
            return health_data
            
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_performance_metrics(self):
        """获取性能指标"""
        try:
            # 从Redis获取性能数据
            response_times = []
            token_usages = []
            cache_hits = []
            
            # 获取最近的性能键
            perf_keys = self.redis_client.keys("dcmm:performance:*")
            for key in perf_keys[-20:]:  # 只检查最近20个
                key_str = key.decode('utf-8')
                value = self.redis_client.get(key)
                
                if value:
                    if "response_time" in key_str:
                        response_times.append(float(value))
                    elif "token_usage" in key_str:
                        token_usages.append(int(value))
                    elif "cache_hit" in key_str:
                        cache_hits.append(int(value))
            
            # 计算指标
            metrics = {
                "response_time": {
                    "average": sum(response_times) / len(response_times) if response_times else 0,
                    "min": min(response_times) if response_times else 0,
                    "max": max(response_times) if response_times else 0,
                    "count": len(response_times),
                    "unit": "ms"
                },
                "token_usage": {
                    "average": sum(token_usages) / len(token_usages) if token_usages else 0,
                    "total": sum(token_usages),
                    "count": len(token_usages),
                    "unit": "tokens"
                },
                "cache_performance": {
                    "hit_rate": (sum(cache_hits) / len(cache_hits)) * 100 if cache_hits else 0,
                    "hit_count": sum(cache_hits),
                    "query_count": len(cache_hits),
                    "unit": "%"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            return metrics
            
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_recent_performance_data(self, limit=10):
        """获取最近的性能数据"""
        try:
            # 检查是否有实时监控数据文件
            realtime_dir = Path("data/performance/realtime")
            recent_files = []
            
            if realtime_dir.exists():
                json_files = list(realtime_dir.glob("*.json"))
                json_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                
                for file_path in json_files[:5]:  # 只读取最近5个文件
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if "performance_history" in data:
                                recent_files.append({
                                    "file": file_path.name,
                                    "data_points": len(data["performance_history"]),
                                    "timestamp": data.get("snapshot_time", "")
                                })
                    except:
                        continue
            
            # 从Redis获取实时数据
            recent_data = []
            perf_keys = self.redis_client.keys("dcmm:performance:*")
            
            for key in perf_keys[-limit:]:
                key_str = key.decode('utf-8')
                value = self.redis_client.get(key)
                
                if value:
                    metric_type = "unknown"
                    if "response_time" in key_str:
                        metric_type = "response_time"
                    elif "token_usage" in key_str:
                        metric_type = "token_usage"
                    elif "cache_hit" in key_str:
                        metric_type = "cache_hit"
                    
                    recent_data.append({
                        "metric": metric_type,
                        "value": float(value) if metric_type == "response_time" else int(value),
                        "timestamp": datetime.fromtimestamp(int(key_str.split(":")[-1])).isoformat() if ":" in key_str else datetime.now().isoformat()
                    })
            
            return {
                "recent_files": recent_files,
                "recent_metrics": recent_data[-limit:],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def update_cache(self):
        """更新缓存数据"""
        self.performance_cache = {
            "last_update": datetime.now().isoformat(),
            "system_health": self.get_system_health(),
            "performance_metrics": self.get_performance_metrics(),
            "recent_data": self.get_recent_performance_data(20)
        }
        
        # 保存到文件
        cache_file = f"data/performance/web/cache_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.performance_cache, f, ensure_ascii=False, indent=2)
        
        return self.performance_cache
    
    def generate_html(self):
        """生成HTML页面"""
        data = self.performance_cache
        
        # 系统健康状态
        health = data.get("system_health", {})
        metrics = data.get("performance_metrics", {})
        recent = data.get("recent_data", {})
        
        # 构建HTML
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DCMMS技能性能监控面板</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
            color: white;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .header p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .dashboard {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }}
        
        .card:hover {{
            transform: translateY(-5px);
        }}
        
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }}
        
        .card-title {{
            font-size: 1.3rem;
            font-weight: 600;
            color: #2d3748;
        }}
        
        .card-status {{
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 500;
        }}
        
        .status-healthy {{
            background: #c6f6d5;
            color: #22543d;
        }}
        
        .status-warning {{
            background: #fed7d7;
            color: #742a2a;
        }}
        
        .metric {{
            margin-bottom: 15px;
        }}
        
        .metric-label {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-size: 0.95rem;
            color: #4a5568;
        }}
        
        .metric-value {{
            font-size: 1.8rem;
            font-weight: 700;
            color: #2d3748;
        }}
        
        .metric-unit {{
            font-size: 0.9rem;
            color: #718096;
            margin-left: 5px;
        }}
        
        .progress-bar {{
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 5px;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #4299e1, #667eea);
            border-radius: 4px;
            transition: width 0.5s ease;
        }}
        
        .recent-data {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }}
        
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        
        .data-table th {{
            text-align: left;
            padding: 12px 15px;
            background: #f7fafc;
            border-bottom: 2px solid #e2e8f0;
            color: #4a5568;
            font-weight: 600;
        }}
        
        .data-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        .data-table tr:hover {{
            background: #f7fafc;
        }}
        
        .footer {{
            text-align: center;
            color: white;
            margin-top: 30px;
            opacity: 0.8;
            font-size: 0.9rem;
        }}
        
        .refresh-btn {{
            background: linear-gradient(135deg, #4299e1, #667eea);
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 25px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: block;
            margin: 20px auto;
        }}
        
        .refresh-btn:hover {{
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }}
        
        .timestamp {{
            font-size: 0.9rem;
            color: #718096;
            text-align: center;
            margin-top: 10px;
        }}
        
        @media (max-width: 768px) {{
            .dashboard {{
                grid-template-columns: 1fr;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 DCMMS技能性能监控面板</h1>
            <p>实时监控动态上下文记忆管理系统的性能表现</p>
        </div>
        
        <div class="dashboard">
            <!-- 系统健康状态卡片 -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">🏥 系统健康状态</div>
                    <div class="card-status status-healthy">运行正常</div>
                </div>
                """
        
        # 添加Redis状态
        if "redis" in health and "error" not in health:
            redis_mem = health["redis"].get("memory_used_kb", 0)
            html += f"""
                <div class="metric">
                    <div class="metric-label">
                        <span>Redis内存使用</span>
                        <span>{redis_mem:.1f} KB</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {min(redis_mem / 5000 * 100, 100)}%"></div>
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label">
                        <span>Redis连接客户端</span>
                        <span>{health["redis"].get("connected_clients", 0)}</span>
                    </div>
                </div>
            """
        
        # 添加SQLite状态
        if "sqlite" in health and "error" not in health:
            html += f"""
                <div class="metric">
                    <div class="metric-label">
                        <span>SQLite表数量</span>
                        <span>{health["sqlite"].get("table_count", 0)}</span>
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label">
                        <span>SQLite数据库大小</span>
                        <span>{health["sqlite"].get("database_size_kb", 0):.1f} KB</span>
                    </div>
                </div>
            """
        
        html += """
            </div>
            
            <!-- 响应时间性能卡片 -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">⚡ 响应时间性能</div>
                    <div class="card-status status-healthy">优秀</div>
                </div>
        """
        
        if "response_time" in metrics and "error" not in metrics:
            resp_avg = metrics["response_time"].get("average", 0)
            status_class = "status-healthy" if resp_avg < 1000 else "status-warning"
            
            html += f"""
                <div class="metric">
                    <div class="metric-label">
                        <span>平均响应时间</span>
                        <span>{resp_avg:.1f} <span class="metric-unit">ms</span></span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {min(resp_avg / 2000 * 100, 100)}%"></div>
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label">
                        <span>最快响应</span>
                        <span>{metrics["response_time"].get("min", 0):.1f} <span class="metric-unit">ms</span></span>
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label">
                        <span>最慢响应</span>
                        <span>{metrics["response_time"].get("max", 0):.1f} <span class="metric-unit">ms</span></span>
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label">
                        <span>响应次数</span>
                        <span>{metrics["response_time"].get("count", 0)}</span>
                    </div>
                </div>
            """
        
        html += """
            </div>
            
            <!-- Token使用效率卡片 -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">💰 Token使用效率</div>
                    <div class="card-status status-healthy">优秀</div>
                </div>
        """
        
        if "token_usage" in metrics and "error" not in metrics:
            token_avg = metrics["token_usage"].get("average", 0)
            
            html += f"""
                <div class="metric">
                    <div class="metric-label">
                        <span>平均Token使用</span>
                        <span>{token_avg:.0f} <span class="metric-unit">tokens</span></span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {min(token_avg / 500 * 100, 100)}%"></div>
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label">
                        <span>总Token使用</span>
                        <span>{metrics["token_usage"].get("total", 0):.0f} <span class="metric-unit">tokens</span></span>
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label">
                        <span>查询次数</span>
                        <span>{metrics["token_usage"].get("count", 0)}</span>
                    </div>
                </div>
            """
        
        html += """
            </div>
            
            <!-- 缓存性能卡片 -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">📦 缓存性能</div>
                    <div class="card-status status-warning">需要优化</div>
                </div>
        """
        
        if "cache_performance" in metrics and "error" not in metrics:
            cache_rate = metrics["cache_performance"].get("hit_rate", 0)
            status_class = "status-healthy" if cache_rate > 60 else "status-warning" if cache_rate > 40 else "status-warning"
            
            html += f"""
                <div class="metric">
                    <div class="metric-label">
                        <span>缓存命中率</span>
                        <span>{cache_rate:.1f} <span class="metric-unit">%</span></span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {cache_rate}%"></div>
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label">
                        <span>命中次数</span>
                        <span>{metrics["cache_performance"].get("hit_count", 0)}</span>
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label">
                        <span>查询次数</span>
                        <span>{metrics["cache_performance"].get("query_count", 0)}</span>
                    </div>
                </div>
            """
        
        html += """
            </div>
        </div>
        
        <!-- 最近数据表格 -->
        <div class="recent-data">
            <div class="card-header">
                <div class="card-title">📊 最近性能数据</div>
            </div>
            
            <table class="data-table">
                <thead>
                    <tr>
                        <th>指标类型</th>
                        <th>数值</th>
                        <th>时间戳</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # 添加最近数据行
        if "recent_metrics" in recent:
            for item in recent["recent_metrics"][:10]:  # 只显示最近10条
                metric_type = item.get("metric", "unknown")
                value = item.get("value", 0)
                timestamp = item.get("timestamp", "")
                
                # 格式化显示
                display_type = {
                    "response_time": "响应时间",
                    "token_usage": "Token使用",
                    "cache_hit": "缓存命中"
                }.get(metric_type, metric_type)
                
                display_value = f"{value:.1f}ms" if metric_type == "response_time" else f"{value} tokens" if metric_type == "token_usage" else f"{value}"
                
                html += f"""
                    <tr>
                        <td>{display_type}</td>
                        <td>{display_value}</td>
                        <td>{timestamp}</td>
                    </tr>
                """
        
        html += """
                </tbody>
            </table>
        </div>
        
        <button class="refresh-btn" onclick="location.reload()">🔄 刷新数据</button>
        
        <div class="timestamp">
            最后更新: {data.get("last_update", "未知")}
        </div>
        
        <div class="footer">
            <p>DCMMS技能性能监控系统 | 数据每30秒自动更新 | 如有问题请检查系统连接</p>
        </div>
    </div>
    
    <script>
        // 自动刷新页面（每30秒）
        setTimeout(function() {{
            location.reload();
        }}, 30000);
        
        // 添加键盘快捷键
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'r' || e.key === 'R') {{
                location.reload();
            }}
            if (e.key === 'f' || e.key === 'F') {{
                document.querySelector('.refresh-btn').click();
            }}
        }});
    </script>
</body>
</html>
        """
        
        return html
    
    def start_web_server(self):
        """启动Web服务器"""
        class DCMMSRequestHandler(BaseHTTPRequestHandler):
            monitor = self
            
            def do_GET(self):
                if self.path == '/':
                    # 更新缓存数据
                    self.monitor.update_cache()
                    
                    # 生成HTML响应
                    html_content = self.monitor.generate_html()
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(html_content.encode('utf-8'))
                
                elif self.path == '/api/health':
                    # API端点：系统健康状态
                    health_data = self.monitor.get_system_health()
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(health_data, ensure_ascii=False).encode('utf-8'))
                
                elif self.path == '/api/metrics':
                    # API端点：性能指标
                    metrics_data = self.monitor.get_performance_metrics()
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(metrics_data, ensure_ascii=False).encode('utf-8'))
                
                elif self.path == '/api/recent':
                    # API端点：最近数据
                    recent_data = self.monitor.get_recent_performance_data(20)
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(recent_data, ensure_ascii=False).encode('utf-8'))
                
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'404 Not Found')
            
            def log_message(self, format, *args):
                # 禁用默认日志
                pass
        
        # 创建服务器
        self.server = HTTPServer((self.host, self.port), DCMMSRequestHandler)
        DCMMSRequestHandler.monitor = self
        
        print(f"DCMMS性能监控Web服务器启动在: http://{self.host}:{self.port}")
        print("按 Ctrl+C 停止服务器")
        
        # 尝试打开浏览器
        try:
            webbrowser.open(f"http://{self.host}:{self.port}")
        except:
            print(f"请手动打开浏览器访问: http://{self.host}:{self.port}")
        
        # 启动服务器
        self.running = True
        self.server.serve_forever()
    
    def start(self):
        """启动监控Web服务器"""
        self.server_thread = threading.Thread(target=self.start_web_server, daemon=True)
        self.server_thread.start()
        return True
    
    def stop(self):
        """停止监控Web服务器"""
        if self.server:
            self.server.shutdown()
            self.running = False
        return True

def main():
    """主函数"""
    import sys
    
    # 解析命令行参数
    host = 'localhost'
    port = 8080
    
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"错误: 端口号必须是数字")
            return
    
    if len(sys.argv) > 2:
        host = sys.argv[2]
    
    # 创建并启动监控器
    monitor = DCMMSWebMonitor(host=host, port=port)
    
    print("=" * 60)
    print("DCMMS技能性能监控Web界面")
    print("=" * 60)
    print(f"服务器地址: http://{host}:{port}")
    print("可用端点:")
    print("  /           - 主监控面板 (HTML)")
    print("  /api/health - 系统健康状态 (JSON)")
    print("  /api/metrics - 性能指标 (JSON)")
    print("  /api/recent - 最近性能数据 (JSON)")
    print("=" * 60)
    
    try:
        monitor.start_web_server()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        monitor.stop()

if __name__ == "__main__":
    main()