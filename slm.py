"""
slm.py — Local Phi-3-mini-4k-instruct-q4.gguf inference via llama-cpp-python.
Model is loaded once at startup. Falls back to original text if model is missing.
"""

from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "models" / "Phi-3-mini-4k-instruct-q4.gguf"

_llm = None
_model_loaded: bool = False
_load_error: str = ""

_SYSTEM_PROMPT = (
    "You are a professional corporate communication assistant. "
    "Your job is to take a raw, informal message and reformat it into a clear, "
    "professional, and well-structured Microsoft Teams message.\n\n"
    "Rules:\n"
    "- Keep the original meaning and intent intact.\n"
    "- Use a proper greeting and closing when appropriate.\n"
    "- Use bullet points or numbered lists where helpful.\n"
    "- Keep the tone professional but friendly.\n"
    "- Do NOT add any information that was not in the original message.\n"
    "- Output ONLY the formatted message — no explanations, no preamble."
)

_USER_TEMPLATE = (
    "Please format the following message for a professional Microsoft Teams broadcast:\n\n"
    "---\n{raw}\n---\n\n"
    "Return only the formatted message."
)


def is_model_available() -> bool:
    return MODEL_PATH.exists()


def load_model() -> bool:
    global _llm, _model_loaded, _load_error
    if _model_loaded:
        return True
    if not MODEL_PATH.exists():
        _load_error = f"Model file not found at: {MODEL_PATH}"
        return False
    try:
        from llama_cpp import Llama  # type: ignore
        _llm = Llama(
            model_path=str(MODEL_PATH),
            n_ctx=4096,
            n_threads=4,
            n_gpu_layers=0,
            verbose=False,
        )
        _model_loaded = True
        _load_error = ""
        return True
    except Exception as e:
        _load_error = str(e)
        return False


def format_message(raw_text: str) -> dict:
    if not _model_loaded:
        if not load_model():
            return {
                "formatted": raw_text,
                "model_used": False,
                "warning": f"Model not loaded — {_load_error}. Showing original message.",
            }

    prompt = (
        f"<|system|>\n{_SYSTEM_PROMPT}<|end|>\n"
        f"<|user|>\n{_USER_TEMPLATE.format(raw=raw_text)}<|end|>\n"
        f"<|assistant|>\n"
    )
    try:
        output = _llm(
            prompt,
            max_tokens=1024,
            temperature=0.3,
            stop=["<|end|>", "<|user|>", "<|system|>"],
            echo=False,
        )
        formatted = output["choices"][0]["text"].strip()
        return {"formatted": formatted, "model_used": True, "warning": None}
    except Exception as e:
        return {
            "formatted": raw_text,
            "model_used": False,
            "warning": f"Inference error: {e}. Showing original message.",
        }
