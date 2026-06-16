"""PyTorch datasets for sequence modeling."""
from __future__ import annotations

import numpy as np
import pandas as pd


def require_torch():
    try:
        import torch
        from torch.utils.data import Dataset, DataLoader
        return torch, Dataset, DataLoader
    except Exception as exc:
        raise RuntimeError("训练需要 PyTorch。请在服务器环境安装 torch 后再运行训练脚本。") from exc


class SequenceIndex:
    def __init__(self, panel: pd.DataFrame, feature_cols: list[str], target_cols: list[str], encoder_length: int, time_range: tuple[int, int]):
        self.panel = panel.sort_values(["stock_code", "time_idx"]).reset_index(drop=True)
        self.feature_cols = feature_cols
        self.target_cols = target_cols
        self.encoder_length = encoder_length
        lo, hi = time_range
        self.samples: list[tuple[int, int]] = []
        for _, idx in self.panel.groupby("stock_code", sort=False).indices.items():
            arr_idx = np.asarray(idx)
            times = self.panel.loc[arr_idx, "time_idx"].to_numpy()
            for pos in range(encoder_length - 1, len(arr_idx)):
                t = int(times[pos])
                if lo <= t <= hi:
                    y = self.panel.loc[arr_idx[pos], target_cols]
                    if not y.isna().any():
                        self.samples.append((int(arr_idx[pos - encoder_length + 1]), int(arr_idx[pos])))


class TorchSequenceDataset(require_torch()[1]):
    def __init__(self, seq_index: SequenceIndex):
        torch, _, _ = require_torch()
        self.torch = torch
        self.panel = seq_index.panel
        self.feature_cols = seq_index.feature_cols
        self.target_cols = seq_index.target_cols
        self.samples = seq_index.samples
        self.encoder_length = seq_index.encoder_length
        self.features = self.panel[self.feature_cols].to_numpy(dtype="float32")
        self.targets = self.panel[self.target_cols].to_numpy(dtype="float32")
        self.meta = self.panel[["date", "stock_code", "time_idx"]].reset_index(drop=True)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        start, end = self.samples[idx]
        x = self.features[start:end + 1]
        y = self.targets[end]
        return self.torch.from_numpy(x), self.torch.from_numpy(y), end


def make_loader(dataset, batch_size: int, shuffle: bool, num_workers: int = 0):
    _, _, DataLoader = require_torch()
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, num_workers=num_workers, pin_memory=False)
