from flask import Flask, request, jsonify, Response
import os, json, re, requests

app = Flask(__name__)

# ─── API Keys ─────────────────────────────────────────────────────────────────
GROQ_KEY      = os.environ.get("GROQ_API_KEY", "")
GEMINI_KEY    = os.environ.get("GEMINI_API_KEY", "")
PEXELS_KEY    = os.environ.get("PEXELS_API_KEY", "")
SHOTSTACK_KEY = os.environ.get("SHOTSTACK_KEY", "")

# ─── Meme templates (imgflip public URLs) ────────────────────────────────────
TEMPLATES = {
    "drake":                "https://i.imgflip.com/30b1gx.jpg",
    "distracted_boyfriend": "https://i.imgflip.com/1ur9b0.jpg",
    "giga_chad":            "https://i.imgflip.com/4r0xzj.jpg",
    "this_is_fine":         "https://i.imgflip.com/wxica.jpg",
    "expanding_brain":      "https://i.imgflip.com/1jwhww.jpg",
    "change_my_mind":       "https://i.imgflip.com/24y43o.jpg",
    "always_has_been":      "https://i.imgflip.com/46e43q.jpg",
    "monkey_puppet":        "https://i.imgflip.com/3n484f.jpg",
    "doge":                 "https://i.imgflip.com/4t0m5.jpg",
    "two_buttons":          "https://i.imgflip.com/1zef.jpg",
    "uno_reverse":          "https://i.imgflip.com/3khte4.jpg",
    "surprised_pikachu":    "https://i.imgflip.com/2kbn1e.jpg",
    "hide_pain_harold":     "https://i.imgflip.com/gk5el.jpg",
    "sad_pablo":            "https://i.imgflip.com/sy4af.jpg",
    "woman_yelling_cat":    "https://i.imgflip.com/3oyevr.jpg",
    "galaxy_brain":         "https://i.imgflip.com/2don3m.jpg",
    "bernie_mittens":       "https://i.imgflip.com/4ux3vl.jpg",
    "success_kid":          "https://i.imgflip.com/1bhk.jpg",
    "panik_kalm":           "https://i.imgflip.com/3qqd4o.jpg",
    "npc":                  "https://i.imgflip.com/7xzpfm.jpg",
}

