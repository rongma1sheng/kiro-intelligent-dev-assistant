# pylint: disable=too-many-lines
"""Engineering Law Validator

白皮书依据: 第九章 9.0 工程铁律 (The Constitution)

This module validates code changes against the 31 engineering laws defined in the MIA whitepaper.
All laws must be checked exactly once for each code change to ensure architectural integrity
and operational safety.

MIA编码铁律依据:
- 铁律1: 白皮书至上 - All laws are defined in whitepaper Chapter 9
- 铁律2: 禁止简化和占位符 - Complete implementation with no placeholders
- 铁律3: 完整的错误处理 - All validation paths have error handling
- 铁律4: 完整的类型注解 - All functions have complete type hints
- 铁律5: 完整的文档字符串 - All public APIs have docstrings with whitepaper references
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable, List, Optional

from loguru import logger


class LawSeverity(Enum):
    """Law violation severity levels"""

    CRITICAL = "CRITICAL"  # System cannot function safely
    HIGH = "HIGH"  # Major architectural violation
    MEDIUM = "MEDIUM"  # Important but not critical


@dataclass
class EngineeringLaw:
    """Engineering law definition

    白皮书依据: 第九章 9.0 工程铁律

    Attributes:
        law_id: Unique law identifier (1-31)
        name: Law name (e.g., "Trinity Law")
        description: Full law description from whitepaper
        validator: Function to validate code against this law
        severity: Violation severity level
    """

    law_id: int
    name: str
    description: str
    validator: Callable[[str, List[str]], bool]
    severity: LawSeverity


@dataclass
class LawViolation:
    """Law violation details

    Attributes:
        law_id: ID of violated law
        law_name: Name of violated law
        file_path: File where violation occurred
        line_number: Line number of violation (0 if not applicable)
        description: Detailed violation description
        severity: Violation severity
    """

    law_id: int
    law_name: str
    file_path: str
    line_number: int
    description: str
    severity: LawSeverity


@dataclass
class ValidationResult:
    """Code validation result

    Attributes:
        is_valid: True if no violations found
        violations: List of law violations
        recommendations: List of recommendations to fix violations
        laws_checked: Number of laws checked
        timestamp: Validation timestamp
    """

    is_valid: bool
    violations: List[LawViolation]
    recommendations: List[str]
    laws_checked: int
    timestamp: datetime


class EngineeringLawValidator:
    """Validates code changes against 31 engineering laws

    白皮书依据: 第九章 9.0 工程铁律 (The Constitution)

    This validator ensures all code changes comply with the 31 engineering laws
    defined in the MIA whitepaper. Each law is checked exactly once per validation.

    The 31 laws cover:
    - Architecture (Trinity, Dual-Drive, AMD Compatibility)
    - Performance (Latency, Radar, Process Isolation)
    - Security (Zero Trust, Doomsday, Code Injection)
    - Operations (Auto-Pilot, Observability, Documentation Sync)
    - Trading (Spartan, Audit, Simulation, LockBox)

    Example:
        >>> validator = EngineeringLawValidator()
        >>> result = validator.validate_code_change(
        ...     code_diff="...",
        ...     affected_files=["src/brain/soldier.py"]
        ... )
        >>> if not result.is_valid:
        ...     for violation in result.violations:
        ...         print(f"Law {violation.law_id} violated: {violation.description}")
    """

    def __init__(self):
        """Initialize engineering law validator

        Raises:
            RuntimeError: If law definitions are incomplete
        """
        self._laws: List[EngineeringLaw] = []
        self._initialize_laws()

        if len(self._laws) != 31:
            raise RuntimeError(
                f"Expected 31 laws, but only {len(self._laws)} were initialized. "
                "This violates the completeness requirement."
            )

        logger.info(f"EngineeringLawValidator initialized with {len(self._laws)} laws")

    def validate_code_change(self, code_diff: str, affected_files: List[str]) -> ValidationResult:
        """Validate code change against all 31 engineering laws

        白皮书依据: 第九章 9.0 工程铁律

        This method checks the code change against all 31 laws exactly once.
        Each law is validated independently, and all violations are collected.

        Args:
            code_diff: Git diff of code changes
            affected_files: List of affected file paths

        Returns:
            ValidationResult with violations and recommendations

        Raises:
            ValueError: If code_diff is empty or affected_files is empty

        Example:
            >>> result = validator.validate_code_change(
            ...     code_diff="+def new_function():\\n+    pass",
            ...     affected_files=["src/new_module.py"]
            ... )
        """
        if not code_diff:
            raise ValueError("code_diff cannot be empty")

        if not affected_files:
            raise ValueError("affected_files cannot be empty")

        logger.info(f"Validating code change affecting {len(affected_files)} files " f"against {len(self._laws)} laws")

        violations: List[LawViolation] = []
        recommendations: List[str] = []

        # Check each law exactly once
        for law in self._laws:
            try:
                is_compliant = law.validator(code_diff, affected_files)

                if not is_compliant:
                    violation = LawViolation(
                        law_id=law.law_id,
                        law_name=law.name,
                        file_path=affected_files[0] if affected_files else "unknown",
                        line_number=0,
                        description=f"Violation of {law.name}: {law.description}",
                        severity=law.severity,
                    )
                    violations.append(violation)

                    # Add recommendation
                    recommendation = self._get_recommendation(law.law_id, law.name)
                    if recommendation:
                        recommendations.append(recommendation)

                    logger.warning(f"Law {law.law_id} ({law.name}) violated in {affected_files[0]}")

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"Error checking law {law.law_id} ({law.name}): {e}", exc_info=True)
                # Treat validation errors as violations for safety
                violation = LawViolation(
                    law_id=law.law_id,
                    law_name=law.name,
                    file_path=affected_files[0] if affected_files else "unknown",
                    line_number=0,
                    description=f"Validation error for {law.name}: {str(e)}",
                    severity=LawSeverity.HIGH,
                )
                violations.append(violation)

        is_valid = len(violations) == 0

        result = ValidationResult(
            is_valid=is_valid,
            violations=violations,
            recommendations=recommendations,
            laws_checked=len(self._laws),
            timestamp=datetime.now(),
        )

        logger.info(f"Validation complete: {len(violations)} violations found, " f"{len(self._laws)} laws checked")

        return result

    def _initialize_laws(self) -> None:
        """Initialize all 31 engineering laws

        白皮书依据: 第九章 9.0 工程铁律

        Each law is defined with:
        - Unique ID (1-31)
        - Name from whitepaper
        - Description from whitepaper
        - Validator function
        - Severity level
        """
        self._laws = [
            EngineeringLaw(
                law_id=1,
                name="Trinity Law",
                description="系统由 AMD/Client/Cloud 构成。AMD 必须具备 Cloud Failover (云端热备) 能力。",
                validator=self._check_trinity_law,
                severity=LawSeverity.CRITICAL,
            ),
            EngineeringLaw(
                law_id=2,
                name="Dual-Drive Law",
                description="C 盘只读，D 盘读写。",
                validator=self._check_dual_drive_law,
                severity=LawSeverity.HIGH,
            ),
            EngineeringLaw(
                law_id=3,
                name="Latency Law",
                description="本地优先。高频数据传输必须使用 SPSC SharedMemory。",
                validator=self._check_latency_law,
                severity=LawSeverity.HIGH,
            ),
            EngineeringLaw(
                law_id=4,
                name="Radar Law",
                description="主力识别模型必须在 AMD 本地运行。",
                validator=self._check_radar_law,
                severity=LawSeverity.HIGH,
            ),
            EngineeringLaw(
                law_id=5,
                name="AMD Compatibility Law",
                description="必须部署 GPU Watchdog，支持驱动热重载，并触发 Soldier 的热备切换。",
                validator=self._check_amd_compatibility_law,
                severity=LawSeverity.CRITICAL,
            ),
            EngineeringLaw(
                law_id=6,
                name="Process Isolation Law",
                description="内存读写必须执行 Sequence ID Atomic Check。",
                validator=self._check_process_isolation_law,
                severity=LawSeverity.CRITICAL,
            ),
            EngineeringLaw(
                law_id=7,
                name="Code Injection Law",
                description="学者引擎生成的代码必须通过 Operator Whitelist 校验。",
                validator=self._check_code_injection_law,
                severity=LawSeverity.CRITICAL,
            ),
            EngineeringLaw(
                law_id=8,
                name="Identity Law",
                description="仅执行带 Z2H 胶囊及审计签名的代码。",
                validator=self._check_identity_law,
                severity=LawSeverity.CRITICAL,
            ),
            EngineeringLaw(
                law_id=9,
                name="Spartan Law",
                description="策略必须在双轨竞技场 (实盘+合成) 中存活。",
                validator=self._check_spartan_law,
                severity=LawSeverity.HIGH,
            ),
            EngineeringLaw(
                law_id=10,
                name="Audit Law",
                description="独立审计进程确认成交。",
                validator=self._check_audit_law,
                severity=LawSeverity.CRITICAL,
            ),
            EngineeringLaw(
                law_id=11,
                name="Simulation Law",
                description="实盘模拟严禁离线回测。",
                validator=self._check_simulation_law,
                severity=LawSeverity.HIGH,
            ),
            EngineeringLaw(
                law_id=12,
                name="Zero Trust Law",
                description="严禁公网暴露端口。Client 端严禁存储 API Key。",
                validator=self._check_zero_trust_law,
                severity=LawSeverity.CRITICAL,
            ),
            EngineeringLaw(
                law_id=13,
                name="Doomsday Law",
                description="物理断电锁，人工复位。",
                validator=self._check_doomsday_law,
                severity=LawSeverity.CRITICAL,
            ),
            EngineeringLaw(
                law_id=14,
                name="Environment Law",
                description="PYTHONDONTWRITEBYTECODE=1。",
                validator=self._check_environment_law,
                severity=LawSeverity.MEDIUM,
            ),
            EngineeringLaw(
                law_id=15,
                name="State Consistency Law",
                description="原子写入协议。",
                validator=self._check_state_consistency_law,
                severity=LawSeverity.CRITICAL,
            ),
            EngineeringLaw(
                law_id=16,
                name="Auto-Pilot Law",
                description="无人值守，Job Objects 风控。",
                validator=self._check_auto_pilot_law,
                severity=LawSeverity.HIGH,
            ),
            EngineeringLaw(
                law_id=17,
                name="Observability Law",
                description="进化产物拒绝黑盒。",
                validator=self._check_observability_law,
                severity=LawSeverity.HIGH,
            ),
            EngineeringLaw(
                law_id=18,
                name="Standardization Law",
                description="Pydantic 标准 Schema。",
                validator=self._check_standardization_law,
                severity=LawSeverity.MEDIUM,
            ),
            EngineeringLaw(
                law_id=19,
                name="Calendar Law",
                description="感知交易日历。",
                validator=self._check_calendar_law,
                severity=LawSeverity.HIGH,
            ),
            EngineeringLaw(
                law_id=20,
                name="PPL Law",
                description="启动执行 PPL 自检。",
                validator=self._check_ppl_law,
                severity=LawSeverity.MEDIUM,
            ),
            EngineeringLaw(
                law_id=21,
                name="LockBox Law",
                description="利润物理隔离 (逆回购/ETF)。",
                validator=self._check_lockbox_law,
                severity=LawSeverity.HIGH,
            ),
            EngineeringLaw(
                law_id=22,
                name="Regime Law",
                description="策略执行校验 Market Regime。",
                validator=self._check_regime_law,
                severity=LawSeverity.HIGH,
            ),
            EngineeringLaw(
                law_id=23,
                name="Oracle Law",
                description="晋升策略必须通过 Cloud SOTA 审计。",
                validator=self._check_oracle_law,
                severity=LawSeverity.HIGH,
            ),
            EngineeringLaw(
                law_id=24,
                name="Clearance Law",
                description="Admin/Guest 两级权限。Guest 物理屏蔽账户数据。",
                validator=self._check_clearance_law,
                severity=LawSeverity.CRITICAL,
            ),
            EngineeringLaw(
                law_id=25,
                name="Concurrency Law",
                description="异步队列 + 单消费者。",
                validator=self._check_concurrency_law,
                severity=LawSeverity.HIGH,
            ),
            EngineeringLaw(
                law_id=26,
                name="Sandbox Law",
                description="衍生品策略必须在 Shadow Mode 下空跑验证。",
                validator=self._check_sandbox_law,
                severity=LawSeverity.HIGH,
            ),
            EngineeringLaw(
                law_id=27,
                name="UI Law",
                description="高频数据必须通过 WebSocket + Iframe 侧通道渲染。",
                validator=self._check_ui_law,
                severity=LawSeverity.MEDIUM,
            ),
            EngineeringLaw(
                law_id=28,
                name="Proxy Law",
                description="所有 Cloud API 调用必须由 AMD 核心进程发起。",
                validator=self._check_proxy_law,
                severity=LawSeverity.HIGH,
            ),
            EngineeringLaw(
                law_id=29,
                name="Failover Law",
                description="在 AMD 驱动重置期间，Soldier 必须强制切换至 Cloud API 模式，禁止系统进入无指令真空期。",
                validator=self._check_failover_law,
                severity=LawSeverity.CRITICAL,
            ),
            EngineeringLaw(
                law_id=30,
                name="Atomic Law",
                description="所有跨进程共享内存读写必须通过 SPSC 协议和序列号校验，杜绝脏读。",
                validator=self._check_atomic_law,
                severity=LawSeverity.CRITICAL,
            ),
            EngineeringLaw(
                law_id=31,
                name="Documentation Sync Law",
                description="所有功能变更、架构调整、新增组件必须同步更新白皮书和辅助文件。",
                validator=self._check_documentation_sync_law,
                severity=LawSeverity.HIGH,
            ),
        ]

    # Individual law validators

    def _check_trinity_law(self, code_diff: str, affected_files: List[str]) -> bool:
        """Check Trinity Law: AMD/Client/Cloud with hot failover

        白皮书依据: 第九章 Law 1 - Trinity Law

        Validates that system maintains AMD/Client/Cloud architecture with
        Cloud failover capability.
        """
        # Check for AMD-related files
        amd_files = [f for f in affected_files if "amd" in f.lower() or "soldier" in f.lower()]

        if not amd_files:
            return True  # Not affecting AMD components

        # Check for failover implementation
        has_failover = bool(re.search(r"(failover|cloud.*fallback|backup.*mode)", code_diff, re.IGNORECASE))

        return has_failover

    def _check_dual_drive_law(
        self, code_diff: str, affected_files: List[str]  # pylint: disable=unused-argument
    ) -> bool:  # pylint: disable=unused-argument
        """Check Dual-Drive Law: C: read-only, D: read-write

        白皮书依据: 第九章 Law 2 - Dual-Drive Law
        """
        # Check for C: drive write operations
        c_drive_write = bool(re.search(r"[Cc]:\\.*\b(write|save|create|mkdir)", code_diff))

        return not c_drive_write

    def _check_latency_law(self, code_diff: str, affected_files: List[str]) -> bool:  # pylint: disable=unused-argument
        """Check Latency Law: Local-first, SPSC for high-frequency data

        白皮书依据: 第九章 Law 3 - Latency Law
        """
        # Check for high-frequency data transfer
        has_high_freq = bool(re.search(r"(high.*freq|real.*time|streaming)", code_diff, re.IGNORECASE))

        if not has_high_freq:
            return True

        # Check for SPSC usage
        has_spsc = bool(re.search(r"(SPSC|SharedMemory|shared.*memory)", code_diff, re.IGNORECASE))

        return has_spsc

    def _check_radar_law(self, code_diff: str, affected_files: List[str]) -> bool:  # pylint: disable=unused-argument
        """Check Radar Law: Main force identification on AMD local

        白皮书依据: 第九章 Law 4 - Radar Law
        """
        # Check for radar/main force identification
        has_radar = bool(re.search(r"(radar|main.*force|主力)", code_diff, re.IGNORECASE))

        if not has_radar:
            return True

        # Check for local execution
        has_local = bool(re.search(r"(local|amd|gpu)", code_diff, re.IGNORECASE))

        return has_local

    def _check_amd_compatibility_law(
        self, code_diff: str, affected_files: List[str]  # pylint: disable=unused-argument
    ) -> bool:  # pylint: disable=unused-argument
        """Check AMD Compatibility Law: GPU Watchdog with hot reload

        白皮书依据: 第九章 Law 5 - AMD Compatibility Law
        """
        # Check for GPU-related code
        has_gpu = bool(re.search(r"(gpu|rocm|amd)", code_diff, re.IGNORECASE))

        if not has_gpu:
            return True

        # Check for watchdog or hot reload
        has_watchdog = bool(re.search(r"(watchdog|hot.*reload|driver.*reload)", code_diff, re.IGNORECASE))

        return has_watchdog

    def _check_process_isolation_law(
        self, code_diff: str, affected_files: List[str]  # pylint: disable=unused-argument
    ) -> bool:  # pylint: disable=unused-argument
        """Check Process Isolation Law: Sequence ID atomic check

        白皮书依据: 第九章 Law 6 - Process Isolation Law
        """
        # Check for shared memory operations
        has_shared_mem = bool(re.search(r"(shared.*memory|SharedMemory|multiprocessing)", code_diff, re.IGNORECASE))

        if not has_shared_mem:
            return True

        # Check for sequence ID or atomic operations
        has_atomic = bool(re.search(r"(sequence.*id|seq.*id|atomic|lock)", code_diff, re.IGNORECASE))

        return has_atomic

    def _check_code_injection_law(
        self, code_diff: str, affected_files: List[str]  # pylint: disable=unused-argument
    ) -> bool:  # pylint: disable=unused-argument
        """Check Code Injection Law: Operator whitelist validation

        白皮书依据: 第九章 Law 7 - Code Injection Law
        """
        # Check for code generation or execution
        has_codegen = bool(re.search(r"(exec|eval|compile|generate.*code)", code_diff, re.IGNORECASE))

        if not has_codegen:
            return True

        # Check for whitelist validation
        has_whitelist = bool(re.search(r"(whitelist|allowed.*operators|validate.*operator)", code_diff, re.IGNORECASE))

        return has_whitelist

    def _check_identity_law(self, code_diff: str, affected_files: List[str]) -> bool:  # pylint: disable=unused-argument
        """Check Identity Law: Z2H capsule and audit signature

        白皮书依据: 第九章 Law 8 - Identity Law
        """
        # Check for strategy execution
        has_strategy_exec = bool(
            re.search(r"(execute.*strategy|run.*strategy|strategy.*run)", code_diff, re.IGNORECASE)
        )

        if not has_strategy_exec:
            return True

        # Check for Z2H or audit signature
        has_signature = bool(
            re.search(r"(z2h|gene.*capsule|audit.*signature|signature.*check)", code_diff, re.IGNORECASE)
        )

        return has_signature

    def _check_spartan_law(self, code_diff: str, affected_files: List[str]) -> bool:  # pylint: disable=unused-argument
        """Check Spartan Law: Dual-track arena survival

        白皮书依据: 第九章 Law 9 - Spartan Law
        """
        # Check for strategy deployment
        has_deployment = bool(re.search(r"(deploy|production|live.*trading)", code_diff, re.IGNORECASE))

        if not has_deployment:
            return True

        # Check for arena testing
        has_arena = bool(re.search(r"(arena|sparta|dual.*track|simulation.*test)", code_diff, re.IGNORECASE))

        return has_arena

    def _check_audit_law(self, code_diff: str, affected_files: List[str]) -> bool:  # pylint: disable=unused-argument
        """Check Audit Law: Independent audit process

        白皮书依据: 第九章 Law 10 - Audit Law
        """
        # Check for trade execution
        has_trade = bool(re.search(r"(execute.*trade|place.*order|submit.*order)", code_diff, re.IGNORECASE))

        if not has_trade:
            return True

        # Check for audit logging
        has_audit = bool(re.search(r"(audit|log.*trade|record.*trade)", code_diff, re.IGNORECASE))

        return has_audit

    def _check_simulation_law(
        self, code_diff: str, affected_files: List[str]  # pylint: disable=unused-argument
    ) -> bool:  # pylint: disable=unused-argument
        """Check Simulation Law: No offline backtesting for live simulation

        白皮书依据: 第九章 Law 11 - Simulation Law
        """
        # Check for simulation code
        has_simulation = bool(re.search(r"(simulation|simulate|sim.*mode)", code_diff, re.IGNORECASE))

        if not has_simulation:
            return True

        # Check for offline/historical data usage
        has_offline = bool(re.search(r"(offline|historical.*data|backtest)", code_diff, re.IGNORECASE))

        return not has_offline

    def _check_zero_trust_law(
        self, code_diff: str, affected_files: List[str]  # pylint: disable=unused-argument
    ) -> bool:  # pylint: disable=unused-argument
        """Check Zero Trust Law: No public port exposure, no client-side API keys

        白皮书依据: 第九章 Law 12 - Zero Trust Law
        """
        # Check for API key storage
        has_api_key = bool(re.search(r"(api.*key|secret.*key|access.*token)\s*=", code_diff, re.IGNORECASE))

        # Check for public port binding
        has_public_port = bool(re.search(r"(0\.0\.0\.0|public.*port|expose.*port)", code_diff))

        return not (has_api_key or has_public_port)

    def _check_doomsday_law(self, code_diff: str, affected_files: List[str]) -> bool:  # pylint: disable=unused-argument
        """Check Doomsday Law: Physical power-off lock with manual reset

        白皮书依据: 第九章 Law 13 - Doomsday Law
        """
        # Check for doomsday/emergency shutdown code
        has_doomsday = bool(re.search(r"(doomsday|emergency.*shutdown|kill.*switch)", code_diff, re.IGNORECASE))

        if not has_doomsday:
            return True

        # Check for manual reset requirement
        has_manual_reset = bool(re.search(r"(manual.*reset|password|authentication)", code_diff, re.IGNORECASE))

        return has_manual_reset

    def _check_environment_law(
        self, code_diff: str, affected_files: List[str]  # pylint: disable=unused-argument
    ) -> bool:  # pylint: disable=unused-argument
        """Check Environment Law: PYTHONDONTWRITEBYTECODE=1

        白皮书依据: 第九章 Law 14 - Environment Law
        """
        # Check for Python environment setup
        has_env_setup = bool(re.search(r"(environment|env.*var|os\.environ)", code_diff, re.IGNORECASE))

        if not has_env_setup:
            return True

        # 检查PYTHONDONTWRITEBYTECODE环境变量
        has_no_bytecode = bool(re.search(r"PYTHONDONTWRITEBYTECODE", code_diff))

        return has_no_bytecode or not has_env_setup

    def _check_state_consistency_law(
        self, code_diff: str, affected_files: List[str]  # pylint: disable=unused-argument
    ) -> bool:  # pylint: disable=unused-argument
        """Check State Consistency Law: Atomic write protocol

        白皮书依据: 第九章 Law 15 - State Consistency Law
        """
        # Check for state writes
        has_state_write = bool(re.search(r"(write.*state|save.*state|persist)", code_diff, re.IGNORECASE))

        if not has_state_write:
            return True

        # Check for atomic operations
        has_atomic = bool(re.search(r"(atomic|transaction|lock|mutex)", code_diff, re.IGNORECASE))

        return has_atomic

    def _check_auto_pilot_law(
        self, code_diff: str, affected_files: List[str]  # pylint: disable=unused-argument
    ) -> bool:  # pylint: disable=unused-argument
        """Check Auto-Pilot Law: Unattended operation with Job Objects

        白皮书依据: 第九章 Law 16 - Auto-Pilot Law
        """
        # Check for daemon/service code
        has_daemon = bool(re.search(r"(daemon|service|unattended|auto.*pilot)", code_diff, re.IGNORECASE))

        if not has_daemon:
            return True

        # Check for risk control
        has_risk_control = bool(re.search(r"(risk.*control|job.*object|watchdog|monitor)", code_diff, re.IGNORECASE))

        return has_risk_control

    def _check_observability_law(
        self, code_diff: str, affected_files: List[str]  # pylint: disable=unused-argument
    ) -> bool:  # pylint: disable=unused-argument
        """Check Observability Law: No black boxes in evolution

        白皮书依据: 第九章 Law 17 - Observability Law
        """
        # Check for evolution/generation code
        has_evolution = bool(re.search(r"(evolve|generate|mutate|crossover)", code_diff, re.IGNORECASE))

        if not has_evolution:
            return True

        # Check for logging/tracing
        has_logging = bool(re.search(r"(log|trace|record|audit)", code_diff, re.IGNORECASE))

        return has_logging

    def _check_standardization_law(
        self, code_diff: str, affected_files: List[str]  # pylint: disable=unused-argument
    ) -> bool:  # pylint: disable=unused-argument
        """Check Standardization Law: Pydantic standard schema

        白皮书依据: 第九章 Law 18 - Standardization Law
        """
        # Check for data model definitions
        has_model = bool(re.search(r"(class.*\(.*\)|dataclass|model)", code_diff, re.IGNORECASE))

        if not has_model:
            return True

        # Check for Pydantic or dataclass usage
        has_standard = bool(re.search(r"(BaseModel|pydantic|dataclass)", code_diff))

        return has_standard

    def _check_calendar_law(self, code_diff: str, affected_files: List[str]) -> bool:  # pylint: disable=unused-argument
        """Check Calendar Law: Trading calendar awareness

        白皮书依据: 第九章 Law 19 - Calendar Law
        """
        # Check for trading/scheduling code
        has_trading = bool(re.search(r"(trade|schedule|execute|market)", code_diff, re.IGNORECASE))

        if not has_trading:
            return True

        # Check for calendar awareness
        has_calendar = bool(re.search(r"(calendar|trading.*day|market.*open|holiday)", code_diff, re.IGNORECASE))

        return has_calendar

    def _check_ppl_law(self, code_diff: str, affected_files: List[str]) -> bool:  # pylint: disable=unused-argument
        """Check PPL Law: Startup PPL self-check

        白皮书依据: 第九章 Law 20 - PPL Law
        """
        # Check for startup/initialization code
        has_startup = bool(re.search(r"(startup|initialize|__init__|main)", code_diff, re.IGNORECASE))

        if not has_startup:
            return True

        # Check for PPL/perplexity check
        has_ppl_check = bool(re.search(r"(ppl|perplexity|self.*check|health.*check)", code_diff, re.IGNORECASE))

        return has_ppl_check or not has_startup

    def _check_lockbox_law(self, code_diff: str, affected_files: List[str]) -> bool:  # pylint: disable=unused-argument
        """Check LockBox Law: Profit physical isolation

        白皮书依据: 第九章 Law 21 - LockBox Law
        """
        # Check for profit/fund management
        has_profit = bool(re.search(r"(profit|pnl|fund|capital)", code_diff, re.IGNORECASE))

        if not has_profit:
            return True

        # Check for lockbox/isolation mechanism
        has_lockbox = bool(re.search(r"(lockbox|isolat|gc001|reverse.*repo|etf)", code_diff, re.IGNORECASE))

        return has_lockbox or not has_profit

    def _check_regime_law(self, code_diff: str, affected_files: List[str]) -> bool:  # pylint: disable=unused-argument
        """Check Regime Law: Market regime validation

        白皮书依据: 第九章 Law 22 - Regime Law
        """
        # Check for strategy execution
        has_strategy = bool(re.search(r"(strategy.*execute|execute.*strategy)", code_diff, re.IGNORECASE))

        if not has_strategy:
            return True

        # Check for regime check
        has_regime = bool(re.search(r"(regime|market.*state|market.*condition)", code_diff, re.IGNORECASE))

        return has_regime

    def _check_oracle_law(self, code_diff: str, affected_files: List[str]) -> bool:  # pylint: disable=unused-argument
        """Check Oracle Law: Cloud SOTA audit for promotion

        白皮书依据: 第九章 Law 23 - Oracle Law
        """
        # Check for strategy promotion
        has_promotion = bool(re.search(r"(promot|upgrade|deploy.*production)", code_diff, re.IGNORECASE))

        if not has_promotion:
            return True

        # Check for cloud audit
        has_audit = bool(re.search(r"(cloud.*audit|sota.*audit|oracle)", code_diff, re.IGNORECASE))

        return has_audit

    def _check_clearance_law(
        self, code_diff: str, affected_files: List[str]  # pylint: disable=unused-argument
    ) -> bool:  # pylint: disable=unused-argument
        """Check Clearance Law: Admin/Guest two-level permissions

        白皮书依据: 第九章 Law 24 - Clearance Law
        """
        # Check for permission/access control
        has_access = bool(re.search(r"(permission|access|auth|role)", code_diff, re.IGNORECASE))

        if not has_access:
            return True

        # Check for admin/guest levels
        has_levels = bool(re.search(r"(admin|guest|role.*level|permission.*level)", code_diff, re.IGNORECASE))

        return has_levels

    def _check_concurrency_law(
        self, code_diff: str, affected_files: List[str]  # pylint: disable=unused-argument
    ) -> bool:  # pylint: disable=unused-argument
        """Check Concurrency Law: Async queue + single consumer

        白皮书依据: 第九章 Law 25 - Concurrency Law
        """
        # Check for concurrent operations
        has_concurrent = bool(re.search(r"(queue|concurrent|parallel|async)", code_diff, re.IGNORECASE))

        if not has_concurrent:
            return True

        # Check for single consumer pattern
        has_single_consumer = bool(re.search(r"(single.*consumer|spsc|one.*consumer)", code_diff, re.IGNORECASE))

        return has_single_consumer or not has_concurrent

    def _check_sandbox_law(self, code_diff: str, affected_files: List[str]) -> bool:  # pylint: disable=unused-argument
        """Check Sandbox Law: Derivatives in shadow mode

        白皮书依据: 第九章 Law 26 - Sandbox Law
        """
        # Check for derivatives strategy
        has_derivatives = bool(re.search(r"(derivative|option|future|swap)", code_diff, re.IGNORECASE))

        if not has_derivatives:
            return True

        # Check for shadow mode
        has_shadow = bool(re.search(r"(shadow.*mode|sandbox|test.*mode|simulation)", code_diff, re.IGNORECASE))

        return has_shadow

    def _check_ui_law(self, code_diff: str, affected_files: List[str]) -> bool:  # pylint: disable=unused-argument
        """Check UI Law: High-frequency data via WebSocket + Iframe

        白皮书依据: 第九章 Law 27 - UI Law
        """
        # Check for UI/dashboard code
        has_ui = bool(re.search(r"(dashboard|ui|interface|render)", code_diff, re.IGNORECASE))

        if not has_ui:
            return True

        # Check for high-frequency data
        has_high_freq = bool(re.search(r"(high.*freq|real.*time|streaming)", code_diff, re.IGNORECASE))

        if not has_high_freq:
            return True

        # Check for WebSocket
        has_websocket = bool(re.search(r"(websocket|ws|iframe)", code_diff, re.IGNORECASE))

        return has_websocket

    def _check_proxy_law(self, code_diff: str, affected_files: List[str]) -> bool:  # pylint: disable=unused-argument
        """Check Proxy Law: Cloud API calls from AMD core process

        白皮书依据: 第九章 Law 28 - Proxy Law
        """
        # Check for cloud API calls
        has_cloud_api = bool(re.search(r"(cloud.*api|api.*call|http.*request)", code_diff, re.IGNORECASE))

        if not has_cloud_api:
            return True

        # Check for AMD core process
        has_amd_core = bool(re.search(r"(amd.*core|core.*process|main.*process)", code_diff, re.IGNORECASE))

        return has_amd_core or not has_cloud_api

    def _check_failover_law(self, code_diff: str, affected_files: List[str]) -> bool:  # pylint: disable=unused-argument
        """Check Failover Law: Soldier switches to Cloud during AMD reset

        白皮书依据: 第九章 Law 29 - Failover Law
        """
        # Check for Soldier/AMD code
        has_soldier = bool(re.search(r"(soldier|amd|driver)", code_diff, re.IGNORECASE))

        if not has_soldier:
            return True

        # Check for failover to cloud
        has_cloud_failover = bool(re.search(r"(cloud.*api|failover|fallback|switch.*cloud)", code_diff, re.IGNORECASE))

        return has_cloud_failover

    def _check_atomic_law(self, code_diff: str, affected_files: List[str]) -> bool:  # pylint: disable=unused-argument
        """Check Atomic Law: SPSC protocol with sequence validation

        白皮书依据: 第九章 Law 30 - Atomic Law
        """
        # Check for shared memory operations
        has_shared_mem = bool(re.search(r"(shared.*memory|ipc|inter.*process)", code_diff, re.IGNORECASE))

        if not has_shared_mem:
            return True

        # Check for SPSC and sequence validation
        has_spsc = bool(re.search(r"(spsc|sequence.*id|seq.*check)", code_diff, re.IGNORECASE))

        return has_spsc

    def _check_documentation_sync_law(self, code_diff: str, affected_files: List[str]) -> bool:
        """Check Documentation Sync Law: Whitepaper and auxiliary files synchronized

        白皮书依据: 第九章 Law 31 - Documentation Sync Law
        """
        # Check for new features or architecture changes
        has_new_feature = bool(re.search(r"(class |def |async def )", code_diff))

        if not has_new_feature:
            return True

        # Check if documentation files are also modified
        doc_files = [
            "00_核心文档/mia.md",
            "tasks.md",
            "TODO.md",
            "IMPLEMENTATION_CHECKLIST.md",
            "ARCHITECTURE",
            "PROJECT_STRUCTURE.md",
        ]

        has_doc_update = any(any(doc_file in f for doc_file in doc_files) for f in affected_files)

        return has_doc_update

    def _get_recommendation(self, law_id: int, law_name: str) -> str:
        """Get recommendation for fixing law violation

        Args:
            law_id: ID of violated law
            law_name: Name of violated law

        Returns:
            Recommendation string
        """
        recommendations = {
            1: "Implement Cloud failover capability for AMD components",
            2: "Move write operations from C: drive to D: drive",
            3: "Use SPSC SharedMemory for high-frequency data transfer",
            4: "Run main force identification model on AMD local GPU",
            5: "Deploy GPU Watchdog with hot reload support",
            6: "Implement Sequence ID atomic check for shared memory",
            7: "Add Operator Whitelist validation for generated code",
            8: "Verify Z2H capsule and audit signature before execution",
            9: "Test strategy in dual-track arena before deployment",
            10: "Add independent audit process for trade confirmation",
            11: "Use real-time data instead of offline backtesting",
            12: "Remove public port exposure and client-side API keys",
            13: "Implement physical power-off lock with manual reset",
            14: "Set PYTHONDONTWRITEBYTECODE=1 in environment",
            15: "Use atomic write protocol for state persistence",
            16: "Add Job Objects risk control for unattended operation",
            17: "Add logging/tracing for evolution operations",
            18: "Use Pydantic BaseModel or dataclass for data models",
            19: "Add trading calendar awareness to scheduling logic",
            20: "Add PPL self-check at startup",
            21: "Implement profit isolation via GC001/ETF",
            22: "Add market regime validation before strategy execution",
            23: "Add Cloud SOTA audit for strategy promotion",
            24: "Implement Admin/Guest two-level permission system",
            25: "Use async queue with single consumer pattern",
            26: "Run derivatives strategies in shadow mode first",
            27: "Use WebSocket + Iframe for high-frequency UI data",
            28: "Route Cloud API calls through AMD core process",
            29: "Implement Soldier failover to Cloud during AMD reset",
            30: "Use SPSC protocol with sequence validation for IPC",
            31: "Update whitepaper and auxiliary documentation files",
        }

        return recommendations.get(law_id, f"Fix {law_name} violation")

    def get_law_by_id(self, law_id: int) -> Optional[EngineeringLaw]:
        """Get engineering law by ID

        Args:
            law_id: Law ID (1-31)

        Returns:
            EngineeringLaw if found, None otherwise

        Raises:
            ValueError: If law_id is out of range
        """
        if not 1 <= law_id <= 31:
            raise ValueError(f"law_id must be between 1 and 31, got {law_id}")

        for law in self._laws:
            if law.law_id == law_id:
                return law

        return None

    def get_all_laws(self) -> List[EngineeringLaw]:
        """Get all engineering laws

        Returns:
            List of all 31 engineering laws
        """
        return self._laws.copy()
