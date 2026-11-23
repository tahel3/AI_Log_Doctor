"""
Tkinter-based GUI for AI Log Doctor.

Launch with:
    python -m log_doctor.gui
or call gui.run() from main.py.
"""
from dotenv import load_dotenv
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Optional

from .grouper import ErrorGrouper
from .llm_client import LLMClient
from .models import ErrorGroup
from .parser import LogParser
from .report import ReportGenerator


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AI Log Doctor")
        self.geometry("900x650")
        self.resizable(True, True)

        self._log_path: Optional[Path] = None
        self._groups: list[ErrorGroup] = []
        self._total_entries = 0
        self._skipped_lines = 0
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # ── Top bar ──────────────────────────────────────────────────
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")

        self._path_var = tk.StringVar(value="No file selected")
        ttk.Label(top, textvariable=self._path_var, width=60).pack(side="left")
        ttk.Button(top, text="Open Log File…", command=self._open_file).pack(side="left", padx=4)
        self._analyse_btn = ttk.Button(top, text="Analyse", command=self._run_analysis)
        self._analyse_btn.pack(side="left", padx=4)
        ttk.Button(top, text="Save Report…", command=self._save_report).pack(side="left", padx=4)
        
        # ── Progress bar ──────────────────────────────────────────────
        self._progress = ttk.Progressbar(self, mode="indeterminate")
        self._progress.pack(fill="x", padx=8)

        # ── Main paned area ───────────────────────────────────────────
        pane = ttk.PanedWindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=8, pady=8)

        # Left: group list
        left = ttk.Frame(pane)
        pane.add(left, weight=1)

        ttk.Label(left, text="Error Groups").pack(anchor="w")
        self._listbox = tk.Listbox(left, selectmode="browse")
        self._listbox.pack(fill="both", expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        # Right: detail panel
        right = ttk.Frame(pane)
        pane.add(right, weight=3)

        ttk.Label(right, text="Details").pack(anchor="w")
        self._detail = scrolledtext.ScrolledText(right, wrap="word", state="disabled")
        self._detail.pack(fill="both", expand=True)

        # ── Status bar ────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self._status_var, relief="sunken", anchor="w").pack(
            fill="x", side="bottom"
        )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select a log file",
            filetypes=[("Log files", "*.log *.txt"), ("All files", "*.*")],
        )
        if path:
            self._log_path = Path(path)
            self._path_var.set(str(self._log_path))
            self._status_var.set(f"Loaded: {self._log_path.name}")

    def _run_analysis(self) -> None:
        if not self._log_path:
            messagebox.showwarning("No file", "Please open a log file first.")
            return
        
        self._status_var.set("Parsing and grouping…")
        self._progress.start(10)
        self._analyse_btn.config(state="disabled")
        threading.Thread(target=self._analysis_worker, daemon=True).start()

    def _analysis_worker(self) -> None:
        try:
            parser = LogParser()
            entries = parser.parse_file(self._log_path)

            grouper = ErrorGrouper()
            groups = grouper.top_n(entries, n=5)
            try:
                client = LLMClient()
            except ValueError:
                client = None
                self.after(0, lambda: self._status_var.set("No API key — showing results without AI analysis"))
            if client:
                self.after(0, lambda: self._status_var.set("Analyzing with AI…"))
                client.analyse_groups(groups)
            self._groups = groups
            self._total_entries = len(entries)
            self._skipped_lines = parser.skipped_lines
            self.after(0, self._populate_list)
        except Exception as exc:
            msg = str(exc)
            self.after(0, lambda: messagebox.showerror("Error", msg))
        finally:
            self.after(0, self._progress.stop)
            self.after(0, lambda: self._analyse_btn.config(state="normal"))

    def _populate_list(self) -> None:
        self._listbox.delete(0, "end")
        for i,g in enumerate(self._groups):
            label = f"[{g.count:>4}x]  {g.signature[:60]}"
            self._listbox.insert("end", label)
        self._status_var.set(f"Found {len(self._groups)} error group(s).")

    def _on_select(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        sel = self._listbox.curselection()
        if not sel:
            return
        group = self._groups[sel[0]]
        self._show_detail(group)

    def _show_detail(self, group: ErrorGroup) -> None:
        lines: list[str] = [
            f"Signature : {group.signature}",
            f"Count     : {group.count}",
        ]
        if group.first_seen:
            lines.append(f"First seen: {group.first_seen:%Y-%m-%d %H:%M:%S}")
        if group.last_seen:
            lines.append(f"Last seen : {group.last_seen:%Y-%m-%d %H:%M:%S}")
        if group.ai_analysis:
            lines += ["", "── AI Analysis ──────────────────────────", group.ai_analysis]
        if group.suggested_fix:
            lines += ["", "── Suggested Fix ────────────────────────", group.suggested_fix]
        lines += ["", "── Sample Entries ───────────────────────"]
        for entry in group.entries[:5]:
            lines.append(entry.raw)

        text = "\n".join(lines)
        self._detail.configure(state="normal")
        self._detail.delete("1.0", "end")
        self._detail.insert("end", text)
        self._detail.configure(state="disabled")

    def _save_report(self) -> None:
        if not self._groups:
            messagebox.showwarning("Nothing to save", "Run analysis first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt")],
        )
        if not path:
            return
        gen = ReportGenerator()
        if path.endswith(".txt"):
            content = gen.to_text(self._groups, self._total_entries, self._skipped_lines)
        else:
            content = gen.to_markdown(self._groups, self._total_entries, self._skipped_lines)
        gen.save(content, path)
        self._status_var.set(f"Report saved: {path}")


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def run() -> None:
    load_dotenv()
    app = App()
    app.mainloop()


if __name__ == "__main__":
    run()
