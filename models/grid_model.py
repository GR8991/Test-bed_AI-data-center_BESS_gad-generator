import numpy as np
from models.sim_state import SimState
from utils.constants import NVIDIA_REQ, LVRT_SEGMENTS, HVRT_SEGMENTS, MP2XL

def run_grid(
    state: SimState,
    grid_mva: float,
    bess_kva: float,
    nominal_kv: float,
    apply_lvrt: bool,
    lvrt_depth_pu: float,
    lvrt_dur_s: float,
    lvrt_t_s: float,
    apply_hvrt: bool,
    hvrt_level_pu: float,
    hvrt_dur_s: float,
    hvrt_t_s: float,
    dt_s: float = 1.0,
) -> SimState:
    N  = len(state.p_it_mw) if state.p_it_mw is not None else int(86400 / dt_s)
    dt = dt_s

    scr = grid_mva / max(bess_kva / 1000.0, 0.001)
    state.scr      = float(scr)
    state.grid_mva = float(grid_mva)

    v_pu = np.ones(N)

    # LVRT event
    if apply_lvrt:
        i0 = int(lvrt_t_s / dt)
        i1 = min(i0 + int(lvrt_dur_s / dt), N)
        v_pu[i0:i1] = lvrt_depth_pu
        # Smooth edges (10 cycle)
        ramp = min(10, i1 - i0)
        for j in range(ramp):
            v_pu[i0 + j] = 1.0 + (lvrt_depth_pu - 1.0) * (j / ramp)
        for j in range(ramp):
            if i1 - ramp + j < N:
                v_pu[i1 - ramp + j] = lvrt_depth_pu + (1.0 - lvrt_depth_pu) * (j / ramp)
        state.lvrt_active = True

    # HVRT event
    if apply_hvrt:
        i0 = int(hvrt_t_s / dt)
        i1 = min(i0 + int(hvrt_dur_s / dt), N)
        v_pu[i0:i1] = hvrt_level_pu
        state.hvrt_active = True

    state.v_pu = v_pu
    return state

def check_lvrt_compliance(v_pu: float, duration_s: float) -> dict:
    """Return whether V+duration is within IEEE 1547 LVRT envelope."""
    for vmin, vmax, rt_s in LVRT_SEGMENTS:
        if vmin <= v_pu < vmax:
            return {
                "inside_envelope": duration_s <= rt_s,
                "allowed_s": rt_s,
                "actual_s":  duration_s,
            }
    return {"inside_envelope": True, "allowed_s": 9999, "actual_s": duration_s}

def check_hvrt_compliance(v_pu: float, duration_s: float) -> dict:
    for vmin, vmax, rt_s in HVRT_SEGMENTS:
        if vmin <= v_pu <= vmax:
            return {
                "inside_envelope": duration_s <= rt_s,
                "allowed_s": rt_s,
                "actual_s":  duration_s,
            }
    return {"inside_envelope": False, "allowed_s": 0, "actual_s": duration_s}
