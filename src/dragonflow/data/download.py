"""中证2000相关数据下载（成分股 / 指数行情 / 个股行情 / 个股信息 / 快照 / 财报）。

设计原则：
    - 每个 ``download_*`` 都返回 ``(DataFrame, list_of_errors)``，不做磁盘落盘；
      上层脚本负责保存到 ``data/raw`` 与 ``data/processed``。
    - 对每个接口都准备 fallback 备用接口，单点失败不影响整个任务。
    - 网络异常使用 tenacity 重试；最终失败写入 ``download_errors.csv``。
"""
from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

try:
    import akshare as ak
except Exception as e:  # pragma: no cover - 这是顶层的可选导入提示
    ak = None
    _AK_IMPORT_ERROR = e
else:
    _AK_IMPORT_ERROR = None

try:
    from tenacity import (
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
    )
    _HAS_TENACITY = True
except Exception:
    _HAS_TENACITY = False

from ..utils.io import (
    ensure_dir,
    now_iso,
    today_str,
    to_dash_date,
    to_yyyymmdd,
)
from ..utils.logger import get_logger
from .schema import (
    BALANCE_RENAME,
    CASHFLOW_RENAME,
    CONSTITUENTS_RENAME,
    CONSTITUENTS_REQUIRED,
    INDEX_DAILY_COLS,
    INDEX_DAILY_RENAME,
    PROFIT_RENAME,
    SPOT_PREFERRED_COLS,
    SPOT_RENAME,
    STOCK_DAILY_COLS,
    STOCK_DAILY_RENAME,
    STOCK_INFO_COLS,
    STOCK_INFO_ITEM_RENAME,
    ensure_stock_code_str,
    rename_and_keep,
    standardize_date_col,
)

log = get_logger("dragonflow.download")


# ---------------------------------------------------------------------------
# 错误记录
# ---------------------------------------------------------------------------
@dataclass
class DownloadError:
    stage: str
    stock_code: str = ""
    stock_name: str = ""
    error_type: str = ""
    error_message: str = ""
    time: str = field(default_factory=now_iso)

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "time": self.time,
        }


def _require_akshare() -> None:
    if ak is None:
        raise RuntimeError(
            f"akshare 未安装或导入失败：{_AK_IMPORT_ERROR}. 请先 `uv add akshare` 或 `pip install akshare`."
        )


def _with_retry(fn: Callable, *args, max_attempts: int = 3, **kwargs):
    """轻量重试封装。tenacity 不存在时手动 retry。"""
    if _HAS_TENACITY:
        decorated = retry(
            reraise=True,
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=0.6, min=0.5, max=4.0),
            retry=retry_if_exception_type(Exception),
        )(fn)
        return decorated(*args, **kwargs)

    last_exc: Exception | None = None
    for i in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            last_exc = e
            time.sleep(0.5 * (i + 1))
    assert last_exc is not None
    raise last_exc


