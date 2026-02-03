---
inclusion: always
priority: critical
---

# 角色权限矩阵 - 动态验证系统

## 🔒 角色权限动态验证机制

### 权限验证流程
```
用户请求 → 角色识别 → 权限检查 → 资源限制验证 → 执行授权/拒绝
```

## 📊 详细权限矩阵

### 🔍 Code Review Specialist
**允许操作**:
- `read_code` - 读取和分析代码文件
- `analyze_quality` - 执行代码质量分析
- `suggest_improvements` - 提供改进建议
- `create_review_reports` - 生成代码审查报告
- `run_quality_checks` - 执行质量门禁检查
- `validate_test_coverage` - 验证测试覆盖率

**禁止操作**:
- `modify_architecture` - 修改系统架构
- `change_requirements` - 变更需求规格
- `deploy_code` - 部署代码到生产环境
- `modify_database_schema` - 修改数据库结构
- `change_security_policies` - 修改安全策略

**资源限制**:
- 最大文件数/会话: 50
- 最大执行时间: 30分钟
- 内存使用限制: 512MB
- 并发任务限制: 3个

### 🚀 Full-Stack Engineer
**允许操作**:
- `read_code` - 读取代码文件
- `write_code` - 编写和修改代码
- `run_tests` - 执行测试套件
- `debug_issues` - 调试和修复问题
- `create_components` - 创建新的代码组件
- `refactor_code` - 重构现有代码
- `manage_dependencies` - 管理项目依赖

**禁止操作**:
- `modify_requirements` - 修改产品需求
- `change_architecture_decisions` - 变更架构决策
- `approve_deployments` - 批准生产部署
- `modify_security_configs` - 修改安全配置
- `change_database_permissions` - 修改数据库权限

**资源限制**:
- 最大文件数/会话: 100
- 最大执行时间: 60分钟
- 内存使用限制: 1GB
- 并发任务限制: 5个

### 🏗️ Software Architect
**允许操作**:
- `design_architecture` - 设计系统架构
- `make_tech_decisions` - 做出技术决策
- `review_designs` - 审查设计方案
- `create_integration_plans` - 创建集成计划
- `evaluate_technologies` - 评估技术选型
- `define_standards` - 定义技术标准

**禁止操作**:
- `implement_code` - 直接实现代码（应委托给工程师）
- `modify_business_requirements` - 修改业务需求
- `make_budget_decisions` - 做出预算决策
- `directly_deploy` - 直接部署系统

**资源限制**:
- 最大文件数/会话: 200
- 最大执行时间: 120分钟
- 内存使用限制: 2GB
- 并发任务限制: 3个

### 🔒 Security Engineer
**允许操作**:
- `security_audit` - 执行安全审计
- `vulnerability_scan` - 漏洞扫描
- `threat_modeling` - 威胁建模
- `security_config` - 配置安全设置
- `compliance_check` - 合规性检查
- `incident_response` - 安全事件响应

**禁止操作**:
- `modify_business_logic` - 修改业务逻辑
- `change_ui_design` - 修改用户界面设计
- `performance_optimization` - 性能优化（非安全相关）
- `feature_development` - 功能开发

**资源限制**:
- 最大文件数/会话: 全部（安全审计需要）
- 最大执行时间: 180分钟
- 内存使用限制: 2GB
- 并发任务限制: 2个

### 🧪 Test Engineer
**允许操作**:
- `create_test_plans` - 创建测试计划
- `write_test_cases` - 编写测试用例
- `execute_tests` - 执行测试
- `analyze_test_results` - 分析测试结果
- `setup_test_environments` - 搭建测试环境
- `performance_testing` - 性能测试

**禁止操作**:
- `modify_production_code` - 修改生产代码
- `change_requirements` - 修改需求
- `make_architecture_decisions` - 做出架构决策
- `deploy_to_production` - 部署到生产环境

**资源限制**:
- 最大文件数/会话: 150
- 最大执行时间: 90分钟
- 内存使用限制: 1.5GB
- 并发任务限制: 4个

## 🚨 权限违规处理机制

### 违规检测
```python
def detect_permission_violation(role, action, context):
    role_config = get_role_config(role)
    
    # 检查操作权限
    if action not in role_config['allowed_operations']:
        return {
            'violation_type': 'unauthorized_operation',
            'severity': 'high',
            'action': 'block_immediately'
        }
    
    # 检查禁止操作
    if action in role_config['forbidden_operations']:
        return {
            'violation_type': 'forbidden_operation', 
            'severity': 'critical',
            'action': 'block_and_alert'
        }
    
    # 检查资源限制
    if exceeds_resource_limits(role_config, context):
        return {
            'violation_type': 'resource_limit_exceeded',
            'severity': 'medium',
            'action': 'warn_and_throttle'
        }
    
    return None  # 无违规
```

### 违规响应策略
- **Critical**: 立即阻断执行，发送告警，记录详细日志
- **High**: 阻断执行，要求重新授权，通知管理员
- **Medium**: 警告用户，限制资源使用，继续监控
- **Low**: 记录日志，定期汇总报告

## 🔄 动态权限调整

### 上下文感知权限
```yaml
context_aware_permissions:
  emergency_mode:
    # 紧急情况下的权限扩展
    conditions: ["system_down", "security_breach", "data_loss"]
    expanded_permissions:
      - "cross_role_operations"
      - "elevated_resource_limits"
      - "bypass_approval_workflows"
    
  learning_mode:
    # 学习模式下的权限限制
    conditions: ["new_team_member", "experimental_feature"]
    restricted_permissions:
      - "production_access"
      - "critical_system_changes"
      - "high_risk_operations"
```

### 权限升级机制
```python
def request_permission_elevation(role, requested_action, justification):
    """请求权限升级"""
    elevation_request = {
        'role': role,
        'action': requested_action,
        'justification': justification,
        'timestamp': datetime.now(),
        'status': 'pending'
    }
    
    # 自动批准的情况
    if is_auto_approvable(requested_action, justification):
        elevation_request['status'] = 'approved'
        elevation_request['approved_by'] = 'system'
    else:
        # 需要人工审批
        notify_approvers(elevation_request)
    
    return elevation_request
```

## 📊 权限使用监控

### 实时监控指标
- 权限使用频率
- 违规尝试次数
- 资源使用情况
- 执行时间分布
- 成功/失败率

### 异常检测
```python
def detect_permission_anomalies(role, recent_actions):
    """检测权限使用异常"""
    anomalies = []
    
    # 检测异常高频操作
    if detect_high_frequency_operations(recent_actions):
        anomalies.append('high_frequency_operations')
    
    # 检测权限边界探测
    if detect_permission_probing(recent_actions):
        anomalies.append('permission_boundary_probing')
    
    # 检测资源使用异常
    if detect_resource_usage_anomalies(recent_actions):
        anomalies.append('abnormal_resource_usage')
    
    return anomalies
```

## 🎯 权限优化建议

### 基于使用模式的优化
1. **权限精简**: 移除从未使用的权限
2. **权限合并**: 合并经常一起使用的权限
3. **权限分级**: 根据风险等级分层管理权限
4. **动态调整**: 根据历史表现动态调整权限范围

### 安全最佳实践
1. **最小权限原则**: 只授予完成任务所需的最小权限
2. **定期审查**: 定期审查和更新权限配置
3. **权限分离**: 关键操作需要多个角色协作
4. **审计追踪**: 完整记录所有权限使用情况

---

**配置版本**: v1.0  
**最后更新**: 2026-02-01  
**维护者**: 硅谷项目开发经理  
**状态**: 生产就绪