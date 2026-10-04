#!/usr/bin/env python3
"""
Score held-out eval cases against model replies.

IMPORTANT: This script NEVER executes model-suggested commands.
It only grades text / tool-call structure from Ollama (or --dry-run fixtures).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "evals" / "cases"
OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = "my-custom-model"

SYSTEM = (
    "You are a careful coding assistant. Prefer inspect → edit → verify. "
    "When useful, call run_command with a bash command. "
    "Do not claim you ran commands unless you emit a run_command tool call."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run bash in a sandbox (eval does not execute; emit the call anyway).",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    }
]


def load_cases() -> list[dict]:
    cases = []
    for path in sorted(CASES_DIR.glob("*.yaml")):
        cases.append(yaml.safe_load(path.read_text()))
    return cases


def ollama_reply(prompt: str) -> dict:
    # Cap generation: Qwen3 can "think" / loop for a long time with the default
    # 32k context, which looks like a hang on later cases (e.g. e12).
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                "tools": TOOLS,
                "stream": False,
                "think": False,
                "options": {
                    "num_predict": 512,
                    "num_ctx": 4096,
                },
            },
            timeout=120,
        )
    except requests.Timeout as e:
        raise SystemExit(
            f"Ollama timed out after 120s on this case (model stuck generating?). "
            f"Try: ollama stop {MODEL}"
        ) from e
    r.raise_for_status()
    return r.json().get("message") or {}


def flatten_assistant_text(message: dict) -> str:
    parts = [message.get("content") or ""]
    for tc in message.get("tool_calls") or []:
        fn = tc.get("function") or {}
        parts.append(fn.get("name") or "")
        args = fn.get("arguments") or ""
        if isinstance(args, dict):
            args = json.dumps(args)
        parts.append(str(args))
    return "\n".join(parts)


def has_run_command(message: dict) -> bool:
    for tc in message.get("tool_calls") or []:
        fn = tc.get("function") or {}
        if fn.get("name") == "run_command":
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    return bool(args.strip())
            if isinstance(args, dict) and str(args.get("command", "")).strip():
                return True
    # Also accept textual pseudo-calls for weaker models
    text = message.get("content") or ""
    return bool(re.search(r"run_command\s*\(|\"name\"\s*:\s*\"run_command\"", text))


def count_steps(text: str) -> int:
    numbered = re.findall(r"(?m)^\s*\d+\.\s+\S+", text)
    bullets = re.findall(r"(?m)^\s*[-*]\s+\S+", text)
    return max(len(numbered), len(bullets), len(re.findall(r"pytest|rg |sed |python ", text)))


def grade(case: dict, message: dict) -> dict:
    rubric = case.get("rubric") or {}
    text = flatten_assistant_text(message)
    text_l = text.lower()

    checks = {}

    # Format / horizon
    min_steps = int(rubric.get("min_steps_or_commands", 1))
    steps = count_steps(text)
    checks["horizon"] = steps >= min_steps

    # Coverage
    needles = [n.lower() for n in rubric.get("must_mention_any", [])]
    checks["coverage"] = (not needles) or any(n in text_l for n in needles)

    # Tool requirement
    require_tool = bool(rubric.get("require_run_command") or case.get("requires_tool"))
    tool_ok = has_run_command(message)
    checks["tool"] = (not require_tool) or tool_ok

    # Order hints (soft): earlier hint should appear before later when both present
    order = [h.lower() for h in rubric.get("expect_ordered_hints", [])]
    if len(order) >= 2 and all(h in text_l for h in order):
        checks["order"] = text_l.index(order[0]) < text_l.index(order[1])
    else:
        checks["order"] = True

    forbidden = [f.lower() for f in rubric.get("forbidden_substrings", [])]
    checks["safety_text"] = not any(f in text_l for f in forbidden)

    passed = all(checks.values())
    return {"id": case["id"], "pass": passed, "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Grade fixture replies instead of calling Ollama",
    )
    args = parser.parse_args()

    cases = load_cases()
    results = []

    if args.dry_run:
        # Self-check the scorer with a clearly good / bad pair on first case
        good = {
            "content": "1. rg divide\n2. fix ops.py\n3. pytest -q",
            "tool_calls": [
                {
                    "function": {
                        "name": "run_command",
                        "arguments": {"command": "pytest -q"},
                    }
                }
            ],
        }
        print("dry-run sample grade:", grade(cases[0], good))
        return

    try:
        requests.get(f"{OLLAMA_URL}/api/tags", timeout=3).raise_for_status()
    except Exception as e:
        raise SystemExit(f"Ollama not reachable: {e}") from e

    for case in cases:
        print(f"Scoring {case['id']}…", flush=True)
        message = ollama_reply(case["prompt"])
        result = grade(case, message)
        results.append(result)
        status = "PASS" if result["pass"] else "FAIL"
        print(f"  {status} {result['checks']}", flush=True)

    n = len(results)
    passed = sum(1 for r in results if r["pass"])
    # Aggregate check rates
    keys = ["horizon", "coverage", "tool", "order", "safety_text"]
    agg = {k: sum(1 for r in results if r["checks"][k]) for k in keys}
    print("\n=== Summary ===")
    print(f"{passed}/{n} pass")
    print(" · ".join(f"{k} {agg[k]}/{n}" for k in keys))


if __name__ == "__main__":
    main()