# ─── System prompt ────────────────────────────────────────────────────────────
SYSTEM = """You are MemeForge AI — India's most creative, savage, and relatable meme generator and general AI assistant. You were built to go viral on Indian social media (Instagram, YouTube, Twitter/X).

━━━ PERSONALITY ━━━
You are witty, funny, clever, and deeply rooted in Indian culture. You understand desi humor, Bollywood, cricket, tech startup culture, student life, and everything in between. You roast with love. You speak in the user's language — Hindi, English, or Hinglish.

━━━ LANGUAGES ━━━
You fully understand and respond in:
• Hindi (Devanagari and romanized)
• English
• Hinglish (code-mixed Hindi-English)
• Indian slangs: bhai, yaar, bsdk, bc, mf, jugaad, chapri, sigma male, sasta, nautanki, pagal, hero, antim, bas kar, chal hat, kya mast, teri maa ki, 420, lodu, bhenchod (write as bc), gadha, bewakoof, chutiya (write as ch*tiya or avoid)
• Internet slangs: ratio, no cap, fr fr, bussin, rizz, L+bozo, it's giving, main character, rent free, slay, lowkey, NPC, chad, sigma, based, cringe

━━━ INDIAN CULTURAL KNOWLEDGE ━━━
You deeply understand:
• JEE/NEET/Board exam pressure, kota factory life, Indian parents' sapne
• IPL, India vs Pakistan, Rohit Sharma, Virat Kohli, MS Dhoni, Bumrah
• Bollywood: Shah Rukh Khan, Salman, Aamir, Deepika, RRR, KGF, Pushpa, DDLJ, "Bade bade deshon mein..."
• Delhi vs Mumbai rivalry, auto-wala bargaining, chai obsession, jugaad fixes
• Indian office culture: HR, Monday blues, appraisal drama
• Indian weddings: sangeet, baraat, "shaadi mein zaroor aana"
• 45°C summers, load shedding, AC band, BSNL jokes
• WhatsApp uncle forwards, gold digger jokes, rishta aunties
• Startup culture: funding milna, pivot, "disrupting the space"
• Paytm, Zomato, Swiggy, OYO desi meme culture

━━━ MEME TEMPLATES AVAILABLE ━━━
drake, distracted_boyfriend, giga_chad, this_is_fine, expanding_brain, change_my_mind, always_has_been, monkey_puppet, doge, two_buttons, uno_reverse, surprised_pikachu, hide_pain_harold, sad_pablo, woman_yelling_cat, galaxy_brain, bernie_mittens, success_kid, panik_kalm, npc

━━━ DECISION LOGIC (CRITICAL) ━━━
You MUST correctly distinguish between a conversation and a meme request:
1. CHAT MODE ("type": "chat"): If the user says a casual greeting (hi/hello), asks a general question, makes a statement, or throws an insult/slang at you. DO NOT generate media. Just reply conversationally. 
2. MEME MODE ("type": "image" or "video"): ONLY trigger this if the user EXPLICITLY asks for a meme, image, or video, or gives a clear scenario meant to be a meme (e.g., "when the code doesn't compile"). Do not default to image just because the text is funny.
• Always respond in the SAME language the user used.

━━━ MEME CAPTION RULES ━━━
• Top text: Sets up the situation (3-7 words, ALL CAPS)
• Bottom text: Delivers the punchline (3-7 words, ALL CAPS)
• Be specific to Indian context when relevant
• Make it relatable — the best memes make people say "this is literally me"
• The punchline should be unexpected, sharp, and funny
• If Hindi: write the text in ROMANIZED HINDI (e.g., "PADHNA CHAHIYE" not "पढ़ना चाहिए") so Canvas can render it

━━━ OUTPUT FORMAT ━━━
Respond ONLY in pure JSON. No markdown. No backticks. No extra text.
{
  "type": "image" | "video" | "chat",
  "text": "Your conversational reply in the user's language. Be warm, funny, and brief. For greetings, introduce yourself.",
  "template": "template_name OR custom" (Leave empty if chat),
  "top_text": "TOP TEXT IN ROMANIZED CAPS" (Leave empty if chat),
  "bottom_text": "BOTTOM TEXT IN ROMANIZED CAPS" (Leave empty if chat),
  "pexels_query": "search query" (Leave empty if chat),
  "pexels_type": "photo | video" (Leave empty if chat),
  "title": "Short meme title" (Leave empty if chat),
  "explanation": "Why this meme is funny" (Leave empty if chat)
}"""

# ─── CORS helper ──────────────────────────────────────────────────────────────
def cors(data, status=200):
    r = jsonify(data)
    r.status_code = status
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r

@app.route("/api/generate", methods=["OPTIONS"])
@app.route("/api/video/<job_id>", methods=["OPTIONS"])
@app.route("/api/proxy", methods=["OPTIONS"])
def options(**kwargs):
    r = Response("", 200)
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return r

# ─── GROQ call ────────────────────────────────────────────────────────────────
def groq(messages, system="", model="llama-3.3-70b-versatile", temp=0.85, max_tok=1024):
    if not GROQ_KEY:
        raise ValueError("GROQ_API_KEY not set in Vercel environment variables")
    hdrs = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    body = {"model": model, "messages": msgs, "max_tokens": max_tok, "temperature": temp}
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                      headers=hdrs, json=body, timeout=25)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

# ─── Gemini fallback ─────────────────────────────────────────────────────────
def gemini(prompt, system=""):
    if not GEMINI_KEY:
        raise ValueError("GEMINI_API_KEY not set")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    body = {
        "systemInstruction": {"parts": [{"text": system}]} if system else None,
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 1024}
    }
    if not body["systemInstruction"]:
        del body["systemInstruction"]
    r = requests.post(url, json=body, timeout=25)
    r.raise_for_status()
    candidates = r.json().get("candidates", [])
    if candidates:
        return candidates[0]["content"]["parts"][0]["text"].strip()
    raise ValueError("No Gemini response")

