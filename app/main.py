import hashlib
import random
import string
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models.url import URL

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

BASE62_ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase

def base62_encode(num: int) -> str:
    if num == 0:
        return BASE62_ALPHABET[0]
    res = []
    base = len(BASE62_ALPHABET)
    while num > 0:
        res.append(BASE62_ALPHABET[num % base])
        num //= base
    return "".join(reversed(res))

@app.get("/health")
def health():
  return {"status": "ok"}

@app.post("/shorten")
def shorten(long_url: str, db: Session = Depends(get_db)) -> dict:
    # Implement Base62 encoder (characters 0–9, a–z, A–Z) — this is the core algorithm, understand it deeply
    # Handle collision: if code exists, append a random suffix and retry (max 3 attempts)
    hash_obj = hashlib.md5(long_url.encode())
    num = int.from_bytes(hash_obj.digest()[:8], "little")
    base_code = base62_encode(num)[:8]
    
    for attempt in range(4):  # Initial try + max 3 retries
        code = base_code
        if attempt > 0:
            suffix = "".join(random.choices(BASE62_ALPHABET, k=attempt))
            code += suffix
            
        existing = db.query(URL).filter(URL.short_code == code).first()
        if existing:
            if existing.original_url == long_url:
                return {"short_code": code}
            if attempt == 3:
                break
            continue
            
        new_url = URL(original_url=long_url, short_code=code)
        db.add(new_url)
        try:
            db.commit()
            return {"short_code": code}
        except IntegrityError:
            db.rollback()
            if attempt == 3:
                break
            continue
            
    raise HTTPException(status_code=500, detail="Failed to generate short code after 3 retries")


@app.get("/{short_code}")
def redirect(short_code: str, db: Session = Depends(get_db)):
    # look up DB, return HTTP 301/302 redirect to original URL
    # Input validation: reject invalid URLs, malformed codes, and expired links (404)
    if not short_code.isalnum():
        raise HTTPException(status_code=400, detail="Malformed short code")

    url = db.query(URL).filter(URL.short_code == short_code).first()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
        
    if url.expires_at and url.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="URL has expired")

    return RedirectResponse(url=url.original_url, status_code=302)
