#!/usr/bin/env python3
"""
简化版指标复算脚本
专门计算四个核心指标：
1. 平均响应时间
2. 最大/最小响应时间
3. 缓存命中率
4. 总/平均Token使用
"""

import redis
import json
from datetime import datetime

def simple_recalculate():
    """简化版指标复算"""
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    print("=" * 80)
    print("DCMMS技能核心指标复算")
    print("=" * 80)
    print(f"计算时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 获取所有性能数据
    perf_keys = redis_client.keys("dcmm:performance:*")
    
    if not perf_keys:
        print("错误: 没有找到性能数据")
        return
    
    # 初始化数据容器
    response_times = []
    token_usages = []
    cache_hits = []
    
    # 解析数据
    for key in perf_keys:
        key_str = key.decode('utf-8')
        value = redis_client.get(key)
        
        if not value:
            continue
        
        try:
            # 解析值
            val = float(value) if b"." in value else int(value)
            
            # 分类存储
            if "response_time" in key_str:
                response_times.append(val)
            elif "token_usage" in key_str:
                token_usages.append(val)
            elif "cache_hit" in key_str:
                cache_hits.append(val)
        
        except ValueError:
            continue
    
    print(f"📊 数据统计:")
    print(f"  响应时间数据点: {len(response_times)} 个")
    print(f"  Token使用数据点: {len(token_usages)} 个")
    print(f"  缓存命中数据点: {len(cache_hits)} 个")
    print(f"  总数据点: {len(response_times) + len(token_usages) + len(cache_hits)} 个")
    print()
    
    # 1. 计算平均响应时间
    print("1. 📈 响应时间统计:")
    print("-" * 40)
    if response_times:
        avg_response = sum(response_times) / len(response_times)
        min_response = min(response_times)
        max_response = max(response_times)
        
        print(f"   平均响应时间: {avg_response:.1f} ms")
        print(f"   最小响应时间: {min_response:.1f} ms")
        print(f"   最大响应时间: {max_response:.1f} ms")
        print(f"   响应范围: {min_response:.1f}-{max_response:.1f} ms")
        print(f"   数据点数量: {len(response_times)} 个")
        
        # 响应时间分布
        fast = len([rt for rt in response_times if rt < 200])
        medium = len([rt for rt in response_times if 200 <= rt < 500])
        slow = len([rt for rt in response_times if rt >= 500])
        
        print(f"   响应时间分布:")
        print(f"     <200ms (极快): {fast} 个 ({fast/len(response_times)*100:.1f}%)")
        print(f"     200-500ms (良好): {medium} 个 ({medium/len(response_times)*100:.1f}%)")
        print(f"     ≥500ms (较慢): {slow} 个 ({slow/len(response_times)*100:.1f}%)")
    else:
        print("   无响应时间数据")
    print()
    
    # 2. 计算最大/最小响应时间（已包含在上面）
    
    # 3. 计算缓存命中率
    print("2. 🎯 缓存命中率统计:")
    print("-" * 40)
    if cache_hits:
        hit_count = sum(cache_hits)
        total_queries = len(cache_hits)
        hit_rate = (hit_count / total_queries) * 100
        
        print(f"   缓存命中率: {hit_rate:.1f}%")
        print(f"   命中次数: {hit_count}/{total_queries}")
        print(f"   未命中次数: {total_queries - hit_count}/{total_queries}")
        print(f"   数据点数量: {total_queries} 个")
        
        # 命中率评价
        if hit_rate >= 70:
            rating = "✅ 优秀"
        elif hit_rate >= 50:
            rating = "⚠️ 良好"
        elif hit_rate >= 30:
            rating = "🔶 一般"
        else:
            rating = "❌ 需要优化"
        
        print(f"   评价: {rating} (目标: >60%)")
    else:
        print("   无缓存命中数据")
    print()
    
    # 4. 计算总/平均Token使用
    print("3. 💰 Token使用统计:")
    print("-" * 40)
    if token_usages:
        total_tokens = sum(token_usages)
        avg_tokens = total_tokens / len(token_usages)
        min_tokens = min(token_usages)
        max_tokens = max(token_usages)
        
        print(f"   平均Token使用: {avg_tokens:.0f} tokens")
        print(f"   总Token使用: {total_tokens:.0f} tokens")
        print(f"   最小Token使用: {min_tokens:.0f} tokens")
        print(f"   最大Token使用: {max_tokens:.0f} tokens")
        print(f"   Token范围: {min_tokens:.0f}-{max_tokens:.0f} tokens")
        print(f"   数据点数量: {len(token_usages)} 个")
        
        # Token使用分布
        low = len([t for t in token_usages if t < 100])
        medium = len([t for t in token_usages if 100 <= t < 250])
        high = len([t for t in token_usages if t >= 250])
        
        print(f"   Token使用分布:")
        print(f"     <100 tokens (极低): {low} 个 ({low/len(token_usages)*100:.1f}%)")
        print(f"     100-250 tokens (正常): {medium} 个 ({medium/len(token_usages)*100:.1f}%)")
        print(f"     ≥250 tokens (较高): {high} 个 ({high/len(token_usages)*100:.1f}%)")
        
        # 估算节省
        # 假设传统方法平均使用300 tokens
        traditional_avg = 300
        estimated_saving = (traditional_avg - avg_tokens) * len(token_usages)
        saving_percent = ((traditional_avg - avg_tokens) / traditional_avg) * 100
        
        print(f"   估算节省:")
        print(f"     相比传统方法({traditional_avg}tokens/查询):")
        print(f"     平均节省: {traditional_avg - avg_tokens:.0f} tokens/查询 ({saving_percent:.1f}%)")
        print(f"     总节省: {estimated_saving:.0f} tokens")
    else:
        print("   无Token使用数据")
    print()
    
    # 生成JSON格式结果
    result = {
        "calculation_time": datetime.now().isoformat(),
        "data_points": {
            "response_times": len(response_times),
            "token_usages": len(token_usages),
            "cache_hits": len(cache_hits),
            "total": len(response_times) + len(token_usages) + len(cache_hits)
        },
        "response_time": {
            "average_ms": avg_response if response_times else 0,
            "min_ms": min_response if response_times else 0,
            "max_ms": max_response if response_times else 0,
            "range": f"{min_response if response_times else 0}-{max_response if response_times else 0}ms",
            "count": len(response_times)
        },
        "cache_performance": {
            "hit_rate_percent": hit_rate if cache_hits else 0,
            "hit_count": hit_count if cache_hits else 0,
            "query_count": total_queries if cache_hits else 0,
            "miss_count": (total_queries - hit_count) if cache_hits else 0
        },
        "token_usage": {
            "average": avg_tokens if token_usages else 0,
            "total": total_tokens if token_usages else 0,
            "min": min_tokens if token_usages else 0,
            "max": max_tokens if token_usages else 0,
            "count": len(token_usages)
        }
    }
    
    # 保存结果
    output_file = f"core_metrics_recalculation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"💾 核心指标计算结果已保存到: {output_file}")
    
    # 生成简明的命令行输出
    print("\n" + "=" * 80)
    print("📋 核心指标摘要:")
    print("=" * 80)
    print(f"平均响应时间: {avg_response:.1f}ms")
    print(f"响应时间范围: {min_response:.1f}-{max_response:.1f}ms")
    print(f"缓存命中率: {hit_rate:.1f}% ({hit_count}/{total_queries})")
    print(f"平均Token使用: {avg_tokens:.0f} tokens")
    print(f"总Token使用: {total_tokens:.0f} tokens")
    print("=" * 80)
    
    return result

def verify_with_web_api():
    """与Web API数据对比验证"""
    print("\n🔍 与Web API数据对比验证:")
    print("-" * 80)
    
    try:
        import urllib.request
        import json as json_module
        
        # 获取Web API数据
        with urllib.request.urlopen("http://localhost:8080/api/metrics") as response:
            api_data = json_module.loads(response.read().decode())
        
        print("Web API返回数据:")
        print(f"  平均响应时间: {api_data['response_time']['average']:.1f}ms")
        print(f"  最小响应时间: {api_data['response_time']['min']:.1f}ms")
        print(f"  最大响应时间: {api_data['response_time']['max']:.1f}ms")
        print(f"  缓存命中率: {api_data['cache_performance']['hit_rate']:.1f}%")
        print(f"  平均Token使用: {api_data['token_usage']['average']:.0f} tokens")
        
    except Exception as e:
        print(f"无法连接Web API: {e}")
        print("请确保Web监控服务器正在运行 (http://localhost:8080)")

if __name__ == "__main__":
    result = simple_recalculate()
    verify_with_web_api()