# ─── Pexels image search ──────────────────────────────────────────────────────
def pexels_photo(query, quality="high"):
    if not PEXELS_KEY:
        return None
    params = {"query": query, "per_page": 5, "orientation": "square"}
    r = requests.get("https://api.pexels.com/v1/search",
                     params=params, headers={"Authorization": PEXELS_KEY}, timeout=8)
    r.raise_for_status()
    photos = r.json().get("photos", [])
    if not photos:
        return None
    p = photos[0]
    src = p.get("src", {})
    if quality == "ultra":
        return src.get("original") or src.get("large2x") or src.get("large")
    elif quality == "high":
        return src.get("large2x") or src.get("large")
    return src.get("large") or src.get("medium")

# ─── Pexels video search ──────────────────────────────────────────────────────
def pexels_video(query):
    if not PEXELS_KEY:
        return None
    r = requests.get("https://api.pexels.com/videos/search",
                     params={"query": query, "per_page": 5, "size": "medium"},
                     headers={"Authorization": PEXELS_KEY}, timeout=8)
    r.raise_for_status()
    videos = r.json().get("videos", [])
    if not videos:
        return None
    video = videos[0]
    files = sorted(video.get("video_files", []), key=lambda x: x.get("width", 0), reverse=True)
    # Prefer HD but not 4K to keep size manageable
    for f in files:
        w = f.get("width", 0)
        if 720 <= w <= 1920:
            return f.get("link")
    return files[0].get("link") if files else None

