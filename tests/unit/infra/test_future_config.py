"""期货品种配置单元测试

白皮书依据: 第三章 3.3 衍生品管道

Author: MIA Team
Date: 2026-01-22
"""

import pytest
from src.infra.future_config import (
    FutureProductConfig,
    FutureType,
    get_product_config,
    extract_product_code,
    FUTURE_PRODUCTS
)


class TestFutureProductConfig:
    """期货品种配置测试"""
    
    def test_stock_index_futures_config(self):
        """测试股指期货配置"""
        # 测试IF（沪深300）
        if_config = get_product_config('IF')
        assert if_config is not None
        assert if_config.code == 'IF'
        assert if_config.name == '沪深300股指期货'
        assert if_config.future_type == FutureType.STOCK_INDEX
        assert if_config.contract_multiplier == 300
        assert if_config.tick_size == 0.2
        assert if_config.expiry_day_threshold == 7
        assert if_config.volume_threshold_ratio == 0.2
        
        # 测试IC（中证500）
        ic_config = get_product_config('IC')
        assert ic_config is not None
        assert ic_config.code == 'IC'
        assert ic_config.name == '中证500股指期货'
        assert ic_config.contract_multiplier == 200
        
        # 测试IH（上证50）
        ih_config = get_product_config('IH')
        assert ih_config is not None
        assert ih_config.code == 'IH'
        assert ih_config.name == '上证50股指期货'
        assert ih_config.contract_multiplier == 300
        
        # 测试IM（中证1000）
        im_config = get_product_config('IM')
        assert im_config is not None
        assert im_config.code == 'IM'
        assert im_config.name == '中证1000股指期货'
        assert im_config.contract_multiplier == 200
    
    def test_commodity_futures_config(self):
        """测试商品期货配置"""
        # 测试CU（沪铜）
        cu_config = get_product_config('CU')
        assert cu_config is not None
        assert cu_config.code == 'CU'
        assert cu_config.name == '沪铜期货'
        assert cu_config.future_type == FutureType.COMMODITY
        assert cu_config.contract_multiplier == 5
        assert cu_config.tick_size == 10.0
        
        # 测试AL（沪铝）
        al_config = get_product_config('AL')
        assert al_config is not None
        assert al_config.code == 'AL'
        assert al_config.name == '沪铝期货'
        assert al_config.tick_size == 5.0
        
        # 测试RB（螺纹钢）
        rb_config = get_product_config('RB')
        assert rb_config is not None
        assert rb_config.code == 'RB'
        assert rb_config.name == '螺纹钢期货'
        assert rb_config.contract_multiplier == 10
        assert rb_config.tick_size == 1.0
    
    def test_treasury_futures_config(self):
        """测试国债期货配置"""
        # 测试T（10年期国债）
        t_config = get_product_config('T')
        assert t_config is not None
        assert t_config.code == 'T'
        assert t_config.name == '10年期国债期货'
        assert t_config.future_type == FutureType.TREASURY
        assert t_config.contract_multiplier == 10000
        assert t_config.tick_size == 0.005
        
        # 测试TF（5年期国债）
        tf_config = get_product_config('TF')
        assert tf_config is not None
        assert tf_config.code == 'TF'
        assert tf_config.name == '5年期国债期货'
        assert tf_config.contract_multiplier == 10000
        
        # 测试TS（2年期国债）
        ts_config = get_product_config('TS')
        assert ts_config is not None
        assert ts_config.code == 'TS'
        assert ts_config.name == '2年期国债期货'
        assert ts_config.contract_multiplier == 20000
    
    def test_get_product_config_case_insensitive(self):
        """测试配置获取大小写不敏感"""
        config_upper = get_product_config('IF')
        config_lower = get_product_config('if')
        config_mixed = get_product_config('If')
        
        assert config_upper is not None
        assert config_lower is not None
        assert config_mixed is not None
        assert config_upper.code == config_lower.code == config_mixed.code
    
    def test_get_product_config_not_found(self):
        """测试获取不存在的品种配置"""
        config = get_product_config('UNKNOWN')
        assert config is None
    
    def test_extract_product_code(self):
        """测试从合约代码提取品种代码"""
        # 股指期货
        assert extract_product_code('IF2401') == 'IF'
        assert extract_product_code('IC2402') == 'IC'
        assert extract_product_code('IH2403') == 'IH'
        assert extract_product_code('IM2404') == 'IM'
        
        # 商品期货
        assert extract_product_code('CU2401') == 'CU'
        assert extract_product_code('AL2402') == 'AL'
        assert extract_product_code('RB2403') == 'RB'
        
        # 国债期货
        assert extract_product_code('T2401') == 'T'
        assert extract_product_code('TF2402') == 'TF'
        assert extract_product_code('TS2403') == 'TS'
    
    def test_extract_product_code_case_insensitive(self):
        """测试提取品种代码大小写不敏感"""
        assert extract_product_code('if2401') == 'IF'
        assert extract_product_code('If2401') == 'IF'
        assert extract_product_code('IF2401') == 'IF'
    
    def test_all_products_have_required_fields(self):
        """测试所有品种配置都有必需字段"""
        for code, config in FUTURE_PRODUCTS.items():
            assert config.code == code
            assert config.name is not None
            assert config.future_type in FutureType
            assert config.contract_multiplier > 0
            assert config.tick_size > 0
            assert config.expiry_day_threshold > 0
            assert 0 < config.volume_threshold_ratio < 1
    
    def test_future_type_enum(self):
        """测试期货类型枚举"""
        assert FutureType.STOCK_INDEX.value == "stock_index"
        assert FutureType.COMMODITY.value == "commodity"
        assert FutureType.TREASURY.value == "treasury"
    
    def test_product_config_dataclass(self):
        """测试品种配置数据类"""
        config = FutureProductConfig(
            code='TEST',
            name='测试期货',
            future_type=FutureType.COMMODITY,
            contract_multiplier=10,
            tick_size=1.0,
            expiry_day_threshold=5,
            volume_threshold_ratio=0.15
        )
        
        assert config.code == 'TEST'
        assert config.name == '测试期货'
        assert config.future_type == FutureType.COMMODITY
        assert config.contract_multiplier == 10
        assert config.tick_size == 1.0
        assert config.expiry_day_threshold == 5
        assert config.volume_threshold_ratio == 0.15
    
    def test_product_config_default_values(self):
        """测试品种配置默认值"""
        config = FutureProductConfig(
            code='TEST',
            name='测试期货',
            future_type=FutureType.COMMODITY,
            contract_multiplier=10,
            tick_size=1.0
        )
        
        # 验证默认值
        assert config.expiry_day_threshold == 7
        assert config.volume_threshold_ratio == 0.2