# ===========================================================================
# 1. 成分股
# ===========================================================================
def download_constituents(index_code: str = "932000") -> tuple[pd.DataFrame, list[DownloadError]]:
    """下载中证2000成分股，含 fallback。"""
    _require_akshare()
    errors: list[DownloadError] = []
    today = today_str()

    fallbacks: list[tuple[str, Callable[[], pd.DataFrame]]] = [
        ("index_stock_cons_csindex", lambda: ak.index_stock_cons_csindex(symbol=index_code)),
        ("index_stock_cons", lambda: ak.index_stock_cons(symbol=index_code)),
        ("index_stock_cons_sina", lambda: ak.index_stock_cons_sina(symbol=index_code)),
    ]

    df: pd.DataFrame | None = None
    used_source = ""
    for source, fn in fallbacks:
        try:
            log.info(f"[constituents] 尝试 {source}(symbol={index_code}) ...")
            raw = _with_retry(fn, max_attempts=2)
            if raw is None or raw.empty:
                raise RuntimeError("接口返回空表")
            df = raw
            used_source = source
            log.info(f"[constituents] {source} 成功, rows={len(df)}")
            break
        except Exception as e:  # noqa: BLE001
            log.warning(f"[constituents] {source} 失败: {e}")
            errors.append(
                DownloadError(
                    stage="constituents",
                    error_type=type(e).__name__,
                    error_message=f"{source}: {e}",
                )
            )

    if df is None:
        log.error("[constituents] 所有 fallback 均失败")
        return pd.DataFrame(columns=CONSTITUENTS_REQUIRED), errors

    df = df.rename(columns=CONSTITUENTS_RENAME)
    df = ensure_stock_code_str(df, "stock_code")

    # 补齐统一字段
    if "index_code" not in df.columns:
        df["index_code"] = index_code
    if "index_name" not in df.columns:
        df["index_name"] = "中证2000"
    if "exchange" not in df.columns:
        # 推断交易所
        df["exchange"] = df["stock_code"].apply(_infer_exchange)
    if "in_date" not in df.columns:
        df["in_date"] = ""
    df["source"] = used_source
    df["download_date"] = today

    # 保留所需列 + 其他原始字段（去重）
    keep_cols = CONSTITUENTS_REQUIRED + [c for c in df.columns if c not in CONSTITUENTS_REQUIRED]
    df = df[keep_cols]
    df = df.drop_duplicates(subset=["stock_code"]).reset_index(drop=True)
    return df, errors


def _infer_exchange(code: str) -> str:
    code = str(code).zfill(6)
    if code.startswith(("60", "68", "11", "5")):
        return "SSE"
    if code.startswith(("00", "30", "12", "15")):
        return "SZSE"
    if code.startswith(("8", "4")):
        return "BSE"
    return "UNKNOWN"


# ===========================================================================
# 2. 指数日行情
# ===========================================================================
def download_index_daily(
    index_code: str,
    start_date: str,
    end_date: str,
) -> tuple[pd.DataFrame, list[DownloadError]]:
    _require_akshare()
    errors: list[DownloadError] = []

    sd = to_yyyymmdd(start_date)
    ed = to_yyyymmdd(end_date)

    # 不同 AkShare 版本接受的 symbol/参数不同，尝试多种写法
    candidates: list[tuple[str, tuple, dict]] = [
        # ak.index_zh_a_hist 是 csi2000 在 AkShare 里最稳定的入口
        ("index_zh_a_hist", (), {"symbol": index_code, "period": "daily", "start_date": sd, "end_date": ed}),
        ("stock_zh_index_daily_em", (f"csi{index_code}",), {}),
        ("stock_zh_index_daily_em", (f"sh{index_code}",), {}),
        ("stock_zh_index_daily_em", (index_code,), {}),
        ("stock_zh_index_daily", (f"sh{index_code}",), {}),
        ("stock_zh_index_daily", (index_code,), {}),
    ]

    df: pd.DataFrame | None = None
    used_source = ""
    for fn_name, args, kwargs in candidates:
        fn = getattr(ak, fn_name, None)
        if fn is None:
            continue
        try:
            sig_str = ", ".join(list(map(repr, args)) + [f"{k}={v!r}" for k, v in kwargs.items()])
            log.info(f"[index_daily] {fn_name}({sig_str}) ...")
            raw = _with_retry(fn, *args, max_attempts=2, **kwargs)
            if raw is None or raw.empty:
                raise RuntimeError("接口返回空表")
            df = raw
            used_source = f"{fn_name}({sig_str})"
            log.info(f"[index_daily] {used_source} 成功, rows={len(df)}")
            break
        except Exception as e:  # noqa: BLE001
            log.warning(f"[index_daily] {fn_name} 失败: {e}")
            errors.append(
                DownloadError(
                    stage="index_daily",
                    error_type=type(e).__name__,
                    error_message=f"{fn_name}: {e}",
                )
            )

    if df is None:
        return pd.DataFrame(columns=INDEX_DAILY_COLS), errors

    # 部分接口（如 sina）把日期放在 index 里 -> reset 出来
    if "date" not in df.columns and "日期" not in df.columns:
        df = df.reset_index()

    df = df.rename(columns=INDEX_DAILY_RENAME)
    df = standardize_date_col(df, "date")

    # 过滤日期范围
    sd_dash = to_dash_date(start_date)
    ed_dash = to_dash_date(end_date)
    df = df[(df["date"] >= sd_dash) & (df["date"] <= ed_dash)].copy()

    df["index_code"] = index_code
    df["source"] = used_source

    for col in INDEX_DAILY_COLS:
        if col not in df.columns:
            df[col] = None
    df = df[INDEX_DAILY_COLS].sort_values("date").reset_index(drop=True)
    return df, errors


