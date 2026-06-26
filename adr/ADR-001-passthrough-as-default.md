# ADR-001: 选择透传作为默认行为

| Field | Value |
|-------|-------|
| **ADR ID** | ADR-001 |
| **Title** | 选择透传作为默认行为 |
| **Status** | Accepted |
| **Date** | 2026-06-26 |
| **Deciders** | AGRA Community |

## Context

传统 AI Gateway（如 LiteLLM、One API）将协议转换作为默认行为。AGRA 面临一个关键架构决策：Gateway 的默认行为应该是协议转换还是透传（pass-through）？

## Decision

采用透传作为默认行为。协议转换作为可选的 Reference Pattern（Protocol Translation Gateway），而非默认行为。

## Rationale

1. **协议分化趋势不可逆**：OpenAI Responses API、Anthropic Thinking、Gemini Grounding 表明协议持续演进
2. **透传保证 PC-5 兼容性**：不修改请求体意味着协议原生能力不被丢失
3. **透传性能更好**：无序列化/反序列化开销
4. **降低维护成本**：新增 Provider 不需要编写 Adapter
5. **避免静默参数丢失**：透传不会出现白名单过滤问题

## Consequences

**正面：**
- Protocol Handler 默认实现更简单
- 新增 Provider 成本降低
- 协议原生能力得到保证

**负面：**
- 客户端必须使用与 Provider 匹配的协议
- 跨协议场景需要显式配置 Protocol Translation 模式

## References

- AGRA-0000: Vision §5 (Core Proposition)
- AGRA-0001: Architecture §2.1 (Principle 1)
- AGRA-0006: Reference Patterns §3 (TLG)
