# Quality Assurance Scripts

## Directory Structure

```
scripts/
├── win/                    # Windows scripts (.bat)
│   ├── run_all_checks.bat
│   ├── run_config_validate.bat
│   ├── run_quality_gate.bat
│   ├── run_deploy_test.bat
│   ├── run_bug_detection.bat
│   ├── run_unified_quality.bat
│   └── README.md
│
├── mac/                    # Mac/Linux scripts (.sh)
│   ├── run_all_checks.sh
│   ├── run_config_validate.sh
│   ├── run_quality_gate.sh
│   ├── run_deploy_test.sh
│   ├── run_bug_detection.sh
│   ├── run_unified_quality.sh
│   └── README.md
│
└── [Core Python Scripts]
    ├── quality_gate.py           # Quality gate
    ├── deploy_test.py            # Deploy test
    ├── unified_quality_system.py # Unified quality system
    ├── auto_bug_detection.py     # Bug detection and fix
    ├── validate_kiro_config.py   # Config validation
    └── prd_parser.py             # PRD parser
```

## Quick Start

### Windows
```cmd
cd scripts\win
run_all_checks.bat
```

### Mac/Linux
```bash
chmod +x scripts/mac/*.sh
./scripts/mac/run_all_checks.sh
```

## Quality Standards

| Metric | Standard |
|--------|----------|
| Test Coverage | 100% |
| Bug Count | 0 |
| Security Issues | 0 |
| Pylint Score | >= 8.0 |

## Workflow

```
Config Validation → Unified Quality Check → Quality Gate → Deploy Test
       │                    │                   │              │
       ▼                    ▼                   ▼              ▼
    Hooks              PRD Parse           Bug Scan       CI/CD Test
    Steering           Code Quality        Auto Fix       Env Check
    Specs              Security Scan       Report Gen     Coverage
    MCP
```

## Team Role Assignment (On Failure)

| Check Type | Assigned Role |
|------------|---------------|
| Environment | ☁️ DevOps Engineer |
| Code Quality | 🔍 Code Review Specialist |
| Security Scan | 🔒 Security Engineer |
| Test Failure | 🧪 Test Engineer |
| Coverage | 🧪 Test Engineer |
