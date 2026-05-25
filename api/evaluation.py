"""
评估 API — 触发 DeepEval 评估 + 查询历史结果
"""
from fastapi import APIRouter
from pydantic import BaseModel
import subprocess
import json
import os
import time
from datetime import datetime, timezone

from common.logging import get_logger


logger = get_logger("api.evaluation")
router = APIRouter(prefix="/eval/v1", tags=["评估体系"])

RESULT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "eval", "data")
HISTORY_FILE = os.path.join(RESULT_DIR, "history.json")


class EvalResult(BaseModel):
    ran_at: str
    passed: bool
    duration_seconds: float
    pytest_summary: str = ""
    output: str = ""


class EvalTriggerResponse(BaseModel):
    ret_code: str = "000000"
    ret_msg: str = "评估已触发"
    data: dict = {}


def _save_to_history(result: dict):
    os.makedirs(RESULT_DIR, exist_ok=True)
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    history.insert(0, result)
    history = history[:50]  # 保留最近 50 次
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


@router.post("/run")
async def run_evaluation():
    """
    运行完整的 DeepEval 评估测试套件

    评估指标:
    - AnswerRelevancy: 答案相关性
    - Faithfulness: 事实准确性
    - Toxicity: 毒性检测
    - BusinessReplyFormat: 业务回复格式
    """
    t0 = time.time()
    logger.info("开始运行评估套件...")

    try:
        project_root = os.path.join(os.path.dirname(__file__), "..")
        proc = subprocess.run(
            ["uv", "run", "pytest", "eval/test_suite.py", "-v", "--tb=short", "-q"],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=project_root,
        )

        elapsed = time.time() - t0
        passed = proc.returncode == 0
        output = proc.stdout + "\n" + proc.stderr

        # 解析测试数
        passed_count = 0
        failed_count = 0
        for line in output.splitlines():
            if "PASSED" in line or "FAILED" in line:
                pass  # 稍后统一解析
        # Pytest 输出格式: "X passed, Y failed"
        import re
        m = re.search(r"(\d+) passed", output)
        passed_count = int(m.group(1)) if m else 0
        m = re.search(r"(\d+) failed", output)
        failed_count = int(m.group(1)) if m else 0

        result = {
            "ran_at": datetime.now(timezone.utc).isoformat(),
            "passed": passed,
            "duration_seconds": round(elapsed, 1),
            "passed_count": passed_count,
            "failed_count": failed_count,
            "exit_code": proc.returncode,
            "summary": f"{passed_count} passed, {failed_count} failed",
            "output": output[-3000:],
        }

        _save_to_history(result)

        return {
            "ret_code": "000000",
            "ret_msg": "评估完成",
            "data": result,
        }

    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        result = {
            "ran_at": datetime.now(timezone.utc).isoformat(),
            "passed": False,
            "duration_seconds": round(elapsed, 1),
            "summary": "评估超时 (>300s)",
        }
        _save_to_history(result)
        return {"ret_code": "000001", "ret_msg": "评估超时", "data": result}

    except Exception as e:
        logger.error(f"评估失败: {e}", exc_info=True)
        return {"ret_code": "999999", "ret_msg": str(e), "data": {}}


@router.get("/results")
async def get_latest_result():
    """获取最近一次评估结果"""
    if not os.path.exists(HISTORY_FILE):
        return {"ret_code": "000000", "ret_msg": "暂无评估记录", "data": {"history": [], "latest": None}}

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
        return {
            "ret_code": "000000",
            "ret_msg": "成功",
            "data": {
                "latest": history[0] if history else None,
                "history": history,
                "total_runs": len(history),
                "recent_pass_rate": sum(1 for h in history[:10] if h.get("passed")) / min(len(history), 10) if history else 0,
            },
        }
    except Exception as e:
        return {"ret_code": "999999", "ret_msg": str(e), "data": {}}


@router.get("/test-cases")
async def get_test_cases():
    """获取评估用的测试用例（专家审核通过的高质量对话）"""
    try:
        import httpx
        async with httpx.AsyncClient(base_url="http://localhost:8081", timeout=30) as c:
            r = await c.post("/api/auth/login", json={
                "phone": "13800000001", "password": "admin", "login_type": "password"
            })
            token = r.json()["access_token"]
            r = await c.get("/memory/v1/conversations/history", params={
                "application_id": "电商主智能客服",
                "expert_verified": "true",
                "limit": 50,
            }, headers={"Authorization": f"Bearer {token}"})
            d = r.json()
            inner = d.get("data", d)
            convs = inner.get("conversations", [])
            cases = [
                {"query": c.get("query"), "response": c.get("response"),
                 "quality_score": c.get("quality_score", 0)}
                for c in convs if c.get("query") and c.get("response")
            ]
        return {"ret_code": "000000", "ret_msg": "成功", "data": {"cases": cases, "total": len(cases)}}
    except Exception as e:
        return {"ret_code": "999999", "ret_msg": str(e), "data": {"cases": [], "total": 0}}
