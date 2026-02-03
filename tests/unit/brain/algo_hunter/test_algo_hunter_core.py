"""Algo Hunter核心类测试

白皮书依据: 第二章 2.3 Algo Hunter (主力雷达)
验证需求: 需求7.1, 需求7.2
"""

import pytest
import time
import sys
from unittest.mock import Mock, patch, MagicMock
from src.brain.algo_hunter.core import AlgoHunter, RadarSignal


class TestRadarSignal:
    """测试RadarSignal数据类
    
    白皮书依据: 第二章 2.3 Algo Hunter
    验证需求: 需求7.2
    """
    
    def test_radar_signal_creation_valid(self):
        """测试有效的雷达信号创建"""
        signal = RadarSignal(
            symbol="000001.SZ",
            timestamp=1737100800.0,
            main_force_probability=0.85,
            volume=1000000,
            price=10.5,
            bid_ask_spread=0.01
        )
        
        assert signal.symbol == "000001.SZ"
        assert signal.timestamp == 1737100800.0
        assert signal.main_force_probability == 0.85
        assert signal.volume == 1000000
        assert signal.price == 10.5
        assert signal.bid_ask_spread == 0.01
    
    def test_radar_signal_empty_symbol(self):
        """测试空标的代码"""
        with pytest.raises(ValueError, match="标的代码不能为空"):
            RadarSignal(
                symbol="",
                timestamp=1737100800.0,
                main_force_probability=0.85,
                volume=1000000,
                price=10.5,
                bid_ask_spread=0.01
            )
    
    def test_radar_signal_invalid_probability_too_high(self):
        """测试主力概率超过1"""
        with pytest.raises(ValueError, match="主力概率必须在\\[0, 1\\]范围内"):
            RadarSignal(
                symbol="000001.SZ",
                timestamp=1737100800.0,
                main_force_probability=1.5,
                volume=1000000,
                price=10.5,
                bid_ask_spread=0.01
            )
    
    def test_radar_signal_invalid_probability_negative(self):
        """测试负的主力概率"""
        with pytest.raises(ValueError, match="主力概率必须在\\[0, 1\\]范围内"):
            RadarSignal(
                symbol="000001.SZ",
                timestamp=1737100800.0,
                main_force_probability=-0.1,
                volume=1000000,
                price=10.5,
                bid_ask_spread=0.01
            )
    
    def test_radar_signal_negative_volume(self):
        """测试负的成交量"""
        with pytest.raises(ValueError, match="成交量不能为负数"):
            RadarSignal(
                symbol="000001.SZ",
                timestamp=1737100800.0,
                main_force_probability=0.85,
                volume=-1000,
                price=10.5,
                bid_ask_spread=0.01
            )
    
    def test_radar_signal_invalid_price(self):
        """测试无效价格"""
        with pytest.raises(ValueError, match="价格必须 > 0"):
            RadarSignal(
                symbol="000001.SZ",
                timestamp=1737100800.0,
                main_force_probability=0.85,
                volume=1000000,
                price=0.0,
                bid_ask_spread=0.01
            )
        
        with pytest.raises(ValueError, match="价格必须 > 0"):
            RadarSignal(
                symbol="000001.SZ",
                timestamp=1737100800.0,
                main_force_probability=0.85,
                volume=1000000,
                price=-10.5,
                bid_ask_spread=0.01
            )
    
    def test_radar_signal_negative_spread(self):
        """测试负的买卖价差"""
        with pytest.raises(ValueError, match="买卖价差不能为负数"):
            RadarSignal(
                symbol="000001.SZ",
                timestamp=1737100800.0,
                main_force_probability=0.85,
                volume=1000000,
                price=10.5,
                bid_ask_spread=-0.01
            )
    
    def test_radar_signal_boundary_probability_zero(self):
        """测试边界值：概率为0"""
        signal = RadarSignal(
            symbol="000001.SZ",
            timestamp=1737100800.0,
            main_force_probability=0.0,
            volume=1000000,
            price=10.5,
            bid_ask_spread=0.01
        )
        
        assert signal.main_force_probability == 0.0
    
    def test_radar_signal_boundary_probability_one(self):
        """测试边界值：概率为1"""
        signal = RadarSignal(
            symbol="000001.SZ",
            timestamp=1737100800.0,
            main_force_probability=1.0,
            volume=1000000,
            price=10.5,
            bid_ask_spread=0.01
        )
        
        assert signal.main_force_probability == 1.0


