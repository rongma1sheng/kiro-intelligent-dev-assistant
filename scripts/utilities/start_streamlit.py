#!/usr/bin/env python3
"""
启动Streamlit Web界面

白皮书依据: 第一章 1.1 服务启动管理
启动MIA系统的Web控制面板
"""

import subprocess
import sys
import os
from pathlib import Path
from loguru import logger


def start_streamlit():
    """启动Streamlit应用"""
    try:
        # 获取项目根目录
        project_root = Path(__file__).parent.parent
        
        # Streamlit应用路径
        app_path = project_root / "src" / "chronos" / "streamlit_app.py"
        
        if not app_path.exists():
            logger.error(f"Streamlit应用文件不存在: {app_path}")
            return False
        
        # 构建启动命令
        cmd = [
            sys.executable, "-m", "streamlit", "run",
            str(app_path),
            "--server.port", "8501",
            "--server.address", "localhost",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false"
        ]
        
        logger.info(f"启动Streamlit应用: {' '.join(cmd)}")
        
        # 启动Streamlit
        process = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        logger.info(f"Streamlit应用已启动，PID: {process.pid}")
        logger.info("访问地址: http://localhost:8501")
        
        return True
        
    except Exception as e:
        logger.error(f"启动Streamlit应用失败: {e}")
        return False


if __name__ == "__main__":
    start_streamlit()