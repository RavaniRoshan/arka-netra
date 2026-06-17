from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("torch")

import torch
from arkanetra.config import ROOT, load_config
from arkanetra.torch_models import (
    DualBranchCrossAttentionGRU,
    GRUAutoencoder,
    DualBranchWithAutoencoder,
    neupert_loss,
)
from arkanetra.training import SequenceDataset, _get_soft_hard_cols, train_gru_model, _config_hash
from arkanetra.anomaly import compute_anomaly_index, _gru_ae_anomaly
from arkanetra.models import GRUModel, train_models
from arkanetra.pipeline import build_dataset


class TestNeupertLoss:
    def test_perfect_match_returns_zero(self):
        x = torch.tensor([[1.0, 2.0, 3.0, 4.0, 5.0]])
        loss = neupert_loss(x, x)
        assert loss.item() < 1e-6

    def test_scaled_match_returns_small(self):
        x = torch.tensor([[1.0, 2.0, 3.0, 4.0, 5.0]], dtype=torch.float32)
        y = torch.tensor([[2.0, 4.0, 6.0, 8.0, 10.0]], dtype=torch.float32)
        loss = neupert_loss(x, y)
        assert loss.item() < 1e-4

    def test_different_signals_return_positive_loss(self):
        x = torch.tensor([[1.0, 2.0, 3.0, 4.0, 5.0]])
        y = torch.tensor([[5.0, 4.0, 3.0, 2.0, 1.0]])
        loss = neupert_loss(x, y)
        assert loss.item() > 0.1

    def test_mask_does_not_crash(self):
        x = torch.tensor([[1.0, 2.0, 3.0, 4.0, 5.0]])
        y = torch.tensor([[1.0, 2.0, 99.0, 99.0, 5.0]])
        mask = torch.tensor([[1.0, 1.0, 0.0, 0.0, 1.0]])
        loss = neupert_loss(x, y, mask=mask)
        assert loss.item() > 0

    def test_batch_dim(self):
        x = torch.randn(4, 24)
        y = torch.randn(4, 24)
        loss = neupert_loss(x, y)
        assert loss.item() > 0

    def test_single_element_does_not_nan(self):
        x = torch.tensor([[42.0]])
        y = torch.tensor([[42.0]])
        loss = neupert_loss(x, y)
        assert not torch.isnan(loss)
        assert loss.item() < 1e-6


class TestGRUAutoencoder:
    def test_forward_shape(self):
        model = GRUAutoencoder(input_dim=5, hidden_dim=16, num_layers=1)
        batch = torch.randn(8, 24, 5)
        output = model(batch)
        assert output.shape == (8, 24, 5)

    def test_reconstruction_error_returns_per_sample(self):
        model = GRUAutoencoder(input_dim=3, hidden_dim=8, num_layers=1)
        batch = torch.randn(4, 10, 3)
        errors = model.reconstruction_error(batch)
        assert errors.shape == (4, 10)
        assert errors.min() >= 0

    def test_training_reduces_error(self):
        torch.manual_seed(42)
        model = GRUAutoencoder(input_dim=2, hidden_dim=32, num_layers=2)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        x = torch.randn(32, 6, 2)
        initial_err = model.reconstruction_error(x).mean().item()
        model.train()
        for _ in range(200):
            recon = model(x)
            loss = torch.nn.functional.mse_loss(recon, x)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        model.eval()
        with torch.no_grad():
            final_err = model.reconstruction_error(x).mean().item()
        assert final_err < initial_err * 0.5


class TestDualBranchCrossAttentionGRU:
    def test_forward_shape(self):
        model = DualBranchCrossAttentionGRU(soft_dim=5, hard_dim=3, hidden_dim=16, num_layers=1)
        soft = torch.randn(2, 24, 5)
        hard = torch.randn(2, 24, 3)
        logits, attention = model(soft, hard)
        assert logits.shape == (2,)
        assert attention.shape == (2, 24, 24)

    def test_output_is_logit(self):
        model = DualBranchCrossAttentionGRU(soft_dim=4, hard_dim=2, hidden_dim=8, num_layers=1)
        soft = torch.randn(1, 12, 4)
        hard = torch.randn(1, 12, 2)
        logits, _ = model(soft, hard)
        prob = torch.sigmoid(logits)
        assert 0.0 <= prob.item() <= 1.0


