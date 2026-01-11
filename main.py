# -*- coding: utf-8 -*-
import asyncio
import time
import sys
import logging
import traceback
from datetime import datetime
from collections import Counter, deque
import httpx
from httpx import AsyncClient, Limits, AsyncHTTPTransport
import numpy as np

# ================== 配置 ==================
PROXY = "socks5://127.0.0.1:" + (sys.argv[1] if len(sys.argv) > 1 else exit(1))
TARGET = "https://www.cloudflare.com/cdn-cgi/trace"
INTERVAL = 1.0  # 请求间隔（秒）
RUN_MINUTES = 60  # 总运行分钟数
TIMEOUT = httpx.Timeout(10.0, connect=5.0, read=8.0)
RECREATE_INTERVAL = 5 * 60  # 强制重建连接池间隔（秒）
MAX_CONSECUTIVE_ERRORS = 4  # 连续失败多少次才重建

# ================== 日志设置 ==================
logger = logging.getLogger("SocksPing")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(
    f"socks_ping_detailed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
    encoding="utf-8",
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s",
        "%Y-%m-%d %H:%M:%S.%f"[:-3],
    )
)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s", "%Y-%m-%d %H:%M:%S"
    )
)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ================== 统计 ==================
rtt_samples = deque(maxlen=5000)
error_counter = Counter()
total_count = 0
success_count = 0
consecutive_errors = 0
client: AsyncClient = None
last_recreate = time.time()
request_seq = 0


# ================== 功能函数 ==================
async def recreate_client(reason=""):
    """重建 HTTPX AsyncClient 并预热连接"""
    global client, last_recreate
    logger.info(
        f"连接池重建 | 原因: {reason} | 上次重建距今: {(time.time() - last_recreate):.0f}s"
    )

    if client is not None:
        try:
            await client.aclose()
            logger.debug("旧客户端已关闭")
        except Exception as e:
            logger.warning(f"关闭旧客户端失败: {e}")

    limits = Limits(
        max_connections=50,
        max_keepalive_connections=30,
        keepalive_expiry=120.0,
    )

    transport = AsyncHTTPTransport(
        proxy=PROXY,
        retries=1,
        http2=True,
    )

    client = AsyncClient(
        transport=transport,
        limits=limits,
        http2=True,
        follow_redirects=False,
    )

    last_recreate = time.time()
    logger.debug(f"新客户端创建完成 | limits: {limits}")

    # 预热（尝试3次，成功即退出）
    for attempt in range(1, 4):
        try:
            start = time.perf_counter_ns()
            resp = await client.head(TARGET, timeout=TIMEOUT)
            cost_ms = (time.perf_counter_ns() - start) / 1e6
            logger.info(
                f"[预热 成功] 第{attempt}次 | RTT: {cost_ms:.1f}ms | "
                f"HTTP/{resp.http_version} | 状态: {resp.status_code}"
            )
            print(f"[预热] 第{attempt}次成功，RTT: {cost_ms:.1f} ms")
            return True
        except Exception as e:
            logger.warning(f"[预热失败 第{attempt}次] {type(e).__name__}: {e}")
            await asyncio.sleep(0.5)

    logger.error("预热连续3次失败！后续测试可能极不稳定")
    print("警告：预热失败，连接可能存在严重问题")
    return False


def print_status(final=False):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not rtt_samples:
        rtt_text = "无样本"
    else:
        times_ms = np.array([t * 1000 for t in rtt_samples])
        avg = times_ms.mean()
        p50 = np.percentile(times_ms, 50)
        p90 = np.percentile(times_ms, 90)
        p99 = np.percentile(times_ms, 99)
        rtt_text = f"avg:{avg:6.2f} P50:{p50:6.2f} P90:{p90:6.2f} P99:{p99:6.2f} ms"

    status = (
        f"[{now}] "
        f"#{request_seq:4d} "
        f"总:{total_count:5d} "
        f"成功:{success_count:5d} "
        f"RTT: {rtt_text} "
        f"连续Err:{consecutive_errors}"
    )

    if final:
        print("\n" + "═" * 100)
        print(status)
        print("═" * 100)
    else:
        sys.stdout.write("\r" + status.ljust(140))
        sys.stdout.flush()


