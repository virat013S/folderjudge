# ⚖️ FolderJudge

[![tests](https://github.com/virat013S/folderjudge/actions/workflows/tests.yml/badge.svg)](https://github.com/virat013S/folderjudge/actions/workflows/tests.yml)

**An AI judge for your messy folders.** It sees your Downloads. It has opinions.
It sentences the crooked files, archives the antiques, keeps the innocent — and
*nothing is deleted*, ever. Everything goes to its own trash with a manifest,
and `folderjudge restore` puts the world back exactly how it was.

Runs 100% offline on your own machine with a local model (Ollama), and still
works with a rules-based heuristic judge if there's no model around.

```
⚖️  FOLDERJUDGE  ·  a court for your junk
  folder   ~/Downloads
  files    238 · 4.2 GB
  judge    Judge Barold · AI judge: gemma3:1b (offline)

  “Order in the folder. I've seen worse, but not by much.”

  action     files         size
  TRASH         12     812.3 MB
  ARCHIVE        4      96.1 KB
  REVIEW        21     903.8 MB
  KEEP          201     2.4 GB

── TRASH ──────────────────────────────────────────────
  🧟 setup-chrome-v3.crdownload · 810.0 MB · 402d
    leftover partial download, never finished
  🗄️ driver-pack.exe · 2.3 MB · 45d
    identical copy of driver-pack-final.exe

  ⚖️  Case closed: 12 files sentenced to the bin (812.3 MB). 201 walk free.
```

## Why this one

- **It judges, it does not delete.** Removals move to FolderJudge's trash with a
  full manifest. One command (`folderjudge restore`) undoes everything.
- **Local AI only.** Judgments come from your own machine (Ollama). No cloud,
  no keys, no privacy leaks.
- **Guardrails the model can't talk its way past.** Even if the model says
  *trash*, big or brand-new files get escalated to `review` instead.
- **Cross-platform for real.** Linux, macOS, Windows — pure Python stdlib,
  no dependencies. And yes, it runs in Termux on Android too (bonus round).

## Install

You need Python **3.9+**. That's it.

```bash
# from this folder — installs the `folderjudge` command
python3 -m pip install --user .

# (Arch/macos note: system pip may ask for --break-system-packages or use pipx)
```

Optional but recommended — the local AI judge:

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma3:1b       # small, fast, plenty of judgment

# macOS
brew install ollama && brew services start ollama && ollama pull gemma3:1b

# Windows
winget install Ollama.Ollama
ollama pull gemma3:1b
```

Check health anytime:

```bash
folderjudge ai
```

## Usage

```bash
folderjudge                     # judge your Downloads folder
folderjudge ~/Downloads --deep  # also judge inside subfolders
folderjudge ~/Desktop --dry-run # show the verdict, touch nothing
folderjudge --persona butler    # or gremlin, if you want to be roasted

python3 -m folderjudge /path --yes  # no install needed — run from the repo
```

When the verdict lands, FolderJudge shows exactly what moves where — then asks
for sign-off. Type `y`, and the sentence is executed into its own trash.

### Subcommands

| command                       | does                                                     |
|-------------------------------|----------------------------------------------------------|
| `restore`                     | pick a past session, bring files home                    |
| `restore --last`              | undo the newest session immediately                      |
| `restore --list`              | show recent sessions                                     |
| `report`                      | print latest markdown report path                        |
| `report --open`               | open it in your browser                                  |
| `ai`                          | Ollama status + which model would judge                  |

### Flags

| flag              | effect                                                      |
|-------------------|-------------------------------------------------------------|
| `--deep`          | include subfolders in the scan                              |
| `--dry-run`       | never touch anything, verdict only                          |
| `--yes`           | skip the confirmation prompt                                |
| `--no-ai`         | heuristics only (no Ollama call)                            |
| `--persona`       | `judge` (dry + fair), `butler` (polite), `gremlin` (chaotic) |
| `--include-hidden`| also judge dotfiles / hidden files                          |
| `--version`       | print version                                               |

## How the judge thinks

Every file gets one of four sentences:

- **TRASH** — junk parts (`.crdownload`, `.part`, `.tmp`…), exact duplicate
  copies (head+tail content fingerprint), big stale installers the model
  agrees could go.
- **ARCHIVE** — worth keeping, out of sight: old small screenshots, classic
  media worth remembering without clutter.
- **REVIEW** — mystery crates, giant files, anything too close to call.
- **KEEP** — work material, recently downloaded, or simply harmless.

The AI pass (when Ollama is up) judges from *name, size, age, category* —
with enough guardrails that a hallucinating model can't nuke your fresh
ISO of a 200 MB installer without you seeing it first.

## Where things live

| OS      | trash and reports live in                                      |
|---------|-----------------------------------------------------------------|
| Linux   | `~/.local/share/FolderJudge/`                                   |
| macOS   | `~/Library/Application Support/FolderJudge/`                    |
| Windows | `%LOCALAPPDATA%\FolderJudge\`                                   |

Markdown reports from every run land in `reports/`; every executed move lands
in `trash/<session-id>/` with its `manifest.json`.

## Tests

```bash
python3 -m pytest tests -q
```

## The terms of the deal

- Nothing is deleted. Ever. Trash means *relocatable*.
- Symlinks are never followed on scan; nothing is executed, opened, or parsed.
- Hidden files are skipped unless you say `--include-hidden`.
- Every destructive action requires a `y`, or `--yes`, and is undoable after.
