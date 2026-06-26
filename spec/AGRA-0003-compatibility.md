# AGRA-0003: Compatibility Model

| Field | Value |
|-------|-------|
| **Document ID** | AGRA-0003 |
| **Title** | Compatibility Model |
| **Status** | Draft |
| **Version** | 0.1 |
| **Last Updated** | 2026-06-26 |
| **Type** | Specification |
| **Depends On** | AGRA-0000, AGRA-0002 |

---

## 1. Summary

本规范定义 AGRA 的协议兼容性分级模型（Protocol Compatibility Levels，PC-0 到 PC-5）。该模型允许任何 Gateway 或 Provider 精确声明其对特定协议的兼容程度，替代行业中长期使用的模糊表述「OpenAI Compatible」。

## 2. Motivation

### 2.1 问题

行业中说「OpenAI Compatible」实际上缺乏统一定义：

- 有的 Gateway 只兼容了 `/v1/chat/completions` 一个端点
- 有的兼容了请求/响应结构
- 有的连 Streaming 事件格式都对齐了
- 有的可以让 OpenAI SDK 无缝替换 `base_url`
- 几乎没有 Gateway 能完整保留协议的原生扩展能力

这种模糊性导致开发者无法准确评估兼容程度，也无法在 Gateway 之间做横向比较。

### 2.2 目标

提供一套 **六级兼容性分级模型**，使兼容性可被精确声明、客观评估和横向比较。

## 3. Compatibility Levels

| 等级 | 名称 | 含义 |
|------|------|------|
| **PC-0** | HTTP Compatible | 支持 HTTP 与基本 REST 访问 |
| **PC-1** | Endpoint Compatible | 兼容 API 路径与请求方式 |
| **PC-2** | Schema Compatible | 请求/响应结构兼容 |
| **PC-3** | Streaming Compatible | 流式事件兼容 |
| **PC-4** | SDK Compatible | 官方 SDK 可直接使用 |
| **PC-5** | Protocol Native | 保留协议原生扩展能力 |

等级是 **累积的**：达到 PC-N 意味着同时满足 PC-0 到 PC-(N-1) 的全部要求。

## 4. Level Definitions

### 4.1 PC-0: HTTP Compatible

**要求：**

- 提供 HTTP/HTTPS 接口
- 接受 POST 请求并返回 HTTP 响应
- 返回有效的 HTTP 状态码

**不要求：**

- 特定的 API 路径
- 特定的请求/响应格式
- JSON 支持

**典型场景：** 自建模型服务的简单代理。

### 4.2 PC-1: Endpoint Compatible

**要求：**

- 兼容目标 Provider 的 API 路径（如 `/v1/chat/completions`）
- 兼容 HTTP 方法（POST/GET）
- 接受 `application/json` Content-Type

**不要求：**

- 请求体结构完全一致
- 响应体结构完全一致

**典型场景：** 简单负载均衡代理。

### 4.3 PC-2: Schema Compatible

**要求：**

- 请求体结构与目标 Provider 一致（字段名、类型、嵌套结构）
- 非流式响应体结构与目标 Provider 一致
- 错误响应格式一致

**不要求：**

- Streaming 支持
- 所有参数都被正确处理（部分参数可能被忽略）

**已知风险：** 部分参数（如 `thinking`、`cache_control`）可能被 Gateway 过滤。

**典型场景：** 基本 Chat 场景，不需要流式响应。

### 4.4 PC-3: Streaming Compatible

**要求（在 PC-2 基础上）：**

- 支持 SSE 流式响应
- 流事件格式与目标 Provider 一致
- 正确处理流终止标记（如 `data: [DONE]`）
- 支持所有流事件类型（如 `content_block_start`、`content_block_delta`）
- Usage 信息在流结束时正确返回

**不要求：**

- 非标准流事件透传
- Provider 特有的流扩展事件

**典型场景：** 需要流式响应的 Chat 和 Completion 场景。

### 4.5 PC-4: SDK Compatible

**要求（在 PC-3 基础上）：**

- 官方 SDK 可直接使用，仅需修改 `base_url`
- 所有标准 API 端点兼容
- 认证方式兼容（API Key Header）
- Error 格式与官方文档一致
- Streaming 完全兼容

**不要求：**

- Provider 特有参数透传
- 非标准端点支持

**典型场景：** 希望无缝替换 Provider Endpoint 的生产环境。

### 4.6 PC-5: Protocol Native

**要求（在 PC-4 基础上）：**

- Provider 特有参数不被过滤（如 `thinking`、`cache_control`、`grounding`）
- 非标准响应字段保留
- 流式扩展事件保留
- 支持 Provider 特有的 API 端点（不仅仅是 Chat Completions）
- `extra_body` 机制有效（对于支持该机制的 SDK）

**这是 AGRA 推荐的目标兼容等级，也是 TLG（Transparent Gateway）模式的默认等级。**

**典型场景：** 需要完整利用 Provider 所有能力的生产环境。

## 5. Compatibility Declaration

### 5.1 声明格式

```
<Name> <version>
- <Protocol> Compatibility: PC-<N> (<Level Name>)
```

### 5.2 示例

```
MyGateway v2.3.1
- OpenAI Compatibility: PC-4 (SDK Compatible)
- Anthropic Compatibility: PC-2 (Schema Compatible)
- Gemini Compatibility: PC-1 (Endpoint Compatible)
```

### 5.3 声明要求

- 必须按协议分别声明，不得笼统声明「兼容 OpenAI」
- 必须标注版本号
- 声明 PC-5 时必须列出支持的 Provider 特有能力（如 `thinking`、`grounding`）

## 6. Conformance Test Requirements

声明某一兼容等级的 Gateway 应通过对应的测试用例：

| 等级 | 测试要求 |
|------|---------|
| PC-0 | HTTP 连通性测试 |
| PC-1 | 端点路由测试 |
| PC-2 | 请求/响应 Schema 验证 |
| PC-3 | SSE 流事件序列验证 |
| PC-4 | SDK 集成测试（使用官方 SDK） |
| PC-5 | 参数透传测试（未识别字段不被丢弃） |

> 具体测试用例定义见 AGRA Conformance Test Suite（agra-tests）。

## 7. Relationship to Reference Patterns

| 参考模式 | 默认兼容等级 | 说明 |
|---------|-------------|------|
| Transparent Gateway (TLG) | PC-5 | 透传保证协议原生能力 |
| Protocol Translation Gateway | PC-2 ~ PC-4 | 取决于转换完整度 |
| OpenAI-Compatible Gateway | PC-2 ~ PC-4 | 取决于适配覆盖度 |

## 8. References

- AGRA-0000: Vision
- AGRA-0002: Terminology
- AGRA-0006: Reference Patterns