# ===========================================================================
# 3. 个股日行情
# ===========================================================================
def _fetch_single_stock_daily_em(
    stock_code: str,
    start_date: str,
    end_date: str,
    adjust: str = "qfq",
) -> pd.DataFrame:
    sd = to_yyyymmdd(start_date)
    ed = to_yyyymmdd(end_date)
    raw = ak.stock_zh_a_hist(
        symbol=stock_code,
        period="daily",
        start_date=sd,
        end_date=ed,
        adjust=adjust,
    )
    if raw is None or raw.empty:
        return pd.DataFrame()
    df = raw.rename(columns=STOCK_DAILY_RENAME).copy()
    df["stock_code"] = stock_code
    df["adjust"] = adjust
    df["source"] = "stock_zh_a_hist"
    df = standardize_date_col(df, "date")
    for col in STOCK_DAILY_COLS:
        if col not in df.columns:
            df[col] = None
    df = df[STOCK_DAILY_COLS]
    return df


_SINA_RENAME: dict[str, str] = {
    "date": "date",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "volume": "volume",
    "amount": "amount",
    "turnover": "turnover_rate",  # 新浪的 turnover 即换手率
}


def _fetch_single_stock_daily_sina(
    stock_code: str,
    start_date: str,
    end_date: str,
    adjust: str = "qfq",
) -> pd.DataFrame:
    """新浪源 fallback。symbol 需要前缀 sh/sz/bj。"""
    code = str(stock_code).zfill(6)
    # 顺序敏感：92 是北交所新代码段，必须先于 9xxxxx 的 sh B 股判断
    if code.startswith(("8", "4", "92")):
        prefix = "bj"
    elif code.startswith(("60", "68", "11", "5", "9")):
        prefix = "sh"
    else:
        prefix = "sz"
    sym = f"{prefix}{code}"
    sd = to_yyyymmdd(start_date)
    ed = to_yyyymmdd(end_date)
    raw = ak.stock_zh_a_daily(symbol=sym, start_date=sd, end_date=ed, adjust=adjust)
    if raw is None or raw.empty:
        return pd.DataFrame()
    df = raw.rename(columns=_SINA_RENAME).copy()
    if "date" not in df.columns:
        df = df.reset_index().rename(columns=_SINA_RENAME)
    df["stock_code"] = code
    df["adjust"] = adjust
    df["source"] = "stock_zh_a_daily(sina)"
    df = standardize_date_col(df, "date")
    # 新浪缺这些字段，置空（后续画像也可用 close 推算 pct_change）
    for col in STOCK_DAILY_COLS:
        if col not in df.columns:
            df[col] = None
    return df[STOCK_DAILY_COLS]


