"""
GustoPins main chat logic: client, Chroma collection, Responses API tool loop.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from prompts import return_instructions, check_restricted
from tools import TOOLS, run_tool
from vectorstore import build_or_load_collection

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / ".secrets")
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR.parent / ".secrets")

MODEL = os.getenv("MODEL", "gpt-4o-mini")
GATEWAY_BASE_URL = "https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1"
MAX_HISTORY = 20
INSTRUCTIONS = return_instructions()


def get_openai_client() -> OpenAI:
    gateway_key = os.getenv("API_GATEWAY_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    use_gateway = bool(
        gateway_key and gateway_key.strip() and not gateway_key.strip().lower().startswith("if ")
    )
    if os.getenv("USE_GATEWAY", "").lower() in ("true", "1", "yes"):
        use_gateway = True

    if use_gateway:
        print("[GustoPins] Using course API Gateway")
        print(f"[GustoPins] base URL: {GATEWAY_BASE_URL}")
        return OpenAI(
            base_url=GATEWAY_BASE_URL,
            api_key="any value",
            default_headers={"x-api-key": gateway_key},
        )
    print("[GustoPins] Using direct OpenAI key")
    return OpenAI(api_key=openai_key)


client = get_openai_client()

# ---------------------------------------------------------------------------
# Vector store
# ---------------------------------------------------------------------------

print("Loading GustoPins café log into ChromaDB (persistent)...")
try:
    cafe_collection = build_or_load_collection(force_rebuild=False)
    print(f"Collection ready. Documents: {cafe_collection.count()}")
except Exception as e:
    print("=" * 60)
    print("WARNING: could not load / build the Chroma collection.")
    print(f"Reason: {e}")
    print("=" * 60)
    cafe_collection = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_text_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return "" if content is None else str(content)


def sanitize_history(history: list) -> list[dict]:
    clean = []
    if not history:
        return clean
    for msg in history:
        if isinstance(msg, dict) and "role" in msg:
            clean.append(
                {"role": msg["role"], "content": extract_text_content(msg.get("content"))}
            )
        elif isinstance(msg, (list, tuple)) and len(msg) >= 2:
            if msg[0]:
                clean.append({"role": "user", "content": str(msg[0])})
            if msg[1]:
                clean.append({"role": "assistant", "content": str(msg[1])})
    return clean[-MAX_HISTORY:]


# ---------------------------------------------------------------------------
# Chat entry point
# ---------------------------------------------------------------------------

def gustopins_chat(message: str, history: list = None) -> str:
    message = (message or "").strip()
    if not message:
        return ""

    refusal = check_restricted(message)
    if refusal:
        return refusal

    conversation_input = sanitize_history(history or []) + [
        {"role": "user", "content": message}
    ]

    try:
        response = client.responses.create(
            model=MODEL,
            instructions=INSTRUCTIONS,
            input=conversation_input,
            tools=TOOLS,
        )
    except Exception as e:
        return _chat_completions_fallback(message, conversation_input, e)

    conversation_input += response.output

    tool_calls = [
        item for item in response.output if getattr(item, "type", None) == "function_call"
    ]

    if tool_calls:
        for item in tool_calls:
            name = item.name
            try:
                args = json.loads(item.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            print(f"[GustoPins] tool call: {name}({args})")
            result = run_tool(name, args, collection=cafe_collection)
            conversation_input.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": result if isinstance(result, str) else json.dumps(result),
                }
            )

        try:
            response = client.responses.create(
                model=MODEL,
                instructions=INSTRUCTIONS,
                tools=TOOLS,
                input=conversation_input,
            )
        except Exception as e:
            return f"I retrieved the information but had trouble forming a reply ({e})."

        more_calls = [
            item for item in response.output if getattr(item, "type", None) == "function_call"
        ]
        if more_calls:
            conversation_input += response.output
            for item in more_calls:
                name = item.name
                try:
                    args = json.loads(item.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                print(f"[GustoPins] tool call (round 2): {name}({args})")
                result = run_tool(name, args, collection=cafe_collection)
                conversation_input.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": result if isinstance(result, str) else json.dumps(result),
                    }
                )
            try:
                response = client.responses.create(
                    model=MODEL,
                    instructions=INSTRUCTIONS,
                    tools=TOOLS,
                    input=conversation_input,
                )
            except Exception as e:
                return f"I retrieved the information but had trouble forming a reply ({e})."

    text = getattr(response, "output_text", None)
    if text:
        return text
    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", None) == "message":
            return extract_text_content(getattr(item, "content", ""))
    return "I am not sure how to answer that right now."


def _chat_completions_fallback(message: str, conversation_input: list, first_error: Exception) -> str:
    print(f"[GustoPins] Responses API failed ({first_error}); trying chat.completions")
    messages = [{"role": "system", "content": INSTRUCTIONS}]
    for m in conversation_input:
        if isinstance(m, dict) and m.get("role") in ("user", "assistant", "system"):
            messages.append({"role": m["role"], "content": m.get("content", "")})

    chat_tools = [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("parameters", {}),
            },
        }
        for t in TOOLS
    ]

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=chat_tools,
            tool_choice="auto",
            temperature=0.6,
        )
    except Exception as e:
        return f"I encountered a problem reaching the model: {e}"

    msg = response.choices[0].message
    if msg.tool_calls:
        messages.append(msg)
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            print(f"[GustoPins] tool call: {tc.function.name}({args})")
            result = run_tool(tc.function.name, args, collection=cafe_collection)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        try:
            second = client.chat.completions.create(
                model=MODEL, messages=messages, temperature=0.6
            )
            return second.choices[0].message.content or "…"
        except Exception as e:
            return f"I retrieved the information but had trouble forming a reply ({e})."
    return msg.content or "…"
