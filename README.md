# AGRA — AI Gateway Reference Architecture

> **A Reference Architecture for Building Multi-Protocol AI Gateways**
>
> 一套构建多协议、Provider 无关 AI Gateway 的参考架构

[![Spec Version](https://img.shields.io/badge/spec-v0.1--draft-blue)]()
[![Documents](https://img.shields.io/badge/documents-7%20specs%20%2B%20book-green)]()
[![License](https://img.shields.io/badge/license-AGRA%20Spec-orange)]()

---

## What is AGRA?

AGRA（AI Gateway Reference Architecture）是一套构建 AI Gateway 的参考架构方法论。它的核心立场是：

> **在保持协议原生能力的前提下，实现统一治理、可观测性和运营能力。**

AGRA 不发明新协议，也不规定具体实现。它定义的是设计原则、架构边界、兼容性标准和参考模式——一套可以被任何 AI Gateway 项目引用和遵循的方法论。

## Why AGRA?

今天的 AI Gateway 面临一个结构性矛盾：

- **协议在分化**：OpenAI Responses API、Anthropic Thinking、Gemini Grounding 各自演进
- **网关在统一**：大多数 Gateway 将所有协议压缩为 OpenAI 格式
- **能力在丢失**：Gateway 不认识的新参数被静默丢弃

AGRA 提出另一个方向：**不统一协议，统一治理。**

## Core Concepts

### 四条设计原则

| 原则 | 核心思想 |
|------|---------|
| **Protocol Preservation** | 协议是能力，不是兼容负担 |
| **Governance over Translation** | 统一治理，而不是统一协议 |
| **Transport Transparency** | 不修改请求/响应体 |
| **Extensible by Design** | 所有能力通过扩展点实现 |

### 五层架构

```
Client Layer → Transport Layer → Protocol Layer → Governance Layer → Observability Layer
                                  (解耦)              (解耦)
```

### 六级兼容性

| 等级 | 名称 |
|------|------|
| PC-0 | HTTP Compatible |
| PC-1 | Endpoint Compatible |
| PC-2 | Schema Compatible |
| PC-3 | Streaming Compatible |
| PC-4 | SDK Compatible |
| PC-5 | Protocol Native（推荐） |

### 三种参考模式

| 模式 | 兼容等级 | 推荐度 |
|------|---------|--------|
| Transparent Gateway (TLG) | PC-5 | ★★★★★ |
| Protocol Translation Gateway | PC-2~4 | ★★★ |
| OpenAI-Compatible Gateway | PC-2~4 | ★★ |

## Documentation

### 规范文档（spec/）

RFC 风格的可引用规范：

| 文档 | 标题 | 说明 |
|------|------|------|
| [AGRA-0000](spec/AGRA-0000-vision.md) | Vision | 愿景、使命、边界 |
| [AGRA-0001](spec/AGRA-0001-architecture.md) | Architecture | 四原则、五层模型 |
| [AGRA-0002](spec/AGRA-0002-terminology.md) | Terminology | 术语定义 |
| [AGRA-0003](spec/AGRA-0003-compatibility.md) | Compatibility Model | PC-0 到 PC-5 |
| [AGRA-0004](spec/AGRA-0004-governance.md) | Governance Model | 治理层架构 |
| [AGRA-0005](spec/AGRA-0005-observability.md) | Observability | 日志/指标/追踪 |
| [AGRA-0006](spec/AGRA-0006-reference-patterns.md) | Reference Patterns | 三种参考模式 |

### 白皮书（book/）

| 文档 | 说明 |
|------|------|
| [AGRA.md](book/AGRA.md) | 完整白皮书（17 章 + 附录） |

### 架构决策记录（adr/）

| ADR | 标题 |
|-----|------|
| [ADR-001](adr/ADR-001-passthrough-as-default.md) | 选择透传作为默认行为 |
| [ADR-002](adr/ADR-002-decoupled-protocol-governance.md) | Protocol Layer 与 Governance Layer 解耦 |
| [ADR-003](adr/ADR-003-compatibility-levels.md) | 兼容性分级模型 |

## Quick Start

### 我要评估一个 AI Gateway

1. 阅读 [AGRA-0003](spec/AGRA-0003-compatibility.md) 了解兼容性等级
2. 要求 Gateway 声明其对每个 Provider 的 PC-N 等级
3. 确认是否达到 PC-5（Protocol Native），特别是 `extra_body` 参数是否被透传

### 我要构建一个 AI Gateway

1. 阅读白皮书 [Chapter 1-4](book/AGRA.md) 理解 AGRA 核心理念
2. 按照 [AGRA-0001](spec/AGRA-0001-architecture.md) 实现五层模型
3. 确保 Protocol Layer 与 Governance Layer 解耦
4. 默认采用 TLG 模式（透传），达到 PC-5
5. 参照 Conformance Requirements 进行自测

### 我要贡献 AGRA

1. 阅读现有规范文档
2. 在 Issues 中讨论提案
3. 按照 RFC 风格编写规范
4. 提交 Pull Request

## Project Structure

```
agra/
├── README.md                    # 本文件
├── spec/                        # 规范文档（RFC 风格）
│   ├── AGRA-0000-vision.md
│   ├── AGRA-0001-architecture.md
│   ├── AGRA-0002-terminology.md
│   ├── AGRA-0003-compatibility.md
│   ├── AGRA-0004-governance.md
│   ├── AGRA-0005-observability.md
│   └── AGRA-0006-reference-patterns.md
├── book/                        # 白皮书
│   └── AGRA.md
├── adr/                         # 架构决策记录
│   ├── ADR-001-passthrough-as-default.md
│   ├── ADR-002-decoupled-protocol-governance.md
│   └── ADR-003-compatibility-levels.md
└── references/                  # 参考资料（未来）
```

## Roadmap

| 版本 | 内容 | 状态 |
|------|------|------|
| v0.1 | Foundation：7 份规范 + 白皮书 + ADR | ✅ Current |
| v0.2 | Deep Dive：Translation 规范、Routing 规范、Extension 接口、Conformance Test | 📋 Planned |
| v0.3 | Reference Implementation：参考实现 + 测试套件 | 📋 Planned |
| v1.0 | Stable：所有规范 Active + 两个独立实现通过测试 | 📋 Planned |

## Key Insights

> **Protocol is Product.** 协议不再只是网络通信格式，而是模型能力的一部分。

> **统一治理，而不是统一协议。** Gateway 应该是协议的守护者，而不是协议的翻译者。

> **透传是默认行为，转换是可选模式。** 任何对请求体的修改都应是显式的、可配置的。

## Contributing

AGRA 是一套开放的参考架构。欢迎通过以下方式贡献：

- 提交 Issue 讨论规范改进
- 提交 Pull Request 修正文档
- 实现符合 AGRA 规范的 Gateway 并反馈经验
- 编写 Conformance Test 用例

## License

AGRA Specification License. 规范文档可自由引用和实现。

## Origin

本项目的初始思路源自对 LiteLLM 等开源 AI Gateway 项目的实践分析，以及对 OpenAI / Anthropic / Gemini 三大 Provider 协议演进的观察。

---

*AGRA v0.1-draft | 2026-06-26*
