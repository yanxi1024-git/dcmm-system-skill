#!/usr/bin/env python3
"""
实时对话监控器
持续监控DCMMS技能在对话中的性能表现
"""

import time
import json
import sqlite3
import redis
import os
import threading
from datetime import datetime
from pathlib import Path
from collections import deque

class RealtimeConversationMonitor:
    def __init__(self, check_interval=30):
        """初始化监控器"""
        self.check_interval = check_interval  # 检查间隔（秒）
        self.running = False
        
        # 数据库连接
        self.db_path = "data/dcmm_system.db"
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        
        # 性能数据队列
        self.performance_history = deque(maxlen=100)  # 保留最近100个数据点
        
        # 确保数据目录存在
        os.makedirs("data/performance/realtime", exist_ok=True)
        
        # 监控线程
        self.monitor_thread = None
        
    def start_monitoring(self):
        """开始监控"""
        if self.running:
            print("监控器已经在运行中")
            return False
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        print(f"实时对话监控器已启动，检查间隔: {self.check_interval}秒")
        return True
    
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        print("实时对话监控器已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                # 收集性能数据
                performance_data = self._collect_performance_data()
                
                # 保存到历史队列
                self.performance_history.append(performance_data)
                
                # 保存到文件（每10次检查保存一次）
                if len(self.performance_history) % 10 == 0:
                    self._save_performance_snapshot()
                
                # 打印状态更新（每5次检查打印一次）
                if len(self.performance_history) % 5 == 0:
                    self._print_status_update(performance_data)
                
            except Exception as e:
                print(f"监控循环出错: {e}")
            
            # 等待下一次检查
            time.sleep(self.check_interval)
    
    def _collect_performance_data(self):
        """收集性能数据"""
        timestamp = datetime.now()
        
        try:
            # Redis性能指标
            redis_info = self.redis_client.info()
            
            # 检查Redis中是否有新的性能数据
            response_times = []
            token_usages = []
            cache_hits = []
            
            # 获取最近的性能键
            perf_keys = self.redis_client.keys("dcmm:performance:*")
            for key in perf_keys[-10:]:  # 只检查最近10个
                key_str = key.decode('utf-8')
                value = self.redis_client.get(key)
                
                if value:
                    if "response_time" in key_str:
                        response_times.append(float(value))
                    elif "token_usage" in key_str:
                        token_usages.append(int(value))
                    elif "cache_hit" in key_str:
                        cache_hits.append(int(value))
            
            # SQLite状态
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取表统计
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            # 获取记录数量
            total_records = 0
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for table in tables:
                table_name = table[0]
                if table_name != 'sqlite_sequence':
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    total_records += count
            
            conn.close()
            
            # 记忆文件状态
            memory_dir = Path("/home/yan/.openclaw/workspace/memory")
            memory_file_count = 0
            memory_total_size = 0
            
            if memory_dir.exists():
                memory_files = list(memory_dir.glob("*.md"))
                memory_file_count = len(memory_files)
                memory_total_size = sum(f.stat().st_size for f in memory_files)
            
            # 构建性能数据
            performance_data = {
                "timestamp": timestamp.isoformat(),
                "metrics": {
                    "response_time_avg": sum(response_times) / len(response_times) if response_times else 0,
                    "response_time_count": len(response_times),
                    "token_usage_avg": sum(token_usages) / len(token_usages) if token_usages else 0,
                    "token_usage_total": sum(token_usages),
                    "cache_hit_rate": (sum(cache_hits) / len(cache_hits)) * 100 if cache_hits else 0,
                    "cache_hit_count": sum(cache_hits),
                    "cache_query_count": len(cache_hits)
                },
                "system_status": {
                    "redis": {
                        "memory_used_kb": redis_info.get('used_memory', 0) / 1024,
                        "connected_clients": redis_info.get('connected_clients', 0),
                        "instantaneous_ops_per_sec": redis_info.get('instantaneous_ops_per_sec', 0)
                    },
                    "sqlite": {
                        "table_count": table_count,
                        "total_records": total_records,
                        "database_size_kb": os.path.getsize(self.db_path) / 1024
                    },
                    "memory_files": {
                        "file_count": memory_file_count,
                        "total_size_kb": memory_total_size / 1024
                    }
                }
            }
            
            return performance_data
            
        except Exception as e:
            print(f"收集性能数据时出错: {e}")
            return {
                "timestamp": timestamp.isoformat(),
                "error": str(e),
                "metrics": {},
                "system_status": {}
            }
    
    def _save_performance_snapshot(self):
        """保存性能快照"""
        if not self.performance_history:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = f"data/performance/realtime/snapshot_{timestamp}.json"
        
        snapshot_data = {
            "snapshot_time": datetime.now().isoformat(),
            "check_interval": self.check_interval,
            "total_data_points": len(self.performance_history),
            "performance_history": list(self.performance_history),
            "summary": self._generate_summary()
        }
        
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2)
        
        print(f"性能快照已保存: {snapshot_path}")
    
    def _generate_summary(self):
        """生成性能摘要"""
        if not self.performance_history:
            return {}
        
        # 计算统计指标
        response_times = [data["metrics"].get("response_time_avg", 0) for data in self.performance_history if "metrics" in data]
        token_usages = [data["metrics"].get("token_usage_avg", 0) for data in self.performance_history if "metrics" in data]
        cache_hit_rates = [data["metrics"].get("cache_hit_rate", 0) for data in self.performance_history if "metrics" in data]
        
        summary = {
            "time_period": {
                "start": self.performance_history[0]["timestamp"],
                "end": self.performance_history[-1]["timestamp"],
                "duration_minutes": len(self.performance_history) * self.check_interval / 60
            },
            "performance_stats": {
                "response_time": {
                    "avg": sum(response_times) / len(response_times) if response_times else 0,
                    "min": min(response_times) if response_times else 0,
                    "max": max(response_times) if response_times else 0,
                    "samples": len(response_times)
                },
                "token_usage": {
                    "avg": sum(token_usages) / len(token_usages) if token_usages else 0,
                    "min": min(token_usages) if token_usages else 0,
                    "max": max(token_usages) if token_usages else 0,
                    "samples": len(token_usages)
                },
                "cache_performance": {
                    "avg_hit_rate": sum(cache_hit_rates) / len(cache_hit_rates) if cache_hit_rates else 0,
                    "min_hit_rate": min(cache_hit_rates) if cache_hit_rates else 0,
                    "max_hit_rate": max(cache_hit_rates) if cache_hit_rates else 0,
                    "samples": len(cache_hit_rates)
                }
            },
            "system_health": {
                "redis_memory_avg_kb": sum(data["system_status"].get("redis", {}).get("memory_used_kb", 0) 
                                          for data in self.performance_history if "system_status" in data) / len(self.performance_history),
                "sqlite_records_avg": sum(data["system_status"].get("sqlite", {}).get("total_records", 0) 
                                         for data in self.performance_history if "system_status" in data) / len(self.performance_history)
            }
        }
        
        return summary
    
    def _print_status_update(self, latest_data):
        """打印状态更新"""
        timestamp = datetime.fromisoformat(latest_data["timestamp"]).strftime("%H:%M:%S")
        
        metrics = latest_data.get("metrics", {})
        system_status = latest_data.get("system_status", {})
        
        print(f"\n[{timestamp}] DCMMS技能实时状态更新:")
        print(f"  📊 性能指标:")
        print(f"    响应时间: {metrics.get('response_time_avg', 0):.1f}ms ({metrics.get('response_time_count', 0)}次)")
        print(f"    Token使用: {metrics.get('token_usage_avg', 0):.0f} tokens (总计: {metrics.get('token_usage_total', 0)})")
        print(f"    缓存命中率: {metrics.get('cache_hit_rate', 0):.1f}% ({metrics.get('cache_hit_count', 0)}/{metrics.get('cache_query_count', 0)})")
        
        print(f"  🏥 系统状态:")
        if "redis" in system_status:
            redis_info = system_status["redis"]
            print(f"    Redis: {redis_info.get('memory_used_kb', 0):.1f}KB, {redis_info.get('connected_clients', 0)}客户端")
        
        if "sqlite" in system_status:
            sqlite_info = system_status["sqlite"]
            print(f"    SQLite: {sqlite_info.get('table_count', 0)}表, {sqlite_info.get('total_records', 0)}记录")
        
        print(f"  📈 历史数据点: {len(self.performance_history)}个")
    
    def get_current_status(self):
        """获取当前状态"""
        if not self.performance_history:
            return {"status": "no_data", "message": "尚未收集到性能数据"}
        
        latest_data = self.performance_history[-1]
        summary = self._generate_summary()
        
        return {
            "status": "monitoring_active",
            "latest_timestamp": latest_data["timestamp"],
            "check_interval": self.check_interval,
            "data_points": len(self.performance_history),
            "latest_metrics": latest_data.get("metrics", {}),
            "performance_summary": summary.get("performance_stats", {}),
            "system_health": summary.get("system_health", {})
        }
    
    def generate_final_report(self):
        """生成最终报告"""
        if not self.performance_history:
            return {"error": "没有可用的性能数据"}
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"data/performance/realtime/final_report_{timestamp}.md"
        
        summary = self._generate_summary()
        latest_status = self.get_current_status()
        
        # 生成Markdown报告
        report = f"""# DCMMS技能实时对话监控报告
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
监控时长: {summary['time_period']['duration_minutes']:.1f} 分钟
数据点数: {len(self.performance_history)} 个

## 📊 性能统计摘要

### 响应时间性能
- **平均响应时间**: {summary['performance_stats']['response_time']['avg']:.1f}ms
- **最快响应**: {summary['performance_stats']['response_time']['min']:.1f}ms
- **最慢响应**: {summary['performance_stats']['response_time']['max']:.1f}ms
- **样本数量**: {summary['performance_stats']['response_time']['samples']}次

### Token使用效率
- **平均Token使用**: {summary['performance_stats']['token_usage']['avg']:.0f} tokens
- **最少Token使用**: {summary['performance_stats']['token_usage']['min']:.0f} tokens
- **最多Token使用**: {summary['performance_stats']['token_usage']['max']:.0f} tokens
- **样本数量**: {summary['performance_stats']['token_usage']['samples']}次

### 缓存性能
- **平均命中率**: {summary['performance_stats']['cache_performance']['avg_hit_rate']:.1f}%
- **最低命中率**: {summary['performance_stats']['cache_performance']['min_hit_rate']:.1f}%
- **最高命中率**: {summary['performance_stats']['cache_performance']['max_hit_rate']:.1f}%
- **样本数量**: {summary['performance_stats']['cache_performance']['samples']}次

## 🏥 系统健康状态
- **Redis平均内存使用**: {summary['system_health']['redis_memory_avg_kb']:.1f} KB
- **SQLite平均记录数**: {summary['system_health']['sqlite_records_avg']:.0f} 条

## 📈 性能趋势分析

### 响应时间趋势
"""
        
        # 添加趋势分析
        response_times = [data["metrics"].get("response_time_avg", 0) for data in self.performance_history if "metrics" in data]
        if response_times:
            first_half_avg = sum(response_times[:len(response_times)//2]) / (len(response_times)//2)
            second_half_avg = sum(response_times[len(response_times)//2:]) / (len(response_times) - len(response_times)//2)
            
            trend = "稳定" if abs(first_half_avg - second_half_avg) < 100 else "上升" if second_half_avg > first_half_avg else "下降"
            
            report += f"- **整体趋势**: {trend}\n"
            report += f"- **前半段平均**: {first_half_avg:.1f}ms\n"
            report += f"- **后半段平均**: {second_half_avg:.1f}ms\n"
        
        report += f"""
### 缓存命中率趋势
"""
        
        cache_hit_rates = [data["metrics"].get("cache_hit_rate", 0) for data in self.performance_history if "metrics" in data]
        if cache_hit_rates:
            first_half_avg = sum(cache_hit_rates[:len(cache_hit_rates)//2]) / (len(cache_hit_rates)//2)
            second_half_avg = sum(cache_hit_rates[len(cache_hit_rates)//2:]) / (len(cache_hit_rates) - len(cache_hit_rates)//2)
            
            trend = "稳定" if abs(first_half_avg - second_half_avg) < 10 else "上升" if second_half_avg > first_half_avg else "下降"
            
            report += f"- **整体趋势**: {trend}\n"
            report += f"- **前半段平均**: {first_half_avg:.1f}%\n"
            report += f"- **后半段平均**: {second_half_avg:.1f}%\n"
        
        report += f"""
## 🎯 评估结论与建议

### 性能评估
"""
        
        # 基于数据生成评估
        response_avg = summary['performance_stats']['response_time']['avg']
        cache_avg = summary['performance_stats']['cache_performance']['avg_hit_rate']
        
        if response_avg < 500:
            report += "- ✅ **响应速度优秀**: 平均响应时间 < 500ms\n"
        elif response_avg < 1000:
            report += "- ⚠️ **响应速度良好**: 平均响应时间 500-1000ms\n"
        else:
            report += "- ❌ **响应速度需要优化**: 平均响应时间 > 1000ms\n"
        
        if cache_avg > 60:
            report += "- ✅ **缓存效率优秀**: 平均命中率 > 60%\n"
        elif cache_avg > 40:
            report += "- ⚠️ **缓存效率良好**: 平均命中率 40-60%\n"
        else:
            report += "- ❌ **缓存效率需要优化**: 平均命中率 < 40%\n"
        
        report += f"""
### 改进建议
"""
        
        suggestions = []
        if response_avg > 800:
            suggestions.append("1. **优化响应时间**: 检查Redis连接池，优化SQLite查询索引")
        
        if cache_