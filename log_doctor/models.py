from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LogEntry:
    """Represents a single parsed log line."""

    timestamp: datetime
    level: str          # e.g. ERROR, WARNING, INFO
    message: str
    raw: str            # original unparsed line
    source: str = ""    # component that emitted the log, e.g. db,api
    line_number: int = 0

    @property
    def is_error(self) -> bool:
        return self.level.upper() in ("ERROR", "CRITICAL", "FATAL")


@dataclass
class ErrorGroup:
    """A cluster of LogEntry objects that share the same root cause."""

    signature: str                          # short canonical key for the group
    entries: list[LogEntry] = field(default_factory=list)
    ai_analysis: str = ""                   # filled in by LLMClient
    suggested_fix: str = ""                 # filled in by LLMClient

    @property
    def sample(self) -> str:
        return self.entries[0].raw if self.entries else ""
    @property
    def count(self) -> int:
        return len(self.entries)

    @property
    def first_seen(self) ->datetime:
        return min(e.timestamp for e in self.entries)

    @property
    def last_seen(self) -> datetime:
        return max(e.timestamp for e in self.entries)

    def add(self, entry: LogEntry) -> None:
        self.entries.append(entry)
