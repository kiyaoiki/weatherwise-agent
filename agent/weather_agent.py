import asyncio, sys, json, os, httpx
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

WMO_CODES = {
    0:"Clear sky",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",
    45:"Fog",48:"Rime fog",51:"Light drizzle",53:"Moderate drizzle",55:"Dense drizzle",
    61:"Slight rain",63:"Moderate rain",65:"Heavy rain",71:"Slight snow",73:"Moderate snow",
    75:"Heavy snow",80:"Slight showers",81:"Moderate showers",82:"Violent showers",
    95:"Thunderstorm",96:"Thunderstorm with hail",
}

async def get_weather(city: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        geo = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"}
        )
        geo.raise_for_status()
        geo_data = geo.json()
        if not geo_data.get("results"):
            return {"error": f"City not found: {city}"}
        r = geo_data["results"][0]
        lat, lon = r["latitude"], r["longitude"]
        weather = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lon,
                "current": ["temperature_2m","relative_humidity_2m","apparent_temperature",
                            "precipitation","weathercode","windspeed_10m","pressure_msl","uv_index"],
                "daily": ["temperature_2m_max","temperature_2m_min","precipitation_sum","weathercode"],
                "forecast_days": 5, "timezone": "auto",
            }
        )
        weather.raise_for_status()
        w = weather.json()

    current = w["current"]
    daily = w["daily"]
    forecast = [
        {"date": daily["time"][i], "max_temp_c": daily["temperature_2m_max"][i],
         "min_temp_c": daily["temperature_2m_min"][i], "precipitation_mm": daily["precipitation_sum"][i],
         "condition": WMO_CODES.get(daily["weathercode"][i], "Unknown")}
        for i in range(len(daily["time"]))
    ]
    return {
        "location": {"city": r["name"], "country": r.get("country",""), "latitude": lat, "longitude": lon},
        "current": {
            "temperature_c": current["temperature_2m"], "feels_like_c": current["apparent_temperature"],
            "humidity_pct": current["relative_humidity_2m"], "wind_speed_kmh": current["windspeed_10m"],
            "precipitation_mm": current["precipitation"], "pressure_hpa": current["pressure_msl"],
            "uv_index": current.get("uv_index"),
            "condition": WMO_CODES.get(current.get("weathercode", 0), "Unknown"),
        },
        "forecast_5_days": forecast,
        "timezone": w.get("timezone", "UTC"),
    }


async def run_agent(city: str) -> str:
    # Step 1: fetch live weather via MCP-style tool call
    weather_data = await get_weather(city)
    if "error" in weather_data:
        return f"Sorry, could not find weather data for {city}."

    # Step 2: send to Groq LLM
    system_prompt = """You are WeatherWise, an expert meteorological AI assistant.
You will receive structured weather JSON and must generate a rich friendly weather report including:
- A warm greeting with city name and country
- Current conditions: temperature, feels like, humidity, wind, UV index, pressure, sky description
- A practical recommendation (umbrella? sunscreen? jacket?)
- A clear 5-day forecast with emojis for each day
- A closing weather tip
Use weather emojis generously. Format numbers cleanly e.g. 23C, 65%, 12 km/h."""

    user_prompt = f"Generate a detailed weather report for {city} using this live data:\n\n{json.dumps(weather_data, indent=2)}"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 1000,
            }
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]


if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else "Bengaluru"
    print(asyncio.run(run_agent(city)))
