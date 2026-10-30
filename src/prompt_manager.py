import json
import os
import re
import tkinter as tk
from pathlib import Path
from tkinter import ttk, scrolledtext, messagebox

from scraper import extract_tags_from_url

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROMPT_DIR = DATA_DIR / "prompts"
DB_PATH = DATA_DIR / "prompt_database.json"
PROMPT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

DARK_BG = "#0d120d"
PANEL_BG = "#171d17"
MID_BG = "#1d2a1d"
INPUT_BG = "#111711"
LIME = "#b8ff4a"
LIME_DARK = "#8de52c"
TEXT = "#ebffe6"
SUBTEXT = "#b7c9b0"
PILL_BG = "#243226"
PILL_BG_HOVER = "#2d4232"
BORDER = "#3a5742"

INJECTORS = {
    "Curvaceous": "mature female, (curvaceous:1.4), (wide hips:1.4), (large breasts:1.3), (plump ass:1.2), (narrow waist:1.4)",
    "Petite": "petite female, (petite:1.4), (small breasts:1.2), narrow waist, slim hips, cute, delicate frame",
    "Voluptuous": "voluptuous female, huge ass, thick thighs, big breasts, mature female, plump, toned body",
    "Glow": "masterpiece, highly detailed, depth of field, soft lighting, ultra quality, cinematic, vibrant colors",
    "Close-up": "close-up, face focus, detailed face, upper body, blurry background, bokeh",
    "Wide Shot": "wide shot, full body, landscape, dynamic composition, background scenery",
}


