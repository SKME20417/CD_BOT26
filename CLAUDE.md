# CLAUDE.md — CD BOT Project

## Project Overview

A web application that enables bulk Microsoft Teams message broadcasting via Microsoft Graph API (delegated permissions / MSAL device flow). Messages are formatted by a locally-running SLM (Small Language Model) before being sent. The entire system runs locally — no external AI APIs.

---

## Application Name

**ABC | CD BOT**

---

## Core Technologies

| Layer | Technology |
|---|---|
| Frontend | HTML + CSS + JavaScript (vanilla or lightweight framework) |
| Backend | Python (FastAPI + Uvicorn) |
| Auth | MSAL (PublicClientApplication — Device Flow) |
| Graph API | Microsoft Graph v1.0 |
| SLM | Phi-3-mini-4K-instruct-q4.gguf (local, via llama-cpp-python or ctransformers) |
| Recipient Data | Excel (.xlsx) via pandas + openpyxl |

---

## Microsoft Entra / Graph Configuration

| Key | Value |
|---|---|
| CLIENT_ID | e20f04d6-7a3d-4ea4-8abb-17092649496b |
| TENANT_ID | dafe49bc-5ac3-4310-97b4-3e44a28cbf18 |
| SENDER_UPN | Sanjay265646@exlservice.com |
| AUTHORITY | https://login.microsoftonline.com/{TENANT_ID} |
| GRAPH BASE | https://graph.microsoft.com/v1.0 |
| SCOPES | Chat.ReadWrite, ChatMessage.Send, User.Read |

---

## SLM Configuration

- **Model:** Phi-3-mini-4K-instruct-q4.gguf
- **Source:** HuggingFace (downloaded locally — no API key required)
- **Runtime:** llama-cpp-python (GGUF inference locally)
- **Purpose:** Format the raw user message into a professional, well-structured Teams message
- **Invocation:** Triggered when user clicks the first "Format Message" / "Send" button in the message input area

---

## Page Layout (Top to Bottom)

### 1. Header
- Text: **ABC | CD BOT**
- Style: Bold, centered, branded header bar

### 2. Upload Section
- Label: "Upload Recipients File"
- Input: File upload button accepting `.xlsx` files only
- On upload: Parse Excel, extract `UPN` column, display recipient count

### 3. Message Input Section
- Label: "Enter your message"
- Input: Multi-line text area for raw message input
- Button: **"Format & Preview"** — triggers SLM formatting

### 4. Formatted Message Preview Section (appears after Format & Preview is clicked)
- Displays the SLM-formatted message
- Fully editable rich text area (supports):
  - Font styling (bold, italic, underline)
  - Hyperlink insertion
  - Direct body content editing
- Button: **"Send to All Recipients"** — triggers the broadcast

### 5. Live Broadcast Log Section (appears after Send is clicked)
- Real-time log panel showing each step with status icons
- Log entries include:
  - ✅ / ❌ Recipients file loaded — `N recipients found`
  - ✅ / ❌ Authentication successful
  - ✅ / ❌ Message formatted by SLM
  - For each recipient:
    - ➡️ Processing `<UPN>`
    - ✅ / ❌ User validated: `<UPN>`
    - ✅ / ❌ Chat created with `<UPN>`
    - ✅ / ❌ Message sent to `<UPN>`
  - 🎯 Broadcast completed — `X of Y messages sent`

---

## Backend API Endpoints (to be built)

| Endpoint | Method | Purpose |
|---|---|---|
| `/upload` | POST | Accept .xlsx file, parse UPNs, return recipient list |
| `/format-message` | POST | Pass raw message to SLM, return formatted message |
| `/authenticate` | POST | Initiate MSAL device flow, return device code + verification URL |
| `/send` | POST | Run broadcast loop, stream logs back to frontend (SSE or WebSocket) |

---

## Key Behaviors

- **Authentication:** Uses MSAL device flow — user is shown a URL + code to authenticate via browser. This must be surfaced clearly in the UI.
- **SLM is local:** Model file (.gguf) is loaded from local disk — no internet call for formatting.
- **Log streaming:** Broadcast logs must stream in real-time (Server-Sent Events preferred).
- **Retry logic:** Each message send retries up to 3 times on rate limit (HTTP 429).
- **Delay:** 2-second delay between recipients to avoid throttling.
- **Editable preview:** The SLM output is editable before sending — the edited version (not the original) is what gets sent.

---

## Project File Structure (planned)

```
CD_BOT/
├── CLAUDE.md                  # This file
├── prompts.md                 # Prompts used for SLM and development
├── secondbot.ipynb            # Original working prototype
├── recipients.xlsx            # Sample recipient data
├── backend/
│   ├── app.py                 # Flask/FastAPI main app
│   ├── auth.py                # MSAL authentication logic
│   ├── graph.py               # Microsoft Graph API calls
│   ├── slm.py                 # Phi-3 GGUF model loader and inference
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── index.html             # Main page
│   ├── style.css              # Styling
│   └── app.js                 # Frontend logic (upload, preview, send, logs)
└── models/
    └── Phi-3-mini-4K-instruct-q4.gguf   # Downloaded model file (local)
```

---

## Dependencies (Python)

```
msal
requests
pandas
openpyxl
flask
flask-cors
llama-cpp-python
```

---

## Constraints & Rules

- Do NOT use any external AI APIs (OpenAI, Anthropic, etc.) for message formatting — only the local GGUF model.
- Do NOT hardcode tokens or secrets in source files.
- The app runs fully locally — no cloud deployment assumed.
- The Excel file must have a column named exactly `UPN`.
- The formatted message (after user edits) is what gets sent — never the raw input directly.
