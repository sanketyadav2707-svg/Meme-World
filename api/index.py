"""
MemeForge AI — Backend
Uses: GROQ (primary AI), Gemini (fallback/creative), Pexels (images+video), Shotstack (video render)
"""
from flask import Flask, request, jsonify, Response
import os, json, re, requests, random
from urllib.parse import urlparse

app = Flask(__name__)

# ─── API Keys ──────────────────────────────────────────────────────────────────
GROQ_KEY      = os.environ.get("GROQ_API_KEY", "")
GEMINI_KEY    = os.environ.get("GEMINI_API_KEY", "")
PEXELS_KEY    = os.environ.get("PEXELS_API_KEY", "")
SHOTSTACK_KEY = os.environ.get("SHOTSTACK_KEY", "")

# ─── Static meme template library ─────────────────────────────────────────────
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
    "surprised_pikachu":    "https://i.imgflip.com/2kbn1e.jpg",
    "hide_pain_harold":     "https://i.imgflip.com/gk5el.jpg",
    "sad_pablo":            "https://i.imgflip.com/sy4af.jpg",
    "woman_yelling_cat":    "https://i.imgflip.com/3oyevr.jpg",
    "galaxy_brain":         "https://i.imgflip.com/2don3m.jpg",
    "success_kid":          "https://i.imgflip.com/1bhk.jpg",
    "panik_kalm":           "https://i.imgflip.com/3qqd4o.jpg",
    "uno_reverse":          "https://i.imgflip.com/3khte4.jpg",
    "npc":                  "https://i.imgflip.com/7xzpfm.jpg",
    "bernie_mittens":       "https://i.imgflip.com/4ux3vl.jpg",
    "roll_safe":            "https://i.imgflip.com/1h7in3.jpg",
    "mocking_spongebob":    "https://i.imgflip.com/1otk96.jpg",
    "disaster_girl":        "https://i.imgflip.com/23ls.jpg",
    "first_world_problems": "https://i.imgflip.com/1bhf.jpg",
    "leonardo_pointing":    "https://i.imgflip.com/qhgdl.jpg",
    "batman_slapping":      "https://i.imgflip.com/9ehk.jpg",
    "ancient_aliens":       "https://i.imgflip.com/26am.jpg",
    "grumpy_cat":           "https://i.imgflip.com/8p0a.jpg",
    "y_u_no":               "https://i.imgflip.com/1bip.jpg",
    "gru_plan":             "https://i.imgflip.com/26jxvz.jpg",
}

