"""Lightweight temporal fusion-style model for return quantile prediction."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import json
import pickle

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from dragonflow.modeling.config import get_device_name
from dragonflow.modeling.torch_datasets import SequenceIndex, TorchSequenceDataset, make_loader, require_torch
from dragonflow.utils.io import ensure_dir
from dragonflow.utils.logger import get_logger

logger = get_logger(__name__)


def quantile_loss(pred, target, quantiles, torch):
    losses = []
    for i, q in enumerate(quantiles):
        e = target - pred[:, i]
        losses.append(torch.maximum((q - 1) * e, q * e).unsqueeze(1))
    return torch.mean(torch.cat(losses, dim=1))


def build_model(input_dim: int, cfg: dict[str, Any]):
    torch, _, _ = require_torch()
    nn = torch.nn
    quantiles = cfg.get("quantiles", [0.1, 0.5, 0.9])

    class TinyTemporalFusion(nn.Module):
        def __init__(self):
            super().__init__()
            d_model = int(cfg.get("d_model", 48))
            self.proj = nn.Linear(input_dim, d_model)
            layer = nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=int(cfg.get("n_heads", 2)),
                dim_feedforward=int(cfg.get("dim_feedforward", 96)),
                dropout=float(cfg.get("dropout", 0.2)),
                batch_first=True,
                activation="gelu",
            )
            self.encoder = nn.TransformerEncoder(layer, num_layers=int(cfg.get("n_layers", 1)))
            self.norm = nn.LayerNorm(d_model)
            self.head = nn.Sequential(
                nn.Linear(d_model, d_model),
                nn.GELU(),
                nn.Dropout(float(cfg.get("dropout", 0.2))),
                nn.Linear(d_model, len(quantiles)),
            )

        def forward(self, x):
            h = self.encoder(self.proj(x))[:, -1, :]
            return self.head(self.norm(h))

    return TinyTemporalFusion()


def _feature_cols(panel: pd.DataFrame, schema: dict[str, list[str]]) -> list[str]:
    cols = []
    for key in ("static_reals", "time_varying_known_reals", "time_varying_observed_reals"):
        cols.extend(schema.get(key, []))
    extra_prefixes = ("spectral_emb_", "kline_emb_")
    for col in panel.columns:
        if col.startswith(extra_prefixes) or col in {"cluster_id", "cluster_ret_mean_1d", "cluster_ret_mean_5d", "cluster_amount_mean", "cluster_turnover_mean", "stock_ret_minus_cluster_1d", "stock_ret_minus_cluster_5d", "kline_pred_ret_1d", "kline_pred_range_1d", "kline_pred_vol_5d"}:
            cols.append(col)
    return sorted([c for c in set(cols) if c in panel.columns])


def train_tft_model(panel: pd.DataFrame, schema: dict[str, list[str]], cfg: dict[str, Any], split: dict[str, list[int]], model_dir: str | Path) -> None:
    torch, _, _ = require_torch()
    ensure_dir(Path(model_dir) / "x")
    model_dir = Path(model_dir)
    target_col = cfg.get("target_col", "excess_ret_fwd_5d")
    feature_cols = _feature_cols(panel, schema)
    train_range = tuple(split["train_time_idx"])
    valid_range = tuple(split["valid_time_idx"])
    scaler = StandardScaler()
    train_mask = panel["time_idx"].between(*train_range)
    panel = panel.copy()
    panel[feature_cols] = panel[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    scaler.fit(panel.loc[train_mask, feature_cols])
    panel[feature_cols] = scaler.transform(panel[feature_cols])

    enc_len = int(cfg.get("encoder_length", 30))
    train_idx = SequenceIndex(panel, feature_cols, [target_col], enc_len, train_range)
    valid_idx = SequenceIndex(panel, feature_cols, [target_col], enc_len, valid_range)
    train_ds = TorchSequenceDataset(train_idx)
    valid_ds = TorchSequenceDataset(valid_idx)
    train_loader = make_loader(train_ds, int(cfg.get("batch_size", 512)), True, int(cfg.get("num_workers", 0)))
    valid_loader = make_loader(valid_ds, int(cfg.get("batch_size", 512)), False, int(cfg.get("num_workers", 0)))
    device = torch.device(get_device_name(cfg.get("device", "auto")))
    model = build_model(len(feature_cols), cfg).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=float(cfg.get("learning_rate", 1e-3)), weight_decay=float(cfg.get("weight_decay", 1e-4)))
    quantiles = [float(q) for q in cfg.get("quantiles", [0.1, 0.5, 0.9])]
    best, bad = float("inf"), 0
    for epoch in range(1, int(cfg.get("max_epochs", 12)) + 1):
        model.train(); losses=[]
        for x,y,_ in train_loader:
            x=x.to(device); y=y[:,0].to(device)
            opt.zero_grad(); pred=model(x); loss=quantile_loss(pred,y,quantiles,torch); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), float(cfg.get("gradient_clip_val", 1.0)))
            opt.step(); losses.append(float(loss.detach().cpu()))
        model.eval(); vloss=[]
        with torch.no_grad():
            for x,y,_ in valid_loader:
                pred=model(x.to(device)); vloss.append(float(quantile_loss(pred,y[:,0].to(device),quantiles,torch).detach().cpu()))
        val=float(np.mean(vloss)) if vloss else float(np.mean(losses))
        logger.info("TFT epoch={} train_loss={:.6f} valid_loss={:.6f}", epoch, float(np.mean(losses)), val)
        if val < best:
            best=val; bad=0
            torch.save({"model": model.state_dict(), "cfg": cfg, "feature_cols": feature_cols, "target_col": target_col, "quantiles": quantiles}, model_dir / "model.ckpt")
            with open(model_dir / "numeric_scaler.pkl", "wb") as f: pickle.dump(scaler, f)
            with open(model_dir / "feature_schema.json", "w", encoding="utf-8") as f: json.dump(schema, f, ensure_ascii=False, indent=2)
        else:
            bad += 1
            if bad >= int(cfg.get("early_stop_patience", 4)):
                break


def predict_tft(panel: pd.DataFrame, split_range: tuple[int, int], model_dir: str | Path) -> pd.DataFrame:
    torch, _, _ = require_torch()
    model_dir = Path(model_dir)
    ckpt = torch.load(model_dir / "model.ckpt", map_location="cpu")
    with open(model_dir / "numeric_scaler.pkl", "rb") as f: scaler = pickle.load(f)
    cfg = ckpt["cfg"]; feature_cols = ckpt["feature_cols"]; quantiles = ckpt["quantiles"]
    tmp = panel.copy()
    tmp[feature_cols] = tmp[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    tmp[feature_cols] = scaler.transform(tmp[feature_cols])
    seq_idx = SequenceIndex(tmp.assign(__dummy_target=0.0), feature_cols, ["__dummy_target"], int(cfg.get("encoder_length", 30)), split_range)
    ds = TorchSequenceDataset(seq_idx)
    loader = make_loader(ds, int(cfg.get("batch_size", 512)), False, int(cfg.get("num_workers", 0)))
    device = torch.device(get_device_name(cfg.get("device", "auto")))
    model = build_model(len(feature_cols), cfg).to(device)
    model.load_state_dict(ckpt["model"]); model.eval()
    rows=[]
    with torch.no_grad():
        for x,_,end_idx in loader:
            pred = model(x.to(device)).detach().cpu().numpy()
            meta = ds.meta.iloc[end_idx.numpy()].reset_index(drop=True)
            block = meta.copy()
            for j,q in enumerate(quantiles):
                block[f"pred_q{int(q*100):02d}_excess_ret_fwd_5d"] = pred[:,j]
            rows.append(block)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
