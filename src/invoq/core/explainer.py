from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from invoq.core.tiers import CommandTier
from invoq.core.validator import CommandValidator
from invoq.mcp.client import MCPClient
from invoq.prompts.system_prompts import build_explain_prompt


@dataclass
class ExplainResult:
    success: bool
    tier: str
    raw_explanation: str = ""
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


class CommandExplainer:
    def __init__(self, mcp_client: MCPClient, validator: CommandValidator) -> None:
        self.client = mcp_client
        self.validator = validator

    async def explain(self, command: str) -> ExplainResult:
        validation = self.validator.validate(command)
        tier = validation.tier.value
        warnings: List[str] = list(validation.warnings)

        if validation.tier == CommandTier.BLOCKED and validation.reason:
            warnings.insert(0, validation.reason)

        user_message = f"Explain this shell command:\n\n{command}"

        try:
            chat_result = await self.client.chat(
                user_message=user_message,
                system_prompt=build_explain_prompt(),
                use_tools=False,
            )
        except Exception as e:
            return ExplainResult(
                success=False,
                tier=tier,
                warnings=warnings,
                error=str(e),
            )

        explanation = (chat_result.response or "").strip()
        if not explanation:
            return ExplainResult(
                success=False,
                tier=tier,
                warnings=warnings,
                error="Model returned empty explanation.",
            )

        return ExplainResult(
            success=True,
            tier=tier,
            raw_explanation=explanation,
            warnings=warnings,
        )


__all__ = ["CommandExplainer", "ExplainResult"]
