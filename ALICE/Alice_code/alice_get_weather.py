import os
import json
import asyncio
import logging
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv
from livekit.agents import function_tool  # ✅ Correct decorator
from langchain.tools import tool

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


_SESSION: requests.Session | None = None


def _get_session() -> requests.Session:
    """Shared requests session with basic retry/backoff.

    Keeps transient network failures from producing noisy stacktraces.
    """
    global _SESSION
    if _SESSION is not None:
        return _SESSION

    session = requests.Session()
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "ALICE-Weather/1.0"})
    _SESSION = session
    return session


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _cache_path() -> str:
    return os.path.join(os.path.dirname(__file__), "alice_weather_cache.json")


def _write_cache(payload: dict) -> None:
    try:
        payload = dict(payload)
        payload["cached_at"] = _now_iso()
        with open(_cache_path(), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        # Cache failures should never break the tool.
        pass


def _read_cache() -> dict | None:
    try:
        with open(_cache_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _timeouts() -> tuple[float, float]:
    """(connect_timeout, read_timeout)"""
    connect_timeout = float(os.getenv("ALICE_WEATHER_CONNECT_TIMEOUT", "5"))
    read_timeout = float(os.getenv("ALICE_WEATHER_READ_TIMEOUT", "12"))
    return connect_timeout, read_timeout


def _should_skip_network() -> bool:
    return os.getenv("ALICE_DISABLE_WEATHER_NETWORK", "").strip().lower() in {"1", "true", "yes"}


def _sync_get_json(url: str, *, params: dict | None = None, headers: dict | None = None) -> dict:
    session = _get_session()
    merged_headers = {}
    if headers:
        merged_headers.update(headers)
    connect_timeout, read_timeout = _timeouts()
    resp = session.get(url, params=params, headers=merged_headers or None, timeout=(connect_timeout, read_timeout))
    resp.raise_for_status()
    return resp.json()

async def get_current_city():
    try:
        if _should_skip_network():
            return "Unknown"
        data = await asyncio.to_thread(_sync_get_json, "https://ipinfo.io")
        return data.get("city", "Unknown")
    except Exception as e:
        return "Unknown"

async def get_coordinates(city: str):
    """Get latitude and longitude for a city using OpenStreetMap Nominatim API"""
    try:
        if _should_skip_network():
            return None, None
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": city,
            "format": "json",
            "limit": 1
        }
        headers = {"User-Agent": "ALICE-Weather/1.0 (Nominatim)"}

        data = await asyncio.to_thread(_sync_get_json, url, params=params, headers=headers)
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
        return None, None
    except Exception as e:
        logger.warning(
            f"Coordinates fetch करते समय error: {e}",
            exc_info=logger.isEnabledFor(logging.DEBUG),
        )
        return None, None

@tool
async def get_weather(city: str = "") -> str:
    """
    Gives current weather information for a given city using Open-Meteo API (free, no API key required).

    Use this tool when the user asks about weather, rain, temperature, humidity, or wind.
    If no city is given, detect city automatically.

    Example prompts:
    - "आज का मौसम कैसा है?"
    - "Weather बताओ Bangalore का"
    - "क्या बारिश होगी मुंबई में?"
    """

    if not city:
        city = await get_current_city()

    # If networking is disabled (or environment is offline), use cached weather if available.
    if _should_skip_network():
        cached = _read_cache()
        if cached and cached.get("result"):
            return str(cached["result"])
        return "Weather अभी उपलब्ध नहीं है (network disabled)."

    logger.info(f"City के लिए weather fetch किया जा रहा है: {city}")

    # Get coordinates for the city
    lat, lon = await get_coordinates(city)
    if lat is None or lon is None:
        cached = _read_cache()
        if cached and cached.get("result"):
            cached_at = cached.get("cached_at")
            return f"Live weather नहीं मिल पाया; last known weather ({cached_at}):\n\n{cached['result']}"
        return f"Error: {city} के लिए coordinates नहीं मिले। कृपया city name चेक करें।"

    # Fetch weather data from Open-Meteo API
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "auto"
        }

        data = await asyncio.to_thread(_sync_get_json, url, params=params)
        current = data["current"]
        
        temperature = current["temperature_2m"]
        humidity = current["relative_humidity_2m"]
        wind_speed = current["wind_speed_10m"]
        weather_code = current["weather_code"]
        
        # Convert weather code to description
        weather_description = get_weather_description(weather_code)

        result = (f"Weather in {city}:\n"
                  f"- Condition: {weather_description}\n"
                  f"- Temperature: {temperature}°C\n"
                  f"- Humidity: {humidity}%\n"
                  f"- Wind Speed: {wind_speed} km/h")

        logger.info(f"Weather result: \n{result}")

        _write_cache(
            {
                "city": city,
                "latitude": lat,
                "longitude": lon,
                "provider": "open-meteo",
                "result": result,
            }
        )
        return result

    except requests.exceptions.RequestException as e:
        logger.warning(
            f"Weather fetch करते समय network issue आया: {e}",
            exc_info=logger.isEnabledFor(logging.DEBUG),
        )
        cached = _read_cache()
        if cached and cached.get("result"):
            cached_at = cached.get("cached_at")
            return f"Live weather नहीं मिल पाया; last known weather ({cached_at}):\n\n{cached['result']}"
        return "Weather अभी नहीं मिल पा रहा (internet/timeout). थोड़ी देर बाद try करें।"

    except Exception as e:
        logger.warning(
            f"Weather fetch करते समय unexpected issue आया: {e}",
            exc_info=logger.isEnabledFor(logging.DEBUG),
        )
        return "Weather fetch करते समय एक error आया"

def get_weather_description(code: int) -> str:
    """Convert Open-Meteo weather codes to descriptions"""
    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        56: "Light freezing drizzle", 57: "Dense freezing drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        66: "Light freezing rain", 67: "Heavy freezing rain",
        71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
        85: "Slight snow showers", 86: "Heavy snow showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
    }
    return weather_codes.get(code, f"Unknown weather (code: {code})")
    
