import time
from contextlib import contextmanager
from fastapi import Request


class PerfTimer:
    """性能计时器：记录各阶段耗时，统一写回 request.state"""

    def __init__(self, request: Request = None):
        self.request = request
        self._perf = {"cache_ms": 0, "llm_ms": 0, "db_ms": 0, "cache_hit": False}

    @contextmanager
    def measure(self, stage: str):
        """
        统计某一阶段的耗时
        用法：
        with perf.measure("llm"):
            result = await call_llm(...)
        """
        start = time.time()
        try:
            yield
        finally:
            cost_ms = round((time.time() - start) * 1000, 2)
            key = f"{stage}_ms"
            self._perf.setdefault(key, 0)
            self._perf[key] += cost_ms

    def mark_cache_hit(self, hit: bool = True):
        """标记缓存是否命中"""
        self._perf["cache_hit"] = hit

    def flush_to_request(self):
        """把统计结果写回 request.state，中间件统一输出"""
        if self.request and hasattr(self.request, "state"):
            self.request.state.perf = self._perf

    def get_snapshot(self) -> dict:
        """获取当前耗时快照"""
        return self._perf.copy()
