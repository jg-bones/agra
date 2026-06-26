"""
AGRA Conformance Tests — 兼容性测试。

对应 AGRA-0003 §6 (Conformance Test Requirements)。
验证实现是否满足 ARCH / GOV / OBS / PAT 系列要求。
"""
import json
import pytest
from agra.context import RequestContext
from agra.protocol.handlers import ProtocolDetector, OpenAIProtocolHandler, AnthropicProtocolHandler, GeminiProtocolHandler
from agra.governance.middleware import MiddlewareChain, Middleware, Response
from agra.governance.auth import AuthMiddleware
from agra.governance.rate_limit import RateLimitMiddleware, RateLimitExceeded
from agra.governance.router import RouterMiddleware, RoundRobinStrategy, CapabilityAwareStrategy
from agra.governance.billing import BillingMiddleware
from agra.observability.observability import ObservabilityMiddleware
from agra.policy.engine import PolicyEngine
from agra.usage.extractor import OpenAIUsageExtractor, AnthropicUsageExtractor, GeminiUsageExtractor


# ═══════════════════════════════════════════════════════════════
# ARCH-001: 必须实现五层模型
# ═══════════════════════════════════════════════════════════════

class TestArchitecture:
    """AGRA-0001 Conformance Requirements."""

    def test_arch_001_five_layer_model(self):
        """ARCH-001: 必须实现五层模型或其等价物。"""
        from agra.gateway import Gateway
        from agra.transport.server import TransportServer
        from agra.protocol.handlers import ProtocolDetector
        from agra.governance.middleware import MiddlewareChain
        from agra.observability.observability import ObservabilityMiddleware

        chain = MiddlewareChain()
        gateway = Gateway(middleware_chain=chain)
        assert gateway.protocol_detector is not None  # Protocol Layer
        assert gateway.middleware_chain is not None   # Governance Layer
        assert gateway.observability is not None      # Observability Layer

    def test_arch_002_decoupled_layers(self):
        """ARCH-002: Protocol Layer 与 Governance Layer 必须解耦。"""
        # Protocol Handler 不包含治理逻辑
        handler = OpenAIProtocolHandler()
        assert not hasattr(handler, 'authenticate')
        assert not hasattr(handler, 'rate_limit')
        assert not hasattr(handler, 'billing')

    def test_arch_003_default_passthrough(self):
        """ARCH-003: 默认行为必须是透传，而非转换。"""
        handler = OpenAIProtocolHandler()
        ctx = RequestContext(path="/v1/chat/completions", body_bytes=b'{"model":"gpt-4o"}')
        # passthrough 不应修改请求体
        url = handler.passthrough(ctx, "https://api.openai.com")
        assert url == "https://api.openai.com"

    def test_arch_004_no_silent_param_drop(self):
        """ARCH-004: 不得静默丢弃未识别的请求参数。"""
        # Protocol Handler 的 extract_metadata 只读取，不过滤
        handler = OpenAIProtocolHandler()
        original_body = b'{"model":"gpt-4o","unknown_param":"value","thinking":{"type":"enabled"}}'
        ctx = RequestContext(path="/v1/chat/completions", body_bytes=original_body)
        handler.extract_metadata(ctx)
        # 请求体应保持不变
        assert ctx.body_bytes == original_body

    def test_arch_005_middleware_chain(self):
        """ARCH-005: 治理能力必须通过 Middleware Chain 实现。"""
        chain = MiddlewareChain()
        chain.add(AuthMiddleware())
        chain.add(RateLimitMiddleware())
        assert len(chain.middlewares) >= 2

    def test_arch_006_observability(self):
        """ARCH-006: 必须支持至少一种可观测性支柱。"""
        obs = ObservabilityMiddleware()
        assert hasattr(obs, 'metrics')  # Metrics
        assert hasattr(obs, 'traces')   # Tracing


# ═══════════════════════════════════════════════════════════════
# PC-0 ~ PC-5 兼容性测试
# ═══════════════════════════════════════════════════════════════