class TestAlgoHunter:
    """测试AlgoHunter类
    
    白皮书依据: 第二章 2.3 Algo Hunter (主力雷达)
    验证需求: 需求7.1, 需求7.2
    """
    
    def test_init_valid_parameters_onnx(self):
        """测试有效参数初始化（ONNX）"""
        hunter = AlgoHunter(
            model_path="model.onnx",
            model_format="onnx",
            use_gpu=True
        )
        
        assert hunter.model is None  # 未调用load_model
        assert hunter.model_path == "model.onnx"
        assert hunter.model_format == "onnx"
        assert hunter.gpu_available is True
        assert hunter.inference_count == 0
        assert hunter.spsc_queue is None
    
    def test_init_valid_parameters_pytorch(self):
        """测试有效参数初始化（PyTorch）"""
        hunter = AlgoHunter(
            model_path="model.pt",
            model_format="pytorch",
            use_gpu=False
        )
        
        assert hunter.model_path == "model.pt"
        assert hunter.model_format == "pytorch"
        assert hunter.gpu_available is False
    
    def test_init_empty_model_path(self):
        """测试空模型路径"""
        with pytest.raises(ValueError, match="模型路径不能为空"):
            AlgoHunter(model_path="")
    
    def test_init_invalid_model_format(self):
        """测试无效模型格式"""
        with pytest.raises(ValueError, match="不支持的模型格式"):
            AlgoHunter(model_path="model.bin", model_format="tensorflow")
    
    def test_load_model_onnx_compatible_mode(self):
        """测试加载ONNX模型（兼容模式）"""
        # 模拟onnxruntime未安装
        with patch.dict('sys.modules', {'onnxruntime': None}):
            hunter = AlgoHunter(model_path="model.onnx", model_format="onnx")
            hunter.load_model()
            
            # 验证兼容模式
            assert hunter.model is not None
            assert isinstance(hunter.model, dict)
            assert hunter.model.get("mode") == "compatible"
    
    def test_load_model_pytorch_compatible_mode(self):
        """测试加载PyTorch模型（兼容模式）"""
        # 模拟torch未安装
        with patch.dict('sys.modules', {'torch': None}):
            hunter = AlgoHunter(model_path="model.pt", model_format="pytorch")
            hunter.load_model()
            
            # 验证兼容模式
            assert hunter.model is not None
            assert isinstance(hunter.model, dict)
            assert hunter.model.get("mode") == "compatible"
    
    def test_analyze_tick_valid_data(self):
        """测试分析有效Tick数据"""
        hunter = AlgoHunter(model_path="model.onnx")
        hunter.load_model()  # 加载模型（兼容模式）
        
        tick_data = {
            "symbol": "000001.SZ",
            "price": 10.5,
            "volume": 1000000,
            "bid": 10.49,
            "ask": 10.51
        }
        
        probability = hunter.analyze_tick(tick_data)
        
        # 验证输出范围
        assert 0 <= probability <= 1
        
        # 验证统计更新
        assert hunter.inference_count == 1
    
    def test_analyze_tick_empty_data(self):
        """测试空Tick数据"""
        hunter = AlgoHunter(model_path="model.onnx")
        hunter.load_model()
        
        with pytest.raises(ValueError, match="Tick数据无效"):
            hunter.analyze_tick(None)
        
        with pytest.raises(ValueError, match="Tick数据无效"):
            hunter.analyze_tick({})
    
    def test_analyze_tick_missing_required_fields(self):
        """测试缺少必需字段"""
        hunter = AlgoHunter(model_path="model.onnx")
        hunter.load_model()
        
        # 缺少symbol
        with pytest.raises(ValueError, match="缺少必需字段: symbol"):
            hunter.analyze_tick({
                "price": 10.5,
                "volume": 1000,
                "bid": 10.49,
                "ask": 10.51
            })
        
        # 缺少price
        with pytest.raises(ValueError, match="缺少必需字段: price"):
            hunter.analyze_tick({
                "symbol": "000001.SZ",
                "volume": 1000,
                "bid": 10.49,
                "ask": 10.51
            })
    
    def test_analyze_tick_model_not_loaded(self):
        """测试模型未加载"""
        hunter = AlgoHunter(model_path="model.onnx")
        
        tick_data = {
            "symbol": "000001.SZ",
            "price": 10.5,
            "volume": 1000,
            "bid": 10.49,
            "ask": 10.51
        }
        
        with pytest.raises(RuntimeError, match="模型未加载"):
            hunter.analyze_tick(tick_data)
    
    def test_analyze_tick_multiple_calls(self):
        """测试多次推理调用"""
        hunter = AlgoHunter(model_path="model.onnx")
        hunter.load_model()
        
        tick_data = {
            "symbol": "000001.SZ",
            "price": 10.5,
            "volume": 1000000,
            "bid": 10.49,
            "ask": 10.51
        }
        
        # 多次调用
        for i in range(5):
            probability = hunter.analyze_tick(tick_data)
            assert 0 <= probability <= 1
        
        # 验证统计
        assert hunter.inference_count == 5
    
    def test_get_status_before_load(self):
        """测试加载前获取状态"""
        hunter = AlgoHunter(model_path="model.onnx", model_format="onnx")
        
        status = hunter.get_status()
        
        assert status["model_loaded"] is False
        assert status["model_path"] == "model.onnx"
        assert status["model_format"] == "onnx"
        assert status["gpu_available"] is True
        assert status["inference_count"] == 0
        assert status["spsc_queue_connected"] is False
    
    def test_get_status_after_load(self):
        """测试加载后获取状态"""
        hunter = AlgoHunter(model_path="model.onnx")
        hunter.load_model()
        
        status = hunter.get_status()
        
        assert status["model_loaded"] is True
        assert status["inference_count"] == 0
    
    def test_get_status_after_inference(self):
        """测试推理后获取状态"""
        hunter = AlgoHunter(model_path="model.onnx")
        hunter.load_model()
        
        tick_data = {
            "symbol": "000001.SZ",
            "price": 10.5,
            "volume": 1000000,
            "bid": 10.49,
            "ask": 10.51
        }
        
        hunter.analyze_tick(tick_data)
        hunter.analyze_tick(tick_data)
        
        status = hunter.get_status()
        
        assert status["inference_count"] == 2


