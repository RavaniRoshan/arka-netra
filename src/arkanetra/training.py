from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from arkanetra.features import FEATURE_COLUMNS

try:
    from arkanetra.torch_models import DualBranchCrossAttentionGRU, neupert_loss
except Exception:
    DualBranchCrossAttentionGRU = None
    neupert_loss = None


class SequenceDataset(Dataset):
    def __init__(
        self,
        frame: pd.DataFrame,
        soft_cols: list[str],
        hard_cols: list[str],
        lookback: int = 24,
        target_col: str = "flare_label",
    ):
        self.soft_cols = soft_cols
        self.hard_cols = hard_cols
        self.lookback = lookback
        self.target_col = target_col
        self.indices = []
        self._build_indices(frame)

    def _build_indices(self, frame: pd.DataFrame):
        self.values = frame
        n = len(self._values)
        for i in range(self.lookback, n):
            self.indices.append(i)

    def __len__(self) -> int:
        return len(self.indices)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        soft = self.values[self.indices[idx] - self.lookback : self.indices[idx]][self.soft_cols].to_numpy()
        hard = self.values[self.indices[idx] - self.lookback : self.indices[idx]][self.hard_cols].to_numpy()
        label = float(self.values.iloc[self.indices[idx]][self.target_col])
        soft_deriv = self.values.iloc[self.indices[idx] - self.lookback : self.indices[idx]][
            "soft_xray_derivative"
        ].to_numpy()
        hard_flux = self.values.iloc[self.indices[idx] - self.lookback : self.indices[idx]]["hard_xray_flux"].to_numpy()
        return (
            torch.as_tensor(soft, dtype=torch.float32),
            torch.as_tensor(hard, dtype=torch.float32),
            torch.as_tensor(label, dtype=torch.float32),
            (torch.as_tensor(soft_deriv, dtype=torch.float32), torch.as_tensor(hard_flux, dtype=torch.float32)),
        )

    @property
    def values(self) -> pd.DataFrame:
        return self._values

    @values.setter
    def values(self, frame: pd.DataFrame):
        self._values = frame.reset_index(drop=True)

    @property
    def indices(self) -> list[int]:
        return self._indices

    @indices.setter
    def indices(self, indices: list[int]):
        self._indices = indices


def _get_soft_hard_cols(config: dict) -> tuple[list[str], list[str]]:
    soft_cols = ["soft_xray_flux", "soft_xray_derivative", "rolling_mean", "rolling_slope", "rolling_volatility"]
    hard_cols = ["hard_xray_flux", "hardness_ratio", "integrated_hard_xray_energy", "hard_rolling_slope"]
    return soft_cols, hard_cols


