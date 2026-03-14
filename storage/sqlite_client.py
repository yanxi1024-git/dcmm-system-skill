"""
SQLite客户端封装 - 简化版
提供DCMMS系统的SQLite数据库操作接口
"""

import sqlite3
import json
import os
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from loguru import logger
from .sqlite_schema import SQLiteSchema


class SQLiteClient:
    """SQLite客户端封装类"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化SQLite客户端
        """
        if db_path is None:
            db_path = SQLiteSchema.DEFAULT_DB_PATH
        
        # 确保目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        
        self.db_path = db_path
        self.connection = None
        self._initialize_database()
    
    def _initialize_database(self):
        """初始化数据库"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            
            # 启用外键约束
            self.connection.execute("PRAGMA foreign_keys = ON")
            
            # 创建所有表
            self._create_tables()
            
            # 插入默认数据
            self._insert_default_data()
            
            logger.info(f"SQLite数据库初始化完成: {self.db_path}")
            
        except Exception as e:
            logger.error(f"SQLite数据库初始化失败: {e}")
            raise
    
    def _create_tables(self):
        """创建所有表"""
        cursor = self.connection.cursor()
        table_definitions = SQLiteSchema.get_table_definitions()
        
        for table_name, create_sql in table_definitions.items():
            try:
                cursor.execute(create_sql)
                logger.debug(f"创建表: {table_name}")
            except Exception as e:
                logger.error(f"创建表 {table_name} 失败: {e}")
        
        self.connection.commit()
    
    def _insert_default_data(self):
        """插入默认数据"""
        cursor = self.connection.cursor()
        default_data = SQLiteSchema.get_default_data()
        
        for table_name, data_list in default_data.items():
            for data in data_list:
                try:
                    # 检查是否已存在
                    if "config_key" in data:
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE config_key = ?", 
                                     (data["config_key"],))
                        count = cursor.fetchone()[0]
                        if count == 0:
                            # 插入数据
                            columns = list(data.keys())
                            placeholders = ", ".join(["?"] * len(columns))
                            sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                            cursor.execute(sql, list(data.values()))
                            logger.debug(f"插入默认数据: {table_name} - {data.get('config_key', 'unknown')}")
                except Exception as e:
                    logger.error(f"插入默认数据失败 {table_name}: {e}")
        
        self.connection.commit()
    
    # ==================== 通用操作方法 ====================
    
    def execute(self, sql: str, params: Tuple = ()) -> sqlite3.Cursor:
        """执行SQL语句"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, params)
            return cursor
        except Exception as e:
            logger.error(f"执行SQL失败: {sql}, 错误: {e}")
            raise
    
    def fetch_one(self, sql: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """获取单条记录"""
        try:
            cursor = self.execute(sql, params)
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"获取单条记录失败: {sql}, 错误: {e}")
            return None
    
    def fetch_all(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """获取所有记录"""
        try:
            cursor = self.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取所有记录失败: {sql}, 错误: {e}")
            return []
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """插入记录"""
        try:
            columns = list(data.keys())
            placeholders = ", ".join(["?"] * len(columns))
            sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
            
            cursor = self.execute(sql, tuple(data.values()))
            self.connection.commit()
            
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"插入记录失败 {table}: {e}")
            self.connection.rollback()
            return -1
    
    def update(self, table: str, data: Dict[str, Any], where: str, where_params: Tuple = ()) -> int:
        """更新记录"""
        try:
            set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
            sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
            
            params = tuple(data.values()) + where_params
            cursor = self.execute(sql, params)
            self.connection.commit()
            
            return cursor.rowcount
        except Exception as e:
            logger.error(f"更新记录失败 {table}: {e}")
            self.connection.rollback()
            return 0
    
    # ==================== 业务特定方法 ====================
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        sql = "SELECT * FROM users WHERE user_id = ?"
        return self.fetch_one(sql, (user_id,))
    
    def create_user(self, user_data: Dict[str, Any]) -> int:
        """创建用户"""
        return self.insert("users", user_data)
    
    def get_user_setting(self, user_id: str, setting_key: str) -> Optional[Dict[str, Any]]:
        """获取用户设置"""
        sql = "SELECT * FROM user_settings WHERE user_id = ? AND setting_key = ?"
        return self.fetch_one(sql, (user_id, setting_key))
    
    def set_user_setting(self, user_id: str, setting_key: str, setting_value: Any, 
                         category: str = "general") -> bool:
        """设置用户设置"""
        existing = self.get_user_setting(user_id, setting_key)
        
        data = {
            "user_id": user_id,
            "setting_key": setting_key,
            "setting_value": str(setting_value),
            "category": category,
            "updated_at": datetime.now().isoformat()
        }
        
        if existing:
            rows = self.update("user_settings", data, "user_id = ? AND setting_key = ?", (user_id, setting_key))
            return rows > 0
        else:
            data["created_at"] = datetime.now().isoformat()
            row_id = self.insert("user_settings", data)
            return row_id > 0
    
    def create_session(self, session_data: Dict[str, Any]) -> int:
        """创建会话"""
        return self.insert("sessions", session_data)
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        sql = "SELECT * FROM sessions WHERE session_id = ?"
        return self.fetch_one(sql, (session_id,))
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> int:
        """更新会话信息"""
        updates["last_activity"] = datetime.now().isoformat()
        return self.update("sessions", updates, "session_id = ?", (session_id,))
    
    def save_conversation(self, conversation_data: Dict[str, Any]) -> int:
        """保存对话记录"""
        return self.insert("conversations", conversation_data)
    
    def get_session_conversations(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取会话的对话记录"""
        sql = """
        SELECT * FROM conversations 
        WHERE session_id = ? 
        ORDER BY turn_id DESC 
        LIMIT ?
        """
        return self.fetch_all(sql, (session_id, limit))
    
    def get_config(self, config_key: str) -> Optional[Dict[str, Any]]:
        """获取系统配置"""
        sql = "SELECT * FROM system_configs WHERE config_key = ?"
        return self.fetch_one(sql, (config_key,))
    
    def set_config(self, config_key: str, config_value: Any, 
                  config_type: str = "string", category: str = "general",
                  description: str = "") -> bool:
        """设置系统配置"""
        existing = self.get_config(config_key)
        
        data = {
            "config_key": config_key,
            "config_value": str(config_value),
            "config_type": config_type,
            "category": category,
            "description": description,
            "updated_at": datetime.now().isoformat()
        }
        
        if existing:
            rows = self.update("system_configs", data, "config_key = ?", (config_key,))
            return rows > 0
        else:
            data["created_at"] = datetime.now().isoformat()
            row_id = self.insert("system_configs", data)
            return row_id > 0
    
    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        info = {}
        
        # 获取表列表
        tables = self.fetch_all("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """)
        
        info["tables"] = [table["name"] for table in tables]
        info["table_count"] = len(tables)
        
        # 获取数据库文件大小
        try:
            file_size = os.path.getsize(self.db_path)
            info["file_size_bytes"] = file_size
            info["file_size_mb"] = round(file_size / (1024 * 1024), 2)
        except:
            info["file_size_bytes"] = 0
            info["file_size_mb"] = 0
        
        # 获取总记录数
        total_records = 0
        for table in info["tables"]:
            try:
                count_result = self.fetch_one(f"SELECT COUNT(*) as count FROM {table}")
                if count_result:
                    total_records += count_result["count"]
            except:
                pass
        
        info["total_records"] = total_records
        
        return info
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("SQLite数据库连接已关闭")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


# 全局SQLite客户端实例
_sqlite_client: Optional[SQLiteClient] = None

def get_sqlite_client() -> SQLiteClient:
    """获取全局SQLite客户端实例"""
    global _sqlite_client
    if _sqlite_client is None:
        _sqlite_client = SQLiteClient()
    return _sqlite_client


if __name__ == "__main__":
    # 测试SQLite客户端
    with get_sqlite_client() as client:
        # 测试数据库信息
        db_info = client.get_database_info()
        print(f"数据库信息: {db_info}")
        
        # 测试配置操作
        client.set_config("test.config", "test_value", "string", "test", "测试配置")
        config = client.get_config("test.config")
        print(f"测试配置: {config}")
        
        print("SQLite客户端测试完成")
