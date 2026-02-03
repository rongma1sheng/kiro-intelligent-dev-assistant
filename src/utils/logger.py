"""
MIA系统日志工具

版本: v1.6.0
作者: MIA Team
日期: 2026-01-18
"""

import logging
import sys


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """获取日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))

        # 创建格式器
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(formatter)

        # 添加处理器到日志记录器
        logger.addHandler(console_handler)
        logger.setLevel(getattr(logging, level.upper()))

        # 防止重复日志
        logger.propagate = False

    return logger