def train_gru_model(
    train_frame: pd.DataFrame,
    valid_frame: pd.DataFrame,
    config: dict,
    output_dir: Path | None = None,
) -> dict:
    require_torch()
    model_cfg = config.get("model", {})
    gru_cfg = model_cfg.get("gru", {})
    hidden_dim = int(gru_cfg.get("hidden_dim", 64))
    num_layers = int(gru_cfg.get("num_layers", 2))
    dropout = float(gru_cfg.get("dropout", 0.25))
    lookback = int(gru_cfg.get("lookback_steps", 24))
    batch_size = int(gru_cfg.get("batch_size", 64))
    lr = float(gru_cfg.get("learning_rate", 0.001))
    epochs = int(gru_cfg.get("epochs", 50))
    neupert_lambda = float(model_cfg.get("neupert_lambda", 0.18))
    seed = int(model_cfg.get("random_seed", 42))

    torch.manual_seed(seed)
    np.random.seed(seed)

    soft_cols, hard_cols = _get_soft_hard_cols(config)

    train_ds = SequenceDataset(train_frame, soft_cols, hard_cols, lookback=lookback)
    train_ds.values = train_frame
    valid_ds = SequenceDataset(valid_frame, soft_cols, hard_cols, lookback=lookback)
    valid_ds.values = valid_frame

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=True)
    valid_loader = DataLoader(valid_ds, batch_size=batch_size, shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    soft_dim = len(soft_cols)
    hard_dim = len(hard_cols)
    model = DualBranchCrossAttentionGRU(soft_dim, hard_dim, hidden_dim=hidden_dim, num_layers=num_layers, dropout=dropout)
    model.to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=5)

    neupert_fn = neupert_loss

    best_val_loss = float("inf")
    best_state: dict | None = None
    best_epoch = 0
    patience = int(gru_cfg.get("patience", 8))
    patience_counter = 0
    history: dict[str, list[float]] = {"train_loss": [], "val_loss": [], "val_f1": []}

    threshold = float(config.get("model", {}).get("warning_threshold", 0.55))

    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for batch_soft, batch_hard, batch_labels, (soft_deriv, hard_flux) in train_loader:
            batch_soft = batch_soft.to(device)
            batch_hard = batch_hard.to(device)
            batch_labels = batch_labels.to(device)
            soft_deriv = soft_deriv.to(device)
            hard_flux = hard_flux.to(device)

            logits, _ = model(batch_soft, batch_hard)
            bce_loss = nn.functional.binary_cross_entropy_with_logits(logits, batch_labels)
            np_loss = neupert_fn(soft_deriv, hard_flux)
            loss = bce_loss + neupert_lambda * np_loss

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item()

        train_loss /= max(len(train_loader), 1)

        model.eval()
        val_loss = 0.0
        all_preds: list[float] = []
        all_labels: list[float] = []
        with torch.no_grad():
            for batch_soft, batch_hard, batch_labels, (soft_deriv, hard_flux) in valid_loader:
                batch_soft = batch_soft.to(device)
                batch_hard = batch_hard.to(device)
                batch_labels = batch_labels.to(device)
                soft_deriv = soft_deriv.to(device)
                hard_flux = hard_flux.to(device)

                logits, _ = model(batch_soft, batch_hard)
                bce_loss = nn.functional.binary_cross_entropy_with_logits(logits, batch_labels)
                np_loss = neupert_fn(soft_deriv, hard_flux)
                loss = bce_loss + neupert_lambda * np_loss
                val_loss += loss.item()

                probs = torch.sigmoid(logits).cpu().numpy()
                all_preds.extend(probs.tolist())
                all_labels.extend(batch_labels.cpu().numpy().tolist())

        val_loss /= max(len(valid_loader), 1)
        all_preds = np.array(all_preds)
        all_labels = np.array(all_labels)
        val_f1 = _f1_at_threshold(all_labels, all_preds, threshold)

        scheduler.step(val_loss)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_f1"].append(val_f1)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            best_epoch = epoch
            patience_counter = 0
        else:
            patience_counter += 1

        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"Epoch {epoch+1}/{epochs} - train_loss: {train_loss:.4f} val_loss: {val_loss:.4f} val_f1: {val_f1:.4f}")

        if patience_counter >= patience and epoch >= 10:
            print(f"Early stopping at epoch {epoch+1}, best epoch {best_epoch+1}, best val_loss: {best_val_loss:.4f}")
            break

    if best_state is not None:
        model.load_state_dict(best_state)

    result = {
        "epochs_trained": epoch + 1,
        "best_epoch": best_epoch,
        "best_val_loss": best_val_loss,
        "final_val_f1": history["val_f1"][-1],
        "best_val_f1": max(history["val_f1"]),
        "history": history,
        "model_state": best_state,
        "config_hash": _config_hash(config),
    }

    if output_dir is not None:
        ckpt_path = save_checkpoint(model, optimizer, result, config, output_dir)
        try:
            from arkanetra.registry.model_registry import get_registry
            registry = get_registry()
            data_mode = config.get("data", {}).get("mode", "synthetic")
            registry.register(
                model_version=f"gru_{result['config_hash']}",
                checkpoint_path=ckpt_path,
                metrics={"best_val_loss": float(best_val_loss), "best_val_f1": float(max(history["val_f1"]))},
                config_snapshot=config,
                data_source=data_mode,
                architecture="dual_branch_cross_attention_gru",
                notes=f"Trained for {result['epochs_trained']} epochs, best at epoch {best_epoch+1}, early stopping patience={patience}",
            )
        except Exception:
            pass

    return result


def _f1_at_threshold(y_true: np.ndarray, y_score: np.ndarray, threshold: float) -> float:
    from sklearn.metrics import f1_score
    if len(np.unique(y_true)) < 2:
        return 0.0
    return float(f1_score(y_true, (y_score >= threshold).astype(int), zero_division=0))


def save_checkpoint(model: nn.Module, optimizer, train_result: dict, config: dict, output_dir: Path) -> Path:
    output_dir = Path(output_dir)
    checkpoint = {
        "model_state": train_result["model_state"],
        "config_hash": train_result["config_hash"],
        "epochs_trained": train_result["epochs_trained"],
        "best_val_loss": train_result["best_val_loss"],
        "final_val_f1": train_result["final_val_f1"],
        "best_val_f1": train_result["best_val_f1"],
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    ckpt_path = output_dir / "model_checkpoint.pt"
    torch.save(checkpoint, ckpt_path)
    return ckpt_path


def load_checkpoint(checkpoint_path: Path) -> dict:
    return torch.load(checkpoint_path, map_location="cpu", weights_only=False)


def _config_hash(config: dict) -> str:
    config_str = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(config_str.encode()).hexdigest()[:16]


def require_torch():
    try:
        import torch
        from arkanetra.torch_models import nn as torch_nn
        if torch is None or torch_nn is None:
            raise ImportError("PyTorch not available")
    except ImportError:
        raise RuntimeError("PyTorch is not installed. Install torch to use GRU models.")