# ─── SYSTEM PROMPT ─────────────────────────────────────────────────────────────
SYSTEM = """You are MemeForge AI — India's most intelligent, creative, and viral meme generator, built to dominate Instagram, YouTube Shorts, and Twitter/X.

━━━ CORE IDENTITY ━━━
You are witty, savage, deeply relatable, and rooted in Indian culture. You think like a desi 20-something who grew up on Bollywood, cricket, JEE memes, and 3AM chai. You roast with love. You're never generic.

━━━ LANGUAGE CAPABILITIES ━━━
You perfectly understand and respond in:
• Pure Hindi: "yaar aaj kuch mast banate hain"
• Pure English: "let's make something viral today"  
• Hinglish: "bhai ek dank meme chahiye"
• Desi slangs: yaar, bhai, bsdk, bc, jugaad, chapri, sigma, nautanki, pagal, seedha, sasta, lodu, ghanta, jhol, bhai kya scene hai, chal hat, bas kar, kya mast, antim, hero ban gaya, teri class lag gayi
• Internet slang: ratio, no cap, fr fr, bussin, rizz, NPC, chad, sigma, based, cringe, it's giving, main character, slay, lowkey, W, L, rent free

━━━ INDIAN KNOWLEDGE BASE ━━━
You deeply know:
• JEE/NEET/12th boards, Kota factory life, IIT sapne, engineering struggles
• IPL, India vs Pakistan cricket, Rohit Sharma, Virat, Dhoni, Bumrah, "mere pass maa hai" moment
• Bollywood: SRK, Salman, KGF, Pushpa, RRR, DDLJ, "bade bade deshon mein...", "Ek baar jo maine commitment de di..."
• Delhi traffic, Mumbai local, auto-rickshaw bargaining, Bangalore rain
• Indian weddings, rishta aunties, "shaadi kab kar rahe ho", joint family drama  
• 45°C summers, BSNL jokes, bijli cut, AC kharab, inverter lag gaya
• WhatsApp forward uncles, Paytm cashback, Zomato late delivery, OYO drama
• Startup culture: funding, pivot, "we're disrupting", layoffs, LinkedIn cringe
• Sarkari naukri vs startup debate, civil services aspirants
• Indian parents: "humne kya kiya tha tumhari umar mein", "doctor ban jao"
• Hostel life, mess ka khana, assignment copy karna, backlog memes

━━━ MEME CREATION PHILOSOPHY ━━━
The best memes are:
1. SPECIFIC — not "studying is hard" but "JEE mains ke 3 din pehle Netflix binge karna"
2. RELATABLE — makes you say "this is literally me bhai"
3. UNEXPECTED punchline — setup leads one way, punchline goes another
4. SHORT & PUNCHY — 3-6 words per text block (Impact font reads best)
5. CULTURALLY LOADED — Indian references hit harder than generic ones
6. TIMING matters — punchline lands because of what comes before

━━━ AVAILABLE TEMPLATES ━━━
drake, distracted_boyfriend, giga_chad, this_is_fine, expanding_brain, change_my_mind, 
always_has_been, monkey_puppet, doge, two_buttons, surprised_pikachu, hide_pain_harold, 
sad_pablo, woman_yelling_cat, galaxy_brain, success_kid, panik_kalm, uno_reverse, npc, 
bernie_mittens, roll_safe, mocking_spongebob, disaster_girl, first_world_problems, 
leonardo_pointing, batman_slapping, ancient_aliens, grumpy_cat, y_u_no, gru_plan

Use "custom" for when a Pexels image would be better than any template.

━━━ DECISION RULES ━━━
• Greeting/casual chat (hi/hello/yo/wassup/kya haal) → type: "chat", be warm and funny, briefly introduce yourself
• Questions about anything → type: "chat", answer helpfully and thoroughly
• Meme request, funny request → type: "image" (default) or "video" if explicitly asked
• Ambiguous humorous prompt → type: "image"
• ALWAYS respond in the user's language/style

━━━ CAPTION RULES ━━━
• Write in ROMANIZED form (not Devanagari) — Impact font doesn't support Hindi script
• Wrong: "पढ़ना चाहिए" Right: "PADHNA CHAHIYE"
• Wrong: "मैं" Right: "MAIN"
• 3-7 words per text block maximum
• Top text = setup/situation | Bottom text = punchline/subversion

━━━ PEXELS SEARCH STRATEGY ━━━
Give 3 different search queries from specific to general:
• primary_pexels: Very specific contextual image ("student crying textbook night")
• alt_pexels_1: More general version ("stressed student studying")
• alt_pexels_2: Abstract fallback ("books frustration")
For video: give the scene you want as background footage

━━━ OUTPUT FORMAT — STRICT JSON, NO MARKDOWN ━━━
{
  "type": "image" | "video" | "chat",
  "text": "Your reply to the user in their language. Warm, funny, brief. For greetings, introduce as MemeForge AI — India's meme machine.",
  "template": "template_name_from_list OR custom",
  "top_text": "SETUP TEXT IN ROMAN CAPS",
  "bottom_text": "PUNCHLINE IN ROMAN CAPS", 
  "primary_pexels": "specific pexels search query",
  "alt_pexels_1": "alternative pexels query",
  "alt_pexels_2": "generic fallback pexels query",
  "pexels_video_query": "video search terms if type=video",
  "title": "Short meme title 2-4 words",
  "why_funny": "One sentence: what makes this land"
}"""

# ─── CORS ──────────────────────────────────────────────────────────────────────
def cors(data, status=200):
    r = jsonify(data)
    r.status_code = status
    for k, v in [
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Headers", "Content-Type"),
        ("Access-Control-Allow-Methods", "GET,POST,OPTIONS"),
    ]: r.headers[k] = v
    return r

@app.route("/api/generate",    methods=["OPTIONS"])
@app.route("/api/video/<jid>", methods=["OPTIONS"])
@app.route("/api/proxy",       methods=["OPTIONS"])
@app.route("/api/health",      methods=["OPTIONS"])
def opts(**_):
    r = Response("", 200)
    r.headers.update({"Access-Control-Allow-Origin": "*",
                       "Access-Control-Allow-Headers": "Content-Type",
                       "Access-Control-Allow-Methods": "GET,POST,OPTIONS"})
    return r

