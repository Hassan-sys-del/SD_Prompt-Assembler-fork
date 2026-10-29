# SD Prompt Assembler

A lightweight desktop project for managing Stable Diffusion and AI art prompts.

## Features

- create and edit prompt text files locally
- save and reload prompt files in the app
- scrape tags from imageboard URLs
- merge extracted tags into your prompt text
- keep a small local library of prompt files

## Setup

1. Open the repository in VS Code.
2. Create/select a Python interpreter.
3. Install dependencies:

```bash
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run the app

```bash
python app.py
```

## Project layout

- `app.py` — app entry point
- `src/scraper.py` — tag extraction logic
- `src/prompt_manager.py` — Tkinter desktop UI
- `data/prompts/` — saved prompt text files
- `tests/` — smoke tests for the scraper

## Notes

- The scraper works best on pages that expose tags in reliable HTML attributes or link metadata.
- Some imageboard layouts require custom parsing.
- Respect site terms and robots policies when scraping.
