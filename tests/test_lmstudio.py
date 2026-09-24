import json
from importlib import import_module
from unittest.mock import AsyncMock

import httpx
import pytest
from typer.testing import CliRunner

from invoq.config import Config, LLMConfig
from invoq.llm import get_llm_client
from invoq.llm.lmstudio import LMStudioClient
from invoq.mcp.client import MCPClient
from invoq.mcp.server import InvoqMCPServer
from invoq.mcp.types import ToolResult


MODEL = "local/test-model"
API_URL = "http://localhost:1234/v1"
TOOLS = [{"type": "function", "function": {
    "name": "read_file", "parameters": {"type": "object", "properties": {
        "path": {"type": "string"},
    }},
}}]


def completion(content="Hello", calls=None):
    message = {"role": "assistant", "content": content}
    if calls is not None:
        message["tool_calls"] = calls
    return {"model": MODEL, "choices": [{"message": message}]}


def tool_call(arguments='{"path": "example.txt"}'):
    return {"id": "call_123", "type": "function", "function": {
        "name": "read_file", "arguments": arguments,
    }}


@pytest.fixture
def mock_http(monkeypatch):
    client_class = httpx.AsyncClient
    requests = []

    def install(handler):
        def record(request):
            requests.append(request)
            return handler(request)

        monkeypatch.setattr(
            "invoq.llm.lmstudio.httpx.AsyncClient",
            lambda **kwargs: client_class(transport=httpx.MockTransport(record), **kwargs),
        )
        return requests

    return install


@pytest.fixture
def client():
    return LMStudioClient(MODEL, API_URL + "/")


@pytest.mark.asyncio
@pytest.mark.parametrize("system_prompt", [None, "Be concise"])
async def test_generate(client, mock_http, system_prompt):
    requests = mock_http(lambda _: httpx.Response(200, json=completion()))

    assert await client.generate("Hi", system_prompt) == "Hello"

    assert str(requests[0].url) == API_URL + "/chat/completions"
    assert requests[0].method == "POST"
    messages = [{"role": "user", "content": "Hi"}]
    if system_prompt:
        messages.insert(0, {"role": "system", "content": system_prompt})
    assert json.loads(requests[0].content) == {
        "model": MODEL, "messages": messages, "stream": False,
    }


@pytest.mark.asyncio
async def test_generate_stream(client, mock_http):
    events = [
        {"choices": [{"delta": {"role": "assistant", "content": None}}]},
        {"choices": [{"delta": {"content": "Hello"}}]},
        {"choices": [{"delta": {"content": " world"}}]},
        {"choices": [{"delta": {}, "finish_reason": "stop"}]},
        {"choices": [], "usage": {"total_tokens": 10}},
    ]
    body = ": keep-alive\n\n" + "".join(
        f"data: {json.dumps(event)}\n\n" for event in events
    ) + "data: [DONE]\n\n"
    requests = mock_http(lambda _: httpx.Response(
        200, text=body, headers={"content-type": "text/event-stream"},
    ))

    assert [part async for part in client.generate_stream("Hi", "Be concise")] == [
        "Hello", " world",
    ]
    payload = json.loads(requests[0].content)
    assert payload["stream"] is True
    assert payload["messages"][0] == {"role": "system", "content": "Be concise"}
    assert str(requests[0].url) == API_URL + "/chat/completions"


@pytest.mark.asyncio
@pytest.mark.parametrize("body,match", [
    ('data: {broken}\n\n', "invalid JSON"),
    ('data: {"choices": [{}]}\n\n', "invalid stream chunk"),
    ('data: {"choices": [{"delta": {"content": "partial"}}]}\n\n', "ended before"),
    ('data: {"error": {"message": "model unloaded"}}\n\n', "model unloaded"),
    ('data: {"choices": [{"delta": {"tool_calls": [{}]}}]}\n\n', "unexpected streaming tool"),
])
async def test_stream_errors(client, mock_http, body, match):
    mock_http(lambda _: httpx.Response(200, text=body))
    with pytest.raises(ValueError, match=match):
        _ = [part async for part in client.generate_stream("Hi")]


