"""
app.py — FastAPI backend for ABC | CD BOT
Run from CD_BOT root: uvicorn backend.app:app --reload --port 8000
"""

import sys
from pathlib import Path

# Ensure sibling modules (auth, graph, slm) are importable
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
import io
import json

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import auth
import graph
import slm

# ── App setup ──────────────────────────────────────────────────────────────────
app = FastAPI(title="CD BOT API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND = Path(__file__).parent.parent / "frontend"

# ── In-memory state (single-user local app) ────────────────────────────────────
# Each entry: {"name": str, "upn": str}
_recipients: list[dict] = []
_pending_message: str = ""
_pending_sender_upn: str = "Sanjay265646@exlservice.com"


# ── Pydantic models ────────────────────────────────────────────────────────────
class MessageRequest(BaseModel):
    message: str


class PrepareRequest(BaseModel):
    message: str
    sender_upn: str = "Sanjay265646@exlservice.com"


# ── Static files & root ────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(str(FRONTEND / "index.html"))


# Mount AFTER all API routes so API routes take priority
# (done at bottom of file)


# ── Upload recipients ──────────────────────────────────────────────────────────
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are accepted.")

    content = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read Excel file: {e}")

    if "UPN" not in df.columns:
        raise HTTPException(status_code=400, detail="Excel file must contain a column named 'UPN'.")

    has_name = "Name" in df.columns
    records = []

    for _, row in df.iterrows():
        upn = str(row["UPN"]).strip() if pd.notna(row["UPN"]) else ""
        if not upn or upn.lower() == "nan":
            continue
        # Extract name: use Name column if present, else derive first name from UPN
        if has_name and pd.notna(row["Name"]):
            name = str(row["Name"]).strip().split()[0]  # first name only
        else:
            # e.g. "Kunal261101@exlservice.com" → "Kunal"
            name = upn.split("@")[0].rstrip("0123456789").capitalize()
        records.append({"name": name, "upn": upn})

    global _recipients
    _recipients = records

    first_name = records[0]["name"] if records else "Team"
    return {
        "count": len(records),
        "recipients": records,
        "first_name": first_name,
    }


# ── Format message via local SLM ───────────────────────────────────────────────
@app.post("/format-message")
async def format_message_endpoint(req: MessageRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    result = await asyncio.to_thread(slm.format_message, req.message)
    return result


# ── Authentication (MSAL device flow) ─────────────────────────────────────────
@app.get("/auth/initiate")
async def initiate_auth():
    try:
        flow_info = auth.initiate_device_flow()
        auth.start_token_polling()
        return flow_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auth/status")
async def check_auth_status():
    return {"status": auth.get_auth_status()}


# ── Prepare broadcast (store message before SSE stream) ───────────────────────
@app.post("/prepare")
async def prepare_broadcast(req: PrepareRequest):
    global _pending_message, _pending_sender_upn
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if not _recipients:
        raise HTTPException(status_code=400, detail="No recipients loaded. Please upload a file first.")
    _pending_message    = req.message
    _pending_sender_upn = req.sender_upn
    return {"ready": True, "recipient_count": len(_recipients)}


# ── Get first name for template preview ───────────────────────────────────────
@app.get("/recipients/first-name")
async def get_first_name():
    if _recipients:
        return {"first_name": _recipients[0]["name"]}
    return {"first_name": "Team"}


# ── SSE broadcast stream ───────────────────────────────────────────────────────
@app.get("/stream")
async def stream_broadcast():
    if auth.get_auth_status() != "success":
        raise HTTPException(status_code=401, detail="Not authenticated.")
    if not _recipients:
        raise HTTPException(status_code=400, detail="No recipients loaded.")
    if not _pending_message:
        raise HTTPException(status_code=400, detail="No message prepared.")

    message_template = _pending_message
    sender_upn       = _pending_sender_upn
    recipients       = list(_recipients)

    async def event_generator():
        def sse(data: dict) -> str:
            return f"data: {json.dumps(data)}\n\n"

        headers = auth.get_headers()
        total = len(recipients)
        sent = 0
        failed = 0

        yield sse({"type": "info", "status": "ok", "text": f"Broadcast started — {total} recipient(s) queued"})
        yield sse({"type": "info", "status": "ok", "text": f"Sender: {sender_upn}"})
        yield sse({"type": "info", "status": "ok", "text": "Microsoft Teams authentication verified"})
        yield sse({"type": "info", "status": "ok", "text": "Message template ready — personalised per recipient"})

        for recipient in recipients:
            upn  = recipient["upn"]
            name = recipient["name"]

            # Personalise: replace {name} placeholder with actual first name
            personalized = message_template.replace("{name}", name)

            yield sse({"type": "processing", "status": "info", "text": f"Processing  {upn}  ({name})", "upn": upn})
            await asyncio.sleep(0.05)

            # 1. Validate user
            valid = await asyncio.to_thread(graph.validate_user, upn, headers)
            if not valid:
                yield sse({"type": "validate", "status": "fail", "text": f"User not found in directory: {upn}", "upn": upn})
                failed += 1
                continue
            yield sse({"type": "validate", "status": "ok", "text": f"User validated: {upn}", "upn": upn})

            # 2. Create / get chat
            chat_id = await asyncio.to_thread(graph.create_chat, upn, sender_upn, headers)
            if not chat_id:
                yield sse({"type": "chat", "status": "fail", "text": f"Chat creation failed: {upn}", "upn": upn})
                failed += 1
                continue
            yield sse({"type": "chat", "status": "ok", "text": f"Chat ready for: {upn}", "upn": upn})

            # 3. Send personalised message
            success = await asyncio.to_thread(graph.send_message, chat_id, personalized, headers)
            if success:
                yield sse({"type": "sent", "status": "ok", "text": f"Message sent to: {name} ({upn})", "upn": upn})
                sent += 1
            else:
                yield sse({"type": "sent", "status": "fail", "text": f"Message delivery failed: {upn}", "upn": upn})
                failed += 1

            await asyncio.sleep(graph.DELAY_SECONDS)

        yield sse({
            "type": "complete",
            "status": "ok",
            "text": f"Broadcast complete — {sent}/{total} sent successfully, {failed} failed",
            "sent": sent,
            "failed": failed,
            "total": total,
        })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Model status ───────────────────────────────────────────────────────────────
@app.get("/model/status")
async def model_status():
    return {
        "available": slm.is_model_available(),
        "path": str(slm.MODEL_PATH),
    }


# ── Mount frontend static files (must be LAST) ────────────────────────────────
app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
