#!/usr/bin/env python3
"""
对话性能数据收集器
实时收集和分析DCMMS技能在对话中的性能表现
"""

import json
import time
import sqlite3
import redis
import os
from datetime import datetime
from pathlib import Path

class ConversationPerformanceCollector:
    def __init__(self):
        # 数据库连接
        self.db_path = "data/dcmm_system.db"
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        
        # 性能数据存储
        self.performance_data = {
            "timestamp": datetime.now().isoformat(),
            "conversation_id": f"conv_{int(time.time())}",
            "metrics": {
                "response_times": [],
                "token_usage": [],
                "cache_hits": [],
                "extraction_accuracy": [],
                "rebuild_quality": []
            },
            "system_health": {},
            "conversation_summary": {}
        }
        
        # 确保数据目录存在
        os.makedirs("data/performance", exist_ok=True)
        
    def collect_system_health(self):
        """收集系统健康状态"""
        try:
            # Redis状态
            redis_info = self.redis_client.info()
            self.performance_data["system_health"]["redis"] = {
                "memory_used_kb": redis_info.get('used_memory', 0) / 1024,
                "connected_clients": redis_info.get('connected_clients', 0),
                "uptime_seconds": redis_info.get('uptime_in_seconds', 0)
            }
            
            # SQLite状态
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取表数量
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            # 获取数据库大小
            db_size = os.path.getsize(self.db_path) / 1024
            
            self.performance_data["system_health"]["sqlite"] = {
                "table_count": table_count,
                "database_size_kb": db_size,
                "connection_status": "healthy"
            }
            
            conn.close()
            
            # 记忆文件状态
            memory_dir = Path("/home/yan/.openclaw/workspace/memory")
            if memory_dir.exists():
                memory_files = list(memory_dir.glob("*.md"))
                total_size = sum(f.stat().st_size for f in memory_files) / 1024
                
                self.performance_data["system_health"]["memory_files"] = {
                    "file_count": len(memory_files),
                    "total_size_kb": total_size,
                    "latest_file": max(memory_files, key=lambda f: f.stat().st_mtime).name if memory_files else None
                }
            
            return True
            
        except Exception as e:
            print(f"收集系统健康状态时出错: {e}")
            return False
    
    def collect_conversation_metrics(self):
        """收集对话指标"""
        try:
            # 从Redis获取最近的性能数据
            redis_keys = self.redis_client.keys("dcmm:performance:*")
            
            for key in redis_keys:
                key_str = key.decode('utf-8')
                if "response_time" in key_str:
                    response_time = float(self.redis_client.get(key) or 0)
                    self.performance_data["metrics"]["response_times"].append(response_time)
                
                elif "token_usage" in key_str:
                    token_usage = int(self.redis_client.get(key) or 0)
                    self.performance_data["metrics"]["token_usage"].append(token_usage)
                
                elif "cache_hit" in key_str:
                    cache_hit = int(self.redis_client.get(key) or 0)
                    self.performance_data["metrics"]["cache_hits"].append(cache_hit)
            
            # 从SQLite获取提取和重建质量数据
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取最近的提取记录
            cursor.execute("""
                SELECT extraction_accuracy, rebuild_quality, timestamp 
                FROM extraction_logs 
                ORDER BY timestamp DESC LIMIT 10
            """)
            
            extraction_records = cursor.fetchall()
            for record in extraction_records:
                self.performance_data["metrics"]["extraction_accuracy"].append(record[0])
                self.performance_data["metrics"]["rebuild_quality"].append(record[1])
            
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"收集对话指标时出错: {e}")
            return False
    
    def analyze_performance(self):
        """分析性能数据"""
        metrics = self.performance_data["metrics"]
        
        # 计算统计指标
        analysis = {
            "response_time": {
                "average": sum(metrics["response_times"]) / len(metrics["response_times"]) if metrics["response_times"] else 0,
                "min": min(metrics["response_times"]) if metrics["response_times"] else 0,
                "max": max(metrics["response_times"]) if metrics["response_times"] else 0,
                "count": len(metrics["response_times"])
            },
            "token_usage": {
                "average": sum(metrics["token_usage"]) / len(metrics["token_usage"]) if metrics["token_usage"] else 0,
                "total": sum(metrics["token_usage"]),
                "count": len(metrics["token_usage"])
            },
            "cache_performance": {
                "hit_rate": (sum(metrics["cache_hits"]) / len(metrics["cache_hits"])) * 100 if metrics["cache_hits"] else 0,
                "total_hits": sum(metrics["cache_hits"]),
                "total_queries": len(metrics["cache_hits"])
            },
            "quality_metrics": {
                "extraction_accuracy_avg": sum(metrics["extraction_accuracy"]) / len(metrics["extraction_accuracy"]) if metrics["extraction_accuracy"] else 0,
                "rebuild_quality_avg": sum(metrics["rebuild_quality"]) / len(metrics["rebuild_quality"]) if metrics["rebuild_quality"] else 0
            }
        }
        
        self.performance_data["analysis"] = analysis
        return analysis
    
    def generate_conversation_summary(self):
        """生成对话摘要"""
        # 从记忆文件中获取最近的对话内容
        memory_file = Path("/home/yan/.openclaw/workspace/memory/2026-03-14.md")
        
        if memory_file.exists():
            content = memory_file.read_text(encoding='utf-8')
            
            # 提取关键信息
            lines = content.split('\n')
            recent_conversations = []
            
            for i, line in enumerate(lines):
                if "DCMMS" in line or "skill" in line.lower() or "性能" in line:
                    context_start = max(0, i-2)
                    context_end = min(len(lines), i+3)
                    context = '\n'.join(lines[context_start:context_end])
                    recent_conversations.append(context)
            
            self.performance_data["conversation_summary"] = {
                "memory_file_size_kb": memory_file.stat().st_size / 1024,
                "recent_dcmm_references": len([line for line in lines if "DCMMS" in line]),
                "sample_conversations": recent_conversations[:5]  # 只取前5个样本
            }
    
    def save_performance_report(self):
        """保存性能报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"data/performance/conversation_performance_{timestamp}.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.performance_data, f, ensure_ascii=False, indent=2)
        
        print(f"性能报告已保存到: {report_path}")
        return report_path
    
    def generate_summary_report(self):
        """生成摘要报告"""
        analysis = self.performance_data.get("analysis", {})
        
        summary = f"""
