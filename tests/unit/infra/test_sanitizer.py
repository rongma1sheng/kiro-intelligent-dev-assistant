"""数据清洗器单元测试

白皮书依据: 第三章 3.3 深度清洗矩阵

测试覆盖:
- AssetType枚举有效性
- DataSanitizer基础功能
- 8层清洗框架
- 数据质量评估
- 边界条件和异常情况
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch

from src.infra.sanitizer import AssetType, DataSanitizer


class TestAssetType:
    """AssetType枚举测试"""
    
    def test_asset_type_values(self):
        """测试资产类型值"""
        assert AssetType.STOCK.value == "stock"
        assert AssetType.FUTURE.value == "future"
        assert AssetType.OPTION.value == "option"
        assert AssetType.FUND.value == "fund"
        assert AssetType.INDEX.value == "index"
    
    def test_asset_type_completeness(self):
        """测试资产类型枚举完整性"""
        expected_types = {'STOCK', 'FUTURE', 'OPTION', 'FUND', 'INDEX'}
        actual_types = {at.name for at in AssetType}
        
        assert actual_types == expected_types


class TestDataSanitizer:
    """DataSanitizer类测试"""
    
    @pytest.fixture
    def stock_sanitizer(self):
        """股票数据清洗器"""
        return DataSanitizer(asset_type=AssetType.STOCK)
    
    @pytest.fixture
    def future_sanitizer(self):
        """期货数据清洗器"""
        return DataSanitizer(asset_type=AssetType.FUTURE)
    
    @pytest.fixture
    def option_sanitizer(self):
        """期权数据清洗器"""
        return DataSanitizer(asset_type=AssetType.OPTION)
    
    @pytest.fixture
    def sample_stock_data(self):
        """示例股票数据"""
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        return pd.DataFrame({
            'date': dates,
            'open': [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0],
            'high': [102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0],
            'low': [99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0],
            'close': [101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0],
            'volume': [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
        })
    
    @pytest.fixture
    def dirty_stock_data(self):
        """脏股票数据（包含各种问题）"""
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        return pd.DataFrame({
            'date': dates,
            'open': [100.0, np.nan, 102.0, -5.0, 104.0, 105.0, 106.0, 107.0, 108.0, 15000.0],
            'high': [102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0],
            'low': [99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0],
            'close': [101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0],
            'volume': [1000, -100, 1200, 1300, 1400, 0, 1600, 1700, 1800, 1000000]
        })
    
    def test_sanitizer_initialization_default(self):
        """测试默认初始化"""
        sanitizer = DataSanitizer()
        
        assert sanitizer.asset_type == AssetType.STOCK
        assert sanitizer.strictness == 0.95
        assert sanitizer.clean_rules is not None
    
    def test_sanitizer_initialization_with_params(self):
        """测试带参数初始化"""
        sanitizer = DataSanitizer(
            asset_type=AssetType.FUTURE,
            strictness=0.85
        )
        
        assert sanitizer.asset_type == AssetType.FUTURE
        assert sanitizer.strictness == 0.85
    
    def test_sanitizer_initialization_invalid_strictness(self):
        """测试无效严格程度"""
        with pytest.raises(ValueError, match="strictness必须在\\(0, 1\\]"):
            DataSanitizer(strictness=0.0)
        
        with pytest.raises(ValueError, match="strictness必须在\\(0, 1\\]"):
            DataSanitizer(strictness=1.5)
        
        with pytest.raises(ValueError, match="strictness必须在\\(0, 1\\]"):
            DataSanitizer(strictness=-0.1)
    
    def test_get_clean_rules_stock(self, stock_sanitizer):
        """测试股票清洗规则"""
        rules = stock_sanitizer.clean_rules
        
        assert rules['nan'] is True
        assert rules['price'] is True
        assert rules['hloc'] is True
        assert rules['volume'] is True
        assert rules['duplicate'] is True
        assert rules['outliers'] is True
        assert rules['gaps'] is True
        assert rules['corporate_actions'] is True
    
    def test_get_clean_rules_future(self, future_sanitizer):
        """测试期货清洗规则"""
        rules = future_sanitizer.clean_rules
        
        assert rules['nan'] is True
        assert rules['price'] is True
        assert rules['hloc'] is True
        assert rules['volume'] is True
        assert rules['duplicate'] is True
        assert rules['outliers'] is True
        assert rules['gaps'] is True
        assert rules['corporate_actions'] is False
    
    def test_get_clean_rules_option(self, option_sanitizer):
        """测试期权清洗规则"""
        rules = option_sanitizer.clean_rules
        
        assert rules['nan'] is True
        assert rules['price'] is True
        assert rules['hloc'] is False  # 期权HLOC规则不适用
        assert rules['volume'] is True
        assert rules['duplicate'] is True
        assert rules['outliers'] is True
        assert rules['gaps'] is True
        assert rules['corporate_actions'] is False
    
    def test_clean_empty_data(self, stock_sanitizer):
        """测试清洗空数据"""
        empty_df = pd.DataFrame()
        
        with pytest.raises(ValueError, match="输入数据不能为空"):
            stock_sanitizer.clean(empty_df)
    
    def test_clean_valid_data(self, stock_sanitizer, sample_stock_data):
        """测试清洗有效数据"""
        result = stock_sanitizer.clean(sample_stock_data)
        
        assert len(result) == len(sample_stock_data)
        assert list(result.columns) == list(sample_stock_data.columns)
    
    def test_clean_nan_layer(self, stock_sanitizer):
        """测试Layer 1: NaN清洗"""
        data_with_nan = pd.DataFrame({
            'open': [100.0, np.nan, 102.0],
            'close': [101.0, 102.0, np.nan],
            'volume': [1000, 1100, 1200]
        })
        
        result = stock_sanitizer._clean_nan(data_with_nan)
        
        assert len(result) == 1  # 只有第一行没有NaN
        assert result.iloc[0]['open'] == 100.0
        assert result.iloc[0]['close'] == 101.0
        assert result.iloc[0]['volume'] == 1000
    
    def test_check_price_validity_stock(self, stock_sanitizer):
        """测试Layer 2: 股票价格合理性检查"""
        data_with_invalid_prices = pd.DataFrame({
            'open': [100.0, -5.0, 15000.0, 50.0],
            'high': [102.0, 10.0, 15100.0, 52.0],
            'low': [99.0, -10.0, 14900.0, 49.0],
            'close': [101.0, 5.0, 15050.0, 51.0]
        })
        
        result = stock_sanitizer._check_price_validity(data_with_invalid_prices)
        
        assert len(result) == 2  # 只有第1行和第4行有效
        assert result.iloc[0]['open'] == 100.0
        assert result.iloc[1]['open'] == 50.0
    
    def test_check_price_validity_future(self, future_sanitizer):
        """测试期货价格合理性检查"""
        data_with_invalid_prices = pd.DataFrame({
            'open': [1000.0, -5.0, 60000.0, 500.0],
            'close': [1010.0, 5.0, 60500.0, 510.0]
        })
        
        result = future_sanitizer._check_price_validity(data_with_invalid_prices)
        
        assert len(result) == 2  # 只有第1行和第4行有效
        assert result.iloc[0]['open'] == 1000.0
        assert result.iloc[1]['open'] == 500.0
    
    def test_check_hloc_consistency_valid(self, stock_sanitizer):
        """测试Layer 3: 有效HLOC一致性"""
        valid_hloc_data = pd.DataFrame({
            'open': [100.0, 101.0, 102.0],
            'high': [105.0, 106.0, 107.0],
            'low': [95.0, 96.0, 97.0],
            'close': [103.0, 104.0, 105.0]
        })
        
        result = stock_sanitizer._check_hloc_consistency(valid_hloc_data)
        
        assert len(result) == 3  # 所有行都有效
    
    def test_check_hloc_consistency_invalid(self, stock_sanitizer):
        """测试Layer 3: 无效HLOC一致性"""
        invalid_hloc_data = pd.DataFrame({
            'open': [100.0, 101.0, 102.0],
            'high': [95.0, 106.0, 107.0],  # 第1行high < open，无效
            'low': [105.0, 96.0, 97.0],    # 第1行low > open，无效
            'close': [103.0, 104.0, 105.0]
        })
        
        result = stock_sanitizer._check_hloc_consistency(invalid_hloc_data)
        
        assert len(result) == 2  # 只有第2、3行有效
    
    def test_check_hloc_consistency_missing_columns(self, stock_sanitizer):
        """测试HLOC一致性检查缺失列"""
        data_missing_columns = pd.DataFrame({
            'open': [100.0, 101.0],
            'close': [103.0, 104.0]
            # 缺少high和low列
        })
        
        result = stock_sanitizer._check_hloc_consistency(data_missing_columns)
        
        assert len(result) == 2  # 返回原数据
        assert list(result.columns) == ['open', 'close']
    
    def test_check_volume_valid(self, stock_sanitizer):
        """测试Layer 4: 有效成交量检查"""
        valid_volume_data = pd.DataFrame({
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        
        result = stock_sanitizer._check_volume(valid_volume_data)
        
        assert len(result) == 5  # 所有行都有效
    
    def test_check_volume_invalid(self, stock_sanitizer):
        """测试Layer 4: 无效成交量检查"""
        invalid_volume_data = pd.DataFrame({
            'volume': [1000, -100, 1200, 1300, 1400]  # 第2行负数，无效
        })
        
        result = stock_sanitizer._check_volume(invalid_volume_data)
        
        assert len(result) == 4  # 第2行被过滤
        assert -100 not in result['volume'].values
    
    def test_check_volume_missing_column(self, stock_sanitizer):
        """测试成交量检查缺失列"""
        data_no_volume = pd.DataFrame({
            'open': [100.0, 101.0],
            'close': [103.0, 104.0]
        })
        
        result = stock_sanitizer._check_volume(data_no_volume)
        
        assert len(result) == 2  # 返回原数据
        assert list(result.columns) == ['open', 'close']
    
    def test_remove_duplicates_complete(self, stock_sanitizer):
        """测试Layer 5: 完全重复行移除"""
        duplicate_data = pd.DataFrame({
            'open': [100.0, 101.0, 100.0, 102.0],
            'close': [103.0, 104.0, 103.0, 105.0]
        })
        
        result = stock_sanitizer._remove_duplicates(duplicate_data)
        
        assert len(result) == 3  # 移除1个重复行
    
    def test_remove_duplicates_by_date(self, stock_sanitizer):
        """测试按日期的重复移除"""
        duplicate_date_data = pd.DataFrame({
            'date': ['2024-01-01', '2024-01-02', '2024-01-01', '2024-01-03'],
            'open': [100.0, 101.0, 100.5, 102.0],
            'close': [103.0, 104.0, 103.5, 105.0]
        })
        
        result = stock_sanitizer._remove_duplicates(duplicate_date_data)
        
        assert len(result) == 3  # 移除1个重复日期
        # 应该保留最后一个重复日期的记录
        date_2024_01_01_rows = result[result['date'] == '2024-01-01']
        assert len(date_2024_01_01_rows) == 1
        assert date_2024_01_01_rows.iloc[0]['open'] == 100.5
    
    def test_detect_outliers_normal_data(self, stock_sanitizer):
        """测试Layer 6: 正常数据异常值检测"""
        normal_data = pd.DataFrame({
            'close': [100.0, 101.0, 102.0, 103.0, 104.0]
        })
        
        result = stock_sanitizer._detect_outliers(normal_data)
        
        assert len(result) == 5  # 所有数据都保留
    
    def test_detect_outliers_with_outliers(self, stock_sanitizer):
        """测试异常值检测"""
        # 需要至少10行数据才能触发异常值检测
        data_with_outliers = pd.DataFrame({
            'close': [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 500.0]  # 500.0是异常值
        })
        
        result = stock_sanitizer._detect_outliers(data_with_outliers)
        
        assert len(result) < 10  # 异常值被移除
        assert 500.0 not in result['close'].values
    
    def test_detect_outliers_insufficient_data(self, stock_sanitizer):
        """测试数据不足时的异常值检测"""
        insufficient_data = pd.DataFrame({
            'close': [100.0, 101.0]  # 少于10行
        })
        
        result = stock_sanitizer._detect_outliers(insufficient_data)
        
        assert len(result) == 2  # 返回原数据
    
    def test_detect_outliers_missing_close(self, stock_sanitizer):
        """测试缺失close列的异常值检测"""
        data_no_close = pd.DataFrame({
            'open': [100.0, 101.0, 102.0]
        })
        
        result = stock_sanitizer._detect_outliers(data_no_close)
        
        assert len(result) == 3  # 返回原数据
        assert list(result.columns) == ['open']
    
    def test_detect_gaps_normal_data(self, stock_sanitizer):
        """测试Layer 7: 正常数据缺口检测"""
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        normal_data = pd.DataFrame({
            'date': dates,
            'close': [100.0, 101.0, 102.0, 103.0, 104.0]
        })
        
        result = stock_sanitizer._detect_gaps(normal_data)
        
        assert len(result) == 5  # 所有数据都保留
        # 应该按日期排序
        assert result['date'].is_monotonic_increasing
    
    def test_detect_gaps_with_gaps(self, stock_sanitizer):
        """测试有缺口的数据"""
        dates = [
            pd.Timestamp('2024-01-01'),
            pd.Timestamp('2024-01-02'),
            pd.Timestamp('2024-01-15'),  # 13天缺口
            pd.Timestamp('2024-01-16')
        ]
        data_with_gaps = pd.DataFrame({
            'date': dates,
            'close': [100.0, 101.0, 102.0, 103.0]
        })
        
        with patch('src.infra.sanitizer.logger') as mock_logger:
            result = stock_sanitizer._detect_gaps(data_with_gaps)
            
            # 应该记录警告
            mock_logger.warning.assert_called()
            
        assert len(result) == 4  # 所有数据都保留，只是记录警告
    
    def test_detect_gaps_insufficient_data(self, stock_sanitizer):
        """测试数据不足时的缺口检测"""
        insufficient_data = pd.DataFrame({
            'date': [pd.Timestamp('2024-01-01')],
            'close': [100.0]
        })
        
        result = stock_sanitizer._detect_gaps(insufficient_data)
        
        assert len(result) == 1  # 返回原数据
    
    def test_detect_gaps_missing_date(self, stock_sanitizer):
        """测试缺失日期列的缺口检测"""
        data_no_date = pd.DataFrame({
            'close': [100.0, 101.0, 102.0]
        })
        
        result = stock_sanitizer._detect_gaps(data_no_date)
        
        assert len(result) == 3  # 返回原数据
    
    def test_handle_corporate_actions_stock(self, stock_sanitizer):
        """测试Layer 8: 股票公司行动处理"""
        # 模拟除权除息导致的价格跳变
        corporate_action_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=5, freq='D'),
            'close': [100.0, 101.0, 50.0, 51.0, 52.0]  # 第3天价格减半（可能是分红）
        })
        
        with patch('src.infra.sanitizer.logger') as mock_logger:
            result = stock_sanitizer._handle_corporate_actions(corporate_action_data)
            
            # 应该记录信息
            mock_logger.info.assert_called()
        
        assert len(result) == 5  # 所有数据都保留
    
    def test_handle_corporate_actions_non_stock(self, future_sanitizer):
        """测试非股票资产的公司行动处理"""
        data = pd.DataFrame({
            'close': [100.0, 101.0, 50.0, 51.0, 52.0]
        })
        
        result = future_sanitizer._handle_corporate_actions(data)
        
        assert len(result) == 5  # 返回原数据（期货不处理公司行动）
    
    def test_handle_corporate_actions_insufficient_data(self, stock_sanitizer):
        """测试数据不足时的公司行动处理"""
        insufficient_data = pd.DataFrame({
            'close': [100.0]
        })
        
        result = stock_sanitizer._handle_corporate_actions(insufficient_data)
        
        assert len(result) == 1  # 返回原数据
    
    def test_assess_quality_perfect_data(self, stock_sanitizer, sample_stock_data):
        """测试完美数据的质量评估"""
        quality = stock_sanitizer.assess_quality(sample_stock_data)
        
        assert quality['overall'] > 0.9  # 高质量
        assert quality['completeness'] == 1.0  # 完整性100%
        assert quality['price_validity'] == 1.0  # 价格有效性100%
        assert quality['hloc_consistency'] == 1.0  # HLOC一致性100%
        assert quality['volume_validity'] == 1.0  # 成交量有效性100%
    
    def test_assess_quality_dirty_data(self, stock_sanitizer, dirty_stock_data):
        """测试脏数据的质量评估"""
        quality = stock_sanitizer.assess_quality(dirty_stock_data)
        
        assert quality['overall'] < 0.9  # 低质量
        assert quality['completeness'] < 1.0  # 有NaN值
        assert quality['price_validity'] < 1.0  # 有无效价格
        assert quality['volume_validity'] < 1.0  # 有无效成交量
    
    def test_assess_quality_empty_data(self, stock_sanitizer):
        """测试空数据的质量评估"""
        empty_data = pd.DataFrame()
        
        quality = stock_sanitizer.assess_quality(empty_data)
        
        assert quality['overall'] == 0.0
        assert quality['completeness'] == 0.0
    
    def test_assess_quality_missing_columns(self, stock_sanitizer):
        """测试缺失列的质量评估"""
        minimal_data = pd.DataFrame({
            'some_column': [1, 2, 3]
        })
        
        quality = stock_sanitizer.assess_quality(minimal_data)
        
        assert 'overall' in quality
        assert 'completeness' in quality
        # 缺失价格、HLOC、成交量列时使用默认值
        assert quality['price_validity'] == 1.0
        assert quality['hloc_consistency'] == 1.0
        assert quality['volume_validity'] == 1.0
    
    def test_full_cleaning_pipeline(self, stock_sanitizer, dirty_stock_data):
        """测试完整清洗流程"""
        original_len = len(dirty_stock_data)
        
        result = stock_sanitizer.clean(dirty_stock_data)
        
        # 清洗后数据应该更少（移除了问题数据）
        assert len(result) < original_len
        
        # 清洗后数据质量应该更高
        original_quality = stock_sanitizer.assess_quality(dirty_stock_data)
        cleaned_quality = stock_sanitizer.assess_quality(result)
        
        assert cleaned_quality['overall'] > original_quality['overall']
        assert cleaned_quality['completeness'] >= original_quality['completeness']
        assert cleaned_quality['price_validity'] >= original_quality['price_validity']
        assert cleaned_quality['volume_validity'] >= original_quality['volume_validity']


class TestDataSanitizerAssetTypeSpecific:
    """资产类型特定测试"""
    
    @pytest.mark.parametrize("asset_type,expected_strictness", [
        (AssetType.STOCK, 0.95),
        (AssetType.FUTURE, 0.90),
        (AssetType.OPTION, 0.85),
        (AssetType.FUND, 0.90),
        (AssetType.INDEX, 0.95),
    ])
    def test_default_strictness_by_asset_type(self, asset_type, expected_strictness):
        """测试不同资产类型的默认严格程度"""
        sanitizer = DataSanitizer(asset_type=asset_type)
        
        assert sanitizer.strictness == expected_strictness
    
    @pytest.mark.parametrize("asset_type,has_hloc,has_corporate_actions", [
        (AssetType.STOCK, True, True),
        (AssetType.FUTURE, True, False),
        (AssetType.OPTION, False, False),
        (AssetType.FUND, True, False),
        (AssetType.INDEX, True, False),
    ])
    def test_clean_rules_by_asset_type(self, asset_type, has_hloc, has_corporate_actions):
        """测试不同资产类型的清洗规则"""
        sanitizer = DataSanitizer(asset_type=asset_type)
        rules = sanitizer.clean_rules
        
        assert rules['hloc'] == has_hloc
        assert rules['corporate_actions'] == has_corporate_actions
        
        # 所有资产类型都应该有的基础规则
        assert rules['nan'] is True
        assert rules['price'] is True
        assert rules['volume'] is True
        assert rules['duplicate'] is True
        assert rules['outliers'] is True
        assert rules['gaps'] is True


class TestDataSanitizerEdgeCases:
    """边界条件测试"""
    
    def test_single_row_data(self):
        """测试单行数据"""
        sanitizer = DataSanitizer()
        single_row = pd.DataFrame({
            'open': [100.0],
            'high': [105.0],
            'low': [95.0],
            'close': [103.0],
            'volume': [1000]
        })
        
        result = sanitizer.clean(single_row)
        
        assert len(result) == 1
    
    def test_all_nan_data(self):
        """测试全NaN数据"""
        sanitizer = DataSanitizer()
        all_nan = pd.DataFrame({
            'open': [np.nan, np.nan],
            'close': [np.nan, np.nan]
        })
        
        result = sanitizer.clean(all_nan)
        
        assert len(result) == 0  # 所有行都被过滤
    
    def test_extreme_values(self):
        """测试极值数据"""
        sanitizer = DataSanitizer(asset_type=AssetType.STOCK)
        extreme_data = pd.DataFrame({
            'open': [0.01, 9999.99],  # 边界值
            'high': [0.02, 10000.0],
            'low': [0.01, 9999.98],
            'close': [0.015, 9999.995],
            'volume': [1, 999999999]
        })
        
        result = sanitizer.clean(extreme_data)
        
        assert len(result) == 2  # 边界值应该被保留
    
    def test_mixed_data_types(self):
        """测试混合数据类型"""
        sanitizer = DataSanitizer()
        mixed_data = pd.DataFrame({
            'open': [100.0, '101.0', 102.0],  # 包含字符串
            'close': [103.0, 104.0, 105.0]
        })
        
        # 应该能处理类型转换或过滤无效数据
        # 具体行为取决于pandas的处理方式
        result = sanitizer.clean(mixed_data)
        
        assert isinstance(result, pd.DataFrame)
    
    def test_very_large_dataset(self):
        """测试大数据集性能"""
        sanitizer = DataSanitizer()
        
        # 创建10000行数据
        large_data = pd.DataFrame({
            'open': np.random.uniform(50, 150, 10000),
            'high': np.random.uniform(55, 155, 10000),
            'low': np.random.uniform(45, 145, 10000),
            'close': np.random.uniform(50, 150, 10000),
            'volume': np.random.randint(1000, 10000, 10000)
        })
        
        # 确保HLOC一致性
        large_data['high'] = np.maximum.reduce([
            large_data['open'], large_data['high'], 
            large_data['low'], large_data['close']
        ])
        large_data['low'] = np.minimum.reduce([
            large_data['open'], large_data['high'], 
            large_data['low'], large_data['close']
        ])
        
        import time
        start_time = time.time()
        result = sanitizer.clean(large_data)
        elapsed = time.time() - start_time
        
        assert len(result) > 0
        assert elapsed < 5.0  # 应该在5秒内完成
    
    def test_unicode_column_names(self):
        """测试Unicode列名"""
        sanitizer = DataSanitizer()
        unicode_data = pd.DataFrame({
            '开盘价': [100.0, 101.0],
            '收盘价': [103.0, 104.0],
            '成交量': [1000, 1100]
        })
        
        # 应该能处理Unicode列名
        result = sanitizer.clean(unicode_data)
        
        assert len(result) == 2
        assert '开盘价' in result.columns