# ─── AI Calls ──────────────────────────────────────────────────────────────────
def call_groq(messages, temp=0.88, model="llama-3.3-70b-versatile"):
    if not GROQ_KEY:
        raise ValueError("GROQ_API_KEY not set in Vercel Environment Variables")
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "max_tokens": 1200, "temperature": temp},
        timeout=28
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def call_gemini(prompt):
    if not GEMINI_KEY:
        raise ValueError("GEMINI_API_KEY not set")
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
        json={"contents": [{"role": "user", "parts": [{"text": prompt}]}],
              "generationConfig": {"temperature": 0.9, "maxOutputTokens": 1200}},
        timeout=25
    )
    r.raise_for_status()
    c = r.json().get("candidates", [])
    return c[0]["content"]["parts"][0]["text"].strip() if c else ""

# ─── Build clean message history ──────────────────────────────────────────────
def build_messages(history, prompt, style, lang):
    """Build a clean alternating-role message list for the AI."""
    sys_msg = {"role": "system", "content": SYSTEM}
    msgs = [sys_msg]

    # Add history, ensuring alternating roles and meaningful content
    clean = []
    for m in history:
        role = m.get("role", "")
        content = m.get("content", "").strip()
        if role not in ("user", "assistant"):
            continue
        # Skip empty assistant messages (they were media-only)
        if not content:
            if role == "assistant":
                content = "[Generated a meme]"
            else:
                continue

        # Ensure alternating — skip duplicate consecutive roles
        if clean and clean[-1]["role"] == role:
            if role == "assistant":
                clean[-1]["content"] = content  # keep last
            continue  # skip duplicate user (shouldn't happen with our fix)
        clean.append({"role": role, "content": content})

    # Ensure last in clean is assistant (not user) before we add current user msg
    if clean and clean[-1]["role"] == "user":
        clean.pop()  # remove to avoid consecutive user messages

    msgs.extend(clean)

    # Add current user prompt
    lang_hint = "Hindi/Hinglish" if lang == "hi" else "English"
    msgs.append({"role": "user", "content": f"[Lang: {lang_hint}] [Style: {style}] {prompt}"})
    return msgs

# ─── Parse AI JSON ─────────────────────────────────────────────────────────────
def parse_json(text):
    try:
        text = re.sub(r"```(?:json)?|```", "", text).strip()
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            return json.loads(m.group())
    except Exception:
        pass
    return {"type": "chat", "text": text, "title": "Response"}

# ─── Pexels photo search ──────────────────────────────────────────────────────
def pexels_photos(query, n=5, orientation="square", quality="high"):
    if not PEXELS_KEY or not query:
        return []
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "per_page": n, "orientation": orientation},
            headers={"Authorization": PEXELS_KEY},
            timeout=8
        )
        r.raise_for_status()
        photos = r.json().get("photos", [])
        results = []
        for p in photos:
            src = p.get("src", {})
            if quality == "ultra":
                url = src.get("original") or src.get("large2x") or src.get("large")
            else:
                url = src.get("large2x") or src.get("large")
            if url:
                results.append(url)
        return results
    except Exception:
        return []

# ─── Pexels video search ──────────────────────────────────────────────────────
def pexels_video(query, n=5):
    if not PEXELS_KEY or not query:
        return None
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            params={"query": query, "per_page": n, "size": "medium"},
            headers={"Authorization": PEXELS_KEY},
            timeout=8
        )
        r.raise_for_status()
        videos = r.json().get("videos", [])
        for v in videos:
            files = sorted(v.get("video_files", []), key=lambda x: x.get("width", 0), reverse=True)
            for f in files:
                w = f.get("width", 0)
                if 640 <= w <= 1920:
                    return f.get("link")
        return None
    except Exception:
        return None

