import random
from typing import Dict, Any, List

class Task:
    def __init__(self, name: str, difficulty: str, attention_capacity: int, max_cycles: int, inputs: List[str], final_question: str, expected_answers: List[str]):
        self.name = name
        self.difficulty = difficulty
        self.attention_capacity = attention_capacity
        self.max_cycles = max_cycles
        self.inputs = inputs
        self.final_question = final_question
        self.expected_answers = expected_answers
    
    def grade(self, answer: str, justifications: List[str]) -> float:
        ans_lower = answer.lower()
        correct_ans = any(exp.lower() in ans_lower for exp in self.expected_answers)
        has_justification = len(justifications) > 0

        # Reward shaping for accurate answers
        if correct_ans and has_justification:
            return 1.0
        elif correct_ans and not has_justification:
            return 0.5  # Heavy penalty for hallucinating an answer without stored justification
        return 0.0

def get_tasks() -> List[Task]:
    # Easy Task: Email Triage
    # Large context window. Agent just needs to find the key email amidst spam.
    easy = Task(
        name="email_triage_easy",
        difficulty="easy",
        attention_capacity=1000, 
        max_cycles=10,
        inputs=[
            "Email 1 [Spam]: Buy cheap meds now!",
            "Email 2 [HR]: Office closed on Friday.",
            "Email 3 [Spam]: You won a lottery!",
            "Email 4 [Boss]: Urgent - the client meeting is rescheduled to 3 PM Tuesday.",
            "Email 5 [Marketing]: Weekly newsletter.",
        ],
        final_question="When is the urgent client meeting?",
        expected_answers=["3 PM Tuesday", "Tuesday at 3", "3:00 PM Tuesday"]
    )

    # Medium Task: Codebase Debugging
    # Very tight attention limit. Agent must systematically read, offload irrelevant files to disk, and keep the conflicting configs in fast memory.
    medium = Task(
        name="codebase_debugging_medium",
        difficulty="medium",
        attention_capacity=200, 
        max_cycles=15,
        inputs=[
            "[File: utils.py] def setup(): return True",
            "[File: db.py] cache = Redis(host='localhost', port=6379)",
            "[Log: Warning] Deprecation warning in auth.py on line 42",
            "[File: api.py] @app.get('/data') def get_data(): return fetch()",
            "[Log: Error] Connection refused on redis_host='10.0.2.14'",
            "[Notice] The staging environment database IP is indeed 10.0.2.14. Localhost fallback removed."
        ],
        final_question="Why is the /data endpoint throwing connection refused on staging?",
        expected_answers=["db.py is hardcoded to localhost", "redis host is localhost", "localhost fallback missing"]
    )

    # Hard Task: Infinite Horizon Incident Response
    # Stream is too long for memory. Agent must compress log blocks into metadata and only retain anomalies.
    hard_inputs = []
    for i in range(25):
        hard_inputs.append(f"[Log T+{i}] Routine CPU metrics normal: {random.randint(40,60)}%")
    hard_inputs[4] = "[Log T+4] Warning: Load balancer health checks failing for Node Alpha."
    hard_inputs[10] = "[Log T+10] Error: Database transaction timeout."
    hard_inputs[19] = "[Log T+19] Critical: Node Alpha evicted from cluster."

    hard = Task(
        name="infinite_incident_response_hard",
        difficulty="hard",
        attention_capacity=100, # Extremely tiny context limit representing a fragmented agent brain.
        max_cycles=30,
        inputs=hard_inputs,
        final_question="What cascade of events led to the eviction of Node Alpha?",
        expected_answers=["Load balancer failing", "health checks", "transaction timeout"]
    )

    return [easy, medium, hard]