def _read_json_list(path: Path):
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _write_json_list(path: Path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(values, fh, ensure_ascii=False, indent=2)


class SDPromptAssembler:
    def __init__(self, root):
        self.root = root
        self.root.title("SD Prompt Assembler")
        self.root.geometry("1380x880")
        self.root.minsize(1120, 700)
        self.root.configure(bg=DARK_BG)

        self.current_file = None
        self.pill_items = []
        self.selected_indices = set()
        self.dragged_index = None
        self.pill_buttons = []
        self.title_var = tk.StringVar()
        self.url_var = tk.StringVar()
        self.output_text = None
        self.status_var = tk.StringVar(value="Ready")
        self.extracted_tags = []
        self.tag_checkboxes = []

        self._apply_theme()
        self._build_ui()
        self.refresh_file_list()
        self._sync_from_editor()

    def _apply_theme(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("Dark.TFrame", background=PANEL_BG)
        style.configure("Dark.TLabel", background=PANEL_BG, foreground=TEXT)
        style.configure("Dark.TButton", background=LIME, foreground="#0d120d", relief="flat", padding=(9, 7), font=("Segoe UI", 10, "bold"))
        style.map("Dark.TButton", background=[("active", LIME_DARK), ("pressed", LIME_DARK)], foreground=[("active", "#0d120d"), ("pressed", "#0d120d")])
        style.configure("Dark.TEntry", fieldbackground=MID_BG, foreground=TEXT, insertcolor=TEXT)
        style.configure("Dark.TPanedwindow", background=DARK_BG)

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=(12, 10, 12, 8), style="Dark.TFrame")
        top.pack(fill="x")

        ttk.Label(top, text="Prompt title:", style="Dark.TLabel").pack(side="left")
        ttk.Entry(top, textvariable=self.title_var, width=30, style="Dark.TEntry").pack(side="left", padx=(8, 12))

        ttk.Label(top, text="Imageboard URL:", style="Dark.TLabel").pack(side="left")
        ttk.Entry(top, textvariable=self.url_var, width=48, style="Dark.TEntry").pack(side="left", padx=(8, 12))

        ttk.Button(top, text="Scrape Tags", command=self.scrape_tags, style="Dark.TButton").pack(side="left")

        main_split = ttk.Panedwindow(self.root, orient="horizontal")
        main_split.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left = ttk.Frame(main_split, padding=8, style="Dark.TFrame")
        main_split.add(left, weight=1)

        left_header = ttk.Frame(left, style="Dark.TFrame")
        left_header.pack(fill="x")
        ttk.Button(left_header, text="New", command=self.new_prompt, style="Dark.TButton").pack(side="left")
        ttk.Button(left_header, text="Save", command=self.save_prompt, style="Dark.TButton").pack(side="left", padx=(6, 0))
        ttk.Button(left_header, text="Delete", command=self.delete_prompt, style="Dark.TButton").pack(side="left", padx=(6, 0))
        ttk.Button(left_header, text="Load", command=self.load_selected_prompt, style="Dark.TButton").pack(side="left", padx=(6, 0))

        self.file_list = tk.Listbox(left, height=24, bg=MID_BG, fg=TEXT, selectbackground="#2f9b41", selectforeground="#041007", relief="flat", borderwidth=0, highlightthickness=0)
        self.file_list.bind("<Double-Button-1>", lambda _event: self.load_selected_prompt())
        self.file_list.pack(fill="both", expand=True, pady=(10, 0))

        center = ttk.Frame(main_split, padding=8, style="Dark.TFrame")
        main_split.add(center, weight=3)

        editor_header = ttk.Frame(center, style="Dark.TFrame")
        editor_header.pack(fill="x", pady=(0, 8))
        ttk.Label(editor_header, text="Prompt Editor", style="Dark.TLabel").pack(side="left")
        ttk.Button(editor_header, text="Build Deck", command=self._sync_from_editor, style="Dark.TButton").pack(side="right")

        self.editor = scrolledtext.ScrolledText(center, wrap="word", font=("Segoe UI", 10), bg=INPUT_BG, fg=TEXT, insertbackground=TEXT, relief="flat", borderwidth=1, highlightthickness=1, highlightbackground=BORDER)
        self.editor.pack(fill="both", expand=True, height=12)

        deck_panel = ttk.Frame(center, style="Dark.TFrame")
        deck_panel.pack(fill="x", pady=(12, 0))
        ttk.Label(deck_panel, text="Prompt Deck", style="Dark.TLabel").pack(anchor="w")

        action_row = ttk.Frame(deck_panel, style="Dark.TFrame")
        action_row.pack(fill="x", pady=(6, 0))
        ttk.Button(action_row, text="Apply Weight", command=self.apply_weight, style="Dark.TButton").pack(side="left")
        ttk.Button(action_row, text="Strip Weight", command=self.strip_weight, style="Dark.TButton").pack(side="left", padx=(6, 0))
        ttk.Button(action_row, text="Delete Selected", command=self.delete_selected, style="Dark.TButton").pack(side="left", padx=(6, 0))
        ttk.Button(action_row, text="Invert Select", command=self.invert_selection, style="Dark.TButton").pack(side="left", padx=(6, 0))
        ttk.Button(action_row, text="Copy Raw", command=self.copy_raw, style="Dark.TButton").pack(side="left", padx=(6, 0))
        ttk.Button(action_row, text="Copy Clean", command=self.copy_clean, style="Dark.TButton").pack(side="left", padx=(6, 0))

        self.weight_var = tk.DoubleVar(value=1.0)
        weight_frame = ttk.Frame(deck_panel, style="Dark.TFrame")
        weight_frame.pack(fill="x", pady=(8, 0))
        ttk.Label(weight_frame, text="Weight:", style="Dark.TLabel").pack(side="left")
        ttk.Scale(weight_frame, from_=0.1, to=2.0, variable=self.weight_var, orient="horizontal").pack(side="left", fill="x", expand=True, padx=(8, 6))
        ttk.Button(weight_frame, text="0.5x", command=lambda: self.set_weight(0.5), style="Dark.TButton").pack(side="left")
        ttk.Button(weight_frame, text="1.0x", command=lambda: self.set_weight(1.0), style="Dark.TButton").pack(side="left", padx=(4, 0))
        ttk.Button(weight_frame, text="1.2x", command=lambda: self.set_weight(1.2), style="Dark.TButton").pack(side="left", padx=(4, 0))
        ttk.Button(weight_frame, text="1.5x", command=lambda: self.set_weight(1.5), style="Dark.TButton").pack(side="left", padx=(4, 0))

        self.deck_canvas = tk.Canvas(deck_panel, height=160, bg=PANEL_BG, highlightthickness=0)
        self.deck_canvas.pack(fill="both", expand=True, pady=(10, 0))
        self.deck_scroll = ttk.Scrollbar(deck_panel, orient="horizontal", command=self.deck_canvas.xview)
        self.deck_scroll.pack(fill="x")
        self.deck_canvas.configure(xscrollcommand=self.deck_scroll.set)
        self.deck_inner = tk.Frame(self.deck_canvas, bg=PANEL_BG)
        self.deck_canvas.create_window((0, 0), window=self.deck_inner, anchor="nw")
        self.deck_inner.bind("<Configure>", lambda event: self.deck_canvas.configure(scrollregion=self.deck_canvas.bbox("all")))

        right = ttk.Frame(main_split, padding=8, style="Dark.TFrame")
        main_split.add(right, weight=1)

        right_header = ttk.Frame(right, style="Dark.TFrame")
        right_header.pack(fill="x")
        ttk.Label(right_header, text="Extracted Tags", style="Dark.TLabel").pack(side="left")
        ttk.Button(right_header, text="Inject Selected", command=self.inject_selected_extracted, style="Dark.TButton").pack(side="right")

        self.tag_frame = ttk.Frame(right, style="Dark.TFrame")
        self.tag_frame.pack(fill="both", expand=True, pady=(8, 0))

        injector_frame = ttk.LabelFrame(right, text="Quick Injectors", padding=8, style="Dark.TFrame")
        injector_frame.pack(fill="x", pady=(10, 0))
        for name in INJECTORS:
            ttk.Button(injector_frame, text=name, command=lambda n=name: self.injector_add(n), style="Dark.TButton").pack(side="top", anchor="w", pady=2)

        db_frame = ttk.LabelFrame(right, text="Database", padding=8, style="Dark.TFrame")
        db_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(db_frame, text="Save Current to DB", command=self.save_to_db, style="Dark.TButton").pack(fill="x")
        ttk.Button(db_frame, text="Load Random", command=self.load_random_from_db, style="Dark.TButton").pack(fill="x", pady=(6, 0))

        status = ttk.Frame(self.root, style="Dark.TFrame")
        status.pack(fill="x", padx=10, pady=(0, 8))
        ttk.Label(status, textvariable=self.status_var, style="Dark.TLabel").pack(anchor="w")

    def refresh_file_list(self):
        self.file_list.delete(0, tk.END)
        for file_path in sorted(PROMPT_DIR.glob("*.txt")):
            self.file_list.insert(tk.END, file_path.name)

    def _split_prompt_text(self, text):
        parts = [part.strip() for part in text.replace("\n", ",").split(",")]
        return [p for p in parts if p]

    def _sync_from_editor(self):
        text = self.editor.get("1.0", tk.END)
        self.pill_items = self._split_prompt_text(text)
        self.selected_indices = set()
        self.render_deck()

    def _editor_from_deck(self):
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", ", ".join(self.pill_items))

    def render_deck(self):
        for child in self.deck_inner.winfo_children():
            child.destroy()

        if not self.pill_items:
            placeholder = tk.Label(self.deck_inner, text="No prompt elements yet. Add tags or scrape a URL.", fg=SUBTEXT, bg=PANEL_BG, font=("Segoe UI", 10))
            placeholder.pack(anchor="w", padx=8, pady=10)
            self.deck_canvas.update_idletasks()
            self.deck_canvas.configure(scrollregion=self.deck_canvas.bbox("all"))
            return

        for idx, item in enumerate(self.pill_items):
            selected = idx in self.selected_indices
            btn = tk.Button(
                self.deck_inner,
                text=item,
                bg=PILL_BG if not selected else "#2f9b41",
                fg=TEXT,
                activebackground=PILL_BG_HOVER,
                activeforeground=TEXT,
                relief="flat",
                borderwidth=0,
                padx=12,
                pady=7,
                justify="center",
                cursor="hand2",
                font=("Segoe UI", 10, "bold"),
            )
            btn.pack(side="left", padx=6, pady=6)
            btn.bind("<ButtonPress-1>", lambda event, i=idx: self._start_drag(i))
            btn.bind("<ButtonRelease-1>", lambda event, i=idx: self._end_drag(i))
            btn.bind("<Button-1>", lambda event, i=idx: self.toggle_select(i))
            self.pill_buttons.append(btn)

        self.deck_canvas.update_idletasks()
        self.deck_canvas.configure(scrollregion=self.deck_canvas.bbox("all"))

    def _start_drag(self, idx):
        self.dragged_index = idx

    def _end_drag(self, idx):
        if self.dragged_index is None:
            return
        source = self.dragged_index
        if source != idx and 0 <= source < len(self.pill_items):
            moved = self.pill_items.pop(source)
            if source < idx:
                idx -= 1
            idx = max(0, min(idx, len(self.pill_items)))
            self.pill_items.insert(idx, moved)
            self._editor_from_deck()
            self.render_deck()
        self.dragged_index = None

    def toggle_select(self, idx):
        if idx in self.selected_indices:
            self.selected_indices.remove(idx)
        else:
            self.selected_indices.add(idx)
        self.render_deck()

    def invert_selection(self):
        all_indices = set(range(len(self.pill_items)))
        self.selected_indices = all_indices - self.selected_indices
        self.render_deck()

    def set_weight(self, value):
        self.weight_var.set(value)
        self.apply_weight()

    def apply_weight(self):
        if not self.selected_indices:
            self.status_var.set("Select tags to weight them.")
            return
        weight = self.weight_var.get()
        for idx in sorted(self.selected_indices, reverse=True):
            tag = self.pill_items[idx]
            tag = re.sub(r"^\((.*?):\s*[-+]?\d*\.?\d+\)$", r"\1", tag.strip())
            self.pill_items[idx] = f"({tag}:{weight:.2f})"
        self._editor_from_deck()
        self.render_deck()
        self.status_var.set(f"Applied weight {weight:.2f} to {len(self.selected_indices)} tag(s).")

    def strip_weight(self):
        if not self.selected_indices:
            return
        for idx in sorted(self.selected_indices, reverse=True):
            tag = self.pill_items[idx]
            self.pill_items[idx] = re.sub(r"^\((.*?):\s*[-+]?\d*\.?\d+\)$", r"\1", tag).strip()
        self._editor_from_deck()
        self.render_deck()
        self.status_var.set("Removed weight annotations from selected tags.")

    def delete_selected(self):
        if not self.selected_indices:
            self.status_var.set("No tags selected.")
            return
        remaining = []
        for idx, item in enumerate(self.pill_items):
            if idx not in self.selected_indices:
                remaining.append(item)
        self.pill_items = remaining
        self.selected_indices = set()
        self._editor_from_deck()
        self.render_deck()
        self.status_var.set("Deleted selected tags.")

    def new_prompt(self):
        self.current_file = None
        self.title_var.set("")
        self.editor.delete("1.0", tk.END)
        self.pill_items = []
        self.selected_indices = set()
        self.render_deck()

    def save_prompt(self):
        prompt_text = self.editor.get("1.0", tk.END).strip()
        if not prompt_text:
            messagebox.showwarning("Empty prompt", "Add some text before saving.")
            return

        title = self.title_var.get().strip() or "untitled_prompt"
        safe_name = re.sub(r"[^A-Za-z0-9_\-\. ]+", "_", title).strip()
        if not safe_name:
            safe_name = "untitled_prompt"
        if not safe_name.lower().endswith(".txt"):
            safe_name += ".txt"

        target = PROMPT_DIR / safe_name
        target.write_text(prompt_text, encoding="utf-8")
        self.current_file = target
        self.refresh_file_list()
        self.title_var.set(target.stem)
        self.status_var.set(f"Saved prompt to {target.name}")

    def delete_prompt(self):
        index = self.file_list.curselection()
        if not index:
            messagebox.showwarning("Choose a file", "Select a saved prompt to delete.")
            return
        name = self.file_list.get(index[0])
        target = PROMPT_DIR / name
        if target.exists():
            target.unlink()
        self.refresh_file_list()
        self.status_var.set(f"Deleted {name}")

    def load_selected_prompt(self):
        index = self.file_list.curselection()
        if not index:
            messagebox.showwarning("Choose a file", "Select a saved prompt to load.")
            return
        name = self.file_list.get(index[0])
        target = PROMPT_DIR / name
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", target.read_text(encoding="utf-8"))
        self.title_var.set(target.stem)
        self._sync_from_editor()
        self.status_var.set(f"Loaded {name}")

    def scrape_tags(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Paste an imageboard URL first.")
            return

        try:
            tags = extract_tags_from_url(url)
        except Exception as exc:
            messagebox.showerror("Scrape failed", str(exc))
            return

        for child in self.tag_frame.winfo_children():
            child.destroy()

        self.extracted_tags = tags
        if not tags:
            tk.Label(self.tag_frame, text="No tags found.", fg=SUBTEXT, bg=PANEL_BG, font=("Segoe UI", 10)).pack(anchor="w", padx=8, pady=10)
            self.status_var.set("No tags found from that page.")
            return

        self.tag_checkboxes = []
        for tag in tags:
            value = tk.BooleanVar(value=False)
            box = tk.Checkbutton(self.tag_frame, text=tag, variable=value, bg=PANEL_BG, fg=TEXT, selectcolor=MID_BG, activebackground=PANEL_BG, activeforeground=TEXT, relief="flat", borderwidth=0)
            box.pack(anchor="w", padx=6, pady=2)
            self.tag_checkboxes.append((tag, value))

        button_row = ttk.Frame(self.tag_frame, style="Dark.TFrame")
        button_row.pack(fill="x", pady=(10, 0))
        ttk.Button(button_row, text="Insert Selected", command=self.insert_extracted_selection, style="Dark.TButton").pack(side="left")
        ttk.Button(button_row, text="Select All", command=self.select_all_extracted, style="Dark.TButton").pack(side="left", padx=(6, 0))
        ttk.Button(button_row, text="Clear", command=self.clear_extracted, style="Dark.TButton").pack(side="left", padx=(6, 0))

        self.status_var.set(f"Loaded {len(tags)} tag(s) from URL.")

    def insert_extracted_selection(self):
        selected = [tag for tag, var in self.tag_checkboxes if var.get()]
        if not selected:
            self.status_var.set("No extracted tags selected.")
            return
        current = self.editor.get("1.0", tk.END).strip()
        merged = (current + ", " if current else "") + ", ".join(selected)
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", merged)
        self._sync_from_editor()
        self.status_var.set(f"Inserted {len(selected)} row(s) into the prompt deck.")

    def select_all_extracted(self):
        for _, var in self.tag_checkboxes:
            var.set(True)

    def clear_extracted(self):
        for _, var in self.tag_checkboxes:
            var.set(False)

    def injector_add(self, name):
        payload = INJECTORS.get(name, "")
        if not payload:
            return
        current = self.editor.get("1.0", tk.END).strip()
        merged = (current + ", " if current else "") + payload
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", merged)
        self._sync_from_editor()
        self.status_var.set(f"Added injector: {name}")

    def inject_selected_extracted(self):
        selected = [tag for tag, var in self.tag_checkboxes if var.get()]
        if not selected:
            self.status_var.set("No extracted tags selected to inject.")
            return
        self.pill_items.extend(selected)
        self._editor_from_deck()
        self.render_deck()
        self.status_var.set(f"Injected {len(selected)} tag(s) into the deck.")

    def copy_raw(self):
        text = ", ".join(self.pill_items)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set("Copied raw deck text to clipboard.")

    def copy_clean(self):
        cleaned = []
        for tag in self.pill_items:
            item = re.sub(r"^\((.*?):\s*[-+]?\d*\.?\d+\)$", r"\1", tag)
            cleaned.append(item)
        text = ", ".join(cleaned)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set("Copied cleaned deck text to clipboard.")

    def save_to_db(self):
        db_entries = _read_json_list(DB_PATH)
        deck_text = ", ".join(self.pill_items)
        if not deck_text.strip():
            messagebox.showwarning("No deck content", "The prompt deck is empty.")
            return
        db_entries.append(deck_text)
        _write_json_list(DB_PATH, db_entries)
        self.status_var.set(f"Saved current deck to database ({len(db_entries)} rows).")

    def load_random_from_db(self):
        entries = _read_json_list(DB_PATH)
        if not entries:
            messagebox.showwarning("Empty database", "No prompt entries are saved yet.")
            return
        entry = entries[0]
        if len(entries) > 1:
            import random
            entry = random.choice(entries)
        current = self.editor.get("1.0", tk.END).strip()
        merged = (current + ", " if current else "") + entry
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", merged)
        self._sync_from_editor()
        self.status_var.set("Loaded a random prompt from the database.")


def main():
    root = tk.Tk()
    SDPromptAssembler(root)
    root.mainloop()


if __name__ == "__main__":
    main()
