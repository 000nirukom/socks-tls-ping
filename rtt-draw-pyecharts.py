import re
import argparse
import statistics
from datetime import datetime

from pyecharts import options as opts
from pyecharts.charts import Scatter

parser = argparse.ArgumentParser()
parser.add_argument("logfile", help="Path to the log file")
args = parser.parse_args()

LOG_FILE = args.logfile


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

rtt_dts = [dt for dt, _ in rtt_list]
rtt_values = [rtt for _, rtt in rtt_list]

avg_rtt = statistics.mean(rtt_values)
std_rtt = statistics.stdev(rtt_values) if len(rtt_values) >= 2 else 0
max_rtt = max(rtt_values)

threshold = round(avg_rtt + 3 * std_rtt, 2)

visualmap_opts = opts.VisualMapOpts(
    type_="piecewise",
    is_piecewise=True,
    pieces=[
        # 小于等于 threshold：渐变区
        {
            "min": 0,
            "max": threshold,
            "label": f"≤ {threshold} ms",
            "color": None,  # 关键：让它走 inRange 渐变
        },
        # 大于 threshold：纯红色
        {
            "min": threshold,
            "max": max_rtt,
            "label": f"> {threshold} ms",
            "color": "red",
        },
    ],
    range_color=["#7CFC00", "#FFA500"],  # 浅绿 → 橙色
)

chart = (
    Scatter(init_opts=opts.InitOpts(width="1200px", height="600px"))
    .add_xaxis(rtt_dts)
    .add_yaxis(
        series_name="RTT",
        y_axis=rtt_values,
        symbol_size=5,
    )
    .set_series_opts(label_opts=opts.LabelOpts(is_show=False))
    .set_global_opts(
        title_opts=opts.TitleOpts(title="RTT Scatter Plot"),
        xaxis_opts=opts.AxisOpts(type_="time", name="Time"),
        yaxis_opts=opts.AxisOpts(type_="value", name="RTT (ms)"),
        toolbox_opts=opts.ToolboxOpts(),
        datazoom_opts=[opts.DataZoomOpts()],
        visualmap_opts=visualmap_opts,
    )
)
chart.render("rtt_scatter_plot.html")
