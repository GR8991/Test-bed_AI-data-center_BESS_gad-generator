"""
BESS Virtual Simulation Tool
Tesla Megapack 2 XL + CAT Gas Generator + AI Data Centre + Grid

Sources:
  - Tesla Megapack 2 XL Design and Installation Manual Rev 2.9 (Nov 2025)
  - NVIDIA BESS Self-Qualification Guidelines v0.4 (Feb 2026)
  - IEEE 1547-2018

DISCLAIMER: This tool is a pre-feasibility education simulator only.
It uses RMS-level energy dispatch models — NOT EMT simulation (PSCAD/EMTP-RV).
Results are indicative only and cannot substitute for:
  - Hardware qualification tests
  - PSCAD/EMTP-RV EMT studies (mandatory for NVIDIA T5, T9, T12)
  - ETAP power system analysis
  - Professional engineering judgement
All NVIDIA BESS Qualification tests must be performed on certified hardware.
"""

import streamlit as st
import numpy as np
from models.sim_state import SimState

st.set_page_config(
    page_title="BESS Simulation — Tesla Megapack 2XL",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state initialisation ─────────────────────────────
if "state" not in st.session_state:
    st.session_state["state"] = SimState(
        dt_s=1.0,
        time_s=np.arange(0, 86400, 1),
        scr=5.0,
        grid_mva=100.0,
    )

# ── Sidebar navigation ────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/b/bd/Tesla_Motors.svg",
             width=120)
    st.title("BESS Simulation")
    st.caption("Tesla Megapack 2 XL\nNVIDIA BESS Qual v0.4")
    st.markdown("---")

    page = st.radio(
        "Navigate",
        [
            "🏠 Home",
            "🖥️ ENV 1 — AI Load",
            "🔋 ENV 2 — BESS (Megapack 2XL)",
            "⚙️ ENV 3 — CAT Generator",
            "⚡ ENV 4 — Grid",
            "📊 ENV 5 — Dashboard & NVIDIA Check",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Global timestep
    dt = st.selectbox("Simulation timestep", [1, 5, 10, 60], index=0,
                      format_func=lambda x: f"{x}s")
    if dt != st.session_state["state"].dt_s:
        st.session_state["state"].dt_s = float(dt)
        st.session_state["state"].time_s = np.arange(0, 86400, float(dt))

    st.markdown("---")
    if st.button("🔄 Reset All", help="Clear all simulation results"):
        st.session_state["state"] = SimState(
            dt_s=float(dt),
            time_s=np.arange(0, 86400, float(dt)),
            scr=5.0,
            grid_mva=100.0,
        )
        st.rerun()

    # Status indicators
    s = st.session_state["state"]
    st.markdown("**Simulation Status**")
    st.markdown(f"{'✅' if s.p_it_mw   is not None else '⬜'} ENV 1 — AI Load")
    st.markdown(f"{'✅' if s.p_bess_mw is not None else '⬜'} ENV 2 — BESS")
    st.markdown(f"{'✅' if s.p_gen_mw  is not None else '⬜'} ENV 3 — Generator")
    st.markdown(f"{'✅' if s.v_pu      is not None else '⬜'} ENV 4 — Grid")
    st.markdown(f"{'✅' if s.nvidia         else '⬜'} ENV 5 — NVIDIA Check")

# ── Disclaimer banner ─────────────────────────────────────────
st.warning(
    "⚠️ **Simulator Disclaimer**: RMS-level energy dispatch model only. "
    "NOT EMT simulation. Results are indicative — cannot substitute for PSCAD/ETAP studies "
    "or NVIDIA hardware qualification tests. "
    "Tesla Megapack 2 XL parameters from Design Manual Rev 2.9 (2025)."
)

def _render_home():
    st.title("🔋 BESS Virtual Simulation Tool")
    st.subheader("Tesla Megapack 2 XL + CAT Gas Generator + AI Data Centre + Grid")

    st.markdown("""
    This tool provides a **pre-feasibility virtual simulation** of a Battery Energy Storage
    System (BESS) integrated with an AI data centre, Caterpillar gas generators, and a utility
    grid connection.

    ---

    ### System Configuration
    | Component | Specification |
    |---|---|
    | **BESS Product** | Tesla Megapack 2 XL (Design Manual Rev 2.9, Nov 2025) |
    | **PCS Architecture** | 24 integrated inverter modules per unit (distributed — not central PCS) |
    | **GFM** | Option code VF01 required for islanding & microgrid |
    | **Archetype** | Grid-Connected Microgrid (AI DC + CAT + BESS + Grid) |
    | **Qualification Framework** | NVIDIA BESS Self-Qualification Guidelines v0.4 (Feb 2026) |

    ---

    ### 5 Environments — Run in Sequence

    | Environment | What It Simulates | Key NVIDIA Tests |
    |---|---|---|
    | **ENV 1 — AI Load** | GPU cluster load profile, ramp events, PUE | T4 ramp rate flag |
    | **ENV 2 — BESS** | Megapack 2 XL SOC, AI buffering, DR dispatch | T4, T6, T11 |
    | **ENV 3 — Generator** | CAT governor response, N-1 trip, black start | T9, T10 |
    | **ENV 4 — Grid** | SCR, LVRT/HVRT IEEE 1547-2018, resonance | T5, T7 |
    | **ENV 5 — Dashboard** | Combined view + all 12 NVIDIA tests + Export | All 12 |

    ---

    ### ⚠️ What This Tool Cannot Do
    - **EMT simulation** — Tests T5 and T9 require PSCAD/EMTP-RV at ≤50 µs timestep
    - **Control loop analysis** — T12 Nyquist/dq impedance requires MATLAB Control Toolbox
    - **Protection coordination** — Requires ETAP
    - **Formal NVIDIA submission** — Hardware test data required on certified equipment

    ---
    """)

    col1, col2, col3 = st.columns(3)
    col1.info("**Source 1**\nTesla Megapack 2 XL\nDesign & Installation Manual\nRev 2.9 — Nov 2025")
    col2.info("**Source 2**\nNVIDIA BESS\nSelf-Qualification Guidelines\nv0.4 — Feb 2026")
    col3.info("**Source 3**\nIEEE 1547-2018\nInterconnection Standard\nLVRT/HVRT curves")


# ── Page routing ──────────────────────────────────────────────
state = st.session_state["state"]

if page == "🏠 Home":
    _render_home()

elif page == "🖥️ ENV 1 — AI Load":
    from environments import env1_ai_load
    state = env1_ai_load.render(state)
    st.session_state["state"] = state

elif page == "🔋 ENV 2 — BESS (Megapack 2XL)":
    from environments import env2_bess
    state = env2_bess.render(state)
    st.session_state["state"] = state

elif page == "⚙️ ENV 3 — CAT Generator":
    from environments import env3_generator
    state = env3_generator.render(state)
    st.session_state["state"] = state

elif page == "⚡ ENV 4 — Grid":
    from environments import env4_grid
    state = env4_grid.render(state)
    st.session_state["state"] = state

elif page == "📊 ENV 5 — Dashboard & NVIDIA Check":
    from environments import env5_dashboard
    state = env5_dashboard.render(state)
    st.session_state["state"] = state

