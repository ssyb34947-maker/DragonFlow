"""Daily-bar execution simulator."""
from __future__ import annotations

import pandas as pd

from dragonflow.backtest.metrics import compute_nav_metrics


def run_simple_backtest(weights: pd.DataFrame, panel: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if weights.empty:
        return pd.DataFrame(), pd.DataFrame(), {}
    prices = panel[["date","stock_code","ret_fwd_1d"]].copy()
    prices["date"] = pd.to_datetime(prices["date"])
    w = weights.copy(); w["date"] = pd.to_datetime(w["date"])
    dates = sorted(panel["date"].unique())
    current = pd.Series(dtype=float)
    nav = 1.0; rows=[]; pos_rows=[]
    cost = (float(cfg.get("buy_cost_bps",10)) + float(cfg.get("slippage_bps",5))) / 10000.0
    sell_cost = (float(cfg.get("sell_cost_bps",10)) + float(cfg.get("slippage_bps",5))) / 10000.0
    rebalance_map = {d: b.set_index("stock_code")["target_weight"] for d,b in w.groupby("date")}
    for d in dates:
        d = pd.Timestamp(d)
        turnover = 0.0
        if d in rebalance_map:
            target = rebalance_map[d]
            all_codes = current.index.union(target.index)
            prev = current.reindex(all_codes).fillna(0.0)
            new = target.reindex(all_codes).fillna(0.0)
            buy_turn = (new - prev).clip(lower=0).sum(); sell_turn = (prev - new).clip(lower=0).sum()
            turnover = float(buy_turn + sell_turn)
            nav *= (1.0 - float(buy_turn)*cost - float(sell_turn)*sell_cost)
            current = new[new.abs() > 1e-12]
        day_ret = prices[prices["date"] == d].set_index("stock_code")["ret_fwd_1d"]
        port_ret = float((current * day_ret.reindex(current.index).fillna(0.0)).sum()) if len(current) else 0.0
        nav *= (1.0 + port_ret)
        rows.append({"date": d, "nav": nav, "portfolio_return": port_ret, "turnover": turnover, "n_positions": int(len(current))})
        for code, wt in current.items(): pos_rows.append({"date": d, "stock_code": code, "weight": float(wt)})
    nav_df = pd.DataFrame(rows); pos_df = pd.DataFrame(pos_rows); metrics = compute_nav_metrics(nav_df)
    return nav_df, pos_df, metrics
