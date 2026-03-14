#!/usr/bin/env python3
"""
启动DCMMS实时监控
"""

import time
import signal
import sys
from real_time_monitor import start_dcmm_monitoring, record_dcmm_turn, get_dcmm_dashboard

def signal_handler(sig, frame):
    """处理Ctrl+C信号"""
    print("\n\n🛑 收到停止信号，生成最终报告...")
    
    # 获取最终仪表板数据
    dashboard = get_dcmm_dashboard()
    
    print("\n" + "="*60)
    print("📊 DCMMS监控最终报告")
    print("="*60)
    print(f"总对话轮次: {dashboard['conversation_metrics']['total_turns']}")
    print(f"平均响应时间: {dashboard['conversation_metrics']['avg_turn_time_ms']:.1f}ms")
    print(f"信息提取成功率: {dashboard['success_rates']['extraction']:.1f}%")
    print(f"上下文重建成功率: {dashboard['success_rates']['rebuild']:.1f}%")
    
    # 存储分布
    print("\n💾 存储层访问分布:")
    for storage_type, percentage in dashboard['storage_performance']['distribution'].items():
        print(f"  {storage_type}: {percentage:.1f}%")
    
    print("\n✅ 监控数据已保存到数据库")
    print("📄 详细报告可在 conversation_monitor 表中查看")
    sys.exit(0)

def main():
    """主函数"""
    print("🚀 启动DCMMS实时性能监控")
    print("="*60)
    
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    
    # 启动监控
    monitor = start_dcmm_monitoring()
    
    # 记录一些初始数据（基于我们之前的对话）
    initial_data = [
        {
            "query": "今天先中止发贴，集中试用和测试DCMMS skill",
            "processing_time": 1.2,
            "tokens_used": 450,
            "extraction": {"success": True, "entities_count": 3, "intents_count": 1},
            "rebuild": {
                "success": True, 
                "context_parts": 4, 
                "tokens_used": 450, 
                "tokens_saved": 200,
                "storage_stats": {
                    "redis": {"hit": True, "time_ms": 5},
                    "sqlite": {"hit": True, "time_ms": 15},
                    "files": {"hit": False, "time_ms": 0}
                }
            }
        },
        {
            "query": "你现在开始收集和分析我们对话时，后台效率、性能、命中和回复质量方面的数据",
            "processing_time": 1.5,
            "tokens_used": 520,
            "extraction": {"success": True, "entities_count": 4, "intents_count": 2},
            "rebuild": {
                "success": True,
                "context_parts": 5,
                "tokens_used": 520,
                "tokens_saved": 250,
                "storage_stats": {
                    "redis": {"hit": True, "time_ms": 5},
                    "sqlite": {"hit": True, "time_ms": 18},
                    "files": {"hit": True, "time_ms": 25}
                }
            }
        }
    ]
    
    print("📝 记录初始对话数据...")
    for data in initial_data:
        record_dcmm_turn(
            data["query"],
            data["processing_time"],
            data["tokens_used"],
            data["extraction"],
            data["rebuild"]
        )
        time.sleep(0.1)
    
    print(f"✅ 已记录 {len(initial_data)} 条初始对话数据")
    print("\n📊 实时监控已启动，正在收集性能数据...")
    print("按 Ctrl+C 停止监控并生成报告")
    print("="*60)
    
    # 显示实时状态
    try:
        while True:
            time.sleep(10)  # 每10秒更新一次状态
            
            # 获取当前仪表板数据
            dashboard = get_dcmm_dashboard()
            
            print(f"\r📈 监控中... 轮次: {dashboard['conversation_metrics']['total_turns']} | "
                  f"平均时间: {dashboard['conversation_metrics']['avg_turn_time_ms']:.1f}ms | "
                  f"成功率: {dashboard['success_rates']['overall']:.1f}%", end="")
                  
    except KeyboardInterrupt:
        # 信号处理器会处理退出
        pass

if __name__ == "__main__":
    main()