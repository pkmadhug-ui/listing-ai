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

## 24x7 chalana (VPS pe, ek baar)

```
bash deploy/install-service.sh   # app ko background service bana deta hai
bash deploy/update.sh            # baad mein naya code laane + restart ke liye
journalctl -u listing-ai -f      # live logs
```

## Invite codes

App sirf invite code se chalta hai. Har code ki fixed limit hoti hai, taaki API ka kharcha control mein rahe.
Codes VPS pe `codes.json` mein save hote hain (GitHub pe nahi jaate).

```
python -m app.codes add Pankaj 500     # naya code, 500 listings
python -m app.codes list               # saare codes aur usage
python -m app.codes topup LA-XXXXXX 50 # limit badhao
python -m app.codes off LA-XXXXXX      # code band karo
```

## Roadmap
- [x] Week 1: Photo + details → listing (Gemini)
- [x] Multi-platform: Shopify, Social, Meesho, Flipkart, Amazon + invite codes
- [ ] Shopify mein seedha Draft product create
- [ ] Week 3: Login + Razorpay subscription
- [ ] Week 4: Landing page + marketing
