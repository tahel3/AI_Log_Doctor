import re
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .models import LogEntry


_PATTERN =re.compile(
        r"(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[,.]\d{3})\s+"
        r"(?P<level>DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)\s+"
        r"\[(?P<source>[^\]]+)\]\s+"
        r"(?P<message>.+)"
    )

_TS_FORMATS = [
    "%Y-%m-%d %H:%M:%S,%f",
    "%Y-%m-%dT%H:%M:%S,%f",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%b %d %H:%M:%S",
]


def _parse_timestamp(raw: str) -> datetime | None:
    for fmt in _TS_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt)
        except ValueError:
            continue
    return None


class LogParser:
    """Parses log files into a sequence of LogEntry objects."""
    def __init__(self) -> None:
        self.skipped_lines = 0

    def parse_file(self, path: str | Path) -> list[LogEntry]:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        return self.parse_text(text)

    def parse_text(self, text: str, source: str = "<text>") -> list[LogEntry]:
        self.skipped_lines = 0
        entries: list[LogEntry] = []
        for lineno, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            entry = self._parse_line(line, lineno=lineno)
            if entry is not None:
                entries.append(entry)
        return entries

    def iter_errors(self, entries: list[LogEntry]) -> Iterator[LogEntry]:
        """Yield only entries whose level indicates an error."""
        for entry in entries:
            if entry.is_error:
                yield entry

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_line(self, line: str,  lineno: int) -> LogEntry|None:
        m = _PATTERN.match(line)
        if m is None:
            # Fallback: unrecognised format
            self.skipped_lines+=1
            return None
        source=m.group("source")
        ts = _parse_timestamp(m.group("ts"))
        if ts is None: 
            self.skipped_lines+=1
            return None
        level = m.group("level").upper()
        if level=="WARN":
            level="WARNING"
        return LogEntry(
                    timestamp=ts,
                    level=level,
                    message=m.group("message").strip(),
                    raw=line,
                    source=source,
                    line_number=lineno,
            )
