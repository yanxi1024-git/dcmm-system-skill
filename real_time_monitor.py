#!/usr/bin/env python3
"""
DCMMS实时监控器
在实际对话中收集性能数据
"""

import time
import json
import sqlite3
import redis
from datetime import datetime
from pathlib import Path
import threading
import queue
import sys
from typing import Dict, List, Any

class RealTimeDCMMSMonitor:
    """实时DCMMS监控器"""
    
    def __init__(self):
        self.db_path = "data/dcmm_system.db"
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.data_queue = queue.Queue()
        self.running = False
        self.monitor_thread = None
        
        # 性能指标
        self.metrics = {
            "conversation_turns": 0,
            "total_processing_time": 0,
            "avg_turn_time": 0,
            "tokens_processed": 0,
            "storage_accesses": {"redis": 0, "sqlite": 0, "files": 0},
            "extraction_events": 0,
            "rebuild_events": 0,
            "errors": 0
        }
        
        # 创建监控表
        self._create_monitoring_tables()
        
    def _create_monitoring_tables(self):
        """创建监控数据库表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 对话轮次监控表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_monitor (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    turn_number INTEGER NOT NULL,
                    query_text TEXT,
                    processing_time_ms REAL,
                    tokens_used INTEGER,
                    extraction_success BOOLEAN,
                    rebuild_success BOOLEAN,
                    storage_hits TEXT,
                    error_message TEXT
                )
            ''')
            
            # 性能聚合表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_aggregates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    interval_minutes INTEGER NOT NULL,
                    total_turns INTEGER NOT NULL,
                    avg_processing_time_ms REAL NOT NULL,
                    total_tokens_used INTEGER NOT NULL,
                    extraction_success_rate REAL NOT NULL,
                    rebuild_success_rate REAL NOT NULL,
                    storage_distribution TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            print("✅ 监控数据库表创建完成")
        except Exception as e:
            print(f"❌ 创建监控表失败: {e}")
    
    def start_monitoring(self):
        """开始实时监控"""
        if self.running:
            print("⚠️ 监控器已在运行")
            return
            
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print("🚀 DCMMS实时监控器已启动")
        
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("🛑 DCMMS实时监控器已停止")
        
    def record_conversation_turn(self, query: str, processing_time: float, 
                                tokens_used: int, extraction_result: Dict, 
                                rebuild_result: Dict):
        """记录一次对话轮次"""
        turn_data = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "processing_time": processing_time,
            "tokens_used": tokens_used,
            "extraction_success": extraction_result.get("success", False),
            "rebuild_success": rebuild_result.get("success", False),
            "storage_hits": rebuild_result.get("storage_stats", {}),
            "error": None
        }
        
        self.data_queue.put(turn_data)
        
        # 更新实时指标
        self.metrics["conversation_turns"] += 1
        self.metrics["total_processing_time"] += processing_time
        self.metrics["avg_turn_time"] = (
            self.metrics["total_processing_time"] / self.metrics["conversation_turns"]
        )
        self.metrics["tokens_processed"] += tokens_used
        
        if extraction_result.get("success", False):
            self.metrics["extraction_events"] += 1
        if rebuild_result.get("success", False):
            self.metrics["rebuild_events"] += 1
            
        # 更新存储访问统计
        storage_stats = rebuild_result.get("storage_stats", {})
        for storage_type in ["redis", "sqlite", "files"]:
            if storage_stats.get(storage_type, {}).get("hit", False):
                self.metrics["storage_accesses"][storage_type] += 1
    
    def _monitoring_loop(self):
        """监控循环 - 处理队列中的数据"""
        last_aggregate_time = time.time()
        
        while self.running:
            try:
                # 处理队列中的数据
                while not self.data_queue.empty():
                    turn_data = self.data_queue.get_nowait()
                    self._save_turn_to_db(turn_data)
                
                # 每分钟聚合一次数据
                current_time = time.time()
                if current_time - last_aggregate_time >= 60:  # 60秒
                    self._aggregate_performance_data()
                    last_aggregate_time = current_time
                    
                time.sleep(0.1)  # 避免CPU占用过高
                
            except Exception as e:
                print(f"监控循环错误: {e}")
                self.metrics["errors"] += 1
                
    def _save_turn_to_db(self, turn_data: Dict):
        """保存对话轮次到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO conversation_monitor 
                (timestamp, turn_number, query_text, processing_time_ms, 
                 tokens_used, extraction_success, rebuild_success, 
                 storage_hits, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                turn_data["timestamp"],
                self.metrics["conversation_turns"],
                turn_data["query"][:500],  # 限制长度
                turn_data["processing_time"] * 1000,  # 转换为毫秒
                turn_data["tokens_used"],
                turn_data["extraction_success"],
                turn_data["rebuild_success"],
                json.dumps(turn_data["storage_hits"]),
                turn_data["error"]
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"保存对话轮次失败: {e}")
            
    def _aggregate_performance_data(self):
        """聚合性能数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取最近一分钟的数据
            one_minute_ago = (datetime.now().timestamp() - 60) * 1000
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_turns,
                    AVG(processing_time_ms) as avg_time,
                    SUM(tokens_used) as total_tokens,
                    AVG(CASE WHEN extraction_success THEN 1.0 ELSE 0.0 END) as extraction_rate,
                    AVG(CASE WHEN rebuild_success THEN 1.0 ELSE 0.0 END) as rebuild_rate
                FROM conversation_monitor 
                WHERE timestamp >= datetime(?, 'unixepoch')
            ''', (one_minute_ago,))
            
            result = cursor.fetchone()
            
            if result and result[0] > 0:
                cursor.execute('''
                    INSERT INTO performance_aggregates 
                    (timestamp, interval_minutes, total_turns, avg_processing_time_ms,
                     total_tokens_used, extraction_success_rate, rebuild_success_rate,
                     storage_distribution)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    1,  # 1分钟间隔
                    result[0],
                    result[1] or 0,
                    result[2] or 0,
                    result[3] or 0,
                    result[4] or 0,
                    json.dumps(self.metrics["storage_accesses"])
                ))
                
                conn.commit()
                
            conn.close()
        except Exception as e:
            print(f"聚合性能数据失败: {e}")
    
    def get_realtime_dashboard(self) -> Dict:
        """获取实时仪表板数据"""
        # 计算成功率
        extraction_success_rate = (
            self.metrics["extraction_events"] / self.metrics["conversation_turns"] * 100
            if self.metrics["conversation_turns"] > 0 else 0
        )
        
        rebuild_success_rate = (
            self.metrics["rebuild_events"] / self.metrics["conversation_turns"] * 100
            if self.metrics["conversation_turns"] > 0 else 0
        )
        
        # 计算存储分布
        total_storage_accesses = sum(self.metrics["storage_accesses"].values())
        storage_distribution = {}
        if total_storage_accesses > 0:
            for storage_type, accesses in self.metrics["storage_accesses"].items():
                storage_distribution[storage_type] = accesses / total_storage_accesses * 100
        
        # 系统健康检查
        system_health = self._check_system_health()
        
        return {
            "conversation_metrics": {
                "total_turns": self.metrics["conversation_turns"],
                "avg_turn_time_ms": self.metrics["avg_turn_time"] * 1000,
                "tokens_processed": self.metrics["tokens_processed"],
                "tokens_per_turn": (
                    self.metrics["tokens_processed"] / self.metrics["conversation_turns"]
                    if self.metrics["conversation_turns"] > 0 else 0
                )
            },
            "success_rates": {
                "extraction": extraction_success_rate,
                "rebuild": rebuild_success_rate,
                "overall": min(extraction_success_rate, rebuild_success_rate)
            },
            "storage_performance": {
                "distribution": storage_distribution,
                "total_accesses": total_storage_accesses
            },
            "system_health": system_health,
            "errors": self.metrics["errors"]
        }
    
    def _check_system_health(self) -> Dict:
        """检查系统健康状态"""
        health = {
            "redis": {"connected": False, "latency_ms": 0},
            "sqlite": {"connected": False, "size_kb": 0},
            "memory_files": {"exists": False, "count": 0}
        }
        
        # 检查Redis
        try:
            start = time.time()
            self.redis_client.ping()
            health["redis"]["connected"] = True
            health["redis"]["latency_ms"] = (time.time() - start) * 1000
            health["redis"]["memory_used_kb"] = (
                int(self.redis_client.info()['used_memory']) / 1024
            )
        except:
            health["redis"]["connected"] = False
            
        # 检查SQLite
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            health["sqlite"]["connected"] = True
            health["sqlite"]["table_count"] = cursor.fetchone()[0]
            
            # 数据库大小
            db_size = Path(self.db_path).stat().st_size
            health["sqlite"]["size_kb"] = db_size / 1024
            conn.close()
        except:
            health["sqlite"]["connected"] = False
            
        # 检查记忆文件
        memory_dir = Path("/home/yan/.openclaw/workspace/memory")
        if memory_dir.exists():
            memory_files = list(memory_dir.glob("*.md"))
            health["memory_files"]["exists"] = len(memory_files) > 0
            health["memory_files"]["count"] = len(memory_files)
            
            # 最新文件
            if memory_files:
                latest_file = max(memory_files, key=lambda f: f.stat().st_mtime)
                health["memory_files"]["latest"] = latest_file.name
                health["memory_files"]["latest_size_kb"] = latest_file.stat().st_size / 1024
        
        return health
    
    def generate_monitoring_report(self, duration_minutes: int = None) -> str:
        """生成监控报告"""
        dashboard = self.get_realtime_dashboard()
        
        if duration_minutes:
            title = f"DCMMS监控报告 - 最近{duration_minutes}分钟"
        else:
            title = f"DCMMS实时监控报告 - 累计{self.metrics['conversation_turns']}轮对话"
        
        report = f"""
