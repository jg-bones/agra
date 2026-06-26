# AGRA-0006: Reference Patterns

| Field | Value |
|-------|-------|
| **Document ID** | AGRA-0006 |
| **Title** | Reference Patterns |
| **Status** | Draft |
| **Version** | 0.1 |
| **Last Updated** | 2026-06-26 |
| **Type** | Specification |
| **Depends On** | AGRA-0001, AGRA-0003 |

---

## 1. Summary

本规范定义 AGRA 的三种参考模式（Reference Patterns）：Transparent Gateway (TLG)、Protocol Translation Gateway 和 OpenAI-Compatible Gateway。每种模式有明确的适用场景、兼容性等级和设计权衡。

## 2. Pattern Overview

| 模式 | 默认兼容等级 | 核心特征 | 推荐度 |
|------|-------------|---------|--------|
| Transparent Gateway (TLG) | PC-5 | 透传，不转换 | ★★★★★ |
| Protocol Translation Gateway | PC-2 ~ PC-4 | 协议翻译 | ★★★ |
| OpenAI-Compatible Gateway | PC-2 ~ PC-4 | 统一为 OpenAI 格式 | ★★ |

## 3. Pattern 1: Transparent Gateway (TLG)

### 3.1 描述

```
Client SDK → Gateway → Provider
              │
              ├── Governance Layer (认证、限流、路由、计费)
              └── Observability Layer (日志、指标、追踪)
              
              [不修改请求体和响应体，原样透传]
```

TLG 是 AGRA 的核心参考模式，也是推荐默认模式。它完整体现 Protocol Preservation 原则。

### 3.2 行为规范

- 客户端使用官方 SDK，直接将请求发送到 Gateway
- Gateway 只做治理和观测，不修改协议内容
- 请求体和响应体原样透传
- Streaming 逐帧转发

### 3.3 兼容性等级

**PC-5 (Protocol Native)** — 保证协议全部原生扩展能力。

### 3.4 适用场景

- 客户端和 Provider 使用相同协议
- 需要统一治理但不想牺牲协议原生能力
- 对透明性和低延迟有高要求
- 企业内部多团队共享同一 Provider

### 3.5 限制

- 客户端必须使用与 Provider 匹配的协议（如访问 Anthropic 必须用 Anthropic SDK）
- 不适用于「用 OpenAI SDK 访问 Anthropic」的场景（需用 Pattern 2 或 3）

## 4. Pattern 2: Protocol Translation Gateway

### 4.1 描述

```
Client (OpenAI SDK) → Gateway → Provider (Anthropic)
                        │
                        ├── Protocol Layer (协议翻译)
                        ├── Governance Layer (治理)
                        └── Observability Layer (观测)
```

当客户端使用的协议与 Provider 不一致时，Gateway 在 Protocol Layer 进行协议转换。

### 4.2 行为规范

- 将源协议请求转换为目标协议请求
- 将目标协议响应转换为源协议格式
- Streaming 事件做格式映射
- 转换规则必须显式定义，不得静默丢弃字段

### 4.3 兼容性等级

**PC-2 ~ PC-4**，取决于转换完整度：

| 转换覆盖度 | 兼容等级 |
|-----------|---------|
| 仅基本字段（model, messages, temperature） | PC-2 |
| 含 Streaming 事件映射 | PC-3 |
| 含 SDK 完全兼容（Error 格式、认证方式） | PC-4 |

### 4.4 适用场景

- 客户端使用 OpenAI SDK，但后端是 Anthropic 或 Gemini
- 需要平滑迁移 Provider
- 多协议环境中的兼容层

### 4.5 设计约束

> **关键约束：** 转换规则必须显式声明哪些字段会被映射、哪些会被丢弃。不得静默丢弃未识别字段。

转换规则声明示例：

