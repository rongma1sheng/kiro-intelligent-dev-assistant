#!/usr/bin/env python
import json
import subprocess
import sys

result = subprocess.run(
    "python -m pylint src --exit-zero --output-format=json --max-line-length=120",
    shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace'
)

bugs = json.loads(result.stdout)
for b in bugs:
    print(f"{b['path']}:{b['line']} {b['message-id']} {b['message'][:60]}")
