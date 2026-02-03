# 第七章：安全架构与统一安全网关 (Security Architecture & Unified Security Gateway)

**版本**: v1.0.0  
**日期**: 2026-01-23  
**优先级**: 🚨 CRITICAL  
**状态**: Phase 1 - Docker加固方案

---

## 7.0 安全架构概述

MIA系统作为一个具备自主进化能力的硅基生命体，其安全架构必须确保在AI代码生成和执行过程中的绝对安全。根据安全审计发现，系统中6个元进化组件中有4个存在严重安全缺口，需要建立工业级统一安全网关。

**核心安全哲学**：
- **零信任原则**: 所有AI生成的代码都是不可信的
- **纵深防御**: 7层安全机制，任何单层失败不导致系统失败
- **最小权限**: 默认拒绝，显式授权
- **完整审计**: 所有操作可追溯
- **性能优先**: 安全检查不能显著影响系统性能

---

## 7.1 统一安全网关 (UnifiedSecurityGateway)

### 7.1.1 架构设计

统一安全网关是MIA系统所有AI代码生成和执行的唯一入口，提供7层纵深防御：

```
┌─────────────────────────────────────────────────────────────────┐
│                    UnifiedSecurityGateway                        │
│                     (统一安全网关)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      7层纵深防御                                  │
├─────────────────────────────────────────────────────────────────┤
│ Layer 1: 内容类型识别 (ContentTypeDetector)                      │
│ Layer 2: AST白名单验证 (ASTWhitelistValidator)                   │
│ Layer 3: 语义验证 (SemanticValidator)                            │
│ Layer 4: 沙箱隔离 (SandboxManager)                               │
│ Layer 5: 网络防护 (NetworkGuard)                                 │
│ Layer 6: 资源限制 (ResourceLimiter)                              │
│ Layer 7: 审计日志 (AuditLogger)                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      受保护组件                                   │
├─────────────────────────────────────────────────────────────────┤
│ • AlgoEvolutionSentinel (算法进化哨兵)                           │
│ • FactorMiningIntelligenceSentinel (因子挖掘智能哨兵)            │
│ • GeneticMiner (遗传算法挖掘器)                                  │
│ • MetaEvolution (元进化引擎)                                     │
└─────────────────────────────────────────────────────────────────┘
```

### 7.1.2 核心接口

```python
class UnifiedSecurityGateway:
    """统一安全网关
    
    白皮书依据: 第七章 7.1 统一安全网关
    
    提供统一的安全验证和执行接口，所有元进化组件必须通过此网关。
    """
    
    async def validate_and_execute(
        self,
        content: str,
        content_type: ContentType,
        context: SecurityContext
    ) -> ValidationResult:
        """验证并执行内容
        
        Args:
            content: 要验证的内容（代码/提示词/配置/表达式）
            content_type: 内容类型枚举
            context: 安全上下文（组件名、用户ID、隔离级别等）
            
        Returns:
            ValidationResult: 验证结果（通过/拒绝、原因、详细信息）
        """
        pass
```

### 7.1.3 内容类型

```python
class ContentType(Enum):
    """内容类型"""
    CODE = "code"              # Python代码
    PROMPT = "prompt"          # 提示词
    CONFIG = "config"          # 配置文件
    EXPRESSION = "expression"  # 因子表达式
```

### 7.1.4 隔离级别

```python
class IsolationLevel(Enum):
    """隔离级别"""
    FIRECRACKER = "firecracker"  # Firecracker microVM (Phase 2)
    GVISOR = "gvisor"            # gVisor用户空间内核 (Phase 2)
    DOCKER = "docker"            # Docker容器 (Phase 1)
    BUBBLEWRAP = "bubblewrap"    # OS级沙箱
    NONE = "none"                # 仅AST验证
```

---

## 7.2 AST白名单验证 (ASTWhitelistValidator)

### 7.2.1 验证原理

基于抽象语法树(AST)分析验证代码安全性，通过白名单和黑名单机制阻止恶意代码。

### 7.2.2 白名单函数

