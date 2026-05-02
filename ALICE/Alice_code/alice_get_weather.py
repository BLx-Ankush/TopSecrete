import os
import requests
import logging
from dotenv import load_dotenv
from livekit.agents import function_tool  # ✅ Correct decorator
from langchain.tools import tool

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_current_city():
    try:
        response = requests.get("https://ipinfo.io", timeout=5)
        data = response.json()
        return data.get("city", "Unknown")
    except Exception as e:
        return "Unknown"

async def get_coordinates(city: str):
    """Get latitude and longitude for a city using OpenStreetMap Nominatim API"""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": city,
            "format": "json",
            "limit": 1
        }
        headers = {"User-Agent": "Alice-Weather-App/1.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
        return None, None
    except Exception as e:
        logger.error(f"Coordinates fetch करते समय error: {e}")
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

    logger.info(f"City के लिए weather fetch किया जा रहा है: {city}")

    # Get coordinates for the city
    lat, lon = await get_coordinates(city)
    if lat is None or lon is None:
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

        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            logger.error(f"Open-Meteo API में error आया: {response.status_code} - {response.text}")
            return f"Error: {city} के लिए weather fetch नहीं कर पाए।"

        data = response.json()
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
        return result

    except Exception as e:
        logger.exception(f"Weather fetch करते समय exception आया: {e}")
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
    
