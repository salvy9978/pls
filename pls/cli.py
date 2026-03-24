from __future__ import annotations

import os
import re
import sys

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

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

app = typer.Typer(add_completion=False, rich_markup_mode="rich")
config_app = typer.Typer(help="Manage pls configuration.")
app.add_typer(config_app, name="config")

console = Console()
err_console = Console(stderr=True)

_SUBCOMMANDS = {"config"}
_CACHE_DIR = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "pls")
_LAST_FILE = os.path.join(_CACHE_DIR, "last")


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
    with open(_LAST_FILE, "w") as f:
        f.write(command)


def _load_last() -> str | None:
    try:
        with open(_LAST_FILE) as f:
            return f.read().strip() or None
    except FileNotFoundError:
        return None


def _read_stdin() -> str | None:
    if sys.stdin.isatty():
        return None
    return sys.stdin.read().strip() or None


def _display_command(command: str, risk: RiskLevel) -> None:
    border_style = {
        RiskLevel.SAFE: "green",
        RiskLevel.CAUTION: "yellow",
        RiskLevel.DANGEROUS: "red bold",
    }[risk]
    syntax = Syntax(command, "bash", theme="monokai", line_numbers=False, word_wrap=True)
    console.print(Panel(syntax, border_style=border_style, padding=(0, 1)))


def _display_warnings(warnings: list[str], risk: RiskLevel) -> None:
    if not warnings:
        return
    icon = "[yellow]\u26a0[/yellow]" if risk == RiskLevel.CAUTION else "[red bold]\u2620[/red bold]"
    label = "Caution" if risk == RiskLevel.CAUTION else "DANGEROUS"
    console.print(f"\n {icon} [bold]{label}:[/bold] {', '.join(warnings)}")


def _confirm_execution(risk: RiskLevel) -> bool:
    if risk == RiskLevel.DANGEROUS:
        console.print("\n [red bold]Run this dangerous command?[/red bold] [dim](y/N)[/dim] ", end="")
        return input().strip().lower() == "y"
    console.print("\n Run it? [dim](Y/n)[/dim] ", end="")
    return input().strip().lower() != "n"


def _show_help() -> None:
    console.print("[bold]pls[/bold] — Terminal in natural language.\n")
    console.print("Usage: [green]pls what you want to do[/green]")
    console.print("       [green]pls \"what you want to do\"[/green]\n")
    console.print("Examples:")
    console.print("  pls [dim]find all files bigger than 100MB[/dim]")
    console.print("  pls [dim]compress all PNGs in this folder[/dim]")
    console.print("  pls [dim]show disk usage sorted by size[/dim]")
    console.print("  echo [dim]\"kill port 3000\" | pls[/dim]\n")
    console.print("Options: --yes, --explain, --dry-run, --last, --provider, --model, --version")
    console.print("Config:  pls config show")


def _run_request(
    request: str,
    yes: bool = False,
    explain: bool = False,
    dry_run: bool = False,
    provider_override: str | None = None,
    model_override: str | None = None,
) -> None:
    config = load_config()
    provider_name = provider_override or get_provider_name(config)

    if model_override:
        config.setdefault(provider_name, {})["model"] = model_override

    try:
        llm = get_provider(provider_name, config)
    except ProviderError as e:
        err_console.print(f"[red bold]Error:[/red bold] {e}")
        sys.exit(1)

    context = gather()
    system_prompt = build_system_prompt(context, explain=explain)
    user_message = build_user_message(request)

    with console.status("[bold blue]Thinking...", spinner="dots"):
        try:
            raw_response = llm.generate(system_prompt, user_message)
        except ProviderError as e:
            err_console.print(f"\n[red bold]Error:[/red bold] {e}")
            sys.exit(1)

    command = _clean_command(raw_response)
    if not command:
        err_console.print("[yellow]No command generated. Try rephrasing your request.[/yellow]")
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
        console.print(f"\n[dim]{explanation}[/dim]")

    if dry_run:
        return

    if not yes:
        if not _confirm_execution(safety.level):
            console.print("[dim]Cancelled.[/dim]")
            return
    elif safety.level == RiskLevel.DANGEROUS:
        err_console.print(
            "[red bold]Refusing to auto-run dangerous command. Remove --yes or review manually.[/red bold]"
        )
        sys.exit(1)

    console.print()
    result = run(command)

    if result.interrupted:
        console.print("\n[yellow]Interrupted.[/yellow]")
    elif result.exit_code == 0:
        console.print(f"\n[green bold]\u2713 Done.[/green bold]")
    elif result.exit_code >= 126:
        console.print(f"\n[red bold]\u2717 Failed[/red bold] [dim](exit code {result.exit_code})[/dim]")
    else:
        console.print(f"\n[dim]Done (exit code {result.exit_code})[/dim]")

    sys.exit(result.exit_code)


@config_app.command("show")
def config_show() -> None:
    config = load_config()
    for sect, values in config.items():
        console.print(f"[bold cyan][{sect}][/bold cyan]")
        if isinstance(values, dict):
            for k, v in values.items():
                display_v = "****" if "key" in k and v else v
                console.print(f"  {k} = {display_v}")
        console.print()


@config_app.command("set")
def config_set(
    section: str = typer.Argument(help="Config section (e.g., default, ollama, openai)"),
    key: str = typer.Argument(help="Config key"),
    value: str = typer.Argument(help="Config value"),
) -> None:
    set_config_value(section, key, value)
    console.print(f"[green]\u2713[/green] Set {section}.{key}")


@config_app.command("get")
def config_get(
    section: str = typer.Argument(help="Config section"),
    key: str = typer.Argument(help="Config key"),
) -> None:
    config = load_config()
    val = config.get(section, {}).get(key, "")
    console.print(val or "[dim](not set)[/dim]")


@config_app.command("reset")
def config_reset() -> None:
    from pls.config import DEFAULT_CONFIG, save_config
    save_config(DEFAULT_CONFIG)
    console.print("[green]\u2713[/green] Config reset to defaults.")


def main() -> None:
    args = sys.argv[1:]

    if not args or args == ["--help"]:
        _show_help()
        return

    if args[0] == "--version" or args[0] == "-v":
        console.print(f"pls [bold]{__version__}[/bold]")
        return

    if args[0] == "--last":
        last = _load_last()
        if last:
            console.print(last)
        else:
            err_console.print("[dim]No previous command.[/dim]")
        return

    if args[0] in _SUBCOMMANDS:
        app()
        return

    request_parts: list[str] = []
    yes = False
    explain = False
    dry_run = False
    provider_val: str | None = None
    model_val: str | None = None

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
    )
