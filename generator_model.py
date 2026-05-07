import numpy as np
from scipy.signal import lfilter
from models.sim_state import SimState
from utils.constants import CAT_DEFAULTS, NVIDIA_REQ

def run_generator(
    state: SimState,
    gen_mw: float,
    num_gens: int,
    governor_s: float,
    droop_pct: float,
    cold_start_s: float,
    n1_trip_t_s: float,
    do_blackstart: bool,
    dt_s: float = 1.0,
) -> SimState:
    if state.p_it_mw is None:
        return state

    N   = len(state.p_it_mw)
    dt  = dt_s
    gen_total_mw = gen_mw * num_gens

    p_bess  = state.p_bess_mw if state.p_bess_mw is not None else np.zeros(N)
    p_it    = state.p_it_mw
    p_gen   = np.zeros(N)
    freq    = np.full(N, 50.0)

    # Generator supplies residual load (after BESS) via slow governor
    residual = np.clip(p_it - p_bess, 0, gen_total_mw)

    # First-order lag — governor response (scipy IIR filter)
    tau   = governor_s
    alpha = dt / (tau + dt)
    b     = [alpha]
    a     = [1, -(1 - alpha)]
    p_gen_raw = lfilter(b, a, residual)
    p_gen = np.clip(p_gen_raw, 0, gen_total_mw)

    # N-1 trip event
    if 0 < n1_trip_t_s < N * dt:
        trip_idx = int(n1_trip_t_s / dt)
        surviving_mw = gen_mw * (num_gens - 1)
        for i in range(trip_idx, N):
            p_gen[i] = min(p_gen[i], surviving_mw)
            # BESS must pick up the slack — frequency deviation
            slack = p_it[i] - p_gen[i] - p_bess[i]
            freq[i] = 50.0 - (slack / max(gen_total_mw, 0.001)) * 1.5

    # Frequency droop model
    for i in range(N):
        p_total = p_gen[i] + p_bess[i]
        imbalance = p_it[i] - p_total
        freq[i] = max(45.0, min(55.0,
                      50.0 - (imbalance / max(gen_total_mw, 0.001)) * (droop_pct / 100) * 50))

    # Smooth frequency
    alpha_f = dt / (2.0 + dt)
    b_f = [alpha_f]
    a_f = [1, -(1 - alpha_f)]
    freq = lfilter(b_f, a_f, freq)

    # Black start sequence — if BESS alone then step-load the generator
    blackstart_done = False
    if do_blackstart:
        bs_steps = NVIDIA_REQ["blackstart_steps"]  # [10, 25, 50]
        step_dur = int(120 / dt)                    # 2 min per step
        for k, pct in enumerate(bs_steps):
            i0 = k * step_dur
            i1 = min(i0 + step_dur, N)
            target = gen_total_mw * pct / 100.0
            p_gen[i0:i1] = np.linspace(
                p_gen[i0] if i0 < N else 0, target, i1 - i0
            )
        blackstart_done = True

    state.p_gen_mw   = p_gen
    state.freq_hz    = freq
    state.gen_mw_rated = gen_total_mw
    state.num_gens   = num_gens
    return state
