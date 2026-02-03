# 第九章单元测试 - 工程铁律

**白皮书依据**: 第九章 9.0 工程铁律 (The Constitution)

## 测试覆盖率目标

**100%** - 用户明确要求

## 测试模块

- `test_engineering_law_validator.py` - 工程铁律验证器测试
- `test_documentation_sync_checker.py` - 文档同步检查器测试

## 运行测试

```bash
# 运行所有第九章测试
pytest tests/unit/chapter_9/ -v

# 运行测试并生成覆盖率报告
pytest tests/unit/chapter_9/ --cov=src/compliance --cov-report=term --cov-report=html

# 验证100%覆盖率
pytest tests/unit/chapter_9/ --cov=src/compliance --cov-fail-under=100
```