class TestAlgoHunterIntegration:
    """测试Algo Hunter集成场景"""
    
    def test_full_lifecycle(self):
        """测试完整生命周期"""
        # 1. 创建Algo Hunter
        hunter = AlgoHunter(
            model_path="model.onnx",
            model_format="onnx",
            use_gpu=True
        )
        
        # 2. 加载模型
        hunter.load_model()
        
        # 3. 分析Tick数据
        tick_data = {
            "symbol": "000001.SZ",
            "price": 10.5,
            "volume": 1000000,
            "bid": 10.49,
            "ask": 10.51,
            "timestamp": 1737100800.0
        }
        
        probability = hunter.analyze_tick(tick_data)
        
        # 4. 验证结果
        assert 0 <= probability <= 1
        
        # 5. 获取状态
        status = hunter.get_status()
        assert status["model_loaded"] is True
        assert status["inference_count"] == 1
    
    def test_different_volume_scenarios(self):
        """测试不同成交量场景"""
        hunter = AlgoHunter(model_path="model.onnx")
        hunter.load_model()
        
        # 场景1: 大成交量
        tick_large_volume = {
            "symbol": "000001.SZ",
            "price": 10.5,
            "volume": 5000000,
            "bid": 10.49,
            "ask": 10.51
        }
        
        prob_large = hunter.analyze_tick(tick_large_volume)
        
        # 场景2: 小成交量
        tick_small_volume = {
            "symbol": "000001.SZ",
            "price": 10.5,
            "volume": 10000,
            "bid": 10.49,
            "ask": 10.51
        }
        
        prob_small = hunter.analyze_tick(tick_small_volume)
        
        # 验证大成交量的主力概率更高
        assert prob_large > prob_small
        
        # 验证都在有效范围内
        assert 0 <= prob_large <= 1
        assert 0 <= prob_small <= 1


