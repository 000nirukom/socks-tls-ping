from math import log
import re
import argparse
from datetime import datetime
from pathlib import Path
import statistics

import numpy as np
import fastplotlib as fpl

parser = argparse.ArgumentParser()
parser.add_argument("logfile", help="Path to the log file")
parser.add_argument("--pixel-font",
                    action="store_true",
                    help="Use fusion pixel font")
args = parser.parse_args()

# TODO: also set font for imgui
if args.pixel_font:
    from pygfx.utils.text import font_manager, FontProps

    font = font_manager.add_font_file(
        "fonts/fusion-pixel-12px-proportional-zh_hans.ttf")
    font_manager._default_font_props = FontProps(
        font.family,
        style="normal",
        weight="regular",
    )

LOG_FILE = Path(args.logfile)
log_name = LOG_FILE.stem.split("_")[0]

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
                dt_str, "%Y-%m-%d %H:%M:%S")  # ← adjust format if needed!
        except ValueError:
            continue

        rtt = float(match.group(2))

        rtt_list.append((dt, rtt))

rtt_dt = [dt for dt, _ in rtt_list]

base_ts = rtt_dt[0].timestamp()
rtt_tsdiff: list[float] = [dt.timestamp() - base_ts for dt in rtt_dt]

min_tsdiff = rtt_tsdiff[0]
max_tsdiff = rtt_tsdiff[-1]

rtt_values = [rtt for _, rtt in rtt_list]

avg_rtt = statistics.mean(rtt_values)
min_rtt = min(rtt_values)
max_rtt = max(rtt_values)
std_rtt = statistics.stdev(rtt_values) if len(rtt_values) >= 2 else 0

threshold = avg_rtt + 3 * std_rtt

colors = ["r" if rtt >= threshold else "#176f58" for rtt in rtt_values]
spike_rate = colors.count("r") / len(rtt_values) * 100

xs = rtt_tsdiff
# manual log-scale transformation for y values
log_base = 1.001
ys = [log(rtt, log_base) for rtt in rtt_values]

data = np.column_stack([xs, ys]).astype(np.float32)

figure = fpl.Figure(
    size=(700, 560),
    names=[log_name],
)

# add a scatter
scatter = figure[0, 0].add_scatter(
    data=data,
    sizes=5,
    colors=colors,
    edge_width=0,
)

# manual log-scale transformation for line values
avg_rtt_log = log(avg_rtt, log_base)
threshold_log = log(threshold, log_base)

min_dt = rtt_dt[0]
max_dt = rtt_dt[-1]
formatter = "%d %H:%M" if max_dt.day != min_dt.day else "%H:%M:%S"


def tick_format_x(
    sec: float,
    _min_sec: float,
    _max_sec: float,
) -> str:
    if not (min_tsdiff <= sec <= max_tsdiff):
        return "--"
    # workaround for date-time x tick labels
    return datetime.fromtimestamp(base_ts + sec).strftime(formatter)


min_rtt_log = min(ys)
max_rtt_log = max(ys)


def tick_format_y(rtt: float, _min, _max) -> str:
    # avoid too large number calculation
    if rtt > max_rtt_log:
        return "--"
    return f"{log_base**rtt:.2f}ms"


figure[0, 0].axes.x.tick_format = tick_format_x
figure[0, 0].axes.y.tick_format = tick_format_y

# disable maintain_aspect
figure[0, 0].camera.maintain_aspect = False

line_avg = figure[0, 0].add_line(
    data=np.array([(xs[0], avg_rtt_log), (xs[-1], avg_rtt_log)],
                  dtype=np.float32),
    colors="g",
)
line_thr = figure[0, 0].add_line(
    data=np.array([(xs[0], threshold_log), (xs[-1], threshold_log)],
                  dtype=np.float32),
    colors="y",
)


def tooltip_info(ev) -> str:
    # get index of the scatter point that is being hovered
    index: int = ev.pick_info["vertex_index"]
    date_time = rtt_dt[index]
    rtt = rtt_values[index]

    return f"""{rtt}ms
{date_time.strftime("%H:%M:%S")}"""


# Custom tooltips
figure.tooltip_manager.register(scatter, custom_info=tooltip_info)
figure.tooltip_manager.register(line_avg,
                                custom_info=lambda _: f"Avg: {avg_rtt:.2f}ms")
figure.tooltip_manager.register(
    line_thr,
    custom_info=lambda _: f"THR: {threshold:.2f}ms\nspike {spike_rate:.2f}%")

figure.show()

if __name__ == "__main__":
    fpl.loop.run()
