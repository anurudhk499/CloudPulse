import os, sys, unittest
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cloudpulse.config import SimConfig
from cloudpulse.policies import StaticPolicy
from cloudpulse.simulator import simulate
from cloudpulse.service import Lab

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Step10:
    def decide(self, t, total, active, hist):
        return 10


class Tests(unittest.TestCase):
    def test_boot_delay(self):
        cfg = SimConfig(boot_steps=2, min_vms=2)
        r = simulate(np.full(10, 100.0), Step10(), cfg, start=0)
        self.assertEqual(r["active"].tolist()[:4], [2, 2, 10, 10])
        self.assertEqual(r["billed"][0], 10)  # booting VMs are billed

    def test_cost(self):
        cfg = SimConfig()
        r = simulate(np.full(12, 100.0), StaticPolicy(10), cfg, start=0)
        self.assertAlmostEqual(r["metrics"]["cost_usd"], 10 * 12 * 5 / 60 * 0.05, places=2)

    def test_sla_when_underprovisioned(self):
        cfg = SimConfig()
        r = simulate(np.full(10, 1000.0), StaticPolicy(5), cfg, start=0)
        self.assertEqual(r["metrics"]["sla_violation_pct"], 100.0)
        self.assertAlmostEqual(r["metrics"]["unserved_pct"], 56.0)  # first 2 intervals run on min_vms while 5 VMs boot

    def test_no_training_leakage(self):
        lab = Lab(os.path.join(ROOT, "data", "trace.csv"))
        fc = lab.forecasters(2)
        self.assertLess(fc.train_idx.max() + 2, lab.split)

    def test_oracle_not_worse_than_reactive_on_flash_crowd(self):
        lab = Lab(os.path.join(ROOT, "data", "trace.csv"))
        r = lab.run("flash_crowd", boot_steps=2, only=["reactive", "oracle"])["policies"]
        self.assertLessEqual(r["oracle"]["metrics"]["sla_violation_pct"],
                             r["reactive"]["metrics"]["sla_violation_pct"])


if __name__ == "__main__":
    unittest.main()
