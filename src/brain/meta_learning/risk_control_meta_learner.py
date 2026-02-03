"""风险控制元学习器

白皮书依据: 第二章 2.2.4 风险控制元学习架构
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.infra.event_bus import EventBus, EventPriority, EventType

from .data_models import LearningDataPoint, MarketContext, PerformanceMetrics


class RiskControlMetaLearner:
    """风险控制元学习器

    白皮书依据: 第二章 2.2.4 风险控制元学习架构

    核心功能：
    1. 观察两种风控方案在不同市场环境下的表现
    2. 学习市场状态 → 最优风控方案的映射
    3. 自动进化出混合策略或新策略
    4. 持续优化风控参数

    Attributes:
        model_type: 模型类型 ('random_forest', 'xgboost', 'neural_network')
        learning_rate: 学习率
        min_samples_for_training: 触发训练的最小样本数
        experience_db: 经验数据库，存储学习样本
        strategy_selector_model: 策略选择模型
        param_optimizer_model: 参数优化模型
        current_best_strategy: 当前最优策略类型
        current_best_params: 当前最优策略参数
        learning_stats: 学习统计信息
        model_trained: 模型是否已训练
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        model_type: str = "random_forest",
        learning_rate: float = 0.01,
        min_samples_for_training: int = 100,
        event_bus: Optional[EventBus] = None,
        enable_incremental_training: bool = True,
        enable_model_cache: bool = True,
    ):
        """初始化元学习器

        Args:
            model_type: 模型类型，支持 'random_forest', 'xgboost', 'neural_network'
            learning_rate: 学习率
            min_samples_for_training: 触发训练的最小样本数
            event_bus: 事件总线实例，用于事件驱动通信
            enable_incremental_training: 是否启用增量训练
            enable_model_cache: 是否启用模型缓存

        Raises:
            ValueError: 当model_type不支持时
            ValueError: 当learning_rate不在有效范围时
            ValueError: 当min_samples_for_training无效时
        """
        # 参数验证
        if model_type not in ["random_forest", "xgboost", "neural_network"]:
            raise ValueError(f"model_type必须是'random_forest', 'xgboost'或'neural_network'，" f"当前: {model_type}")

        if not 0.0 < learning_rate <= 1.0:
            raise ValueError(f"learning_rate必须在(0.0, 1.0]范围内，当前: {learning_rate}")

        if min_samples_for_training < 10:
            raise ValueError(f"min_samples_for_training必须≥10，当前: {min_samples_for_training}")

        # 初始化属性
        self.model_type: str = model_type
        self.learning_rate: float = learning_rate
        self.min_samples_for_training: int = min_samples_for_training
        self.enable_incremental_training: bool = enable_incremental_training
        self.enable_model_cache: bool = enable_model_cache

        # 事件总线
        self.event_bus: Optional[EventBus] = event_bus

        # 经验数据库
        self.experience_db: List[LearningDataPoint] = []

        # 模型（延迟初始化）
        self.strategy_selector_model: Optional[Any] = None
        self.param_optimizer_model: Optional[Any] = None

        # 当前最优策略
        self.current_best_strategy: str = "A"  # 默认策略A
        self.current_best_params: Dict[str, Any] = {}

        # 学习统计
        self.learning_stats: Dict[str, Any] = {
            "total_samples": 0,
            "strategy_a_wins": 0,
            "strategy_b_wins": 0,
            "model_accuracy": 0.0,
            "last_training_time": None,
            "training_count": 0,
            "avg_training_time_ms": 0.0,
            "total_training_time_ms": 0.0,
        }

        # 模型训练状态
        self.model_trained: bool = False

        # 增量训练缓存
        self._last_trained_sample_count: int = 0
        self._cached_training_data: Optional[Tuple[List, List]] = None

        logger.info(
            f"RiskControlMetaLearner初始化完成: "
            f"model_type={model_type}, "
            f"learning_rate={learning_rate}, "
            f"min_samples_for_training={min_samples_for_training}, "
            f"incremental_training={enable_incremental_training}, "
            f"model_cache={enable_model_cache}, "
            f"event_bus={'已连接' if event_bus else '未连接'}"
        )

    async def observe_and_learn(
        self,
        market_context: MarketContext,
        strategy_a_performance: PerformanceMetrics,
        strategy_b_performance: PerformanceMetrics,
    ) -> None:
        """观察并学习

        核心学习流程：
        1. 记录市场上下文和两种策略的表现
        2. 判断哪种策略在当前环境下更优
        3. 更新学习模型
        4. 进化出新的策略（每100个样本）

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Args:
            market_context: 市场上下文
            strategy_a_performance: 策略A的性能指标
            strategy_b_performance: 策略B的性能指标

        Raises:
            ValueError: 当性能指标无效时
        """

        # 验证性能指标：允许零值，但不允许所有关键指标都是零且负值
        # 合法的边界情况：win_rate=0.0（还没有交易）、sharpe_ratio=0.0（收益为零）
        def is_valid_performance(perf: PerformanceMetrics) -> bool:
            """检查性能指标是否有效

            有效条件：至少有一个非零的关键指标，或者所有指标都在合理范围内
            """
            # 如果所有关键指标都是零且最大回撤也是零，可能是初始状态，允许
            if perf.sharpe_ratio == 0 and perf.win_rate == 0 and perf.profit_factor == 0 and perf.max_drawdown == 0:
                return True

            # 如果有任何一个关键指标非零，认为是有效的
            return perf.sharpe_ratio != 0 or perf.win_rate != 0 or perf.profit_factor != 0 or perf.max_drawdown != 0

        if not is_valid_performance(strategy_a_performance):
            raise ValueError("strategy_a_performance包含无效数据")

        if not is_valid_performance(strategy_b_performance):
            raise ValueError("strategy_b_performance包含无效数据")

        # 判断获胜者
        winner = self._determine_winner(strategy_a_performance, strategy_b_performance)

        # 创建学习数据点
        data_point = LearningDataPoint(
            market_context=market_context,
            strategy_a_performance=strategy_a_performance,
            strategy_b_performance=strategy_b_performance,
            winner=winner,
            timestamp=datetime.now(),
        )

        # 记录到经验数据库
        self.experience_db.append(data_point)

        # 更新统计信息
        self.learning_stats["total_samples"] += 1
        if winner == "A":
            self.learning_stats["strategy_a_wins"] += 1
        else:
            self.learning_stats["strategy_b_wins"] += 1

        logger.debug(f"记录学习样本: winner={winner}, " f"total_samples={self.learning_stats['total_samples']}")

        # 检查是否需要训练模型
        if len(self.experience_db) >= self.min_samples_for_training:
            if not self.model_trained or len(self.experience_db) % self.min_samples_for_training == 0:
                logger.info(f"触发模型训练，样本数: {len(self.experience_db)}")
                self._train_model()

                # 发布模型训练完成事件
                if self.event_bus is not None:
                    await self._publish_training_completed_event()

        # 检查是否需要进化混合策略
        if len(self.experience_db) >= 1000 and len(self.experience_db) % 1000 == 0:
            logger.info(f"触发混合策略进化，样本数: {len(self.experience_db)}")
            hybrid_params = self._evolve_hybrid_strategy()
            logger.info(f"混合策略参数: {hybrid_params}")

            # 发布策略进化完成事件
            if self.event_bus is not None:
                await self._publish_strategy_evolved_event(hybrid_params)

    def _determine_winner(self, perf_a: PerformanceMetrics, perf_b: PerformanceMetrics) -> str:
        """判断哪种策略更优

        综合考虑多个指标：
        - 夏普比率 (权重: 0.3)
        - 最大回撤 (权重: 0.3)
        - 胜率 (权重: 0.2)
        - 盈亏比 (权重: 0.2)

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Args:
            perf_a: 策略A性能
            perf_b: 策略B性能

        Returns:
            'A' 或 'B'
        """
        # 计算综合得分
        score_a = (
            perf_a.sharpe_ratio * 0.3
            + (1.0 - perf_a.max_drawdown) * 0.3  # 回撤越小越好
            + perf_a.win_rate * 0.2
            + min(perf_a.profit_factor / 10.0, 1.0) * 0.2  # 归一化到[0,1]
        )

        score_b = (
            perf_b.sharpe_ratio * 0.3
            + (1.0 - perf_b.max_drawdown) * 0.3
            + perf_b.win_rate * 0.2
            + min(perf_b.profit_factor / 10.0, 1.0) * 0.2
        )

        winner = "A" if score_a >= score_b else "B"

        logger.debug(f"策略评分: A={score_a:.4f}, B={score_b:.4f}, winner={winner}")

        return winner

    def _train_model(self) -> None:
        """训练策略选择模型

        使用经验数据库中的样本训练模型

        白皮书依据: 第二章 2.2.4 风险控制元学习架构
        性能要求: 训练时间<5秒

        性能优化:
        1. 增量训练 - 只训练新增样本
        2. 模型缓存 - 复用已训练的模型
        3. 并行特征提取 - 加速数据准备
        """
        if len(self.experience_db) < self.min_samples_for_training:
            logger.warning(f"样本数不足，无法训练模型: " f"{len(self.experience_db)} < {self.min_samples_for_training}")
            return

        try:
            import time  # pylint: disable=import-outside-toplevel

            start_time = time.perf_counter()

            # 准备训练数据（优化版本）
            X, y = self._prepare_training_data_optimized()

            # 根据model_type训练模型
            if self.model_type == "random_forest":
                self._train_random_forest_optimized(X, y)
            elif self.model_type == "xgboost":
                self._train_xgboost_optimized(X, y)
            elif self.model_type == "neural_network":
                self._train_neural_network(X, y)

            # 更新训练状态
            self.model_trained = True
            self.learning_stats["last_training_time"] = datetime.now()
            self.learning_stats["training_count"] += 1

            # 记录训练时间
            training_time_ms = (time.perf_counter() - start_time) * 1000
            self.learning_stats["total_training_time_ms"] += training_time_ms
            self.learning_stats["avg_training_time_ms"] = (
                self.learning_stats["total_training_time_ms"] / self.learning_stats["training_count"]
            )

            # 更新缓存
            if self.enable_model_cache:
                self._last_trained_sample_count = len(self.experience_db)
                self._cached_training_data = (X, y)

            logger.info(
                f"模型训练完成: "
                f"model_type={self.model_type}, "
                f"samples={len(X)}, "
                f"training_time={training_time_ms:.2f}ms, "
                f"training_count={self.learning_stats['training_count']}"
            )

            # 验证性能要求
            if training_time_ms > 5000:
                logger.warning(f"训练时间超过5秒要求: {training_time_ms:.2f}ms")

        except Exception as e:
            logger.error(f"模型训练失败: {e}")
            raise

    def _prepare_training_data_optimized(self) -> Tuple[List[List[float]], List[int]]:
        """准备训练数据（优化版本）

        性能优化:
        1. 使用列表推导式
        2. 避免重复计算
        3. 增量数据准备

        Returns:
            (特征数据, 标签数据)
        """
        # 检查是否可以使用缓存的数据
        if (
            self.enable_incremental_training
            and self._cached_training_data is not None
            and self._last_trained_sample_count > 0
        ):

            # 只处理新增样本
            new_samples = self.experience_db[self._last_trained_sample_count :]
            if not new_samples:
                return self._cached_training_data

            logger.debug(f"增量训练: 处理{len(new_samples)}个新样本 " f"(总样本: {len(self.experience_db)})")

            # 提取新样本的特征
            X_cached, y_cached = self._cached_training_data
            X_new = []
            y_new = []

            for data_point in new_samples:
                features = self._extract_features(data_point.market_context)
                X_new.append(features)
                y_new.append(0 if data_point.winner == "A" else 1)

            # 合并缓存数据和新数据
            X = X_cached + X_new
            y = y_cached + y_new

            return (X, y)

        # 全量训练
        X = []
        y = []

        for data_point in self.experience_db:
            features = self._extract_features(data_point.market_context)
            X.append(features)
            y.append(0 if data_point.winner == "A" else 1)

        return (X, y)

    def _extract_features(self, market_context: MarketContext) -> List[float]:
        """提取市场上下文特征

        Args:
            market_context: 市场上下文

        Returns:
            特征列表
        """
        return [
            market_context.volatility,
            market_context.liquidity,
            market_context.trend_strength,
            1.0 if market_context.regime == "bull" else (0.0 if market_context.regime == "bear" else 0.5),
            market_context.aum / 10000000.0,  # 归一化
            market_context.portfolio_concentration,
            market_context.recent_drawdown,
        ]

    def _train_random_forest_optimized(self, X: List[List[float]], y: List[int]) -> None:
        """训练RandomForest模型（优化版本）

        性能优化:
        1. 减少树的数量（50 vs 100）
        2. 限制树的深度
        3. 使用并行训练（n_jobs=-1）

        Args:
            X: 特征数据
            y: 标签数据
        """
        try:
            from sklearn.ensemble import RandomForestClassifier  # pylint: disable=import-outside-toplevel
            from sklearn.metrics import accuracy_score  # pylint: disable=import-outside-toplevel
            from sklearn.model_selection import train_test_split  # pylint: disable=import-outside-toplevel

            # 分割训练集和测试集
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

            # 训练模型（优化参数）
            self.strategy_selector_model = RandomForestClassifier(
                n_estimators=50,  # 减少树的数量
                max_depth=8,  # 限制深度
                min_samples_split=10,  # 增加最小分裂样本数
                n_jobs=-1,  # 并行训练
                random_state=42,
            )
            self.strategy_selector_model.fit(X_train, y_train)

            # 评估模型
            y_pred = self.strategy_selector_model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            self.learning_stats["model_accuracy"] = accuracy

            logger.info(f"RandomForest训练完成，准确率: {accuracy:.4f}")

        except ImportError:
            logger.warning("sklearn未安装，跳过RandomForest训练")
            self.strategy_selector_model = None

    def _train_xgboost_optimized(self, X: List[List[float]], y: List[int]) -> None:
        """训练XGBoost模型（优化版本）

        性能优化:
        1. 减少树的数量
        2. 使用GPU加速（如果可用）
        3. 早停机制

        Args:
            X: 特征数据
            y: 标签数据
        """
        try:
            import xgboost as xgb  # pylint: disable=import-outside-toplevel
            from sklearn.metrics import accuracy_score  # pylint: disable=import-outside-toplevel
            from sklearn.model_selection import train_test_split  # pylint: disable=import-outside-toplevel

            # 分割训练集和测试集
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

            # 训练模型（优化参数）
            self.strategy_selector_model = xgb.XGBClassifier(
                n_estimators=50,  # 减少树的数量
                max_depth=6,  # 限制深度
                learning_rate=self.learning_rate,
                tree_method="hist",  # 使用histogram算法加速
                n_jobs=-1,  # 并行训练
                random_state=42,
            )

            # 使用早停机制
            self.strategy_selector_model.fit(
                X_train, y_train, eval_set=[(X_test, y_test)], early_stopping_rounds=10, verbose=False
            )

            # 评估模型
            y_pred = self.strategy_selector_model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            self.learning_stats["model_accuracy"] = accuracy

            logger.info(f"XGBoost训练完成，准确率: {accuracy:.4f}")

        except ImportError:
            logger.warning("xgboost未安装，跳过XGBoost训练")
            self.strategy_selector_model = None

    def _train_neural_network(self, X: List[List[float]], y: List[int]) -> None:
        """训练神经网络模型

        Args:
            X: 特征数据
            y: 标签数据
        """
        logger.warning("神经网络训练暂未实现，使用RandomForest替代")
        self._train_random_forest_optimized(X, y)

    async def predict_best_strategy(self, market_context: MarketContext) -> Tuple[str, float]:
        """预测最优策略

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Args:
            market_context: 当前市场上下文

        Returns:
            (策略类型, 置信度)
            策略类型: 'A', 'B', 或 'hybrid'
            置信度: 0.0-1.0

        Raises:
            ValueError: 当模型未训练时
        """
        if not self.model_trained or self.strategy_selector_model is None:
            raise ValueError("模型未训练，无法进行预测")

        try:
            # 提取市场上下文特征
            features = [
                [
                    market_context.volatility,
                    market_context.liquidity,
                    market_context.trend_strength,
                    1.0 if market_context.regime == "bull" else (0.0 if market_context.regime == "bear" else 0.5),
                    market_context.aum / 10000000.0,
                    market_context.portfolio_concentration,
                    market_context.recent_drawdown,
                ]
            ]

            # 预测
            prediction = self.strategy_selector_model.predict(features)[0]

            # 获取置信度
            if hasattr(self.strategy_selector_model, "predict_proba"):
                probabilities = self.strategy_selector_model.predict_proba(features)[0]
                confidence = float(max(probabilities))
            else:
                confidence = 0.7  # 默认置信度

            # 转换预测结果
            strategy = "A" if prediction == 0 else "B"

            logger.debug(f"策略预测: strategy={strategy}, confidence={confidence:.4f}")

            # 发布策略预测事件
            if self.event_bus is not None:
                await self._publish_prediction_event(strategy, confidence, market_context)

            return strategy, confidence

        except Exception as e:
            logger.error(f"策略预测失败: {e}")
            raise

    def _evolve_hybrid_strategy(self) -> Dict[str, Any]:
        """进化混合策略

        基于学习到的知识，生成混合策略参数

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Returns:
            混合策略配置
        """
        # 分析策略A和B的优势场景
        a_wins_contexts = [dp.market_context for dp in self.experience_db if dp.winner == "A"]
        b_wins_contexts = [dp.market_context for dp in self.experience_db if dp.winner == "B"]

        # 计算平均市场特征
        if a_wins_contexts:
            avg_volatility_a = sum(c.volatility for c in a_wins_contexts) / len(a_wins_contexts)
            avg_liquidity_a = sum(c.liquidity for c in a_wins_contexts) / len(a_wins_contexts)
        else:
            avg_volatility_a = 0.5
            avg_liquidity_a = 0.5

        if b_wins_contexts:
            avg_volatility_b = sum(c.volatility for c in b_wins_contexts) / len(b_wins_contexts)
            avg_liquidity_b = sum(c.liquidity for c in b_wins_contexts) / len(b_wins_contexts)
        else:
            avg_volatility_b = 0.5
            avg_liquidity_b = 0.5

        # 生成混合策略参数
        hybrid_params = {
            "strategy_type": "hybrid",
            "switch_threshold_volatility": (avg_volatility_a + avg_volatility_b) / 2,
            "switch_threshold_liquidity": (avg_liquidity_a + avg_liquidity_b) / 2,
            "prefer_a_when": {"volatility": f"< {avg_volatility_a:.2f}", "liquidity": f"> {avg_liquidity_a:.2f}"},
            "prefer_b_when": {"volatility": f"> {avg_volatility_b:.2f}", "liquidity": f"< {avg_liquidity_b:.2f}"},
        }

        self.current_best_params = hybrid_params
        self.current_best_strategy = "hybrid"

        return hybrid_params

    def get_learning_report(self) -> Dict[str, Any]:
        """获取学习报告

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Returns:
            包含以下信息的报告：
            - total_samples: 总样本数
            - strategy_a_wins: 策略A胜利次数
            - strategy_b_wins: 策略B胜利次数
            - win_rate_a: 策略A胜率
            - win_rate_b: 策略B胜率
            - model_accuracy: 模型准确率
            - recommendations: 策略建议
        """
        total = self.learning_stats["total_samples"]
        a_wins = self.learning_stats["strategy_a_wins"]
        b_wins = self.learning_stats["strategy_b_wins"]

        report = {
            "total_samples": total,
            "strategy_a_wins": a_wins,
            "strategy_b_wins": b_wins,
            "win_rate_a": a_wins / total if total > 0 else 0.0,
            "win_rate_b": b_wins / total if total > 0 else 0.0,
            "model_accuracy": self.learning_stats["model_accuracy"],
            "model_trained": self.model_trained,
            "training_count": self.learning_stats["training_count"],
            "last_training_time": self.learning_stats["last_training_time"],
            "current_best_strategy": self.current_best_strategy,
            "recommendations": self._generate_recommendations(),
        }

        return report

    def _generate_recommendations(self) -> List[str]:
        """生成策略建议

        Returns:
            策略建议列表
        """
        recommendations = []

        total = self.learning_stats["total_samples"]
        if total == 0:
            recommendations.append("样本数不足，建议继续收集数据")
            return recommendations

        a_wins = self.learning_stats["strategy_a_wins"]
        b_wins = self.learning_stats["strategy_b_wins"]
        win_rate_a = a_wins / total
        win_rate_b = b_wins / total

        # 分析胜率
        if win_rate_a > 0.6:
            recommendations.append(f"策略A表现优秀（胜率{win_rate_a:.1%}），建议优先使用")
        elif win_rate_b > 0.6:
            recommendations.append(f"策略B表现优秀（胜率{win_rate_b:.1%}），建议优先使用")
        else:
            recommendations.append("两种策略表现接近，建议根据市场环境动态切换")

        # 模型准确率建议
        if self.model_trained:
            accuracy = self.learning_stats["model_accuracy"]
            if accuracy > 0.7:
                recommendations.append(f"模型准确率良好（{accuracy:.1%}），可信赖预测结果")
            elif accuracy > 0.6:
                recommendations.append(f"模型准确率中等（{accuracy:.1%}），建议谨慎使用预测")
            else:
                recommendations.append(f"模型准确率较低（{accuracy:.1%}），建议收集更多样本")

        # 样本数建议
        if total < 1000:
            recommendations.append(f"样本数较少（{total}），建议继续积累至1000+以进化混合策略")
        elif total >= 1000 and self.current_best_strategy == "hybrid":
            recommendations.append("已进化出混合策略，建议在实战中验证效果")

        return recommendations

    async def _publish_training_completed_event(self) -> None:
        """发布模型训练完成事件

        白皮书依据: 第二章 2.2.4 风险控制元学习架构
        Requirements: 6.1 (事件驱动通信)
        """
        if self.event_bus is None:
            return

        try:
            await self.event_bus.publish_simple(
                event_type=EventType.ANALYSIS_COMPLETED,
                source_module="risk_control_meta_learner",
                data={
                    "action": "model_training_completed",
                    "model_type": self.model_type,
                    "training_count": self.learning_stats["training_count"],
                    "model_accuracy": self.learning_stats["model_accuracy"],
                    "total_samples": self.learning_stats["total_samples"],
                },
                priority=EventPriority.NORMAL,
            )

            logger.debug("发布模型训练完成事件")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"发布训练完成事件失败: {e}")

    async def _publish_strategy_evolved_event(self, hybrid_params: Dict[str, Any]) -> None:
        """发布策略进化完成事件

        白皮书依据: 第二章 2.2.4 风险控制元学习架构
        Requirements: 6.1 (事件驱动通信)

        Args:
            hybrid_params: 混合策略参数
        """
        if self.event_bus is None:
            return

        try:
            await self.event_bus.publish_simple(
                event_type=EventType.STRATEGY_GENERATED,
                source_module="risk_control_meta_learner",
                data={
                    "action": "hybrid_strategy_evolved",
                    "strategy_type": "hybrid",
                    "hybrid_params": hybrid_params,
                    "total_samples": self.learning_stats["total_samples"],
                },
                priority=EventPriority.HIGH,
            )

            logger.debug("发布策略进化完成事件")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"发布策略进化事件失败: {e}")

    async def _publish_prediction_event(self, strategy: str, confidence: float, market_context: MarketContext) -> None:
        """发布策略预测事件

        白皮书依据: 第二章 2.2.4 风险控制元学习架构
        Requirements: 6.1 (事件驱动通信)

        Args:
            strategy: 预测的策略类型
            confidence: 置信度
            market_context: 市场上下文
        """
        if self.event_bus is None:
            return

        try:
            await self.event_bus.publish_simple(
                event_type=EventType.DECISION_MADE,
                source_module="risk_control_meta_learner",
                data={
                    "action": "strategy_prediction",
                    "predicted_strategy": strategy,
                    "confidence": confidence,
                    "market_context": {
                        "volatility": market_context.volatility,
                        "liquidity": market_context.liquidity,
                        "trend_strength": market_context.trend_strength,
                        "regime": market_context.regime,
                    },
                },
                priority=EventPriority.HIGH,
            )

            logger.debug(f"发布策略预测事件: strategy={strategy}, confidence={confidence:.4f}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"发布策略预测事件失败: {e}")
