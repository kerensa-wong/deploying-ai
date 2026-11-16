"""
Tool definitions and dispatcher for GustoPins (Service 3 – function calling).
"""

from __future__ import annotations

from typing import Any

from tools_weather import get_weather
from tools_country import get_country_info
from tools_cafe import list_by_status, lookup_place, search_cafe_log

# Responses API style tool schemas (same shape as course labs / horoscope_chat)
TOOLS = [
    {
        "type": "function",
        "name": "get_weather",
        "description": (
            "Get current weather and a short outlook for a city. "
            "Use when the user asks about weather, temperature, rain, or whether it is a good day to go out."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name. Defaults to Toronto if omitted.",
                }
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_country_info",
        "description": (
            "Get factual information about a country (capital, region, languages, currency, population). "
            "Use when the user asks about a country."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "country": {"type": "string", "description": "Country name in English."}
            },
            "required": ["country"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "list_by_status",
        "description": (
            "List ALL places in the personal café log with a given status. "
            "Use when the user wants the FULL list of pinned/tried/blacklist/want-to-try places with no location filter. "
            "status must be one of: pin, tried, blacklist, want-to-try."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "One of: pin, tried, blacklist, want-to-try",
                    "enum": ["pin", "tried", "blacklist", "want-to-try"],
                }
            },
            "required": ["status"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "lookup_place",
        "description": (
            "Look up ONE specific named café or restaurant in the personal log "
            "(e.g. Arvo Coffee, PAI, Lazy Barista, % Arabica). "
            "ALWAYS use this when the user asks whether a named place is good, whether to go, "
            "or what you think of a specific place by name."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the café or restaurant to look up.",
                }
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "search_cafe_log",
        "description": (
            "Semantic search over the café log for neighbourhood and recommendation questions, "
            'including "liked/pinned near X" and "disliked near X". '
            "Do NOT use this for 'show my pinned/tried/blacklist' full-list requests — use list_by_status instead."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language description of what the user is looking for.",
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
]


def run_tool(name: str, arguments: dict[str, Any], collection=None) -> str:
    if name == "get_weather":
        return get_weather(arguments.get("city") or "Toronto")
    if name == "get_country_info":
        country = arguments.get("country") or ""
        if not country:
            return "Please tell me which country you would like to know about."
        return get_country_info(country)
    if name == "list_by_status":
        return list_by_status(arguments.get("status") or "", collection)
    if name == "lookup_place":
        return lookup_place(arguments.get("name") or "", collection)
    if name == "search_cafe_log":
        return search_cafe_log(arguments.get("query") or "", collection)
    return f"Unknown tool: {name}"
