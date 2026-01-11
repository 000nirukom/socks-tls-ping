# -*- coding: utf-8 -*-
import re
import statistics
import matplotlib.pyplot as plt
import sys

# Log file path
LOG_FILE = sys.argv[1] if len(sys.argv) > 1 else exit(1)

# Spike threshold factor
SPIKE_THRESHOLD_FACTOR = 3

# Parse RTT from log
rtt_list = []

# Only match normal requests, ignore "preheat" lines
pattern = re.compile(r"请求 #(\d+) 成功 \| RTT: ([\d.]+)ms")

with open(LOG_FILE, "r", encoding="utf-8") as f:
    for line in f:
        if "[预热 成功]" in line:
            continue  # skip preheat requests
        date_time = line.strip().split(" | ")[0]
        match = pattern.search(line)
        if match:
            req_num = int(match.group(1))
            rtt = float(match.group(2))
            rtt_list.append((date_time, rtt))

# Extract RTT values
rtt_values = [rtt for _, rtt in rtt_list]

# Statistics
avg_rtt = statistics.mean(rtt_values)
max_rtt = max(rtt_values)
min_rtt = min(rtt_values)
median_rtt = statistics.median(rtt_values)
stddev_rtt = statistics.stdev(rtt_values)
percentile_95 = sorted(rtt_values)[int(len(rtt_values) * 0.95) - 1]

# Spike detection
threshold = avg_rtt + SPIKE_THRESHOLD_FACTOR * stddev_rtt
spike_requests = [(num, rtt) for num, rtt in rtt_list if rtt > threshold]

# Print results
print("=== Socks5 RTT Analysis (Preheat Ignored) ===")
print(f"Total Requests     : {len(rtt_values)}")
print(f"Average RTT        : {avg_rtt:.2f} ms")
print(f"Median RTT         : {median_rtt:.2f} ms")
print(f"Max RTT            : {max_rtt:.2f} ms")
print(f"Min RTT            : {min_rtt:.2f} ms")
print(f"Standard Deviation : {stddev_rtt:.2f} ms")
print(f"95th Percentile RTT: {percentile_95:.2f} ms")
print(f"Spike Threshold    : {threshold:.2f} ms")
print(f"Spike Requests     : {spike_requests}")

# ========== Scatter Plot ==========
plt.figure(figsize=(14, 6))

req_dts = [dt for dt, _ in rtt_list]
rtt_vals = [rtt for _, rtt in rtt_list]

# Colors: red for spike, blue for normal
colors = ["red" if rtt > threshold else "blue" for rtt in rtt_vals]

plt.scatter(req_dts, rtt_vals, c=colors, s=20, alpha=0.7, edgecolors="k", label="RTT")

# Draw average and spike threshold lines
plt.axhline(
    avg_rtt,
    color="green",
    linestyle="--",
    linewidth=2,
    label=f"Average RTT ({avg_rtt:.2f} ms)",
)
plt.axhline(
    threshold,
    color="orange",
    linestyle="--",
    linewidth=2,
    label=f"Spike Threshold ({threshold:.2f} ms)",
)

plt.xlabel("Request Number")
plt.ylabel("RTT (ms)")
plt.title(LOG_FILE)
plt.suptitle("Socks5 RTT Scatter Plot (Red = Spike, Preheat Ignored)")
plt.legend()
plt.grid(True, linestyle="--", alpha=0.5)
plt.tight_layout()
plt.show()
