# Advanced AI Memory Management System (LLM Brain Optimizer)

## Description
A sophisticated OpenEnv simulation of a real-world multi-tiered Memory Controller subsystem (similar to MemGPT or OS paging architectures). With context windows acting as a strict bounding bottleneck, the agent must efficiently map the flow of incoming real-time chunks between its "Fast Memory" and "Slow Disk," while aggressively computing semantic compressions to avoid an Out-of-Memory (OOM) terminal crash.

## Motivation
Optimizing multi-tiered LLM memory management is highly requested in modern AI systems research. Agents often face infinite-horizon tasks (like incident response, code linting, or long-term companion models) where the context window *will* eventually run out. This environment trains an agent to actively juggle semantic boundaries without losing reasoning fidelity, explicitly penalizing hallucinations or "lost in the middle" side constraints.

## Advanced Observation Space (Tiered Paging)
Instead of generic properties, the agent watches system limits:
- `attention_tokens_used`: The weight of the active context window. Overloading this crashes the container!
- `disk_storage_count`: Items safely committed to cheap, slow, long-term storage.
- `cpu_cycles_left`: Turn counter before strict stream termination.

## Action Space (Memory Commands)
1. `store_in_fast_memory`: Immediately retain information to the active buffer.
2. `offload_to_disk`: Evict raw inputs to cheap long-term storage to prevent OOM.
3. `semantic_compress`: Burn cycles to summarize data in fast memory, freeing tokens while retaining facts.
4. `retrieve_from_disk`: Search long-term storage for previously offloaded facts.
5. `submit_final_synthesis`: Answer the overarching goal and *explicitly cite justification ids* mapped in memory.

## Expected Task Difficulty & Baseline Scores
- **Easy (Email Triage)**: Simple stream, large context bounds. The agent simply drops spam and retains explicit action items. (*Baseline Score: ~1.0*)
- **Medium (Code Review)**: Multi-file code trace. Extremely tight fast memory constraint. The agent must constantly jump back and forth reading chunks, offloading clean configs, and keeping only buggy API endpoints in fast memory. (*Baseline Score: ~0.8*)
- **Hard (Infinite Context)**: Continuous anomaly metric stream. Requires continuous, aggressive semantic compression of routine logs over time to synthesize a proper timeline for root-cause synthesis before cpu cycles run out. (*Baseline Score: ~0.5*)

## Usage
Start the background simulation server:
```powershell
python -m uvicorn main:app --host 0.0.0.0 --port 7860
```

Export your local keys or target configurations, then run the evaluation LLM loop:
```powershell
export API_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
export MODEL_NAME="gemini-1.5-flash"
export HF_TOKEN="<YOUR_KEY>"

python inference.py
```
