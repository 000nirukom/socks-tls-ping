# -*- coding: utf-8 -*-
from matplotlib.ticker import StrMethodFormatter
import re
import sys
from datetime import datetime

import matplotlib
import matplotlib.pyplot as plt
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
parser.add_argument(
    "--factor", type=float, default=98, help="Percentile factor to trim outliers"
)
parser.add_argument(
    "--bin-precision",
    type=int,
    default=5,
    help="Number of bins per ms (e.g., 5 means each bin is 0.2ms wide)",
)

args = parser.parse_args()

LOG_FILE = Path(args.logfile)
log_name = "_".join(LOG_FILE.stem.split("_")[:-2])

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

        rtt_list.append(rtt)

# ────────────────────────────────────────────────
#  Histogram: split into linear bins and plot
# ────────────────────────────────────────────────

rtts = np.array(rtt_list, dtype=float)

# 去除异常值
factor: float = args.factor

pfactor = np.percentile(rtts, factor)

rtts = rtts[(rtts <= pfactor)]

if len(rtts) == 0:
    print("No RTT data found!")
    sys.exit(1)

bin_nums = args.bin_precision * int((rtts.max() - rtts.min())) + 1
bin_edges = np.linspace(rtts.min(), rtts.max(), bin_nums)

# 统计每个区间的数量
hist, edges = np.histogram(rtts, bins=bin_edges)

# 计算每个 bin 的中心点，用于绘图
bin_centers = (edges[:-1] + edges[1:]) / 2
bin_width = edges[1] - edges[0]

# 开始画图
plt.figure(figsize=(12, 6))
plt.bar(bin_centers, hist, width=bin_width, align="center")

plt.xlabel("RTT (ms)")
plt.ylabel("Count")
plt.title(f"RTT Distribution Histogram (~p{factor}%)\n{log_name}")

ax: plt.Axes = plt.gca()
# x 轴不用科学计数法
ax.xaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))
ax.set_xlim(rtts.min() - bin_width, rtts.max() + bin_width)

plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
