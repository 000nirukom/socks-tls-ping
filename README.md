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

## Draw chart

We have different image draw backend,

|               | matplotlib | pyecharts | fastplotlib |
| ------------: | :--------: | :-------: | :---------: |
|   Performance |  Not bad   |  Garbage  |    Best     |
| Interactivity |    Good    |   Good    |   Usable    |
| informativity |    Best    |  Not bad  |     WIP     |

For the interactivity, matplotlib provides tooltip with focused region view,
while pyecharts provides sliding time range selector.

### Screenshots