class TestAlgoHunterPreprocessing:
    """测试数据预处理功能
    
    白皮书依据: 第二章 2.3 Algo Hunter
    验证需求: 需求7.1
    """
    
    def test_preprocess_normal_data(self):
        """测试正常数据预处理"""
        hunter = AlgoHunter(model_path="model.onnx")
        hunter.load_model()
        
        tick_data = {
            "symbol": "000001.SZ",
            "price": 10.5,
            "volume": 1000000,
            "bid": 10.49,
            "ask": 10.51
        }
        
        features = hunter._preprocess(tick_data)
        
        # 验证特征提取
        assert "price" in features
        assert "volume" in features
        assert "bid_ask_spread" in features
        assert "price_deviation" in features
        
        # 验证计算正确性
        assert features["price"] == 10.5
        assert features["volume"] == 1000000
        assert abs(features["bid_ask_spread"] - 0.02) < 1e-10  # 浮点数比较
    
    def test_preprocess_zero_mid_price(self):
        """测试中间价为0的边界情况"""
        hunter = AlgoHunter(model_path="model.onnx")
        hunter.load_model()
        
        tick_data = {
            "symbol": "000001.SZ",
            "price": 10.5,
            "volume": 1000000,
            "bid": 0.0,
            "ask": 0.0
        }
        
        features = hunter._preprocess(tick_data)
        
        # 验证价格偏离为0（避免除以0）
        assert features["price_deviation"] == 0
    
    def test_preprocess_large_spread(self):
        """测试大买卖价差场景"""
        hunter = AlgoHunter(model_path="model.onnx")
        hunter.load_model()
        
        tick_data = {
            "symbol": "000001.SZ",
            "price": 10.5,
            "volume": 1000000,
            "bid": 10.0,
            "ask": 11.0
        }
        
        features = hunter._preprocess(tick_data)
        
        # 验证大价差
        assert features["bid_ask_spread"] == 1.0


class TestAlgoHunterInference:
    """测试模型推理功能
    
    白皮书依据: 第二章 2.3 Algo Hunter
    验证需求: 需求7.1, 需求7.2
    """
    
    def test_inference_onnx_format(self):
        """测试ONNX格式推理"""
        hunter = AlgoHunter(model_path="model.onnx", model_format="onnx")
        hunter.load_model()
        
        features = {
            "price": 10.5,
            "volume": 1000000,
            "bid_ask_spread": 0.02,
            "price_deviation": 0.001
        }
        
        probability = hunter._inference_onnx(features)
        
        # 验证输出范围
        assert 0 <= probability <= 1
    
    def test_inference_pytorch_format(self):
        """测试PyTorch格式推理"""
        # 使用兼容模式测试
        hunter = AlgoHunter(model_path="model.pt", model_format="pytorch")
        
        # 手动设置兼容模式模型
        hunter.model = {
            "format": "pytorch",
            "path": "model.pt",
            "loaded": True,
            "mode": "compatible"
        }
        
        features = {
            "price": 10.5,
            "volume": 1000000,
            "bid_ask_spread": 0.02,
            "price_deviation": 0.001
        }
        
        probability = hunter._inference_pytorch(features)
        
        # 验证输出范围
        assert 0 <= probability <= 1
    
    def test_inference_output_range_constraint(self):
        """测试输出范围约束
        
        属性: 输出范围约束
        验证需求: 需求7.2
        """
        hunter = AlgoHunter(model_path="model.onnx")
        hunter.load_model()
        
        # 测试多种特征组合
        test_cases = [
            {"volume": 0, "bid_ask_spread": 0},
            {"volume": 1000000, "bid_ask_spread": 0.01},
            {"volume": 10000000, "bid_ask_spread": 1.0},
            {"volume": 500000, "bid_ask_spread": 0.5},
        ]
        
        for features in test_cases:
            probability = hunter._inference_onnx(features)
            assert 0 <= probability <= 1, f"输出超出范围: {probability}"
    
    def test_inference_compatible_mode_volume_thresholds(self):
        """测试兼容模式的成交量阈值"""
        hunter = AlgoHunter(model_path="model.onnx")
        hunter.load_model()
        
        # 测试大成交量（> 100000）
        features_large = {"volume": 150000, "bid_ask_spread": 0.01}
        prob_large = hunter._inference(features_large)
        assert prob_large == 0.75
        
        # 测试中等成交量（50000-100000）
        features_medium = {"volume": 75000, "bid_ask_spread": 0.01}
        prob_medium = hunter._inference(features_medium)
        assert prob_medium == 0.55
        
        # 测试小成交量（< 50000）
        features_small = {"volume": 30000, "bid_ask_spread": 0.01}
        prob_small = hunter._inference(features_small)
        assert prob_small == 0.35


