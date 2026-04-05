from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from models import Action, Observation, Reward
from env import MemoryEnvironment

app = FastAPI(title="AI Memory Management System")

# Global environment instance
env = MemoryEnvironment()

class ResetRequest(BaseModel):
    task_idx: int = 0

class StepResponse(BaseModel):
    observation: Observation
    reward: Reward
    done: bool
    info: Dict[str, Any]

@app.get("/")
def read_root():
    return {"status": "ok", "environment": "AI Memory Management System"}

@app.post("/reset", response_model=Observation)
def reset_env(request: ResetRequest):
    return env.reset(task_idx=request.task_idx)

@app.post("/step", response_model=StepResponse)
def step_env(action: Action):
    obs, reward, done, info = env.step(action)
    return StepResponse(observation=obs, reward=reward, done=done, info=info)

@app.get("/state", response_model=Observation)
def get_state():
    return env._get_obs()
