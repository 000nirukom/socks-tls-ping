import os
from math import log
import re
import argparse
from datetime import datetime
from pathlib import Path
from importlib import resources
import statistics

import numpy as np
import fastplotlib as fpl
import pygfx
import imgui_bundle
from pygfx.utils.text import font_manager as gfx_font_manager, FontProps
from fastplotlib.layouts import ImguiFigure
from fastplotlib.ui import EdgeWindow
from imgui_bundle import imgui

parser = argparse.ArgumentParser()
parser.add_argument("logfile", help="Path to the log file")
parser.add_argument(
    "--pixel-font-canvas",
    action="store_true",
    help="Force to fusion pixel font for canvas",
)
parser.add_argument(
    "--pixel-font-imgui",
    action="store_true",
    help="Force to fusion pixel font for imgui",
)
parser.add_argument(
    "--ignore-fpl-font",
    action="store_true",
    help="Override fastplotlib default fonts, otherwise only font for missing characters fallback",
)
parser.add_argument(
    "--hide-distribution",
    action="store_true",
    help="Hide RTT distribution subplot",
)
parser.add_argument(
    "--distribution-precision",
    type=int,
    help="Number of bins per ms (e.g., 5 means each bin is 0.2ms wide)",
    default=2,
)
args = parser.parse_args()

LOG_FILE = Path(args.logfile)
log_name = "_".join(LOG_FILE.stem.split("_")[:-2])

show_distribution: bool = not args.hide_distribution
IGNORE_FPL_DEFAULT: bool = args.ignore_fpl_font
FORCE_PIXEL_GFX = args.pixel_font_canvas
FORCE_PIXEL_IMGUI = args.pixel_font_imgui

PIXEL_FONT_PATH = str(Path("fonts") / "fusion-pixel-12px-proportional-zh_hans.ttf")
system_fonts = []

match os.name:
    case "nt":
        system_fonts = [f"{os.getenv('SystemDrive') or 'C:'}/Windows/Fonts/msyh.ttc"]
    case "posix":
        import fontconfig  # type: ignore

        # make sure font contains needed characters
        font_match = fontconfig.match(
            pattern="".join(f":charset={ord(ch):X}" for ch in log_name)
            + ":weight=Regular",
            select=("family", "file"),
        )
        fontconfig.list()
        if font_match is not None:
            system_fonts = [font_match["file"]]

if FORCE_PIXEL_IMGUI:
    imgui_font_paths: list[str] = [PIXEL_FONT_PATH]
elif system_fonts:
    imgui_font_paths = system_fonts
else:
    print("Warning: using default font for Dear ImGui")
    imgui_font_paths = []

if FORCE_PIXEL_GFX:
    gfx_font_path: str = PIXEL_FONT_PATH
elif system_fonts:
    gfx_font_path = system_fonts[0]
else:
    print("Warning: using default font for PyGFX")
    gfx_font_path = None


print(f"""Fonts for canvas: 
{gfx_font_path}
""")

if gfx_font_path is not None:
    gfx_font = gfx_font_manager.add_font_file(font_file=gfx_font_path)
    gfx_font_manager._default_font_props = FontProps(
        gfx_font.family,
        style="normal",
        weight="regular",
    )

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

figure: ImguiFigure = fpl.Figure(
    size=(700, 560),
    shape=(2, 1) if show_distribution else (1, 1),
    names=["RTT Distribution", log_name] if show_distribution else [log_name],
)

if imgui_font_paths:
    imgui.set_current_context(figure._imgui_renderer.imgui_context)

    imgui_io = imgui.get_io()

    if IGNORE_FPL_DEFAULT:
        imgui_io.fonts.clear()

    # Workaround for PUA icon font
    with resources.as_file(
        resources.files(imgui_bundle)
        / "assets"
        / "fonts"
        / "Font_Awesome_6_Free-Solid-900.otf"
    ) as icon_font_path:
        if IGNORE_FPL_DEFAULT:
            imgui_font_paths.append(str(icon_font_path))

        print("Fonts for imgui:")

        for i, font_path in enumerate(imgui_font_paths):
            font_config = imgui.ImFontConfig()

            if IGNORE_FPL_DEFAULT:
                font_config.merge_mode = i > 0
            else:
                font_config.merge_mode = True

            imgui_font = imgui_io.fonts.add_font_from_file_ttf(
                font_path,
                14.0,
                font_config,
            )
            print(font_path)

    imgui.push_font(
        imgui_font,
        imgui_font.legacy_size,
    )

scatter_idx = 0 if not show_distribution else 1, 0


