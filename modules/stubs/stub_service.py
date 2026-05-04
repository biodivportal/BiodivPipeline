from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class ProcessRequest(BaseModel):
    records: list[dict]
    module: str = "generic"

@app.post("/process")
async def process(req: ProcessRequest):
    return {
        "module": req.module,
        "status": "stub",
        "records_received": len(req.records),
        "results": [{"id": r.get("HerbariumID", "unknown"), "processed": False} for r in req.records]
    }

@app.get("/health")
async def health():
    return {"status": "ok"}
