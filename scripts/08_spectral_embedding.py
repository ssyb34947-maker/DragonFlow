#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parents[1]; _SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path: sys.path.insert(0, str(_SRC))
import argparse, pandas as pd
from dragonflow.modeling.config import load_model_config
from dragonflow.analysis.spectral_embedding import build_rolling_spectral_embeddings, attach_spectral_features, add_cluster_peer_features
from dragonflow.utils.io import resolve_path, save_json, save_parquet
from dragonflow.modeling.schema import V1_SCHEMA

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--config', default='configs/model_v1.yaml'); args=ap.parse_args()
    cfg=load_model_config(args.config); sp=cfg['spectral']; paths=cfg['paths']
    panel=pd.read_parquet(resolve_path(paths['base_panel']))
    sp_args = {k: v for k, v in sp.items() if k != 'enabled'}
    emb=build_rolling_spectral_embeddings(panel, **sp_args)
    save_parquet(emb, resolve_path(paths['spectral_embeddings']))
    panel2=attach_spectral_features(panel, emb, embedding_dim=int(sp['embedding_dim']))
    panel2=add_cluster_peer_features(panel2)
    save_parquet(panel2, resolve_path(paths['tft_panel']))
    save_json(V1_SCHEMA.to_dict(), resolve_path(paths['feature_schema']))
    print(f"谱嵌入完成: embeddings={len(emb)} panel={panel2.shape}")
if __name__ == '__main__': main()
