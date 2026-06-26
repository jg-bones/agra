# ADR-002: Protocol Layer 与 Governance Layer 解耦

| Field | Value |
|-------|-------|
| **ADR ID** | ADR-002 |
| **Title** | Protocol Layer 与 Governance Layer 解耦 |
| **Status** | Accepted |
| **Date** | 2026-06-26 |
| **Deciders** | AGRA Community |

## Context

传统 AI Gateway 架构中，治理逻辑（认证、限流、计费）和协议逻辑（参数映射、格式转换）耦合在一起。例如，LiteLLM 的 Proxy Server 同时处理认证和参数转换。

这导致：协议演进时需要修改治理代码；治理增强时需要调整协议适配；难以独立测试和替换。

## Decision

将 Protocol Layer 和 Governance Layer 设计为独立的、解耦的层。治理层通过 Middleware Chain 实现，不依赖协议细节。协议层通过 Protocol Handler 实现，不包含治理逻辑。

## Rationale

1. **独立演进**：协议演进不影响治理逻辑，治理增强不影响协议适配
2. **独立测试**：每层可独立测试
3. **可替换性**：可独立替换任一层
4. **关注点分离**：协议处理和治理是正交的两个维度

## Consequences

**正面：**
- 架构清晰，职责分明
- 协议和治理可独立迭代
- 便于第三方扩展

**负面：**
- 增加一层抽象
- 需要明确定义层间接口（RequestContext）

## References

- AGRA-0001: Architecture §3 (Five-Layer Model) and §4 (Key Architectural Decision)
- AGRA-0004: Governance Model
