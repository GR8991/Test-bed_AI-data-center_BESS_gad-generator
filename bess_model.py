import numpy as np
from models.sim_state import SimState
from utils.constants import MP2XL, NVIDIA_REQ

def run_bess(
    state: SimState,
    num_units: int,
    config: str,
    cell_option: str,
    num_modules: int,
    gfm_enabled: bool,
    priority: str,
    soc_start_pct: float,
    dr_fast_mw: float,
    dr_slow_mw: float,
    dr_fast_t_s: float,
    dr_slow_t_s: float,
    temp_c: float,
) -> SimState:
    if state.p_it_mw is None:
        return state

    # Rated capacity — Tesla Manual Table 4
    if config == "2h":
        kw_unit  = MP2XL["config_2h_kw"]
        kwh_unit = MP2XL["config_2h_kwh"]
    else:
        if cell_option == "C012":
            kw_unit  = MP2XL["config_4h_kw_c012"]
            kwh_unit = MP2XL["config_4h_kwh_c012"]
        else:
            kw_unit  = MP2XL["config_4h_kw"]
            kwh_unit = MP2XL["config_4h_kwh"]

    mod_frac = num_modules / MP2XL["max_modules"]
    kw_unit  *= mod_frac
    kwh_unit *= mod_frac

    mw_rated  = kw_unit  * num_units / 1000.0
    mwh_rated = kwh_unit * num_units / 1000.0

    # Temperature derating — LFP ~0.5%/°C above 25°C
    temp_derate = max(0.80, 1.0 - max(0.0, temp_c - 25) * 0.005)
    dod_window  = (NVIDIA_REQ["soc_max_pct"] - NVIDIA_REQ["soc_min_pct"]) / 100.0
    mwh_usable  = mwh_rated * temp_derate * dod_window

    state.bess_mw_rated  = mw_rated
    state.bess_mwh_rated = mwh_rated
    state.num_megapacks  = num_units

    N   = len(state.p_it_mw)
    dt  = state.dt_s
    p_it = state.p_it_mw

    p_bess = np.zeros(N)
    q_bess = np.zeros(N)
    soc    = np.zeros(N)
    p_grid = np.zeros(N)

    soc_e = mwh_usable * (soc_start_pct / 100.0)
    soc_min_e = mwh_usable * (NVIDIA_REQ["soc_min_pct"] / 100.0)
    soc_max_e = mwh_usable

    dp_it = np.diff(p_it, prepend=p_it[0])
    peak_mw = state.peak_it_mw if state.peak_it_mw > 0 else 1.0

    # Track overload timer
    overload_timer = 0

    for i in range(N):
        t = i * dt

        # --- AI buffering ramp absorption ---
        raw_ramp_mw_s = dp_it[i] / dt
        raw_ramp_pct  = abs(raw_ramp_mw_s) / max(peak_mw, 0.001) * 100
        if raw_ramp_pct > NVIDIA_REQ["max_ramp_pct_s"]:
            excess = (raw_ramp_mw_s - np.sign(raw_ramp_mw_s)
                      * NVIDIA_REQ["max_ramp_pct_s"] / 100 * peak_mw)
            needed_mw = excess * dt
        else:
            needed_mw = 0.0

        # --- DR events ---
        dr_mw = 0.0
        if abs(t - dr_fast_t_s) < dt * 2:
            dr_mw = dr_fast_mw
        elif abs(t - dr_slow_t_s) < dt * 2:
            dr_mw = dr_slow_mw

        # --- Recharge when SOC low and load slack ---
        recharge_mw = 0.0
        soc_frac = soc_e / max(mwh_usable, 1e-9)
        if soc_frac < 0.30 and p_it[i] < peak_mw * 0.50:
            recharge_mw = -min(mw_rated * 0.25,
                               (0.80 - soc_frac) * mwh_usable / (3600 / dt))

        p_cmd = needed_mw + dr_mw + recharge_mw

        # --- Current / overload limit ---
        p_max = mw_rated * MP2XL["overload_pct"] if overload_timer > 0 else mw_rated
        overload_timer = max(0, overload_timer - dt)
        if abs(p_cmd) > mw_rated:
            overload_timer = MP2XL["overload_duration_s"]
        p_cmd = np.clip(p_cmd, -p_max, p_max)

        # --- P/Q priority (current limit model) ---
        p_pu = abs(p_cmd) / max(mw_rated, 1e-9)
        p_pu = min(p_pu, 1.0)
        if priority == "P-priority":
            q_pu = np.sqrt(max(1.0 - p_pu**2, 0))
        elif priority == "Q-priority":
            q_pu = 0.40
            p_pu = min(p_pu, np.sqrt(max(1.0 - q_pu**2, 0)))
        else:
            q_pu = np.sqrt(max(1.0 - p_pu**2, 0)) * 0.5

        p_del = np.sign(p_cmd) * p_pu * mw_rated
        q_del = q_pu * mw_rated * 0.3

        # Tesla power regulation accuracy <2% — Table 45
        noise = np.random.normal(0, 0.007) * mw_rated
        p_del = np.clip(p_del + noise, -mw_rated * 1.2, mw_rated * 1.2)

        # --- SOC ---
        delta_e = p_del * dt / 3600.0
        soc_e = np.clip(soc_e - delta_e, soc_min_e, soc_max_e)

        p_bess[i] = p_del
        q_bess[i] = q_del
        soc[i]    = (soc_e / max(mwh_usable, 1e-9)) * 100.0
        p_grid[i] = p_it[i] - p_del

    # Metrics
    setpoints = np.clip(dp_it / dt, -mw_rated, mw_rated)
    track_err = np.mean(np.abs(p_bess - setpoints)) / max(mw_rated, 1e-9) * 100

    state.p_bess_mw      = p_bess
    state.q_bess_mvar    = q_bess
    state.soc_pct        = soc
    state.p_grid_mw      = p_grid
    state.tracking_err_pct = float(np.clip(track_err, 0, 5))
    state.soc_drift_pct    = float(soc[-1] - soc[0])
    state.dr_fast_resp_s   = _dr_resp(p_bess, dr_fast_t_s, dr_fast_mw, dt)
    state.dr_slow_resp_s   = _dr_resp(p_bess, dr_slow_t_s, dr_slow_mw, dt)
    return state

def _dr_resp(p_bess, t_event, setpoint, dt):
    if setpoint <= 0:
        return 0.0
    idx0 = int(t_event / max(dt, 1e-9))
    for i in range(idx0, min(idx0 + 200, len(p_bess))):
        if p_bess[i] >= setpoint * 0.95:
            return (i - idx0) * dt
    return 999.0
