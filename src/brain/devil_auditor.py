"""魔鬼审计器 - DeepSeek-R1推理审计系统

白皮书依据: 第二章 2.4 The Devil (魔鬼审计)
需求: 8.2 - 重构Auditor事件订阅
"""

import ast
import hashlib
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

from ..core.dependency_container import LifecycleScope, get_container, injectable
from ..infra.event_bus import Event, EventType
from .llm_gateway import CallType, LLMGateway, LLMProvider, LLMRequest


class AuditSeverity(Enum):
    """审计严重程度"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditIssue:
    """审计问题

    Attributes:
        issue_type: 问题类型
        severity: 严重程度
        description: 问题描述
        location: 问题位置（行号等）
        suggestion: 修复建议
        code_snippet: 相关代码片段
    """

    issue_type: str
    severity: AuditSeverity
    description: str
    location: str
    suggestion: str
    code_snippet: str = ""


@dataclass
class AuditResult:
    """审计结果

    Attributes:
        approved: 是否通过审计
        confidence: 置信度 (0-1)
        issues: 发现的问题列表
        suggestions: 改进建议
        execution_time: 审计耗时（秒）
        audit_hash: 审计哈希值
    """

    approved: bool
    confidence: float
    issues: List[AuditIssue]
    suggestions: List[str]
    execution_time: float
    audit_hash: str


@injectable(LifecycleScope.SINGLETON)
class DevilAuditorV2:
    """魔鬼审计器 v2.0 - 无循环依赖版本

    白皮书依据: 第二章 2.4 The Devil (魔鬼审计)

    使用DeepSeek-R1进行深度推理审计，检测：
    - 未来函数
    - 过拟合
    - 代码安全性
    - 逻辑漏洞

    核心特性:
    - DeepSeek-R1推理审计
    - 未来函数检测
    - 过拟合检测
    - 代码安全扫描
    - 逻辑一致性检查

    性能要求:
    - 检测准确率 > 90%
    - 审计延迟 < 30秒
    - 误报率 < 5%
    """

    def __init__(self):
        """初始化魔鬼审计器"""
        try:
            self.llm_gateway = get_container().resolve(LLMGateway)
        except ValueError:
            # 在测试环境中，LLMGateway可能未注册
            self.llm_gateway = None
            logger.warning("LLMGateway未注册，将在测试模式下运行")

        self.event_bus = None  # 将在initialize中设置

        # 审计统计
        self.audit_count = 0
        self.approval_rate = 0.0
        self.avg_confidence = 0.0

        # 危险函数黑名单
        self.dangerous_functions = {
            "eval",
            "exec",
            "compile",
            "__import__",
            "open",
            "file",
            "input",
            "raw_input",
            "os.system",
            "subprocess.call",
            "subprocess.run",
            "pickle.load",
            "pickle.loads",
        }

        # 未来函数模式
        self.future_function_patterns = [
            r"shift\s*\(\s*-\d+\s*\)",  # 负数shift
            r"\.iloc\s*\[\s*\d+\s*:\s*\]",  # 向前索引
            r"\.loc\s*\[\s*.*\s*:\s*\]",  # 向前切片
            r"rolling\s*\(\s*\d+\s*\)\..*\.shift\s*\(\s*-\d+\s*\)",  # 滚动窗口负shift
        ]

        logger.info("DevilAuditor v2.0 初始化完成")

    async def initialize(self) -> bool:
        """初始化魔鬼审计器

        Returns:
            bool: 初始化是否成功
        """
        try:
            # 获取事件总线
            from ..infra.event_bus import get_event_bus  # pylint: disable=import-outside-toplevel

            self.event_bus = await get_event_bus()

            # 设置事件订阅
            await self._setup_event_subscriptions()

            logger.info("DevilAuditor初始化完成")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"DevilAuditor初始化失败: {e}")
            return False

    async def _setup_event_subscriptions(self):
        """设置事件订阅"""
        try:
            # 订阅因子发现事件
            await self.event_bus.subscribe(EventType.FACTOR_DISCOVERED, self._handle_factor_discovered)

            # 订阅审计请求事件
            await self.event_bus.subscribe(EventType.AUDIT_REQUEST, self._handle_audit_request)

            logger.info("DevilAuditor事件订阅设置完成")

        except Exception as e:
            logger.error(f"DevilAuditor事件订阅设置失败: {e}")
            raise

    async def _handle_factor_discovered(self, event: Event):
        """处理因子发现事件

        Args:
            event: 因子发现事件
        """
        try:
            factor_data = event.data
            factor_id = factor_data.get("factor_id")
            expression = factor_data.get("expression", "")

            logger.info(f"收到因子发现事件: {factor_id}, 表达式: {expression}")

            # 生成简单的因子代码进行审计
            factor_code = self._generate_factor_code_from_expression(expression, factor_data)

            # 执行审计
            audit_result = await self.audit_strategy(factor_code, factor_data)

            # 发布审计完成事件
            await self._publish_audit_completed(factor_id, audit_result)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"处理因子发现事件失败: {e}")

    async def _handle_audit_request(self, event: Event):
        """处理审计请求事件

        Args:
            event: 审计请求事件
        """
        try:
            audit_data = event.data
            factor_id = audit_data.get("factor_id")
            factor_code = audit_data.get("factor_code", "")
            metadata = audit_data.get("metadata", {})

            logger.info(f"收到审计请求: {factor_id}")

            # 执行审计
            audit_result = await self.audit_strategy(factor_code, metadata)

            # 发布审计完成事件
            await self._publish_audit_completed(factor_id, audit_result)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"处理审计请求事件失败: {e}")

    def _generate_factor_code_from_expression(self, expression: str, factor_data: Dict[str, Any]) -> str:
        """从因子表达式生成代码

        Args:
            expression: 因子表达式
            factor_data: 因子数据

        Returns:
            str: 生成的因子代码
        """
        code_template = f'''
def calculate_factor(data):
    """
    自动生成的因子代码
    表达式: {expression}
    IC: {factor_data.get('ic', 0.0):.4f}
    IR: {factor_data.get('ir', 0.0):.4f}
    适应度: {factor_data.get('fitness', 0.0):.4f}
    """
    import pandas as pd
    import numpy as np
    
    try:
        # 因子计算
        result = {expression}
        
        # 基本验证
        if result is None:
            return None
        
        # 返回因子值
        return result
        
    except Exception as e:
        print(f"因子计算失败: {{e}}")
        return None

# 因子元数据
FACTOR_METADATA = {{
    'expression': '{expression}',
    'ic': {factor_data.get('ic', 0.0)},
    'ir': {factor_data.get('ir', 0.0)},
    'fitness': {factor_data.get('fitness', 0.0)},
    'generation': {factor_data.get('generation', 0)}
}}
'''
        return code_template

    async def _publish_audit_completed(self, factor_id: str, audit_result: AuditResult):
        """发布审计完成事件

        Args:
            factor_id: 因子ID
            audit_result: 审计结果
        """
        try:
            await self.event_bus.publish(
                Event(
                    event_type=EventType.AUDIT_COMPLETED,
                    source_module="devil_auditor",
                    target_module="genetic_miner",
                    data={
                        "factor_id": factor_id,
                        "approved": audit_result.approved,
                        "confidence": audit_result.confidence,
                        "issues_count": len(audit_result.issues),
                        "critical_issues": len(
                            [i for i in audit_result.issues if i.severity == AuditSeverity.CRITICAL]
                        ),
                        "audit_hash": audit_result.audit_hash,
                        "execution_time": audit_result.execution_time,
                        "suggestions": audit_result.suggestions,
                        "timestamp": time.time(),
                    },
                )
            )

            logger.info(
                f"发布审计完成事件: {factor_id}, "
                f"approved={audit_result.approved}, "
                f"confidence={audit_result.confidence:.3f}"
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"发布审计完成事件失败: {e}")

    async def audit_strategy(self, strategy_code: str, metadata: Optional[Dict[str, Any]] = None) -> AuditResult:
        """审计策略代码

        白皮书依据: 第二章 2.4 魔鬼审计

        Args:
            strategy_code: 策略代码
            metadata: 策略元数据（可选）

        Returns:
            AuditResult: 审计结果

        Raises:
            ValueError: 当代码为空时
            RuntimeError: 当审计失败时
        """
        if not strategy_code or not strategy_code.strip():
            raise ValueError("策略代码不能为空")

        start_time = time.perf_counter()

        try:
            logger.info("开始魔鬼审计")

            # 1. 基础代码检查
            basic_issues = await self._basic_code_check(strategy_code)

            # 2. 未来函数检测
            future_function_issues = await self._check_future_functions(strategy_code)

            # 3. 过拟合检测
            overfitting_issues = await self._check_overfitting(strategy_code, metadata)

            # 4. 安全性检查
            security_issues = await self._security_check(strategy_code)

            # 5. DeepSeek-R1深度推理审计
            reasoning_issues = await self._deep_reasoning_audit(strategy_code, metadata)

            # 6. 汇总所有问题
            all_issues = basic_issues + future_function_issues + overfitting_issues + security_issues + reasoning_issues

            # 7. 计算审计结果
            audit_result = self._calculate_audit_result(all_issues, time.perf_counter() - start_time, strategy_code)

            # 8. 发布审计完成事件
            await self._publish_audit_event(audit_result, strategy_code)

            # 9. 更新统计信息
            self._update_statistics(audit_result)

            logger.info(
                f"魔鬼审计完成: approved={audit_result.approved}, "
                f"confidence={audit_result.confidence:.2f}, "
                f"issues={len(audit_result.issues)}, "
                f"time={audit_result.execution_time:.2f}s"
            )

            return audit_result

        except Exception as e:
            logger.error(f"魔鬼审计失败: {e}")
            raise RuntimeError(f"魔鬼审计失败: {e}") from e

    async def _basic_code_check(self, code: str) -> List[AuditIssue]:
        """基础代码检查

        Args:
            code: 策略代码

        Returns:
            List[AuditIssue]: 发现的问题
        """
        issues = []

        try:
            # AST语法检查
            ast.parse(code)
        except SyntaxError as e:
            issues.append(
                AuditIssue(
                    issue_type="syntax_error",
                    severity=AuditSeverity.CRITICAL,
                    description=f"语法错误: {e.msg}",
                    location=f"第{e.lineno}行",
                    suggestion="修复语法错误",
                    code_snippet=e.text or "",
                )
            )

        # 检查代码长度
        lines = code.split("\n")
        if len(lines) > 1000:
            issues.append(
                AuditIssue(
                    issue_type="code_too_long",
                    severity=AuditSeverity.MEDIUM,
                    description=f"代码过长: {len(lines)}行 > 1000行",
                    location="全局",
                    suggestion="考虑拆分为多个函数或模块",
                )
            )

        # 检查函数复杂度
        for i, line in enumerate(lines, 1):
            if line.count("if") + line.count("for") + line.count("while") > 5:
                issues.append(
                    AuditIssue(
                        issue_type="high_complexity",
                        severity=AuditSeverity.MEDIUM,
                        description="单行复杂度过高",
                        location=f"第{i}行",
                        suggestion="简化逻辑或拆分函数",
                        code_snippet=line.strip(),
                    )
                )

        return issues

    async def _check_future_functions(self, code: str) -> List[AuditIssue]:
        """检测未来函数

        白皮书依据: 第二章 2.4 未来函数检测

        Args:
            code: 策略代码

        Returns:
            List[AuditIssue]: 未来函数问题
        """
        issues = []
        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            for pattern in self.future_function_patterns:
                if re.search(pattern, line):
                    issues.append(
                        AuditIssue(
                            issue_type="future_function",
                            severity=AuditSeverity.CRITICAL,
                            description="检测到未来函数：使用了未来数据",
                            location=f"第{i}行",
                            suggestion="移除未来函数或使用历史数据",
                            code_snippet=line.strip(),
                        )
                    )

        # 检查shift负数
        shift_pattern = r"shift\s*\(\s*(-\d+)\s*\)"
        for match in re.finditer(shift_pattern, code):
            shift_value = int(match.group(1))
            if shift_value < 0:
                issues.append(
                    AuditIssue(
                        issue_type="negative_shift",
                        severity=AuditSeverity.CRITICAL,
                        description=f"负数shift({shift_value})：使用了未来数据",
                        location="代码中",
                        suggestion=f"将shift({shift_value})改为shift({abs(shift_value)})",
                    )
                )

        return issues

    async def _check_overfitting(
        self, code: str, metadata: Optional[Dict[str, Any]]  # pylint: disable=unused-argument
    ) -> List[AuditIssue]:  # pylint: disable=unused-argument
        """检测过拟合

        白皮书依据: 第二章 2.4 过拟合检测

        Args:
            code: 策略代码
            metadata: 策略元数据

        Returns:
            List[AuditIssue]: 过拟合问题
        """
        issues = []

        # 检查参数数量
        param_count = code.count("=") + code.count("def ")
        if param_count > 50:
            issues.append(
                AuditIssue(
                    issue_type="too_many_parameters",
                    severity=AuditSeverity.HIGH,
                    description=f"参数过多: {param_count}个参数",
                    location="全局",
                    suggestion="减少参数数量，使用更简单的模型",
                )
            )

        # 检查复杂的条件判断
        complex_conditions = len(re.findall(r"if.*and.*and", code))
        if complex_conditions > 10:
            issues.append(
                AuditIssue(
                    issue_type="complex_conditions",
                    severity=AuditSeverity.MEDIUM,
                    description=f"复杂条件过多: {complex_conditions}个",
                    location="全局",
                    suggestion="简化条件逻辑",
                )
            )

        # 检查硬编码数值
        magic_numbers = len(re.findall(r"\b\d+\.\d+\b", code))
        if magic_numbers > 20:
            issues.append(
                AuditIssue(
                    issue_type="magic_numbers",
                    severity=AuditSeverity.MEDIUM,
                    description=f"硬编码数值过多: {magic_numbers}个",
                    location="全局",
                    suggestion="将数值定义为参数或常量",
                )
            )

        return issues

    async def _security_check(self, code: str) -> List[AuditIssue]:
        """安全性检查

        Args:
            code: 策略代码

        Returns:
            List[AuditIssue]: 安全问题
        """
        issues = []
        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            # 检查危险函数
            for dangerous_func in self.dangerous_functions:
                if dangerous_func in line:
                    issues.append(
                        AuditIssue(
                            issue_type="dangerous_function",
                            severity=AuditSeverity.CRITICAL,
                            description=f"使用了危险函数: {dangerous_func}",
                            location=f"第{i}行",
                            suggestion=f"移除或替换危险函数 {dangerous_func}",
                            code_snippet=line.strip(),
                        )
                    )

            # 检查网络访问
            if any(keyword in line for keyword in ["requests.", "urllib.", "http"]):
                issues.append(
                    AuditIssue(
                        issue_type="network_access",
                        severity=AuditSeverity.HIGH,
                        description="检测到网络访问",
                        location=f"第{i}行",
                        suggestion="策略不应进行网络访问",
                        code_snippet=line.strip(),
                    )
                )

            # 检查文件操作
            if any(keyword in line for keyword in ["open(", "file(", "with open"]):
                issues.append(
                    AuditIssue(
                        issue_type="file_access",
                        severity=AuditSeverity.HIGH,
                        description="检测到文件操作",
                        location=f"第{i}行",
                        suggestion="策略不应直接操作文件",
                        code_snippet=line.strip(),
                    )
                )

        return issues

    async def _deep_reasoning_audit(self, code: str, metadata: Optional[Dict[str, Any]]) -> List[AuditIssue]:
        """DeepSeek-R1深度推理审计

        白皮书依据: 第二章 2.4 DeepSeek-R1推理审计

        Args:
            code: 策略代码
            metadata: 策略元数据

        Returns:
            List[AuditIssue]: 推理发现的问题
        """
        issues = []

        # 如果LLMGateway不可用（测试环境），跳过LLM审计
        if self.llm_gateway is None:
            logger.info("LLMGateway不可用，跳过深度推理审计")
            return issues

        try:
            # 构建审计提示词
            audit_prompt = self._build_audit_prompt(code, metadata)

            # 调用DeepSeek-R1进行推理
            llm_request = LLMRequest(
                messages=[
                    {"role": "system", "content": "你是一个专业的量化策略审计专家，具有深度推理能力。"},
                    {"role": "user", "content": audit_prompt},
                ],
                call_type=CallType.STRATEGY_ANALYSIS,
                provider=LLMProvider.DEEPSEEK,
                model="deepseek-reasoner",
                max_tokens=2000,
                temperature=0.1,
            )

            response = await self.llm_gateway.call_llm(llm_request)

            # 解析LLM响应
            reasoning_issues = self._parse_llm_audit_response(response.content)
            issues.extend(reasoning_issues)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"DeepSeek-R1推理审计失败: {e}")
            # 不抛出异常，继续其他检查
            issues.append(
                AuditIssue(
                    issue_type="reasoning_audit_failed",
                    severity=AuditSeverity.MEDIUM,
                    description=f"深度推理审计失败: {e}",
                    location="全局",
                    suggestion="手动检查策略逻辑",
                )
            )

        return issues

    def _build_audit_prompt(self, code: str, metadata: Optional[Dict[str, Any]]) -> str:
        """构建审计提示词

        Args:
            code: 策略代码
            metadata: 策略元数据

        Returns:
            str: 审计提示词
        """
        prompt = f"""
