import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

from scraper import extract_tags_from_url


def get_runtime_prompt_dir() -> Path:
    if getattr(sys, "frozen", False):
        base_dir = Path.home() / "SD Prompt Assembler"
    else:
        base_dir = Path(__file__).resolve().parents[1] / "data"

    prompt_dir = base_dir / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    return prompt_dir


PROMPT_DIR = get_runtime_prompt_dir()
