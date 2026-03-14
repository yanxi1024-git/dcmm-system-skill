"""
SQLite数据库设计 - 简化版
定义DCMMS系统中使用的SQLite表结构
"""

from typing import List, Dict, Any


class SQLiteSchema:
    """SQLite数据库表结构定义"""
    
    # 数据库文件路径
    DEFAULT_DB_PATH = "data/dcmm_system.db"
    
    @classmethod
    def get_table_definitions(cls) -> Dict[str, str]:
        """获取所有表定义SQL"""
        return {
            "users": cls._create_users_table(),
            "user_settings": cls._create_user_settings_table(),
            "sessions": cls._create_sessions_table(),
            "conversations": cls._create_conversations_table(),
            "system_configs": cls._create_system_configs_table(),
        }
    
    @staticmethod
    def _create_users_table() -> str:
        """创建用户表"""
        return """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            username TEXT,
            timezone TEXT DEFAULT 'Asia/Shanghai',
            language TEXT DEFAULT 'zh-CN',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    
    @staticmethod
    def _create_user_settings_table() -> str:
        """创建用户设置表"""
        return """
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            setting_key TEXT NOT NULL,
            setting_value TEXT,
            category TEXT DEFAULT 'general',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, setting_key)
        )
        """
    
    @staticmethod
    def _create_sessions_table() -> str:
        """创建会话表"""
        return """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT DEFAULT 'active',
            conversation_count INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0
        )
        """
    
    @staticmethod
    def _create_conversations_table() -> str:
        """创建对话表"""
        return """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            turn_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_message TEXT NOT NULL,
            llm_response TEXT NOT NULL,
            context_tokens INTEGER DEFAULT 0,
            response_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            UNIQUE(session_id, turn_id)
        )
        """
    
    @staticmethod
    def _create_system_configs_table() -> str:
        """创建系统配置表"""
        return """
        CREATE TABLE IF NOT EXISTS system_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,
            config_value TEXT NOT NULL,
            config_type TEXT DEFAULT 'string',
            category TEXT DEFAULT 'general',
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    
    @classmethod
    def get_default_data(cls) -> Dict[str, List[Dict[str, Any]]]:
        """获取默认数据"""
        return {
            "system_configs": [
                {
                    "config_key": "system.name",
                    "config_value": "DCMMS",
                    "config_type": "string",
                    "category": "system",
                    "description": "系统名称"
                },
                {
                    "config_key": "system.version",
                    "config_value": "1.0.0",
                    "config_type": "string",
                    "category": "system",
                    "description": "系统版本"
                },
                {
                    "config_key": "context.max_tokens",
                    "config_value": "8000",
                    "config_type": "number",
                    "category": "performance",
                    "description": "最大上下文Token数"
                },
                {
                    "config_key": "context.compression_ratio",
                    "config_value": "0.7",
                    "config_type": "number",
                    "category": "performance",
                    "description": "上下文压缩比例"
                },
                {
                    "config_key": "task.prep_time_offset",
                    "config_value": "300",
                    "config_type": "number",
                    "category": "scheduling",
                    "description": "任务提前准备时间（秒）"
                }
            ]
        }
