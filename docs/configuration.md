# Configuration

invoq loads packaged defaults, then applies overrides from
`~/.config/invoq/config.yaml`. The reference defaults are in
[`config/default.yaml`](../config/default.yaml); the installed defaults are in
[`src/invoq/default.yaml`](../src/invoq/default.yaml).

```yaml
llm:
  backend: "ollama"
  model: "auto"
  api_url: null

security:
  remediation_mode: true

extensions:
  enabled: []

setup_completed: false
```

The Ollama setup wizard saves the selected model and marks setup as completed.

## LLM backends

`llm.backend` accepts `ollama` (default) and `lmstudio`. Omitting `api_url`,
or setting it to `null`, selects the backend's default: `http://localhost:11434`
for Ollama and `http://localhost:1234/v1` for LM Studio. An explicit URL is
always preserved, including URLs in configurations previously saved by setup.
When switching an existing configuration to LM Studio, remove the old Ollama
URL or replace it with the LM Studio URL.

To use LM Studio, start its local server in the Developer tab, make a model
available, and merge these settings into `~/.config/invoq/config.yaml`:

```yaml
llm:
  backend: "lmstudio"
  model: "your-model-identifier"
  api_url: "http://localhost:1234/v1"

setup_completed: true
```

Use an identifier returned by `GET http://localhost:1234/v1/models` as the model
name. With Just-In-Time loading enabled, the list can also include downloaded
models. `model: auto` and automatic model installation remain Ollama-only;
configure LM Studio manually instead of using `invoq setup`.

`ask` and `explain` use the selected backend. The MCP tool execution, validation,
and confirmation rules apply to both backends. `debug` remains unimplemented.
The client uses async HTTP requests to `/v1/chat/completions` for generation
and streaming, and `/v1/models` for connection checks, discovery, and model
metadata. Model metadata is the matching entry from that list, without
Ollama-specific details. The client assumes the local server does not require
authentication; token configuration is not currently supported.

LM Studio supports native and fallback tool calling; choose a model with native
tool support for best results. Server-reported tool incompatibility raises a
specific error, and malformed structured tool calls are rejected before dispatch.
The OpenAI-compatible model list does not advertise a reliable tool capability
flag, so invoq does not infer incompatibility merely from a text-only response.
It never retries a rejected tool request with tools removed.

See the official [chat completions](https://lmstudio.ai/docs/developer/openai-compat/chat-completions),
[model listing](https://lmstudio.ai/docs/developer/openai-compat/models), and
[tool use](https://lmstudio.ai/docs/developer/openai-compat/tools) documentation.

Extensions are not yet implemented; the framework is deferred to Phase 6.
`extensions.enabled` is reserved and does not load or activate any extension.
Existing lists (including `git`) are preserved when saving configuration but
have no effect. New configurations enable no extensions. `invoq extensions list`
reports the unimplemented status and exits with a nonzero code.

## Execution policy

`security.remediation_mode` defaults to `true` and must be a YAML boolean.
It requires manual approval for every allowed command or script submitted
through the MCP tool gate, including SAFE commands. When disabled, SAFE calls
can proceed automatically; CONFIRM calls still require approval. BLOCKED and
UNKNOWN commands cannot execute in either mode.

Confirmation and explanation display are not configurable. Command previews,
validation information, and warnings retain their existing behavior. There is
no sudo-bypass feature. The classifier and MCP tool policy are described in
[Classification policy](security-classification.md) and
[Tool capability policy](security-tool-capabilities.md).

## Migrate existing configurations

R.5 removes the entire `execution` section because its settings were loaded but
never enforced. Loading any config containing that section now raises a
`ValueError` with migration guidance, including when the section is empty.

Remove the `execution` section and its nested entries from
`~/.config/invoq/config.yaml`, preserve your other settings, and restart invoq.
Do not move its entries elsewhere or replace them with new toggles. The loader
does not rewrite your config, and newly saved configs omit the removed section.
Keep `security.remediation_mode: true` for the default manual approval policy.
