"""Headless experiment runner: produces the tables for your report.   python scripts/run_experiments.py"""
import os, sys
import pandas as pd
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)
from cloudpulse.service import Lab
from cloudpulse.trace import SCENARIOS

lab = Lab(os.path.join(root, "data", "trace.csv"))
os.makedirs(os.path.join(root, "results"), exist_ok=True)
rows, frows = [], []
for boot in (0, 1, 2, 4, 6):
    for sc in SCENARIOS:
        r = lab.run(scenario=sc, boot_steps=boot)
        for name, p in r["policies"].items():
            rows.append({"scenario": sc, "boot_minutes": boot * lab.step_min, "policy": p["label"], **p["metrics"]})
        for f in r["forecast"]:
            frows.append({"scenario": sc, "boot_minutes": boot * lab.step_min, **f})
res = pd.DataFrame(rows)
res.to_csv(os.path.join(root, "results", "policy_results.csv"), index=False)
pd.DataFrame(frows).to_csv(os.path.join(root, "results", "forecast_accuracy.csv"), index=False)
pd.set_option("display.width", 200, "display.max_columns", 20)
for sc in SCENARIOS:
    print(f"\n=== scenario: {sc} (boot = 10 min) ===")
    print(res[(res.scenario == sc) & (res.boot_minutes == 10)].drop(columns=["scenario", "boot_minutes"]).to_string(index=False))
print("\nFull results saved in results/*.csv")
