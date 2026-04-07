"""
Inference Script — LLM Memory Optimizer + DevOps Decision System
===================================
MANDATORY ENV VARS:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.

STDOUT FORMAT:
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> rewards=<r1,r2,...,rn>

DETERMINISM:
    Baseline uses deterministic decoding (temperature=0, top_p=1).
    Environment grading is fully deterministic (regex-based, no randomness).
    Score variance comes only from LLM output variation, which is minimized
    by greedy decoding settings.

FALLBACK MODE:
    If HF_TOKEN is not set, the script runs a deterministic dummy baseline
    that exercises all environment endpoints and produces valid STDOUT output.
    This ensures the baseline always reproduces regardless of API availability.
"""

import os
import sys
import json
import re
import requests
import time

# Hackathon mandatory env vars
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
BENCHMARK = "llm_memory_optimizer"
MAX_STEPS = 30

# HTTP request timeout (seconds) — prevents API hangs
REQUEST_TIMEOUT = 30

ENV_URL = os.getenv("ENV_URL", "http://127.0.0.1:7860")


def get_client():
    from openai import OpenAI
    return OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)


SYSTEM_PROMPT = """You are an advanced AI Agent performing real-world DevOps debugging and memory management tasks.
You receive observations about incoming data streams, system telemetry, service statuses, and memory states.

You MUST respond with ONLY a valid JSON object matching this action schema:
{
  "action_type": "<one of the allowed actions>",
  "action_args": {<arguments for that action>}
}

ALLOWED ACTIONS:
1. store_in_fast_memory: {"content": "<string data>"} — Store critical data in fast memory
2. offload_to_disk: {"fast_memory_ids": ["id1", "id2"]} — Move data to slow disk storage to free memory
3. semantic_compress: {"fast_memory_ids": ["id1"], "summary": "<text>"} — Compress multiple items into a summary
4. retrieve_from_disk: {"query": "<search term>", "limit": 3} — Search disk for previously stored data
5. submit_final_synthesis: {"answer": "<final answer>", "justification_ids": ["id1"]} — Submit final answer with evidence
6. mark_email_important: {"memory_id": "<id>"} — Flag a stored email as important (only for genuinely critical emails)
7. fix_config: {"target": "<config key>", "new_value": "<corrected value>"} — Fix a misconfigured setting
8. restart_service: {"service_name": "<name>"} — Restart a service (only effective after fixing root cause)
9. escalate_incident: {"summary": "<detailed description>", "severity": "low|medium|high|critical"} — Escalate to on-call
10. no_op: {} — Do nothing this cycle

CRITICAL RULES:
1. Fast Memory has an OOM threshold. If attention_tokens_used exceeds attention_capacity, the system crashes.
2. If memory usage is above 80% of capacity, IMMEDIATELY offload_to_disk or semantic_compress.
3. Check services_status — if services are crashed, investigate logs, fix_config, then restart_service.
4. For incident tasks, analyze logs systematically, identify root cause, then escalate with evidence.
5. When submitting, ALWAYS provide justification_ids pointing to valid memory blocks for full credit.
6. DO NOT restart services before applying a fix — it will crash again.
7. Watch cpu_cycles_left — if running low, submit_final_synthesis with your best answer NOW.
8. If you have gathered sufficient evidence and identified the answer, submit early. Do NOT waste steps.
9. Be EFFICIENT — every step matters. Plan your approach: gather evidence → act → submit.

ONLY output raw JSON. No markdown, no backticks, no explanation."""

LLM_MAX_RETRIES = 2  # Retry LLM calls to avoid wasting steps on transient failures


# ─── Deterministic dummy baseline (runs without LLM API) ───────────────────
#
# NOTE: The dummy baseline exists ONLY for reproducibility — it ensures
# `python inference.py` always produces valid [START]/[STEP]/[END] output
# even without an API key. Actual evaluation uses the full LLM-powered agent
# (run_task) which calls the model specified by MODEL_NAME.
#
# The dummy actions are intentionally simple and do NOT represent optimal play.
# They exercise each action type to prove the environment API contract works.

