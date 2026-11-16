# GustoPins – Assignment 2

A calm, journal-style conversational system for exploring cafés and restaurants, checking the weather, and looking up basic country information.

**Personality**  
GustoPins speaks quietly and thoughtfully, like someone who carefully keeps a personal notebook of places. Default geographic context is Toronto.

---

## Project structure (course style)

```
05_src/assignment_chat/
├── app.py                 # Gradio UI only
├── main.py                # Client, Chroma load, Responses API tool loop
├── prompts.py             # System instructions + guardrail checks
├── tools.py               # Tool schemas + run_tool dispatcher
├── tools_weather.py       # Open-Meteo weather
├── tools_country.py       # REST Countries
├── tools_cafe.py          # list_by_status, lookup_place, search_cafe_log
├── vectorstore.py         # Chroma persistent client + embeddings
├── data/cafe_log.jsonl    # Personal café / restaurant log
├── chroma_db/             # Created at runtime (do not commit)
├── readme.md
└── __init__.py
```

This layout follows the lecture examples (`app.py` / `main.py` / `prompts.py` / tool modules).

---

## Services

### Service 1 – API Calls
| Purpose | API | Notes |
|---------|-----|-------|
| Weather | Open-Meteo | No API key; natural-language summary |
| Country info | REST Countries | No API key; natural-language summary |

### Service 2 – Semantic Query
ChromaDB **persistent** client over `data/cafe_log.jsonl`.

- Status values: `pin`, `tried`, `blacklist`, `want-to-try`
- Embedding model: `text-embedding-3-small` via the course API Gateway
- First run builds `./chroma_db`; later runs reuse it

### Service 3 – Function Calling
Tools (Responses API, with chat.completions fallback):

- `get_weather`
- `get_country_info`
- `list_by_status` — full lists by status (metadata filter)
- `lookup_place` — one named place from the journal
- `search_cafe_log` — neighbourhood / recommendation search

---

## Guardrails

- No system-prompt reveal or modification
- Soft refusal for cats/dogs, horoscopes/zodiac, Taylor Swift

---

## How to run

```bash
source deploying-ai-env/Scripts/activate   # Windows Git Bash
cd 05_src/assignment_chat
python app.py
```

Requires `API_GATEWAY_KEY` in `05_src/.secrets` (course gateway).

If you change `data/cafe_log.jsonl`, rebuild embeddings once:

```bash
rm -rf chroma_db
python app.py
```

---

## Design decisions

- File split for clarity and marker familiarity
- Responses API tool loop aligned with lab / horoscope_chat patterns
- Dedicated `list_by_status` and `lookup_place` so pinned lists and named places are reliable
- No SQLite; Chroma + JSONL only
