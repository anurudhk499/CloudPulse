"""CloudPulse - Flask API + dashboard.   Run:  python app.py   then open http://127.0.0.1:5000"""
import os
from flask import Flask, jsonify, render_template, request
from cloudpulse.service import Lab
from cloudpulse.trace import SCENARIOS

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
lab = Lab(os.environ.get("CLOUDPULSE_TRACE", os.path.join(BASE, "data", "trace.csv")))


def _num(data, key, default, lo, hi, cast=float):
    try:
        v = cast(data.get(key, default))
    except (TypeError, ValueError):
        v = default
    return min(max(v, lo), hi)


@app.get("/")
def index():
    return render_template("index.html", scenarios=SCENARIOS)


@app.get("/api/health")
def health():
    return jsonify(status="ok", points=lab.n, step_minutes=lab.step_min)


@app.post("/api/simulate")
def simulate_api():
    d = request.get_json(silent=True) or {}
    scenario = d.get("scenario", "normal")
    if scenario not in SCENARIOS:
        return jsonify(error=f"scenario must be one of {list(SCENARIOS)}"), 400
    result = lab.run(
        scenario=scenario,
        boot_steps=_num(d, "boot_steps", 2, 0, 12, int),
        capacity=_num(d, "capacity", 100, 1, 100000),
        target_util=_num(d, "target_util", 0.75, 0.3, 0.95),
        price=_num(d, "price", 0.05, 0.001, 100),
        traffic_x=_num(d, "traffic_x", 1.0, 0.3, 3.0),
    )
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
