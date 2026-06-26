#!/usr/bin/env python3
"""
AGRA Demo Runner — 启动一个完整的 AGRA Gateway 实例。

演示 AGRA 规范的全部要素：
- 五层架构
- 四原则（Protocol Preservation, Governance over Translation, Transport Transparency, Extensible by Design）
- PC-0~PC-5 兼容性（默认 PC-5 Protocol Native，透传模式）
- TLG (Transparent Gateway) 模式
- Middleware Chain: Auth / RateLimit / Router / Billing / Audit / Observability
- Policy Engine: 声明式规则
- Plugin System: Cache / ContentFilter
- Usage Extractor: OpenAI / Anthropic / Gemini

Usage:
    python examples/run_demo.py
"""
from __future__ import annotations

import asyncio
import logging
import sys
import os

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
from agra.gateway import Gateway
from agra.governance.middleware import MiddlewareChain
from agra.governance.auth import AuthMiddleware
from agra.governance.rate_limit import RateLimitMiddleware
from agra.governance.router import (
    RouterMiddleware,
    RoundRobinStrategy,
    WeightedStrategy,
    LatencyAwareStrategy,
    CostAwareStrategy,
    FallbackStrategy,
    CapabilityAwareStrategy,
)
from agra.governance.billing import BillingMiddleware, AuditMiddleware
from agra.observability.observability import ObservabilityMiddleware
from agra.policy.engine import PolicyEngine
from agra.plugins.base import CachePlugin, ContentFilterPlugin
from agra.transport.server import TransportServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("agra.demo")


def load_config() -> dict:
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config",
        "demo.yaml",
    )
    with open(config_path) as f:
        return yaml.safe_load(f)


def build_gateway(config: dict) -> Gateway:
    """构建完整的 AGRA Gateway。"""
    # ─── Governance Layer: Middleware Chain ───
    chain = MiddlewareChain()

    # 1. Auth Middleware (对应 AGRA-0004 §4)
    auth = AuthMiddleware(
        client_api_keys=config.get("client_api_keys", {}),
        provider_api_keys={
            name: pc.get("api_key", "")
            for name, pc in config.get("providers", {}).items()
        },
    )
    chain.add(auth)

    # 2. Rate Limit Middleware (对应 AGRA-0004 §7)
    rate_limit = RateLimitMiddleware(limits=config.get("rate_limits", {}))
    chain.add(rate_limit)

    # 3. Router Middleware (对应 AGRA-0004 §6)
    strategy_name = config.get("routing", {}).get("strategy", "round_robin")
    strategies = {
        "round_robin": RoundRobinStrategy,
        "weighted": WeightedStrategy,
        "latency_aware": LatencyAwareStrategy,
        "cost_aware": CostAwareStrategy,
        "fallback": FallbackStrategy,
        "capability_aware": CapabilityAwareStrategy,
    }
    strategy_cls = strategies.get(strategy_name, RoundRobinStrategy)
    router = RouterMiddleware(
        strategy=strategy_cls(),
        provider_configs=config.get("providers", {}),
    )
    chain.add(router)

    # 4. Billing Middleware (对应 AGRA-0004 §8)
    billing = BillingMiddleware()
    chain.add(billing)

    # 5. Audit Middleware (对应 AGRA-0005 §3.3)
    audit = AuditMiddleware()
    chain.add(audit)

    # ─── Policy Engine (对应 AGRA-0004 §9) ───
    policy_engine = PolicyEngine()
    policy_engine.load(config.get("policies", []))

    # ─── Gateway ───
    gateway = Gateway(
        middleware_chain=chain,
        policy_engine=policy_engine,
        provider_api_keys={
            name: pc.get("api_key", "")
            for name, pc in config.get("providers", {}).items()
        },
        provider_configs=config.get("providers", {}),
        default_provider=config.get("gateway", {}).get("default_provider", "openai"),
    )

    # ─── Plugins (对应 AGRA-0001 §2.4) ───
    async def setup_plugins():
        for plugin_config in config.get("plugins", []):
            name = plugin_config.get("name")
            cfg = plugin_config.get("config", {})
            if name == "cache":
                plugin = CachePlugin(ttl=cfg.get("ttl", 300))
                await plugin.setup(gateway)
            elif name == "content_filter":
                plugin = ContentFilterPlugin()
                await plugin.setup(gateway)

    # 同步执行 plugin setup
    asyncio.get_event_loop().run_until_complete(setup_plugins())

    return gateway


