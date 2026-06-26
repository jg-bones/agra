# AGRA Reference Implementation — 全要素 Demo

AGRA 规范的 Python 参考实现，覆盖规范全部要素。

## Quick Start

```bash
cd agra-reference
pip install -r requirements.txt

# 启动 demo gateway
python examples/run_demo.py

# 另一个终端，运行客户端测试
python examples/client_example.py
```

## Elements Coverage

| AGRA 要素 | 实现位置 | 规范来源 |
|-----------|---------|---------|
| 五层架构 | `agra/gateway.py` | AGRA-0001 §3 |
| Protocol Preservation | `agra/protocol/handlers.py` | AGRA-0001 §2.1 |
| Governance over Translation | `agra/governance/` | AGRA-0001 §2.2 |
| Transport Transparency | `agra/transport/` | AGRA-0001 §2.3 |
| Extensible by Design | `agra/plugins/`, `agra/policy/` | AGRA-0001 §2.4 |
| PC-0 ~ PC-5 兼容性 | `tests/test_compat.py` | AGRA-0003 |
| TLG 模式 | `agra/protocol/handlers.py` | AGRA-0006 §3 |
| Middleware Chain | `agra/governance/middleware.py` | AGRA-0004 §3 |
| Auth / RateLimit / Router / Billing | `agra/governance/` | AGRA-0004 §4-9 |
| Policy Engine | `agra/policy/engine.py` | AGRA-0004 §9 |
| Plugin System | `agra/plugins/` | AGRA-0001 §2.4 |
| Usage Extractor | `agra/usage/` | AGRA-0004 |
| Observability | `agra/observability/` | AGRA-0005 |

## Architecture

```
Client (SDK/HTTP)
    │
    ▼
Transport Layer (aiohttp server)        ← 不解析请求体，字节流透传
    │
    ▼
Protocol Layer (ProtocolDetector)       ← 路径识别协议，默认透传
    │
    ▼
Governance Layer (MiddlewareChain)       ← 认证/限流/路由/计费
    │
    ▼
Observability Layer (贯穿所有层)          ← 日志/指标/追踪
    │
    ▼
Provider (OpenAI / Anthropic / Gemini)
```

## Conformance

本实现满足以下 Conformance Requirements：

- ARCH-001: 五层模型 ✓
- ARCH-002: Protocol/Governance 解耦 ✓
- ARCH-003: 默认透传 ✓
- ARCH-004: 不丢弃未识别参数 ✓
- ARCH-005: Middleware Chain ✓
- ARCH-006: 可观测性 ✓
- GOV-001~006: 治理层全部要求 ✓
- OBS-001~006: 可观测性全部要求 ✓
- PAT-001~005: 参考模式要求 ✓
