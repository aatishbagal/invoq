from pathlib import Path
import shlex
import sys

from invoq.shell.installation import install_shell_hooks, uninstall_shell_hooks

__all__ = ["bash_hook", "zsh_hook", "install_shell_hooks", "uninstall_shell_hooks"]


def _recorder() -> str:
    python = shlex.quote(sys.executable)
    helper = shlex.quote(str(Path(__file__).with_name("capture.py").resolve()))
    return f"""
_invoq_record_failure() {{
    if ! command {python} {helper} record "$1" "$2" "$3"; then
        if [ "${{_invoq_capture_warned-}}" != 1 ]; then
            printf '%s\\n' 'invoq: failed to save shell failure; check invoq shell status.' >&2
            _invoq_capture_warned=1
        fi
    fi
    return 0
}}
"""


def bash_hook() -> str:
    """Generate a Bash ERR hook without redirecting command stderr."""
    return r'''# invoq shell hook: bash
if [ -z "${BASH_VERSION-}" ] || [ "${_invoq_bash_loaded-}" = 1 ]; then
    return 0
fi
_invoq_bash_loaded=1
_invoq_previous_err=$(trap -p ERR)
if [ -n "$_invoq_previous_err" ]; then
    _invoq_previous_err=${_invoq_previous_err#trap -- }
    _invoq_previous_err=${_invoq_previous_err% ERR}
    eval "_invoq_previous_err=$_invoq_previous_err"
fi
''' + _recorder() + r'''
_invoq_restore_status() {
    return "$1"
}

_invoq_on_error() {
    local _invoq_status=$1 _invoq_command=$2 _invoq_cwd=$3
    local BASH_COMMAND=$_invoq_command
    shift 3
    if [ "${_invoq_in_error-}" = 1 ]; then
        return 0
    fi
    local _invoq_in_error=1
    if [ -n "$_invoq_previous_err" ]; then
        if _invoq_restore_status "$_invoq_status"; then
            eval -- "$_invoq_previous_err"
        else
            eval -- "$_invoq_previous_err"
        fi
    fi
    _invoq_record_failure "$_invoq_command" "$_invoq_status" "$_invoq_cwd"
    return 0
}

trap '_invoq_on_error "$?" "$BASH_COMMAND" "$PWD" "$@"' ERR
'''


def zsh_hook() -> str:
    """Generate Zsh hooks that preserve existing hook arrays."""
    return r'''# invoq shell hook: zsh
if [ -z "${ZSH_VERSION-}" ] || [ "${_invoq_zsh_loaded-}" = 1 ]; then
    return 0
fi
_invoq_zsh_loaded=1
''' + _recorder() + r'''
_invoq_preexec() {
    _invoq_command=$1
    _invoq_cwd=$PWD
    return 0
}

_invoq_precmd() {
    local _invoq_status=$?
    if [ -n "${_invoq_command-}" ]; then
        if [ "$_invoq_status" -ne 0 ]; then
            _invoq_record_failure "$_invoq_command" "$_invoq_status" "$_invoq_cwd"
        fi
        _invoq_command=''
    fi
    return 0
}

autoload -Uz add-zsh-hook
add-zsh-hook preexec _invoq_preexec
add-zsh-hook precmd _invoq_precmd
'''
