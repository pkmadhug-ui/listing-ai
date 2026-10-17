import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from . import codes
from .prompt import DEFAULT_PLATFORMS, PLATFORMS, build_system_prompt, build_user_prompt

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
MAX_IMAGE_BYTES = 8 * 1024 * 1024
STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Listing AI")


def call_gemini(image: bytes, mime: str, details: dict, platforms: list[str]) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=API_KEY)
    resp = client.models.generate_content(
        model=MODEL,
        contents=[types.Part.from_bytes(data=image, mime_type=mime), build_user_prompt(details)],
        config=types.GenerateContentConfig(
            system_instruction=build_system_prompt(platforms),
            response_mime_type="application/json",
            temperature=0.7,
        ),
    )
    return json.loads(resp.text)


def mock_listing(details: dict, platforms: list[str]) -> dict:
    """API key na ho tab bhi app test ho sake."""
    name = details.get("product_type") or "Product"
    note = "[DEMO] GEMINI_API_KEY .env mein daalo, tab asli listing aayegi"
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
        raise HTTPException(400, "Sirf image file upload karo (jpg/png/webp).")
    data = await image.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(400, "Image 8MB se chhoti honi chahiye.")

    details = dict(
        product_type=product_type, material=material, color=color, price=price,
        occasion=occasion, brand_name=brand_name, extra_notes=extra_notes,
    )
    if not API_KEY:
        return mock_listing(details, chosen)
    try:
        result = call_gemini(data, image.content_type, details, chosen)
    except json.JSONDecodeError:
        raise HTTPException(502, "AI ne galat format diya, ek baar phir try karo.")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"AI call fail hua: {e}")

    # Sirf successful listing pe hi count kam hota hai.
    result["_remaining"] = codes.use_one(code)
    return result