class TestAlgoHunterQueueIntegration:
    """测试SPSC队列集成
    
    白皮书依据: 第二章 2.3 Algo Hunter
    验证需求: 需求7.3
    """
    
    def test_write_to_queue_with_timestamp(self):
        """测试写入队列（带时间戳）"""
        hunter = AlgoHunter(model_path="model.onnx")
        hunter.load_model()
        
        tick_data = {
            "symbol": "000001.SZ",
            "price": 10.5,
            "volume": 1000000,
            "bid": 10.49,
            "ask": 10.51,
            "timestamp": 1737100800.0
        }
        
        # 模拟队列
        hunter.spsc_queue = Mock()
        
        # 执行推理（会触发写入队列）
        probability = hunter.analyze_tick(tick_data)
        
        # 验证推理成功
        assert 0 <= probability <= 1
    
    def test_write_to_queue_without_timestamp(self):
        """测试写入队列（无时间戳，使用当前时间）"""
        hunter = AlgoHunter(model_path="model.onnx")
        hunter.load_model()
        
        tick_data = {
            "symbol": "000001.SZ",
            "price": 10.5,
            "volume": 1000000,
            "bid": 10.49,
            "ask": 10.51
        }
        
        # 模拟队列
        hunter.spsc_queue = Mock()
        
        # 执行推理（会触发写入队列）
        probability = hunter.analyze_tick(tick_data)
        
        # 验证推理成功
        assert 0 <= probability <= 1
    
    def test_write_to_queue_signal_creation(self):
        """测试雷达信号创建"""
        hunter = AlgoHunter(model_path="model.onnx")
        hunter.load_model()
        
        tick_data = {
            "symbol": "000001.SZ",
            "price": 10.5,
            "volume": 1000000,
            "bid": 10.49,
            "ask": 10.51,
            "timestamp": 1737100800.0
        }
        
        # 直接测试_write_to_queue方法
        probability = 0.85
        
        # 不应该抛出异常
        hunter._write_to_queue(tick_data, probability)


