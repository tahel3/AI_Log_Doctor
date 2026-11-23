import re
from collections import defaultdict

from .models import ErrorGroup, LogEntry

# Tokens that vary per occurrence and should be replaced with placeholders before grouping
_VARIABLE_PATTERNS = [ 
    (re.compile(r'"[^"]*"'),"<QS>"),                   # quoted strings
    (re.compile(r"'[^']*'"),"<SQS>"),                # single-quoted strings
    (re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.,\d]*\b"),"<TS>"),  # timestamps
    (re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"),"<UUID>"),  # UUIDs
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "<IP>"),   # IP addresses
    (re.compile(r"/\S+"),"<PATH>"),                     #paths
    (re.compile(r"\b0x[0-9a-fA-F]+\b"),"<HEX>"),        # hex numbers
    (re.compile(r"\d+"),"<INT>")                   # integers
]


def _signature(message: str) -> str:
    """Reduce a log message to a stable grouping key."""
    sig = message
    for pattern,place_holder in _VARIABLE_PATTERNS:
        sig = pattern.sub(place_holder, sig)
    # Collapse repeated whitespace
    sig = re.sub(r"\s+", " ", sig).strip()
    return sig


class ErrorGrouper:
    """Clusters LogEntry objects by message signature."""

    def group(self, entries: list[LogEntry]) -> list[ErrorGroup]:
        """Return a list of ErrorGroup objects, sorted by frequency (descending)."""
        buckets: dict[str, ErrorGroup] = {}
        for entry in entries:
            if not entry.is_error:
                continue
            sig = f"{entry.source}|{_signature(entry.message)}"
            if sig not in buckets:
                buckets[sig] = ErrorGroup(signature=sig)
            buckets[sig].add(entry)
        groups = list(buckets.values())
        groups.sort(key=lambda g: g.count, reverse=True)
        return groups

    def top_n(self, entries: list[LogEntry], n: int = 10) -> list[ErrorGroup]:
        """Convenience wrapper — return only the N most frequent groups."""
        return self.group(entries)[:n]
if __name__ == "__main__":
    from .parser import LogParser
    entries = LogParser().parse_file("sample_logs/app.log")
    for g in ErrorGrouper().group(entries):
        print(g.count, g.signature)