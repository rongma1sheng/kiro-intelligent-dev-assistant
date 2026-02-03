"""Unit tests for FeaturePrioritizer

白皮书依据: 第十五章 15.0 功能完善路线图

测试覆盖:
- 功能优先级排序
- 业务价值计算
- 优先级汇总
- 功能推荐
"""

import pytest
from src.planning.feature_prioritizer import (
    FeaturePrioritizer,
    Feature,
    PriorityLevel
)


class TestFeaturePrioritizer:
    """FeaturePrioritizer单元测试"""
    
    @pytest.fixture
    def prioritizer(self):
        """创建FeaturePrioritizer实例"""
        return FeaturePrioritizer()
    
    @pytest.fixture
    def sample_features(self):
        """创建示例功能列表"""
        return [
            Feature(
                name="LockBox实体化",
                description="真实GC001交易",
                impact=9.0,
                urgency=8.0,
                cost=3.0,
                risk=2.0,
                priority=PriorityLevel.P1
            ),
            Feature(
                name="WebSocket推流",
                description="60Hz雷达数据",
                impact=7.0,
                urgency=6.0,
                cost=4.0,
                risk=3.0,
                priority=PriorityLevel.P1
            ),
            Feature(
                name="日志轮转",
                description="自动日志管理",
                impact=5.0,
                urgency=4.0,
                cost=2.0,
                risk=1.0,
                priority=PriorityLevel.P2
            ),
            Feature(
                name="末日开关",
                description="紧急停止",
                impact=10.0,
                urgency=10.0,
                cost=1.0,
                risk=1.0,
                priority=PriorityLevel.P0
            )
        ]
    
    # 初始化测试
    def test_init_default_weights(self):
        """测试默认权重"""
        prioritizer = FeaturePrioritizer()
        
        assert prioritizer.impact_weight == 0.4
        assert prioritizer.urgency_weight == 0.3
        assert prioritizer.cost_weight == 0.2
        assert prioritizer.risk_weight == 0.1
    
    def test_init_custom_weights(self):
        """测试自定义权重"""
        prioritizer = FeaturePrioritizer(
            impact_weight=0.5,
            urgency_weight=0.2,
            cost_weight=0.2,
            risk_weight=0.1
        )
        
        assert prioritizer.impact_weight == 0.5
        assert prioritizer.urgency_weight == 0.2
        assert prioritizer.cost_weight == 0.2
        assert prioritizer.risk_weight == 0.1
    
    def test_init_invalid_weights_sum(self):
        """测试权重之和不等于1.0"""
        with pytest.raises(ValueError, match="权重之和必须等于1.0"):
            FeaturePrioritizer(
                impact_weight=0.5,
                urgency_weight=0.3,
                cost_weight=0.3,
                risk_weight=0.1
            )
    
    # 业务价值计算测试
    def test_calculate_business_value_default_weights(self, prioritizer):
        """测试默认权重下的业务价值计算"""
        feature = Feature(
            name="Test",
            description="Test feature",
            impact=8.0,
            urgency=6.0,
            cost=4.0,
            risk=2.0
        )
        
        value = prioritizer.calculate_business_value(feature)
        
        # 8*0.4 + 6*0.3 - 4*0.2 - 2*0.1 = 3.2 + 1.8 - 0.8 - 0.2 = 4.0
        assert value == pytest.approx(4.0, rel=1e-6)
    
    def test_calculate_business_value_high_impact(self, prioritizer):
        """测试高影响力功能"""
        feature = Feature(
            name="High Impact",
            description="High impact feature",
            impact=10.0,
            urgency=5.0,
            cost=2.0,
            risk=1.0
        )
        
        value = prioritizer.calculate_business_value(feature)
        
        # 10*0.4 + 5*0.3 - 2*0.2 - 1*0.1 = 4.0 + 1.5 - 0.4 - 0.1 = 5.0
        assert value == pytest.approx(5.0, rel=1e-6)
    
    def test_calculate_business_value_high_cost(self, prioritizer):
        """测试高成本功能"""
        feature = Feature(
            name="High Cost",
            description="High cost feature",
            impact=5.0,
            urgency=5.0,
            cost=10.0,
            risk=5.0
        )
        
        value = prioritizer.calculate_business_value(feature)
        
        # 5*0.4 + 5*0.3 - 10*0.2 - 5*0.1 = 2.0 + 1.5 - 2.0 - 0.5 = 1.0
        assert value == pytest.approx(1.0, rel=1e-6)
    
    def test_calculate_business_value_negative(self, prioritizer):
        """测试负业务价值"""
        feature = Feature(
            name="Negative Value",
            description="Negative value feature",
            impact=1.0,
            urgency=1.0,
            cost=10.0,
            risk=10.0
        )
        
        value = prioritizer.calculate_business_value(feature)
        
        # 1*0.4 + 1*0.3 - 10*0.2 - 10*0.1 = 0.4 + 0.3 - 2.0 - 1.0 = -2.3
        assert value == pytest.approx(-2.3, rel=1e-6)
    
    def test_calculate_business_value_invalid_impact(self, prioritizer):
        """测试无效的影响力评分"""
        feature = Feature(
            name="Invalid",
            description="Invalid feature",
            impact=11.0,  # 超出范围
            urgency=5.0,
            cost=5.0,
            risk=5.0
        )
        
        with pytest.raises(ValueError, match="impact评分必须在\\[1, 10\\]范围内"):
            prioritizer.calculate_business_value(feature)
    
    def test_calculate_business_value_invalid_urgency(self, prioritizer):
        """测试无效的紧急度评分"""
        feature = Feature(
            name="Invalid",
            description="Invalid feature",
            impact=5.0,
            urgency=0.0,  # 超出范围
            cost=5.0,
            risk=5.0
        )
        
        with pytest.raises(ValueError, match="urgency评分必须在\\[1, 10\\]范围内"):
            prioritizer.calculate_business_value(feature)
    
    # 功能排序测试
    def test_prioritize_features_by_priority_level(self, prioritizer, sample_features):
        """测试按优先级级别排序"""
        sorted_features = prioritizer.prioritize_features(sample_features)
        
        # P0应该在最前面
        assert sorted_features[0].priority == PriorityLevel.P0
        assert sorted_features[0].name == "末日开关"
        
        # P1其次
        assert sorted_features[1].priority == PriorityLevel.P1
        assert sorted_features[2].priority == PriorityLevel.P1
        
        # P2最后
        assert sorted_features[3].priority == PriorityLevel.P2
    
    def test_prioritize_features_by_business_value(self, prioritizer):
        """测试同优先级内按业务价值排序"""
        features = [
            Feature(
                name="Feature A",
                description="A",
                impact=8.0,
                urgency=6.0,
                cost=3.0,
                risk=2.0,
                priority=PriorityLevel.P1
            ),
            Feature(
                name="Feature B",
                description="B",
                impact=9.0,
                urgency=7.0,
                cost=2.0,
                risk=1.0,
                priority=PriorityLevel.P1
            ),
            Feature(
                name="Feature C",
                description="C",
                impact=7.0,
                urgency=5.0,
                cost=4.0,
                risk=3.0,
                priority=PriorityLevel.P1
            )
        ]
        
        sorted_features = prioritizer.prioritize_features(features)
        
        # Feature B应该在最前面（业务价值最高）
        assert sorted_features[0].name == "Feature B"
        # Feature A其次
        assert sorted_features[1].name == "Feature A"
        # Feature C最后
        assert sorted_features[2].name == "Feature C"
    
    def test_prioritize_features_empty_list(self, prioritizer):
        """测试空功能列表"""
        with pytest.raises(ValueError, match="功能列表不能为空"):
            prioritizer.prioritize_features([])
    
    def test_prioritize_features_single_feature(self, prioritizer):
        """测试单个功能"""
        features = [
            Feature(
                name="Single",
                description="Single feature",
                impact=5.0,
                urgency=5.0,
                cost=5.0,
                risk=5.0,
                priority=PriorityLevel.P1
            )
        ]
        
        sorted_features = prioritizer.prioritize_features(features)
        
        assert len(sorted_features) == 1
        assert sorted_features[0].name == "Single"
    
    # 优先级汇总测试
    def test_get_priority_summary(self, prioritizer, sample_features):
        """测试获取优先级汇总"""
        summary = prioritizer.get_priority_summary(sample_features)
        
        assert summary['total_count'] == 4
        assert summary['p0_count'] == 1
        assert summary['p1_count'] == 2
        assert summary['p2_count'] == 1
        assert summary['p3_count'] == 0
        assert 'avg_business_value' in summary
        assert len(summary['top_features']) == 4
    
    def test_get_priority_summary_empty_list(self, prioritizer):
        """测试空列表汇总"""
        summary = prioritizer.get_priority_summary([])
        
        assert summary['total_count'] == 0
        assert summary['p0_count'] == 0
        assert summary['avg_business_value'] == 0.0
        assert summary['top_features'] == []
    
    def test_get_priority_summary_top_features_limit(self, prioritizer):
        """测试top功能数量限制"""
        features = [
            Feature(
                name=f"Feature {i}",
                description=f"Feature {i}",
                impact=5.0,
                urgency=5.0,
                cost=5.0,
                risk=5.0,
                priority=PriorityLevel.P1
            )
            for i in range(10)
        ]
        
        summary = prioritizer.get_priority_summary(features)
        
        # 应该只返回前5个
        assert len(summary['top_features']) == 5
    
    # 功能推荐测试
    def test_recommend_next_features(self, prioritizer, sample_features):
        """测试推荐下一批功能"""
        recommended = prioritizer.recommend_next_features(
            sample_features,
            count=2
        )
        
        assert len(recommended) == 2
        # 第一个应该是P0
        assert recommended[0].priority == PriorityLevel.P0
        # 第二个应该是P1中业务价值最高的
        assert recommended[1].priority == PriorityLevel.P1
    
    def test_recommend_next_features_default_count(self, prioritizer, sample_features):
        """测试默认推荐数量"""
        recommended = prioritizer.recommend_next_features(sample_features)
        
        assert len(recommended) == 3
    
    def test_recommend_next_features_more_than_available(self, prioritizer, sample_features):
        """测试推荐数量超过可用数量"""
        recommended = prioritizer.recommend_next_features(
            sample_features,
            count=10
        )
        
        # 应该返回所有功能
        assert len(recommended) == 4
    
    def test_recommend_next_features_empty_list(self, prioritizer):
        """测试空列表推荐"""
        recommended = prioritizer.recommend_next_features([])
        
        assert recommended == []
    
    # 边界条件测试
    def test_all_same_priority(self, prioritizer):
        """测试所有功能同优先级"""
        features = [
            Feature(
                name=f"Feature {i}",
                description=f"Feature {i}",
                impact=float(10 - i),
                urgency=5.0,
                cost=5.0,
                risk=5.0,
                priority=PriorityLevel.P1
            )
            for i in range(5)
        ]
        
        sorted_features = prioritizer.prioritize_features(features)
        
        # 应该按业务价值降序排序
        for i in range(len(sorted_features) - 1):
            assert (sorted_features[i].business_value >=
                   sorted_features[i + 1].business_value)
    
    def test_all_different_priorities(self, prioritizer):
        """测试所有功能不同优先级"""
        features = [
            Feature(
                name="P3 Feature",
                description="P3",
                impact=10.0,
                urgency=10.0,
                cost=1.0,
                risk=1.0,
                priority=PriorityLevel.P3
            ),
            Feature(
                name="P0 Feature",
                description="P0",
                impact=5.0,
                urgency=5.0,
                cost=5.0,
                risk=5.0,
                priority=PriorityLevel.P0
            ),
            Feature(
                name="P2 Feature",
                description="P2",
                impact=8.0,
                urgency=8.0,
                cost=2.0,
                risk=2.0,
                priority=PriorityLevel.P2
            ),
            Feature(
                name="P1 Feature",
                description="P1",
                impact=7.0,
                urgency=7.0,
                cost=3.0,
                risk=3.0,
                priority=PriorityLevel.P1
            )
        ]
        
        sorted_features = prioritizer.prioritize_features(features)
        
        # 应该按P0, P1, P2, P3顺序
        assert sorted_features[0].priority == PriorityLevel.P0
        assert sorted_features[1].priority == PriorityLevel.P1
        assert sorted_features[2].priority == PriorityLevel.P2
        assert sorted_features[3].priority == PriorityLevel.P3
    
    # 自定义权重测试
    def test_custom_weights_impact_dominant(self):
        """测试影响力主导的权重"""
        prioritizer = FeaturePrioritizer(
            impact_weight=0.7,
            urgency_weight=0.1,
            cost_weight=0.1,
            risk_weight=0.1
        )
        
        feature = Feature(
            name="High Impact",
            description="High impact feature",
            impact=10.0,
            urgency=1.0,
            cost=1.0,
            risk=1.0
        )
        
        value = prioritizer.calculate_business_value(feature)
        
        # 10*0.7 + 1*0.1 - 1*0.1 - 1*0.1 = 7.0 + 0.1 - 0.1 - 0.1 = 6.9
        assert value == pytest.approx(6.9, rel=1e-6)
    
    def test_custom_weights_urgency_dominant(self):
        """测试紧急度主导的权重"""
        prioritizer = FeaturePrioritizer(
            impact_weight=0.1,
            urgency_weight=0.7,
            cost_weight=0.1,
            risk_weight=0.1
        )
        
        feature = Feature(
            name="High Urgency",
            description="High urgency feature",
            impact=1.0,
            urgency=10.0,
            cost=1.0,
            risk=1.0
        )
        
        value = prioritizer.calculate_business_value(feature)
        
        # 1*0.1 + 10*0.7 - 1*0.1 - 1*0.1 = 0.1 + 7.0 - 0.1 - 0.1 = 6.9
        assert value == pytest.approx(6.9, rel=1e-6)
