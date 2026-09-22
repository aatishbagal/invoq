# Configuration

invoq loads packaged defaults, then applies overrides from
`~/.config/invoq/config.yaml`. The reference defaults are in
[`config/default.yaml`](../config/default.yaml); the installed defaults are in
[`src/invoq/default.yaml`](../src/invoq/default.yaml).

```yaml
llm:
  backend: "ollama"
  model: "auto"
  api_url: "http://localhost:11434"

security:
  remediation_mode: true

extensions:
  enabled: []

setup_completed: false
```

The setup wizard saves the selected model and marks setup as completed.

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
