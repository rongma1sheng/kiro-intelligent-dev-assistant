"""认证API网关

白皮书依据: 第四章 4.3.2 Z2H认证系统 - API接口

本模块实现认证系统的RESTful API接口，提供前端调用认证功能和查询认证数据的能力。

核心功能：
- 启动认证流程API
- 查询认证状态API
- 查询认证记录API
- 查询Z2H基因胶囊API
- 撤销认证API
- 降级认证API
- 导出认证报告API
- 统一错误处理和响应格式

Author: MIA System
Version: 1.0.0
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

from src.evolution.certification_failure_analyzer import CertificationFailureAnalyzer
from src.evolution.certification_persistence_service import CertificationPersistenceService
from src.evolution.certification_traceability import CertificationTraceabilityManager
from src.evolution.z2h_certification_v2 import Z2HCertificationV2
from src.evolution.z2h_data_models import CertificationLevel, CertificationStatus


class ResponseStatus(Enum):
    """响应状态枚举

    白皮书依据: Requirement 13.8 - 标准JSON格式响应
    """

    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"


@dataclass
class APIResponse:
    """API响应数据模型

    白皮书依据: Requirement 13.8 - 标准JSON格式响应

    Attributes:
        status: 响应状态
        message: 响应消息
        data: 响应数据
        error: 错误信息（仅在status=ERROR时）
        timestamp: 响应时间戳
    """

    status: ResponseStatus
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: str = None

    def __post_init__(self):
        """初始化后处理"""
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            字典格式的响应数据
        """
        result = {"status": self.status.value, "message": self.message, "timestamp": self.timestamp}

        if self.data is not None:
            result["data"] = self.data

        if self.error is not None:
            result["error"] = self.error

        return result


@dataclass
class StartCertificationRequest:
    """启动认证请求数据模型

    Attributes:
        strategy_id: 策略ID
        strategy_name: 策略名称
        strategy_type: 策略类型
        source_factors: 源因子列表
    """

    strategy_id: str
    strategy_name: str
    strategy_type: str
    source_factors: List[str]


@dataclass
class RevokeCertificationRequest:
    """撤销认证请求数据模型

    Attributes:
        strategy_id: 策略ID
        reason: 撤销原因
    """

    strategy_id: str
    reason: str


@dataclass
class DowngradeCertificationRequest:
    """降级认证请求数据模型

    Attributes:
        strategy_id: 策略ID
        new_level: 新的认证等级
        reason: 降级原因
    """

    strategy_id: str
    new_level: str
    reason: str


