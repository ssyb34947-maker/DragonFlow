"""IO 工具：路径、CSV/Parquet 读写、原子写。"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]


def project_root() -> Path:
    """返回项目根目录绝对路径（即仓库根，不依赖 cwd）。"""
    return PROJECT_ROOT


def resolve_path(*parts: str | Path) -> Path:
    """基于项目根目录拼接路径。"""
    return PROJECT_ROOT.joinpath(*[str(p) for p in parts])


def ensure_dir(path: str | Path) -> Path:
    """确保目录存在并返回 Path 对象。如果传入文件路径会创建其父目录。"""
    p = Path(path)
    if p.suffix:
        p.parent.mkdir(parents=True, exist_ok=True)
    else:
        p.mkdir(parents=True, exist_ok=True)
    return p


def today_str(fmt: str = "%Y%m%d") -> str:
    return datetime.now().strftime(fmt)


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def to_yyyymmdd(date_str: str) -> str:
    """``2026-01-01`` -> ``20260101``。支持已是 ``20260101`` 的写法。"""
    s = str(date_str).strip()
    if "-" in s:
        return s.replace("-", "")
    return s


def to_dash_date(date_str: str) -> str:
    """``20260101`` -> ``2026-01-01``。"""
    s = str(date_str).strip()
    if "-" in s:
        return s
    if len(s) == 8:
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return s


def save_csv(df: pd.DataFrame, path: str | Path, **kwargs: Any) -> Path:
    """落盘 CSV，UTF-8-SIG（Excel 友好），自动建父目录。"""
    p = Path(path)
    ensure_dir(p)
    kwargs.setdefault("index", False)
    kwargs.setdefault("encoding", "utf-8-sig")
    df.to_csv(p, **kwargs)
    return p


def save_parquet(df: pd.DataFrame, path: str | Path) -> Path:
    """落盘 Parquet。若 pyarrow 缺失则提示。"""
    p = Path(path)
    ensure_dir(p)
    try:
        df.to_parquet(p, index=False)
    except Exception as e:
        raise RuntimeError(
            f"保存 parquet 失败，请确认已安装 pyarrow: {e}"
        ) from e
    return p


def save_json(obj: Any, path: str | Path) -> Path:
    p = Path(path)
    ensure_dir(p)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
    return p


def load_csv_codes(path: str | Path, code_col: str = "stock_code") -> pd.DataFrame:
    """读取 CSV，并保证 ``stock_code`` 是 6 位字符串。"""
    df = pd.read_csv(path, dtype={code_col: str}, encoding="utf-8-sig")
    if code_col in df.columns:
        df[code_col] = df[code_col].astype(str).str.zfill(6)
    return df


def append_error_row(path: str | Path, row: dict) -> None:
    """以追加方式写一行错误日志 CSV（含表头管理）。"""
    p = Path(path)
    ensure_dir(p)
    df = pd.DataFrame([row])
    if p.exists():
        df.to_csv(p, mode="a", header=False, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(p, mode="w", header=True, index=False, encoding="utf-8-sig")


def list_existing_stock_files(
    raw_dir: str | Path,
    stock_codes: Iterable[str],
    suffix: str = ".csv",
) -> dict[str, bool]:
    """返回 ``stock_code -> 是否已存在文件``。"""
    raw = Path(raw_dir)
    result: dict[str, bool] = {}
    for code in stock_codes:
        result[code] = (raw / f"{code}{suffix}").exists()
    return result