# {title}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 对话性能指标
- **总对话轮次**: {dashboard['conversation_metrics']['total_turns']}
- **平均轮次时间**: {dashboard['conversation_metrics']['avg_turn_time_ms']:.1f}ms
- **总处理Token数**: {dashboard['conversation_metrics']['tokens_processed']}
- **平均每轮Token数**: {dashboard['conversation_metrics']['tokens_per_turn']:.1f}

## 🎯 成功率指标
- **信息提取成功率**: {dashboard['success_rates']['extraction']:.1f}%
- **上下文重建成功率**: {dashboard['success_rates']['rebuild']:.1f}%
- **整体成功率**: {dashboard['success_rates']['overall']:.1f}%

## 💾 存储层性能
"""
        
        for storage_type, percentage in dashboard['storage_performance']['distribution'].items():
            report += f"- **{storage_type}访问比例**: {percentage:.1f}%\n"
        
        report += f"- **总存储访问次数**: {dashboard['storage_performance']['total_accesses']}\n"
        
        # 系统健康状态
        health = dashboard['system_health']
        report += f"""
## 🏥 系统健康状态

### Redis
- **连接状态**: {'✅ 正常' if health['redis']['connected'] else '❌ 异常'}
- **响应延迟**: {health['redis'].get('latency_ms', 0):.1f}ms
- **内存使用**: {health['redis'].get('memory_used_kb', 0):.1f} KB

