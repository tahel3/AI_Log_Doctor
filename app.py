"""Gradio web UI for AI Log Doctor (for Hugging Face Spaces / web demo)."""
import tempfile
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

from log_doctor.parser import LogParser
from log_doctor.grouper import ErrorGrouper
from log_doctor.llm_client import LLMClient
from log_doctor.report import ReportGenerator

load_dotenv()

SAMPLE_LOG = Path(__file__).parent / "sample_logs" / "app.log"
MAX_CHARS = 500_000  # protect the demo from huge uploads


def analyze(log_file, log_text: str, top: int, use_ai: bool):
    # 1. Get the log content (uploaded file wins over pasted text)
    if log_file is not None:
        text = Path(log_file).read_text(encoding="utf-8", errors="replace")
    else:
        text = log_text or ""
    if not text.strip():
        return "⚠️ Upload a log file or paste log lines.", None
    text = text[:MAX_CHARS]

    # 2. Parse + group
    parser = LogParser()
    entries = parser.parse_text(text)
    groups = ErrorGrouper().group(entries)
    if not groups:
        return (
            f"Parsed **{len(entries)}** entries ({parser.skipped_lines} skipped) — "
            "no errors found.",
            None,
        )
    top_groups = groups[: int(top)]

    # 3. AI analysis (optional)
    note = ""
    if use_ai:
        try:
            LLMClient().analyse_groups(top_groups)
        except ValueError:
            note = "> ⚠️ GEMINI_API_KEY is not configured on the server — showing results without AI.\n\n"

    # 4. Report
    gen = ReportGenerator()
    report = gen.to_markdown(top_groups, len(entries), parser.skipped_lines)
    out = Path(tempfile.mkdtemp()) / "report.md"
    gen.save(report, out)
    return note + report, str(out)


def load_sample() -> str:
    return SAMPLE_LOG.read_text(encoding="utf-8", errors="replace")


with gr.Blocks(title="AI Log Doctor") as demo:
    gr.Markdown(
        "# 🩺 AI Log Doctor\n"
        "Upload a log file — errors are parsed, grouped by root cause, "
        "and analyzed by AI with suggested fixes."
    )
    with gr.Row():
        with gr.Column(scale=1):
            log_file = gr.File(label="Log file", file_types=[".log", ".txt"], type="filepath")
            log_text = gr.Textbox(label="…or paste log lines", lines=10)
            sample_btn = gr.Button("Load sample log")
            top = gr.Slider(1, 20, value=5, step=1, label="Top error groups to analyze")
            use_ai = gr.Checkbox(value=True, label="Use AI analysis")
            run_btn = gr.Button("Analyze", variant="primary")
        with gr.Column(scale=2):
            report_md = gr.Markdown()
            report_file = gr.File(label="Download report")

    sample_btn.click(load_sample, outputs=log_text)
    run_btn.click(analyze, inputs=[log_file, log_text, top, use_ai],
                  outputs=[report_md, report_file])

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=2).launch()
