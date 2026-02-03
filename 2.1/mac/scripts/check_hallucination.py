#!/usr/bin/env python3
"""
MIA系统幻觉检查脚本
检查代码中的导入、类名、函数名是否在白皮书中定义
"""

import ast
import sys
from pathlib import Path
from typing import List, Set, Dict

# 白皮书定义的模块白名单
WHITELIST_MODULES = {
    # 第一章: 柯罗诺斯生物钟
    'scheduler.main_orchestrator',
    'scheduler.state_machine',
    'scheduler.gpu_watchdog',
    
    # 第二章: AI三脑
    'brain.soldier',
    'brain.commander',
    'brain.devil',
    'brain.scholar',
    'brain.algo_hunter',
    
    # 第三章: 基础设施
    'infra.spsc_queue',
    'infra.data_probe',
    'infra.sanitizer',
    'infra.bridge',
    'infra.ipc_protocol',
    
    # 第四章: 斯巴达进化
    'evolution.genetic_miner',
    'evolution.arena',
    'evolution.meta_evolution',
    'evolution.prompt_evolution',
    'evolution.z2h_capsule',
    'evolution.etf_lof',  # ETF/LOF因子挖掘器模块
    'genetic_miner',  # 内部导入
    'data_models',  # 内部导入
    'etf_operators',  # 内部导入
    'lof_operators',  # 内部导入
    'exceptions',  # 内部导入
    'arena_integration',  # 内部导入
    'cross_market_alignment',  # 内部导入
    'logging_config',  # 内部导入
    
    # 第五章: LLM策略分析
    'brain.analyzers.strategy_analyzer',
    'brain.analyzers.essence_analyzer',
    'brain.analyzers.risk_analyzer',
    'brain.analyzers.overfitting_detector',
    'brain.analyzers.feature_analyzer',
    'brain.analyzers.macro_analyzer',
    'brain.analyzers.microstructure_analyzer',
    'brain.analyzers.sector_analyzer',
    'brain.analyzers.smart_money_analyzer',
    'brain.analyzers.recommendation_engine',
    'brain.analyzers.trading_cost_analyzer',
    'brain.analyzers.decay_analyzer',
    'brain.analyzers.stop_loss_analyzer',
    'brain.analyzers.slippage_analyzer',
    'brain.analyzers.nonstationarity_analyzer',
    'brain.analyzers.signal_noise_analyzer',
    'brain.analyzers.capacity_analyzer',
    'brain.analyzers.stress_test_analyzer',
    'brain.analyzers.trade_review_analyzer',
    'brain.analyzers.sentiment_analyzer',
    'brain.analyzers.retail_sentiment_analyzer',
    'brain.analyzers.correlation_analyzer',
    'brain.analyzers.position_sizing_analyzer',
    
    # 第六章: 执行与风控
    'execution.executor',
    'execution.risk_gate',
    'execution.lockbox',
    'strategies.meta_momentum',
    'strategies.meta_mean_reversion',
    'strategies.meta_following',
    'strategies.meta_arbitrage',
    'strategies.meta_event',
    
    # 第七章: 安全与审计
    'config.secure_config',
    'interface.auth',
    'core.auditor',
    'monitoring.audit_logger',
    
    # 标准库和常用第三方库
    'os', 'sys', 'time', 'datetime', 'json', 'logging',
    'pathlib', 'typing', 'dataclasses', 'enum', 'random',
    'numpy', 'pandas', 'redis', 'fastapi', 'streamlit',
    'pytest', 'unittest', 'multiprocessing', 'asyncio',
    'cryptography', 'jwt', 'pydantic', 'torch', 'onnx',
    'loguru',  # 日志库
}