async def do_request():
    """执行一次请求，返回是否算作「成功」"""
    global total_count, success_count, consecutive_errors, request_seq
    request_seq += 1
    total_count += 1

    # 定时重建
    if time.time() - last_recreate >= RECREATE_INTERVAL:
        await recreate_client(f"定时重建（{RECREATE_INTERVAL // 60}分钟）")

    logger.debug(
        f"请求 #{request_seq} 开始 | 距上次重建: {(time.time() - last_recreate):.0f}s"
    )

    success = False
    try:
        start = time.perf_counter_ns()
        resp = await client.head(TARGET, timeout=TIMEOUT)
        cost_ns = time.perf_counter_ns() - start
        cost = cost_ns / 1e9

        if resp.status_code == 200:
            success = True
            success_count += 1
            rtt_samples.append(cost)
            logger.debug(
                f"请求 #{request_seq} 成功 | RTT: {cost * 1000:.2f}ms | "
                f"HTTP/{resp.http_version}"
            )
        else:
            error_counter[f"HTTP_{resp.status_code}"] += 1
            logger.warning(f"请求 #{request_seq} 非200 | 状态码: {resp.status_code}")

    except Exception as e:
        error_counter[type(e).__name__] += 1
        logger.warning(
            f"请求 #{request_seq} 异常 | 类型: {type(e).__name__} | 错误: {str(e)}"
        )
        if consecutive_errors >= 1:  # 从第二次异常开始打印堆栈
            logger.debug(traceback.format_exc())

    # 连续错误判断
    if success:
        consecutive_errors = 0
    else:
        consecutive_errors += 1
        if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            await recreate_client(f"连续 {consecutive_errors} 次失败触发重建")
            consecutive_errors = 0  # 重置计数

    print_status()
    return success


async def run_loop(start_time):
    """主循环，方便被取消"""
    while time.time() - start_time < RUN_MINUTES * 60:
        await do_request()
        await asyncio.sleep(INTERVAL)


async def main():
    global client
    logger.info("=" * 70)
    logger.info("Socks5 连接质量详细压测程序 v2（修复 Ctrl+C 版）")
    logger.info(f"代理: {PROXY}")
    logger.info(f"目标: {TARGET}")
    logger.info(f"运行时长: {RUN_MINUTES} 分钟")
    logger.info(f"请求间隔: {INTERVAL}s")
    logger.info(f"强制重建周期: {RECREATE_INTERVAL // 60} 分钟")
    logger.info(f"连续错误阈值: {MAX_CONSECUTIVE_ERRORS} 次")
    logger.info("=" * 70)

    print("\n正在初始化连接池并预热...")
    prewarm_ok = await recreate_client("程序初始启动")

    if not prewarm_ok:
        print("\n预热失败，仍然继续测试？(y/n): ", end="")
        if input().strip().lower() not in ("y", "yes", ""):
            print("测试中止")
            return

    print("\n开始正式测试... 详细日志已记录到文件")
    print("按 Ctrl+C 可随时结束\n")
    print("-" * 100)

    start_time = time.time()
    loop_task = asyncio.create_task(run_loop(start_time))

    try:
        await loop_task
    except KeyboardInterrupt:
        logger.info("用户手动中断测试")
        print("\n\n用户中断测试")
        loop_task.cancel()
        try:
            await loop_task
        except asyncio.CancelledError:
            pass
    except asyncio.CancelledError:
        pass
    finally:
        print_status(final=True)
        print("\n" + "═" * 100)
        print("最终统计汇总（更多详情见日志文件）:")

        if rtt_samples:
            times = np.array([t * 1000 for t in rtt_samples])
            print(f" 有效样本数: {len(times):,d}")
            print(f" 平均RTT: {times.mean():.2f} ms")
            print(f" 中位数(P50): {np.percentile(times, 50):.2f} ms")
            print(f" P90: {np.percentile(times, 90):.2f} ms")
            print(f" P99: {np.percentile(times, 99):.2f} ms")

        print("\n错误分布（Top8）：")
        for k, v in error_counter.most_common(8):
            print(f" {k:20} : {v}")

        print("═" * 100)

        if client:
            await client.aclose()

        logger.info("测试结束 | 日志文件已保存")
        logger.info("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序已通过外部 KeyboardInterrupt 退出")
