# Unsloth MLX → Ollama sandbox tutorial

Fine-tune a small model on **code-change** chats (inspect → edit → verify), export **GGUF q4_k_m**, then try a **real tool-use prompt** inside a **session-scoped Docker sandbox**.

Hardware target: Mac M5 with 32 GB memory

---

## Prerequisites

- macOS + Apple Silicon
- **Python 3.11–3.13** (Unsloth does not support 3.14 yet)
- [Ollama](https://ollama.com)
- Docker Desktop (or compatible Docker engine)
- `uv` recommended

---

## 1. Setup

```bash
cd unsloth-ollama-finetuning

# Use 3.12/3.13, not system 3.14
uv sync --python 3.12

# Build sandbox image once (has pytest; runs with --network=none later)
docker build -t unsloth-ollama-sandbox:local -f sandbox/Dockerfile sandbox

# Start ollama (in one tab)
ollama serve
```

---

## 2. Build training JSONL

Edit readable YAML under `data/sessions/`, then:

```bash
uv run scripts/build_dataset.py
```

This writes `data/train.jsonl`.

---

## 3. Train + export GGUF

```bash
uv run train.py
```

What it does:

1. Loads `unsloth/Qwen3-0.6B` with **`load_in_4bit=False`** (no train-time quant)
2. Applies LoRA and trains briefly on `data/train.jsonl` (quick loop defaults)
3. Saves adapters under `outputs/lora_adapters/`
4. Exports with:

```python
model.save_pretrained_gguf("my_model", tokenizer, quantization_method="q4_k_m")
```

5. Rewrites `Modelfile` `FROM` to the exported `.gguf`

Tune loop speed in `train.py`: `MAX_STEPS`, `LORA_R`, `MAX_SEQ_LENGTH`.

---

## 4. Create the Ollama model

```bash
ollama create my-custom-model -f Modelfile
```

---

## 5. Run a real tool-use prompt (sandbox)

```bash
uv run scripts/sandbox_chat.py
```

This:

1. Starts a Docker session container
2. Sends a default prompt: fix `divide` in `sandbox/workspace/calc/ops.py` using `run_command`
3. Executes each tool call with `docker exec`
4. On Ctrl+C / exit, stops and removes the container

Custom prompt:

```bash
uv run scripts/sandbox_chat.py "Reproduce the failing pytest, fix the bug, re-run tests."
```

Toy project layout:

```
sandbox/workspace/
  calc/ops.py      # deliberate bug: // instead of /
  tests/test_ops.py
```

---

## 6. Score the eval set

12 held-out prompts in `evals/cases/*.yaml`. Scoring is **deterministic text rubrics** — it does **not** run commands.

```bash
uv run evals/score.py
```

Example summary line: `8/12 pass · horizon … · coverage … · tool …`

Dry-run the scorer without Ollama:

```bash
uv run evals/score.py --dry-run
```

---

## Notes

- If Unsloth MLX import paths differ slightly by version, check the error from `train.py` and adjust imports to match your installed `unsloth` / `unsloth_zoo`
- **JSONL** is the training standard; **YAML** is the human-editable source
