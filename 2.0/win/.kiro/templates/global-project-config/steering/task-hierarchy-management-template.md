# 通用任务层次化管理系统模板

## 🎯 任务层次结构定义（通用版）

### 长期任务 (Strategic Tasks)
- **时间跨度**: 3-12个月
- **特征**: 战略性、架构性、系统性
- **责任人**: Product Manager
- **示例模板**: "构建完整的{项目核心功能}系统"
- **验收标准模板**:
  - "系统架构完整"
  - "核心功能实现"
  - "质量标准达标"

### 中期任务 (Tactical Tasks)
- **时间跨度**: 2-8周
- **特征**: 功能性、模块性、可交付
- **责任人**: Software Architect + 相关工程师
- **示例模板**: "实现{具体模块名称}模块"
- **验收标准模板**:
  - "模块功能完整"
  - "接口规范"
  - "测试覆盖率100%"

### 短期任务 (Operational Tasks)
- **时间跨度**: 1-5天
- **特征**: 具体性、可执行、可验证
- **责任人**: 具体执行角色
- **示例模板**: "修复{具体文件}中的{具体问题}"
- **验收标准模板**:
  - "代码质量达标"
  - "测试通过"
  - "文档更新"

### 临时任务 (Ad-hoc Tasks)
- **时间跨度**: 立即-1天
- **特征**: 紧急性、响应性、插入性
- **责任人**: 相关专业角色
- **示例模板**: "修复{环境}的紧急{问题类型}"
- **验收标准模板**:
  - "问题解决"
  - "影响评估"
  - "预防措施"

## 🔄 通用任务分解规则

### 分解模板
```yaml
task_decomposition_template:
  long_to_medium:
    process:
      - "识别关键里程碑"
      - "评估技术可行性"
      - "分析资源需求"
      - "制定风险缓解策略"
    output_format: "中期任务列表"
    
  medium_to_short:
    process:
      - "分析功能模块"
      - "设计技术方案"
      - "制定测试策略"
      - "规划集成步骤"
    output_format: "短期任务列表"
    
  short_to_execution:
    process:
      - "编写实现代码"
      - "创建单元测试"
      - "执行代码审查"
      - "进行集成验证"
    output_format: "可交付代码"
```

## 📊 通用进度跟踪模板

### 完成度计算公式
```yaml
progress_calculation:
  long_term: "sum(medium_term_completion) / count(medium_term_tasks)"
  medium_term: "sum(short_term_completion) / count(short_term_tasks)"
  short_term: "completed_deliverables / total_deliverables"
```

### 状态定义（标准化）
- **planned**: 已规划 - 任务已定义但未开始
- **in_progress**: 进行中 - 任务正在执行
- **blocked**: 阻塞中 - 遇到阻塞问题暂停
- **review**: 审查中 - 等待代码审查或验收
- **completed**: 已完成 - 任务执行完毕
- **verified**: 已验证 - 通过质量验证
- **failed**: 失败 - 任务执行失败需重新规划
- **cancelled**: 已取消 - 任务被取消不再执行

## 🚨 通用防漂移机制

### 漂移检测阈值（可配置）
```yaml
drift_thresholds:
  goal_deviation: 30%        # 目标偏离度
  quality_degradation: -10%  # 质量下降
  progress_anomaly: 50%      # 进度异常
  context_inconsistency: 3   # 上下文不一致次数
```

### 自动纠正动作
```yaml
auto_correction_actions:
  goal_deviation: "立即重新对齐目标"
  quality_degradation: "暂停执行，质量改进"
  progress_anomaly: "重新评估和调整计划"
  context_inconsistency: "重新锚定上下文"
```

## 🎯 项目适配指南

### 小型项目适配（1-5人团队）
- 合并角色：Full-Stack Engineer兼任多个角色
- 简化流程：减少审批层级
- 保持核心：任务层次化和质量门禁不变

### 中型项目适配（6-15人团队）
- 标准配置：使用完整的12角色体系
- 专业分工：每个角色专注自己的职责
- 完整流程：执行所有质量门禁和审查

### 大型项目适配（15+人团队）
- 扩展角色：每个角色可以有多人
- 分层管理：增加Team Lead层级
- 强化治理：更严格的流程和审查

## 📋 配置检查清单

### 部署前检查
- [ ] 任务层次定义是否符合项目特点
- [ ] 角色分工是否匹配团队规模
- [ ] 质量标准是否适合技术栈
- [ ] 工具配置是否正确设置

### 运行中监控
- [ ] 任务完成率是否达标
- [ ] 质量门禁通过率是否正常
- [ ] 团队协作效率是否提升
- [ ] 漂移检测是否有效工作

---

**模板版本**: v1.0  
**适用范围**: 所有软件开发项目  
**维护者**: Software Architect  
**更新频率**: 季度评估，年度升级