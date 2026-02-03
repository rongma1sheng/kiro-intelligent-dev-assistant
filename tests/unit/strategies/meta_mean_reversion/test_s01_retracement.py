# -*- coding: utf-8 -*-
"""S01 Retracement Strategy Tests

Test Coverage Target: 100%
Strategy: Strong stock retracement (回马枪)
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.strategies.meta_mean_reversion.s01_retracement import S01RetracementStrategy
from src.strategies.data_models import Position, Signal, StrategyConfig
from src.strategies.base_strategy import Strategy


def create_test_config() -> StrategyConfig:
    """Create test StrategyConfig"""
    return StrategyConfig(
        strategy_name="S01_Test",
        capital_tier="tier1_micro",
        max_position=0.20,
        max_single_stock=0.05,
        max_industry=0.30,
        stop_loss_pct=-0.08,
        take_profit_pct=0.15,
        trailing_stop_enabled=False,
    )


class TestS01RetracementInitialization:
    """Test S01 strategy initialization"""

    def test_initialization(self):
        """Test strategy initialization"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        assert strategy.name == "S01_Retracement"
        assert strategy.strong_stock_threshold == 0.20
        assert strategy.lookback_period == 20
        assert strategy.ma_periods == [10, 20]
        assert strategy.volume_shrink_threshold == 0.6
        assert strategy.retracement_threshold == 0.10


