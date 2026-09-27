#!/usr/bin/env python3
"""Command-line JSON <-> TOON converter.

Usage:
    python cli.py to-toon input.json [-o output.toon] [--indent 2]
    python cli.py to-json input.toon [-o output.json] [--indent 2]
    echo '{"a":1}' | python cli.py to-toon
"""

import argparse
import json
import sys

from toonlib import compare, dumps, loads


def _read_input(path):
    if path is None or path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write_output(path, text):
    if path is None or path == "-":
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)


def main():
    parser = argparse.ArgumentParser(description="Convert between JSON and TOON.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    to_toon = subparsers.add_parser("to-toon", help="Convert JSON to TOON")
    to_toon.add_argument("input", nargs="?", default="-", help="Input JSON file (default: stdin)")
    to_toon.add_argument("-o", "--output", default="-", help="Output file (default: stdout)")
    to_toon.add_argument("--indent", type=int, default=2, help="Indent width (default: 2)")
    to_toon.add_argument("--stats", action="store_true", help="Print token/char comparison to stderr")

    to_json = subparsers.add_parser("to-json", help="Convert TOON to JSON")
    to_json.add_argument("input", nargs="?", default="-", help="Input TOON file (default: stdin)")
    to_json.add_argument("-o", "--output", default="-", help="Output file (default: stdout)")
    to_json.add_argument("--indent", type=int, default=2, help="JSON indent width (default: 2)")
    to_json.add_argument("--stats", action="store_true", help="Print token/char comparison to stderr")

    args = parser.parse_args()

    if args.command == "to-toon":
        input_text = _read_input(args.input)
        data = json.loads(input_text)
        toon_text = dumps(data, indent=args.indent)
        _write_output(args.output, toon_text)
        if args.stats:
            json_minified = json.dumps(data, separators=(",", ":"))
            _print_stats(compare(json_minified, toon_text))
    elif args.command == "to-json":
        input_text = _read_input(args.input)
        data = loads(input_text)
        json_text = json.dumps(data, indent=args.indent)
        _write_output(args.output, json_text)
        if args.stats:
            json_minified = json.dumps(data, separators=(",", ":"))
            _print_stats(compare(json_minified, input_text))


def _print_stats(stats):
    direction = "fewer" if stats["savings_pct"] >= 0 else "more"
    print(
        f"JSON: {stats['json_tokens']} tokens (~{stats['json_chars']} chars)  "
        f"TOON: {stats['toon_tokens']} tokens (~{stats['toon_chars']} chars)  "
        f"-> TOON uses {abs(stats['savings_pct'])}% {direction} tokens",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