class TestDualBranchWithAutoencoder:
    def test_forward_shape(self):
        model = DualBranchWithAutoencoder(soft_dim=5, hard_dim=3, feature_dim=8, hidden_dim=16, num_layers=1)
        soft = torch.randn(2, 24, 5)
        hard = torch.randn(2, 24, 3)
        full = torch.randn(2, 24, 8)
        logits, attention, ae_error = model(soft, hard, full)
        assert logits.shape == (2,)
        assert attention.shape == (2, 24, 24)
        assert ae_error.shape == (2, 24)

    def test_anomaly_score(self):
        model = DualBranchWithAutoencoder(soft_dim=3, hard_dim=2, feature_dim=4, hidden_dim=8, num_layers=1)
        full = torch.randn(4, 10, 4)
        scores = model.anomaly_score(full)
        assert scores.shape == (4, 10)


class TestSequenceDataset:
    def test_len_matches_sliding_window(self):
        n = 100
        lookback = 10
        frame = pd.DataFrame(
            {
                "soft_xray_flux": np.random.randn(n),
                "soft_xray_derivative": np.random.randn(n),
                "rolling_mean": np.random.randn(n),
                "rolling_slope": np.random.randn(n),
                "rolling_volatility": np.random.randn(n),
                "hard_xray_flux": np.random.randn(n),
                "hardness_ratio": np.random.randn(n),
                "integrated_hard_xray_energy": np.random.randn(n),
                "hard_rolling_slope": np.random.randn(n),
                "flare_label": np.random.randint(0, 2, n),
            }
        )
        soft_cols = ["soft_xray_flux", "soft_xray_derivative", "rolling_mean", "rolling_slope", "rolling_volatility"]
        hard_cols = ["hard_xray_flux", "hardness_ratio", "integrated_hard_xray_energy", "hard_rolling_slope"]
        ds = SequenceDataset(frame, soft_cols, hard_cols, lookback=lookback)
        assert len(ds) == n - lookback

    def test_no_future_leakage(self):
        frame = pd.DataFrame({
            "soft_xray_flux": [float(i) for i in range(50)],
            "soft_xray_derivative": [float(i) for i in range(50)],
            "rolling_mean": [float(i) for i in range(50)],
            "rolling_slope": [float(i) for i in range(50)],
            "rolling_volatility": [float(i) for i in range(50)],
            "hard_xray_flux": [float(i) for i in range(50)],
            "hardness_ratio": [float(i) for i in range(50)],
            "integrated_hard_xray_energy": [float(i) for i in range(50)],
            "hard_rolling_slope": [float(i) for i in range(50)],
            "flare_label": [0] * 50,
        })
        soft_cols = ["soft_xray_flux", "soft_xray_derivative", "rolling_mean", "rolling_slope", "rolling_volatility"]
        hard_cols = ["hard_xray_flux", "hardness_ratio", "integrated_hard_xray_energy", "hard_rolling_slope"]
        lookback = 5
        ds = SequenceDataset(frame, soft_cols, hard_cols, lookback=lookback)
        for i in range(len(ds)):
            soft, hard, label, (s_deriv, h_flux) = ds[i]
            soft_np = soft.numpy()
            expected_idx = lookback + i
            for row in soft_np:
                for val in row:
                    assert val < expected_idx, f"Future value at index {i}: soft contains {val} >= {expected_idx}"

    def test_returns_correct_shapes(self):
        n = 30
        lookback = 5
        frame = pd.DataFrame(
            {
                "soft_xray_flux": np.random.randn(n),
                "soft_xray_derivative": np.random.randn(n),
                "rolling_mean": np.random.randn(n),
                "rolling_slope": np.random.randn(n),
                "rolling_volatility": np.random.randn(n),
                "hard_xray_flux": np.random.randn(n),
                "hardness_ratio": np.random.randn(n),
                "integrated_hard_xray_energy": np.random.randn(n),
                "hard_rolling_slope": np.random.randn(n),
                "flare_label": np.random.randint(0, 2, n),
            }
        )
        soft_cols = ["soft_xray_flux", "soft_xray_derivative", "rolling_mean", "rolling_slope", "rolling_volatility"]
        hard_cols = ["hard_xray_flux", "hardness_ratio", "integrated_hard_xray_energy", "hard_rolling_slope"]
        ds = SequenceDataset(frame, soft_cols, hard_cols, lookback=lookback)
        soft, hard, label, (s_deriv, h_flux) = ds[0]
        assert soft.shape == (lookback, len(soft_cols))
        assert hard.shape == (lookback, len(hard_cols))
        assert isinstance(label, torch.Tensor)
        assert s_deriv.shape == (lookback,)
        assert h_flux.shape == (lookback,)