class TestAlgoHunterModelLoading:
    """测试模型加载功能
    
    白皮书依据: 第二章 2.3 Algo Hunter
    验证需求: 需求7.1, 需求7.4
    """
    
    def test_load_model_file_not_found_onnx(self):
        """测试ONNX模型文件不存在"""
        # 创建mock模块
        mock_ort = MagicMock()
        
        with patch.dict('sys.modules', {'onnxruntime': mock_ort}):
            with patch('os.path.exists', return_value=False):
                hunter = AlgoHunter(model_path="nonexistent.onnx", model_format="onnx")
                
                with pytest.raises(RuntimeError, match="模型加载失败"):
                    hunter.load_model()
    
    def test_load_model_file_not_found_pytorch(self):
        """测试PyTorch模型文件不存在"""
        with patch('torch.load') as mock_load:
            with patch('os.path.exists', return_value=False):
                hunter = AlgoHunter(model_path="nonexistent.pt", model_format="pytorch")
                
                with pytest.raises(RuntimeError, match="模型加载失败"):
                    hunter.load_model()
    
    def test_load_onnx_model_with_cuda(self):
        """测试使用CUDA加载ONNX模型"""
        mock_session = MagicMock()
        mock_session.get_providers.return_value = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        
        # 创建mock模块
        mock_ort = MagicMock()
        mock_ort.InferenceSession.return_value = mock_session
        mock_ort.get_available_providers.return_value = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        
        with patch.dict('sys.modules', {'onnxruntime': mock_ort}):
            with patch('os.path.exists', return_value=True):
                hunter = AlgoHunter(model_path="model.onnx", model_format="onnx", use_gpu=True)
                hunter.load_model()
                
                # 验证模型已加载
                assert hunter.model is not None
    
    def test_load_onnx_model_with_rocm(self):
        """测试使用ROCm加载ONNX模型（AMD GPU）"""
        mock_session = MagicMock()
        mock_session.get_providers.return_value = ['ROCMExecutionProvider', 'CPUExecutionProvider']
        
        # 创建mock模块
        mock_ort = MagicMock()
        mock_ort.InferenceSession.return_value = mock_session
        mock_ort.get_available_providers.return_value = ['ROCMExecutionProvider', 'CPUExecutionProvider']
        
        with patch.dict('sys.modules', {'onnxruntime': mock_ort}):
            with patch('os.path.exists', return_value=True):
                hunter = AlgoHunter(model_path="model.onnx", model_format="onnx", use_gpu=True)
                hunter.load_model()
                
                # 验证模型已加载
                assert hunter.model is not None
    
    def test_load_onnx_model_gpu_unavailable(self):
        """测试GPU不可用时降级到CPU"""
        mock_session = MagicMock()
        mock_session.get_providers.return_value = ['CPUExecutionProvider']
        
        # 创建mock模块
        mock_ort = MagicMock()
        mock_ort.InferenceSession.return_value = mock_session
        mock_ort.get_available_providers.return_value = ['CPUExecutionProvider']
        
        with patch.dict('sys.modules', {'onnxruntime': mock_ort}):
            with patch('os.path.exists', return_value=True):
                hunter = AlgoHunter(model_path="model.onnx", model_format="onnx", use_gpu=True)
                hunter.load_model()
                
                # 验证降级到CPU
                assert hunter.gpu_available is False
                assert hunter.model is not None
    
    def test_load_pytorch_model_with_cuda(self):
        """测试使用CUDA加载PyTorch模型"""
        mock_model = MagicMock()
        mock_model.eval.return_value = mock_model
        mock_model.cuda.return_value = mock_model
        
        with patch('torch.load', return_value=mock_model):
            with patch('torch.cuda.is_available', return_value=True):
                with patch('os.path.exists', return_value=True):
                    hunter = AlgoHunter(model_path="model.pt", model_format="pytorch", use_gpu=True)
                    hunter.load_model()
                    
                    # 验证模型已加载并使用GPU
                    assert hunter.model is not None
                    assert hunter.gpu_available is True
    
    def test_load_pytorch_model_gpu_unavailable(self):
        """测试PyTorch GPU不可用时使用CPU"""
        mock_model = MagicMock()
        mock_model.eval.return_value = mock_model
        
        with patch('torch.load', return_value=mock_model):
            with patch('torch.cuda.is_available', return_value=False):
                with patch('os.path.exists', return_value=True):
                    hunter = AlgoHunter(model_path="model.pt", model_format="pytorch", use_gpu=True)
                    hunter.load_model()
                    
                    # 验证降级到CPU
                    assert hunter.gpu_available is False
                    assert hunter.model is not None


class TestAlgoHunterPerformance:
    """测试性能要求
    
    白皮书依据: 第二章 2.3 Algo Hunter
    验证需求: 需求7.1
    """
    
    def test_inference_latency_timeout(self):
        """测试推理延迟超时
        
        属性: 推理延迟上界
        验证需求: 需求7.1
        """
        hunter = AlgoHunter(model_path="model.onnx")
        hunter.load_model()
        
        tick_data = {
            "symbol": "000001.SZ",
            "price": 10.5,
            "volume": 1000000,
            "bid": 10.49,
            "ask": 10.51
        }
        
        # 模拟慢速推理（超过10ms）
        with patch.object(hunter, '_inference', side_effect=lambda x: (time.sleep(0.015), 0.5)[1]):
            with pytest.raises(TimeoutError, match="推理超时"):
                hunter.analyze_tick(tick_data)
