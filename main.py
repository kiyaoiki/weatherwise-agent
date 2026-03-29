"""FastAPI Web Server for WeatherWise Agent"""

import os, sys, time, httpx
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
import os
_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here))
os.chdir(str(_here))

class WeatherRequest(BaseModel):
    city: str

class WeatherResponse(BaseModel):
    city: str
    report: str
    duration_ms: float

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 WeatherWise Agent starting up...")
    yield

app = FastAPI(title="WeatherWise AI Agent", version="1.0.0", lifespan=lifespan)

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "WeatherWise AI Agent", "version": "1.0.0"}

@app.get("/api/raw-weather/{city}")
async def raw_weather(city: str):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            geo = await client.get("https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "en", "format": "json"})
            geo.raise_for_status()
            geo_data = geo.json()
            if not geo_data.get("results"):
                raise HTTPException(status_code=404, detail=f"City '{city}' not found")
            r = geo_data["results"][0]
            lat, lon = r["latitude"], r["longitude"]
            weather = await client.get("https://api.open-meteo.com/v1/forecast",
                params={"latitude": lat, "longitude": lon,
                    "current": ["temperature_2m","relative_humidity_2m","apparent_temperature",
                                "precipitation","weathercode","windspeed_10m","uv_index"],
                    "daily": ["temperature_2m_max","temperature_2m_min","weathercode","precipitation_sum"],
                    "forecast_days": 5, "timezone": "auto"})
            weather.raise_for_status()
            return {"location": {"city": r["name"], "country": r.get("country",""), "lat": lat, "lon": lon},
                    "weather": weather.json()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/weather", response_model=WeatherResponse)
async def get_weather_report(req: WeatherRequest):
    city = req.city.strip()
    if not city:
        raise HTTPException(status_code=400, detail="city is required")
    start = time.time()
    try:
        from agent.weather_agent import run_agent
        report = await run_agent(city)
        duration = (time.time() - start) * 1000
        return WeatherResponse(city=city, report=report, duration_ms=round(duration, 1))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def index():
    for p in [Path(__file__).parent / "static" / "index.html", Path.cwd() / "static" / "index.html"]:
        if p.exists():
            return HTMLResponse(content=p.read_text(encoding="utf-8"))
    return HTMLResponse(content=get_inline_html())

def get_inline_html():
    return open(Path(__file__).parent / "static" / "index.html", encoding="utf-8").read() if (Path(__file__).parent / "static" / "index.html").exists() else FALLBACK_HTML

FALLBACK_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>WeatherWise</title>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Mono:wght@400&display=swap" rel="stylesheet">
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    :root{--sky:#0a0f1e;--card:rgba(13,27,62,0.8);--border:rgba(77,217,255,0.15);--gold:#f5c842;--cyan:#4dd9ff;--white:#f0f4ff;--muted:#7b8db0}
    body{background:var(--sky);color:var(--white);font-family:'DM Mono',monospace;min-height:100vh}
    .bg{position:fixed;inset:0;z-index:0;background:radial-gradient(ellipse at 20% 0%,#1a3a6b,transparent 60%),radial-gradient(ellipse at 80% 10%,#0d2a55,transparent 50%),#0a0f1e}
    .wrap{position:relative;z-index:1;max-width:820px;margin:0 auto;padding:48px 24px 80px}
    header{text-align:center;margin-bottom:48px}
    .logo{display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:10px}
    .icon{font-size:2.6rem;animation:float 4s ease-in-out infinite}
    @keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
    h1{font-family:'Syne',sans-serif;font-size:clamp(1.8rem,5vw,3rem);font-weight:800;background:linear-gradient(135deg,var(--gold),var(--cyan));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
    .sub{color:var(--muted);font-size:.78rem;letter-spacing:.12em;text-transform:uppercase;margin-top:6px}
    .badge{display:inline-flex;align-items:center;gap:6px;margin-top:14px;padding:5px 14px;border:1px solid var(--border);border-radius:999px;font-size:.7rem;color:var(--cyan)}
    .dot{width:6px;height:6px;border-radius:50%;background:var(--cyan);animation:pulse 2s infinite}
    @keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
    .card{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:28px;backdrop-filter:blur(20px);margin-bottom:24px}
    .lbl{display:block;font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}
    .row{display:flex;gap:10px}
    input{flex:1;background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:12px;color:var(--white);font-family:'DM Mono',monospace;font-size:.95rem;padding:13px 18px;outline:none;transition:.2s}
    input:focus{border-color:var(--cyan);box-shadow:0 0 0 3px rgba(77,217,255,.1)}
    input::placeholder{color:var(--muted)}
    .btn{background:linear-gradient(135deg,var(--gold),#e8a820);border:none;border-radius:12px;color:#0a0f1e;cursor:pointer;font-family:'Syne',sans-serif;font-weight:700;font-size:.88rem;padding:13px 26px;transition:.15s;white-space:nowrap}
    .btn:hover{transform:translateY(-1px);box-shadow:0 6px 20px rgba(245,200,66,.3)}
    .btn:disabled{opacity:.5;cursor:not-allowed;transform:none}
    .chips{margin-top:14px;display:flex;flex-wrap:wrap;gap:8px}
    .chip{background:transparent;border:1px solid var(--border);border-radius:999px;color:var(--muted);cursor:pointer;font-family:'DM Mono',monospace;font-size:.72rem;padding:5px 13px;transition:.15s}
    .chip:hover{border-color:var(--gold);color:var(--gold)}
    .loading{display:none;text-align:center;padding:36px;color:var(--muted)}
    .loading.on{display:block}
    .spin{width:40px;height:40px;border:3px solid var(--border);border-top-color:var(--cyan);border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 14px}
    @keyframes spin{to{transform:rotate(360deg)}}
    .step{opacity:0;transition:opacity .4s;font-size:.76rem;line-height:2.2}
    .step.on{opacity:1}
    .result{display:none;background:var(--card);border:1px solid var(--border);border-radius:20px;backdrop-filter:blur(20px);overflow:hidden;animation:up .4s ease}
    .result.on{display:block}
    @keyframes up{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
    .rh{background:linear-gradient(135deg,rgba(245,200,66,.08),rgba(77,217,255,.06));border-bottom:1px solid var(--border);padding:18px 26px;display:flex;align-items:center;justify-content:space-between}
    .rcity{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:var(--gold)}
    .rmeta{font-size:.7rem;color:var(--muted)}
    .rbody{padding:26px;white-space:pre-wrap;line-height:1.9;font-size:.86rem;color:#c8d6f5}
    .err{display:none;background:rgba(255,80,80,.08);border:1px solid rgba(255,80,80,.25);border-radius:12px;padding:14px 18px;color:#ff8080;font-size:.8rem;margin-bottom:16px}
    .err.on{display:block}
    .arch{margin-top:44px}
    .at{font-size:.7rem;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);margin-bottom:18px;font-family:'Syne',sans-serif}
    .ag{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
    .ac{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:18px;transition:.2s}
    .ac:hover{border-color:rgba(77,217,255,.3)}
    .ai{font-size:1.5rem;margin-bottom:8px}
    .an{font-family:'Syne',sans-serif;font-size:.8rem;font-weight:700;color:var(--white);margin-bottom:3px}
    .ad{font-size:.71rem;color:var(--muted);line-height:1.55}
    @media(max-width:500px){.row{flex-direction:column}.btn{width:100%}}
  </style>
</head>
<body>
<div class="bg"></div>
<div class="wrap">
  <header>
    <div class="logo"><span class="icon">&#9925;</span><h1>WeatherWise</h1></div>
    <p class="sub">AI Weather Agent &middot; MCP + ADK + Open-Meteo</p>
    <div class="badge"><span class="dot"></span>Live Data &middot; Free &middot; No Extra API Key</div>
  </header>
  <div class="card">
    <span class="lbl">Enter a city</span>
    <div class="row">
      <input id="inp" type="text" placeholder="e.g. Bengaluru, Tokyo, Paris..." autocomplete="off"/>
      <button class="btn" id="btn" onclick="go()">Get Report &#8594;</button>
    </div>
    <div class="chips">
      <button class="chip" onclick="q('Bengaluru')">&#127470;&#127475; Bengaluru</button>
      <button class="chip" onclick="q('Mumbai')">&#127470;&#127475; Mumbai</button>
      <button class="chip" onclick="q('London')">&#127468;&#127463; London</button>
      <button class="chip" onclick="q('Tokyo')">&#127471;&#127477; Tokyo</button>
      <button class="chip" onclick="q('New York')">&#127482;&#127480; New York</button>
      <button class="chip" onclick="q('Sydney')">&#127462;&#127482; Sydney</button>
      <button class="chip" onclick="q('Dubai')">&#127462;&#127466; Dubai</button>
    </div>
  </div>
  <div class="err" id="err"></div>
  <div class="loading" id="load">
    <div class="spin"></div>
    <div class="step" id="s1">&#128279; Connecting to MCP server...</div>
    <div class="step" id="s2">&#127757; Geocoding city location...</div>
    <div class="step" id="s3">&#127777; Fetching live weather data...</div>
    <div class="step" id="s4">&#129302; ADK agent generating report...</div>
  </div>
  <div class="result" id="res">
    <div class="rh"><span class="rcity" id="rcity"></span><span class="rmeta" id="rmeta"></span></div>
    <div class="rbody" id="rbody"></div>
  </div>
  <div class="arch">
    <p class="at">How it works</p>
    <div class="ag">
      <div class="ac"><div class="ai">&#129302;</div><div class="an">Google ADK</div><div class="ad">Orchestrates LLM reasoning and tool-use loop</div></div>
      <div class="ac"><div class="ai">&#128268;</div><div class="an">MCP Protocol</div><div class="ad">Connects the agent to weather tool via stdio</div></div>
      <div class="ac"><div class="ai">&#127750;</div><div class="an">Open-Meteo</div><div class="ad">Free global weather API, no key needed</div></div>
      <div class="ac"><div class="ai">&#9729;</div><div class="an">Cloud Run</div><div class="ad">Serverless deployment with auto-scaling</div></div>
    </div>
  </div>
</div>
<script>
  const inp=document.getElementById('inp'),btn=document.getElementById('btn');
  const load=document.getElementById('load'),res=document.getElementById('res'),err=document.getElementById('err');
  inp.addEventListener('keydown',e=>{if(e.key==='Enter')go()});
  function q(c){inp.value=c;go()}
  function showLoad(){
    load.classList.add('on');res.classList.remove('on');err.classList.remove('on');
    ['s1','s2','s3','s4'].forEach((id,i)=>{
      const el=document.getElementById(id);el.classList.remove('on');
      setTimeout(()=>el.classList.add('on'),i*900);
    });
  }
  async function go(){
    const city=inp.value.trim();if(!city){inp.focus();return}
    btn.disabled=true;showLoad();
    try{
      const r=await fetch('/api/weather',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({city})});
      const d=await r.json();
      if(!r.ok)throw new Error(d.detail||'Server error');
      load.classList.remove('on');
      document.getElementById('rcity').textContent='&#128205; '+d.city;
      document.getElementById('rmeta').textContent='Generated in '+d.duration_ms.toFixed(0)+'ms';
      document.getElementById('rbody').textContent=d.report;
      res.classList.add('on');res.scrollIntoView({behavior:'smooth',block:'start'});
    }catch(e){
      load.classList.remove('on');err.textContent='Warning: '+e.message;err.classList.add('on');
    }finally{btn.disabled=false}
  }
</script>
</body>
</html>"""

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)