class TestTrainGruModel:
    def _small_config(self):
        config = load_config()
        config["model"]["architecture"] = "gru"
        config["model"]["gru"] = {
            "hidden_dim": 16,
            "num_layers": 1,
            "dropout": 0.1,
            "lookback_steps": 8,
            "batch_size": 32,
            "learning_rate": 0.005,
            "epochs": 8,
            "patience": 4,
            "ae_hidden_dim": 8,
        }
        return config

    def test_trains_on_synthetic_data_and_returns_result(self):
        config = self._small_config()
        dataset, _ = build_dataset(config)
        train = dataset[dataset["split"] == "train"]
        valid = dataset[dataset["split"].isin(["validation", "test"])]
        result = train_gru_model(train, valid, config)
        assert isinstance(result, dict)
        assert "epochs_trained" in result
        assert "best_val_loss" in result
        assert result["best_val_loss"] > 0
        assert "best_val_f1" in result
        assert "history" in result
        assert len(result["history"]["train_loss"]) > 0

    def test_neupert_loss_integrated(self):
        config = self._small_config()
        config["model"]["neupert_lambda"] = 0.5
        dataset, _ = build_dataset(config)
        train = dataset[dataset["split"] == "train"]
        valid = dataset[dataset["split"].isin(["validation", "test"])]
        result = train_gru_model(train, valid, config)
        assert result["best_val_loss"] > 0


class TestGRUModelWrapper:
    def _small_config(self):
        config = load_config()
        config["model"]["architecture"] = "gru"
        config["model"]["gru"] = {
            "hidden_dim": 16,
            "num_layers": 1,
            "dropout": 0.1,
            "lookback_steps": 8,
            "batch_size": 32,
            "learning_rate": 0.005,
            "epochs": 6,
            "patience": 4,
            "ae_hidden_dim": 8,
        }
        return config

    def test_fit_and_predict_proba(self):
        config = self._small_config()
        dataset, _ = build_dataset(config)
        train = dataset[dataset["split"] == "train"]
        valid = dataset[dataset["split"].isin(["validation", "test"])]
        gru_cfg = config["model"]["gru"]
        soft_cols, hard_cols = _get_soft_hard_cols(config)
        model = GRUModel(
            soft_cols=soft_cols, hard_cols=hard_cols,
            lookback=gru_cfg["lookback_steps"],
            hidden_dim=gru_cfg["hidden_dim"],
            num_layers=gru_cfg["num_layers"],
            dropout=gru_cfg["dropout"],
        )
        model.fit(train, valid, config)
        probs = model.predict_proba(valid)
        assert len(probs) == len(valid)
        assert probs.min() >= 0.0
        assert probs.max() <= 1.0

    def test_attention_matrix(self):
        config = self._small_config()
        dataset, _ = build_dataset(config)
        train = dataset[dataset["split"] == "train"]
        valid = dataset[dataset["split"].isin(["validation", "test"])]
        gru_cfg = config["model"]["gru"]
        soft_cols, hard_cols = _get_soft_hard_cols(config)
        model = GRUModel(
            soft_cols=soft_cols, hard_cols=hard_cols,
            lookback=gru_cfg["lookback_steps"],
            hidden_dim=gru_cfg["hidden_dim"],
            num_layers=gru_cfg["num_layers"],
            dropout=gru_cfg["dropout"],
        )
        model.fit(train, valid, config)
        attn = model.attention_matrix(valid, rows=6)
        assert attn.shape[0] > 0