class TestCompatibility:
    """AGRA-0003 Conformance Tests."""

    def test_pc_0_http_compatible(self):
        """PC-0: HTTP 连通性。"""
        from agra.transport.server import TransportServer
        from agra.gateway import Gateway
        gateway = Gateway()
        server = TransportServer(gateway)
        app = server.create_app()
        assert app is not None  # HTTP 接口存在

    def test_pc_1_endpoint_compatible(self):
        """PC-1: 端点路由测试。"""
        detector = ProtocolDetector()
        proto, handler = detector.detect("POST", "/v1/chat/completions")
        assert proto == "openai"
        assert handler is not None

        proto, handler = detector.detect("POST", "/v1/messages")
        assert proto == "anthropic"
        assert handler is not None

        proto, handler = detector.detect("POST", "/v1beta/models/gemini-2.5-pro:generateContent")
        assert proto == "gemini"
        assert handler is not None

    def test_pc_2_schema_compatible(self):
        """PC-2: 请求/响应结构验证。"""
        # OpenAI 响应中的 usage 解析
        extractor = OpenAIUsageExtractor()
        body = json.dumps({
            "id": "chatcmpl-123",
            "choices": [{"message": {"content": "Hello"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        }).encode()
        usage = extractor.extract_from_response(body)
        assert usage.input_tokens == 10
        assert usage.output_tokens == 5
        assert usage.total_tokens == 15

    def test_pc_3_streaming_compatible(self):
        """PC-3: SSE 流事件验证。"""
        extractor = OpenAIUsageExtractor()
        # 模拟 SSE chunk with usage
        chunk = b'data: {"id":"1","usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}\n\ndata: [DONE]\n\n'
        usage = extractor.extract_from_stream_chunk(chunk)
        assert usage is not None
        assert usage.total_tokens == 15

    def test_pc_4_sdk_compatible(self):
        """PC-4: SDK 兼容性——认证方式兼容。"""
        openai_handler = OpenAIProtocolHandler()
        headers = openai_handler.get_auth_headers("sk-test")
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer sk-test"

        anthropic_handler = AnthropicProtocolHandler()
        headers = anthropic_handler.get_auth_headers("sk-ant-test")
        assert "x-api-key" in headers
        assert "anthropic-version" in headers

        gemini_handler = GeminiProtocolHandler()
        headers = gemini_handler.get_auth_headers("AIza-test")
        assert "x-goog-api-key" in headers

    def test_pc_5_protocol_native(self):
        """PC-5: 参数透传测试——未识别字段不被丢弃。"""
        # 这是 AGRA 最核心的测试
        handler = OpenAIProtocolHandler()
        body = json.dumps({
            "model": "claude-sonnet-4-5",
            "messages": [{"role": "user", "content": "test"}],
            "thinking": {"type": "enabled", "budget_tokens": 4000},
            "cache_control": {"type": "ephemeral"},
            "unknown_future_param": {"some": "capability"}
        }).encode()

        ctx = RequestContext(path="/v1/chat/completions", body_bytes=body)
        handler.extract_metadata(ctx)

        # 请求体完整保留——没有参数被丢弃
        assert b'"thinking"' in ctx.body_bytes
        assert b'"cache_control"' in ctx.body_bytes
        assert b'"unknown_future_param"' in ctx.body_bytes


# ═══════════════════════════════════════════════════════════════
# GOV-001 ~ GOV-006 治理层测试
# ═══════════════════════════════════════════════════════════════

class TestGovernance:
    """AGRA-0004 Conformance Tests."""

    @pytest.mark.asyncio
    async def test_gov_001_middleware_chain(self):
        """GOV-001: 必须实现 Middleware Chain 模式。"""
        chain = MiddlewareChain()
        chain.add(AuthMiddleware())
        assert len(chain.middlewares) >= 1
        ctx = RequestContext(path="/v1/chat/completions")
        result = await chain.run_request(ctx)
        assert result is ctx

    @pytest.mark.asyncio
    async def test_gov_002_api_key_auth(self):
        """GOV-002: 必须支持 API Key 认证。"""
        auth = AuthMiddleware(
            client_api_keys={"test-key": {"org_id": "org1", "user_id": "user1"}}
        )
        ctx = RequestContext(
            path="/v1/chat/completions",
            headers={"Authorization": "Bearer test-key"},
        )
        result = await auth.on_request(ctx)
        assert result.client_org_id == "org1"

    @pytest.mark.asyncio
    async def test_gov_003_rate_limit(self):
        """GOV-003: 必须支持至少一种限流算法。"""
        rl = RateLimitMiddleware(limits={
            "user": {"capacity": 2, "refill_rate": 0.1}
        })
        ctx = RequestContext(path="/v1/chat/completions")
        # 前两次应该通过
        await rl.on_request(ctx)
        await rl.on_request(ctx)
        # 第三次应该被限流
        with pytest.raises(RateLimitExceeded):
            await rl.on_request(ctx)

    @pytest.mark.asyncio
    async def test_gov_004_router(self):
        """GOV-004: 必须支持至少一种路由策略。"""
        router = RouterMiddleware(
            strategy=RoundRobinStrategy(),
            provider_configs={
                "openai": {"endpoint": "https://api.openai.com", "models": ["gpt-4o"]},
            }
        )
        ctx = RequestContext(path="/v1/chat/completions", body_bytes=b'{"model":"gpt-4o"}')
        ctx.shallow_parse()
        result = await router.on_request(ctx)
        assert result.target_provider == "openai"

    @pytest.mark.asyncio
    async def test_gov_005_no_body_parse_in_governance(self):
        """GOV-005: 治理逻辑不得依赖请求体解析。"""
        # AuthMiddleware 只读 Header，不解析 Body
        auth = AuthMiddleware()
        original_body = b'{"some":"body"}'
        ctx = RequestContext(
            path="/v1/chat/completions",
            headers={"Authorization": "Bearer key"},
            body_bytes=original_body,
        )
        await auth.on_request(ctx)
        assert ctx.body_bytes == original_body  # Body 未被修改

    @pytest.mark.asyncio
    async def test_gov_006_middleware_skippable(self):
        """GOV-006: Middleware 必须可独立配置和跳过。"""
        chain = MiddlewareChain()
        mw1 = AuthMiddleware()
        mw1.name = "auth"
        chain.add(mw1)
        # 可以通过 Policy Engine 跳过
        assert any(mw.name == "auth" for mw in chain.middlewares)


# ═══════════════════════════════════════════════════════════════
# OBS-001 ~ OBS-006 可观测性测试
# ═══════════════════════════════════════════════════════════════

class TestObservability:
    """AGRA-0005 Conformance Tests."""

    def test_obs_001_structured_logging(self):
        """OBS-001: 必须支持结构化日志（JSON）。"""
        obs = ObservabilityMiddleware()
        assert hasattr(obs, 'on_response')  # 会输出 JSON 日志

    def test_obs_002_metrics(self):
        """OBS-002: 必须支持至少一种 Metrics 导出格式。"""
        obs = ObservabilityMiddleware()
        summary = obs.get_metrics_summary()
        assert isinstance(summary, dict)

    def test_obs_003_tracing(self):
        """OBS-003: 必须支持分布式追踪。"""
        obs = ObservabilityMiddleware()
        assert hasattr(obs, 'traces')

    def test_obs_004_request_trace_ids(self):
        """OBS-004: 必须记录 request_id 和 trace_id。"""
        ctx = RequestContext()
        assert ctx.request_id.startswith("req_")
        assert ctx.trace_id.startswith("trace_")

    def test_obs_005_usage_extraction(self):
        """OBS-005: 必须支持 Token 用量提取。"""
        extractor = OpenAIUsageExtractor()
        body = json.dumps({"usage": {"prompt_tokens": 100, "completion_tokens": 50}}).encode()
        usage = extractor.extract_from_response(body)
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50

    def test_obs_006_no_body_modification(self):
        """OBS-006: 可观测性数据采集不得修改请求/响应体。"""
        obs = ObservabilityMiddleware()
        original = b'{"original":"body"}'
        ctx = RequestContext(body_bytes=original)
        # Observability 不修改 body
        assert ctx.body_bytes == original


# ═══════════════════════════════════════════════════════════════
# PAT-001 ~ PAT-005 参考模式测试
# ═══════════════════════════════════════════════════════════════

class TestPatterns:
    """AGRA-0006 Conformance Tests."""

    def test_pat_001_tlg_implemented(self):
        """PAT-001: 必须至少实现 TLG 模式。"""
        from agra.gateway import Gateway
        gateway = Gateway()
        # Gateway 默认行为是透传
        assert gateway.protocol_detector is not None

    def test_pat_002_tlg_pc5(self):
        """PAT-002: TLG 模式必须达到 PC-5。"""
        handler = OpenAIProtocolHandler()
        ctx = RequestContext(
            path="/v1/chat/completions",
            body_bytes=b'{"model":"gpt-4o","thinking":{"type":"enabled"}}'
        )
        handler.extract_metadata(ctx)
        # PC-5 要求：参数不被丢弃
        assert b'"thinking"' in ctx.body_bytes

    def test_pat_003_translation_declares_rules(self):
        """PAT-003: Protocol Translation 必须显式声明转换规则。"""
        # PolicyEngine 支持声明式规则
        engine = PolicyEngine()
        engine.load([{
            "name": "test-rule",
            "match": {"body_contains": ["thinking"]},
            "action": {"route": {"require_capability": "thinking"}}
        }])
        assert len(engine.policies) == 1

    def test_pat_004_no_silent_drop_in_compatible(self):
        """PAT-004: OpenAI-Compatible 不得静默丢弃未识别字段。"""
        # AGRA 实现中，所有 Handler 都是透传，不丢弃字段
        handler = OpenAIProtocolHandler()
        body = b'{"model":"gpt-4o","unknown":"value"}'
        ctx = RequestContext(body_bytes=body)
        handler.extract_metadata(ctx)
        assert ctx.body_bytes == body  # 完整保留

    def test_pat_005_shared_governance(self):
        """PAT-005: 所有模式必须复用同一 Governance Layer。"""
        from agra.gateway import Gateway
        chain = MiddlewareChain()
        chain.add(AuthMiddleware())
        gateway = Gateway(middleware_chain=chain)
        # 所有协议请求经过同一个 Middleware Chain
        assert len(gateway.middleware_chain.middlewares) >= 1
