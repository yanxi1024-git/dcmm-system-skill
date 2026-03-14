#!/usr/bin/env python3
"""
DCMMS技能性能评估工具
实时监控和评估DCMMS在对话中的表现
"""

import time
import json
import sqlite3
import redis
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
import sys

class DCMMSPerformanceMonitor:
    """DCMMS性能监控器"""
    
    def __init__(self, db_path: str = "data/dcmm_system.db"):
        self.db_path = db_path
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.metrics = {
            "total_queries": 0,
            "avg_response_time": 0,
            "total_tokens_saved": 0,
            "extraction_hits": 0,
            "extraction_misses": 0,
            "context_rebuild_success": 0,
            "context_rebuild_failures": 0,
            "storage_hits": {"redis": 0, "sqlite": 0, "files": 0}
        }
        self.start_time = time.time()
        
    def record_query(self, query: str, response_time: float, tokens_used: int, 
                    tokens_saved: int, extraction_result: Dict, rebuild_result: Dict):
        """记录一次查询的性能数据"""
        self.metrics["total_queries"] += 1
        
        # 更新平均响应时间
        old_avg = self.metrics["avg_response_time"]
        self.metrics["avg_response_time"] = (
            (old_avg * (self.metrics["total_queries"] - 1) + response_time) 
            / self.metrics["total_queries"]
        )
        
        # Token节省
        self.metrics["total_tokens_saved"] += tokens_saved
        
        # 提取命中率
        if extraction_result.get("entities_count", 0) > 0:
            self.metrics["extraction_hits"] += 1
        else:
            self.metrics["extraction_misses"] += 1
            
        # 上下文重建成功率
        if rebuild_result.get("success", False):
            self.metrics["context_rebuild_success"] += 1
        else:
            self.metrics["context_rebuild_failures"] += 1
            
        # 存储层命中统计
        storage_stats = rebuild_result.get("storage_stats", {})
        for storage_type in ["redis", "sqlite", "files"]:
            if storage_stats.get(storage_type, {}).get("hit", False):
                self.metrics["storage_hits"][storage_type] += 1
                
        # 保存详细记录到SQLite
        self._save_detailed_record(query, response_time, tokens_used, 
                                  tokens_saved, extraction_result, rebuild_result)
        
    def _save_detailed_record(self, query: str, response_time: float, 
                             tokens_used: int, tokens_saved: int,
                             extraction_result: Dict, rebuild_result: Dict):
        """保存详细记录到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 确保表存在
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    query TEXT NOT NULL,
                    response_time_ms REAL NOT NULL,
                    tokens_used INTEGER NOT NULL,
                    tokens_saved INTEGER NOT NULL,
                    extraction_entities INTEGER NOT NULL,
                    extraction_intents INTEGER NOT NULL,
                    context_parts INTEGER NOT NULL,
                    storage_hits TEXT NOT NULL,
                    success BOOLEAN NOT NULL
                )
            ''')
            
            # 插入记录
            cursor.execute('''
                INSERT INTO performance_logs 
                (timestamp, query, response_time_ms, tokens_used, tokens_saved,
                 extraction_entities, extraction_intents, context_parts, 
                 storage_hits, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                query[:500],  # 限制长度
                response_time * 1000,  # 转换为毫秒
                tokens_used,
                tokens_saved,
                extraction_result.get("entities_count", 0),
                extraction_result.get("intents_count", 0),
                rebuild_result.get("context_parts", 0),
                json.dumps(rebuild_result.get("storage_stats", {})),
                rebuild_result.get("success", False)
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"保存性能记录失败: {e}")
            
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        elapsed_time = time.time() - self.start_time
        
        # 计算命中率
        total_extractions = self.metrics["extraction_hits"] + self.metrics["extraction_misses"]
        extraction_hit_rate = (
            self.metrics["extraction_hits"] / total_extractions * 100 
            if total_extractions > 0 else 0
        )
        
        # 计算上下文重建成功率
        total_rebuilds = (self.metrics["context_rebuild_success"] + 
                         self.metrics["context_rebuild_failures"])
        rebuild_success_rate = (
            self.metrics["context_rebuild_success"] / total_rebuilds * 100 
            if total_rebuilds > 0 else 0
        )
        
        # 计算存储层命中分布
        total_storage_hits = sum(self.metrics["storage_hits"].values())
        storage_distribution = {}
        if total_storage_hits > 0:
            for storage_type, hits in self.metrics["storage_hits"].items():
                storage_distribution[storage_type] = hits / total_storage_hits * 100
        
        return {
            "monitoring_duration_seconds": elapsed_time,
            "total_queries": self.metrics["total_queries"],
            "queries_per_minute": self.metrics["total_queries"] / (elapsed_time / 60),
            "avg_response_time_ms": self.metrics["avg_response_time"] * 1000,
            "total_tokens_saved": self.metrics["total_tokens_saved"],
            "avg_tokens_saved_per_query": (
                self.metrics["total_tokens_saved"] / self.metrics["total_queries"] 
                if self.metrics["total_queries"] > 0 else 0
            ),
            "extraction_hit_rate_percent": extraction_hit_rate,
            "context_rebuild_success_rate_percent": rebuild_success_rate,
            "storage_hit_distribution_percent": storage_distribution,
            "system_health": self._check_system_health()
        }
    
    def _check_system_health(self) -> Dict[str, Any]:
        """检查系统健康状态"""
        health = {
            "redis_connected": False,
            "sqlite_accessible": False,
            "memory_files_exist": False,
            "storage_sizes": {}
        }
        
        # 检查Redis连接
        try:
            self.redis_client.ping()
            health["redis_connected"] = True
            health["storage_sizes"]["redis_memory_used_kb"] = (
                int(self.redis_client.info()['used_memory']) / 1024
            )
        except:
            health["redis_connected"] = False
            
        # 检查SQLite
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            health["sqlite_accessible"] = True
            health["storage_sizes"]["sqlite_tables"] = table_count
            
            # 获取数据库大小
            db_size = Path(self.db_path).stat().st_size
            health["storage_sizes"]["sqlite_size_kb"] = db_size / 1024
            conn.close()
        except:
            health["sqlite_accessible"] = False
            
        # 检查记忆文件
        memory_dir = Path("/home/yan/.openclaw/workspace/memory")
        if memory_dir.exists():
            memory_files = list(memory_dir.glob("*.md"))
            health["memory_files_exist"] = len(memory_files) > 0
            health["storage_sizes"]["memory_files_count"] = len(memory_files)
            
            # 计算总大小
            total_size = sum(f.stat().st_size for f in memory_files)
            health["storage_sizes"]["memory_files_size_kb"] = total_size / 1024
            
        return health
    
    def generate_report(self) -> str:
        """生成评估报告"""
        summary = self.get_performance_summary()
        
        report = f"""
