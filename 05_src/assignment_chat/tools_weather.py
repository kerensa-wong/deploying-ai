"""Service 1a – Weather via Open-Meteo (no API key). Output is always natural language."""

from __future__ import annotations

import requests

CITY_COORDS = {
    "toronto": (43.6532, -79.3832),
    "vancouver": (49.2827, -123.1207),
    "montreal": (45.5017, -73.5673),
    "ottawa": (45.4215, -75.6972),
    "calgary": (51.0447, -114.0719),
    "new york": (40.7128, -74.0060),
    "london": (51.5074, -0.1278),
    "paris": (48.8566, 2.3522),
    "tokyo": (35.6762, 139.6503),
    "sydney": (-33.8688, 151.2093),
}

WMO = {
    0: "clear",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "rime fog",
    51: "light drizzle",
    53: "drizzle",
    55: "dense drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "slight snow",
    73: "moderate snow",
    75: "heavy snow",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
}


def get_weather(city: str = "Toronto") -> str:
    city_key = (city or "Toronto").strip().lower()
    if city_key in CITY_COORDS:
        lat, lon = CITY_COORDS[city_key]
        resolved = city.strip().title()
    else:
        try:
            geo = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "en", "format": "json"},
                timeout=8,
            )
            geo.raise_for_status()
            results = geo.json().get("results") or []
            if not results:
                return f"I could not find coordinates for “{city}”. Could you try a more specific name?"
            lat, lon = results[0]["latitude"], results[0]["longitude"]
            resolved = results[0].get("name", city)
        except Exception as e:
            return f"I had trouble looking up “{city}” ({e})."

    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "auto",
                "forecast_days": 2,
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return f"I could not reach the weather service ({e})."

    cur = data.get("current", {})
    daily = data.get("daily", {})
    condition = WMO.get(cur.get("weather_code", 0), "variable conditions")
    summary = (
        f"Right now in {resolved} it is about {cur.get('temperature_2m')}°C, {condition}, "
        f"with humidity around {cur.get('relative_humidity_2m')}% and wind near {cur.get('wind_speed_10m')} km/h."
    )
    if daily.get("temperature_2m_max") and len(daily["temperature_2m_max"]) > 1:
        precip = daily.get("precipitation_probability_max", [None, None])[1]
        summary += (
            f" Tomorrow looks like a high of {daily['temperature_2m_max'][1]}°C "
            f"and a low of {daily['temperature_2m_min'][1]}°C"
        )
        if precip is not None:
            summary += f", with roughly {precip}% chance of precipitation"
        summary += "."
    return summary
