# -*- coding: utf-8 -*-
"""S13 Limit Down Reversal Strategy Tests

Test Coverage Target: 100%
Strategy: Limit down reversal (floor-to-ceiling board)
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.strategies.meta_momentum.s13_limit_down_reversal import S13LimitDownReversalStrategy
from src.strategies.data_models import Position, Signal, StrategyConfig
from src.strategies.base_strategy import Strategy


def create_test_config() -> StrategyConfig:
    """Create test StrategyConfig"""
    return StrategyConfig(
        strategy_name="S13_Test",
        capital_tier="tier1_micro",
        max_position=0.20,
        max_single_stock=0.05,
        max_industry=0.30,
        stop_loss_pct=-0.08,
        take_profit_pct=0.15,
        trailing_stop_enabled=False,
    )


class TestS13LimitDownReversalInitialization:
    """Test S13 strategy initialization"""

    def test_initialization(self):
        """Test strategy initialization"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        assert strategy.name == "S13_Limit_Down_Reversal"
        assert strategy.limit_down_threshold == -0.095
        assert strategy.open_threshold == -0.08
        assert strategy.volume_surge_threshold == 2.0
        assert strategy.bid_volume_ratio == 1.5
        assert strategy.max_single_position == 0.03
        assert strategy.max_total_position == 0.10
        assert strategy.strict_stop_loss == -0.05



class TestGenerateSignals:
    """Test signal generation"""

    @pytest.mark.asyncio
    async def test_generate_signals_with_valid_data(self):
        """Test signal generation with valid data"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        market_data = {
            "limit_down_stocks": {
                "000001": {
                    "price_change": -0.07,
                    "was_limit_down": True,
                    "is_open": True,
                    "open_time": "10:30:00",
                    "volume_ratio": 3.0,
                    "bid_ask_ratio": 2.0,
                    "reason": "bad news exhausted",
                },
            },
            "fundamentals": {
                "000001": {"is_st": False, "delisting_risk": False, "consecutive_loss_quarters": 0, "pe_ratio": 20, "pb_ratio": 2},
            },
            "news_sentiment": {
                "000001": {"negative_news_count": 1, "sentiment_score": 0.6},
            },
        }

        signals = await strategy.generate_signals(market_data)

        assert len(signals) <= 3
        assert all(isinstance(s, Signal) for s in signals)
        assert all(s.action == "buy" for s in signals)
        assert all(0.4 <= s.confidence <= 0.75 for s in signals)

    @pytest.mark.asyncio
    async def test_generate_signals_filters_not_limit_down(self):
        """Test filtering non-limit-down stocks"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        market_data = {
            "limit_down_stocks": {
                "000001": {
                    "price_change": -0.07,
                    "was_limit_down": False,
                    "is_open": True,
                    "open_time": "10:30:00",
                    "volume_ratio": 3.0,
                    "bid_ask_ratio": 2.0,
                    "reason": "normal",
                },
            },
            "fundamentals": {"000001": {}},
            "news_sentiment": {"000001": {}},
        }

        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_filters_not_open(self):
        """Test filtering unopened limit-down stocks"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        market_data = {
            "limit_down_stocks": {
                "000001": {
                    "price_change": -0.095,
                    "was_limit_down": True,
                    "is_open": False,
                    "open_time": "",
                    "volume_ratio": 3.0,
                    "bid_ask_ratio": 2.0,
                    "reason": "limit down",
                },
            },
            "fundamentals": {"000001": {}},
            "news_sentiment": {"000001": {}},
        }

        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_filters_low_recovery(self):
        """Test filtering insufficient recovery"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        market_data = {
            "limit_down_stocks": {
                "000001": {
                    "price_change": -0.09,
                    "was_limit_down": True,
                    "is_open": True,
                    "open_time": "10:30:00",
                    "volume_ratio": 3.0,
                    "bid_ask_ratio": 2.0,
                    "reason": "test",
                },
            },
            "fundamentals": {"000001": {}},
            "news_sentiment": {"000001": {}},
        }

        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_filters_low_volume(self):
        """Test filtering low volume"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        market_data = {
            "limit_down_stocks": {
                "000001": {
                    "price_change": -0.07,
                    "was_limit_down": True,
                    "is_open": True,
                    "open_time": "10:30:00",
                    "volume_ratio": 1.5,
                    "bid_ask_ratio": 2.0,
                    "reason": "test",
                },
            },
            "fundamentals": {"000001": {}},
            "news_sentiment": {"000001": {}},
        }

        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_filters_low_bid_ask_ratio(self):
        """Test filtering low bid/ask ratio"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        market_data = {
            "limit_down_stocks": {
                "000001": {
                    "price_change": -0.07,
                    "was_limit_down": True,
                    "is_open": True,
                    "open_time": "10:30:00",
                    "volume_ratio": 3.0,
                    "bid_ask_ratio": 1.0,
                    "reason": "test",
                },
            },
            "fundamentals": {"000001": {}},
            "news_sentiment": {"000001": {}},
        }

        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_filters_continuous_negative(self):
        """Test filtering continuous negative news"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        market_data = {
            "limit_down_stocks": {
                "000001": {
                    "price_change": -0.07,
                    "was_limit_down": True,
                    "is_open": True,
                    "open_time": "10:30:00",
                    "volume_ratio": 3.0,
                    "bid_ask_ratio": 2.0,
                    "reason": "test",
                },
            },
            "fundamentals": {
                "000001": {
                    "is_st": True,
                    "delisting_risk": False,
                    "consecutive_loss_quarters": 0,
                }
            },
            "news_sentiment": {"000001": {}},
        }

        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_with_empty_data(self):
        """Test with empty data"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        market_data = {"limit_down_stocks": {}}
        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_limits_to_top_3(self):
        """Test limiting to top 3 signals"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        market_data = {
            "limit_down_stocks": {
                f"00000{i}": {
                    "price_change": -0.07,
                    "was_limit_down": True,
                    "is_open": True,
                    "open_time": "10:30:00",
                    "volume_ratio": 3.0 + i * 0.1,
                    "bid_ask_ratio": 2.0,
                    "reason": "test",
                }
                for i in range(1, 6)
            },
            "fundamentals": {f"00000{i}": {} for i in range(1, 6)},
            "news_sentiment": {f"00000{i}": {} for i in range(1, 6)},
        }

        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 3

    @pytest.mark.asyncio
    async def test_generate_signals_exception_handling(self):
        """Test exception handling"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        market_data = {
            "limit_down_stocks": {
                "000001": {
                    "price_change": -0.07,
                },
            },
            "fundamentals": {},
            "news_sentiment": {},
        }

        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 0



