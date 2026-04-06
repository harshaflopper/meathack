from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

class Action(BaseModel):
    action_type: str = Field(
        ...,
        description=(
            "Allowed values: "
            "store_in_fast_memory, offload_to_disk, semantic_compress, "
            "retrieve_from_disk, submit_final_synthesis, "
            "mark_email_important, fix_config, restart_service, "
            "escalate_incident, no_op"
        )
    )
    action_args: Dict[str, Any] = Field(
        default_factory=dict,
        description="""Arguments for the chosen action:
- store_in_fast_memory: {'content': '<string data>'}
- offload_to_disk: {'fast_memory_ids': ['id1', 'id2']}
- semantic_compress: {'fast_memory_ids': ['id1', 'id2'], 'summary': '<abstracted text>'}
- retrieve_from_disk: {'query': '<semantic search string>', 'limit': 3}
- submit_final_synthesis: {'answer': '<final answer>', 'justification_ids': ['id1']}
- mark_email_important: {'memory_id': '<id of email in fast_memory>'}
- fix_config: {'target': '<config key/file to fix>', 'new_value': '<corrected value>'}
- restart_service: {'service_name': '<name of the service to restart>'}
- escalate_incident: {'summary': '<incident summary>', 'severity': 'low|medium|high|critical'}
- no_op: {}
"""
    )

class Observation(BaseModel):
    current_stream_chunk: Optional[str] = Field(
        default=None,
        description="Latest incoming data chunk (e.g., streaming logs, emails, config files)."
    )
    attention_tokens_used: int = Field(
        description="Cost of all data currently held in fast memory."
    )
    attention_capacity: int = Field(
        description="Max tokens before Out-Of-Memory (OOM) fatal crash."
    )
    disk_storage_count: int = Field(
        description="Number of items safely offloaded to slow disk."
    )
    fast_memory_index: Dict[str, str] = Field(
        description="Current contents occupying the fast context window."
    )
    disk_index_preview: Dict[str, str] = Field(
        description="Summary tags for chunks currently on disk."
    )
    recent_disk_retrieval: Optional[str] = Field(
        default=None,
        description="Content returned from the latest disk query."
    )
    task_goal: str = Field(
        description="The underlying objective the agent must accomplish."
    )
    task_type: str = Field(
        description="Difficulty tier: easy, medium, or hard."
    )
    cpu_cycles_left: int = Field(
        description="Turns remaining before the system times out."
    )
    status_message: str = Field(
        description="Environment telemetry regarding the last action."
    )
    partial_progress: Dict[str, bool] = Field(
        default_factory=dict,
        description="Intermediate milestones achieved so far (e.g., key evidence discovered)."
    )
    decision_log: List[str] = Field(
        default_factory=list,
        description="Chronological log of all agent decisions and outcomes for explainability."
    )
    services_status: Dict[str, str] = Field(
        default_factory=dict,
        description="Current status of simulated services (e.g., {'redis': 'down', 'api': 'running'})."
    )


