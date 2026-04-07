from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class ResetRequest(BaseModel):
    task_idx: int = 0

@app.post("/reset")
def reset_env(request: Optional[ResetRequest] = None):
    return {"status": "ok", "request": request.model_dump() if request else None}

client = TestClient(app)

print("Empty body response:")
print(client.post("/reset").json())
print("Null body response:")
print(client.post("/reset", json=None).json())
print("Empty dict response:")
print(client.post("/reset", json={}).json())
