# 通用项目管理配置使用指南

## 🚀 快速开始

### 1. 新项目初始化

```bash
# 方法一：使用初始化脚本（推荐）
python .kiro/templates/global-project-config/scripts/project_initializer.py \
  --project-type medium \
  --language python \
  --team-size 6

# 方法二：手动复制配置
cp -r .kiro/templates/global-project-config/steering/* .kiro/steering/
cp -r .kiro/templates/global-project-config/hooks/* .kiro/hooks/
cp -r .kiro/templates/global-project-config/scripts/* .kiro/scripts/
```

### 2. 验证配置

```bash
# 检查配置完整性
python .kiro/scripts/iron_law_checker.py

# 验证Hook配置
ls -la .kiro/hooks/

# 查看项目配置
cat .kiro/project_config.json
```

## 🎯 项目类型适配

### 小型项目（1-3人团队）

```bash
python project_initializer.py --project-type small --team-size 3
```

**特点**：
- 简化角色：3个核心角色
- 快速迭代：减少审批流程
- 保持质量：100%测试覆盖率不变

**角色配置**：
- 🚀 Full-Stack Engineer（主力开发）
- 🧪 Test Engineer（质量保证）
- 🔍 Code Review Specialist（代码审查）

### 中型项目（4-8人团队）

```bash
python project_initializer.py --project-type medium --team-size 6
```

**特点**：
- 标准配置：6个核心角色
- 专业分工：每个角色专注职责
- 完整流程：所有质量门禁

**角色配置**：
- 📊 Product Manager
- 🏗️ Software Architect
- 🚀 Full-Stack Engineer
- 🧪 Test Engineer
- 🔒 Security Engineer
- 🔍 Code Review Specialist

### 大型项目（9+人团队）

```bash
python project_initializer.py --project-type large --team-size 12
```

**特点**：
- 完整配置：12个专业角色
- 严格治理：多层审查机制
- 企业级：适合复杂项目

**角色配置**：
- 完整的硅谷12人团队配置

## 🔧 语言特定配置

### Python项目

```bash
python project_initializer.py --language python
```

**配置特点**：
- 文件模式：`*.py`
- 测试框架：pytest
- 覆盖率工具：coverage.py
- 代码质量：pylint, mypy

### JavaScript/TypeScript项目

```bash
python project_initializer.py --language javascript
```

**配置特点**：
- 文件模式：`*.js`, `*.ts`
- 测试框架：Jest, Mocha
- 覆盖率工具：Istanbul
- 代码质量：ESLint, TSLint

### Java项目

```bash
python project_initializer.py --language java
```

**配置特点**：
- 文件模式：`*.java`
- 测试框架：JUnit, TestNG
- 覆盖率工具：JaCoCo
- 代码质量：SpotBugs, PMD

## 📊 自定义配置

### 1. 调整质量标准

编辑 `.kiro/project_config.json`：

```json
{
  "quality_thresholds": {
    "test_coverage": 100,      // 测试覆盖率（不建议低于100%）
    "code_complexity": 10,     // 代码复杂度
    "security_score": 90,      // 安全评分
    "documentation_coverage": 80  // 文档覆盖率
  }
}
```

### 2. 自定义Hook触发条件

编辑 `.kiro/hooks/*.kiro.hook` 文件：

```json
{
  "when": {
    "type": "fileEdited",
    "patterns": ["*.py", "*.js"]  // 自定义文件模式
  }
}
```

### 3. 添加项目特定角色

在 `.kiro/steering/silicon-valley-team-config.md` 中添加：

```markdown
### 13. 🎮 Game Developer
**职责**: 游戏逻辑、物理引擎、渲染优化
**触发条件**: 游戏相关问题
**输出**: 游戏设计文档、性能优化方案
**适用项目**: 游戏开发项目
```

## 🔄 工作流程

### 日常开发流程

1. **编写代码** → Hook自动触发质量检查
2. **运行测试** → 验证100%覆盖率
3. **代码审查** → Code Review Specialist审查
4. **集成测试** → 验证系统集成
5. **部署发布** → DevOps Engineer处理

### 任务管理流程

1. **长期规划** → Product Manager制定战略
2. **中期分解** → Software Architect设计架构
3. **短期执行** → 各角色具体实施
4. **质量验证** → Test Engineer全面测试
5. **最终审查** → Code Review Specialist把关

## 🚨 常见问题解决

### Q1: Hook没有自动触发？

**解决方案**：
```bash
# 检查Hook配置
cat .kiro/hooks/task-lifecycle-management.kiro.hook

# 验证文件模式匹配
ls -la *.py  # 确认文件扩展名正确
```

### Q2: 测试覆盖率无法达到100%？

**解决方案**：
1. 检查未覆盖的代码行
2. 添加针对性测试用例
3. 使用Mock技术处理外部依赖
4. 测试异常处理路径

### Q3: 代码复杂度超过10？

**解决方案**：
1. 拆分大函数为小函数
2. 使用设计模式简化逻辑
3. 提取公共代码到工具函数
4. 重构复杂的条件判断

### Q4: 团队角色分工不清？

**解决方案**：
1. 查看角色权限矩阵
2. 明确每个角色的职责边界
3. 建立角色间协作机制
4. 定期进行角色培训

## 📈 成功指标

使用这套配置的项目应该达到：

- ✅ **任务完成率** > 90%
- ✅ **质量门禁通过率** > 95%
- ✅ **代码覆盖率** = 100%
- ✅ **团队协作效率提升** > 30%
- ✅ **Bug修复时间** < 24小时
- ✅ **代码审查覆盖率** = 100%

## 🔄 持续改进

### 定期评估（建议频率）

- **周度**：任务进度和质量指标
- **月度**：团队协作效率和流程优化
- **季度**：配置模板更新和最佳实践总结
- **年度**：整体架构评估和重大升级

### 反馈收集

1. 团队成员使用体验反馈
2. 项目成功案例总结
3. 失败案例分析和改进
4. 行业最佳实践跟踪

---

**使用指南版本**: v1.0  
**最后更新**: 2026-02-02  
**维护者**: Software Architect  
**支持联系**: 项目管理团队