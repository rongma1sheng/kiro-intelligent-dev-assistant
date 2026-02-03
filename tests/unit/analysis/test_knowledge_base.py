"""KnowledgeBase单元测试

白皮书依据: 第五章 5.5.2 知识库存储

测试覆盖:
- 基因胶囊存储和检索
- 演化树构建和更新
- 精英策略管理
- 失败案例管理
- 反向黑名单管理
- 知识检索接口
- 错误处理
- 性能要求
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import redis

from src.analysis.knowledge_base import (
    KnowledgeBase,
    GeneCapsule,
    EvolutionNode,
    EliteStrategy,
    FailedStrategy,
    AntiPattern
)


@pytest.fixture
def mock_redis():
    """Mock Redis客户端"""
    with patch('src.analysis.knowledge_base.redis.Redis') as mock:
        redis_client = MagicMock()
        mock.return_value = redis_client
        yield redis_client


@pytest.fixture
def mock_connection_pool():
    """Mock Redis连接池"""
    with patch('src.analysis.knowledge_base.ConnectionPool') as mock:
        pool = MagicMock()
        mock.return_value = pool
        yield pool


@pytest.fixture
def knowledge_base(mock_redis, mock_connection_pool):
    """创建KnowledgeBase实例"""
    kb = KnowledgeBase(
        redis_host='localhost',
        redis_port=6379,
        redis_db=0,
        max_connections=50
    )
    return kb


@pytest.fixture
def sample_gene_capsule():
    """示例基因胶囊"""
    return GeneCapsule(
        capsule_id='capsule_001',
        strategy_id='strategy_001',
        certification_tier='Gold',
        performance_metrics={
            'sharpe_ratio': 2.5,
            'annual_return': 0.35,
            'max_drawdown': 0.12,
            'win_rate': 0.62
        },
        metadata={
            'factor_count': 5,
            'market': 'A股',
            'aum_tier': 'Tier 2'
        },
        created_at=datetime.now().isoformat()
    )


@pytest.fixture
def sample_evolution_node():
    """示例演化节点"""
    return EvolutionNode(
        node_id='node_001',
        strategy_id='strategy_001',
        parent_id=None,
        children_ids=[],
        generation=0,
        fitness_score=0.85
    )


@pytest.fixture
def sample_elite_strategy():
    """示例精英策略"""
    return EliteStrategy(
        strategy_id='strategy_001',
        sharpe_ratio=2.5,
        annual_return=0.35,
        max_drawdown=0.12,
        win_rate=0.62,
        added_at=datetime.now().isoformat()
    )


@pytest.fixture
def sample_failed_strategy():
    """示例失败策略"""
    return FailedStrategy(
        strategy_id='strategy_failed_001',
        failure_reason='过拟合',
        failure_type='overfitting',
        lessons_learned='避免在训练集上过度优化',
        failed_at=datetime.now().isoformat()
    )


@pytest.fixture
def sample_anti_pattern():
    """示例反模式"""
    return AntiPattern(
        pattern_id='pattern_001',
        pattern_name='过度交易',
        description='频繁交易导致高额交易成本',
        detection_rules={'keywords': ['high_frequency', 'day_trading']},
        severity='high',
        added_at=datetime.now().isoformat()
    )



class TestKnowledgeBaseInitialization:
    """测试KnowledgeBase初始化"""
    
    def test_initialization_success(self, knowledge_base):
        """测试成功初始化"""
        assert knowledge_base is not None
        assert knowledge_base.redis_client is not None
        assert knowledge_base.connection_pool is not None
    
    def test_initialization_custom_config(self, mock_redis, mock_connection_pool):
        """测试自定义配置初始化"""
        kb = KnowledgeBase(
            redis_host='192.168.1.100',
            redis_port=6380,
            redis_db=1,
            max_connections=100
        )
        
        # 验证实例创建成功
        assert kb is not None
        assert kb.redis_client is not None
        assert kb.connection_pool is not None


class TestGeneCapsuleManagement:
    """测试基因胶囊管理"""
    
    def test_store_gene_capsule_success(
        self,
        knowledge_base,
        sample_gene_capsule
    ):
        """测试成功存储基因胶囊"""
        # 配置mock
        knowledge_base.redis_client.set.return_value = True
        knowledge_base.redis_client.sadd.return_value = 1
        
        # 执行
        result = knowledge_base.store_gene_capsule(sample_gene_capsule)
        
        # 验证
        assert result is True
        
        # 验证Redis调用
        knowledge_base.redis_client.set.assert_called_once()
        knowledge_base.redis_client.sadd.assert_called_once_with(
            'mia:knowledge:elite_strategies',
            'strategy_001'
        )
    
    def test_store_gene_capsule_invalid_id(self, knowledge_base):
        """测试存储无效ID的基因胶囊"""
        capsule = GeneCapsule(
            capsule_id='',  # 空ID
            strategy_id='strategy_001',
            certification_tier='Gold',
            performance_metrics={},
            metadata={},
            created_at=datetime.now().isoformat()
        )
        
        with pytest.raises(ValueError, match="胶囊ID不能为空"):
            knowledge_base.store_gene_capsule(capsule)
    
    def test_store_gene_capsule_invalid_tier(self, knowledge_base):
        """测试存储无效认证层级的基因胶囊"""
        capsule = GeneCapsule(
            capsule_id='capsule_001',
            strategy_id='strategy_001',
            certification_tier='Invalid',  # 无效层级
            performance_metrics={},
            metadata={},
            created_at=datetime.now().isoformat()
        )
        
        with pytest.raises(ValueError, match="无效的认证层级"):
            knowledge_base.store_gene_capsule(capsule)
    
    def test_get_gene_capsule_success(
        self,
        knowledge_base,
        sample_gene_capsule
    ):
        """测试成功获取基因胶囊"""
        # 配置mock
        capsule_json = json.dumps({
            'capsule_id': 'capsule_001',
            'strategy_id': 'strategy_001',
            'certification_tier': 'Gold',
            'performance_metrics': {'sharpe_ratio': 2.5},
            'metadata': {},
            'created_at': datetime.now().isoformat()
        })
        knowledge_base.redis_client.get.return_value = capsule_json
        
        # 执行
        result = knowledge_base.get_gene_capsule('capsule_001')
        
        # 验证
        assert result is not None
        assert result.capsule_id == 'capsule_001'
        assert result.strategy_id == 'strategy_001'
        assert result.certification_tier == 'Gold'
    
    def test_get_gene_capsule_not_found(self, knowledge_base):
        """测试获取不存在的基因胶囊"""
        # 配置mock
        knowledge_base.redis_client.get.return_value = None
        
        # 执行
        result = knowledge_base.get_gene_capsule('nonexistent')
        
        # 验证
        assert result is None
    
    def test_get_gene_capsules_by_tier(self, knowledge_base):
        """测试按层级获取基因胶囊"""
        # 配置mock
        capsule1_json = json.dumps({
            'capsule_id': 'capsule_001',
            'strategy_id': 'strategy_001',
            'certification_tier': 'Gold',
            'performance_metrics': {},
            'metadata': {},
            'created_at': datetime.now().isoformat()
        })
        
        capsule2_json = json.dumps({
            'capsule_id': 'capsule_002',
            'strategy_id': 'strategy_002',
            'certification_tier': 'Silver',
            'performance_metrics': {},
            'metadata': {},
            'created_at': datetime.now().isoformat()
        })
        
        knowledge_base.redis_client.scan_iter.return_value = [
            'mia:knowledge:gene_capsule:capsule_001',
            'mia:knowledge:gene_capsule:capsule_002'
        ]
        
        knowledge_base.redis_client.get.side_effect = [
            capsule1_json,
            capsule2_json
        ]
        
        # 执行
        result = knowledge_base.get_gene_capsules_by_tier('Gold')
        
        # 验证
        assert len(result) == 1
        assert result[0].certification_tier == 'Gold'



class TestEvolutionTreeManagement:
    """测试演化树管理"""
    
    def test_build_evolution_tree_empty(self, knowledge_base):
        """测试构建空演化树"""
        # 配置mock
        knowledge_base.redis_client.get.return_value = None
        knowledge_base.redis_client.set.return_value = True
        
        # 执行
        tree = knowledge_base.build_evolution_tree()
        
        # 验证
        assert tree is not None
        assert tree['nodes'] == {}
        assert tree['root_nodes'] == []
        assert tree['max_generation'] == 0
        assert tree['total_nodes'] == 0
    
    def test_build_evolution_tree_existing(self, knowledge_base):
        """测试构建已存在的演化树"""
        # 配置mock
        existing_tree = {
            'nodes': {'node_001': {'node_id': 'node_001'}},
            'root_nodes': ['node_001'],
            'max_generation': 5,
            'total_nodes': 10,
            'updated_at': datetime.now().isoformat()
        }
        knowledge_base.redis_client.get.return_value = json.dumps(existing_tree)
        
        # 执行
        tree = knowledge_base.build_evolution_tree()
        
        # 验证
        assert tree['total_nodes'] == 10
        assert tree['max_generation'] == 5
        assert len(tree['root_nodes']) == 1
    
    def test_update_evolution_tree_root_node(
        self,
        knowledge_base,
        sample_evolution_node
    ):
        """测试更新演化树（根节点）"""
        # 配置mock
        empty_tree = {
            'nodes': {},
            'root_nodes': [],
            'max_generation': 0,
            'total_nodes': 0,
            'updated_at': datetime.now().isoformat()
        }
        knowledge_base.redis_client.get.return_value = json.dumps(empty_tree)
        knowledge_base.redis_client.set.return_value = True
        
        # 执行
        result = knowledge_base.update_evolution_tree(sample_evolution_node)
        
        # 验证
        assert result is True
        knowledge_base.redis_client.set.assert_called()
    
    def test_update_evolution_tree_child_node(self, knowledge_base):
        """测试更新演化树（子节点）"""
        # 配置mock
        existing_tree = {
            'nodes': {
                'node_001': {
                    'node_id': 'node_001',
                    'strategy_id': 'strategy_001',
                    'parent_id': None,
                    'children_ids': [],
                    'generation': 0,
                    'fitness_score': 0.85
                }
            },
            'root_nodes': ['node_001'],
            'max_generation': 0,
            'total_nodes': 1,
            'updated_at': datetime.now().isoformat()
        }
        knowledge_base.redis_client.get.return_value = json.dumps(existing_tree)
        knowledge_base.redis_client.set.return_value = True
        
        # 创建子节点
        child_node = EvolutionNode(
            node_id='node_002',
            strategy_id='strategy_002',
            parent_id='node_001',
            children_ids=[],
            generation=1,
            fitness_score=0.90
        )
        
        # 执行
        result = knowledge_base.update_evolution_tree(child_node)
        
        # 验证
        assert result is True
    
    def test_get_evolution_path(self, knowledge_base):
        """测试获取演化路径"""
        # 配置mock
        tree = {
            'nodes': {
                'node_001': {
                    'node_id': 'node_001',
                    'strategy_id': 'strategy_001',
                    'parent_id': None,
                    'children_ids': ['node_002'],
                    'generation': 0,
                    'fitness_score': 0.85
                },
                'node_002': {
                    'node_id': 'node_002',
                    'strategy_id': 'strategy_002',
                    'parent_id': 'node_001',
                    'children_ids': ['node_003'],
                    'generation': 1,
                    'fitness_score': 0.90
                },
                'node_003': {
                    'node_id': 'node_003',
                    'strategy_id': 'strategy_003',
                    'parent_id': 'node_002',
                    'children_ids': [],
                    'generation': 2,
                    'fitness_score': 0.95
                }
            },
            'root_nodes': ['node_001'],
            'max_generation': 2,
            'total_nodes': 3,
            'updated_at': datetime.now().isoformat()
        }
        knowledge_base.redis_client.get.return_value = json.dumps(tree)
        
        # 执行
        path = knowledge_base.get_evolution_path('node_003')
        
        # 验证
        assert len(path) == 3
        assert path[0].node_id == 'node_001'
        assert path[1].node_id == 'node_002'
        assert path[2].node_id == 'node_003'
    
    def test_get_evolution_path_nonexistent(self, knowledge_base):
        """测试获取不存在节点的演化路径"""
        # 配置mock
        empty_tree = {
            'nodes': {},
            'root_nodes': [],
            'max_generation': 0,
            'total_nodes': 0,
            'updated_at': datetime.now().isoformat()
        }
        knowledge_base.redis_client.get.return_value = json.dumps(empty_tree)
        
        # 执行并验证
        with pytest.raises(ValueError, match="节点不存在"):
            knowledge_base.get_evolution_path('nonexistent')



class TestEliteStrategyManagement:
    """测试精英策略管理"""
    
    def test_add_elite_strategy_success(
        self,
        knowledge_base,
        sample_elite_strategy
    ):
        """测试成功添加精英策略"""
        # 配置mock
        knowledge_base.redis_client.sadd.return_value = 1
        knowledge_base.redis_client.set.return_value = True
        
        # 执行
        result = knowledge_base.add_elite_strategy(sample_elite_strategy)
        
        # 验证
        assert result is True
        knowledge_base.redis_client.sadd.assert_called_once()
        knowledge_base.redis_client.set.assert_called_once()
    
    def test_add_elite_strategy_invalid_sharpe(self, knowledge_base):
        """测试添加无效夏普比率的精英策略"""
        strategy = EliteStrategy(
            strategy_id='strategy_001',
            sharpe_ratio=0.0,  # 无效值
            annual_return=0.35,
            max_drawdown=0.12,
            win_rate=0.62,
            added_at=datetime.now().isoformat()
        )
        
        with pytest.raises(ValueError, match="夏普比率必须 > 0"):
            knowledge_base.add_elite_strategy(strategy)
    
    def test_get_elite_strategies(self, knowledge_base):
        """测试获取精英策略列表"""
        # 配置mock
        knowledge_base.redis_client.smembers.return_value = {
            'strategy_001',
            'strategy_002'
        }
        
        strategy1_json = json.dumps({
            'strategy_id': 'strategy_001',
            'sharpe_ratio': 2.5,
            'annual_return': 0.35,
            'max_drawdown': 0.12,
            'win_rate': 0.62,
            'added_at': datetime.now().isoformat()
        })
        
        strategy2_json = json.dumps({
            'strategy_id': 'strategy_002',
            'sharpe_ratio': 1.8,
            'annual_return': 0.25,
            'max_drawdown': 0.15,
            'win_rate': 0.58,
            'added_at': datetime.now().isoformat()
        })
        
        knowledge_base.redis_client.get.side_effect = [
            strategy1_json,
            strategy2_json
        ]
        
        # 执行
        strategies = knowledge_base.get_elite_strategies(min_sharpe=1.5)
        
        # 验证
        assert len(strategies) == 2
        assert strategies[0].sharpe_ratio == 2.5  # 按夏普比率降序
        assert strategies[1].sharpe_ratio == 1.8
    
    def test_get_elite_strategies_with_filter(self, knowledge_base):
        """测试过滤获取精英策略"""
        # 配置mock
        knowledge_base.redis_client.smembers.return_value = {
            'strategy_001',
            'strategy_002'
        }
        
        strategy1_json = json.dumps({
            'strategy_id': 'strategy_001',
            'sharpe_ratio': 2.5,
            'annual_return': 0.35,
            'max_drawdown': 0.12,
            'win_rate': 0.62,
            'added_at': datetime.now().isoformat()
        })
        
        strategy2_json = json.dumps({
            'strategy_id': 'strategy_002',
            'sharpe_ratio': 1.2,  # 低于过滤条件
            'annual_return': 0.15,
            'max_drawdown': 0.18,
            'win_rate': 0.52,
            'added_at': datetime.now().isoformat()
        })
        
        knowledge_base.redis_client.get.side_effect = [
            strategy1_json,
            strategy2_json
        ]
        
        # 执行
        strategies = knowledge_base.get_elite_strategies(min_sharpe=2.0)
        
        # 验证
        assert len(strategies) == 1
        assert strategies[0].sharpe_ratio == 2.5
    
    def test_remove_elite_strategy(self, knowledge_base):
        """测试移除精英策略"""
        # 配置mock
        knowledge_base.redis_client.srem.return_value = 1
        knowledge_base.redis_client.delete.return_value = 1
        
        # 执行
        result = knowledge_base.remove_elite_strategy('strategy_001')
        
        # 验证
        assert result is True
        knowledge_base.redis_client.srem.assert_called_once()
        knowledge_base.redis_client.delete.assert_called_once()


class TestFailedStrategyManagement:
    """测试失败策略管理"""
    
    def test_add_failed_strategy_success(
        self,
        knowledge_base,
        sample_failed_strategy
    ):
        """测试成功添加失败策略"""
        # 配置mock
        knowledge_base.redis_client.sadd.return_value = 1
        knowledge_base.redis_client.set.return_value = True
        
        # 执行
        result = knowledge_base.add_failed_strategy(sample_failed_strategy)
        
        # 验证
        assert result is True
        knowledge_base.redis_client.sadd.assert_called_once()
        knowledge_base.redis_client.set.assert_called_once()
    
    def test_get_failed_strategies(self, knowledge_base):
        """测试获取失败策略列表"""
        # 配置mock
        knowledge_base.redis_client.smembers.return_value = {
            'strategy_failed_001',
            'strategy_failed_002'
        }
        
        strategy1_json = json.dumps({
            'strategy_id': 'strategy_failed_001',
            'failure_reason': '过拟合',
            'failure_type': 'overfitting',
            'lessons_learned': '避免过度优化',
            'failed_at': '2026-01-27T10:00:00'
        })
        
        strategy2_json = json.dumps({
            'strategy_id': 'strategy_failed_002',
            'failure_reason': '流动性不足',
            'failure_type': 'liquidity',
            'lessons_learned': '检查流动性约束',
            'failed_at': '2026-01-27T11:00:00'
        })
        
        knowledge_base.redis_client.get.side_effect = [
            strategy1_json,
            strategy2_json
        ]
        
        # 执行
        strategies = knowledge_base.get_failed_strategies()
        
        # 验证
        assert len(strategies) == 2
    
    def test_get_lessons_learned(self, knowledge_base):
        """测试获取经验教训"""
        # 配置mock
        knowledge_base.redis_client.smembers.return_value = {
            'strategy_failed_001'
        }
        
        strategy_json = json.dumps({
            'strategy_id': 'strategy_failed_001',
            'failure_reason': '过拟合',
            'failure_type': 'overfitting',
            'lessons_learned': '避免在训练集上过度优化',
            'failed_at': datetime.now().isoformat()
        })
        
        knowledge_base.redis_client.get.return_value = strategy_json
        
        # 执行
        lessons = knowledge_base.get_lessons_learned()
        
        # 验证
        assert len(lessons) == 1
        assert '避免在训练集上过度优化' in lessons[0]



class TestAntiPatternManagement:
    """测试反向黑名单管理"""
    
    def test_add_anti_pattern_success(
        self,
        knowledge_base,
        sample_anti_pattern
    ):
        """测试成功添加反模式"""
        # 配置mock
        knowledge_base.redis_client.lpush.return_value = 1
        
        # 执行
        result = knowledge_base.add_anti_pattern(sample_anti_pattern)
        
        # 验证
        assert result is True
        knowledge_base.redis_client.lpush.assert_called_once()
    
    def test_add_anti_pattern_invalid_severity(self, knowledge_base):
        """测试添加无效严重程度的反模式"""
        pattern = AntiPattern(
            pattern_id='pattern_001',
            pattern_name='测试模式',
            description='测试描述',
            detection_rules={},
            severity='invalid',  # 无效值
            added_at=datetime.now().isoformat()
        )
        
        with pytest.raises(ValueError, match="无效的严重程度"):
            knowledge_base.add_anti_pattern(pattern)
    
    def test_get_anti_patterns(self, knowledge_base):
        """测试获取反模式列表"""
        # 配置mock
        pattern1_json = json.dumps({
            'pattern_id': 'pattern_001',
            'pattern_name': '过度交易',
            'description': '频繁交易',
            'detection_rules': {'keywords': ['high_frequency']},
            'severity': 'high',
            'added_at': datetime.now().isoformat()
        })
        
        pattern2_json = json.dumps({
            'pattern_id': 'pattern_002',
            'pattern_name': '数据泄露',
            'description': '使用未来数据',
            'detection_rules': {'keywords': ['future_data']},
            'severity': 'critical',
            'added_at': datetime.now().isoformat()
        })
        
        knowledge_base.redis_client.lrange.return_value = [
            pattern1_json,
            pattern2_json
        ]
        
        # 执行
        patterns = knowledge_base.get_anti_patterns()
        
        # 验证
        assert len(patterns) == 2
    
    def test_get_anti_patterns_with_severity_filter(self, knowledge_base):
        """测试按严重程度过滤反模式"""
        # 配置mock
        pattern1_json = json.dumps({
            'pattern_id': 'pattern_001',
            'pattern_name': '过度交易',
            'description': '频繁交易',
            'detection_rules': {},
            'severity': 'high',
            'added_at': datetime.now().isoformat()
        })
        
        pattern2_json = json.dumps({
            'pattern_id': 'pattern_002',
            'pattern_name': '数据泄露',
            'description': '使用未来数据',
            'detection_rules': {},
            'severity': 'critical',
            'added_at': datetime.now().isoformat()
        })
        
        knowledge_base.redis_client.lrange.return_value = [
            pattern1_json,
            pattern2_json
        ]
        
        # 执行
        patterns = knowledge_base.get_anti_patterns(severity='critical')
        
        # 验证
        assert len(patterns) == 1
        assert patterns[0].severity == 'critical'
    
    def test_check_anti_patterns_match(self, knowledge_base):
        """测试检查反模式匹配"""
        # 配置mock
        pattern_json = json.dumps({
            'pattern_id': 'pattern_001',
            'pattern_name': '过度交易',
            'description': '频繁交易',
            'detection_rules': {'keywords': ['high_frequency', 'day_trading']},
            'severity': 'high',
            'added_at': datetime.now().isoformat()
        })
        
        knowledge_base.redis_client.lrange.return_value = [pattern_json]
        
        # 执行
        strategy_code = "def strategy(): high_frequency_trading()"
        matched = knowledge_base.check_anti_patterns(strategy_code)
        
        # 验证
        assert len(matched) == 1
        assert matched[0].pattern_name == '过度交易'
    
    def test_check_anti_patterns_no_match(self, knowledge_base):
        """测试检查反模式无匹配"""
        # 配置mock
        pattern_json = json.dumps({
            'pattern_id': 'pattern_001',
            'pattern_name': '过度交易',
            'description': '频繁交易',
            'detection_rules': {'keywords': ['high_frequency']},
            'severity': 'high',
            'added_at': datetime.now().isoformat()
        })
        
        knowledge_base.redis_client.lrange.return_value = [pattern_json]
        
        # 执行
        strategy_code = "def strategy(): normal_trading()"
        matched = knowledge_base.check_anti_patterns(strategy_code)
        
        # 验证
        assert len(matched) == 0


class TestKnowledgeSearch:
    """测试知识检索"""
    
    def test_search_knowledge_all_types(self, knowledge_base):
        """测试搜索所有类型的知识"""
        # 配置mock
        knowledge_base.redis_client.scan_iter.return_value = []
        knowledge_base.redis_client.smembers.return_value = set()
        knowledge_base.redis_client.lrange.return_value = []
        
        # 执行
        results = knowledge_base.search_knowledge('test')
        
        # 验证
        assert 'gene_capsules' in results
        assert 'elite_strategies' in results
        assert 'failed_strategies' in results
        assert 'anti_patterns' in results
    
    def test_search_knowledge_specific_types(self, knowledge_base):
        """测试搜索特定类型的知识"""
        # 配置mock
        knowledge_base.redis_client.smembers.return_value = set()
        
        # 执行
        results = knowledge_base.search_knowledge(
            'test',
            knowledge_types=['elite_strategy']
        )
        
        # 验证
        assert 'elite_strategies' in results
        assert 'gene_capsules' not in results
    
    def test_search_knowledge_invalid_type(self, knowledge_base):
        """测试搜索无效类型"""
        with pytest.raises(ValueError, match="无效的知识类型"):
            knowledge_base.search_knowledge(
                'test',
                knowledge_types=['invalid_type']
            )
    
    def test_get_knowledge_statistics(self, knowledge_base):
        """测试获取知识库统计"""
        # 配置mock
        knowledge_base.redis_client.scan_iter.return_value = ['key1', 'key2']
        knowledge_base.redis_client.scard.return_value = 5
        knowledge_base.redis_client.llen.return_value = 3
        
        tree_json = json.dumps({
            'nodes': {},
            'root_nodes': [],
            'max_generation': 10,
            'total_nodes': 50,
            'updated_at': datetime.now().isoformat()
        })
        knowledge_base.redis_client.get.return_value = tree_json
        
        # 执行
        stats = knowledge_base.get_knowledge_statistics()
        
        # 验证
        assert 'gene_capsules' in stats
        assert 'elite_strategies' in stats
        assert 'failed_strategies' in stats
        assert 'anti_patterns' in stats
        assert 'evolution_nodes' in stats
        assert 'max_generation' in stats
        assert stats['max_generation'] == 10
        assert stats['evolution_nodes'] == 50


class TestKnowledgeClear:
    """测试知识清空"""
    
    def test_clear_gene_capsule(self, knowledge_base):
        """测试清空基因胶囊"""
        # 配置mock
        knowledge_base.redis_client.scan_iter.return_value = [
            'mia:knowledge:gene_capsule:001'
        ]
        knowledge_base.redis_client.delete.return_value = 1
        
        # 执行
        result = knowledge_base.clear_knowledge('gene_capsule')
        
        # 验证
        assert result is True
        knowledge_base.redis_client.delete.assert_called()
    
    def test_clear_elite_strategy(self, knowledge_base):
        """测试清空精英策略"""
        # 配置mock
        knowledge_base.redis_client.scan_iter.return_value = []
        knowledge_base.redis_client.delete.return_value = 1
        
        # 执行
        result = knowledge_base.clear_knowledge('elite_strategy')
        
        # 验证
        assert result is True
    
    def test_clear_invalid_type(self, knowledge_base):
        """测试清空无效类型"""
        with pytest.raises(ValueError, match="无效的知识类型"):
            knowledge_base.clear_knowledge('invalid_type')


class TestErrorHandling:
    """测试错误处理"""
    
    def test_redis_error_on_store(self, knowledge_base, sample_gene_capsule):
        """测试存储时Redis错误"""
        # 配置mock抛出异常
        knowledge_base.redis_client.set.side_effect = redis.RedisError("连接失败")
        
        # 执行并验证
        with pytest.raises(redis.RedisError):
            knowledge_base.store_gene_capsule(sample_gene_capsule)
    
    def test_redis_error_on_get(self, knowledge_base):
        """测试获取时Redis错误"""
        # 配置mock抛出异常
        knowledge_base.redis_client.get.side_effect = redis.RedisError("连接失败")
        
        # 执行并验证
        with pytest.raises(redis.RedisError):
            knowledge_base.get_gene_capsule('capsule_001')
    
    def test_invalid_json_on_get(self, knowledge_base):
        """测试获取时JSON解析错误"""
        # 配置mock返回无效JSON
        knowledge_base.redis_client.get.return_value = "invalid json"
        
        # 执行
        result = knowledge_base.get_gene_capsule('capsule_001')
        
        # 验证
        assert result is None


class TestPerformanceRequirements:
    """测试性能要求"""
    
    def test_store_gene_capsule_performance(
        self,
        knowledge_base,
        sample_gene_capsule
    ):
        """测试基因胶囊存储性能 < 10ms"""
        import time
        
        # 配置mock
        knowledge_base.redis_client.set.return_value = True
        knowledge_base.redis_client.sadd.return_value = 1
        
        # 执行并计时
        start = time.perf_counter()
        knowledge_base.store_gene_capsule(sample_gene_capsule)
        elapsed = time.perf_counter() - start
        
        # 验证性能
        assert elapsed < 0.010, f"存储延迟 {elapsed*1000:.2f}ms > 10ms"
    
    def test_get_gene_capsule_performance(self, knowledge_base):
        """测试基因胶囊检索性能 < 50ms"""
        import time
        
        # 配置mock
        capsule_json = json.dumps({
            'capsule_id': 'capsule_001',
            'strategy_id': 'strategy_001',
            'certification_tier': 'Gold',
            'performance_metrics': {},
            'metadata': {},
            'created_at': datetime.now().isoformat()
        })
        knowledge_base.redis_client.get.return_value = capsule_json
        
        # 执行并计时
        start = time.perf_counter()
        knowledge_base.get_gene_capsule('capsule_001')
        elapsed = time.perf_counter() - start
        
        # 验证性能
        assert elapsed < 0.050, f"检索延迟 {elapsed*1000:.2f}ms > 50ms"
    
    def test_build_evolution_tree_performance(self, knowledge_base):
        """测试演化树构建性能 < 100ms"""
        import time
        
        # 配置mock
        tree_json = json.dumps({
            'nodes': {},
            'root_nodes': [],
            'max_generation': 0,
            'total_nodes': 0,
            'updated_at': datetime.now().isoformat()
        })
        knowledge_base.redis_client.get.return_value = tree_json
        
        # 执行并计时
        start = time.perf_counter()
        knowledge_base.build_evolution_tree()
        elapsed = time.perf_counter() - start
        
        # 验证性能
        assert elapsed < 0.100, f"构建延迟 {elapsed*1000:.2f}ms > 100ms"


class TestConnectionManagement:
    """测试连接管理"""
    
    def test_close_connection(self, knowledge_base):
        """测试关闭连接"""
        # 配置mock
        knowledge_base.redis_client.close = Mock()
        knowledge_base.connection_pool.disconnect = Mock()
        
        # 执行
        knowledge_base.close()
        
        # 验证
        knowledge_base.redis_client.close.assert_called_once()
        knowledge_base.connection_pool.disconnect.assert_called_once()
