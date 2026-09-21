# Server-owned tool capabilities

R.2 is a security fix. Every registered tool declares `ToolCapabilities`.
Execution permission follows that declaration, not the tool's name. The server
owns command validation, user confirmation, and the executor call.

## Registration contract

`ToolRegistry.register` now accepts declarations rather than arbitrary Python
callbacks. It rejects missing or untyped capabilities, duplicate names,
conflicting capabilities, missing validator hooks, callable hooks, and invalid
execution-parameter bindings. Registered definitions, capabilities, and bindings
are frozen.

There are two supported forms:

- A subprocess tool declares `ToolCapabilities(subprocess=True)` and an
  `ExecutionBinding` as its `validator_hook`. It supplies no handler. The binding
  maps declared string arguments into a command or script and optional working
  directory. It cannot execute code or replace the validator.
- A read-only tool declares `ToolCapabilities(subprocess=False)` and selects a
  `ReadOnlyOperation`: `READ_FILE`, `LIST_DIRECTORY`, or `GET_SYSTEM_INFO`.
  No validator hook is allowed. Dispatch uses the corresponding reviewed built-in
  implementation, not a function supplied during registration.

A handler cannot gain permission by declaring `subprocess=False`, adding a type
annotation, or passing a validator callback. Arbitrary Python handlers are
rejected even if they promise to call the validator. New read-only operations
require a reviewed implementation and a catalogue update.

Example execution declaration with a new tool name and argument name:

```python
from invoq.mcp import ExecutionBinding, ExecutionMode, ToolCapabilities
from invoq.mcp.registry import registry
from invoq.mcp.types import ToolParameter

registry.register(
    name="run_checked_task",
    description="Run a command after server validation and approval",
    capabilities=ToolCapabilities(subprocess=True),
    validator_hook=ExecutionBinding(ExecutionMode.COMMAND, "task_command", None),
    parameters=[ToolParameter("task_command", "string", "Command to run")],
)
```

Use `ExecutionMode.SCRIPT` for a complete script. To accept a working directory,
set `working_dir_parameter` to its declared string parameter name (the default
is `working_dir`). Using `None` omits that input.

This intentionally replaces the old decorator/callback registration API. It is
not a general extension manifest or loader. Loading untrusted Python modules
would execute their top-level code outside this contract and remains unsupported;
a future extension runtime needs isolation. This policy does not pretend to
sandbox Python that already runs inside the trusted application process.

## Execution boundary

All subprocess-capable tool names are resolved through the registry and use the
same server-owned handlers as the built-in execution tools. An unregistered name
cannot invoke a built-in execution path. Calling `ToolRegistry.execute` directly
for a subprocess tool returns a refusal; there is no approval flag to bypass it.

The server, executor, and confirmation handler must share the same validator
instance. Commands and entire scripts are validated before confirmation. Edited
commands are revalidated before execution. Unexpected confirmation results do not
authorize execution. The existing executor performs its own validation as well.

R.0 remediation mode continues to require manual approval for every allowed
execution call, including SAFE results and tools registered under new names.
With remediation mode disabled, the existing tier policy still applies. Bound
arguments cannot override the validator, confirmation handler, or execution flags.

The `execute_command` and `execute_script` Python convenience functions delegate
to the server. Their former independent executor and `get_executor` export have
been removed to close that alternate dispatch path. The three read-only tools
retain their existing behavior.

## Read-only tool audit and remaining gaps

The reviewed implementations do not launch subprocesses. They retain their
existing file/type/permission checks and error handling. The following gaps are
recorded, not fixed by R.2:

| Tool | Existing controls | Remaining gap |
| --- | --- | --- |
| `read_file` | Resolves paths, checks regular files, checks a 1 MB size limit before reading, defaults to 100 lines | No workspace-root restriction; absolute paths, `..`, `~`, and resolved symlinks can access any readable file. Stat/open races can change the target or size after checking. |
| `list_directory` | Resolves paths, checks directory type, handles permission errors, hides dotfiles by default | No workspace-root restriction; traversal and symlinks are unrestricted. Directory size/output is not bounded. |
| `get_system_info` | Returns a fixed set of OS and user-context fields | Reveals working directory, home path, username, and shell; there is no per-field disclosure policy. |

A workspace access boundary, symlink policy, race-resistant file access, and
output/disclosure limits require explicit filesystem-policy work. R.2 does not
claim that path resolution alone provides containment.

## Verification

Regression tests reject undeclared or falsely declared subprocess handlers,
callable hooks, direct registry execution, and name-based dispatch bypasses.
Additional tests exercise new command/script tool names, approval and denial,
blocked payloads, malformed arguments, edited commands, shared validators,
read-only dispatch, and shell convenience functions. Exploit payloads are never
executed; executors and subprocess calls are mocked in boundary tests.
