"""Logging Configuration for ETF/LOF Factor Mining

白皮书依据: 第四章 4.1.17-4.1.18 - ETF/LOF因子挖掘器日志系统
版本: v1.6.1
铁律依据: MIA编码铁律1 (白皮书至上), 铁律5 (完整的文档字符串)

This module configures structured logging for ETF/LOF factor mining operations.
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger


def configure_etf_lof_logging(
    log_file: Optional[str] = None,
    log_level: str = "INFO",
    rotation: str = "100 MB",
    retention: str = "30 days",
    compression: str = "zip",
) -> None:
    """Configure structured logging for ETF/LOF factor mining

    白皮书依据: 第四章 4.1.17-4.1.18 - 日志配置
    铁律依据: MIA编码铁律3 (完整的错误处理), 铁律4 (完整的类型注解)

    Sets up loguru logger with:
    - File rotation (default 100 MB)
    - Log retention (default 30 days)
    - Compression (default zip)
    - Structured logging with context fields
    - Console and file handlers

    Args:
        log_file: Path to log file (default: logs/etf_lof_mining.log)
        log_level: Logging level (default: INFO)
        rotation: Log rotation size (default: 100 MB)
        retention: Log retention period (default: 30 days)
        compression: Compression format (default: zip)

    Raises:
        ValueError: If log_level is invalid
        OSError: If log directory cannot be created

    Example:
        >>> configure_etf_lof_logging(
        ...     log_file="logs/etf_mining.log",
        ...     log_level="DEBUG"
        ... )
    """
    # Validate log level
    valid_levels = ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]
    if log_level.upper() not in valid_levels:
        raise ValueError(f"Invalid log_level: {log_level}. " f"Must be one of {valid_levels}")

    # Remove default logger
    logger.remove()

    # Add console handler with color
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[component]}</cyan> | "
            "<level>{message}</level>"
        ),
        level=log_level,
        colorize=True,
        enqueue=True,
    )

    # Add file handler with rotation
    if log_file is None:
        log_file = "logs/etf_lof_mining.log"

    # Create log directory if it doesn't exist
    log_path = Path(log_file)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"Failed to create log directory: {log_path.parent}") from e

    logger.add(
        log_file,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{extra[component]} | "
            "{extra[action]} | "
            "{message} | "
            "{extra}"
        ),
        level=log_level,
        rotation=rotation,
        retention=retention,
        compression=compression,
        enqueue=True,
        serialize=False,
    )

    logger.info(
        "ETF/LOF logging configured",
        extra={
            "component": "LoggingConfig",
            "action": "configure",
            "log_file": str(log_file),
            "log_level": log_level,
            "rotation": rotation,
            "retention": retention,
            "compression": compression,
        },
    )


def get_logger_with_context(component: str):
    """Get logger with component context

    白皮书依据: 第四章 4.1.17-4.1.18 - 结构化日志

    Args:
        component: Component name (e.g., "ETFFactorMiner", "LOFFactorMiner")

    Returns:
        Logger instance with component context

    Example:
        >>> log = get_logger_with_context("ETFFactorMiner")
        >>> log.info("Evolution started", action="evolve", generation=1)
    """
    return logger.bind(component=component, action="unknown")


def get_logger(name: str = "etf_lof"):
    """获取日志器

    Args:
        name: 日志器名称

    Returns:
        Logger实例
    """
    return logger.bind(component=name, action="log")


# 别名，保持向后兼容
setup_etf_lof_logging = configure_etf_lof_logging


def configure_default_logging(log_level: str = "INFO") -> None:
    """配置默认日志（简化版本）

    Args:
        log_level: 日志级别
    """
    configure_etf_lof_logging(log_file=None, log_level=log_level)