```python
WHITELIST_FUNCTIONS = {
    # 数学函数
    'abs', 'min', 'max', 'sum', 'round', 'pow',
    'math.sqrt', 'math.log', 'math.exp',
    
    # Pandas/Numpy
    'pd.Series', 'pd.DataFrame', 'np.array', 'np.mean',
    'np.std', 'np.sum', 'np.abs',
    
    # 因子算子
    'rank', 'delay', 'delta', 'ts_mean', 'ts_std',
    'ts_sum', 'ts_rank', 'correlation', 'covariance'
}
```

### 7.2.3 黑名单函数

```python
BLACKLIST_FUNCTIONS = {
    # 危险函数
    'eval', 'exec', 'compile', '__import__',
    
    # 文件操作
    'open', 'file', 'read', 'write',
    
    # 系统调用
    'os.system', 'subprocess.call', 'subprocess.run',
    'subprocess.Popen',
    
    # 网络操作
    'socket.socket', 'requests.get', 'requests.post',
    'urllib.request', 'http.client',
    
    # 序列化
    'pickle.load', 'pickle.loads', 'pickle.dump'
}
```

### 7.2.4 黑名单模块

```python
BLACKLIST_MODULES = {
    'os', 'sys', 'subprocess', 'socket', 'pickle',
    'ctypes', 'multiprocessing', 'threading'
}
```

### 7.2.5 验证规则

1. **语法检查**: 使用ast.parse验证语法
2. **函数调用检查**: 检查黑名单函数
3. **模块导入检查**: 检查黑名单模块
4. **复杂度检查**: 限制代码复杂度
5. **深度检查**: 限制AST树深度

---

## 7.3 Docker沙箱 (DockerSandbox)

### 7.3.1 沙箱配置

```bash
--user 1001:1001          # 非root用户
--read-only               # 只读文件系统
--tmpfs /tmp:rw,noexec    # 临时文件系统
--cap-drop ALL            # 移除所有capabilities
--security-opt no-new-privileges
--memory="512m"           # 内存限制
--cpus="1.0"              # CPU限制
--pids-limit 100          # 进程数限制
--network none            # 无网络
```

### 7.3.2 seccomp配置

使用seccomp-bpf限制系统调用，只允许必要的系统调用，阻止危险操作。

配置文件: `config/seccomp-profile.json`

### 7.3.3 容器生命周期

1. **创建**: 基于预构建镜像创建容器
2. **配置**: 应用seccomp、cgroups、namespaces
3. **执行**: 运行代码
4. **清理**: 销毁容器

### 7.3.4 性能优化

- **容器池**: 预创建容器减少启动开销
- **容器复用**: 相同配置的容器可复用
- **异步执行**: 不阻塞主流程

---

## 7.4 网络防护 (NetworkGuard)

### 7.4.1 防护策略

1. **默认拒绝**: 默认禁止所有网络访问
2. **白名单**: 仅允许白名单域名
3. **黑名单**: 阻止内部地址访问
4. **DNS监控**: 记录所有DNS查询
5. **流量分析**: 检测异常流量模式

### 7.4.2 白名单域名

```python
WHITELIST_DOMAINS = {
    # Python包
    'pypi.org',
    'files.pythonhosted.org',
    
    # npm包
    'registry.npmjs.org',
    
    # 数据源（根据需要添加）
    # 'api.example.com'
}
```

### 7.4.3 黑名单IP段

```python
BLACKLIST_IP_RANGES = {
    '10.0.0.0/8',
    '172.16.0.0/12',
    '192.168.0.0/16',
    '169.254.169.254/32',  # AWS元数据
    '127.0.0.0/8',         # 本地回环
}
```

### 7.4.4 实现方式

- Docker网络模式：`--network none`（默认）
- 自定义网络：使用iptables规则
- DNS拦截：自定义DNS服务器

---

## 7.5 审计日志 (AuditLogger)

### 7.5.1 日志内容

