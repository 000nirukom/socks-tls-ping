import re
import argparse
import statistics
from datetime import datetime, timedelta
from pathlib import Path

from pyecharts import options as opts
from pyecharts.charts import Scatter
from pyecharts.commons.utils import JsCode

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

rtt_dts = [dt for dt, _ in rtt_list]
rtt_values = [rtt for _, rtt in rtt_list]

avg_rtt = statistics.mean(rtt_values)
std_rtt = statistics.stdev(rtt_values) if len(rtt_values) >= 2 else 0
min_rtt = min(rtt_values)
max_rtt = max(rtt_values)

threshold = round(avg_rtt + 3 * std_rtt, 2)

first_time = min(rtt_dts)
hour_end = 100
for ui, dt in enumerate(rtt_dts):
    if dt >= first_time + timedelta(hours=1):
        hour_end = int(ui / len(rtt_dts) * 100)
        break

datazoom_opts = [
    opts.DataZoomOpts(
        type_="slider",
        is_show=True,
        xaxis_index=0,
        range_start=0,
        range_end=hour_end,
    )
]

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
    Scatter(
        init_opts=opts.InitOpts(width="1200px", height="600px"),
        render_opts=opts.RenderOpts(is_embed_js=False),
    )
    .add_xaxis(rtt_dts)
    .add_yaxis(
        series_name="RTT",
        y_axis=rtt_values,
        symbol_size=5,
    )
    .set_series_opts(
        label_opts=opts.LabelOpts(is_show=False),  # series data labels off
        markline_opts=opts.MarkLineOpts(
            data=[
                opts.MarkLineItem(
                    y=threshold,
                    name="THR",  # ← this becomes {name} in formatter
                ),
                opts.MarkLineItem(
                    y=avg_rtt,
                    name="AVG",
                ),
            ],
            linestyle_opts=opts.LineStyleOpts(
                width=2.5,
                type_="dashed",
                opacity=0.9,
                color="#5DBA58",
            ),
            label_opts=opts.LabelOpts(
                position="start",
                # Use {name} for different prefix, {c} for the y-value
                formatter=JsCode(
                    "(param) => `${param.name}: ${param.value.toFixed(2)} ms`"
                ),
                color="#000",  # or make dynamic if needed (harder)
                font_size=15,
                font_weight="bold",
                distance=10,
                vertical_align="middle",
                horizontal_align="right",
            ),
            symbol=["none", "none"],
        ),
    )
    .set_global_opts(
        title_opts=opts.TitleOpts(title=log_name),
        xaxis_opts=opts.AxisOpts(type_="time", name="Time"),
        yaxis_opts=opts.AxisOpts(
            type_="log",
            min_=round(min_rtt, 2),
            max_=round(max_rtt, 2),
            name="RTT (ms)",
        ),
        toolbox_opts=opts.ToolboxOpts(),
        datazoom_opts=datazoom_opts,
        visualmap_opts=visualmap_opts,
    )
)
filename = f"rtt_{log_name}.html"

html = chart.render_embed()

if ENABLE_WEBGL:
    html = html.replace(
        "</head>",
        """
    <script src="https://cdn.jsdelivr.net/npm/echarts-gl@2.0.9/dist/echarts-gl.min.js"></script>
    </head>""",
    )
    html = html.replace("scatter", "scatterGL")

with open(filename, "w", encoding="utf-8") as f:
    f.write(html)
