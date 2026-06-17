from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from arkanetra.features import FEATURE_COLUMNS


try:
    import torch
    from arkanetra.torch_models import DualBranchCrossAttentionGRU
except Exception:
    torch = None
    DualBranchCrossAttentionGRU = None


@dataclass
class ModelBundle:
    baseline: object
    final_model: object
    feature_columns: list[str]
    metrics: pd.DataFrame


def _safe_auc(metric, y_true, y_score) -> float:
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(metric(y_true, y_score))


def _expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    bin_edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        mask = (y_prob >= lo) & (y_prob < hi)
        if mask.sum() == 0:
            continue
        bin_acc = y_true[mask].mean()
        bin_conf = y_prob[mask].mean()
        ece += mask.sum() / len(y_true) * abs(bin_acc - bin_conf)
    return float(ece)


def metric_row(name: str, y_true: np.ndarray, y_score: np.ndarray, threshold: float) -> dict:
    y_pred = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "model": name,
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "pr_auc": _safe_auc(average_precision_score, y_true, y_score),
        "roc_auc": _safe_auc(roc_auc_score, y_true, y_score),
        "brier_score": float(brier_score_loss(y_true, y_score)),
        "ece": _expected_calibration_error(y_true, y_score),
        "false_alarm_rate": float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0,
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
    }


class ArkaNetraFusionModel:
    """Executable MVP approximation of the planned dual-branch cross-attention model."""

    def __init__(self, random_seed: int = 42, neupert_lambda: float = 0.18):
        self.random_seed = random_seed
        self.neupert_lambda = neupert_lambda
        self.classifier = make_pipeline(
            StandardScaler(),
            LogisticRegression(class_weight="balanced", max_iter=1000, random_state=random_seed),
        )
        self.feature_importance_: dict[str, float] = {}

    def _augment(self, frame: pd.DataFrame) -> pd.DataFrame:
        soft_signal = frame[["soft_xray_flux", "soft_xray_derivative", "rolling_slope", "rolling_volatility"]].copy()
        hard_signal = frame[["hard_xray_flux", "hardness_ratio", "integrated_hard_xray_energy", "hard_rolling_slope"]].copy()
        augmented = frame[FEATURE_COLUMNS].copy()
        augmented["cross_attention_score"] = (
            soft_signal.rank(pct=True).mean(axis=1) * hard_signal.rank(pct=True).mean(axis=1)
        )
        augmented["neupert_consistency"] = 1.0 / (
            1.0 + np.abs(_z(frame["soft_xray_derivative"]) - _z(frame["hard_xray_flux"]))
        )
        augmented["physics_weighted_risk"] = (
            augmented["cross_attention_score"] * (1 + self.neupert_lambda * augmented["neupert_consistency"])
        )
        return augmented

    def fit(self, frame: pd.DataFrame) -> "ArkaNetraFusionModel":
        x = self._augment(frame)
        y = frame["flare_label"].to_numpy()
        self.classifier.fit(x, y)
        final = self.classifier.named_steps["logisticregression"]
        self.feature_importance_ = dict(zip(x.columns, np.abs(final.coef_[0]), strict=False))
        return self

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        return self.classifier.predict_proba(self._augment(frame))[:, 1]

    def attention_matrix(self, frame: pd.DataFrame, rows: int = 24) -> pd.DataFrame:
        tail = frame.tail(rows)
        soft = _z(tail["soft_xray_derivative"].to_numpy())
        hard = _z(tail["hard_xray_flux"].to_numpy())
        logits = np.outer(soft, hard)
        attention = np.exp(logits - np.nanmax(logits))
        attention = attention / max(attention.sum(), 1e-12)
        return pd.DataFrame(attention)


