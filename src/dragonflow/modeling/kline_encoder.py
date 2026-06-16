"""Kronos-inspired lightweight K-line encoder."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from dragonflow.modeling.config import get_device_name
from dragonflow.modeling.torch_datasets import SequenceIndex, TorchSequenceDataset, make_loader, require_torch
from dragonflow.utils.io import ensure_dir
from dragonflow.utils.logger import get_logger

logger = get_logger(__name__)

KLINE_FEATURES = ["k_body", "k_range", "k_upper_shadow", "k_lower_shadow", "k_close_pos", "k_gap", "k_volume_chg", "k_amount_chg"]
KLINE_TARGETS = ["ret_fwd_1d", "range_fwd_1d", "vol_fwd_5d"]


def add_kline_aux_targets(panel: pd.DataFrame) -> pd.DataFrame:
    out = panel.sort_values(["stock_code", "time_idx"]).copy()
    g = out.groupby("stock_code", sort=False)
    out["range_fwd_1d"] = g["k_range"].shift(-1)
    out["vol_fwd_5d"] = g["ret_1d"].transform(lambda s: s.shift(-1).rolling(5, min_periods=3).std().shift(-4))
    return out


def build_model(input_dim: int, output_dim: int, cfg: dict[str, Any]):
    torch, _, _ = require_torch()
    nn = torch.nn

    class KLineEncoder(nn.Module):
        def __init__(self):
            super().__init__()
            d_model = int(cfg.get("d_model", 24))
            self.proj = nn.Linear(input_dim, d_model)
            layer = nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=int(cfg.get("n_heads", 2)),
                dim_feedforward=int(cfg.get("dim_feedforward", 48)),
                dropout=float(cfg.get("dropout", 0.2)),
                batch_first=True,
                activation="gelu",
            )
            self.encoder = nn.TransformerEncoder(layer, num_layers=int(cfg.get("n_layers", 1)))
            self.emb = nn.Linear(d_model, int(cfg.get("output_dim", 4)))
            self.head = nn.Linear(int(cfg.get("output_dim", 4)), output_dim)

        def forward(self, x):
            h = self.encoder(self.proj(x))[:, -1, :]
            z = self.emb(h)
            y = self.head(z)
            return y, z

    return KLineEncoder()


def train_kline_encoder(panel: pd.DataFrame, cfg: dict[str, Any], model_dir: str | Path) -> pd.DataFrame:
    torch, _, _ = require_torch()
    device = torch.device(get_device_name(cfg.get("device", "auto")))
    panel = add_kline_aux_targets(panel)
    target_cols = KLINE_TARGETS
    feature_cols = [c for c in KLINE_FEATURES if c in panel.columns]
    panel[feature_cols + target_cols] = panel[feature_cols + target_cols].replace([np.inf, -np.inf], np.nan)
    panel[feature_cols] = panel[feature_cols].fillna(0.0)

    split_train = tuple(cfg["split"]["train_time_idx"]) if "split" in cfg else (40, 64)
    split_valid = tuple(cfg["split"]["valid_time_idx"]) if "split" in cfg else (65, 79)
    enc_len = int(cfg.get("input_length", 30))
    train_idx = SequenceIndex(panel, feature_cols, target_cols, enc_len, split_train)
    valid_idx = SequenceIndex(panel, feature_cols, target_cols, enc_len, split_valid)
    train_ds = TorchSequenceDataset(train_idx)
    valid_ds = TorchSequenceDataset(valid_idx)
    train_loader = make_loader(train_ds, int(cfg.get("batch_size", 512)), True, int(cfg.get("num_workers", 0)))
    valid_loader = make_loader(valid_ds, int(cfg.get("batch_size", 512)), False, int(cfg.get("num_workers", 0)))

    model = build_model(len(feature_cols), len(target_cols), cfg).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=float(cfg.get("learning_rate", 1e-3)), weight_decay=float(cfg.get("weight_decay", 1e-4)))
    loss_fn = torch.nn.SmoothL1Loss()
    best_loss, bad = float("inf"), 0
    ensure_dir(Path(model_dir) / "x")
    ckpt = Path(model_dir) / "kline_encoder.ckpt"
    for epoch in range(1, int(cfg.get("max_epochs", 8)) + 1):
        model.train(); losses=[]
        for x,y,_ in train_loader:
            x=x.to(device); y=y.to(device)
            opt.zero_grad(); pred,_=model(x); loss=loss_fn(pred,y); loss.backward(); opt.step(); losses.append(float(loss.detach().cpu()))
        model.eval(); vloss=[]
        with torch.no_grad():
            for x,y,_ in valid_loader:
                pred,_=model(x.to(device)); vloss.append(float(loss_fn(pred,y.to(device)).detach().cpu()))
        val=float(np.mean(vloss)) if vloss else float(np.mean(losses))
        logger.info("K线编码器 epoch={} train_loss={:.6f} valid_loss={:.6f}", epoch, float(np.mean(losses)), val)
        if val < best_loss:
            best_loss=val; bad=0; torch.save({"model": model.state_dict(), "feature_cols": feature_cols, "target_cols": target_cols, "cfg": cfg}, ckpt)
        else:
            bad += 1
            if bad >= int(cfg.get("early_stop_patience", 3)):
                break
    return infer_kline_embeddings(panel, cfg, model_dir)


def infer_kline_embeddings(panel: pd.DataFrame, cfg: dict[str, Any], model_dir: str | Path) -> pd.DataFrame:
    torch, _, _ = require_torch()
    device = torch.device(get_device_name(cfg.get("device", "auto")))
    ckpt = torch.load(Path(model_dir) / "kline_encoder.ckpt", map_location=device)
    feature_cols = ckpt["feature_cols"]
    target_cols = ckpt["target_cols"]
    model = build_model(len(feature_cols), len(target_cols), ckpt["cfg"]).to(device)
    model.load_state_dict(ckpt["model"]); model.eval()
    tmp = panel.copy().sort_values(["stock_code", "time_idx"])
    tmp[feature_cols] = tmp[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    seq_idx = SequenceIndex(tmp.assign(__dummy_target=0.0), feature_cols, ["__dummy_target"], int(cfg.get("input_length", 30)), (0, int(tmp["time_idx"].max())))
    ds = TorchSequenceDataset(seq_idx)
    loader = make_loader(ds, int(cfg.get("batch_size", 512)), False, int(cfg.get("num_workers", 0)))
    rows=[]
    with torch.no_grad():
        for x,_,end_idx in loader:
            pred,z = model(x.to(device))
            meta = ds.meta.iloc[end_idx.numpy()].reset_index(drop=True)
            block = meta.copy()
            for j in range(z.shape[1]):
                block[f"kline_emb_{j+1}"] = z[:,j].detach().cpu().numpy()
            for j,name in enumerate(["kline_pred_ret_1d","kline_pred_range_1d","kline_pred_vol_5d"]):
                block[name] = pred[:,j].detach().cpu().numpy()
            rows.append(block)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
