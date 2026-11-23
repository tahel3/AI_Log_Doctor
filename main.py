import argparse
import sys

from dotenv import load_dotenv

from log_doctor.parser import LogParser
from log_doctor.grouper import ErrorGrouper
from log_doctor.llm_client import LLMClient
from log_doctor.report import ReportGenerator


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Analyze log files with AI")
    parser.add_argument("log_file", nargs="?", help="Path to the log file (not needed with --gui)")             
    parser.add_argument("--top", type=int, default=5, help="Number of most frequent error groups to send to the AI (default: 5)")              
    parser.add_argument("--no-ai", action="store_true", help="Skip AI analysis and only parse and group errors")          
    parser.add_argument("--format", choices=["markdown", "text"], default="markdown", help="Report format (default: markdown)")
    parser.add_argument("--gui", action="store_true", help="Launch the graphical interface")
    parser.add_argument("--output", default="report.md", help="Where to save the report")
    args = parser.parse_args()
    if args.gui:
        from log_doctor.gui import run
        run()
        return
    if not args.log_file:
        parser.error("log_file is required (or use --gui)")
    log_parser = LogParser()
    try:
        entries = log_parser.parse_file(args.log_file)
    except FileNotFoundError:
        print(f"Error: file not found: {args.log_file}")
        sys.exit(1)
    print(f"Parsed {len(entries)} entries ({log_parser.skipped_lines} skipped)")
    groups = ErrorGrouper().group(entries)
    if not groups:
        print("No errors found.")
        return
    top_groups = groups[:args.top]
    if not args.no_ai:
        try:
            client = LLMClient()
        except ValueError:
           print("Error: GEMINI_API_KEY is not set. Add it to your .env file, or run with --no-ai.",file=sys.stderr)
           sys.exit(1)
        print(f"Analyzing top {len(top_groups)} of {len(groups)} groups...")
        client.analyse_groups(top_groups)
    gen = ReportGenerator()
    if args.format == "text":
        content = gen.to_text(top_groups, len(entries), log_parser.skipped_lines)
    else:
        content = gen.to_markdown(top_groups, len(entries), log_parser.skipped_lines)
    path = gen.save(content, args.output)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    main()