class GRUModel:
    """PyTorch DualBranchCrossAttentionGRU wrapped to match sklearn predict_proba interface."""

    def __init__(
        self,
        soft_cols: list[str],
        hard_cols: list[str],
        lookback: int = 24,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.25,
        device: str = "cpu",
    ):
        self.soft_cols = soft_cols
        self.hard_cols = hard_cols
        self.lookback = lookback
        self.device = device
        self.model: DualBranchCrossAttentionGRU | None = None
        self._hidden_dim = hidden_dim
        self._num_layers = num_layers
        self._dropout = dropout
        self.attention_matrix_: pd.DataFrame | None = None

    def fit(self, train_frame: pd.DataFrame, valid_frame: pd.DataFrame, config: dict) -> "GRUModel":
        from arkanetra.training import train_gru_model
        result = train_gru_model(train_frame, valid_frame, config)
        soft_dim = len(self.soft_cols)
        hard_dim = len(self.hard_cols)
        self.model = DualBranchCrossAttentionGRU(
            soft_dim, hard_dim, hidden_dim=self._hidden_dim, num_layers=self._num_layers, dropout=self._dropout
        )
        if result["model_state"] is not None:
            self.model.load_state_dict(result["model_state"])
        self.model.to(self.device)
        self.model.eval()
        return self

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            return np.zeros(len(frame))
        values = frame.reset_index(drop=True)
        lookback = self.lookback
        soft_cols = self.soft_cols
        hard_cols = self.hard_cols
        device = self.device
        sequences_s: list[np.ndarray] = []
        sequences_h: list[np.ndarray] = []
        valid_indices: list[int] = []
        for i in range(lookback, len(values)):
            s = values.iloc[i - lookback : i][soft_cols].to_numpy()
            h = values.iloc[i - lookback : i][hard_cols].to_numpy()
            sequences_s.append(s)
            sequences_h.append(h)
            valid_indices.append(i)
        result = np.zeros(len(frame))
        if sequences_s:
            batch_s = torch.as_tensor(np.array(sequences_s), dtype=torch.float32).to(device)
            batch_h = torch.as_tensor(np.array(sequences_h), dtype=torch.float32).to(device)
            with torch.no_grad():
                logits, attention = self.model(batch_s, batch_h)
                probs = torch.sigmoid(logits).cpu().numpy()
            result[valid_indices] = probs
        return result

    def attention_matrix(self, frame: pd.DataFrame, rows: int = 24) -> pd.DataFrame:
        if self.model is None:
            return pd.DataFrame()
        lookback = self.lookback
        values = frame.reset_index(drop=True)
        soft_cols = self.soft_cols
        hard_cols = self.hard_cols
        device = self.device
        sequences_s: list[np.ndarray] = []
        sequences_h: list[np.ndarray] = []
        for i in range(lookback, min(lookback + rows, len(values))):
            sequences_s.append(values.iloc[i - lookback : i][soft_cols].to_numpy())
            sequences_h.append(values.iloc[i - lookback : i][hard_cols].to_numpy())
        if not sequences_s:
            return pd.DataFrame()
        batch_s = torch.as_tensor(np.array(sequences_s), dtype=torch.float32).to(device)
        batch_h = torch.as_tensor(np.array(sequences_h), dtype=torch.float32).to(device)
        with torch.no_grad():
            _, attention = self.model(batch_s, batch_h)
        att = attention.cpu().numpy()
        return pd.DataFrame(att[:, :, 0])


def _z(values) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    std = float(arr.std())
    if std < 1e-12:
        return np.zeros_like(arr)
    return (arr - float(arr.mean())) / std


def train_models(dataset: pd.DataFrame, config: dict) -> ModelBundle:
    threshold = float(config["model"]["warning_threshold"])
    train = dataset[dataset["split"] == "train"]
    valid = dataset[dataset["split"].isin(["validation", "test"])]
    architecture = config.get("model", {}).get("architecture", "sklearn")

    x_train = train[FEATURE_COLUMNS]
    y_train = train["flare_label"].to_numpy()
    x_valid = valid[FEATURE_COLUMNS]
    y_valid = valid["flare_label"].to_numpy()

    baseline = RandomForestClassifier(n_estimators=160, max_depth=5, class_weight="balanced", random_state=42)
    baseline.fit(x_train, y_train)
    baseline_scores = baseline.predict_proba(x_valid)[:, 1]

    soft_only = make_pipeline(
        StandardScaler(),
        LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42),
    )
    soft_cols_list = ["soft_xray_flux", "soft_xray_derivative", "rolling_mean", "rolling_slope", "rolling_volatility"]
    soft_only.fit(train[soft_cols_list], y_train)
    soft_scores = soft_only.predict_proba(valid[soft_cols_list])[:, 1]

    if architecture == "gru" and torch is not None:
        gru_cfg = config.get("model", {}).get("gru", {})
        hidden_dim = int(gru_cfg.get("hidden_dim", 64))
        num_layers = int(gru_cfg.get("num_layers", 2))
        dropout = float(gru_cfg.get("dropout", 0.25))
        lookback = int(gru_cfg.get("lookback_steps", 24))
        device = "cuda" if torch.cuda.is_available() else "cpu"

        final_model = GRUModel(
            soft_cols=soft_cols_list,
            hard_cols=["hard_xray_flux", "hardness_ratio", "integrated_hard_xray_energy", "hard_rolling_slope"],
            lookback=lookback,
            hidden_dim=hidden_dim,
            num_layers=num_layers,
            dropout=dropout,
            device=device,
        ).fit(train, valid, config)
        final_scores = final_model.predict_proba(valid)
        model_name = "dual_branch_cross_attention_gru"
    else:
        final_model = ArkaNetraFusionModel(
            random_seed=int(config["model"]["random_seed"]),
            neupert_lambda=float(config["model"]["neupert_lambda"]),
        ).fit(train)
        final_scores = final_model.predict_proba(valid)
        model_name = "dual_branch_cross_attention_surrogate"

    metrics = pd.DataFrame(
        [
            metric_row("random_forest_baseline", y_valid, baseline_scores, threshold),
            metric_row("soft_only_logistic", y_valid, soft_scores, threshold),
            metric_row(model_name, y_valid, final_scores, threshold),
        ]
    )
    return ModelBundle(baseline=baseline, final_model=final_model, feature_columns=FEATURE_COLUMNS, metrics=metrics)


def monte_carlo_uncertainty(probabilities: np.ndarray, passes: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    draws = []
    logits = np.log(np.clip(probabilities, 1e-6, 1 - 1e-6) / np.clip(1 - probabilities, 1e-6, 1))
    for _ in range(passes):
        perturbed = logits + rng.normal(0, 0.18 + 0.22 * probabilities, size=len(probabilities))
        draws.append(1 / (1 + np.exp(-perturbed)))
    sample = np.vstack(draws)
    return sample.mean(axis=0), sample.var(axis=0), np.quantile(sample, 0.1, axis=0), np.quantile(sample, 0.9, axis=0)