```python
@dataclass
class AuditEvent:
    """审计事件"""
    timestamp: float             # 时间戳
    event_type: str              # 事件类型
    source_component: str        # 来源组件
    user_id: str                 # 用户ID
    session_id: str              # 会话ID
    content_hash: str            # 内容哈希
    isolation_level: str         # 隔离级别
    approved: bool               # 是否通过
    execution_time_ms: float     # 执行时间
    memory_used_mb: float        # 内存使用
    security_violations: List[str]  # 安全违规
    result: str                  # 执行结果
```

### 7.5.2 存储方式

- **本地文件**: `logs/security/audit_{date}.log`
- **结构化日志**: JSON格式
- **异步写入**: 不阻塞主流程

### 7.5.3 告警机制

- 安全违规立即告警
- 告警包含完整上下文
- 告警发送到监控系统

---

## 7.6 错误处理

### 7.6.1 错误分类

```python
class SecurityErrorType(Enum):
    """安全错误类型"""
    VALIDATION_FAILED = "validation_failed"
    BLACKLIST_DETECTED = "blacklist_detected"
    SANDBOX_FAILED = "sandbox_failed"
    TIMEOUT_EXCEEDED = "timeout_exceeded"
    MEMORY_EXCEEDED = "memory_exceeded"
    NETWORK_VIOLATION = "network_violation"
    EXECUTION_FAILED = "execution_failed"
```

### 7.6.2 错误处理策略

**验证失败**:
- 记录详细错误信息
- 返回ValidationResult(approved=False)
- 不执行代码
- 发送告警（如果是CRITICAL级别）

**沙箱失败**:
- 记录容器创建/执行失败
- 清理残留容器
- 返回ExecutionResult(success=False)
- 发送告警

**超时**:
- 强制终止容器
- 记录超时事件
- 返回超时错误
- 不重试（避免资源浪费）

**资源超限**:
- 终止执行
- 记录资源使用情况
- 返回资源超限错误
- 调整资源限制（如果需要）

**网络违规**:
- 阻止网络访问
- 记录违规尝试
- 发送高优先级告警
- 可能标记组件为高风险

### 7.6.3 降级策略

**Docker不可用**:
- 降级到BUBBLEWRAP隔离
- 如果BUBBLEWRAP也不可用，降级到NONE（仅AST验证）
- 记录降级事件
- 发送告警

**性能降级**:
- 如果延迟 > 150ms，启用容器池
- 如果延迟 > 300ms，增加容器池大小
- 如果延迟 > 500ms，考虑异步执行

**审计日志失败**:
- 不阻塞主流程
- 缓存日志到内存
- 异步重试写入
- 如果持续失败，发送告警

---

## 7.7 测试策略

### 7.7.1 测试方法

本系统采用**双重测试方法**：
- **单元测试**: 验证具体示例、边界条件、错误情况
- **属性测试**: 验证通用属性在所有输入下都成立

### 7.7.2 单元测试

**测试覆盖率**: ≥ 85%

**测试文件结构**:
```
tests/unit/evolution/security/
├── test_unified_security_gateway.py
├── test_ast_validator.py
├── test_docker_sandbox.py
├── test_network_guard.py
└── test_audit_logger.py
```

### 7.7.3 属性测试

**测试配置**: 每个属性测试运行 ≥ 100 次迭代

**测试文件结构**:
```
tests/properties/evolution/security/
├── test_security_properties.py
└── generators.py
```

### 7.7.4 性能测试

**性能指标**:
- AST验证延迟: < 1ms (P99)
- Docker容器启动: < 100ms (P99)
- 代码执行: < 20ms (P99)
- 审计日志写入: < 5ms (P99)
- 总体延迟: < 150ms (P99)

---

## 7.8 系统集成

### 7.8.1 与现有组件集成

#### 集成DevilAuditor

**现有组件**: `src/brain/devil_auditor.py`

**集成方式**:
- UnifiedSecurityGateway作为第一道防线（AST + 沙箱）
- DevilAuditor作为第二道防线（深度推理审计）
- 流程：代码 → SecurityGateway验证 → 沙箱执行 → DevilAuditor审计

#### 集成SemanticValidator

**现有组件**: `src/evolution/expression_types.py`

