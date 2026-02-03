#!/usr/bin/env python3
"""
LLM执行监控系统 - 实时防漂移监控
硅谷项目开发经理设计的LLM行为约束引擎实现
"""

import json
import time
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

class ViolationSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ActionType(Enum):
    READ_CODE = "read_code"
    WRITE_CODE = "write_code"
    RUN_TESTS = "run_tests"
    ANALYZE_QUALITY = "analyze_quality"
    MODIFY_ARCHITECTURE = "modify_architecture"
    CHANGE_REQUIREMENTS = "change_requirements"
    DEPLOY_CODE = "deploy_code"

@dataclass
class ExecutionContext:
    """执行上下文"""
    current_role: str
    task_id: str
    start_time: datetime
    file_modifications: List[str]
    resource_usage: Dict[str, Any]
    context_hash: str

@dataclass
class ViolationReport:
    """违规报告"""
    violation_type: str
    severity: ViolationSeverity
    action: str
    role: str
    context: ExecutionContext
    timestamp: datetime
    details: Dict[str, Any]

class LLMExecutionMonitor:
    """LLM执行监控器"""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.role_permissions = self._load_role_permissions()
        self.quality_thresholds = self._load_quality_thresholds()
        self.execution_history = []
        self.violation_count = 0
        self.context_anchors = {}
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('llm_execution_monitor')
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler('logs/llm_execution_monitor.log', encoding='utf-8')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _load_role_permissions(self) -> Dict[str, Dict]:
        """加载角色权限配置"""
        return {
            "🔍 Code Review Specialist": {
                "allowed_operations": [
                    ActionType.READ_CODE,
                    ActionType.ANALYZE_QUALITY,
                    ActionType.RUN_TESTS
                ],
                "forbidden_operations": [
                    ActionType.MODIFY_ARCHITECTURE,
                    ActionType.CHANGE_REQUIREMENTS,
                    ActionType.DEPLOY_CODE
                ],
                "resource_limits": {
                    "max_files_per_session": 50,
                    "max_execution_time": 30 * 60,  # 30分钟
                    "max_memory_mb": 512,
                    "max_concurrent_tasks": 3
                }
            },
            "🚀 Full-Stack Engineer": {
                "allowed_operations": [
                    ActionType.READ_CODE,
                    ActionType.WRITE_CODE,
                    ActionType.RUN_TESTS
                ],
                "forbidden_operations": [
                    ActionType.CHANGE_REQUIREMENTS,
                    ActionType.DEPLOY_CODE
                ],
                "resource_limits": {
                    "max_files_per_session": 100,
                    "max_execution_time": 60 * 60,  # 60分钟
                    "max_memory_mb": 1024,
                    "max_concurrent_tasks": 5
                }
            },
            "🏗️ Software Architect": {
                "allowed_operations": [
                    ActionType.READ_CODE,
                    ActionType.MODIFY_ARCHITECTURE,
                    ActionType.ANALYZE_QUALITY
                ],
                "forbidden_operations": [
                    ActionType.DEPLOY_CODE
                ],
                "resource_limits": {
                    "max_files_per_session": 200,
                    "max_execution_time": 120 * 60,  # 120分钟
                    "max_memory_mb": 2048,
                    "max_concurrent_tasks": 3
                }
            }
        }
    
    def _load_quality_thresholds(self) -> Dict[str, float]:
        """加载质量阈值配置"""
        return {
            "code_complexity": 10.0,
            "test_coverage": 100.0,
            "documentation_coverage": 70.0,
            "security_score": 90.0,
            "performance_score": 85.0,
            "maintainability_index": 70.0
        }
    
    def create_execution_context(self, role: str, task_id: str) -> ExecutionContext:
        """创建执行上下文"""
        context = ExecutionContext(
            current_role=role,
            task_id=task_id,
            start_time=datetime.now(),
            file_modifications=[],
            resource_usage={},
            context_hash=self._calculate_context_hash(role, task_id)
        )
        
        # 锚定关键信息
        self._anchor_critical_info(context)
        
        return context
    
    def _calculate_context_hash(self, role: str, task_id: str) -> str:
        """计算上下文哈希"""
        context_data = f"{role}:{task_id}:{datetime.now().isoformat()}"
        return hashlib.md5(context_data.encode()).hexdigest()
    
    def _anchor_critical_info(self, context: ExecutionContext):
        """锚定关键信息"""
        self.context_anchors[context.task_id] = {
            "system_constraints": [
                "零号铁律：只修复明确缺失内容",
                "核心铁律：中文交流、禁止占位符、及时修复bug",
                "测试铁律：严禁跳过测试、超时必须溯源"
            ],
            "current_objectives": f"角色：{context.current_role}",
            "quality_standards": self.quality_thresholds,
            "last_refresh": datetime.now()
        }
    
    def pre_execution_check(self, action: ActionType, context: ExecutionContext) -> Tuple[bool, Optional[str]]:
        """执行前检查"""
        self.logger.info(f"执行前检查: {action} by {context.current_role}")
        
        # 检查角色权限
        role_check = self._check_role_compliance(action, context.current_role)
        if not role_check[0]:
            return False, f"角色权限违规: {role_check[1]}"
        
        # 检查上下文一致性
        context_check = self._check_context_consistency(context)
        if not context_check[0]:
            return False, f"上下文不一致: {context_check[1]}"
        
        # 检查资源限制
        resource_check = self._check_resource_limits(action, context)
        if not resource_check[0]:
            return False, f"资源限制超出: {resource_check[1]}"
        
        return True, "执行前检查通过"
    
    def _check_role_compliance(self, action: ActionType, role: str) -> Tuple[bool, str]:
        """检查角色合规性"""
        role_config = self.role_permissions.get(role)
        if not role_config:
            return False, f"未知角色: {role}"
        
        # 检查是否在允许操作列表中
        if action not in role_config["allowed_operations"]:
            return False, f"操作 {action} 不在角色 {role} 的允许列表中"
        
        # 检查是否在禁止操作列表中
        if action in role_config["forbidden_operations"]:
            return False, f"操作 {action} 在角色 {role} 的禁止列表中"
        
        return True, "角色权限检查通过"
    
    def _check_context_consistency(self, context: ExecutionContext) -> Tuple[bool, str]:
        """检查上下文一致性"""
        # 检查上下文锚点是否存在
        if context.task_id not in self.context_anchors:
            return False, "上下文锚点丢失"
        
        anchor = self.context_anchors[context.task_id]
        
        # 检查是否需要刷新锚点
        if datetime.now() - anchor["last_refresh"] > timedelta(minutes=5):
            self._refresh_context_anchor(context.task_id)
        
        # 验证上下文哈希
        expected_hash = self._calculate_context_hash(context.current_role, context.task_id)
        if context.context_hash != expected_hash:
            return False, "上下文哈希不匹配"
        
        return True, "上下文一致性检查通过"
    
    def _check_resource_limits(self, action: ActionType, context: ExecutionContext) -> Tuple[bool, str]:
        """检查资源限制"""
        role_config = self.role_permissions.get(context.current_role)
        if not role_config:
            return False, "角色配置不存在"
        
        limits = role_config["resource_limits"]
        
        # 检查执行时间
        execution_time = (datetime.now() - context.start_time).total_seconds()
        if execution_time > limits["max_execution_time"]:
            return False, f"执行时间超限: {execution_time}s > {limits['max_execution_time']}s"
        
        # 检查文件数量
        if len(context.file_modifications) > limits["max_files_per_session"]:
            return False, f"文件数量超限: {len(context.file_modifications)} > {limits['max_files_per_session']}"
        
        return True, "资源限制检查通过"
    
    def _refresh_context_anchor(self, task_id: str):
        """刷新上下文锚点"""
        if task_id in self.context_anchors:
            self.context_anchors[task_id]["last_refresh"] = datetime.now()
            self.logger.info(f"刷新上下文锚点: {task_id}")
    
    def post_execution_check(self, action: ActionType, result: Any, context: ExecutionContext) -> Tuple[bool, Optional[str]]:
        """执行后验证"""
        self.logger.info(f"执行后检查: {action} by {context.current_role}")
        
        # 验证结果质量
        quality_check = self._validate_result_quality(result, action)
        if not quality_check[0]:
            self._rollback_action(action, context)
            return False, f"结果质量不达标: {quality_check[1]}"
        
        # 记录执行历史
        self._record_execution(action, result, context)
        
        return True, "执行后检查通过"
    
    def _validate_result_quality(self, result: Any, action: ActionType) -> Tuple[bool, str]:
        """验证结果质量"""
        if action == ActionType.WRITE_CODE:
            # 检查代码质量
            if isinstance(result, str):
                # 简单的代码质量检查
                if len(result.split('\n')) > 100:  # 代码行数检查
                    return False, "代码过长，可能复杂度过高"
                
                if "TODO" in result or "FIXME" in result:
                    return False, "代码包含未完成标记"
        
        return True, "结果质量检查通过"
    
    def _rollback_action(self, action: ActionType, context: ExecutionContext):
        """回滚操作"""
        self.logger.warning(f"回滚操作: {action} for {context.task_id}")
        # 实现具体的回滚逻辑
        pass
    
    def _record_execution(self, action: ActionType, result: Any, context: ExecutionContext):
        """记录执行历史"""
        execution_record = {
            "action": action.value,
            "role": context.current_role,
            "task_id": context.task_id,
            "timestamp": datetime.now().isoformat(),
            "success": True,
            "execution_time": (datetime.now() - context.start_time).total_seconds()
        }
        
        self.execution_history.append(execution_record)
        
        # 保持历史记录在合理范围内
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-500:]
    
    def handle_violation(self, violation: ViolationReport):
        """处理违规"""
        self.violation_count += 1
        self.logger.error(f"检测到违规: {violation.violation_type} - {violation.severity.value}")
        
        if violation.severity == ViolationSeverity.CRITICAL:
            self._block_execution_immediately(violation)
        elif violation.severity == ViolationSeverity.HIGH:
            self._block_and_require_reauth(violation)
        elif violation.severity == ViolationSeverity.MEDIUM:
            self._warn_and_throttle(violation)
        else:
            self._log_violation(violation)
    
    def _block_execution_immediately(self, violation: ViolationReport):
        """立即阻断执行"""
        self.logger.critical(f"立即阻断执行: {violation.details}")
        # 实现立即阻断逻辑
        raise Exception(f"执行被阻断: {violation.violation_type}")
    
    def _block_and_require_reauth(self, violation: ViolationReport):
        """阻断并要求重新授权"""
        self.logger.error(f"阻断执行，要求重新授权: {violation.details}")
        # 实现重新授权逻辑
        pass
    
    def _warn_and_throttle(self, violation: ViolationReport):
        """警告并限流"""
        self.logger.warning(f"警告并限流: {violation.details}")
        # 实现限流逻辑
        pass
    
    def _log_violation(self, violation: ViolationReport):
        """记录违规"""
        self.logger.info(f"记录违规: {violation.details}")
    
    def analyze_behavior_patterns(self) -> Dict[str, Any]:
        """分析行为模式"""
        if not self.execution_history:
            return {"patterns": [], "drift_indicators": [], "confidence_score": 0.0}
        
        # 分析执行频率
        action_frequency = {}
        for record in self.execution_history[-100:]:  # 分析最近100条记录
            action = record["action"]
            action_frequency[action] = action_frequency.get(action, 0) + 1
        
        # 检测异常模式
        drift_indicators = []
        for action, frequency in action_frequency.items():
            if frequency > 50:  # 异常高频
                drift_indicators.append(f"高频操作: {action} ({frequency}次)")
        
        # 计算置信度
        confidence_score = min(1.0, len(self.execution_history) / 100.0)
        
        return {
            "patterns": action_frequency,
            "drift_indicators": drift_indicators,
            "confidence_score": confidence_score,
            "total_violations": self.violation_count
        }
    
    def generate_monitoring_report(self) -> Dict[str, Any]:
        """生成监控报告"""
        behavior_analysis = self.analyze_behavior_patterns()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_executions": len(self.execution_history),
            "total_violations": self.violation_count,
            "behavior_analysis": behavior_analysis,
            "active_contexts": len(self.context_anchors),
            "system_status": "operational" if self.violation_count < 10 else "warning"
        }

def main():
    """主函数 - 用于测试"""
    monitor = LLMExecutionMonitor()
    
    # 创建测试上下文
    context = monitor.create_execution_context("🔍 Code Review Specialist", "test_task_001")
    
    # 测试执行前检查
    check_result = monitor.pre_execution_check(ActionType.READ_CODE, context)
    print(f"执行前检查结果: {check_result}")
    
    # 测试执行后检查
    post_result = monitor.post_execution_check(ActionType.READ_CODE, "test_code", context)
    print(f"执行后检查结果: {post_result}")
    
    # 生成监控报告
    report = monitor.generate_monitoring_report()
    print(f"监控报告: {json.dumps(report, indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    main()