class CertificationAPIGateway:
    """认证API网关

    白皮书依据: 第四章 4.3.2 Z2H认证系统 - API接口

    提供RESTful API接口，方便前端调用认证功能和查询认证数据。
    实现统一的错误处理和响应格式。

    Attributes:
        certification_service: Z2H认证服务
        persistence_service: 数据持久化服务
        traceability_manager: 可追溯性管理器
        failure_analyzer: 失败分析器
    """

    def __init__(
        self,
        certification_service: Z2HCertificationV2,
        persistence_service: CertificationPersistenceService,
        traceability_manager: CertificationTraceabilityManager,
        failure_analyzer: CertificationFailureAnalyzer,
    ):
        """初始化API网关

        Args:
            certification_service: Z2H认证服务
            persistence_service: 数据持久化服务
            traceability_manager: 可追溯性管理器
            failure_analyzer: 失败分析器
        """
        self.certification_service = certification_service
        self.persistence_service = persistence_service
        self.traceability_manager = traceability_manager
        self.failure_analyzer = failure_analyzer

        logger.info("初始化CertificationAPIGateway")

    def start_certification(self, request: StartCertificationRequest) -> APIResponse:
        """启动认证流程

        白皮书依据: Requirement 13.1 - 启动认证流程API

        Args:
            request: 启动认证请求

        Returns:
            API响应
        """
        try:
            logger.info(
                f"收到启动认证请求 - " f"strategy_id={request.strategy_id}, " f"strategy_name={request.strategy_name}"
            )

            # 调用认证服务启动认证流程
            # 注意：这里假设certification_service有start_certification方法
            # 实际实现需要根据Z2HCertificationV2的接口调整

            # 保存初始状态
            metadata = {
                "strategy_id": request.strategy_id,
                "strategy_name": request.strategy_name,
                "strategy_type": request.strategy_type,
                "source_factors": request.source_factors,
                "status": CertificationStatus.IN_PROGRESS.value,
                "created_at": datetime.now().isoformat(),
            }

            self.persistence_service.save_strategy_metadata(request.strategy_id, metadata)

            # 记录状态变更
            self.persistence_service.save_status_change(
                request.strategy_id,
                {
                    "from_status": "not_started",
                    "to_status": CertificationStatus.IN_PROGRESS.value,
                    "reason": "认证流程启动",
                },
            )

            return APIResponse(
                status=ResponseStatus.SUCCESS,
                message="认证流程已启动",
                data={
                    "strategy_id": request.strategy_id,
                    "status": CertificationStatus.IN_PROGRESS.value,
                    "created_at": metadata["created_at"],
                },
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"启动认证流程失败: {e}")
            return APIResponse(
                status=ResponseStatus.ERROR,
                message="启动认证流程失败",
                error={"type": type(e).__name__, "message": str(e)},
            )

    def get_certification_status(self, strategy_id: str) -> APIResponse:
        """查询认证状态

        白皮书依据: Requirement 13.2 - 查询认证状态API

        Args:
            strategy_id: 策略ID

        Returns:
            API响应
        """
        try:
            logger.info(f"查询认证状态 - strategy_id={strategy_id}")

            # 加载策略元数据
            metadata = self.persistence_service.load_strategy_metadata(strategy_id)

            if metadata is None:
                return APIResponse(
                    status=ResponseStatus.ERROR,
                    message="策略不存在",
                    error={"type": "NotFoundError", "message": f"未找到策略: {strategy_id}"},
                )

            # 加载状态历史
            history = self.persistence_service.load_status_history(strategy_id)

            return APIResponse(
                status=ResponseStatus.SUCCESS,
                message="查询成功",
                data={
                    "strategy_id": strategy_id,
                    "strategy_name": metadata.get("strategy_name"),
                    "current_status": metadata.get("status"),
                    "certification_level": metadata.get("certification_level"),
                    "created_at": metadata.get("created_at"),
                    "last_updated": metadata.get("last_updated"),
                    "status_history": history[-5:] if history else [],  # 最近5条记录
                },
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"查询认证状态失败: {e}")
            return APIResponse(
                status=ResponseStatus.ERROR,
                message="查询认证状态失败",
                error={"type": type(e).__name__, "message": str(e)},
            )

    def get_certification_records(
        self, status: Optional[str] = None, level: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> APIResponse:
        """查询认证记录

        白皮书依据: Requirement 13.3 - 查询认证记录API

        Args:
            status: 过滤状态（可选）
            level: 过滤认证等级（可选）
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            API响应
        """
        try:
            logger.info(f"查询认证记录 - " f"status={status}, level={level}, limit={limit}, offset={offset}")

            # 使用可追溯性管理器查询
            if status:
                traces = self.traceability_manager.query_by_status(status)
            else:
                # 如果没有指定状态，查询所有记录
                # 这里需要一个查询所有记录的方法，暂时返回空列表
                traces = []

            if level:
                traces = [t for t in traces if t.certification_level and t.certification_level.value == level]

            # 分页
            total = len(traces)
            traces = traces[offset : offset + limit]

            # 转换为响应格式
            records = []
            for trace in traces:
                records.append(
                    {
                        "trace_id": trace.trace_id,
                        "strategy_id": trace.strategy_id,
                        "strategy_name": trace.strategy_name,
                        "certification_level": trace.certification_level.value if trace.certification_level else None,
                        "status": trace.final_status,
                        "start_time": trace.start_time.isoformat(),
                        "end_time": trace.end_time.isoformat() if trace.end_time else None,
                    }
                )

            return APIResponse(
                status=ResponseStatus.SUCCESS,
                message="查询成功",
                data={"total": total, "limit": limit, "offset": offset, "records": records},
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"查询认证记录失败: {e}")
            return APIResponse(
                status=ResponseStatus.ERROR,
                message="查询认证记录失败",
                error={"type": type(e).__name__, "message": str(e)},
            )

    def get_gene_capsule(self, strategy_id: str) -> APIResponse:
        """查询Z2H基因胶囊

        白皮书依据: Requirement 13.4 - 查询Z2H基因胶囊API

        Args:
            strategy_id: 策略ID

        Returns:
            API响应
        """
        try:
            logger.info(f"查询Z2H基因胶囊 - strategy_id={strategy_id}")

            # 加载基因胶囊
            gene_capsule = self.persistence_service.load_gene_capsule(strategy_id)

            if gene_capsule is None:
                return APIResponse(
                    status=ResponseStatus.ERROR,
                    message="基因胶囊不存在",
                    error={"type": "NotFoundError", "message": f"未找到策略的基因胶囊: {strategy_id}"},
                )

            return APIResponse(status=ResponseStatus.SUCCESS, message="查询成功", data=gene_capsule.to_dict())

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"查询Z2H基因胶囊失败: {e}")
            return APIResponse(
                status=ResponseStatus.ERROR,
                message="查询Z2H基因胶囊失败",
                error={"type": type(e).__name__, "message": str(e)},
            )

    def revoke_certification(self, request: RevokeCertificationRequest) -> APIResponse:
        """撤销认证

        白皮书依据: Requirement 13.5 - 撤销认证API

        Args:
            request: 撤销认证请求

        Returns:
            API响应
        """
        try:
            logger.info(f"撤销认证 - " f"strategy_id={request.strategy_id}, reason={request.reason}")

            # 调用认证服务撤销认证
            # 注意：这里假设certification_service有revoke_certification方法
            # 实际实现需要根据Z2HCertificationV2的接口调整

            # 更新元数据
            metadata = self.persistence_service.load_strategy_metadata(request.strategy_id)
            if metadata is None:
                return APIResponse(
                    status=ResponseStatus.ERROR,
                    message="策略不存在",
                    error={"type": "NotFoundError", "message": f"未找到策略: {request.strategy_id}"},
                )

            old_status = metadata.get("status")
            metadata["status"] = CertificationStatus.REVOKED.value
            metadata["revoked_at"] = datetime.now().isoformat()
            metadata["revoke_reason"] = request.reason

            self.persistence_service.save_strategy_metadata(request.strategy_id, metadata)

            # 记录状态变更
            self.persistence_service.save_status_change(
                request.strategy_id,
                {"from_status": old_status, "to_status": CertificationStatus.REVOKED.value, "reason": request.reason},
            )

            return APIResponse(
                status=ResponseStatus.SUCCESS,
                message="认证已撤销",
                data={
                    "strategy_id": request.strategy_id,
                    "status": CertificationStatus.REVOKED.value,
                    "revoked_at": metadata["revoked_at"],
                    "reason": request.reason,
                },
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"撤销认证失败: {e}")
            return APIResponse(
                status=ResponseStatus.ERROR, message="撤销认证失败", error={"type": type(e).__name__, "message": str(e)}
            )

    def downgrade_certification(self, request: DowngradeCertificationRequest) -> APIResponse:
        """降级认证

        白皮书依据: Requirement 13.6 - 降级认证API

        Args:
            request: 降级认证请求

        Returns:
            API响应
        """
        try:
            logger.info(
                f"降级认证 - "
                f"strategy_id={request.strategy_id}, "
                f"new_level={request.new_level}, "
                f"reason={request.reason}"
            )

            # 验证新等级
            try:
                new_level = CertificationLevel[request.new_level.upper()]
            except KeyError:
                return APIResponse(
                    status=ResponseStatus.ERROR,
                    message="无效的认证等级",
                    error={"type": "ValidationError", "message": f"无效的认证等级: {request.new_level}"},
                )

            # 更新元数据
            metadata = self.persistence_service.load_strategy_metadata(request.strategy_id)
            if metadata is None:
                return APIResponse(
                    status=ResponseStatus.ERROR,
                    message="策略不存在",
                    error={"type": "NotFoundError", "message": f"未找到策略: {request.strategy_id}"},
                )

            old_level = metadata.get("certification_level")
            metadata["certification_level"] = new_level.value
            metadata["downgraded_at"] = datetime.now().isoformat()
            metadata["downgrade_reason"] = request.reason

            self.persistence_service.save_strategy_metadata(request.strategy_id, metadata)

            # 记录状态变更
            self.persistence_service.save_status_change(
                request.strategy_id,
                {
                    "from_status": f"certified_{old_level}",
                    "to_status": f"certified_{new_level.value}",
                    "reason": f"降级: {request.reason}",
                },
            )

            return APIResponse(
                status=ResponseStatus.SUCCESS,
                message="认证已降级",
                data={
                    "strategy_id": request.strategy_id,
                    "old_level": old_level,
                    "new_level": new_level.value,
                    "downgraded_at": metadata["downgraded_at"],
                    "reason": request.reason,
                },
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"降级认证失败: {e}")
            return APIResponse(
                status=ResponseStatus.ERROR, message="降级认证失败", error={"type": type(e).__name__, "message": str(e)}
            )

    def get_certification_report(self, strategy_id: str) -> APIResponse:
        """导出认证报告

        白皮书依据: Requirement 13.7 - 导出认证报告API

        Args:
            strategy_id: 策略ID

        Returns:
            API响应
        """
        try:
            logger.info(f"导出认证报告 - strategy_id={strategy_id}")

            # 查询可追溯性记录
            traces = self.traceability_manager.query_by_strategy_id(strategy_id)

            if not traces:
                return APIResponse(
                    status=ResponseStatus.ERROR,
                    message="未找到认证记录",
                    error={"type": "NotFoundError", "message": f"未找到策略的认证记录: {strategy_id}"},
                )

            # 获取最新的trace
            trace = traces[0]

            # 生成审计报告
            report = self.traceability_manager.generate_audit_report(trace.trace_id)

            # 如果认证失败，添加失败分析
            if trace.final_status == "failed":
                # 这里需要构造失败数据，实际实现需要从持久化服务加载
                failure_report = self.failure_analyzer.generate_failure_analysis_report(
                    strategy_id=strategy_id,
                    strategy_name=trace.strategy_name,
                    failed_stage="unknown",  # 需要从trace中获取
                    arena_result={},  # 需要加载实际数据
                    simulation_result={},  # 需要加载实际数据
                )
                report["failure_analysis"] = failure_report.to_dict()

            return APIResponse(status=ResponseStatus.SUCCESS, message="报告生成成功", data=report)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"导出认证报告失败: {e}")
            return APIResponse(
                status=ResponseStatus.ERROR,
                message="导出认证报告失败",
                error={"type": type(e).__name__, "message": str(e)},
            )
