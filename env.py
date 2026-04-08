import uuid
import json
from typing import Dict, Any, Tuple, List
from models import Observation, Action
from tasks import Task, get_tasks

VALID_ACTIONS = {
    "store_in_fast_memory", "offload_to_disk", "semantic_compress",
    "retrieve_from_disk", "submit_final_synthesis",
    "mark_email_important", "fix_config", "restart_service",
    "escalate_incident", "no_op",
}

# Absolute hard ceiling — prevents infinite loops regardless of task config
HARD_MAX_STEPS = 100

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

        # Partial progress tracking (Step 4)
        self.partial_progress: Dict[str, bool] = {}

        # Decision log for explainability (Step 9)
        self.decision_log: List[str] = []

        # Service states for real actions (Step 1)
        self.services_status: Dict[str, str] = {}

        # Config state for fix_config action
        self.config_state: Dict[str, str] = {}

        # Track marked important items
        self.marked_important: List[str] = []

        # Track if fix was applied (for restart_service logic)
        self.fix_applied = False

        # Action history for anti-loop detection
        self.action_history: List[str] = []

        # Full action+args history for anti-exploit detection
        self.action_args_history: List[str] = []

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

        # Reset new state
        self.partial_progress = {}
        self.decision_log = []
        self.services_status = dict(self.current_task.services) if self.current_task.services else {}
        self.config_state = dict(self.current_task.config_bugs) if self.current_task.config_bugs else {}
        self.marked_important = []
        self.fix_applied = False
        self.action_history = []
        self.action_args_history = []

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
            status_message=self.status_message,
            partial_progress=self.partial_progress.copy(),
            decision_log=list(self.decision_log[-10:]),  # Last 10 entries
            services_status=self.services_status.copy(),
        )

    def _check_partial_milestones(self) -> float:
        """Check if any partial milestones are newly achieved. Returns bonus reward."""
        bonus = 0.0
        milestones = self.current_task.partial_milestones
        if not milestones:
            return bonus

        # Check all content in fast_memory and disk_storage
        all_content = " ".join(self.fast_memory.values()).lower()
        all_content += " " + " ".join(self.disk_storage.values()).lower()

        for milestone_key, keywords in milestones.items():
            if milestone_key not in self.partial_progress:
                if any(kw.lower() in all_content for kw in keywords):
                    self.partial_progress[milestone_key] = True
                    bonus += 0.15
                    self.decision_log.append(
                        f"MILESTONE: '{milestone_key}' achieved (+0.15 reward)"
                    )

        return bonus

    def _efficiency_bonus(self) -> float:
        """Reward efficiency — fewer steps used relative to max."""
        ratio = self.cycles_elapsed / self.current_task.max_cycles
        if ratio < 0.4:
            return 0.1
        elif ratio < 0.6:
            return 0.05
        return 0.0

    def _memory_optimization_bonus(self) -> float:
        """Reward staying well within memory capacity."""
        used = self._get_tokens_used()
        cap = self.current_task.attention_capacity
        if cap == 0:
            return 0.0
        ratio = used / cap
        if ratio < 0.5:
            return 0.1
        elif ratio < 0.8:
            return 0.05
        return 0.0

    def step(self, action: Action) -> Tuple[Observation, float, bool, Dict[str, Any]]:
        self.recent_disk_retrieval = None
        reward_value = 0.0
        reward_msg = ""
        done = False

        if self.is_done:
            return (
                self._get_obs(),
                0.0,
                True,
                {"error": "Episode already finished."},
            )

        self.cycles_elapsed += 1
        effective_max = min(self.current_task.max_cycles, HARD_MAX_STEPS)
        if self.cycles_elapsed >= effective_max:
            self.status_message = "CRIT: System timed out — out of CPU cycles."
            self.decision_log.append("TIMEOUT: No more CPU cycles.")
            done = True
            self.is_done = done
            return (
                self._get_obs(),
                0.0,
                done,
                {"error": "Timeout."},
            )

        atype = action.action_type
        args = action.action_args

        # Track action history
        self.action_history.append(atype)

        # Track full action signature for exploit detection
        action_signature = json.dumps({"t": atype, "a": args}, sort_keys=True)
        self.action_args_history.append(action_signature)

        # Anti-exploit: penalize repeated identical actions (same type + same args)
        # This catches keyword-spamming, repeated fix_config with same values, etc.
        if len(self.action_args_history) >= 3:
            last_3 = self.action_args_history[-3:]
            if last_3[0] == last_3[1] == last_3[2] and atype != "no_op":
                # Count consecutive identical
                consecutive = 0
                for sig in reversed(self.action_args_history):
                    if sig == action_signature:
                        consecutive += 1
                    else:
                        break
                repeat_penalty = min(0.1, 0.02 * (consecutive - 2))
                reward_value -= repeat_penalty
                self.decision_log.append(
                    f"ANTI_EXPLOIT: Identical action repeated {consecutive}x, "
                    f"penalty={repeat_penalty:.2f}"
                )

        # Validate action type
        if atype not in VALID_ACTIONS:
            self.status_message = f"Unknown action: {atype}. Valid actions: {', '.join(sorted(VALID_ACTIONS))}"
            reward_value -= 0.05
            self.decision_log.append(f"INVALID_ACTION: {atype} not recognized.")
            self.is_done = False
            return (
                self._get_obs(),
                0.0,  # Clamped: penalty signal is zero reward (not negative)
                False,
                {"error": f"Invalid action_type: {atype}"},
            )

        # OOM penalty — episode does NOT end, agent can still offload/compress
        used_tokens = self._get_tokens_used()
        if used_tokens > self.current_task.attention_capacity:
            reward_value -= 0.2
            self.status_message = (
                "WARNING: OOM — memory overflowed! "
                "Use 'offload_to_disk' or 'semantic_compress' to free space. "
                "Episode continues."
            )

        # ----- MEMORY MANAGEMENT ACTIONS -----

        if atype == "store_in_fast_memory":
            content = args.get("content", "") if args else ""
            if content:
                mem_id = str(uuid.uuid4())[:6]
                self.fast_memory[mem_id] = content
                self.status_message = f"Stored {mem_id} in fast memory."
                # Correctness reward: storing relevant content
                if any(
                    kw.lower() in content.lower()
                    for kws in self.current_task.partial_milestones.values()
                    for kw in kws
                ):
                    reward_value += 0.05  # Bonus for storing relevant data
                else:
                    reward_value += 0.01
                self.decision_log.append(
                    f"STORE: Added {mem_id} ({len(content)} chars) to fast memory."
                )
            else:
                self.status_message = "Failed: Missing content."
                self.decision_log.append("STORE_FAIL: No content provided.")

        elif atype == "offload_to_disk":
            mem_ids = args.get("fast_memory_ids", []) if args else []
            if not isinstance(mem_ids, list):
                mem_ids = []
            moved = 0
            for m in mem_ids:
                if m in self.fast_memory:
                    self.disk_storage[m] = self.fast_memory.pop(m)
                    moved += 1
            if moved > 0:
                reward_value += 0.1
                self.status_message = f"Offloaded {moved} items to disk."
                self.decision_log.append(f"OFFLOAD: Moved {moved} items to disk.")
            else:
                self.status_message = "Failed: Invalid fast_memory_ids."
                self.decision_log.append("OFFLOAD_FAIL: No valid IDs.")

        elif atype == "semantic_compress":
            mem_ids = args.get("fast_memory_ids", []) if args else []
            summary = args.get("summary", "") if args else ""
            if not isinstance(mem_ids, list):
                mem_ids = []
            valid = [m for m in mem_ids if m in self.fast_memory]
            if len(valid) > 0 and summary:
                original_size = sum(len(self.fast_memory[m]) for m in valid)
                for m in valid:
                    del self.fast_memory[m]
                new_id = str(uuid.uuid4())[:6]
                self.fast_memory[new_id] = f"[COMPRESSED] {summary}"
                compressed_size = len(self.fast_memory[new_id])
                compression_ratio = 1 - (compressed_size / max(original_size, 1))
                reward_value += 0.1 + (0.1 * max(0, compression_ratio))
                self.status_message = (
                    f"Compressed {len(valid)} items into {new_id} "
                    f"(ratio: {compression_ratio:.0%})."
                )
                self.decision_log.append(
                    f"COMPRESS: {len(valid)} items → {new_id} "
                    f"({original_size} → {compressed_size} chars)."
                )
            else:
                self.status_message = "Failed: Invalid targets or missing summary."
                self.decision_log.append("COMPRESS_FAIL: Invalid input.")

        elif atype == "retrieve_from_disk":
            query = (args.get("query", "") if args else "").lower()
            limit = args.get("limit", 3) if args else 3
            results = []
            for k, v in self.disk_storage.items():
                if query in v.lower():
                    results.append(f"{k}: {v}")
            if results:
                self.recent_disk_retrieval = "\n".join(results[:limit])
                self.status_message = f"Disk retrieval: {len(results)} matches found."
                reward_value += 0.02
                self.decision_log.append(
                    f"RETRIEVE: Query '{query}' → {len(results)} matches."
                )
            else:
                self.recent_disk_retrieval = "No matches."
                self.status_message = "Disk retrieval: 0 matches."
                reward_value -= 0.05
                self.decision_log.append(
                    f"RETRIEVE_FAIL: Query '{query}' → 0 matches."
                )

        # ----- REAL-WORLD ACTIONS (Step 1) -----

        elif atype == "mark_email_important":
            mem_id = (args.get("memory_id", "") if args else "")
            if mem_id in self.fast_memory or mem_id in self.disk_storage:
                content = self.fast_memory.get(mem_id, self.disk_storage.get(mem_id, ""))
                # Check if this is actually an important email
                is_important = any(
                    kw in content.lower()
                    for kw in ["urgent", "critical", "security", "alert", "ceo", "cto", "escalation"]
                )
                if is_important and mem_id not in self.marked_important:
                    self.marked_important.append(mem_id)
                    reward_value += 0.3  # Correctness: marked genuinely important
                    self.status_message = f"Email {mem_id} marked as IMPORTANT. Correct!"
                    self.decision_log.append(
                        f"MARK_IMPORTANT: {mem_id} — correctly identified critical email."
                    )
                elif mem_id in self.marked_important:
                    self.status_message = f"Email {mem_id} already marked."
                    self.decision_log.append(f"MARK_IMPORTANT: {mem_id} — duplicate action.")
                else:
                    reward_value -= 0.1  # Penalty for marking non-important
                    self.status_message = f"Email {mem_id} marked, but it's not important."
                    self.decision_log.append(
                        f"MARK_IMPORTANT_WRONG: {mem_id} — not a critical email."
                    )
            else:
                self.status_message = f"Failed: Memory ID {mem_id} not found."
                self.decision_log.append(f"MARK_IMPORTANT_FAIL: {mem_id} not found.")

        elif atype == "fix_config":
            target = (args.get("target", "") if args else "").upper()
            new_value = (args.get("new_value", "") if args else "")
            if self.config_state:
                # Check if fixing the right config key
                bug_key = list(self.config_state.keys())[0] if self.config_state else ""
                correct_val = self.config_state.get("correct_value", "")
                if target and (
                    target.lower() == bug_key.lower()
                    or bug_key.lower() in target.lower()
                ):
                    if correct_val and correct_val.lower() in new_value.lower():
                        reward_value += 0.5  # Big reward for correct fix
                        self.config_state["fixed"] = "true"
                        self.fix_applied = True
                        # Update service status
                        for svc, status in self.services_status.items():
                            if status == "crashed":
                                self.services_status[svc] = "fix_pending_restart"
                        self.status_message = (
                            f"Config '{target}' fixed to '{new_value}'. "
                            "Services need restart to apply."
                        )
                        self.decision_log.append(
                            f"FIX_CONFIG: {target} → '{new_value}' — CORRECT FIX."
                        )
                    else:
                        reward_value += 0.1  # Partial: right key, wrong value
                        self.status_message = (
                            f"Config '{target}' updated but value may be incorrect."
                        )
                        self.decision_log.append(
                            f"FIX_CONFIG_PARTIAL: {target} → '{new_value}' — wrong value."
                        )
                else:
                    self.status_message = f"Config key '{target}' is not the root cause."
                    reward_value -= 0.05
                    self.decision_log.append(
                        f"FIX_CONFIG_WRONG: {target} — not relevant."
                    )
            else:
                self.status_message = "No config bugs exist for this task."
                self.decision_log.append("FIX_CONFIG: No config bugs in task.")

        elif atype == "restart_service":
            svc = (args.get("service_name", "") if args else "")
            if svc in self.services_status:
                current_status = self.services_status[svc]
                if current_status == "fix_pending_restart":
                    self.services_status[svc] = "running"
                    reward_value += 0.3  # Correct: restart after fix
                    self.status_message = f"Service '{svc}' restarted successfully."
                    self.decision_log.append(
                        f"RESTART: '{svc}' → running. Fix applied successfully."
                    )
                elif current_status == "crashed" and not self.fix_applied:
                    self.services_status[svc] = "crashed"  # Stays crashed without fix
                    reward_value -= 0.1  # Penalty: restarting without fixing
                    self.status_message = (
                        f"Service '{svc}' restarted but crashed again — "
                        "root cause not fixed."
                    )
                    self.decision_log.append(
                        f"RESTART_FAIL: '{svc}' crashed again. Fix not applied."
                    )
                elif current_status == "running":
                    self.status_message = f"Service '{svc}' is already running."
                    self.decision_log.append(f"RESTART_NOOP: '{svc}' already running.")
                else:
                    self.services_status[svc] = "running"
                    reward_value += 0.1
                    self.status_message = f"Service '{svc}' restarted."
                    self.decision_log.append(f"RESTART: '{svc}' restarted.")
            else:
                self.status_message = f"Unknown service: '{svc}'."
                self.decision_log.append(f"RESTART_FAIL: Unknown service '{svc}'.")

        elif atype == "escalate_incident":
            summary = (args.get("summary", "") if args else "")
            severity = (args.get("severity", "medium") if args else "medium")
            if summary:
                # Escalation is appropriate for hard tasks or when critical issues found
                is_appropriate = (
                    self.current_task.difficulty == "hard"
                    or severity in ["high", "critical"]
                    or any(
                        self.services_status.get(s) in ["crashed", "overloaded"]
                        for s in self.services_status
                    )
                )
                if is_appropriate and len(summary) > 20:
                    reward_value += 0.2
                    self.status_message = (
                        f"Incident escalated (severity: {severity}). "
                        "On-call team notified."
                    )
                    self.decision_log.append(
                        f"ESCALATE: Severity={severity}. Summary: {summary[:80]}..."
                    )
                elif is_appropriate:
                    reward_value += 0.05  # Partial: good idea but weak summary
                    self.status_message = "Escalated but summary too brief."
                    self.decision_log.append(
                        f"ESCALATE_WEAK: Severity={severity}. Summary too short."
                    )
                else:
                    reward_value -= 0.05  # Unnecessary escalation
                    self.status_message = "Escalation not warranted for this situation."
                    self.decision_log.append(
                        f"ESCALATE_UNNECESSARY: No critical issues found."
                    )
            else:
                self.status_message = "Failed: Escalation requires a summary."
                self.decision_log.append("ESCALATE_FAIL: No summary provided.")

        # ----- FINAL SUBMISSION -----

        elif atype == "submit_final_synthesis":
            answer = (args.get("answer", "") if args else "")
            j_ids = (args.get("justification_ids", []) if args else [])
            if not isinstance(j_ids, list):
                j_ids = []

            # Verify justification exists in fast or disk
            valid_just = [
                jid for jid in j_ids
                if jid in self.fast_memory or jid in self.disk_storage
            ]

            score = self.current_task.grade(answer, valid_just)

            # Anti-exploit: no valid justification IDs → cap score
            if not valid_just and score > 0:
                score = min(score, 0.3)  # Can't get >0.3 without evidence
                self.decision_log.append(
                    "SUBMIT_WARNING: No valid justification IDs — score capped at 0.3"
                )

            # Add efficiency and memory bonuses (only if justified)
            eff_bonus = self._efficiency_bonus() if valid_just else 0.0
            mem_bonus = self._memory_optimization_bonus() if valid_just else 0.0

            if score == 1.0:
                reward_value = min(1.0, 1.0 + eff_bonus + mem_bonus)
                reward_msg = (
                    f"Task Success! Answer verified and justified. "
                    f"Efficiency bonus: {eff_bonus:.2f}, Memory bonus: {mem_bonus:.2f}"
                )
                self.status_message = "Synthesis Approved."
            elif score > 0:
                reward_value = min(1.0, score + eff_bonus + mem_bonus)
                reward_msg = (
                    f"Task Partial Success (score={score:.2f}). "
                    f"Efficiency: {eff_bonus:.2f}, Memory: {mem_bonus:.2f}"
                )
                self.status_message = "Synthesis Partially Accepted."
            else:
                reward_value = 0.0
                reward_msg = "Task Failed. Answer incorrect."
                self.status_message = "Synthesis Denied."

            self.decision_log.append(
                f"SUBMIT: score={score:.2f}, eff={eff_bonus:.2f}, "
                f"mem={mem_bonus:.2f}, final={reward_value:.2f}"
            )
            done = True

        elif atype == "no_op":
            self.status_message = "Idle."
            self.decision_log.append("NO_OP: Agent idled.")
            # Anti-loop: graduated penalty for repeated no_ops
            recent = self.action_history[-3:]
            if len(recent) == 3 and all(a == "no_op" for a in recent):
                consecutive_noop = 0
                for a in reversed(self.action_history):
                    if a == "no_op":
                        consecutive_noop += 1
                    else:
                        break
                # Scale: -0.01, -0.03, -0.05, capped at -0.05
                penalty = min(0.05, 0.01 * (consecutive_noop - 2))
                reward_value -= penalty
                self.decision_log.append(
                    f"ANTI_LOOP: {consecutive_noop} consecutive no_ops, penalty={penalty:.2f}"
                )

        else:
            self.status_message = f"Unknown action: {atype}"
            reward_value -= 0.1
            self.decision_log.append(f"UNKNOWN_ACTION: {atype}")

        # Check partial milestones after every action
        milestone_bonus = self._check_partial_milestones()
        reward_value += milestone_bonus

        # Advance stream if not OOM and not done
        if not done and atype != "submit_final_synthesis":
            if self._get_tokens_used() <= self.current_task.attention_capacity:
                if self.stream_index < len(self.current_task.inputs):
                    self.stream_index += 1
            else:
                self.status_message += " | STREAM HALTED DUE TO OOM."

        self.is_done = done
        if not reward_msg:
            reward_msg = self.status_message

        # Clamping to [0.0001, 0.9999]
        reward_value = max(0.0001, min(0.9999, reward_value))

        info_dict = {"partial_progress": self.partial_progress.copy()}
        if reward_msg:
            info_dict["reward_message"] = reward_msg

        return (
            self._get_obs(),
            reward_value,
            done,
            info_dict,
        )
