import asyncio, json, httpx
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp import types

app = Server("weather-mcp-server")

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES = {
    0:"Clear sky",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",
    45:"Fog",48:"Rime fog",51:"Light drizzle",53:"Moderate drizzle",55:"Dense drizzle",
    61:"Slight rain",63:"Moderate rain",65:"Heavy rain",71:"Slight snow",73:"Moderate snow",
    75:"Heavy snow",80:"Slight showers",81:"Moderate showers",82:"Violent showers",
    95:"Thunderstorm",96:"Thunderstorm with hail",
}

async def geocode(city):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(GEOCODING_URL, params={"name":city,"count":1,"language":"en","format":"json"})
        r.raise_for_status()
        data = r.json()
        if not data.get("results"):
            raise ValueError(f"City not found: {city}")
        res = data["results"][0]
        return {"lat":res["latitude"],"lon":res["longitude"],"name":res["name"],"country":res.get("country","")}

async def fetch_weather(lat, lon):
    params = {
        "latitude":lat,"longitude":lon,
        "current":["temperature_2m","relative_humidity_2m","apparent_temperature",
                   "precipitation","weathercode","windspeed_10m","winddirection_10m","pressure_msl","uv_index"],
        "daily":["temperature_2m_max","temperature_2m_min","precipitation_sum","weathercode"],
        "forecast_days":5,"timezone":"auto",
    }
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(WEATHER_URL, params=params)
        r.raise_for_status()
        return r.json()

@app.list_tools()
async def list_tools():
    return [types.Tool(
        name="get_weather",
        description="Fetch current weather and 5-day forecast for any city.",
        inputSchema={"type":"object","properties":{"city":{"type":"string","description":"City name"}},"required":["city"]},
    )]

@app.call_tool()
async def call_tool(name, arguments):
    if name != "get_weather":
        raise ValueError(f"Unknown tool: {name}")
    city = arguments.get("city","").strip()
    if not city:
        raise ValueError("city is required")
    location = await geocode(city)
    weather = await fetch_weather(location["lat"], location["lon"])
    current = weather["current"]
    daily = weather["daily"]
    forecast = [{"date":daily["time"][i],"max_temp_c":daily["temperature_2m_max"][i],
                 "min_temp_c":daily["temperature_2m_min"][i],"precipitation_mm":daily["precipitation_sum"][i],
                 "condition":WMO_CODES.get(daily["weathercode"][i],"Unknown")} for i in range(len(daily["time"]))]
    result = {
        "location":{"city":location["name"],"country":location["country"],"latitude":location["lat"],"longitude":location["lon"]},
        "current":{"temperature_c":current["temperature_2m"],"feels_like_c":current["apparent_temperature"],
                   "humidity_pct":current["relative_humidity_2m"],"wind_speed_kmh":current["windspeed_10m"],
                   "precipitation_mm":current["precipitation"],"pressure_hpa":current["pressure_msl"],
                   "uv_index":current.get("uv_index"),"condition":WMO_CODES.get(current.get("weathercode",0),"Unknown")},
        "forecast_5_days":forecast,"timezone":weather.get("timezone","UTC"),
    }
    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream,
            InitializationOptions(server_name="weather-mcp-server", server_version="1.0.0",
                capabilities=app.get_capabilities(notification_options=None, experimental_capabilities={})))

if __name__ == "__main__":
    asyncio.run(main())
