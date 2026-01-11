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

---

## Main Features

### Long-running stable sampling

* Fixed interval probing (default: 0.5s)
* Fixed total runtime (default: 180 minutes)
* Uses monotonic clock for time control
* Each request records RTT or failure

### Automatic connection pool lifecycle

The client is automatically recreated in three situations:

* Startup prewarm: up to 3 attempts before entering test loop
* Periodic recreation: every `RECREATE_INTERVAL` seconds
* Failure-triggered recreation: after `MAX_CONSECUTIVE_ERRORS` consecutive failures

This prevents long-lived HTTP/2 or TCP sessions from silently degrading.

### Real-time statistics

* Keeps up to 200k recent RTT samples
* Continuously prints:

  * average
  * P50 / P90 / P99
* One-line live status update in terminal

### Logging and final report

* File log contains:

  * every request result
  * RTT
  * HTTP version
  * all errors and stack traces
  * connection pool rebuild events
* On exit (time limit or Ctrl+C), prints:

  * total samples
  * avg / P50 / P90 / P99
  * error distribution summary

---

## Usage

Run:

```bash
python socks_ping.py <socks_port> <log_name_prefix>
```

Example:

```bash
python socks_ping.py 60005 hk_test
```

This creates a log file like:

```text
hk_test_20260112_013045.log
```

Configuration is at the top of the script:

* `INTERVAL` — request interval
* `RUN_MINUTES` — total runtime
* `RECREATE_INTERVAL` — forced client rebuild period
* `MAX_CONSECUTIVE_ERRORS` — failure threshold
* `TARGET` — probe URL (default: Cloudflare trace endpoint)

---

## What is actually being measured

This is **not raw TCP RTT**.

Each sample includes:

> SOCKS handshake + TCP + TLS + HTTP + server processing + response headers

So the numbers represent **real application-level latency**, close to what browsers or real clients see.

Using Cloudflare as target also means:

* CDN routing may change
* Edge nodes may switch
* HTTP/2 sessions may migrate

This is intentional: the tool is meant to observe **real path behavior**, not a lab-grade ping.

## Design characteristics and limitations

* Single in-flight request, strictly sequential (not a throughput benchmark)
* Focused on quality and stability, not bandwidth or QPS
* Keeps RTT samples in memory (up to 200k entries)
* Result is highly dependent on the quality of:

  * SOCKS implementation
  * TCP/TLS stack
  * proxy chaining behavior

## Implementation overview

* On startup:

  * Create HTTP client
  * Perform up to 3 prewarm requests
* Main loop:

  * Send one HEAD request
  * Record RTT or error
  * Update statistics and live status line
  * Sleep to maintain fixed interval
* If:

  * Periodic timer expires → rebuild client
  * Consecutive failures exceed threshold → rebuild client
* On exit:

  * Print summary statistics
  * Print error distribution
  * Close client and flush logs
