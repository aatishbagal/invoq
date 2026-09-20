from __future__ import annotations

import json
import logging
import re
from typing import Dict, List, Optional

from invoq.config import load_config
from invoq.core.executor import SafeExecutor
from invoq.core.history import CommandHistory
from invoq.core.validator import CommandValidator
from invoq.mcp.confirmation import ConfirmationHandler, ConfirmationResult
from invoq.mcp.registry import ToolRegistry, registry
from invoq.mcp.types import ToolCall, ToolDefinition, ToolResult

from invoq.mcp import tools as _tools  # noqa: F401 - import registers tools


logger = logging.getLogger(__name__)


class InvoqMCPServer:
    """MCP Server for invoq.

    Security boundary between the LLM and the system. All command-executing
    tool calls pass through a confirmation handler before reaching the
    executor.
    """

    def __init__(
        self,
        tool_registry: Optional[ToolRegistry] = None,
        validator: Optional[CommandValidator] = None,
        executor: Optional[SafeExecutor] = None,
        history: Optional[CommandHistory] = None,
        confirmation_handler: Optional[ConfirmationHandler] = None,
    ) -> None:
        self.registry = tool_registry or registry
        self.validator = validator or CommandValidator()
        self.history = history or CommandHistory()
        if executor is None:
            executor = SafeExecutor(self.validator, load_config(), history=self.history)
        self.executor = executor
        self.config = executor.config
        self.confirmation_handler = confirmation_handler or ConfirmationHandler(
            self.validator
        )
        if self.config.security.remediation_mode:
            logger.warning(
                "Running in remediation mode: all command execution requires manual approval."
            )

    def get_tools(self) -> List[ToolDefinition]:
        return self.registry.list_tools()

    def get_tools_for_ollama(self) -> List[Dict]:
        return self.registry.to_ollama_tools()

    async def handle_tool_call(self, call: ToolCall) -> ToolResult:
        if call.name == "execute_command":
            return await self._handle_execute_command(call)
        if call.name == "execute_script":
            return await self._handle_execute_script(call)
        return await self.registry.execute(call)

    async def handle_tool_calls(self, calls: List[ToolCall]) -> List[ToolResult]:
        results = []
        for call in calls:
            result = await self.handle_tool_call(call)
            results.append(result)
        return results

    async def _handle_execute_command(self, call: ToolCall) -> ToolResult:
        command = call.arguments.get("command", "")
        working_dir = call.arguments.get("working_dir")

        if not command:
            return ToolResult(
                call_id=call.call_id,
                success=False,
                output="",
                error="Missing 'command' argument",
            )

        validation = self.validator.validate(command)
        if not validation.allowed:
            return ToolResult(
                call_id=call.call_id,
                success=False,
                output="",
                error=f"BLOCKED: {validation.reason}",
            )

        confirmation = await self.confirmation_handler.request_confirmation(
            command=command,
            working_dir=working_dir,
            force_confirmation=self.config.security.remediation_mode,
        )

        if confirmation.result == ConfirmationResult.DENIED:
            return ToolResult(
                call_id=call.call_id,
                success=False,
                output="",
                error="Command cancelled by user.",
            )

        final_command = (
            confirmation.edited_command
            if confirmation.result == ConfirmationResult.EDITED
            and confirmation.edited_command
            else command
        )

        result = await self.executor.execute(
            command=final_command,
            working_dir=working_dir,
            skip_confirmation=True,
        )

        if result.was_blocked:
            return ToolResult(
                call_id=call.call_id,
                success=False,
                output="",
                error=f"BLOCKED: {result.block_reason}",
            )

        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR: {result.stderr}"

        return ToolResult(
            call_id=call.call_id,
            success=result.success,
            output=output,
            error=result.stderr if result.failed else None,
        )

    async def _handle_execute_script(self, call: ToolCall) -> ToolResult:
        script = call.arguments.get("script", "")
        working_dir = call.arguments.get("working_dir")

        if not script:
            return ToolResult(
                call_id=call.call_id,
                success=False,
                output="",
                error="Missing 'script' argument",
            )

        parsed_commands = self.executor._parse_script_commands(script)

        confirmation = await self.confirmation_handler.request_script_confirmation(
            script=script,
            parsed_commands=parsed_commands,
            working_dir=working_dir,
            force_confirmation=self.config.security.remediation_mode,
        )

        if confirmation.result == ConfirmationResult.DENIED:
            return ToolResult(
                call_id=call.call_id,
                success=False,
                output="",
                error="Script cancelled by user.",
            )

        result = await self.executor.execute_script(
            script=script,
            working_dir=working_dir,
            skip_confirmation=True,
        )

        if result.commands_blocked:
            return ToolResult(
                call_id=call.call_id,
                success=False,
                output="",
                error=f"BLOCKED: Script contains blocked commands: "
                f"{', '.join(result.commands_blocked)}",
            )

        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR: {result.stderr}"

        return ToolResult(
            call_id=call.call_id,
            success=result.success,
            output=output,
            error=result.stderr if not result.success else None,
        )

    def parse_ollama_tool_calls(self, response: Dict) -> List[ToolCall]:
        """Parse tool calls from Ollama response.

        Handles two formats:
        1. Native tool_calls field (newer models)
        2. JSON in message.content (qwen2.5-coder and similar)
        """
        tool_calls: List[ToolCall] = []
        message = response.get("message", {})

        native_calls = message.get("tool_calls", [])
        if native_calls:
            for call in native_calls:
                function = call.get("function", {})
                tool_calls.append(
                    ToolCall(
                        name=function.get("name", ""),
                        arguments=function.get("arguments", {}),
                        call_id=call.get("id"),
                    )
                )
            return tool_calls

        content = message.get("content", "")
        if content:
            parsed = self._parse_tool_call_from_content(content)
            if parsed:
                tool_calls.append(parsed)

        return tool_calls

    def _parse_tool_call_from_content(self, content: str) -> Optional[ToolCall]:
        """Try to extract a tool call from message content.

        Handles formats like:
        - {"name": "tool_name", "arguments": {...}}
        - ```json\n{"name": "tool_name", "arguments": {...}}\n```
        - tool_name({"arg": "value"})
        """
        content = content.strip()

        if content.startswith("```"):
            match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
            if match:
                content = match.group(1).strip()

        func_call = self._parse_function_call_syntax(content)
        if func_call is not None:
            return func_call

        try:
            data = json.loads(content)
            if isinstance(data, dict) and "name" in data:
                name = data.get("name", "")
                arguments = data.get("arguments", {})
                if self.registry.get(name):
                    return ToolCall(
                        name=name,
                        arguments=arguments if isinstance(arguments, dict) else {},
                        call_id=None,
                    )
        except json.JSONDecodeError:
            pass

        json_match = re.search(
            r'\{[^{}]*"name"\s*:\s*"[^"]+"[^{}]*"arguments"\s*:\s*\{[^{}]*\}[^{}]*\}',
            content,
        )
        if json_match:
            try:
                data = json.loads(json_match.group())
                name = data.get("name", "")
                if self.registry.get(name):
                    return ToolCall(
                        name=name,
                        arguments=data.get("arguments", {}),
                        call_id=None,
                    )
            except json.JSONDecodeError:
                pass

        return None

    def _parse_function_call_syntax(self, content: str) -> Optional[ToolCall]:
        """Parse `tool_name({json_args})` syntax emitted by some models."""
        match = re.search(r"\b([a-zA-Z_][\w]*)\s*\(", content)
        if not match:
            return None

        name = match.group(1)
        if not self.registry.get(name):
            return None

        start = content.find("(", match.end() - 1)
        if start == -1:
            return None

        depth = 0
        end = -1
        in_string = False
        escape = False
        for i in range(start, len(content)):
            ch = content[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = i
                    break

        if end == -1:
            return None

        inner = content[start + 1:end].strip()
        if not inner:
            return ToolCall(name=name, arguments={}, call_id=None)

        try:
            args = json.loads(inner)
        except json.JSONDecodeError:
            return None

        if not isinstance(args, dict):
            return None

        return ToolCall(name=name, arguments=args, call_id=None)


server = InvoqMCPServer()


__all__ = ["InvoqMCPServer", "server"]
