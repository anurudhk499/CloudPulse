"""Discrete-time auto-scaling simulator.

Timeline of interval t:
  1. VMs whose boot finished become active.
  2. The policy sees only load[:t] (past intervals) and returns the desired TOTAL VM count.
  3. New VMs become active at interval t + boot_steps. Removed VMs vanish at once.
  4. Demand load[t] is served by the ACTIVE VMs; anything above capacity is unserved (SLA violation).
Billing: booting VMs are billed (as on real clouds)."""
import numpy as np


def simulate(load, policy, cfg, start):
    load = np.asarray(load, dtype=float)
    n = len(load)
    active, pending, actions, events = cfg.min_vms, [], 0, []
    act_arr, billed_arr = [], []
    for t in range(start, n):
        ready = [r for r in pending if r <= t]
        if ready:
            events.append([t - start, "ready", len(ready)])
        active += len(ready)
        pending = [r for r in pending if r > t]
        total = active + len(pending)
        want = int(min(max(policy.decide(t, total, active, load[:t]), cfg.min_vms), cfg.max_vms))
        if want > total:
            pending += [t + cfg.boot_steps] * (want - total)
            events.append([t - start, "order", want - total])
            actions += 1
        elif want < total:
            rem = total - want
            pending.sort()
            k = min(rem, len(pending))
            if k:
                pending = pending[:len(pending) - k]  # cancel newest boots first
                rem -= k
            active -= rem
            events.append([t - start, "remove", total - want])
            actions += 1
        ready = [r for r in pending if r <= t]  # boot_steps == 0 case
        if ready:
            events.append([t - start, "ready", len(ready)])
        active += len(ready)
        pending = [r for r in pending if r > t]
        act_arr.append(active)
        billed_arr.append(active + len(pending))
    act = np.array(act_arr)
    billed = np.array(billed_arr)
    demand = load[start:]
    cap = act * cfg.capacity
    hours = cfg.step_minutes / 60
    vm_hours = float(billed.sum() * hours)
    metrics = {
        "sla_violation_pct": round(float((demand > cap).mean() * 100), 2),
        "unserved_pct": round(float(np.maximum(demand - cap, 0).sum() / demand.sum() * 100), 2),
        "vm_hours": round(vm_hours, 1),
        "cost_usd": round(vm_hours * cfg.price_per_vm_hour, 2),
        "avg_utilization_pct": round(float(np.minimum(demand / cap, 1).mean() * 100), 1),
        "scaling_actions": int(actions),
    }
    return {"active": act, "billed": billed, "capacity": cap, "metrics": metrics, "events": events}
