"""
AGRA Observability Layer — 日志、指标、追踪。

对应 AGRA-0005 (Observability) 和 AGRA-0001 §3.5。
三根支柱：Logging、Metrics、Tracing。
横切关注点，贯穿所有层。
"""
from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from agra.context import RequestContext
from agra.governance.middleware import Middleware, Response

logger = logging.getLogger("agra.observability")


@dataclass
class Span:
    """追踪 Span。对应 AGRA-0005 §5.2。"""

    name: str
    trace_id: str
    span_id: str
    parent_id: str | None = None
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)

    def add_event(self, name: str, **attrs) -> None:
        self.events.append({"name": name, "timestamp": time.time(), "attrs": attrs})

    def finish(self) -> None:
        self.end_time = time.time()

    @property
    def duration_ms(self) -> float:
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "duration_ms": round(self.duration_ms, 2),
            "attributes": self.attributes,
            "events": self.events,
        }


class ObservabilityMiddleware(Middleware):
    """可观测性 Middleware。

    对应 AGRA-0005。

    实现三根支柱：
    - Logging: 结构化 JSON 日志
    - Metrics: Counter / Histogram
    - Tracing: 分布式 Span

    关键约束（OBS-006）：数据采集不修改请求/响应体。
    """

    name = "observability"

    def __init__(self) -> None:
        # Metrics 存储
        self.metrics: dict[str, Any] = {
            "requests_total": defaultdict(int),
            "errors_total": defaultdict(int),
            "tokens_total": defaultdict(int),
            "cost_usd_total": defaultdict(float),
            "latency_samples": defaultdict(list),
            "ttft_samples": defaultdict(list),
        }
        # Traces 存储
        self.traces: dict[str, list[Span]] = defaultdict(list)

    async def on_request(self, ctx: RequestContext) -> RequestContext:
        # 创建 Root Span
        root_span = Span(
            name="gateway.request",
            trace_id=ctx.trace_id,
            span_id=ctx.request_id,
        )
        root_span.attributes.update({
            "gateway.protocol": ctx.protocol,
            "gateway.model": ctx.target_model or "unknown",
            "gateway.organization": ctx.client_org_id,
            "http.method": ctx.method,
            "http.path": ctx.path,
        })
        root_span.add_event("request_received")
        self.traces[ctx.trace_id].append(root_span)
        ctx.metadata["root_span"] = root_span

        # 记录指标
        self.metrics["requests_total"][ctx.protocol] += 1
        return ctx

    async def on_response(self, ctx: RequestContext, response: Response) -> Response:
        # 结束 Root Span
        root_span: Span = ctx.metadata.get("root_span")
        if root_span:
            root_span.attributes["http.status_code"] = response.status
            root_span.attributes["gateway.provider"] = ctx.target_provider or "unknown"
            root_span.add_event("response_sent")
            root_span.finish()

        # 记录延迟
        latency = ctx.latency_ms
        model = ctx.target_model or "unknown"
        self.metrics["latency_samples"][model].append(latency)

        # 记录用量指标
        if response.usage:
            self.metrics["tokens_total"][f"{model}:input"] += response.usage.input_tokens
            self.metrics["tokens_total"][f"{model}:output"] += response.usage.output_tokens
            self.metrics["cost_usd_total"][ctx.client_org_id] += response.usage.cost_usd

        # 记录错误
        if response.status >= 400:
            self.metrics["errors_total"][ctx.protocol] += 1

        # 结构化日志（OBS-001）
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            "level": "ERROR" if response.status >= 500 else "WARN" if response.status >= 400 else "INFO",
            "request_id": ctx.request_id,
            "trace_id": ctx.trace_id,
            "client": {
                "org_id": ctx.client_org_id,
                "user_id": ctx.client_user_id,
            },
            "request": {
                "method": ctx.method,
                "path": ctx.path,
                "protocol": ctx.protocol,
                "model": ctx.target_model,
            },
            "response": {
                "status_code": response.status,
                "latency_ms": round(latency, 2),
            },
            "provider": {
                "name": ctx.target_provider,
            },
            "usage": {
                "input_tokens": response.usage.input_tokens if response.usage else 0,
                "output_tokens": response.usage.output_tokens if response.usage else 0,
                "cost_usd": response.usage.cost_usd if response.usage else 0,
            },
        }
        logger.info(json.dumps(log_entry, ensure_ascii=False))

        return response

    def get_metrics_summary(self) -> dict:
        """获取指标摘要（Prometheus 风格）。"""
        summary = {}
        for key, val in self.metrics.items():
            if isinstance(val, defaultdict):
                if "samples" in key:
                    # Histogram
                    for label, samples in val.items():
                        if samples:
                            summary[f"{key}_{label}"] = {
                                "count": len(samples),
                                "avg_ms": round(sum(samples) / len(samples), 2),
                                "p50_ms": round(sorted(samples)[len(samples) // 2], 2),
                                "p95_ms": round(sorted(samples)[int(len(samples) * 0.95)], 2) if len(samples) > 1 else 0,
                            }
                else:
                    # Counter
                    for label, count in val.items():
                        summary[f"{key}_{label}"] = count
        return summary

    def get_trace(self, trace_id: str) -> list[dict]:
        """获取 Trace 详情。"""
        return [span.to_dict() for span in self.traces.get(trace_id, [])]
