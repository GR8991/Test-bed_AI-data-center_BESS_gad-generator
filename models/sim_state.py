from dataclasses import dataclass, field
from typing import Optional
import numpy as np

@dataclass
class SimState:
    dt_s: float = 1.0
    time_s: Optional[np.ndarray] = None

    # ENV 1 — AI load
    p_it_mw:     Optional[np.ndarray] = None
    p_site_mw:   Optional[np.ndarray] = None
    peak_it_mw:  float = 0.0
    avg_it_mw:   float = 0.0
    daily_mwh:   float = 0.0
    ramp_events: list  = field(default_factory=list)
    max_ramp_pct_s: float = 0.0

    # ENV 2 — BESS
    p_bess_mw:   Optional[np.ndarray] = None
    q_bess_mvar: Optional[np.ndarray] = None
    soc_pct:     Optional[np.ndarray] = None
    p_grid_mw:   Optional[np.ndarray] = None
    bess_mw_rated:  float = 0.0
    bess_mwh_rated: float = 0.0
    num_megapacks:  int   = 1
    tracking_err_pct: float = 0.0
    soc_drift_pct:    float = 0.0
    dr_fast_resp_s:   float = 999.0
    dr_slow_resp_s:   float = 999.0

    # ENV 3 — Generator
    p_gen_mw:   Optional[np.ndarray] = None
    freq_hz:    Optional[np.ndarray] = None
    gen_mw_rated: float = 0.0
    num_gens:     int   = 1

    # ENV 4 — Grid
    v_pu:       Optional[np.ndarray] = None
    scr:        float = 5.0
    grid_mva:   float = 100.0
    lvrt_active: bool = False
    hvrt_active: bool = False

    # NVIDIA results
    nvidia: dict = field(default_factory=dict)
