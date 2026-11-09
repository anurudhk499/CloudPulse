# CloudPulse: Reactive vs Predictive Auto-Scaling Simulation

A Cloud Computing (7th sem) academic project. It replays a workload trace through a small cloud simulator
(VM pool, boot delay, billing, SLA check) and compares six scaling policies on a web dashboard.

| Policy | Idea |
|---|---|
| Static | Fixed fleet sized for the 95th-percentile training load |
| Reactive threshold | Scale out above 80% utilisation, in below 40% (classic rule) |
| Forecast: last value / moving average | Size the fleet for a simple forecast |
| Forecast: Random Forest (ML) | Size the fleet for an ML forecast of load when new VMs are ready |
| Oracle | Knows the future load: a lower bound, not a real policy |

## 1. Run it (Windows / macOS / Linux)

Needs Python 3.10+.

```bash
cd cloudpulse
python -m venv venv
venv\Scripts\activate          # Windows      (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
python app.py
```
Open **http://127.0.0.1:5000**. Pick a scenario and boot time, then press *Run simulation*.
The dashboard loads Chart.js from a CDN, so you need internet for the charts.

Other commands:
```bash
python -m unittest discover -s tests      # 5 unit tests
python scripts/run_experiments.py         # prints tables, saves results/*.csv for your report
```

## 2. Use a real trace (recommended for the viva)

`data/trace.csv` is **synthetic** (daily + weekly pattern, noise, bursts). To use real traffic:
1. Download `NASA_access_log_Jul95.gz` from https://ita.ee.lbl.gov/html/contrib/NASA-HTTP.html
2. `python scripts/prepare_nasa.py NASA_access_log_Jul95.gz --scale 20`
   (NASA traffic is small, so counts are multiplied by 20; say so in your report)
3. Run `python app.py` again. Any CSV with columns `timestamp,requests_per_min` works.

## 3. Deploy on Google App Engine (ties to your lab manual)

`app.yaml` is included. With the Google Cloud SDK installed and a project created:
`gcloud app deploy`. Check the current free-quota rules first. Deployment is optional; the project works locally.

## 4. Architecture

```
trace.csv -> trace.py (+ scenarios) -> forecaster.py (train on first 70%, time split)
                                   \-> simulator.py <- policies.py
service.py (glue, caching) -> app.py (Flask REST: POST /api/simulate) -> templates/index.html (Chart.js)
```
Simulator timeline per 5-minute interval: boots finish -> policy sees only past load -> VMs ordered now
become active after the boot delay -> demand is served by active VMs; excess demand = SLA violation.
VMs are billed while booting.

## 5. What the results show (default settings, synthetic trace)

Run `scripts/run_experiments.py` and quote your own numbers. On the bundled trace:
- Every policy beats the static fleet on cost (about 50% cheaper) with similar SLA in the normal scenario.
- **The ML forecaster does not clearly beat a naive "last value" forecast** (MAE 46 vs 43 req/min). The trace is smooth, so recent load already predicts the next load well.
- Random Forest has fewer SLA violations than the moving average in the normal scenario, but it is worse in flash-crowd and growth scenarios because tree models cannot predict loads above the training range.
- The reactive rule scores fewer violations than forecast policies here, but it keeps more spare capacity (higher cost). Forecast policies size tightly, so the comparison is a cost vs SLA trade-off, not a win for one side.
- Longer boot times hurt every policy; the oracle shows how much room a perfect predictor would have.

Reporting this honestly is the strength of the project: *when* does prediction help, and when does it not.

## 6. Limitations (put these in your report)
- Synthetic trace by default; the generator's assumptions shape the results.
- No real VMs are provisioned; capacity per VM, boot time and price are assumed constants.
- No request queueing, no per-request latency, one resource dimension (requests/min).
- One trace, one train/test split; no statistical confidence intervals.
- Results are valid under the stated simulation assumptions only, not as real cloud savings.

## 7. Files
`app.py` Flask API | `cloudpulse/` simulator, policies, forecaster | `templates/index.html` dashboard |
`scripts/` experiments and NASA converter | `tests/` unit tests | `docs/VIVA_AND_REPORT.md` report outline and viva Q&A

## Dashboard guide (beginner-friendly view)
1. Pick a situation (normal, sudden spike, growing, jumpy) and a start-up time for new computers.
2. Pick a manager (fixed, rule-based, AI predictor, perfect foresight).
3. Press Play. Traffic flows through the load balancer to the VM blocks; the meters flash when values change; the event list explains each decision.
The scoreboard compares all managers; the "Technical details" panel has the full metric tables, forecast accuracy and settings.
Response time is a simple queueing-style estimate (grows as VMs fill up), not a measurement.
