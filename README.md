# Socks5 Long-Run RTT & Stability Probe

> To test other provider nodes, you can use [singbox-dae-bridge](https://github.com/MeowKatee/singbox-dae-bridge) to generate a local loopback SOCKS5 inbound that forwards traffic to any real outbound protocol.

A **long-running, low-frequency RTT and stability probe** for SOCKS5 proxies, built with `asyncio` and `httpx`.

It is designed to observe **real-world latency distribution, jitter, tail latency and failure behavior over hours**, rather than peak throughput.

It continuously sends HTTP HEAD requests through a SOCKS5 proxy and records:

* End-to-end RTT (SOCKS + TCP + TLS + HTTP + server)
* Success / failure statistics
* Long-term percentile behavior (P50 / P90 / P99)
* Connection degradation and recovery behavior

Typical use cases:

* Compare different nodes / routes / entrances
* Detect long-lived connection degradation
* Observe jitter, tail latency and instability over time
* Verify whether a proxy or chain is suitable for latency-sensitive traffic

## Installation

```bash
uv sync # only for network requests

# matplotlib, fastplotlib, pyecharts
uv sync --extra [plot_backend] # plot chart for quick analysis
```

[fpl-rectangle-selector]: https://www.fastplotlib.org/ver/dev/_gallery/selection_tools/rectangle_selector.html

|                     | matplotlib | pyecharts |                fastplotlib                |
| ------------------: | :--------: | :-------: | :---------------------------------------: |
|       Ranged slider |     --     |    Yes    |                    --                     |
| Rectangle selection |    Yes     |    Yes    | [Partial support][fpl-rectangle-selector] |
|            Tooltips |     --     |    Yes    |                    Yes                    |
|         Drag to pan |    Slow    |    --     |                   Great                   |
|         Export HTML |     --     |    Yes    |                    --                     |
|        Export image |    Yes     |    Yes    |                    --                     |

### Render performance

The performance of matplotlib depends on the use case. It is relatively slower than pyecharts when plotting a subregion, but can be faster when rendering the full dataset.

For pyecharts, performance is more consistent with large datasets, particularly when interacting with subregions of the data.

In any case, fastplotlib can render plots in real time, making it the best choice for interactive use, whether working with the full chart or a subregion.

## Usage

```bash
uv run socks-tls-ping [SOCKS5_PORT] [LOG_PREFIX]
```

### Matplotlib

<img width="1400" height="734" alt="image" src="https://github.com/user-attachments/assets/800c5ad5-2775-4b00-aa69-9171c010ad54" />

### Pyecharts

<img width="1209" height="614" alt="image" src="https://github.com/user-attachments/assets/61183c75-b793-4d8a-b4f3-da5c3f7d009c" />

### Fastplotlib

> For fastplotlib, the interaction model is similar to matplotlib:
>
> * Left-click and drag to pan the view.
> * Right-click and drag to scale along the x or y axis.
> * Use the mouse wheel to zoom while preserving the current aspect ratio.

<img width="1918" height="968" alt="image" src="https://github.com/user-attachments/assets/a5657d77-219f-422a-938f-9708c0e6d128" />

