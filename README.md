# AGRA — AI Gateway Reference Architecture

> A reference architecture for building multi-protocol, provider-independent AI gateways.

AGRA defines how to build AI gateways that preserve protocol-native capabilities while providing unified governance, observability, and operational control.

## 一句话使命

**AGRA 定义了一套构建多协议、Provider 无关 AI Gateway 的参考架构，在保持协议原生能力的前提下，实现统一治理、可观测性和运营能力。**

## 核心理念

| 原则 | 说明 |
|------|------|
| **Protocol Preservation** | 协议是能力，不是兼容负担 |
| **Governance over Translation** | 网关应该统一治理，而不是统一协议 |
| **Transport Transparency** | 保持请求/响应透传，最小化修改 |
| **Extensible by Design** | 所有能力通过扩展点实现 |

## 项目结构

- `AGRA.md` — 完整技术白皮书（11章 + 附录）
- `specs/` — AGRA 规范文档

## 兼容性分级

从 PC-0（HTTP Compatible）到 PC-5（Protocol Native），六级精确兼容性定义。
