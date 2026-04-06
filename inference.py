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
"""

import os
import json
import requests
import time
from openai import OpenAI

# Hackathon mandatory env vars
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
BENCHMARK = "llm_memory_optimizer"
MAX_STEPS = 30

ENV_URL = os.getenv("ENV_URL", "http://127.0.0.1:7860")


def get_client():
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
2. If memory is dangerously full, offload_to_disk or semantic_compress immediately.
3. Check services_status — if services are crashed, investigate logs, fix_config, then restart_service.
4. For incident tasks, analyze logs systematically, identify root cause, then escalate with evidence.
5. When submitting, provide justification_ids pointing to valid memory blocks for full credit.
6. DO NOT restart services before applying a fix — it will crash again.
7. Watch cpu_cycles_left — you'll be terminated if you run out.

ONLY output raw JSON. No markdown, no backticks, no explanation."""


def reset_env(task_idx):
    response = requests.post(f"{ENV_URL}/reset", json={"task_idx": task_idx})
    response.raise_for_status()
    return response.json()


def step_env(action_dict):
    response = requests.post(f"{ENV_URL}/step", json=action_dict)
    response.raise_for_status()
    return response.json()


def run_task(client, task_idx, task_name):
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

            # Build observation prompt
            obs_str = json.dumps(obs, indent=2)
            messages.append({
                "role": "user",
                "content": f"Observation:\n{obs_str}\n\nRespond with your next action as JSON."
            })

            # LLM call
            try:
                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    temperature=0.0,
                )
                llm_response = completion.choices[0].message.content.strip()

                # Safely extract first valid JSON block
                start_idx = llm_response.find('{')
                end_idx = llm_response.rfind('}')
                
                if start_idx != -1 and end_idx != -1:
                    clean_json = llm_response[start_idx:end_idx+1]
                    action_dict = json.loads(clean_json)
                    # Validate required keys exist
                    if "action_type" not in action_dict:
                        raise ValueError("Parsed JSON missing 'action_type' key.")
                    if "action_args" not in action_dict:
                        action_dict["action_args"] = {}
                    last_error = None
                else:
                    raise ValueError("No JSON object detected in response.")
            except Exception as e:
                action_dict = {"action_type": "no_op", "action_args": {}}
                last_error = str(e)

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
                    obs = requests.get(f"{ENV_URL}/state").json()
                except Exception:
                    pass  # Keep previous obs as last resort

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

        # Calculate final score
        final_score = rewards_list[-1] if rewards_list else 0.0
        success = final_score >= 0.5

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
    client = get_client()

    task_names = [
        "email_triage_easy",
        "config_debugging_medium",
        "incident_response_hard",
    ]

    # Wait for environment server to start
    for i in range(15):
        try:
            resp = requests.get(f"{ENV_URL}/")
            if resp.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)

    total_scores = []
    for idx, name in enumerate(task_names):
        score = run_task(client, idx, name)
        total_scores.append(score)

    avg_score = sum(total_scores) / len(total_scores) if total_scores else 0.0
    print(f"\n--- FINAL AVERAGE SCORE: {avg_score:.2f} ---")
