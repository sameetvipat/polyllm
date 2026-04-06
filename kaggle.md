# Kaggle Notebook Cells for PolyLLM Chairman Training

Use this as a copy-paste cell guide in Kaggle.

## Before You Run

1. Enable GPU in Kaggle notebook settings.
2. Add a Kaggle dataset containing:
- `train.jsonl`
- `val.jsonl`
3. If available, add another dataset containing your latest checkpoint folder (for resume).
4. Add Kaggle Secrets:
- `HF_TOKEN`
- `HF_USERNAME`

## Cell 1: Install packages

```python
!pip -q install "unsloth[kaggle-new] @ git+https://github.com/unslothai/unsloth.git"
!pip -q install --no-deps "trl>=0.11.0" "peft>=0.13.0" "accelerate>=0.34.0" "datasets>=3.0.0" huggingface_hub
!pip -q install modelscope

print("Packages installed")
print("If Kaggle asks for restart, restart session, then continue from Cell 2.")
```

## Cell 2: Environment setup

```python
import os

os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "600"
os.environ["HF_HUB_ETAG_TIMEOUT"] = "60"
os.environ["UNSLOTH_USE_MODELSCOPE"] = "1"

print("Env vars applied")
```

## Cell 3: GPU check

```python
import torch
print("GPU:", torch.cuda.get_device_name(0))
print("VRAM:", f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
print("CUDA:", torch.version.cuda)
```

## Cell 4: Hugging Face login

```python
from kaggle_secrets import UserSecretsClient
from huggingface_hub import login

secrets = UserSecretsClient()
HF_TOKEN = secrets.get_secret("HF_TOKEN")
HF_USERNAME = secrets.get_secret("HF_USERNAME")

login(token=HF_TOKEN)
print("Logged in to Hugging Face as:", HF_USERNAME)
```

## Cell 5: Set dataset paths

```python
import os

# Update to your Kaggle dataset input path
DATASET_DIR = "/kaggle/input/polyllm-dataset"

TRAIN_PATH = f"{DATASET_DIR}/train.jsonl"
VAL_PATH = f"{DATASET_DIR}/val.jsonl"

assert os.path.exists(TRAIN_PATH), f"Missing {TRAIN_PATH}"
assert os.path.exists(VAL_PATH), f"Missing {VAL_PATH}"

print("Train:", TRAIN_PATH)
print("Val:", VAL_PATH)
```

## Cell 6: Load and format dataset

```python
from datasets import load_dataset

dataset = load_dataset("json", data_files={
    "train": TRAIN_PATH,
    "validation": VAL_PATH,
})

print("Train examples:", len(dataset["train"]))
print("Val examples:", len(dataset["validation"]))

def format_example(example):
    text = (
        f"<s>[INST] <<SYS>>\n{example['instruction']}\n<</SYS>>\n\n"
        f"{example['input']} [/INST] "
        f"{example['output']} </s>"
    )
    return {"text": text}

dataset = dataset.map(
    format_example,
    remove_columns=["id", "domain", "instruction", "input", "output"],
)

print("Sample:", dataset["train"][0]["text"][:300])
```

## Cell 7: Load base model (4-bit)

```python
from unsloth import FastLanguageModel
import torch

BASE_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
MAX_SEQ_LEN = 4096

print("Loading", BASE_MODEL, "in 4-bit")

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=BASE_MODEL,
    max_seq_length=MAX_SEQ_LEN,
    dtype=None,
    load_in_4bit=True,
    token=HF_TOKEN,
)

tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

print("Model loaded. VRAM used:", f"{torch.cuda.memory_allocated() / 1e9:.2f} GB")
```

## Cell 8: Configure LoRA

```python
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

model.print_trainable_parameters()
```

## Cell 9: Training arguments

```python
from transformers import TrainingArguments
import os

WORK_DIR = "/kaggle/working/polyllm-chairman"
CHECKPOINT_DIR = f"{WORK_DIR}/checkpoints"
ADAPTER_DIR = f"{WORK_DIR}/adapter"

os.makedirs(CHECKPOINT_DIR, exist_ok=True)
os.makedirs(ADAPTER_DIR, exist_ok=True)

training_args = TrainingArguments(
    output_dir=CHECKPOINT_DIR,
    num_train_epochs=3,
    per_device_train_batch_size=1,
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=16,
    gradient_checkpointing=True,
    optim="paged_adamw_32bit",
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_steps=11,
    logging_steps=10,
    eval_steps=50,
    save_steps=25,
    save_total_limit=10,
    eval_strategy="steps",
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    fp16=True,
    report_to="none",
    dataloader_pin_memory=False,
)

print("Training args configured")
print("Checkpoint dir:", CHECKPOINT_DIR)
```

## Cell 10: Trainer and auto-resume

```python
from trl import SFTTrainer
import glob
import os

# Update if you uploaded old checkpoints as a Kaggle dataset
RESUME_INPUT_ROOT = "/kaggle/input/polyllm-checkpoints"

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset["train"],
    eval_dataset=dataset["validation"],
    tokenizer=tokenizer,
    args=training_args,
    dataset_text_field="text",
    max_seq_length=MAX_SEQ_LEN,
    packing=False,
)

def find_latest_checkpoint():
    candidates = []
    if os.path.exists(CHECKPOINT_DIR):
        candidates += glob.glob(f"{CHECKPOINT_DIR}/checkpoint-*")
    if os.path.exists(RESUME_INPUT_ROOT):
        candidates += glob.glob(f"{RESUME_INPUT_ROOT}/checkpoint-*")
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: int(p.split("-")[-1]))[-1]

resume_from = find_latest_checkpoint()

if resume_from:
    print("Resuming from checkpoint:", resume_from)
else:
    print("Starting fresh training")

trainer.train(resume_from_checkpoint=resume_from)
print("Training complete")
```

## Cell 11: Save adapter

```python
model.save_pretrained(ADAPTER_DIR)
tokenizer.save_pretrained(ADAPTER_DIR)
print("Adapter saved to:", ADAPTER_DIR)
```

## Cell 12: Push adapter to Hugging Face Hub

```python
repo_id = f"{HF_USERNAME}/polyllm-chairman"

model.push_to_hub(repo_id, token=HF_TOKEN)
tokenizer.push_to_hub(repo_id, token=HF_TOKEN)

print("Pushed to:", repo_id)
```

## Cell 13: Quick inference test

```python
from transformers import pipeline

pipe = pipeline(
    "text-generation",
    model=ADAPTER_DIR,
    tokenizer=ADAPTER_DIR,
    device_map="auto",
)

prompt = "<s>[INST] <<SYS>>You are a council chairman. Synthesize the best final answer. <</SYS>>\n\nQuestion: Why is the sky blue? [/INST]"
out = pipe(prompt, max_new_tokens=200, do_sample=False)
print(out[0]["generated_text"])
```
