"""Command-line interface for pls."""

from __future__ import annotations

import os
import re
import sys

from pls import __version__
from pls.config import (
    get_provider_name,
    load_config,
    set_config_value,
)
from pls.context import gather
from pls.executor import run
from pls.prompt import build_system_prompt, build_user_message
from pls.providers import ProviderError, get_provider
from pls.safety import RiskLevel, analyze

_SUBCOMMANDS = {"config"}
_CACHE_DIR = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "pls")
_LAST_FILE = os.path.join(_CACHE_DIR, "last")

_CONSOLE = None
_ERR_CONSOLE = None


def _get_console():
    global _CONSOLE
    if _CONSOLE is None:
        from rich.console import Console
        _CONSOLE = Console()
    return _CONSOLE


def _get_err_console():
    global _ERR_CONSOLE
    if _ERR_CONSOLE is None:
        from rich.console import Console
        _ERR_CONSOLE = Console(stderr=True)
    return _ERR_CONSOLE


def _clean_command(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    if cleaned.startswith("`") and cleaned.endswith("`"):
        cleaned = cleaned[1:-1]
    cleaned = re.sub(r"\s*#\s*WARNING:.*$", "", cleaned, flags=re.MULTILINE).strip()
    return cleaned


def _save_last(command: str) -> None:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    with open(_LAST_FILE, "w", encoding="utf-8") as f:
        f.write(command)


def _load_last() -> str | None:
    try:
        with open(_LAST_FILE, encoding="utf-8") as f:
            return f.read().strip() or None
    except FileNotFoundError:
        return None


def _read_stdin() -> str | None:
    if sys.stdin.isatty():
        return None
    return sys.stdin.read().strip() or None


def _display_command(command: str, risk: RiskLevel) -> None:
    from rich.panel import Panel
    from rich.syntax import Syntax

    border_style = {
        RiskLevel.SAFE: "green",
        RiskLevel.CAUTION: "yellow",
        RiskLevel.DANGEROUS: "red bold",
    }[risk]
    syntax = Syntax(command, "bash", theme="monokai", line_numbers=False, word_wrap=True)
    _get_console().print(Panel(syntax, border_style=border_style, padding=(0, 1)))


def _display_warnings(warnings: list[str], risk: RiskLevel) -> None:
    if not warnings:
        return
    icon = "[yellow]\u26a0[/yellow]" if risk == RiskLevel.CAUTION else "[red bold]\u2620[/red bold]"
    label = "Caution" if risk == RiskLevel.CAUTION else "DANGEROUS"
    _get_console().print(f"\n {icon} [bold]{label}:[/bold] {', '.join(warnings)}")


def _confirm_execution(risk: RiskLevel) -> str:
    if risk == RiskLevel.DANGEROUS:
        _get_console().print("\n [red bold]Run this dangerous command?[/red bold] [dim](y/N/e)[/dim] ", end="")
        choice = input().strip().lower()
        if choice == "y":
            return "run"
        if choice == "e":
            return "edit"
        return "cancel"
    _get_console().print("\n Run it? [dim](Y/n/e)[/dim] ", end="")
    choice = input().strip().lower()
    if choice == "n":
        return "cancel"
    if choice == "e":
        return "edit"
    return "run"


def _edit_command(command: str) -> str | None:
    import readline
    readline.set_startup_hook(lambda: readline.insert_text(command))
    try:
        _get_console().print("\n [dim]Edit command (press Enter to run):[/dim]")
        edited = input(" $ ").strip()
        return edited if edited else None
    except (EOFError, KeyboardInterrupt):
        return None
    finally:
        readline.set_startup_hook()


def _show_help() -> None:
    c = _get_console()
    c.print("[bold]pls[/bold] — Terminal in natural language.\n")
    c.print("Usage: [green]pls what you want to do[/green]")
    c.print("       [green]pls \"what you want to do\"[/green]\n")
    c.print("Examples:")
    c.print("  pls [dim]find all files bigger than 100MB[/dim]")
    c.print("  pls [dim]compress all PNGs in this folder[/dim]")
    c.print("  pls [dim]show disk usage sorted by size[/dim]")
    c.print("  echo [dim]\"kill port 3000\" | pls[/dim]\n")
    c.print("Options: --yes, --explain, --dry-run, --last, --provider, --model, --version")
    c.print("Config:  pls config show")


def _run_request(
    request: str,
    yes: bool = False,
    explain: bool = False,
    dry_run: bool = False,
    provider_override: str | None = None,
    model_override: str | None = None,
    api_url_override: str | None = None,
) -> None:
    config = load_config()
    provider_name = provider_override or get_provider_name(config)

    if model_override:
        config.setdefault(provider_name, {})["model"] = model_override
    if api_url_override:
        config.setdefault(provider_name, {})["api_url"] = api_url_override

    try:
        llm = get_provider(provider_name, config)
    except ProviderError as e:
        _get_err_console().print(f"[red bold]Error:[/red bold] {e}")
        sys.exit(1)

    context = gather()
    system_prompt = build_system_prompt(context, explain=explain)
    user_message = build_user_message(request)

    with _get_console().status("[bold blue]Thinking...", spinner="dots"):
        try:
            raw_response = llm.generate(system_prompt, user_message)
        except ProviderError as e:
            _get_err_console().print(f"\n[red bold]Error:[/red bold] {e}")
            sys.exit(1)

    command = _clean_command(raw_response)
    if not command:
        _get_err_console().print("[yellow]No command generated. Try rephrasing your request.[/yellow]")
        sys.exit(1)

    explanation = ""
    if explain and "\n" in raw_response:
        parts = raw_response.split("\n", 1)
        command = _clean_command(parts[0])
        explanation = parts[1].strip()

    _save_last(command)

    safety = analyze(command)
    _display_command(command, safety.level)
    _display_warnings(safety.warnings, safety.level)

    if explanation:
        _get_console().print(f"\n[dim]{explanation}[/dim]")

    if dry_run:
        return

    if not yes:
        choice = _confirm_execution(safety.level)
        if choice == "cancel":
            _get_console().print("[dim]Cancelled.[/dim]")
            return
        if choice == "edit":
            edited = _edit_command(command)
            if not edited:
                _get_console().print("[dim]Cancelled.[/dim]")
                return
            command = edited
            _save_last(command)
    elif safety.level == RiskLevel.DANGEROUS:
        _get_err_console().print(
            "[red bold]Refusing to auto-run dangerous command. Remove --yes or review manually.[/red bold]"
        )
        sys.exit(1)

    _get_console().print()
    result = run(command)

    c = _get_console()
    if result.interrupted:
        c.print("\n[yellow]Interrupted.[/yellow]")
    elif result.exit_code == 0:
        c.print("\n[green bold]\u2713 Done.[/green bold]")
    elif result.exit_code >= 126:
        c.print(f"\n[red bold]\u2717 Failed[/red bold] [dim](exit code {result.exit_code})[/dim]")
    else:
        c.print(f"\n[dim]Done (exit code {result.exit_code})[/dim]")

    sys.exit(result.exit_code)


def _run_config_command() -> None:
    """Build and run the Typer config app — only called for 'pls config ...'."""
    import typer

    app = typer.Typer(add_completion=False, rich_markup_mode="rich")
    config_app = typer.Typer(help="Manage pls configuration.")
    app.add_typer(config_app, name="config")

    @config_app.command("show")
    def config_show() -> None:
        c = _get_console()
        config = load_config()
        for sect, values in config.items():
            c.print(f"[bold cyan][{sect}][/bold cyan]")
            if isinstance(values, dict):
                for k, v in values.items():
                    display_v = "****" if "key" in k and v else v
                    c.print(f"  {k} = {display_v}")
            c.print()

    @config_app.command("set")
    def config_set(
        section: str = typer.Argument(help="Config section (e.g., default, ollama, openai)"),
        key: str = typer.Argument(help="Config key"),
        value: str = typer.Argument(help="Config value"),
    ) -> None:
        set_config_value(section, key, value)
        _get_console().print(f"[green]\u2713[/green] Set {section}.{key}")

    @config_app.command("get")
    def config_get(
        section: str = typer.Argument(help="Config section"),
        key: str = typer.Argument(help="Config key"),
    ) -> None:
        config = load_config()
        val = config.get(section, {}).get(key, "")
        _get_console().print(val or "[dim](not set)[/dim]")

    @config_app.command("reset")
    def config_reset() -> None:
        from pls.config import DEFAULT_CONFIG, save_config
        save_config(DEFAULT_CONFIG)
        _get_console().print("[green]\u2713[/green] Config reset to defaults.")

    app()


def main() -> None:
    """Main entry point for the pls CLI."""
    args = sys.argv[1:]

    if not args or args == ["--help"]:
        _show_help()
        return

    if args[0] == "--version" or args[0] == "-v":
        _get_console().print(f"pls [bold]{__version__}[/bold]")
        return

    if args[0] == "--last":
        last = _load_last()
        if last:
            _get_console().print(last)
        else:
            _get_err_console().print("[dim]No previous command.[/dim]")
        return

    if args[0] in _SUBCOMMANDS:
        _run_config_command()
        return

    request_parts: list[str] = []
    yes = False
    explain = False
    dry_run = False
    provider_val: str | None = None
    model_val: str | None = None
    api_url_val: str | None = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--yes", "-y"):
            yes = True
        elif arg in ("--explain", "-e"):
            explain = True
        elif arg in ("--dry-run", "-n"):
            dry_run = True
        elif arg in ("--provider", "-p") and i + 1 < len(args):
            i += 1
            provider_val = args[i]
        elif arg in ("--model", "-m") and i + 1 < len(args):
            i += 1
            model_val = args[i]
        elif arg in ("--api-url", "-u") and i + 1 < len(args):
            i += 1
            api_url_val = args[i]
        elif not arg.startswith("-"):
            request_parts.append(arg)
        i += 1

    request = " ".join(request_parts)

    if not request:
        piped = _read_stdin()
        if piped:
            request = piped
        else:
            _show_help()
            return

    _run_request(
        request,
        yes=yes,
        explain=explain,
        dry_run=dry_run,
        provider_override=provider_val,
        model_override=model_val,
        api_url_override=api_url_val,
    )
