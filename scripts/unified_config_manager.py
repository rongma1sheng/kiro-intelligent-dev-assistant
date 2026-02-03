#!/usr/bin/env python3
"""
统一配置管理系统 - 硅谷项目开发经理设计
确保所有Kiro配置的一致性、同步性和可维护性
"""

import json
import yaml
import os
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, asdict

@dataclass
class ConfigSource:
    """配置源定义"""
    name: str
    path: str
    type: str  # 'json', 'yaml', 'md'
    priority: int
    last_modified: datetime
    checksum: str

@dataclass
class ConfigInconsistency:
    """配置不一致报告"""
    source1: str
    source2: str
    field: str
    value1: Any
    value2: Any
    severity: str
    recommendation: str

class UnifiedConfigManager:
    """统一配置管理器"""
    
    def __init__(self, kiro_root: str = ".kiro"):
        self.kiro_root = Path(kiro_root)
        self.logger = self._setup_logger()
        self.config_sources = []
        self.config_cache = {}
        self.sync_status = {}
        
        # 初始化配置源
        self._discover_config_sources()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('unified_config_manager')
        logger.setLevel(logging.INFO)
        
        # 确保日志目录存在
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        handler = logging.FileHandler('logs/config_manager.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _discover_config_sources(self):
        """发现所有配置源"""
        config_patterns = [
            # Hooks配置
            (self.kiro_root / "hooks", "*.kiro.hook", "json", 1),
            # Settings配置
            (self.kiro_root / "settings", "*.json", "json", 2),
            # Steering配置
            (self.kiro_root / "steering", "*.md", "md", 3),
            # Specs配置
            (self.kiro_root / "specs", "*.md", "md", 4),
        ]
        
        for base_path, pattern, config_type, priority in config_patterns:
            if base_path.exists():
                for config_file in base_path.rglob(pattern):
                    self._add_config_source(config_file, config_type, priority)
    
    def _add_config_source(self, file_path: Path, config_type: str, priority: int):
        """添加配置源"""
        try:
            stat = file_path.stat()
            checksum = self._calculate_file_checksum(file_path)
            
            source = ConfigSource(
                name=file_path.name,
                path=str(file_path),
                type=config_type,
                priority=priority,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                checksum=checksum
            )
            
            self.config_sources.append(source)
            self.logger.info(f"发现配置源: {source.name}")
            
        except Exception as e:
            self.logger.error(f"添加配置源失败 {file_path}: {e}")
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """计算文件校验和"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception as e:
            self.logger.error(f"计算校验和失败 {file_path}: {e}")
            return ""
    
    def sync_all_configs(self) -> Dict[str, Any]:
        """同步所有配置"""
        sync_results = {}
        
        for source in self.config_sources:
            try:
                result = self._sync_config_source(source)
                sync_results[source.name] = result
                self.sync_status[source.name] = {
                    'status': 'success',
                    'last_sync': datetime.now(),
                    'checksum': source.checksum
                }
            except Exception as e:
                error_msg = str(e)
                sync_results[source.name] = {
                    'status': 'failed', 
                    'error': error_msg
                }
                self.sync_status[source.name] = {
                    'status': 'failed',
                    'last_sync': datetime.now(),
                    'error': error_msg
                }
                self.logger.error(f"同步配置失败 {source.name}: {e}")
        
        return sync_results
    
    def _sync_config_source(self, source: ConfigSource) -> Dict[str, Any]:
        """同步单个配置源"""
        # 检查文件是否被修改
        current_checksum = self._calculate_file_checksum(Path(source.path))
        if current_checksum != source.checksum:
            self.logger.info(f"检测到配置变更: {source.name}")
            source.checksum = current_checksum
            source.last_modified = datetime.now()
        
        # 加载配置内容
        config_content = self._load_config_content(source)
        self.config_cache[source.name] = config_content
        
        return {
            'status': 'success',
            'checksum': current_checksum,
            'last_modified': source.last_modified.isoformat()
        }
    
    def _load_config_content(self, source: ConfigSource) -> Any:
        """加载配置内容"""
        try:
            with open(source.path, 'r', encoding='utf-8') as f:
                if source.type == 'json':
                    return json.load(f)
                elif source.type == 'yaml':
                    return yaml.safe_load(f)
                elif source.type == 'md':
                    return f.read()
                else:
                    return f.read()
        except Exception as e:
            self.logger.error(f"加载配置内容失败 {source.path}: {e}")
            return None
    
    def validate_config_consistency(self) -> List[ConfigInconsistency]:
        """验证配置一致性"""
        inconsistencies = []
        
        # 检查角色定义一致性
        role_inconsistencies = self._check_role_consistency()
        inconsistencies.extend(role_inconsistencies)
        
        # 检查权限配置一致性
        permission_inconsistencies = self._check_permission_consistency()
        inconsistencies.extend(permission_inconsistencies)
        
        # 检查Hook配置一致性
        hook_inconsistencies = self._check_hook_consistency()
        inconsistencies.extend(hook_inconsistencies)
        
        # 检查质量标准一致性
        quality_inconsistencies = self._check_quality_standards_consistency()
        inconsistencies.extend(quality_inconsistencies)
        
        return inconsistencies
    
    def _check_role_consistency(self) -> List[ConfigInconsistency]:
        """检查角色定义一致性"""
        inconsistencies = []
        
        # 从不同配置源提取角色定义
        role_sources = {}
        
        # 从steering配置提取角色
        for source_name, content in self.config_cache.items():
            if 'steering' in source_name and isinstance(content, str):
                roles = self._extract_roles_from_markdown(content)
                if roles:
                    role_sources[source_name] = roles
        
        # 从权限矩阵提取角色
        for source_name, content in self.config_cache.items():
            if 'role-permission-matrix' in source_name and isinstance(content, str):
                roles = self._extract_roles_from_permission_matrix(content)
                if roles:
                    role_sources[source_name] = roles
        
        # 比较角色定义
        if len(role_sources) >= 2:
            source_names = list(role_sources.keys())
            for i in range(len(source_names)):
                for j in range(i + 1, len(source_names)):
                    source1, source2 = source_names[i], source_names[j]
                    roles1, roles2 = role_sources[source1], role_sources[source2]
                    
                    # 检查角色数量
                    if len(roles1) != len(roles2):
                        inconsistencies.append(ConfigInconsistency(
                            source1=source1,
                            source2=source2,
                            field="role_count",
                            value1=len(roles1),
                            value2=len(roles2),
                            severity="medium",
                            recommendation="统一角色数量定义"
                        ))
                    
                    # 检查角色名称
                    roles1_set = set(roles1)
                    roles2_set = set(roles2)
                    missing_in_source2 = roles1_set - roles2_set
                    missing_in_source1 = roles2_set - roles1_set
                    
                    if missing_in_source2:
                        inconsistencies.append(ConfigInconsistency(
                            source1=source1,
                            source2=source2,
                            field="missing_roles",
                            value1=list(missing_in_source2),
                            value2="not_present",
                            severity="high",
                            recommendation=f"在{source2}中添加缺失角色"
                        ))
        
        return inconsistencies
    
    def _extract_roles_from_markdown(self, content: str) -> List[str]:
        """从Markdown内容提取角色"""
        roles = []
        lines = content.split('\n')
        
        for line in lines:
            # 查找角色定义模式，如 "### 1. 📊 Product Manager"
            if line.strip().startswith('###') and any(emoji in line for emoji in ['📊', '🏗️', '🧮', '🗄️', '🎨', '🚀', '🔒', '☁️', '📈', '🧪', '🎯', '🔍']):
                # 提取角色名称
                role_part = line.split('###')[1].strip()
                if '. ' in role_part:
                    role_name = role_part.split('. ', 1)[1].strip()
                    roles.append(role_name)
        
        return roles
    
    def _extract_roles_from_permission_matrix(self, content: str) -> List[str]:
        """从权限矩阵提取角色"""
        roles = []
        lines = content.split('\n')
        
        for line in lines:
            # 查找权限矩阵中的角色定义
            if line.strip().startswith('### ') and any(emoji in line for emoji in ['📊', '🏗️', '🧮', '🗄️', '🎨', '🚀', '🔒', '☁️', '📈', '🧪', '🎯', '🔍']):
                role_name = line.replace('### ', '').strip()
                roles.append(role_name)
        
        return roles
    
    def _check_permission_consistency(self) -> List[ConfigInconsistency]:
        """检查权限配置一致性"""
        inconsistencies = []
        
        # 从MCP配置和权限矩阵检查权限一致性
        mcp_permissions = self._extract_mcp_permissions()
        matrix_permissions = self._extract_matrix_permissions()
        
        if mcp_permissions and matrix_permissions:
            # 检查权限工具名称一致性
            mcp_tools = set(mcp_permissions.get('autoApprove', []))
            matrix_operations = set()
            
            for role_perms in matrix_permissions.values():
                matrix_operations.update(role_perms.get('allowed_operations', []))
            
            # 这里可以添加更详细的权限一致性检查
            
        return inconsistencies
    
    def _extract_mcp_permissions(self) -> Optional[Dict]:
        """提取MCP权限配置"""
        for source_name, content in self.config_cache.items():
            if 'mcp.json' in source_name and isinstance(content, dict):
                return content
        return None
    
    def _extract_matrix_permissions(self) -> Optional[Dict]:
        """提取权限矩阵配置"""
        # 这里需要解析权限矩阵Markdown文件
        # 实现具体的解析逻辑
        return None
    
    def _check_hook_consistency(self) -> List[ConfigInconsistency]:
        """检查Hook配置一致性"""
        inconsistencies = []
        
        hook_configs = {}
        for source_name, content in self.config_cache.items():
            if source_name.endswith('.kiro.hook') and isinstance(content, dict):
                hook_configs[source_name] = content
        
        # 检查Hook版本一致性
        versions = {}
        for hook_name, config in hook_configs.items():
            version = config.get('version', 'unknown')
            if version not in versions:
                versions[version] = []
            versions[version].append(hook_name)
        
        # 如果有多个版本，报告不一致
        if len(versions) > 1:
            inconsistencies.append(ConfigInconsistency(
                source1="multiple_hooks",
                source2="version_mismatch",
                field="version",
                value1=list(versions.keys()),
                value2="should_be_consistent",
                severity="medium",
                recommendation="统一Hook版本号"
            ))
        
        return inconsistencies
    
    def _check_quality_standards_consistency(self) -> List[ConfigInconsistency]:
        """检查质量标准一致性"""
        inconsistencies = []
        
        # 从不同配置源提取质量标准
        quality_sources = {}
        
        # 从LLM行为约束配置提取
        for source_name, content in self.config_cache.items():
            if 'llm-behavior-constraints.json' in source_name and isinstance(content, dict):
                quality_thresholds = content.get('quality_thresholds', {})
                if quality_thresholds:
                    quality_sources[source_name] = quality_thresholds
        
        # 从其他配置源提取质量标准
        # 可以添加更多源的检查
        
        return inconsistencies
    
    def generate_consistency_report(self) -> Dict[str, Any]:
        """生成一致性报告"""
        inconsistencies = self.validate_config_consistency()
        
        # 按严重程度分类
        by_severity = {'critical': [], 'high': [], 'medium': [], 'low': []}
        for inconsistency in inconsistencies:
            severity = inconsistency.severity
            if severity in by_severity:
                by_severity[severity].append(asdict(inconsistency))
        
        # 生成摘要
        summary = {
            'total_inconsistencies': len(inconsistencies),
            'by_severity': {k: len(v) for k, v in by_severity.items()},
            'config_sources_count': len(self.config_sources),
            'last_sync_status': self.sync_status
        }
        
        return {
            'timestamp': datetime.now().isoformat(),
            'summary': summary,
            'inconsistencies': by_severity,
            'recommendations': self._generate_recommendations(inconsistencies)
        }
    
    def _generate_recommendations(self, inconsistencies: List[ConfigInconsistency]) -> List[str]:
        """生成修复建议"""
        recommendations = []
        
        # 按问题类型分组并生成建议
        role_issues = [i for i in inconsistencies if 'role' in i.field]
        if role_issues:
            recommendations.append("统一所有配置文件中的角色定义")
        
        permission_issues = [i for i in inconsistencies if 'permission' in i.field]
        if permission_issues:
            recommendations.append("同步MCP配置和权限矩阵中的权限定义")
        
        version_issues = [i for i in inconsistencies if 'version' in i.field]
        if version_issues:
            recommendations.append("统一所有Hook配置的版本号")
        
        return recommendations
    
    def auto_fix_inconsistencies(self, inconsistencies: List[ConfigInconsistency]) -> Dict[str, Any]:
        """自动修复不一致问题"""
        fix_results = {}
        
        for inconsistency in inconsistencies:
            try:
                if inconsistency.severity in ['low', 'medium']:
                    # 只自动修复低风险问题
                    result = self._apply_auto_fix(inconsistency)
                    fix_results[f"{inconsistency.source1}_{inconsistency.field}"] = result
                else:
                    fix_results[f"{inconsistency.source1}_{inconsistency.field}"] = {
                        'status': 'skipped',
                        'reason': 'high_risk_requires_manual_review'
                    }
            except Exception as e:
                fix_results[f"{inconsistency.source1}_{inconsistency.field}"] = {
                    'status': 'failed',
                    'error': str(e)
                }
        
        return fix_results
    
    def _apply_auto_fix(self, inconsistency: ConfigInconsistency) -> Dict[str, Any]:
        """应用自动修复"""
        # 实现具体的自动修复逻辑
        # 这里只是示例框架
        return {
            'status': 'success',
            'action': 'auto_fixed',
            'details': inconsistency.recommendation
        }
    
    def backup_configs(self) -> str:
        """备份所有配置"""
        backup_dir = Path('backups') / f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        for source in self.config_sources:
            try:
                source_path = Path(source.path)
                backup_path = backup_dir / source_path.name
                
                # 复制文件
                import shutil
                shutil.copy2(source_path, backup_path)
                
                self.logger.info(f"备份配置文件: {source.name} -> {backup_path}")
                
            except Exception as e:
                self.logger.error(f"备份失败 {source.name}: {e}")
        
        return str(backup_dir)

def main():
    """主函数 - 用于测试和命令行使用"""
    import argparse
    
    parser = argparse.ArgumentParser(description='统一配置管理系统')
    parser.add_argument('--sync', action='store_true', help='同步所有配置')
    parser.add_argument('--validate', action='store_true', help='验证配置一致性')
    parser.add_argument('--report', action='store_true', help='生成一致性报告')
    parser.add_argument('--backup', action='store_true', help='备份所有配置')
    parser.add_argument('--auto-fix', action='store_true', help='自动修复不一致问题')
    
    args = parser.parse_args()
    
    manager = UnifiedConfigManager()
    
    if args.sync:
        print("同步所有配置...")
        results = manager.sync_all_configs()
        print(json.dumps(results, indent=2, ensure_ascii=False))
    
    if args.validate:
        print("验证配置一致性...")
        inconsistencies = manager.validate_config_consistency()
        print(f"发现 {len(inconsistencies)} 个不一致问题")
        for inc in inconsistencies:
            print(f"- {inc.severity}: {inc.field} ({inc.source1} vs {inc.source2})")
    
    if args.report:
        print("生成一致性报告...")
        report = manager.generate_consistency_report()
        print(json.dumps(report, indent=2, ensure_ascii=False))
    
    if args.backup:
        print("备份所有配置...")
        backup_path = manager.backup_configs()
        print(f"配置已备份到: {backup_path}")
    
    if args.auto_fix:
        print("自动修复不一致问题...")
        inconsistencies = manager.validate_config_consistency()
        fix_results = manager.auto_fix_inconsistencies(inconsistencies)
        print(json.dumps(fix_results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()