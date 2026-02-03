# MIA System PRD - AI Agent Governance Document

🧪 **Hook触发测试标记** - 测试 prd-sync-on-change.kiro.hook

```yaml
# ============================================================================
# MIA SYSTEM PRD v1.0.0
# AI Agent Executable Product Requirements Document
# ============================================================================
# 文档类型: 机器可执行PRD (面向AI Agent)
# 法律效力: 系统当前版本最高裁决文本 (Source of Truth)
# 约束范围: 所有AI Agent、自动化流程、人工决策
# 生成日期: 2026-01-28
# 白皮书依据: 00_核心文档/mia.md v1.6.1
# ============================================================================

prd_metadata:
  version: "1.0.0"
  generated_at: "2026-01-28T00:00:00Z"
  source_documents:
    - path: "00_核心文档/mia.md"
      version: "v1.6.1"
    - path: ".kiro/specs/codebase-retention-audit/requirements.md"
      version: "v1.0.0"
    - path: ".kiro/specs/codebase-retention-audit/design.md"
      version: "v1.0.0"
  classification: "TOP_SECRET"
  status: "INDUSTRIAL_GRADE"

# ============================================================================
# 最高原则 (SUPREME_PRINCIPLES) - 不可违背
# ============================================================================
supreme_principles:
  - id: SP-001
    name: "默认不信任任何LLM输出"
    enforcement: MANDATORY
    violation_action: REJECT_AND_HALT
    
  - id: SP-002
    name: "无证据即无效"
    enforcement: MANDATORY
    violation_action: MARK_AS_BLOCKED
    
  - id: SP-003
    name: "未知必须中断"
    enforcement: MANDATORY
    violation_action: HALT_EXECUTION
    
  - id: SP-004
    name: "测试是唯一合法的行为证明"
    enforcement: MANDATORY
    violation_action: REJECT_IMPLEMENTATION

  - id: SP-005
    name: "PRD高于代码，测试高于实现"
    enforcement: MANDATORY
    violation_action: ROLLBACK_CHANGES

# ============================================================================
# 1. PRODUCT_REQUIREMENTS - 功能性需求
# ============================================================================
product_requirements:

  # --------------------------------------------------------------------------
  # 1.1 代码库审计系统 (Codebase Retention Audit)
  # --------------------------------------------------------------------------
  codebase_retention_audit:
    
    - id: PRD-CRA-001
      name: "文件分类系统"
      description: "对代码库中的每个文件进行唯一分类"
      boundary:
        input: "代码库文件路径"
        output: "分类结果 (CORE|SUPPORTING|CANDIDATE|BLOCKED)"
        scope: "src/, tests/, config/, 00_核心文档/"
      acceptance_criteria:
        - criterion: "每个文件必须且只能被分类为四类之一"
          verification: "property_test"
          pass_condition: "classification IN {CORE, SUPPORTING, CANDIDATE, BLOCKED}"
          fail_condition: "classification IS NULL OR classification NOT IN allowed_set"
        - criterion: "被入口文件引用的文件必须分类为CORE"
          verification: "unit_test"
          pass_condition: "referenced_by_entry_point => classification == CORE"
        - criterion: "测试覆盖率>0%的文件必须分类为CORE"
          verification: "unit_test"
          pass_condition: "test_coverage > 0 => classification == CORE"
        - criterion: "白皮书中明确提及的文件必须分类为CORE"
          verification: "unit_test"
          pass_condition: "mentioned_in_whitepaper => classification == CORE"
      whitepaper_reference: "待添加到白皮书"
      
    - id: PRD-CRA-002
      name: "证据收集系统"
      description: "收集每个文件的引用证据"
      boundary:
        input: "文件路径"
        output: "证据列表 (Evidence[])"
        scope: "import分析, 测试覆盖, PRD绑定, 构建依赖"
      acceptance_criteria:
        - criterion: "使用AST解析Python导入关系"
          verification: "unit_test"
          pass_condition: "ast.parse() succeeds AND imports extracted"
        - criterion: "从coverage.json提取测试覆盖数据"
          verification: "unit_test"
          pass_condition: "coverage_data loaded AND parsed"
        - criterion: "扫描白皮书提取文件/类/函数引用"
          verification: "unit_test"
          pass_condition: "whitepaper_references extracted"
        - criterion: "每条证据必须包含来源和置信度"
          verification: "property_test"
          pass_condition: "evidence.source IS NOT NULL AND 0.0 <= evidence.confidence <= 1.0"
      whitepaper_reference: "待添加到白皮书"

    - id: PRD-CRA-003
      name: "依赖图构建"
      description: "构建完整的文件依赖图"
      boundary:
        input: "项目根目录"
        output: "有向依赖图 (Dict[Path, DependencyNode])"
        scope: "所有Python文件"
      acceptance_criteria:
        - criterion: "构建有向依赖图"
          verification: "unit_test"
          pass_condition: "graph.nodes > 0 AND graph.edges defined"
        - criterion: "识别入口文件"
          verification: "unit_test"
          pass_condition: "entry_points identified (no incoming edges)"
        - criterion: "检测循环依赖"
          verification: "property_test"
          pass_condition: "circular_deps detected AND marked"
        - criterion: "双向一致性"
          verification: "property_test"
          pass_condition: "A imports B => B.imported_by contains A"
      whitepaper_reference: "待添加到白皮书"

    - id: PRD-CRA-004
      name: "审计报告生成"
      description: "生成YAML格式的审计报告"
      boundary:
        input: "分类结果列表"
        output: "YAML审计报告"
        scope: "metadata, summary, files, human_review_queue"
      acceptance_criteria:
        - criterion: "报告必须为有效YAML格式"
          verification: "property_test"
          pass_condition: "yaml.safe_load(report) succeeds"
        - criterion: "摘要统计必须准确"
          verification: "property_test"
          pass_condition: "summary.core == count(files where classification==CORE)"
        - criterion: "CANDIDATE文件必须包含deletion_impact"
          verification: "property_test"
          pass_condition: "classification==CANDIDATE => deletion_impact IS NOT NULL"
        - criterion: "BLOCKED文件必须包含blocked_reason"
          verification: "property_test"
          pass_condition: "classification==BLOCKED => blocked_reason IS NOT NULL"
      whitepaper_reference: "待添加到白皮书"

    - id: PRD-CRA-005
      name: "人工审批流程"
      description: "对CANDIDATE和BLOCKED文件进行人工审批"
      boundary:
        input: "待审批文件列表"
        output: "审批决策 (approve|reject|defer)"
        scope: "Human_Approval_Queue"
      acceptance_criteria:
        - criterion: "CANDIDATE文件必须加入审批队列"
          verification: "unit_test"
          pass_condition: "classification==CANDIDATE => in_approval_queue"
        - criterion: "BLOCKED文件必须加入审批队列"
          verification: "unit_test"
          pass_condition: "classification==BLOCKED => in_approval_queue"
        - criterion: "维护完整审计轨迹"
          verification: "unit_test"
          pass_condition: "audit_trail contains all decisions"
      whitepaper_reference: "待添加到白皮书"

    - id: PRD-CRA-006
      name: "安全保护机制"
      description: "确保审计工具不会意外删除文件"
      boundary:
        input: "审计操作"
        output: "只读操作结果"
        scope: "整个代码库"
      acceptance_criteria:
        - criterion: "审计器绝不执行删除操作"
          verification: "property_test"
          pass_condition: "NO file.delete() calls in audit code"
        - criterion: "审计器以只读模式运行"
          verification: "property_test"
          pass_condition: "source_codebase unchanged after audit"
        - criterion: "有CORE依赖的文件不能分类为CANDIDATE"
          verification: "property_test"
          pass_condition: "has_core_dependency => classification != CANDIDATE"
        - criterion: "受保护文件不能分类为CANDIDATE"
          verification: "property_test"
          pass_condition: "matches_protected_pattern => classification != CANDIDATE"
        - criterion: "证据不足时默认分类为BLOCKED"
          verification: "property_test"
          pass_condition: "insufficient_evidence => classification == BLOCKED"
      whitepaper_reference: "待添加到白皮书"

    - id: PRD-CRA-007
      name: "验证文件导出"
      description: "将验证通过的文件导出到指定目录"
      boundary:
        input: "分类结果, 目标目录"
        output: "导出清单 (ExportManifest)"
        scope: "CORE和SUPPORTING文件"
      acceptance_criteria:
        - criterion: "只导出CORE和SUPPORTING文件"
          verification: "property_test"
          pass_condition: "exported_files.all(f => f.classification IN {CORE, SUPPORTING})"
        - criterion: "保持原始目录结构"
          verification: "property_test"
          pass_condition: "relative_path(exported) == relative_path(source)"
        - criterion: "导出清单完整"
          verification: "property_test"
          pass_condition: "manifest.count == actual_exported_count"
        - criterion: "导出代码库可运行"
          verification: "integration_test"
          pass_condition: "all CORE transitive dependencies present"
      whitepaper_reference: "待添加到白皮书"

  # --------------------------------------------------------------------------
  # 1.2 AI三脑系统 (Tri-Brain Architecture)
  # --------------------------------------------------------------------------
  tri_brain_architecture:
    
    - id: PRD-TBA-001
      name: "Soldier快系统"
      description: "本地快速决策引擎"
      boundary:
        input: "市场上下文 (MarketContext)"
        output: "交易决策 (Decision)"
        scope: "实时交易决策"
      acceptance_criteria:
        - criterion: "决策延迟P99 < 150ms"
          verification: "performance_test"
          pass_condition: "latency_p99 < 150"
        - criterion: "支持热备切换"
          verification: "integration_test"
          pass_condition: "failover_latency < 200ms"
        - criterion: "无循环依赖"
          verification: "static_analysis"
          pass_condition: "no circular imports with Commander/Scholar"
      whitepaper_reference: "第二章 2.1 Soldier"

    - id: PRD-TBA-002
      name: "Commander慢系统"
      description: "云端策略分析引擎"
      boundary:
        input: "市场数据 (MarketData)"
        output: "策略建议 (StrategyRecommendation)"
        scope: "策略分析和风险评估"
      acceptance_criteria:
        - criterion: "策略分析完整性"
          verification: "unit_test"
          pass_condition: "analysis contains market_regime, risk_assessment, strategy"
        - criterion: "无循环依赖"
          verification: "static_analysis"
          pass_condition: "no circular imports with Soldier/Scholar"
      whitepaper_reference: "第二章 2.2 Commander"

    - id: PRD-TBA-003
      name: "Scholar深度研究系统"
      description: "因子研究和理论分析引擎"
      boundary:
        input: "因子表达式 (FactorExpression)"
        output: "研究报告 (ResearchReport)"
        scope: "因子挖掘和验证"
      acceptance_criteria:
        - criterion: "因子研究完整性"
          verification: "unit_test"
          pass_condition: "report contains factor_score, insight, risk_metrics"
        - criterion: "无循环依赖"
          verification: "static_analysis"
          pass_condition: "no circular imports with Soldier/Commander"
      whitepaper_reference: "第二章 2.3 Scholar"

# ============================================================================
# 2. QUALITY_GATES - 质量门禁
# ============================================================================
quality_gates:

  test_requirements:
    unit_test:
      coverage_threshold: 100
      enforcement: MANDATORY
      fail_action: BLOCK_MERGE
      
    integration_test:
      coverage_threshold: 100
      enforcement: MANDATORY
      fail_action: BLOCK_MERGE
      
    property_test:
      min_iterations: 100
      enforcement: MANDATORY
      fail_action: BLOCK_MERGE
      
    e2e_test:
      critical_flows_coverage: 100
      enforcement: MANDATORY
      fail_action: BLOCK_RELEASE

  traceability:
    requirement_to_behavior:
      enforcement: MANDATORY
      rule: "每个PRD-*需求必须有对应的行为定义"
      
    behavior_to_test:
      enforcement: MANDATORY
      rule: "每个行为必须有对应的测试用例"
      
    test_to_evidence:
      enforcement: MANDATORY
      rule: "每个测试必须产生可验证的证据"

  fail_fast_conditions:
    - condition: "任何测试失败"
      action: HALT_PIPELINE
    - condition: "覆盖率低于阈值"
      action: BLOCK_MERGE
    - condition: "属性测试发现反例"
      action: HALT_AND_INVESTIGATE
    - condition: "静态分析发现循环依赖"
      action: BLOCK_MERGE

# ============================================================================
# 3. NON_FUNCTIONAL_REQUIREMENTS - 非功能性需求
# ============================================================================
non_functional_requirements:

  performance:
    - id: NFR-PERF-001
      name: "本地推理延迟"
      metric: "latency_p99"
      threshold: "< 20ms"
      measurement: "time.perf_counter()"
      verification: "performance_test"
      whitepaper_reference: "第一章 1.2 战争态"
      
    - id: NFR-PERF-002
      name: "热备切换延迟"
      metric: "failover_latency"
      threshold: "< 200ms"
      measurement: "time.perf_counter()"
      verification: "integration_test"
      whitepaper_reference: "第一章 1.2 战争态"
      
    - id: NFR-PERF-003
      name: "SPSC延迟"
      metric: "spsc_latency"
      threshold: "< 100μs"
      measurement: "time.perf_counter_ns()"
      verification: "performance_test"
      whitepaper_reference: "第0章 物理感知"

  stability:
    - id: NFR-STAB-001
      name: "系统可用性"
      metric: "availability"
      threshold: "> 99.9%"
      measurement: "uptime / total_time"
      verification: "monitoring"
      
    - id: NFR-STAB-002
      name: "错误恢复时间"
      metric: "mttr"
      threshold: "< 5min"
      measurement: "recovery_time"
      verification: "chaos_test"

  resource_usage:
    - id: NFR-RES-001
      name: "内存使用"
      metric: "memory_usage"
      threshold: "< 100GB"
      measurement: "psutil.Process().memory_info()"
      verification: "resource_monitor"
      
    - id: NFR-RES-002
      name: "GPU显存"
      metric: "gpu_memory"
      threshold: "< 32GB"
      measurement: "rocm-smi"
      verification: "resource_monitor"

  security:
    - id: NFR-SEC-001
      name: "无硬编码密钥"
      metric: "hardcoded_secrets"
      threshold: "== 0"
      measurement: "static_analysis"
      verification: "security_scan"
      
    - id: NFR-SEC-002
      name: "输入验证完整"
      metric: "input_validation_coverage"
      threshold: "== 100%"
      measurement: "code_review"
      verification: "security_audit"

  maintainability:
    - id: NFR-MAIN-001
      name: "圈复杂度"
      metric: "cyclomatic_complexity"
      threshold: "<= 10"
      measurement: "radon cc"
      verification: "static_analysis"
      
    - id: NFR-MAIN-002
      name: "函数长度"
      metric: "function_lines"
      threshold: "<= 50"
      measurement: "line_count"
      verification: "static_analysis"
      
    - id: NFR-MAIN-003
      name: "类长度"
      metric: "class_lines"
      threshold: "<= 300"
      measurement: "line_count"
      verification: "static_analysis"
      
    - id: NFR-MAIN-004
      name: "代码重复率"
      metric: "duplication_rate"
      threshold: "< 5%"
      measurement: "jscpd"
      verification: "static_analysis"

# ============================================================================
# 4. FEATURE_AUDIT - 冗余功能审计
# ============================================================================
feature_audit:

  redundancy_criteria:
    - id: FA-CRIT-001
      name: "行为重叠"
      definition: "两个功能产生相同的输出对于相同的输入"
      detection: "property_test with same inputs"
      
    - id: FA-CRIT-002
      name: "覆盖冗余"
      definition: "一个功能的测试完全覆盖另一个功能"
      detection: "coverage_analysis"
      
    - id: FA-CRIT-003
      name: "语义等价"
      definition: "两个功能在语义上等价"
      detection: "ast_comparison + behavior_test"

  redundancy_actions:
    allowed:
      - MARK_AS_REDUNDANT
      - ANALYZE_IMPACT
      - EXPLAIN_REDUNDANCY
      - SUGGEST_REMOVAL
    forbidden:
      - AUTO_DELETE
      - SILENT_REMOVAL
      - MERGE_WITHOUT_APPROVAL

  default_policy:
    action: MARK_ONLY
    rationale: "删掉一个不确定的文件，比保留十个冗余文件，对系统的伤害更大"

# ============================================================================
# 5. CODE_MINIMALITY - 最小充分实现
# ============================================================================
code_minimality:

  msi_principle:
    name: "Minimum Sufficient Implementation"
    definition: "删除任意一部分代码 → 至少一个测试失败，或破坏稳定性/语义"
    enforcement: MANDATORY

  verification_methods:
    - id: CM-VER-001
      name: "覆盖率反向分析"
      method: "identify code not covered by any test"
      action: "mark as candidate for review"
      
    - id: CM-VER-002
      name: "变异测试"
      method: "mutate code and verify test failure"
      tool: "mutmut or cosmic-ray"
      threshold: "mutation_score > 80%"
      
    - id: CM-VER-003
      name: "行为等价性验证"
      method: "verify no two code paths produce identical behavior"
      action: "flag potential redundancy"

  candidate_marking:
    allowed: true
    auto_delete: false
    requires_human_approval: true

# ============================================================================
# 6. ENGINEERING_CORRECTNESS_AND_RATIONALITY - 工程正确性
# ============================================================================
engineering_correctness_and_rationality:

  algorithm_correctness:
    - id: ECR-ALG-001
      name: "算法假设显式化"
      requirement: "所有算法假设必须在docstring中明确声明"
      verification: "code_review"
      
    - id: ECR-ALG-002
      name: "边界条件覆盖"
      requirement: "所有边界条件必须有测试覆盖"
      verification: "boundary_test"
      
    - id: ECR-ALG-003
      name: "复杂度声明"
      requirement: "时间/空间复杂度必须在docstring中声明"
      verification: "code_review"

  engineering_rationality:
    - id: ECR-RAT-001
      name: "禁止过度复杂"
      requirement: "实现复杂度必须与问题复杂度匹配"
      verification: "complexity_analysis"
      
    - id: ECR-RAT-002
      name: "禁止感觉正确"
      requirement: "所有实现必须有测试证明"
      verification: "test_coverage"
      
    - id: ECR-RAT-003
      name: "禁止经验判断"
      requirement: "所有决策必须有数据支撑"
      verification: "evidence_chain"

# ============================================================================
# 7. ANTI_HALLUCINATION_POLICY - 抗幻觉治理
# ============================================================================
anti_hallucination_policy:

  core_rules:
    - id: AHP-001
      name: "无证据断言无效"
      rule: "任何没有PRD ID或测试证据支撑的断言视为无效"
      enforcement: MANDATORY
      
    - id: AHP-002
      name: "禁止隐式补全"
      rule: "不允许AI Agent补全未在PRD中定义的功能"
      enforcement: MANDATORY
      
    - id: AHP-003
      name: "禁止合理猜测"
      rule: "不允许基于'合理推断'实现功能"
      enforcement: MANDATORY
      
    - id: AHP-004
      name: "禁止经验推断"
      rule: "不允许基于'经验判断'做出决策"
      enforcement: MANDATORY

  evidence_binding:
    required_for_all_conclusions: true
    evidence_types:
      - prd_id: "PRD-*"
      - test_evidence: "test_*.py"
      - static_analysis: "pylint/mypy/radon"
      - dynamic_analysis: "coverage/profiler"

  output_states:
    - state: PASS
      definition: "所有验收条件满足，有测试证据"
    - state: FAIL
      definition: "至少一个验收条件不满足"
    - state: BLOCKED
      definition: "证据不足，无法裁决"

  whitepaper_supremacy:
    rule: "所有实现必须在白皮书(00_核心文档/mia.md)中有明确定义"
    violation_response: |
      "抱歉，该功能在白皮书（00_核心文档/mia.md）中未定义。
      根据MIA编码铁律1（白皮书至上），我不能实现未在白皮书中明确定义的功能。
      请先在白皮书中添加该功能的定义，或者确认我理解的功能名称是否正确。"

# ============================================================================
# 8. EXECUTION_POLICY - AI Agent执行策略
# ============================================================================
execution_policy:

  human_approval_required:
    - operation: "功能删除"
      approval_level: MANDATORY
      rationale: "防止误删核心功能"
      
    - operation: "API移除"
      approval_level: MANDATORY
      rationale: "防止破坏外部依赖"
      
    - operation: "核心逻辑重构"
      approval_level: MANDATORY
      rationale: "防止引入回归"
      
    - operation: "架构层级变更"
      approval_level: MANDATORY
      rationale: "防止架构偏离"
      
    - operation: "白皮书修改"
      approval_level: MANDATORY
      rationale: "防止规格漂移"

  forbidden_actions:
    - action: "为代码更少牺牲稳定性"
      rationale: "稳定性优先于简洁性"
      
    - action: "为代码更少牺牲语义完整性"
      rationale: "语义完整性不可妥协"
      
    - action: "自动删除任何文件"
      rationale: "删除必须人工确认"
      
    - action: "跳过测试验证"
      rationale: "测试是唯一合法证明"
      
    - action: "使用pass/TODO/NotImplemented"
      rationale: "MIA编码铁律2禁止占位符"

  agent_boundaries:
    read_operations:
      allowed: true
      scope: "整个代码库"
    write_operations:
      allowed: true
      scope: "src/, tests/, config/"
      requires_test: true
    delete_operations:
      allowed: false
      exception: "人工批准后"

# ============================================================================
# 9. ROLES_AND_SOP_GOVERNANCE - 角色与SOP治理
# ============================================================================
roles_and_sop_governance:

  agent_roles:
    - role_id: ROLE-001
      name: "Spec_Guardian"
      responsibility: "规格守护"
      hard_constraints:
        - "所有实现必须有PRD ID"
        - "所有PRD变更必须有审批"
        - "禁止实现未定义功能"
      veto_power:
        - "可否决任何违反PRD的实现"
        
    - role_id: ROLE-002
      name: "Test_Sovereign"
      responsibility: "测试主权"
      hard_constraints:
        - "测试覆盖率必须达标"
        - "属性测试必须通过"
        - "测试失败必须阻断"
      veto_power:
        - "可否决任何测试不通过的合并"
        
    - role_id: ROLE-003
      name: "Correctness_Auditor"
      responsibility: "算法正确性审计"
      hard_constraints:
        - "算法假设必须显式"
        - "边界条件必须覆盖"
        - "复杂度必须声明"
      veto_power:
        - "可否决任何正确性存疑的实现"
        
    - role_id: ROLE-004
      name: "Cognitive_Load_Auditor"
      responsibility: "可理解性审计"
      hard_constraints:
        - "圈复杂度 <= 10"
        - "函数长度 <= 50行"
        - "类长度 <= 300行"
      veto_power:
        - "可否决任何过度复杂的实现"
        
    - role_id: ROLE-005
      name: "Minimality_Inspector"
      responsibility: "最小性与冗余检查"
      hard_constraints:
        - "MSI原则必须满足"
        - "冗余代码必须标记"
        - "禁止自动删除"
      veto_power:
        - "可否决任何违反MSI的实现"
        
    - role_id: ROLE-006
      name: "Human_Approval_Gatekeeper"
      responsibility: "人工审批守门"
      hard_constraints:
        - "删除操作必须人工批准"
        - "架构变更必须人工批准"
        - "白皮书修改必须人工批准"
      veto_power:
        - "可否决任何未经批准的敏感操作"

  sop_requirements:
    mandatory_sops:
      - sop_id: SOP-001
        name: "代码提交流程"
        steps:
          - "运行单元测试"
          - "运行属性测试"
          - "检查覆盖率"
          - "静态分析"
          - "提交审查"
        skip_allowed: false
        
      - sop_id: SOP-002
        name: "功能删除流程"
        steps:
          - "标记为CANDIDATE"
          - "影响分析"
          - "人工审批"
          - "备份"
          - "执行删除"
        skip_allowed: false
        
      - sop_id: SOP-003
        name: "架构变更流程"
        steps:
          - "设计文档"
          - "影响分析"
          - "人工审批"
          - "增量实现"
          - "回归测试"
        skip_allowed: false

  role_veto_rules:
    - rule: "任何角色可否决其职责范围内的违规"
    - rule: "否决必须提供具体理由和PRD引用"
    - rule: "否决可被更高级别人工审批覆盖"

# ============================================================================
# 10. COMPLETENESS_AND_ANTI_OMISSION_POLICY - 完整性与防遗漏
# ============================================================================
completeness_and_anti_omission_policy:

  enumeration_requirements:
    - id: CAOP-001
      name: "需求可枚举"
      rule: "所有需求必须有唯一PRD ID"
      verification: "prd_id_uniqueness_check"
      
    - id: CAOP-002
      name: "需求可对账"
      rule: "PRD需求数量必须与实现数量匹配"
      verification: "requirement_implementation_mapping"

  mapping_requirements:
    - id: CAOP-003
      name: "需求到行为映射"
      rule: "每个PRD-*必须有对应的行为定义"
      verification: "behavior_mapping_check"
      
    - id: CAOP-004
      name: "行为到测试映射"
      rule: "每个行为必须有对应的测试用例"
      verification: "test_mapping_check"

  incomplete_handling:
    - condition: "需求未完成裁决"
      action: HALT_EXECUTION
      rationale: "未完成的需求不能进入下一阶段"
      
    - condition: "测试未覆盖"
      action: BLOCK_MERGE
      rationale: "未测试的代码不能合并"

  forbidden_assumptions:
    - assumption: "默认已覆盖"
      rule: "必须有显式测试证据"
      
    - assumption: "应该没问题"
      rule: "必须有测试通过证明"
      
    - assumption: "以前工作正常"
      rule: "必须有回归测试证明"

# ============================================================================
# 11. CORRECTNESS_PROPERTIES - 正确性属性 (Property-Based Testing)
# ============================================================================
correctness_properties:

  codebase_retention_audit:
    - property_id: PROP-CRA-001
      name: "Exclusive Classification"
      statement: "对于任意文件，分类引擎必须分配恰好一个分类"
      formal: "∀f ∈ Files: |{c | classify(f) = c}| = 1"
      test_type: property_test
      min_iterations: 100
      validates: "PRD-CRA-001"
      
    - property_id: PROP-CRA-002
      name: "CORE Classification Evidence"
      statement: "被入口引用、有测试覆盖、或在白皮书中提及的文件必须分类为CORE"
      formal: "∀f: (entry_ref(f) ∨ coverage(f)>0 ∨ whitepaper(f)) → class(f)=CORE"
      test_type: property_test
      min_iterations: 100
      validates: "PRD-CRA-001"
      
    - property_id: PROP-CRA-003
      name: "BLOCKED Default Safety"
      statement: "证据不足时必须分类为BLOCKED而非CANDIDATE"
      formal: "∀f: insufficient_evidence(f) → class(f)=BLOCKED"
      test_type: property_test
      min_iterations: 100
      validates: "PRD-CRA-006"
      
    - property_id: PROP-CRA-004
      name: "Evidence Requirement Invariant"
      statement: "任何分类结果的证据列表必须非空"
      formal: "∀r ∈ Results: |r.evidence_list| > 0"
      test_type: property_test
      min_iterations: 100
      validates: "PRD-CRA-002"
      
    - property_id: PROP-CRA-005
      name: "Dependency Graph Consistency"
      statement: "依赖图必须双向一致"
      formal: "∀a,b: a.imports(b) ↔ b.imported_by(a)"
      test_type: property_test
      min_iterations: 100
      validates: "PRD-CRA-003"
      
    - property_id: PROP-CRA-006
      name: "Read-Only Operation"
      statement: "审计操作不得修改源代码库"
      formal: "∀audit: hash(codebase_before) = hash(codebase_after)"
      test_type: property_test
      min_iterations: 100
      validates: "PRD-CRA-006"
      
    - property_id: PROP-CRA-007
      name: "Export Filtering"
      statement: "导出文件只包含CORE和SUPPORTING"
      formal: "∀f ∈ exported: class(f) ∈ {CORE, SUPPORTING}"
      test_type: property_test
      min_iterations: 100
      validates: "PRD-CRA-007"
      
    - property_id: PROP-CRA-008
      name: "Report YAML Validity"
      statement: "审计报告必须是有效YAML"
      formal: "∀r: yaml.safe_load(yaml.dump(r)) = r"
      test_type: property_test
      min_iterations: 100
      validates: "PRD-CRA-004"

# ============================================================================
# 12. VERIFICATION_MATRIX - 验证矩阵
# ============================================================================
verification_matrix:

  requirement_to_test_mapping:
    - prd_id: PRD-CRA-001
      tests:
        - "tests/unit/audit/retention/test_classification_engine.py"
        - "tests/property/audit/retention/test_exclusive_classification.py"
      properties:
        - PROP-CRA-001
        - PROP-CRA-002
      status: PENDING
      
    - prd_id: PRD-CRA-002
      tests:
        - "tests/unit/audit/retention/test_evidence_collector.py"
        - "tests/property/audit/retention/test_evidence_completeness.py"
      properties:
        - PROP-CRA-004
      status: PENDING
      
    - prd_id: PRD-CRA-003
      tests:
        - "tests/unit/audit/retention/test_dependency_analyzer.py"
        - "tests/property/audit/retention/test_graph_consistency.py"
      properties:
        - PROP-CRA-005
      status: PENDING
      
    - prd_id: PRD-CRA-004
      tests:
        - "tests/unit/audit/retention/test_report_generator.py"
        - "tests/property/audit/retention/test_yaml_validity.py"
      properties:
        - PROP-CRA-008
      status: PENDING
      
    - prd_id: PRD-CRA-005
      tests:
        - "tests/unit/audit/retention/test_human_approval_queue.py"
      properties: []
      status: PENDING
      
    - prd_id: PRD-CRA-006
      tests:
        - "tests/unit/audit/retention/test_retention_auditor.py"
        - "tests/property/audit/retention/test_read_only.py"
      properties:
        - PROP-CRA-003
        - PROP-CRA-006
      status: PENDING
      
    - prd_id: PRD-CRA-007
      tests:
        - "tests/unit/audit/retention/test_file_exporter.py"
        - "tests/property/audit/retention/test_export_filtering.py"
      properties:
        - PROP-CRA-007
      status: PENDING

# ============================================================================
# 13. AUDIT_TRAIL - 审计轨迹要求
# ============================================================================
audit_trail:

  required_records:
    - record_type: "classification_decision"
      fields:
        - file_path
        - classification
        - evidence_list
        - timestamp
        - auditor_version
      retention: "365 days"
      
    - record_type: "human_approval"
      fields:
        - file_path
        - decision
        - approver
        - timestamp
        - rationale
      retention: "365 days"
      
    - record_type: "export_operation"
      fields:
        - source_path
        - destination_path
        - file_count
        - timestamp
      retention: "365 days"

  immutability:
    rule: "审计记录一旦创建不可修改"
    enforcement: MANDATORY

# ============================================================================
# 14. TASK_HIERARCHY_MANAGEMENT - 任务层次化管理
# ============================================================================
task_hierarchy_management:

  task_classification:
    long_term_tasks:
      - id: THM-LT-001
        name: "战略任务层"
        time_span: "3-12个月"
        characteristics: ["战略性", "架构性", "系统性"]
        responsibility: "Product Manager"
        example: "构建完整的AI驱动量化交易系统"
        acceptance_criteria:
          - "系统架构完整"
          - "核心功能实现"
          - "质量标准达标"
        verification: "系统级集成测试"
        
    medium_term_tasks:
      - id: THM-MT-001
        name: "战术任务层"
        time_span: "2-8周"
        characteristics: ["功能性", "模块性", "可交付"]
        responsibility: "Software Architect + 相关工程师"
        example: "实现AI大脑协调器模块"
        acceptance_criteria:
          - "模块功能完整"
          - "接口规范"
          - "测试覆盖率100%"
        verification: "模块级集成测试"
        
    short_term_tasks:
      - id: THM-ST-001
        name: "操作任务层"
        time_span: "1-5天"
        characteristics: ["具体性", "可执行", "可验证"]
        responsibility: "具体执行角色"
        example: "修复ai_brain_coordinator.py中的测试覆盖率缺失"
        acceptance_criteria:
          - "代码质量达标"
          - "测试通过"
          - "文档更新"
        verification: "单元测试 + 代码审查"
        
    adhoc_tasks:
      - id: THM-AT-001
        name: "临时任务层"
        time_span: "立即-1天"
        characteristics: ["紧急性", "响应性", "插入性"]
        responsibility: "相关专业角色"
        example: "修复生产环境的紧急bug"
        acceptance_criteria:
          - "问题解决"
          - "影响评估"
          - "预防措施"
        verification: "问题验证 + 回归测试"

  task_decomposition_rules:
    long_to_medium:
      - "基于里程碑分解"
      - "考虑依赖关系"
      - "评估风险等级"
      - "分配责任人"
      enforcement: MANDATORY
      
    medium_to_short:
      - "基于功能模块分解"
      - "明确技术实现路径"
      - "设定质量标准"
      - "制定测试策略"
      enforcement: MANDATORY
      
    short_to_execution:
      - "具体代码实现"
      - "单元测试编写"
      - "代码审查"
      - "集成验证"
      enforcement: MANDATORY

  task_completion_verification:
    self_check:
      - "交付物完整性检查"
      - "质量标准验证"
      - "功能测试通过"
      - "文档同步更新"
      enforcement: MANDATORY
      
    peer_review:
      - "Code Review Specialist审查"
      - "相关角色交叉验证"
      - "集成测试验证"
      - "安全合规检查"
      enforcement: MANDATORY
      
    supervisor_approval:
      - "中期任务需Product Manager确认"
      - "长期任务需Software Architect确认"
      - "关键里程碑需全团队确认"
      - "生产部署需DevOps Engineer确认"
      enforcement: MANDATORY

  task_state_tracking:
    states:
      - "planned": "已规划 - 任务已定义但未开始"
      - "in_progress": "进行中 - 任务正在执行"
      - "blocked": "阻塞中 - 遇到阻塞问题暂停"
      - "review": "审查中 - 等待代码审查或验收"
      - "completed": "已完成 - 任务执行完毕"
      - "verified": "已验证 - 通过质量验证"
      - "failed": "失败 - 任务执行失败需重新规划"
      - "cancelled": "已取消 - 任务被取消不再执行"
      
    progress_metrics:
      - "completion_percentage": "完成百分比 (0-100%)"
      - "quality_score": "质量评分 (0-100分)"
      - "test_coverage": "测试覆盖率 (0-100%)"
      - "code_review_status": "代码审查状态"
      - "blocking_issues_count": "阻塞问题数量"
      - "estimated_remaining_time": "预估剩余时间"

  anti_drift_mechanisms:
    context_anchoring:
      - "任务目标持续提醒"
      - "质量标准定期检查"
      - "技术选型一致性验证"
      - "架构约束持续监控"
      enforcement: MANDATORY
      
    progress_checkpoints:
      - "每日进度检查"
      - "每周质量评估"
      - "每月目标对齐"
      - "里程碑完成验证"
      enforcement: MANDATORY
      
    automatic_correction:
      - "偏离检测自动告警"
      - "质量下降自动阻断"
      - "上下文丢失自动恢复"
      - "目标漂移自动纠正"
      enforcement: MANDATORY

  drift_indicators:
    goal_deviation:
      threshold: 30%
      description: "目标偏离度超过30%"
      action: "立即重新对齐目标"
      
    quality_degradation:
      threshold: -10%
      description: "质量评分下降超过10%"
      action: "暂停执行，质量改进"
      
    progress_anomaly:
      threshold: 50%
      description: "进度异常偏离计划50%"
      action: "重新评估和调整计划"
      
    context_inconsistency:
      threshold: 3
      description: "上下文不一致次数超过3次"
      action: "重新锚定上下文"

  next_phase_planning:
    planning_triggers:
      - "当前任务完成度 >= 80%"
      - "关键里程碑达成"
      - "阻塞问题解决"
      - "资源可用性确认"
      
    planning_process:
      dependency_analysis:
        - "分析前置条件是否满足"
        - "识别关键依赖关系"
        - "评估风险因素"
        
      resource_assessment:
        - "评估所需人力资源"
        - "估算时间成本"
        - "确认技术资源可用性"
        
      priority_ranking:
        - "基于业务价值排序"
        - "考虑技术债务影响"
        - "评估用户影响程度"
        
      execution_planning:
        - "制定详细执行计划"
        - "分配具体责任人"
        - "设定质量标准"
        - "定义验收标准"

# ============================================================================
# 15. DOCUMENT_SYNC_REQUIREMENTS - 文档同步要求
# ============================================================================
document_sync_requirements:

  mandatory_documents:
    - document: "00_核心文档/mia.md"
      sync_trigger: "功能变更"
      sync_action: "更新白皮书定义"
      
    - document: ".kiro/specs/*/tasks.md"
      sync_trigger: "任务完成"
      sync_action: "标记[x]完成状态"
      
    - document: "00_核心文档/IMPLEMENTATION_CHECKLIST.md"
      sync_trigger: "功能实现"
      sync_action: "更新检查项"
      
    - document: ".kiro/steering/task-hierarchy-management.md"
      sync_trigger: "任务层次变更"
      sync_action: "更新任务层次定义"
      
    - document: ".kiro/hooks/task-lifecycle-management.kiro.hook"
      sync_trigger: "任务流程变更"
      sync_action: "更新Hook配置"

  task_hierarchy_sync:
    long_term_to_medium:
      sync_rule: "长期任务分解时必须同步更新中期任务定义"
      enforcement: MANDATORY
      
    medium_to_short:
      sync_rule: "中期任务分解时必须同步更新短期任务定义"
      enforcement: MANDATORY
      
    completion_propagation:
      sync_rule: "短期任务完成时必须同步更新上级任务进度"
      enforcement: MANDATORY

  sync_principle:
    name: "文档先行 + 任务层次一致性"
    rule: "文档定义 → 任务分解 → 代码实现 → 任务验证 → 文档同步 → 代码审查"
    enforcement: MANDATORY

  violation_consequence:
    - "代码审查不通过"
    - "必须回退所有变更"
    - "重新按照任务层次化原则执行"
    - "任务状态回滚到上一个验证点"

# ============================================================================
# END OF PRD
# ============================================================================
```
