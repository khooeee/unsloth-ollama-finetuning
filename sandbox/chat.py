#!/usr/bin/env python3
"""
Interactive Ollama chat with run_command tool execution inside a session Docker container.

Lifecycle:
  - start: build image if needed, docker run -d (network=none, workspace mounted)
  - each tool call: docker exec in that container
  - Ctrl+C / exit: stop + remove container

Nothing runs on the host except the Docker client and Ollama HTTP calls.
"""

from __future__ import annotations

import atexit
import json
import signal
import subprocess
import sys
import uuid
from pathlib import Path

import requests

SANDBOX_DIR = Path(__file__).resolve().parent
WORKSPACE = SANDBOX_DIR / "workspace"
DOCKERFILE = SANDBOX_DIR / "Dockerfile"
IMAGE = "unsloth-ollama-sandbox:local"
OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = "my-custom-model"
CONTAINER_NAME = f"unsloth-sandbox-{uuid.uuid4().hex[:8]}"

SYSTEM = """You are a careful coding assistant working inside a sandboxed workspace at /workspace.

You have one tool: run_command — runs bash inside the sandbox container only.
Typical loop: inspect/reproduce → edit → re-run tests → brief confirmation.
The workspace already contains a small Python project with a deliberate bug in calc/ops.py.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a bash command inside the sandboxed /workspace (Docker). Arbitrary shell is allowed; blast radius is the container + mounted workspace only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Bash command to run with cwd=/workspace",
                    }
                },
                "required": ["command"],
            },
        },
    }
]

DEFAULT_PROMPT = (
    "In /workspace, pytest fails because divide(5, 2) returns 2 instead of 2.5. "
    "Use run_command to reproduce, fix calc/ops.py, and re-run pytest until green."
)

_container_started = False


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def ensure_image() -> None:
    probe = run(["docker", "image", "inspect", IMAGE], check=False)
    if probe.returncode == 0:
        return
    print(f"Building sandbox image {IMAGE}…")
    subprocess.run(
        ["docker", "build", "-t", IMAGE, "-f", str(DOCKERFILE), str(SANDBOX_DIR)],
        check=True,
    )


def start_container() -> None:
    global _container_started
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    ensure_image()
    run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            CONTAINER_NAME,
            "--network",
            "none",
            "-v",
            f"{WORKSPACE.resolve()}:/workspace",
            "-w",
            "/workspace",
            IMAGE,
            "sleep",
            "infinity",
        ]
    )
    _container_started = True
    print(f"Sandbox container started: {CONTAINER_NAME}")


def stop_container() -> None:
    global _container_started
    if not _container_started:
        return
    print(f"\nStopping sandbox container {CONTAINER_NAME}…")
    run(["docker", "rm", "-f", CONTAINER_NAME], check=False)
    _container_started = False


def docker_exec(command: str, timeout: int = 60) -> str:
    """Run arbitrary bash inside the session container."""
    try:
        proc = subprocess.run(
            ["docker", "exec", CONTAINER_NAME, "bash", "-lc", command],
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"[sandbox] command timed out after {timeout}s"
    out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    out = out.strip()
    if proc.returncode != 0:
        out = (out + f"\n[exit {proc.returncode}]").strip()
    return out or "[no output]"


def ollama_chat(messages: list[dict]) -> dict:
    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": MODEL,
            "messages": messages,
            "tools": TOOLS,
            "stream": False,
        },
        timeout=600,
    )
    if r.status_code != 200:
        raise SystemExit(f"Ollama error {r.status_code}: {r.text}")
    return r.json()


def extract_tool_calls(message: dict) -> list[dict]:
    return message.get("tool_calls") or []


def tool_call_to_result_message(tc: dict) -> dict:
    fn = tc.get("function") or {}
    name = fn.get("name", "")
    raw_args = fn.get("arguments", {})
    if isinstance(raw_args, str):
        try:
            args = json.loads(raw_args) if raw_args else {}
        except json.JSONDecodeError:
            args = {"command": raw_args}
    else:
        args = raw_args or {}

    if name != "run_command":
        content = f"Unknown tool: {name}"
    else:
        command = args.get("command", "")
        print(f"\n$ {command}")
        content = docker_exec(command)
        print(content)

    # Ollama accepts role=tool with content; include name when present
    msg = {"role": "tool", "content": content}
    if name:
        msg["name"] = name
    return msg


def chat_loop(initial_prompt: str) -> None:
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": initial_prompt},
    ]
    print(f"\nYou: {initial_prompt}\n")

    while True:
        resp = ollama_chat(messages)
        msg = resp.get("message") or {}
        messages.append(msg)

        content = (msg.get("content") or "").strip()
        if content:
            print(f"Assistant: {content}\n")

        tool_calls = extract_tool_calls(msg)
        if tool_calls:
            for tc in tool_calls:
                messages.append(tool_call_to_result_message(tc))
            continue

        # No tool calls — wait for next user turn
        try:
            user = input("You (empty to exit): ").strip()
        except EOFError:
            break
        if not user:
            break
        messages.append({"role": "user", "content": user})


def main() -> None:
    # Ensure Ollama is up
    try:
        requests.get(f"{OLLAMA_URL}/api/tags", timeout=3).raise_for_status()
    except Exception as e:
        raise SystemExit(
            "Cannot reach Ollama at http://127.0.0.1:11434. Start it, then:\n"
            "  ollama create my-custom-model -f Modelfile\n"
            f"Details: {e}"
        ) from e

    start_container()
    atexit.register(stop_container)

    def _sig(_signum, _frame):
        stop_container()
        sys.exit(130)

    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)

    prompt = " ".join(sys.argv[1:]).strip() or DEFAULT_PROMPT
    try:
        chat_loop(prompt)
    finally:
        stop_container()


if __name__ == "__main__":
    main()
