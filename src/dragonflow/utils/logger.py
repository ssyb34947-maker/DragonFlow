"""统一日志：优先使用 loguru，回退到 logging。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    from loguru import logger as _loguru_logger
    _HAS_LOGURU = True
except Exception:
    _HAS_LOGURU = False

_CONFIGURED = False


def get_logger(name: str = "dragonflow", log_dir: str | Path | None = None) -> Any:
    """返回一个全局 logger。第一次调用会做基本配置。

    Args:
        name: 日志名（仅在 fallback 到标准 logging 时使用）。
        log_dir: 若提供，则同时写入文件 ``<log_dir>/dragonflow.log``。
    """
    global _CONFIGURED

    if _HAS_LOGURU:
        if not _CONFIGURED:
            _loguru_logger.remove()
            _loguru_logger.add(
                sys.stderr,
                level="INFO",
                format=(
                    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> "
                    "| <level>{level: <7}</level> "
                    "| <cyan>{name}:{line}</cyan> - <level>{message}</level>"
                ),
                colorize=True,
            )
            if log_dir is not None:
                log_path = Path(log_dir)
                log_path.mkdir(parents=True, exist_ok=True)
                _loguru_logger.add(
                    log_path / "dragonflow.log",
                    level="DEBUG",
                    rotation="10 MB",
                    retention=5,
                    encoding="utf-8",
                )
            _CONFIGURED = True
        return _loguru_logger

    import logging

    py_logger = logging.getLogger(name)
    if not _CONFIGURED:
        py_logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s:%(lineno)d - %(message)s")
        )
        py_logger.addHandler(handler)
        if log_dir is not None:
            log_path = Path(log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(log_path / "dragonflow.log", encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(
                logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s:%(lineno)d - %(message)s")
            )
            py_logger.addHandler(fh)
        _CONFIGURED = True
    return py_logger
