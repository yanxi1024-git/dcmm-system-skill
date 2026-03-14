"""
会话关键信息提取器
从对话历史中提取关键信息
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from loguru import logger


@dataclass
class ExtractedEntity:
    """提取的实体"""
    entity_id: str
    entity_type: str
    name: str
    display_name: Optional[str] = None
    attributes: Dict[str, Any] = None
    importance_score: float = 0.0
    occurrence_count: int = 1
    context: str = ""
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}


@dataclass
class ExtractedIntent:
    """提取的意图"""
    intent_type: str  # query, instruction, confirmation, decision, etc.
    confidence: float = 1.0
    target_entity: Optional[str] = None
    action: Optional[str] = None
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class ExtractedDecision:
    """提取的决策"""
    decision_id: str
    decision_type: str
    description: str
    made_by: str
    timestamp: str
    status: str = "pending"  # pending, confirmed, executed, cancelled
    related_entities: List[str] = None
    
    def __post_init__(self):
        if self.related_entities is None:
            self.related_entities = []


@dataclass
class ExtractedAction:
    """提取的行动"""
    action_id: str
    action_type: str
    description: str
    target: Optional[str] = None
    status: str = "planned"  # planned, in_progress, completed, failed
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class ConversationSummary:
    """对话摘要"""
    summary_text: str
    key_points: List[str]
    topics: List[str]
    sentiment: str = "neutral"  # positive, negative, neutral
    urgency: str = "normal"  # urgent, high, normal, low
    completeness: float = 1.0


class ConversationExtractor:
    """
    会话关键信息提取器
    从对话历史中提取实体、意图、决策、行动和摘要
    """
    
    def __init__(self):
        """初始化提取器"""
        # 实体类型定义
        self.entity_types = {
            "person": ["人名", "用户", "开发者", "管理员"],
            "project": ["项目", "仓库", "系统", "模块"],
            "task": ["任务", "工作", "计划", "目标"],
            "location": ["位置", "路径", "目录", "文件"],
            "concept": ["概念", "技术", "方法", "策略"],
            "tool": ["工具", "软件", "库", "框架"],
            "time": ["时间", "日期", "期限", "周期"],
            "value": ["数值", "数量", "比例", "百分比"]
        }
        
        # 意图类型定义
        self.intent_patterns = {
            "query": ["是什么", "为什么", "怎么样", "如何", "查询", "查看"],
            "instruction": ["请", "需要", "应该", "必须", "执行", "开始"],
            "confirmation": ["同意", "确认", "批准", "可以", "好的", "行"],
            "rejection": ["不同意", "拒绝", "不行", "不可以", "不要"],
            "decision": ["决定", "选择", "确定", "采纳", "批准"],
            "question": ["?", "问", "疑问", "咨询"]
        }
        
        # 决策模式
        self.decision_patterns = [
            r"决定.*?(?:采用|使用|选择)",
            r"确认.*?(?:方案|计划|策略)",
            r"批准.*?(?:执行|实施|开始)",
            r"同意.*?(?:建议|提案|方案)"
        ]
        
        # 行动模式
        self.action_patterns = [
            r"需要.*?(?:完成|执行|实现)",
            r"应该.*?(?:做|完成|准备)",
            r"计划.*?(?:开发|测试|部署)",
            r"准备.*?(?:开始|执行|实施)"
        ]
        
        logger.info("会话提取器初始化完成")
    
    def extract_from_conversation(self, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        从对话历史中提取所有关键信息
        
        Args:
            conversation_history: 对话历史列表
        
        Returns:
            Dict: 包含所有提取信息的字典
        """
        logger.info(f"开始提取对话信息，共 {len(conversation_history)} 轮对话")
        
        # 合并所有对话文本
        full_text = self._merge_conversation_text(conversation_history)
        
        # 提取各类信息
        entities = self.extract_entities(full_text, conversation_history)
        intents = self.extract_intents(full_text, conversation_history)
        decisions = self.extract_decisions(full_text, conversation_history)
        actions = self.extract_actions(full_text, conversation_history)
        summary = self.generate_summary(full_text, conversation_history)
        
        result = {
            "entities": [asdict(e) for e in entities],
            "intents": [asdict(i) for i in intents],
            "decisions": [asdict(d) for d in decisions],
            "actions": [asdict(a) for a in actions],
            "summary": asdict(summary),
            "extraction_time": datetime.now().isoformat(),
            "conversation_count": len(conversation_history)
        }
        
        logger.info(f"提取完成：{len(entities)}个实体, {len(intents)}个意图, "
                   f"{len(decisions)}个决策, {len(actions)}个行动")
        
        return result
    
    def extract_entities(self, text: str, 
                        conversation_history: Optional[List[Dict]] = None) -> List[ExtractedEntity]:
        """
        提取文本中的实体
        
        Args:
            text: 文本内容
            conversation_history: 对话历史（用于上下文）
        
        Returns:
            List[ExtractedEntity]: 提取的实体列表
        """
        entities = []
        
        # 基于规则提取
        for entity_type, keywords in self.entity_types.items():
            for keyword in keywords:
                # 查找关键词
                pattern = rf"{keyword}[：:]\s*([^，。！？\n]+)"
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    entity_name = match.group(1).strip()
                    if entity_name and len(entity_name) > 1:
                        entity = ExtractedEntity(
                            entity_id=f"{entity_type}_{hash(entity_name) % 1000000:06d}",
                            entity_type=entity_type,
                            name=entity_name,
                            context=text[max(0, match.start() - 50):min(len(text), match.end() + 50)],
                            importance_score=self._calculate_entity_importance(entity_name, text)
                        )
                        entities.append(entity)
        
        # 去重和合并
        entities = self._deduplicate_entities(entities)
        
        return entities
    
    def extract_intents(self, text: str,
                       conversation_history: Optional[List[Dict]] = None) -> List[ExtractedIntent]:
        """
        提取文本中的意图
        
        Args:
            text: 文本内容
            conversation_history: 对话历史
        
        Returns:
            List[ExtractedIntent]: 提取的意图列表
        """
        intents = []
        
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    intent = ExtractedIntent(
                        intent_type=intent_type,
                        confidence=0.8 if pattern in text else 0.5,
                        action=self._extract_action_from_text(text)
                    )
                    intents.append(intent)
                    break  # 每种意图类型只取第一个匹配
        
        return intents
    
    def extract_decisions(self, text: str,
                         conversation_history: Optional[List[Dict]] = None) -> List[ExtractedDecision]:
        """
        提取文本中的决策
        
        Args:
            text: 文本内容
            conversation_history: 对话历史
        
        Returns:
            List[ExtractedDecision]: 提取的决策列表
        """
        decisions = []
        
        for pattern in self.decision_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                decision_text = match.group(0)
                decision = ExtractedDecision(
                    decision_id=f"decision_{hash(decision_text) % 1000000:06d}",
                    decision_type="strategic" if "战略" in text else "tactical",
                    description=decision_text,
                    made_by="user",  # 假设是用户做出的决策
                    timestamp=datetime.now().isoformat(),
                    status="confirmed" if "确认" in text else "pending"
                )
                decisions.append(decision)
        
        return decisions
    
    def extract_actions(self, text: str,
                       conversation_history: Optional[List[Dict]] = None) -> List[ExtractedAction]:
        """
        提取文本中的行动
        
        Args:
            text: 文本内容
            conversation_history: 对话历史
        
        Returns:
            List[ExtractedAction]: 提取的行动列表
        """
        actions = []
        
        for pattern in self.action_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                action_text = match.group(0)
                action = ExtractedAction(
                    action_id=f"action_{hash(action_text) % 1000000:06d}",
                    action_type=self._classify_action_type(action_text),
                    description=action_text,
                    target=self._extract_target_from_action(action_text),
                    status="planned"
                )
                actions.append(action)
        
        return actions
    
    def generate_summary(self, text: str,
                        conversation_history: Optional[List[Dict]] = None) -> ConversationSummary:
        """
        生成对话摘要
        
        Args:
            text: 文本内容
            conversation_history: 对话历史
        
        Returns:
            ConversationSummary: 对话摘要
        """
        # 提取关键句子（简化版，实际可以使用更复杂的摘要算法）
        sentences = re.split(r'[。！？\n]+', text)
        key_points = [s.strip() for s in sentences if len(s.strip()) > 10][:5]
        
        # 提取主题
        topics = self._extract_topics(text)
        
        # 分析情感
        sentiment = self._analyze_sentiment(text)
        
        # 分析紧急程度
        urgency = self._analyze_urgency(text)
        
        # 生成摘要文本
        summary_text = self._generate_summary_text(key_points, topics)
        
        return ConversationSummary(
            summary_text=summary_text,
            key_points=key_points,
            topics=topics,
            sentiment=sentiment,
            urgency=urgency,
            completeness=min(1.0, len(key_points) / 5.0)
        )
    
    # ==================== 辅助方法 ====================
    
    def _merge_conversation_text(self, conversation_history: List[Dict[str, Any]]) -> str:
        """合并对话历史为文本"""
        texts = []
        for conv in conversation_history:
            if "user_message" in conv:
                texts.append(f"用户: {conv['user_message']}")
            if "llm_response" in conv:
                texts.append(f"助手: {conv['llm_response']}")
        return "\n".join(texts)
    
    def _calculate_entity_importance(self, entity_name: str, text: str) -> float:
        """计算实体重要性分数"""
        # 基于出现频率和上下文计算重要性
        count = text.lower().count(entity_name.lower())
        base_score = min(1.0, count / 5.0)  # 最多5次出现得满分
        
        # 如果在句首或重要位置出现，增加权重
        if entity_name in text[:100]:
            base_score += 0.2
        
        return min(1.0, base_score)
    
    def _deduplicate_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """去重实体"""
        seen = {}
        unique_entities = []
        
        for entity in entities:
            key = (entity.entity_type, entity.name.lower())
            if key in seen:
                # 合并相同实体
                existing = seen[key]
                existing.occurrence_count += entity.occurrence_count
                existing.importance_score = max(existing.importance_score, entity.importance_score)
            else:
                seen[key] = entity
                unique_entities.append(entity)
        
        return unique_entities
    
    def _extract_action_from_text(self, text: str) -> Optional[str]:
        """从文本中提取行动"""
        action_keywords = ["执行", "开始", "完成", "准备", "开发", "测试", "部署"]
        for keyword in action_keywords:
            if keyword in text:
                return keyword
        return None
    
    def _classify_action_type(self, action_text: str) -> str:
        """分类行动类型"""
        if any(kw in action_text for kw in ["开发", "编码", "实现"]):
            return "development"
        elif any(kw in action_text for kw in ["测试", "验证", "检查"]):
            return "testing"
        elif any(kw in action_text for kw in ["部署", "发布", "上线"]):
            return "deployment"
        elif any(kw in action_text for kw in ["设计", "规划", "架构"]):
            return "design"
        else:
            return "general"
    
    def _extract_target_from_action(self, action_text: str) -> Optional[str]:
        """从行动文本中提取目标"""
        # 简单的目标提取逻辑
        patterns = [
            r"(?:完成|执行|实现|开发)(.+?)(?:任务|工作|功能|模块)",
            r"(?:准备|开始)(.+?)(?:阶段|步骤|流程)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, action_text)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_topics(self, text: str) -> List[str]:
        """提取主题"""
        # 基于关键词提取主题
        topic_keywords = {
            "技术": ["技术", "架构", "设计", "实现"],
            "管理": ["管理", "计划", "任务", "进度"],
            "安全": ["安全", "风险", "备份", "保护"],
            "性能": ["性能", "优化", "效率", "速度"],
            "数据": ["数据", "存储", "数据库", "缓存"]
        }
        
        topics = []
        for topic, keywords in topic_keywords.items():
            if any(kw in text for kw in keywords):
                topics.append(topic)
        
        return topics[:3]  # 最多3个主题
    
    def _analyze_sentiment(self, text: str) -> str:
        """分析情感"""
        positive_words = ["好", "优秀", "成功", "完成", "满意", "喜欢"]
        negative_words = ["差", "失败", "错误", "问题", "困难", "不喜欢"]
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _analyze_urgency(self, text: str) -> str:
        """分析紧急程度"""
        urgent_words = ["紧急", "立即", "马上", "必须", "尽快", "重要"]
        
        if any(word in text for word in urgent_words):
            return "urgent"
        elif any(word in text for word in ["尽快", "优先"]):
            return "high"
        elif any(word in text for word in ["计划", "安排"]):
            return "normal"
        else:
            return "low"
    
    def _generate_summary_text(self, key_points: List[str], topics: List[str]) -> str:
        """生成摘要文本"""
        if not key_points:
            return "无关键信息"
        
        summary = "对话主要涉及"
        if topics:
            summary += f"{'、'.join(topics)}等方面。"
        else:
            summary += "多个方面。"
        
        if key_points:
            summary += f"关键内容包括：{key_points[0]}"
            if len(key_points) > 1:
                summary += f"等{len(key_points)}个要点。"
            else:
                summary += "。"
        
        return summary


if __name__ == "__main__":
    # 测试提取器
    extractor = ConversationExtractor()
    
    # 测试数据
    test_conversation = [
        {
            "user_message": "我们需要开发一个动态上下文记忆管理系统",
            "llm_response": "好的，这是一个很好的想法。我们可以采用三级存储架构。"
        },
        {
            "user_message": "决定采用Redis作为热缓存",
            "llm_response": "同意，Redis的毫秒级响应很适合高频访问。"
        }
    ]
    
    result = extractor.extract_from_conversation(test_conversation)
    print(json.dumps(result, ensure_ascii=False, indent=2))