class TestGenerateSignals:
    """Test signal generation"""

    @pytest.mark.asyncio
    async def test_generate_signals_with_valid_data(self):
        """Test signal generation with valid data"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        market_data = {
            "symbols": ["000001"],
            "prices": {
                "000001": {
                    "close": 10.8,  # 回调10%
                    "high_20d": 12.0,
                    "low_20d": 8.0,
                    "close_20d_ago": 8.0,
                }
            },
            "volumes": {
                "000001": {
                    "volume": 5000000,
                    "avg_volume_20d": 10000000,
                }
            },
            "indicators": {
                "000001": {
                    "ma_10": 10.8,
                    "ma_20": 9.5,
                }
            },
        }

        signals = await strategy.generate_signals(market_data)

        assert len(signals) >= 1
        assert all(isinstance(s, Signal) for s in signals)
        assert all(s.action == "buy" for s in signals)
        assert all(0.5 <= s.confidence <= 0.90 for s in signals)

    @pytest.mark.asyncio
    async def test_generate_signals_filters_weak_stocks(self):
        """Test filtering weak stocks"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        market_data = {
            "symbols": ["000001"],
            "prices": {
                "000001": {
                    "close": 10.0,
                    "high_20d": 10.5,
                    "low_20d": 9.5,
                    "close_20d_ago": 9.5,
                }
            },
            "volumes": {"000001": {"volume": 5000000, "avg_volume_20d": 10000000}},
            "indicators": {"000001": {"ma_10": 10.1, "ma_20": 9.5}},
        }

        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_filters_not_near_ma(self):
        """Test filtering stocks not near MA"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        market_data = {
            "symbols": ["000001"],
            "prices": {
                "000001": {
                    "close": 10.0,
                    "high_20d": 12.0,
                    "low_20d": 8.0,
                    "close_20d_ago": 8.0,
                }
            },
            "volumes": {"000001": {"volume": 5000000, "avg_volume_20d": 10000000}},
            "indicators": {"000001": {"ma_10": 11.0, "ma_20": 11.5}},
        }

        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_filters_high_volume(self):
        """Test filtering high volume"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        market_data = {
            "symbols": ["000001"],
            "prices": {
                "000001": {
                    "close": 10.0,
                    "high_20d": 12.0,
                    "low_20d": 8.0,
                    "close_20d_ago": 8.0,
                }
            },
            "volumes": {"000001": {"volume": 15000000, "avg_volume_20d": 10000000}},
            "indicators": {"000001": {"ma_10": 10.1, "ma_20": 9.5}},
        }

        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_filters_unreasonable_retracement(self):
        """Test filtering unreasonable retracement"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        market_data = {
            "symbols": ["000001"],
            "prices": {
                "000001": {
                    "close": 11.5,
                    "high_20d": 12.0,
                    "low_20d": 8.0,
                    "close_20d_ago": 8.0,
                }
            },
            "volumes": {"000001": {"volume": 5000000, "avg_volume_20d": 10000000}},
            "indicators": {"000001": {"ma_10": 11.5, "ma_20": 10.5}},
        }

        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_with_empty_data(self):
        """Test with empty data"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        market_data = {"symbols": []}
        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_exception_handling(self):
        """Test exception handling"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        market_data = {
            "symbols": ["000001"],
            "prices": {"000001": {"close": 10.0}},
            "volumes": {},
            "indicators": {},
        }

        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 0


class TestAnalyzeRetracement:
    """Test retracement analysis"""

    @pytest.mark.asyncio
    async def test_analyze_retracement_near_ma10(self):
        """Test analysis near MA10"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        price_data = {
            "close": 10.8,  # 回调10%，在合理范围内
            "high_20d": 12.0,
            "low_20d": 8.0,
            "close_20d_ago": 8.0,
        }
        volume_data = {"volume": 5000000, "avg_volume_20d": 10000000}
        indicator_data = {"ma_10": 10.8, "ma_20": 9.0}

        signal = await strategy._analyze_retracement("000001", price_data, volume_data, indicator_data)

        assert signal is not None
        assert signal.symbol == "000001"
        assert signal.action == "buy"
        assert 0.5 <= signal.confidence <= 0.90
        assert "MA10" in signal.reason

    @pytest.mark.asyncio
    async def test_analyze_retracement_near_ma20(self):
        """Test analysis near MA20"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        price_data = {
            "close": 10.8,  # 回调10%
            "high_20d": 12.0,
            "low_20d": 8.0,
            "close_20d_ago": 8.0,
        }
        volume_data = {"volume": 5000000, "avg_volume_20d": 10000000}
        indicator_data = {"ma_10": 11.5, "ma_20": 10.8}

        signal = await strategy._analyze_retracement("000001", price_data, volume_data, indicator_data)

        assert signal is not None
        assert "MA20" in signal.reason

    @pytest.mark.asyncio
    async def test_analyze_retracement_invalid_price(self):
        """Test with invalid price"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        price_data = {
            "close": 0,
            "high_20d": 12.0,
            "low_20d": 8.0,
            "close_20d_ago": 8.0,
        }
        volume_data = {"volume": 5000000, "avg_volume_20d": 10000000}
        indicator_data = {"ma_10": 10.1, "ma_20": 9.5}

        signal = await strategy._analyze_retracement("000001", price_data, volume_data, indicator_data)
        assert signal is None

    @pytest.mark.asyncio
    async def test_analyze_retracement_zero_low_20d(self):
        """Test with zero low_20d"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        price_data = {
            "close": 10.0,
            "high_20d": 12.0,
            "low_20d": 0,
            "close_20d_ago": 8.0,
        }
        volume_data = {"volume": 5000000, "avg_volume_20d": 10000000}
        indicator_data = {"ma_10": 10.1, "ma_20": 9.5}

        signal = await strategy._analyze_retracement("000001", price_data, volume_data, indicator_data)
        assert signal is None


class TestCalculateRetracementConfidence:
    """Test confidence calculation"""

    def test_calculate_confidence_optimal_retracement(self):
        """Test optimal retracement confidence"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        confidence = strategy._calculate_retracement_confidence(
            gain_20d=0.30, retracement=0.06, volume_ratio=0.4, near_ma10=True, near_ma20=False
        )

        assert 0.70 <= confidence <= 0.90

    def test_calculate_confidence_medium_retracement(self):
        """Test medium retracement confidence"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        confidence = strategy._calculate_retracement_confidence(
            gain_20d=0.25, retracement=0.09, volume_ratio=0.5, near_ma10=False, near_ma20=True
        )

        assert 0.60 <= confidence <= 0.90

    def test_calculate_confidence_weak_signal(self):
        """Test weak signal confidence"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        confidence = strategy._calculate_retracement_confidence(
            gain_20d=0.20, retracement=0.10, volume_ratio=0.59, near_ma10=False, near_ma20=True
        )

        assert 0.50 <= confidence <= 0.90

    def test_calculate_confidence_minimum_threshold(self):
        """Test minimum confidence threshold"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        confidence = strategy._calculate_retracement_confidence(
            gain_20d=0.20, retracement=0.10, volume_ratio=0.6, near_ma10=False, near_ma20=True
        )

        assert confidence >= 0.5

    def test_calculate_confidence_maximum_cap(self):
        """Test maximum confidence cap"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        confidence = strategy._calculate_retracement_confidence(
            gain_20d=1.0, retracement=0.05, volume_ratio=0.1, near_ma10=True, near_ma20=False
        )

        assert confidence <= 0.90

    def test_calculate_confidence_ma10_vs_ma20(self):
        """Test MA10 vs MA20 scoring"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        confidence_ma10 = strategy._calculate_retracement_confidence(
            gain_20d=0.25, retracement=0.07, volume_ratio=0.5, near_ma10=True, near_ma20=False
        )

        confidence_ma20 = strategy._calculate_retracement_confidence(
            gain_20d=0.25, retracement=0.07, volume_ratio=0.5, near_ma10=False, near_ma20=True
        )

        # Both hit the 0.90 cap, so test with lower values
        confidence_ma10_lower = strategy._calculate_retracement_confidence(
            gain_20d=0.22, retracement=0.08, volume_ratio=0.55, near_ma10=True, near_ma20=False
        )

        confidence_ma20_lower = strategy._calculate_retracement_confidence(
            gain_20d=0.22, retracement=0.08, volume_ratio=0.55, near_ma10=False, near_ma20=True
        )

        assert confidence_ma10_lower > confidence_ma20_lower


class TestCalculatePositionSizes:
    """Test position size calculation"""

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_signals(self):
        """Test basic position calculation"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        signals = [
            Signal(symbol="000001", action="buy", confidence=0.80, timestamp="2024-01-01", reason="test"),
            Signal(symbol="000002", action="buy", confidence=0.70, timestamp="2024-01-01", reason="test"),
        ]

        positions = await strategy.calculate_position_sizes(signals)

        assert len(positions) == 2
        assert all(isinstance(p, Position) for p in positions)
        assert all(p.size > 0 for p in positions)
        assert sum(p.size for p in positions) <= strategy.max_position

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_respects_max_position(self):
        """Test max position limit"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        signals = [
            Signal(symbol=f"00000{i}", action="buy", confidence=0.80, timestamp="2024-01-01", reason="test")
            for i in range(1, 10)
        ]

        positions = await strategy.calculate_position_sizes(signals)

        total_position = sum(p.size for p in positions)
        assert total_position <= strategy.max_position

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_empty_signals(self):
        """Test with empty signals"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        positions = await strategy.calculate_position_sizes([])
        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_filters_sell_signals(self):
        """Test filtering sell signals"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        signals = [
            Signal(symbol="000001", action="buy", confidence=0.80, timestamp="2024-01-01", reason="test"),
            Signal(symbol="000002", action="sell", confidence=0.70, timestamp="2024-01-01", reason="test"),
        ]

        positions = await strategy.calculate_position_sizes(signals)

        assert len(positions) == 1
        assert positions[0].symbol == "000001"

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_confidence_affects_size(self):
        """Test confidence affects position size"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        signals = [
            Signal(symbol="000001", action="buy", confidence=0.85, timestamp="2024-01-01", reason="test"),
            Signal(symbol="000002", action="buy", confidence=0.60, timestamp="2024-01-01", reason="test"),
        ]

        positions = await strategy.calculate_position_sizes(signals)
        assert positions[0].size > positions[1].size

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_stops_at_minimum(self):
        """Test stops at minimum position"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        signals = [
            Signal(symbol=f"00000{i}", action="buy", confidence=0.50, timestamp="2024-01-01", reason="test")
            for i in range(1, 20)
        ]

        positions = await strategy.calculate_position_sizes(signals)
        assert all(p.size >= 0.01 for p in positions)


class TestEdgeCases:
    """Test edge cases"""

    @pytest.mark.asyncio
    async def test_generate_signals_with_missing_keys(self):
        """Test with missing keys"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        market_data = {
            "symbols": ["000001"],
            "prices": {"000001": {"close": 10.0}},
        }

        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 0

    def test_calculate_confidence_with_zero_values(self):
        """Test confidence with zero values"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        confidence = strategy._calculate_retracement_confidence(
            gain_20d=0.20, retracement=0.07, volume_ratio=0.5, near_ma10=False, near_ma20=False
        )

        assert 0.5 <= confidence <= 0.90

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_position_price(self):
        """Test position price setting"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        signals = [
            Signal(symbol="000001", action="buy", confidence=0.80, timestamp="2024-01-01", reason="test"),
        ]

        positions = await strategy.calculate_position_sizes(signals)

        # Fixed: Now uses 100.0 placeholder price
        assert positions[0].entry_price == 100.0
        assert positions[0].current_price == 100.0

    @pytest.mark.asyncio
    async def test_analyze_retracement_with_zero_ma(self):
        """Test with zero MA values"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        price_data = {
            "close": 10.0,
            "high_20d": 12.0,
            "low_20d": 8.0,
            "close_20d_ago": 8.0,
        }
        volume_data = {"volume": 5000000, "avg_volume_20d": 10000000}
        indicator_data = {"ma_10": 0, "ma_20": 0}

        signal = await strategy._analyze_retracement("000001", price_data, volume_data, indicator_data)
        assert signal is None

    @pytest.mark.asyncio
    async def test_analyze_retracement_with_zero_avg_volume(self):
        """Test with zero average volume"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        price_data = {
            "close": 10.0,
            "high_20d": 12.0,
            "low_20d": 8.0,
            "close_20d_ago": 8.0,
        }
        volume_data = {"volume": 5000000, "avg_volume_20d": 0}
        indicator_data = {"ma_10": 10.1, "ma_20": 9.5}

        signal = await strategy._analyze_retracement("000001", price_data, volume_data, indicator_data)
        assert signal is None

    @pytest.mark.asyncio
    async def test_analyze_retracement_with_zero_high_20d(self):
        """Test with zero high_20d"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        price_data = {
            "close": 10.0,
            "high_20d": 0,
            "low_20d": 8.0,
            "close_20d_ago": 8.0,
        }
        volume_data = {"volume": 5000000, "avg_volume_20d": 10000000}
        indicator_data = {"ma_10": 10.1, "ma_20": 9.5}

        signal = await strategy._analyze_retracement("000001", price_data, volume_data, indicator_data)
        assert signal is None

    @pytest.mark.asyncio
    async def test_generate_signals_logs_exception(self):
        """Test exception logging in signal generation"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        # Mock _analyze_retracement to raise exception
        with patch.object(strategy, '_analyze_retracement', side_effect=Exception("Test error")):
            market_data = {
                "symbols": ["000001"],
                "prices": {"000001": {"close": 10.0}},
                "volumes": {"000001": {}},
                "indicators": {"000001": {}},
            }

            signals = await strategy.generate_signals(market_data)
            
            # Exception is caught and logged, returns empty list
            assert len(signals) == 0

    def test_calculate_confidence_retracement_else_branch(self):
        """Test retracement score else branch"""
        config = create_test_config()
        strategy = S01RetracementStrategy(config)

        # Test retracement > 0.10 (else branch)
        confidence = strategy._calculate_retracement_confidence(
            gain_20d=0.25, retracement=0.11, volume_ratio=0.5, near_ma10=True, near_ma20=False
        )

        assert 0.5 <= confidence <= 0.90