### SQLite
- **连接状态**: {'✅ 正常' if health['sqlite']['connected'] else '❌ 异常'}
- **表数量**: {health['sqlite'].get('table_count', 0)}
- **数据库大小**: {health['sqlite'].get('size_kb', 0):.1f} KB

### 记忆文件
- **存在状态**: {'✅ 存在' if health['memory_files']['exists'] else '❌ 不存在'}
- **文件数量**: {health['memory_files'].get('count', 0)}
- **最新文件**: {health['memory_files'].get('latest', '无')}
- **最新文件大小**: {health['memory_files'].get('latest_size_kb', 0):.1f} KB

## ⚠️ 错误统计
- **总错误数**: {dashboard['errors']}
- **错误率**: {dashboard['errors'] / max(1, self.metrics['conversation_turns']) * 100:.2f}%

## 📈 性能趋势分析
"""
        
        # 添加性能趋势分析
        if self.metrics["conversation_turns"] > 10:
            report += "- **性能稳定**: 对话轮次超过10轮，系统表现稳定\n"
        else:
            report += "- **数据不足**: 对话轮次较少，建议继续收集数据\n"
            
        if dashboard['success_rates']['overall'] > 95:
            report += "- **可靠性高**: 整体成功率超过95%，系统可靠性优秀\n"
        elif dashboard['success_rates']['overall'] > 80:
            report += "- **可靠性良好**: 整体成功率超过80%，系统可靠性良好\n"
        else:
            report += "- **可靠性待提升**: 整体成功率低于80%，需要优化\n"
            
        if dashboard['conversation_metrics']['avg_turn_time_ms'] < 1000:
            report += "- **响应速度快**: 平均响应时间低于1秒，性能优秀\n"
        else:
            report += "- **响应时间待优化**: 平均响应时间超过1秒，需要优化\n"
        
        return report

# 全局监控器实例
global_monitor = RealTimeDCMMSMonitor()

def start_dcmm_monitoring():
    """启动DCMMS监控"""
    global_monitor.start_monitoring()
    return global_monitor

def stop_dcmm_monitoring():
    """停止DCMMS监控"""
    global_monitor.stop_monitoring()

def get_dcmm_dashboard():
    """获取DCMMS仪表板数据"""
    return global_monitor.get_realtime_dashboard()

def record_dcmm_turn(query: str, processing_time: float, tokens_used: int,
                    extraction_result: Dict, rebuild_result: Dict):
    """记录DCMMS对话轮次"""
    global_monitor.record_conversation_turn(
        query, processing_time, tokens_used,
        extraction_result, rebuild_result
    )

if __name__ == "__main__":
    # 测试监控器
    monitor = RealTimeDCMMSMonitor()
    monitor.start_monitoring()
    
    print("DCMMS实时监控器测试模式")
    print("模拟对话数据收集...")
    
    try:
        # 模拟一些对话数据
        for i in range(5):
            monitor.record_conversation_turn(
                query=f"测试查询 {i+1}",
                processing_time=0.5 + i*0.1,
                tokens_used=300 + i*50,
                extraction_result={"success": True, "entities_count": 2},
                rebuild_result={
                    "success": True,
                    "context_parts": 3,
                    "storage_stats": {
                        "redis": {"hit": True},
                        "sqlite": {"hit": True},
                        "files": {"hit": False}
                    }
                }
            )
            time.sleep(0.5)
        
        # 显示监控数据
        print("\n监控数据收集完成，显示结果...")
        dashboard = monitor.get_realtime_dashboard()
        print(f"总对话轮次: {dashboard['conversation_metrics']['total_turns']}")
        print(f"平均响应时间: {dashboard['conversation_metrics']['avg_turn_time_ms']:.1f}ms")
        
        monitor.stop_monitoring()
        
    except KeyboardInterrupt:
        monitor.stop_monitoring()
        print("\n监控测试结束")