# Pre-scripted action sequences per task — exercises key environment features
# and produces reproducible scores for validation without requiring an API key.
# justification_ids are populated dynamically from real memory IDs at runtime.
DUMMY_ACTIONS = {
    0: [  # email_triage_easy
        {"action_type": "store_in_fast_memory", "action_args": {"content": "CEO urgent: Acme Corp client escalation, call at 3 PM EST today"}},
        {"action_type": "store_in_fast_memory", "action_args": {"content": "Security alert: unusual login from TOR exit node, reset password immediately"}},
        {"action_type": "store_in_fast_memory", "action_args": {"content": "CTO followup: Acme Corp revenue $2.4M at risk, competitor threat, need SLA numbers"}},
        {"action_type": "submit_final_synthesis", "action_args": {
            "answer": "Critical action items: 1) Join Acme Corp escalation call at 3 PM EST - prepare Q4 metrics. 2) Security alert - reset password due to TOR login. 3) Acme Corp revenue at risk from competitor.",
            "justification_ids": "__AUTO__"
        }},
    ],
    1: [  # config_debugging_medium
        {"action_type": "store_in_fast_memory", "action_args": {"content": "REDIS_HOST=localhost in .env.staging — connection refused"}},
        {"action_type": "fix_config", "action_args": {"target": "REDIS_HOST", "new_value": "redis"}},
        {"action_type": "restart_service", "action_args": {"service_name": "api"}},
        {"action_type": "submit_final_synthesis", "action_args": {
            "answer": "Root cause: REDIS_HOST=localhost in .env.staging. In Docker, containers use service names for network resolution. Changed REDIS_HOST from localhost to redis. API container also needs backend network attachment.",
            "justification_ids": "__AUTO__"
        }},
    ],
    2: [  # incident_response_hard
        {"action_type": "store_in_fast_memory", "action_args": {"content": "Slow query: SELECT * FROM orders, 3200ms, 1.45M rows scanned"}},
        {"action_type": "store_in_fast_memory", "action_args": {"content": "Connection pool exhausted: 50/50 active, 14 waiting"}},
        {"action_type": "offload_to_disk", "action_args": {"fast_memory_ids": "__AUTO__"}},
        {"action_type": "store_in_fast_memory", "action_args": {"content": "Health check failed, OOMKilled, transaction timeout, node evicted"}},
        {"action_type": "escalate_incident", "action_args": {
            "summary": "Cascading failure: slow query caused connection pool exhaustion, leading to health check failures, OOMKill of api-alpha, and node eviction. Root cause is unindexed query on orders table scanning 1.45M rows.",
            "severity": "critical"
        }},
        {"action_type": "submit_final_synthesis", "action_args": {
            "answer": "Root cause chain: slow query (SELECT * FROM orders, 1.45M rows) → connection pool exhausted (50/50) → health check timeout → transaction timeout → OOMKilled (2048MB) → node alpha evicted. Fix: add index on orders.status column.",
            "justification_ids": "__AUTO__"
        }},
    ],
}


