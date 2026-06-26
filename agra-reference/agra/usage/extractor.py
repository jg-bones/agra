"""
AGRA Usage Extractor — 用量提取器。

对应 AGRA-0001 §2.4 (Extensible by Design) / AGRA-0004。
不同 Provider 的 Token 计数方式不同，通过可扩展接口实现。
"""
from __future__ import annotations

import abc
import json
from typing import Optional

from agra.context import Usage


class UsageExtractor(abc.ABC):
    """用量提取器基类。

    对应 AGRA-0001 §2.4 / AGRA-BOOK Chapter 9。

    每个 Provider 有自己的 Token 用量格式，通过此接口扩展。
    """

    protocol: str = "unknown"

    @abc.abstractmethod
    def extract_from_response(self, body: bytes) -> Usage:
        """从非流式响应中提取用量。"""
        ...

    @abc.abstractmethod
    def extract_from_stream_chunk(self, chunk: bytes) -> Optional[Usage]:
        """从流式 SSE chunk 中提取用量。

        返回 None 表示该 chunk 不含用量信息。
        """
        ...


class OpenAIUsageExtractor(UsageExtractor):
    """OpenAI 用量提取器。

    OpenAI 响应格式:
    "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    流式: 在最后一个 chunk 的 usage 字段中（需 stream_options.include_usage=true）
    """

    protocol = "openai"

    def extract_from_response(self, body: bytes) -> Usage:
        try:
            data = json.loads(body)
            usage = data.get("usage", {})
            return Usage(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Usage()

    def extract_from_stream_chunk(self, chunk: bytes) -> Optional[Usage]:
        try:
            text = chunk.decode("utf-8")
            for line in text.split("\n"):
                if line.startswith("data: ") and line != "data: [DONE]":
                    data = json.loads(line[6:])
                    if "usage" in data and data["usage"]:
                        u = data["usage"]
                        return Usage(
                            input_tokens=u.get("prompt_tokens", 0),
                            output_tokens=u.get("completion_tokens", 0),
                            total_tokens=u.get("total_tokens", 0),
                        )
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        return None


class AnthropicUsageExtractor(UsageExtractor):
    """Anthropic 用量提取器。

    Anthropic 响应格式:
    "usage": {"input_tokens": 100, "output_tokens": 50}
    流式: 在 message_delta 事件的 usage 中
    """

    protocol = "anthropic"

    def extract_from_response(self, body: bytes) -> Usage:
        try:
            data = json.loads(body)
            usage = data.get("usage", {})
            input_t = usage.get("input_tokens", 0)
            output_t = usage.get("output_tokens", 0)
            return Usage(
                input_tokens=input_t,
                output_tokens=output_t,
                total_tokens=input_t + output_t,
                cached_tokens=usage.get("cache_read_input_tokens", 0),
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Usage()

    def extract_from_stream_chunk(self, chunk: bytes) -> Optional[Usage]:
        try:
            text = chunk.decode("utf-8")
            for line in text.split("\n"):
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if data.get("type") == "message_delta":
                        usage = data.get("usage", {})
                        if usage:
                            return Usage(
                                output_tokens=usage.get("output_tokens", 0),
                            )
                    elif data.get("type") == "message_start":
                        msg = data.get("message", {})
                        usage = msg.get("usage", {})
                        if usage:
                            return Usage(
                                input_tokens=usage.get("input_tokens", 0),
                            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        return None


class GeminiUsageExtractor(UsageExtractor):
    """Gemini 用量提取器。

    Gemini 响应格式:
    "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 50, "totalTokenCount": 150}
    """

    protocol = "gemini"

    def extract_from_response(self, body: bytes) -> Usage:
        try:
            data = json.loads(body)
            meta = data.get("usageMetadata", {})
            return Usage(
                input_tokens=meta.get("promptTokenCount", 0),
                output_tokens=meta.get("candidatesTokenCount", 0),
                total_tokens=meta.get("totalTokenCount", 0),
                cached_tokens=meta.get("cachedContentTokenCount", 0),
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Usage()

    def extract_from_stream_chunk(self, chunk: bytes) -> Optional[Usage]:
        try:
            text = chunk.decode("utf-8")
            for line in text.split("\n"):
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if "usageMetadata" in data:
                        meta = data["usageMetadata"]
                        return Usage(
                            input_tokens=meta.get("promptTokenCount", 0),
                            output_tokens=meta.get("candidatesTokenCount", 0),
                            total_tokens=meta.get("totalTokenCount", 0),
                        )
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        return None


# 注册表
EXTRACTORS: dict[str, UsageExtractor] = {
    "openai": OpenAIUsageExtractor(),
    "anthropic": AnthropicUsageExtractor(),
    "gemini": GeminiUsageExtractor(),
}


def get_extractor(protocol: str) -> UsageExtractor:
    """获取指定协议的 Usage Extractor。"""
    return EXTRACTORS.get(protocol, OpenAIUsageExtractor())
