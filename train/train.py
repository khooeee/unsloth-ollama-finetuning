#!/usr/bin/env python3
"""
Fine-tune Qwen3-0.6B with Unsloth's MLX path on Apple Silicon, then export GGUF.

Reads:  train/train.jsonl  (build with train/build_train_jsonl.py)
Writes: outputs/my_model/  (GGUF via save_pretrained_gguf, q4_k_m)
"""

from __future__ import annotations

import json
from pathlib import Path

TRAIN_DIR = Path(__file__).resolve().parent
ROOT = TRAIN_DIR.parent
TRAIN_PATH = TRAIN_DIR / "train.jsonl"
OUTPUT_DIR = ROOT / "outputs"
GGUF_DIR = OUTPUT_DIR / "my_model"

# Non-4bit base so GGUF export stays reliable; we quantize at export time.
MODEL_NAME = "unsloth/Qwen3-0.6B"
MAX_SEQ_LENGTH = 1024
LORA_R = 16
MAX_STEPS = 60  # short feedback loop; raise when iterating seriously


def load_messages_dataset(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    if not rows:
        raise SystemExit(f"No training rows in {path}. Run: uv run train/build_train_jsonl.py")
    return rows


def main() -> None:
    try:
        from unsloth import FastMLXModel, MLXTrainer, MLXTrainingConfig
    except ImportError as e:
        raise SystemExit(
            "Could not import Unsloth MLX APIs (FastMLXModel / MLXTrainer).\n"
            "Use Python 3.11–3.13 via uv, then: uv sync --python 3.12\n"
            f"Original error: {e}"
        ) from e

    if not TRAIN_PATH.exists():
        raise SystemExit(f"Missing {TRAIN_PATH}. Run: uv run train/build_train_jsonl.py")

    print(f"Loading {MODEL_NAME} (load_in_4bit=False)…")
    model, tokenizer = FastMLXModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        load_in_4bit=False,
    )

    model = FastMLXModel.get_peft_model(
        model,
        r=LORA_R,
        lora_alpha=LORA_R * 2,
        target_modules="all-linear",
        use_gradient_checkpointing=True,
    )

    train_dataset = load_messages_dataset(TRAIN_PATH)
    print(f"Training on {len(train_dataset)} conversations from {TRAIN_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    args = MLXTrainingConfig(
        output_dir=str(OUTPUT_DIR),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        max_steps=MAX_STEPS,
        logging_steps=5,
        save_steps=MAX_STEPS,
    )

    trainer = MLXTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        args=args,
    )
    trainer.train()

    # Save LoRA adapters for iteration / resume experiments
    adapter_dir = OUTPUT_DIR / "lora_adapters"
    adapter_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    print(f"Saved LoRA adapters → {adapter_dir}")

    print("Exporting GGUF (q4_k_m)…")
    GGUF_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained_gguf(
        str(GGUF_DIR),
        tokenizer,
        quantization_method="q4_k_m",
    )
    print(f"GGUF export complete → {GGUF_DIR}")

    ggufs = sorted(GGUF_DIR.glob("*.gguf"))
    if not ggufs:
        raise SystemExit(f"No .gguf files found in {GGUF_DIR}")
    gguf = ggufs[-1]
    modelfile = ROOT / "Modelfile"
    modelfile.write_text(
        "\n".join(
            [
                f"FROM ./{gguf.relative_to(ROOT).as_posix()}",
                "",
                'SYSTEM """You are a careful coding assistant that fixes bugs by inspecting code, '
                "editing files, and verifying with tests. You may call run_command to run bash "
                'inside a sandbox."""',
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Updated Modelfile → FROM ./{gguf.relative_to(ROOT).as_posix()}")
    print("Next:")
    print("  ollama create my-custom-model -f Modelfile")
    print("  uv run sandbox/chat.py")


if __name__ == "__main__":
    main()