# DCMMS技能性能评估报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
监控时长: {summary['monitoring_duration_seconds']:.1f}秒

## 📊 性能指标
- **总查询数**: {summary['total_queries']}
- **查询频率**: {summary['queries_per_minute']:.1f} 次/分钟
- **平均响应时间**: {summary['avg_response_time_ms']:.1f}ms
- **总Token节省**: {summary['total_tokens_saved']}
- **平均每查询节省**: {summary['avg_tokens_saved_per_query']:.1f} tokens

## 🎯 准确性指标
- **信息提取命中率**: {summary['extraction_hit_rate_percent']:.1f}%
- **上下文重建成功率**: {summary['context_rebuild_success_rate_percent']:.1f}%

## 💾 存储层性能
"""
        
        # 存储命中分布
        for storage_type, percentage in summary['storage_hit_distribution_percent'].items():
            report += f"- **{storage_type}命中率**: {percentage:.1f}%\n"
            
        # 系统健康状态
        health = summary['system_health']
        report += f"""
## 🏥 系统健康状态
- **Redis连接**: {'✅ 正常' if health['redis_connected'] else '❌ 异常'}
- **SQLite访问**: {'✅ 正常' if health['sqlite_accessible'] else '❌ 异常'}
- **记忆文件**: {'✅ 存在' if health['memory_files_exist'] else '❌ 不存在'}

## 📈 存储使用情况
"""
        
        for metric, value in health['storage_sizes'].items():
            if 'kb' in metric or 'size' in metric:
                report += f"- **{metric}**: {value:.1f} KB\n"
            else:
                report += f"- **{metric}**: {value}\n"
                
        return report

def main():
    """主函数 - 实时监控模式"""
    print("🚀 启动DCMMS性能监控器...")
    monitor = DCMMSPerformanceMonitor()
    
    try:
        print("📊 监控器已启动，开始收集性能数据...")
        print("按Ctrl+C停止监控并生成报告")
        
        # 模拟监控循环（实际使用时需要集成到DCMMS处理流程中）
        import time
        while True:
            time.sleep(5)
            # 这里应该从实际DCMMS处理中获取数据
            # 暂时显示当前状态
            print(f"\r监控中... 已记录 {monitor.metrics['total_queries']} 次查询", end="")
            
    except KeyboardInterrupt:
        print("\n\n🛑 监控停止，生成评估报告...")
        report = monitor.generate_report()
        print(report)
        
        # 保存报告到文件
        report_file = f"dcmm_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n📄 报告已保存到: {report_file}")

if __name__ == "__main__":
    main()