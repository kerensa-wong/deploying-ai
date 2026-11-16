"""
GustoPins Gradio UI (thin entry point – course style).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `python app.py` from inside this folder
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import gradio as gr
from dotenv import load_dotenv

from main import gustopins_chat

load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / ".secrets")
load_dotenv(_ROOT.parent / ".env")
load_dotenv(_ROOT.parent / ".secrets")

demo = gr.ChatInterface(
    fn=gustopins_chat,
    title="GustoPins",
    description=(
        "A calm journal-style companion for cafés, restaurants, weather, and a little country context. "
        "Default city is Toronto. Ask about pinned places, quiet spots, the weather, or a country."
    ),
    examples=[
        "What is the weather like in Toronto today?",
        "Show me all the places I have pinned.",
        "Quiet cafés good for reading or journaling?",
        "Tell me a little about Japan.",
        "Any places near Kensington that I liked?",
        "Is it a good day to go out for coffee?",
    ],
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
