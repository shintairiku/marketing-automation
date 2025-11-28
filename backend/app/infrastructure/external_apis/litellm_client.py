# -*- coding: utf-8 -*-
"""LiteLLM thin wrapper for streaming chat completions (writing step専用)。"""

from typing import AsyncIterator, List, Dict, Any

from litellm import acompletion

from app.core.config import settings

Message = Dict[str, str]
DEFAULT_MAX_TOKENS = 32768


async def stream_chat_completion(messages: List[Message], **kwargs: Any) -> AsyncIterator[str]:
    """LiteLLM によるチャット補完ストリーム。

    Parameters
    ----------
    messages: List[Message]
        [{"role": "system"|"user"|"assistant", "content": str}, ...]
    **kwargs: Any
        LiteLLM にそのまま渡す追加パラメータ。
    """

    response = await acompletion(
        model=settings.writing_model,
        messages=messages,
        max_tokens=DEFAULT_MAX_TOKENS,
        stream=True,
        **kwargs,
    )

    async for chunk in response:
        delta = chunk["choices"][0]["delta"].get("content", "")
        if delta:
            yield delta
