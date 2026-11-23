from datetime import datetime
from pathlib import Path

from .models import ErrorGroup


class ReportGenerator:
    """Converts a list of ErrorGroup objects into human-readable reports."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def to_markdown( self,
        groups: list[ErrorGroup],
        total_entries: int,
        skipped_lines: int,
        title: str = "AI Log Doctor Report",
    ) -> str:
        lines: list[str] = []
        lines.append(f"# {title}")
        lines.append(f"_Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}_\n")
        lines.append("## Summary")
        lines.append(f"- **Total log entries:** {total_entries}")
        lines.append(f"- **Error entries:** {sum(g.count for g in groups)}")
        lines.append(f"- **Error groups:** {len(groups)}")         
        lines.append(f"- **Skipped lines:** {skipped_lines}\n")
        for i, group in enumerate(groups, start=1):
            lines.append(f"---\n## Group {i}: `{group.signature}`")
            lines.append(f"- **Occurrences:** {group.count}")
            if group.first_seen:
                lines.append(f"- **First seen:** {group.first_seen:%Y-%m-%d %H:%M:%S}")
            if group.last_seen:
                lines.append(f"- **Last seen:** {group.last_seen:%Y-%m-%d %H:%M:%S}")

            if group.ai_analysis:
                lines.append(f"\n### Analysis\n{group.ai_analysis}")
            if group.suggested_fix:
                lines.append(f"\n### Suggested Fix\n{group.suggested_fix}")
            lines.append("\n### Sample Log Entries")
            lines.append("```")
            for entry in group.entries[:3]:
                lines.append(entry.raw)
            lines.append("```")
        return "\n".join(lines)

    def to_text(
        self,
        groups: list[ErrorGroup],
        total_entries: int,
        skipped_lines: int,
        title: str = "AI Log Doctor Report",
    ) -> str:
        sep = "=" * 70
        lines: list[str] = [sep, title, sep, ""]
        lines.append(f"Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n")
        lines.append("Summary: ")
        lines.append(f"- Total log entries: {total_entries}")
        lines.append(f"- Error entries: {sum(g.count for g in groups)}")
        lines.append(f"- Error groups: {len(groups)}")
        lines.append(f"- Skipped lines: {skipped_lines}\n")
        for i, group in enumerate(groups, start=1):
            lines.append(f"[{i}] {group.signature}")
            lines.append(f"    Occurrences : {group.count}")
            if group.first_seen:
                lines.append(f"    First seen  : {group.first_seen:%Y-%m-%d %H:%M:%S}")
            if group.last_seen:
                lines.append(f"    Last seen   : {group.last_seen:%Y-%m-%d %H:%M:%S}")
            if group.ai_analysis:
                lines.append(f"    Analysis    : {group.ai_analysis}")
            if group.suggested_fix:
                lines.append(f"    Fix         : {group.suggested_fix}")
            lines.append("")

        lines.append(sep)
        return "\n".join(lines)

    def save(self, content: str, output_path: str | Path) -> Path:
        output_path = Path(output_path)
        output_path.write_text(content, encoding="utf-8")
        return output_path


if __name__ == "__main__":
    from .parser import LogParser
    from .grouper import ErrorGrouper
    from dotenv import load_dotenv
    from .llm_client import LLMClient
    load_dotenv()
    log_path = Path(__file__).parent.parent / "sample_logs" / "app.log"
    parser = LogParser()
    entries = parser.parse_file(log_path)
    groups = ErrorGrouper().group(entries)
    LLMClient().analyse_groups(groups) 
    gen = ReportGenerator()
    report = gen.to_markdown(groups, len(entries), parser.skipped_lines)
    print(report)
    gen.save(report, "report.md")