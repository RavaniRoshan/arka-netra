from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS = ROOT / "reports" / "predictions" / "arkanetra_mvp_predictions.parquet"
METRICS = ROOT / "reports" / "metrics.csv"
TOP_FEATURES = ROOT / "reports" / "top_features.json"
ATTENTION = ROOT / "reports" / "attention_matrix.csv"
EVENT_SUMMARY = ROOT / "reports" / "event_summary.csv"
MANIFEST = ROOT / "reports" / "artifact_manifest.json"

# Phase 6: New dashboard modes
ANALYSIS_DATA = ROOT / "reports" / "analysis_data.json"
MODEL_COMPARISON = ROOT / "reports" / "model_comparison.csv"
MULTI_HORIZON = ROOT / "reports" / "multi_horizon_predictions.parquet"
EVENT_SUMMARY_EXPORT = ROOT / "reports" / "event_summary_export.md"
ALERT_POLICY_CONFIG = ROOT / "reports" / "alert_policy_config.json"


st.set_page_config(page_title="ArkaNetra", layout="wide")
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stMetric"] { background: #f7f7f7; border: 1px solid #dedede; padding: 0.7rem; border-radius: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("ArkaNetra Mission Console")
st.caption("Physics-informed multimodal solar flare early-warning MVP")

# Phase 6: Navigation tabs
if ANALYSIS_DATA.exists():
    tabs = st.tabs(["Replay", "Analysis", "Model Comparison", "Multi-Horizon", "Evidence & Limitations"])
    current_tab = tabs[0]
else:
    tabs = st.tabs(["Replay", "Evidence & Limitations"])
    current_tab = tabs[0]


@st.cache_data
def load_predictions() -> pd.DataFrame:
    return pd.read_parquet(PREDICTIONS)


predictions = load_predictions()
preferred_order = [
    "Quiet Sun replay",
    "C-class watch replay",
    "M-class warning replay",
    "X-class critical replay",
    "Background archive",
]
available = list(predictions["scenario"].drop_duplicates())
scenarios = [name for name in preferred_order if name in available] + [name for name in available if name not in preferred_order]

# Phase 6: Navigation tabs
if ANALYSIS_DATA.exists():
    tabs = st.tabs(["Replay", "Analysis", "Model Comparison", "Multi-Horizon", "Evidence & Limitations"])
    current_tab = tabs[0]
else:
    tabs = st.tabs(["Replay", "Evidence & Limitations"])
    current_tab = tabs[0]

