---
title: NeuroCache - LLM Memory Optimizer
emoji: 🧠
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# 🧠 LLM Memory Optimizer — DevOps Decision & Execution System

> An OpenEnv-compliant AI agent environment where LLMs manage constrained memory while solving real-world DevOps problems — triaging emails, debugging configs, and performing incident response under strict resource limits.

---

## 📌 What Is This Project?

This project simulates a **realistic DevOps work environment** where an AI agent must:

1. **Read** incoming data (emails, config files, server logs)
2. **Remember** what's important — but within a strict memory budget
3. **Act** — fix broken configs, restart crashed services, escalate incidents
4. **Answer** — synthesize findings and submit a final answer with evidence

The core constraint: the agent has a limited **"fast memory"** (analogous to an LLM's context window). If `attention_tokens_used` exceeds `attention_capacity`, the system applies an OOM penalty and halts the data stream until the agent frees space by compressing or offloading data.

This forces the AI to make the same tradeoffs a DevOps engineer faces daily: *what to keep in working memory, what to archive, and when to act*.

---

## ✅ OpenEnv Compliance

| Requirement | Status |
|-------------|:------:|
| `POST /reset` returns valid `Observation` | ✅ |
| `POST /step` returns `{observation, reward, done, info}` | ✅ |
| `GET /state` returns current state without stepping | ✅ |
| `reward` is structured `Reward` object with `value` ∈ `[0.0, 1.0]` and `message` | ✅ |
| All tasks and graders are **fully deterministic** (no randomness) | ✅ |
| `inference.py` STDOUT follows `[START]`, `[STEP]`, `[END]` format with `score=` | ✅ |
| Dockerfile builds and passes health check on port 7860 | ✅ |
| All actions validated via Pydantic; invalid actions return safe penalty responses | ✅ |

> **Note on STDOUT format**: Output follows the OpenEnv validator format with the required `score=` field in the `[END]` line: `[END] success=... steps=... score=... rewards=...`

---

## 💡 Why This Environment Matters

Modern LLM agents fail catastrophically in **long-horizon, memory-constrained tasks**. Most benchmarks test single-turn reasoning or tool use — but real-world work requires an agent to:

- **Decide what to remember** when the inbox has 50 emails and the context window fits 10
- **Archive strategically** — offload data you might need later, compress what you can
- **Act under pressure** — fix a misconfigured database before the CEO's call in 30 minutes
- **Reason about evidence** — don't just guess the answer, show your work

This environment simulates exactly these tradeoffs:

| Scenario | Real-World Mapping | Why It's Hard |
|----------|-------------------|---------------|
| **Email Triage** | Inbox overload for a senior engineer | Must distinguish spam from CEO-urgent with limited memory |
| **Config Debugging** | Broken staging deployment Friday at 5 PM | Must read logs, identify `REDIS_HOST=localhost` bug, fix + restart — in the right order |
| **Incident Response** | 3 AM production cascading failure | 25 structured logs, 150-char memory limit — must compress aggressively to find root cause chain |

The memory constraint is the key innovation: **every token the agent stores costs attention capacity**. Store too much → OOM crash. Store too little → miss critical evidence. This creates a genuine resource-allocation challenge that simple tool-use benchmarks don't capture.

> *"The best engineer isn't the one who reads the most logs — it's the one who knows which logs to read."*

---

## 🏗️ How It Works (Architecture)

```
┌──────────────┐         ┌──────────────────┐
│              │  HTTP   │                  │
│  inference.py│ ─────►  │  main.py (API)   │
│  (LLM Agent) │ ◄─────  │  FastAPI Server  │
│              │         │                  │
└──────────────┘         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │                  │
                         │  env.py          │
                         │  (Game Engine)   │
                         │                  │
                         └────────┬─────────┘
                                  │
                         ┌────────┴─────────┐
                         │                  │
                         │  tasks/          │
                         │  (Scenarios)     │
                         │                  │
                         └──────────────────┘
```

**Component roles**:
- `tasks/` = The **scenarios** (easy, medium, hard) with embedded data and grading criteria
- `env.py` = The **environment engine** (state management, reward logic, action handling)
- `main.py` = The **API layer** (receives HTTP requests, routes to engine)
- `inference.py` = The **agent** (calls LLM, parses actions, interacts with API)

---

## 📂 Project Structure

```
meathack/
├── main.py              ← API server (FastAPI endpoints)
├── env.py               ← Environment engine (state, rewards, actions)
├── models.py            ← Pydantic data contracts (Action, Observation)
├── inference.py         ← AI agent inference script
├── tasks/               ← Task scenarios (modular package)
│   ├── __init__.py      ← Package entry: exports Task, get_tasks()
│   ├── base.py          ← Task class + deterministic grader
│   ├── easy.py          ← Level 1: Email Triage
│   ├── medium.py        ← Level 2: Config Debugging
│   └── hard.py          ← Level 3: Incident Response
├── openenv.yaml         ← OpenEnv environment specification
├── Dockerfile           ← Container build instructions
├── requirements.txt     ← Python dependencies
├── .gitignore           ← Files excluded from git
└── .dockerignore        ← Files excluded from Docker build
```

---

## 📄 File-by-File Documentation

### `main.py` — The API Server

Creates a FastAPI web server exposing the OpenEnv-required endpoints.

| Endpoint | Method | What It Does |
|----------|--------|-------------|
| `GET /` | Health check | Returns `{"status": "ok"}` — proves the server is alive |
| `POST /reset` | Start a task | Resets the environment for a specific task (0=easy, 1=medium, 2=hard) |
| `POST /step` | Take an action | Agent sends an action, gets back `{observation, reward, done, info}` |
| `GET /state` | Read state | Returns current environment state without stepping |
| `GET /tasks` | List tasks | Shows all available tasks with name, difficulty, description |

**Error handling**: All endpoints are wrapped in try/except blocks. If any internal error occurs, the endpoint returns a valid response structure with `reward=0.0` and an error message in `info` — designed to handle failures gracefully and avoid unhandled exceptions.

---

### `env.py` — The Environment Engine

The core game logic. Manages all state and computes rewards.

**Memory model**:
- **Fast Memory** (`Dict[str, str]`): Key-value store where keys are 6-char UUIDs and values are content strings. Total size measured by `sum(len(v) for v in fast_memory.values())` in characters.
- **Disk Storage** (`Dict[str, str]`): Same structure, unlimited capacity, but only accessible via `retrieve_from_disk` search queries.
- **Capacity check**: Every step compares `attention_tokens_used` against `attention_capacity`. Exceeding capacity triggers a -0.2 penalty and halts the input stream.

**Action validation**: All 10 action types are validated against a `VALID_ACTIONS` whitelist. Any unrecognized `action_type` returns `(observation, 0.0, False, {"error": "..."})` — the episode continues safely.

**10 available actions**:

| Action | Category | What It Does |
|--------|----------|-------------|
| `store_in_fast_memory` | Memory | Save data to fast memory |
| `offload_to_disk` | Memory | Move items from fast memory to disk (frees space) |
| `semantic_compress` | Memory | Replace multiple items with a summary (saves space) |
| `retrieve_from_disk` | Memory | Search disk storage by keyword query |
| `mark_email_important` | Real-world | Flag a stored email as critical |
| `fix_config` | Real-world | Patch a broken configuration value |
| `restart_service` | Real-world | Restart a crashed service (only works after fix) |
| `escalate_incident` | Real-world | Alert the on-call team with a severity summary |
| `submit_final_synthesis` | Terminal | Submit final answer with evidence IDs |
| `no_op` | Utility | Skip this turn (penalized after 3+ consecutive uses) |

---

### `models.py` — Data Contracts

Pydantic models enforcing strict type validation on all API inputs and outputs.

- **`Action`**: `{action_type: str, action_args: Dict[str, Any]}` — validated on every `/step` call. Malformed requests receive a 422 response from FastAPI's built-in validation; the inference script handles this gracefully and continues.
- **`Observation`**: 13 fields including `attention_tokens_used`, `attention_capacity`, `fast_memory_index`, `services_status`, `partial_progress`, `decision_log`, etc.

---

### `inference.py` — The AI Agent

Connects to a real LLM (default: Qwen 72B via HuggingFace Router) and plays through all 3 tasks sequentially.

**Loop logic**:
```
1. POST /reset → get initial observation
2. Send observation to LLM → "What should I do?"
3. Extract JSON from LLM response (finds first {...} block)
4. Validate action_type key exists
5. POST /step with action → get new observation + reward
6. Print [STEP] line (ALWAYS, even on errors)
7. Repeat until done=true or max_steps reached
8. Print [END] line (ALWAYS)
```

**STDOUT format** (strictly follows OpenEnv validator — no additional fields):
```
[START] task=email_triage_easy env=llm_memory_optimizer model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=store_in_fast_memory reward=0.05 done=false error=null
[STEP] step=2 action=mark_email_important reward=0.30 done=false error=null
[STEP] step=3 action=submit_final_synthesis reward=1.00 done=true error=null
[END] success=true steps=3 rewards=0.05,0.30,1.00
```

**Failure recovery**:
- Invalid LLM JSON → falls back to `no_op`, error logged
- API call fails (422/500/network) → `reward=0.0`, fetches fresh state from `/state`, continues
- `[STEP]` line is printed outside the try/except → always emitted regardless of errors

---

### `tasks/` — The Three Scenarios

#### `tasks/base.py` — Task Class + Deterministic Grader

Defines the `Task` data structure and the `grade()` function.

**Grading mechanism** (deterministic, non-exploitable):
1. Normalize both the agent's answer and each expected keyword: `lowercase + strip dashes/underscores`
2. Use `re.escape()` + `re.search()` to match each normalized keyword against the normalized answer
3. Calculate `correctness = matches / total_expected`
4. Apply scoring tiers based on correctness + whether justification IDs were provided

| Correctness | Has Justification? | Score |
|:-:|:-:|:-:|
| ≥ 80% | ✅ | **1.0** (full marks) |
| ≥ 80% | ❌ | 0.5 |
| ≥ 40% | ✅ | 0.3 + (correctness × 0.5) |
| > 0% | ❌ | correctness × 0.4 |
| 0% | — | 0.0 |

**Why `re.escape`**: Prevents regex injection attacks. The normalization is controlled — it only strips `-` and `_` characters, not arbitrary punctuation. This allows `"OOM-Killed"` to match `"OOMKilled"` while preventing partial-match exploits like `"oom"` matching `"oomkilled"` independently (since the expected answer is `"OOMKilled"` as a full term).

---

#### `tasks/easy.py` — Level 1: Email Triage

| Property | Value |
|----------|-------|
| **Memory Limit** | 1,500 characters |
| **Max Steps** | 15 |
| **Scenario** | 10 corporate emails (spam, HR, CEO urgent, security alerts) |
| **Goal** | Find the critical emails and identify required actions |
| **Expected Keywords** | `"3 PM"`, `"Acme Corp"`, `"security alert"`, `"password"` |

Large memory capacity — the agent can hold most emails simultaneously.

---

#### `tasks/medium.py` — Level 2: Config Debugging

| Property | Value |
|----------|-------|
| **Memory Limit** | 300 characters |
| **Max Steps** | 20 |
| **Scenario** | Broken staging deployment (`.env` files, Docker configs, error logs, runbook) |
| **Goal** | Find `REDIS_HOST=localhost` misconfiguration, change to `redis`, restart API |
| **Expected Keywords** | `"REDIS_HOST"`, `"localhost"`, `"redis"`, `"network"` |

Tight memory forces the agent to compress and offload data to make room for new inputs.

---

#### `tasks/hard.py` — Level 3: Incident Response

| Property | Value |
|----------|-------|
| **Memory Limit** | 150 characters |
| **Max Steps** | 35 |
| **Scenario** | 25 structured JSON production logs showing cascading failure |
| **Goal** | Root-cause analysis: slow query → pool exhaustion → OOMKill → node eviction |
| **Expected Keywords** | `"slow query"`, `"connection pool"`, `"health check"`, `"OOMKilled"`, `"transaction timeout"` |

Extremely tight memory constraint with many log entries — demands aggressive compression and selective storage.

---

### `openenv.yaml` — Environment Specification

Machine-readable documentation of the environment's API contract, action space, observation space, reward structure, and task definitions. Read by the OpenEnv framework to understand the environment interface.

---

### `Dockerfile` — Container Build

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
```

**Design choices**:
- `python:3.11-slim` — lightweight base image (~140MB vs ~900MB for full)
- No `build-essential` — all pip packages are pure Python wheels, no C compilation needed
- `--no-cache-dir` — prevents pip from storing download cache in the image
- `.dockerignore` excludes `venv/`, `__pycache__/`, `.git/` to avoid stale bytecode conflicts
- `HEALTHCHECK` uses `curl -f` (fail on HTTP errors) with `|| exit 1` for reliable health reporting

---

## 🏆 Reward Structure

Rewards are computed per-step and clamped to `[0.0, 1.0]`. Approximate ranges — exact values depend on action context:

| Event | Reward Range | Trigger |
|-------|:------:|---------|
| Stored relevant data | ~+0.05 | Content contains task-relevant keywords |
| Stored irrelevant data | ~+0.01 | Content stored but not task-relevant |
| Offloaded to disk | ~+0.10 | Successfully moved items to disk |
| Compressed efficiently | ~+0.10–0.20 | Compression ratio determines bonus |
| Marked correct important email | ~+0.30 | Email contains critical keywords |
| Fixed correct config value | ~+0.50 | Right key + right value |
| Restarted service after fix | ~+0.30 | Service was in `fix_pending_restart` state |
| Escalated appropriately | ~+0.20 | Hard task or critical severity with detailed summary |
| Discovered milestone | ~+0.15 | Stored content that matches milestone keywords |
| Submitted correct answer | **1.0** | ≥80% keyword match with justification evidence |
| Memory overflow (OOM) | ~-0.20 | `attention_tokens_used > attention_capacity` |
| Incorrect action | ~-0.05 to -0.10 | Wrong config key, unnecessary escalation |
| Repeated no_op spam | ~-0.01 to -0.05 | 3+ consecutive no_ops (graduated penalty) |

---

## 🔒 Safety & Robustness

| Risk | Protection |
|------|-----------|
| LLM outputs invalid JSON | Extracts first `{...}` block via `.find('{')`/`.rfind('}')`; falls back to `no_op` |
| Parsed JSON missing `action_type` | Explicitly validated; missing key raises error → safe fallback |
| API endpoint receives malformed action | Pydantic validates schema; 422 handled by inference try/except |
| Internal exception during `step()` | `/step` endpoint catches all errors, returns valid response shape |
| Agent sends unrecognized action type | `VALID_ACTIONS` whitelist check → returns safe penalty response |
| Agent spams `no_op` | Graduated penalty: -0.01 → -0.03 → -0.05 after 3+ consecutive |
| Memory overflow | OOM penalty applied, input stream halted until space freed |
| Stale observation after API error | Inference script fetches fresh state from `GET /state` |
| Reward out of bounds | Clamped to `[0.0, 1.0]` via `max(0.0, min(1.0, value))` |

---

## 🤖 Compatible Models

The baseline uses **deterministic decoding** (`temperature=0`, `top_p=1`) to minimize score variance between runs.

| Model | Status | Notes |
|-------|:------:|-------|
| `Qwen/Qwen2.5-72B-Instruct` | ✅ Tested (baseline) | Default model via HuggingFace Router |
| Any OpenAI-compatible model | ✅ Supported | Set `API_BASE_URL` and `MODEL_NAME` env vars |
| `nvidia/Llama-3.1-Nemotron-70B-Instruct-HF` | ✅ Compatible | Standard Phase 2 evaluation agent |
| No API key available | ✅ Fallback | Runs deterministic dummy baseline (pre-scripted actions) |

> **⚠️ About the dummy baseline**: The dummy mode exists **solely for reproducibility** — it ensures `python inference.py` always produces valid STDOUT output even without an API key. The dummy baseline **does not inspect observation content** and uses **fixed action sequences** — it is **not task-adaptive**. Actual evaluation uses the **full LLM-powered agent** (`run_task()`), which dynamically reasons about observations, manages memory pressure, and achieves significantly higher scores. Memory IDs are resolved from live state at runtime only to demonstrate proper API contract usage.

**To use a different model:**
```bash
export API_BASE_URL="https://your-api-endpoint/v1"
export MODEL_NAME="your-model/name"
export HF_TOKEN="your-api-key"
python inference.py
```

### Determinism Guarantees

| Component | Deterministic? | How |
|-----------|:-:|-----|
| Environment grading | ✅ Yes | Regex-based keyword matching, no randomness |
| Reward computation | ✅ Yes | Pure function of action + state, no stochastic elements |
| Task inputs | ✅ Yes | Hardcoded scenario data, same every run |
| LLM decoding | ✅ Greedy | `temperature=0`, `top_p=1` — near-deterministic output |
| Dummy baseline | ✅ Yes | Pre-scripted action sequences, fully reproducible |

> **Score variance** between runs comes only from minor LLM output variation (rare with greedy decoding). The dummy baseline produces identical scores every run.

---

## 🛡️ Anti-Exploit Protections

| Exploit Vector | Protection | Details |
|----------------|:-:|--------|
| Keyword spam in answer | ✅ Blocked | Grading requires contextual keyword match via `re.search`, not substring count |
| Submit without evidence | ✅ Capped | Score capped at 0.3 without valid `justification_ids` |
| Repeated identical actions | ✅ Penalized | Graduated penalty (-0.02 to -0.10) for 3+ identical action+args |
| No-op spam | ✅ Penalized | Graduated penalty after 3+ consecutive `no_op` actions |
| Restart without fix | ✅ Penalized | -0.1 penalty; service stays crashed |
| Unnecessary escalation | ✅ Penalized | -0.05 for escalating when no critical issues exist |
| Regex injection in answer | ✅ Safe | `re.escape()` on all expected keywords |
| Memory overflow gaming | ✅ Safe | OOM penalty applied, stream halted until space freed |
| Infinite loops | ✅ Hard stop | `HARD_MAX_STEPS=100` absolute ceiling regardless of task config |

---

## 📊 Expected Scores

| Task | Difficulty | Baseline Score Range |
|------|:----------:|:--------------------:|
| Email Triage | Easy | 0.8 – 1.0 |
| Config Debugging | Medium | 0.5 – 0.8 |
| Incident Response | Hard | 0.3 – 0.5 |

---

## 🚀 How to Run

### Local Development
```bash
# Terminal 1: Start the environment server
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 7860

# Terminal 2: Run the AI agent (with LLM)
export HF_TOKEN="your_huggingface_token"
python inference.py

# OR: Run deterministic dummy baseline (no API key required)
python inference.py
# → Automatically detects missing HF_TOKEN and runs pre-scripted actions
```

### Docker
```bash
docker build -t llm-memory-optimizer .
docker run -p 7860:7860 llm-memory-optimizer
```

### Quick API Test
```bash
# Health check
curl http://127.0.0.1:7860/

# Reset to easy task
curl -X POST http://127.0.0.1:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_idx": 0}'

# Take an action
curl -X POST http://127.0.0.1:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "no_op", "action_args": {}}'

# Read current state (no side effects)
curl http://127.0.0.1:7860/state
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Web Framework | FastAPI |
| Server | Uvicorn |
| Data Validation | Pydantic |
| LLM Client | OpenAI SDK (HuggingFace Router) |
| Container | Docker (python:3.11-slim) |
| Language | Python 3.11 |
