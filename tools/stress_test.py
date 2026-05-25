"""
API 压力测试工具
用法: uv run python tools/stress_test.py [--concurrency 10] [--requests 100] [--endpoint all]
"""
import asyncio
import time
import statistics
import sys
import httpx
from dataclasses import dataclass, field

BASE_URL = "http://localhost:8081"

@dataclass
class Result:
    endpoint: str
    method: str
    total: int
    success: int
    errors: int
    times: list = field(default_factory=list)

    @property
    def qps(self) -> float:
        if not self.times:
            return 0
        total_time = max(self.times) - min(self.times)
        return self.total / total_time if total_time > 0 else self.total

    @property
    def avg_ms(self) -> float:
        return statistics.mean(self.times) * 1000 if self.times else 0

    @property
    def min_ms(self) -> float:
        return min(self.times) * 1000 if self.times else 0

    @property
    def max_ms(self) -> float:
        return max(self.times) * 1000 if self.times else 0

    @property
    def p50_ms(self) -> float:
        return self._percentile(50) * 1000

    @property
    def p95_ms(self) -> float:
        return self._percentile(95) * 1000

    @property
    def p99_ms(self) -> float:
        return self._percentile(99) * 1000

    def _percentile(self, p: float) -> float:
        if not self.times:
            return 0
        sorted_times = sorted(self.times)
        idx = int(len(sorted_times) * p / 100)
        return sorted_times[min(idx, len(sorted_times) - 1)]

    def report(self) -> str:
        rate = f"{self.success}/{self.total}"
        return (f"{self.method:6s} {self.endpoint:50s} "
                f"OK={rate:8s} "
                f"QPS={self.qps:6.1f}  "
                f"avg={self.avg_ms:7.1f}ms  "
                f"p50={self.p50_ms:7.1f}ms  "
                f"p95={self.p95_ms:7.1f}ms  "
                f"p99={self.p99_ms:7.1f}ms  "
                f"min={self.min_ms:5.0f}ms  "
                f"max={self.max_ms:6.0f}ms")


async def run_endpoint(client: httpx.AsyncClient, result: Result, method: str, url: str,
                       json_data=None, params=None, headers=None, sem=None):
    async def do_one():
        t0 = time.monotonic()
        try:
            if method == "GET":
                r = await client.get(url, params=params, headers=headers)
            else:
                r = await client.post(url, json=json_data, headers=headers)
            dt = time.monotonic() - t0
            if r.status_code < 400:
                result.success += 1
            else:
                result.errors += 1
            result.times.append(dt)
        except Exception:
            result.errors += 1
            result.times.append(time.monotonic() - t0)
        result.total += 1

    if sem:
        async with sem:
            await do_one()
    else:
        await do_one()


async def bench(method: str, endpoint: str, desc: str, n: int, c: int,
                json_data=None, params=None, headers=None) -> Result:
    result = Result(endpoint=endpoint, method=method, total=0, success=0, errors=0)
    sem = asyncio.Semaphore(c)

    limits = httpx.Limits(max_connections=c * 2, max_keepalive_connections=c)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, limits=limits) as client:
        tasks = [run_endpoint(client, result, method, endpoint, json_data, params, headers, sem)
                 for _ in range(n)]
        await asyncio.gather(*tasks)

    return result


async def main():
    concurrency = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    requests = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    target = sys.argv[3] if len(sys.argv) > 3 else "all"

    # First, get a login token
    token = None
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as c:
            r = await c.post("/api/auth/login", json={
                "phone": "13800000001", "password": "admin", "login_type": "password"
            })
            token = r.json()["access_token"]
    except Exception:
        print("WARNING: Login failed, skipping auth-required tests")

    auth_headers = {"Authorization": f"Bearer {token}"} if token else {}

    print(f"{'='*100}")
    print(f"  压力测试: concurrency={concurrency}, requests={requests}")
    print(f"{'='*100}\n")

    tests = [
        # (name, method, endpoint, json_data, params, headers)
        ("Health Check (无依赖)", "GET", "/health", None, None, {}),
        ("Dashboard Overview", "GET", "/api/v1/admin/dashboard/overview", None,
         {"tenant_id": "default"}, auth_headers),
        ("Dashboard Users Top", "GET", "/api/v1/admin/dashboard/users/top", None,
         {"tenant_id": "default", "limit": 10}, auth_headers),
        ("Billing Usage", "GET", "/api/v1/admin/billing/usage", None,
         {"tenant_id": "default", "days": 7}, auth_headers),
        ("Conversation History", "GET", "/memory/v1/conversations/history", None,
         {"application_id": "电商主智能客服", "limit": 10}, auth_headers),
        ("User Profile", "GET", "/memory/v1/profile/user_10001", None, {}, auth_headers),
        ("Login (含 Argon2)", "POST", "/api/auth/login",
         {"phone": "13800000001", "password": "admin", "login_type": "password"}, None, {}),
    ]

    results = []
    for desc, method, endpoint, json_data, params, headers in tests:
        if target != "all" and target not in endpoint and target not in desc:
            continue

        print(f"  Testing: {desc} ...", end=" ", flush=True)
        t0 = time.monotonic()
        result = await bench(method, endpoint, desc, requests, concurrency, json_data, params, headers)
        elapsed = time.monotonic() - t0
        actual_qps = requests / elapsed if elapsed > 0 else 0
        print(f"done ({elapsed:.1f}s, {actual_qps:.1f} req/s)")
        results.append((desc, result, actual_qps))

    print(f"\n{'='*100}")
    print(f"{'Endpoint':52s} {'Result':10s} {'QPS':>7s} {'avg':>8s} {'p50':>8s} {'p95':>8s} {'p99':>8s} {'min':>6s} {'max':>7s}")
    print(f"{'─'*100}")

    for desc, r, actual_qps in results:
        rate = f"{r.success}/{r.total}"
        print(f"{desc:50s}  {rate:8s}  {actual_qps:6.1f}  {r.avg_ms:7.1f}ms {r.p50_ms:7.1f}ms {r.p95_ms:7.1f}ms {r.p99_ms:7.1f}ms {r.min_ms:5.0f}ms {r.max_ms:7.0f}ms")

    print(f"{'─'*100}")

    # Summary
    if results:
        all_times = [t for _, r, _ in results for t in r.times]
        total_ok = sum(r.success for _, r, _ in results)
        total_req = sum(r.total for _, r, _ in results)
        print(f"\n  Summary: {total_ok}/{total_req} successful ({total_ok/max(total_req,1)*100:.1f}%)")
        print(f"  Concurrency: {concurrency}, Total requests: {total_req}")
        if all_times:
            print(f"  Overall avg: {statistics.mean(all_times)*1000:.1f}ms, "
                  f"p95: {sorted(all_times)[int(len(all_times)*0.95)]*1000:.1f}ms")


if __name__ == "__main__":
    asyncio.run(main())