@pytest.mark.asyncio
async def test_models_and_connection(client, mock_http):
    info = {"id": MODEL, "object": "model", "owned_by": "organization-owner"}
    requests = mock_http(lambda _: httpx.Response(200, json={"data": [info]}))

    assert await client.check_connection() is True
    assert await client.list_models() == [MODEL]
    assert await client.get_model_info(MODEL) == info
    with pytest.raises(ValueError, match="not found or unavailable"):
        await client.get_model_info("missing")
    assert all(r.method == "GET" and str(r.url) == API_URL + "/models" for r in requests)


@pytest.mark.asyncio
async def test_empty_model_list_is_reachable(client, mock_http):
    mock_http(lambda _: httpx.Response(200, json={"data": []}))
    assert await client.check_connection() is True
    assert await client.list_models() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("error_class", [httpx.ConnectError, httpx.ReadTimeout])
async def test_connection_failures(client, mock_http, error_class):
    def fail(request):
        raise error_class("unavailable", request=request)

    mock_http(fail)
    assert await client.check_connection() is False
    for operation in [
        client.generate("Hi"), client.list_models(), client.get_model_info(MODEL),
        client.generate_with_tools("Hi", tools=TOOLS),
    ]:
        with pytest.raises(ConnectionError, match="LM Studio not reachable.*server running"):
            await operation
    with pytest.raises(ConnectionError, match="LM Studio not reachable"):
        _ = [part async for part in client.generate_stream("Hi")]


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 404, 500])
async def test_http_errors(client, mock_http, status):
    mock_http(lambda _: httpx.Response(status, json={"error": "server rejected request"}))
    assert await client.check_connection() is False
    with pytest.raises(ValueError, match=f"HTTP {status}"):
        await client.generate("Hi")
    with pytest.raises(ValueError, match=f"HTTP {status}"):
        _ = [part async for part in client.generate_stream("Hi")]


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [200, 400])
async def test_unsupported_tools_report_specific_error(client, mock_http, status):
    requests = mock_http(lambda _: httpx.Response(status, json={"error": {
        "message": "This model does not support tool calling",
    }}))
    with pytest.raises(ValueError, match="LM Studio tool-calling error.*support"):
        await client.generate_with_tools("Read file", tools=TOOLS)
    with pytest.raises(ValueError, match="LM Studio tool-calling error.*support"):
        await client.generate("Read file")
    assert len(requests) == 2
    assert json.loads(requests[0].content)["tools"] == TOOLS


@pytest.mark.asyncio
async def test_tool_response_normalized_for_mcp(client, mock_http):
    requests = mock_http(lambda _: httpx.Response(
        200, json=completion(None, [tool_call(), tool_call('{"path": "two.txt"}')]),
    ))
    response = await client.generate_with_tools("Read files", "Use tools", TOOLS)
    calls = InvoqMCPServer().parse_ollama_tool_calls(response)
    assert response["message"]["content"] == ""
    assert [call.arguments for call in calls] == [{"path": "example.txt"}, {"path": "two.txt"}]
    assert calls[0].call_id == "call_123"
    assert calls[0].name == "read_file"
    assert json.loads(requests[0].content)["tools"] == TOOLS


@pytest.mark.asyncio
async def test_no_tools_text_response(client, mock_http):
    requests = mock_http(lambda _: httpx.Response(200, json=completion()))
    response = await client.generate_with_tools("Hi", tools=[])
    assert response["message"]["content"] == "Hello"
    assert response["message"]["tool_calls"] == []
    assert "tools" not in json.loads(requests[0].content)


