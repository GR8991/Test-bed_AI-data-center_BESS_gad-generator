import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.constants import NVIDIA_REQ, LVRT_SEGMENTS, HVRT_SEGMENTS

COLORS = {
    "load":  "#1565C0",
    "bess":  "#76B900",
    "gen":   "#E65100",
    "grid":  "#4527A0",
    "soc":   "#0C6E5A",
    "freq":  "#C62828",
    "limit": "#C62828",
    "amber": "#E65100",
    "bg":    "#0E1117",
    "grid_c":"#1e2130",
}

def _base(title=""):
    return dict(
        plot_bgcolor=COLORS["bg"],
        paper_bgcolor=COLORS["bg"],
        font=dict(color="#CCCCCC", family="Arial"),
        title=dict(text=title, font=dict(size=14, color="#76B900")),
        margin=dict(l=50, r=20, t=50, b=40),
        xaxis=dict(gridcolor=COLORS["grid_c"], zeroline=False),
        yaxis=dict(gridcolor=COLORS["grid_c"], zeroline=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#333"),
    )

def plot_load_profile(state) -> go.Figure:
    t_h = state.time_s / 3600
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t_h, y=state.p_site_mw, name="Total Site (inc. cooling)",
        fill="tozeroy", fillcolor="rgba(21,101,192,0.15)",
        line=dict(color=COLORS["load"], width=2)
    ))
    fig.add_trace(go.Scatter(
        x=t_h, y=state.p_it_mw, name="IT Load only",
        line=dict(color="#76B900", width=2, dash="dash")
    ))
    fig.update_layout(**_base("24-Hour Site Load Profile"),
                      xaxis_title="Hour of Day", yaxis_title="Power (MW)")
    return fig

def plot_ramp_rate(state) -> go.Figure:
    t_h = state.time_s / 3600
    dp = np.abs(np.diff(state.p_it_mw, prepend=state.p_it_mw[0])) / state.dt_s
    ramp_pct = dp / max(state.peak_it_mw, 0.001) * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t_h, y=ramp_pct, name="Ramp Rate (% IT/s)",
        line=dict(color=COLORS["load"], width=1.5)
    ))
    fig.add_hline(y=NVIDIA_REQ["max_ramp_pct_s"],
                  line=dict(color=COLORS["limit"], dash="dash", width=2),
                  annotation_text="NVIDIA T4 limit 20%/s",
                  annotation_font_color=COLORS["limit"])
    fig.update_layout(**_base("Load Ramp Rate vs NVIDIA T4 Limit"),
                      xaxis_title="Hour of Day", yaxis_title="Ramp Rate (% IT load/s)")
    return fig

def plot_bess_overview(state) -> go.Figure:
    t_h = state.time_s / 3600
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        subplot_titles=("BESS Power vs IT Load",
                                        "SOC % over 24h",
                                        "Grid-Side Power"))
    fig.add_trace(go.Scatter(x=t_h, y=state.p_it_mw, name="IT Load",
                             line=dict(color=COLORS["load"], width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=t_h, y=state.p_bess_mw, name="BESS Output",
                             line=dict(color=COLORS["bess"], width=2)), row=1, col=1)

    fig.add_trace(go.Scatter(x=t_h, y=state.soc_pct, name="SOC %",
                             fill="tozeroy", fillcolor="rgba(118,185,0,0.1)",
                             line=dict(color=COLORS["soc"], width=2)), row=2, col=1)
    fig.add_hline(y=NVIDIA_REQ["soc_min_pct"], row=2, col=1,
                  line=dict(color=COLORS["limit"], dash="dot"))
    fig.add_hline(y=NVIDIA_REQ["soc_max_pct"], row=2, col=1,
                  line=dict(color=COLORS["amber"], dash="dot"))

    fig.add_trace(go.Scatter(x=t_h, y=state.p_grid_mw, name="Grid Power",
                             line=dict(color=COLORS["grid"], width=1.5)), row=3, col=1)

    fig.update_layout(height=550, plot_bgcolor=COLORS["bg"],
                      paper_bgcolor=COLORS["bg"],
                      font=dict(color="#CCCCCC", family="Arial"),
                      margin=dict(l=60, r=20, t=60, b=40))
    return fig

def plot_soc(state) -> go.Figure:
    t_h = state.time_s / 3600
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t_h, y=state.soc_pct, name="SOC %",
        fill="tozeroy", fillcolor="rgba(118,185,0,0.12)",
        line=dict(color=COLORS["soc"], width=2.5)
    ))
    fig.add_hline(y=NVIDIA_REQ["soc_min_pct"],
                  line=dict(color=COLORS["limit"], dash="dot", width=1.5),
                  annotation_text="Min 20% (NVIDIA)")
    fig.add_hline(y=NVIDIA_REQ["soc_max_pct"],
                  line=dict(color=COLORS["amber"], dash="dot", width=1.5),
                  annotation_text="Max 80% (NVIDIA)")
    fig.update_layout(**_base("State of Charge — 24 Hours"),
                      xaxis_title="Hour of Day", yaxis_title="SOC (%)",
                      yaxis_range=[0, 100])
    return fig

