# Windows Scripts

## Scripts List

| Script | Function |
|--------|----------|
| `run_all_checks.bat` | Complete quality check flow |
| `run_config_validate.bat` | Kiro config validation |
| `run_quality_gate.bat` | Quality gate check |
| `run_deploy_test.bat` | Deploy test |
| `run_bug_detection.bat` | Bug detection and fix |
| `run_unified_quality.bat` | Unified quality system |

## Quick Start

### Complete Check (Recommended)
```cmd
run_all_checks.bat
```

### Single Check
```cmd
run_quality_gate.bat
run_deploy_test.bat
run_config_validate.bat
```

### With Parameters
```cmd
run_bug_detection.bat scan
run_bug_detection.bat fix
run_bug_detection.bat cycle

run_unified_quality.bat check
run_unified_quality.bat prd
run_unified_quality.bat config
```

## Quality Standards

- Test Coverage: 100%
- Bug Count: 0
- Security Issues: 0

## Requirements

- Python >= 3.10
- Packages: pytest, pylint, black, isort, bandit
