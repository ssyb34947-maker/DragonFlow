#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第一步：下载中证2000相关行情/基本面/财报数据并落盘。

只做下载与本地落盘，不做建模 / 聚类 / 画像 / 可视化。

示例：

    uv run python scripts/01_download_csi2000_data.py \
        --start-date 2026-01-01 \
        --end-date 2026-05-31 \
        --index-code 932000 \
        --adjust qfq

无 uv 时：

    python scripts/01_download_csi2000_data.py \
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
    download_constituents,
    download_financial_reports,
    download_index_daily,
    download_spot_snapshot,
    download_stock_daily_batch,
    download_stock_info_batch,
)
from dragonflow.utils.io import (  # noqa: E402
    ensure_dir,
    now_iso,
    project_root,
    resolve_path,
    save_csv,
    save_json,
    save_parquet,
    to_yyyymmdd,
    today_str,
)
from dragonflow.utils.logger import get_logger  # noqa: E402

log = get_logger("dragonflow.download_csi2000", log_dir=str(resolve_path("logs")))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="下载中证2000相关数据到本地 data/ 目录")
    p.add_argument("--start-date", default="2026-01-01", help="起始日期 YYYY-MM-DD，默认 2026-01-01")
    p.add_argument("--end-date", default="2026-05-31", help="结束日期 YYYY-MM-DD，默认 2026-05-31")
    p.add_argument("--index-code", default="932000", help="指数代码，默认 932000（中证2000）")
    p.add_argument("--adjust", default="qfq", choices=["", "qfq", "hfq"], help="复权方式，默认 qfq")
    p.add_argument("--force", action="store_true", help="忽略已存在的单只股票 csv 文件，强制重新下载")
    p.add_argument("--sleep", type=float, default=0.3, help="单只股票请求之间的间隔秒数，默认 0.3")
    p.add_argument("--max-workers", type=int, default=1, help="并发数（当前默认串行 1；预留参数）")
    p.add_argument(
        "--skip-fundamental",
        action="store_true",
        help="跳过个股基础信息 / 财务报表 / 快照（仅做行情下载，用于快速冒烟）",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="仅下载前 N 只成分股的日线，用于快速测试，0 表示全部",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# 数据质量检查
# ---------------------------------------------------------------------------
def quality_check(
    constituents: pd.DataFrame,
    stock_daily: pd.DataFrame,
    n_failed: int,
    n_total: int,
) -> list[str]:
    """返回告警消息列表。"""
    warnings: list[str] = []

    # 1. 成分股数量
    n_const = len(constituents)
    if n_const < 1500 or n_const > 2200:
        warnings.append(f"[QC] 成分股数量异常: {n_const} (预期约 2000)")
    else:
        log.info(f"[QC] 成分股数量: {n_const} (OK)")

    # 2. 代码是否 6 位字符串
    if not constituents.empty and "stock_code" in constituents.columns:
        bad = constituents["stock_code"].astype(str).str.len() != 6
        if bad.any():
            warnings.append(f"[QC] {bad.sum()} 只成分股 stock_code 不是 6 位字符串")
        else:
            log.info("[QC] 成分股代码均为 6 位字符串 (OK)")

    # 3. 日行情是否非空
    if stock_daily.empty:
        warnings.append("[QC] 合并后的 stock_daily 长表为空！请检查接口连通性")
    else:
        log.info(f"[QC] stock_daily 总行数: {len(stock_daily)}")

    # 4. 关键列
    required = ["date", "stock_code", "close", "amount", "turnover_rate"]
    missing = [c for c in required if c not in stock_daily.columns]
    if missing:
        warnings.append(f"[QC] stock_daily 缺少关键列: {missing}")
    else:
        log.info("[QC] stock_daily 关键列齐全 (OK)")

    # 5. 失败率
    if n_total > 0:
        fail_ratio = n_failed / n_total
        if fail_ratio > 0.2:
            warnings.append(
                f"[QC] !!!!!!!!! 成分股日线下载失败比例 {fail_ratio:.1%} 超过 20%，请检查网络/接口 !!!!!!!!!"
            )
        else:
            log.info(f"[QC] 失败比例 {fail_ratio:.1%} (OK)")

    return warnings


def build_coverage_report(
    constituents: pd.DataFrame,
    stock_daily: pd.DataFrame,
    expected_start: str,
    expected_end: str,
    failed_codes: set[str],
) -> pd.DataFrame:
    if constituents.empty:
        return pd.DataFrame(
            columns=[
                "stock_code",
                "stock_name",
                "n_daily_rows",
                "first_date",
                "last_date",
                "missing_ratio",
                "download_success",
            ]
        )
    code_to_name = dict(zip(constituents["stock_code"].astype(str), constituents.get("stock_name", "")))

    if not stock_daily.empty:
        gb = stock_daily.groupby("stock_code", as_index=False).agg(
            n_daily_rows=("date", "count"),
            first_date=("date", "min"),
            last_date=("date", "max"),
        )
    else:
        gb = pd.DataFrame(columns=["stock_code", "n_daily_rows", "first_date", "last_date"])

    rows = []
    # 计算预期交易日数粗估：使用指数日历或者用日历中工作日近似
    try:
        biz = pd.bdate_range(start=expected_start, end=expected_end)
        expected_n = len(biz)
    except Exception:
        expected_n = 0

    gb_map = {r["stock_code"]: r for _, r in gb.iterrows()}
    for code in constituents["stock_code"].astype(str):
        rec = gb_map.get(code)
        n = int(rec["n_daily_rows"]) if rec is not None else 0
        first = rec["first_date"] if rec is not None else ""
        last = rec["last_date"] if rec is not None else ""
        missing_ratio = 0.0
        if expected_n > 0:
            missing_ratio = max(0.0, 1.0 - n / expected_n)
        rows.append(
            {
                "stock_code": code,
                "stock_name": code_to_name.get(code, ""),
                "n_daily_rows": n,
                "first_date": first,
                "last_date": last,
                "missing_ratio": round(missing_ratio, 4),
                "download_success": (code not in failed_codes) and n > 0,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main() -> int:
    args = parse_args()

    start_date = args.start_date
    end_date = args.end_date
    index_code = args.index_code
    adjust = args.adjust or "qfq"

    run_t0 = now_iso()
    log.info("=" * 80)
    log.info(
        f"DragonFlow 数据下载启动: start={start_date}, end={end_date}, index={index_code}, "
        f"adjust={adjust}, force={args.force}, sleep={args.sleep}s"
    )
    log.info(f"项目根目录: {project_root()}")
    log.info("=" * 80)

    sd_compact = to_yyyymmdd(start_date)
    ed_compact = to_yyyymmdd(end_date)
    today = today_str()

    # 路径
    p_raw_csi = resolve_path("data", "raw", "csi2000")
    p_raw_stock = resolve_path("data", "raw", "stock_daily", adjust)
    p_raw_fund = resolve_path("data", "raw", "fundamental")
    p_proc = resolve_path("data", "processed")
    for p in (p_raw_csi, p_raw_stock, p_raw_fund, p_proc):
        ensure_dir(p)

    errors_path = p_proc / "download_errors.csv"
    # 清掉旧的错误文件（如有），避免上次的脏数据混入
    if errors_path.exists():
        errors_path.unlink()

    all_errors: list[DownloadError] = []
    output_files: list[str] = []

    # ---------------- 1. 成分股 ----------------
    log.info("\n>>> [1/6] 下载中证2000成分股")
    constituents, errs = download_constituents(index_code=index_code)
    all_errors.extend(errs)
    if constituents.empty:
        log.error("成分股下载失败，后续依赖该列表的步骤都无法进行")
    else:
        f1 = save_csv(constituents, p_raw_csi / f"constituents_{index_code}_{today}.csv")
        f2 = save_csv(constituents, p_raw_csi / f"constituents_{index_code}_latest.csv")
        output_files.extend([str(f1), str(f2)])
        log.info(f"成分股已保存: {f1} ({len(constituents)} rows)")

    code_to_name = dict(
        zip(
            constituents["stock_code"].astype(str) if not constituents.empty else [],
            constituents["stock_name"].astype(str) if not constituents.empty else [],
        )
    )
    all_codes = list(code_to_name.keys())
    if args.limit and args.limit > 0:
        log.warning(f"--limit={args.limit} 已生效，仅下载前 {args.limit} 只成分股的日线（测试用途）")
        target_codes = all_codes[: args.limit]
    else:
        target_codes = all_codes

    # ---------------- 2. 指数日行情 ----------------
    log.info("\n>>> [2/6] 下载中证2000指数日行情")
    index_daily, errs = download_index_daily(index_code, start_date, end_date)
    all_errors.extend(errs)
    if index_daily.empty:
        log.warning("指数日行情下载为空")
    else:
        idx_csv = p_raw_csi / f"index_daily_{index_code}_{sd_compact}_{ed_compact}.csv"
        idx_pq = p_raw_csi / f"index_daily_{index_code}_{sd_compact}_{ed_compact}.parquet"
        save_csv(index_daily, idx_csv)
        try:
            save_parquet(index_daily, idx_pq)
            output_files.extend([str(idx_csv), str(idx_pq)])
        except Exception as e:  # noqa: BLE001
            log.warning(f"指数 parquet 保存失败（不影响 CSV）: {e}")
            output_files.append(str(idx_csv))
        log.info(f"指数日行情 rows={len(index_daily)}")

    # ---------------- 3. 个股日行情 ----------------
    log.info(f"\n>>> [3/6] 下载 {len(target_codes)} 只成分股日行情 (adjust={adjust})")
    stock_daily = pd.DataFrame()
    stock_daily_errors: list[DownloadError] = []
    if not target_codes:
        log.warning("没有成分股代码，跳过个股日行情")
    else:
        stock_daily, stock_daily_errors = download_stock_daily_batch(
            stock_codes=target_codes,
            stock_names=code_to_name,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
            out_dir=p_raw_stock,
            sleep=args.sleep,
            force=args.force,
        )
        all_errors.extend(stock_daily_errors)

        if not stock_daily.empty:
            sd_csv = p_proc / f"stock_daily_csi2000_{adjust}_{sd_compact}_{ed_compact}.csv"
            sd_pq = p_proc / f"stock_daily_csi2000_{adjust}_{sd_compact}_{ed_compact}.parquet"
            save_csv(stock_daily, sd_csv)
            try:
                save_parquet(stock_daily, sd_pq)
                output_files.extend([str(sd_csv), str(sd_pq)])
            except Exception as e:  # noqa: BLE001
                log.warning(f"日线 parquet 保存失败（不影响 CSV）: {e}")
                output_files.append(str(sd_csv))

    failed_codes = {e.stock_code for e in stock_daily_errors if e.stock_code}
    n_failed = len(failed_codes)
    n_ok = len(target_codes) - n_failed

    # ---------------- 4. 个股基础信息 ----------------
    stock_info = pd.DataFrame()
    if not args.skip_fundamental and target_codes:
        log.info(f"\n>>> [4/6] 下载个股基础信息 (n={len(target_codes)})")
        stock_info, errs = download_stock_info_batch(
            stock_codes=target_codes,
            stock_names=code_to_name,
            sleep=max(0.0, args.sleep / 2),
        )
        all_errors.extend(errs)
        if not stock_info.empty:
            si_csv = p_raw_fund / f"stock_info_csi2000_{today}.csv"
            si_pq = p_proc / "stock_info_csi2000_latest.parquet"
            save_csv(stock_info, si_csv)
            try:
                save_parquet(stock_info, si_pq)
                output_files.extend([str(si_csv), str(si_pq)])
            except Exception as e:  # noqa: BLE001
                log.warning(f"个股信息 parquet 保存失败: {e}")
                output_files.append(str(si_csv))
            log.info(f"个股基础信息 rows={len(stock_info)}")
    else:
        log.info("\n>>> [4/6] 跳过个股基础信息 (--skip-fundamental)")

    # ---------------- 5. 截面快照 ----------------
    spot = pd.DataFrame()
    if not args.skip_fundamental and target_codes:
        log.info("\n>>> [5/6] 下载实时截面快照并过滤成分股")
        spot, errs = download_spot_snapshot(constituent_codes=target_codes)
        all_errors.extend(errs)
        if not spot.empty:
            sp_csv = p_raw_fund / f"stock_spot_snapshot_{today}.csv"
            sp_pq = p_proc / "stock_spot_snapshot_csi2000_latest.parquet"
            save_csv(spot, sp_csv)
            try:
                save_parquet(spot, sp_pq)
                output_files.extend([str(sp_csv), str(sp_pq)])
            except Exception as e:  # noqa: BLE001
                log.warning(f"快照 parquet 保存失败: {e}")
                output_files.append(str(sp_csv))
            log.info(f"快照 rows={len(spot)}")
    else:
        log.info("\n>>> [5/6] 跳过截面快照 (--skip-fundamental)")

    # ---------------- 6. 财务报表 ----------------
    fundamentals_rows = 0
    if not args.skip_fundamental and target_codes:
        log.info("\n>>> [6/6] 下载利润表 / 资产负债表 / 现金流量表")
        frames, used_dates, errs = download_financial_reports(
            preferred_date="20260331",
            constituent_codes=target_codes,
        )
        all_errors.extend(errs)
        # 三张表分别保存到 raw（含全市场，过滤前的版本太大，这里直接保存过滤后的）
        merged_fund_rows: list[pd.DataFrame] = []
        for key, df in frames.items():
            if df is None or df.empty:
                continue
            d = used_dates.get(key, today)
            raw_path = p_raw_fund / f"{key}_{d or today}.csv"
            save_csv(df, raw_path)
            output_files.append(str(raw_path))

            # 标记表类型加入合并
            tmp = df.copy()
            tmp["report_type"] = key
            merged_fund_rows.append(tmp)

        if merged_fund_rows:
            merged = pd.concat(merged_fund_rows, ignore_index=True, sort=False)
            fundamentals_rows = len(merged)
            fp_csv = p_proc / "fundamental_csi2000_latest.csv"
            fp_pq = p_proc / "fundamental_csi2000_latest.parquet"
            save_csv(merged, fp_csv)
            try:
                save_parquet(merged, fp_pq)
                output_files.extend([str(fp_csv), str(fp_pq)])
            except Exception as e:  # noqa: BLE001
                log.warning(f"财务报表 parquet 保存失败: {e}")
                output_files.append(str(fp_csv))
            log.info(f"财务报表合并 rows={fundamentals_rows}")
        else:
            log.warning("三张财务报表全部为空，未生成 fundamental_csi2000_latest.*")
    else:
        log.info("\n>>> [6/6] 跳过财务报表 (--skip-fundamental)")

    # ---------------- 写错误日志 ----------------
    if all_errors:
        err_df = pd.DataFrame([e.to_dict() for e in all_errors])
        save_csv(err_df, errors_path)
        output_files.append(str(errors_path))
        log.info(f"已写入错误清单: {errors_path} ({len(err_df)} rows)")

    # ---------------- 数据质量检查 ----------------
    log.info("\n>>> 数据质量检查")
    warns = quality_check(constituents, stock_daily, n_failed, len(target_codes))
    for w in warns:
        log.warning(w)

    # ---------------- 覆盖率报告 ----------------
    coverage = build_coverage_report(
        constituents,
        stock_daily,
        expected_start=start_date,
        expected_end=end_date,
        failed_codes=failed_codes,
    )
    cov_path = p_proc / "data_coverage_report.csv"
    save_csv(coverage, cov_path)
    output_files.append(str(cov_path))
    log.info(f"数据覆盖率报告: {cov_path} ({len(coverage)} rows)")

    # ---------------- manifest ----------------
    manifest = {
        "run_time": run_t0,
        "finish_time": now_iso(),
        "start_date": start_date,
        "end_date": end_date,
        "index_code": index_code,
        "adjust": adjust,
        "n_constituents": int(len(constituents)),
        "n_stock_daily_success": int(n_ok),
        "n_stock_daily_failed": int(n_failed),
        "n_index_daily_rows": int(len(index_daily) if 'index_daily' in locals() else 0),
        "n_stock_daily_rows": int(len(stock_daily) if 'stock_daily' in locals() else 0),
        "n_stock_info_rows": int(len(stock_info) if 'stock_info' in locals() else 0),
        "n_fundamental_rows": int(fundamentals_rows),
        "warnings": warns,
        "output_files": output_files,
    }
    manifest_path = p_proc / "download_manifest.json"
    save_json(manifest, manifest_path)
    log.info(f"manifest: {manifest_path}")

    log.info("\n" + "=" * 80)
    log.info(
        f"下载完成: 成分股 {len(constituents)} 只, "
        f"日线成功 {n_ok} / 失败 {n_failed}, "
        f"指数行情 {len(index_daily) if 'index_daily' in locals() else 0} 行"
    )
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
