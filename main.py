from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from models import Action, Observation
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
def reset_env(request: Optional[Dict[str, Any]] = Body(default=None)):
    """Reset environment. Accepts empty body (defaults to task 0)."""
    task_idx = request.get("task_idx", 0) if request else 0
    try:
        return env.reset(task_idx=task_idx)
    except Exception as e:
        # Fallback: reset to task 0 on error
        try:
            return env.reset(task_idx=0)
        except Exception:
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/step", response_model=StepResponse)
def step_env(request: Optional[Dict[str, Any]] = Body(default=None)):
    try:
        # Construct action safely from raw dict to prevent 422 errors
        if not request:
            action = Action(action_type="no_op", action_args={})
        else:
            # Manually validate to prevent Pydantic 422s from bubbling up unhandled
            action_type = request.get("action_type", "no_op")
            action_args = request.get("action_args", {})
            if not isinstance(action_args, dict):
                action_args = {}
            action = Action(action_type=action_type, action_args=action_args)

        obs, reward, done, info = env.step(action)
        return StepResponse(observation=obs, reward=reward, done=done, info=info)
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
