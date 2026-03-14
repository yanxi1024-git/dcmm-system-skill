# 动态上下文记忆管理系统 (DCMMS) Skill

## 技能概述

动态上下文记忆管理系统 (Dynamic Context Memory Management System) 是一个革命性的大模型上下文管理解决方案，通过"干净重启+精准重建"的方式，解决传统大模型对话中的上下文污染、Token浪费和幻觉问题。

## 核心功能

### 1. 动态对话循环
- 接收用户消息后自动提取关键信息
- 更新三级存储系统
- 重置大模型会话
- 重建精准上下文
- 获取优化后的回复

### 2. 三级智能存储
- **Redis热缓存**: 毫秒级访问高频数据
- **SQLite温存储**: 秒级访问结构化数据
- **记忆文件冷存储**: 持久化完整历史

### 3. 智能上下文重建
- 基于查询相关性匹配记忆
- 优先级排序和Token优化
- 结构化组织上下文内容
- 自适应长度控制

## 技术架构

### 核心模块
- `core/conversation_extractor.py`: 会话关键信息提取
- `core/context_rebuilder.py`: 动态上下文重建
- `core/token_optimizer.py`: Token智能优化
- `core/quality_assessor.py`: 对话质量评估

### 存储层
- `storage/redis_client.py`: Redis客户端
- `storage/sqlite_client.py`: SQLite客户端
- `storage/memory_sync.py`: 记忆同步机制

### LLM集成
- `llm/session_manager.py`: 会话管理
- `llm/context_formatter.py`: 上下文格式化
- `llm/prompt_templates.py`: 提示词模板

### 调度器
- `scheduler/task_scheduler.py`: 任务调度
- `scheduler/context_refresh.py`: 上下文刷新
- `scheduler/cleanup_manager.py`: 清理管理

## 安装和配置

### 前置要求
1. Redis 7.0+ (已配置)
2. SQLite 3.35+
3. Python 3.9+
4. OpenClaw 2026.3+

### 安装步骤
```bash
# 1. 克隆技能仓库
git clone https://github.com/yanxi1024-git/dcmm-system-skill.git

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp config/.env.example config/.env
# 编辑config/.env设置Redis和数据库连接

# 4. 初始化系统
python scripts/init_system.py

# 5. 迁移现有数据
python scripts/migrate_existing_data.py

# 6. 启动监控
python scripts/performance_monitor.py
```

### 配置文件
- `config/default_settings.json`: 默认系统设置
- `config/extraction_rules.json`: 信息提取规则
- `config/context_templates.json`: 上下文模板
- `config/optimization_rules.json`: 优化规则

## 使用方法

### 基础使用
```python
from core.memory_manager import DynamicContextMemoryManager

# 初始化管理器
manager = DynamicContextMemoryManager()

# 处理用户消息
response = manager.process_message(
    user_message="今天Moltbook的发帖计划执行了吗？",
    session_id="session_123"
)

print(response)
```

### 高级配置
```python
# 自定义提取规则
manager.configure_extraction({
    "entity_types": ["person", "project", "task", "decision"],
    "intent_categories": ["query", "instruction", "confirmation", "decision"],
    "summary_length": 200  # 字符数
})

# 自定义Token优化
manager.configure_optimization({
    "max_context_tokens": 8000,
    "compression_ratio": 0.7,
    "priority_weights": {
        "recent": 0.4,
        "relevant": 0.3,
        "important": 0.2,
        "frequent": 0.1
    }
})
```

### 监控和诊断
```python
# 获取系统状态
status = manager.get_system_status()
print(f"Token节省: {status['token_saving_percentage']}%")
print(f"平均响应时间: {status['avg_response_time']}ms")
print(f"系统可用性: {status['availability']}%")

# 获取对话质量报告
quality_report = manager.get_quality_report(session_id="session_123")
print(f"相关性得分: {quality_report['relevance_score']}")
print(f"准确性得分: {quality_report['accuracy_score']}")
print(f"幻觉风险: {quality_report['hallucination_risk']}")
```

## 性能指标

### 量化目标
- **Token节省**: 30-50% 减少
- **响应时间**: < 2秒 平均响应
- **准确性**: 提升20%以上
- **幻觉风险**: 降低40%以上
- **系统可用性**: 99.9%

### 监控指标
1. **性能指标**: Token使用、响应时间、吞吐量
2. **质量指标**: 相关性、准确性、完整性
3. **系统指标**: 可用性、错误率、资源使用
4. **业务指标**: 用户满意度、任务完成率

## 故障排除

### 常见问题

#### 1. Redis连接失败
```bash
# 检查Redis服务状态
systemctl status redis

# 检查连接配置
cat config/.env | grep REDIS
```

#### 2. 数据同步失败
```python
# 手动触发同步
from storage.memory_sync import MemorySynchronizer
sync = MemorySynchronizer()
sync.force_sync_all()
```

#### 3. Token优化效果不佳
```python
# 调整优化参数
manager.configure_optimization({
    "compression_ratio": 0.6,  # 提高压缩率
    "min_content_length": 50   # 提高最小内容长度
})
```

### 诊断工具
```bash
# 运行系统诊断
python scripts/system_diagnostic.py

# 检查数据一致性
python scripts/check_data_consistency.py

# 性能基准测试
python scripts/run_benchmark.py
```

## 维护和更新

### 日常维护
1. **每日检查**: 系统状态、错误日志、性能指标
2. **每周备份**: 完整数据备份、配置备份
3. **每月优化**: 算法调优、参数优化、性能优化

### 更新流程
1. 备份当前系统和数据
2. 测试新版本在测试环境
3. 逐步在生产环境部署
4. 监控更新后的性能
5. 回滚计划准备

## 安全考虑

### 数据安全
1. **加密存储**: 敏感数据加密存储
2. **访问控制**: 严格的权限管理
3. **审计日志**: 完整的操作审计
4. **数据脱敏**: 生产环境数据脱敏

### 系统安全
1. **输入验证**: 严格的输入验证和清理
2. **错误处理**: 安全的错误信息处理
3. **资源限制**: 防止资源滥用
4. **安全更新**: 及时的安全补丁更新

## 支持和贡献

### 获取支持
- **文档**: 查看完整文档和示例
- **问题跟踪**: GitHub Issues报告问题
- **社区支持**: OpenClaw社区讨论

### 贡献指南
1. Fork仓库并创建特性分支
2. 遵循代码规范和测试要求
3. 提交Pull Request并描述变更
4. 通过所有测试和代码审查

## 许可证

MIT License - 详见LICENSE文件

## 版本历史

### v1.0.0 (2026-03-14)
- 初始版本发布
- 基础动态上下文管理功能
- 三级存储系统集成
- 基础监控和诊断工具

### 路线图
- v1.1.0: 高级优化算法
- v1.2.0: 多LLM支持
- v2.0.0: 分布式架构

---

**技能版本**: v1.0.0  
**兼容性**: OpenClaw 2026.3+  
**最后更新**: 2026-03-14  
**维护者**: 小龙女