## 📊 DCMMS技能对话性能评估报告
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
对话ID: {self.performance_data["conversation_id"]}

### 🎯 性能指标摘要

**响应时间性能**:
- 平均响应时间: {analysis.get('response_time', {}).get('average', 0):.1f}ms
- 响应次数: {analysis.get('response_time', {}).get('count', 0)}次
- 最快响应: {analysis.get('response_time', {}).get('min', 0):.1f}ms
- 最慢响应: {analysis.get('response_time', {}).get('max', 0):.1f}ms

**Token使用效率**:
- 平均Token使用: {analysis.get('token_usage', {}).get('average', 0):.0f} tokens
- 总Token使用: {analysis.get('token_usage', {}).get('total', 0):.0f} tokens
- 查询次数: {analysis.get('token_usage', {}).get('count', 0)}次

**缓存性能**:
- 缓存命中率: {analysis.get('cache_performance', {}).get('hit_rate', 0):.1f}%
- 总命中次数: {analysis.get('cache_performance', {}).get('total_hits', 0)}次
- 总查询次数: {analysis.get('cache_performance', {}).get('total_queries', 0)}次

**质量指标**:
- 信息提取准确率: {analysis.get('quality_metrics', {}).get('extraction_accuracy_avg', 0):.1f}%
- 上下文重建质量: {analysis.get('quality_metrics', {}).get('rebuild_quality_avg', 0):.1f}%

### 🏥 系统健康状态
"""
        
        # 添加系统健康信息
        health = self.performance_data.get("system_health", {})
        if "redis" in health:
            summary += f"""
**Redis状态**:
- 内存使用: {health['redis'].get('memory_used_kb', 0):.1f} KB
- 连接客户端: {health['redis'].get('connected_clients', 0)}个
- 运行时间: {health['redis'].get('uptime_seconds', 0)}秒
"""
        
        if "sqlite" in health:
            summary += f"""
