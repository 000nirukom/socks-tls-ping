# -*- coding: utf-8 -*-
import re
import statistics
import sys
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict
import argparse

# ────────────────────────────────────────────────
#  Argument parsing
# ────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("logfile", help="Path to the log file")
parser.add_argument(
    "--max-points",
    type=int,
    default=8000,
    help="Maximum number of points to plot (default: 8000)",
)
parser.add_argument(
    "--bin-seconds",
    type=int,
    default=30,
    help="Time bin size for aggregation / downsampling in seconds",
)
parser.add_argument(
    "--no-spike-color", action="store_true", help="Don't color spikes differently"
)
args = parser.parse_args()

LOG_FILE = args.logfile
MAX_PLOT_POINTS = args.max_points
BIN_SECONDS = args.bin_seconds

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
p95 = np.percentile(rtt_values, 95)

threshold = avg_rtt + 3 * std_rtt

spikes = [(dt, rtt, num) for dt, rtt, num in rtt_list if rtt > threshold]

print("=== Socks5 RTT Analysis (Preheat Ignored) ===")
print(f"Total requests     : {n:,d}")
print(f"Average RTT        : {avg_rtt:6.2f} ms")
print(f"Median RTT         : {median_rtt:6.2f} ms")
print(f"Min / Max RTT      : {min_rtt:6.2f} – {max_rtt:6.2f} ms")
print(f"Std deviation      : {std_rtt:6.2f} ms")
print(f"95th percentile    : {p95:6.2f} ms")
print(f"Spike threshold    : {threshold:6.2f} ms")
print(f"Number of spikes   : {len(spikes):,d}  ({len(spikes) / n * 100:.2f}%)")
if spikes:
    print(f"  → worst spike   : {max(spikes, key=lambda x: x[1])[1]:.2f} ms")

# ────────────────────────────────────────────────
#  Downsampling / binning for plot (very important for > 50k points)
# ────────────────────────────────────────────────
if len(rtt_list) > MAX_PLOT_POINTS * 1.5:
    print(
        f"\nDownsampling plot data ({len(rtt_list):,} → ~{MAX_PLOT_POINTS:,} points or fewer)"
    )

    # Bin by time
    bins = defaultdict(list)
    start_time = rtt_list[0][0]

    for dt, rtt, _ in rtt_list:
        age_sec = (dt - start_time).total_seconds()
        bin_idx = int(age_sec // BIN_SECONDS)
        bins[bin_idx].append(rtt)

    # Build binned data
    bin_times = []
    bin_medians = []
    bin_p90s = []
    bin_p99s = []

    for idx in sorted(bins):
        vals = bins[idx]
        if not vals:
            continue
        t = start_time + timedelta(seconds=idx * BIN_SECONDS + BIN_SECONDS / 2)
        bin_times.append(t)
        bin_medians.append(np.median(vals))
        bin_p90s.append(np.percentile(vals, 90))
        bin_p99s.append(np.percentile(vals, 99))

    plot_times = bin_times
    plot_main = bin_medians
    plot_extra = {"p90": bin_p90s, "p99": bin_p99s}
    title_suffix = f" (binned {BIN_SECONDS}s — median / p90 / p99)"

else:
    # No downsampling needed
    plot_times = [dt for dt, _, _ in rtt_list]
    plot_main = rtt_values
    plot_extra = {}
    title_suffix = ""

# ────────────────────────────────────────────────
#  Plot
# ────────────────────────────────────────────────
plt.figure(figsize=(14, 7))

if len(plot_times) <= MAX_PLOT_POINTS or not plot_extra:
    # Scatter only when we have reasonable number of points
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
        label="RTT per request" if len(plot_times) < 3000 else "RTT (sampled)",
    )

else:
    # Binned mode → line + bands
    plt.plot(
        plot_times, plot_extra["p99"], lw=1.1, color="salmon", alpha=0.9, label="99th %"
    )
    plt.plot(
        plot_times, plot_extra["p90"], lw=1.4, color="orange", alpha=0.9, label="90th %"
    )
    plt.plot(plot_times, plot_main, lw=2.0, color="darkblue", label="Median RTT")

plt.axhline(
    avg_rtt, color="green", ls="--", lw=1.8, alpha=0.9, label=f"Avg = {avg_rtt:.1f} ms"
)
plt.axhline(
    threshold,
    color="darkorange",
    ls="--",
    lw=1.8,
    alpha=0.9,
    label=f"Spike threshold = {threshold:.1f} ms",
)

# ── Nice date formatting ───────────────────────────────
plt.gca().xaxis.set_major_formatter(mdates.AutoDateFormatter(mdates.AutoDateLocator()))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=12))
plt.xticks(rotation=38, ha="right")

plt.ylabel("RTT [ms]")
plt.xlabel("Time")
plt.title(f"Socks5 RTT – {LOG_FILE}{title_suffix}")
plt.grid(True, alpha=0.35, ls="--")
plt.legend(loc="upper right", framealpha=0.92)
plt.tight_layout()

plt.show()
