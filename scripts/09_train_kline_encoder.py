#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parents[1]; _SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path: sys.path.insert(0, str(_SRC))
import argparse, pandas as pd
from dragonflow.modeling.config import load_model_config
from dragonflow.modeling.kline_encoder import train_kline_encoder
from dragonflow.utils.io import resolve_path, save_parquet

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--config', default='configs/model_v1.yaml'); args=ap.parse_args()
    cfg=load_model_config(args.config); paths=cfg['paths']
    panel_path = paths.get('tft_panel') if resolve_path(paths.get('tft_panel')).exists() else paths['base_panel']
    panel=pd.read_parquet(resolve_path(panel_path))
    kcfg=dict(cfg['kline_encoder']); kcfg['split']=cfg['split']
    emb=train_kline_encoder(panel, kcfg, resolve_path(paths['model_dir']))
    save_parquet(emb, resolve_path(paths['kline_embeddings']))
    print(f"K线编码器训练完成: {emb.shape}")
if __name__ == '__main__': main()
