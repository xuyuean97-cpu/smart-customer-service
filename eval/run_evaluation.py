"""
评估运行器 — 通过 HTTP API 触发或独立运行

用法:
  # 独立运行
  uv run python eval/run_evaluation.py

  # 通过 API 触发
  curl -X POST http://localhost:8081/eval/v1/run
  curl http://localhost:8081/eval/v1/results
"""
import asyncio
import httpx
import json
import os
import time
import subprocess
from datetime import datetime

BASE_URL = os.getenv("EVAL_BASE_URL", "http://localhost:8081")
RESULT_FILE = os.path.join(os.path.dirname(__file__), "data", "latest_result.json")


def run_evaluation() -> dict:
    """运行 DeepEval 评估并返回结果"""
    t0 = time.time()

    result = subprocess.run(
        ["uv", "run", "pytest", "eval/test_suite.py", "-v", "--tb=short", "-q"],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=os.path.join(os.path.dirname(__file__), ".."),
    )

    elapsed = time.time() - t0
    output = result.stdout + "\n" + result.stderr

    # 解析 pytest 输出
    passed = result.returncode == 0
    summary = {
        "ran_at": datetime.now().isoformat(),
        "duration_seconds": round(elapsed, 1),
        "passed": passed,
        "exit_code": result.returncode,
        "output": output[-3000:],  # 截断超长输出
    }

    # 即时分析
    lines = output.splitlines()
    for line in lines:
        if "passed" in line and "failed" in line:
            summary["pytest_summary"] = line.strip()

    # 保存结果
    os.makedirs(os.path.dirname(RESULT_FILE), exist_ok=True)
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return summary


def get_latest_result() -> dict:
    """获取最近一次评估结果"""
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"status": "no_results", "message": "尚未运行评估"}


async def trigger_via_api() -> dict:
    """通过 API 触发评估并轮询结果"""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=300) as c:
        r = await c.post("/eval/v1/run")
        return r.json()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--via-api", action="store_true", help="通过 HTTP API 触发")
    parser.add_argument("--result", action="store_true", help="只查看最近结果")
    args = parser.parse_args()

    if args.result:
        print(json.dumps(get_latest_result(), ensure_ascii=False, indent=2))
    elif args.via_api:
        result = asyncio.run(trigger_via_api())
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("Running evaluation...")
        result = run_evaluation()
        print(json.dumps(result, ensure_ascii=False, indent=2))