class TestGRUAutoencoderAnomaly:
    def _small_config(self):
        config = load_config()
        config["model"]["architecture"] = "gru"
        config["model"]["gru"] = {
            "hidden_dim": 16,
            "num_layers": 1,
            "dropout": 0.1,
            "lookback_steps": 8,
            "batch_size": 32,
            "learning_rate": 0.005,
            "epochs": 6,
            "patience": 4,
            "ae_hidden_dim": 8,
            "ae_train_epochs": 5,
        }
        return config

    def test_compute_anomaly_index_gru_path(self):
        config = self._small_config()
        dataset, _ = build_dataset(config)
        result = compute_anomaly_index(dataset, config)
        assert isinstance(result, pd.Series)
        assert len(result) == len(dataset)
        assert result.min() >= 0
        assert result.max() <= 100

    def test_gru_ae_returns_within_range(self):
        dataset, _ = build_dataset(load_config())
        result = _gru_ae_anomaly(dataset, lookback=8, hidden_dim=8, num_layers=1, train_epochs=5)
        assert result.min() >= 0
        assert result.max() <= 100


class TestTrainModelsGRU:
    def test_train_models_gru_path_returns_metrics(self):
        config = load_config()
        config["model"]["architecture"] = "gru"
        config["model"]["gru"] = {
            "hidden_dim": 16,
            "num_layers": 1,
            "dropout": 0.1,
            "lookback_steps": 8,
            "batch_size": 32,
            "learning_rate": 0.005,
            "epochs": 6,
            "patience": 4,
            "ae_hidden_dim": 8,
        }
        dataset, _ = build_dataset(config)
        bundle = train_models(dataset, config)
        assert {"model", "precision", "recall", "f1"}.issubset(bundle.metrics.columns)
        assert len(bundle.metrics) == 3
        assert bundle.metrics["model"].iloc[2] == "dual_branch_cross_attention_gru"


class TestRegistryIntegration:
    def test_registry_accepts_gru_checkpoint(self, tmp_path):
        from arkanetra.registry.model_registry import get_registry
        registry = get_registry()
        config = load_config()
        config["model"]["architecture"] = "gru"
        config["model"]["gru"] = {
            "hidden_dim": 16,
            "num_layers": 1,
            "dropout": 0.1,
            "lookback_steps": 8,
            "batch_size": 32,
            "learning_rate": 0.005,
            "epochs": 4,
            "patience": 4,
            "ae_hidden_dim": 8,
        }
        dataset, _ = build_dataset(config)
        train = dataset[dataset["split"] == "train"]
        valid = dataset[dataset["split"].isin(["validation", "test"])]
        result = train_gru_model(train, valid, config, output_dir=tmp_path)
        assert result is not None
        version = f"gru_{_config_hash(config)}"
        entry = registry.get(version)
        assert entry is not None
        assert entry["architecture"] == "dual_branch_cross_attention_gru"


class TestConfigHash:
    def test_hash_is_deterministic(self):
        config = load_config()
        h1 = _config_hash(config)
        h2 = _config_hash(config)
        assert h1 == h2


class TestMakePredictionsGRU:
    def test_make_predictions_gru_path(self):
        from arkanetra.pipeline import make_predictions
        config = load_config()
        config["model"]["architecture"] = "gru"
        config["model"]["gru"] = {
            "hidden_dim": 16,
            "num_layers": 1,
            "dropout": 0.1,
            "lookback_steps": 8,
            "batch_size": 32,
            "learning_rate": 0.005,
            "epochs": 6,
            "patience": 4,
            "ae_hidden_dim": 8,
        }
        dataset, events = build_dataset(config)
        predictions, bundle = make_predictions(dataset, config, events)
        assert "flare_probability" in predictions.columns
        assert "anomaly_index" in predictions.columns
        assert "uncertainty_variance" in predictions.columns
        assert len(predictions) == len(dataset)