@pytest.mark.asyncio
@pytest.mark.parametrize("arguments", ["invalid", "[]", "null", "42", '"text"', None])
async def test_malformed_tool_arguments_fail_before_dispatch(client, mock_http, monkeypatch, arguments):
    mock_http(lambda _: httpx.Response(200, json=completion(None, [tool_call(arguments)])))
    server = InvoqMCPServer()
    dispatch = AsyncMock()
    monkeypatch.setattr(server, "handle_tool_call", dispatch)
    with pytest.raises(ValueError, match="malformed tool call"):
        await MCPClient(client, server).chat("Read file")
    dispatch.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [{}, {"choices": []}, {"choices": [{"message": None}]}])
async def test_malformed_completion(client, mock_http, response):
    mock_http(lambda _: httpx.Response(200, json=response))
    with pytest.raises(ValueError, match="invalid chat completion"):
        await client.generate("Hi")


@pytest.mark.asyncio
async def test_malformed_models(client, mock_http):
    mock_http(lambda _: httpx.Response(200, json={"data": [{}]}))
    assert await client.check_connection() is False
    with pytest.raises(ValueError, match="invalid model list"):
        await client.list_models()


@pytest.mark.asyncio
async def test_mcp_tool_loop_uses_existing_server(client, mock_http, tmp_path):
    path = tmp_path / "example.txt"
    path.write_text("sample file contents")
    replies = iter([
        completion(None, [tool_call(json.dumps({"path": str(path)}))]),
        completion("The file contains sample file contents."),
    ])
    requests = mock_http(lambda _: httpx.Response(200, json=next(replies)))
    result = await MCPClient(client, InvoqMCPServer()).chat_with_tool_loop("Read the file")
    assert result.response == "The file contains sample file contents."
    assert len(result.tool_calls) == 1
    assert result.tool_results[0].success
    assert "sample file contents" in result.tool_results[0].output
    assert "sample file contents" in json.loads(requests[1].content)["messages"][-1]["content"]


@pytest.mark.asyncio
async def test_mcp_without_tools(client, mock_http):
    requests = mock_http(lambda _: httpx.Response(200, json=completion()))
    result = await MCPClient(client, InvoqMCPServer()).chat("Explain this", use_tools=False)
    assert result.response == "Hello"
    assert result.tool_calls == []
    assert "tools" not in json.loads(requests[0].content)


def test_factory_selects_lmstudio_without_ollama_autoselection(monkeypatch):
    def forbidden():
        pytest.fail("LM Studio must not use Ollama's model selector")

    monkeypatch.setattr("invoq.llm.model_selector.get_recommended_model", forbidden)
    client = get_llm_client(Config(llm=LLMConfig(backend="lmstudio")))
    assert isinstance(client, LMStudioClient)


@pytest.mark.asyncio
async def test_lmstudio_requires_explicit_model(mock_http):
    requests = mock_http(lambda _: pytest.fail("No HTTP request expected"))
    client = get_llm_client(Config(llm=LLMConfig(backend="lmstudio")))
    with pytest.raises(ValueError, match="explicit llm.model"):
        await client.generate("Hi")
    assert requests == []


def test_ask_selects_lmstudio_and_dispatches_through_gate(mock_http, monkeypatch):
    cli = import_module("invoq.main")
    config = Config(llm=LLMConfig(backend="lmstudio", model=MODEL))
    requests = mock_http(lambda request: httpx.Response(200, json=(
        {"data": [{"id": MODEL}]} if request.method == "GET" else
        completion(None, [{"id": "call_gate", "function": {
            "name": "execute_command", "arguments": '{"command": "echo hello"}',
        }}])
    )))
    gate = AsyncMock(return_value=ToolResult(
        call_id="call_gate", success=False, output="", error="BLOCKED: test",
    ))
    monkeypatch.setattr(cli, "load_config", lambda: config)
    monkeypatch.setattr(cli, "is_first_run", lambda: False)
    monkeypatch.setattr(type(cli.mcp_server), "handle_tool_call", gate)

    result = CliRunner().invoke(cli.app, ["ask", "Say hello"])

    assert result.exit_code == 0, result.output
    gate.assert_awaited_once()
    assert gate.call_args.args[0].arguments == {"command": "echo hello"}
    assert "Blocked" in result.output
    assert all(str(request.url).startswith(API_URL) for request in requests)


