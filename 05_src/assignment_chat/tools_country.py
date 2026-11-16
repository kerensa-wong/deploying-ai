"""Service 1b – Country info via REST Countries (no API key). Output is always natural language."""

from __future__ import annotations

import requests


def get_country_info(country: str) -> str:
    try:
        r = requests.get(
            f"https://restcountries.com/v3.1/name/{country}",
            params={"fields": "name,capital,region,subregion,languages,currencies,population"},
            timeout=10,
        )
        if r.status_code == 404:
            return f"I could not find a country matching “{country}”. Check the spelling?"
        r.raise_for_status()
        data = r.json()
        if not data:
            return f"No information found for “{country}”."
        c = data[0]
    except Exception as e:
        return f"I had trouble reaching the country service ({e})."

    name = c.get("name", {}).get("common", country)
    official = c.get("name", {}).get("official", "")
    capital = (c.get("capital") or ["unknown"])[0]
    region = c.get("region", "")
    subregion = c.get("subregion", "")
    population = c.get("population")
    languages = ", ".join((c.get("languages") or {}).values()) or "not listed"
    currencies = c.get("currencies") or {}
    curr_str = ", ".join(
        f"{v.get('name', k)} ({v.get('symbol', '')})" for k, v in currencies.items()
    ) or "not listed"

    parts = [name]
    if official and official != name:
        parts.append(f"(officially {official})")
    parts.append(f"is in {region}")
    if subregion:
        parts.append(f"({subregion})")
    parts.append(f". Its capital is {capital}.")
    if population:
        parts.append(f" The population is roughly {population:,}.")
    parts.append(f" Languages: {languages}. Currency: {curr_str}.")
    return "".join(parts)
