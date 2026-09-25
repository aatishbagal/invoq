# Shell hooks

Linux users of Bash or Zsh can enable local failed-command metadata capture:

```sh
invoq shell install
invoq shell status
invoq shell uninstall
```

Install detects the shell from `SHELL`, previews the script destination and exact
source line, and asks for confirmation before writing. It saves the script at
`~/.config/invoq/shell_hook.sh` and adds the source line to `~/.bashrc` or
`~/.zshrc`. Restart the shell or source that rc file to activate it. Repeated
installation and repeated sourcing do not duplicate registration. Uninstall
before switching the installed shell type.

Uninstall removes invoq's source line from both rc files and moves the script to
`~/.config/invoq/deprecated/`, following the project's file-preservation rule.
Existing sessions keep their loaded hooks until restarted. The failure log is
preserved. Status reports the script, rc source lines, and whether the nonempty
log was modified within the last 24 hours. It does not inspect another running
shell; no recent failures is also normal in a working installation.

## Captured data

Each failure appends a JSON object to
`~/.local/share/invoq/shell_failures.log`. The file is created with mode `0600`.
Existing log permissions are tightened to `0600`; concurrent writers use a file
lock. Command text can contain sensitive arguments, so treat this log as private.

```json
{"command":"false","exit_code":1,"stderr":null,"stderr_file":null,"stderr_captured":false,"cwd":"/home/user","timestamp":"2026-09-25T12:00:00+00:00"}
```

Stderr stays attached to its original destination. These hooks do not redirect
or mirror streams, create stderr temporary files, change prompts or aliases, or
enable shell options. Both stderr fields are null and `stderr_captured` is false.
A future debug feature may offer an explicitly approved rerun through
`SafeExecutor` to obtain fresh stderr; no rerun or analysis is implemented here.

Bash uses an `ERR` trap and reads the failed command from `BASH_COMMAND` without
installing a `DEBUG` trap. Existing DEBUG traps remain in place, and the existing
ERR handler runs before invoq's recorder with the original status and command.
Normal Bash ERR semantics apply: failures tested by `if`, `while`, `!`, or most
`&&`/`||` lists are not reported, and pipeline behavior follows the user's
`pipefail` setting. No additional trap inheritance is enabled. Bash records the
failing simple command, which can differ from the complete input line.

Zsh appends functions with `add-zsh-hook`, preserving existing `preexec` and
`precmd` functions and arrays. It records the input command line in `preexec`
and its final status at the next prompt. Intermediate failures in a command list
that ultimately succeeds are not recorded. An earlier framework hook that aborts
the hook chain can prevent capture; frameworks that replace traps or arrays
after invoq is loaded can also disable it. Keep the invoq source line after
framework initialization.

The hook uses the Python environment in which invoq was installed. If that
environment is moved or removed, reinstall the hooks. Capture errors report a
diagnostic without changing the failed command's exit status.

This baseline targets Linux. macOS Bash 3.2 compatibility and login-shell
`.bash_profile` installation, Windows integration, and Homebrew packaging are
separate follow-up work.
