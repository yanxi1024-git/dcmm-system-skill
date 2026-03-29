#!/usr/bin/env python3
"""
指标复算脚本
从原始日志重新计算关键性能指标
"""

import json
import redis
import statistics
from datetime import datetime
from collections import defaultdict

class MetricsRecalculator:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    def get_all_performance_data(self, limit=None):
        """从Redis获取所有性能数据"""
        perf_keys = self.redis_client.keys("dcmm:performance:*")
        
        data = {
            "response_times": [],
            "token_usages": [],
            "cache_hits": []
        }
        
        timestamps = defaultdict(list)
        
        for key in perf_keys:
            key_str = key.decode('utf-8')
            value = self.redis_client.get(key)
            
            if not value:
                continue
            
            # 解析键名获取时间戳和类型
            parts = key_str.split(":")
            if len(parts) >= 4:
                metric_type = parts[2]  # response_time, token_usage, cache_hit
                timestamp = int(parts[3])
                
                # 解析值
                try:
                    val = float(value) if b"." in value else int(value)
                    
                    if metric_type == "response_time":
                        data["response_times"].append({
                            "timestamp": timestamp,
                            "value": val,
                            "key": key_str
                        })
                        timestamps[timestamp].append(("response_time", val))
                    
                    elif metric_type == "token_usage":
                        data["token_usages"].append({
                            "timestamp": timestamp,
                            "value": val,
                            "key": key_str
                        })
                        timestamps[timestamp].append(("token_usage", val))
                    
                    elif metric_type == "cache_hit":
                        data["cache_hits"].append({
                            "timestamp": timestamp,
                            "value": val,
                            "key": key_str
                        })
                        timestamps[timestamp].append(("cache_hit", val))
                
                except ValueError:
                    continue
        
        # 如果需要限制数量
        if limit:
            for key in data:
                data[key] = data[key][:limit]
        
        return data, timestamps
    
    def calculate_basic_metrics(self, data):
        """计算基础指标"""
        response_values = [item["value"] for item in data["response_times"]]
        token_values = [item["value"] for item in data["token_usages"]]
        cache_values = [item["value"] for item in data["cache_hits"]]
        
        metrics = {
            "response_time": {
                "count": len(response_values),
                "values": response_values
            },
            "token_usage": {
                "count": len(token_values),
                "values": token_values
            },
            "cache_hit": {
                "count": len(cache_values),
                "values": cache_values
            }
        }
        
        return metrics
    
    def recalculate_derived_metrics(self, metrics):
        """重新计算衍生指标"""
        response_values = metrics["response_time"]["values"]
        token_values = metrics["token_usage"]["values"]
        cache_values = metrics["cache_hit"]["values"]
        
        derived = {}
        
        # 1. 平均响应时间
        if response_values:
            derived["avg_response_time_ms"] = statistics.mean(response_values)
            derived["min_response_time_ms"] = min(response_values)
            derived["max_response_time_ms"] = max(response_values)
            derived["response_time_range"] = f"{min(response_values)}-{max(response_values)}ms"
            derived["response_time_std"] = statistics.stdev(response_values) if len(response_values) > 1 else 0
        else:
            derived["avg_response_time_ms"] = 0
            derived["min_response_time_ms"] = 0
            derived["max_response_time_ms"] = 0
            derived["response_time_range"] = "N/A"
            derived["response_time_std"] = 0
        
        # 2. Token统计
        if token_values:
            derived["avg_token_usage"] = statistics.mean(token_values)
            derived["total_token_usage"] = sum(token_values)
            derived["min_token_usage"] = min(token_values)
            derived["max_token_usage"] = max(token_values)
            derived["token_usage_range"] = f"{min(token_values)}-{max(token_values)} tokens"
        else:
            derived["avg_token_usage"] = 0
            derived["total_token_usage"] = 0
            derived["min_token_usage"] = 0
            derived["max_token_usage"] = 0
            derived["token_usage_range"] = "N/A"
        
        # 3. 缓存命中率
        if cache_values:
            hit_count = sum(cache_values)
            total = len(cache_values)
            derived["cache_hit_count"] = hit_count
            derived["cache_query_count"] = total
            derived["cache_hit_rate_percent"] = (hit_count / total) * 100
            derived["cache_miss_rate_percent"] = 100 - derived["cache_hit_rate_percent"]
        else:
            derived["cache_hit_count"] = 0
            derived["cache_query_count"] = 0
            derived["cache_hit_rate_percent"] = 0
            derived["cache_miss_rate_percent"] = 100
        
        # 4. 数据质量指标
        derived["total_data_points"] = (
            len(response_values) + len(token_values) + len(cache_values)
        )
        
        # 注意：这里需要传入原始data参数，但在当前函数中不可用
        # 这个指标将在外部计算
        
        return derived
    
    def calculate_by_time_window(self, data, window_minutes=5):
        """按时间窗口计算指标"""
        now = datetime.now().timestamp()
        window_seconds = window_minutes * 60
        
        # 过滤最近window_minutes的数据
        recent_response = [
            item for item in data["response_times"] 
            if now - item["timestamp"] <= window_seconds
        ]
        recent_token = [
            item for item in data["token_usages"] 
            if now - item["timestamp"] <= window_seconds
        ]
        recent_cache = [
            item for item in data["cache_hits"] 
            if now - item["timestamp"] <= window_seconds
        ]
        
        recent_data = {
            "response_times": recent_response,
            "token_usages": recent_token,
            "cache_hits": recent_cache
        }
        
        recent_metrics = self.calculate_basic_metrics(recent_data)
        recent_derived = self.recalculate_derived_metrics(recent_metrics)
        
        return {
            "window_minutes": window_minutes,
            "data_points": len(recent_response) + len(recent_token) + len(recent_cache),
            "metrics": recent_derived
        }
    
    def generate_report(self, data, derived_metrics, time_windows=[1, 5, 15, 60]):
        """生成完整报告"""
        # 计算唯一时间戳数量
        unique_timestamps = len(set(
            [item["timestamp"] for item in data["response_times"]] +
            [item["timestamp"] for item in data["token_usages"]] +
            [item["timestamp"] for item in data["cache_hits"]]
        ))
        
        report = {
            "report_time": datetime.now().isoformat(),
            "data_summary": {
                "response_time_points": len(data["response_times"]),
                "token_usage_points": len(data["token_usages"]),
                "cache_hit_points": len(data["cache_hits"]),
                "total_points": len(data["response_times"]) + len(data["token_usages"]) + len(data["cache_hits"]),
                "unique_timestamps": unique_timestamps
            },
            "key_metrics": derived_metrics,
            "time_window_analysis": {}
        }
        
        # 时间窗口分析
        for window in time_windows:
            window_analysis = self.calculate_by_time_window(data, window)
            report["time_window_analysis"][f"last_{window}_minutes"] = window_analysis
        
        return report
    
    def print_human_readable_report(self, report):
        """打印人类可读的报告"""
        print("=" * 80)
        print("DCMMS技能指标复算报告")
        print("=" * 80)
        print(f"报告时间: {report['report_time']}")
        print(f"数据点总数: {report['data_summary']['total_points']}")
        print(f"  响应时间: {report['data_summary']['response_time_points']} 个")
        print(f"  Token使用: {report['data_summary']['token_usage_points']} 个")
        print(f"  缓存命中: {report['data_summary']['cache_hit_points']} 个")
        print()
        
        metrics = report["key_metrics"]
        print("📊 关键性能指标复算结果:")
        print("-" * 80)
        
        # 响应时间
        print("1. 响应时间统计:")
        print(f"   平均响应时间: {metrics['avg_response_time_ms']:.1f} ms")
        print(f"   最小响应时间: {metrics['min_response_time_ms']:.1f} ms")
        print(f"   最大响应时间: {metrics['max_response_time_ms']:.1f} ms")
        print(f"   响应范围: {metrics['response_time_range']}")
        print(f"   标准差: {metrics['response_time_std']:.1f} ms")
        print()
        
        # Token使用
        print("2. Token使用统计:")
        print(f"   平均Token使用: {metrics['avg_token_usage']:.0f} tokens")
        print(f"   总Token使用: {metrics['total_token_usage']:.0f} tokens")
        print(f"   最小Token使用: {metrics['min_token_usage']:.0f} tokens")
        print(f"   最大Token使用: {metrics['max_token_usage']:.0f} tokens")
        print(f"   Token范围: {metrics['token_usage_range']}")
        print()
        
        # 缓存命中
        print("3. 缓存性能统计:")
        print(f"   缓存命中率: {metrics['cache_hit_rate_percent']:.1f}%")
        print(f"   缓存未命中率: {metrics['cache_miss_rate_percent']:.1f}%")
        print(f"   命中次数: {metrics['cache_hit_count']}/{metrics['cache_query_count']}")
        print()
        
        # 时间窗口分析
        print("⏰ 时间窗口分析:")
        print("-" * 80)
        
        for window_name, analysis in report["time_window_analysis"].items():
            window_metrics = analysis["metrics"]
            print(f"{window_name.replace('_', ' ')}:")
            print(f"  数据点: {analysis['data_points']} 个")
            if analysis["data_points"] > 0:
                print(f"  平均响应: {window_metrics.get('avg_response_time_ms', 0):.1f}ms")
                print(f"  缓存命中: {window_metrics.get('cache_hit_rate_percent', 0):.1f}%")
                print(f"  平均Token: {window_metrics.get('avg_token_usage', 0):.0f} tokens")
            else:
                print("  无数据")
            print()
        
        print("=" * 80)
    
    def save_report_to_file(self, report, filename=None):
        """保存报告到文件"""
        if filename is None:
            filename = f"metrics_recalculation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"📁 报告已保存到: {filename}")
        return filename

