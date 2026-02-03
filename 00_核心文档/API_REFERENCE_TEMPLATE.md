# MIA系统API参考文档 (API Reference)

**版本**: v1.0  
**日期**: 2026-01-16  
**状态**: 模板文档  
**目的**: 提供统一的API文档格式

---

## 📋 文档规范

所有公共API必须遵循以下文档格式：

### 函数文档格式

```python
def function_name(param1: Type1, param2: Type2 = default) -> ReturnType:
    """
    简短描述（一句话）
    
    详细描述（可选，多行）
    
    Args:
        param1: 参数1的描述
        param2: 参数2的描述，默认值说明
        
    Returns:
        返回值的描述
        
    Raises:
        ExceptionType: 异常情况描述
        
    Example:
        >>> result = function_name(arg1, arg2)
        >>> print(result)
        expected_output
        
    Performance:
        延迟: < 10ms (P99)
        内存: < 100MB
        
    Note:
        额外说明或注意事项
    """
    pass
```

### 类文档格式

```python
class ClassName:
    """
    简短描述（一句话）
    
    详细描述（可选，多行）
    
    Attributes:
        attr1: 属性1的描述
        attr2: 属性2的描述
        
    Example:
        >>> obj = ClassName(param1, param2)
        >>> result = obj.method()
        
    Note:
        额外说明或注意事项
    """
    
    def __init__(self, param1: Type1, param2: Type2):
        """
        初始化方法
        
        Args:
            param1: 参数1的描述
            param2: 参数2的描述
        """
        pass
```

---

## 第一章: 柯罗诺斯生物钟

### MainOrchestrator

```python
class MainOrchestrator:
    """
    主调度器，负责五态生物钟的状态管理和资源调度
    
    五态定义:
    - State 0: 维护态 (Manual)
    - State 1: 战备态 (08:30-09:15)
    - State 2: 战争态 (09:15-15:00)
    - State 3: 诊疗态 (15:00-20:00)
    - State 4: 进化态 (20:00-08:30)
    
    Attributes:
        current_state: 当前状态
        services: 服务进程字典
        
    Example:
        >>> orchestrator = MainOrchestrator()
        >>> orchestrator.start()
        >>> orchestrator.transition_to_state(State.PREP_TIME)
    """
    
    def transition_to_state(self, target_state: State) -> bool:
        """
        切换到目标状态
        
        Args:
            target_state: 目标状态
            
        Returns:
            切换是否成功
            
        Raises:
            StateTransitionError: 状态切换失败
            
        Performance:
            延迟: < 1秒
        """
        pass
```

---

## 第二章: AI三脑

### Soldier

```python
class Soldier:
    """
    快系统，负责毫秒级交易决策
    
    支持两种模式:
    - LOCAL: AMD本地Qwen-30B (延迟 < 20ms)
    - CLOUD: DeepSeek-v3.2 API (延迟 < 200ms)
    
    Attributes:
        current_mode: 当前模式 ('LOCAL' or 'CLOUD')
        short_term_memory: 短期记忆（Redis）
        
    Example:
        >>> soldier = Soldier(mode='LOCAL')
        >>> decision = soldier.make_decision(context)
        >>> print(decision['action'])
        'BUY'
    """
    
    def make_decision(self, context: Dict) -> Dict:
        """
        做出交易决策
        
        Args:
            context: 决策上下文，包含市场数据、持仓等
            
        Returns:
            决策结果字典:
            {
                'action': 'BUY' | 'SELL' | 'HOLD',
                'confidence': float (0-1),
                'reason': str
            }
            
        Raises:
            DecisionError: 决策失败
            
        Performance:
            LOCAL模式: < 20ms (P99)
            CLOUD模式: < 200ms (P99)
            
        Note:
            自动热备切换，本地故障时切换到云端
        """
        pass
```

### Commander

```python
class Commander:
    """
    慢系统，负责战略级分析
    
    使用Qwen3-Next-80B-Instruct进行深度分析
    
    Attributes:
        api_client: LLM API客户端
        cost_tracker: 成本追踪器
        
    Example:
        >>> commander = Commander()
        >>> strategy = commander.analyze_strategy(context)
        >>> print(strategy['recommendation'])
    """
    
    def analyze_strategy(self, context: Dict) -> Dict:
        """
        分析策略并提供建议
        
        Args:
            context: 分析上下文
            
        Returns:
            战略分析结果
            
        Performance:
            延迟: < 5秒
            成本: ¥1.0/M tokens
        """
        pass
```

---

## 第三章: 基础设施

### DataProbe

