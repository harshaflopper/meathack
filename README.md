# LLM Memory Optimizer — DevOps Decision & Execution System

## Description

A real-world OpenEnv environment that simulates **AI-assisted DevOps debugging and operational decision-making** under strict compute and memory constraints. Agents must triage corporate emails, debug production configuration issues, and perform incident root-cause analysis — all while managing a constrained "fast memory" context window (analogous to an LLM's limited context).

This environment uniquely combines **memory management** (store, compress, offload, retrieve) with **real-world actions** (fix configurations, restart services, escalate incidents), creating a hybrid decision + execution system that mirrors actual DevOps workflows.

## Motivation

Modern AI agents deployed in production face two simultaneous challenges:
1. **Context window limitations** — they can't hold everything in memory
2. **Real-world decision-making** — they must take concrete actions, not just analyze

This environment trains agents to handle both — managing information efficiently while making correct operational decisions under pressure. It directly models tasks that SRE/DevOps teams perform daily: email triage, config debugging, and incident response.

---

## Action Space (9 + 1 Actions)

### Memory Management Actions
| Action | Args | Description |
|--------|------|-------------|
| `store_in_fast_memory` | `{content: str}` | Store data in the active context window |
| `offload_to_disk` | `{fast_memory_ids: [str]}` | Move items to slow disk to free memory |
| `semantic_compress` | `{fast_memory_ids: [str], summary: str}` | Summarize multiple items into one |
| `retrieve_from_disk` | `{query: str, limit: int}` | Search disk for previously stored data |

### Real-World Actions
| Action | Args | Description |
|--------|------|-------------|
| `mark_email_important` | `{memory_id: str}` | Flag an email as critical (rewarded if correct) |
| `fix_config` | `{target: str, new_value: str}` | Patch a misconfigured setting |
| `restart_service` | `{service_name: str}` | Restart a service (only works after fix) |
| `escalate_incident` | `{summary: str, severity: str}` | Escalate to on-call team |

### Terminal Action
| Action | Args | Description |
|--------|------|-------------|
| `submit_final_synthesis` | `{answer: str, justification_ids: [str]}` | Submit answer with evidence |
| `no_op` | `{}` | Skip this cycle |

---

## Observation Space

| Field | Type | Description |
|-------|------|-------------|
| `current_stream_chunk` | `str?` | Latest incoming data (email, log, config file) |
| `attention_tokens_used` | `int` | Current fast memory usage |
| `attention_capacity` | `int` | Max before OOM crash |
| `disk_storage_count` | `int` | Items on disk |
| `fast_memory_index` | `{id: content}` | Contents in fast memory |
| `disk_index_preview` | `{id: size}` | Disk storage summary |
| `recent_disk_retrieval` | `str?` | Latest disk query result |
| `task_goal` | `str` | What to accomplish |
| `task_type` | `str` | easy / medium / hard |
| `cpu_cycles_left` | `int` | Turns remaining |
| `status_message` | `str` | Last action result |
| `partial_progress` | `{milestone: bool}` | Intermediate milestones achieved |
| `decision_log` | `[str]` | Chronological decision history |
| `services_status` | `{name: status}` | Live service health |

---

## Tasks & Expected Difficulty

### Task 1: Email Triage (Easy)
- **Capacity**: 1500 tokens | **Cycles**: 15
- **Scenario**: 10 realistic corporate emails (spam, HR, security alerts, CEO urgent messages)
- **Goal**: Identify critical action items, mark important emails
- **Baseline Score**: ~0.8–1.0

### Task 2: Config Debugging (Medium)
- **Capacity**: 300 tokens | **Cycles**: 20
- **Scenario**: Staging deployment failure — `.env` files, docker-compose configs, application error logs, troubleshooting runbook
- **Goal**: Find `REDIS_HOST=localhost` misconfiguration, fix it, restart services
- **Baseline Score**: ~0.5–0.8

### Task 3: Incident Response (Hard)
- **Capacity**: 150 tokens | **Cycles**: 35
- **Scenario**: 25 structured JSON production logs showing cascading failure: slow query → pool exhaustion → health check failure → OOMKill → node eviction
- **Goal**: Root-cause analysis, identify chain of events, escalate with evidence
- **Baseline Score**: ~0.3–0.5

---

## Reward Structure

| Component | Reward | Trigger |
|-----------|--------|---------|
| **Correctness** | +0.3 to +0.5 | Correct real-world action (mark, fix, restart) |
| **Partial Milestone** | +0.15 each | Discovering key evidence in logs/configs |
| **Efficiency Bonus** | +0.05 to +0.1 | Completing task in fewer cycles |
| **Memory Bonus** | +0.05 to +0.1 | Staying within memory capacity |
| **Final Success** | 1.0 | Correct synthesis with justification |
| **OOM Penalty** | -0.2 | Exceeding memory capacity |
| **Wrong Action** | -0.05 to -0.1 | Incorrect fix, unnecessary escalation |

---

## Setup & Usage

### 1. Start the Environment Server
```bash
uvicorn main:app --host 0.0.0.0 --port 7860
```

### 2. Configure Environment Variables
```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="<YOUR_HF_TOKEN>"
```

### 3. Run Inference
```bash
python inference.py
```

### Docker Build & Run
```bash
docker build -t llm-memory-optimizer .
docker run -p 7860:7860 llm-memory-optimizer
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /` | GET | Health check — returns status 200 |
| `POST /reset` | POST | Reset env for a task `{task_idx: 0}` |
| `POST /step` | POST | Execute action, get observation+reward |
| `GET /state` | GET | Get current state without stepping |
| `GET /tasks` | GET | List all available tasks |

---

## Inference Output Format

The inference script emits structured stdout logs per the OpenEnv spec:
```
[START] task=email_triage_easy env=llm_memory_optimizer model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=store_in_fast_memory reward=0.05 done=false error=null
[STEP] step=2 action=mark_email_important reward=0.30 done=false error=null
[STEP] step=3 action=submit_final_synthesis reward=1.00 done=true error=null
[END] success=true steps=3 score=1.00 rewards=0.05,0.30,1.00
```
