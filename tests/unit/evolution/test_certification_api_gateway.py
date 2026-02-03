"""认证API网关单元测试

白皮书依据: 第四章 4.3.2 Z2H认证系统 - API接口

测试覆盖：
- 启动认证流程API
- 查询认证状态API
- 查询认证记录API
- 查询Z2H基因胶囊API
- 撤销认证API
- 降级认证API
- 导出认证报告API
- 错误处理和响应格式

Author: MIA System
Version: 1.0.0
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from src.evolution.certification_api_gateway import (
    CertificationAPIGateway,
    APIResponse,
    ResponseStatus,
    StartCertificationRequest,
    RevokeCertificationRequest,
    DowngradeCertificationRequest
)
from src.evolution.z2h_data_models import (
    Z2HGeneCapsule,
    CertificationLevel,
    CertificationStatus,
    CapitalTier
)
from src.evolution.certification_traceability import (
    CertificationTrace,
    StageType
)


class TestAPIResponse:
    """测试APIResponse类"""
    
    def test_success_response(self):
        """测试成功响应"""
        response = APIResponse(
            status=ResponseStatus.SUCCESS,
            message="操作成功",
            data={"key": "value"}
        )
        
        assert response.status == ResponseStatus.SUCCESS
        assert response.message == "操作成功"
        assert response.data == {"key": "value"}
        assert response.error is None
        assert response.timestamp is not None
    
    def test_error_response(self):
        """测试错误响应"""
        response = APIResponse(
            status=ResponseStatus.ERROR,
            message="操作失败",
            error={"type": "ValueError", "message": "无效参数"}
        )
        
        assert response.status == ResponseStatus.ERROR
        assert response.message == "操作失败"
        assert response.data is None
        assert response.error == {"type": "ValueError", "message": "无效参数"}
    
    def test_to_dict(self):
        """测试转换为字典"""
        response = APIResponse(
            status=ResponseStatus.SUCCESS,
            message="测试",
            data={"test": "data"}
        )
        
        result = response.to_dict()
        
        assert result["status"] == "success"
        assert result["message"] == "测试"
        assert result["data"] == {"test": "data"}
        assert "timestamp" in result
        assert "error" not in result


class TestCertificationAPIGateway:
    """测试CertificationAPIGateway类"""
    
    @pytest.fixture
    def mock_certification_service(self):
        """创建模拟认证服务"""
        return Mock()
    
    @pytest.fixture
    def mock_persistence_service(self):
        """创建模拟持久化服务"""
        return Mock()
    
    @pytest.fixture
    def mock_traceability_manager(self):
        """创建模拟可追溯性管理器"""
        return Mock()
    
    @pytest.fixture
    def mock_failure_analyzer(self):
        """创建模拟失败分析器"""
        return Mock()
    
    @pytest.fixture
    def gateway(
        self,
        mock_certification_service,
        mock_persistence_service,
        mock_traceability_manager,
        mock_failure_analyzer
    ):
        """创建API网关实例"""
        return CertificationAPIGateway(
            certification_service=mock_certification_service,
            persistence_service=mock_persistence_service,
            traceability_manager=mock_traceability_manager,
            failure_analyzer=mock_failure_analyzer
        )
    
    def test_initialization(self, gateway):
        """测试初始化"""
        assert gateway.certification_service is not None
        assert gateway.persistence_service is not None
        assert gateway.traceability_manager is not None
        assert gateway.failure_analyzer is not None
    
    def test_start_certification_success(self, gateway, mock_persistence_service):
        """测试启动认证成功"""
        request = StartCertificationRequest(
            strategy_id="strategy_001",
            strategy_name="测试策略",
            strategy_type="momentum",
            source_factors=["factor_1", "factor_2"]
        )
        
        # 配置mock
        mock_persistence_service.save_strategy_metadata.return_value = True
        mock_persistence_service.save_status_change.return_value = True
        
        # 调用API
        response = gateway.start_certification(request)
        
        # 验证响应
        assert response.status == ResponseStatus.SUCCESS
        assert response.message == "认证流程已启动"
        assert response.data["strategy_id"] == "strategy_001"
        assert response.data["status"] == CertificationStatus.IN_PROGRESS.value
        
        # 验证调用
        assert mock_persistence_service.save_strategy_metadata.called
        assert mock_persistence_service.save_status_change.called
    
    def test_start_certification_error(self, gateway, mock_persistence_service):
        """测试启动认证失败"""
        request = StartCertificationRequest(
            strategy_id="strategy_001",
            strategy_name="测试策略",
            strategy_type="momentum",
            source_factors=[]
        )
        
        # 配置mock抛出异常
        mock_persistence_service.save_strategy_metadata.side_effect = Exception("数据库错误")
        
        # 调用API
        response = gateway.start_certification(request)
        
        # 验证响应
        assert response.status == ResponseStatus.ERROR
        assert response.message == "启动认证流程失败"
        assert response.error is not None
        assert response.error["type"] == "Exception"
    
    def test_get_certification_status_success(self, gateway, mock_persistence_service):
        """测试查询认证状态成功"""
        strategy_id = "strategy_001"
        
        # 配置mock
        mock_persistence_service.load_strategy_metadata.return_value = {
            "strategy_id": strategy_id,
            "strategy_name": "测试策略",
            "status": CertificationStatus.CERTIFIED.value,
            "certification_level": CertificationLevel.GOLD.value,
            "created_at": "2024-01-01T00:00:00",
            "last_updated": "2024-01-02T00:00:00"
        }
        mock_persistence_service.load_status_history.return_value = [
            {"from_status": "not_started", "to_status": "in_progress", "timestamp": "2024-01-01T00:00:00"}
        ]
        
        # 调用API
        response = gateway.get_certification_status(strategy_id)
        
        # 验证响应
        assert response.status == ResponseStatus.SUCCESS
        assert response.data["strategy_id"] == strategy_id
        assert response.data["current_status"] == CertificationStatus.CERTIFIED.value
        assert response.data["certification_level"] == CertificationLevel.GOLD.value
    
    def test_get_certification_status_not_found(self, gateway, mock_persistence_service):
        """测试查询不存在的策略"""
        strategy_id = "nonexistent"
        
        # 配置mock
        mock_persistence_service.load_strategy_metadata.return_value = None
        
        # 调用API
        response = gateway.get_certification_status(strategy_id)
        
        # 验证响应
        assert response.status == ResponseStatus.ERROR
        assert response.message == "策略不存在"
        assert response.error["type"] == "NotFoundError"
    
    def test_get_certification_records_success(self, gateway, mock_traceability_manager):
        """测试查询认证记录成功"""
        # 创建模拟trace
        trace = CertificationTrace(
            trace_id="trace_001",
            strategy_id="strategy_001",
            strategy_name="测试策略",
            start_time=datetime.now(),
            final_status="completed",
            certification_level=CertificationLevel.GOLD
        )
        
        # 配置mock
        mock_traceability_manager.query_by_status.return_value = [trace]
        
        # 调用API
        response = gateway.get_certification_records(
            status=CertificationStatus.CERTIFIED.value,
            limit=10,
            offset=0
        )
        
        # 验证响应
        assert response.status == ResponseStatus.SUCCESS
        assert response.data["total"] == 1
        assert len(response.data["records"]) == 1
        assert response.data["records"][0]["strategy_id"] == "strategy_001"
    
    def test_get_certification_records_with_pagination(self, gateway, mock_traceability_manager):
        """测试分页查询认证记录"""
        # 创建多个模拟trace
        traces = [
            CertificationTrace(
                trace_id=f"trace_{i:03d}",
                strategy_id=f"strategy_{i:03d}",
                strategy_name=f"策略{i}",
                start_time=datetime.now(),
                final_status="completed"
            )
            for i in range(20)
        ]
        
        # 配置mock
        mock_traceability_manager.query_by_status.return_value = traces
        
        # 调用API（第一页）- 指定status
        response = gateway.get_certification_records(
            status="completed",
            limit=10,
            offset=0
        )
        
        # 验证响应
        assert response.status == ResponseStatus.SUCCESS
        assert response.data["total"] == 20
        assert len(response.data["records"]) == 10
        
        # 调用API（第二页）
        response = gateway.get_certification_records(
            status="completed",
            limit=10,
            offset=10
        )
        
        # 验证响应
        assert len(response.data["records"]) == 10
    
    def test_get_gene_capsule_success(self, gateway, mock_persistence_service):
        """测试查询基因胶囊成功"""
        strategy_id = "strategy_001"
        
        # 创建模拟基因胶囊
        gene_capsule = Z2HGeneCapsule(
            strategy_id=strategy_id,
            strategy_name="测试策略",
            strategy_type="momentum",
            source_factors=["factor_1"],
            creation_date=datetime.now(),
            certification_date=datetime.now(),
            certification_level=CertificationLevel.GOLD,
            arena_overall_score=0.85,
            arena_layer_results={},
            arena_passed_layers=4,
            arena_failed_layers=[],
            simulation_duration_days=30,
            simulation_tier_results={},
            simulation_best_tier=CapitalTier.TIER_2,
            simulation_metrics={},
            max_allocation_ratio=0.15,
            recommended_capital_scale={"optimal": 30000.0},
            optimal_trade_size=5000.0,
            liquidity_requirements={},
            market_impact_analysis={},
            avg_holding_period_days=5.0,
            turnover_rate=2.0,
            avg_position_count=10,
            sector_distribution={},
            market_cap_preference="mid_cap",
            var_95=0.02,
            expected_shortfall=0.03,
            max_drawdown=0.15,
            drawdown_duration_days=10,
            volatility=0.15,
            beta=1.0,
            market_correlation=0.7,
            bull_market_performance={},
            bear_market_performance={},
            sideways_market_performance={},
            high_volatility_performance={},
            low_volatility_performance={},
            market_adaptability_score=0.85,
            optimal_deployment_timing=[],
            risk_management_rules={},
            monitoring_indicators=[],
            exit_conditions=[],
            portfolio_strategy_suggestions=[]
        )
        
        # 配置mock
        mock_persistence_service.load_gene_capsule.return_value = gene_capsule
        
        # 调用API
        response = gateway.get_gene_capsule(strategy_id)
        
        # 验证响应
        assert response.status == ResponseStatus.SUCCESS
        assert response.data["strategy_id"] == strategy_id
        assert response.data["certification_level"] == CertificationLevel.GOLD.value
    
    def test_get_gene_capsule_not_found(self, gateway, mock_persistence_service):
        """测试查询不存在的基因胶囊"""
        strategy_id = "nonexistent"
        
        # 配置mock
        mock_persistence_service.load_gene_capsule.return_value = None
        
        # 调用API
        response = gateway.get_gene_capsule(strategy_id)
        
        # 验证响应
        assert response.status == ResponseStatus.ERROR
        assert response.message == "基因胶囊不存在"
        assert response.error["type"] == "NotFoundError"
    
    def test_revoke_certification_success(self, gateway, mock_persistence_service):
        """测试撤销认证成功"""
        request = RevokeCertificationRequest(
            strategy_id="strategy_001",
            reason="性能下降"
        )
        
        # 配置mock
        mock_persistence_service.load_strategy_metadata.return_value = {
            "strategy_id": "strategy_001",
            "status": CertificationStatus.CERTIFIED.value
        }
        mock_persistence_service.save_strategy_metadata.return_value = True
        mock_persistence_service.save_status_change.return_value = True
        
        # 调用API
        response = gateway.revoke_certification(request)
        
        # 验证响应
        assert response.status == ResponseStatus.SUCCESS
        assert response.message == "认证已撤销"
        assert response.data["status"] == CertificationStatus.REVOKED.value
        assert response.data["reason"] == "性能下降"
    
    def test_revoke_certification_not_found(self, gateway, mock_persistence_service):
        """测试撤销不存在的认证"""
        request = RevokeCertificationRequest(
            strategy_id="nonexistent",
            reason="测试"
        )
        
        # 配置mock
        mock_persistence_service.load_strategy_metadata.return_value = None
        
        # 调用API
        response = gateway.revoke_certification(request)
        
        # 验证响应
        assert response.status == ResponseStatus.ERROR
        assert response.message == "策略不存在"
    
    def test_downgrade_certification_success(self, gateway, mock_persistence_service):
        """测试降级认证成功"""
        request = DowngradeCertificationRequest(
            strategy_id="strategy_001",
            new_level="SILVER",
            reason="性能下降"
        )
        
        # 配置mock
        mock_persistence_service.load_strategy_metadata.return_value = {
            "strategy_id": "strategy_001",
            "certification_level": CertificationLevel.GOLD.value
        }
        mock_persistence_service.save_strategy_metadata.return_value = True
        mock_persistence_service.save_status_change.return_value = True
        
        # 调用API
        response = gateway.downgrade_certification(request)
        
        # 验证响应
        assert response.status == ResponseStatus.SUCCESS
        assert response.message == "认证已降级"
        assert response.data["old_level"] == CertificationLevel.GOLD.value
        assert response.data["new_level"] == CertificationLevel.SILVER.value
    
    def test_downgrade_certification_invalid_level(self, gateway, mock_persistence_service):
        """测试降级到无效等级"""
        request = DowngradeCertificationRequest(
            strategy_id="strategy_001",
            new_level="INVALID",
            reason="测试"
        )
        
        # 配置mock
        mock_persistence_service.load_strategy_metadata.return_value = {
            "strategy_id": "strategy_001"
        }
        
        # 调用API
        response = gateway.downgrade_certification(request)
        
        # 验证响应
        assert response.status == ResponseStatus.ERROR
        assert response.message == "无效的认证等级"
        assert response.error["type"] == "ValidationError"
    
    def test_get_certification_report_success(self, gateway, mock_traceability_manager):
        """测试导出认证报告成功"""
        strategy_id = "strategy_001"
        
        # 创建模拟trace
        trace = CertificationTrace(
            trace_id="trace_001",
            strategy_id=strategy_id,
            strategy_name="测试策略",
            start_time=datetime.now(),
            final_status="completed",
            certification_level=CertificationLevel.GOLD
        )
        
        # 配置mock
        mock_traceability_manager.query_by_strategy_id.return_value = [trace]
        mock_traceability_manager.generate_audit_report.return_value = {
            "trace_id": "trace_001",
            "strategy_id": strategy_id,
            "report": "详细报告"
        }
        
        # 调用API
        response = gateway.get_certification_report(strategy_id)
        
        # 验证响应
        assert response.status == ResponseStatus.SUCCESS
        assert response.message == "报告生成成功"
        assert "trace_id" in response.data
    
    def test_get_certification_report_not_found(self, gateway, mock_traceability_manager):
        """测试导出不存在的报告"""
        strategy_id = "nonexistent"
        
        # 配置mock
        mock_traceability_manager.query_by_strategy_id.return_value = []
        
        # 调用API
        response = gateway.get_certification_report(strategy_id)
        
        # 验证响应
        assert response.status == ResponseStatus.ERROR
        assert response.message == "未找到认证记录"
        assert response.error["type"] == "NotFoundError"
    
    def test_get_certification_status_error(self, gateway, mock_persistence_service):
        """测试查询认证状态异常"""
        strategy_id = "strategy_001"
        
        # 配置mock抛出异常
        mock_persistence_service.load_strategy_metadata.side_effect = Exception("数据库错误")
        
        # 调用API
        response = gateway.get_certification_status(strategy_id)
        
        # 验证响应
        assert response.status == ResponseStatus.ERROR
        assert response.message == "查询认证状态失败"
        assert response.error["type"] == "Exception"
    
    def test_get_certification_records_error(self, gateway, mock_traceability_manager):
        """测试查询认证记录异常"""
        # 配置mock抛出异常
        mock_traceability_manager.query_by_status.side_effect = Exception("查询错误")
        
        # 调用API
        response = gateway.get_certification_records(status="completed")
        
        # 验证响应
        assert response.status == ResponseStatus.ERROR
        assert response.message == "查询认证记录失败"
        assert response.error["type"] == "Exception"
    
    def test_get_gene_capsule_error(self, gateway, mock_persistence_service):
        """测试查询基因胶囊异常"""
        strategy_id = "strategy_001"
        
        # 配置mock抛出异常
        mock_persistence_service.load_gene_capsule.side_effect = Exception("加载错误")
        
        # 调用API
        response = gateway.get_gene_capsule(strategy_id)
        
        # 验证响应
        assert response.status == ResponseStatus.ERROR
        assert response.message == "查询Z2H基因胶囊失败"
        assert response.error["type"] == "Exception"
    
    def test_revoke_certification_error(self, gateway, mock_persistence_service):
        """测试撤销认证异常"""
        request = RevokeCertificationRequest(
            strategy_id="strategy_001",
            reason="测试"
        )
        
        # 配置mock抛出异常
        mock_persistence_service.load_strategy_metadata.side_effect = Exception("数据库错误")
        
        # 调用API
        response = gateway.revoke_certification(request)
        
        # 验证响应
        assert response.status == ResponseStatus.ERROR
        assert response.message == "撤销认证失败"
        assert response.error["type"] == "Exception"
    
    def test_downgrade_certification_error(self, gateway, mock_persistence_service):
        """测试降级认证异常"""
        request = DowngradeCertificationRequest(
            strategy_id="strategy_001",
            new_level="SILVER",
            reason="测试"
        )
        
        # 配置mock抛出异常
        mock_persistence_service.load_strategy_metadata.side_effect = Exception("数据库错误")
        
        # 调用API
        response = gateway.downgrade_certification(request)
        
        # 验证响应
        assert response.status == ResponseStatus.ERROR
        assert response.message == "降级认证失败"
        assert response.error["type"] == "Exception"
    
    def test_get_certification_report_error(self, gateway, mock_traceability_manager):
        """测试导出认证报告异常"""
        strategy_id = "strategy_001"
        
        # 配置mock抛出异常
        mock_traceability_manager.query_by_strategy_id.side_effect = Exception("查询错误")
        
        # 调用API
        response = gateway.get_certification_report(strategy_id)
        
        # 验证响应
        assert response.status == ResponseStatus.ERROR
        assert response.message == "导出认证报告失败"
        assert response.error["type"] == "Exception"
    
    def test_get_certification_records_with_level_filter(self, gateway, mock_traceability_manager):
        """测试按等级过滤认证记录"""
        # 创建不同等级的trace
        traces = [
            CertificationTrace(
                trace_id="trace_001",
                strategy_id="strategy_001",
                strategy_name="策略1",
                start_time=datetime.now(),
                final_status="completed",
                certification_level=CertificationLevel.GOLD
            ),
            CertificationTrace(
                trace_id="trace_002",
                strategy_id="strategy_002",
                strategy_name="策略2",
                start_time=datetime.now(),
                final_status="completed",
                certification_level=CertificationLevel.SILVER
            ),
            CertificationTrace(
                trace_id="trace_003",
                strategy_id="strategy_003",
                strategy_name="策略3",
                start_time=datetime.now(),
                final_status="completed",
                certification_level=CertificationLevel.GOLD
            )
        ]
        
        # 配置mock
        mock_traceability_manager.query_by_status.return_value = traces
        
        # 调用API - 过滤GOLD等级
        response = gateway.get_certification_records(
            status="completed",
            level="gold",
            limit=10,
            offset=0
        )
        
        # 验证响应 - 应该只返回2个GOLD等级的记录
        assert response.status == ResponseStatus.SUCCESS
        assert response.data["total"] == 2
        assert len(response.data["records"]) == 2
        for record in response.data["records"]:
            assert record["certification_level"] == "gold"
    
    def test_downgrade_certification_not_found(self, gateway, mock_persistence_service):
        """测试降级不存在的策略"""
        request = DowngradeCertificationRequest(
            strategy_id="nonexistent",
            new_level="SILVER",
            reason="测试"
        )
        
        # 配置mock
        mock_persistence_service.load_strategy_metadata.return_value = None
        
        # 调用API
        response = gateway.downgrade_certification(request)
        
        # 验证响应
        assert response.status == ResponseStatus.ERROR
        assert response.message == "策略不存在"
        assert response.error["type"] == "NotFoundError"
    
    def test_get_certification_report_with_failure_analysis(self, gateway, mock_traceability_manager, mock_failure_analyzer):
        """测试导出失败策略的认证报告（包含失败分析）"""
        strategy_id = "strategy_001"
        
        # 创建失败的trace
        trace = CertificationTrace(
            trace_id="trace_001",
            strategy_id=strategy_id,
            strategy_name="测试策略",
            start_time=datetime.now(),
            final_status="failed",
            failed_stage="arena",
            failure_reason="Arena测试未通过"
        )
        
        # 创建模拟失败报告
        from src.evolution.certification_failure_analyzer import FailureAnalysisReport
        failure_report = Mock()
        failure_report.to_dict.return_value = {
            "strategy_id": strategy_id,
            "failed_stage": "arena",
            "failure_category": "arena_reality_track_failed"
        }
        
        # 配置mock
        mock_traceability_manager.query_by_strategy_id.return_value = [trace]
        mock_traceability_manager.generate_audit_report.return_value = {
            "trace_id": "trace_001",
            "strategy_id": strategy_id,
            "report": "详细报告"
        }
        mock_failure_analyzer.generate_failure_analysis_report.return_value = failure_report
        
        # 调用API
        response = gateway.get_certification_report(strategy_id)
        
        # 验证响应
        assert response.status == ResponseStatus.SUCCESS
        assert response.message == "报告生成成功"
        assert "failure_analysis" in response.data
        assert response.data["failure_analysis"]["failed_stage"] == "arena"
        
        # 验证失败分析器被调用
        assert mock_failure_analyzer.generate_failure_analysis_report.called
    
    def test_api_response_to_dict_with_error(self):
        """测试APIResponse.to_dict包含error字段"""
        response = APIResponse(
            status=ResponseStatus.ERROR,
            message="错误",
            error={"type": "TestError", "message": "测试错误"}
        )
        
        result = response.to_dict()
        
        assert "error" in result
        assert result["error"]["type"] == "TestError"
        assert "data" not in result
    
    def test_get_certification_records_without_status_filter(self, gateway, mock_traceability_manager):
        """测试查询认证记录不指定状态过滤"""
        # 不指定status参数时，应该返回空列表（因为没有查询所有记录的方法）
        
        # 调用API - 不指定status
        response = gateway.get_certification_records(limit=10, offset=0)
        
        # 验证响应 - 应该返回空列表
        assert response.status == ResponseStatus.SUCCESS
        assert response.data["total"] == 0
        assert len(response.data["records"]) == 0
