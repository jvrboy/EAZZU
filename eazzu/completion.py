"""Shell-completion script generator for EAZZU.

Supports bash, zsh, and fish. The generated scripts call ``eazzu
--_complete`` which is an internal argparse-driven completion hook.

Usage:
    eazzu --install-completion [bash|zsh|fish]
    eval "$(eazzu --_completion-script bash)"  # one-shot load
"""
from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path
from typing import Iterable


BASH_SCRIPT = """# EAZZU bash completion — append to ~/.bashrc or source directly.
_eazzu_completions() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local IFS=$'\\n'
    local replies=$(COMP_LINE="$COMP_LINE" COMP_POINT="$COMP_POINT" eazzu --_complete 2>/dev/null)
    COMPREPLY=( $(compgen -W "${replies}" -- "${cur}") )
}
complete -o default -F _eazzu_completions eazzu
"""


ZSH_SCRIPT = """#compdef eazzu
# EAZZU zsh completion — drop in a directory in $fpath named _eazzu.
_eazzu() {
    local -a replies
    local IFS=$'\\n'
    replies=( ${(f)"$(COMP_LINE="$words" COMP_POINT=0 eazzu --_complete 2>/dev/null)"} )
    _describe 'eazzu' replies
}
compdef _eazzu eazzu
"""


FISH_SCRIPT = """# EAZZU fish completion — save as ~/.config/fish/completions/eazzu.fish
complete -c eazzu -f -a '(eval (string join " " (commandline -opc)) --_complete 2>/dev/null)'
"""


SCRIPTS = {"bash": BASH_SCRIPT, "zsh": ZSH_SCRIPT, "fish": FISH_SCRIPT}


def print_script(shell: str) -> int:
    if shell not in SCRIPTS:
        print(f"unknown shell {shell!r}; supported: {', '.join(SCRIPTS)}", file=sys.stderr)
        return 2
    print(SCRIPTS[shell])
    return 0


def install(shell: str | None = None) -> int:
    """Append completion script to the appropriate rc file."""
    if shell is None:
        shell = _detect_shell()
    if shell not in SCRIPTS:
        print(f"couldn't detect shell; pass one of: {', '.join(SCRIPTS)}", file=sys.stderr)
        return 2

    rc = {
        "bash": Path.home() / ".bashrc",
        "zsh": Path.home() / ".zshrc",
        "fish": Path.home() / ".config" / "fish" / "completions" / "eazzu.fish",
    }[shell]

    script = SCRIPTS[shell]
    if rc.exists() and f"EAZZU {shell} completion" in rc.read_text(encoding="utf-8", errors="ignore"):
        print(f"completion already installed in {rc}")
        return 0

    rc.parent.mkdir(parents=True, exist_ok=True)
    with rc.open("a", encoding="utf-8") as f:
        f.write(f"\n# EAZZU {shell} completion\n{script}\n")
    print(f"Installed {shell} completion into {rc}")
    if shell in {"bash", "zsh"}:
        print(f"Reload your shell or run:  source {rc}")
    return 0


def _detect_shell() -> str:
    shell = os.environ.get("SHELL", "")
    for candidate in ("bash", "zsh", "fish"):
        if candidate in shell:
            return candidate
    return "bash"


def do_complete() -> int:
    """Called by the shell to emit completions for the current command line.

    Uses ``COMP_LINE`` / ``sys.argv`` context to figure out the partial word
    and emits matching flags/subcommands/choices one per line.
    """
    from eazzu.cli import build_parser

    line = os.environ.get("COMP_LINE", "")
    words = shlex.split(line) if line else sys.argv[1:]
    # Drop the program name
    if words and words[0] == "eazzu":
        words = words[1:]
    # The word being typed is the last token in COMP_LINE if COMP_LINE ends in
    # whitespace we complete the next positional; otherwise we complete the last word.
    partial = ""
    if line and not line.rstrip().endswith(" ") and words:
        partial = words[-1]
        words = words[:-1]

    parser = build_parser()

    # Walk subparsers.
    completions: list[str] = []
    current = parser
    sub_action = None
    for a in current._actions:
        if a.dest == "cmd" and hasattr(a, "choices"):
            sub_action = a
            break

    i = 0
    while i < len(words):
        w = words[i]
        if sub_action and w in sub_action.choices:
            current = sub_action.choices[w]
            sub_action = None
            # Look for the next level of subparser.
            for a in current._actions:
                if isinstance(a, type(sub_action)) if sub_action else False:
                    pass
                from argparse import _SubParsersAction
                if isinstance(a, _SubParsersAction):
                    sub_action = a
                    break
        else:
            # Skip flags + their values
            if w.startswith("-"):
                action = next((a for a in current._actions if w in a.option_strings), None)
                if action and action.nargs in (None, "?"):
                    pass
                elif action and action.type is not None:
                    i += 1  # skip value
        i += 1

    # Collect completions from the current parser
    for a in current._actions:
        if a.option_strings:
            completions.extend(a.option_strings)
        if hasattr(a, "choices") and a.choices and not a.option_strings:
            # Positional with choices (like subcommand names)
            completions.extend(a.choices.keys() if isinstance(a.choices, dict) else a.choices)
    if sub_action is not None and hasattr(sub_action, "choices"):
        completions.extend(sub_action.choices.keys())

    # Filter by partial prefix
    if partial:
        completions = [c for c in completions if c.startswith(partial)]
    # Deduplicate and print
    for c in sorted(set(completions)):
        print(c)
    return 0


__all__ = ["print_script", "install", "do_complete", "SCRIPTS"]
