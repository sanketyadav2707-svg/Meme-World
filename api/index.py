from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import httpx
import os

# Initialize the API
app = FastAPI(title="Automated Meme Engine API")

# Securely load environment variables
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
SHOTSTACK_KEY = os.getenv("SHOTSTACK_KEY")

# Data Validation: Ensures the user always sends the correct data format
class MemeRequest(BaseModel):
    topic: str
    vibe: str = "Gen-Z sarcastic"

@app.post("/api/generate")
async def generate_meme(req: MemeRequest):
    # Safety Check: Verify API keys are present
    if not GEMINI_KEY or not SHOTSTACK_KEY:
        raise HTTPException(status_code=500, detail="Server configuration error: Missing API Keys.")

    # PHASE 1: The Brain (Generate Caption)
    try:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Strict prompt engineering for accurate output
        prompt = f"Write a short, highly viral, 10-word {req.vibe} meme caption about {req.topic}. Output strictly the caption, nothing else."
        
        response = model.generate_content(prompt)
        caption = response.text.strip().replace('"', '')
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to generate text from AI: {str(e)}")

    # PHASE 2: The Muscle (Render Video)
    shotstack_url = "https://api.shotstack.io/edit/v1/render"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": SHOTSTACK_KEY
    }
    
    # The JSON blueprint for the video
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
        "output": {
            "format": "mp4",
            "resolution": "sd"
        }
    }

    # Asynchronous fetching (The secret to making it very fast)
    try:
        async with httpx.AsyncClient() as client:
            render_response = await client.post(shotstack_url, json=payload, headers=headers)
            render_response.raise_for_status() # Automatically catches HTTP errors
            shotstack_data = render_response.json()
            
            return {
                "status": "success",
                "topic": req.topic,
                "caption": caption,
                "render_id": shotstack_data.get("response", {}).get("id"),
                "message": "Video rendering started successfully."
            }
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to communicate with Video Rendering API: {str(e)}")
