#!/usr/bin/env python3
"""Analyze LLM token usage and estimated cost from llm_logs."""

import csv
from pathlib import Path
from collections import defaultdict

LLM_LOG_DIR = Path(__file__).resolve().parent / "backend" / "llm_logs"

# Pricing per 1M tokens (input, output) in USD
PRICING = {
    # OpenAI
    "gpt-4o-mini":          (0.15,  0.60),
    "gpt-4o":               (2.50,  10.00),
    "gpt-4":                (30.00, 60.00),
    # Gemini
    "gemini/gemini-2.0-flash":          (0.10, 0.40),
    "gemini/gemini-3-flash-preview":    (0.10, 0.40),
    "gemini/gemini-3.1-flash-lite-preview": (0.05, 0.20),
    "gemini/gemini-3-pro-preview":      (1.25, 10.00),
    # Anthropic
    "claude-sonnet-4-6":    (3.00, 15.00),
    "claude-haiku-4-5":     (0.80,  4.00),
}

DEFAULT_PRICING = (1.00, 3.00)  # fallback


def detect_model(session_dir: str, rows: list) -> str:
    """Try to detect model from game log player column."""
    game_log_dir = LLM_LOG_DIR.parent / "logs" / session_dir
    # Check if any game log CSV has this session_id in filename
    # For now, infer from the player column in game logs
    # Fallback: return "unknown"
    return "unknown"


def analyze():
    if not LLM_LOG_DIR.exists():
        print("No llm_logs/ directory found.")
        return

    # Structure: {(model, game, difficulty): {"steps": N, "input": N, "output": N, "sessions": N}}
    summary = defaultdict(lambda: {"steps": 0, "input_tokens": 0, "output_tokens": 0, "sessions": 0})

    # Also try to match with game logs to get model name and difficulty
    game_log_dir = LLM_LOG_DIR.parent / "logs"

    for game_dir in sorted(LLM_LOG_DIR.iterdir()):
        if not game_dir.is_dir():
            continue
        game_name = game_dir.name

        for log_file in sorted(game_dir.glob("*.csv")):
            session_id = log_file.stem

            # Read LLM log
            with open(log_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            if not rows:
                continue

            total_input = 0
            total_output = 0
            for row in rows:
                total_input += int(row.get("input_tokens", 0) or 0)
                total_output += int(row.get("output_tokens", 0) or 0)

            # Try to find matching game log for model name and difficulty
            model = "unknown"
            difficulty = "?"
            game_log_subdir = game_log_dir / game_name
            if game_log_subdir.exists():
                for glog in game_log_subdir.glob(f"{session_id}*.csv"):
                    with open(glog, encoding="utf-8") as gf:
                        greader = csv.DictReader(gf)
                        for grow in greader:
                            if grow.get("player"):
                                model = grow["player"]
                            if grow.get("difficulty"):
                                difficulty = grow["difficulty"]
                            break
                    break

            key = (model, game_name, difficulty)
            summary[key]["steps"] += len(rows)
            summary[key]["input_tokens"] += total_input
            summary[key]["output_tokens"] += total_output
            summary[key]["sessions"] += 1

    if not summary:
        print("No log data found.")
        return

    # Print table
    header = f"{'Model':<30} {'Game':<15} {'Diff':<6} {'Sess':>4} {'Steps':>5} {'Input Tok':>10} {'Output Tok':>10} {'Est. Cost':>10}"
    sep = "=" * len(header)
    print(sep)
    print(header)
    print("-" * len(header))

    total_input_all = 0
    total_output_all = 0
    total_cost_all = 0.0

    for (model, game, diff), stats in sorted(summary.items()):
        inp = stats["input_tokens"]
        out = stats["output_tokens"]
        pricing = PRICING.get(model, DEFAULT_PRICING)
        cost = (inp / 1_000_000) * pricing[0] + (out / 1_000_000) * pricing[1]

        total_input_all += inp
        total_output_all += out
        total_cost_all += cost

        print(f"{model:<30} {game:<15} {diff:<6} {stats['sessions']:>4} {stats['steps']:>5} {inp:>10,} {out:>10,} ${cost:>8.4f}")

    print("-" * len(header))
    print(f"{'TOTAL':<30} {'':<15} {'':<6} {'':<4} {'':<5} {total_input_all:>10,} {total_output_all:>10,} ${total_cost_all:>8.4f}")
    print(sep)


if __name__ == "__main__":
    analyze()