# 白皮书定义的类名白名单
WHITELIST_CLASSES = {
    # 第一章
    'MainOrchestrator', 'State', 'GPUWatchdog',
    
    # 第二章
    'Soldier', 'Commander', 'Devil', 'Scholar', 'AlgoHunter',
    
    # 第三章
    'SPSCQueue', 'DataProbe', 'DataSanitizer', 'Bridge',
    'TickData', 'OrderData', 'BarData',
    
    # 第四章
    'GeneticMiner', 'Arena', 'MetaEvolution', 'PromptEvolutionEngine',
    'Z2HGeneCapsule', 'HyperParameters',
    'ETFFactorMiner', 'LOFFactorMiner',  # ETF/LOF因子挖掘器
    'ETFOperators', 'LOFOperators',  # ETF/LOF算子
    'ETFMarketData', 'LOFMarketData',  # ETF/LOF数据模型
    'FactorExpression', 'ArenaTestResult',  # 因子表达式和测试结果
    'ArenaIntegration',  # Arena集成
    'MarketType',  # 市场类型枚举
    
    # 第五章
    'StrategyAnalyzer', 'EssenceAnalyzer', 'RiskAnalyzer',
    'OverfittingDetector', 'FeatureAnalyzer', 'MacroAnalyzer',
    'MicrostructureAnalyzer', 'SectorAnalyzer', 'SmartMoneyAnalyzer',
    'RecommendationEngine', 'TradingCostAnalyzer', 'DecayAnalyzer',
    'StopLossAnalyzer', 'SlippageAnalyzer', 'NonstationarityAnalyzer',
    'SignalNoiseAnalyzer', 'CapacityAnalyzer', 'StressTestAnalyzer',
    'TradeReviewAnalyzer', 'SentimentAnalyzer', 'RetailSentimentAnalyzer',
    'CorrelationAnalyzer', 'PositionSizingAnalyzer',
    
    # 第六章
    'Executor', 'RiskGate', 'LockBox',
    
    # 第七章
    'SecureConfig', 'AuthManager', 'Auditor', 'AuditLogger',
}


class HallucinationChecker:
    """幻觉检查器"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.issues: List[Dict] = []
        
    def check(self) -> bool:
        """
        执行检查
        
        Returns:
            是否通过检查（无幻觉）
        """
        if not self.file_path.exists():
            print(f"❌ 文件不存在: {self.file_path}")
            return False
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=str(self.file_path))
        except SyntaxError as e:
            print(f"❌ 语法错误: {e}")
            return False
        
        # 检查导入
        self._check_imports(tree)
        
        # 检查类定义
        self._check_classes(tree)
        
        # 输出结果
        return self._report()
    
    def _check_imports(self, tree: ast.AST):
        """检查导入语句"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._validate_module(alias.name, node.lineno)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self._validate_module(node.module, node.lineno)
    
    def _check_classes(self, tree: ast.AST):
        """检查类定义"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._validate_class(node.name, node.lineno)
    
    def _validate_module(self, module_name: str, lineno: int):
        """验证模块名"""
        # 检查是否在白名单中
        if module_name in WHITELIST_MODULES:
            return
        
        # 检查是否是白名单模块的子模块
        for whitelist_module in WHITELIST_MODULES:
            if module_name.startswith(whitelist_module + '.'):
                return
        
        # 可能的幻觉
        self.issues.append({
            'type': 'MODULE',
            'name': module_name,
            'line': lineno,
            'severity': 'WARNING',
            'message': f"模块 '{module_name}' 未在白皮书中定义"
        })
    
    def _validate_class(self, class_name: str, lineno: int):
        """验证类名"""
        # 跳过测试类
        if class_name.startswith('Test'):
            return
        
        # 检查是否在白名单中
        if class_name in WHITELIST_CLASSES:
            return
        
        # 可能的幻觉
        self.issues.append({
            'type': 'CLASS',
            'name': class_name,
            'line': lineno,
            'severity': 'WARNING',
            'message': f"类 '{class_name}' 未在白皮书中定义"
        })
    
    def _report(self) -> bool:
        """输出报告"""
        # 类型映射
        type_map = {
            'MODULE': '模块',
            'CLASS': '类',
            'FUNCTION': '函数'
        }
        
        if not self.issues:
            print(f"✅ {self.file_path}: 未发现幻觉")
            return True
        
        print(f"\n⚠️  {self.file_path}: 发现 {len(self.issues)} 个潜在幻觉\n")
        
        for issue in self.issues:
            type_cn = type_map.get(issue['type'], issue['type'])
            print(f"  [{issue['severity']}] 行 {issue['line']}: {issue['message']}")
            print(f"    类型: {type_cn}, 名称: {issue['name']}")
        
        print("\n💡 建议:")
        print("  1. 检查白皮书 (mia.md) 确认该功能是否已定义")
        print("  2. 如果是新功能，先更新白皮书再实现")
        print("  3. 如果是标准库，将其添加到白名单")
        
        return False


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python check_hallucination.py <file_path>")
        print("示例: python check_hallucination.py src/brain/soldier.py")
        sys.exit(1)
    
    file_path = sys.argv[1]
    checker = HallucinationChecker(file_path)
    
    if checker.check():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
