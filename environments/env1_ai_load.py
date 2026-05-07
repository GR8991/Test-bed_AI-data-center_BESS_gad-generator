import streamlit as st
import pandas as pd
from models.ai_load_model import build_ai_load
from utils.plots import plot_load_profile, plot_ramp_rate
from utils.constants import NVIDIA_REQ, MP2XL

def render(state):
    st.header("🖥️ ENV 1 — AI Data Centre Load")
    st.caption(
        "Models GPU cluster load behaviour over 24 hours. "
        "Outputs the IT load profile consumed by ENV 2 (BESS)."
    )

    # ── Presets ──────────────────────────────────────────────
    col_p1, col_p2, col_p3 = st.columns(3)
    preset = None
    if col_p1.button("🔹 Small (100× H100)"):  preset = "small"
    if col_p2.button("🔷 Medium (1000× H100)"): preset = "medium"
    if col_p3.button("🔶 Large (10k× H100)"):  preset = "large"

    presets = {
        "small":  dict(num_gpus=100,   tdp=0.7, util=80, clusters=2,  ramp=0.5,  jobs=10, pue=1.35),
        "medium": dict(num_gpus=1000,  tdp=0.7, util=80, clusters=4,  ramp=2.0,  jobs=30, pue=1.35),
        "large":  dict(num_gpus=10000, tdp=0.7, util=80, clusters=8,  ramp=10.0, jobs=80, pue=1.40),
    }
    p = presets.get(preset, {})

    st.markdown("---")
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("GPU Cluster Configuration")
        num_gpus  = st.number_input("Total GPU count",       100, 200000, p.get("num_gpus", 1000), 100)
        tdp_kw    = st.number_input("TDP per GPU (kW)",      0.1, 5.0,    p.get("tdp", 0.7),       0.1)
        util_pct  = st.slider("GPU utilisation at peak (%)", 40, 100,     p.get("util", 80))
        num_cls   = st.number_input("Number of clusters",    1, 20,       p.get("clusters", 4),     1)

    with c2:
        st.subheader("Load Dynamics")
        ramp_mw_s = st.number_input("Cluster ramp rate (MW/s)", 0.1, 50.0, p.get("ramp", 2.0), 0.1,
                                    help="How fast each cluster ramps to full load")
        jobs_day  = st.number_input("Training jobs per day",    1, 200,    p.get("jobs", 30),    1)
        pue       = st.slider("PUE (Power Usage Effectiveness)", 1.1, 2.0, p.get("pue", 1.35),  0.05,
                              help="Total site power = IT load × PUE")

    # ── Resonance check — Tesla Manual Section 2.9.1 ─────────
    peak_mw_est = num_gpus * tdp_kw * (util_pct / 100) / 1000
    # Using default 2h Megapack as reference
    default_kva = MP2XL["config_2h_kva"]
    resonance_ratio = peak_mw_est * 1000 / max(default_kva, 1)
    if resonance_ratio > MP2XL["resonance_threshold_pct"]:
        st.warning(
            f"⚠️ **Resonance Risk — Tesla Manual Section 2.9.1**: "
            f"Estimated IT load ({peak_mw_est:.1f} MW) exceeds 20% of Megapack apparent power. "
            f"Resonance is expected when GPU PSU switching frequency <35 kHz. "
            f"Mitigate with line reactor or isolation transformer."
        )

    if st.button("▶ Run ENV 1 Simulation", type="primary"):
        with st.spinner("Building 24-hour load profile..."):
            new_state = build_ai_load(
                num_gpus=int(num_gpus),
                tdp_kw=float(tdp_kw),
                util_pct=float(util_pct),
                num_clusters=int(num_cls),
                ramp_rate_mw_s=float(ramp_mw_s),
                jobs_per_day=int(jobs_day),
                pue=float(pue),
                dt_s=state.dt_s,
            )
            # Carry forward grid data from previous runs
            new_state.scr     = state.scr
            new_state.grid_mva = state.grid_mva
            st.session_state["state"] = new_state
            state = new_state

        st.success("✅ ENV 1 complete — load profile ready for ENV 2")

    # ── Results ───────────────────────────────────────────────
    if state.p_it_mw is not None:
        st.markdown("---")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Peak IT Load",  f"{state.peak_it_mw:.2f} MW")
        m2.metric("Average Load",  f"{state.avg_it_mw:.2f} MW")
        m3.metric("Daily Energy",  f"{state.daily_mwh:.0f} MWh")
        m4.metric("Load Factor",   f"{state.avg_it_mw/max(state.peak_it_mw,0.001)*100:.0f}%")
        m5.metric("Ramp Events",   str(len(state.ramp_events)))

        # T4 NVIDIA flag
        if state.max_ramp_pct_s > NVIDIA_REQ["max_ramp_pct_s"]:
            st.error(
                f"🔴 **NVIDIA T4 RISK**: Max ramp rate {state.max_ramp_pct_s:.1f}% IT/s "
                f"exceeds 20%/s limit. BESS must absorb the excess. "
                f"Configure BESS in ENV 2."
            )
        else:
            st.success(
                f"🟢 Ramp rate {state.max_ramp_pct_s:.1f}% IT/s — within NVIDIA T4 ≤20%/s"
            )

        st.plotly_chart(plot_load_profile(state), use_container_width=True)
        st.plotly_chart(plot_ramp_rate(state), use_container_width=True)

        if state.ramp_events:
            st.subheader("Ramp Events (training job starts)")
            df = pd.DataFrame(state.ramp_events)
            df["ramp_pct_s"] = df["ramp_pct_s"].round(1)
            df["delta_mw"]   = df["delta_mw"].round(3)
            st.dataframe(df[["t_hhmm", "cluster", "delta_mw",
                              "ramp_mw_s", "ramp_pct_s"]]
                         .rename(columns={
                             "t_hhmm": "Time", "cluster": "Cluster",
                             "delta_mw": "ΔMW", "ramp_mw_s": "Rate (MW/s)",
                             "ramp_pct_s": "Rate (% IT/s)"}),
                         use_container_width=True)

    return state
