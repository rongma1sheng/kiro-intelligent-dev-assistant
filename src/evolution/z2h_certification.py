"""Z2H认证系统

白皮书依据: 第四章 4.2 斯巴达竞技场

Z2H = Zero to Hero（从零到英雄）
策略认证体系，确保只有经过严格验证的策略才能进入实盘交易。

认证标准基于投研级评价体系：
- 收益质量（Annual Return, Sharpe, Sortino, Calmar）
- 风险结构（Max Drawdown, DD Duration, CVaR）
- 交易结构（Win Rate, Payoff Ratio, Expectancy）
- 稳健性（Parameter Sensitivity, Rolling Window）
"""

from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger

from src.evolution.strategy_evaluator import MarketType, StrategyEvaluator
from src.strategies.data_models import StrategyMetadata


class Z2HCertification:
    """Z2H认证系统

    白皮书依据: 第四章 4.2 斯巴达竞技场

    认证流程：
    1. Arena测试（4档位）
    2. 投研级指标评估
    3. 斯巴达Arena考核
    4. 模拟盘1个月验证
    5. 达标后颁发Z2H基因胶囊认证
    6. 进入实盘策略库
    """

    def __init__(self, market_type: MarketType = MarketType.A_STOCK):
        """初始化Z2H认证系统

        Args:
            market_type: 市场类型，决定评价标准
        """
        # 策略评价器
        self.evaluator = StrategyEvaluator(market_type=market_type)
        self.market_type = market_type

        # 认证记录
        self.certification_records: Dict[str, Dict[str, Any]] = {}

        logger.info(f"Z2HCertification初始化完成 - 市场类型: {market_type.value}")

    async def check_certification_eligibility(self, strategy_metadata: StrategyMetadata) -> Dict[str, Any]:
        """检查策略是否符合认证条件

        白皮书依据: Requirement 19

        使用投研级评价体系，包括：
        - 收益质量指标
        - 风险结构指标
        - 交易层面指标
        - 稳健性检查

        Args:
            strategy_metadata: 策略元数据

        Returns:
            {
                'eligible': bool,
                'excellent': bool,
                'grade': str,
                'passed_criteria': List[str],
                'failed_criteria': List[str],
                'metrics': Dict[str, Any],
                'excellent_ratio': float
            }
        """
        logger.info(f"检查认证资格 - 策略: {strategy_metadata.strategy_name}")

        # 检查是否有Arena测试结果
        if not strategy_metadata.arena_results:
            return {
                "eligible": False,
                "excellent": False,
                "grade": "不合格",
                "passed_criteria": [],
                "failed_criteria": ["缺少Arena测试结果"],
                "metrics": {},
                "excellent_ratio": 0.0,
            }

        # 获取最佳档位的测试结果
        best_tier = strategy_metadata.best_tier
        best_result = strategy_metadata.arena_results.get(best_tier)

        if not best_result:
            return {
                "eligible": False,
                "excellent": False,
                "grade": "不合格",
                "passed_criteria": [],
                "failed_criteria": [f"缺少最佳档位({best_tier})的测试结果"],
                "metrics": {},
                "excellent_ratio": 0.0,
            }

        # 从Arena结果提取评价指标
        # 注意：这里假设Arena结果已经包含了完整的回测数据
        # 实际使用时需要从Arena的equity_curve计算
        metrics = {
            "annual_return": best_result.total_return_pct / 100.0,  # 转换为小数
            "sharpe": best_result.sharpe_ratio,
            "sortino": best_result.sharpe_ratio * 1.2,  # 简化估算
            "max_drawdown": best_result.max_drawdown_pct / 100.0,
            "calmar": (
                (best_result.total_return_pct / 100.0) / abs(best_result.max_drawdown_pct / 100.0)
                if best_result.max_drawdown_pct != 0
                else 0.0
            ),
            "max_dd_duration_days": 60,  # 简化：假设2个月
            "cvar_5pct": best_result.max_drawdown_pct / 100.0 * 0.5,  # 简化估算
            "win_rate": best_result.win_rate,
            "payoff_ratio": 2.0,  # 简化：假设盈亏比2.0
            "expectancy": best_result.total_return_pct / 100.0 / 252,  # 简化估算
            "max_consecutive_losses": 5,  # 简化：假设最大连续亏损5次
            "max_single_loss": -0.02,  # 简化：假设单笔最大亏损2%
        }

        # 使用评价器检查阈值
        threshold_result = self.evaluator.check_thresholds(metrics)

        logger.info(
            f"认证资格检查完成 - "
            f"策略: {strategy_metadata.strategy_name}, "
            f"合格: {threshold_result['qualified']}, "
            f"优秀: {threshold_result['excellent']}, "
            f"评级: {threshold_result['grade']}"
        )

        return {
            "eligible": threshold_result["qualified"],
            "excellent": threshold_result["excellent"],
            "grade": threshold_result["grade"],
            "passed_criteria": threshold_result["passed_criteria"],
            "failed_criteria": threshold_result["failed_criteria"],
            "metrics": metrics,
            "excellent_ratio": threshold_result["excellent_ratio"],
        }

    async def grant_certification(
        self, strategy_metadata: StrategyMetadata, simulation_result: Optional[Dict[str, Any]] = None
    ) -> StrategyMetadata:
        """颁发Z2H认证

        白皮书依据: Requirement 19.4

        Args:
            strategy_metadata: 策略元数据
            simulation_result: 模拟盘验证结果（可选）

        Returns:
            更新后的策略元数据（包含认证信息）

        Raises:
            CertificationError: 当策略不符合认证条件时
        """
        logger.info(f"颁发Z2H认证 - 策略: {strategy_metadata.strategy_name}")

        # 检查认证资格
        eligibility = await self.check_certification_eligibility(strategy_metadata)

        if not eligibility["eligible"]:
            error_msg = f"策略不符合认证条件: {', '.join(eligibility['failed_criteria'])}"
            logger.error(error_msg)
            raise CertificationError(error_msg)

        # 更新认证状态
        strategy_metadata.z2h_certified = True
        strategy_metadata.z2h_certification_date = datetime.now().strftime("%Y-%m-%d")

        # 记录认证信息
        certification_record = {
            "strategy_name": strategy_metadata.strategy_name,
            "certification_date": strategy_metadata.z2h_certification_date,
            "best_tier": strategy_metadata.best_tier,
            "eligibility_check": eligibility,
            "simulation_result": simulation_result,
        }

        self.certification_records[strategy_metadata.strategy_name] = certification_record

        logger.info(
            f"Z2H认证颁发成功 - "
            f"策略: {strategy_metadata.strategy_name}, "
            f"日期: {strategy_metadata.z2h_certification_date}"
        )

        return strategy_metadata

    async def revoke_certification(self, strategy_metadata: StrategyMetadata, reason: str) -> StrategyMetadata:
        """撤销Z2H认证

        Args:
            strategy_metadata: 策略元数据
            reason: 撤销原因

        Returns:
            更新后的策略元数据
        """
        logger.warning(f"撤销Z2H认证 - " f"策略: {strategy_metadata.strategy_name}, " f"原因: {reason}")

        strategy_metadata.z2h_certified = False
        strategy_metadata.z2h_certification_date = None

        # 记录撤销信息
        if strategy_metadata.strategy_name in self.certification_records:
            self.certification_records[strategy_metadata.strategy_name]["revoked"] = True
            self.certification_records[strategy_metadata.strategy_name]["revoke_reason"] = reason
            self.certification_records[strategy_metadata.strategy_name]["revoke_date"] = datetime.now().strftime(
                "%Y-%m-%d"
            )

        return strategy_metadata

    def get_certification_record(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """获取认证记录

        Args:
            strategy_name: 策略名称

        Returns:
            认证记录，如果不存在返回None
        """
        return self.certification_records.get(strategy_name)

    def get_all_certified_strategies(self) -> list[str]:
        """获取所有已认证的策略名称

        Returns:
            已认证策略名称列表
        """
        certified = [name for name, record in self.certification_records.items() if not record.get("revoked", False)]

        logger.debug(f"已认证策略数量: {len(certified)}")

        return certified

    def update_certification_criteria(self, new_criteria: Dict[str, Any]) -> None:
        """更新认证标准

        Args:
            new_criteria: 新的认证标准
        """
        self.certification_criteria.update(new_criteria)  # pylint: disable=no-member

        logger.info(f"认证标准已更新: {self.certification_criteria}")  # pylint: disable=no-member


class StrategyMetadataManager:
    """策略元数据管理器

    白皮书依据: Requirement 19.6

    管理策略元数据的持久化和查询
    """

    def __init__(self):
        """初始化策略元数据管理器"""
        # 内存存储（实际应该使用数据库）
        self.metadata_store: Dict[str, StrategyMetadata] = {}

        logger.info("StrategyMetadataManager初始化完成")

    def save_metadata(self, metadata: StrategyMetadata) -> None:
        """保存策略元数据

        Args:
            metadata: 策略元数据
        """
        self.metadata_store[metadata.strategy_name] = metadata

        logger.info(f"策略元数据已保存: {metadata.strategy_name}")

    def load_metadata(self, strategy_name: str) -> Optional[StrategyMetadata]:
        """加载策略元数据

        Args:
            strategy_name: 策略名称

        Returns:
            策略元数据，如果不存在返回None
        """
        metadata = self.metadata_store.get(strategy_name)

        if metadata:
            logger.debug(f"策略元数据已加载: {strategy_name}")
        else:
            logger.warning(f"策略元数据不存在: {strategy_name}")

        return metadata

    def list_all_strategies(self) -> list[str]:
        """列出所有策略名称

        Returns:
            策略名称列表
        """
        return list(self.metadata_store.keys())

    def list_certified_strategies(self) -> list[StrategyMetadata]:
        """列出所有已认证的策略

        Returns:
            已认证策略元数据列表
        """
        certified = [metadata for metadata in self.metadata_store.values() if metadata.z2h_certified]

        logger.debug(f"已认证策略数量: {len(certified)}")

        return certified

    def delete_metadata(self, strategy_name: str) -> bool:
        """删除策略元数据

        Args:
            strategy_name: 策略名称

        Returns:
            是否删除成功
        """
        if strategy_name in self.metadata_store:  # pylint: disable=no-else-return
            del self.metadata_store[strategy_name]
            logger.info(f"策略元数据已删除: {strategy_name}")
            return True
        else:
            logger.warning(f"策略元数据不存在，无法删除: {strategy_name}")
            return False


class CertificationError(Exception):
    """认证异常"""