```python
class DataProbe:
    """
    数据探针，自动发现和管理数据源
    
    功能:
    - 全量探测数据接口
    - 评估接口质量
    - 自动切换BACKUP
    - 数据完整性检查
    
    Attributes:
        probe_log: 探针日志
        download_log: 下载日志
        
    Example:
        >>> probe = DataProbe()
        >>> probe.discover_all()
        >>> data = probe.download_data('000001.SZ')
    """
    
    def discover_all(self) -> Dict:
        """
        全量探测所有数据接口
        
        Returns:
            探测结果字典:
            {
                'platforms': List[str],
                'discoveries': Dict[str, List[Interface]],
                'total_interfaces': int
            }
            
        Performance:
            延迟: < 30秒
            
        Note:
            首次启动或手动触发时执行
        """
        pass
    
    def download_data(self, symbol: str, source: str = 'PRIMARY') -> pd.DataFrame:
        """
        下载数据，支持自动重试和切换
        
        Args:
            symbol: 标的代码
            source: 数据源 ('PRIMARY' or 'BACKUP')
            
        Returns:
            数据DataFrame
            
        Raises:
            DataDownloadError: 下载失败
            
        Performance:
            延迟: < 2秒
            
        Note:
            失败自动重试3次，然后切换BACKUP
        """
        pass
```

### DataSanitizer

```python
class DataSanitizer:
    """
    数据清洗器，8层清洗框架
    
    清洗层级:
    1. NaN清洗
    2. 价格合理性检查
    3. HLOC一致性检查
    4. 成交量检查
    5. 重复值检查
    6. 异常值检测
    7. 数据缺口检测
    8. 公司行动处理
    
    Attributes:
        clean_rules: 清洗规则配置
        asset_config: 资产类型配置
        
    Example:
        >>> sanitizer = DataSanitizer()
        >>> clean_data = sanitizer.clean_dataframe(df, asset_type='stock')
        >>> quality = sanitizer.assess_data_quality(clean_data)
    """
    
    def clean_dataframe(self, df: pd.DataFrame, asset_type: str = 'stock') -> pd.DataFrame:
        """
        清洗数据
        
        Args:
            df: 原始数据
            asset_type: 资产类型 ('stock', 'future', 'option')
            
        Returns:
            清洗后的数据
            
        Performance:
            延迟: < 1秒 (1000行数据)
            
        Note:
            根据资产类型自适应清洗标准
        """
        pass
    
    def assess_data_quality(self, df: pd.DataFrame, asset_type: str = 'stock') -> Dict:
        """
        评估数据质量
        
        Args:
            df: 数据
            asset_type: 资产类型
            
        Returns:
            质量评估结果:
            {
                'overall': float (0-1),
                'completeness': float,
                'price_validity': float,
                'hloc_consistency': float,
                'volume_validity': float,
                'grade': str ('A+', 'A', 'B', ...)
            }
        """
        pass
```

---

## 第四章: 斯巴达进化

### GeneticMiner

```python
class GeneticMiner:
    """
    遗传算法因子挖掘器
    
    使用遗传算法在无限因子空间中搜索最优因子组合
    
    Attributes:
        population_size: 种群大小
        elite_ratio: 精英保留比例
        mutation_rate: 变异率
        crossover_rate: 交叉率
        population: 当前种群
        
    Example:
        >>> miner = GeneticMiner(population_size=50)
        >>> miner.initialize_population()
        >>> miner.evolve(generations=10)
        >>> best = miner.population[0]
    """
    
    def initialize_population(self) -> None:
        """
        初始化随机种群
        
        Performance:
            延迟: < 5秒
        """
        pass
    
    def evolve(self, generations: int = 10) -> None:
        """
        运行N代进化
        
        Args:
            generations: 进化代数
            
        Performance:
            延迟: ~30秒/代 (population_size=50)
            
        Note:
            每代包含: 评估适应度 -> 精英选择 -> 交叉 -> 变异
        """
        pass
```

### Arena

```python
class Arena:
    """
    斯巴达竞技场，双轨压力测试
    
    两条测试轨道:
    - Reality Track: 真实历史数据测试
    - Hell Track: 极端行情模拟
    
    Example:
        >>> arena = Arena()
        >>> reality_result = arena.reality_track(strategy)
        >>> hell_result = arena.hell_track(strategy)
    """
    
    def reality_track(self, strategy: Strategy) -> Dict:
        """
        真实历史数据测试
        
        Args:
            strategy: 待测试策略
            
        Returns:
            测试结果:
            {
                'passed': bool,
                'score': float (0-1),
                'sharpe_ratio': float,
                'max_drawdown': float,
                'annual_return': float,
                'win_rate': float
            }
            
        Performance:
            延迟: < 60秒
            
        Note:
            通过标准: score > 0.5
        """
        pass
    
    def hell_track(self, strategy: Strategy) -> Dict:
        """
        极端行情模拟测试
        
        Args:
            strategy: 待测试策略
            
        Returns:
            测试结果:
            {
                'passed': bool,
                'survival_rate': float (0-1),
                'scenarios_survived': int,
                'total_scenarios': int
            }
            
        Performance:
            延迟: < 120秒
            
        Note:
            通过标准: survival_rate > 0.3
        """
        pass
```