def _fetch_single_stock_daily(
    stock_code: str,
    start_date: str,
    end_date: str,
    adjust: str = "qfq",
) -> pd.DataFrame:
    """EM 主源 + sina 备源。某一只 EM 抓不到（限流/封 IP）时自动降级到 sina。"""
    try:
        df = _fetch_single_stock_daily_em(stock_code, start_date, end_date, adjust)
        if df is not None and not df.empty:
            return df
        raise RuntimeError("EM empty")
    except Exception as em_err:  # noqa: BLE001
        try:
            df2 = _fetch_single_stock_daily_sina(stock_code, start_date, end_date, adjust)
            if df2 is not None and not df2.empty:
                return df2
        except Exception as sina_err:  # noqa: BLE001
            raise RuntimeError(
                f"EM={type(em_err).__name__}:{em_err}; SINA={type(sina_err).__name__}:{sina_err}"
            ) from sina_err
        # 两边都返回空
        return pd.DataFrame()


def download_stock_daily_one(
    stock_code: str,
    start_date: str,
    end_date: str,
    adjust: str = "qfq",
    out_dir: str | Path | None = None,
    sleep: float = 0.0,
    force: bool = False,
) -> tuple[pd.DataFrame | None, DownloadError | None]:
    """下载单只股票日线。返回 (df, error)。"""
    _require_akshare()
    out_path: Path | None = None
    if out_dir is not None:
        out_path = Path(out_dir) / f"{stock_code}.csv"
        if out_path.exists() and not force:
            try:
                df = pd.read_csv(out_path, dtype={"stock_code": str}, encoding="utf-8-sig")
                if "stock_code" in df.columns:
                    df["stock_code"] = df["stock_code"].astype(str).str.zfill(6)
                return df, None
            except Exception as e:  # noqa: BLE001
                log.warning(f"[stock_daily] 读取已存在文件 {out_path} 失败，将重新下载: {e}")

    try:
        df = _with_retry(
            _fetch_single_stock_daily,
            stock_code,
            start_date,
            end_date,
            adjust,
            max_attempts=3,
        )
        if sleep > 0:
            time.sleep(sleep)
        if df is None or df.empty:
            err = DownloadError(
                stage="stock_daily",
                stock_code=stock_code,
                error_type="EmptyResult",
                error_message="接口返回空表（可能停牌 / 退市 / 不在交易日范围）",
            )
            return df if df is not None else pd.DataFrame(columns=STOCK_DAILY_COLS), err
        if out_path is not None:
            ensure_dir(out_path)
            df.to_csv(out_path, index=False, encoding="utf-8-sig")
        return df, None
    except Exception as e:  # noqa: BLE001
        err = DownloadError(
            stage="stock_daily",
            stock_code=stock_code,
            error_type=type(e).__name__,
            error_message=str(e)[:500],
        )
        return None, err


def download_stock_daily_batch(
    stock_codes: Iterable[str],
    stock_names: dict[str, str] | None,
    start_date: str,
    end_date: str,
    adjust: str = "qfq",
    out_dir: str | Path = "data/raw/stock_daily/qfq",
    sleep: float = 0.3,
    force: bool = False,
    progress: bool = True,
) -> tuple[pd.DataFrame, list[DownloadError]]:
    """批量下载成分股日线。串行 + sleep，避免触发 AkShare/东方财富限流。"""
    _require_akshare()
    out_dir = Path(out_dir)
    ensure_dir(out_dir)

    codes = list(stock_codes)
    errors: list[DownloadError] = []
    frames: list[pd.DataFrame] = []

    iterator = codes
    if progress:
        try:
            from tqdm import tqdm  # type: ignore

            iterator = tqdm(codes, desc=f"stock_daily[{adjust}]", ncols=88)
        except Exception:
            iterator = codes

    n_ok = 0
    n_fail = 0
    for code in iterator:
        df, err = download_stock_daily_one(
            stock_code=code,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
            out_dir=out_dir,
            sleep=sleep,
            force=force,
        )
        if err is not None:
            if stock_names is not None:
                err.stock_name = stock_names.get(code, "")
            errors.append(err)
            n_fail += 1
        if df is not None and not df.empty:
            frames.append(df)
            n_ok += 1

    log.info(
        f"[stock_daily] 完成: 成功 {n_ok}, 失败 {n_fail}, 总计 {len(codes)}"
    )

    if frames:
        merged = pd.concat(frames, ignore_index=True)
        merged = ensure_stock_code_str(merged, "stock_code")
        merged = merged.sort_values(["stock_code", "date"]).reset_index(drop=True)
    else:
        merged = pd.DataFrame(columns=STOCK_DAILY_COLS)

    return merged, errors


