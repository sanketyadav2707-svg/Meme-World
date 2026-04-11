from flask import Flask, request, jsonify
import anthropic
import replicate
import os
import json
import re
import requests

app = Flask(__name__)

# Core AI Keys
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
REPLICATE_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "")

# Expansion APIs (Scraping, Stock, Publishing)
APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN", "")
PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "")
AYRSHARE_KEY = os.environ.get("AYRSHARE_API_KEY", "")

# ── CORS helper ───────────────────────────────────────────────────────────────
def cors(resp, status=200):
    r = jsonify(resp)
    r.status_code = status
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return r

@app.route("/api/generate", methods=["OPTIONS"])
def options():
    return cors({}, 200)

# ── Main endpoint ─────────────────────────────────────────────────────────────
@app.route("/api/generate", methods=["POST"])
def generate():
    try:
        body = request.get_json(force=True)
        prompt = (body.get("prompt") or "").strip()
        gen_type = body.get("genType", "auto")   # auto | image | video | chat
        quality = body.get("quality", "high")     # standard | high | ultra
        style = body.get("style", "funny")        # funny | dank | wholesome | dark | viral
        history = body.get("history", [])

        if not prompt:
            return cors({"error": "Empty prompt"}, 400)

        if not ANTHROPIC_KEY:
            return cors({"error": "ANTHROPIC_API_KEY not set in Vercel environment variables."}, 500)

        # ── Expansion 1: Apify (The Scraper) ──────────────────────────────────
        # If the user asks for something trending, we fetch real data first
        if "trending" in prompt.lower() or "latest" in prompt.lower():
            if APIFY_TOKEN:
                try:
                    # Example: Hitting a generic Apify Actor to get trending topics
                    # Replace the URL with your specific Apify Actor API endpoint
                    apify_url = f"https://api.apify.com/v2/acts/some-actor-id/runs/last/dataset/items?token={APIFY_TOKEN}"
                    apify_resp = requests.get(apify_url)
                    if apify_resp.status_code == 200:
                        trending_data = apify_resp.json()
                        if trending_data:
                            # Append the live data to the prompt for Claude
                            prompt = f"{prompt}. Context from internet: {str(trending_data[0])}"
                except Exception as e:
                    print(f"Apify fetch failed, continuing with standard prompt: {e}")

        # ── Step 1: Ask Claude to analyse the prompt ──────────────────────────
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

        system_prompt = """You are MemeForge AI — the world's most creative meme generator.
Your job:
1. Understand what the user wants.
2. Decide if they want: an IMAGE meme, a VIDEO meme, or just a text CHAT reply.
3. If it's a meme request, craft the PERFECT creative prompt for image/video generation.

Rules:
- For image memes: describe the exact meme format, top text, bottom text, visual scene, characters, style.
- For video memes: describe the video scene, characters, actions, audio cues, on-screen text.
- If it's just a question or chat, answer helpfully.
- Never generate inappropriate, violent, or NSFW content.
- Style guide: funny=humorous and relatable, dank=surreal/absurdist, wholesome=warm/positive, dark=edgy satire, viral=trending formats.

Respond ONLY in this JSON format (no markdown, no backticks):
{
  "type": "image" | "video" | "chat",
  "text": "Your conversational reply to the user",
  "image_prompt": "Detailed prompt for image generation (if type=image)",
  "video_prompt": "Detailed prompt for video generation (if type=video)",
  "title": "Short title for the meme"
}"""

        # Build conversation history for context
        messages = []
        for m in history[-8:]:
            if m.get("role") in ("user", "assistant") and m.get("content"):
                messages.append({"role": m["role"], "content": m["content"]})

        # Make sure last user message is the current prompt
        if not messages or messages[-1]["role"] != "user":
            messages.append({"role": "user", "content": f"[Style: {style}] {prompt}"})
        else:
            messages[-1]["content"] = f"[Style: {style}] {prompt}"

        ai_resp = client.messages.create(
            model="claude-3-opus-20240229", # Updated to a valid Claude 3 model string
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )

        raw = ai_resp.content[0].text.strip()

        # Parse JSON from Claude
        try:
            # Remove any accidental markdown fences
            raw = re.sub(r"```json|```", "", raw).strip()
            parsed = json.loads(raw)
        except Exception:
            # Fallback: treat as chat
            parsed = {"type": "chat", "text": raw, "title": "Response"}

        result_type = parsed.get("type", "chat")
        reply_text = parsed.get("text", "")
        title = parsed.get("title", "Generated Meme")

        # Override type if user explicitly chose
        if gen_type in ("image", "video", "chat"):
            result_type = gen_type

        # ── Step 2: Generate media if needed ─────────────────────────────────
        media_url = None

        if result_type == "image":
            if not REPLICATE_TOKEN:
                return cors({"error": "REPLICATE_API_TOKEN not set. Add it in Vercel environment variables."}, 500)

            img_prompt = parsed.get("image_prompt") or prompt
            img_prompt = _quality_suffix(img_prompt, quality, style)

            os.environ["REPLICATE_API_TOKEN"] = REPLICATE_TOKEN

            # Use FLUX Schnell (fastest, free tier friendly)
            try:
                output = replicate.run(
                    "black-forest-labs/flux-schnell",
                    input={
                        "prompt": img_prompt,
                        "num_outputs": 1,
                        "aspect_ratio": "1:1",
                        "output_format": "webp",
                        "output_quality": 90 if quality == "ultra" else 80,
                        "go_fast": quality != "ultra",
                    }
                )
                media_url = str(output[0]) if isinstance(output, list) else str(output)
            except Exception as e:
                # Fallback to SDXL
                try:
                    output = replicate.run(
                        "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                        input={"prompt": img_prompt, "width": 1024, "height": 1024}
                    )
                    media_url = str(output[0]) if isinstance(output, list) else str(output)
                except Exception as e2:
                    return cors({"error": f"Image generation failed: {str(e2)}"}, 500)

        elif result_type == "video":
            if not REPLICATE_TOKEN:
                return cors({"error": "REPLICATE_API_TOKEN not set."}, 500)

            vid_prompt = parsed.get("video_prompt") or prompt
            vid_prompt = _quality_suffix(vid_prompt, quality, style)

            os.environ["REPLICATE_API_TOKEN"] = REPLICATE_TOKEN

            try:
                # Use Wan 2.1 (open source, on Replicate)
                output = replicate.run(
                    "wavespeedai/wan-2.1-t2v-480p",
                    input={
                        "prompt": vid_prompt,
                        "num_frames": 81,
                        "fps": 16,
                    }
                )
                media_url = str(output) if not isinstance(output, list) else str(output[0])
            except Exception as e:
                # ── Expansion 2: Pexels Fallback ────────────────────────────────
                # If AI Video generation fails, we instantly grab a stock video instead of crashing
                if PEXELS_KEY:
                    try:
                        pexels_url = f"https://api.pexels.com/videos/search?query={title}&per_page=1"
                        px_resp = requests.get(pexels_url, headers={"Authorization": PEXELS_KEY})
                        if px_resp.status_code == 200 and px_resp.json().get('videos'):
                            media_url = px_resp.json()['videos'][0]['video_files'][0]['link']
                            reply_text += " (Note: Used high-quality stock footage due to AI render limits.)"
                        else:
                            raise Exception("No Pexels fallback found.")
                    except Exception as px_e:
                        return cors({"error": f"Video generation and fallback failed: {str(e)}"}, 500)
                else:
                    return cors({"error": f"Video generation failed: {str(e)}"}, 500)

        # ── Expansion 3: Ayrshare (The Publisher) ─────────────────────────────
        # If we successfully created a media URL, post it to social media
        posted_to_socials = False
        if media_url and AYRSHARE_KEY:
            try:
                ayrshare_endpoint = "https://app.ayrshare.com/api/post"
                payload = {
                    "post": f"{title}\n\n#meme #{style}",
                    "platforms": ["instagram", "tiktok", "youtube"],
                    "mediaUrls": [media_url]
                }
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {AYRSHARE_KEY}"
                }
                ayr_resp = requests.post(ayrshare_endpoint, json=payload, headers=headers)
                if ayr_resp.status_code in [200, 201]:
                    posted_to_socials = True
            except Exception as e:
                print(f"Failed to auto-post to Ayrshare: {e}")

        return cors({
            "type": result_type if result_type in ("image","video") else None,
            "text": reply_text,
            "url": media_url,
            "title": title,
            "auto_posted": posted_to_socials
        })

    except anthropic.AuthenticationError:
        return cors({"error": "Invalid Anthropic API key. Check your ANTHROPIC_API_KEY env var."}, 401)
    except Exception as e:
        return cors({"error": str(e)}, 500)


def _quality_suffix(prompt, quality, style):
    """Add quality and style modifiers to the generation prompt."""
    style_map = {
        "funny": "funny, humorous, relatable, internet meme style",
        "dank": "dank meme, surreal, absurdist humor, deep fried meme aesthetic",
        "wholesome": "wholesome, warm, positive vibes, cute meme",
        "dark": "dark humor, edgy satire, clever irony",
        "viral": "viral meme format, trending, high engagement style",
    }
    quality_map = {
        "standard": "good quality",
        "high": "high quality, detailed, sharp, 4K",
        "ultra": "ultra high quality, photorealistic detail, 8K, masterpiece",
    }
    style_str = style_map.get(style, style_map["funny"])
    quality_str = quality_map.get(quality, quality_map["high"])
    return f"{prompt}, {style_str}, {quality_str}, meme format, bold white text, internet culture"


# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return cors({"status": "ok", "service": "MemeForge AI"})
