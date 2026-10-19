"""Bedrock with reasoning effort for DeepSeek and Kimi, which Inspect's Bedrock provider does not
configure.

DeepSeek V3.2 on Bedrock returns a reasoning block only when the request carries
`reasoning_effort` (values: none, minimal, low, medium, high, xhigh, max). Inspect forwards that
field only for gpt-oss, Claude and Nova, so this subclass adds it for DeepSeek and leaves every
other model exactly as stock Bedrock. Use as `bedrock_reasoning/<model id>`. Importing this module
registers the provider (done in `perceived_oversight/__init__.py`).

DeepSeek sometimes closes its thinking with a literal `</thinking>` inside the reasoning block and
writes its answer there too (live probe, 1 of 2 tries), leaving the visible reply empty; the part
after the tag is moved back to a text block (`split_leaked_answer`).
"""

from __future__ import annotations

import re
from typing import Any

from inspect_ai.model import (
    ChatMessage,
    Content,
    ContentReasoning,
    ContentText,
    GenerateConfig,
    ModelAPI,
    ModelOutput,
    modelapi,
)
from inspect_ai.tool import ToolChoice, ToolInfo

PROVIDER = "bedrock_reasoning"
_CLOSING = re.compile(r"</think(?:ing)?>")


def split_leaked_answer(content: list[Content]) -> list[Content]:
    """Text after a closing thinking tag inside a reasoning block becomes a text block."""
    out: list[Content] = []
    leaked: list[Content] = []
    for block in content:
        if isinstance(block, ContentReasoning) and _CLOSING.search(block.reasoning):
            thought, answer = _CLOSING.split(block.reasoning, maxsplit=1)
            out.append(block.model_copy(update={"reasoning": thought.strip()}))
            if answer.strip():
                leaked.append(ContentText(text=answer.strip()))
        else:
            if leaked and not isinstance(block, ContentReasoning):
                out.extend(leaked)
                leaked = []
            out.append(block)
    return out + leaked


@modelapi(name=PROVIDER)
def bedrock_reasoning() -> type[ModelAPI]:
    from inspect_ai.model._providers.bedrock import BedrockAPI

    class BedrockReasoningAPI(BedrockAPI):
        def _deepseek(self) -> bool:
            """Models that take `reasoning_effort` here: DeepSeek (reasons only at high) and Kimi
            K3 (always thinks, max by default; pinned so the request log records it)."""
            name = self.model_name.lower()
            return "deepseek" in name or "kimi" in name

        def reasoning_config(self, config: GenerateConfig) -> dict[str, Any]:
            if self._deepseek():
                effort = config.reasoning_effort or config.effort
                return {"reasoning_effort": effort} if effort is not None else {}
            return super().reasoning_config(config)

        async def generate(
            self,
            input: list[ChatMessage],
            tools: list[ToolInfo],
            tool_choice: ToolChoice,
            config: GenerateConfig,
        ) -> Any:
            result = await super().generate(input, tools, tool_choice, config)
            output = result[0] if isinstance(result, tuple) else result
            if self._deepseek() and isinstance(output, ModelOutput):
                for choice in output.choices:
                    if isinstance(choice.message.content, list):
                        choice.message.content = split_leaked_answer(choice.message.content)
            return result

    return BedrockReasoningAPI
