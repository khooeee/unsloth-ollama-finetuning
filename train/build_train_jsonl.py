#!/usr/bin/env python3
"""Compile train/sessions/*.yaml into train/train.jsonl (OpenAI messages format)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

TRAIN_DIR = Path(__file__).resolve().parent
SESSIONS_DIR = TRAIN_DIR / "sessions"
OUT_PATH = TRAIN_DIR / "train.jsonl"

SYSTEM_PROMPT = """You are a careful coding assistant that fixes bugs by inspecting code, editing files, and verifying with tests.

You have one tool: run_command — it runs bash inside a sandboxed workspace.

Typical loop:
1) reproduce / inspect with run_command
2) edit the code with run_command
3) re-run tests with run_command
4) briefly confirm the fix

Prefer small, targeted shell commands. Do not claim you edited a file unless you issued a command that does so."""


def normalize_message(raw: dict) -> dict:
    """Convert readable YAML message shapes into OpenAI-style JSONL messages."""
    role = raw["role"]
    msg: dict = {"role": role}

    if role == "assistant" and "tool_calls" in raw:
        tool_calls = []
        for i, tc in enumerate(raw["tool_calls"]):
            call_id = tc.get("id", f"call_{i+1}")
            name = tc["name"]
            args = tc.get("arguments", {})
            if isinstance(args, dict):
                args_str = json.dumps(args, ensure_ascii=False)
            else:
                args_str = str(args)
            tool_calls.append(
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": name, "arguments": args_str},
                }
            )
        msg["tool_calls"] = tool_calls
        # Keep optional assistant narration if present
        if raw.get("content"):
            msg["content"] = raw["content"]
        else:
            msg["content"] = ""
        return msg

    if role == "tool":
        msg["tool_call_id"] = raw.get("tool_call_id", raw.get("id", "call_1"))
        if "name" in raw:
            msg["name"] = raw["name"]
        msg["content"] = raw.get("content", "")
        return msg

    msg["content"] = raw.get("content", "")
    return msg


def session_to_record(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    messages = []
    has_system = any(m.get("role") == "system" for m in data["messages"])
    if not has_system:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
    for raw in data["messages"]:
        messages.append(normalize_message(raw))
    record = {"messages": messages}
    if "id" in data:
        record["id"] = data["id"]
    return record


def main() -> None:
    files = sorted(SESSIONS_DIR.glob("*.yaml"))
    if not files:
        raise SystemExit(f"No sessions found in {SESSIONS_DIR}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for path in files:
            record = session_to_record(path)
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote {len(files)} sessions → {OUT_PATH}")


if __name__ == "__main__":
    main()
