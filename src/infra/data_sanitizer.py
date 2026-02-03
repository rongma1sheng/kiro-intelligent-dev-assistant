"""
深度清洗矩阵实现

白皮书依据: 第三章 3.3 深度清洗矩阵
实现8层数据清洗框架，支持股票、期货、期权等多种资产类型
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger


class AssetType(Enum):
    """资产类型枚举

    白皮书依据: 第三章 3.3 资产类型自适应
    """

    STOCK = "stock"  # 股票
    INDEX = "index"  # 指数
    FUTURE = "future"  # 期货
    OPTION = "option"  # 期权
    BOND = "bond"  # 债券
    FUND = "fund"  # 基金


@dataclass
class PriceRange:
    """价格范围配置

    Attributes:
        min_price: 最小价格
        max_price: 最大价格
        description: 描述
    """

    min_price: float
    max_price: float
    description: str


@dataclass
class CleaningResult:
    """清洗结果

    Attributes:
        original_count: 原始数据行数
        cleaned_count: 清洗后数据行数
        removed_count: 移除的数据行数
        quality_score: 质量评分 (0-1)
        layer_results: 各层清洗结果
        warnings: 警告信息
        errors: 错误信息
    """

    original_count: int
    cleaned_count: int
    removed_count: int
    quality_score: float
    layer_results: Dict[str, Dict[str, Any]]
    warnings: List[str]
    errors: List[str]


class DataSanitizer:
    """数据清洗器

    白皮书依据: 第三章 3.3 深度清洗矩阵

    实现8层数据清洗框架：
    1. NaN清洗
    2. 价格合理性检查
    3. HLOC一致性检查
    4. 成交量检查
    5. 重复值检查
    6. 异常值检测
    7. 数据缺口检测
    8. 公司行动处理

    Attributes:
        asset_type: 资产类型
        price_ranges: 价格范围配置
        cleaning_config: 清洗配置
    """

    # 价格范围配置
    PRICE_RANGES = {
        AssetType.STOCK: PriceRange(0.01, 10000, "A股股票范围"),
        AssetType.INDEX: PriceRange(1, 100000, "沪深300等指数"),
        AssetType.FUTURE: PriceRange(0.01, 50000, "商品期货点位"),
        AssetType.OPTION: PriceRange(0, 10000, "期权费用"),
        AssetType.BOND: PriceRange(50, 200, "债券价格"),
        AssetType.FUND: PriceRange(0.1, 100, "基金净值"),
    }

    def __init__(self, asset_type: AssetType, config: Optional[Dict[str, Any]] = None):
        """初始化数据清洗器

        Args:
            asset_type: 资产类型
            config: 清洗配置
        """
        self.asset_type = asset_type
        self.price_range = self.PRICE_RANGES.get(asset_type, self.PRICE_RANGES[AssetType.STOCK])
        self.config = config or self._get_default_config()

        logger.info(f"DataSanitizer initialized for {asset_type.value}")

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置

        Returns:
            默认配置字典
        """
        return {
            "nan_threshold": 0.05,  # NaN比例阈值
            "price_change_threshold": 0.5,  # 价格变动阈值
            "volume_threshold": 0,  # 成交量阈值
            "duplicate_threshold": 0.01,  # 重复值阈值
            "outlier_std_threshold": 3.0,  # 异常值标准差阈值
            "gap_threshold": 0.1,  # 数据缺口阈值
            "enable_corporate_actions": True,  # 是否处理公司行动
        }

    def clean_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, CleaningResult]:
        """执行完整的数据清洗流程

        白皮书依据: 第三章 3.3 八层清洗框架

        Args:
            df: 原始数据

        Returns:
            (清洗后数据, 清洗结果)
        """
        logger.info(f"Starting data cleaning for {len(df)} rows")

        # 初始化结果
        original_count = len(df)
        layer_results = {}
        warnings_list = []
        errors_list = []

        # 复制数据
        cleaned_df = df.copy()

        try:
            # Layer 1: NaN清洗
            cleaned_df, layer1_result = self._layer1_nan_cleaning(cleaned_df)
            layer_results["layer1_nan"] = layer1_result

            # Layer 2: 价格合理性检查
            cleaned_df, layer2_result = self._layer2_price_validation(cleaned_df)
            layer_results["layer2_price"] = layer2_result

            # Layer 3: HLOC一致性检查
            cleaned_df, layer3_result = self._layer3_hloc_consistency(cleaned_df)
            layer_results["layer3_hloc"] = layer3_result

            # Layer 4: 成交量检查
            cleaned_df, layer4_result = self._layer4_volume_check(cleaned_df)
            layer_results["layer4_volume"] = layer4_result

            # Layer 5: 重复值检查
            cleaned_df, layer5_result = self._layer5_duplicate_check(cleaned_df)
            layer_results["layer5_duplicate"] = layer5_result

            # Layer 6: 异常值检测
            cleaned_df, layer6_result = self._layer6_outlier_detection(cleaned_df)
            layer_results["layer6_outlier"] = layer6_result

            # Layer 7: 数据缺口检测
            cleaned_df, layer7_result = self._layer7_gap_detection(cleaned_df)
            layer_results["layer7_gap"] = layer7_result

            # Layer 8: 公司行动处理
            if self.config["enable_corporate_actions"]:
                cleaned_df, layer8_result = self._layer8_corporate_actions(cleaned_df)
                layer_results["layer8_corporate"] = layer8_result

            # 计算质量评分
            quality_score = self._calculate_quality_score(original_count, len(cleaned_df), layer_results)

            # 生成清洗结果
            result = CleaningResult(
                original_count=original_count,
                cleaned_count=len(cleaned_df),
                removed_count=original_count - len(cleaned_df),
                quality_score=quality_score,
                layer_results=layer_results,
                warnings=warnings_list,
                errors=errors_list,
            )

            logger.info(
                f"Data cleaning completed: {original_count} -> {len(cleaned_df)} "
                f"({result.removed_count} removed, quality: {quality_score:.3f})"
            )

            return cleaned_df, result

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Data cleaning failed: {e}")
            errors_list.append(str(e))

            # 返回原始数据和错误结果
            result = CleaningResult(
                original_count=original_count,
                cleaned_count=original_count,
                removed_count=0,
                quality_score=0.0,
                layer_results=layer_results,
                warnings=warnings_list,
                errors=errors_list,
            )

            return df, result

    def _layer1_nan_cleaning(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Layer 1: NaN清洗

        白皮书依据: 第三章 3.3 Layer 1

        Args:
            df: 输入数据

        Returns:
            (清洗后数据, 清洗结果)
        """
        original_count = len(df)

        # 计算NaN比例
        nan_count = df.isnull().sum().sum()
        total_cells = len(df) * len(df.columns)
        nan_ratio = nan_count / total_cells if total_cells > 0 else 0

        # 删除有NaN的行
        cleaned_df = df.dropna()

        result = {
            "original_count": original_count,
            "cleaned_count": len(cleaned_df),
            "removed_count": original_count - len(cleaned_df),
            "nan_ratio": nan_ratio,
            "threshold_exceeded": nan_ratio > self.config["nan_threshold"],
        }

        if result["threshold_exceeded"]:
            logger.warning(f"High NaN ratio: {nan_ratio:.2%} > {self.config['nan_threshold']:.2%}")

        logger.debug(f"Layer 1 (NaN): {original_count} -> {len(cleaned_df)}")
        return cleaned_df, result

    def _layer2_price_validation(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Layer 2: 价格合理性检查

        白皮书依据: 第三章 3.3 Layer 2

        Args:
            df: 输入数据

        Returns:
            (清洗后数据, 清洗结果)
        """
        original_count = len(df)

        # 检查价格列是否存在
        price_columns = ["open", "high", "low", "close"]
        existing_columns = [col for col in price_columns if col in df.columns]

        if not existing_columns:
            logger.warning("No price columns found, skipping price validation")
            return df, {"skipped": True, "reason": "No price columns"}

        # 价格合理性检查
        min_price = self.price_range.min_price
        max_price = self.price_range.max_price

        invalid_mask = pd.Series(False, index=df.index)

        for col in existing_columns:
            if col in df.columns:
                invalid_mask |= (df[col] <= 0) | (df[col] < min_price) | (df[col] > max_price)

        # 移除无效价格的行
        cleaned_df = df[~invalid_mask]

        result = {
            "original_count": original_count,
            "cleaned_count": len(cleaned_df),
            "removed_count": original_count - len(cleaned_df),
            "price_range": f"{min_price}-{max_price}",
            "checked_columns": existing_columns,
        }

        logger.debug(f"Layer 2 (Price): {original_count} -> {len(cleaned_df)}")
        return cleaned_df, result

    def _layer3_hloc_consistency(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Layer 3: HLOC一致性检查

        白皮书依据: 第三章 3.3 Layer 3

        Args:
            df: 输入数据

        Returns:
            (清洗后数据, 清洗结果)
        """
        original_count = len(df)

        # 检查HLOC列是否存在
        required_columns = ["high", "low", "open", "close"]
        if not all(col in df.columns for col in required_columns):
            logger.warning("HLOC columns not complete, skipping consistency check")
            return df, {"skipped": True, "reason": "Incomplete HLOC columns"}

        # HLOC一致性检查
        invalid_mask = (
            (df["high"] < df["low"])  # High < Low
            | (df["high"] < df["open"])  # High < Open
            | (df["high"] < df["close"])  # High < Close
            | (df["low"] > df["open"])  # Low > Open
            | (df["low"] > df["close"])  # Low > Close
            | (abs(df["close"] - df["open"]) > df["open"] * self.config["price_change_threshold"])  # 异常价格变动
        )

        # 移除不一致的行
        cleaned_df = df[~invalid_mask]

        result = {
            "original_count": original_count,
            "cleaned_count": len(cleaned_df),
            "removed_count": original_count - len(cleaned_df),
            "consistency_rules": [
                "High >= Low",
                "High >= Open",
                "High >= Close",
                "Low <= Open",
                "Low <= Close",
                f'|Close - Open| <= {self.config["price_change_threshold"]*100}% of Open',
            ],
        }

        logger.debug(f"Layer 3 (HLOC): {original_count} -> {len(cleaned_df)}")
        return cleaned_df, result

    def _layer4_volume_check(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Layer 4: 成交量检查

        白皮书依据: 第三章 3.3 Layer 4

        Args:
            df: 输入数据

        Returns:
            (清洗后数据, 清洗结果)
        """
        original_count = len(df)

        # 检查成交量列是否存在
        volume_columns = ["volume", "vol"]
        volume_col = None

        for col in volume_columns:
            if col in df.columns:
                volume_col = col
                break

        if volume_col is None:
            logger.warning("No volume column found, skipping volume check")
            return df, {"skipped": True, "reason": "No volume column"}

        # 成交量检查
        invalid_mask = (df[volume_col] < self.config["volume_threshold"]) | (  # 成交量过小
            df[volume_col].isnull()
        )  # 成交量为空

        # 移除无效成交量的行
        cleaned_df = df[~invalid_mask]

        result = {
            "original_count": original_count,
            "cleaned_count": len(cleaned_df),
            "removed_count": original_count - len(cleaned_df),
            "volume_column": volume_col,
            "volume_threshold": self.config["volume_threshold"],
        }

        logger.debug(f"Layer 4 (Volume): {original_count} -> {len(cleaned_df)}")
        return cleaned_df, result

    def _layer5_duplicate_check(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Layer 5: 重复值检查

        白皮书依据: 第三章 3.3 Layer 5

        Args:
            df: 输入数据

        Returns:
            (清洗后数据, 清洗结果)
        """
        original_count = len(df)

        # 检查重复行
        duplicate_mask = df.duplicated()
        duplicate_count = duplicate_mask.sum()
        duplicate_ratio = duplicate_count / len(df) if len(df) > 0 else 0

        # 移除重复行
        cleaned_df = df[~duplicate_mask]

        result = {
            "original_count": original_count,
            "cleaned_count": len(cleaned_df),
            "removed_count": original_count - len(cleaned_df),
            "duplicate_ratio": duplicate_ratio,
            "threshold_exceeded": duplicate_ratio > self.config["duplicate_threshold"],
        }

        if result["threshold_exceeded"]:
            logger.warning(f"High duplicate ratio: {duplicate_ratio:.2%} > {self.config['duplicate_threshold']:.2%}")

        logger.debug(f"Layer 5 (Duplicate): {original_count} -> {len(cleaned_df)}")
        return cleaned_df, result

    def _layer6_outlier_detection(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Layer 6: 异常值检测

        白皮书依据: 第三章 3.3 Layer 6

        Args:
            df: 输入数据

        Returns:
            (清洗后数据, 清洗结果)
        """
        original_count = len(df)

        # 检查数值列
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()

        if not numeric_columns:
            logger.warning("No numeric columns found, skipping outlier detection")
            return df, {"skipped": True, "reason": "No numeric columns"}

        # 异常值检测（使用Z-score方法）
        outlier_mask = pd.Series(False, index=df.index)
        outlier_details = {}

        for col in numeric_columns:
            if col in df.columns:
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                col_outliers = z_scores > self.config["outlier_std_threshold"]
                outlier_mask |= col_outliers
                outlier_details[col] = col_outliers.sum()

        # 移除异常值
        cleaned_df = df[~outlier_mask]

        result = {
            "original_count": original_count,
            "cleaned_count": len(cleaned_df),
            "removed_count": original_count - len(cleaned_df),
            "outlier_threshold": self.config["outlier_std_threshold"],
            "outlier_details": outlier_details,
            "checked_columns": numeric_columns,
        }

        logger.debug(f"Layer 6 (Outlier): {original_count} -> {len(cleaned_df)}")
        return cleaned_df, result

    def _layer7_gap_detection(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Layer 7: 数据缺口检测

        白皮书依据: 第三章 3.3 Layer 7

        Args:
            df: 输入数据

        Returns:
            (清洗后数据, 清洗结果)
        """
        original_count = len(df)

        # 检查时间列
        time_columns = ["timestamp", "datetime", "date", "time"]
        time_col = None

        for col in time_columns:
            if col in df.columns:
                time_col = col
                break

        if time_col is None:
            logger.warning("No time column found, skipping gap detection")
            return df, {"skipped": True, "reason": "No time column"}

        # 简化的缺口检测（这里可以根据具体需求实现更复杂的逻辑）
        # 目前只是占位实现
        result = {
            "original_count": original_count,
            "cleaned_count": original_count,
            "removed_count": 0,
            "time_column": time_col,
            "gaps_detected": 0,
        }

        logger.debug(f"Layer 7 (Gap): {original_count} -> {original_count}")
        return df, result

    def _layer8_corporate_actions(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Layer 8: 公司行动处理

        白皮书依据: 第三章 3.3 Layer 8

        Args:
            df: 输入数据

        Returns:
            (清洗后数据, 清洗结果)
        """
        original_count = len(df)

        # 简化的公司行动处理（这里可以根据具体需求实现更复杂的逻辑）
        # 目前只是占位实现
        result = {
            "original_count": original_count,
            "cleaned_count": original_count,
            "removed_count": 0,
            "corporate_actions_processed": 0,
        }

        logger.debug(f"Layer 8 (Corporate): {original_count} -> {original_count}")
        return df, result

    def _calculate_quality_score(
        self, original_count: int, cleaned_count: int, layer_results: Dict[str, Dict[str, Any]]
    ) -> float:
        """计算数据质量评分

        Args:
            original_count: 原始数据行数
            cleaned_count: 清洗后数据行数
            layer_results: 各层清洗结果

        Returns:
            质量评分 (0-1)
        """
        if original_count == 0:
            return 0.0

        # 基础评分：保留数据比例
        retention_ratio = cleaned_count / original_count
        base_score = retention_ratio * 0.6

        # 质量加分：各层清洗效果
        quality_bonus = 0.0

        # NaN比例加分
        if "layer1_nan" in layer_results:
            nan_result = layer_results["layer1_nan"]
            if not nan_result.get("threshold_exceeded", False):
                quality_bonus += 0.1

        # 重复值比例加分
        if "layer5_duplicate" in layer_results:
            dup_result = layer_results["layer5_duplicate"]
            if not dup_result.get("threshold_exceeded", False):
                quality_bonus += 0.1

        # 一致性检查加分
        if "layer3_hloc" in layer_results:
            hloc_result = layer_results["layer3_hloc"]
            if not hloc_result.get("skipped", False):
                quality_bonus += 0.1

        # 价格合理性加分
        if "layer2_price" in layer_results:
            price_result = layer_results["layer2_price"]
            if not price_result.get("skipped", False):
                quality_bonus += 0.1

        total_score = min(base_score + quality_bonus, 1.0)
        return total_score

    def generate_report(self, result: CleaningResult) -> str:
        """生成清洗报告

        Args:
            result: 清洗结果

        Returns:
            清洗报告文本
        """
        report = []
        report.append("=" * 60)
        report.append("数据清洗报告")
        report.append("=" * 60)
        report.append(f"资产类型: {self.asset_type.value}")
        report.append(f"原始数据: {result.original_count:,} 行")
        report.append(f"清洗后数据: {result.cleaned_count:,} 行")
        report.append(f"移除数据: {result.removed_count:,} 行 ({result.removed_count/result.original_count*100:.1f}%)")
        report.append(f"质量评分: {result.quality_score:.3f}")
        report.append("")

        # 各层清洗结果
        report.append("各层清洗结果:")
        report.append("-" * 40)

        for layer_name, layer_result in result.layer_results.items():
            if layer_result.get("skipped"):
                report.append(f"{layer_name}: 跳过 ({layer_result.get('reason', 'Unknown')})")
            else:
                removed = layer_result.get("removed_count", 0)
                report.append(f"{layer_name}: 移除 {removed} 行")

        # 警告和错误
        if result.warnings:
            report.append("")
            report.append("警告:")
            for warning in result.warnings:
                report.append(f"  - {warning}")

        if result.errors:
            report.append("")
            report.append("错误:")
            for error in result.errors:
                report.append(f"  - {error}")

        report.append("=" * 60)

        return "\n".join(report)
