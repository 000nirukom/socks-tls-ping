import re
import argparse
from datetime import datetime
from pathlib import Path
import statistics

import numpy as np
import fastplotlib as fpl

parser = argparse.ArgumentParser()
parser.add_argument("logfile", help="Path to the log file")
parser.add_argument("--webgl", action="store_true", help="Accelerate with WebGL")
args = parser.parse_args()

LOG_FILE = Path(args.logfile)
log_name = LOG_FILE.stem.split("_")[0]

ENABLE_WEBGL = args.webgl

rtt_list: list[tuple[datetime, float]] = []
pattern = re.compile(r"请求 #(\d+) 成功 \| RTT: ([\d.]+)ms")

with open(LOG_FILE, "r", encoding="utf-8") as f:
    for line in f:
        if "[预热 成功]" in line:
            continue

        parts = line.strip().split(" | ", 1)
        if len(parts) < 2:
            continue

        dt_str = parts[0]
        match = pattern.search(line)
        if not match:
            continue

        try:
            dt = datetime.strptime(
                dt_str, "%Y-%m-%d %H:%M:%S"
            )  # ← adjust format if needed!
        except ValueError:
            continue

        rtt = float(match.group(2))

        rtt_list.append((dt, rtt))


base_ts = rtt_list[0][0].timestamp()

rtt_ts: list[float] = [dt.timestamp() - base_ts for dt, _ in rtt_list]
rtt_values = [rtt for _, rtt in rtt_list]

avg_rtt = statistics.mean(rtt_values)
min_rtt = min(rtt_values)
max_rtt = max(rtt_values)
std_rtt = statistics.stdev(rtt_values) if len(rtt_values) >= 2 else 0

threshold = avg_rtt + 3 * std_rtt

colors = ["r" if rtt >= threshold else "#176f58" for rtt in rtt_values]

xs = rtt_ts
ys = rtt_values

data = np.column_stack([xs, ys])

figure = fpl.Figure(size=(700, 560))


# add a scatter
scatter = figure[0, 0].add_scatter(
    data=data,
    sizes=5,
    colors=colors,
    edge_width=0,
)

min_ts = datetime.fromtimestamp(base_ts + xs[0])
max_ts = datetime.fromtimestamp(base_ts + xs[-1])
formatter = "%d %H:%M" if max_ts.day != min_ts.day else "%H:%M:%S"


def tick_format(
    sec: float,
    _min_sec: float,
    _max_sec: float,
) -> str:
    return datetime.fromtimestamp(base_ts + sec).strftime(formatter)


figure[0, 0].axes.x.tick_side = "right"
figure[0, 0].axes.x.tick_format = tick_format

is_moving = False
vertex_index = None


figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