def plot_power_split(state) -> go.Figure:
    if state.p_gen_mw is None:
        return go.Figure()
    t_h = state.time_s / 3600
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t_h, y=state.p_it_mw, name="IT Load",
                             line=dict(color=COLORS["load"], width=2)))
    fig.add_trace(go.Scatter(x=t_h, y=state.p_bess_mw or [0]*len(t_h),
                             name="BESS (fast)", line=dict(color=COLORS["bess"], width=2)))
    fig.add_trace(go.Scatter(x=t_h, y=state.p_gen_mw, name="Generator (slow)",
                             line=dict(color=COLORS["gen"], width=2)))
    fig.update_layout(**_base("Power Split: BESS (fast) vs Generator (slow)"),
                      xaxis_title="Hour of Day", yaxis_title="Power (MW)")
    return fig

def plot_frequency(state) -> go.Figure:
    if state.freq_hz is None:
        return go.Figure()
    t_h = state.time_s / 3600
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t_h, y=state.freq_hz, name="Frequency",
                             line=dict(color=COLORS["freq"], width=1.5)))
    fig.add_hline(y=50.0, line=dict(color="#AAAAAA", dash="dash"))
    fig.add_hline(y=47.0, line=dict(color=COLORS["limit"], dash="dot"),
                  annotation_text="Under-freq trip")
    fig.add_hline(y=52.0, line=dict(color=COLORS["amber"], dash="dot"),
                  annotation_text="Over-freq trip")
    fig.update_layout(**_base("System Frequency (Hz)"),
                      xaxis_title="Hour of Day", yaxis_title="Frequency (Hz)",
                      yaxis_range=[46, 54])
    return fig

def plot_voltage(state) -> go.Figure:
    if state.v_pu is None:
        return go.Figure()
    t_h = state.time_s / 3600
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t_h, y=state.v_pu, name="Voltage (pu)",
                             line=dict(color="#76B900", width=2)))
    fig.add_hline(y=0.88, line=dict(color=COLORS["limit"], dash="dot"),
                  annotation_text="LVRT threshold 0.88 pu")
    fig.add_hline(y=1.10, line=dict(color=COLORS["amber"], dash="dot"),
                  annotation_text="HVRT threshold 1.10 pu")
    fig.update_layout(**_base("PCC Voltage (per unit)"),
                      xaxis_title="Hour of Day", yaxis_title="Voltage (pu)",
                      yaxis_range=[0, 1.35])
    return fig

def plot_lvrt_envelope() -> go.Figure:
    """Plot IEEE 1547-2018 LVRT envelope from Tesla Manual Table 56."""
    fig = go.Figure()
    v_pts = [1.00, 0.88, 0.65, 0.45, 0.30, 0.00]
    t_pts = [9999,  20.0,  0.32, 0.16, 0.16, 0.16]
    t_plot = [min(t, 30) for t in t_pts]
    fig.add_trace(go.Scatter(
        x=t_plot, y=v_pts, name="LVRT Envelope (IEEE 1547-2018)",
        fill="tozeroy", fillcolor="rgba(118,185,0,0.10)",
        line=dict(color="#76B900", width=2)
    ))
    fig.update_layout(**_base("IEEE 1547-2018 LVRT Capability (Tesla Manual Table 56)"),
                      xaxis_title="Ride-Through Duration (s)",
                      yaxis_title="Voltage (pu)",
                      yaxis_range=[0, 1.2])
    return fig

def plot_combined_dashboard(state) -> go.Figure:
    t_h = state.time_s / 3600 if state.time_s is not None else []
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "IT Load vs BESS vs Generator",
            "SOC % (NVIDIA: 20–80%)",
            "Grid-Side Power",
            "System Frequency",
        )
    )
    # Row1 Col1
    if state.p_it_mw is not None:
        fig.add_trace(go.Scatter(x=t_h, y=state.p_it_mw, name="IT Load",
                                 line=dict(color=COLORS["load"])), row=1, col=1)
    if state.p_bess_mw is not None:
        fig.add_trace(go.Scatter(x=t_h, y=state.p_bess_mw, name="BESS",
                                 line=dict(color=COLORS["bess"])), row=1, col=1)
    if state.p_gen_mw is not None:
        fig.add_trace(go.Scatter(x=t_h, y=state.p_gen_mw, name="Generator",
                                 line=dict(color=COLORS["gen"])), row=1, col=1)
    # Row1 Col2
    if state.soc_pct is not None:
        fig.add_trace(go.Scatter(x=t_h, y=state.soc_pct, name="SOC",
                                 line=dict(color=COLORS["soc"])), row=1, col=2)
    # Row2 Col1
    if state.p_grid_mw is not None:
        fig.add_trace(go.Scatter(x=t_h, y=state.p_grid_mw, name="Grid Power",
                                 line=dict(color=COLORS["grid"])), row=2, col=1)
    # Row2 Col2
    if state.freq_hz is not None:
        fig.add_trace(go.Scatter(x=t_h, y=state.freq_hz, name="Freq",
                                 line=dict(color=COLORS["freq"])), row=2, col=2)

    fig.update_layout(height=500, showlegend=True,
                      plot_bgcolor=COLORS["bg"], paper_bgcolor=COLORS["bg"],
                      font=dict(color="#CCCCCC", family="Arial"),
                      margin=dict(l=50, r=20, t=60, b=40))
    return fig
