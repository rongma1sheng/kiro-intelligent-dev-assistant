"""Configuration Manager

白皮书依据: 第四章 4.9 配置管理

This module provides configuration management with hot reload capability.
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml
from loguru import logger

from src.evolution.config.data_models import (
    ArenaConfig,
    DecayConfig,
    SimulationConfig,
    SpartaEvolutionConfig,
    Z2HConfig,
    get_default_config,
)


class ConfigurationManager:
    """配置管理器

    白皮书依据: 第四章 4.9 配置管理

    提供配置加载、验证、热重载功能。

    Attributes:
        config_path: 配置文件路径
        config: 当前配置
        _lock: 线程锁
        _last_modified: 配置文件最后修改时间
        _reload_callbacks: 重载回调函数列表
    """

    def __init__(self, config_path: Optional[str] = None, auto_reload: bool = False):
        """初始化配置管理器

        Args:
            config_path: 配置文件路径，None则使用默认配置
            auto_reload: 是否启用自动重载

        Raises:
            ValueError: 当配置文件格式不支持时
        """
        self.config_path: Optional[str] = config_path
        self._config: SpartaEvolutionConfig = get_default_config()
        self._lock: threading.RLock = threading.RLock()
        self._last_modified: Optional[float] = None
        self._reload_callbacks: List[Callable[[SpartaEvolutionConfig], None]] = []
        self._auto_reload: bool = auto_reload
        self._reload_errors: List[str] = []

        # 如果提供了配置文件路径，加载配置
        if config_path:
            self._load_config_from_file(config_path)

        logger.info(
            f"ConfigurationManager初始化完成 - "
            f"config_path={config_path}, "
            f"auto_reload={auto_reload}, "
            f"version={self._config.version}"
        )

    @property
    def config(self) -> SpartaEvolutionConfig:
        """获取当前配置

        Returns:
            当前配置
        """
        with self._lock:
            return self._config

    @property
    def arena(self) -> ArenaConfig:
        """获取Arena配置

        Returns:
            Arena配置
        """
        with self._lock:
            return self._config.arena

    @property
    def simulation(self) -> SimulationConfig:
        """获取模拟配置

        Returns:
            模拟配置
        """
        with self._lock:
            return self._config.simulation

    @property
    def z2h(self) -> Z2HConfig:
        """获取Z2H配置

        Returns:
            Z2H配置
        """
        with self._lock:
            return self._config.z2h

    @property
    def decay(self) -> DecayConfig:
        """获取衰减配置

        Returns:
            衰减配置
        """
        with self._lock:
            return self._config.decay

    @property
    def reload_errors(self) -> List[str]:
        """获取重载错误列表

        Returns:
            错误列表
        """
        with self._lock:
            return self._reload_errors.copy()

    def _load_config_from_file(self, config_path: str) -> bool:
        """从文件加载配置

        Args:
            config_path: 配置文件路径

        Returns:
            是否加载成功
        """
        path = Path(config_path)

        if not path.exists():
            logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
            return False

        try:
            # 读取文件内容
            content = path.read_text(encoding="utf-8")

            # 根据文件扩展名解析
            if path.suffix.lower() in [".yaml", ".yml"]:
                data = yaml.safe_load(content)
            elif path.suffix.lower() == ".json":
                data = json.loads(content)
            else:
                raise ValueError(f"不支持的配置文件格式: {path.suffix}")

            # 解析配置
            new_config = SpartaEvolutionConfig.from_dict(data or {})

            # 更新配置
            with self._lock:
                self._config = new_config
                self._last_modified = path.stat().st_mtime
                self._reload_errors = []

            logger.info(f"配置加载成功: {config_path}, version={new_config.version}")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            error_msg = f"配置加载失败: {config_path}, 错误: {e}"
            logger.error(error_msg)

            with self._lock:
                self._reload_errors.append(error_msg)

            # 使用默认配置
            logger.warning("使用默认配置")
            return False

    def reload(self) -> bool:
        """重新加载配置

        白皮书依据: 第四章 4.9.6 热重载

        Returns:
            是否重载成功
        """
        if not self.config_path:
            logger.warning("未设置配置文件路径，无法重载")
            return False

        logger.info(f"开始重载配置: {self.config_path}")

        # 保存旧配置
        old_config = self._config

        # 尝试加载新配置
        success = self._load_config_from_file(self.config_path)

        if success:
            # 通知回调
            self._notify_reload_callbacks()
            logger.info("配置重载成功")
        else:
            # 恢复旧配置
            with self._lock:
                self._config = old_config
            logger.warning("配置重载失败，保持原配置")

        return success

    def check_and_reload(self) -> bool:
        """检查配置文件是否变更并重载

        Returns:
            是否进行了重载
        """
        if not self.config_path:
            return False

        path = Path(self.config_path)

        if not path.exists():
            return False

        current_mtime = path.stat().st_mtime

        with self._lock:
            if self._last_modified is None or current_mtime > self._last_modified:
                logger.info(f"检测到配置文件变更: {self.config_path}")
                return self.reload()

        return False

    def register_reload_callback(self, callback: Callable[[SpartaEvolutionConfig], None]) -> None:
        """注册重载回调

        Args:
            callback: 回调函数，接收新配置作为参数
        """
        with self._lock:
            self._reload_callbacks.append(callback)

        logger.debug(f"注册重载回调，当前回调数: {len(self._reload_callbacks)}")

    def unregister_reload_callback(self, callback: Callable[[SpartaEvolutionConfig], None]) -> None:
        """取消注册重载回调

        Args:
            callback: 要取消的回调函数
        """
        with self._lock:
            if callback in self._reload_callbacks:
                self._reload_callbacks.remove(callback)

        logger.debug(f"取消重载回调，当前回调数: {len(self._reload_callbacks)}")

    def _notify_reload_callbacks(self) -> None:
        """通知所有重载回调"""
        with self._lock:
            callbacks = self._reload_callbacks.copy()
            config = self._config

        for callback in callbacks:
            try:
                callback(config)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"重载回调执行失败: {e}")

    def update_config(self, updates: Dict[str, Any]) -> bool:
        """更新配置

        Args:
            updates: 配置更新字典

        Returns:
            是否更新成功
        """
        try:
            # 获取当前配置字典
            current_dict = self._config.to_dict()

            # 深度合并更新
            merged_dict = self._deep_merge(current_dict, updates)

            # 创建新配置
            new_config = SpartaEvolutionConfig.from_dict(merged_dict)

            # 更新配置
            with self._lock:
                self._config = new_config
                self._reload_errors = []

            # 通知回调
            self._notify_reload_callbacks()

            logger.info(f"配置更新成功: {list(updates.keys())}")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            error_msg = f"配置更新失败: {e}"
            logger.error(error_msg)

            with self._lock:
                self._reload_errors.append(error_msg)

            return False

    def _deep_merge(self, base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并字典

        Args:
            base: 基础字典
            updates: 更新字典

        Returns:
            合并后的字典
        """
        result = base.copy()

        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def validate_config(self, config_dict: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证配置

        Args:
            config_dict: 配置字典

        Returns:
            (是否有效, 错误列表)
        """
        errors = []

        try:
            SpartaEvolutionConfig.from_dict(config_dict)
            return True, []
        except ValueError as e:
            errors.append(str(e))
            return False, errors
        except Exception as e:  # pylint: disable=broad-exception-caught
            errors.append(f"配置验证异常: {e}")
            return False, errors

    def save_config(self, config_path: Optional[str] = None) -> bool:
        """保存配置到文件

        Args:
            config_path: 配置文件路径，None则使用当前路径

        Returns:
            是否保存成功
        """
        path_str = config_path or self.config_path

        if not path_str:
            logger.error("未指定配置文件路径")
            return False

        path = Path(path_str)

        try:
            # 确保目录存在
            path.parent.mkdir(parents=True, exist_ok=True)

            # 获取配置字典
            config_dict = self._config.to_dict()

            # 根据文件扩展名保存
            if path.suffix.lower() in [".yaml", ".yml"]:
                content = yaml.dump(config_dict, default_flow_style=False, allow_unicode=True)
            elif path.suffix.lower() == ".json":
                content = json.dumps(config_dict, indent=2, ensure_ascii=False)
            else:
                raise ValueError(f"不支持的配置文件格式: {path.suffix}")

            # 写入文件
            path.write_text(content, encoding="utf-8")

            # 更新最后修改时间
            with self._lock:
                self._last_modified = path.stat().st_mtime

            logger.info(f"配置保存成功: {path_str}")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"配置保存失败: {path_str}, 错误: {e}")
            return False

    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要

        Returns:
            配置摘要字典
        """
        with self._lock:
            return {
                "version": self._config.version,
                "config_path": self.config_path,
                "last_modified": (
                    datetime.fromtimestamp(self._last_modified).isoformat() if self._last_modified else None
                ),
                "auto_reload": self._auto_reload,
                "reload_callbacks_count": len(self._reload_callbacks),
                "has_errors": len(self._reload_errors) > 0,
                "arena_pass_score": self._config.arena.pass_score,
                "simulation_duration_days": self._config.simulation.duration_days,
                "z2h_gold_threshold": self._config.z2h.gold_sharpe_threshold,
                "decay_ic_threshold": self._config.decay.ic_warning_threshold,
            }
