from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from solaris.features import FEATURE_COLUMNS

try:
    import torch
except ImportError:
    torch = None


def _pca_anomaly(frame: pd.DataFrame) -> pd.Series:
    quiet = frame[(frame["split"] == "train") & (frame["flare_label"] == 0)]
    if len(quiet) < 20:
        quiet = frame[frame["flare_label"] == 0]
    n_components = min(5, len(FEATURE_COLUMNS), max(1, len(quiet) - 1))
    scaler = StandardScaler()
    quiet_scaled = scaler.fit_transform(quiet[FEATURE_COLUMNS])
    pca = PCA(n_components=n_components, random_state=42)
    pca.fit(quiet_scaled)
    scaled = scaler.transform(frame[FEATURE_COLUMNS])
    transformed = pca.transform(scaled)
    reconstructed = pca.inverse_transform(transformed)
    error = np.mean((scaled - reconstructed) ** 2, axis=1)
    low, high = np.quantile(error, [0.05, 0.98])
    index = 100 * (error - low) / max(high - low, 1e-12)
    return pd.Series(np.clip(index, 0, 100), index=frame.index, name="anomaly_index")


def _gru_ae_anomaly(
    frame: pd.DataFrame,
    model_state: dict | None = None,
    lookback: int = 24,
    hidden_dim: int = 32,
    num_layers: int = 2,
    dropout: float = 0.25,
    quiet_only: bool = True,
    train_epochs: int = 20,
    train_lr: float = 0.001,
) -> pd.Series:
    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset
        from solaris.torch_models import GRUAutoencoder
    except Exception:
        return _pca_anomaly(frame)

    device = torch.device("cpu")
    input_dim = len(FEATURE_COLUMNS)
    ae_model = GRUAutoencoder(input_dim, hidden_dim=hidden_dim, num_layers=num_layers, dropout=dropout)

    if model_state is not None:
        ae_model.load_state_dict(model_state)
    else:
        quiet = frame[(frame["split"] == "train") & (frame["flare_label"] == 0)]
        if len(quiet) < lookback + 5:
            quiet = frame[frame["flare_label"] == 0]
        quiet_values = quiet[FEATURE_COLUMNS].to_numpy()
        n_quiet = len(quiet_values)
        if n_quiet > lookback:
            q_sequences = []
            for i in range(lookback, n_quiet):
                q_sequences.append(quiet_values[i - lookback : i])
            q_tensor = torch.tensor(np.array(q_sequences), dtype=torch.float32)
            q_dataset = TensorDataset(q_tensor)
            q_loader = DataLoader(q_dataset, batch_size=64, shuffle=True)
            ae_model.train()
            ae_model.to(device)
            optimizer = torch.optim.Adam(ae_model.parameters(), lr=train_lr)
            for _ in range(train_epochs):
                for (batch,) in q_loader:
                    batch = batch.to(device)
                    recon = ae_model(batch)
                    loss = nn.functional.mse_loss(recon, batch)
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
            ae_model.eval()

    ae_model.to(device)
    ae_model.eval()

    values = frame.reset_index(drop=True)
    sequences = []
    valid_indices = []
    for i in range(lookback, len(values)):
        window = values.iloc[i - lookback : i][FEATURE_COLUMNS].to_numpy()
        sequences.append(window)
        valid_indices.append(i)

    if not sequences:
        return pd.Series(np.zeros(len(frame)), index=frame.index, name="anomaly_index")

    batch = torch.tensor(np.array(sequences), dtype=torch.float32).to(device)
    with torch.no_grad():
        errors = ae_model.reconstruction_error(batch).cpu().numpy()
    per_sample_error = errors.mean(axis=1)

    result = np.zeros(len(frame))
    result[valid_indices] = per_sample_error
    low, high = np.quantile(per_sample_error, [0.05, 0.98]) if len(per_sample_error) > 0 else (0, 1)
    index = 100 * (result - low) / max(high - low, 1e-12)
    return pd.Series(np.clip(index, 0, 100), index=frame.index, name="anomaly_index")


def compute_anomaly_index(
    dataset: pd.DataFrame,
    config: dict | None = None,
    model_state: dict | None = None,
) -> pd.Series:
    """Compute anomaly index using PCA (sklearn fallback) or GRU autoencoder (PyTorch)."""
    architecture = None
    if config is not None:
        architecture = config.get("model", {}).get("architecture", "sklearn")

    if architecture == "gru":
        gru_cfg = config.get("model", {}).get("gru", {})
        return _gru_ae_anomaly(
            dataset,
            model_state=model_state,
            lookback=int(gru_cfg.get("lookback_steps", 24)),
            hidden_dim=int(gru_cfg.get("ae_hidden_dim", 32)),
            num_layers=int(gru_cfg.get("num_layers", 2)),
            dropout=float(gru_cfg.get("dropout", 0.25)),
            train_epochs=int(gru_cfg.get("ae_train_epochs", 20)),
            train_lr=float(gru_cfg.get("learning_rate", 0.001)),
        )

    return _pca_anomaly(dataset)
