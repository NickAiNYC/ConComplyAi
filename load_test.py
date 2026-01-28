"""Load Test - 100 concurrent sites, assert p95 < 5s"""
import asyncio
import time
import sys
from typing import List
import statistics

sys.path.insert(0, '/mnt/user-data/outputs/construction-compliance-ai/core')
from supervisor import run_compliance_check


async def process_site_async(site_id: str) -> float:
    """Process single site and return elapsed time"""
    start = time.time()
    loop = asyncio.get_event_loop()
    # Run sync function in executor
    await loop.run_in_executor(None, run_compliance_check, site_id)
    return time.time() - start


async def load_test(num_sites: int = 100) -> dict:
    """
    Spawn num_sites concurrent processing tasks
    Returns metrics including p95 latency
    """
    print(f"\n🚀 Starting load test with {num_sites} concurrent sites...")
    
    site_ids = [f"LOAD-{i:04d}" for i in range(num_sites)]
    
    start_time = time.time()
    
    # Process all sites concurrently
    latencies = await asyncio.gather(*[
        process_site_async(site_id) for site_id in site_ids
    ])
    
    total_time = time.time() - start_time
    
    # Calculate metrics
    metrics = {
        "total_sites": num_sites,
        "total_time": total_time,
        "avg_latency": statistics.mean(latencies),
        "p50_latency": statistics.median(latencies),
        "p95_latency": statistics.quantiles(latencies, n=20)[18],  # 95th percentile
        "p99_latency": statistics.quantiles(latencies, n=100)[98],
        "min_latency": min(latencies),
        "max_latency": max(latencies),
        "throughput_rps": num_sites / total_time
    }
    
    return metrics


def print_results(metrics: dict):
    """Pretty print load test results"""
    print("\n" + "="*60)
    print("LOAD TEST RESULTS")
    print("="*60)
    print(f"Total Sites:     {metrics['total_sites']}")
    print(f"Total Time:      {metrics['total_time']:.2f}s")
    print(f"Throughput:      {metrics['throughput_rps']:.2f} requests/sec")
    print(f"\nLatency Metrics:")
    print(f"  Min:           {metrics['min_latency']:.3f}s")
    print(f"  Avg:           {metrics['avg_latency']:.3f}s")
    print(f"  P50:           {metrics['p50_latency']:.3f}s")
    print(f"  P95:           {metrics['p95_latency']:.3f}s ⭐")
    print(f"  P99:           {metrics['p99_latency']:.3f}s")
    print(f"  Max:           {metrics['max_latency']:.3f}s")
    print("="*60)
    
    # Assert P95 < 5s
    if metrics['p95_latency'] < 5.0:
        print(f"✅ PASS: P95 latency {metrics['p95_latency']:.3f}s < 5s target")
    else:
        print(f"❌ FAIL: P95 latency {metrics['p95_latency']:.3f}s exceeds 5s target")
        sys.exit(1)


if __name__ == "__main__":
    # Run load test
    metrics = asyncio.run(load_test(100))
    print_results(metrics)
