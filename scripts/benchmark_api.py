#!/usr/bin/env python3
"""Simple concurrent benchmark for backend endpoints.

Usage examples:
  python scripts/benchmark_api.py --url http://127.0.0.1:8000/api/health
  python scripts/benchmark_api.py --url http://127.0.0.1:8000/api/chat/sources?user_id=test --concurrency 20 --requests 200
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import dataclass

import httpx


@dataclass
class Result:
    ok: bool
    status: int
    latency_ms: float
    error: str = ""


def percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


async def hit_once(client: httpx.AsyncClient, method: str, url: str, payload: dict | None, timeout: float) -> Result:
    start = time.perf_counter()
    try:
        if method == "GET":
            resp = await client.get(url, timeout=timeout)
        else:
            resp = await client.post(url, json=payload or {}, timeout=timeout)
        latency_ms = (time.perf_counter() - start) * 1000
        return Result(ok=resp.status_code < 400, status=resp.status_code, latency_ms=latency_ms)
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return Result(ok=False, status=0, latency_ms=latency_ms, error=str(exc))


async def run_benchmark(url: str, method: str, payload: dict | None, concurrency: int, requests: int, timeout: float) -> list[Result]:
    semaphore = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(max_connections=max(50, concurrency * 2), max_keepalive_connections=max(20, concurrency))

    async with httpx.AsyncClient(limits=limits) as client:
        async def worker() -> Result:
            async with semaphore:
                return await hit_once(client, method, url, payload, timeout)

        tasks = [asyncio.create_task(worker()) for _ in range(requests)]
        return await asyncio.gather(*tasks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Concurrent API benchmark")
    parser.add_argument("--url", required=True, help="Target URL")
    parser.add_argument("--method", default="GET", choices=["GET", "POST"], help="HTTP method")
    parser.add_argument("--payload", default="", help="JSON string for POST payload")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent in-flight requests")
    parser.add_argument("--requests", type=int, default=100, help="Total requests")
    parser.add_argument("--timeout", type=float, default=45.0, help="Per request timeout in seconds")
    args = parser.parse_args()

    payload = json.loads(args.payload) if args.payload else None

    started = time.perf_counter()
    results = asyncio.run(
        run_benchmark(
            url=args.url,
            method=args.method,
            payload=payload,
            concurrency=max(1, args.concurrency),
            requests=max(1, args.requests),
            timeout=max(1.0, args.timeout),
        )
    )
    total_seconds = max(0.001, time.perf_counter() - started)

    latencies = sorted([r.latency_ms for r in results])
    oks = [r for r in results if r.ok]
    errs = [r for r in results if not r.ok]

    print("=== Benchmark Result ===")
    print(f"URL: {args.url}")
    print(f"Method: {args.method}")
    print(f"Requests: {len(results)}")
    print(f"Concurrency: {args.concurrency}")
    print(f"Duration(s): {total_seconds:.2f}")
    print(f"Throughput(req/s): {len(results) / total_seconds:.2f}")
    print(f"Success: {len(oks)} | Errors: {len(errs)} | Error rate: {(len(errs) / len(results)) * 100:.2f}%")
    print(f"Latency p50(ms): {percentile(latencies, 0.50):.2f}")
    print(f"Latency p95(ms): {percentile(latencies, 0.95):.2f}")
    print(f"Latency p99(ms): {percentile(latencies, 0.99):.2f}")
    print(f"Latency avg(ms): {statistics.mean(latencies):.2f}")

    if errs:
        print("\nSample errors:")
        for item in errs[:5]:
            print(f"- status={item.status} latency_ms={item.latency_ms:.2f} error={item.error}")


if __name__ == "__main__":
    main()
