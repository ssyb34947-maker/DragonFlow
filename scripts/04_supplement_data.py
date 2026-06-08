#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第四步：补充下载缺失的基准指数行情、个股基础信息与实时快照数据。

下载内容：
    1. 中证2000指数日行情（作为基准）
    2. 个股基础信息（行业、总市值、上市日期等）
    3. 实时截面快照（PE、PB、最新价等）

示例：

    uv run python scripts/04_supplement_data.py \
        --start-date 2026-01-01 \
        --end-date 2026-05-31 \
        --index-code 932000

无 uv 时：

    python scripts/04_supplement_data.py \
        --start-date 2026-01-01 --end-date 2026-05-31
"""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

# 让脚本能直接 `python scripts/xxx.py` 跑，无需 pip install -e .
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import pandas as pd

from dragonflow.data.download import (  # noqa: E402
    DownloadError,
    download_index_daily,
    download_spot_snapshot,
    download_stock_info_batch,
)
from dragonflow.utils.io import (  # noqa: E402
    ensure_dir,
    load_csv_codes,
    now_iso,
    project_root,
    resolve_path,
    save_csv,
    save_parquet,
    to_yyyymmdd,
    today_str,
)
from dragonflow.utils.logger import get_logger  # noqa: E402

log = get_logger("dragonflow.supplement_data", log_dir=str(resolve_path("logs")))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="补充下载中证2000基准指数行情、个股信息与截面快照")
    p.add_argument("--start-date", default="2026-01-01", help="起始日期 YYYY-MM-DD，默认 2026-01-01")
    p.add_argument("--end-date", default="2026-05-31", help="结束日期 YYYY-MM-DD，默认 2026-05-31")
    p.add_argument("--index-code", default="932000", help="指数代码，默认 932000（中证2000）")
    p.add_argument("--sleep", type=float, default=0.2, help="个股信息请求之间的间隔秒数，默认 0.2")
    p.add_argument("--skip-info", action="store_true", help="跳过个股基础信息下载")
    p.add_argument("--skip-snapshot", action="store_true", help="跳过实时截面快照下载")
    return p.parse_args()


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main() -> int:
    args = parse_args()

    start_date = args.start_date
    end_date = args.end_date
    index_code = args.index_code

    run_t0 = now_iso()
    log.info("=" * 80)
    log.info(
        f"DragonFlow 补充数据下载启动: start={start_date}, end={end_date}, "
        f"index={index_code}, sleep={args.sleep}s"
    )
    log.info(f"项目根目录: {project_root()}")
    log.info("=" * 80)

    sd_compact = to_yyyymmdd(start_date)
    ed_compact = to_yyyymmdd(end_date)
    today = today_str()

    # 路径
    p_proc = resolve_path("data", "processed")
    ensure_dir(p_proc)

    all_errors: list[DownloadError] = []
    output_files: list[str] = []

    # ---------------- 0. 读取成分股列表 ----------------
    constituents_path = resolve_path("data", "raw", "csi2000", f"constituents_{index_code}_latest.csv")
    if not constituents_path.exists():
        log.error(f"成分股文件不存在: {constituents_path}")
        log.error("请先运行 scripts/01_download_csi2000_data.py 下载成分股列表")
        return 1

    log.info(f"\n>>> [0/3] 读取成分股列表: {constituents_path}")
    constituents = load_csv_codes(constituents_path)
    log.info(f"成分股数量: {len(constituents)}")

    code_to_name: dict[str, str] = dict(
        zip(
            constituents["stock_code"].astype(str),
            constituents["stock_name"].astype(str) if "stock_name" in constituents.columns else [""] * len(constituents),
        )
    )
    all_codes = list(code_to_name.keys())

    # ---------------- 1. 指数日行情（基准） ----------------
    log.info(f"\n>>> [1/3] 下载中证2000指数日行情 (基准): {start_date} ~ {end_date}")
    index_daily, errs = download_index_daily(index_code, start_date, end_date)
    all_errors.extend(errs)

    # Fallback：如果接口全部失败，从已有个股日线合成等权指数
    if index_daily.empty:
        log.warning("指数日行情接口全部失败，尝试从个股日线合成等权指数...")
        daily_path = p_proc / f"stock_daily_csi2000_qfq_{sd_compact}_{ed_compact}_clean.csv"
        if not daily_path.exists():
            daily_path = p_proc / f"stock_daily_csi2000_qfq_{sd_compact}_{ed_compact}.csv"
        if daily_path.exists():
            daily_raw = pd.read_csv(daily_path, dtype={"stock_code": str}, encoding="utf-8-sig")
            # 每日等权平均收盘价 → 合成指数
            synth = daily_raw.groupby("date").agg(
                close=("close", "mean"),
                open=("open", "mean"),
                high=("high", "mean"),
                low=("low", "mean"),
                volume=("volume", "sum"),
                amount=("amount", "sum"),
            ).reset_index().sort_values("date")
            # 归一化到基点 1000
            base = synth["close"].iloc[0]
            if base > 0:
                for col in ["open", "high", "low", "close"]:
                    synth[col] = (synth[col] / base * 1000).round(2)
            synth["index_code"] = index_code
            synth["source"] = "synthetic_equal_weight"
            index_daily = synth
            log.info(f"合成等权指数成功：{len(index_daily)} 行")
        else:
            log.warning(f"个股日线文件也不存在: {daily_path}，指数数据将为空")

    if not index_daily.empty:
        idx_csv = p_proc / f"index_daily_{index_code}_{sd_compact}_{ed_compact}.csv"
        idx_pq = p_proc / f"index_daily_{index_code}_{sd_compact}_{ed_compact}.parquet"
        save_csv(index_daily, idx_csv)
        try:
            save_parquet(index_daily, idx_pq)
            output_files.extend([str(idx_csv), str(idx_pq)])
        except Exception as e:  # noqa: BLE001
            log.warning(f"指数 parquet 保存失败（不影响 CSV）: {e}")
            output_files.append(str(idx_csv))
        log.info(f"指数日行情 rows={len(index_daily)}, 已保存: {idx_csv}")

    # ---------------- 2. 个股基础信息 ----------------
    stock_info = pd.DataFrame()
    if not args.skip_info and all_codes:
        log.info(f"\n>>> [2/3] 下载个股基础信息 (n={len(all_codes)})")
        stock_info, errs = download_stock_info_batch(
            stock_codes=all_codes,
            stock_names=code_to_name,
            sleep=args.sleep,
        )
        all_errors.extend(errs)
        if not stock_info.empty:
            si_csv = p_proc / "stock_info_csi2000_latest.csv"
            si_pq = p_proc / "stock_info_csi2000_latest.parquet"
            save_csv(stock_info, si_csv)
            try:
                save_parquet(stock_info, si_pq)
                output_files.extend([str(si_csv), str(si_pq)])
            except Exception as e:  # noqa: BLE001
                log.warning(f"个股信息 parquet 保存失败: {e}")
                output_files.append(str(si_csv))
            log.info(f"个股基础信息 rows={len(stock_info)}, 已保存: {si_csv}")
        else:
            log.warning("个股基础信息下载为空")
    else:
        log.info("\n>>> [2/3] 跳过个股基础信息 (--skip-info)")

    # ---------------- 3. 截面快照 ----------------
    spot = pd.DataFrame()
    if not args.skip_snapshot and all_codes:
        log.info(f"\n>>> [3/3] 下载实时截面快照 (PE/PB/最新价) 并过滤成分股 (n={len(all_codes)})")
        spot, errs = download_spot_snapshot(constituent_codes=all_codes)
        all_errors.extend(errs)
        if not spot.empty:
            sp_csv = p_proc / "stock_spot_snapshot_csi2000_latest.csv"
            sp_pq = p_proc / "stock_spot_snapshot_csi2000_latest.parquet"
            save_csv(spot, sp_csv)
            try:
                save_parquet(spot, sp_pq)
                output_files.extend([str(sp_csv), str(sp_pq)])
            except Exception as e:  # noqa: BLE001
                log.warning(f"快照 parquet 保存失败: {e}")
                output_files.append(str(sp_csv))
            log.info(f"截面快照 rows={len(spot)}, 已保存: {sp_csv}")
        else:
            log.warning("截面快照下载为空")
    else:
        log.info("\n>>> [3/3] 跳过截面快照 (--skip-snapshot)")

    # ---------------- 错误日志 ----------------
    if all_errors:
        errors_path = p_proc / "supplement_errors.csv"
        err_df = pd.DataFrame([e.to_dict() for e in all_errors])
        save_csv(err_df, errors_path)
        output_files.append(str(errors_path))
        log.warning(f"共 {len(all_errors)} 个错误，已写入: {errors_path}")

    # ---------------- 汇总 ----------------
    log.info("\n" + "=" * 80)
    log.info("补充数据下载完成 — 汇总:")
    log.info(f"  成分股数量:       {len(constituents)}")
    log.info(f"  指数日行情行数:   {len(index_daily)}")
    log.info(f"  个股基础信息行数: {len(stock_info)}")
    log.info(f"  截面快照行数:     {len(spot)}")
    log.info(f"  错误数:           {len(all_errors)}")
    log.info(f"  输出文件:         {len(output_files)} 个")
    for f in output_files:
        log.info(f"    -> {f}")
    log.info(f"  启动时间: {run_t0}")
    log.info(f"  完成时间: {now_iso()}")
    log.info("=" * 80)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log.error("用户中断")
        sys.exit(130)
    except Exception as e:  # noqa: BLE001
        log.error(f"脚本异常退出: {e}\n{traceback.format_exc()}")
        sys.exit(1)