# ===========================================================================
# 4. 个股基础信息
# ===========================================================================
def _fetch_stock_info_em(stock_code: str) -> dict:
    raw = ak.stock_individual_info_em(symbol=stock_code)
    if raw is None or raw.empty:
        return {}
    # 该接口返回长表：item, value
    if {"item", "value"}.issubset(set(raw.columns)):
        d = dict(zip(raw["item"].astype(str), raw["value"]))
    else:
        d = dict(zip(raw.iloc[:, 0].astype(str), raw.iloc[:, 1]))
    return d


def download_stock_info_batch(
    stock_codes: Iterable[str],
    stock_names: dict[str, str] | None,
    sleep: float = 0.2,
    progress: bool = True,
) -> tuple[pd.DataFrame, list[DownloadError]]:
    _require_akshare()
    codes = list(stock_codes)
    errors: list[DownloadError] = []
    rows: list[dict] = []
    today = today_str()

    iterator = codes
    if progress:
        try:
            from tqdm import tqdm  # type: ignore

            iterator = tqdm(codes, desc="stock_info", ncols=88)
        except Exception:
            iterator = codes

    for code in iterator:
        try:
            raw = _with_retry(_fetch_stock_info_em, code, max_attempts=2)
            if sleep > 0:
                time.sleep(sleep)
            if not raw:
                errors.append(
                    DownloadError(
                        stage="stock_info",
                        stock_code=code,
                        stock_name=(stock_names or {}).get(code, ""),
                        error_type="EmptyResult",
                        error_message="stock_individual_info_em 返回空",
                    )
                )
                continue
            row = {}
            for cn, en in STOCK_INFO_ITEM_RENAME.items():
                if cn in raw:
                    row[en] = raw[cn]
            row.setdefault("stock_code", code)
            if (stock_names or {}).get(code) and not row.get("stock_name"):
                row["stock_name"] = stock_names[code]
            row["source"] = "stock_individual_info_em"
            row["download_date"] = today
            rows.append(row)
        except Exception as e:  # noqa: BLE001
            errors.append(
                DownloadError(
                    stage="stock_info",
                    stock_code=code,
                    stock_name=(stock_names or {}).get(code, ""),
                    error_type=type(e).__name__,
                    error_message=str(e)[:500],
                )
            )

    df = pd.DataFrame(rows)
    df = ensure_stock_code_str(df, "stock_code")
    for col in STOCK_INFO_COLS:
        if col not in df.columns:
            df[col] = None
    df = df[STOCK_INFO_COLS].drop_duplicates(subset=["stock_code"]).reset_index(drop=True)
    return df, errors


# ===========================================================================
# 5. 截面快照
# ===========================================================================
def download_spot_snapshot(
    constituent_codes: Iterable[str] | None = None,
) -> tuple[pd.DataFrame, list[DownloadError]]:
    _require_akshare()
    errors: list[DownloadError] = []
    try:
        raw = _with_retry(ak.stock_zh_a_spot_em, max_attempts=3)
    except Exception as e:  # noqa: BLE001
        errors.append(
            DownloadError(
                stage="spot_snapshot",
                error_type=type(e).__name__,
                error_message=str(e)[:500],
            )
        )
        return pd.DataFrame(columns=SPOT_PREFERRED_COLS), errors

    if raw is None or raw.empty:
        errors.append(
            DownloadError(
                stage="spot_snapshot",
                error_type="EmptyResult",
                error_message="stock_zh_a_spot_em 返回空",
            )
        )
        return pd.DataFrame(columns=SPOT_PREFERRED_COLS), errors

    df = raw.rename(columns=SPOT_RENAME).copy()
    df = ensure_stock_code_str(df, "stock_code")

    keep = [c for c in SPOT_PREFERRED_COLS if c in df.columns]
    df = df[keep].copy()

    if constituent_codes is not None:
        codes = set(c.zfill(6) for c in constituent_codes)
        df = df[df["stock_code"].isin(codes)].reset_index(drop=True)

    return df, errors


