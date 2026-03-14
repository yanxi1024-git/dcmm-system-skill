"""
SQLite数据库设计
定义DCMMS系统中使用的所有SQLite表结构
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import json


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
            "extracted_info": cls._create_extracted_info_table(),
            "entities": cls._create_entities_table(),
            "entity_occurrences": cls._create_entity_occurrences_table(),
            "tasks": cls._create_tasks_table(),
            "task_executions": cls._create_task_executions_table(),
            "projects": cls._create_projects_table(),
            "project_boundaries": cls._create_project_boundaries_table(),
            "memory_summaries": cls._create_memory_summaries_table(),
            "memory_details": cls._create_memory_details_table(),
            "system_configs": cls._create_system_configs_table(),
            "performance_metrics": cls._create_performance_metrics_table(),
            "error_logs": cls._create_error_logs_table(),
            "token_usage": cls._create_token_usage_table(),
            "quality_metrics": cls._create_quality_metrics_table(),
        }
    
    @classmethod
    def get_index_definitions(cls) -> Dict[str, List[str]]:
        """获取所有索引定义SQL"""
        return {
            "users": [
                "CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_users_updated ON users(updated_at)",
            ],
            "sessions": [
                "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_sessions_time ON sessions(start_time, last_activity)",
                "CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)",
            ],
            "conversations": [
                "CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)",
                "CREATE INDEX IF NOT EXISTS idx_conversations_turn ON conversations(session_id, turn_id)",
                "CREATE INDEX IF NOT EXISTS idx_conversations_time ON conversations(timestamp)",
            ],
            "entities": [
                "CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)",
                "CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)",
                "CREATE INDEX IF NOT EXISTS idx_entities_importance ON entities(importance_score DESC)",
            ],
            "tasks": [
                "CREATE INDEX IF NOT EXISTS idx_tasks_scheduled ON tasks(scheduled_time)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(task_type)",
            ],
            "projects": [
                "CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name)",
                "CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)",
            ],
            "memory_summaries": [
                "CREATE INDEX IF NOT EXISTS idx_memory_summaries_date ON memory_summaries(memory_date)",
                "CREATE INDEX IF NOT EXISTS idx_memory_summaries_type ON memory_summaries(summary_type)",
            ],
            "performance_metrics": [
                "CREATE INDEX IF NOT EXISTS idx_perf_metric_name ON performance_metrics(metric_name)",
                "CREATE INDEX IF NOT EXISTS idx_perf_timestamp ON performance_metrics(timestamp)",
            ],
        }
    
    @staticmethod
    def _create_users_table() -> str:
        """创建用户表"""
        return """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            username TEXT,
            email TEXT,
            timezone TEXT DEFAULT 'Asia/Shanghai',
            language TEXT DEFAULT 'zh-CN',
            status TEXT DEFAULT 'active',  -- active, inactive, suspended
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            metadata TEXT DEFAULT '{}'  -- JSON格式的额外信息
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
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, setting_key),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
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
            status TEXT DEFAULT 'active',  -- active, ended, timeout
            conversation_count INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            avg_response_time_ms INTEGER DEFAULT 0,
            context_summary TEXT,
            metadata TEXT DEFAULT '{}',
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
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
            response_time_ms INTEGER DEFAULT 0,
            model_used TEXT,
            temperature REAL DEFAULT 0.7,
            metadata TEXT DEFAULT '{}',
            UNIQUE(session_id, turn_id),
            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
        )
        """
    
    @staticmethod
    def _create_extracted_info_table() -> str:
        """创建提取信息表"""
        return """
        CREATE TABLE IF NOT EXISTS extracted_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            info_type TEXT NOT NULL,  -- entity, intent, decision, action, summary
            info_key TEXT NOT NULL,
            info_value TEXT,
            confidence_score REAL DEFAULT 1.0,
            metadata TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
        """
    
    @staticmethod
    def _create_entities_table() -> str:
        """创建实体表"""
        return """
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id TEXT UNIQUE NOT NULL,
            entity_type TEXT NOT NULL,  -- person, project, task, location, concept, etc.
            name TEXT NOT NULL,
            display_name TEXT,
            description TEXT,
            attributes TEXT DEFAULT '{}',  -- JSON格式的属性
            importance_score REAL DEFAULT 0.0,
            occurrence_count INTEGER DEFAULT 0,
            first_mentioned TIMESTAMP,
            last_mentioned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT DEFAULT '{}'
        )
        """
    
    @staticmethod
    def _create_entity_occurrences_table() -> str:
        """创建实体出现记录表"""
        return """
        CREATE TABLE IF NOT EXISTS entity_occurrences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id TEXT NOT NULL,
            conversation_id INTEGER NOT NULL,
            occurrence_context TEXT,  -- 出现时的上下文
            relevance_score REAL DEFAULT 1.0,
            mentioned_as TEXT,  -- 被提及的方式
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
        """
    
    @staticmethod
    def _create_tasks_table() -> str:
        """创建任务表"""
        return """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            task_type TEXT NOT NULL,  -- daily_posting, server_check, memory_maintenance, etc.
            title TEXT NOT NULL,
            description TEXT,
            scheduled_time TIMESTAMP NOT NULL,
            prep_start_offset INTEGER DEFAULT 300,  -- 提前准备时间（秒）
            status TEXT DEFAULT 'pending',  -- pending, preparing, waiting_confirmation, executing, completed, failed
            priority INTEGER DEFAULT 5,  -- 1-10，1最高
            requires_confirmation BOOLEAN DEFAULT FALSE,
            confirmation_status TEXT DEFAULT 'pending',  -- pending, approved, rejected
            max_retries INTEGER DEFAULT 3,
            retry_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT DEFAULT '{}'
        )
        """
    
    @staticmethod
    def _create_task_executions_table() -> str:
        """创建任务执行记录表"""
        return """
        CREATE TABLE IF NOT EXISTS task_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            execution_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL,  -- started, completed, failed
            result TEXT,
            error_message TEXT,
            execution_duration_ms INTEGER,
            resources_used TEXT DEFAULT '{}',  -- JSON格式的资源使用情况
            metadata TEXT DEFAULT '{}',
            FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
        )
        """
    
    @staticmethod
    def _create_projects_table() -> str:
        """创建项目表"""
        return """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            display_name TEXT,
            description TEXT,
            project_type TEXT NOT NULL,  -- development, operations, research, content
            status TEXT DEFAULT 'active',  -- active, completed, paused, archived
            owner_user_id TEXT,
            start_date DATE,
            target_completion_date DATE,
            actual_completion_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT DEFAULT '{}',
            FOREIGN KEY (owner_user_id) REFERENCES users(user_id) ON DELETE SET NULL
        )
        """
    
    @staticmethod
    def _create_project_boundaries_table() -> str:
        """创建项目边界表"""
        return """
        CREATE TABLE IF NOT EXISTS project_boundaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            boundary_type TEXT NOT NULL,  -- purpose, scope, allowed_actions, restricted_actions, cross_project
            boundary_key TEXT NOT NULL,
            boundary_value TEXT,
            description TEXT,
            priority INTEGER DEFAULT 5,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(project_id, boundary_type, boundary_key),
            FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
        )
        """
    
    @staticmethod
    def _create_memory_summaries_table() -> str:
        """创建记忆摘要表"""
        return """
        CREATE TABLE IF NOT EXISTS memory_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_date DATE NOT NULL,
            summary_type TEXT NOT NULL,  -- daily, weekly, monthly, project_specific
            summary_key TEXT NOT NULL,
            summary_value TEXT NOT NULL,
            importance_score REAL DEFAULT 0.0,
            source_type TEXT,  -- conversation, task, manual_entry
            source_id TEXT,  -- 来源ID（对话ID、任务ID等）
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT DEFAULT '{}',
            UNIQUE(memory_date, summary_type, summary_key)
        )
        """
    
    @staticmethod
    def _create_memory_details_table() -> str:
        """创建记忆详情表"""
        return """
        CREATE TABLE IF NOT EXISTS memory_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_summary_id INTEGER NOT NULL,
            detail_type TEXT NOT NULL,  -- decision, event, learning, task, problem
            detail_key TEXT NOT NULL,
            detail_value TEXT NOT NULL,
            context TEXT,
            related_entities TEXT DEFAULT '[]',  -- JSON数组
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (memory_summary_id) REFERENCES memory_summaries(id) ON DELETE CASCADE
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
            config_type TEXT DEFAULT 'string',  -- string, number, boolean, json, list
            category TEXT DEFAULT 'general',
            description TEXT,
            is_editable BOOLEAN DEFAULT TRUE,
            requires_restart BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by TEXT DEFAULT 'system'
        )
        """
    
    @staticmethod
    def _create_performance_metrics_table() -> str:
        """创建性能指标表"""
        return """
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            metric_unit TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            context TEXT DEFAULT '{}',  -- JSON格式的上下文信息
            tags TEXT DEFAULT '{}'  -- JSON格式的标签
        )
        """
    
    @staticmethod
    def _create_error_logs_table() -> str:
        """创建错误日志表"""
        return """
        CREATE TABLE IF NOT EXISTS error_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            error_id TEXT UNIQUE NOT NULL,
            error_type TEXT NOT NULL,  -- system, application, network, database, etc.
            error_code TEXT,
            error_message TEXT NOT NULL,
            module_name TEXT,
            function_name TEXT,
            stack_trace TEXT,
            severity TEXT DEFAULT 'error',  -- debug, info, warning, error, critical
            context TEXT DEFAULT '{}',
            resolved BOOLEAN DEFAULT FALSE,
            resolution TEXT,
            resolved_at TIMESTAMP,
            resolved_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    
    @staticmethod
    def _create_token_usage_table() -> str:
        """创建Token使用表"""
        return """
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            conversation_id INTEGER,
            model_name TEXT NOT NULL,
            context_tokens INTEGER DEFAULT 0,
            response_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            cost_estimate REAL DEFAULT 0.0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT DEFAULT '{}',
            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE SET NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL
        )
        """
    
    @staticmethod
    def _create_quality_metrics_table() -> str:
        """创建质量指标表"""
        return """
        CREATE TABLE IF NOT EXISTS quality_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            metric_type TEXT NOT NULL,  -- relevance, accuracy, completeness, hallucination_risk
            metric_value REAL NOT NULL,
            confidence REAL DEFAULT 1.0,
            evaluation_method TEXT,  -- automated, human, hybrid
            evaluator TEXT DEFAULT 'system',
            comments TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
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
                    "description": "系统名称",
                    "is_editable": False
                },
                {
                    "config_key": "system.version",
                    "config_value": "1.0.0",
                    "config_type": "string",
                    "category": "system",
                    "description": "系统版本",
                    "is_editable": False
                },
                {
                    "config_key": "context.max_tokens",
                    "config_value": "8000",
                    "config_type": "number",
                    "category": "performance",
                    "description": "最大上下文Token数",
                    "is_editable": True
                },
                {
                    "config_key": "context.compression_ratio",
                    "config_value": "0.7",
                    "config_type": "number",
                    "category": "performance",
                    "description": "上下文压缩比例",
                    "is_editable": True
                },
                {
                    "config_key": "task.prep_time_offset",
                    "config_value": "300",
                    "config_type": "number",
                    "category": "scheduling",
                    "description": "任务提前准备时间（秒）",
                    "is_editable": True
                },
                {
                    "config_key": "redis.default_ttl",
                    "config_value": "3600",
                    "config_type": "number",
                    "category": "storage",
                    "description": "Redis默认TTL（秒）",
                    "is_editable": True
                },
                {
                    "config_key": "monitoring.enabled",
                    "config_value": "true",
                    "config_type": "boolean",
                    "category": "mon