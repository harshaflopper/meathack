from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class Action(BaseModel):
    action_type: str = Field(
        ...,
        description="Allowed values: store_in_fast_memory, offload_to_disk, semantic_compress, retrieve_from_disk, submit_final_synthesis, no_op"
    )
    action_args: Dict[str, Any] = Field(
        default_factory=dict,
        description="""Arguments for the chosen action:
- store_in_fast_memory: {'content': '...'}
- offload_to_disk: {'fast_memory_ids': ['id1', 'id2']} 
- semantic_compress: {'fast_memory_ids': ['id1', 'id2'], 'summary': '...'}
- retrieve_from_disk: {'query': '...', 'limit': 3}
- submit_final_synthesis: {'answer': '...', 'justification_ids': ['id1']}
"""
    )

class Observation(BaseModel):
    current_stream_chunk: Optional[str] = Field(description="Latest incoming data chunk (e.g., streaming logs, emails).")
    attention_tokens_used: int = Field(description="Cost of all data currently held in fast memory.")
    attention_capacity: int = Field(description="Max tokens before Out-Of-Memory (OOM) fatal crash.")
    disk_storage_count: int = Field(description="Number of items safely offloaded to slow disk.")
    fast_memory_index: Dict[str, str] = Field(description="Current contents occupying the fast context window.")
    disk_index_preview: Dict[str, str] = Field(description="List of summary tags for chunks currently on disk.")
    recent_disk_retrieval: Optional[str] = Field(description="Content returned from the latest disk query.")
    task_goal: str = Field(description="The underlying objective.")
    task_type: str = Field(description="Difficulty tier.")
    cpu_cycles_left: int = Field(description="Turns remaining before the stream terminates or system times out.")
    status_message: str = Field(description="Environment telemetry regarding the last action.")

class Reward(BaseModel):
    value: float = Field(..., description="Reward value between 0.0 and 1.0.")
    message: str = Field(..., description="Reason for reward shaping.")
