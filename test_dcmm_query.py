#!/usr/bin/env python3
"""
测试DCMMS系统：查询下午任务
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 激活虚拟环境
venv_path = project_root / "venv"
if venv_path.exists():
    activate_script = venv_path / "bin" / "activate_this.py"
    if activate_script.exists():
        with open(activate_script) as f:
            exec(f.read(), {'__file__': str(activate_script)})

# 直接导入模块
sys.path.insert(0, str(project_root / "core"))
sys.path.insert(0, str(project_root / "storage"))

try:
    from core.memory_manager import DynamicContextMemoryManager
except ImportError:
    # 尝试直接导入
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "memory_manager", 
        project_root / "core" / "memory_manager.py"
    )
    memory_manager = importlib.util.module_from_spec(spec)
    sys.modules["memory_manager"] = memory_manager
    spec.loader.exec_module(memory_manager)
    DynamicContextMemoryManager = memory_manager.DynamicContextMemoryManager

def test_dcmm_query():
    """测试DCMMS查询功能"""
    print("🧪 开始测试DCMMS系统查询功能")
    print("=" * 50)
    
    # 1. 创建管理器
    print("1. 初始化内存管理器...")
    manager = DynamicContextMemoryManager(user_id="test_user")
    
    # 2. 开始会话
    print("2. 开始新会话...")
    session_id = manager.start_session()
    print(f"   会话ID: {session_id}")
    
    # 3. 模拟一些对话历史（模拟上午的工作）
    print("3. 模拟对话历史...")
    
    # 模拟上午的对话
    morning_conversations = [
        {
            "user_message": "我们需要检查Moltbook社区状态",
            "llm_response": "好的，我来检查未读通知和社区热点。"
        },
        {
            "user_message": "发布今天的技术分析帖子",
            "llm_response": "已发布帖子：Decentralized AI Compute Networks"
        },
        {
            "user_message": "准备晚上22:00的第三个帖子",
            "llm_response": "明白，晚上22:00发布趋势观察帖子。"
        }
    ]
    
    # 保存到当前会话历史
    manager.current_conversation_history = morning_conversations
    
    # 4. 测试快速查询
    print("4. 测试快速查询功能...")
    
    # 查询"晚上"相关任务
    print("   查询'晚上'相关任务:")
    evening_tasks = manager.quick_query(
        "session_context",
        session_id=session_id
    )
    
    if evening_tasks:
        print(f"   查询结果: {evening_tasks}")
    else:
        print("   未找到相关记录（新系统，数据为空）")
    
    # 5. 测试系统状态
    print("5. 获取系统状态...")
    status = manager.get_system_status()
    print(f"   Redis连接: {'✅ 已连接' if status['redis']['connected'] else '❌ 未连接'}")
    print(f"   SQLite状态: ✅ 已连接")
    print(f"   当前会话: {status['sessions']['current_session']}")
    print(f"   历史长度: {status['sessions']['current_history_length']}")
    
    # 6. 测试设置管理
    print("6. 测试设置管理...")
    manager.update_setting("timezone", "Asia/Shanghai", "general")
    timezone = manager.get_setting("timezone")
    print(f"   时区设置: {timezone}")
    
    # 7. 测试会话历史
    print("7. 测试会话历史...")
    history = manager.get_session_history(limit=5)
    print(f"   历史记录数: {len(history)}")
    
    # 8. 结束会话
    print("8. 结束会话...")
    manager.end_session()
    
    print("=" * 50)
    print("✅ DCMMS系统基础功能测试完成")
    
    return True

if __name__ == "__main__":
    try:
        success = test_dcmm_query()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
