#!/usr/bin/env python3
"""
性能数据注入脚本
模拟DCMMS技能在实际对话中的性能数据
"""

import redis
import time
import random
from datetime import datetime

def inject_performance_data():
    """注入性能数据到Redis"""
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    print("开始注入DCMMS技能性能数据...")
    print("按 Ctrl+C 停止注入")
    print("")
    
    try:
        count = 0
        while True:
            # 生成模拟性能数据
            timestamp = int(time.time())
            
            # 响应时间 (50-800ms，大多数在100-300ms)
            response_time = random.randint(50, 800)
            if random.random() < 0.7:  # 70%的数据在100-300ms
                response_time = random.randint(100, 300)
            
            # Token使用 (50-400 tokens，大多数在100-250)
            token_usage = random.randint(50, 400)
            if random.random() < 0.6:  # 60%的数据在100-250
                token_usage = random.randint(100, 250)
            
            # 缓存命中 (0或1，命中率约50%)
            cache_hit = 1 if random.random() < 0.5 else 0
            
            # 存储到Redis
            redis_client.set(f"dcmm:performance:response_time:{timestamp}", response_time, ex=3600)
            redis_client.set(f"dcmm:performance:token_usage:{timestamp}", token_usage, ex=3600)
            redis_client.set(f"dcmm:performance:cache_hit:{timestamp}", cache_hit, ex=3600)
            
            count += 1
            
            # 每5次打印一次状态
            if count % 5 == 0:
                current_time = datetime.now().strftime("%H:%M:%S")
                print(f"[{current_time}] 已注入 {count} 条性能数据")
                print(f"  最新数据: 响应时间={response_time}ms, Token使用={token_usage}, 缓存命中={'是' if cache_hit else '否'}")
                print("")
            
            # 等待1-3秒
            time.sleep(random.uniform(1, 3))
            
    except KeyboardInterrupt:
        print(f"\n注入停止，总共注入了 {count} 条性能数据")
        print("数据将在Redis中保留1小时")

def clear_performance_data():
    """清除性能数据"""
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    # 删除所有性能相关的键
    perf_keys = redis_client.keys("dcmm:performance:*")
    if perf_keys:
        deleted = redis_client.delete(*perf_keys)
        print(f"已清除 {deleted} 个性能数据键")
    else:
        print("没有找到性能数据")

def show_current_stats():
    """显示当前统计"""
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    perf_keys = redis_client.keys("dcmm:performance:*")
    
    if not perf_keys:
        print("当前没有性能数据")
        return
    
    response_times = []
    token_usages = []
    cache_hits = []
    
    for key in perf_keys:
        key_str = key.decode('utf-8')
        value = redis_client.get(key)
        
        if value:
            if "response_time" in key_str:
                response_times.append(float(value))
            elif "token_usage" in key_str:
                token_usages.append(int(value))
            elif "cache_hit" in key_str:
                cache_hits.append(int(value))
    
    print("当前性能数据统计:")
    print(f"  响应时间数据点: {len(response_times)} 个")
    if response_times:
        print(f"  平均响应时间: {sum(response_times)/len(response_times):.1f}ms")
        print(f"  范围: {min(response_times)}-{max(response_times)}ms")
    
    print(f"  Token使用数据点: {len(token_usages)} 个")
    if token_usages:
        print(f"  平均Token使用: {sum(token_usages)/len(token_usages):.0f} tokens")
        print(f"  总Token使用: {sum(token_usages)} tokens")
    
    print(f"  缓存命中数据点: {len(cache_hits)} 个")
    if cache_hits:
        hit_rate = (sum(cache_hits) / len(cache_hits)) * 100
        print(f"  缓存命中率: {hit_rate:.1f}%")
        print(f"  命中次数: {sum(cache_hits)}/{len(cache_hits)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "clear":
            clear_performance_data()
        elif sys.argv[1] == "stats":
            show_current_stats()
        elif sys.argv[1] == "help":
            print("用法:")
            print("  python inject_performance_data.py          # 开始注入数据")
            print("  python inject_performance_data.py clear    # 清除所有数据")
            print("  python inject_performance_data.py stats    # 显示当前统计")
            print("  python inject_performance_data.py help     # 显示帮助")
        else:
            print(f"未知命令: {sys.argv[1]}")
            print("使用 'help' 查看可用命令")
    else:
        inject_performance_data()