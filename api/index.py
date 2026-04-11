from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import google.generativeai as genai
import httpx
import os

app = FastAPI(title="Automated Meme Engine API")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
SHOTSTACK_KEY = os.getenv("SHOTSTACK_KEY")

class MemeRequest(BaseModel):
    topic: str
    vibe: str = "Gen-Z sarcastic"

# --- NEW: This tells Python to load your UI ---
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    try:
        # This goes up one folder from /api to find your index.html
        with open("index.html", "r") as f:
            return f.read()
    except Exception as e:
        return f"<h1>UI File Not Found</h1><p>Make sure index.html is exactly in your main GitHub folder.</p><p>Error: {str(e)}</p>"

# --- Your existing AI Engine Logic ---
@app.post("/api/generate")
async def generate_meme(req: MemeRequest):
    if not GEMINI_KEY or not SHOTSTACK_KEY:
        raise HTTPException(status_code=500, detail="Missing API Keys.")

    try:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-1.5-pro')
        prompt = f"Write a short, viral, 10-word {req.vibe} meme caption about {req.topic}. Output strictly the caption."
        response = model.generate_content(prompt)
        caption = response.text.strip().replace('"', '')
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI Error: {str(e)}")

    shotstack_url = "https://api.shotstack.io/edit/v1/render"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": SHOTSTACK_KEY
    }
    
    payload = {
        "timeline": {
            "background": "#000000",
            "tracks": [{
                "clips": [{
                    "asset": {
                        "type": "title",
                        "text": caption,
                        "style": "future",
                        "size": "medium"
                    },
                    "start": 0,
                    "length": 5
                }]
            }]
        },
        "output": { "format": "mp4", "resolution": "sd" }
    }

    try:
        async with httpx.AsyncClient() as client:
            render_response = await client.post(shotstack_url, json=payload, headers=headers)
            render_response.raise_for_status()
            shotstack_data = render_response.json()
            
            return {
                "status": "success",
                "caption": caption,
                "render_id": shotstack_data.get("response", {}).get("id")
            }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Video Render Error: {str(e)}")
