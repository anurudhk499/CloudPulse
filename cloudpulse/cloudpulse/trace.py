"""Workload traces: a synthetic generator, a CSV loader, and test scenarios."""
import numpy as np
import pandas as pd


def generate_synthetic(days=14, step_min=5, seed=42):
    """Synthetic web-traffic trace (daily + weekly pattern, AR(1) noise, random bursts).
    NOTE: this is synthetic. For real data see scripts/prepare_nasa.py."""
    rng = np.random.default_rng(seed)
    n = days * 24 * 60 // step_min
    ts = pd.date_range("2026-01-05 00:00", periods=n, freq=f"{step_min}min")  # a Monday
    hour = ts.hour.values + ts.minute.values / 60
    diurnal = (0.55 + 0.30 * np.sin((hour - 9) * 2 * np.pi / 24)
               + 0.10 * np.sin((hour - 12) * 4 * np.pi / 24))
    weekly = np.where(ts.dayofweek >= 5, 0.6, 1.0)
    e = np.zeros(n)
    for i in range(1, n):
        e[i] = 0.85 * e[i - 1] + rng.normal(0, 0.03)
    load = 1800 * diurnal * weekly * (1 + e)
    for _ in range(25):  # short bursts
        s = rng.integers(0, n - 10)
        d = rng.integers(2, 7)
        load[s:s + d] *= 1 + rng.uniform(0.3, 0.8)
    load = np.clip(load, 50, None)
    return pd.DataFrame({"timestamp": ts, "requests_per_min": load.round(1)})


def load_trace(path):
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    if len(df) < 500:
        raise ValueError("Trace too short: need at least 500 rows.")
    step = int((df.timestamp.iloc[1] - df.timestamp.iloc[0]).total_seconds() // 60)
    return df, max(step, 1)


SCENARIOS = {
    "normal": "Test period replayed unchanged",
    "flash_crowd": "4 sudden 2.5x traffic spikes in the test period (never seen in training)",
    "steady_growth": "Traffic grows 1.0x -> 1.8x over the test period (beyond training range)",
    "noisy": "Heavy random noise (about +/-25%) on top of the test period",
}


def apply_scenario(base, split, name, seed=7):
    """Return a copy of the trace where only the TEST segment (index >= split) is modified."""
    load = np.array(base, dtype=float)
    test = load[split:]
    m = len(test)
    rng = np.random.default_rng(seed)
    if name == "normal":
        pass
    elif name == "flash_crowd":
        mult = np.ones(m)
        for frac in (0.15, 0.40, 0.62, 0.85):
            s = int(m * frac) + int(rng.integers(-10, 10))
            shape = [1.6, 2.5] + [2.5] * 6 + [1.8, 1.3]
            for k, v in enumerate(shape):
                if 0 <= s + k < m:
                    mult[s + k] = max(mult[s + k], v)
        test = test * mult
    elif name == "steady_growth":
        test = test * np.linspace(1.0, 1.8, m)
    elif name == "noisy":
        test = test * rng.lognormal(0, 0.25, m)
    else:
        raise ValueError(f"Unknown scenario: {name}")
    load[split:] = test
    return load
