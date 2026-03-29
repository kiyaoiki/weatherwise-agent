# ⛅ WeatherWise — AI Agent with MCP + Google ADK

> An AI agent that uses **Model Context Protocol (MCP)** to connect to a live weather data source, retrieves structured meteorological data, and uses **Google ADK** (Agent Development Kit) + **Gemini 2.0 Flash** to generate human-friendly weather reports.

---

## 🏗️ Architecture

```
User Request
    │
    ▼
FastAPI Server (main.py)
    │
    ▼
Google ADK LlmAgent  ←──── Gemini 2.0 Flash (LLM)
    │
    │  MCP stdio transport
    ▼
Weather MCP Server (mcp_server/weather_mcp_server.py)
    │
    │  HTTP (httpx)
    ▼
Open-Meteo API  ──→  Geocoding API
                ──→  Forecast API (current + 5-day)
```

### Components
| Component | Role |
|-----------|------|
| **Google ADK** | Orchestrates the agent loop, manages tool calls |
| **MCP Server** | Exposes `get_weather` tool via stdio transport |
| **Open-Meteo** | Free, no-API-key weather data (global coverage) |
| **FastAPI** | REST API + web UI server |
| **Cloud Run** | Serverless Google Cloud deployment |

---

## 📁 Project Structure

```
weather-mcp-agent/
├── main.py                        # FastAPI server + API endpoints
├── agent/
│   └── weather_agent.py           # Google ADK agent definition
├── mcp_server/
│   └── weather_mcp_server.py      # MCP server exposing get_weather tool
├── static/
│   └── index.html                 # Frontend web UI
├── requirements.txt
├── Dockerfile
├── deploy.sh                      # One-command Cloud Run deploy
├── .env.example                   # Environment variable template
└── .gitignore
```

---

## 🖥️ Running Locally in VS Code

### Prerequisites
- Python 3.11 or 3.12
- VS Code with Python extension
- A **Google API Key** (for Gemini / ADK)

### Step 1 — Clone / open the project

Open the `weather-mcp-agent/` folder in VS Code:
```
File → Open Folder → weather-mcp-agent/
```

### Step 2 — Create a virtual environment

Open the VS Code terminal (`Ctrl+`` ` ``) and run:

```bash
python -m venv .venv
```

Activate it:
- **Windows:** `.venv\Scripts\activate`
- **Mac/Linux:** `source .venv/bin/activate`

VS Code should auto-detect the venv. If prompted, click **"Yes"** to use it as the workspace interpreter.

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your key:
```env
GOOGLE_API_KEY=AIza...your-key-here
```

Get a key at: https://aistudio.google.com/app/apikey (free tier works)

### Step 5 — Run the server

```bash
python main.py
```

Or use the VS Code Run button if you have a launch config. The server starts on **http://localhost:8080**

### Step 6 — Open the UI

Visit **http://localhost:8080** in your browser — you'll see the WeatherWise UI.

Or test via curl:
```bash
curl -X POST http://localhost:8080/api/weather \
  -H "Content-Type: application/json" \
  -d '{"city": "Bengaluru"}'
```

### VS Code launch.json (optional)

Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run WeatherWise",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/main.py",
      "envFile": "${workspaceFolder}/.env",
      "console": "integratedTerminal"
    }
  ]
}
```

---

## 🧪 Testing the MCP Server Directly

Run the agent from the CLI (bypasses FastAPI):
```bash
python agent/weather_agent.py "Tokyo"
python agent/weather_agent.py "London"
```

Test raw weather data (no LLM required):
```bash
curl http://localhost:8080/api/raw-weather/Mumbai
```

---

## ☁️ Deploying to Google Cloud Run

### Prerequisites
- Google Cloud account with a project
- `gcloud` CLI installed: https://cloud.google.com/sdk/docs/install
- Docker installed (for local builds) or Cloud Build enabled

### Step 1 — Set environment variables

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_API_KEY=your-google-api-key
export GOOGLE_CLOUD_REGION=us-central1   # or asia-south1 for India
```

### Step 2 — Authenticate

```bash
gcloud auth login
gcloud config set project $GOOGLE_CLOUD_PROJECT
```

### Step 3 — Deploy (one command)

```bash
chmod +x deploy.sh
./deploy.sh
```

This script automatically:
1. Enables required Google Cloud APIs
2. Builds the Docker image via Cloud Build
3. Pushes to Google Container Registry
4. Deploys to Cloud Run with your API key
5. Prints the live Cloud Run URL

### Step 4 — Test your deployment

```bash
# Replace with your actual Cloud Run URL
curl -X POST https://weatherwise-agent-xxxx-uc.a.run.app/api/weather \
  -H "Content-Type: application/json" \
  -d '{"city": "Bengaluru"}'
```

### Manual Cloud Run deploy (alternative)

```bash
# Build image
gcloud builds submit --tag gcr.io/$GOOGLE_CLOUD_PROJECT/weatherwise-agent .

# Deploy
gcloud run deploy weatherwise-agent \
  --image gcr.io/$GOOGLE_CLOUD_PROJECT/weatherwise-agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --set-env-vars "GOOGLE_API_KEY=$GOOGLE_API_KEY"
```

---

## 🔌 MCP Tool Reference

The MCP server exposes one tool:

### `get_weather`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `city`    | string | ✅ | City name (e.g. "Bengaluru", "Tokyo") |

**Returns:**
```json
{
  "location": { "city": "Bengaluru", "country": "India", "latitude": 12.97, "longitude": 77.59 },
  "current": {
    "temperature_c": 24.5,
    "feels_like_c": 25.1,
    "humidity_pct": 68,
    "wind_speed_kmh": 12.4,
    "wind_direction_deg": 270,
    "precipitation_mm": 0.0,
    "pressure_hpa": 1013.2,
    "uv_index": 6,
    "condition": "Partly cloudy"
  },
  "forecast_5_days": [...]
}
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/`      | Web UI |
| `GET`  | `/health` | Health check |
| `POST` | `/api/weather` | AI-generated weather report |
| `GET`  | `/api/raw-weather/{city}` | Raw weather data (no LLM) |

---

## 🛠️ How MCP Integration Works

1. **Agent startup**: `MCPToolset` launches the MCP server as a subprocess via stdio
2. **Tool discovery**: ADK queries the MCP server for available tools (`list_tools`)
3. **LLM decides**: Gemini sees the tool schema and decides to call `get_weather`
4. **Tool call**: ADK sends the call via MCP protocol → server fetches from Open-Meteo
5. **Response**: Structured JSON weather data flows back to the agent
6. **Report**: Gemini uses the data to craft a detailed, friendly weather report

---

## 📝 Submission Checklist

- [x] Implemented using Google ADK
- [x] Uses MCP to connect to one tool (Weather via Open-Meteo)
- [x] Retrieves structured data (current conditions + 5-day forecast)
- [x] Uses retrieved data to generate the final response
- [x] Deployable to Google Cloud Run
- [x] Runnable locally in VS Code

---

## 🔑 Getting a Free Google API Key

1. Go to https://aistudio.google.com/app/apikey
2. Click **"Create API Key"**
3. Copy the key and paste it into `.env`

The free tier includes generous Gemini 2.0 Flash usage.

---

## 📄 License

MIT — feel free to use and extend.
