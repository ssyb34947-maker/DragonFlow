#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parents[1]; _SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path: sys.path.insert(0, str(_SRC))
import argparse, pandas as pd
from dragonflow.modeling.config import load_model_config
from dragonflow.modeling.tft import predict_tft
from dragonflow.utils.io import resolve_path, save_parquet

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--config', default='configs/model_v1.yaml'); ap.add_argument('--range', choices=['valid','test','predict','all'], default='test'); args=ap.parse_args()
    cfg=load_model_config(args.config); paths=cfg['paths']; split=cfg['split']
    panel=pd.read_parquet(resolve_path(paths['tft_panel']))
    ranges={'valid': tuple(split['valid_time_idx']), 'test': tuple(split['test_time_idx']), 'predict': tuple(split['prediction_only_time_idx']), 'all': (split['valid_time_idx'][0], split['prediction_only_time_idx'][1])}
    pred=predict_tft(panel, ranges[args.range], resolve_path(paths['model_dir']))
    save_parquet(pred, resolve_path(paths['predictions']))
    print(f"预测完成: {pred.shape} -> {resolve_path(paths['predictions'])}")
if __name__ == '__main__': main()
