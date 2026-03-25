<p align="center">
  <h1 align="center">pls</h1>
  <p align="center">Just say what you want. In your terminal.</p>
</p>

<p align="center">
  <a href="#install">Install</a> •
  <a href="#usage">Usage</a> •
  <a href="#providers">Providers</a> •
  <a href="#config">Config</a>
</p>

<p align="center">
  <img src="https://img.shields.io/pypi/v/pls-sh?color=blue&v=2" alt="PyPI">
  <img src="https://img.shields.io/pypi/pyversions/pls-sh?v=2" alt="Python">
  <img src="https://img.shields.io/github/license/salvy9978/pls" alt="License">
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/salvy9978/pls/main/demo.gif" alt="pls demo" width="600">
</p>

```
$ pls "compress all PNGs in this folder"

╭───────────────────────────────────────────────────────────╮
│ find . -name "*.png" -exec pngquant --quality=65-80 {} \; │
╰───────────────────────────────────────────────────────────╯

 Run it? (Y/n)

✓ Done.
```

---

## Install

```bash
pipx install pls-sh    # recommended
# or
pip install pls-sh
```

That's it. The command is `pls`.

## Usage

```bash
pls "find files bigger than 100MB"
pls "kill whatever is using port 3000"
pls "convert video.mp4 to gif"
pls "show disk usage sorted by size"
pls "rename all .jpeg files to .jpg"
```

Works offline by default with [Ollama](https://ollama.ai). No API key, no internet, no telemetry.

### Flags

```bash
pls "do something" --explain        # also explains what the command does
pls "do something" --yes            # skip confirmation, just run it
pls "do something" --dry-run        # show command but don't run it
pls "do something" --provider openai
pls "do something" --model gpt-4o
pls "do something" --api-url http://localhost:8080   # override URL on the fly
pls --last                          # show the last generated command
echo "do something" | pls           # pipe from stdin
```

### Safety

`pls` flags dangerous commands before running them. Stuff like `rm -rf`, `chmod 777`,
`dd`, piping random scripts into `bash` — all gets highlighted in red with a warning.
Dangerous commands flip the confirmation to opt-in (`y/N` instead of `Y/n`).

Press `e` at the confirmation prompt to edit the command before running it.

## Providers

**Ollama** is the default. Runs locally, no account needed.

```bash
# make sure ollama is running
ollama serve
ollama pull qwen3.5:2b

pls "list all docker containers"
# just works
```

**LM Studio**, **llama.cpp**, or any **OpenAI-compatible** server:

```bash
# LM Studio (runs on port 1234 by default)
pls config set default provider lmstudio

# any OpenAI-compatible endpoint (llama.cpp, vLLM, OpenRouter, etc.)
pls config set custom api_url http://localhost:8080
pls config set custom model my-model
pls config set custom api_key sk-...          # optional
pls config set default provider custom

`pls` automatically handles URL expansion — you can just provide the base host and port (e.g., `http://localhost:8080`), and it will correctly target the `/v1/chat/completions` endpoint.
```

**OpenAI** and **Anthropic** if you want cloud models:

```bash
# either set env vars
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

# or save them in config
pls config set openai api_key sk-...
pls config set anthropic api_key sk-ant-...

# then use them
pls "do something" --provider openai
pls "do something" --provider anthropic

# or set a default
pls config set default provider anthropic
```

## Config

Config lives in `~/.config/pls/config.toml`.

```bash
pls config show          # see current config
pls config set ...       # change a value
pls config reset         # back to defaults
```

## How it works

1. You type what you want in plain English (or any language, really)
2. `pls` grabs context — your OS, shell, what's in the current directory
3. Sends that + your request to the LLM
4. Shows you the command, asks for confirmation
5. Runs it

No history stored, no data sent anywhere (unless you use OpenAI/Anthropic).

## License

MIT
