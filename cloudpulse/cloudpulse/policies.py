"""Scaling policies. Each policy is a small object with decide(t, total, active, history)."""
import math
import numpy as np

LABELS = {
    "static": "Static (sized for p95)",
    "reactive": "Reactive threshold",
    "naive": "Forecast: last value",
    "moving_avg": "Forecast: moving average",
    "ml_rf": "Forecast: Random Forest (ML)",
    "oracle": "Oracle (perfect foresight)",
}


def vms_needed(load, cfg):
    return max(1, math.ceil(load / (cfg.capacity * cfg.target_util)))


class StaticPolicy:
    def __init__(self, n):
        self.n = n

    def decide(self, t, total, active, hist):
        return self.n


class ReactivePolicy:
    """Classic rule: look at current utilisation of ACTIVE VMs; scale out above `up`, in below `down`."""
    def __init__(self, cfg, up=0.80, down=0.40):
        self.cfg, self.up, self.down, self.last = cfg, up, down, -10**9

    def decide(self, t, total, active, hist):
        util = hist[-1] / (max(active, 1) * self.cfg.capacity)
        need = vms_needed(hist[-1], self.cfg)
        if util > self.up and need > total:
            self.last = t
            return need
        if util < self.down and need < total and t - self.last >= self.cfg.cooldown_steps:
            self.last = t
            return need
        return total


class ForecastPolicy:
    """Predictive rule: size the fleet for the FORECAST load at the moment new VMs become ready."""
    def __init__(self, cfg, forecast_fn):
        self.cfg, self.f, self.last = cfg, forecast_fn, -10**9

    def decide(self, t, total, active, hist):
        f = self.f(t, hist)
        if f is None or not np.isfinite(f):
            f = hist[-1]
        need = vms_needed(f, self.cfg)
        if need > total:                      # scale out for the forecast
            self.last = t
            return need
        keep = vms_needed(max(f, hist[-1]), self.cfg)  # never scale in below what NOW needs
        if keep < total and t - self.last >= self.cfg.cooldown_steps:
            self.last = t
            return keep
        return total


def build_policies(cfg, load, ml_preds, static_n):
    """Return {name: factory}. A fresh policy object is created per simulation (they hold state)."""
    n = len(load)
    return {
        "static": lambda: StaticPolicy(static_n),
        "reactive": lambda: ReactivePolicy(cfg),
        "naive": lambda: ForecastPolicy(cfg, lambda t, h: h[-1]),
        "moving_avg": lambda: ForecastPolicy(cfg, lambda t, h: h[-3:].mean()),
        "ml_rf": lambda: ForecastPolicy(cfg, lambda t, h: ml_preds[t]),
        "oracle": lambda: ForecastPolicy(cfg, lambda t, h: load[t:min(t + cfg.boot_steps + 1, n)].max()),
    }
