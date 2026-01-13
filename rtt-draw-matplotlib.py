# -*- coding: utf-8 -*-
import re
import statistics
import sys
from datetime import datetime

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import StrMethodFormatter
import numpy as np

import argparse
from pathlib import Path

matplotlib.use("QtAgg")

FONT_PATH = Path("./fonts/fusion-pixel-12px-proportional-zh_hans.ttf")

if FONT_PATH.exists():
    from matplotlib import font_manager

    fm: font_manager.FontManager = font_manager.fontManager
    fm.addfont(FONT_PATH)
    prop = font_manager.FontProperties(fname=FONT_PATH)
    plt.rcParams["font.family"] = prop.get_name()
    plt.rc("font", **{"size": 12})

# ────────────────────────────────────────────────
#  Argument parsing
# ────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("logfile", help="Path to the log file")
parser.add_argument(
    "--no-spike-color", action="store_true", help="Don't color spikes differently"
)
args = parser.parse_args()

LOG_FILE = args.logfile

# ────────────────────────────────────────────────
#  Parse log
# ────────────────────────────────────────────────
rtt_list = []  # list of (datetime, rtt, req_num)
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

        req_num = int(match.group(1))
        rtt = float(match.group(2))

        rtt_list.append((dt, rtt, req_num))

if not rtt_list:
    print("No valid RTT records found.")
    sys.exit(1)

# Sort just in case log lines are not in order
rtt_list.sort(key=lambda x: x[0])

rtt_values = [rtt for _, rtt, _ in rtt_list]
req_numbers = [num for _, _, num in rtt_list]

# ────────────────────────────────────────────────
#  Basic statistics
# ────────────────────────────────────────────────
n = len(rtt_values)
avg_rtt = statistics.mean(rtt_values)
median_rtt = statistics.median(rtt_values)
min_rtt = min(rtt_values)
max_rtt = max(rtt_values)
std_rtt = statistics.stdev(rtt_values) if n >= 2 else 0
p90 = np.percentile(rtt_values, 90)
p95 = np.percentile(rtt_values, 95)
p99 = np.percentile(rtt_values, 99)

threshold = avg_rtt + 3 * std_rtt

spikes = [(dt, rtt, num) for dt, rtt, num in rtt_list if rtt > threshold]
spike_rate = len(spikes) / n * 100

print("=== Socks5 RTT Analysis (Preheat Ignored) ===")
print(f"Total requests     : {n:,d}")
print(f"Average RTT        : {avg_rtt:6.2f} ms")
print(f"Median RTT         : {median_rtt:6.2f} ms")
print(f"Min / Max RTT      : {min_rtt:6.2f} – {max_rtt:6.2f} ms")
print(f"Std deviation      : {std_rtt:6.2f} ms")
print(f"95th percentile    : {p95:6.2f} ms")
print(f"Spike threshold    : {threshold:6.2f} ms")
print(f"Number of spikes   : {len(spikes):,d}  ({spike_rate:.2f}%)")
if spikes:
    print(f"  → worst spike   : {max(spikes, key=lambda x: x[1])[1]:.2f} ms")

plot_times = [dt for dt, _, _ in rtt_list]
plot_main = rtt_values
plot_extra = {}

# ────────────────────────────────────────────────
#  Plot
# ────────────────────────────────────────────────
plt.figure(figsize=(14, 7))

if args.no_spike_color:
    colors = "royalblue"
else:
    colors = ["indianred" if r > threshold else "cornflowerblue" for r in plot_main]

plt.scatter(
    plot_times,
    plot_main,
    c=colors,
    s=18,
    alpha=0.6,
    edgecolors="none",
    label="RTT per request",
)

plt.axhline(
    avg_rtt, color="green", ls="--", lw=1.8, alpha=0.9, label=f"Avg = {avg_rtt:.1f} ms"
)
plt.axhline(
    p95,
    color="#1db986",
    ls="--",
    lw=1.8,
    alpha=0.7,
    label=f"P95 = {p95:.1f} ms",
)
plt.axhline(
    p99,
    color="#2af0ae",
    ls="--",
    lw=1.8,
    alpha=0.7,
    label=f"P99 = {p99:.1f} ms",
)
plt.axhline(
    threshold,
    color="darkorange",
    ls="--",
    lw=1.8,
    alpha=0.4,
    label=f"Spike = {threshold:.1f} ms ({spike_rate:.2f}%)",
)

# log-scale
plt.gca().set_ylim(bottom=min_rtt - 1, top=max_rtt + 1)
plt.gca().set_yscale("log")
plt.gca().yaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))
plt.gca().yaxis.set_minor_formatter(StrMethodFormatter("{x:.0f}"))

# ── Nice date formatting ───────────────────────────────
plt.gca().xaxis.set_major_formatter(mdates.AutoDateFormatter(mdates.AutoDateLocator()))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=12))
plt.xticks(rotation=38, ha="right")

plt.ylabel("RTT [ms]")
plt.xlabel("Time")
plt.title(f"HTTPS RTT – {LOG_FILE.split('_')[0]}")
plt.grid(True, alpha=0.35, ls="--")
plt.legend(loc="upper right", framealpha=0.92)
plt.tight_layout()

plt.show()
