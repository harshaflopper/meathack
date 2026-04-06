"""
Task base class with deterministic grader.
All task definitions import from here.
"""
import re
from typing import Dict, List


class Task:
    def __init__(
        self,
        name: str,
        difficulty: str,
        attention_capacity: int,
        max_cycles: int,
        inputs: List[str],
        final_question: str,
        expected_answers: List[str],
        config_bugs: Dict[str, str] = None,
        services: Dict[str, str] = None,
        important_ids: List[int] = None,
        partial_milestones: Dict[str, List[str]] = None,
    ):
        self.name = name
        self.difficulty = difficulty
        self.attention_capacity = attention_capacity
        self.max_cycles = max_cycles
        self.inputs = inputs
        self.final_question = final_question
        self.expected_answers = expected_answers
        self.config_bugs = config_bugs or {}
        self.services = services or {}
        self.important_ids = important_ids or []
        self.partial_milestones = partial_milestones or {}

    def grade(self, answer: str, justifications: List[str]) -> float:
        """Deterministic grader with controlled normalization.
        Uses regex on normalized strings to prevent partial-match exploits.
        """
        # Normalize: lowercase, strip dashes/underscores for safe comparison
        normalized = answer.lower().replace("-", "").replace("_", "")

        total = len(self.expected_answers)
        if total == 0:
            return 0.0

        matches = 0
        for exp in self.expected_answers:
            exp_normalized = exp.lower().replace("-", "").replace("_", "")
            # Use escaped pattern search — deterministic and controlled
            pattern = re.escape(exp_normalized)
            if re.search(pattern, normalized):
                matches += 1

        correctness = matches / total
        has_justification = len(justifications) > 0

        if correctness >= 0.8 and has_justification:
            return 1.0
        elif correctness >= 0.8 and not has_justification:
            return 0.5
        elif correctness >= 0.4 and has_justification:
            return 0.3 + (correctness * 0.5)
        elif correctness > 0:
            return correctness * 0.4
        return 0.0