---

## 第五章: LLM策略分析

### StrategyAnalyzer

```python
class StrategyAnalyzer:
    """
    策略深度分析器，29个维度综合分析
    
    集成16个专业分析器，提供全面的策略评估
    
    Attributes:
        analyzers: 分析器字典
        redis_client: Redis客户端
        
    Example:
        >>> analyzer = StrategyAnalyzer()
        >>> result = analyzer.analyze_comprehensive(strategy_id='S01')
        >>> print(result['overall_score'])
    """
    
    def analyze_comprehensive(self, strategy_id: str) -> Dict:
        """
        综合分析策略（29个维度）
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            综合分析结果
            
        Performance:
            延迟: < 30秒
            
        Note:
            结果自动存储到Redis
        """
        pass
```

### SmartMoneyAnalyzer

```python
class SmartMoneyAnalyzer:
    """
    主力资金深度分析器
    
    基于Level-2数据分析主力行为
    
    Example:
        >>> analyzer = SmartMoneyAnalyzer()
        >>> analysis = analyzer.analyze('000001.SZ')
        >>> print(analysis['main_force_type'])
        '机构'
    """
    
    def analyze(self, symbol: str) -> Dict:
        """
        分析主力资金
        
        Args:
            symbol: 标的代码
            
        Returns:
            分析结果:
            {
                'cost_basis': float,
                'estimated_holdings': float,
                'holdings_pct': float,
                'profit_loss_pct': float,
                'main_force_type': str,
                'behavior_pattern': str,
                'next_action_prediction': str,
                'follow_risk': str
            }
            
        Performance:
            延迟: < 3秒
            
        Note:
            需要Level-2数据权限
        """
        pass
```

---

## 第七章: 安全与审计

### SecureConfig

```python
class SecureConfig:
    """
    安全配置管理器，加密存储敏感信息
    
    使用Fernet对称加密保护API密钥
    
    Attributes:
        key_file: 主密钥文件路径
        cipher: Fernet加密器
        
    Example:
        >>> config = SecureConfig()
        >>> api_key = config.get_api_key('DEEPSEEK_API_KEY')
    """
    
    def encrypt_api_key(self, api_key: str) -> str:
        """
        加密API密钥
        
        Args:
            api_key: 原始API密钥
            
        Returns:
            加密后的密钥
            
        Example:
            >>> encrypted = config.encrypt_api_key('sk-1234567890')
            >>> print(encrypted)
            'gAAAAABf...'
        """
        pass
    
    def get_api_key(self, key_name: str) -> str:
        """
        获取并解密API密钥
        
        Args:
            key_name: 密钥名称
            
        Returns:
            解密后的API密钥
            
        Raises:
            ValueError: 密钥不存在
            
        Example:
            >>> api_key = config.get_api_key('DEEPSEEK_API_KEY')
        """
        pass
```

### Auditor

```python
class Auditor:
    """
    独立审计进程，维护影子账本
    
    确保交易记录的准确性和完整性
    
    Attributes:
        shadow_ledger: 影子账本
        redis_client: Redis客户端
        
    Example:
        >>> auditor = Auditor()
        >>> auditor.sync_from_broker()
        >>> discrepancies = auditor.reconcile()
    """
    
    def sync_from_broker(self) -> None:
        """
        从券商同步真实持仓
        
        Performance:
            延迟: < 5秒
            
        Note:
            每5分钟自动执行
        """
        pass
    
    def reconcile(self) -> List[Dict]:
        """
        对账：比对执行进程记录与影子账本
        
        Returns:
            差异列表
            
        Performance:
            延迟: < 1秒
            
        Note:
            发现差异立即告警
        """
        pass
```

---

## 📝 文档生成

### 自动生成API文档

```bash
# 使用Sphinx生成文档
pip install sphinx sphinx-rtd-theme

# 初始化
sphinx-quickstart docs

# 配置autodoc
# docs/conf.py
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon']

# 生成文档
cd docs
make html

# 查看文档
open _build/html/index.html
```

---

**注意**: 所有公共API必须有完整的文档字符串，包括参数、返回值、异常、示例和性能指标。
