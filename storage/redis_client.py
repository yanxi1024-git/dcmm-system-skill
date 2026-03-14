"""
Redis客户端封装
提供DCMMS系统的Redis操作接口
"""

import redis
import json
import pickle
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from loguru import logger
from .redis_schema import (
    RedisSchema, UserDataSchema, SessionDataSchema, EntityDataSchema,
    TaskDataSchema, ProjectDataSchema, MemoryDataSchema, 
    ConfigDataSchema, MonitorDataSchema
)


class RedisClient:
    """Redis客户端封装类"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, 
                 db: int = 0, password: Optional[str] = None,
                 decode_responses: bool = True):
        """
        初始化Redis客户端
        
        Args:
            host: Redis主机地址
            port: Redis端口
            db: Redis数据库编号
            password: Redis密码
            decode_responses: 是否解码响应
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=decode_responses,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                max_connections=20
            )
            # 测试连接
            self.client.ping()
            logger.info(f"Redis连接成功: {host}:{port}/{db}")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            raise
    
    def is_connected(self) -> bool:
        """检查Redis连接状态"""
        try:
            return self.client.ping()
        except:
            return False
    
    # ==================== 通用操作方法 ====================
    
    def set_with_ttl(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置键值对并指定TTL
        
        Args:
            key: 键名
            value: 值（自动序列化）
            ttl: 生存时间（秒），None表示永久
        
        Returns:
            bool: 是否成功
        """
        try:
            serialized_value = self._serialize(value)
            if ttl:
                return bool(self.client.setex(key, ttl, serialized_value))
            else:
                return bool(self.client.set(key, serialized_value))
        except Exception as e:
            logger.error(f"设置键值失败 {key}: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取键值
        
        Args:
            key: 键名
            default: 默认值
        
        Returns:
            Any: 反序列化后的值
        """
        try:
            value = self.client.get(key)
            if value is None:
                return default
            return self._deserialize(value)
        except Exception as e:
            logger.error(f"获取键值失败 {key}: {e}")
            return default
    
    def delete(self, *keys: str) -> int:
        """
        删除一个或多个键
        
        Returns:
            int: 删除的键数量
        """
        try:
            return self.client.delete(*keys)
        except Exception as e:
            logger.error(f"删除键失败 {keys}: {e}")
            return 0
    
    def exists(self, *keys: str) -> int:
        """
        检查键是否存在
        
        Returns:
            int: 存在的键数量
        """
        try:
            return self.client.exists(*keys)
        except Exception as e:
            logger.error(f"检查键存在失败 {keys}: {e}")
            return 0
    
    def expire(self, key: str, ttl: int) -> bool:
        """
        设置键的过期时间
        
        Args:
            key: 键名
            ttl: 生存时间（秒）
        
        Returns:
            bool: 是否成功
        """
        try:
            return bool(self.client.expire(key, ttl))
        except Exception as e:
            logger.error(f"设置过期时间失败 {key}: {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """
        获取键的剩余生存时间
        
        Returns:
            int: 剩余秒数，-1表示永久，-2表示键不存在
        """
        try:
            return self.client.ttl(key)
        except Exception as e:
            logger.error(f"获取TTL失败 {key}: {e}")
            return -2
    
    def keys(self, pattern: str = "*") -> List[str]:
        """
        查找匹配模式的键
        
        Args:
            pattern: 匹配模式
        
        Returns:
            List[str]: 匹配的键列表
        """
        try:
            return self.client.keys(pattern)
        except Exception as e:
            logger.error(f"查找键失败 {pattern}: {e}")
            return []
    
    # ==================== 数据结构特定方法 ====================
    
    # Hash操作
    def hset(self, key: str, field: str, value: Any) -> bool:
        """设置哈希字段"""
        try:
            serialized_value = self._serialize(value)
            return bool(self.client.hset(key, field, serialized_value))
        except Exception as e:
            logger.error(f"设置哈希字段失败 {key}.{field}: {e}")
            return False
    
    def hget(self, key: str, field: str, default: Any = None) -> Any:
        """获取哈希字段"""
        try:
            value = self.client.hget(key, field)
            if value is None:
                return default
            return self._deserialize(value)
        except Exception as e:
            logger.error(f"获取哈希字段失败 {key}.{field}: {e}")
            return default
    
    def hgetall(self, key: str) -> Dict[str, Any]:
        """获取所有哈希字段"""
        try:
            result = self.client.hgetall(key)
            return {k: self._deserialize(v) for k, v in result.items()}
        except Exception as e:
            logger.error(f"获取所有哈希字段失败 {key}: {e}")
            return {}
    
    # List操作
    def lpush(self, key: str, *values: Any) -> int:
        """从左侧推入列表"""
        try:
            serialized_values = [self._serialize(v) for v in values]
            return self.client.lpush(key, *serialized_values)
        except Exception as e:
            logger.error(f"左侧推入列表失败 {key}: {e}")
            return 0
    
    def rpush(self, key: str, *values: Any) -> int:
        """从右侧推入列表"""
        try:
            serialized_values = [self._serialize(v) for v in values]
            return self.client.rpush(key, *serialized_values)
        except Exception as e:
            logger.error(f"右侧推入列表失败 {key}: {e}")
            return 0
    
    def lrange(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """获取列表范围"""
        try:
            values = self.client.lrange(key, start, end)
            return [self._deserialize(v) for v in values]
        except Exception as e:
            logger.error(f"获取列表范围失败 {key}: {e}")
            return []
    
    # Set操作
    def sadd(self, key: str, *values: Any) -> int:
        """添加集合元素"""
        try:
            serialized_values = [self._serialize(v) for v in values]
            return self.client.sadd(key, *serialized_values)
        except Exception as e:
            logger.error(f"添加集合元素失败 {key}: {e}")
            return 0
    
    def smembers(self, key: str) -> List[Any]:
        """获取集合所有元素"""
        try:
            values = self.client.smembers(key)
            return [self._deserialize(v) for v in values]
        except Exception as e:
            logger.error(f"获取集合元素失败 {key}: {e}")
            return []
    
    # Sorted Set操作
    def zadd(self, key: str, mapping: Dict[Any, float]) -> int:
        """添加有序集合元素"""
        try:
            serialized_mapping = {self._serialize(k): v for k, v in mapping.items()}
            return self.client.zadd(key, serialized_mapping)
        except Exception as e:
            logger.error(f"添加有序集合元素失败 {key}: {e}")
            return 0
    
    def zrange(self, key: str, start: int = 0, end: int = -1, 
               withscores: bool = False) -> Union[List[Any], List[Tuple[Any, float]]]:
        """获取有序集合范围"""
        try:
            if withscores:
                result = self.client.zrange(key, start, end, withscores=True)
                return [(self._deserialize(k), v) for k, v in result]
            else:
                values = self.client.zrange(key, start, end)
                return [self._deserialize(v) for v in values]
        except Exception as e:
            logger.error(f"获取有序集合范围失败 {key}: {e}")
            return []
    
    def zrangebyscore(self, key: str, min_score: float, max_score: float,
                      withscores: bool = False) -> Union[List[Any], List[Tuple[Any, float]]]:
        """按分数范围获取有序集合元素"""
        try:
            if withscores:
                result = self.client.zrangebyscore(key, min_score, max_score, withscores=True)
                return [(self._deserialize(k), v) for k, v in result]
            else:
                values = self.client.zrangebyscore(key, min_score, max_score)
                return [self._deserialize(v) for v in values]
        except Exception as e:
            logger.error(f"按分数范围获取有序集合失败 {key}: {e}")
            return []
    
    # ==================== 高级操作方法 ====================
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """获取用户偏好设置"""
        schema = UserDataSchema.user_preferences(user_id)
        return self.hgetall(schema["key"]) or schema["structure"]
    
    def update_user_preferences(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """更新用户偏好设置"""
        schema = UserDataSchema.user_preferences(user_id)
        for field, value in updates.items():
            if not self.hset(schema["key"], field, value):
                return False
        self.expire(schema["key"], schema["ttl"])
        return True
    
    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """获取会话上下文"""
        schema = SessionDataSchema.session_context(session_id)
        return self.hgetall(schema["key"]) or schema["structure"]
    
    def update_session_context(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """更新会话上下文"""
        schema = SessionDataSchema.session_context(session_id)
        for field, value in updates.items():
            if not self.hset(schema["key"], field, value):
                return False
        self.expire(schema["key"], schema["ttl"])
        return True
    
    def save_conversation_turn(self, session_id: str, turn_id: int, 
                              conversation_data: Dict[str, Any]) -> bool:
        """保存对话轮次"""
        schema = SessionDataSchema.conversation_history(session_id, turn_id)
        for field, value in conversation_data.items():
            if not self.hset(schema["key"], field, value):
                return False
        self.expire(schema["key"], schema["ttl"])
        return True
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        schema = TaskDataSchema.task_status(task_id)
        return self.hgetall(schema["key"]) or schema["structure"]
    
    def update_task_status(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """更新任务状态"""
        schema = TaskDataSchema.task_status(task_id)
        for field, value in updates.items():
            if not self.hset(schema["key"], field, value):
                return False
        self.expire(schema["key"], schema["ttl"])
        return True
    
    def add_to_task_queue(self, task_id: str, scheduled_time: float) -> bool:
        """添加到任务队列"""
        schema = TaskDataSchema.task_queue()
        return bool(self.zadd(schema["key"], {task_id: scheduled_time}))
    
    def get_upcoming_tasks(self, lookahead_seconds: int = 300) -> List[Tuple[str, float]]:
        """获取即将执行的任务"""
        schema = TaskDataSchema.task_queue()
        now = datetime.now().timestamp()
        max_time = now + lookahead_seconds
        return self.zrangebyscore(schema["key"], now, max_time, withscores=True)
    
    # ==================== 序列化方法 ====================
    
    def _serialize(self, value: Any) -> str:
        """序列化值"""
        if isinstance(value, (str, int, float, bool)) or value is None:
            return json.dumps(value)
        elif isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False)
        else:
            # 使用pickle处理复杂对象
            return pickle.dumps(value).hex()
    
    def _deserialize(self, value: str) -> Any:
        """反序列化值"""
        try:
            # 先尝试JSON解析
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            try:
                # 再尝试pickle解析
                return pickle.loads(bytes.fromhex(value))
            except:
                # 返回原始字符串
                return value
    
    # ==================== 清理和维护方法 ====================
    
    def cleanup_expired_keys(self, pattern: str = "*") -> int:
        """清理过期键（实际由Redis自动处理，此方法用于监控）"""
        try:
            keys = self.keys(pattern)
            expired_count = 0
            for key in keys:
                if self.ttl(key) == -2:  # 键已过期但未删除
                    self.delete(key)
                    expired_count += 1
            return expired_count
        except Exception as e:
            logger.error(f"清理过期键失败: {e}")
            return 0
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        try:
            info = self.client.info("memory")
            return {
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "used_memory_peak": info.get("used_memory_peak", 0),
                "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
                "used_memory_rss": info.get("used_memory_rss", 0),
                "used_memory_rss_human": info.get("used_memory_rss_human", "0B"),
                "mem_fragmentation_ratio": info.get("mem_fragmentation_ratio", 0.0),
                "total_keys": self.client.dbsize()
            }
        except Exception as e:
            logger.error(f"获取内存使用情况失败: {e}")
            return {}
    
    def close(self):
        """关闭Redis连接"""
        try:
            self.client.close()
            logger.info("Redis连接已关闭")
        except:
            pass
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


# 全局Redis客户端实例
_redis_client: Optional[RedisClient] = None

def get_redis_client() -> RedisClient:
    """获取全局Redis客户端实例"""
    global _redis_client
    if _redis_client is None:
        # 从环境变量或配置文件读取配置
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))
        password = os.getenv("REDIS_PASSWORD")
        
        _redis_client = RedisClient(
            host=host,
            port=port,
            db=db,
            password=password
        )
    return _redis_client


if __name__ == "__main__":
    # 测试Redis客户端
    with get_redis_client() as client:
        # 测试基本操作
        client.set_with_ttl("test:key", {"hello": "world"}, 60)
        value = client.get("test:key")
        print(f"测试值: {value}")
        
        # 测试用户偏好
        client.update_user_preferences("user123", {"timezone": "Asia/Shanghai"})
        prefs = client.get_user_preferences("user123")
        print(f"用户偏好: {prefs}")
        
        # 测试内存使用
        memory_info = client.get_memory_usage()
        print(f"内存使用: {memory_info}")
