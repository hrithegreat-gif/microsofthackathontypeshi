# api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import cosmos_client as db
import director
from models import TaskLedger, NonFunctionalRequirements, TechConstraints
import uuid
import asyncio

app = FastAPI(title="Agentic Nexus — Director Service")


# ── Request schemas ────────────────────────────────────────────────────────────

class ClarifyRequest(BaseModel):
    project_id: Optional[str] = None
    message: str

class BaseRequest(BaseModel):
    project_id: str


# ── POST /clarify ──────────────────────────────────────────────────────────────

@app.post("/clarify")
async def clarify(req: ClarifyRequest):

    project_id = req.project_id or str(uuid.uuid4())
    history = db.get_conversation(project_id)
    history.append({"role": "user", "content": req.message})

    result = await director.run_clarification(history)

    if result["action"] == "TASK_LEDGER_COMPLETE":

        raw = result["task_ledger"]

        ledger = TaskLedger(
            project_id=project_id,
            user_intent=raw["user_intent"],
            functional_requirements=raw.get("functional_requirements", []),
            integration_targets=raw.get("integration_targets", []),
            status="DRAFT"
        )

        nfr_data = raw.get("non_functional_requirements", {})
        if nfr_data:
            ledger.non_functional_requirements = NonFunctionalRequirements(**nfr_data)

        tc_data = raw.get("tech_constraints", {})
        if tc_data:
            ledger.tech_constraints = TechConstraints(**tc_data)

        db.save_task_ledger(ledger)
        db.save_conversation(project_id, history)

        return {
            "status": "complete",
            "project_id": project_id,
            "task_ledger": ledger.model_dump(),
            "message": "Task Ledger saved. Call POST /aeg to generate the execution graph."
        }

    elif result["action"] == "GUARDRAIL":

        history.append({"role": "assistant", "content": result["question"]})
        db.save_conversation(project_id, history)

        return {
            "status": "guardrail",
            "project_id": project_id,
            "risk": result["risk"],
            "recommendation": result["recommendation"],
            "question": result["question"]
        }

    else:

        history.append({"role": "assistant", "content": result["question"]})
        db.save_conversation(project_id, history)

        return {
            "status": "asking",
            "project_id": project_id,
            "question": result["question"]
        }


# ── GET /ledger/{project_id} ───────────────────────────────────────────────────

@app.get("/ledger/{project_id}")
async def get_ledger(project_id: str):
    try:
        ledger = db.get_task_ledger(project_id)
        return {"status": "found", "task_ledger": ledger}
    except Exception:
        raise HTTPException(
            status_code=404,
            detail="No Task Ledger found for project " + project_id
        )


# ── GET /health ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "director"}


# ── Startup ────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    pass