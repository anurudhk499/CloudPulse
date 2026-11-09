# Report outline
1. Introduction and problem statement (elastic demand, over- vs under-provisioning)
2. Background: auto-scaling, reactive vs predictive, VM boot delay, SLA, cloud billing
3. System design: architecture diagram (see README), simulator timeline, policies
4. Data: trace source, aggregation, scenarios (normal, flash crowd, growth, noisy), train/test split
5. Forecasting: features (12 lags, moving averages, trend, time of day, weekend), models, MAE/RMSE/R2
6. Experiments: tables from `results/policy_results.csv`, boot-time sweep, discussion
7. Limitations and future work (real traces, real cloud, CloudSim/OpenStack integration, queueing model)
8. Testing: `tests/test_cloudpulse.py` (boot delay, cost, SLA, no leakage, oracle bound)

# Likely viva questions
- **Why simulate instead of using AWS?** Controlled, repeatable, free; lets all policies see the same load.
- **Why does boot delay matter?** Reactive scaling reacts after load rises; new VMs arrive late. Prediction can order VMs early.
- **Did ML win?** Honest answer from the results: not clearly on this trace. It beats the moving average in normal traffic but fails on spikes beyond training range.
- **What is the oracle?** Perfect-knowledge policy; a lower bound that shows the maximum possible gain.
- **How did you avoid data leakage?** Time-ordered split (first 70% train, last 30% test); training targets never touch the test period; scenarios modify only the test segment; a unit test checks this.
- **Why is R2 high for the naive forecast too?** Load is strongly autocorrelated, so R2 alone is misleading; compare to baselines.
- **What is an SLA violation here?** An interval where demand exceeds active capacity.
- **How does this relate to CloudSim/OpenStack?** CloudSim simulates datacentres and VM scheduling; this project simulates elastic scaling over time. OpenStack/App Engine are where such policies would run (App Engine has built-in autoscaling).
- **How would you extend it?** Real traces, latency model with queueing, CPU+memory, cost of scale actions, LSTM forecaster, real cloud APIs.
