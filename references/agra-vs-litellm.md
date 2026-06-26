# AGRA vs LiteLLM — 架构对比分析

> 本文从架构设计层面分析 AGRA 与 LiteLLM 的根本差异，以及各自适合的场景。

---

## 一句话区别

**LiteLLM 是「翻译官」** — 把所有协议翻译成 OpenAI 格式，统一对外。

**AGRA 是「透明管道」** — 不翻译，原样透传，只统一治理。

---

## 核心差异矩阵

| 维度 | LiteLLM | AGRA |
|------|---------|------|
| **默认行为** | 解析请求 → 转换格式 → 转发 | 透传字节流，不解析 |
| **参数处理** | 白名单机制，未识别参数可能被丢弃 | 全部保留，不丢弃任何参数 |
| **协议关系** | 所有协议 → 统一为 OpenAI 格式 | 各协议保持原生，互不转换 |
| **架构耦合** | 治理逻辑和协议适配耦合在 Proxy 中 | Protocol Layer 和 Governance Layer 解耦 |
| **新增 Provider** | 写完整 Adapter（参数映射+Streaming+Usage+Error） | 写 Protocol Handler（默认透传，几乎不用写逻辑） |
| **新增参数** | 更新所有 Adapter 的映射表 | 不需要改任何代码（透传） |
| **兼容等级** | PC-2 ~ PC-4（取决于 Adapter 覆盖度） | PC-5（Protocol Native，默认） |
| **Streaming** | 转换流事件格式 | 逐帧原样透传 |
| **成熟度** | 生产级，100+ Provider，大社区 | 参考架构 + demo 实现 |

---

## 分水岭：Thinking 参数丢失案例

这是两者最根本的差异——**一个真实场景下的行为对比**。

### 场景

客户端使用 OpenAI Python SDK，通过 Gateway 访问支持 `thinking` 参数的 Provider：

```python
from openai import OpenAI

client = OpenAI(base_url="https://gateway.example.com/v1")

response = client.chat.completions.create(
    model="claude-sonnet-4-5",
    messages=[{"role": "user", "content": "9.11 和 9.8 哪个更大？"}],
    extra_body={
        "thinking": {
            "type": "enabled",
            "budget_tokens": 4000
        }
    }
)
```

### 经过 LiteLLM

```
请求进来
  → 解析为内部统一格式
  → 查参数白名单
  → thinking 不在白名单
  → 丢弃
  → Provider 收不到 thinking
  → 模型未执行 Thinking 推理
  → 客户端不知道（静默失败）
```

### 经过 AGRA

```
请求进来
  → 不解析请求体
  → 原样转发字节流
  → Provider 收到完整请求体（含 thinking）
  → Thinking 推理正常执行
  → 客户端获得推理后的结果
```

### 差异本质

| | LiteLLM | AGRA |
|---|---------|------|
| 请求体 | 被解析、重构 | 原样透传 |
| thinking 参数 | 可能被白名单过滤 | 保证到达 Provider |
| 失败方式 | 静默（无报错，能力丢失） | 不会发生 |
| 修复方式 | 更新 Adapter 映射表 | 不需要修复 |

---

## 架构对比

### LiteLLM 架构

```
Client (OpenAI SDK)
    │
    ▼
LiteLLM Proxy (FastAPI)
    ├── 认证、限流、日志 (治理)
    ├── Router (路由)
    └── LLM Translation (协议翻译) ← 治理和协议耦合在这层
          ├── OpenAI Adapter (参数映射 + Streaming + Usage + Error)
          ├── Anthropic Adapter
          ├── Gemini Adapter
          └── ... 100+ Adapters
    │
    ▼
Provider (被转换为原生格式)
```

**特征：** 治理逻辑和协议适配在同一个 Proxy 中耦合。每新增 Provider 或新参数，都需要修改 Adapter。

### AGRA 架构

```
Client (任意官方 SDK)
    │
    ▼
Transport Layer (字节流透传，不解析)
    │
    ▼
Protocol Layer (协议检测 + 透传)          ← 解耦
    │                                        │
    ▼                                        │
Governance Layer (认证/限流/路由/计费)     ← 解耦
    │
    ▼
Provider (收到原样请求)
```

**特征：** Protocol Layer 和 Governance Layer 完全解耦。协议演进不影响治理，治理增强不影响协议。

---

## 新增 Provider 成本对比