**集成方式**:
- 因子表达式先通过SemanticValidator（类型检查）
- 再通过UnifiedSecurityGateway（AST + 沙箱）
- 流程：表达式 → SemanticValidator → SecurityGateway → 执行

### 7.8.2 与事件总线集成

**事件定义**:
```python
class SecurityEventType(Enum):
    VALIDATION_REQUEST = "security.validation_request"
    VALIDATION_COMPLETED = "security.validation_completed"
    SECURITY_VIOLATION = "security.security_violation"
    SANDBOX_CREATED = "security.sandbox_created"
    SANDBOX_DESTROYED = "security.sandbox_destroyed"
```

### 7.8.3 配置管理

**配置文件**: `config/security.yaml`

```yaml
security:
  default_isolation_level: docker
  default_timeout_ms: 30000
  default_memory_mb: 512
  default_cpu_cores: 1.0
  
  docker:
    image: mia-sandbox:latest
    user: "1001:1001"
    read_only: true
    network_mode: none
    seccomp_profile: config/seccomp-profile.json
  
  whitelist:
    functions:
      - abs
      - min
      - max
      - sum
      - round
      - pd.Series
      - pd.DataFrame
      - np.array
    
    modules:
      - pandas
      - numpy
      - math
    
    domains:
      - pypi.org
      - files.pythonhosted.org
  
  blacklist:
    functions:
      - eval
      - exec
      - compile
      - __import__
      - open
      - os.system
      - subprocess.call
      - pickle.load
    
    modules:
      - os
      - sys
      - subprocess
      - socket
      - pickle
  
  audit:
    log_path: logs/security
    alert_webhook: null
    retention_days: 90
```

---

## 7.9 性能优化

### 7.9.1 容器池化

**问题**: Docker容器启动有开销（~100ms）

**解决方案**: 容器池

**效果**:
- 首次执行：~100ms（创建容器）
- 后续执行：~20ms（复用容器）
- 平均延迟降低：80%

### 7.9.2 AST缓存

**问题**: 相同代码重复验证浪费资源

**解决方案**: AST验证结果缓存

**效果**:
- 缓存命中：<0.1ms
- 缓存未命中：~1ms
- 对于重复代码，性能提升：10×

### 7.9.3 异步执行

**问题**: 同步执行阻塞主流程

**解决方案**: 异步执行 + 回调

### 7.9.4 批量处理

**问题**: 单个请求处理效率低

**解决方案**: 批量处理

**效果**:
- 10个请求串行：~1500ms
- 10个请求并行：~200ms
- 吞吐量提升：7.5×

---

## 7.10 监控告警

### 7.10.1 监控指标

**性能指标**:
- `security.validation.latency_ms`: 验证延迟（P50, P95, P99）
- `security.execution.latency_ms`: 执行延迟（P50, P95, P99）
- `security.container.startup_ms`: 容器启动时间
- `security.audit.write_latency_ms`: 审计日志写入延迟

**业务指标**:
- `security.validation.total`: 总验证次数
- `security.validation.approved`: 通过验证次数
- `security.validation.rejected`: 拒绝验证次数
- `security.violations.total`: 安全违规总数
- `security.violations.by_type`: 按类型分组的违规数

**资源指标**:
- `security.container.active`: 活跃容器数
- `security.container.pool_size`: 容器池大小
- `security.memory.used_mb`: 内存使用量
- `security.cpu.usage_percent`: CPU使用率

### 7.10.2 告警规则

**Critical告警**:
- 安全违规率 > 5%
- 容器逃逸尝试
- 黑名单函数检测率 > 1%
- 审计日志写入失败率 > 1%

**Warning告警**:
- P99延迟 > 300ms
- 容器池耗尽
- 内存使用 > 80%
- CPU使用 > 85%

**Info告警**:
- 新的安全模式检测
- 配置变更
- 容器池扩容

---

## 7.11 未来扩展

### 7.11.1 Phase 2: Firecracker集成

**时间**: Phase 1完成后2-3周

**目标**: 升级到Firecracker microVM，提供更强的隔离

**实施步骤**:
1. 安装Firecracker和配置KVM
2. 实现FirecrackerSandbox类
3. 创建Firecracker镜像
4. 性能测试和优化
5. 逐步迁移（先高风险组件）

