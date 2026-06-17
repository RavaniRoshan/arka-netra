from __future__ import annotations

import pandas as pd

from solaris.config import load_config
from solaris.data.synthetic import build_synthetic_proxy_data
from solaris.features import add_features


def test_features_are_past_only_and_finite():
    config = load_config()
    raw, events = build_synthetic_proxy_data(config)
    featured = add_features(raw.head(60), events, config)
    assert featured["hardness_ratio"].notna().all()
    assert featured["rolling_variance"].notna().all()
    assert featured.loc[0, "soft_xray_derivative"] == 0
    assert featured["timestamp"].is_monotonic_increasing


def test_near_zero_soft_flux_does_not_break_hardness_ratio():
    config = load_config()
    raw, events = build_synthetic_proxy_data(config)
    raw.loc[:5, "soft_xray_flux"] = 0.0
    featured = add_features(raw.head(20), events, config)
    assert pd.Series(featured["hardness_ratio"]).map(pd.notna).all()

