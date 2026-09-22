# Command classification policy

R.1 is a security fix. SAFE applies only to understood, literal invocations of
read-only commands. Unsupported syntax is BLOCKED. An unknown executable keeps
its UNKNOWN tier for API compatibility and is denied (`allowed=False`).
CONFIRM always requires approval at the executor. R.0 remediation mode remains
enabled and also requires approval for SAFE MCP command and script calls.

## Supported shell syntax

The parser recognizes literal POSIX words, single and double quotes, escapes,
line continuations, comments, pipelines, `&&`, `||`, semicolons, newlines, and
background separators. It examines every segment. Quoted or escaped operators
are data; quoted and escaped executable names and flags are decoded before
checking policy. Command identity is case-sensitive.

Input/output redirection, append, descriptor duplication/closing, combined
stdout/stderr redirection, and redirect-only commands require confirmation.
Canonical blocked device and system-file destinations remain blocked, including
quoted or escaped targets. Background execution and explicit executable paths
also require confirmation. A path ending in `ls` is not sufficient to make it SAFE.

Expansions, variables, substitutions, globbing, unquoted braces and tildes,
assignments, subshells, process substitution, here-documents, here-strings,
control characters, incomplete quotes/escapes, and malformed command chains are
blocked. These constructs require a fuller shell parser before they can be
accepted. This is a constrained POSIX policy, not a general shell interpreter or
a PowerShell parser.

`execute_script` has a stricter R.3 contract: a single line of literal commands
joined only by `&&`, such as `echo one && echo two`. Newlines (including quoted
newlines and line continuations), shebangs, comments, pipelines, semicolons,
`||`, background operators, shell control syntax, and function definitions are
blocked. Expansions, assignments, process substitution, here-documents, and
here-strings are also blocked. Quoted or escaped syntax remains literal data.
Control words cannot be enabled through extension command registration.

Each command is independently validated before any command runs or the executor
requests confirmation. Literal POSIX redirections (`<`, `>`, `>>`, `<>`, `>&`,
`<&`, `>|`) retain their existing confirmation and destination checks, including
redirect-only commands. If any command is rejected, the entire list is rejected,
even with `skip_confirmation=True`.

The executor joins the validated commands with `&&` and uses its existing shell
command runner, stopping at the first failure. It no longer writes or executes
a temporary Bash file; `ScriptExecutionResult.script_path` is empty. Replace
previous multiline scripts with an explicit `&&` chain. `execute_command` and
the R.1 classifier retain their existing syntax policy.

## Audit of the previous SAFE list

Every previous SAFE entry was reviewed. The retained set is:

- File/text inspection: `cat`, `head`, `tail`, `grep`, `cut`, `wc`, `tr`, `stat`,
  `md5sum`, `sha256sum`.
- Directory/location inspection: `ls`, `pwd`, `locate`, `which`, `whereis`.
- System/user inspection: `whoami`, `id`, `groups`, `cal`, `uptime`, `df`, `du`,
  `free`, `ps`, `who`, `w`.
- Literal output, queries, and calculations: `echo`, `true`, `false`, `expr`,
  `seq`, `yes`, `help`, `type`, `printenv`.

The following now have a minimum CONFIRM tier, with stronger argument policies
where specified below:

| Programs | Reason for removal from SAFE |
| --- | --- |
| `awk`, `find`, `sed` | Embedded programs, subcommands, or mutation actions |
| `less`, `more`, `bat`, `man`, `info` | Shell escapes, pagers, or helper programs |
| `sort`, `uniq`, `diff`, `tree`, `file`, `lsof` | Output/cache writes, helper execution, or platform-specific behavior |
| `date`, `hostname`, `uname`, `top`, `htop` | System mutation or interactive/platform-dependent behavior |
| `alias`, `history`, `env`, `set`, `printf`, `test` | Shell state, wrappers, variable writes, or shell-dependent evaluation |

Python, Perl, Ruby, Node, PHP, Lua and related interpreters remain outside SAFE.
Additional awk/sed variants and `xargs` are explicitly covered.

## Argument policy

- Awk and sed programs, including program files, are blocked. This deliberately
  rejects read-only programs too: their embedded languages are not parsed.
- `find -exec`, `-execdir`, `-ok`, `-okdir`, and `-delete` are blocked. A literal
  query such as `find /tmp -name '*.py' -type f` requires confirmation.
- Interpreter options are blocked, including inline code, module execution,
  option clusters and standard-input selection. Literal script paths such as
  `python script.py` retain CONFIRM. The exact single arguments `--help` and
  `--version` are exceptions; they still do not become SAFE.
- Shells, command wrappers and `xargs` are blocked. `env` is allowed only with
  no arguments or a single `--help`/`--version` argument, at CONFIRM.
- Sort compression helpers, including abbreviated long options, are blocked.
- Viewer options and startup commands beginning with `-` or `+` are blocked,
  except a single `--help`/`--version`. Literal file/manual arguments require
  confirmation. This deliberately sacrifices some harmless options.

The existing destructive-operation regex blocks remain in place. The validator
also checks decoded command arguments and redirection targets, so quoting or
escaping a known destructive name/flag cannot hide it. These checks precede
extension allowances.

This policy does not sandbox approved commands, resolve filesystem symlinks,
or prove the identity of executables found through PATH. An approved script or
stateful tool can still run code. Registered tool dispatch is covered by the
[R.2 capability policy](security-tool-capabilities.md). Untrusted extension
loading and platform execution adapters remain separate remediation work.

## Regression validation

Tests never execute the exploit payloads. They check classification, parser
boundaries, and executor rejection with subprocesses mocked. Existing canonical
blocked-pattern tests remain unchanged. R.0 gate tests now simulate a SAFE
validator response so that the gate remains independently tested after the
classifier correctly rejects those payloads.
