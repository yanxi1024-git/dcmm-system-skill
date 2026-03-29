#!/usr/bin/env python3
"""
导出原始监控日志
从Redis中获取最近20条原始监控记录
"""

import redis
import json
from datetime import datetime

def export_raw_logs(limit=20):
    """导出原始日志"""
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    print("=" * 80)
    print("DCMMS技能原始监控日志样本")
    print("=" * 80)
    print(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"数据源: Redis (localhost:6379/0)")
    print(f"限制: 最近 {limit} 条记录")
    print("=" * 80)
    print()
    
    # 获取所有性能相关的键
    perf_keys = redis_client.keys("dcmm:performance:*")
    
    if not perf_keys:
        print("没有找到性能数据")
        return
    
    # 按时间戳排序（假设键名中包含时间戳）
    sorted_keys = []
    for key in perf_keys:
        key_str = key.decode('utf-8')
        try:
            # 尝试从键名中提取时间戳
            if ":" in key_str:
                parts = key_str.split(":")
                if len(parts) >= 4:
                    timestamp = int(parts[-1])
                    sorted_keys.append((timestamp, key_str, key))
        except:
            continue
    
    # 按时间戳降序排序
    sorted_keys.sort(key=lambda x: x[0], reverse=True)
    
    # 只取最近limit条
    recent_keys = sorted_keys[:limit]
    
    print("📊 原始事件日志样本（最近20条）:")
    print("-" * 80)
    
    logs = []
    for i, (timestamp, key_str, key) in enumerate(recent_keys, 1):
        value = redis_client.get(key)
        if value:
            try:
                # 尝试解析值
                val = float(value) if "." in value.decode('utf-8') else int(value)
                
                # 确定指标类型
                metric_type = "unknown"
                if "response_time" in key_str:
                    metric_type = "response_time_ms"
                    unit = "ms"
                elif "token_usage" in key_str:
                    metric_type = "token_usage_count"
                    unit = "tokens"
                elif "cache_hit" in key_str:
                    metric_type = "cache_hit_binary"
                    unit = "1=hit, 0=miss"
                else:
                    unit = ""
                
                # 格式化时间
                time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                
                log_entry = {
                    "index": i,
                    "timestamp": timestamp,
                    "time_human": time_str,
                    "metric_type": metric_type,
                    "key": key_str,
                    "value": val,
                    "unit": unit
                }
                
                logs.append(log_entry)
                
                # 打印
                print(f"{i:2d}. [{time_str}] {metric_type:20s} = {val:8.1f} {unit}")
                
            except Exception as e:
                print(f"{i:2d}. 错误解析键: {key_str} -> {value} ({e})")
    
    print("-" * 80)
    
    # 按指标类型分组统计
    print("\n📈 按指标类型分组统计:")
    print("-" * 80)
    
    response_times = [log["value"] for log in logs if log["metric_type"] == "response_time_ms"]
    token_usages = [log["value"] for log in logs if log["metric_type"] == "token_usage_count"]
    cache_hits = [log["value"] for log in logs if log["metric_type"] == "cache_hit_binary"]
    
    if response_times:
        print(f"响应时间 ({len(response_times)}条):")
        print(f"  平均值: {sum(response_times)/len(response_times):.1f}ms")
        print(f"  最小值: {min(response_times):.1f}ms")
        print(f"  最大值: {max(response_times):.1f}ms")
        print(f"  范围: {min(response_times):.1f}-{max(response_times):.1f}ms")
    
    if token_usages:
        print(f"Token使用 ({len(token_usages)}条):")
        print(f"  平均值: {sum(token_usages)/len(token_usages):.0f} tokens")
        print(f"  总计: {sum(token_usages):.0f} tokens")
        print(f"  范围: {min(token_usages)}-{max(token_usages)} tokens")
    
    if cache_hits:
        hit_count = sum(cache_hits)
        total = len(cache_hits)
        hit_rate = (hit_count / total) * 100 if total > 0 else 0
        print(f"缓存命中 ({total}条):")
        print(f"  命中次数: {hit_count}/{total}")
        print(f"  命中率: {hit_rate:.1f}%")
    
    print("-" * 80)
    
    # 保存到文件
    export_file = f"raw_monitor_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(export_file, 'w', encoding='utf-8') as f:
        json.dump({
            "export_time": datetime.now().isoformat(),
            "total_keys_found": len(perf_keys),
            "exported_count": len(logs),
            "logs": logs,
            "summary": {
                "response_times": response_times,
                "token_usages": token_usages,
                "cache_hits": cache_hits
            }
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 原始日志已保存到: {export_file}")
    print("=" * 80)
    
    return logs

def get_detailed_logs(limit=50):
    """获取更详细的日志（包含原始Redis数据）"""
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    # 获取所有键
    all_keys = redis_client.keys("dcmm:performance:*")
    
    detailed_logs = []
    for key in all_keys[:limit]:
        key_str = key.decode('utf-8')
        value = redis_client.get(key)
        ttl = redis_client.ttl(key)
        
        log_entry = {
            "key": key_str,
            "value": value.decode('utf-8') if value else None,
            "ttl_seconds": ttl,
            "type": redis_client.type(key).decode('utf-8'),
            "size_bytes": len(value) if value else 0
        }
        
        detailed_logs.append(log_entry)
    
    return detailed_logs

if __name__ == "__main__":
    export_raw_logs(20)