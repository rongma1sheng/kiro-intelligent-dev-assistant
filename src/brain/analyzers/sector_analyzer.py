"""行业与板块分析器

白皮书依据: 第五章 5.2.7 行业与板块分析
引擎: Commander (战略级分析)
"""

from typing import Any, Dict, List

from loguru import logger

from .data_models import SectorAnalysisReport


class SectorAnalyzer:
    """行业与板块分析器

    白皮书依据: 第五章 5.2.7 行业与板块分析

    分析内容:
    - 行业基本面: 各行业基本面情况
    - 政策支持: 政策对行业的支持程度
    - 资金流向: 行业资金流入流出
    - 相对强度: 行业相对大盘的强弱
    - 轮动预测: 预测下一阶段强势行业
    """

    # 行业分类
    SECTOR_CATEGORIES = {
        "cyclical": ["钢铁", "煤炭", "有色", "化工", "建材", "机械"],
        "defensive": ["食品饮料", "医药", "公用事业", "银行"],
        "growth": ["电子", "计算机", "通信", "传媒", "新能源"],
        "financial": ["银行", "证券", "保险", "多元金融"],
        "consumer": ["食品饮料", "家电", "汽车", "商贸零售", "纺织服装"],
    }

    def __init__(self):
        """初始化行业分析器"""
        logger.info("SectorAnalyzer初始化完成")

    async def analyze(self, sector_data: Dict[str, Any]) -> SectorAnalysisReport:
        """分析行业与板块

        Args:
            sector_data: 板块数据，包含fundamentals, returns, flows等

        Returns:
            SectorAnalysisReport: 行业分析报告
        """
        logger.info("开始行业板块分析")

        try:
            fundamentals = sector_data.get("fundamentals", {})
            returns = sector_data.get("returns", {})
            flows = sector_data.get("flows", {})
            policies = sector_data.get("policies", {})
            index_return = sector_data.get("index_return", 0)

            # 1. 分析行业基本面
            sector_fundamentals = self._analyze_fundamentals(fundamentals)

            # 2. 评估政策支持
            policy_support = self._evaluate_policy_support(policies)

            # 3. 分析资金流向
            capital_flow = self._analyze_capital_flow(flows)

            # 4. 计算相对强度
            relative_strength = self._calculate_relative_strength(returns, index_return)

            # 5. 预测板块轮动
            rotation_prediction = self._predict_rotation(relative_strength, capital_flow, policy_support)

            # 6. 构建行业矩阵
            sector_matrix = self._build_sector_matrix(sector_fundamentals, relative_strength, capital_flow)

            # 7. 识别强弱板块
            top_sectors, weak_sectors = self._identify_top_weak_sectors(relative_strength, capital_flow)

            report = SectorAnalysisReport(
                sector_fundamentals=sector_fundamentals,
                policy_support=policy_support,
                capital_flow=capital_flow,
                relative_strength=relative_strength,
                rotation_prediction=rotation_prediction,
                sector_matrix=sector_matrix,
                top_sectors=top_sectors,
                weak_sectors=weak_sectors,
            )

            logger.info(f"行业分析完成: 强势板块={top_sectors[:3]}, 弱势板块={weak_sectors[:3]}")
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"行业分析失败: {e}")
            return SectorAnalysisReport(
                sector_fundamentals={},
                policy_support={},
                capital_flow={},
                relative_strength={},
                rotation_prediction=[],
                sector_matrix={},
                top_sectors=[],
                weak_sectors=[],
            )

    def _analyze_fundamentals(  # pylint: disable=too-many-branches
        self, fundamentals: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:  # pylint: disable=too-many-branches
        """分析行业基本面

        Args:
            fundamentals: 行业基本面数据

        Returns:
            Dict[str, Dict[str, Any]]: 基本面分析结果
        """
        if not fundamentals:
            return {}

        analysis = {}

        for sector, data in fundamentals.items():
            pe = data.get("pe", 0)
            pb = data.get("pb", 0)
            roe = data.get("roe", 0)
            revenue_growth = data.get("revenue_growth", 0)
            profit_growth = data.get("profit_growth", 0)

            # 估值评级
            if pe > 0:
                if pe < 15:
                    valuation = "low"
                elif pe < 30:
                    valuation = "medium"
                else:
                    valuation = "high"
            else:
                valuation = "negative"

            # 成长性评级
            if profit_growth > 30:
                growth = "high"
            elif profit_growth > 10:
                growth = "medium"
            elif profit_growth > 0:
                growth = "low"
            else:
                growth = "negative"

            # 盈利能力评级
            if roe > 15:
                profitability = "excellent"
            elif roe > 10:
                profitability = "good"
            elif roe > 5:
                profitability = "fair"
            else:
                profitability = "poor"

            # 综合评分
            score = 0
            if valuation == "low":
                score += 2
            elif valuation == "medium":
                score += 1

            if growth == "high":
                score += 2
            elif growth == "medium":
                score += 1

            if profitability in ["excellent", "good"]:
                score += 2
            elif profitability == "fair":
                score += 1

            analysis[sector] = {
                "pe": pe,
                "pb": pb,
                "roe": roe,
                "revenue_growth": revenue_growth,
                "profit_growth": profit_growth,
                "valuation": valuation,
                "growth": growth,
                "profitability": profitability,
                "fundamental_score": score,
            }

        return analysis

    def _evaluate_policy_support(self, policies: Dict[str, Any]) -> Dict[str, float]:
        """评估政策支持

        Args:
            policies: 政策数据

        Returns:
            Dict[str, float]: 行业 -> 政策支持评分
        """
        if not policies:
            # 默认政策支持评分
            return {
                "新能源": 0.9,
                "半导体": 0.85,
                "人工智能": 0.85,
                "医药": 0.7,
                "消费": 0.6,
                "金融": 0.5,
                "房地产": 0.3,
            }

        support_scores = {}

        for sector, policy_data in policies.items():
            positive_count = policy_data.get("positive_policies", 0)
            negative_count = policy_data.get("negative_policies", 0)
            support_level = policy_data.get("support_level", "neutral")

            # 基础分
            if support_level == "strong":
                base_score = 0.8
            elif support_level == "moderate":
                base_score = 0.6
            elif support_level == "neutral":
                base_score = 0.5
            else:
                base_score = 0.3

            # 根据政策数量调整
            policy_adjustment = (positive_count - negative_count) * 0.05

            support_scores[sector] = min(1.0, max(0.0, base_score + policy_adjustment))

        return support_scores

    def _analyze_capital_flow(self, flows: Dict[str, Any]) -> Dict[str, float]:
        """分析资金流向

        Args:
            flows: 资金流向数据

        Returns:
            Dict[str, float]: 行业 -> 资金流向（正为流入，负为流出）
        """
        if not flows:
            return {}

        capital_flow = {}

        for sector, flow_data in flows.items():
            if isinstance(flow_data, (int, float)):
                capital_flow[sector] = flow_data
            elif isinstance(flow_data, dict):
                inflow = flow_data.get("inflow", 0)
                outflow = flow_data.get("outflow", 0)
                capital_flow[sector] = inflow - outflow
            elif isinstance(flow_data, list):
                capital_flow[sector] = sum(flow_data)

        return capital_flow

    def _calculate_relative_strength(self, returns: Dict[str, float], index_return: float) -> Dict[str, float]:
        """计算相对强度

        Args:
            returns: 行业收益率
            index_return: 指数收益率

        Returns:
            Dict[str, float]: 行业 -> 相对强度
        """
        if not returns:
            return {}

        relative_strength = {}

        for sector, sector_return in returns.items():
            # 相对强度 = 行业收益 - 指数收益
            rs = sector_return - index_return
            relative_strength[sector] = round(rs, 4)

        return relative_strength

    def _predict_rotation(
        self, relative_strength: Dict[str, float], capital_flow: Dict[str, float], policy_support: Dict[str, float]
    ) -> List[str]:
        """预测板块轮动

        Args:
            relative_strength: 相对强度
            capital_flow: 资金流向
            policy_support: 政策支持

        Returns:
            List[str]: 轮动预测
        """
        predictions = []

        # 找出资金流入但相对强度较弱的板块（可能即将启动）
        potential_sectors = []
        for sector in set(relative_strength.keys()) & set(capital_flow.keys()):
            rs = relative_strength.get(sector, 0)
            flow = capital_flow.get(sector, 0)
            policy = policy_support.get(sector, 0.5)

            # 资金流入 + 相对弱势 + 政策支持 = 潜在机会
            if flow > 0 and rs < 0 and policy > 0.5:  # pylint: disable=r1716
                score = flow * policy * (1 - rs)
                potential_sectors.append((sector, score))

        if potential_sectors:
            potential_sectors.sort(key=lambda x: x[1], reverse=True)
            for sector, _ in potential_sectors[:3]:
                predictions.append(f"关注{sector}：资金流入但涨幅落后，可能即将启动")

        # 找出强势但资金流出的板块（可能见顶）
        warning_sectors = []
        for sector in set(relative_strength.keys()) & set(capital_flow.keys()):
            rs = relative_strength.get(sector, 0)
            flow = capital_flow.get(sector, 0)

            if rs > 0.05 and flow < 0:
                warning_sectors.append(sector)

        if warning_sectors:
            predictions.append(f"警惕{', '.join(warning_sectors[:3])}：涨幅较大但资金流出")

        # 周期性轮动建议
        predictions.append("建议关注周期股与成长股的轮动节奏")

        return predictions

    def _build_sector_matrix(
        self,
        fundamentals: Dict[str, Dict[str, Any]],
        relative_strength: Dict[str, float],
        capital_flow: Dict[str, float],
    ) -> Dict[str, Dict[str, Any]]:
        """构建行业矩阵

        Args:
            fundamentals: 基本面分析
            relative_strength: 相对强度
            capital_flow: 资金流向

        Returns:
            Dict[str, Dict[str, Any]]: 行业矩阵
        """
        matrix = {}

        all_sectors = set(fundamentals.keys()) | set(relative_strength.keys()) | set(capital_flow.keys())

        for sector in all_sectors:
            fund = fundamentals.get(sector, {})
            rs = relative_strength.get(sector, 0)
            flow = capital_flow.get(sector, 0)

            # 确定象限
            # 高强度+资金流入 = 强势
            # 高强度+资金流出 = 见顶
            # 低强度+资金流入 = 启动
            # 低强度+资金流出 = 弱势

            if rs > 0 and flow > 0:
                quadrant = "strong"
                recommendation = "持有"
            elif rs > 0 and flow <= 0:  # pylint: disable=r1716
                quadrant = "topping"
                recommendation = "减仓"
            elif rs <= 0 and flow > 0:  # pylint: disable=r1716
                quadrant = "starting"
                recommendation = "关注"
            else:
                quadrant = "weak"
                recommendation = "回避"

            matrix[sector] = {
                "relative_strength": rs,
                "capital_flow": flow,
                "fundamental_score": fund.get("fundamental_score", 0),
                "quadrant": quadrant,
                "recommendation": recommendation,
            }

        return matrix

    def _identify_top_weak_sectors(self, relative_strength: Dict[str, float], capital_flow: Dict[str, float]) -> tuple:
        """识别强弱板块

        Args:
            relative_strength: 相对强度
            capital_flow: 资金流向

        Returns:
            tuple: (强势板块列表, 弱势板块列表)
        """
        if not relative_strength:
            return [], []

        # 综合评分 = 相对强度 * 0.6 + 资金流向标准化 * 0.4
        scores = {}

        # 标准化资金流向
        if capital_flow:
            flow_values = list(capital_flow.values())
            flow_max = max(abs(v) for v in flow_values) if flow_values else 1
        else:
            flow_max = 1

        for sector, rs in relative_strength.items():
            flow = capital_flow.get(sector, 0)
            flow_normalized = flow / flow_max if flow_max > 0 else 0

            score = rs * 0.6 + flow_normalized * 0.4
            scores[sector] = score

        # 排序
        sorted_sectors = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        top_sectors = [s[0] for s in sorted_sectors[:5]]
        weak_sectors = [s[0] for s in sorted_sectors[-5:]]

        return top_sectors, weak_sectors
