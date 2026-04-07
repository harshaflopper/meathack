from fastapi import FastAPI, HTTPException, Body, Request
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from models import Action, Observation, Reward
from env import MemoryEnvironment

app = FastAPI(title="LLM Memory Optimizer — DevOps Decision System")

# Global environment instance
env = MemoryEnvironment()


class ResetRequest(BaseModel):
    task_idx: int = 0


class StepResponse(BaseModel):
    observation: Observation
    reward: float
    done: bool
    info: Dict[str, Any]


class TaskInfo(BaseModel):
    index: int
    name: str
    difficulty: str
    description: str


@app.get("/")
def read_root():
    return {
        "status": "ok",
        "environment": "LLM Memory Optimizer — DevOps Decision System",
        "version": "3.0.0",
        "tasks": len(env.tasks),
    }


@app.post("/reset", response_model=Observation)
async def reset_env(request: Request):
    """Bulletproof reset endpoint - handles empty body, null, invalid JSON."""
    try:
        body = await request.json()
        task_idx = body.get("task_idx", 0) if body else 0
    except Exception:
        task_idx = 0  # handles empty or invalid JSON

    try:
        return env.reset(task_idx=task_idx)
    except Exception:
        return env.reset(task_idx=0)


@app.post("/step", response_model=StepResponse)
def step_env(action: Action):
    try:
        obs, reward_val, done, info = env.step(action)
        return StepResponse(observation=obs, reward=reward_val, done=done, info=info)
    except Exception as e:
        # NEVER crash — always return valid shape
        try:
            fallback_obs = env._get_obs()
        except Exception:
            fallback_obs = env.reset(task_idx=env.current_task_idx)
        return StepResponse(
            observation=fallback_obs,
            reward=0.0,
            done=False,
            info={"error": str(e)},
        )


@app.get("/state", response_model=Observation)
def get_state():
    return env._get_obs()


@app.get("/tasks", response_model=List[TaskInfo])
def list_tasks():
    return [
        TaskInfo(
            index=i,
            name=t.name,
            difficulty=t.difficulty,
            description=t.final_question,
        )
        for i, t in enumerate(env.tasks)
    ]