class TestIsContinuousNegative:
    """Test continuous negative detection"""

    def test_is_continuous_negative_st_stock(self):
        """Test ST stock detection"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        fundamental_data = {"is_st": True, "delisting_risk": False, "consecutive_loss_quarters": 0}
        sentiment_data = {}

        result = strategy._is_continuous_negative(fundamental_data, sentiment_data)
        assert result is True

    def test_is_continuous_negative_delisting_risk(self):
        """Test delisting risk detection"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        fundamental_data = {"is_st": False, "delisting_risk": True, "consecutive_loss_quarters": 0}
        sentiment_data = {}

        result = strategy._is_continuous_negative(fundamental_data, sentiment_data)
        assert result is True

    def test_is_continuous_negative_consecutive_loss(self):
        """Test consecutive loss detection"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        fundamental_data = {"is_st": False, "delisting_risk": False, "consecutive_loss_quarters": 2}
        sentiment_data = {}

        result = strategy._is_continuous_negative(fundamental_data, sentiment_data)
        assert result is True

    def test_is_continuous_negative_negative_news(self):
        """Test negative news detection"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        fundamental_data = {"is_st": False, "delisting_risk": False, "consecutive_loss_quarters": 0}
        sentiment_data = {"negative_news_count": 3, "sentiment_score": 0.2}

        result = strategy._is_continuous_negative(fundamental_data, sentiment_data)
        assert result is True

    def test_is_continuous_negative_no_risk(self):
        """Test no risk detection"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        fundamental_data = {"is_st": False, "delisting_risk": False, "consecutive_loss_quarters": 0}
        sentiment_data = {"negative_news_count": 1, "sentiment_score": 0.6}

        result = strategy._is_continuous_negative(fundamental_data, sentiment_data)
        assert result is False


class TestCalculateReversalConfidence:
    """Test confidence calculation"""

    def test_calculate_confidence_strong_signal(self):
        """Test strong signal confidence"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        confidence = strategy._calculate_reversal_confidence(
            current_change=-0.05,
            volume_ratio=4.0,
            bid_ask_ratio=3.0,
            fundamental_data={"pe_ratio": 20, "pb_ratio": 2},
            sentiment_data={"sentiment_score": 0.7},
        )

        assert 0.65 <= confidence <= 0.75

    def test_calculate_confidence_medium_signal(self):
        """Test medium signal confidence"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        confidence = strategy._calculate_reversal_confidence(
            current_change=-0.07,
            volume_ratio=2.5,
            bid_ask_ratio=2.0,
            fundamental_data={"pe_ratio": 40, "pb_ratio": 4},
            sentiment_data={"sentiment_score": 0.5},
        )

        assert 0.50 <= confidence <= 0.75

    def test_calculate_confidence_weak_signal(self):
        """Test weak signal confidence"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        confidence = strategy._calculate_reversal_confidence(
            current_change=-0.08,
            volume_ratio=2.0,
            bid_ask_ratio=1.5,
            fundamental_data={"pe_ratio": 60, "pb_ratio": 6},
            sentiment_data={"sentiment_score": 0.3},
        )

        assert 0.40 <= confidence <= 0.55

    def test_calculate_confidence_minimum_threshold(self):
        """Test minimum confidence threshold"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        confidence = strategy._calculate_reversal_confidence(
            current_change=-0.095,
            volume_ratio=2.0,
            bid_ask_ratio=1.5,
            fundamental_data={},
            sentiment_data={},
        )

        assert confidence >= 0.4

    def test_calculate_confidence_maximum_cap(self):
        """Test maximum confidence cap"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        confidence = strategy._calculate_reversal_confidence(
            current_change=0.0,
            volume_ratio=10.0,
            bid_ask_ratio=10.0,
            fundamental_data={"pe_ratio": 10, "pb_ratio": 1},
            sentiment_data={"sentiment_score": 1.0},
        )

        assert confidence <= 0.75



