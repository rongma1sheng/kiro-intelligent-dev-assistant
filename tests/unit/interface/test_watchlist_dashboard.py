"""重点关注仪表盘单元测试

白皮书依据: 附录A 全息指挥台 - 6. 重点关注 (Watchlist)
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from src.interface.watchlist_dashboard import (
    WatchlistDashboard,
    CorePoolStock,
    WatchlistStock,
    SectorHeat,
    RankingType
)


class TestRankingType:
    """RankingType枚举测试"""
    
    def test_ranking_type_values(self):
        """测试排名类型值"""
        assert RankingType.SOLDIER.value == "Soldier评分"
        assert RankingType.COMMANDER.value == "Commander评分"
        assert RankingType.COMBINED.value == "综合评分"


class TestCorePoolStock:
    """CorePoolStock数据模型测试"""
    
    def test_creation(self):
        """测试创建核心池股票"""
        stock = CorePoolStock(
            rank=1,
            symbol="000001",
            name="平安银行",
            score=92.5,
            price=12.50,
            change_pct=2.35,
            ranking_type=RankingType.COMBINED
        )
        
        assert stock.rank == 1
        assert stock.symbol == "000001"
        assert stock.score == 92.5
        assert stock.ranking_type == RankingType.COMBINED
    
    def test_to_dict(self):
        """测试转换为字典"""
        stock = CorePoolStock(
            rank=1,
            symbol="000001",
            name="平安银行",
            score=90.0,
            price=12.00,
            change_pct=1.5
        )
        
        result = stock.to_dict()
        
        assert isinstance(result, dict)
        assert result['rank'] == 1
        assert result['score'] == 90.0
    
    def test_default_ranking_type(self):
        """测试默认排名类型"""
        stock = CorePoolStock(
            rank=1,
            symbol="000001",
            name="平安银行",
            score=90.0,
            price=12.00,
            change_pct=1.5
        )
        
        assert stock.ranking_type == RankingType.COMBINED


class TestWatchlistStock:
    """WatchlistStock数据模型测试"""
    
    def test_creation(self):
        """测试创建自选股"""
        stock = WatchlistStock(
            symbol="000001",
            name="平安银行",
            price=12.50,
            change_pct=2.35,
            group="重点",
            sort_order=1,
            added_time=datetime.now()
        )
        
        assert stock.symbol == "000001"
        assert stock.group == "重点"
        assert stock.sort_order == 1
    
    def test_to_dict(self):
        """测试转换为字典"""
        stock = WatchlistStock(
            symbol="000001",
            name="平安银行",
            price=12.00,
            change_pct=1.5,
            group="默认"
        )
        
        result = stock.to_dict()
        
        assert isinstance(result, dict)
        assert result['symbol'] == "000001"
        assert result['group'] == "默认"
    
    def test_default_values(self):
        """测试默认值"""
        stock = WatchlistStock(
            symbol="000001",
            name="平安银行",
            price=12.00,
            change_pct=1.5
        )
        
        assert stock.group == "默认"
        assert stock.sort_order == 0
        assert stock.added_time is None


class TestSectorHeat:
    """SectorHeat数据模型测试"""
    
    def test_creation(self):
        """测试创建板块热度"""
        sector = SectorHeat(
            sector_name="银行",
            sector_type="行业",
            heat_score=95,
            change_pct=2.35,
            money_flow=15.5,
            sentiment_score=82
        )
        
        assert sector.sector_name == "银行"
        assert sector.sector_type == "行业"
        assert sector.heat_score == 95
        assert sector.money_flow == 15.5
    
    def test_to_dict(self):
        """测试转换为字典"""
        sector = SectorHeat(
            sector_name="银行",
            sector_type="行业",
            heat_score=90,
            change_pct=2.0
        )
        
        result = sector.to_dict()
        
        assert isinstance(result, dict)
        assert result['sector_name'] == "银行"
        assert result['heat_score'] == 90
    
    def test_default_values(self):
        """测试默认值"""
        sector = SectorHeat(
            sector_name="银行",
            sector_type="行业",
            heat_score=90,
            change_pct=2.0
        )
        
        assert sector.money_flow == 0.0
        assert sector.sentiment_score == 0.0


class TestWatchlistDashboard:
    """WatchlistDashboard测试"""
    
    @pytest.fixture
    def dashboard(self):
        """创建测试实例"""
        return WatchlistDashboard()
    
    @pytest.fixture
    def dashboard_with_redis(self):
        """创建带Redis的测试实例"""
        mock_redis = Mock()
        return WatchlistDashboard(redis_client=mock_redis)
    
    def test_init_default(self, dashboard):
        """测试默认初始化"""
        assert dashboard.redis_client is None
    
    def test_init_with_redis(self):
        """测试带Redis初始化"""
        mock_redis = Mock()
        dashboard = WatchlistDashboard(redis_client=mock_redis)
        
        assert dashboard.redis_client is mock_redis
    
    def test_color_scheme(self, dashboard):
        """测试色彩方案"""
        assert 'rise' in dashboard.COLOR_SCHEME
        assert 'fall' in dashboard.COLOR_SCHEME
        assert dashboard.COLOR_SCHEME['rise'] == '#FF4D4F'
        assert dashboard.COLOR_SCHEME['fall'] == '#52C41A'
    
    def test_get_core_pool_mock(self, dashboard):
        """测试获取核心池（模拟数据）"""
        stocks = dashboard.get_core_pool(RankingType.COMBINED, 20)
        
        assert isinstance(stocks, list)
        assert len(stocks) == 20
        assert all(isinstance(s, CorePoolStock) for s in stocks)
    
    def test_get_core_pool_limit(self, dashboard):
        """测试核心池数量限制"""
        stocks = dashboard.get_core_pool(RankingType.SOLDIER, 10)
        
        assert len(stocks) == 10
    
    def test_get_core_pool_ranking_types(self, dashboard):
        """测试不同排名类型"""
        for ranking_type in RankingType:
            stocks = dashboard.get_core_pool(ranking_type, 5)
            assert all(s.ranking_type == ranking_type for s in stocks)
    
    def test_get_watchlist_mock(self, dashboard):
        """测试获取自选股（模拟数据）"""
        stocks = dashboard.get_watchlist()
        
        assert isinstance(stocks, list)
        assert len(stocks) > 0
        assert all(isinstance(s, WatchlistStock) for s in stocks)
    
    def test_get_watchlist_filter_group(self, dashboard):
        """测试按分组筛选自选股"""
        stocks = dashboard.get_watchlist(group="重点")
        
        for stock in stocks:
            assert stock.group == "重点"
    
    def test_add_to_watchlist(self, dashboard):
        """测试添加自选股"""
        result = dashboard.add_to_watchlist("000001", "平安银行", "重点")
        
        assert result['success'] is True
        assert result['symbol'] == "000001"
        assert result['group'] == "重点"
    
    def test_remove_from_watchlist(self, dashboard):
        """测试删除自选股"""
        result = dashboard.remove_from_watchlist("000001")
        
        assert result['success'] is True
        assert result['symbol'] == "000001"
    
    def test_get_sector_heatmap_mock(self, dashboard):
        """测试获取板块热力图（模拟数据）"""
        sectors = dashboard.get_sector_heatmap("行业")
        
        assert isinstance(sectors, list)
        assert len(sectors) > 0
        assert all(isinstance(s, SectorHeat) for s in sectors)
    
    def test_get_sector_heatmap_types(self, dashboard):
        """测试不同板块类型"""
        industry_sectors = dashboard.get_sector_heatmap("行业")
        concept_sectors = dashboard.get_sector_heatmap("概念")
        
        assert all(s.sector_type == "行业" for s in industry_sectors)
        assert all(s.sector_type == "概念" for s in concept_sectors)
    
    def test_get_sector_heatmap_sorted(self, dashboard):
        """测试板块按热度排序"""
        sectors = dashboard.get_sector_heatmap("行业")
        
        for i in range(len(sectors) - 1):
            assert sectors[i].heat_score >= sectors[i + 1].heat_score


class TestWatchlistDashboardRedis:
    """WatchlistDashboard Redis集成测试"""
    
    @pytest.fixture
    def mock_redis(self):
        """创建Mock Redis"""
        return Mock()
    
    @pytest.fixture
    def dashboard(self, mock_redis):
        """创建带Redis的测试实例"""
        return WatchlistDashboard(redis_client=mock_redis)
    
    def test_add_to_watchlist_with_redis(self, dashboard, mock_redis):
        """测试添加自选股（带Redis）"""
        result = dashboard.add_to_watchlist("000001", "平安银行", "重点")
        
        assert result['success'] is True
        mock_redis.hset.assert_called_once()
    
    def test_remove_from_watchlist_with_redis(self, dashboard, mock_redis):
        """测试删除自选股（带Redis）"""
        result = dashboard.remove_from_watchlist("000001")
        
        assert result['success'] is True
        mock_redis.hdel.assert_called_once()
    
    def test_redis_error_fallback(self, dashboard, mock_redis):
        """测试Redis错误时回退到模拟数据"""
        mock_redis.zrevrange.side_effect = Exception("Redis error")
        
        stocks = dashboard.get_core_pool(RankingType.COMBINED, 10)
        
        assert isinstance(stocks, list)
        assert len(stocks) > 0


class TestWatchlistDashboardEdgeCases:
    """WatchlistDashboard边界条件测试"""
    
    @pytest.fixture
    def dashboard(self):
        """创建测试实例"""
        return WatchlistDashboard()
    
    def test_empty_watchlist(self):
        """测试空自选股"""
        mock_redis = Mock()
        mock_redis.hgetall.return_value = {}
        dashboard = WatchlistDashboard(redis_client=mock_redis)
        
        stocks = dashboard.get_watchlist()
        
        # 空时回退到模拟数据
        assert isinstance(stocks, list)
    
    def test_negative_change_pct(self):
        """测试负涨跌幅"""
        stock = WatchlistStock(
            symbol="000001",
            name="平安银行",
            price=12.00,
            change_pct=-2.5
        )
        
        assert stock.change_pct < 0
    
    def test_sector_negative_money_flow(self):
        """测试负资金流向"""
        sector = SectorHeat(
            sector_name="房地产",
            sector_type="行业",
            heat_score=65,
            change_pct=-2.15,
            money_flow=-12.5
        )
        
        assert sector.money_flow < 0
