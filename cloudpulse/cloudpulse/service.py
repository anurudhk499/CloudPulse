"""Glue layer: loads the trace, trains forecasters (cached), runs all policies."""
import os
import numpy as np
from .config import SimConfig
from .forecaster import Forecasters
from .policies import LABELS, build_policies, vms_needed
from .simulator import simulate
from .trace import SCENARIOS, apply_scenario, generate_synthetic, load_trace

TRAIN_FRAC = 0.7


class Lab:
    def __init__(self, trace_path):
        if not os.path.exists(trace_path):
            os.makedirs(os.path.dirname(trace_path) or ".", exist_ok=True)
            generate_synthetic().to_csv(trace_path, index=False)
        df, self.step_min = load_trace(trace_path)
        self.df, self.base = df, df["requests_per_min"].values.astype(float)
        self.ts = df["timestamp"]
        self.n = len(df)
        self.split = int(self.n * TRAIN_FRAC)
        self._fc = {}

    def forecasters(self, boot):
        if boot not in self._fc:
            self._fc[boot] = Forecasters(self.base, self.ts.iloc[0], self.step_min, boot, self.split)
        return self._fc[boot]

    def run(self, scenario="normal", boot_steps=2, capacity=100.0, target_util=0.75,
            price=0.05, only=None, traffic_x=1.0):
        cfg = SimConfig(capacity=capacity, boot_steps=boot_steps, step_minutes=self.step_min,
                        price_per_vm_hour=price, target_util=target_util)
        load = apply_scenario(self.base, self.split, scenario)
        if traffic_x != 1.0:
            load[self.split:] *= traffic_x
        fc = self.forecasters(boot_steps)
        preds = fc.predict_rf(load)
        static_n = vms_needed(float(np.percentile(self.base[:self.split], 95)), cfg)
        factories = build_policies(cfg, load, preds, static_n)
        out = {}
        for name, make in factories.items():
            if only and name not in only:
                continue
            r = simulate(load, make(), cfg, self.split)
            demand = load[self.split:]
            u = demand / r["capacity"]
            rt = 80 / (1 - np.minimum(u, 0.95)) + np.maximum(u - 0.95, 0) * 20000  # simple queueing-style estimate (ms)
            rt = np.clip(rt, 0, 5000)
            r["metrics"]["avg_response_ms"] = int(rt.mean())
            r["metrics"]["p95_response_ms"] = int(np.percentile(rt, 95))
            out[name] = {"label": LABELS[name], "vms": r["active"].tolist(),
                         "booting": (r["billed"] - r["active"]).tolist(),
                         "capacity": r["capacity"].tolist(), "response_ms": rt.round().astype(int).tolist(),
                         "events": r["events"], "metrics": r["metrics"]}
        return {
            "scenario": scenario, "scenario_text": SCENARIOS[scenario],
            "timestamps": self.ts.iloc[self.split:].dt.strftime("%Y-%m-%d %H:%M").tolist(),
            "load": load[self.split:].round(1).tolist(),
            "policies": out,
            "forecast": fc.evaluate(load),
            "info": {"train_points": self.split, "test_points": self.n - self.split,
                     "step_minutes": self.step_min, "static_vms": static_n,
                     "boot_minutes": boot_steps * self.step_min, "price": price},
        }
