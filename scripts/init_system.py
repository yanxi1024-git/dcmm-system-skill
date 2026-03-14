#!/usr/bin/env python3
"""
系统初始化脚本
初始化DCMMS系统的数据库和配置
"""

import os
import sys
import argparse
from pathlib import Path
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from storage.sqlite_client import SQLiteClient
from storage.redis_client import RedisClient


def init_directories():
    """初始化目录结构"""
    directories = [
        "data",
        "logs",
        "config",
        "backups"
    ]
    
    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(exist_ok=True)
        logger.info(f"目录已创建/确认: {directory}")


def init_sqlite_database():
    """初始化SQLite数据库"""
    logger.info("初始化SQLite数据库...")
    
    try:
        client = SQLiteClient()
        
        # 获取数据库信息
        db_info = client.get_database_info()
        logger.info(f"数据库初始化完成")
        logger.info(f"  - 表数量: {db_info['table_count']}")
        logger.info(f"  - 总记录数: {db_info['total_records']}")
        
        client.close()
        return True
    except Exception as e:
        logger.error(f"SQLite数据库初始化失败: {e}")
        return False


def init_redis():
    """初始化Redis连接"""
    logger.info("初始化Redis连接...")
    
    try:
        client = RedisClient()
        
        if client.is_connected():
            memory_info = client.get_memory_usage()
            logger.info(f"Redis连接成功")
            logger.info(f"  - 内存使用: {memory_info.get('used_memory_human', 'unknown')}")
            logger.info(f"  - 总键数: {memory_info.get('total_keys', 0)}")
            
            # 设置系统启动标记
            client.set_with_ttl("system:status", "initialized", 3600)
            
            client.close()
            return True
        else:
            logger.error("Redis连接失败")
            return False
    except Exception as e:
        logger.error(f"Redis初始化失败: {e}")
        return False


def create_default_configs():
    """创建默认配置文件"""
    logger.info("创建默认配置...")
    
    env_file = project_root / "config" / ".env"
    
    if not env_file.exists():
        env_content = """# DCMMS系统环境配置

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# SQLite配置
SQLITE_DB_PATH=data/dcmm_system.db

# 系统配置
SYSTEM_NAME=DCMMS
SYSTEM_VERSION=1.0.0
LOG_LEVEL=INFO

# 性能配置
MAX_CONTEXT_TOKENS=8000
COMPRESSION_RATIO=0.7
DEFAULT_TTL=3600

# 监控配置
MONITORING_ENABLED=true
METRICS_RETENTION_DAYS=30
"""
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        logger.info(f"环境配置文件已创建: {env_file}")
    else:
        logger.info("环境配置文件已存在")


def init_system(args):
    """初始化系统"""
    logger.info("=" * 50)
    logger.info("开始初始化DCMMS系统")
    logger.info("=" * 50)
    
    # 1. 初始化目录
    init_directories()
    
    # 2. 初始化SQLite
    if not init_sqlite_database():
        logger.error("SQLite初始化失败，系统初始化中止")
        return False
    
    # 3. 初始化Redis
    if not init_redis():
        logger.warning("Redis初始化失败，某些功能可能不可用")
        if not args.skip_redis:
            return False
    
    # 4. 创建默认配置
    create_default_configs()
    
    logger.info("=" * 50)
    logger.info("DCMMS系统初始化完成！")
    logger.info("=" * 50)
    logger.info("下一步：")
    logger.info("1. 编辑 config/.env 文件配置系统参数")
    logger.info("2. 运行测试: python -m pytest tests/")
    logger.info("3. 开始使用: from core import DynamicContextMemoryManager")
    
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="DCMMS系统初始化脚本")
    parser.add_argument(
        "--skip-redis",
        action="store_true",
        help="跳过Redis初始化（如果Redis不可用）"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新初始化（会清除现有数据）"
    )
    
    args = parser.parse_args()
    
    # 配置日志
    logger.add(
        project_root / "logs" / "init.log",
        rotation="10 MB",
        retention="7 days",
        level="INFO"
    )
    
    # 执行初始化
    success = init_system(args)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