**SQLite状态**:
- 表数量: {health['sqlite'].get('table_count', 0)}个
- 数据库大小: {health['sqlite'].get('database_size_kb', 0):.1f} KB
- 连接状态: {health['sqlite'].get('connection_status', 'unknown')}
"""
        
        if "memory_files" in health:
            summary += f"""
**记忆文件状态**:
- 文件数量: {health['memory_files'].get('file_count', 0)}个
- 总大小: {health['memory_files'].get('total_size_kb', 0):.1f} KB
- 最新文件: {health['memory_files'].get('latest_file', '无')}
"""
        
        summary += f"""
### 📝 对话摘要
- 记忆文件大小: {self.performance_data.get('conversation_summary', {}).get('memory_file_size_kb', 0):.1f} KB
- DCMMS相关引用: {self.performance_data.get('conversation_summary', {}).get('recent_dcmm_references', 0)}处

### 🎯 评估结论
"""
        
        # 基于数据生成评估结论
        response_time_avg = analysis.get('response_time', {}).get('average', 0)
        cache_hit_rate = analysis.get('cache_performance', {}).get('hit_rate', 0)
        extraction_accuracy = analysis.get('quality_metrics', {}).get('extraction_accuracy_avg', 0)
        
        conclusions = []
        
        if response_time_avg < 1000:
            conclusions.append("✅ **响应速度优秀**: 平均响应时间 < 1秒")
        elif response_time_avg < 2000:
            conclusions.append("⚠️ **响应速度良好**: 平均响应时间 1-2秒")
        else:
            conclusions.append("❌ **响应速度需要优化**: 平均响应时间 > 2秒")
        
        if cache_hit_rate > 60:
            conclusions.append("✅ **缓存效率优秀**: 命中率 > 60%")
        elif cache_hit_rate > 40:
            conclusions.append("⚠️ **缓存效率良好**: 命中率 40-60%")
        else:
            conclusions.append("❌ **缓存效率需要优化**: 命中率 < 40%")
        
        if extraction_accuracy > 90:
            conclusions.append("✅ **信息提取准确**: 准确率 > 90%")
        elif extraction_accuracy > 70:
            conclusions.append("⚠️ **信息提取良好**: 准确率 70-90%")
        else:
            conclusions.append("❌ **信息提取需要改进**: 准确率 < 70%")
        
        summary += "\n".join(conclusions)
        
        summary += f"""

### 🔄 改进建议
"""
        
        # 基于分析结果提供改进建议
        suggestions = []
        
        if response_time_avg > 1500:
            suggestions.append("1. **优化响应时间**: 考虑增加Redis缓存预热机制")
        
        if cache_hit_rate < 50:
            suggestions.append("2. **提高缓存命中率**: 优化缓存策略，增加热门数据缓存")
        
        if extraction_accuracy < 80:
            suggestions.append("3. **改进信息提取**: 优化实体识别算法，增加训练数据")
        
        if not suggestions:
            suggestions.append("1. **保持当前优化**: 系统性能良好，继续监控")
            suggestions.append("2. **扩展功能**: 考虑增加更多实体类型支持")
            suggestions.append("3. **性能基准**: 建立长期性能基准线")
        
        summary += "\n".join(suggestions)
        
        return summary
    
    def run_collection(self):
        """运行完整的数据收集和分析流程"""
        print("开始收集DCMMS技能对话性能数据...")
        
        # 收集数据
        self.collect_system_health()
        self.collect_conversation_metrics()
        self.generate_conversation_summary()
        
        # 分析数据
        analysis = self.analyze_performance()
        
        # 保存报告
        report_path = self.save_performance_report()
        
        # 生成摘要
        summary = self.generate_summary_report()
        
        print("数据收集和分析完成！")
        
        return {
            "report_path": report_path,
            "summary": summary,
            "analysis": analysis
        }

def main():
    """主函数"""
    collector = ConversationPerformanceCollector()
    result = collector.run_collection()
    
    # 打印摘要报告
    print("\n" + "="*60)
    print("DCMMS技能对话性能评估摘要")
    print("="*60)
    print(result["summary"])
    
    # 保存摘要报告到文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = f"data/performance/conversation_summary_{timestamp}.md"
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(result["summary"])
    
    print(f"\n详细报告已保存到: {result['report_path']}")
    print(f"摘要报告已保存到: {summary_path}")

if __name__ == "__main__":
    main()