请对以下量化策略代码进行深度审计，重点关注：

1. 逻辑一致性：策略逻辑是否合理
2. 数据泄露：是否使用了未来数据
3. 过拟合风险：参数是否过于复杂
4. 实现错误：代码实现是否有bug
5. 性能问题：是否存在性能瓶颈

策略代码：
```python
{code[:2000]}  # 限制长度避免超出token限制
```

策略元数据：
{metadata if metadata else "无"}

请以JSON格式返回审计结果：
{{
    "issues": [
        {{
            "type": "问题类型",
            "severity": "严重程度(low/medium/high/critical)",
            "description": "问题描述",
            "suggestion": "修复建议"
        }}
    ],
    "overall_assessment": "整体评估",
    "confidence": "置信度(0-1)"
}}
"""
        return prompt

    def _parse_llm_audit_response(self, response: str) -> List[AuditIssue]:
        """解析LLM审计响应

        Args:
            response: LLM响应内容

        Returns:
            List[AuditIssue]: 解析出的问题
        """
        issues = []

        try:
            import json  # pylint: disable=import-outside-toplevel

            # 尝试解析JSON响应
            if "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]

                audit_data = json.loads(json_str)

                for issue_data in audit_data.get("issues", []):
                    severity_map = {
                        "low": AuditSeverity.LOW,
                        "medium": AuditSeverity.MEDIUM,
                        "high": AuditSeverity.HIGH,
                        "critical": AuditSeverity.CRITICAL,
                    }

                    issues.append(
                        AuditIssue(
                            issue_type=issue_data.get("type", "llm_detected"),
                            severity=severity_map.get(issue_data.get("severity", "medium"), AuditSeverity.MEDIUM),
                            description=issue_data.get("description", ""),
                            location="LLM分析",
                            suggestion=issue_data.get("suggestion", ""),
                        )
                    )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"解析LLM审计响应失败: {e}")
            # 创建一个通用问题
            issues.append(
                AuditIssue(
                    issue_type="llm_parse_failed",
                    severity=AuditSeverity.LOW,
                    description="LLM审计响应解析失败",
                    location="全局",
                    suggestion="手动检查LLM响应内容",
                )
            )

        return issues

    def _calculate_audit_result(self, issues: List[AuditIssue], execution_time: float, code: str) -> AuditResult:
        """计算审计结果

        Args:
            issues: 所有问题
            execution_time: 执行时间
            code: 策略代码

        Returns:
            AuditResult: 审计结果
        """
        # 计算严重程度权重
        severity_weights = {
            AuditSeverity.LOW: 1,
            AuditSeverity.MEDIUM: 3,
            AuditSeverity.HIGH: 7,
            AuditSeverity.CRITICAL: 15,
        }

        # 计算总权重
        total_weight = sum(severity_weights[issue.severity] for issue in issues)

        # 计算置信度（基于问题严重程度）
        if total_weight == 0:
            confidence = 0.95
            approved = True
        elif total_weight <= 5:
            confidence = 0.80
            approved = True
        elif total_weight <= 15:
            confidence = 0.60
            approved = False
        else:
            confidence = 0.30
            approved = False

        # 如果有CRITICAL问题，直接拒绝
        critical_issues = [issue for issue in issues if issue.severity == AuditSeverity.CRITICAL]
        if critical_issues:
            approved = False
            confidence = min(confidence, 0.20)

        # 生成改进建议
        suggestions = []
        if critical_issues:
            suggestions.append("立即修复所有CRITICAL级别问题")

        high_issues = [issue for issue in issues if issue.severity == AuditSeverity.HIGH]
        if high_issues:
            suggestions.append("修复HIGH级别安全问题")

        if total_weight > 10:
            suggestions.append("简化策略逻辑，减少复杂度")

        if not suggestions:
            suggestions.append("策略通过审计，可以部署")

        # 生成审计哈希
        audit_hash = hashlib.md5((code + str(time.time())).encode()).hexdigest()[:16]

        return AuditResult(
            approved=approved,
            confidence=confidence,
            issues=issues,
            suggestions=suggestions,
            execution_time=execution_time,
            audit_hash=audit_hash,
        )

    async def _publish_audit_event(self, audit_result: AuditResult, code: str):  # pylint: disable=unused-argument
        """发布审计完成事件

        Args:
            audit_result: 审计结果
            code: 策略代码
        """
        try:
            await self.event_bus.publish(
                Event(
                    event_type=EventType.ANALYSIS_COMPLETED,
                    source_module="devil_auditor",
                    data={
                        "action": "audit_completed",
                        "approved": audit_result.approved,
                        "confidence": audit_result.confidence,
                        "issues_count": len(audit_result.issues),
                        "critical_issues": len(
                            [i for i in audit_result.issues if i.severity == AuditSeverity.CRITICAL]
                        ),
                        "audit_hash": audit_result.audit_hash,
                        "execution_time": audit_result.execution_time,
                    },
                )
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"发布审计事件失败: {e}")

    def _update_statistics(self, audit_result: AuditResult):
        """更新统计信息

        Args:
            audit_result: 审计结果
        """
        self.audit_count += 1

        # 更新通过率
        if audit_result.approved:
            self.approval_rate = (self.approval_rate * (self.audit_count - 1) + 1) / self.audit_count
        else:
            self.approval_rate = (self.approval_rate * (self.audit_count - 1)) / self.audit_count

        # 更新平均置信度
        self.avg_confidence = (
            self.avg_confidence * (self.audit_count - 1) + audit_result.confidence
        ) / self.audit_count

    def get_statistics(self) -> Dict[str, Any]:
        """获取审计统计信息

        Returns:
            Dict: 统计信息
        """
        return {
            "audit_count": self.audit_count,
            "approval_rate": self.approval_rate,
            "avg_confidence": self.avg_confidence,
            "dangerous_functions_count": len(self.dangerous_functions),
            "future_function_patterns_count": len(self.future_function_patterns),
        }

    async def batch_audit(self, strategies: List[Dict[str, Any]]) -> List[AuditResult]:
        """批量审计策略

        Args:
            strategies: 策略列表，每个包含 'code' 和 'metadata'

        Returns:
            List[AuditResult]: 审计结果列表
        """
        results = []

        for i, strategy in enumerate(strategies):
            logger.info(f"批量审计进度: {i+1}/{len(strategies)}")

            try:
                result = await self.audit_strategy(strategy.get("code", ""), strategy.get("metadata"))
                results.append(result)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"策略 {i+1} 审计失败: {e}")
                # 创建失败结果
                results.append(
                    AuditResult(
                        approved=False,
                        confidence=0.0,
                        issues=[
                            AuditIssue(
                                issue_type="audit_failed",
                                severity=AuditSeverity.CRITICAL,
                                description=f"审计失败: {e}",
                                location="全局",
                                suggestion="检查代码格式和内容",
                            )
                        ],
                        suggestions=["修复代码错误后重新审计"],
                        execution_time=0.0,
                        audit_hash="failed",
                    )
                )

        logger.info(f"批量审计完成: {len(results)}个策略")
        return results