# ===========================================================================
# 6. 财务报表
# ===========================================================================
def _resolve_quarter_date(preferred: str = "20260331") -> list[str]:
    """从首选季度向前回退候选列表。"""
    order = [
        preferred,
        "20251231",
        "20250930",
        "20250630",
        "20250331",
    ]
    # 去重 + 保序
    seen = set()
    out = []
    for d in order:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def _try_financial_endpoint(
    fn_name: str,
    candidate_dates: list[str],
    rename_map: dict[str, str],
) -> tuple[pd.DataFrame, str, list[DownloadError]]:
    """对一个财务报表接口在多个季度日期上做 fallback。"""
    errors: list[DownloadError] = []
    fn = getattr(ak, fn_name, None)
    if fn is None:
        errors.append(
            DownloadError(
                stage=f"financial:{fn_name}",
                error_type="AttributeError",
                error_message=f"akshare 没有 {fn_name}",
            )
        )
        return pd.DataFrame(), "", errors

    for d in candidate_dates:
        try:
            log.info(f"[financial] {fn_name}(date={d}) ...")
            raw = _with_retry(fn, date=d, max_attempts=2)
            if raw is None or raw.empty:
                raise RuntimeError("空表")
            df = raw.rename(columns=rename_map).copy()
            df = ensure_stock_code_str(df, "stock_code")
            df["report_date_param"] = d
            log.info(f"[financial] {fn_name}({d}) 成功, rows={len(df)}")
            return df, d, errors
        except Exception as e:  # noqa: BLE001
            log.warning(f"[financial] {fn_name}({d}) 失败: {e}")
            errors.append(
                DownloadError(
                    stage=f"financial:{fn_name}",
                    error_type=type(e).__name__,
                    error_message=f"date={d}: {e}",
                )
            )
    return pd.DataFrame(), "", errors


def download_financial_reports(
    preferred_date: str = "20260331",
    constituent_codes: Iterable[str] | None = None,
) -> tuple[dict[str, pd.DataFrame], dict[str, str], list[DownloadError]]:
    """下载利润表 / 资产负债表 / 现金流量表的最近可用季度。

    Returns:
        (frames_dict, used_dates_dict, errors)
        frames_dict 的键固定为 ``profit / balance / cashflow``。
    """
    _require_akshare()
    candidates = _resolve_quarter_date(preferred_date)
    out_frames: dict[str, pd.DataFrame] = {}
    used: dict[str, str] = {}
    errs: list[DownloadError] = []

    targets = [
        ("profit", "stock_lrb_em", PROFIT_RENAME),
        ("balance", "stock_zcfz_em", BALANCE_RENAME),
        ("cashflow", "stock_xjll_em", CASHFLOW_RENAME),
    ]
    for key, fn_name, rmap in targets:
        df, used_date, e = _try_financial_endpoint(fn_name, candidates, rmap)
        out_frames[key] = df
        used[key] = used_date
        errs.extend(e)

    if constituent_codes is not None:
        codes = set(c.zfill(6) for c in constituent_codes)
        for k in list(out_frames.keys()):
            df = out_frames[k]
            if not df.empty and "stock_code" in df.columns:
                out_frames[k] = df[df["stock_code"].isin(codes)].reset_index(drop=True)

    return out_frames, used, errs
