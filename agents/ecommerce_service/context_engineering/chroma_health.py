"""
ChromaDB 健康检查 + 熔断器

用法:
    health = get_chroma_health()

    async with health.guard("store_conversation"):
        await memory_manager.store_conversation(...)

特性:
- 每次操作前检查 ChromaDB 连通性（最多 30 秒缓存一次）
- 连续 5 次失败 → 熔断 60 秒（跳过所有 ChromaDB 操作）
- 熔断期间不阻塞主流程，对话功能正常工作
- 自动恢复：熔断期过后重试一次，成功则关闭熔断
"""
import asyncio
import time
from collections import deque
from common.logging import get_logger

logger = get_logger("chroma.health")


class ChromaDBHealth:
    """ChromaDB 健康状态管理器"""

    def __init__(
        self,
        failure_threshold: int = 5,       # 连续失败 N 次触发熔断
        cooldown_seconds: int = 60,       # 熔断持续 M 秒
        probe_interval: int = 30,         # 主动探测间隔（秒）
        retry_attempts: int = 3,          # 单次操作重试次数
        retry_base_delay: float = 0.5,    # 重试基础延迟（秒）
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.probe_interval = probe_interval
        self.retry_attempts = retry_attempts
        self.retry_base_delay = retry_base_delay

        self._recent_failures: deque[float] = deque()
        self._circuit_open_since: float | None = None
        self._last_probe: float = 0.0
        self._probe_ok: bool = True          # 最近一次探测结果
        self._lock = asyncio.Lock()

        # 外部注册的回调：用于主动 ping ChromaDB
        self._ping_fn = None

    def set_ping(self, fn):
        """注册连通性探测函数: async fn() -> bool"""
        self._ping_fn = fn

    # ── 公开状态 ──

    @property
    def is_circuit_open(self) -> bool:
        """熔断是否打开（打开 = 跳过 ChromaDB 操作）"""
        if self._circuit_open_since is None:
            return False
        if time.monotonic() - self._circuit_open_since > self.cooldown_seconds:
            # 熔断到期，自动恢复
            self._circuit_open_since = None
            logger.info("ChromaDB 熔断期结束，尝试恢复连接")
            return False
        return True

    @property
    def is_healthy(self) -> bool:
        """ChromaDB 是否健康（综合判断）"""
        return not self.is_circuit_open and self._probe_ok

    def stats(self) -> dict:
        return {
            "healthy": self.is_healthy,
            "circuit_open": self.is_circuit_open,
            "consecutive_failures": len(self._recent_failures),
            "circuit_open_since": self._circuit_open_since,
        }

    # ── 记录结果 ──

    def record_success(self):
        """记录一次成功"""
        self._recent_failures.clear()
        if self._circuit_open_since is not None:
            logger.info("ChromaDB 连接已恢复，熔断器关闭")
            self._circuit_open_since = None

    def record_failure(self, error: str = ""):
        """记录一次失败"""
        now = time.monotonic()
        self._recent_failures.append(now)

        # 只保留最近 failure_threshold * 2 条（清理过期）
        while len(self._recent_failures) > self.failure_threshold * 2:
            self._recent_failures.popleft()

        if len(self._recent_failures) >= self.failure_threshold:
            self._circuit_open_since = now
            logger.warning(
                f"ChromaDB 连续失败 {len(self._recent_failures)} 次，"
                f"熔断 {self.cooldown_seconds}s (错误: {error[:100]})"
            )

    # ── 主动探测 ──

    async def _probe(self) -> bool:
        """主动 ping ChromaDB（有缓存）"""
        now = time.monotonic()
        if now - self._last_probe < self.probe_interval:
            return self._probe_ok

        if self._ping_fn is None:
            return True   # 未注册探测函数，假定健康

        try:
            ok = await self._ping_fn()
            self._probe_ok = ok
            self._last_probe = now
            if ok:
                self.record_success()
            else:
                self.record_failure("probe returned False")
            return ok
        except Exception as e:
            self._probe_ok = False
            self._last_probe = now
            self.record_failure(str(e))
            return False

    # ── 守护上下文 ──

    def guard(self, operation_name: str):
        """
        异步上下文管理器: 自动处理健康检查 + 重试 + 熔断

        用法:
            async with health.guard("store_conversation") as ok:
                if ok:
                    await memory.store_conversation(...)
        """
        return _GuardContext(self, operation_name)

    # ── 便捷包装 ──

    async def try_call(self, operation_name: str, coro, *args, **kwargs):
        """
        带重试 + 熔断的异步调用

        Args:
            operation_name: 操作名（仅用于日志）
            coro: 异步可调用对象
            *args, **kwargs: 传给 coro

        Returns:
            coro 的返回值，或 None（熔断/全部重试失败时）
        """
        async with self.guard(operation_name) as ok:
            if not ok:
                return None
            return await coro(*args, **kwargs)


class _GuardContext:
    """守护上下文 — 由 ChromaDBHealth.guard() 创建"""

    def __init__(self, health: ChromaDBHealth, op_name: str):
        self.health = health
        self.op_name = op_name
        self._ok = False

    async def __aenter__(self) -> bool:
        # 1. 熔断检查
        if self.health.is_circuit_open:
            logger.warning(f"[熔断] 跳过 {self.op_name}")
            return False

        # 2. 探测检查
        if not await self.health._probe():
            logger.warning(f"[探测失败] 跳过 {self.op_name}")
            return False

        self._ok = True
        return True

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.health.record_failure(str(exc_val) if exc_val else exc_type.__name__)
            # 让调用方的 retry 逻辑处理，不吞异常
            return False
        if self._ok:
            self.health.record_success()
        return False


# ── 全局实例 ──
_chroma_health: ChromaDBHealth | None = None


def get_chroma_health() -> ChromaDBHealth:
    """获取全局 ChromaDBHealth 单例"""
    global _chroma_health
    if _chroma_health is None:
        _chroma_health = ChromaDBHealth()
    return _chroma_health
