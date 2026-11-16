"""Service 2 – Café log: list by status, lookup by name, semantic search (Chroma)."""

from __future__ import annotations

STATUS_LABEL = {
    "pin": "📌 pinned (I would gladly return)",
    "tried": "already tried",
    "blacklist": "on my personal blacklist",
    "want-to-try": "on my want-to-try list",
}


def _format_entries(pairs: list) -> str:
    lines = []
    for meta in pairs:
        name = meta.get("name", "Unknown place")
        status = meta.get("status", "")
        neighbourhood = meta.get("neighbourhood", "")
        city = meta.get("city", "Toronto")
        vibe = meta.get("vibe", "")
        notes = meta.get("notes", "")

        entry = f"• **{name}**"
        if neighbourhood:
            entry += f" ({neighbourhood}, {city})"
        entry += f" — {STATUS_LABEL.get(status, status)}."
        if vibe:
            entry += f" Vibe: {vibe}."
        if notes:
            short = notes if len(notes) < 220 else notes[:217] + "…"
            entry += f" My note: “{short}”"
        lines.append(entry)
    return "\n\n".join(lines)


def list_by_status(status: str, collection) -> str:
    """
    Return ALL places with a given status (pin / tried / blacklist / want-to-try).
    Uses metadata filter so nothing is dropped by semantic ranking.
    """
    if collection is None:
        return "The café log is not available at the moment."

    status = (status or "").strip().lower()
    aliases = {
        "pinned": "pin",
        "favourite": "pin",
        "favorite": "pin",
        "pin": "pin",
        "tried": "tried",
        "blacklist": "blacklist",
        "dislike": "blacklist",
        "want-to-try": "want-to-try",
        "want_to_try": "want-to-try",
        "wishlist": "want-to-try",
    }
    status = aliases.get(status, status)
    if status not in ("pin", "tried", "blacklist", "want-to-try"):
        return f"I only track these statuses: pin, tried, blacklist, want-to-try. You asked for “{status}”."

    try:
        # Prefer metadata filter
        results = collection.get(where={"status": status}, include=["metadatas"])
        metas = results.get("metadatas") or []
    except Exception:
        # Fallback: get all and filter in Python
        try:
            results = collection.get(include=["metadatas"])
            metas = [m for m in (results.get("metadatas") or []) if m.get("status") == status]
        except Exception as e:
            return f"I could not read the café log ({e})."

    if not metas:
        return f"There are no places marked as “{status}” in the log yet."

    header = {
        "pin": "Here are all the places currently pinned in your journal:\n\n",
        "tried": "Here are the places you have already tried:\n\n",
        "blacklist": "Here are the places on your personal blacklist:\n\n",
        "want-to-try": "Here are the places on your want-to-try list:\n\n",
    }[status]
    return header + _format_entries(metas)



def lookup_place(name: str, collection) -> str:
    """
    Look up a specific place by name in the café log.
    Use when the user asks about one named café/restaurant (e.g. "is Arvo Coffee good?").
    """
    if collection is None:
        return "The café log is not available at the moment."
    name = (name or "").strip()
    if not name:
        return "Which place would you like me to look up?"

    name_l = name.lower()
    # Normalise common variants
    aliases = {
        "% arabica": "arabica",
        "percent arabica": "arabica",
        "pai": "pai",
        "arvo": "arvo coffee",
    }
    for a, b in aliases.items():
        if a in name_l:
            name_l = b

    try:
        results = collection.get(include=["metadatas"])
        metas = results.get("metadatas") or []
    except Exception as e:
        return f"I could not read the café log ({e})."

    matches = []
    for m in metas:
        n = (m.get("name") or "").lower()
        if name_l in n or n in name_l:
            matches.append(m)
        elif any(tok and tok in n for tok in name_l.replace("%", " ").split() if len(tok) > 2):
            matches.append(m)

    def score(m):
        n = (m.get("name") or "").lower()
        if name_l == n:
            return 0
        if name_l in n or n in name_l:
            return 1
        return 2

    seen = set()
    uniq = []
    for m in sorted(matches, key=score):
        key = m.get("name")
        if key not in seen:
            seen.add(key)
            uniq.append(m)
    matches = uniq

    if not matches:
        return (
            f"I do not have “{name}” in the GustoPins log. "
            "I can only speak from places already recorded there, or help you search for similar spots."
        )

    header = f"From your journal entry on this place:\n\n"
    return header + _format_entries(matches)


def search_cafe_log(query: str, collection, n_results: int = 8) -> str:
    """Semantic search over the café log (open-ended place questions)."""
    if collection is None:
        return "The café log is not available at the moment."
    if not (query or "").strip():
        return "What kind of place are you looking for?"

    q = query.lower()

    # Light neighbourhood expansion so adjacent areas can match (Toronto-specific)
    expansions = []
    if "distillery" in q:
        expansions.append("Corktown near Distillery District")
    if "corktown" in q:
        expansions.append("Distillery District Corktown")
    if "kensington" in q:
        expansions.append("Kensington Market Chinatown")
    search_text = query
    if expansions:
        search_text = query + " " + " ".join(expansions)

    # Fetch extra candidates so we can re-rank by preference
    try:
        results = collection.query(
            query_texts=[search_text],
            n_results=min(max(collection.count(), 1), 20),
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        return f"I could not search the café log ({e})."

    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]
    if not metas:
        return (
            "I looked through the log and did not find a close match. "
            "Would you like different words, or shall we stay with Toronto places I know?"
        )

    pairs = list(zip(metas, dists))

    # Preference-aware re-rank for recommendation-style queries
    wants_liked = any(w in q for w in ("like", "liked", "pin", "pinned", "favourite", "favorite", "love"))
    wants_dislike = any(w in q for w in ("dislike", "blacklist", "avoid", "hate"))
    is_recommend = any(w in q for w in ("recommend", "suggest", "nice", "good", "find", "near", "coffee", "cafe", "restaurant"))

    def rank_key(item):
        meta, dist = item
        status = meta.get("status", "")
        notes = (meta.get("notes") or "").lower()
        # lower is better
        if wants_dislike:
            pref = 0 if status == "blacklist" else 5
        elif wants_liked:
            pref = 0 if status == "pin" else 5
        elif is_recommend:
            if status == "pin":
                pref = 0
            elif status == "want-to-try":
                pref = 1
            elif status == "tried" and ("not interested" in notes or "not eager" in notes or "not a pin" in notes):
                pref = 4
            elif status == "tried":
                pref = 2
            elif status == "blacklist":
                pref = 9
            else:
                pref = 3
        else:
            pref = 0
        return (pref, dist)

    pairs.sort(key=rank_key)

    if wants_liked:
        pairs = [(m, d) for m, d in pairs if m.get("status") == "pin"] or pairs[:n_results]
    elif wants_dislike:
        pairs = [(m, d) for m, d in pairs if m.get("status") == "blacklist"] or pairs[:n_results]
    elif is_recommend:
        # drop blacklist from recommendations
        pairs = [(m, d) for m, d in pairs if m.get("status") != "blacklist"]

    pairs = pairs[:n_results]
    if not pairs:
        return (
            "I looked through the log and did not find a close match for that request. "
            "Would you like to try different words?"
        )

    return "From the GustoPins log, here is what feels closest:\n\n" + _format_entries([m for m, _ in pairs])
