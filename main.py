from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from models import Action, Observation, Reward
from env import MemoryEnvironment

app = FastAPI(title="LLM Memory Optimizer — DevOps Decision System")

# Global environment instance
env = MemoryEnvironment()


class ResetRequest(BaseModel):
    task_idx: int = 0


class StepResponse(BaseModel):
    observation: Observation
    reward: Reward
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
def reset_env(request: ResetRequest):
    try:
        return env.reset(task_idx=request.task_idx)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step", response_model=StepResponse)
def step_env(action: Action):
    try:
        obs, reward, done, info = env.step(action)
        return StepResponse(observation=obs, reward=reward, done=done, info=info)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
