"""
Redis数据结构设计
定义DCMMS系统中使用的所有Redis数据结构
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json


class RedisSchema:
    """Redis数据结构定义类"""
    
    # 键前缀定义
    PREFIXES = {
        "user": "user",                    # 用户相关
        "session": "session",              # 会话相关
        "conversation": "conv",            # 对话相关
        "entity": "entity",                # 实体相关
        "task": "task",                    # 任务相关
        "project": "project",              # 项目相关
        "memory": "memory",                # 记忆相关
        "config": "config",                # 配置相关
        "monitor": "monitor",              # 监控相关
    }
    
    # TTL配置（秒）
    TTL_CONFIG = {
        "user_preferences": 86400,         # 24小时
        "session_context": 300,            # 5分钟
        "conversation_cache": 1800,        # 30分钟
        "entity_cache": 3600,              # 1小时
        "task_status": 600,                # 10分钟
        "project_boundaries": 7200,        # 2小时
        "memory_summary": 10800,           # 3小时
        "config_cache": 43200,             # 12小时
        "monitor_metrics": 300,            # 5分钟
    }
    
    @classmethod
    def get_key(cls, prefix: str, identifier: str, sub_key: Optional[str] = None) -> str:
        """生成Redis键"""
        key = f"{cls.PREFIXES[prefix]}:{identifier}"
        if sub_key:
            key = f"{key}:{sub_key}"
        return key
    
    @classmethod
    def get_ttl(cls, key_type: str) -> int:
        """获取键的TTL"""
        return cls.TTL_CONFIG.get(key_type, 3600)  # 默认1小时


class UserDataSchema:
    """用户数据结构"""
    
    @staticmethod
    def user_preferences(user_id: str) -> Dict[str, Any]:
        """用户偏好设置"""
        return {
            "key": RedisSchema.get_key("user", user_id, "preferences"),
            "structure": {
                "timezone": "Asia/Shanghai",
                "working_hours": "08:00-18:00",
                "language": "zh-CN",
                "model_preference": "deepseek",
                "notification_preferences": {
                    "telegram": True,
                    "email": False,
                    "push": True
                },
                "content_preferences": {
                    "technical_depth": "high",
                    "format_preference": "markdown",
                    "summary_length": "medium"
                }
            },
            "ttl": RedisSchema.get_ttl("user_preferences")
        }
    
    @staticmethod
    def user_sessions(user_id: str) -> Dict[str, Any]:
        """用户会话列表"""
        return {
            "key": RedisSchema.get_key("user", user_id, "sessions"),
            "structure": "sorted_set",  # 有序集合，按最后活动时间排序
            "ttl": RedisSchema.get_ttl("session_context")
        }


class SessionDataSchema:
    """会话数据结构"""
    
    @staticmethod
    def session_context(session_id: str) -> Dict[str, Any]:
        """会话上下文"""
        return {
            "key": RedisSchema.get_key("session", session_id, "context"),
            "structure": {
                "session_id": session_id,
                "user_id": "",
                "start_time": "",
                "last_activity": "",
                "conversation_count": 0,
                "extracted_entities": [],
                "current_intent": "",
                "context_summary": "",
                "token_usage": {
                    "total": 0,
                    "average": 0,
                    "last_n": []
                }
            },
            "ttl": RedisSchema.get_ttl("session_context")
        }
    
    @staticmethod
    def conversation_history(session_id: str, turn_id: int) -> Dict[str, Any]:
        """对话历史记录"""
        return {
            "key": RedisSchema.get_key("session", session_id, f"conv:{turn_id}"),
            "structure": {
                "turn_id": turn_id,
                "timestamp": "",
                "user_message": "",
                "llm_response": "",
                "extracted_info": {
                    "entities": [],
                    "intents": [],
                    "decisions": [],
                    "actions": []
                },
                "context_used": {
                    "tokens": 0,
                    "sources": []
                },
                "quality_metrics": {
                    "relevance": 0.0,
                    "accuracy": 0.0,
                    "completeness": 0.0
                }
            },
            "ttl": RedisSchema.get_ttl("conversation_cache")
        }


class EntityDataSchema:
    """实体数据结构"""
    
    @staticmethod
    def entity_cache(entity_type: str, entity_id: str) -> Dict[str, Any]:
        """实体缓存"""
        return {
            "key": RedisSchema.get_key("entity", f"{entity_type}:{entity_id}"),
            "structure": {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "name": "",
                "attributes": {},
                "relationships": [],
                "occurrence_count": 0,
                "last_mentioned": "",
                "importance_score": 0.0
            },
            "ttl": RedisSchema.get_ttl("entity_cache")
        }
    
    @staticmethod
    def entity_occurrences(entity_type: str, entity_id: str) -> Dict[str, Any]:
        """实体出现记录"""
        return {
            "key": RedisSchema.get_key("entity", f"{entity_type}:{entity_id}:occurrences"),
            "structure": "list",  # 列表，存储出现的时间戳和上下文
            "ttl": RedisSchema.get_ttl("entity_cache")
        }


class TaskDataSchema:
    """任务数据结构"""
    
    @staticmethod
    def task_queue() -> Dict[str, Any]:
        """任务队列"""
        return {
            "key": "task:queue",
            "structure": "sorted_set",  # 有序集合，按执行时间排序
            "ttl": 0  # 永久
        }
    
    @staticmethod
    def task_status(task_id: str) -> Dict[str, Any]:
        """任务状态"""
        return {
            "key": RedisSchema.get_key("task", task_id, "status"),
            "structure": {
                "task_id": task_id,
                "type": "",
                "scheduled_time": "",
                "status": "pending",  # pending, preparing, waiting_confirmation, executing, completed, failed
                "prep_start_time": "",
                "execution_history": [],
                "requires_confirmation": False,
                "confirmation_status": "pending",  # pending, approved, rejected
                "retry_count": 0,
                "last_error": "",
                "result": {}
            },
            "ttl": RedisSchema.get_ttl("task_status")
        }


class ProjectDataSchema:
    """项目数据结构"""
    
    @staticmethod
    def project_boundaries(project_name: str) -> Dict[str, Any]:
        """项目边界规则"""
        return {
            "key": RedisSchema.get_key("project", project_name, "boundaries"),
            "structure": {
                "project_name": project_name,
                "purpose": "",
                "boundaries": [],
                "allowed_actions": [],
                "restricted_actions": [],
                "cross_project_rules": [],
                "last_reviewed": "",
                "version": "1.0"
            },
            "ttl": RedisSchema.get_ttl("project_boundaries")
        }
    
    @staticmethod
    def project_context(project_name: str) -> Dict[str, Any]:
        """项目上下文"""
        return {
            "key": RedisSchema.get_key("project", project_name, "context"),
            "structure": {
                "current_tasks": [],
                "recent_decisions": [],
                "key_entities": [],
                "status_summary": "",
                "next_milestone": "",
                "risks_and_issues": []
            },
            "ttl": RedisSchema.get_ttl("project_boundaries")
        }


class MemoryDataSchema:
    """记忆数据结构"""
    
    @staticmethod
    def memory_summary(date: str) -> Dict[str, Any]:
        """每日记忆摘要"""
        return {
            "key": RedisSchema.get_key("memory", f"summary:{date}"),
            "structure": {
                "date": date,
                "key_decisions": [],
                "important_events": [],
                "learnings": [],
                "tasks_completed": [],
                "problems_solved": [],
                "next_day_plan": [],
                "summary_text": ""
            },
            "ttl": RedisSchema.get_ttl("memory_summary")
        }
    
    @staticmethod
    def memory_index(entity: str) -> Dict[str, Any]:
        """记忆索引"""
        return {
            "key": RedisSchema.get_key("memory", f"index:{entity}"),
            "structure": "set",  # 集合，存储相关记忆的ID
            "ttl": RedisSchema.get_ttl("memory_summary")
        }


class ConfigDataSchema:
    """配置数据结构"""
    
    @staticmethod
    def system_config(config_key: str) -> Dict[str, Any]:
        """系统配置"""
        return {
            "key": RedisSchema.get_key("config", config_key),
            "structure": {
                "key": config_key,
                "value": {},
                "description": "",
                "last_modified": "",
                "modified_by": "system"
            },
            "ttl": RedisSchema.get_ttl("config_cache")
        }


class MonitorDataSchema:
    """监控数据结构"""
    
    @staticmethod
    def performance_metrics(metric_name: str) -> Dict[str, Any]:
        """性能指标"""
        return {
            "key": RedisSchema.get_key("monitor", f"performance:{metric_name}"),
            "structure": {
                "metric_name": metric_name,
                "values": [],  # 时间序列数据
                "statistics": {
                    "avg": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "p95": 0.0,
                    "p99": 0.0
                },
                "alerts": [],
                "last_updated": ""
            },
            "ttl": RedisSchema.get_ttl("monitor_metrics")
        }
    
    @staticmethod
    def error_log(error_id: str) -> Dict[str, Any]:
        """错误日志"""
        return {
            "key": RedisSchema.get_key("monitor", f"error:{error_id}"),
            "structure": {
                "error_id": error_id,
                "timestamp": "",
                "module": "",
                "error_type": "",
                "error_message": "",
                "stack_trace": "",
                "context": {},
                "resolution": "",
                "resolved": False
            },
            "ttl": RedisSchema.get_ttl("monitor_metrics")
        }


# 导出所有schema类
__all__ = [
    "RedisSchema",
    "UserDataSchema",
    "SessionDataSchema",
    "EntityDataSchema",
    "TaskDataSchema",
    "ProjectDataSchema",
    "MemoryDataSchema",
    "ConfigDataSchema",
    "MonitorDataSchema"
]