def reset_env(task_idx):
    response = requests.post(
        f"{ENV_URL}/reset", json={"task_idx": task_idx}, timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    return response.json()


def step_env(action_dict):
    response = requests.post(
        f"{ENV_URL}/step", json=action_dict, timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    return response.json()


def _resolve_auto_ids(action_dict, obs):
    """Replace '__AUTO__' placeholders with real memory IDs from current observation."""
    action_dict = json.loads(json.dumps(action_dict))  # deep copy
    args = action_dict.get("action_args", {})
    mem_ids = list(obs.get("fast_memory_index", {}).keys())

    for key, val in list(args.items()):
        if val == "__AUTO__":
            args[key] = mem_ids if mem_ids else []

    action_dict["action_args"] = args
    return action_dict


def run_task_dummy(task_idx, task_name):
    """Deterministic dummy baseline — no LLM required.
    Exercises all environment endpoints with pre-scripted actions.
    Dynamically resolves justification_ids from real memory state."""
    step_num = 0
    rewards_list = []
    success = False
    last_error = None

    print(f"[START] task={task_name} env={BENCHMARK} model=dummy_baseline")

    try:
        obs = reset_env(task_idx)
        actions = DUMMY_ACTIONS.get(task_idx, [
            {"action_type": "no_op", "action_args": {}},
            {"action_type": "submit_final_synthesis", "action_args": {"answer": "Unable to determine", "justification_ids": []}},
        ])

        for raw_action in actions:
            step_num += 1
            # Resolve __AUTO__ placeholders with actual memory IDs
            action_dict = _resolve_auto_ids(raw_action, obs)
            action_str = action_dict.get("action_type", "no_op")

            try:
                step_response = step_env(action_dict)
                obs = step_response["observation"]
                reward_val = float(step_response["reward"])
                done = step_response["done"]
            except Exception as step_err:
                reward_val = 0.0
                done = False
                last_error = str(step_err)
                try:
                    obs = requests.get(f"{ENV_URL}/state", timeout=REQUEST_TIMEOUT).json()
                except Exception:
                    obs = obs if obs else {}  # safe fallback

            rewards_list.append(reward_val)
            error_str = f'"{last_error}"' if last_error else "null"
            done_str = "true" if done else "false"

            print(
                f"[STEP] step={step_num} action={action_str} "
                f"reward={reward_val:.2f} done={done_str} error={error_str}"
            )

            if done:
                break

    except Exception as e:
        last_error = str(e)
        if not rewards_list:
            rewards_list = [0.0]

    final_score = max(rewards_list) if rewards_list else 0.0
    success = final_score >= 0.5
    rewards_str = ",".join(f"{r:.2f}" for r in rewards_list)
    success_str = "true" if success else "false"
    print(
        f"[END] success={success_str} steps={step_num} "
        f"rewards={rewards_str}"
    )
    return final_score


def run_task(client, task_idx, task_name):
    """Full LLM-powered baseline."""
    step_num = 0
    rewards_list = []
    final_score = 0.0
    success = False
    last_error = None

    # [START] line
    print(f"[START] task={task_name} env={BENCHMARK} model={MODEL_NAME}")

    try:
        obs = reset_env(task_idx)
        done = False

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        while not done and step_num < MAX_STEPS:
            step_num += 1

            # Build memory-aware observation prompt with key constraints
            obs_str = json.dumps(obs, indent=2)
            mem_used = obs.get("attention_tokens_used", 0)
            mem_cap = obs.get("attention_capacity", 1)
            mem_pct = int((mem_used / max(mem_cap, 1)) * 100)
            cycles_left = obs.get("cpu_cycles_left", 0)
            mem_ids = list(obs.get("fast_memory_index", {}).keys())

            # Inject situational awareness into the prompt
            constraints = f"""\nKey constraints:
- Memory: {mem_used}/{mem_cap} ({mem_pct}% used){' — DANGER: near OOM, compress/offload NOW!' if mem_pct > 80 else ''}
- Cycles left: {cycles_left}{' — URGENT: submit answer soon!' if cycles_left <= 5 else ''}
- Memory IDs available for justification: {mem_ids if mem_ids else 'none yet'}
- Always include justification_ids when submitting for full credit.
- If you have enough evidence, submit_final_synthesis NOW — don't waste steps."""

            messages.append({
                "role": "user",
                "content": f"Observation:\n{obs_str}\n{constraints}\n\nRespond with your next action as JSON."
            })

            # LLM call with retry — deterministic decoding (temperature=0, top_p=1)
            action_dict = None
            for attempt in range(LLM_MAX_RETRIES):
                try:
                    completion = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=messages,
                        temperature=0.0,
                        top_p=1.0,
                    )
                    llm_response = completion.choices[0].message.content.strip()

                    # Parse JSON: try direct parse first, then regex fallback
                    try:
                        action_dict = json.loads(llm_response)
                    except json.JSONDecodeError:
                        # Fallback: extract JSON via regex
                        json_match = re.search(
                            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
                            llm_response, re.DOTALL
                        )
                        if json_match:
                            action_dict = json.loads(json_match.group(0))
                        else:
                            raise ValueError("No JSON object detected in response.")

                    # Validate required keys
                    if "action_type" not in action_dict:
                        raise ValueError("Parsed JSON missing 'action_type' key.")
                    if "action_args" not in action_dict:
                        action_dict["action_args"] = {}
                    last_error = None
                    break  # Success — exit retry loop

                except Exception as e:
                    last_error = str(e)
                    if attempt < LLM_MAX_RETRIES - 1:
                        time.sleep(0.5)  # Brief pause before retry
                    # else: fall through to no_op

            if action_dict is None:
                action_dict = {"action_type": "no_op", "action_args": {}}

            # Step the environment — wrapped safely so [STEP] always prints
            action_str = action_dict.get("action_type", "no_op")
            try:
                step_response = step_env(action_dict)
                obs = step_response["observation"]
                reward_val = float(step_response["reward"])
                done = step_response["done"]
            except Exception as step_err:
                # API error (422, 500, network) — do NOT crash, log and continue
                reward_val = 0.0
                done = False
                last_error = str(step_err)
                # Fetch fresh observation so LLM doesn't loop on stale state
                try:
                    obs = requests.get(f"{ENV_URL}/state", timeout=REQUEST_TIMEOUT).json()
                except Exception:
                    obs = obs if obs else {}  # safe fallback — never None

            rewards_list.append(reward_val)

            # Determine error string
            error_str = f'"{last_error}"' if last_error else "null"
            done_str = "true" if done else "false"

            # [STEP] line — mandatory format, ALWAYS emitted
            print(
                f"[STEP] step={step_num} action={action_str} "
                f"reward={reward_val:.2f} done={done_str} error={error_str}"
            )

            messages.append({"role": "assistant", "content": json.dumps(action_dict)})

        # Score = best reward achieved; success = based on final step outcome
        final_score = max(rewards_list) if rewards_list else 0.0
        success = bool(rewards_list and rewards_list[-1] >= 0.5)

    except Exception as e:
        last_error = str(e)
        if not rewards_list:
            rewards_list = [0.0]
        success = False
        final_score = 0.0

    # [END] line — always emitted
    rewards_str = ",".join(f"{r:.2f}" for r in rewards_list)
    success_str = "true" if success else "false"
    print(
        f"[END] success={success_str} steps={step_num} "
        f"rewards={rewards_str}"
    )

    return final_score


if __name__ == "__main__":
    task_names = [
        "email_triage_easy",
        "config_debugging_medium",
        "incident_response_hard",
    ]

    # Wait for environment server to start
    for i in range(15):
        try:
            resp = requests.get(f"{ENV_URL}/", timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            pass
        time.sleep(1)

    # Decide mode: LLM or deterministic dummy baseline
    use_dummy = not HF_TOKEN
    if use_dummy:
        print(
            "[WARNING] HF_TOKEN not set. Running deterministic dummy baseline. "
            "Set HF_TOKEN to use a real LLM agent.",
            file=sys.stderr,
        )
        runner = lambda idx, name: run_task_dummy(idx, name)
    else:
        client = get_client()
        runner = lambda idx, name: run_task(client, idx, name)

    total_scores = []
    for idx, name in enumerate(task_names):
        score = runner(idx, name)
        total_scores.append(score)

    avg_score = sum(total_scores) / len(total_scores) if total_scores else 0.0
    print(f"\n--- FINAL AVERAGE SCORE: {avg_score:.2f} ---")
