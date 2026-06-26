#!/usr/bin/env python3
"""
AGRA Client Example — 演示如何通过 AGRA Gateway 访问不同 Provider。

展示 AGRA 的核心价值：
1. 客户端使用官方 SDK（OpenAI Python SDK），只需修改 base_url
2. extra_body 参数被完整透传（PC-5 Protocol Native）
3. 同一 Gateway 服务多协议
"""
from __future__ import annotations

import asyncio
import httpx
import json


GATEWAY_URL = "http://localhost:8080"


async def demo_openai_protocol():
    """演示 OpenAI 协议透传。"""
    print("\n=== Demo 1: OpenAI Protocol (PC-5) ===")
    print("通过 AGRA Gateway 发送 OpenAI Chat Completions 请求")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{GATEWAY_URL}/v1/chat/completions",
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "Hello!"}],
                "max_tokens": 50,
            },
            headers={"Authorization": "Bearer agra-key-demo-001"},
        )
        print(f"Status: {response.status_code}")
        print(f"X-Request-ID: {response.headers.get('X-Request-ID', 'N/A')}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}")
        else:
            print(f"Error: {response.text[:200]}")


async def demo_extra_body_passthrough():
    """演示 extra_body 透传——AGRA 的核心价值。

    这正是 AGRA-0000 §2.1 中描述的 thinking 参数丢失案例。
    传统 Gateway 会过滤 thinking，AGRA Gateway（TLG 模式）完整透传。
    """
    print("\n=== Demo 2: extra_body Passthrough (AGRA 核心价值) ===")
    print("发送带 extra_body (thinking) 的请求——AGRA 保证透传，不丢失参数")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{GATEWAY_URL}/v1/chat/completions",
            json={
                "model": "claude-sonnet-4-5",
                "messages": [{"role": "user", "content": "9.11 和 9.8 哪个更大？"}],
                "extra_body": {
                    "thinking": {
                        "type": "enabled",
                        "budget_tokens": 4000
                    }
                },
                # 注意：实际 OpenAI SDK 会将 extra_body 展开到顶层
                # 这里直接在顶层放 thinking 模拟展开后的效果
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": 4000
                },
            },
            headers={"Authorization": "Bearer agra-key-demo-001"},
        )
        print(f"Status: {response.status_code}")
        print(f"X-Request-ID: {response.headers.get('X-Request-ID', 'N/A')}")
        print("→ AGRA Gateway 保证 thinking 参数被透传到 Provider，不会被白名单过滤")


async def demo_anthropic_protocol():
    """演示 Anthropic 协议透传。"""
    print("\n=== Demo 3: Anthropic Protocol ===")
    print("通过 AGRA Gateway 发送 Anthropic Messages API 请求")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{GATEWAY_URL}/v1/messages",
            json={
                "model": "claude-sonnet-4-5",
                "messages": [{"role": "user", "content": "Hello!"}],
                "max_tokens": 50,
            },
            headers={
                "x-api-key": "agra-key-demo-001",
                "anthropic-version": "2023-06-01",
            },
        )
        print(f"Status: {response.status_code}")
        print(f"X-Request-ID: {response.headers.get('X-Request-ID', 'N/A')}")


async def demo_gemini_protocol():
    """演示 Gemini 协议透传。"""
    print("\n=== Demo 4: Gemini Protocol ===")
    print("通过 AGRA Gateway 发送 Gemini generateContent 请求")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{GATEWAY_URL}/v1beta/models/gemini-2.5-pro:generateContent",
            json={
                "contents": [{"role": "user", "parts": [{"text": "Hello!"}]}],
                "generationConfig": {"maxOutputTokens": 50},
            },
            headers={"x-goog-api-key": "agra-key-demo-001"},
        )
        print(f"Status: {response.status_code}")
        print(f"X-Request-ID: {response.headers.get('X-Request-ID', 'N/A')}")


async def demo_streaming():
    """演示 SSE 流式透传。"""
    print("\n=== Demo 5: SSE Streaming Transparency ===")
    print("流式请求——AGRA 保证 SSE 逐帧透传")

    async with httpx.AsyncClient(timeout=30) as client:
        async with client.stream(
            "POST",
            f"{GATEWAY_URL}/v1/chat/completions",
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "Tell me a joke"}],
                "stream": True,
                "stream_options": {"include_usage": True},
            },
            headers={"Authorization": "Bearer agra-key-demo-001"},
        ) as response:
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            count = 0
            async for chunk in response.aiter_bytes():
                count += 1
                if count <= 3:
                    print(f"  Chunk {count}: {chunk[:80]}...")
            print(f"  Total chunks received: {count}")


async def demo_compat_endpoint():
    """演示兼容性声明端点。"""
    print("\n=== Demo 6: Compatibility Declaration ===")
    print("查询 Gateway 的兼容性等级声明")

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{GATEWAY_URL}/.well-known/agra-compatibility")
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))


async def demo_metrics():
    """演示 Metrics 端点。"""
    print("\n=== Demo 7: Observability Metrics ===")
    print("查询 Prometheus 格式的指标")

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{GATEWAY_URL}/metrics")
        text = response.text
        # 只显示前 500 字符
        print(text[:500] if text else "(no metrics yet)")


async def main():
    print("=" * 60)
    print("AGRA Client Examples")
    print("Demonstrating AGRA specification compliance")
    print("=" * 60)

    demos = [
        demo_openai_protocol,
        demo_extra_body_passthrough,
        demo_anthropic_protocol,
        demo_gemini_protocol,
        demo_streaming,
        demo_compat_endpoint,
        demo_metrics,
    ]

    for demo in demos:
        try:
            await demo()
        except httpx.ConnectError:
            print(f"  ⚠ Cannot connect to Gateway at {GATEWAY_URL}")
            print("  Make sure the Gateway is running: python examples/run_demo.py")
            return
        except Exception as e:
            print(f"  ⚠ Error: {e}")

    print("\n" + "=" * 60)
    print("All demos completed.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
