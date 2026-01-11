# -*- coding: utf-8 -*-
import re
import statistics
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import sys

# ==================== Config ====================
LOG_FILE = sys.argv[1] if len(sys.argv) > 1 else exit(1)
SPIKE_THRESHOLD_FACTOR = 3.0

# How many points to show in the plot (recommended 5k–20k)
MAX_PLOT_POINTS = 10000

# ==================== Parsing ====================
rtt_values = []
timestamps = []  # will store seconds since start
request_numbers = []  # original request #

pattern = re.compile(r"请求 #(\d+) 成功 \| RTT: ([\d.]+)ms")

print("Reading log file...", end="", flush=True)

with open(LOG_FILE, "r", encoding="utf-8") as f:
    for line in f:
        if "[预热 成功]" in line:
            continue

        match = pattern.search(line)
        if not match:
            continue

        req_num = int(match.group(1))
        rtt = float(match.group(2))

        # Extract timestamp (first part before first " | ")
        try:
            dt_str = line.split(" | ", 1)[0].strip()
            dt = datetime.strptime(
                dt_str, "%Y-%m-%d %H:%M:%S"
            )  # adjust format if needed
            seconds_since_start = (dt - datetime(1970, 1, 1)).total_seconds()
        except:
            # fallback: just use request number
            seconds_since_start = req_num

        rtt_values.append(rtt)
        timestamps.append(seconds_since_start)
        request_numbers.append(req_num)

print(f" done. Found {len(rtt_values):,} normal requests.")

if not rtt_values:
    print("No valid RTT data found.")
    sys.exit(0)

# ==================== Statistics ====================
avg_rtt = statistics.mean(rtt_values)
median_rtt = statistics.median(rtt_values)
min_rtt = min(rtt_values)
max_rtt = max(rtt_values)
stddev_rtt = statistics.stdev(rtt_values) if len(rtt_values) > 1 else 0
p95 = np.percentile(rtt_values, 95)

threshold = avg_rtt + SPIKE_THRESHOLD_FACTOR * stddev_rtt

spike_indices = [i for i, rtt in enumerate(rtt_values) if rtt > threshold]
spike_requests = [(request_numbers[i], rtt_values[i]) for i in spike_indices]

# ==================== Print results ====================
print("\n=== Socks5 RTT Analysis (Preheat Ignored) ===")
print(f"Total Requests      : {len(rtt_values):,}")
print(f"Average RTT         : {avg_rtt:.2f} ms")
print(f"Median RTT          : {median_rtt:.2f} ms")
print(f"Min / Max RTT       : {min_rtt:.2f} – {max_rtt:.2f} ms")
print(f"Std Deviation       : {stddev_rtt:.2f} ms")
print(f"95th Percentile     : {p95:.2f} ms")
print(f"Spike Threshold     : {threshold:.2f} ms")
print(f"Detected Spikes     : {len(spike_requests):,}")

if spike_requests:
    print("\nFirst 10 spikes (request #, RTT):")
    for req, rtt in spike_requests[:10]:
        print(f"  #{req:6d}  {rtt:6.2f} ms")

# ==================== Plotting ====================
if len(rtt_values) <= MAX_PLOT_POINTS:
    # Small dataset → plot everything
    plot_times = np.array(timestamps)
    plot_rtts = np.array(rtt_values)
    plot_reqs = np.array(request_numbers)
else:
    # Downsample to MAX_PLOT_POINTS points
    print(f"Downsampling plot to ~{MAX_PLOT_POINTS:,} points...")
    indices = np.linspace(0, len(rtt_values) - 1, MAX_PLOT_POINTS, dtype=int)
    plot_times = np.array(timestamps)[indices]
    plot_rtts = np.array(rtt_values)[indices]
    plot_reqs = np.array(request_numbers)[indices]

# Colors
colors = np.array(["red" if r > threshold else "blue" for r in plot_rtts])

plt.figure(figsize=(14, 6))

# Main scatter
sc = plt.scatter(plot_reqs, plot_rtts, c=colors, s=16, alpha=0.7, edgecolors="none")

# Optional: highlight spikes more clearly
if spike_indices:
    spike_plot_indices = [
        i
        for i in range(len(plot_reqs))
        if plot_reqs[i] in [request_numbers[j] for j in spike_indices]
    ]
    if spike_plot_indices:
        plt.scatter(
            plot_reqs[spike_plot_indices],
            plot_rtts[spike_plot_indices],
            c="red",
            s=40,
            marker="x",
            label="Spike",
            zorder=10,
        )

# Reference lines
plt.axhline(
    avg_rtt,
    color="green",
    linestyle="--",
    linewidth=1.5,
    label=f"Avg = {avg_rtt:.2f} ms",
)
plt.axhline(
    threshold,
    color="orange",
    linestyle="--",
    linewidth=1.5,
    label=f"Spike threshold = {threshold:.2f} ms",
)

plt.xlabel("Request number")
plt.ylabel("RTT (ms)")
plt.title(f"Socks5 RTT - {LOG_FILE}\n(Preheat ignored • {len(rtt_values):,} requests)")
plt.grid(True, linestyle="--", alpha=0.4)
plt.legend()

# Optional: secondary x-axis with real time
if len(timestamps) > 10:
    try:
        first_ts = datetime.fromtimestamp(timestamps[0])
        last_ts = datetime.fromtimestamp(timestamps[-1])

        def format_func(x, pos):
            # x is request number → approximate time
            frac = x / len(rtt_values)
            ts = first_ts + (last_ts - first_ts) * frac
            return ts.strftime("%H:%M:%S")

        sec_ax = plt.secondary_xaxis("top", functions=(lambda x: x, lambda x: x))
        sec_ax.set_xlabel("Approximate time")
        sec_ax.set_xticks(plt.xticks()[0])
        sec_ax.xaxis.set_major_formatter(plt.FuncFormatter(format_func))
    except:
        pass  # fallback to only request number

plt.tight_layout()
plt.show()
