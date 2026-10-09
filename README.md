# Listing AI

Product photo + basic details → complete Shopify listing (SEO title, description, meta, tags, alt text, social captions, hashtags, FAQ).

## Chalane ka tareeka (VPS ya laptop)

1. Packages install karo:
   ```
   pip install -r requirements.txt
   ```
2. `.env.example` ko copy karke `.env` banao aur apni Gemini API key daalo.
3. Server chalao:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
4. Browser mein kholo: `http://localhost:8000` (VPS pe `http://<VPS-IP>:8000`)

API key nahi daali toh app **demo mode** mein chalega (dummy output), taaki setup test ho sake.

## Roadmap
- [x] Week 1: Photo + details → listing (Gemini)
- [ ] Week 2: Shopify mein seedha product create
- [ ] Week 3: Login + Razorpay subscription
- [ ] Week 4: Landing page + marketing