# add a scatter
scatter = figure[scatter_idx].add_scatter(
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


figure[scatter_idx].axes.x.tick_format = tick_format_x
figure[scatter_idx].axes.y.tick_format = tick_format_y

# disable maintain_aspect
figure[scatter_idx].camera.maintain_aspect = False

avg_color = "#4caf50c0"
thr_color = "#fcff33c0"

line_avg = figure[scatter_idx].add_line(
    data=np.array([(xs[0], avg_rtt_log), (xs[-1], avg_rtt_log)], dtype=np.float32),
    colors=avg_color,
    thickness=2,
)
line_thr = figure[scatter_idx].add_line(
    data=np.array([(xs[0], threshold_log), (xs[-1], threshold_log)], dtype=np.float32),
    colors=thr_color,
    thickness=2,
)


def tooltip_info(ev: pygfx.PointerEvent) -> str:
    # get index of the scatter point that is being hovered
    index: int = ev.pick_info["vertex_index"]
    date_time = rtt_dt[index]
    rtt = rtt_values[index]

    return f"""{rtt}ms
{date_time.strftime("%H:%M:%S")}"""


# Custom tooltips
figure.tooltip_manager.register(scatter, custom_info=tooltip_info)
figure.tooltip_manager.register(line_avg, custom_info=lambda _: f"Avg: {avg_rtt:.2f}ms")
figure.tooltip_manager.register(
    line_thr, custom_info=lambda _: f"THR: {threshold:.2f}ms\nspike {spike_rate:.2f}%"
)

rtt_values = np.array(rtt_values, dtype=float)

p90 = np.percentile(rtt_values, 90)
p95 = np.percentile(rtt_values, 95)
p98 = np.percentile(rtt_values, 98)
p99 = np.percentile(rtt_values, 99)

p90_color = "#ff5722c0"
p95_color = "#e91e63c0"
p98_color = "#9c27b0c0"
p99_color = "#673ab7c0"


class RTTInfo(EdgeWindow):
    @staticmethod
    def _colorhex_to_rgba(color_hex: str) -> tuple[float, float, float, float]:
        color_hex = color_hex.strip("#")
        if len(color_hex) == 6:
            color_hex += "FF"
        return tuple(
            int(color_hex[i : i + 2], base=16) / 255.0
            for i in range(0, len(color_hex), 2)
        )

    def update(self):
        # Your ImGui calls go here
        imgui.begin("RTT")

        imgui.text_colored(
            self._colorhex_to_rgba(avg_color),
            f"Avg: {avg_rtt:.2f}ms",
        )

        imgui.text_colored(
            self._colorhex_to_rgba(thr_color),
            f"Avg+3σ: {threshold:.2f}ms",
        )

        if show_distribution:
            imgui.text_colored(
                self._colorhex_to_rgba(p90_color),
                f"P90: {p90:.2f}ms",
            )
            imgui.text_colored(
                self._colorhex_to_rgba(p95_color),
                f"P95: {p95:.2f}ms",
            )
            imgui.text_colored(
                self._colorhex_to_rgba(p98_color),
                f"P98: {p98:.2f}ms",
            )
            imgui.text_colored(
                self._colorhex_to_rgba(p99_color),
                f"P99: {p99:.2f}ms",
            )

        imgui.end()


figure.add_gui(
    RTTInfo(
        figure=figure,
        size=0,
        location="right",
        title="_",
        window_flags=imgui.WindowFlags_.always_auto_resize,
    )
)


def draw_distribution():
    distribution_precision: int = args.distribution_precision
    dist_idx = 0, 0

    # filter out 0.5% extreme values for better distribution display
    factor: float = 99.5
    pfactor = np.percentile(rtt_values, factor)
    filtered_rtts = rtt_values[(rtt_values <= pfactor)]

    # calculate bin number using filtered
    bin = distribution_precision * int((filtered_rtts.max() - filtered_rtts.min())) + 1
    # 统计每个区间的数量
    hist, bin_edges = np.histogram(filtered_rtts, bins=bin)
    hist = hist / hist.max() * 100  # normalize to 100 for better display

    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    distribution = figure[dist_idx].add_scatter(
        data=np.column_stack(
            [
                bin_centers,
                hist,
            ]
        ).astype(np.float32),
        sizes=5,
        colors=["#2196f3" if h else "#ffffff00" for h in hist],
        edge_width=0,
    )

    # disable maintain_aspect
    figure[dist_idx].camera.maintain_aspect = False

    line_p90 = figure[dist_idx].add_line(
        data=np.array(
            [
                (p90, 0),
                (p90, hist.max()),
            ],
            dtype=np.float32,
        ),
        colors=p90_color,
        thickness=2,
    )
    line_p95 = figure[dist_idx].add_line(
        data=np.array(
            [
                (p95, 0),
                (p95, hist.max()),
            ],
            dtype=np.float32,
        ),
        colors=p95_color,
        thickness=2,
    )
    line_p98 = figure[dist_idx].add_line(
        data=np.array(
            [
                (p98, 0),
                (p98, hist.max()),
            ],
            dtype=np.float32,
        ),
        colors=p98_color,
        thickness=2,
    )
    line_p99 = figure[dist_idx].add_line(
        data=np.array(
            [
                (p99, 0),
                (p99, hist.max()),
            ],
            dtype=np.float32,
        ),
        colors=p99_color,
        thickness=2,
    )

    def tooltip_dist_info(ev: pygfx.PointerEvent) -> str:
        index: int = ev.pick_info["vertex_index"]
        rtt = bin_centers[index]

        return f"""RTT: {rtt:.2f}ms"""

    figure.tooltip_manager.register(
        distribution,
        custom_info=tooltip_dist_info,
    )
    figure.tooltip_manager.register(
        line_p90,
        custom_info=lambda _: f"P90: {p90:.2f}ms",
    )
    figure.tooltip_manager.register(
        line_p95,
        custom_info=lambda _: f"P95: {p95:.2f}ms",
    )
    figure.tooltip_manager.register(
        line_p98,
        custom_info=lambda _: f"P98: {p98:.2f}ms",
    )
    figure.tooltip_manager.register(
        line_p99,
        custom_info=lambda _: f"P99: {p99:.2f}ms",
    )


# add a scatter chart for distribution
if show_distribution:
    draw_distribution()

figure.show()

if __name__ == "__main__":
    fpl.loop.run()
