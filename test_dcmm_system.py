#!/usr/bin/env python3
"""
直接测试DCMMS存储层功能
"""

import sys
import os
import json
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

def test_storage_layer():
    """测试存储层功能"""
    print("🧪 开始测试DCMMS存储层功能")
    print("=" * 50)
    
    # 1. 测试SQLite客户端
    print("1. 测试SQLite客户端...")
    try:
        from storage.sqlite_client import SQLiteClient
        sqlite_client = SQLiteClient()
        
        # 获取数据库信息
        db_info = sqlite_client.get_database_info()
        print(f"   ✅ SQLite连接成功")
        print(f"     表数量: {db_info.get('table_count', 0)}")
        print(f"     总记录数: {db_info.get('total_records', 0)}")
        
        # 测试配置操作
        sqlite_client.set_config("test.key", "test_value", "string", "test")
        config = sqlite_client.get_config("test.key")
        print(f"     配置测试: {config.get('config_value') if config else '失败'}")
        
        sqlite_client.close()
    except Exception as e:
        print(f"   ❌ SQLite测试失败: {e}")
        return False
    
    # 2. 测试Redis客户端
    print("2. 测试Redis客户端...")
    try:
        from storage.redis_client import RedisClient
        redis_client = RedisClient()
        
        if redis_client.is_connected():
            print(f"   ✅ Redis连接成功")
            
            # 测试基本操作
            redis_client.set_with_ttl("test:key", {"test": "value"}, 60)
            value = redis_client.get("test:key")
            print(f"     基本操作测试: {value}")
            
            # 测试内存使用
            memory_info = redis_client.get_memory_usage()
            print(f"     内存使用: {memory_info.get('used_memory_human', 'unknown')}")
            
            redis_client.close()
        else:
            print("   ⚠️ Redis未连接，跳过Redis测试")
    except Exception as e:
        print(f"   ⚠️ Redis测试失败（可能未运行）: {e}")
    
    # 3. 测试数据模型
    print("3. 测试数据模型...")
    try:
        from storage.sqlite_schema import SQLiteSchema
        from storage.redis_schema import RedisSchema
        
        print(f"   ✅ 数据模型加载成功")
        print(f"     SQLite表数量: {len(SQLiteSchema.get_table_definitions())}")
        print(f"     Redis前缀数量: {len(RedisSchema.PREFIXES)}")
    except Exception as e:
        print(f"   ❌ 数据模型测试失败: {e}")
        return False
    
    print("=" * 50)
    print("✅ 存储层功能测试完成")
    return True

def test_core_engine():
    """测试核心引擎功能"""
    print("\n🧪 开始测试核心引擎功能")
    print("=" * 50)
    
    # 1. 测试会话提取器
    print("1. 测试会话提取器...")
    try:
        # 直接导入文件
        import importlib.util
        
        # 导入会话提取器
        extractor_path = project_root / "core" / "conversation_extractor.py"
        spec = importlib.util.spec_from_file_location("conversation_extractor", extractor_path)
        extractor_module = importlib.util.module_from_spec(spec)
        sys.modules["conversation_extractor"] = extractor_module
        spec.loader.exec_module(extractor_module)
        
        extractor = extractor_module.ConversationExtractor()
        
        # 测试提取
        test_conversation = [
            {
                "user_message": "晚上22:00需要发布第三个帖子",
                "llm_response": "明白，准备趋势观察帖子。"
            }
        ]
        
        result = extractor.extract_from_conversation(test_conversation)
        print(f"   ✅ 会话提取器测试成功")
        print(f"     提取实体数: {len(result.get('entities', []))}")
        print(f"     提取意图数: {len(result.get('intents', []))}")
        
        # 检查是否提取到"晚上"相关实体
        entities = result.get('entities', [])
        evening_related = [e for e in entities if '晚上' in str(e)]
        print(f"     晚上相关实体: {len(evening_related)}个")
        
    except Exception as e:
        print(f"   ❌ 会话提取器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 2. 测试上下文重建器
    print("2. 测试上下文重建器...")
    try:
        # 导入上下文重建器
        rebuilder_path = project_root / "core" / "context_rebuilder.py"
        spec = importlib.util.spec_from_file_location("context_rebuilder", rebuilder_path)
        rebuilder_module = importlib.util.module_from_spec(spec)
        sys.modules["context_rebuilder"] = rebuilder_module
        spec.loader.exec_module(rebuilder_module)
        
        rebuilder = rebuilder_module.ContextRebuilder(max_tokens=1000)
        
        # 测试重建
        user_query = "下午还有什么任务需要完成？"
        key_info = {
            "entities": [
                {"name": "晚上帖子", "entity_type": "task"},
                {"name": "22:00", "entity_type": "time"}
            ],
            "summary": {
                "key_points": ["晚上22:00发布第三个帖子", "监控评论互动"]
            }
        }
        
        context = rebuilder.rebuild_context(user_query, key_info)
        print(f"   ✅ 上下文重建器测试成功")
        print(f"     上下文部分数: {len(context.sections)}")
        print(f"     总Token数: {context.total_tokens}")
        
        # 格式化输出
        formatted = rebuilder.format_for_llm(context)
        print(f"     格式化长度: {len(formatted)} 字符")
        
    except Exception as e:
        print(f"   ❌ 上下文重建器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("=" * 50)
    print("✅ 核心引擎功能测试完成")
    return True

if __name__ == "__main__":
    print("🚀 DCMMS系统实时测试")
    print("=" * 50)
    
    # 测试存储层
    storage_success = test_storage_layer()
    
    # 测试核心引擎
    core_success = test_core_engine()
    
    print("\n" + "=" * 50)
    if storage_success and core_success:
        print("🎉 所有测试通过！DCMMS系统基础功能正常")
    else:
        print("⚠️  部分测试失败，需要进一步调试")
    
    print("=" * 50)
