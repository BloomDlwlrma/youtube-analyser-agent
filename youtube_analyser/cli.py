from __future__ import annotations

import argparse
import sys

from .service import run_analysis
from .models import AnalyzeRequest


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a YouTube video with local Ollama.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze = subparsers.add_parser("analyze")
    analyze.add_argument("url")
    analyze.add_argument("--language", default="zh")
    analyze.add_argument("--model", default="llama3.1:8b")
    analyze.add_argument("--whisper-model", default="small")
    analyze.add_argument("--output-dir")
    args = parser.parse_args()
    try:
        AnalyzeRequest(url=args.url, language=args.language, model=args.model,
                       whisper_model=args.whisper_model)
        result = run_analysis(
            args.url,
            language=args.language,
            model=args.model,
            whisper_model=args.whisper_model,
            output_dir=args.output_dir,
        )
    except (ValueError, RuntimeError) as exc:
        print(f"Analysis failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(result.model_dump_json(indent=2))
