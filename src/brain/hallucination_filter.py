"""
MIA系统防幻觉过滤器 (Hallucination Filter)

白皮书依据: 第十一章 11.1 防幻觉系统
版本: v1.6.0
作者: MIA Team
日期: 2026-01-18

核心理念: 通过5层检测机制识别并过滤AI模型的幻觉响应，确保输出的可靠性和准确性。

检测层次:
1. Layer 1: 内部矛盾检测 (25%权重)
2. Layer 2: 事实一致性检查 (30%权重)
3. Layer 3: 置信度校准 (20%权重)
4. Layer 4: 语义漂移检测 (15%权重)
5. Layer 5: 黑名单匹配 (10%权重)
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class HallucinationDetectionResult:
    """幻觉检测结果"""

    is_hallucination: bool
    confidence: float
    scores: Dict[str, float]
    explanation: str
    detected_issues: List[str]
    severity: str  # 'low', 'medium', 'high', 'critical'


class HallucinationFilter:
    """防幻觉过滤器

    白皮书依据: 第十一章 11.1 防幻觉系统

    通过多层检测机制识别AI响应中的幻觉内容：
    - 内部矛盾检测：识别同一响应中的逻辑矛盾
    - 事实一致性检查：验证数值声明和事实陈述
    - 置信度校准：检查置信度表述与实际准确率的匹配
    - 语义漂移检测：识别偏离主题的内容
    - 黑名单匹配：匹配已知的幻觉模式

    使用示例:
        >>> filter = HallucinationFilter()
        >>> result = filter.detect_hallucination(
        ...     ai_response="我建议买入，同时也建议卖出这只股票",
        ...     context={"call_type": "trading_decision"}
        ... )
        >>> if result.is_hallucination:
        ...     print(f"检测到幻觉: {result.explanation}")
    """

    def __init__(self):
        """初始化防幻觉过滤器"""
        # 检测权重配置
        self.weights = {
            "contradiction": 0.25,  # 内部矛盾
            "factual_consistency": 0.30,  # 事实一致性
            "confidence_calibration": 0.20,  # 置信度校准
            "semantic_drift": 0.15,  # 语义漂移
            "blacklist_match": 0.10,  # 黑名单匹配
        }

        # 幻觉阈值
        self.threshold = 0.5  # 超过此阈值认为是幻觉

        # 严重程度阈值
        self.severity_thresholds = {"low": 0.3, "medium": 0.5, "high": 0.7, "critical": 0.9}

        # 加载已知幻觉模式
        self.known_hallucinations = self._load_blacklist()

        # 矛盾词对
        self.contradiction_pairs = [
            ("买入", "卖出"),
            ("buy", "sell"),
            ("看涨", "看跌"),
            ("bullish", "bearish"),
            ("上涨", "下跌"),
            ("increase", "decrease"),
            ("推荐", "不推荐"),
            ("recommend", "not recommend"),
            ("支持", "反对"),
            ("support", "oppose"),
            ("同意", "不同意"),
            ("agree", "disagree"),
            ("确定", "不确定"),
            ("certain", "uncertain"),
            ("有效", "无效"),
            ("effective", "ineffective"),
            ("盈利", "亏损"),
            ("profit", "loss"),
            ("风险低", "风险高"),
            ("low risk", "high risk"),
        ]

        # 置信度表述映射
        self.confidence_phrases = {
            "绝对确定": 0.95,
            "absolutely certain": 0.95,
            "非常确定": 0.90,
            "very certain": 0.90,
            "确定": 0.85,
            "certain": 0.85,
            "很有信心": 0.80,
            "very confident": 0.80,
            "有信心": 0.75,
            "confident": 0.75,
            "可能": 0.60,
            "likely": 0.60,
            "也许": 0.50,
            "maybe": 0.50,
            "不太确定": 0.40,
            "not sure": 0.40,
            "不确定": 0.30,
            "uncertain": 0.30,
            "很不确定": 0.20,
            "very uncertain": 0.20,
        }

        logger.info("防幻觉过滤器初始化完成")

    def detect_hallucination(
        self, ai_response: str, context: Optional[Dict[str, Any]] = None
    ) -> HallucinationDetectionResult:
        """检测AI响应是否为幻觉

        Args:
            ai_response: AI生成的响应文本
            context: 上下文信息，包含历史准确率、业务上下文等

        Returns:
            幻觉检测结果
        """
        if not ai_response or not ai_response.strip():
            return HallucinationDetectionResult(
                is_hallucination=True,
                confidence=1.0,
                scores={"empty_response": 1.0},
                explanation="响应为空",
                detected_issues=["空响应"],
                severity="critical",
            )

        context = context or {}

        # 执行5层检测
        scores = {}
        detected_issues = []

        # Layer 1: 内部矛盾检测
        contradiction_score, contradiction_issues = self._check_contradiction(ai_response)
        scores["contradiction"] = contradiction_score
        detected_issues.extend(contradiction_issues)

        # Layer 2: 事实一致性检查
        factual_score, factual_issues = self._check_factual_consistency(ai_response, context)
        scores["factual_consistency"] = factual_score
        detected_issues.extend(factual_issues)

        # Layer 3: 置信度校准
        confidence_score, confidence_issues = self._check_confidence_calibration(ai_response, context)
        scores["confidence_calibration"] = confidence_score
        detected_issues.extend(confidence_issues)

        # Layer 4: 语义漂移检测
        drift_score, drift_issues = self._check_semantic_drift(ai_response, context)
        scores["semantic_drift"] = drift_score
        detected_issues.extend(drift_issues)

        # Layer 5: 黑名单匹配
        blacklist_score, blacklist_issues = self._check_blacklist(ai_response)
        scores["blacklist_match"] = blacklist_score
        detected_issues.extend(blacklist_issues)

        # 计算加权总分
        total_score = sum(scores[key] * self.weights[key] for key in scores)  # pylint: disable=c0206

        # 判断是否为幻觉
        is_hallucination = total_score > self.threshold

        # 确定严重程度
        severity = self._determine_severity(total_score)

        # 生成解释
        explanation = self._generate_explanation(scores, detected_issues, is_hallucination)

        result = HallucinationDetectionResult(
            is_hallucination=is_hallucination,
            confidence=total_score,
            scores=scores,
            explanation=explanation,
            detected_issues=detected_issues,
            severity=severity,
        )

        if is_hallucination:
            logger.warning(  # pylint: disable=logging-fstring-interpolation
                f"检测到幻觉: 置信度={total_score:.3f}, 严重程度={severity}"
            )  # pylint: disable=logging-fstring-interpolation

        return result

    def _check_contradiction(self, response: str) -> Tuple[float, List[str]]:
        """Layer 1: 检查内部矛盾

        Args:
            response: AI响应文本

        Returns:
            (矛盾评分, 检测到的问题列表)
        """
        issues = []
        contradiction_count = 0

        response_lower = response.lower()

        # 检测矛盾词对
        for word1, word2 in self.contradiction_pairs:
            if word1.lower() in response_lower and word2.lower() in response_lower:
                # 检查是否在同一句子或相近位置
                sentences = re.split(r"[.!?。！？]", response)

                for sentence in sentences:
                    sentence_lower = sentence.lower()
                    if word1.lower() in sentence_lower and word2.lower() in sentence_lower:
                        contradiction_count += 1
                        issues.append(f"同一句中出现矛盾词对: '{word1}' 和 '{word2}'")
                        break

                # 检查相邻句子中的矛盾
                for i in range(len(sentences) - 1):
                    curr_sentence = sentences[i].lower()
                    next_sentence = sentences[i + 1].lower()

                    if (word1.lower() in curr_sentence and word2.lower() in next_sentence) or (
                        word2.lower() in curr_sentence and word1.lower() in next_sentence
                    ):
                        contradiction_count += 1
                        issues.append(f"相邻句子中出现矛盾: '{word1}' 和 '{word2}'")

        # 检测数值矛盾
        numbers = re.findall(r"\d+\.?\d*%?", response)
        if len(numbers) >= 2:
            # 简化检测：如果同时出现很大和很小的数值可能有问题
            try:
                numeric_values = []
                for num in numbers:
                    clean_num = num.replace("%", "")
                    if "." in clean_num:
                        numeric_values.append(float(clean_num))
                    else:
                        numeric_values.append(int(clean_num))

                if numeric_values:
                    max_val = max(numeric_values)
                    min_val = min(numeric_values)

                    # 如果最大值和最小值差异过大，可能存在矛盾
                    if max_val > 0 and min_val >= 0 and max_val / min_val > 1000:
                        contradiction_count += 1
                        issues.append(f"数值差异过大: {max_val} vs {min_val}")

            except (ValueError, ZeroDivisionError):
                pass

        # 归一化评分 (0-1)
        score = min(contradiction_count / 3.0, 1.0)

        return score, issues

    def _check_factual_consistency(self, response: str, context: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Layer 2: 检查事实一致性

        Args:
            response: AI响应文本
            context: 上下文信息

        Returns:
            (一致性评分, 检测到的问题列表)
        """
        issues = []
        inconsistencies = 0

        # 提取响应中的数值声明
        claimed_values = self._extract_numeric_claims(response)

        if not claimed_values:
            return 0.0, issues

        # 与上下文中的实际数据对比
        for claim in claimed_values:
            if not self._verify_claim(claim, context):
                inconsistencies += 1
                issues.append(f"数值声明可能不准确: {claim}")

        # 检查常识性错误
        common_sense_issues = self._check_common_sense(response)
        issues.extend(common_sense_issues)
        inconsistencies += len(common_sense_issues)

        # 归一化评分
        total_claims = len(claimed_values) + len(common_sense_issues)
        if total_claims == 0:
            return 0.0, issues

        score = inconsistencies / total_claims

        return score, issues

    def _check_confidence_calibration(self, response: str, context: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Layer 3: 检查置信度校准

        Args:
            response: AI响应文本
            context: 上下文信息

        Returns:
            (校准评分, 检测到的问题列表)
        """
        issues = []

        # 提取置信度表述
        stated_confidence = self._extract_confidence(response)

        if stated_confidence is None:
            return 0.0, issues  # 没有置信度表述，不扣分

        # 获取历史准确率
        historical_accuracy = context.get("historical_accuracy", 0.7)

        # 计算校准误差
        calibration_error = abs(stated_confidence - historical_accuracy)

        # 如果校准误差过大，认为存在问题
        if calibration_error > 0.3:
            issues.append(f"置信度校准偏差过大: 声称{stated_confidence:.2f}, 历史准确率{historical_accuracy:.2f}")

        # 检查过度自信
        if stated_confidence > 0.9 and historical_accuracy < 0.7:
            issues.append("可能存在过度自信")
            calibration_error += 0.2

        # 检查过度谦虚
        if stated_confidence < 0.5 and historical_accuracy > 0.8:
            issues.append("可能过度谦虚")
            calibration_error += 0.1

        # 归一化评分
        score = min(calibration_error, 1.0)

        return score, issues

    def _check_semantic_drift(self, response: str, context: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Layer 4: 检查语义漂移

        Args:
            response: AI响应文本
            context: 上下文信息

        Returns:
            (漂移评分, 检测到的问题列表)
        """
        issues = []

        # 获取预期的主题关键词
        call_type = context.get("call_type", "")
        expected_keywords = self._get_expected_keywords(call_type)

        if not expected_keywords:
            return 0.0, issues

        # 计算关键词重叠度
        response_lower = response.lower()
        keyword_matches = sum(1 for keyword in expected_keywords if keyword in response_lower)

        if len(expected_keywords) > 0:
            overlap_ratio = keyword_matches / len(expected_keywords)
        else:
            overlap_ratio = 0.0

        # 如果重叠度过低，可能存在语义漂移
        if overlap_ratio < 0.3:
            issues.append(f"响应与预期主题相关性较低: {overlap_ratio:.2f}")

        # 检查是否包含无关内容
        irrelevant_patterns = [
            r"顺便说一下",
            r"by the way",
            r"另外",
            r"additionally",
            r"题外话",
            r"off topic",
            r"我想起",
            r"reminds me",
        ]

        for pattern in irrelevant_patterns:
            if re.search(pattern, response_lower):
                issues.append(f"可能包含无关内容: {pattern}")

        # 计算漂移评分
        drift_score = 1.0 - overlap_ratio
        if issues:
            drift_score += 0.2  # 发现无关内容时增加评分

        score = min(drift_score, 1.0)

        return score, issues

    def _check_blacklist(self, response: str) -> Tuple[float, List[str]]:
        """Layer 5: 检查黑名单匹配

        Args:
            response: AI响应文本

        Returns:
            (匹配评分, 检测到的问题列表)
        """
        issues = []
        matches = 0

        response_lower = response.lower()

        # 检查已知幻觉模式
        for pattern in self.known_hallucinations:
            if pattern.lower() in response_lower:
                matches += 1
                issues.append(f"匹配已知幻觉模式: {pattern}")

        # 检查可疑表述
        suspicious_patterns = [
            r"我确信.*但是.*不确定",
            r"绝对.*可能",
            r"一定.*也许",
            r"必须.*或许",
            r"definitely.*maybe",
            r"certainly.*possibly",
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, response_lower):
                matches += 1
                issues.append(f"检测到可疑表述模式: {pattern}")

        # 归一化评分
        score = min(matches / 5.0, 1.0)

        return score, issues

    def _extract_numeric_claims(self, response: str) -> List[str]:
        """提取响应中的数值声明"""
        claims = []

        # 匹配数值声明模式
        patterns = [
            r"(\d+\.?\d*%?\s*的?\s*(收益|回报|利润|亏损|涨幅|跌幅))",
            r"(价格.*\d+\.?\d*)",
            r"(市值.*\d+\.?\d*)",
            r"(\d+\.?\d*.*倍)",
            r"(\d+\.?\d*.*年)",
            r"(\d+\.?\d*.*月)",
            r"(\d+\.?\d*.*天)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            claims.extend([match[0] if isinstance(match, tuple) else match for match in matches])

        return claims

    def _verify_claim(self, claim: str, context: Dict[str, Any]) -> bool:  # pylint: disable=unused-argument
        """验证数值声明的准确性"""
        # 简化实现：检查是否有明显不合理的数值

        # 提取数值
        numbers = re.findall(r"\d+\.?\d*", claim)

        for num_str in numbers:
            try:
                num = float(num_str)

                # 检查是否为不合理的大数值
                if num > 10000 and ("收益" in claim or "回报" in claim or "%" in claim):
                    return False  # 收益率超过10000%不合理

                # 检查是否为负的价格
                if num < 0 and ("价格" in claim or "市值" in claim):
                    return False  # 负价格不合理

            except ValueError:
                continue

        return True  # 默认认为合理

    def _check_common_sense(self, response: str) -> List[str]:
        """检查常识性错误"""
        issues = []

        # 检查时间相关的常识错误
        if re.search(r"(昨天|yesterday).*未来", response, re.IGNORECASE):
            issues.append("时间逻辑错误：昨天不能预测未来")

        # 检查数学常识错误
        if re.search(r"100%.*以上", response):
            issues.append("数学错误：百分比不能超过100%")

        # 检查市场常识错误
        if re.search(r"股价.*负数", response):
            issues.append("市场常识错误：股价不能为负数")

        return issues

    def _extract_confidence(self, response: str) -> Optional[float]:
        """提取置信度表述"""
        response_lower = response.lower()

        for phrase, confidence in self.confidence_phrases.items():
            if phrase in response_lower:
                return confidence

        # 检查百分比表述
        confidence_match = re.search(r"(\d+)%.*确信|确信.*(\d+)%", response_lower)
        if confidence_match:
            percentage = int(confidence_match.group(1) or confidence_match.group(2))
            return percentage / 100.0

        return None

    def _get_expected_keywords(self, call_type: str) -> List[str]:
        """获取预期的主题关键词"""
        keyword_map = {
            "trading_decision": [
                "买入",
                "卖出",
                "持有",
                "价格",
                "股票",
                "交易",
                "buy",
                "sell",
                "hold",
                "price",
                "stock",
            ],
            "strategy_analysis": ["策略", "回测", "收益", "风险", "夏普", "strategy", "backtest", "return", "risk"],
            "research_analysis": ["研究", "分析", "报告", "数据", "结论", "research", "analysis", "report", "data"],
            "factor_generation": ["因子", "特征", "相关性", "预测", "factor", "feature", "correlation", "prediction"],
            "risk_assessment": ["风险", "波动", "回撤", "控制", "risk", "volatility", "drawdown", "control"],
            "market_sentiment": ["情绪", "市场", "投资者", "恐慌", "sentiment", "market", "investor", "fear"],
        }

        return keyword_map.get(call_type, [])

    def _determine_severity(self, score: float) -> str:
        """确定严重程度"""
        if score >= self.severity_thresholds["critical"]:  # pylint: disable=no-else-return
            return "critical"
        elif score >= self.severity_thresholds["high"]:
            return "high"
        elif score >= self.severity_thresholds["medium"]:
            return "medium"
        else:
            return "low"

    def _generate_explanation(self, scores: Dict[str, float], issues: List[str], is_hallucination: bool) -> str:
        """生成检测结果解释"""
        if not is_hallucination:
            return "响应质量良好，未检测到明显幻觉"

        explanation_parts = ["检测到潜在幻觉，原因："]

        # 按权重排序问题
        sorted_scores = sorted(scores.items(), key=lambda x: x[1] * self.weights[x[0]], reverse=True)

        for layer, score in sorted_scores[:3]:  # 只显示前3个主要问题
            if score > 0.3:  # 只显示显著问题
                layer_name = {
                    "contradiction": "内部矛盾",
                    "factual_consistency": "事实一致性",
                    "confidence_calibration": "置信度校准",
                    "semantic_drift": "语义漂移",
                    "blacklist_match": "黑名单匹配",
                }.get(layer, layer)

                explanation_parts.append(f"- {layer_name}: {score:.2f}")

        if issues:
            explanation_parts.append("具体问题：")
            for issue in issues[:5]:  # 最多显示5个具体问题
                explanation_parts.append(f"• {issue}")

        return "\n".join(explanation_parts)

    def _load_blacklist(self) -> List[str]:
        """加载已知幻觉模式黑名单"""
        # 这里应该从文件或数据库加载，现在使用硬编码
        return [
            "我是GPT-4",
            "我是ChatGPT",
            "我是Claude",
            "我不能提供投资建议",
            "我无法预测股价",
            "根据我的训练数据",
            "截至我的知识更新",
            "我没有实时数据",
            "这不是投资建议",
            "请咨询专业人士",
            "我建议买入同时卖出",
            "100%确定会上涨",
            "绝对不会亏损",
            "保证盈利",
            "无风险投资",
        ]

    def add_to_blacklist(self, pattern: str) -> None:
        """添加新的幻觉模式到黑名单"""
        if pattern not in self.known_hallucinations:
            self.known_hallucinations.append(pattern)
            logger.info(f"添加新的幻觉模式到黑名单: {pattern}")  # pylint: disable=logging-fstring-interpolation

    def update_weights(self, new_weights: Dict[str, float]) -> None:
        """更新检测权重"""
        # 验证权重总和为1
        total_weight = sum(new_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"权重总和必须为1.0，当前为: {total_weight}")

        self.weights.update(new_weights)
        logger.info(f"更新检测权重: {new_weights}")  # pylint: disable=logging-fstring-interpolation

    def get_statistics(self) -> Dict[str, Any]:
        """获取检测统计信息"""
        return {
            "weights": self.weights,
            "threshold": self.threshold,
            "severity_thresholds": self.severity_thresholds,
            "blacklist_size": len(self.known_hallucinations),
            "contradiction_pairs": len(self.contradiction_pairs),
            "confidence_phrases": len(self.confidence_phrases),
        }
