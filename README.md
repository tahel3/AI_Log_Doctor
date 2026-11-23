---
title: AI Log Doctor
emoji: 🩺
colorFrom: blue
colorTo: indigo
sdk: gradio
app_file: app.py
python_version: "3.12"
pinned: false
---

# AI Log Doctor 🩺

**English** | [עברית](README.he.md)

A Python tool that reads log files, groups recurring errors by a shared "signature", and sends the most frequent groups to Google Gemini for analysis. It then writes a report that explains the likely root cause of each error and suggests a fix.

You can run it from the command line or through a Tkinter GUI.

## How it works

```
log file ──► Parser ──► Grouper ──► LLM Client ──► Report
            (parse      (group      (analyze with   (Markdown /
             lines)      errors)     Gemini)         Text)
```

1. **Parser**: splits each line into timestamp, level, source and message. Lines that don't match the format are counted as skipped.
2. **Grouper**: groups only `ERROR`, `CRITICAL` and `FATAL` entries. Values that change between occurrences (numbers, IP addresses, paths, UUIDs, timestamps, quoted strings, hex values) are replaced with placeholders, so messages like these:
   ```
   User 812 not found
   User 1043 not found
   ```
   get the same signature: `api|User <INT> not found`. Groups are sorted by how often they occur.
3. **LLM Client**: sends the most frequent groups (5 by default) to Gemini, with up to 5 sample lines per group. The model returns JSON with `root_cause` and `fix`. Temporary failures (timeouts, connection errors, HTTP 429/5xx) are retried with a wait that doubles after each attempt (exponential backoff).
4. **Report**: starts with a summary, then lists each group with its occurrence count, first and last time seen, the analysis, the suggested fix and sample log lines.

## Supported log format

```
YYYY-MM-DD HH:MM:SS,mmm LEVEL [source] message
```

Example:

```
2026-11-14 10:01:15,442 ERROR [db] Connection timeout after 30s to host 10.0.0.12
```

- The date and time can be separated by a space or a `T`, and the milliseconds by `,` or `.`.
- Supported levels: `DEBUG`, `INFO`, `WARNING`/`WARN`, `ERROR`, `CRITICAL`, `FATAL`.

## Requirements

- **Python 3.12 or newer** (the code uses f-string syntax that was added in 3.12)
- A Google Gemini API key. You can get one from [Google AI Studio](https://aistudio.google.com/apikey). Without a key you can still use `--no-ai`.

## Installation

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to a file named `.env` and fill in the values:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-flash-lite-latest
```

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes (unless you run with `--no-ai`) | Your Gemini API key |
| `GEMINI_MODEL` | No | Model name. Defaults to `gemini-flash-lite-latest` |

To see which models your key can use:

```bash
python sample_logs/ex.py
```

## Usage

### Command line

```bash
# Full analysis with AI, report saved to report.md
python main.py sample_logs/app.log

# Parse and group only, no AI calls
python main.py sample_logs/app.log --no-ai

# Analyze the 3 most frequent groups and save a text report
python main.py sample_logs/app.log --top 3 --format text --output report.txt
```

| Option | Default | Description |
|--------|---------|-------------|
| `log_file` | — | Path to the log file (not needed with `--gui`) |
| `--top N` | `5` | How many of the most frequent groups to send to the AI and include in the report |
| `--no-ai` | off | Skip the AI analysis |
| `--format` | `markdown` | Report format: `markdown` or `text` |
| `--output` | `report.md` | Where to save the report |
| `--gui` | off | Open the graphical interface |

### GUI

```bash
python main.py --gui
# or
python -m log_doctor.gui
```

1. **Open Log File…**: choose a log file.
2. **Analyse**: parse, group and run AI analysis on the top 5 groups. If no API key is set, results are shown without AI analysis.
3. Click a group in the left list to see its details, analysis and sample lines.
4. **Save Report…**: save the report as `.md` or `.txt`.

## Example output

Running it on [sample_logs/app.log](sample_logs/app.log) produces a report like this (shortened):

```markdown
## Summary
- **Total log entries:** 13
- **Error entries:** 10
- **Error groups:** 4
- **Skipped lines:** 1

## Group 1: `db|Connection timeout after <INT>s to host <IP>`
- **Occurrences:** 4
- **First seen:** 2026-11-14 10:01:15
- **Last seen:** 2026-11-14 10:10:20

### Analysis
The application is experiencing intermittent database connection timeouts...

### Suggested Fix
Investigate the network path and firewall configurations...
```

The full report is in [report.md](report.md).

## Project structure

```
ai-log-doctor/
├── main.py               # CLI entry point
├── requirements.txt
├── .env.example          # Environment variable template
├── log_doctor/
│   ├── models.py         # LogEntry, ErrorGroup (dataclasses)
│   ├── parser.py         # LogParser: parses log lines
│   ├── grouper.py        # ErrorGrouper: groups errors by signature
│   ├── llm_client.py     # LLMClient: Gemini calls and retries
│   ├── report.py         # ReportGenerator: Markdown / text reports
│   └── gui.py            # Tkinter GUI
└── sample_logs/
    ├── app.log           # Sample log
    └── ex.py             # Lists the Gemini models available to your key
```

## Using it as a library

```python
from dotenv import load_dotenv
from log_doctor import LogParser, ErrorGrouper, LLMClient, ReportGenerator

load_dotenv()

parser = LogParser()
entries = parser.parse_file("sample_logs/app.log")
groups = ErrorGrouper().top_n(entries, n=5)

LLMClient().analyse_groups(groups)

gen = ReportGenerator()
report = gen.to_markdown(groups, len(entries), parser.skipped_lines)
gen.save(report, "report.md")
```

## Notes

- Gemini calls are sent one at a time, with a one-second pause between them, to stay within rate limits.
- If the analysis of one group fails, the failure is recorded in the report and the run continues with the remaining groups.
- Log lines are sent as-is to Google's API. Don't run AI analysis on logs that contain sensitive data.