### 7.11.2 Phase 3: gVisor集成

**时间**: Phase 2完成后1-2周

**目标**: 提供gVisor作为备选隔离方案

**优势**:
- 比Docker更强的隔离
- 比Firecracker更轻量
- 与Kubernetes兼容

### 7.11.3 机器学习增强

**目标**: 使用ML检测异常代码模式

**方法**:
- 训练代码嵌入模型
- 检测异常代码模式
- 预测安全风险
- 自动更新黑名单

### 7.11.4 分布式部署

**目标**: 支持多节点部署，提高吞吐量

**架构**:
- 负载均衡器
- 多个SecurityGateway节点
- 共享审计日志存储
- 分布式容器池

---

## 7.T 测试要求与标准

### 7.T.1 单元测试要求

**测试覆盖率目标**: ≥ 85%

**测试文件**: `tests/unit/evolution/security/`

**核心测试用例**:
- 所有公共函数必须有对应的单元测试
- 边界条件测试（空输入、极值、异常值）
- 异常处理测试（错误输入、超时、资源不足）
- 性能基准测试（延迟、吞吐量、资源使用）

**测试标准**:
- ✅ 函数级测试覆盖率 ≥ 90%
- ✅ 分支覆盖率 ≥ 80%
- ✅ 所有异常路径有测试
- ✅ 所有边界条件有测试

### 7.T.2 集成测试要求

**测试覆盖率目标**: ≥ 75%

**测试文件**: `tests/integration/evolution/security/`

**核心测试场景**:
- 模块间接口测试
- 数据流完整性测试
- 并发场景测试
- 故障恢复测试

**测试标准**:
- ✅ 关键流程端到端测试
- ✅ 模块间交互测试
- ✅ 异常场景恢复测试
- ✅ 性能回归测试

### 7.T.3 性能测试要求

**性能指标**:
- 延迟测试（P50, P95, P99）
- 吞吐量测试（QPS, TPS）
- 资源使用测试（CPU, 内存, GPU）
- 压力测试（峰值负载）

**测试标准**:
- ✅ 性能基准建立
- ✅ 性能回归检测
- ✅ 资源使用监控
- ✅ 瓶颈识别与优化

### 7.T.4 安全测试要求

**测试场景**:
- 恶意代码注入：尝试注入eval、exec等危险函数
- 沙箱逃逸：尝试访问宿主机文件系统
- 网络攻击：尝试访问内部网络地址
- 资源耗尽：尝试消耗大量内存/CPU
- 权限提升：尝试获取root权限

**测试方法**:
- 使用已知的恶意代码模式
- 模拟攻击场景
- 验证所有攻击都被阻止
- 验证所有攻击都被记录

---

## 7.总结

第七章定义了MIA系统的完整安全架构，包括：

1. **统一安全网关**: 所有AI代码生成和执行的唯一入口
2. **7层纵深防御**: 从内容识别到审计日志的完整安全链
3. **核心组件**: ASTWhitelistValidator、DockerSandbox、NetworkGuard、AuditLogger
4. **完整的错误处理**: 覆盖所有异常情况
5. **双重测试策略**: 单元测试 + 属性测试
6. **性能优化**: 容器池、AST缓存、异步执行、批量处理
7. **监控告警**: 完整的指标和告警规则
8. **渐进式实施**: Phase 1 Docker → Phase 2 Firecracker → Phase 3 gVisor

**关键指标**:
- 总延迟: < 150ms (P99)
- 测试覆盖率: > 85%
- 安全违规检测率: 100%
- 系统可用性: 99.9%

**受保护组件**:
- AlgoEvolutionSentinel (算法进化哨兵) - EXTREME RISK
- FactorMiningIntelligenceSentinel (因子挖掘智能哨兵) - EXTREME RISK
- GeneticMiner (遗传算法挖掘器) - HIGH RISK
- MetaEvolution (元进化引擎) - HIGH RISK

通过统一安全网关，MIA系统实现了工业级的安全防护，确保在AI自主进化过程中的绝对安全。
