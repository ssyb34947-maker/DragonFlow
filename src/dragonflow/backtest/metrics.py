"""Simple backtest metrics."""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_nav_metrics(nav: pd.DataFrame) -> dict:
    if nav.empty:
        return {}
    ret = nav["portfolio_return"].fillna(0.0)
    total = float(nav["nav"].iloc[-1] / nav["nav"].iloc[0] - 1.0) if len(nav) > 1 else 0.0
    ann_ret = float((1 + total) ** (252 / max(len(nav), 1)) - 1) if total > -1 else -1.0
    ann_vol = float(ret.std() * np.sqrt(252))
    sharpe = float(ann_ret / ann_vol) if ann_vol > 0 else 0.0
    dd = nav["nav"] / nav["nav"].cummax() - 1.0
    return {"total_return": total, "annual_return": ann_ret, "annual_volatility": ann_vol, "sharpe": sharpe, "max_drawdown": float(dd.min()), "n_days": int(len(nav))}
