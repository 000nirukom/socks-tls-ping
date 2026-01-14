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

## Usage

```bash
uv run socks-tls-ping [SOCKS5_PORT] [LOG_PREFIX]
```

## Draw chart

We have different image draw backend,

|               | matplotlib | pyecharts |           fastplotlib           |
| ------------: | :--------: | :-------: | :-----------------------------: |
|   Performance |  Not bad   |  Garbage  |              Best               |
| Interactivity |    Good    |   Best    | Pretty good<br>Smooth rendering |
| Informativity |    Best    |  Not bad  |     Customizable with imgui     |

For the interactivity, matplotlib provides tooltip with focused region view,
while pyecharts also provides sliding time range selector.

### Matplotlib

<img width="1400" height="734" alt="image" src="https://github.com/user-attachments/assets/800c5ad5-2775-4b00-aa69-9171c010ad54" />

### Pyecharts

<img width="1209" height="614" alt="image" src="https://github.com/user-attachments/assets/61183c75-b793-4d8a-b4f3-da5c3f7d009c" />

### Fastplotlib

<img width="1920" height="1009" alt="image" src="https://github.com/user-attachments/assets/26593247-bf37-494b-abb3-abcf54e1a340" />

