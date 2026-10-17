import asyncio
import io
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from . import codes
from .prompt import DEFAULT_PLATFORMS, PLATFORMS, build_system_prompt, build_user_prompt

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
# "low" = fast. Quality kam lage toh .env mein GEMINI_THINKING=medium kar do. "off" = setting mat bhejo.
THINKING = os.getenv("GEMINI_THINKING", "low").strip().lower()
# Ek saath kitni AI calls. Free tier pe zyada calls ek saath bhejne se Google rok deta hai.
PARALLEL = max(1, int(os.getenv("GEMINI_PARALLEL", "2")))
CALL_TIMEOUT_SEC = int(os.getenv("GEMINI_TIMEOUT", "60"))
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_SIDE = 1024  # AI ko itni photo kaafi hai; badi photo sirf upload aur tokens badhati hai
STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Listing AI")
_thinking_supported = True  # agar model thinking setting reject kare, toh aage se nahi bhejenge


def shrink_image(data: bytes, mime: str) -> tuple[bytes, str]:
    """Phone ki 4-5MB photo ko ~150KB JPEG bana do. Kuch gadbad ho toh original hi bhejo."""
    try:
        from PIL import Image, ImageOps

        img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
        if max(img.size) <= MAX_SIDE and len(data) < 400_000:
            return data, mime
        img.thumbnail((MAX_SIDE, MAX_SIDE))
        if img.mode not in ("RGB", "L"):
            bg = Image.new("RGB", img.size, "white")
            bg.paste(img, mask=img.convert("RGBA").split()[-1])
            img = bg
        out = io.BytesIO()
        img.save(out, "JPEG", quality=85)
        return out.getvalue(), "image/jpeg"
    except Exception:  # noqa: BLE001
        return data, mime


def log(msg: str) -> None:
    print(f"[listing-ai {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def call_gemini(image: bytes, mime: str, details: dict, platforms: list[str]) -> dict:
    global _thinking_supported
    from google import genai
    from google.genai import types

    # Ek call 60 sec se zyada na chale, aur error pe bas 1 baar chhota retry. Warna page atka rehta hai.
    client = genai.Client(
        api_key=API_KEY,
        http_options=types.HttpOptions(
            timeout=CALL_TIMEOUT_SEC * 1000,
            retry_options=types.HttpRetryOptions(attempts=2, initial_delay=1.0, max_delay=4.0),
        ),
    )
    contents = [types.Part.from_bytes(data=image, mime_type=mime), build_user_prompt(details)]

    def run(with_thinking: bool):
        extra = {}
        if with_thinking:
            extra["thinking_config"] = types.ThinkingConfig(thinking_level=THINKING.upper())
        return client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=build_system_prompt(platforms),
                response_mime_type="application/json",
                temperature=0.7,
                **extra,
            ),
        )

    name = ",".join(platforms)
    use_thinking = _thinking_supported and THINKING not in ("", "off")
    start = time.time()
    try:
        resp = run(use_thinking)
    except Exception as e:  # noqa: BLE001
        if use_thinking and "think" in str(e).lower():
            log(f"{name}: model ne thinking setting reject ki, bina uske try kar rahe hain")
            _thinking_supported = False
            resp = run(False)
        else:
            log(f"{name}: FAILED after {time.time() - start:.1f}s -> {str(e)[:300]}")
            raise
    log(f"{name}: done in {time.time() - start:.1f}s")
    return json.loads(resp.text)


async def generate_all(image: bytes, mime: str, details: dict, platforms: list[str]) -> dict:
    """Har platform ki alag call, ek saath max PARALLEL calls (free tier ki rate limit ka dhyan)."""
    sem = asyncio.Semaphore(PARALLEL)

    async def one(p: str):
        async with sem:
            return await asyncio.to_thread(call_gemini, image, mime, details, [p])

    log(f"start: {platforms} (parallel={PARALLEL}, thinking={THINKING}, model={MODEL})")
    t0 = time.time()
    results = await asyncio.gather(*(one(p) for p in platforms), return_exceptions=True)
    log(f"all done in {time.time() - t0:.1f}s")
    merged, errors = {}, []
    for p, r in zip(platforms, results):
        if isinstance(r, Exception):
            errors.append(f"{p}: {r}")
        elif isinstance(r, dict):
            merged[p] = r.get(p, r)  # model kabhi wrapper key deta hai, kabhi seedha block
    if not merged:
        raise RuntimeError(errors[0] if errors else "No result")
    if errors:
        merged["_errors"] = errors
    return merged


def mock_listing(details: dict, platforms: list[str]) -> dict:
    """API key na ho tab bhi app test ho sake."""
    name = details.get("product_type") or "Product"
    note = "[DEMO] Add GEMINI_API_KEY in .env to get real listings"
    out = {}
    for p in platforms:
        out[p] = {"title": f"{note} — {name}"} if p != "social" else {"instagram_caption": note}
    out["_demo"] = True
    return out


@app.get("/")
def home():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    return {"ok": True, "mode": "live" if API_KEY else "demo", "model": MODEL}


@app.post("/api/check-code")
def check_code(code: str = Form("")):
    ok, msg, left = codes.check(code)
    if not ok:
        raise HTTPException(403, msg)
    return {"remaining": left}


@app.post("/api/generate")
async def generate(
    image: UploadFile = File(...),
    code: str = Form(""),
    platforms: str = Form(""),
    product_type: str = Form(""),
    material: str = Form(""),
    color: str = Form(""),
    price: str = Form(""),
    occasion: str = Form(""),
    brand_name: str = Form(""),
    extra_notes: str = Form(""),
):
    ok, msg, _ = codes.check(code)
    if not ok:
        raise HTTPException(403, msg)

    chosen = [p for p in platforms.split(",") if p in PLATFORMS] or DEFAULT_PLATFORMS

    if not (image.content_type or "").startswith("image/"):
        raise HTTPException(400, "Please upload an image file (JPG, PNG or WEBP).")
    data = await image.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(400, "Image must be smaller than 8 MB.")

    details = dict(
        product_type=product_type, material=material, color=color, price=price,
        occasion=occasion, brand_name=brand_name, extra_notes=extra_notes,
    )
    if not API_KEY:
        return mock_listing(details, chosen)
    small, mime = await asyncio.to_thread(shrink_image, data, image.content_type)
    try:
        result = await generate_all(small, mime, details, chosen)
    except Exception as e:  # noqa: BLE001
        if "Expecting" in str(e) or "JSON" in str(e):
            raise HTTPException(502, "Something went wrong while writing the listing. Please try again.")
        raise HTTPException(502, f"Could not generate the listing. Please try again. ({e})")

    # Sirf successful listing pe hi count kam hota hai.
    result["_remaining"] = codes.use_one(code)
    return result