class TestCalculatePositionSizes:
    """Test position size calculation"""

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_signals(self):
        """Test basic position calculation"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        signals = [
            Signal(symbol="000001", action="buy", confidence=0.70, timestamp="2024-01-01", reason="test"),
            Signal(symbol="000002", action="buy", confidence=0.60, timestamp="2024-01-01", reason="test"),
        ]

        positions = await strategy.calculate_position_sizes(signals)

        assert len(positions) == 2
        assert all(isinstance(p, Position) for p in positions)
        assert all(p.size > 0 for p in positions)
        assert sum(p.size for p in positions) <= strategy.max_total_position

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_respects_max_total(self):
        """Test max total position limit"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        signals = [
            Signal(symbol=f"00000{i}", action="buy", confidence=0.70, timestamp="2024-01-01", reason="test")
            for i in range(1, 6)
        ]

        positions = await strategy.calculate_position_sizes(signals)

        total_position = sum(p.size for p in positions)
        assert total_position <= strategy.max_total_position

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_empty_signals(self):
        """Test with empty signals"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        positions = await strategy.calculate_position_sizes([])
        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_filters_sell_signals(self):
        """Test filtering sell signals"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        signals = [
            Signal(symbol="000001", action="buy", confidence=0.70, timestamp="2024-01-01", reason="test"),
            Signal(symbol="000002", action="sell", confidence=0.60, timestamp="2024-01-01", reason="test"),
        ]

        positions = await strategy.calculate_position_sizes(signals)

        assert len(positions) == 1
        assert positions[0].symbol == "000001"

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_confidence_affects_size(self):
        """Test confidence affects position size"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        signals = [
            Signal(symbol="000001", action="buy", confidence=0.70, timestamp="2024-01-01", reason="test"),
            Signal(symbol="000002", action="buy", confidence=0.50, timestamp="2024-01-01", reason="test"),
        ]

        positions = await strategy.calculate_position_sizes(signals)
        assert positions[0].size > positions[1].size

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_stops_at_minimum(self):
        """Test stops at minimum position"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        signals = [
            Signal(symbol=f"00000{i}", action="buy", confidence=0.40, timestamp="2024-01-01", reason="test")
            for i in range(1, 20)
        ]

        positions = await strategy.calculate_position_sizes(signals)
        assert all(p.size >= 0.005 for p in positions)


