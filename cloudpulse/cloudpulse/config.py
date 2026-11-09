"""Simulation parameters. Every number here is an ASSUMPTION - state them in your report."""
from dataclasses import dataclass


@dataclass
class SimConfig:
    capacity: float = 100.0         # requests/min one VM can serve
    boot_steps: int = 2             # VM boot delay in intervals (2 x 5 min = 10 min)
    step_minutes: int = 5           # length of one simulation interval
    price_per_vm_hour: float = 0.05 # USD, billed while VM is booting or running
    min_vms: int = 2
    max_vms: int = 200
    target_util: float = 0.75       # utilisation that policies try to size for
    cooldown_steps: int = 3         # min intervals between a scale-out and a scale-in
