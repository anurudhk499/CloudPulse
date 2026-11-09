"""Convert a real web-server access log (NASA HTTP, Common Log Format) into data/trace.csv.
Usage: python scripts/prepare_nasa.py NASA_access_log_Jul95.gz [--scale 20] [--step 5]
Download: https://ita.ee.lbl.gov/html/contrib/NASA-HTTP.html
--scale multiplies request counts (NASA traffic is small vs. a VM capacity of 100 req/min);
state this scaling in your report, or use --scale 1 and set VM capacity to about 5 in the dashboard."""
import argparse, gzip, re, sys
from collections import Counter
from datetime import datetime
import pandas as pd

RX = re.compile(r"\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})")
ap = argparse.ArgumentParser()
ap.add_argument("log")
ap.add_argument("--out", default="data/trace.csv")
ap.add_argument("--step", type=int, default=5, help="minutes per interval")
ap.add_argument("--scale", type=float, default=20.0)
a = ap.parse_args()

opener = gzip.open if a.log.endswith(".gz") else open
counts = Counter()
with opener(a.log, "rt", encoding="latin-1") as f:
    for line in f:
        m = RX.search(line)
        if m:
            t = datetime.strptime(m.group(1), "%d/%b/%Y:%H:%M:%S")
            counts[t.replace(minute=t.minute // a.step * a.step, second=0)] += 1
if not counts:
    sys.exit("No log lines parsed - is this a Common Log Format file?")
s = pd.Series(counts).sort_index()
s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq=f"{a.step}min"))
s = s.interpolate(limit_direction="both")  # fill gaps in the log (e.g. server outage)
df = pd.DataFrame({"timestamp": s.index, "requests_per_min": (s.values / a.step * a.scale).round(1)})
df.to_csv(a.out, index=False)
print(f"Wrote {len(df)} rows ({df.timestamp.min()} -> {df.timestamp.max()}) to {a.out}")
