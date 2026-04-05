import uuid
from typing import Dict, Any, Tuple
from models import Observation, Action, Reward
from tasks import Task, get_tasks

class MemoryEnvironment:
    def __init__(self):
        self.tasks = get_tasks()
        self.current_task_idx = 0
        self.current_task: Task = self.tasks[0]
        
        self.fast_memory: Dict[str, str] = {}
        self.disk_storage: Dict[str, str] = {}
        
        self.stream_index = 0
        self.cycles_elapsed = 0
        self.recent_disk_retrieval = None
        self.status_message = "System booted. Streaming initiated."
        self.is_done = False
        
    def reset(self, task_idx: int = None) -> Observation:
        if task_idx is not None and 0 <= task_idx < len(self.tasks):
            self.current_task_idx = task_idx
        else:
            self.current_task_idx = 0
            
        self.current_task = self.tasks[self.current_task_idx]
        self.fast_memory = {}
        self.disk_storage = {}
        self.stream_index = 0
        self.cycles_elapsed = 0
        self.recent_disk_retrieval = None
        self.status_message = f"Task '{self.current_task.name}' started."
        self.is_done = False
        
        return self._get_obs()

    def _get_tokens_used(self) -> int:
        return sum(len(v) for v in self.fast_memory.values())

    def _get_obs(self) -> Observation:
        input_stream = None
        if self.stream_index < len(self.current_task.inputs):
            input_stream = self.current_task.inputs[self.stream_index]
            
        return Observation(
            current_stream_chunk=input_stream,
            attention_tokens_used=self._get_tokens_used(),
            attention_capacity=self.current_task.attention_capacity,
            disk_storage_count=len(self.disk_storage),
            fast_memory_index=self.fast_memory.copy(),
            disk_index_preview={k: f"[{len(v)} chars]" for k, v in self.disk_storage.items()},
            recent_disk_retrieval=self.recent_disk_retrieval,
            task_goal=self.current_task.final_question,
            task_type=self.current_task.difficulty,
            cpu_cycles_left=self.current_task.max_cycles - self.cycles_elapsed,
            status_message=self.status_message
        )

    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Dict[str, Any]]:
        self.recent_disk_retrieval = None
        reward_value = 0.0
        reward_msg = ""
        done = False
        
        if self.is_done:
            return self._get_obs(), Reward(value=0.0, message="Episode already finished."), True, {}

        self.cycles_elapsed += 1
        if self.cycles_elapsed >= self.current_task.max_cycles:
            self.status_message = "CRIT: System timed out out of CPU cycles."
            done = True
            return self._get_obs(), Reward(value=0.0, message="Timeout."), done, {}

        atype = action.action_type
        args = action.action_args

        used_tokens = self._get_tokens_used()
        if used_tokens > self.current_task.attention_capacity:
            reward_value -= 0.2
            self.status_message = "FATAL: OOM Penalty. Fast memory overflowed. Must offload or compress immediately!"

        if atype == "store_in_fast_memory":
            content = args.get("content", "")
            if content:
                mem_id = str(uuid.uuid4())[:6]
                self.fast_memory[mem_id] = content
                self.status_message = f"Stored {mem_id} in fast memory."
                reward_value += 0.01 
            else:
                self.status_message = "Failed: Missing content."
                
        elif atype == "offload_to_disk":
            mem_ids = args.get("fast_memory_ids", [])
            moved = 0
            for m in mem_ids:
                if m in self.fast_memory:
                    self.disk_storage[m] = self.fast_memory.pop(m)
                    moved += 1
            if moved > 0:
                reward_value += 0.1 
                self.status_message = f"Offloaded {moved} items to disk."
            else:
                self.status_message = "Failed: Invalid fast_memory_ids."

        elif atype == "semantic_compress":
            mem_ids = args.get("fast_memory_ids", [])
            summary = args.get("summary", "")
            valid = [m for m in mem_ids if m in self.fast_memory]
            if len(valid) > 0 and summary:
                for m in valid:
                    del self.fast_memory[m]
                new_id = str(uuid.uuid4())[:6]
                self.fast_memory[new_id] = f"[COMPRESSED] {summary}"
                reward_value += 0.15 
                self.status_message = f"Compressed {len(valid)} items into {new_id}."
            else:
                self.status_message = "Failed: Invalid targets or missing summary."
                
        elif atype == "retrieve_from_disk":
            query = args.get("query", "").lower()
            limit = args.get("limit", 3)
            results = []
            for k, v in self.disk_storage.items():
                if query in v.lower():
                    results.append(f"{k}: {v}")
            if results:
                self.recent_disk_retrieval = "\\n".join(results[:limit])
                self.status_message = f"Disk retrieval: {len(results)} matches found."
            else:
                self.recent_disk_retrieval = "No matches."
                self.status_message = "Disk retrieval: 0 matches."
                reward_value -= 0.05 # Penalty for bad query
                
        elif atype == "submit_final_synthesis":
            answer = args.get("answer", "")
            j_ids = args.get("justification_ids", [])
            
            # verify justification exists in fast or disk
            valid_just = [jid for jid in j_ids if jid in self.fast_memory or jid in self.disk_storage]
            
            score = self.current_task.grade(answer, valid_just)
            if score == 1.0:
                reward_value = 1.0
                reward_msg = "Task Success! Answer verified and cleanly justified."
                self.status_message = "Synthesis Approved."
            elif score > 0:
                reward_value = score
                reward_msg = "Task Partial Success. Answer correct but missing valid justification in memory."
                self.status_message = "Synthesis Unjustified."
            else:
                reward_value = 0.0
                reward_msg = "Task Failed. Answer incorrect."
                self.status_message = "Synthesis Denied."
            done = True
            
        elif atype == "no_op":
            self.status_message = "Idle."
        else:
            self.status_message = f"Unknown sequence: {atype}"
            reward_value -= 0.1

        # Advance stream if not OOM
        if not done and atype != "submit_final_synthesis":
            if self._get_tokens_used() <= self.current_task.attention_capacity:
                if self.stream_index < len(self.current_task.inputs):
                    self.stream_index += 1
            else:
                self.status_message += " | STREAM HALTED DUE TO OOM."

        self.is_done = done
        if not reward_msg:
            reward_msg = self.status_message

        # Clamping
        reward_value = max(0.0, min(1.0, reward_value))

        return self._get_obs(), Reward(value=reward_value, message=reward_msg), done, {}