def main():
    """主函数"""
    import sys
    
    # 解析命令行参数
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            print(f"限制数据点数量: {limit}")
        except ValueError:
            print(f"错误: 参数必须是数字")
            return
    
    # 创建复算器
    recalculator = MetricsRecalculator()
    
    # 获取数据
    print("从Redis获取性能数据...")
    data, timestamps = recalculator.get_all_performance_data(limit)
    
    if not any(data.values()):
        print("错误: 没有找到性能数据")
        return
    
    # 计算基础指标
    print("计算基础指标...")
    basic_metrics = recalculator.calculate_basic_metrics(data)
    
    # 重新计算衍生指标
    print("重新计算衍生指标...")
    derived_metrics = recalculator.recalculate_derived_metrics(basic_metrics)
    
    # 生成报告
    print("生成分析报告...")
    report = recalculator.generate_report(data, derived_metrics)
    
    # 打印报告
    recalculator.print_human_readable_report(report)
    
    # 保存报告
    recalculator.save_report_to_file(report)
    
    # 额外：验证Web API返回的数据
    print("\n🔍 验证Web API数据一致性:")
    print("-" * 80)
    
    import requests
    try:
        api_response = requests.get("http://localhost:8080/api/metrics", timeout=5)
        if api_response.status_code == 200:
            api_data = api_response.json()
            print("Web API返回数据:")
            print(f"  平均响应时间: {api_data['response_time']['average']:.1f}ms (复算: {derived_metrics['avg_response_time_ms']:.1f}ms)")
            print(f"  缓存命中率: {api_data['cache_performance']['hit_rate']:.1f}% (复算: {derived_metrics['cache_hit_rate_percent']:.1f}%)")
            print(f"  平均Token: {api_data['token_usage']['average']:.0f} tokens (复算: {derived_metrics['avg_token_usage']:.0f} tokens)")
            
            # 计算差异
            resp_diff = abs(api_data['response_time']['average'] - derived_metrics['avg_response_time_ms'])
            cache_diff = abs(api_data['cache_performance']['hit_rate'] - derived_metrics['cache_hit_rate_percent'])
            token_diff = abs(api_data['token_usage']['average'] - derived_metrics['avg_token_usage'])
            
            print(f"\n数据一致性检查:")
            print(f"  响应时间差异: {resp_diff:.1f}ms ({'✅ 一致' if resp_diff < 1 else '⚠️ 有差异'})")
            print(f"  缓存命中率差异: {cache_diff:.1f}% ({'✅ 一致' if cache_diff < 0.1 else '⚠️ 有差异'})")
            print(f"  Token使用差异: {token_diff:.0f} tokens ({'✅ 一致' if token_diff < 1 else '⚠️ 有差异'})")
        else:
            print(f"Web API请求失败: {api_response.status_code}")
    except Exception as e:
        print(f"无法连接Web API: {e}")

if __name__ == "__main__":
    main()