@pytest.mark.parametrize("command", [["ask", "Hi"], ["explain", "echo hi"]])
def test_cli_connection_guidance_is_backend_specific(mock_http, monkeypatch, command):
    cli = import_module("invoq.main")
    mock_http(lambda _: httpx.Response(503, text="unavailable"))
    monkeypatch.setattr(cli, "load_config", lambda: Config(
        llm=LLMConfig(backend="lmstudio", model=MODEL),
    ))
    monkeypatch.setattr(cli, "is_first_run", lambda: False)

    result = CliRunner().invoke(cli.app, command)

    assert "LM Studio not reachable" in result.output
    assert "ollama serve" not in result.output


def test_explain_uses_lmstudio_without_exposing_tools(mock_http, monkeypatch):
    cli = import_module("invoq.main")
    requests = mock_http(lambda request: httpx.Response(200, json=(
        {"data": [{"id": MODEL}]} if request.method == "GET" else
        completion("This command prints hello.")
    )))
    monkeypatch.setattr(cli, "load_config", lambda: Config(
        llm=LLMConfig(backend="lmstudio", model=MODEL),
    ))
    monkeypatch.setattr(cli, "is_first_run", lambda: False)

    result = CliRunner().invoke(cli.app, ["explain", "echo hello"])

    assert result.exit_code == 0, result.output
    assert "This command prints hello." in result.output
    assert len(requests) == 2
    assert "tools" not in json.loads(requests[-1].content)


@pytest.mark.asyncio
async def test_lmstudio_setup_does_not_run_ollama_wizard(monkeypatch):
    setup = import_module("invoq.cli.setup_command")
    monkeypatch.setattr(setup, "load_config", lambda: Config(
        llm=LLMConfig(backend="lmstudio", model=MODEL),
    ))
    ollama_info = AsyncMock()
    monkeypatch.setattr(setup, "get_ollama_info", ollama_info)
    assert await setup.run_setup(skip_system_check=True) is False
    ollama_info.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("calls", [False, "", {}, "invalid", [None], [{}]])
async def test_invalid_tool_calls_are_rejected(client, mock_http, calls):
    mock_http(lambda _: httpx.Response(200, json=completion(None, calls)))
    with pytest.raises(ValueError, match="invalid tool call list|malformed tool call"):
        await client.generate_with_tools("Read file", tools=TOOLS)


@pytest.mark.asyncio
async def test_missing_reported_tool_calls_are_rejected(client, mock_http):
    response = completion()
    response["choices"][0]["finish_reason"] = "tool_calls"
    mock_http(lambda _: httpx.Response(200, json=response))
    with pytest.raises(ValueError, match="reported tool calls but returned none"):
        await client.generate_with_tools("Read file", tools=TOOLS)


@pytest.mark.asyncio
async def test_unsolicited_tools_are_rejected(client, mock_http):
    mock_http(lambda _: httpx.Response(200, json=completion(None, [tool_call()])))
    with pytest.raises(ValueError, match="when no tools were requested"):
        await client.generate_with_tools("Explain only")
    with pytest.raises(ValueError, match="unexpected tool calls"):
        await client.generate("Explain only")


@pytest.mark.asyncio
async def test_stream_handles_fragmented_utf8_and_closes(client, mock_http):
    class Stream(httpx.AsyncByteStream):
        closed = False

        async def __aiter__(self):
            body = 'data: {"choices": [{"delta": {"content": "café"}}]}\n\ndata: [DONE]\n\n'
            for byte in body.encode():
                yield bytes([byte])

        async def aclose(self):
            self.closed = True

    stream = Stream()
    mock_http(lambda _: httpx.Response(200, stream=stream))
    assert [part async for part in client.generate_stream("Hi")] == ["café"]
    assert stream.closed
