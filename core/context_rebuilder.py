"""
动态上下文重建器
基于用户查询和关键信息重建精准上下文
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from loguru import logger


@dataclass
class ContextSection:
    """上下文部分"""
    section_type: str  # system, user, project, task, history
    content: str
    priority: int  # 1-10, 1最高
    token_count: int = 0
    relevance_score: float = 1.0


@dataclass
class RebuiltContext:
    """重建的上下文"""
    sections: List[ContextSection]
    total_tokens: int
    user_query: str
    metadata: Dict[str, Any]


class ContextRebuilder:
    """
    动态上下文重建器
    根据用户查询和关键信息重建最精准、最简洁的上下文
    """
    
    def __init__(self, max_tokens: int = 8000, 
                 compression_ratio: float = 0.7):
        """
        初始化重建器
        
        Args:
            max_tokens: 最大Token数
            compression_ratio: 压缩比例
        """
        self.max_tokens = max_tokens
        self.compression_ratio = compression_ratio
        
        # 上下文优先级权重
        self.priority_weights = {
            "system": 1.0,      # 系统提示最高优先级
            "user": 0.9,        # 用户信息
            "project": 0.8,     # 项目上下文
            "task": 0.7,        # 任务上下文
            "history": 0.6,     # 历史对话
            "memory": 0.5       # 记忆摘要
        }
        
        logger.info(f"上下文重建器初始化完成 (max_tokens={max_tokens})")
    
    def rebuild_context(self, user_query: str, 
                       key_info: Dict[str, Any],
                       user_preferences: Optional[Dict] = None,
                       project_context: Optional[Dict] = None,
                       task_context: Optional[Dict] = None) -> RebuiltContext:
        """
        重建上下文
        
        Args:
            user_query: 用户查询
            key_info: 提取的关键信息
            user_preferences: 用户偏好
            project_context: 项目上下文
            task_context: 任务上下文
        
        Returns:
            RebuiltContext: 重建的上下文
        """
        logger.info(f"开始重建上下文，用户查询: {user_query[:50]}...")
        
        sections = []
        
        # 1. 构建系统提示部分
        system_section = self._build_system_section(key_info)
        sections.append(system_section)
        
        # 2. 构建用户上下文部分
        if user_preferences:
            user_section = self._build_user_section(user_preferences, key_info)
            sections.append(user_section)
        
        # 3. 构建项目上下文部分
        if project_context:
            project_section = self._build_project_section(project_context, key_info)
            sections.append(project_section)
        
        # 4. 构建任务上下文部分
        if task_context:
            task_section = self._build_task_section(task_context, key_info)
            sections.append(task_section)
        
        # 5. 构建相关历史部分
        history_section = self._build_history_section(key_info, user_query)
        if history_section:
            sections.append(history_section)
        
        # 6. 构建记忆摘要部分
        memory_section = self._build_memory_section(key_info, user_query)
        if memory_section:
            sections.append(memory_section)
        
        # 7. 优化和压缩
        optimized_sections = self._optimize_sections(sections)
        
        # 8. 计算总Token数
        total_tokens = sum(section.token_count for section in optimized_sections)
        
        # 9. 组装最终上下文
        context = RebuiltContext(
            sections=optimized_sections,
            total_tokens=total_tokens,
            user_query=user_query,
            metadata={
                "rebuild_time": datetime.now().isoformat(),
                "section_count": len(optimized_sections),
                "compression_ratio": self.compression_ratio,
                "max_tokens": self.max_tokens
            }
        )
        
        logger.info(f"上下文重建完成: {len(optimized_sections)}个部分, "
                   f"{total_tokens} tokens")
        
        return context
    
    def _build_system_section(self, key_info: Dict[str, Any]) -> ContextSection:
        """构建系统提示部分"""
        system_prompt = """你是一个智能助手，正在使用动态上下文记忆管理系统(DCMMS)。

