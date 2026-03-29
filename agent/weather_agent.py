import asyncio, sys, json, os, httpx
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

async def get_weather(city: str) -> dict:
    """Fetch weather from wttr.in - no rate limits, no API key needed."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"https://wttr.in/{city}",
            params={"format": "j1"},
            headers={"User-Agent": "WeatherWise-Agent/1.0"}
        )
        response.raise_for_status()
        data = response.json()

        current = data["current_condition"][0]
        area = data["nearest_area"][0]
        city_name = area["areaName"][0]["value"]
        country = area["country"][0]["value"]

        forecast = []
        for day in data["weather"]:
            forecast.append({
                "date": day["date"],
                "max_temp_c": day["maxtempC"],
                "min_temp_c": day["mintempC"],
                "avg_temp_c": day["avgtempC"],
                "precipitation_mm": day["hourly"][4]["precipMM"],
                "condition": day["hourly"][4]["weatherDesc"][0]["value"],
                "sunrise": day["astronomy"][0]["sunrise"],
                "sunset": day["astronomy"][0]["sunset"],
            })

        return {
            "location": {"city": city_name, "country": country},
            "current": {
                "temperature_c": current["temp_C"],
                "feels_like_c": current["FeelsLikeC"],
                "humidity_pct": current["humidity"],
                "wind_speed_kmh": current["windspeedKmph"],
                "wind_direction": current["winddir16Point"],
                "visibility_km": current["visibility"],
                "uv_index": current["uvIndex"],
                "pressure_mb": current["pressure"],
                "condition": current["weatherDesc"][0]["value"],
            },
            "forecast_3_days": forecast,
        }


async def run_agent(city: str) -> str:
    weather_data = await get_weather(city)
    if "error" in weather_data:
        return f"Sorry, could not fetch weather for {city}: {weather_data['error']}"

    system_prompt = """You are WeatherWise, an expert meteorological AI assistant.
You will receive structured weather JSON and must generate a rich friendly weather report including:
- A warm greeting with city name and country
- Current conditions: temperature, feels like, humidity, wind, UV index, pressure, sky description
- A practical recommendation (umbrella? sunscreen? jacket?)
- A clear 3-day forecast with emojis for each day
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
