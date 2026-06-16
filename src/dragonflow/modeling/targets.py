"""Forward-return target construction."""
from __future__ import annotations

import pandas as pd


def add_forward_return_targets(
    df: pd.DataFrame,
    index_df: pd.DataFrame | None = None,
    horizon: int = 5,
) -> pd.DataFrame:
    """Add leakage-safe forward return targets.

    The main horizon target uses ``t+1`` as the entry reference and ``t+h`` as
    the exit reference.  This matches a signal generated after the close of
    date ``t`` and traded on the next bar.
    """
    out = df.sort_values(["stock_code", "date"]).copy()
    g = out.groupby("stock_code", sort=False)

    next_close = g["close"].shift(-1)
    exit_close = g["close"].shift(-horizon)
    out["ret_fwd_1d"] = g["close"].shift(-1) / out["close"] - 1.0
    out[f"ret_fwd_{horizon}d"] = exit_close / next_close - 1.0

    if index_df is not None and not index_df.empty:
        idx = index_df[["date", "close"]].copy()
        idx["date"] = pd.to_datetime(idx["date"])
        idx = idx.sort_values("date")
        idx_next = idx["close"].shift(-1)
        idx_exit = idx["close"].shift(-horizon)
        idx[f"index_ret_fwd_{horizon}d"] = idx_exit / idx_next - 1.0
        out = out.merge(
            idx[["date", f"index_ret_fwd_{horizon}d"]],
            on="date",
            how="left",
        )
    else:
        out[f"index_ret_fwd_{horizon}d"] = 0.0

    out[f"excess_ret_fwd_{horizon}d"] = (
        out[f"ret_fwd_{horizon}d"] - out[f"index_ret_fwd_{horizon}d"]
    )
    out[f"direction_fwd_{horizon}d"] = (
        out[f"excess_ret_fwd_{horizon}d"] > 0
    ).astype("float64")
    out.loc[out[f"excess_ret_fwd_{horizon}d"].isna(), f"direction_fwd_{horizon}d"] = pd.NA
    return out
