"""数据清洗器

白皮书依据: 第三章 3.3 深度清洗矩阵

实现8层清洗框架，支持资产类型自适应的多层次清洗。
"""

from enum import Enum
from typing import Dict, Optional

import pandas as pd
from loguru import logger


class AssetType(Enum):
    """资产类型

    白皮书依据: 第三章 3.3 深度清洗矩阵

    支持多种资产类型，每种类型有不同的清洗规则。
    """

    STOCK = "stock"
    FUTURE = "future"
    OPTION = "option"
    FUND = "fund"
    INDEX = "index"


class DataSanitizer:
    """数据清洗器

    白皮书依据: 第三章 3.3 深度清洗矩阵

    8层清洗框架：
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
        strictness: 严格程度 (0.85-0.95)
        clean_rules: 清洗规则配置

    Example:
        >>> sanitizer = DataSanitizer(asset_type=AssetType.STOCK)
        >>> df_clean = sanitizer.clean(df_raw)
        >>> quality = sanitizer.assess_quality(df_clean)
        >>> print(f"Quality: {quality['overall']:.2%}")
    """

    def __init__(self, asset_type: AssetType = AssetType.STOCK, strictness: Optional[float] = None):
        """初始化数据清洗器

        Args:
            asset_type: 资产类型
            strictness: 严格程度，None表示使用默认值

        Raises:
            ValueError: 当参数不合法时
        """
        self.asset_type = asset_type

        # 根据资产类型设置默认严格程度
        default_strictness = {
            AssetType.STOCK: 0.95,
            AssetType.FUTURE: 0.90,
            AssetType.OPTION: 0.85,
            AssetType.FUND: 0.90,
            AssetType.INDEX: 0.95,
        }

        self.strictness = strictness if strictness is not None else default_strictness[asset_type]

        if not 0 < self.strictness <= 1:
            raise ValueError(f"strictness必须在(0, 1]，当前: {self.strictness}")

        # 清洗规则配置
        self.clean_rules = self._get_clean_rules()

        logger.info(f"DataSanitizer initialized: " f"asset_type={asset_type.value}, " f"strictness={self.strictness}")

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """清洗数据

        白皮书依据: 第三章 3.3 深度清洗矩阵

        Args:
            df: 原始数据

        Returns:
            清洗后的数据

        Raises:
            ValueError: 当数据格式不正确时
        """
        if df.empty:
            raise ValueError("输入数据不能为空")

        logger.info(f"开始清洗数据: {len(df)} rows")

        df_clean = df.copy()

        # Layer 1: NaN清洗
        if self.clean_rules["nan"]:
            df_clean = self._clean_nan(df_clean)

        # Layer 2: 价格合理性检查
        if self.clean_rules["price"]:
            df_clean = self._check_price_validity(df_clean)

        # Layer 3: HLOC一致性检查
        if self.clean_rules["hloc"]:
            df_clean = self._check_hloc_consistency(df_clean)

        # Layer 4: 成交量检查
        if self.clean_rules["volume"]:
            df_clean = self._check_volume(df_clean)

        # Layer 5: 重复值检查
        if self.clean_rules["duplicate"]:
            df_clean = self._remove_duplicates(df_clean)

        # Layer 6: 异常值检测
        if self.clean_rules["outliers"]:
            df_clean = self._detect_outliers(df_clean)

        # Layer 7: 数据缺口检测
        if self.clean_rules["gaps"]:
            df_clean = self._detect_gaps(df_clean)

        # Layer 8: 公司行动处理
        if self.clean_rules["corporate_actions"]:
            df_clean = self._handle_corporate_actions(df_clean)

        logger.info(f"清洗完成: {len(df)} → {len(df_clean)} rows " f"({len(df_clean)/len(df)*100:.2f}%)")

        return df_clean

    def assess_quality(self, df: pd.DataFrame) -> Dict[str, float]:
        """评估数据质量

        Args:
            df: 要评估的数据

        Returns:
            质量评估结果
        """
        if df.empty:
            return {"overall": 0.0, "completeness": 0.0}

        # 计算完整性
        completeness = 1.0 - (df.isnull().sum().sum() / (len(df) * len(df.columns)))

        # 计算价格有效性（如果有价格列）
        price_validity = 1.0
        price_columns = ["open", "high", "low", "close"]
        valid_price_counts = []
        total_price_values = 0

        for col in price_columns:
            if col in df.columns:
                valid_prices = (df[col] > 0) & (df[col] < 10000)
                valid_price_counts.append(valid_prices.sum())
                total_price_values += len(df)

        if total_price_values > 0:
            price_validity = sum(valid_price_counts) / total_price_values

        # 计算HLOC一致性（如果有HLOC列）
        hloc_consistency = 1.0
        if all(col in df.columns for col in ["open", "high", "low", "close"]):
            valid_hloc = (
                (df["high"] >= df["open"])
                & (df["high"] >= df["close"])
                & (df["low"] <= df["open"])
                & (df["low"] <= df["close"])
                & (df["high"] >= df["low"])
            )
            hloc_consistency = valid_hloc.sum() / len(df)

        # 计算成交量有效性（如果有成交量列）
        volume_validity = 1.0
        if "volume" in df.columns:
            valid_volume = df["volume"] >= 0
            volume_validity = valid_volume.sum() / len(df)

        # 综合评分
        overall = (
            completeness * 0.3 + price_validity * 0.3 + hloc_consistency * 0.2 + volume_validity * 0.2
        ) * self.strictness

        return {
            "overall": overall,
            "completeness": completeness,
            "price_validity": price_validity,
            "hloc_consistency": hloc_consistency,
            "volume_validity": volume_validity,
        }

    def _get_clean_rules(self) -> Dict[str, bool]:
        """获取清洗规则配置

        Returns:
            清洗规则字典
        """
        # 基础规则（所有资产类型都适用）
        rules = {
            "nan": True,
            "price": True,
            "volume": True,
            "duplicate": True,
            "outliers": True,
            "gaps": True,
        }

        # 资产类型特定规则
        if self.asset_type == AssetType.STOCK:
            rules.update({"hloc": True, "corporate_actions": True})
        elif self.asset_type == AssetType.FUTURE:
            rules.update({"hloc": True, "corporate_actions": False})
        elif self.asset_type == AssetType.OPTION:
            rules.update({"hloc": False, "corporate_actions": False})  # 期权HLOC规则不适用
        else:
            rules.update({"hloc": True, "corporate_actions": False})

        return rules

    def _clean_nan(self, df: pd.DataFrame) -> pd.DataFrame:
        """Layer 1: NaN清洗"""
        original_len = len(df)
        df_clean = df.dropna()

        nan_ratio = (original_len - len(df_clean)) / original_len
        if nan_ratio > 0.05:
            logger.warning(f"High NaN ratio: {nan_ratio:.2%}")

        return df_clean

    def _check_price_validity(self, df: pd.DataFrame) -> pd.DataFrame:
        """Layer 2: 价格合理性检查"""
        # 价格范围配置
        price_ranges = {
            AssetType.STOCK: (0.01, 10000),
            AssetType.FUTURE: (0.01, 50000),
            AssetType.OPTION: (0, 10000),
            AssetType.FUND: (0.01, 1000),
            AssetType.INDEX: (1, 100000),
        }

        min_price, max_price = price_ranges[self.asset_type]

        # 检查价格列
        price_columns = ["open", "high", "low", "close"]
        valid_mask = pd.Series(True, index=df.index)

        for col in price_columns:
            if col in df.columns:
                try:
                    # 尝试转换为数值类型
                    numeric_col = pd.to_numeric(df[col], errors="coerce")
                    valid_mask &= (numeric_col >= min_price) & (numeric_col <= max_price) & numeric_col.notna()
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.warning(f"Price validity check failed for column {col}: {e}")
                    # 如果转换失败，标记所有行为无效
                    valid_mask &= False

        return df[valid_mask]

    def _check_hloc_consistency(self, df: pd.DataFrame) -> pd.DataFrame:
        """Layer 3: HLOC一致性检查"""
        if not all(col in df.columns for col in ["open", "high", "low", "close"]):
            return df

        valid_hloc = (
            (df["high"] >= df["low"])
            & (df["high"] >= df["open"])
            & (df["high"] >= df["close"])
            & (df["low"] <= df["open"])
            & (df["low"] <= df["close"])
            & (abs(df["close"] - df["open"]) <= df["open"] * 0.5)  # 正常交易日涨跌幅限制
        )

        return df[valid_hloc]

    def _check_volume(self, df: pd.DataFrame) -> pd.DataFrame:
        """Layer 4: 成交量检查"""
        if "volume" not in df.columns:
            return df

        # 基本检查：成交量 >= 0
        valid_volume = df["volume"] >= 0

        # 异常成交量检查
        if len(df) > 20:
            volume_ma = df["volume"].rolling(20).mean()
            abnormal_volume = df["volume"] > volume_ma * 100
            valid_volume &= ~abnormal_volume

        # 零成交量比例检查
        zero_volume_ratio = (df["volume"] == 0).sum() / len(df)
        tolerance = {
            AssetType.STOCK: 0.05,
            AssetType.FUTURE: 0.10,
            AssetType.OPTION: 0.15,
            AssetType.FUND: 0.05,
            AssetType.INDEX: 0.01,
        }

        if zero_volume_ratio > tolerance[self.asset_type]:
            logger.warning(f"High zero-volume ratio: {zero_volume_ratio:.2%}")

        return df[valid_volume]

    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Layer 5: 重复值检查"""
        # 完全重复行
        df_clean = df.drop_duplicates(keep="last")

        # 按日期的重复（如果有日期列）
        if "date" in df.columns:
            df_clean = df_clean.drop_duplicates(subset=["date"], keep="last")

        return df_clean

    def _detect_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Layer 6: 异常值检测"""
        if "close" not in df.columns or len(df) < 10:
            return df

        # 计算涨跌幅
        df_clean = df.copy()
        df_clean["pct_change"] = df_clean["close"].pct_change()

        # 资产类型异常阈值
        thresholds = {
            AssetType.STOCK: 0.15,  # 15%
            AssetType.FUTURE: 0.20,  # 20%
            AssetType.OPTION: 0.50,  # 50%
            AssetType.FUND: 0.10,  # 10%
            AssetType.INDEX: 0.12,  # 12%
        }

        threshold = thresholds[self.asset_type]
        outliers = abs(df_clean["pct_change"]) > threshold

        # 使用sigma规则
        sigma_levels = {
            AssetType.STOCK: 3.0,
            AssetType.FUTURE: 2.5,
            AssetType.OPTION: 2.0,
            AssetType.FUND: 3.0,
            AssetType.INDEX: 3.0,
        }

        sigma = sigma_levels[self.asset_type]
        mean = df_clean["close"].mean()
        std = df_clean["close"].std()
        sigma_outliers = abs(df_clean["close"] - mean) > sigma * std

        # 移除异常值
        valid_mask = ~(outliers | sigma_outliers)
        return df_clean[valid_mask].drop(columns=["pct_change"])

    def _detect_gaps(self, df: pd.DataFrame) -> pd.DataFrame:
        """Layer 7: 数据缺口检测"""
        if "date" not in df.columns or len(df) < 2:
            return df

        df_sorted = df.sort_values("date")

        # 检测异常缺口（> 10天无数据）
        if pd.api.types.is_datetime64_any_dtype(df_sorted["date"]):
            date_diff = df_sorted["date"].diff()
            abnormal_gaps = date_diff > pd.Timedelta(days=10)

            if abnormal_gaps.any():
                gap_dates = df_sorted[abnormal_gaps]["date"].values
                logger.warning(f"Data gaps detected at: {gap_dates}")

        return df_sorted

    def _handle_corporate_actions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Layer 8: 公司行动处理"""
        if self.asset_type != AssetType.STOCK or "close" not in df.columns:
            return df

        if len(df) < 2:
            return df

        # 检测异常的价格跳变（可能是权息事件）
        df_sorted = df.sort_values("date") if "date" in df.columns else df
        price_ratio = df_sorted["close"].shift(1) / df_sorted["close"]

        # 突然的大幅跳变 > 50%
        has_event = abs(price_ratio - 1) > 0.50

        if has_event.any():
            event_dates = df_sorted[has_event].index.tolist()
            logger.info(f"Potential corporate actions detected at indices: {event_dates}")

            # 简单处理：标记但不删除（实际应用中需要获取权息信息进行复权）

        return df_sorted
