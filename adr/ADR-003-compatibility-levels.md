# ADR-003: 兼容性分级模型（PC-0 到 PC-5）

| Field | Value |
|-------|-------|
| **ADR ID** | ADR-003 |
| **Title** | 采用六级兼容性分级模型替代「OpenAI Compatible」 |
| **Status** | Accepted |
| **Date** | 2026-06-26 |
| **Deciders** | AGRA Community |

## Context

行业中「OpenAI Compatible」缺乏统一定义，导致开发者无法准确评估 Gateway 兼容程度，也无法横向比较不同 Gateway。

## Decision

采用六级兼容性分级模型（PC-0 到 PC-5），累积式等级。任何 Gateway 或 Provider 必须按协议分别声明兼容等级。

## Rationale

1. **精确性**：PC-N 比「兼容 OpenAI」更精确
2. **可比较**：不同 Gateway 可横向比较
3. **可测试**：每级有明确的 Conformance Test 要求
4. **累积性**：PC-N 自动满足 PC-0 到 PC-(N-1)

## Consequences

**正面：**
- 开发者选型更清晰
- Gateway 实现有了明确目标
- 促进了兼容性测试标准化

**负面：**
- Gateway 需要维护详细的兼容性声明
- 需要配套 Conformance Test Suite

## References

- AGRA-0003: Compatibility Model
