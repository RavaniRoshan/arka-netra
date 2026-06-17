from __future__ import annotations


try:
    import torch
    from torch import nn
except ModuleNotFoundError:  # pragma: no cover - optional dependency boundary
    torch = None
    nn = None


class TorchNotInstalledError(RuntimeError):
    """Raised when the optional PyTorch model is requested without torch installed."""


def require_torch():
    if torch is None or nn is None:
        raise TorchNotInstalledError(
            "PyTorch is not installed in this runtime. Install torch to use DualBranchCrossAttentionGRU."
        )


if nn is not None:

    class DualBranchCrossAttentionGRU(nn.Module):
        """Planned production model: soft branch, hard branch, cross-attention fusion, forecast head."""

        def __init__(
            self,
            soft_dim: int,
            hard_dim: int,
            hidden_dim: int = 64,
            num_layers: int = 2,
            dropout: float = 0.25,
        ):
            super().__init__()
            self.soft_encoder = nn.GRU(soft_dim, hidden_dim, num_layers=num_layers, batch_first=True, dropout=dropout if num_layers > 1 else 0)
            self.hard_encoder = nn.GRU(hard_dim, hidden_dim, num_layers=num_layers, batch_first=True, dropout=dropout if num_layers > 1 else 0)
            self.attention = nn.MultiheadAttention(hidden_dim, num_heads=4, dropout=dropout, batch_first=True)
            self.dropout = nn.Dropout(dropout)
            self.forecast_head = nn.Sequential(
                nn.Linear(hidden_dim * 2, hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim, 1),
            )

        def forward(self, soft_sequence, hard_sequence):
            soft_encoded, _ = self.soft_encoder(soft_sequence)
            hard_encoded, _ = self.hard_encoder(hard_sequence)
            attended_soft, attention_weights = self.attention(soft_encoded, hard_encoded, hard_encoded)
            pooled_soft = attended_soft[:, -1, :]
            pooled_hard = hard_encoded[:, -1, :]
            logits = self.forecast_head(self.dropout(torch.cat([pooled_soft, pooled_hard], dim=-1)))
            return logits.squeeze(-1), attention_weights

    class GRUAutoencoder(nn.Module):
        """Autoencoder trained on quiet-Sun sequences. Reconstruction error is used as anomaly score."""

        def __init__(self, input_dim: int, hidden_dim: int = 32, num_layers: int = 2, dropout: float = 0.25):
            super().__init__()
            self.encoder = nn.GRU(input_dim, hidden_dim, num_layers=num_layers, batch_first=True, dropout=dropout if num_layers > 1 else 0)
            self.decoder = nn.GRU(hidden_dim, input_dim, num_layers=num_layers, batch_first=True, dropout=dropout if num_layers > 1 else 0)

        def forward(self, x):
            encoded, _ = self.encoder(x)
            decoded, _ = self.decoder(encoded)
            return decoded

        def reconstruction_error(self, x):
            recon = self.forward(x)
            return torch.mean((x - recon) ** 2, dim=-1)

    class DualBranchWithAutoencoder(nn.Module):
        """Combined model: DualBranchCrossAttentionGRU + GRUAutoencoder for joint prediction and anomaly."""

        def __init__(
            self,
            soft_dim: int,
            hard_dim: int,
            feature_dim: int,
            hidden_dim: int = 64,
            num_layers: int = 2,
            dropout: float = 0.25,
            ae_hidden_dim: int = 32,
        ):
            super().__init__()
            self.branch = DualBranchCrossAttentionGRU(soft_dim, hard_dim, hidden_dim, num_layers, dropout)
            self.autoencoder = GRUAutoencoder(feature_dim, ae_hidden_dim, num_layers, dropout)
            self.dropout = nn.Dropout(dropout)

        def forward(self, soft_sequence, hard_sequence, full_sequence):
            logits, attention = self.branch(soft_sequence, hard_sequence)
            ae_error = self.autoencoder.reconstruction_error(full_sequence)
            return logits, attention, ae_error

        def anomaly_score(self, full_sequence):
            self.eval()
            with torch.no_grad():
                errors = self.autoencoder.reconstruction_error(full_sequence)
            return errors


def neupert_loss(soft_derivative, hard_xray, mask=None):
    """Soft physics loss for d(SXR)/dt approximately matching HXR after normalization."""
    require_torch()
    soft_z = (soft_derivative - soft_derivative.mean(dim=-1, keepdim=True)) / (
        soft_derivative.std(dim=-1, keepdim=True, correction=0) + 1e-6
    )
    hard_z = (hard_xray - hard_xray.mean(dim=-1, keepdim=True)) / (hard_xray.std(dim=-1, keepdim=True, correction=0) + 1e-6)
    error = (soft_z - hard_z).pow(2)
    if mask is not None:
        error = error * mask
        return error.sum() / mask.sum().clamp_min(1)
    return error.mean()

