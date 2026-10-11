import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .prompt import SYSTEM_PROMPT, build_user_prompt

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
MAX_IMAGE_BYTES = 8 * 1024 * 1024
STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Listing AI")


def call_gemini(image: bytes, mime: str, details: dict) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=API_KEY)
    resp = client.models.generate_content(
        model=MODEL,
        contents=[types.Part.from_bytes(data=image, mime_type=mime), build_user_prompt(details)],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.7,
        ),
    )
    return json.loads(resp.text)


def mock_listing(details: dict) -> dict:
    """API key na ho tab bhi app test ho sake."""
    name = details.get("product_type") or "Product"
    return {
        "title": f"[DEMO] {name} — add GEMINI_API_KEY in .env for real output",
        "description_html": "<p>Demo mode. Real description will appear once the API key is set.</p>",
        "seo_meta_title": f"{name} | Demo",
        "seo_meta_description": "Demo mode output.",
        "url_handle": name.lower().replace(" ", "-"),
        "focus_keyword": name.lower(),
        "long_tail_keywords": [],
        "image_alt_text": name,
        "tags": [],
        "instagram_caption": "",
        "pinterest_description": "",
        "reel_hook": "",
        "hashtags": [],
        "festival_angle": "",
        "faq": [],
        "_demo": True,
    }


@app.get("/")
def home():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    return {"ok": True, "mode": "live" if API_KEY else "demo", "model": MODEL}


@app.post("/api/generate")
async def generate(
    image: UploadFile = File(...),
    product_type: str = Form(""),
    material: str = Form(""),
    color: str = Form(""),
    price: str = Form(""),
    occasion: str = Form(""),
    brand_name: str = Form(""),
    extra_notes: str = Form(""),
):
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
        return mock_listing(details)
    try:
        return call_gemini(data, image.content_type, details)
    except json.JSONDecodeError:
        raise HTTPException(502, "AI ne galat format diya, ek baar phir try karo.")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"AI call fail hua: {e}")
