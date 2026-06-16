#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parents[1]; _SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path: sys.path.insert(0, str(_SRC))
import argparse, pandas as pd
from dragonflow.modeling.config import load_model_config
from dragonflow.backtest.portfolio import build_rebalance_weights
from dragonflow.backtest.execution import run_simple_backtest
from dragonflow.utils.io import resolve_path, save_json, save_parquet

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--config', default='configs/model_v1.yaml'); args=ap.parse_args()
    cfg=load_model_config(args.config); paths=cfg['paths']
    panel=pd.read_parquet(resolve_path(paths['tft_panel']))
    pred=pd.read_parquet(resolve_path(paths['predictions']))
    weights=build_rebalance_weights(pred, panel, cfg['backtest'])
    nav,pos,metrics=run_simple_backtest(weights, panel, cfg['backtest'])
    save_parquet(nav, resolve_path(paths['backtest_nav']))
    save_parquet(pos, resolve_path(paths['backtest_positions']))
    save_json(metrics, resolve_path(paths['backtest_metrics']))
    print('回测完成'); print(metrics)
if __name__ == '__main__': main()
