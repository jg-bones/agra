# AGRA-0000: Vision

| Field | Value |
|-------|-------|
| **Document ID** | AGRA-0000 |
| **Title** | Vision |
| **Status** | Draft |
| **Version** | 0.1 |
| **Last Updated** | 2026-06-26 |
| **Type** | Specification |

---

## 1. Summary

本规范定义 AGRA（AI Gateway Reference Architecture）的愿景、使命、边界和核心命题。AGRA 是一套构建多协议、Provider 无关 AI Gateway 的参考架构，其核心立场是：**在保持协议原生能力的前提下，实现统一治理、可观测性和运营能力。**

## 2. Motivation

### 2.1 行业现状

AI Gateway 领域目前面临一个结构性矛盾：

- **协议在分化**：OpenAI Responses API、Anthropic Messages API（Thinking/Prompt Cache/Computer Use）、Gemini API（Grounding/Live API）各自演进，协议已承载 Provider 的产品能力。
- **网关在统一**：绝大多数现有 AI Gateway 采用 Protocol Translation 架构，将所有协议压缩为 OpenAI Chat Completions 格式。
- **能力在丢失**：当 Gateway 不认识新协议字段时（如 `thinking`、`cache_control`），该字段会在请求生命周期中被过滤，导致 Provider 能力无法触达客户端。

这一矛盾的本质是：

> **Protocol is Product.** 协议不再只是网络通信格式，而是模型能力的一部分。

将协议视为「可以被完全抽象掉的细节」这一假设，在 2023 年成立，在今天不再成立。

### 2.2 需要一个参考架构

行业缺少一套公认的、可引用的 AI Gateway 架构方法论。现有实践分散在各开源项目中（LiteLLM、One API、Helicone 等），缺少统一的：

- 术语体系
- 兼容性定义
- 架构分层
- 治理边界
- 可观测性标准

AGRA 旨在填补这一空白，提供一套类似 RFC 的、可被引用和遵循的参考架构。

## 3. Mission

> **AGRA defines how to build AI gateways that preserve protocol-native capabilities while providing unified governance, observability, and operational control.**

AGRA 定义了一套构建多协议、Provider 无关 AI Gateway 的参考架构，在保持协议原生能力的前提下，实现统一治理、可观测性和运营能力。

## 4. Scope

### 4.1 AGRA 要解决的问题

- 多协议接入（OpenAI、Anthropic、Gemini 等）
- 多 Provider 路由
- 认证与授权
- 限流与配额
- 成本统计与计费
- 可观测性（Logging、Metrics、Tracing）
- 请求生命周期管理
- 插件扩展机制
- 协议兼容性评估

### 4.2 AGRA 不解决的问题

- 不重新设计模型 API
- 不统一所有 Provider 的参数
- 不隐藏 Provider 的原生能力
- 不替代 SDK
- 不规定模型推理实现

> 这一定位让 AGRA 保持在 **架构层**，而不是协议层。AGRA 不发明新协议，而是定义如何正确地代理、治理和观测现有协议。

## 5. Core Proposition

AGRA 的核心命题可以表述为一句话：

> **AI Gateway 应优先保持协议原生能力（Protocol Preservation），统一治理能力（Governance），而不是统一协议本身。**

这一命题构成 AGRA 全部设计的逻辑起点，由此推导出四条设计原则（AGRA-0001）、五层架构模型、六级兼容性分级（AGRA-0003）和三种参考模式（AGRA-0006）。

## 6. Design Philosophy

### 6.1 Protocol Preservation over Protocol Translation

传统 AI Gateway 的目标是「统一协议」。AGRA 认为这一目标在协议多元化时代不可持续，应转向「保持协议、统一治理」。

### 6.2 Governance Layer ≠ Protocol Layer

治理能力（认证、限流、计费、可观测性）与协议处理（参数映射、格式转换）是正交的两个维度，应在架构上解耦。

### 6.3 Transparency by Default

Gateway 的默认行为应是透传（pass-through），而非转换。任何对请求体或响应体的修改都应是显式的、可配置的、可追溯的。

### 6.4 Extensible, Not Monolithic

所有增值能力通过扩展点（Middleware、Plugin、Policy）实现，核心引擎保持简洁稳定。

## 7. Target Audience

- AI Gateway 项目的架构师和开发者
- 企业 AI 平台团队
- 模型服务 Provider
- 开源 AI Gateway 维护者
- 需要评估和选型 AI Gateway 的技术决策者

## 8. Document Lifecycle

本规范遵循 AGRA 文档生命周期：

| 阶段 | 说明 |
|------|------|
| Draft | 初稿，接受社区反馈 |
| Proposed | 核心议题达成共识 |
| Active | 规范确定，可被引用 |
| Deprecated | 被新版本替代 |
| Rejected | 未获共识，归档 |

## 9. References

- AGRA-0001: Architecture — 五层模型与设计原则
- AGRA-0002: Terminology — 术语定义
- AGRA-0003: Compatibility Model — 兼容性分级
- AGRA-0006: Reference Patterns — 参考模式

## 10. Acknowledgments

本规范的初始思路源自对 LiteLLM 等开源 AI Gateway 项目的实践分析，以及对 OpenAI / Anthropic / Gemini 三大 Provider 协议演进的观察。
