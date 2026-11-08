#!/usr/bin/env python3
"""Platform Performance Benchmark: Measures concurrency, throughput, and overhead.

Executes concurrent workflow requests against the Orchestrator service using MockLLM
with near-zero latency to measure platform-only framework overhead (LangGraph, Pydantic,
SQLite checkpointer, tool dispatch, HTTP). Saves real measured metrics to benchmarks/results.json.
"""

import argparse
import asyncio
import json
import logging
import platform
import time
from pathlib import Path
from typing import Any, Dict, List
import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent


def get_system_hardware_info() -> Dict[str, Any]:
    """Capture host system hardware profile for benchmark reproducibility."""
    info = {
        "os": f"{platform.system()} {platform.release()}",
        "architecture": platform.machine(),
        "processor": platform.processor() or "x86_64",
        "python_version": platform.python_version(),
    }
    try:
        import psutil

        info["cpu_physical_cores"] = psutil.cpu_count(logical=False)
        info["cpu_logical_cores"] = psutil.cpu_count(logical=True)
        info["total_ram_gb"] = round(psutil.virtual_memory().total / (1024**3), 2)
    except ImportError:
        pass
    return info


async def execute_single_request(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    url: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute a single workflow run request under concurrency semaphore."""
    async with semaphore:
        t0 = time.perf_counter()
        try:
            resp = await client.post(f"{url.rstrip('/')}/runs", json=payload, timeout=30.0)
            latency_ms = (time.perf_counter() - t0) * 1000
            success = resp.status_code == 201
            return {
                "success": success,
                "status_code": resp.status_code,
                "latency_ms": latency_ms,
                "error": None if success else resp.text[:100],
            }
        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000
            return {
                "success": False,
                "status_code": 0,
                "latency_ms": latency_ms,
                "error": str(exc)[:100],
            }


async def run_benchmark(
    base_url: str,
    total_requests: int,
    concurrency: int,
    pack_name: str,
    output_file: Path,
) -> Dict[str, Any]:
    """Run concurrent load test and calculate latency percentiles and throughput."""
    print("=" * 70)
    print(" ENTERPRISE AGENT PLATFORM - PERFORMANCE BENCHMARK")
    print(f" Target URL:        {base_url}")
    print(f" Domain Pack:       {pack_name}")
    print(f" Total Requests:    {total_requests}")
    print(f" Concurrency Level: {concurrency}")
    print("=" * 70)

    # Health pre-check
    async with httpx.AsyncClient() as pre_client:
        try:
            health_resp = await pre_client.get(f"{base_url.rstrip('/')}/health", timeout=5.0)
            if health_resp.status_code != 200:
                raise RuntimeError(f"Service returned unhealthy status {health_resp.status_code}")
        except Exception as e:
            print(f"\nERROR: Could not contact orchestrator service at {base_url}: {e}")
            print("Please ensure the orchestrator service is running before executing benchmark.")
            raise

    sample_payload = {
        "pack_name": pack_name,
        "input_data": {
            "ticket_id": "INC-BENCH-01",
            "issue": "Cannot connect to VPN from remote workstation",
            "user": "benchmark@company.com",
        },
        "session_id": "bench-session-fixed",
    }

    semaphore = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(max_connections=concurrency + 10, max_keepalive_connections=concurrency)

    print(f"\nWarming up and dispatching {total_requests} requests...")
    bench_start = time.perf_counter()

    async with httpx.AsyncClient(limits=limits) as client:
        tasks = [
            execute_single_request(client, semaphore, base_url, sample_payload)
            for _ in range(total_requests)
        ]
        results: List[Dict[str, Any]] = await asyncio.gather(*tasks)

    bench_total_duration = time.perf_counter() - bench_start

    # Metrics calculation
    latencies = sorted([r["latency_ms"] for r in results])
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    def percentile(p: float, values: List[float]) -> float:
        if not values:
            return 0.0
        idx = int(len(values) * (p / 100.0))
        return round(values[min(idx, len(values) - 1)], 2)

    p50 = percentile(50.0, latencies)
    p95 = percentile(95.0, latencies)
    p99 = percentile(99.0, latencies)
    pmin = round(latencies[0], 2) if latencies else 0.0
    pmax = round(latencies[-1], 2) if latencies else 0.0
    pmean = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    throughput = round(total_requests / bench_total_duration, 2)
    error_rate = round((len(failed) / total_requests) * 100, 2)

    hardware = get_system_hardware_info()

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hardware": hardware,
        "configuration": {
            "total_requests": total_requests,
            "concurrency": concurrency,
            "domain_pack": pack_name,
            "llm_provider": "MockLLM (near-zero latency platform overhead test)",
            "excludes_real_llm_latency": True,
        },
        "metrics": {
            "total_requests": total_requests,
            "successful_requests": len(successful),
            "failed_requests": len(failed),
            "error_rate_percent": error_rate,
            "total_duration_seconds": round(bench_total_duration, 3),
            "throughput_req_per_sec": throughput,
            "latency_ms": {
                "min": pmin,
                "mean": pmean,
                "p50": p50,
                "p95": p95,
                "p99": p99,
                "max": pmax,
            },
        },
    }

    print("\n" + "=" * 70)
    print(" BENCHMARK RESULTS")
    print("=" * 70)
    print(f" Hardware:           {hardware.get('processor')} ({hardware.get('os')})")
    print(f" Requests Completed: {len(successful)}/{total_requests} (Errors: {len(failed)}, {error_rate}%)")
    print(f" Total Duration:     {bench_total_duration:.2f}s")
    print(f" Throughput:         {throughput} requests/sec")
    print(f" Latency Min:        {pmin} ms")
    print(f" Latency Mean:       {pmean} ms")
    print(f" Latency p50:        {p50} ms")
    print(f" Latency p95:        {p95} ms")
    print(f" Latency p99:        {p99} ms")
    print(f" Latency Max:        {pmax} ms")
    print("=" * 70)
    print(" NOTE: This benchmark measures pure platform execution overhead")
    print(" (LangGraph scheduling, Pydantic validation, SQLite checkpointer,")
    print(" tool execution, HTTP) using MockLLM. Excludes external LLM API latency.")
    print("=" * 70)

    # Save to json
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved benchmark metrics to: {output_file}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Enterprise Agent Platform Benchmark")
    parser.add_argument("--url", default="http://localhost:8000", help="Orchestrator URL")
    parser.add_argument("--requests", type=int, default=200, help="Total requests")
    parser.add_argument("--concurrency", type=int, default=20, help="Concurrent workers")
    parser.add_argument("--pack", default="it_ticket_triage", help="Domain pack name")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "benchmarks" / "results.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    asyncio.run(
        run_benchmark(
            base_url=args.url,
            total_requests=args.requests,
            concurrency=args.concurrency,
            pack_name=args.pack,
            output_file=args.output,
        )
    )


if __name__ == "__main__":
    main()
