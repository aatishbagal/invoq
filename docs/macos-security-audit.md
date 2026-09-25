# macOS platform and validator audit

This is the first macOS compatibility step. It adds macOS/BSD context and
explicit disk-destruction blocks; it does not establish full macOS execution
support. Shell hooks and packaging remain separate work.

## Platform context

`get_system_context()` recognizes `platform.system() == "Darwin"` and reports
the macOS product version, Darwin kernel release, and BSD userland to the ask,
explain, and debug prompt builders. Prompts no longer identify every host as
Linux or assume GNU-only options. The debug command remains unimplemented.

`get_system_info()` retains `os: Darwin` and the existing kernel fields, and
adds `os_name: macOS`, `macos_version`, and `userland: BSD`. Non-macOS detection
and fields retain their existing behavior. Windows and WSL guards are unchanged.

## Disk-operation policy

The following are explicitly BLOCKED on every host, before extension allowances:

- `diskutil erase*`, `partitionDisk`, and `zeroDisk`, including the APFS
  `eraseVolume` form. Quoted, escaped, explicit-path, and case variants are
  covered; the latter matters for case-insensitive macOS volumes.
- `newfs_*` filesystem formatters, including HFS, APFS, MS-DOS, ExFAT, UDF,
  and additional formatter names with the same prefix.
- Redirects and direct operands naming `/dev/diskN` or `/dev/rdiskN`, including
  partition suffixes such as `disk2s1` and `disk2s1s1`. Decoded quotes/escapes,
  redundant slashes, and literal `.`/`..` path components are checked using
  POSIX path normalization, independently of the host OS.

Device checks also cover output operands such as `cp image.bin /dev/disk2`,
`curl --output=/dev/rdisk2`, attached output options such as `-o/dev/disk2`,
and `tee /dev/disk2`. Direct device operands and input redirects are denied
conservatively too: the validator does not infer safe raw-device access from
arbitrary argument positions. Ordinary files and quoted explanatory command
strings retain their existing classification.

These checks do not resolve symlinks, relative paths against an execution
directory, or filesystem object identity. They are literal command validation,
not a device sandbox. Existing restrictions on expansions, wrappers, and
embedded programs remain in force.

Other macOS-native utilities, including `pbcopy`, `pbpaste`, `open`, `launchctl`,
`defaults`, and `softwareupdate`, are not added to SAFE or CONFIRM. Their
UNKNOWN tier is preserved for API compatibility and execution remains denied
with `allowed=False`. Non-destructive `diskutil` invocations are likewise not
newly enabled.

## BSD syntax audit

The audit used the installed macOS manuals on macOS 27.0: `sed(1)`, `find(1)`,
`awk(1)`, `diskutil(8)`, `newfs_apfs(8)`, and `zshmisc(1)`. Apple's published
[sed manual](https://github.com/apple-oss-distributions/text_cmds/blob/main/sed/sed.1)
and [find manual](https://github.com/apple-oss-distributions/shell_cmds/blob/main/find/find.1)
provide the corresponding source documentation. No destructive invocation was
executed to perform this audit.

| BSD invocation or behavior | Current classification and evidence |
| --- | --- |
| `sed -i '' 's/old/new/' file` | BLOCKED. BSD consumes a backup suffix, including an empty argument; the existing policy rejects embedded sed programs regardless of suffix syntax. |
| `sed -i .bak`, `-i.bak`, `-I ''`, and `-E -i '' -f script.sed` | BLOCKED. Separate/attached suffixes, continuous-file editing, and script files remain covered. |
| `find -exec` / `-execdir` with quoted `{}` and escaped `;`, or `{}` followed by `+` | BLOCKED. Both individual and batched execution forms are covered. |
| `find -ok`, `-okdir`, and `find -d . -delete` | BLOCKED. Interactive execution and depth-first deletion are prohibited independently of BSD traversal options. |
| `find -E`, `-x`, or `-f` with ordinary queries | CONFIRM. BSD query syntax never becomes SAFE. |
| `awk 'BEGIN { system("echo payload") }'`, output redirects inside awk, and `awk -f` | BLOCKED. BEGIN runs before input; system invokes a command; the policy rejects the embedded language rather than relying on GNU-specific parsing. |
| Ordinary file `>`, `>>`, `>|`, `2>`, `&>`, and `<>` redirects | CONFIRM. A shell redirection can write, truncate, or open a file for writing independently of the executable. |
| The same redirects targeting macOS disk devices | BLOCKED by the new device checks. |

Existing sed/find/awk restrictions already covered the audited BSD forms and
were not relaxed. Existing Linux blocked patterns and tests remain intact.

## Regression evidence

`tests/test_macos_security_regressions.py` belongs to the `security` marker and
has no host-based skips. Classification is checked with both Linux and Darwin
platform detection mocked. Platform-context tests mock the product and kernel
versions separately.

The initial regression run against the previous implementation had 207 failing
cases and 48 passing audit/compatibility cases. An additional 16 failing checks
exposed executable-case variants before that fix. The cases exercise explicit
blocked-pattern matches, decoded paths, and command/script dispatch through
the real MCP server. Subprocess entry points are guarded by mocks, confirmation
must never be reached for these payloads, and history uses a mock.

Run the focused audit and existing regression suites with:

```bash
python -m pytest tests/test_macos_security_regressions.py -q
python -m pytest -m security -q
python -m pytest -q
```
