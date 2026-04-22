# prompts.md — CD BOT Prompt Library

This file stores all prompts used in the CD BOT project — both SLM system/user prompts and development prompts used during building.

---

## 1. SLM Message Formatting Prompt

### Purpose
Sent to the local Phi-3-mini-4K-instruct-q4.gguf model to transform a raw user message into a professional, well-structured Microsoft Teams message.

### System Prompt
```
You are a professional corporate communication assistant. Your job is to take a raw, informal message and reformat it into a clear, professional, and well-structured Microsoft Teams message.

Rules:
- Keep the original meaning and intent intact.
- Use proper greeting and closing if appropriate.
- Use bullet points or numbered lists where helpful.
- Keep the tone professional but friendly.
- Do not add information that was not in the original message.
- Output only the formatted message — no explanations, no preamble.
```

### User Prompt Template
```
Please format the following message for a professional Microsoft Teams broadcast:

---
{raw_message}
---

Return only the formatted message.
```

---

## 2. Development Prompts (used with Claude Code)

### 2.1 — Initial Project Brief
```
I have a Python notebook (secondbot.ipynb) that sends Microsoft Teams messages to a list of recipients via Microsoft Graph API using MSAL delegated permissions. I need to build a full web application around this code.

Layout:
- Header: "ABC | CD BOT"
- Upload section: .xlsx file with UPN column
- Message input with Format & Preview button
- SLM-formatted editable preview (Phi-3-mini-4K-instruct-q4.gguf, local GGUF model)
- Send button
- Real-time broadcast log with tick/cross status per recipient

No external AI APIs — only the local GGUF model.
SLM model: Phi-3-mini-4K-instruct-q4.gguf from HuggingFace.
```

### 2.2 — Backend Build Prompt
```
Build the Python Flask backend for CD BOT with the following endpoints:
- POST /upload — parse .xlsx, return UPN list and count
- POST /format-message — run raw message through local Phi-3 GGUF model, return formatted text
- POST /authenticate — initiate MSAL device flow, return user_code and verification_uri
- POST /send — broadcast formatted message to all UPNs via Graph API, stream logs via SSE

Use the Microsoft credentials from CLAUDE.md. Implement retry logic (3 retries, 429 handling) and 2s delay between recipients.
```

### 2.3 — Frontend Build Prompt
```
Build the HTML/CSS/JS frontend for CD BOT:
- Branded header "ABC | CD BOT"
- File upload for .xlsx (shows recipient count on upload)
- Textarea for raw message input + "Format & Preview" button
- Rich text editable preview area for SLM output (bold, italic, underline, hyperlink support)
- "Send to All Recipients" button
- Real-time log panel below (SSE stream) with ✅/❌ icons per log entry
- Clean, professional dark/light corporate theme
```

### 2.4 — SLM Integration Prompt
```
Build slm.py for the CD BOT backend:
- Load Phi-3-mini-4K-instruct-q4.gguf from the local models/ directory using llama-cpp-python
- Expose a format_message(raw_text: str) -> str function
- Use the system prompt and user prompt template from prompts.md
- Handle model load errors gracefully
- Cache the model instance so it is only loaded once at startup
```

---

## 3. Phi-3 Model Download Instructions

### HuggingFace Source
- **Model page:** microsoft/Phi-3-mini-4k-instruct-gguf
- **File:** `Phi-3-mini-4k-instruct-q4.gguf`
- **Download command:**
  ```bash
  pip install huggingface_hub
  huggingface-cli download microsoft/Phi-3-mini-4k-instruct-gguf Phi-3-mini-4k-instruct-q4.gguf --local-dir ./models
  ```
- **Place the downloaded file at:** `CD_BOT/models/Phi-3-mini-4k-instruct-q4.gguf`

---

## 4. Notes on Prompt Engineering for Teams Messages

- Teams supports basic HTML in message body (`<b>`, `<i>`, `<u>`, `<a href>`, `<br>`, `<ul>/<li>`)
- The SLM output should be plain text; the frontend rich text editor handles HTML formatting
- When sending via Graph API, message `content` field accepts HTML with `contentType: "html"`
- Keep SLM output under ~500 words to stay within Teams message limits