### LiteLLM 新增一个 Provider

需要编写完整的 Adapter：

```
1. 创建 Provider Adapter 类
2. 实现参数映射 (param_mapping)
   - temperature → provider_temperature
   - max_tokens → provider_max_tokens
   - ... (每个参数都要映射)
3. 实现参数过滤 (白名单)
4. 实现 Streaming 转换
   - 将 Provider 的 SSE 事件转为 OpenAI 格式
5. 实现 Usage 转换
   - 将 Provider 的用量格式转为 OpenAI 格式
6. 实现 Error 转换
7. 编写测试
8. 更新文档
```

### AGRA 新增一个 Provider

```
1. 创建 ProtocolHandler 子类
2. 实现 matches() (路径匹配，约 3 行)
3. 实现 get_provider_endpoint() (返回 URL，1 行)
4. 实现 get_auth_headers() (返回认证 Header，3 行)
```

完。不需要写参数映射、不需要写 Streaming 转换、不需要写 Usage 转换——因为默认行为是透传。

---

## 新增协议参数成本对比

当 Provider 发布一个新参数（比如 Anthropic 新增了 `citations`）：

### LiteLLM

```
1. 在 Anthropic Adapter 中添加 citations 到白名单
2. 实现参数映射逻辑
3. 更新 Streaming 处理（如果影响流事件）
4. 更新测试
5. 发版
6. 用户升级 Gateway
```

直到 Gateway 发版升级前，用户的 `citations` 参数会被丢弃。

### AGRA

```
不需要做任何事。
```

参数在请求体中，Gateway 不解析也不过滤，直接透传给 Provider。

---

## 各自适合的场景

### LiteLLM 适合

- 你只用 OpenAI SDK，想接入 100+ Provider
- 你不需要 Provider 特有能力（Thinking、Grounding、Computer Use）
- 你要的是「一个 API 格式走天下」
- 你需要成熟的生产级工具（大社区、经过验证）
- 你的团队不想自己维护 Gateway 代码

### AGRA 适合

- 你需要用 Provider 的全部能力（包括新出的、未知的参数）
- 你不想每次 Provider 发新能力都等 Gateway 适配
- 你需要协议和治理独立演进
- 你在构建企业级 AI 平台，需要长期可维护的架构
- 你有团队可以基于参考实现做定制

---

## AGRA 能从 LiteLLM 学到什么

LiteLLM 在工程实践上远比 AGRA 成熟，有几个方面值得学习：

1. **Provider 覆盖度**：100+ Provider 的适配经验
2. **生产级可靠性**：错误处理、重试、fallback 的实战检验
3. **社区运营**：如何围绕一个开源 Gateway 建立社区
4. **配置体系**：YAML 配置、环境变量、动态加载
5. **观测工具**：与 Langfuse、Helicone 等观测平台的集成

## LiteLLM 能从 AGRA 借鉴什么

AGRA 的设计思路可以反向改进 LiteLLM：

1. **白名单改黑名单**：默认保留所有参数，只过滤明确不需要的
2. **支持 `extra_body` 透传**：将 OpenAI SDK 的 `extra_body` 原样传递给 Provider
3. **协议层和治理层解耦**：让治理能力增强不需要动 Adapter
4. **引入透传模式**：对相同协议的请求，绕过 Adapter 直接透传

事实上，LiteLLM 的 `drop_params=False` 配置就在往 AGRA 的方向靠——默认不丢弃参数。这是一个好的开始。

---

## 诚实评估

LiteLLM 是一个**成熟的生产级工具**，支持 100+ Provider，有庞大的社区和丰富的工程经验。

AGRA 现在是一套**参考架构规范 + 一个 demo 级参考实现**，还远不到生产可用。

AGRA 的价值不在于替代 LiteLLM，而在于：

1. **提出一种不同的设计思路**——当协议越来越分化时，「保持协议、统一治理」可能比「统一协议」更可持续
2. **定义兼容性标准**——PC-0 到 PC-5 让行业可以精确描述 Gateway 的兼容程度
3. **提供架构参考**——给新建 AI Gateway 的团队一套可遵循的设计原则

两者不是互斥的。LiteLLM 可以借鉴 AGRA 的思路做改进，AGRA 的参考实现也可以学习 LiteLLM 的工程实践。

---

*本文档属于 AGRA 项目的一部分。*
*Last Updated: 2026-06-26*
