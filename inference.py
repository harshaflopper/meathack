import os
import json
import requests
import time
from openai import OpenAI

# Hackathon standard ENVs
# Note: To use Gemini for free, set these locally before running:
# export API_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
# export MODEL_NAME="gemini-1.5-flash"
# export HF_TOKEN="<YOUR_GEMINI_API_KEY>"

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4-turbo")
HF_TOKEN = os.getenv("HF_TOKEN", os.getenv("OPENAI_API_KEY", ""))

ENV_URL = "http://127.0.0.1:7860"

def get_client():
    return OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

system_prompt = """You are an advanced AI Memory Manager Agent. Your goal is to maximize reward under strict compute and memory constraints.
You receive observations about the current data stream, system telemetry (like cpu_cycles_left and attention_tokens_used), and memory states.

You MUST output a valid JSON answering to this exact action schema:
{
  "action_type": "store_in_fast_memory | offload_to_disk | semantic_compress | retrieve_from_disk | submit_final_synthesis | no_op",
  "action_args": {}
}

Arguments for the actions:
- store_in_fast_memory: {"content": "<string data>"}
- offload_to_disk: {"fast_memory_ids": ["<id1>", "<id2>"]} 
- semantic_compress: {"fast_memory_ids": ["<id1>", "<id2>"], "summary": "<abstracted text>"}
- retrieve_from_disk: {"query": "<semantic search string>", "limit": 3}
- submit_final_synthesis: {"answer": "<final answer to task_goal>", "justification_ids": ["<id1>"]}

CRITICAL RULES:
1. Fast Memory has an OOM threshold ('attention_capacity'). If 'attention_tokens_used' exceeds it, the system crashes and halts the data stream.
2. If fast memory is dangerously full, you MUST offload_to_disk or semantic_compress immediately!
3. Disk storage is unlimited but requires you to explicitly query it later via retrieve_from_disk.
4. When you submit_final_synthesis, you MUST provide justification_ids that point to valid memory blocks in fast memory or disk to earn the full 1.0 reward.
5. Watch the stream. Once cpu_cycles_left runs out, the run is forcibly terminated.
ONLY output raw JSON. No markdown brackets.
"""

def reset(task_idx):
    response = requests.post(f"{ENV_URL}/reset", json={"task_idx": task_idx})
    return response.json()

def step(action_dict):
    response = requests.post(f"{ENV_URL}/step", json=action_dict)
    return response.json()

def run_task(client, task_idx, task_name):
    print(f"[START] task={task_name}")
    obs = reset(task_idx)
    done = False
    
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    total_reward = 0.0
    
    while not done:
        obs_str = json.dumps(obs, indent=2)
        messages.append({"role": "user", "content": f"Observation:\n{obs_str}\n\nWhat is your next action in JSON format?"})
        
        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.0
            )
            llm_response = completion.choices[0].message.content.strip()
            
            if llm_response.startswith("```json"):
                llm_response = llm_response.replace("```json", "").replace("```", "").strip()
            elif llm_response.startswith("```"):
                llm_response = llm_response.replace("```", "").strip()
                
            action_dict = json.loads(llm_response)
        except Exception as e:
            action_dict = {"action_type": "no_op", "action_args": {}}
            
        print(f"[STEP] Action: {json.dumps(action_dict)}")
        
        step_response = step(action_dict)
        obs = step_response["observation"]
        reward_info = step_response["reward"]
        done = step_response["done"]
        
        reward_val = getattr(reward_info, "value", reward_info.get("value", 0.0) if isinstance(reward_info, dict) else 0.0)
        total_reward += reward_val
        
        print(f"[STEP] Observation: {json.dumps(obs)}")
        print(f"[STEP] Reward: {reward_val}")
        
        messages.append({"role": "assistant", "content": json.dumps(action_dict)})
        
    print(f"[END] total_reward={total_reward:.2f}")
    return total_reward

if __name__ == "__main__":
    client = get_client()
    task_names = ["email_triage_easy", "codebase_debugging_medium", "infinite_incident_response_hard"]
    
    for i in range(10):
        try:
            requests.get(f"{ENV_URL}/")
            break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
            
    for idx, name in enumerate(task_names):
        run_task(client, idx, name)