# ─── Shotstack video renderer ─────────────────────────────────────────────────
def shotstack_render(video_url, top_text, bottom_text):
    if not SHOTSTACK_KEY:
        raise ValueError("SHOTSTACK_KEY not set")

    hdrs = {"x-api-key": SHOTSTACK_KEY, "Content-Type": "application/json"}
    style = "font-family:Impact,Arial Black,sans-serif;color:white;-webkit-text-stroke:3px black;text-transform:uppercase;text-align:center;"

    clips = [{
        "asset": {"type": "video", "src": video_url, "volume": 0},
        "start": 0, "length": 7,
        "transition": {"in": "fade", "out": "fade"}
    }]

    text_clips = []
    if top_text:
        text_clips.append({
            "asset": {
                "type": "html",
                "html": f"<p style='{style}font-size:72px;margin:8px;'>{top_text.upper()}</p>",
                "css": "p{margin:0;padding:8px 12px;}",
                "width": 1280, "height": 200, "background": "transparent"
            },
            "position": "topCenter", "start": 0, "length": 7
        })
    if bottom_text:
        text_clips.append({
            "asset": {
                "type": "html",
                "html": f"<p style='{style}font-size:72px;margin:8px;'>{bottom_text.upper()}</p>",
                "css": "p{margin:0;padding:8px 12px;}",
                "width": 1280, "height": 200, "background": "transparent"
            },
            "position": "bottomCenter", "start": 0, "length": 7
        })

    payload = {
        "timeline": {
            "tracks": [
                {"clips": text_clips},
                {"clips": clips}
            ]
        },
        "output": {"format": "mp4", "resolution": "hd", "fps": 30, "quality": "high"}
    }

    r = requests.post("https://api.shotstack.io/stage/render",
                      headers=hdrs, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()["response"]["id"]

# ═══════════════════════════════════════════════════════════════════════════════
#   MAIN /api/generate
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/api/generate", methods=["POST"])
def generate():
    try:
        body      = request.get_json(force=True) or {}
        prompt    = (body.get("prompt") or "").strip()
        gen_type  = body.get("genType", "auto")
        quality   = body.get("quality", "high")
        style     = body.get("style", "funny")
        lang      = body.get("lang", "hi")
        history   = body.get("history", [])  # ★ already excludes current message (fixed in frontend)
        autoswitch = body.get("autoswitch", True)

        if not prompt:
            return cors({"error": "Empty prompt"}, 400)
        if not GROQ_KEY:
            return cors({"error": "GROQ_API_KEY not set in Vercel Environment Variables. Please add it in Project Settings → Environment Variables."}, 500)

        # ── Step 1: Build messages and call AI ──────────────────────────────
        msgs = build_messages(history, prompt, style, lang)

        raw = None
        try:
            raw = call_groq(msgs, temp=0.88)
        except Exception as e1:
            # Fallback to Gemini
            if GEMINI_KEY:
                try:
                    combined = SYSTEM + f"\n\nConversation history:\n"
                    for m in history[-6:]:
                        combined += f"{m.get('role','user').upper()}: {m.get('content','')}\n"
                    combined += f"\nUSER: {prompt}\n\nRespond in JSON format as specified."
                    raw = call_gemini(combined)
                except Exception as e2:
                    return cors({"error": f"AI unavailable: {str(e1)}. Gemini fallback: {str(e2)}"}, 500)
            else:
                return cors({"error": f"GROQ error: {str(e1)}"}, 500)

        parsed = parse_json(raw)

        # Override type if explicitly chosen in frontend
        if gen_type in ("image", "video", "chat"):
            parsed["type"] = gen_type

        t         = parsed.get("type", "chat")
        text      = parsed.get("text", "")
        template  = parsed.get("template", "custom").lower()
        top       = (parsed.get("top_text") or "").strip()
        bot       = (parsed.get("bottom_text") or "").strip()
        p_primary = (parsed.get("primary_pexels") or parsed.get("pexels_query") or "").strip()
        p_alt1    = (parsed.get("alt_pexels_1") or "").strip()
        p_alt2    = (parsed.get("alt_pexels_2") or "funny meme reaction").strip()
        vid_q     = (parsed.get("pexels_video_query") or p_primary or "funny moment").strip()
        title     = (parsed.get("title") or "Meme").strip()

        # ── Step 2: Image meme ───────────────────────────────────────────────
        if t == "image":
            img_url  = None
            alt_urls = []

            if template in TEMPLATES:
                img_url = TEMPLATES[template]
                # Also try to get some Pexels alternatives
                if autoswitch and p_primary and PEXELS_KEY:
                    alts = pexels_photos(p_primary, n=3, quality=quality)
                    alt_urls = alts[:2]
            else:
                # Try Pexels with multiple queries
                if PEXELS_KEY:
                    for q in [p_primary, p_alt1, p_alt2]:
                        if not q:
                            continue
                        photos = pexels_photos(q, n=5, quality=quality)
                        if photos:
                            img_url = photos[0]
                            alt_urls = photos[1:3]
                            break

                # Last resort: use a template
                if not img_url:
                    # Pick template based on content hints
                    tpl_map = {
                        "drake": ["vs", "prefer", "vs ", "over", "instead"],
                        "this_is_fine": ["fine", "okay", "chill", "garmi", "hot", "fire"],
                        "giga_chad": ["chad", "sigma", "alpha", "hero", "winner"],
                        "distracted_boyfriend": ["distracted", "attracted", "eyeing", "looking"],
                        "expanding_brain": ["levels", "galaxy", "brain", "smart", "iq", "jugaad"],
                        "surprised_pikachu": ["shocked", "surprised", "unexpected", "really"],
                        "hide_pain_harold": ["hide", "pain", "smile", "cope", "harold", "sad"],
                    }
                    chosen = "drake"
                    lp = (top + " " + bot).lower()
                    for tpl, kws in tpl_map.items():
                        if any(kw in lp for kw in kws):
                            chosen = tpl
                            break
                    img_url = TEMPLATES[chosen]

            if not top and not bot:
                top = "WHEN THE MEME"
                bot = "HITS DIFFERENT"

            return cors({
                "type": "image",
                "text": text or "Yeh lo tera meme! 😂",
                "url": img_url,
                "alts": alt_urls,
                "topText": top.upper(),
                "bottomText": bot.upper(),
                "title": title,
                "quality": quality
            })

        # ── Step 3: Video meme ───────────────────────────────────────────────
        elif t == "video":
            vid_url = None
            for q in [vid_q, p_primary, p_alt1, "funny street scene"]:
                if not q: continue
                vid_url = pexels_video(q)
                if vid_url: break

            if not vid_url:
                # Fall back to image meme
                img_url = TEMPLATES.get(template, TEMPLATES["this_is_fine"])
                return cors({
                    "type": "image",
                    "text": (text or "") + " (Video background nahi mila, image meme ready hai!)",
                    "url": img_url,
                    "alts": [],
                    "topText": top.upper(),
                    "bottomText": bot.upper(),
                    "title": title,
                    "quality": quality
                })

            # Try Shotstack
            if SHOTSTACK_KEY:
                try:
                    job_id = shotstack_render(vid_url, top, bot)
                    return cors({
                        "type": None,
                        "videoJobId": job_id,
                        "text": text or "Video meme render ho raha hai! 15-30 seconds mein ready hoga. 🎬",
                        "title": title
                    })
                except Exception:
                    pass  # Fall through to raw video

            # Raw video without text overlay
            return cors({
                "type": "video",
                "text": text or "Meme video ready hai! 🎬",
                "url": vid_url,
                "topText": top,
                "bottomText": bot,
                "title": title,
                "quality": quality
            })

        # ── Step 4: Chat ─────────────────────────────────────────────────────
        else:
            return cors({
                "type": None,
                "text": text or raw,
                "title": title
            })

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(tb)
        return cors({"error": str(e)}, 500)


# ═══════════════════════════════════════════════════════════════════════════════
#   VIDEO STATUS POLL
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/api/video/<jid>", methods=["GET"])
def video_status(jid):
    try:
        if not SHOTSTACK_KEY:
            return cors({"status": "failed", "error": "No SHOTSTACK_KEY"})
        r = requests.get(
            f"https://api.shotstack.io/stage/render/{jid}",
            headers={"x-api-key": SHOTSTACK_KEY},
            timeout=10
        )
        r.raise_for_status()
        resp = r.json().get("response", {})
        return cors({"status": resp.get("status", "unknown"), "url": resp.get("url")})
    except Exception as e:
        return cors({"status": "failed", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════════
#   IMAGE PROXY (for Canvas CORS)
# ═══════════════════════════════════════════════════════════════════════════════
ALLOWED_DOMAINS = (
    "i.imgflip.com", "images.pexels.com", "videos.pexels.com",
    "cdn.pixabay.com", "shotstack-store.s3-ap-southeast-2.amazonaws.com",
    "shotstack-store.s3.ap-southeast-2.amazonaws.com",
    "player.vimeo.com", "res.cloudinary.com"
)

@app.route("/api/proxy", methods=["GET"])
def proxy():
    url = request.args.get("url", "").strip()
    if not url or not url.startswith("http"):
        return "Bad URL", 400
    domain = urlparse(url).netloc
    if not any(domain == d or domain.endswith("." + d) for d in ALLOWED_DOMAINS):
        return "Domain not allowed", 403
    try:
        r = requests.get(url, timeout=12, headers={
            "User-Agent": "Mozilla/5.0 (MemeForge/2.0; +https://meme-world.vercel.app)",
            "Referer": "https://meme-world.vercel.app"
        }, stream=True)
        ct = r.headers.get("Content-Type", "image/jpeg")
        resp = Response(r.content, content_type=ct)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Cache-Control"] = "public, max-age=604800"
        return resp
    except Exception as e:
        return str(e), 500


# ═══════════════════════════════════════════════════════════════════════════════
#   HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/api/health", methods=["GET"])
def health():
    return cors({
        "status": "ok",
        "apis": {
            "groq":      bool(GROQ_KEY),
            "gemini":    bool(GEMINI_KEY),
            "pexels":    bool(PEXELS_KEY),
            "shotstack": bool(SHOTSTACK_KEY),
        }
    })