```yaml
translation:
  source: openai
  target: anthropic
  field_mapping:
    - source: "messages"
      target: "messages"
      transform: "openai_to_anthropic_messages"
    - source: "max_tokens"
      target: "max_tokens"
      transform: "identity"
    - source: "temperature"
      target: "temperature"
      transform: "identity"
  dropped_fields:
    - "frequency_penalty"  # Anthropic 不支持
    - "presence_penalty"   # Anthropic 不支持
  passthrough_fields:
    - "thinking"           # 原样透传
    - "cache_control"      # 原样透传
```

## 5. Pattern 3: OpenAI-Compatible Gateway

### 5.1 描述

```
Client (OpenAI SDK) → Gateway → Provider (任何)
                        │
                        ├── Protocol Layer (模拟 OpenAI 协议)
                        ├── Governance Layer (治理)
                        └── Observability Layer (观测)
```

这是目前行业中最常见的模式。Gateway 对外暴露标准 OpenAI API 接口，内部适配各种 Provider。

### 5.2 行为规范

- 对外：完全兼容 OpenAI Chat Completions API
- 对内：将请求转换为各 Provider 的原生格式
- 使用 Provider Adapter 架构

### 5.3 兼容性等级

**PC-2 ~ PC-4**，取决于适配覆盖度。

### 5.4 适用场景

- 现有应用已基于 OpenAI SDK 构建
- 需要快速接入多 Provider 但不希望修改应用代码
- 对 Provider 特有能力的依赖较低

### 5.5 风险

> **这是 AGRA 认为风险最高的模式。**

主要风险：

1. **参数丢失**：Gateway 不认识的新协议字段被白名单过滤（参见 AGRA-0000 §2.1 的 Thinking 案例）
2. **能力退化**：Provider 特有能力（Thinking、Grounding、Computer Use）无法通过 OpenAI 格式表达
3. **维护成本**：每新增 Provider 能力，需更新所有 Adapter
4. **语义失真**：不同 Provider 的参数语义不可完全映射

### 5.6 缓解措施

如果必须使用此模式，AGRA 建议：

1. **改白名单为黑名单**：默认保留所有参数，只过滤明确不需要的
2. **支持 `extra_body` 透传**：将 OpenAI SDK 的 `extra_body` 字段原样传递给 Provider
3. **声明兼容等级**：明确声明 PC-N，不笼统说「兼容 OpenAI」
4. **提供逃逸通道**：允许客户端通过特殊 Header 或路径直接访问原生协议

## 6. Pattern Selection Guide

| 场景 | 推荐模式 | 兼容等级 |
|------|---------|---------|
| 使用 Provider 全部能力 | TLG | PC-5 |
| 混合使用多 Provider（各自原生协议） | TLG（多端点） | PC-5 |
| 迁移 Provider（协议不同） | Protocol Translation | PC-2 ~ PC-4 |
| 统一多 Provider 接口（OpenAI 格式） | OpenAI-Compatible | PC-2 ~ PC-4 |
| 内部工具链 | TLG | PC-5 |
| 已有 OpenAI SDK 应用接入新 Provider | OpenAI-Compatible + 逃逸通道 | PC-4 (主) + PC-5 (逃逸) |

## 7. Multi-Pattern Deployment

AGRA 允许在同一 Gateway 中混合部署多种模式：

```
Gateway
├── /v1/chat/completions      → OpenAI-Compatible (PC-4)
├── /v1/messages              → TLG for Anthropic (PC-5)
├── /v1beta/models/*/generate → TLG for Gemini (PC-5)
└── /v1/translate/to-anthropic → Protocol Translation (PC-3)
```

客户端根据需求选择端点，同一 Gateway 同时服务不同模式。

## 8. Conformance Requirements

| 编号 | 要求 |
|------|------|
| PAT-001 | 必须至少实现 TLG 模式 |
| PAT-002 | TLG 模式必须达到 PC-5 |
| PAT-003 | Protocol Translation 必须显式声明转换规则和丢弃字段 |
| PAT-004 | OpenAI-Compatible 不得静默丢弃未识别字段 |
| PAT-005 | 所有模式必须复用同一 Governance Layer |

## 9. References

- AGRA-0000: Vision
- AGRA-0001: Architecture
- AGRA-0003: Compatibility Model
- AGRA-0004: Governance Model