async def print_banner(config: dict):
    """打印启动 Banner。"""
    gw_config = config.get("gateway", {})
    providers = config.get("providers", {})

    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    AGRA Gateway v0.1                         ║
║         AI Gateway Reference Architecture                    ║
║                                                              ║
║  Spec: AGRA v0.1-draft                                      ║
║  Mode: Transparent Gateway (TLG) — PC-5 Protocol Native     ║
║                                                              ║
║  Principles:                                                 ║
║    ✓ Protocol Preservation                                  ║
║    ✓ Governance over Translation                            ║
║    ✓ Transport Transparency                                 ║
║    ✓ Extensible by Design                                   ║
║                                                              ║
║  Layers:                                                     ║
║    ✓ Transport (aiohttp)                                    ║
║    ✓ Protocol (OpenAI / Anthropic / Gemini)                 ║
║    ✓ Governance (Auth / RateLimit / Router / Billing)       ║
║    ✓ Observability (Logging / Metrics / Tracing)            ║
║                                                              ║
║  Extensions:                                                 ║
║    ✓ Policy Engine                                           ║
║    ✓ Plugin System (Cache / ContentFilter)                  ║
║    ✓ Usage Extractor (per-protocol)                         ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)
    print(f"  Listening: http://{gw_config.get('host', '0.0.0.0')}:{gw_config.get('port', 8080)}")
    print(f"  Providers: {', '.join(providers.keys())}")
    print(f"  Endpoints:")
    print(f"    POST /v1/chat/completions     → OpenAI protocol")
    print(f"    POST /v1/messages             → Anthropic protocol")
    print(f"    POST /v1beta/models/*/generateContent → Gemini protocol")
    print(f"    GET  /metrics                  → Prometheus metrics")
    print(f"    GET  /health                   → Health check")
    print()


async def add_admin_endpoints(app, gateway: Gateway):
    """添加管理端点。"""
    from aiohttp import web
    from agra.observability.observability import ObservabilityMiddleware

    async def health(request: web.Request) -> web.Response:
        return web.json_response({"status": "healthy", "version": "0.1.0"})

    async def metrics(request: web.Request) -> web.Response:
        obs = gateway.observability
        summary = obs.get_metrics_summary()
        # Prometheus 格式
        lines = []
        for key, val in summary.items():
            if isinstance(val, dict):
                for subkey, subval in val.items():
                    lines.append(f'agra_{key}_{subkey} {subval}')
            else:
                lines.append(f'agra_{key} {val}')
        return web.Response(text="\n".join(lines) + "\n", content_type="text/plain")

    async def compat(request: web.Request) -> web.Response:
        """声明兼容性等级。对应 AGRA-0003 §5。"""
        return web.json_response({
            "gateway": "AGRA Reference Implementation v0.1",
            "compatibility": {
                "openai": {"level": "PC-5", "name": "Protocol Native"},
                "anthropic": {"level": "PC-5", "name": "Protocol Native"},
                "gemini": {"level": "PC-5", "name": "Protocol Native"},
            },
            "pattern": "Transparent Gateway (TLG)",
            "spec": "AGRA v0.1-draft",
        })

    app.router.add_get("/health", health)
    app.router.add_get("/metrics", metrics)
    app.router.add_get("/.well-known/agra-compatibility", compat)


async def main():
    config = load_config()

    await print_banner(config)

    gateway = build_gateway(config)
    await gateway.start()

    gw_config = config.get("gateway", {})
    server = TransportServer(
        gateway=gateway,
        host=gw_config.get("host", "0.0.0.0"),
        port=gw_config.get("port", 8080),
    )

    # 添加管理端点
    app = server.create_app()
    await add_admin_endpoints(app, gateway)

    # 重新设置 app（因为 add_admin_endpoints 修改了 app）
    from aiohttp import web
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, server.host, server.port)
    await site.start()

    logger.info("AGRA Gateway ready. Press Ctrl+C to stop.")

    try:
        # 保持运行
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await gateway.stop()
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")
