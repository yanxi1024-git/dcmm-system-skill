"""
动态上下文内存管理器
主入口类，整合所有功能
"""

import uuid
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from loguru import logger

from ..core.conversation_extractor import ConversationExtractor
from ..core.context_rebuilder import ContextRebuilder
from ..storage.redis_client import get_redis_client
from ..storage.sqlite_client import get_sqlite_client


class DynamicContextMemoryManager:
    """
    动态上下文内存管理器
    主入口类，提供完整的对话管理功能
    """
    
    def __init__(self, user_id: str = "default_user",
                 max_context_tokens: int = 8000,
                 compression_ratio: float = 0.7):
        """
        初始化管理器
        
        Args:
            user_id: 用户ID
            max_context_tokens: 最大上下文Token数
            compression_ratio: 压缩比例
        """
        self.user_id = user_id
        self.max_context_tokens = max_context_tokens
        self.compression_ratio = compression_ratio
        
        # 初始化组件
        self.extractor = ConversationExtractor()
        self.rebuilder = ContextRebuilder(max_context_tokens, compression_ratio)
        
        # 初始化存储
        self.redis_client = get_redis_client()
        self.sqlite_client = get_sqlite_client()
        
        # 当前会话信息
        self.current_session_id: Optional[str] = None
        self.current_conversation_history: List[Dict[str, Any]] = []
        
        logger.info(f"动态上下文内存管理器初始化完成 (user_id={user_id})")
    
    def start_session(self, session_id: Optional[str] = None) -> str:
        """
        开始新会话
        
        Args:
            session_id: 会话ID，None则自动生成
        
        Returns:
            str: 会话ID
        """
        if session_id is None:
            session_id = f"session_{uuid.uuid4().hex[:16]}"
        
        self.current_session_id = session_id
        self.current_conversation_history = []
        
        # 保存会话信息到数据库
        session_data = {
            "session_id": session_id,
            "user_id": self.user_id,
            "start_time": datetime.now().isoformat(),
            "status": "active"
        }
        self.sqlite_client.create_session(session_data)
        
        # 更新Redis中的用户会话列表
        self.redis_client.sadd(f"user:{self.user_id}:sessions", session_id)
        
        logger.info(f"新会话开始: {session_id}")
        
        return session_id
    
    def process_message(self, user_message: str,
                       llm_callback: Optional[Callable[[str], str]] = None,
                       reset_session: bool = True) -> Dict[str, Any]:
        """
        处理用户消息（完整流程）
        
        Args:
            user_message: 用户消息
            llm_callback: LLM回调函数，用于获取回复
            reset_session: 是否重置会话上下文
        
        Returns:
            Dict: 包含回复和元信息的字典
        """
        logger.info(f"处理用户消息: {user_message[:50]}...")
        
        # 1. 确保有活跃会话
        if not self.current_session_id:
            self.start_session()
        
        # 2. 从存储加载上下文信息
        user_preferences = self._load_user_preferences()
        project_context = self._load_project_context()
        task_context = self._load_task_context()
        
        # 3. 提取当前会话的关键信息
        key_info = self.extractor.extract_from_conversation(
            self.current_conversation_history[-10:]  # 最近10轮
        )
        
        # 4. 更新存储（保证数据持久化）
        self._update_storage(key_info)
        
        # 5. 重建上下文
        rebuilt_context = self.rebuilder.rebuild_context(
            user_query=user_message,
            key_info=key_info,
            user_preferences=user_preferences,
            project_context=project_context,
            task_context=task_context
        )
        
        # 6. 格式化上下文为LLM可用格式
        formatted_context = self.rebuilder.format_for_llm(rebuilt_context)
        
        # 7. 获取LLM回复
        llm_response = ""
        if llm_callback:
            try:
                llm_response = llm_callback(formatted_context)
            except Exception as e:
                logger.error(f"LLM调用失败: {e}")
                llm_response = "抱歉，处理您的请求时出现了错误。"
        else:
            llm_response = "（LLM回调未设置，无法生成回复）"
        
        # 8. 记录对话
        conversation_data = {
            "session_id": self.current_session_id,
            "turn_id": len(self.current_conversation_history) + 1,
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "llm_response": llm_response,
            "context_tokens": rebuilt_context.total_tokens,
            "total_tokens": rebuilt_context.total_tokens + self._estimate_tokens(llm_response)
        }
        
        # 保存到数据库
        conversation_id = self.sqlite_client.save_conversation(conversation_data)
        
        # 添加到当前会话历史
        self.current_conversation_history.append({
            "user_message": user_message,
            "llm_response": llm_response,
            "extracted_info": key_info,
            "context_tokens": rebuilt_context.total_tokens
        })
        
        # 9. 更新会话信息
        self.sqlite_client.update_session(
            self.current_session_id,
            {
                "conversation_count": len(self.current_conversation_history),
                "last_activity": datetime.now().isoformat()
            }
        )
        
        # 10. 记录性能指标
        self.sqlite_client.record_performance_metric(
            metric_name="context_rebuild_tokens",
            metric_value=rebuilt_context.total_tokens,
            context={"session_id": self.current_session_id}
        )
        
        result = {
            "response": llm_response,
            "conversation_id": conversation_id,
            "session_id": self.current_session_id,
            "context_tokens": rebuilt_context.total_tokens,
            "metadata": {
                "section_count": len(rebuilt_context.sections),
                "extraction_summary": {
                    "entities": len(key_info.get("entities", [])),
                    "intents": len(key_info.get("intents", [])),
                    "decisions": len(key_info.get("decisions", [])),
                    "actions": len(key_info.get("actions", []))
                }
            }
        }
        
        logger.info(f"消息处理完成，使用 {rebuilt_context.total_tokens} tokens")
        
        return result
    
    def quick_query(self, query_type: str, **kwargs) -> Any:
        """
        快速查询接口
        
        Args:
            query_type: 查询类型
            **kwargs: 查询参数
        
        Returns:
            Any: 查询结果
        """
        # 优先从Redis查询
        redis_result = self._query_redis(query_type, **kwargs)
        if redis_result is not None:
            return redis_result
        
        # 从SQLite查询
        sqlite_result = self._query_sqlite(query_type, **kwargs)
        if sqlite_result is not None:
            # 回填Redis
            self._cache_to_redis(query_type, sqlite_result, **kwargs)
            return sqlite_result
        
        # 从记忆文件查询（如果需要）
        memory_result = self._query_memory_files(query_type, **kwargs)
        if memory_result is not None:
            # 更新SQLite和Redis
            self._update_sqlite(query_type, memory_result, **kwargs)
            self._cache_to_redis(query_type, memory_result, **kwargs)
            return memory_result
        
        return None
    
    def update_setting(self, setting_key: str, setting_value: Any,
                      category: str = "general") -> bool:
        """
        更新用户设置
        
        Args:
            setting_key: 设置键
            setting_value: 设置值
            category: 设置类别
        
        Returns:
            bool: 是否成功
        """
        # 更新SQLite
        success = self.sqlite_client.set_user_setting(
            self.user_id, setting_key, setting_value, category
        )
        
        if success:
            # 更新Redis
            self.redis_client.hset(
                f"user:{self.user_id}:preferences",
                setting_key,
                setting_value
            )
            
            logger.info(f"用户设置已更新: {setting_key} = {setting_value}")
        
        return success
    
    def get_setting(self, setting_key: str) -> Any:
        """
        获取用户设置
        
        Args:
            setting_key: 设置键
        
        Returns:
            Any: 设置值
        """
        # 优先从Redis获取
        redis_value = self.redis_client.hget(
            f"user:{self.user_id}:preferences",
            setting_key
        )
        
        if redis_value is not None:
            return redis_value
        
        # 从SQLite获取
        sqlite_result = self.sqlite_client.get_user_setting(
            self.user_id, setting_key
        )
        
        if sqlite_result:
            # 回填Redis
            self.redis_client.hset(
                f"user:{self.user_id}:preferences",
                setting_key,
                sqlite_result["setting_value"]
            )
            return sqlite_result["setting_value"]
        
        return None
    
    def get_session_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取当前会话历史
        
        Args:
            limit: 限制数量
        
        Returns:
            List[Dict]: 会话历史
        """
        if not self.current_session_id:
            return []
        
        return self.sqlite_client.get_session_conversations(
            self.current_session_id, limit
        )
    
    def end_session(self) -> bool:
        """
        结束当前会话
        
        Returns:
            bool: 是否成功
        """
        if not self.current_session_id:
            return False
        
        # 结束会话
        success = self.sqlite_client.end_session(self.current_session_id)
        
        if success:
            logger.info(f"会话已结束: {self.current_session_id}")
            self.current_session_id = None
            self.current_conversation_history = []
        
        return success
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        获取系统状态
        
        Returns:
            Dict: 系统状态信息
        """
        # Redis状态
        redis_info = self.redis_client.get_memory_usage()
        
        # SQLite状态
        sqlite_info = self.sqlite_client.get_database_info()
        
        # 会话统计
        session_count = len(self.sqlite_client.get_user_sessions(self.user_id))
        
        return {
            "redis": {
                "connected": self.redis_client.is_connected(),
                "memory_usage": redis_info.get("used_memory_human", "unknown"),
                "total_keys": redis_info.get("total_keys", 0)
            },
            "sqlite": {
                "connected": True,
                "file_size_mb": sqlite_info.get("file_size_mb", 0),
                "table_count": sqlite_info.get("table_count", 0),
                "total_records": sqlite_info.get("total_records", 0)
            },
            "sessions": {
                "current_session": self.current_session_id,
                "total_sessions": session_count,
                "current_history_length": len(self.current_conversation_history)
            },
            "config": {
                "max_context_tokens": self.max_context_tokens,
                "compression_ratio": self.compression_ratio
            }
        }
    
    # ==================== 私有方法 ====================
    
    def _load_user_preferences(self) -> Dict[str, Any]:
        """加载用户偏好"""
        # 从Redis获取
        prefs = self.redis_client.hgetall(f"user:{self.user_id}:preferences")
        
        if not prefs:
            # 从SQLite获取
            settings = self.sqlite_client.get_user_settings(self.user_id)
            prefs = {s["setting_key"]: s["setting_value"] for s in settings}
            
            # 回填Redis
            for key, value in prefs.items():
                self.redis_client.hset(
                    f"user:{self.user_id}:preferences",
                    key, value
                )
        
        return prefs
    
    def _load_project_context(self) -> Optional[Dict[str, Any]]:
        """加载项目上下文"""
        # 从Redis获取当前活跃项目
        active_project = self.redis_client.get(f"user:{self.user_id}:active_project")
        
        if active_project:
            # 获取项目详情
            project_info = self.sqlite_client.get_project_by_name(active_project)
            if project_info:
                # 获取项目边界
                boundaries = self.sqlite_client.get_project_boundaries(
                    project_info["project_id"]
                )
                project_info["boundaries"] = [
                    b["boundary_value"] for b in boundaries if b.get("boundary_value")
                ]
                return project_info
        
        return None
    
    def _load_task_context(self) -> Optional[Dict[str, Any]]:
        """加载任务上下文"""
        # 获取活跃任务
        active_tasks = self.redis_client.zrange(
            f"user:{self.user_id}:active_tasks", 0, 9
        )
        
        # 获取即将执行的任务
        upcoming_tasks = self.sqlite_client.get_upcoming_tasks(lookahead_hours=24)
        
        return {
            "active_tasks": [{"title": t} for t in active_tasks],
            "upcoming_tasks": upcoming_tasks
        }
    
    def _update_storage(self, key_info: Dict[str, Any]):
        """更新存储"""
        # 更新实体
        for entity_data in key_info.get("entities", []):
            entity = {
                "entity_id": entity_data.get("entity_id"),
                "entity_type": entity_data.get("entity_type"),
                "name": entity_data.get("name"),
                "display_name": entity_data.get("display_name"),
                "importance_score": entity_data.get("importance_score", 0),
                "occurrence_count": entity_data.get("occurrence_count", 1)
            }
            self.sqlite_client.save_entity(entity)
        
        # 更新记忆摘要
        if key_info.get("summary"):
            summary = key_info["summary"]
            today = datetime.now().strftime("%Y-%m-%d")
            
            self.sqlite_client.save_memory_summary(
                memory_date=today,
                summary_type="daily",
                summary_key="conversation_summary",
                summary_value=summary.get("summary_text", ""),
                importance_score=0.8
            )
    
    def _query_redis(self, query_type: str, **kwargs) -> Any:
        """从Redis查询"""
        if query_type == "user_setting":
            key = kwargs.get("key")
            return self.redis_client.hget(
                f"user:{self.user_id}:preferences", key
            )
        elif query_type == "session_context":
            session_id = kwargs.get("session_id", self.current_session_id)
            return self.redis_client.hgetall(f"session:{session_id}:context")
        
        return None
    
    def _query_sqlite(self, query_type: str, **kwargs) -> Any:
        """从SQLite查询"""
        if query_type == "user_setting":
            key = kwargs.get("key")
            result = self.sqlite_client.get_user_setting(self.user_id, key)
            return result["setting_value"] if result else None
        elif query_type == "session_context":
            session_id = kwargs.get("session_id", self.current_session_id)
            return self.sqlite_client.get_session(session_id)
        
        return None
    
    def _query_memory_files(self, query_type: str, **kwargs) -> Any:
        """从记忆文件查询"""
        # 简化版，实际实现需要解析记忆文件
        return None
    
    def _cache_to_redis(self, query_type: str, data: Any, **kwargs):
        """缓存到Redis"""
        if query_type == "user_setting":
            key = kwargs.get("key")
            self.redis_client.hset(
                f"user:{self.user_id}:preferences",
                key, data
            )
    
    def _update_sqlite(self, query_type: str, data: Any, **kwargs):
        """更新SQLite"""
        if query_type == "user_setting":
            key = kwargs.get("key")
            self.sqlite_client.set_user_setting(self.user_id, key, data)
    
    def _estimate_tokens(self, text: str) -> int:
        """估算Token数"""
        import re
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        other_chars = len(text) - chinese_chars - sum(len(w) for w in re.findall(r'[a-zA-Z]+', text))
        return int(chinese_chars * 1.5 + english_words * 1.2 + other_chars * 0.5)


if __name__ == "__main__":
    # 测试管理器
    manager = DynamicContextMemoryManager(user_id="test_user")
    
    # 开始会话
    session_id = manager.start_session()
    print(f"会话ID: {session_id}")
    
    # 获取系统状态
    status = manager.get_system_status()
    print(f"系统状态: {json.dumps(status, indent=2, default=str)}")
    
    # 模拟LLM回调
    def mock_llm_callback(context: str) -> str:
        return "这是一个模拟的LLM回复。"
    
    # 处理消息
    result = manager.process_message(
        "测试消息：今天有什么任务？",
        llm_callback=mock_llm_callback
    )
    
    print(f"处理结果: {json.dumps(result, indent=2, default=str)}")
    
    # 结束会话
    manager.end_session()
    print("测试完成")