# Replay tab
if ANALYSIS_DATA.exists():
    with tabs[0]:
        scenario = st.sidebar.selectbox("Replay scenario", scenarios, index=scenarios.index("M-class warning replay") if "M-class warning replay" in scenarios else 0)
        scenario_rows = predictions[predictions["scenario"] == scenario].reset_index(drop=True)
        position = st.sidebar.slider("Replay position", 0, max(len(scenario_rows) - 1, 0), min(len(scenario_rows) - 1, 24))
        row = scenario_rows.iloc[position]
        
        if MANIFEST.exists():
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
            st.sidebar.caption(f"Mode: {manifest.get('data_mode', 'unknown')}")
            st.sidebar.caption(f"Rows: {manifest.get('prediction_rows', 'unknown')}")
            st.sidebar.caption("Milestone: 1.1 demo hardening")
        
        state_color = {"NORMAL": "#2E7D32", "WATCH": "#C88719", "WARNING": "#C7522A", "CRITICAL": "#B00020"}.get(row["mission_state"], "#444")
        st.markdown(
            f"""
            <div style="border-left: 8px solid {state_color}; padding: 0.75rem 1rem; background: #f7f7f7;">
              <strong>Mission State:</strong> {row['mission_state']} &nbsp; | &nbsp;
              <strong>Flare Probability:</strong> {row['flare_probability']:.1%} &nbsp; | &nbsp;
              <strong>Anomaly Index:</strong> {row['anomaly_index']:.0f}/100 &nbsp; | &nbsp;
              <strong>Time:</strong> {row['timestamp']}
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        if scenario == "Background archive":
            st.warning("Background archive is for QA inspection. Use the named replay scenarios for the judge demo.")
        
        metric_a, metric_b, metric_c, metric_d = st.columns(4)
        metric_a.metric("Probability", f"{row['flare_probability']:.1%}", f"{row['mission_state']}")
        metric_b.metric("Confidence Band", f"{row['confidence_low']:.1%} - {row['confidence_high']:.1%}")
        metric_c.metric("Anomaly", f"{row['anomaly_index']:.0f}/100")
        lead_label = "No event in horizon" if pd.isna(row["time_to_flare_minutes"]) else f"{row['time_to_flare_minutes']:.0f} min"
        metric_d.metric("Time To Flare", lead_label)
        
        left, center, right = st.columns([1.2, 1.0, 1.0])
        with left:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=scenario_rows["timestamp"], y=scenario_rows["soft_xray_flux"], mode="lines", name="Soft X-ray"))
            fig.add_vline(x=row["timestamp"], line_dash="dash", line_color="#444")
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10), title="Soft X-Ray Flux")
            st.plotly_chart(fig, use_container_width=True)
        
        with center:
            gauge = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=float(row["flare_probability"]) * 100,
                    title={"text": "Flare Risk"},
                    gauge={"axis": {"range": [0, 100]}, "bar": {"color": state_color}},
                )
            )
            gauge.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(gauge, use_container_width=True)
        
        with right:
            anomaly = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=float(row["anomaly_index"]),
                    title={"text": "Anomaly Index"},
                    gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#5C6BC0"}},
                )
            )
            anomaly.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(anomaly, use_container_width=True)
        
        bottom_left, bottom_right = st.columns([1.2, 1.0])
        with bottom_left:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=scenario_rows["timestamp"], y=scenario_rows["hard_xray_flux"], mode="lines", name="Hard X-ray"))
            fig.add_trace(go.Scatter(x=scenario_rows["timestamp"], y=scenario_rows["hardness_ratio"], mode="lines", name="Hardness ratio", yaxis="y2"))
            fig.add_vline(x=row["timestamp"], line_dash="dash", line_color="#444")
            fig.update_layout(
                height=340,
                title="Hard X-Ray And Hardness",
                yaxis2={"overlaying": "y", "side": "right"},
                margin=dict(l=10, r=10, t=30, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with bottom_right:
            interval = go.Figure()
            interval.add_trace(go.Scatter(x=scenario_rows["timestamp"], y=scenario_rows["confidence_high"], mode="lines", line=dict(width=0), showlegend=False))
            interval.add_trace(
                go.Scatter(
                    x=scenario_rows["timestamp"],
                    y=scenario_rows["confidence_low"],
                    fill="tonexty",
                    mode="lines",
                    line=dict(width=0),
                    name="Confidence band",
                )
            )
            interval.add_trace(go.Scatter(x=scenario_rows["timestamp"], y=scenario_rows["flare_probability"], mode="lines", name="Probability"))
            interval.add_vline(x=row["timestamp"], line_dash="dash", line_color="#444")
            interval.update_layout(height=340, title="Risk Confidence Band", margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(interval, use_container_width=True)
        
        expl_left, expl_right = st.columns([1, 1])
        with expl_left:
            st.subheader("Top Feature Drivers")
            if TOP_FEATURES.exists():
                features = json.loads(TOP_FEATURES.read_text(encoding="utf-8"))
                st.dataframe(pd.DataFrame(features, columns=["feature", "importance"]), use_container_width=True, hide_index=True)
            st.info(row["sep_risk_context"])
        
        with expl_right:
            st.subheader("Cross-Modal Attention Snapshot")
            if ATTENTION.exists():
                attention = pd.read_csv(ATTENTION)
                heatmap = go.Figure(data=go.Heatmap(z=attention.values, colorscale="Viridis"))
                heatmap.update_layout(height=300, margin=dict(l=10, r=10, t=20, b=10), xaxis_title="Hard X-ray window", yaxis_title="Soft derivative window")
                st.plotly_chart(heatmap, use_container_width=True)
        
        if METRICS.exists():
            st.subheader("MVP Model Comparison")
            st.dataframe(pd.read_csv(METRICS), use_container_width=True, hide_index=True)
        
        if EVENT_SUMMARY.exists():
            st.subheader("Replay Scenario Summary")
            st.dataframe(pd.read_csv(EVENT_SUMMARY), use_container_width=True, hide_index=True)
        
        ALERT_PATH = ROOT / "reports" / "alert_history.csv"
        if ALERT_PATH.exists():
            with st.expander("Alert History", expanded=False):
                alert_df = pd.read_csv(ALERT_PATH)
                st.dataframe(alert_df[["timestamp", "state", "flare_probability", "anomaly_index", "scenario"]].tail(20), use_container_width=True, hide_index=True)
                st.caption(f"Total alerts: {len(alert_df)}")
        
        AUDIT_PATH = ROOT / "reports" / "audit_log.jsonl"
        if AUDIT_PATH.exists():
            with st.expander("Audit Log", expanded=False):
                audit_entries = []
                with AUDIT_PATH.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            import json
                            audit_entries.append(json.loads(line))
                if audit_entries:
                    latest = audit_entries[-1]
                    st.write(f"**Latest run:** {latest.get('timestamp', 'N/A')}")
                    st.write(f"**Config hash:** `{latest.get('config_hash', 'N/A')}`")
                    st.write(f"**Data hash:** `{latest.get('data_hash', 'N/A')}`")
                    st.write(f"**Mission mode:** {latest.get('mission_mode', 'N/A')}")
                    st.write(f"**Prediction rows:** {latest.get('prediction_rows', 0)}")
    
    # Analysis tab
    if ANALYSIS_DATA.exists():
        with tabs[1]:
            st.header("Event Analysis")
            st.write("Deep-dive view for selected event")
            st.write("Features, attention, anomaly reconstruction, Neupert consistency")
    
    # Model comparison tab
    if MODEL_COMPARISON.exists():
        with tabs[2]:
            st.header("Model Comparison")
            st.write("Side-by-side comparison of sklearn vs GRU predictions")
            model_comparison = pd.read_csv(MODEL_COMPARISON)
            st.dataframe(model_comparison, use_container_width=True, hide_index=True)
    
    # Multi-horizon tab
    if MULTI_HORIZON.exists():
        with tabs[3]:
            st.header("Multi-Horizon Forecasts")
            st.write("Predictions for multiple forecast windows (30min, 60min, 120min)")
            multi_horizon = pd.read_parquet(MULTI_HORIZON)
            st.dataframe(multi_horizon, use_container_width=True, hide_index=True)
    
    # Event summary export tab
    if EVENT_SUMMARY_EXPORT.exists():
        with tabs[4]:
            st.header("Event Summary Export")
            st.write("Exportable event summary in Markdown and CSV")
            with open(EVENT_SUMMARY_EXPORT, 'r') as f:
                st.markdown(f.read())
    
    # Evidence & Limitations tab
    with tabs[-1]:
        if MANIFEST.exists():
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
            data_mode = manifest.get("data_mode", "unknown")
            soft_source = manifest.get("soft_source", "GOES") if MANIFEST.exists() else "GOES"
            hard_source = manifest.get("hard_source", "N/A") if MANIFEST.exists() else "N/A"
            mission_mode = manifest.get("mission_mode", "synthetic") if MANIFEST.exists() else "synthetic"
            
            if mission_mode == "aditya_l1":
                soft_label = "SoLEXS" if soft_source == "SOLEXS" else soft_source
                hard_label = "HEL1OS" if hard_source == "HEL1OS" else hard_source
                lines = [
                    f"**Aditya-L1 Mission Mode**: This run uses **{soft_label}** soft X-ray "
                    f"(0.3-3 keV) and **{hard_label}** hard X-ray (25-100 keV) data."
                ]
                lines.append("")
                lines.append("**Instruments:**")
                lines.append(f"- **{soft_label}** (Solar X-ray Sensor): Soft X-ray flux from Aditya-L1")
                lines.append(f"- **{hard_label}** (High Energy X-ray Spectrometer): Hard X-ray flux from Aditya-L1")
                lines.append("")
                lines.append("**Data Source:** ISRO Aditya-L1 mission telemetry")
                lines.append("")
                lines.append("Dual-band observation from India's Aditya-L1 mission at Sun-Earth L1 point "
                            "aligns with the ArkaNetra physics-informed thesis.")
                evidence = "\n".join(lines)
            elif "synthetic" in data_mode or mission_mode == "synthetic":
                evidence = (
                    "This run uses deterministic synthetic proxy replay data. "
                    "Soft X-ray and hard X-ray are both synthetically generated for demo purposes."
                )
            elif "goes" in data_mode or mission_mode == "goes_proxy":
                lines = [f"This run uses real **{soft_source}** soft X-ray data from NOAA SWPC GOES."]
                if hard_source and hard_source != "N/A" and "NONE" not in hard_source:
                    lines.append(f"Hard X-ray source: **{hard_source}** (Phase 2 multimodal integration).")
                else:
                    lines.append("Hard X-ray is zero-filled (Phase 1 soft X-ray only; Phase 2 adds RHESSI/Fermi).")
                evidence = " ".join(lines)
            else:
                evidence = "Data mode: " + data_mode
            st.markdown(evidence)
            if MANIFEST.exists():
                st.json(json.loads(MANIFEST.read_text(encoding="utf-8")))