核心原则：
1. 基于提供的上下文信息回答问题
2. 如果信息不足，明确说明
3. 保持回答简洁、准确、相关
4. 避免添加未经验证的信息

当前对话特点：
- 采用干净重启机制，上下文经过优化
- 只包含最相关和最重要的信息
- 所有信息都有明确的来源和时效性
"""
        
        # 根据关键信息调整系统提示
        if key_info.get("entities"):
            entity_types = set(e.get("entity_type") for e in key_info["entities"])
            if "project" in entity_types:
                system_prompt += "\n- 当前对话涉及项目管理相关内容"
            if "task" in entity_types:
                system_prompt += "\n- 当前对话涉及任务执行相关内容"
        
        return ContextSection(
            section_type="system",
            content=system_prompt,
            priority=1,
            token_count=self._estimate_tokens(system_prompt),
            relevance_score=1.0
        )
    
    def _build_user_section(self, user_preferences: Dict[str, Any], 
                           key_info: Dict[str, Any]) -> ContextSection:
        """构建用户上下文部分"""
        content_parts = ["用户偏好和设置："]
        
        # 基本信息
        if user_preferences.get("timezone"):
            content_parts.append(f"- 时区: {user_preferences['timezone']}")
        if user_preferences.get("language"):
            content_parts.append(f"- 语言: {user_preferences['language']}")
        
        # 工作偏好
        if user_preferences.get("working_hours"):
            content_parts.append(f"- 工作时间: {user_preferences['working_hours']}")
        
        # 模型偏好
        if user_preferences.get("model_preference"):
            content_parts.append(f"- 模型偏好: {user_preferences['model_preference']}")
        
        # 内容偏好
        if user_preferences.get("content_preferences"):
            prefs = user_preferences["content_preferences"]
            if prefs.get("technical_depth"):
                content_parts.append(f"- 技术深度: {prefs['technical_depth']}")
        
        content = "\n".join(content_parts)
        
        return ContextSection(
            section_type="user",
            content=content,
            priority=2,
            token_count=self._estimate_tokens(content),
            relevance_score=0.9
        )
    
    def _build_project_section(self, project_context: Dict[str, Any],
                              key_info: Dict[str, Any]) -> ContextSection:
        """构建项目上下文部分"""
        content_parts = ["项目上下文："]
        
        # 项目基本信息
        if project_context.get("name"):
            content_parts.append(f"- 项目名称: {project_context['name']}")
        if project_context.get("description"):
            content_parts.append(f"- 项目描述: {project_context['description']}")
        
        # 项目状态
        if project_context.get("status"):
            content_parts.append(f"- 项目状态: {project_context['status']}")
        
        # 项目边界
        if project_context.get("boundaries"):
            content_parts.append("- 项目边界:")
            for boundary in project_context["boundaries"][:3]:  # 最多3个边界
                content_parts.append(f"  * {boundary}")
        
        # 当前任务
        if project_context.get("current_tasks"):
            content_parts.append("- 当前任务:")
            for task in project_context["current_tasks"][:3]:  # 最多3个任务
                content_parts.append(f"  * {task}")
        
        content = "\n".join(content_parts)
        
        return ContextSection(
            section_type="project",
            content=content,
            priority=3,
            token_count=self._estimate_tokens(content),
            relevance_score=0.8
        )
    
    def _build_task_section(self, task_context: Dict[str, Any],
                           key_info: Dict[str, Any]) -> ContextSection:
        """构建任务上下文部分"""
        content_parts = ["任务上下文："]
        
        # 活跃任务
        if task_context.get("active_tasks"):
            content_parts.append("当前活跃任务：")
            for task in task_context["active_tasks"][:5]:  # 最多5个任务
                task_desc = f"- {task.get('title', '未命名任务')}"
                if task.get("status"):
                    task_desc += f" (状态: {task['status']})"
                if task.get("scheduled_time"):
                    task_desc += f" [计划: {task['scheduled_time']}]"
                content_parts.append(task_desc)
        
        # 即将执行的任务
        if task_context.get("upcoming_tasks"):
            content_parts.append("\n即将执行的任务：")
            for task in task_context["upcoming_tasks"][:3]:  # 最多3个
                content_parts.append(f"- {task.get('title', '未命名任务')} "
                                   f"[计划: {task.get('scheduled_time', '未安排')}]")
        
        content = "\n".join(content_parts)
        
        return ContextSection(
            section_type="task",
            content=content,
            priority=4,
            token_count=self._estimate_tokens(content),
            relevance_score=0.7
        )
    
    def _build_history_section(self, key_info: Dict[str, Any],
                              user_query: str) -> Optional[ContextSection]:
        """构建相关历史部分"""
        # 从key_info中提取相关历史
        relevant_history = []
        
        if key_info.get("summary") and key_info["summary"].get("key_points"):
            relevant_history = key_info["summary"]["key_points"][:5]  # 最多5个要点
        
        if not relevant_history:
            return None
        
        content_parts = ["相关历史对话要点："]
        for i, point in enumerate(relevant_history, 1):
            content_parts.append(f"{i}. {point}")
        
        content = "\n".join(content_parts)
        
        return ContextSection(
            section_type="history",
            content=content,
            priority=5,
            token_count=self._estimate_tokens(content),
            relevance_score=0.6
        )
    
    def _build_memory_section(self, key_info: Dict[str, Any],
                             user_query: str) -> Optional[ContextSection]:
        """构建记忆摘要部分"""
        memory_items = []
        
        # 提取的实体
        if key_info.get("entities"):
            entities = key_info["entities"][:5]  # 最多5个实体
            if entities:
                memory_items.append("相关实体：")
                for entity in entities:
                    entity_desc = f"- {entity.get('name', '未命名')}"
                    if entity.get("entity_type"):
                        entity_desc += f" ({entity['entity_type']})"
                    memory_items.append(entity_desc)
        
        # 提取的决策
        if key_info.get("decisions"):
            decisions = key_info["decisions"][:3]  # 最多3个决策
            if decisions:
                memory_items.append("\n相关决策：")
                for decision in decisions:
                    decision_desc = f"- {decision.get('description', '未描述决策')[:50]}"
                    if decision.get("status"):
                        decision_desc += f" [{decision['status']}]"
                    memory_items.append(decision_desc)
        
        # 提取的行动
        if key_info.get("actions"):
            actions = key_info["actions"][:3]  # 最多3个行动
            if actions:
                memory_items.append("\n相关行动：")
                for action in actions:
                    action_desc = f"- {action.get('description', '未描述行动')[:50]}"
                    if action.get("status"):
                        action_desc += f" [{action['status']}]"
                    memory_items.append(action_desc)
        
        if not memory_items:
            return None
        
        content = "\n".join(memory_items)
        
        return ContextSection(
            section_type="memory",
            content=content,
            priority=6,
            token_count=self._estimate_tokens(content),
            relevance_score=0.5
        )
    
    def _optimize_sections(self, sections: List[ContextSection]) -> List[ContextSection]:
        """优化和压缩上下文部分"""
        # 按优先级排序
        sorted_sections = sorted(sections, key=lambda s: s.priority)
        
        optimized = []
        total_tokens = 0
        max_allowed_tokens = int(self.max_tokens * self.compression_ratio)
        
        for section in sorted_sections:
            # 检查是否超过限制
            if total_tokens + section.token_count > max_allowed_tokens:
                # 压缩或跳过
                if section.priority <= 3:  # 高优先级部分尝试压缩
                    compressed_content = self._compress_content(section.content, 
                                                               max_allowed_tokens - total_tokens)
                    if compressed_content:
                        compressed_section = ContextSection(
                            section_type=section.section_type,
                            content=compressed_content,
                            priority=section.priority,
                            token_count=self._estimate_tokens(compressed_content),
                            relevance_score=section.relevance_score * 0.8
                        )
                        optimized.append(compressed_section)
                        total_tokens += compressed_section.token_count
                # 低优先级部分直接跳过
                continue
            
            optimized.append(section)
            total_tokens += section.token_count
        
        return optimized
    
    def _compress_content(self, content: str, max_tokens: int) -> Optional[str]:
        """压缩内容以适应Token限制"""
        current_tokens = self._estimate_tokens(content)
        
        if current_tokens <= max_tokens:
            return content
        
        # 简单的压缩策略：保留关键句子
        sentences = content.split('\n')
        compressed_parts = []
        current_count = 0
        
        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)
            if current_count + sentence_tokens <= max_tokens:
                compressed_parts.append(sentence)
                current_count += sentence_tokens
            else:
                break
        
        if compressed_parts:
            return '\n'.join(compressed_parts) + "\n..."
        
        return None
    
    def _estimate_tokens(self, text: str) -> int:
        """
        估算文本的Token数
        简化版：假设平均每个中文字符1.5个token，每个英文单词1个token
        """
        import re
        
        # 中文字符数
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        
        # 英文单词数
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        
        # 其他字符（标点、数字等）
        other_chars = len(text) - chinese_chars - sum(len(w) for w in re.findall(r'[a-zA-Z]+', text))
        
        # 估算token数
        estimated_tokens = int(chinese_chars * 1.5 + english_words * 1.2 + other_chars * 0.5)
        
        return max(1, estimated_tokens)
    
    def format_for_llm(self, context: RebuiltContext) -> str:
        """
        将重建的上下文格式化为LLM可用的格式
        
        Args:
            context: 重建的上下文
        
        Returns:
            str: 格式化后的上下文文本
        """
        parts = []
        
        for section in context.sections:
            if section.section_type == "system":
                parts.append(f"[系统提示]\n{section.content}")
            elif section.section_type == "user":
                parts.append(f"[用户信息]\n{section.content}")
            elif section.section_type == "project":
                parts.append(f"[项目上下文]\n{section.content}")
            elif section.section_type == "task":
                parts.append(f"[任务上下文]\n{section.content}")
            elif section.section_type == "history":
                parts.append(f"[相关历史]\n{section.content}")
            elif section.section_type == "memory":
                parts.append(f"[记忆摘要]\n{section.content}")
        
        # 添加用户查询
        parts.append(f"\n[用户查询]\n{context.user_query}")
        
        return "\n\n".join(parts)


if __name__ == "__main__":
    # 测试上下文重建器
    rebuilder = ContextRebuilder(max_tokens=2000)
    
    # 测试数据
    user_query = "今天的Moltbook发帖任务执行了吗？"
    
    key_info = {
        "entities": [
            {"name": "Moltbook", "entity_type": "project"},
            {"name": "发帖任务", "entity_type": "task"}
        ],
        "summary": {
            "key_points": [
                "早上发布了两个帖子",
                "Karma增长到42",
                "需要准备晚上22:00的帖子"
            ]
        }
    }
    
    user_preferences = {
        "timezone": "Asia/Shanghai",
        "language": "zh-CN",
        "working_hours": "08:00-18:00"
    }
    
    project_context = {
        "name": "Moltbook深度内容",
        "description": "Moltbook社区AI+区块链领域KOL项目",
        "status": "active",
        "current_tasks": ["每日发帖", "评论互动", "社区监控"]
    }
    
    task_context = {
        "active_tasks": [
            {"title": "准备晚上帖子", "status": "pending", "scheduled_time": "22:00"}
        ]
    }
    
    # 重建上下文
    context = rebuilder.rebuild_context(
        user_query=user_query,
        key_info=key_info,
        user_preferences=user_preferences,
        project_context=project_context,
        task_context=task_context
    )
    
    # 格式化输出
    formatted_context = rebuilder.format_for_llm(context)
    print(formatted_context)
    print(f"\n总Token数: {context.total_tokens}")
    print(f"部分数: {len(context.sections)}")
