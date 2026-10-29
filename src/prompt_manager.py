import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

from scraper import extract_tags_from_url

PROMPT_DIR = Path(__file__).resolve().parents[1] / "data" / "prompts"
PROMPT_DIR.mkdir(parents=True, exist_ok=True)

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


class SDPromptApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("SD Prompt Assembler")
        self.root.geometry("1280x820")
        self.root.minsize(980, 650)
        self.root.configure(bg=DARK_BG)

        self.current_file: Path | None = None
        self.pill_items: list[str] = []
        self.dragged_index: int | None = None
        self.pill_buttons: list[tk.Button] = []
        self.pill_placeholder: tk.Label | None = None

        self._apply_theme()
        self._build_ui()
        self.refresh_file_list()
        self.sync_pills_from_editor()

    def _apply_theme(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Dark.TFrame", background=PANEL_BG)
        style.configure("Dark.TLabel", background=PANEL_BG, foreground=TEXT)
        style.configure(
            "Dark.TButton",
            background=LIME,
            foreground="#0d120d",
            borderwidth=0,
            relief="flat",
            padding=(10, 7),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Dark.TButton",
            background=[("active", LIME_DARK), ("pressed", LIME_DARK)],
            foreground=[("active", "#0d120d"), ("pressed", "#0d120d")],
        )
        style.configure("Dark.TEntry", fieldbackground=MID_BG, foreground=TEXT, insertcolor=TEXT)
        style.configure("Dark.TPanedwindow", background=DARK_BG)

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=(12, 10, 12, 8), style="Dark.TFrame")
        top.pack(fill="x")

        ttk.Label(top, text="Prompt title:", style="Dark.TLabel").pack(side="left")
        self.title_var = tk.StringVar()
        self.title_entry = ttk.Entry(top, textvariable=self.title_var, width=32, style="Dark.TEntry")
        self.title_entry.pack(side="left", padx=(8, 12))

        ttk.Label(top, text="Imageboard URL:", style="Dark.TLabel").pack(side="left")
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(top, textvariable=self.url_var, width=48, style="Dark.TEntry")
        self.url_entry.pack(side="left", padx=(8, 12))

        self.scrape_btn = ttk.Button(top, text="Scrape Tags", command=self.scrape_and_append, style="Dark.TButton")
        self.scrape_btn.pack(side="left")

        body = ttk.Panedwindow(self.root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left = ttk.Frame(body, padding=8, style="Dark.TFrame")
        body.add(left, weight=1)

        file_controls = ttk.Frame(left, style="Dark.TFrame")
        file_controls.pack(fill="x")
        ttk.Button(file_controls, text="New", command=self.new_prompt, style="Dark.TButton").pack(side="left")
        ttk.Button(file_controls, text="Save", command=self.save_prompt, style="Dark.TButton").pack(side="left", padx=(6, 0))
        ttk.Button(file_controls, text="Delete", command=self.delete_prompt, style="Dark.TButton").pack(side="left", padx=(6, 0))
        ttk.Button(file_controls, text="Load", command=self.load_selected_prompt, style="Dark.TButton").pack(side="left", padx=(6, 0))

        self.file_list = tk.Listbox(
            left,
            height=26,
            activestyle="none",
            bg=MID_BG,
            fg=TEXT,
            selectbackground="#2f9b41",
            selectforeground="#041007",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
        )
        self.file_list.bind("<Double-Button-1>", lambda _event: self.load_selected_prompt())
        self.file_list.pack(fill="both", expand=True, pady=(10, 0))

        center = ttk.Frame(body, padding=8, style="Dark.TFrame")
        body.add(center, weight=3)

        prompt_header = ttk.Frame(center, style="Dark.TFrame")
        prompt_header.pack(fill="x", pady=(0, 8))
        ttk.Label(prompt_header, text="Prompt Editor", style="Dark.TLabel").pack(side="left")
        ttk.Button(prompt_header, text="Build Pills", command=self.sync_pills_from_editor, style="Dark.TButton").pack(side="right")

        self.prompt_editor = scrolledtext.ScrolledText(
            center,
            wrap="word",
            font=("Segoe UI", 10),
            undo=True,
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self.prompt_editor.pack(fill="both", expand=True, height=12)

        pill_frame = ttk.Frame(center, style="Dark.TFrame")
        pill_frame.pack(fill="x", pady=(10, 0))
        ttk.Label(pill_frame, text="Prompt Pill Board", style="Dark.TLabel").pack(anchor="w")

        self.pill_canvas = tk.Canvas(pill_frame, height=140, bg=PANEL_BG, highlightthickness=0)
        self.pill_canvas.pack(fill="both", expand=True, pady=(8, 0))
        self.pill_scroll = ttk.Scrollbar(pill_frame, orient="horizontal", command=self.pill_canvas.xview)
        self.pill_scroll.pack(fill="x")
        self.pill_canvas.configure(xscrollcommand=self.pill_scroll.set)

        self.pill_inner = tk.Frame(self.pill_canvas, bg=PANEL_BG)
        self.pill_canvas.create_window((0, 0), window=self.pill_inner, anchor="nw")
        self.pill_inner.bind("<Configure>", lambda event: self.pill_canvas.configure(scrollregion=self.pill_canvas.bbox("all")))

        right = ttk.Frame(body, padding=8, style="Dark.TFrame")
        body.add(right, weight=1)

        tag_header = ttk.Frame(right, style="Dark.TFrame")
        tag_header.pack(fill="x")
        ttk.Label(tag_header, text="Extracted tags", style="Dark.TLabel").pack(side="left")
        ttk.Button(tag_header, text="Copy to Prompt", command=self.copy_tags_to_prompt, style="Dark.TButton").pack(side="right")

        self.tags_box = scrolledtext.ScrolledText(
            right,
            wrap="word",
            height=18,
            font=("Segoe UI", 10),
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self.tags_box.pack(fill="both", expand=True, pady=(8, 8))

        ttk.Button(right, text="Clear Tags", command=self.clear_tags, style="Dark.TButton").pack(fill="x")

    def refresh_file_list(self):
        self.file_list.delete(0, tk.END)
        for file_path in sorted(PROMPT_DIR.glob("*.txt")):
            self.file_list.insert(tk.END, file_path.name)

    def _split_prompt_to_pills(self, text: str) -> list[str]:
        parts = [part.strip() for part in text.split(",")]
        return [part for part in parts if part]

    def _update_editor_from_pills(self):
        self.prompt_editor.delete("1.0", tk.END)
        self.prompt_editor.insert("1.0", ", ".join(self.pill_items))

    def sync_pills_from_editor(self):
        text = self.prompt_editor.get("1.0", tk.END)
        self.pill_items = self._split_prompt_to_pills(text)
        self.render_pills()

    def render_pills(self):
        for btn in self.pill_buttons:
            btn.destroy()
        self.pill_buttons.clear()

        if self.pill_placeholder is not None:
            self.pill_placeholder.destroy()
            self.pill_placeholder = None

        if not self.pill_items:
            self.pill_placeholder = tk.Label(
                self.pill_inner,
                text="No prompt elements yet. Add comma-separated tags or prompts.",
                fg=SUBTEXT,
                bg=PANEL_BG,
                font=("Segoe UI", 10),
            )
            self.pill_placeholder.pack(anchor="w", padx=8, pady=10)
            self.pill_canvas.update_idletasks()
            self.pill_canvas.configure(scrollregion=self.pill_canvas.bbox("all"))
            return

        for index, pill in enumerate(self.pill_items):
            pill_button = tk.Button(
                self.pill_inner,
                text=pill,
                bg=PILL_BG,
                fg=TEXT,
                activebackground=PILL_BG_HOVER,
                activeforeground=TEXT,
                relief="flat",
                borderwidth=0,
                padx=10,
                pady=7,
                anchor="center",
                cursor="hand2",
                justify="center",
                font=("Segoe UI", 10, "bold"),
            )
            pill_button.pack(side="left", padx=6, pady=6)
            pill_button.bind("<ButtonPress-1>", lambda event, idx=index: self._start_drag(idx))
            pill_button.bind("<ButtonRelease-1>", lambda event, idx=index: self._end_drag(idx))
            self.pill_buttons.append(pill_button)

        self.pill_canvas.update_idletasks()
        self.pill_canvas.configure(scrollregion=self.pill_canvas.bbox("all"))

    def _start_drag(self, index: int):
        self.dragged_index = index

    def _end_drag(self, target_index: int):
        if self.dragged_index is None:
            return

        source_index = self.dragged_index
        if not 0 <= source_index < len(self.pill_items):
            self.dragged_index = None
            return

        if source_index != target_index:
            moved = self.pill_items.pop(source_index)
            if source_index < target_index:
                target_index -= 1
            target_index = max(0, min(target_index, len(self.pill_items)))
            self.pill_items.insert(target_index, moved)
            self._update_editor_from_pills()
            self.render_pills()

        self.dragged_index = None

    def new_prompt(self):
        self.current_file = None
        self.title_var.set("")
        self.prompt_editor.delete("1.0", tk.END)
        self.tags_box.delete("1.0", tk.END)
        self.pill_items = []
        self.render_pills()

    def _prompt_name_from_title(self) -> str:
        name = self.title_var.get().strip()
        if not name:
            return "untitled_prompt.txt"
        safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_", ".", " ") else "_" for ch in name)
        safe_name = safe_name.strip()
        if not safe_name:
            safe_name = "untitled_prompt"
        if not safe_name.lower().endswith(".txt"):
            safe_name += ".txt"
        return safe_name

    def save_prompt(self):
        file_name = self._prompt_name_from_title()
        target = PROMPT_DIR / file_name
        text = self.prompt_editor.get("1.0", tk.END).strip()

        if not text:
            messagebox.showwarning("Empty prompt", "The prompt is empty. Add some text before saving.")
            return

        if target.exists() and self.current_file != target:
            confirm = messagebox.askyesno("Overwrite file", f"'{file_name}' already exists. Overwrite it?")
            if not confirm:
                return

        with open(target, "w", encoding="utf-8") as handle:
            handle.write(text)

        self.current_file = target
        self.refresh_file_list()
        self.title_var.set(target.stem)
        messagebox.showinfo("Saved", f"Prompt saved to: {target.name}")

    def delete_prompt(self):
        selection = self.file_list.curselection()
        if not selection:
            messagebox.showwarning("Choose a file", "Select a saved prompt to delete.")
            return

        file_name = self.file_list.get(selection[0])
        confirm = messagebox.askyesno("Delete prompt", f"Delete '{file_name}'?")
        if confirm:
            target = PROMPT_DIR / file_name
            if target.exists():
                target.unlink()
            self.refresh_file_list()
            if self.current_file == target:
                self.new_prompt()

    def load_selected_prompt(self):
        selection = self.file_list.curselection()
        if not selection:
            messagebox.showwarning("Choose a file", "Select a saved prompt file to load.")
            return

        file_name = self.file_list.get(selection[0])
        target = PROMPT_DIR / file_name
        self.current_file = target
        self.title_var.set(target.stem)
        self.prompt_editor.delete("1.0", tk.END)
        self.prompt_editor.insert("1.0", target.read_text(encoding="utf-8"))
        self.sync_pills_from_editor()

    def scrape_and_append(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Paste an imageboard URL before scraping tags.")
            return

        self.tags_box.delete("1.0", tk.END)
        try:
            tags = extract_tags_from_url(url)
        except Exception as exc:  # pragma: no cover
            messagebox.showerror("Scraping failed", str(exc))
            return

        if not tags:
            self.tags_box.insert("1.0", "No tags were found. Try a different page or a site with embedded tag metadata.")
            return

        self.tags_box.insert("1.0", "\n".join(tags))

    def copy_tags_to_prompt(self):
        tags_text = self.tags_box.get("1.0", tk.END).strip()
        if not tags_text:
            messagebox.showwarning("No tags", "There are no extracted tags to append.")
            return

        tags = [line.strip() for line in tags_text.splitlines() if line.strip()]
        if not tags:
            return

        existing = self.prompt_editor.get("1.0", tk.END).strip()
        combined = existing + (", " if existing else "") + ", ".join(tags)
        self.prompt_editor.delete("1.0", tk.END)
        self.prompt_editor.insert("1.0", combined)
        self.sync_pills_from_editor()

    def clear_tags(self):
        self.tags_box.delete("1.0", tk.END)


def main():
    root = tk.Tk()
    SDPromptApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