# ─── Shotstack video render ───────────────────────────────────────────────────
def shotstack_render(video_url, top_text, bottom_text, title):
    if not SHOTSTACK_KEY:
        raise ValueError("SHOTSTACK_KEY not set in Vercel environment variables")

    # Use stage endpoint
    base = "https://api.shotstack.io/stage"
    hdrs = {"x-api-key": SHOTSTACK_KEY, "Content-Type": "application/json"}

    # Video clip track
    video_clip = {
        "asset": {"type": "video", "src": video_url, "volume": 0},
        "start": 0, "length": 6,
        "transition": {"in": "fade", "out": "fade"}
    }

    clips = [video_clip]

    # Text clips
    text_style = "font-family:Impact,Arial Black,sans-serif;color:white;-webkit-text-stroke:3px black;text-align:center;text-transform:uppercase;"

    if top_text:
        clips.append({
            "asset": {
                "type": "html",
                "html": f"<p style='{text_style}font-size:64px;margin:0;padding:10px'>{top_text}</p>",
                "css": "",
                "width": 1280, "height": 180,
                "background": "transparent"
            },
            "position": "topCenter",
            "start": 0, "length": 6
        })

    if bottom_text:
        clips.append({
            "asset": {
                "type": "html",
                "html": f"<p style='{text_style}font-size:64px;margin:0;padding:10px'>{bottom_text}</p>",
                "css": "",
                "width": 1280, "height": 180,
                "background": "transparent"
            },
            "position": "bottomCenter",
            "start": 0, "length": 6
        })

    payload = {
        "timeline": {
            "tracks": [
                {"clips": [c for c in clips if c["asset"]["type"] in ("html",)]},
                {"clips": [video_clip]}
            ]
        },
        "output": {
            "format": "mp4",
            "resolution": "hd",
            "fps": 30,
            "quality": "high"
        }
    }

    r = requests.post(f"{base}/render", headers=hdrs, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()["response"]["id"]

# ─── Parse AI JSON safely ─────────────────────────────────────────────────────
def parse_ai(text):
    try:
        clean = re.sub(r"```json|```", "", text).strip()
        # Extract JSON block
        m = re.search(r'\{.*\}', clean, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception:
        pass
    return {"type": "chat", "text": text, "title": "Response"}

# ─── Build conversation messages ──────────────────────────────────────────────
def build_msgs(history, prompt, style, lang):
    msgs = []
    for m in history[-10:]:
        role = m.get("role", "")
        content = m.get("content", "")
        if role in ("user", "assistant") and content:
            msgs.append({"role": role, "content": content})

    lang_hint = "Hindi" if lang == "hi" else "English"
    full_prompt = f"[Language preference: {lang_hint}] [Style: {style}] {prompt}"

    # Ensure last message is from user
    if not msgs or msgs[-1]["role"] != "user":
        msgs.append({"role": "user", "content": full_prompt})
    else:
        msgs[-1]["content"] = full_prompt

    return msgs

# ═══════════════════════════════════════════════════════════════════════════════
#   MAIN GENERATE ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/api/generate", methods=["POST"])
def generate():
    try:
        body     = request.get_json(force=True) or {}
        prompt   = (body.get("prompt") or "").strip()
        gen_type = body.get("genType", "auto")   # auto | image | video | chat
        quality  = body.get("quality", "high")   # standard | high | ultra
        style    = body.get("style", "funny")
        lang     = body.get("lang", "hi")
        history  = body.get("history", [])

        if not prompt:
            return cors({"error": "Empty prompt"}, 400)

        if not GROQ_KEY:
            return cors({"error": "GROQ_API_KEY not configured in Vercel Environment Variables. Please add it in your Vercel project settings."}, 500)

        # ── Step 1: AI analysis ─────────────────────────────────────────────
        msgs = build_msgs(history, prompt, style, lang)

        try:
            raw = groq(msgs, system=SYSTEM, temp=0.88)
        except Exception as groq_err:
            # Fallback to Gemini
            if GEMINI_KEY:
                try:
                    full = SYSTEM + "\n\nUser says: " + prompt
                    raw = gemini(full, system=SYSTEM)
                except Exception:
                    return cors({"error": f"AI error: {str(groq_err)}"}, 500)
            else:
                return cors({"error": f"GROQ error: {str(groq_err)}"}, 500)

        parsed = parse_ai(raw)

        # Honor explicit type override
        if gen_type in ("image", "video", "chat"):
            parsed["type"] = gen_type

        result_type = parsed.get("type", "chat")
        reply_text  = parsed.get("text", "")
        title       = parsed.get("title", "Meme")
        top_text    = parsed.get("top_text", "")
        bottom_text = parsed.get("bottom_text", "")
        template    = parsed.get("template", "custom")
        pexels_q    = parsed.get("pexels_query", "funny meme moment")

        # ── Step 2: Image meme ──────────────────────────────────────────────
        if result_type == "image":
            img_url = None

            if template in TEMPLATES:
                img_url = TEMPLATES[template]
            else:
                # Search Pexels for custom image
                if PEXELS_KEY:
                    try:
                        img_url = pexels_photo(pexels_q, quality)
                    except Exception:
                        pass

                # Final fallback: use a default meme template
                if not img_url:
                    img_url = TEMPLATES.get("drake")

            if not top_text and not bottom_text:
                top_text  = "WHEN THE MEME"
                bottom_text = "HITS DIFFERENT"

            return cors({
                "type":      "image",
                "text":      reply_text or "Yeh lo tera meme! 😂",
                "url":       img_url,
                "pexelsUrl": img_url,
                "topText":   top_text.upper() if top_text else "",
                "bottomText":bottom_text.upper() if bottom_text else "",
                "title":     title,
                "quality":   quality
            })

        # ── Step 3: Video meme ──────────────────────────────────────────────
        elif result_type == "video":
            vid_url = None

            if PEXELS_KEY:
                try:
                    vid_url = pexels_video(pexels_q)
                except Exception:
                    pass

            if not vid_url:
                # No video source — return as image meme instead
                fallback_url = TEMPLATES.get("this_is_fine", TEMPLATES["drake"])
                return cors({
                    "type":      "image",
                    "text":      (reply_text or "Video banane mein thodi dikkat aayi, lekin yeh image meme toh lo!") + " (Video background nahi mila, image meme bana diya!)",
                    "url":       fallback_url,
                    "pexelsUrl": fallback_url,
                    "topText":   top_text.upper() if top_text else "",
                    "bottomText":bottom_text.upper() if bottom_text else "",
                    "title":     title,
                    "quality":   quality
                })

            # Try Shotstack render
            if SHOTSTACK_KEY:
                try:
                    job_id = shotstack_render(vid_url, top_text, bottom_text, title)
                    return cors({
                        "type":       None,
                        "videoJobId": job_id,
                        "text":       reply_text or "Video meme render shuru ho gaya! 15-30 seconds mein ready hoga. 🎬",
                        "title":      title
                    })
                except Exception as se:
                    # Shotstack failed — return pexels video directly with metadata
                    return cors({
                        "type":      "video",
                        "text":      reply_text or "Meme video ready hai! 🎬",
                        "url":       vid_url,
                        "topText":   top_text,
                        "bottomText":bottom_text,
                        "title":     title,
                        "quality":   quality
                    })
            else:
                # No Shotstack — return raw video
                return cors({
                    "type":      "video",
                    "text":      reply_text or "Meme video ready hai! 🎬",
                    "url":       vid_url,
                    "topText":   top_text,
                    "bottomText":bottom_text,
                    "title":     title,
                    "quality":   quality
                })

        # ── Step 4: Chat response ───────────────────────────────────────────
        else:
            return cors({
                "type": None,
                "text": reply_text or raw,
                "title": title
            })

    except Exception as e:
        import traceback
        return cors({"error": str(e), "trace": traceback.format_exc()[-500:]}, 500)


# ═══════════════════════════════════════════════════════════════════════════════
#   VIDEO STATUS POLLING (Shotstack)
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/api/video/<job_id>", methods=["GET"])
def video_status(job_id):
    try:
        if not SHOTSTACK_KEY:
            return cors({"status": "failed", "error": "SHOTSTACK_KEY not set"})

        hdrs = {"x-api-key": SHOTSTACK_KEY}
        r = requests.get(f"https://api.shotstack.io/stage/render/{job_id}",
                         headers=hdrs, timeout=10)
        r.raise_for_status()
        resp = r.json().get("response", {})
        status = resp.get("status", "unknown")
        url    = resp.get("url")

        return cors({"status": status, "url": url})
    except Exception as e:
        return cors({"status": "failed", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════════
#   IMAGE PROXY (for Canvas CORS)
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/api/proxy", methods=["GET"])
def proxy():
    url = request.args.get("url", "").strip()
    if not url or not url.startswith("http"):
        return "Invalid URL", 400
    # Only allow known safe domains
    allowed = ("i.imgflip.com", "images.pexels.com", "videos.pexels.com",
               "cdn.pixabay.com", "shotstack-store.s3-ap-southeast-2.amazonaws.com")
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    if not any(domain.endswith(d) for d in allowed):
        return "Domain not allowed", 403
    try:
        r = requests.get(url, timeout=12, headers={
            "User-Agent": "Mozilla/5.0 (MemeForge/2.0)",
            "Referer": "https://meme-world.vercel.app"
        }, stream=True)
        content_type = r.headers.get("Content-Type", "image/jpeg")
        resp = Response(r.content, content_type=content_type)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Cache-Control"] = "public, max-age=86400"
        return resp
    except Exception as e:
        return str(e), 500


# ═══════════════════════════════════════════════════════════════════════════════
#   HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/api/health", methods=["GET"])
def health():
    keys = {
        "groq":      bool(GROQ_KEY),
        "gemini":    bool(GEMINI_KEY),
        "pexels":    bool(PEXELS_KEY),
        "shotstack": bool(SHOTSTACK_KEY),
    }
    return cors({"status": "ok", "api_keys": keys})