class TestApplyRiskControls:
    """Test risk controls"""

    @pytest.mark.asyncio
    async def test_apply_risk_controls_with_positions(self):
        """Test applying risk controls"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        positions = [
            Position(
                symbol="000001",
                size=0.02,
                entry_price=100.0,
                current_price=100.0,
                pnl_pct=0.0,
                holding_days=0,
                industry="tech",
            )
        ]

        filtered = await strategy.apply_risk_controls(positions)

        assert len(filtered) == 1
        assert filtered[0].symbol == "000001"

    @pytest.mark.asyncio
    async def test_apply_risk_controls_sets_strict_stop_loss(self):
        """Test setting strict stop loss"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        strategy.risk_manager = MagicMock()
        strategy.risk_manager.stop_loss_pct = -0.08

        positions = [
            Position(
                symbol="000001",
                size=0.02,
                entry_price=100.0,
                current_price=100.0,
                pnl_pct=0.0,
                holding_days=0,
                industry="tech",
            )
        ]

        with patch.object(Strategy, "apply_risk_controls", new_callable=AsyncMock) as mock_super:
            mock_super.return_value = positions
            filtered = await strategy.apply_risk_controls(positions)

        assert strategy.risk_manager.stop_loss_pct == strategy.strict_stop_loss


class TestEdgeCases:
    """Test edge cases"""

    @pytest.mark.asyncio
    async def test_generate_signals_with_missing_keys(self):
        """Test with missing keys"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        market_data = {
            "limit_down_stocks": {
                "000001": {
                    "price_change": -0.07,
                },
            },
        }

        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 0

    def test_is_continuous_negative_with_missing_keys(self):
        """Test with missing fundamental keys"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        fundamental_data = {}
        sentiment_data = {}

        result = strategy._is_continuous_negative(fundamental_data, sentiment_data)
        assert result is False

    def test_calculate_confidence_with_empty_data(self):
        """Test confidence with empty data"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        confidence = strategy._calculate_reversal_confidence(
            current_change=-0.08,
            volume_ratio=2.0,
            bid_ask_ratio=1.5,
            fundamental_data={},
            sentiment_data={},
        )

        assert 0.4 <= confidence <= 0.75

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_position_price(self):
        """Test position price setting"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        signals = [
            Signal(symbol="000001", action="buy", confidence=0.70, timestamp="2024-01-01", reason="test"),
        ]

        positions = await strategy.calculate_position_sizes(signals)

        assert positions[0].entry_price == 100.0
        assert positions[0].current_price == 100.0


    @pytest.mark.asyncio
    async def test_generate_signals_logs_exception(self):
        """Test exception logging in signal generation"""
        config = create_test_config()
        strategy = S13LimitDownReversalStrategy(config)

        # Mock _analyze_limit_down to raise exception
        with patch.object(strategy, '_analyze_limit_down', side_effect=Exception("Test error")):
            market_data = {
                "limit_down_stocks": {
                    "000001": {
                        "price_change": -0.07,
                        "was_limit_down": True,
                        "is_open": True,
                        "open_time": "10:30:00",
                        "volume_ratio": 3.0,
                        "bid_ask_ratio": 2.0,
                        "reason": "test",
                    },
                },
                "fundamentals": {"000001": {}},
                "news_sentiment": {"000001": {}},
            }

            signals = await strategy.generate_signals(market_data)
            
            # Exception is caught and logged, returns empty list
            assert len(signals) == 0
